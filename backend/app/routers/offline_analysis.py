import os
import time
import shutil
import threading
import cv2
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db, SessionLocal
from app.models import OfflineAnalysisJobModel
from app.schemas import OfflineJobResponse
from app.ai.detector import detector
from app.ai.density import CrowdDensityEvaluator

router = APIRouter(prefix="/offline-analysis", tags=["Offline Video Analysis"])

UPLOAD_OFFLINE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "offline_videos")
os.makedirs(UPLOAD_OFFLINE_DIR, exist_ok=True)

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

# Active running worker flags
active_jobs: dict = {}

def _run_offline_analysis(job_id: str, file_path: str):
    """
    Background worker that executes genuine OpenCV + YOLO computer vision processing
    on the recorded video file frame-by-frame. Calculates actual frame counts, FPS,
    peak crowd metrics, and summary.
    """
    db = SessionLocal()
    job = db.query(OfflineAnalysisJobModel).filter(OfflineAnalysisJobModel.id == job_id).first()
    if not job:
        db.close()
        return

    job.status = "processing"
    db.commit()

    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        job.status = "failed"
        job.error_message = f"Could not decode video file '{os.path.basename(file_path)}'"
        db.commit()
        db.close()
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
    duration_secs = int(total_frames / max(1.0, fps))
    m, s = divmod(duration_secs, 60)
    h, m = divmod(m, 60)
    duration_str = f"{h:02d}:{m:02d}:{s:02d}"

    job.total_frames = total_frames
    job.resolution = f"{width}x{height}"
    job.duration = duration_str
    db.commit()

    frame_idx = 0
    counts = []
    densities = []
    start_time = time.time()
    active_jobs[job_id] = True

    try:
        # Sample every 3rd frame to optimize offline analysis turnaround while retaining high fidelity
        sample_step = 2 if total_frames > 300 else 1

        while cap.isOpened() and active_jobs.get(job_id, False):
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            if frame_idx % sample_step != 0:
                continue

            boxes, count, _ = detector.process_frame(frame, draw_boxes=False)
            density = CrowdDensityEvaluator.calculate_density(count, capacity=200)

            counts.append(count)
            densities.append(density)

            # Update progress periodically
            if frame_idx % 20 == 0 or frame_idx == total_frames:
                elapsed = time.time() - start_time
                actual_fps = round(frame_idx / max(0.1, elapsed), 1)
                pct = int(min(99, (frame_idx / max(1, total_frames)) * 100))

                job.frames_processed = frame_idx
                job.progress = pct
                job.processing_fps = actual_fps
                job.peak_count = max(counts) if counts else 0
                job.avg_count = round(sum(counts) / max(1, len(counts)), 1) if counts else 0.0
                job.peak_density = max(densities) if densities else 0.0
                db.commit()

        cap.release()

        if active_jobs.get(job_id, False):
            peak_cnt = max(counts) if counts else 0
            avg_cnt = round(sum(counts) / max(1, len(counts)), 1) if counts else 0.0
            peak_dens = max(densities) if densities else 0.0
            elapsed_tot = time.time() - start_time
            fin_fps = round(frame_idx / max(0.1, elapsed_tot), 1)

            risk_sum = "CRITICAL" if peak_dens >= 85.0 else "HIGH" if peak_dens >= 70.0 else "MEDIUM" if peak_dens >= 40.0 else "LOW"

            job.status = "completed"
            job.progress = 100
            job.frames_processed = frame_idx
            job.processing_fps = fin_fps
            job.peak_count = peak_cnt
            job.avg_count = avg_cnt
            job.peak_density = peak_dens
            job.risk_summary = risk_sum
            job.result_summary = (
                f"Analysis completed across {frame_idx} decoded frames at {fin_fps} FPS. "
                f"Peak occupancy: {peak_cnt} persons ({peak_dens}% density). Risk Level: {risk_sum}."
            )
            job.completed_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
    finally:
        active_jobs.pop(job_id, None)
        db.close()


@router.get("/hardware")
@router.get("/hardware-info")
def get_hardware_info():
    """Returns genuine hardware acceleration and model status without fabricating fake GPU names."""
    return detector.get_runtime_engine_info()


@router.get("/jobs", response_model=List[OfflineJobResponse])
def get_offline_jobs(db: Session = Depends(get_db)):
    """Fetch all offline video analysis jobs."""
    return db.query(OfflineAnalysisJobModel).order_by(OfflineAnalysisJobModel.created_at.desc()).all()


@router.get("/jobs/{job_id}", response_model=OfflineJobResponse)
def get_offline_job(job_id: str, db: Session = Depends(get_db)):
    """Fetch single offline video analysis job by ID."""
    job = db.query(OfflineAnalysisJobModel).filter(OfflineAnalysisJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return job


@router.post("/upload", response_model=OfflineJobResponse, status_code=status.HTTP_201_CREATED)
async def upload_offline_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload pre-recorded CCTV video file and create a real offline analysis processing job."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{ext}'. Allowed: MP4, AVI, MOV, MKV.")

    job_id = f"job-{int(time.time() * 1000)}"
    save_filename = f"{job_id}{ext}"
    dest_path = os.path.join(UPLOAD_OFFLINE_DIR, save_filename)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size_mb = round(os.path.getsize(dest_path) / (1024.0 * 1024.0), 2)

    new_job = OfflineAnalysisJobModel(
        id=job_id,
        filename=file.filename,
        file_path=dest_path,
        status="queued",
        progress=0,
        file_size_mb=file_size_mb,
        total_frames=0,
        frames_processed=0,
        peak_count=0,
        avg_count=0.0,
        peak_density=0.0,
        risk_summary="LOW",
        result_summary="Queued for computer vision detection...",
        created_at=datetime.utcnow()
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Spawn background worker thread
    t = threading.Thread(target=_run_offline_analysis, args=(job_id, dest_path), daemon=True)
    t.start()

    return new_job


@router.post("/jobs/{job_id}/cancel")
def cancel_offline_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel a running offline video analysis job."""
    job = db.query(OfflineAnalysisJobModel).filter(OfflineAnalysisJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    active_jobs[job_id] = False
    job.status = "failed"
    job.error_message = "Cancelled by operator"
    db.commit()
    return {"message": "Job cancelled", "id": job_id}

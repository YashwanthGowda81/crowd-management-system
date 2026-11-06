import time
import os
import shutil
import cv2
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import get_db
from app.models import CameraModel, EventModel, User
from app.schemas import CameraCreate, CameraUpdate, CameraResponse
from app.ai.stream_processor import stream_manager
from app.auth_utils import decode_access_token

router = APIRouter(prefix="/cameras", tags=["Cameras"])
security = HTTPBearer(auto_error=False)

def get_current_user_from_auth(auth: Optional[HTTPAuthorizationCredentials], db: Session) -> Optional[User]:
    if not auth or not auth.credentials:
        return None
    try:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("sub"):
            return db.query(User).filter(User.email == payload["sub"]).first()
    except Exception:
        pass
    return None

UPLOAD_VIDEOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "videos")
os.makedirs(UPLOAD_VIDEOS_DIR, exist_ok=True)

def _ensure_default_cameras(db: Session):
    """No-op: Cameras have been reset. Cameras are registered through the camera setup workflow."""
    pass

@router.get("", response_model=List[CameraResponse])
def get_cameras(
    event_id: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Fetch camera records directly from database, optionally filtered by event_id."""
    _ensure_default_cameras(db)
    user = get_current_user_from_auth(auth, db)
    target_event_id = event_id
    if user and event_id:
        evt = db.query(EventModel).filter(EventModel.id == event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot read cameras for an event owned by another account."
            )
    elif not target_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id
        else:
            return []

    query = db.query(CameraModel)
    if target_event_id:
        query = query.filter(CameraModel.event_id == target_event_id)
    return query.all()

@router.get("/diagnostics")
def get_pipeline_diagnostics(
    event_id: Optional[str] = None,
    since_id: int = 0,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Returns live parallel video capture and batched YOLO inference diagnostics snapshot.
    Enforces authentication and event-level isolation. Read-only without modifying processing state.
    """
    user = get_current_user_from_auth(auth, db)
    target_event_id = event_id

    if user and event_id:
        evt = db.query(EventModel).filter(EventModel.id == event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot read diagnostics for an event owned by another account."
            )
    elif not target_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id

    # Build camera metadata lookup for human-readable labels
    cam_meta = {}
    query = db.query(CameraModel)
    if target_event_id:
        query = query.filter(CameraModel.event_id == target_event_id)
    cams = query.all()
    for c in cams:
        cam_meta[c.id] = {
            "name": c.name,
            "location": c.location,
            "zone_id": c.zone_id
        }

    from app.ai.diagnostics import pipeline_diagnostics
    snapshot = pipeline_diagnostics.get_snapshot(
        event_id=target_event_id,
        since_event_id=since_id,
        cam_metadata_map=cam_meta
    )
    return snapshot

@router.get("/get/{cam_id}", response_model=CameraResponse)
@router.get("/{cam_id}", response_model=CameraResponse)
def get_single_camera(
    cam_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Fetch single camera by ID with authorization verification."""
    cam = db.query(CameraModel).filter(CameraModel.id == cam_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    user = get_current_user_from_auth(auth, db)
    if user and cam.event_id:
        evt = db.query(EventModel).filter(EventModel.id == cam.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot access a camera belonging to another account's event."
            )
    return cam

@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(
    cam: CameraCreate,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Register new IP/RTSP camera record in READY status (Requires user to click ANALYZE)."""
    cam_id = f"cam-{int(time.time() * 1000)}"
    user = get_current_user_from_auth(auth, db)
    assigned_event_id = cam.event_id
    if not assigned_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            assigned_event_id = evt.id

    if assigned_event_id and user:
        evt = db.query(EventModel).filter(EventModel.id == assigned_event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot register a camera for an event owned by another account."
            )

    db_cam = CameraModel(
        id=cam_id,
        name=cam.name,
        rtsp_url=cam.rtsp_url,
        location=cam.location,
        zone_id=cam.zone_id,
        event_id=assigned_event_id,
        status="ready",
        enabled=False,
        resolution=cam.resolution or "1920x1080",
        fps=cam.fps or 30,
        last_active="Ready for analysis",
        capacity=cam.capacity or 200,
        count=0,
        density=0.0,
        risk="low",
        health="green",
        source_type="rtsp",
        source_fps=30.0,
        processing_fps=30.0,
        playback_status="ready"
    )
    db.add(db_cam)
    db.commit()
    db.refresh(db_cam)

    print(f"[CAMERA][REGISTERED] Camera ID: {cam_id} | Name: {cam.name} | Status: READY")
    return db_cam

@router.post("/webcam", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def add_webcam_camera(
    name: Optional[str] = Form("Web Camera 01"),
    location: Optional[str] = Form("Local Station"),
    capacity: Optional[int] = Form(100),
    zone_id: Optional[str] = Form(None),
    event_id: Optional[str] = Form(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Register PC/Laptop Live Webcam in READY status."""
    cam_id = f"cam-webcam-{int(time.time() * 1000)}"
    user = get_current_user_from_auth(auth, db)
    assigned_event_id = event_id
    if not assigned_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            assigned_event_id = evt.id

    if assigned_event_id and user:
        evt = db.query(EventModel).filter(EventModel.id == assigned_event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot register a camera for an event owned by another account."
            )

    db_cam = CameraModel(
        id=cam_id,
        name=name,
        rtsp_url="0",
        location=location,
        zone_id=zone_id,
        event_id=assigned_event_id,
        status="ready",
        enabled=False,
        resolution="1280x720",
        fps=30,
        last_active="Ready for analysis",
        capacity=capacity,
        count=0,
        density=0.0,
        risk="low",
        health="green",
        source_type="webcam",
        source_fps=30.0,
        processing_fps=30.0,
        playback_status="ready"
    )
    db.add(db_cam)
    db.commit()
    db.refresh(db_cam)

    print(f"[CAMERA][WEBCAM REGISTERED] Camera ID: {cam_id} | Name: {name} | Status: READY")
    return db_cam

@router.post("/upload-video", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def upload_video_camera(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    location: Optional[str] = Form("Uploaded Video Source"),
    capacity: Optional[int] = Form(200),
    zone_id: Optional[str] = Form(None),
    event_id: Optional[str] = Form(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Upload CCTV video file (MP4, AVI, MOV, MKV) and create virtual camera record in READY status."""
    cam_id = f"cam-vid-{int(time.time() * 1000)}"
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in [".mp4", ".avi", ".mov", ".mkv"]:
        raise HTTPException(status_code=400, detail="Unsupported video format. Allowed: MP4, AVI, MOV, MKV")

    user = get_current_user_from_auth(auth, db)
    assigned_event_id = event_id
    if not assigned_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            assigned_event_id = evt.id

    if assigned_event_id and user:
        evt = db.query(EventModel).filter(EventModel.id == assigned_event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot upload a video for an event owned by another account."
            )

    filename = f"{cam_id}{ext}"
    file_path = os.path.join(UPLOAD_VIDEOS_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    camera_name = name if name and name.strip() else f"CCTV Footage ({file.filename})"

    db_cam = CameraModel(
        id=cam_id,
        name=camera_name,
        rtsp_url=file_path,
        location=location,
        zone_id=zone_id,
        event_id=assigned_event_id,
        status="ready",
        enabled=False,
        resolution="1920x1080",
        fps=30,
        last_active="Ready for analysis",
        capacity=capacity,
        count=0,
        density=0.0,
        risk="low",
        health="green",
        source_type="video",
        source_fps=30.0,
        processing_fps=30.0,
        playback_status="ready"
    )
    db.add(db_cam)
    db.commit()
    db.refresh(db_cam)

    print(f"[VIDEO][VIRTUAL CAMERA CREATED] Video: {file.filename} | Camera ID: {cam_id} | Name: {camera_name} | Status: READY")
    return db_cam

@router.get("/{cam_id}/stream")
def stream_camera_video(
    cam_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Live MJPEG video stream displaying actual CCTV frames with real-time YOLO person detection and tracking overlays."""
    cam = db.query(CameraModel).filter(CameraModel.id == cam_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    user = get_current_user_from_auth(auth, db)
    if user and cam.event_id:
        evt = db.query(EventModel).filter(EventModel.id == cam.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot view stream for a camera belonging to another account's event."
            )

    worker = stream_manager.workers.get(cam_id)
    if not worker:
        from app.ai.ingestion_manager import ingestion_coordinator
        if not ingestion_coordinator.is_owner:
            owner_pid = ingestion_coordinator.get_owner_pid()
            owner_str = f"PID: {owner_pid}" if owner_pid is not None else "PID: active owner"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Camera preview stream is managed by the ingestion owner process ({owner_str}). Follower API workers cannot start local camera ingestion workers."
            )
        worker = stream_manager.get_or_create_worker(
            cam_id, cam.rtsp_url, cam.source_type or "video", cam.capacity or 200, cam.event_id
        )

    def generate_frames():
        target_delay = 1.0 / max(1.0, worker.source_fps)
        last_seq = -1
        while True:
            if not worker.is_running:
                break
            if worker.last_annotated_frame is not None and worker.frame_seq != last_seq:
                last_seq = worker.frame_seq
                frame_to_stream = worker.last_annotated_frame
                # High-efficiency streaming: downscale frames wider than 1280 to save CPU
                if frame_to_stream.shape[1] > 1280:
                    scale = 1280.0 / frame_to_stream.shape[1]
                    new_h = int(frame_to_stream.shape[0] * scale)
                    frame_to_stream = cv2.resize(frame_to_stream, (1280, new_h), interpolation=cv2.INTER_AREA)
                ret, jpeg = cv2.imencode('.jpg', frame_to_stream, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(min(0.020, target_delay * 0.6))

    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@router.post("/{cam_id}/analyze", response_model=CameraResponse)
def analyze_camera(
    cam_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Explicitly start AI analysis pipeline for camera."""
    cam = db.query(CameraModel).filter(CameraModel.id == cam_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    user = get_current_user_from_auth(auth, db)
    if user and cam.event_id:
        evt = db.query(EventModel).filter(EventModel.id == cam.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot analyze a camera belonging to another account's event."
            )

    cam.playback_status = "analyzing"
    cam.status = "online"
    cam.enabled = True
    cam.last_active = "Just now"
    # Fresh analysis session invalidates previous heartbeat (Fix B)
    cam.last_frame_timestamp = None
    cam.last_frame_seq = 0

    from app.ai.ingestion_manager import ingestion_coordinator
    if ingestion_coordinator.is_owner:
        worker = stream_manager.workers.get(cam_id)
        if worker:
            worker.resume()
        else:
            stream_manager.get_or_create_worker(cam_id, cam.rtsp_url, cam.source_type, cam.capacity, cam.event_id)

    db.commit()
    db.refresh(cam)
    print(f"[CAMERA][ANALYZE] Camera ID: {cam_id} | Name: {cam.name} | Status: ANALYZING")
    return cam

@router.put("/{cam_id}/playback", response_model=CameraResponse)
def control_camera_playback(
    cam_id: str,
    action: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Control camera/video playback (analyze, play, pause, stop, restart)."""
    cam = db.query(CameraModel).filter(CameraModel.id == cam_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    user = get_current_user_from_auth(auth, db)
    if user and cam.event_id:
        evt = db.query(EventModel).filter(EventModel.id == cam.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot control a camera belonging to another account's event."
            )

    from app.ai.ingestion_manager import ingestion_coordinator
    worker = stream_manager.workers.get(cam_id)

    if action in ["analyze", "start_analysis", "play"]:
        # Fresh analysis session or play from inactive invalidates heartbeat (Fix B)
        if action in ["analyze", "start_analysis"] or cam.playback_status in ["stopped", "ready"]:
            cam.last_frame_timestamp = None
            cam.last_frame_seq = 0
        cam.playback_status = "analyzing"
        cam.status = "online"
        cam.enabled = True
        cam.last_active = "Just now"
        if ingestion_coordinator.is_owner:
            if worker:
                worker.resume()
            else:
                stream_manager.get_or_create_worker(cam_id, cam.rtsp_url, cam.source_type, cam.capacity, cam.event_id)

    elif action == "pause":
        cam.playback_status = "paused"
        if ingestion_coordinator.is_owner and worker:
            worker.pause()

    elif action in ["stop", "stop_analysis"]:
        cam.playback_status = "stopped"
        cam.status = "ready"
        cam.enabled = False
        cam.last_frame_timestamp = None
        cam.last_frame_seq = 0
        if ingestion_coordinator.is_owner and worker:
            worker.stop()

    elif action == "restart":
        cam.playback_status = "analyzing"
        cam.status = "online"
        cam.enabled = True
        cam.last_active = "Just now"
        cam.last_frame_timestamp = None
        cam.last_frame_seq = 0
        if ingestion_coordinator.is_owner:
            if worker:
                worker.stop()
            stream_manager.get_or_create_worker(cam_id, cam.rtsp_url, cam.source_type, cam.capacity, cam.event_id)

    db.commit()
    db.refresh(cam)
    return cam

@router.put("/{cam_id}", response_model=CameraResponse)
def update_camera(
    cam_id: str,
    cam_data: CameraUpdate,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Update camera attributes in MySQL database."""
    cam = db.query(CameraModel).filter(CameraModel.id == cam_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    user = get_current_user_from_auth(auth, db)
    if user and cam.event_id:
        evt = db.query(EventModel).filter(EventModel.id == cam.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot modify a camera belonging to another account's event."
            )

    if cam_data.name is not None:
        cam.name = cam_data.name
    if cam_data.rtsp_url is not None:
        cam.rtsp_url = cam_data.rtsp_url
    if cam_data.location is not None:
        cam.location = cam_data.location
    if cam_data.status is not None:
        cam.status = cam_data.status
        if cam.status != "online":
            cam.last_frame_timestamp = None
            cam.last_frame_seq = 0
    if cam_data.enabled is not None:
        cam.enabled = cam_data.enabled
        if not cam.enabled:
            cam.last_frame_timestamp = None
            cam.last_frame_seq = 0
    if cam_data.resolution is not None:
        cam.resolution = cam_data.resolution
    if cam_data.fps is not None:
        cam.fps = cam_data.fps
    if cam_data.capacity is not None:
        cam.capacity = cam_data.capacity
    if cam_data.zone_id is not None:
        cam.zone_id = cam_data.zone_id
    if cam_data.event_id is not None:
        cam.event_id = cam_data.event_id

    db.commit()
    db.refresh(cam)
    return cam

@router.put("/{cam_id}/toggle-enabled", response_model=CameraResponse)
def toggle_camera_enabled(
    cam_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Toggle enabled status in MySQL database."""
    cam = db.query(CameraModel).filter(CameraModel.id == cam_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    user = get_current_user_from_auth(auth, db)
    if user and cam.event_id:
        evt = db.query(EventModel).filter(EventModel.id == cam.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot modify a camera belonging to another account's event."
            )

    cam.enabled = not cam.enabled
    if not cam.enabled:
        from app.ai.ingestion_manager import ingestion_coordinator
        if ingestion_coordinator.is_owner and stream_manager.workers.get(cam_id):
            stream_manager.stop_worker(cam_id)
        cam.playback_status = "stopped"
        cam.last_frame_timestamp = None
        cam.last_frame_seq = 0
    db.commit()
    db.refresh(cam)
    return cam

@router.put("/{cam_id}/toggle-status", response_model=CameraResponse)
def toggle_camera_status(
    cam_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Toggle online/offline status in MySQL database."""
    cam = db.query(CameraModel).filter(CameraModel.id == cam_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    user = get_current_user_from_auth(auth, db)
    if user and cam.event_id:
        evt = db.query(EventModel).filter(EventModel.id == cam.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot modify a camera belonging to another account's event."
            )

    cam.status = "offline" if cam.status == "online" else "online"
    if cam.status != "online":
        cam.last_frame_timestamp = None
        cam.last_frame_seq = 0
    db.commit()
    db.refresh(cam)
    return cam

@router.delete("/{cam_id}")
def delete_camera(
    cam_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Delete camera row from MySQL database."""
    cam = db.query(CameraModel).filter(CameraModel.id == cam_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    user = get_current_user_from_auth(auth, db)
    if user and cam.event_id:
        evt = db.query(EventModel).filter(EventModel.id == cam.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot delete a camera belonging to another account's event."
            )

    from app.ai.ingestion_manager import ingestion_coordinator
    if ingestion_coordinator.is_owner and stream_manager.workers.get(cam_id):
        stream_manager.stop_worker(cam_id)
    db.delete(cam)
    db.commit()
    return {"message": "Camera deleted successfully", "id": cam_id}

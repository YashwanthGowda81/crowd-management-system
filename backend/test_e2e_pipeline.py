import asyncio
import time
import os
import sys

# Add backend to path

sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal
from app.models import CameraModel, ZoneModel, CrowdAnalyticsModel, AlertModel, EventModel
from app.ai.stream_processor import stream_manager
from app.routers.websocket import start_ai_processing_loop
from app.routers.analytics import get_crowd_analysis
from app.routers.alerts import get_alerts
from app.routers.reports import generate_pdf_report
from fastapi.responses import Response

async def run_pipeline_test():
    print("=" * 60)
    print("STARTING E2E PIPELINE & DATA CONSISTENCY TEST")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # 1. Fetch default event and cameras
        evt = db.query(EventModel).filter(EventModel.id == "evt-1793089557795").first()
        if not evt:
            print("[FAIL] Default event not found!")
            return False
            
        cameras = db.query(CameraModel).filter(CameraModel.event_id == evt.id).all()
        print(f"[SETUP] Found event: {evt.title} ({evt.id}) with {len(cameras)} cameras")
        for c in cameras:
            print(f"  - Camera: {c.id} ({c.name}), type={c.source_type}, source={os.path.basename(c.rtsp_url or '')}")

        # Set first camera to online and analyzing status
        cam = cameras[0]
        cam.status = "online"
        cam.enabled = True
        cam.playback_status = "analyzing"
        db.commit()

        # 2. Get or create worker for cam
        stream_manager._allow_non_owner = True
        worker = stream_manager.get_or_create_worker(
            camera_id=cam.id,
            source=cam.rtsp_url,
            source_type=cam.source_type or "video",
            capacity=cam.capacity or 200,
            event_id=evt.id
        )
        print(f"[WORKER] Started stream worker for {cam.id}. Is running: {worker.is_running}")

        # Let worker process for 2 seconds to gather initial detections
        await asyncio.sleep(2.0)

        # 3. Launch background processing loop as a task for 5 seconds
        loop_task = asyncio.create_task(start_ai_processing_loop())
        print("[LOOP] AI Processing loop running in background for 5 seconds...")
        await asyncio.sleep(5.0)

        # Cancel background loop
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass
        print("[LOOP] AI Processing loop stopped.")

        # 4. Verify DB updates on CameraModel
        db.expire_all()
        cam_fresh = db.query(CameraModel).filter(CameraModel.id == cam.id).first()
        print(f"[DB CAM] count={cam_fresh.count}, density={cam_fresh.density:.2f}%, risk={cam_fresh.risk}, fps={cam_fresh.processing_fps}")
        assert cam_fresh.count is not None, "Camera count was not updated!"
        assert cam_fresh.count > 0, f"Expected non-zero person detection, got {cam_fresh.count}"

        # 5. Verify CrowdAnalyticsModel persistence
        analytics_rows = db.query(CrowdAnalyticsModel).filter(
            CrowdAnalyticsModel.camera_id == cam.id,
            CrowdAnalyticsModel.event_id == evt.id
        ).all()
        assert len(analytics_rows) > 0, "No CrowdAnalyticsModel rows were persisted!"
        latest_row = analytics_rows[-1]
        print(f"  Latest row: count={latest_row.count}, density={latest_row.density_pct:.2f}%, risk={latest_row.risk_level}")
        assert latest_row.count > 0, f"Latest analytics row count should be positive, got {latest_row.count}"
        assert cam_fresh.count > 0, f"Camera count should be positive, got {cam_fresh.count}"

        # 6. Verify cross-page consistency via get_live_status & get_crowd_analysis
        from app.routers.analytics import get_live_status
        live_status = get_live_status(event_id=evt.id, db=db, auth=None)
        print(f"[API LIVE STATUS] total_count={live_status['total_count']}, avg_density={live_status['average_density']:.2f}%, active_cameras={live_status['active_cameras']}, status={live_status['system_status']}")
        assert live_status['total_count'] >= cam_fresh.count, "Live status total_count should reflect active camera detections!"

        analysis_data = get_crowd_analysis(event_id=evt.id, db=db, auth=None)
        print(f"[API ANALYSIS] total_count={analysis_data['total_count']}, avg_speed={analysis_data['average_walking_speed_ms']}m/s, unique_tracked={analysis_data['unique_tracked_window']}")
        print(f"[API ANALYSIS] Hourly trend points: {len(analysis_data['hourly_trend'])}")
        assert analysis_data['total_count'] >= cam_fresh.count, "Aggregated total_count should reflect active camera count!"
        assert len(analysis_data['hourly_trend']) > 0, "Hourly trend should contain persisted data points!"

        # 7. Verify Event Isolation
        other_event_id = "evt-non-existent-9999"
        isolated_status = get_live_status(event_id=other_event_id, db=db, auth=None)
        isolated_analysis = get_crowd_analysis(event_id=other_event_id, db=db, auth=None)
        print(f"[ISOLATION] Non-existent event total_count={isolated_status['total_count']}, trend points={len(isolated_analysis['hourly_trend'])}")
        assert isolated_status['total_count'] == 0, "Event isolation failed: other event got non-zero count!"
        assert len(isolated_analysis['hourly_trend']) == 0, "Event isolation failed: other event got trend points!"

        # 8. Verify Alert endpoint
        alerts = get_alerts(event_id=evt.id, db=db, auth=None)
        print(f"[API ALERTS] Found {len(alerts)} alerts for event {evt.id}")
        for a in alerts:
            print(f"  - Alert: {a.id} [{a.level}] {a.title}: {a.description} (resolved={a.resolved})")

        # 9. Verify PDF Report Generation
        pdf_resp = generate_pdf_report(event_id=evt.id, db=db)
        assert isinstance(pdf_resp, Response), "Report did not return a Response object!"
        print(f"[REPORTS] Generated PDF report: {len(pdf_resp.body)} bytes, media_type={pdf_resp.media_type}")
        assert len(pdf_resp.body) > 1000, "PDF body unexpectedly small!"

        # Stop all workers
        for worker_id in list(stream_manager.workers.keys()):
            stream_manager.stop_worker(worker_id)
        print("[CLEANUP] All workers stopped cleanly.")
        
        print("=" * 60)
        print("ALL E2E PIPELINE & DATA CONSISTENCY TESTS PASSED!")
        print("=" * 60)
        return True

    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(run_pipeline_test())
    sys.exit(0 if success else 1)

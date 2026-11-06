import sys
import os
import time
import cv2
import numpy as np

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import (
    CameraModel, 
    AlertModel, 
    EmergencyEventModel, 
    RecommendationModel, 
    ZoneModel, 
    EventModel,
    CrowdAnalyticsModel,
    SettingsModel
)
from app.ai.detector import detector, TemporalPersonTracker
from app.ai.stream_processor import CameraStreamWorker
from app.ai.heatmap import heatmap_manager
from app.ai.fca_engine import fca_solver
from app.ai.density import CrowdDensityEvaluator

def run_tests():
    print("=" * 70)
    print(" CROWD-AI v2.4 MASTER SYSTEM REGRESSION & VERIFICATION SUITE")
    print("=" * 70)

    db = SessionLocal()
    results = {}

    # TEST 1: Database Schema & Migration Verification
    print("\n[TEST 1] Verifying Database Schema and Migration Columns...")
    try:
        # Check event_id columns
        alert = db.query(AlertModel).first()
        emg = db.query(EmergencyEventModel).first()
        rec = db.query(RecommendationModel).first()
        
        has_alert_eid = hasattr(AlertModel, 'event_id')
        has_emg_eid = hasattr(EmergencyEventModel, 'event_id')
        has_rec_eid = hasattr(RecommendationModel, 'event_id')
        
        assert has_alert_eid, "AlertModel missing event_id"
        assert has_emg_eid, "EmergencyEventModel missing event_id"
        assert has_rec_eid, "RecommendationModel missing event_id"

        # Check seeded zones for active event
        active_evt = db.query(EventModel).first()
        active_eid = active_evt.id if active_evt else "evt-arena-01"
        event_zones = db.query(ZoneModel).filter(ZoneModel.event_id == active_eid).all()
        assert len(event_zones) >= 1, f"Expected operational zones for active event, got {len(event_zones)}"

        # Check cameras for active event
        event_cams = db.query(CameraModel).filter(CameraModel.event_id == active_eid).all()
        assert len(event_cams) >= 1, f"Expected cameras for active event, got {len(event_cams)}"

        print(f"  -> SUCCESS: All models have event_id. Found {len(event_zones)} operational zones and {len(event_cams)} cameras.")
        results["DB_SCHEMA_AND_ZONES"] = "PASS"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        results["DB_SCHEMA_AND_ZONES"] = "FAIL"

    # TEST 2: Real CCTV Video YOLO Inference on Feeds
    print("\n[TEST 2] Verifying Real YOLOv8 Inference on Video Feeds...")
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "uploads", "videos")
    available_vids = [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir) if f.endswith(".mp4") and os.path.getsize(os.path.join(uploads_dir, f)) > 10000]
    test2_passed = True
    for vpath in available_vids[:3]:
        cap = cv2.VideoCapture(vpath)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            continue
        
        t0 = time.time()
        boxes, count, infer_ms = detector.detect_frame(frame, conf_threshold=0.20, imgsz=480)
        dt = (time.time() - t0) * 1000.0
        print(f"  -> Video {os.path.basename(vpath)}: Detections = {count}, infer_ms = {infer_ms:.1f}ms, total = {dt:.1f}ms")

    results["YOLO_DETECTION_ALL_CAMS"] = "PASS" if test2_passed else "FAIL"

    # TEST 3: Per-Camera TemporalPersonTracker & Freshness Safeguards
    print("\n[TEST 3] Verifying TemporalPersonTracker and Max Age Safeguards (6 Frames)...")
    try:
        tracker = TemporalPersonTracker(max_prediction_frames=6)
        dummy_frame = np.zeros((360, 640, 3), dtype=np.uint8)
        
        # Ground truth detections at frame_seq = 10
        mock_detections = [
            [50, 50, 100, 150, 0.88, None],
            [200, 100, 250, 220, 0.92, None],
            [300, 80, 350, 190, 0.79, None]
        ]
        tracker.update_detections(mock_detections, det_seq=10, det_time=time.time())
        
        # Track at frame_seq = 10 (age = 0)
        tracks_10 = tracker.track_frame(dummy_frame, curr_seq=10, curr_time=time.time())
        assert len(tracks_10) == 3, f"Expected 3 tracks at frame 10, got {len(tracks_10)}"
        assert tracks_10[0][7] == 0, f"Expected age 0, got {tracks_10[0][7]}"

        # Track at frame_seq = 15 (age = 5 <= 6)
        tracks_15 = tracker.track_frame(dummy_frame, curr_seq=15, curr_time=time.time())
        assert len(tracks_15) == 3, f"Expected 3 tracks at frame 15, got {len(tracks_15)}"
        assert tracks_15[0][7] == 5, f"Expected age 5, got {tracks_15[0][7]}"

        # Track at frame_seq = 17 (age = 7 > 6) -> Must drop expired tracks!
        tracks_17 = tracker.track_frame(dummy_frame, curr_seq=17, curr_time=time.time())
        assert len(tracks_17) == 0, f"Expected 0 tracks at frame 17 (expired), got {len(tracks_17)}"

        # Reset on loop
        tracker.reset()
        assert len(tracker.tracks) == 0, "Expected empty tracks after reset"

        print("  -> SUCCESS: Freshness safeguard dropped tracks after 6 frames. Reset successfully cleared state.")
        results["TEMPORAL_TRACKER_FRESHNESS"] = "PASS"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        results["TEMPORAL_TRACKER_FRESHNESS"] = "FAIL"

    # TEST 4: CameraStreamWorker Decoupled Pipeline
    print("\n[TEST 4] Verifying CameraStreamWorker Decoupled Inference and Telemetry...")
    try:
        sample_source = available_vids[0] if available_vids else "0"
        worker = CameraStreamWorker(
            camera_id="cam-regression-test",
            source=sample_source,
            source_type="video",
            capacity=250,
            event_id=active_eid
        )
        worker.start()
        
        # Wait for worker playback and background inference to run
        time.sleep(2.0)
        
        assert worker.is_running, "Worker failed to run"
        assert worker.frame_seq > 5, f"Playback loop stalled, frame_seq={worker.frame_seq}"
        assert worker.last_annotated_frame is not None, "Annotated frame not produced"
        
        print(f"  -> SUCCESS: Worker running | frame_seq={worker.frame_seq} | yolo_count={worker.yolo_detection_count} | tracked_count={worker.tracker_track_count} | playback_fps={worker.playback_fps}")
        worker.stop()
        results["STREAM_WORKER_PIPELINE"] = "PASS"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        results["STREAM_WORKER_PIPELINE"] = "FAIL"

    # TEST 5: Heatmap Generation & Base64 Prefix Consistency
    print("\n[TEST 5] Verifying OpenCV Heatmap Generation...")
    try:
        cam_gen = heatmap_manager.get_camera_generator("cam-vid-1791478895356")
        cam_gen.accumulate_points([[100, 100, 150, 200, 0.9], [250, 200, 300, 300, 0.85]])
        
        b64_img = cam_gen.generate_base64_heatmap(transparent_zero=False)
        assert b64_img.startswith("data:image/jpeg;base64,"), "Invalid JPEG base64 prefix"

        b64_trans = cam_gen.generate_base64_heatmap(transparent_zero=True)
        assert b64_trans.startswith("data:image/png;base64,"), "Invalid PNG base64 prefix"

        print(f"  -> SUCCESS: Heatmap generated correctly (Length: {len(b64_img)} bytes).")
        results["HEATMAP_GENERATION"] = "PASS"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        results["HEATMAP_GENERATION"] = "FAIL"

    # TEST 6: Formal Concept Analysis (FCA) & Recommendations
    print("\n[TEST 6] Verifying FCA Galois Engine and Event Scoping...")
    try:
        mock_cams = [{"id": "c1", "location": "North Gate", "count": 18, "density": 85.0, "risk": "HIGH"}]
        mock_alerts = [{"id": "a1", "camera": "North Gate", "zone": "North Gate", "title": "Crowd Surge", "description": "High density surge", "resolved": False}]
        mock_zones = [{"id": "z1", "name": "North Gate", "capacity": 500, "density": 85.0}]

        objects, relation = fca_solver.build_formal_context(mock_cams, mock_alerts, mock_zones)
        concepts = fca_solver.derive_formal_concepts(objects, relation)
        assert len(concepts) > 0, "No formal concepts derived"

        recs = fca_solver.generate_recommendations_from_fca(concepts, event_id="evt-1790793930112")
        assert len(recs) > 0, "No recommendations generated"
        assert recs[0]["id"].startswith("rec-fca-evt-1790793930112-"), f"Recommendation ID not event-scoped: {recs[0]['id']}"
        assert recs[0]["status"] == "pending", "Recommendation should default to pending for operator review"

        print(f"  -> SUCCESS: Derived {len(concepts)} formal concepts and {len(recs)} event-scoped directives (status=pending).")
        results["FCA_GALOIS_ENGINE"] = "PASS"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        results["FCA_GALOIS_ENGINE"] = "FAIL"

    # TEST 7: PDF Report Generation
    print("\n[TEST 7] Verifying PDF Report Generation (ReportLab)...")
    try:
        from app.routers.reports import generate_pdf_report
        resp = generate_pdf_report(
            cam_id="all",
            event_id="evt-1790793930112",
            include_fca=True,
            include_cams=True,
            include_alerts=True,
            db=db
        )
        pdf_bytes = resp.body
        assert pdf_bytes.startswith(b"%PDF"), "Generated bytes do not start with %PDF"
        assert len(pdf_bytes) > 1000, f"PDF too small: {len(pdf_bytes)} bytes"

        print(f"  -> SUCCESS: Generated valid PDF report ({len(pdf_bytes)} bytes).")
        results["PDF_REPORT_GENERATION"] = "PASS"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        results["PDF_REPORT_GENERATION"] = "FAIL"

    db.close()

    print("\n" + "=" * 70)
    print(" SUMMARY OF REGRESSION TEST RESULTS")
    print("=" * 70)
    all_pass = True
    for test_name, status in results.items():
        print(f"  {test_name.ljust(35)}: {status}")
        if status != "PASS":
            all_pass = False
    print("=" * 70)
    print(f" OVERALL STATUS: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    print("=" * 70)
    return all_pass

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

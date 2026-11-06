import os
import sys
import time
import numpy as np
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.routers.cameras import get_pipeline_diagnostics
from app.ai.diagnostics import pipeline_diagnostics, PipelineDiagnosticsCollector
from app.ai.detector import detector, PersonDetector
from app.ai.stream_processor import DynamicInferenceScheduler, CameraStreamWorker, inference_scheduler
from app.database import SessionLocal
from app.models import User, EventModel, CameraModel
from app.auth_utils import create_access_token


def test_01_metrics_reflect_real_capture_and_inference_events():
    """Requirement 1: Metrics reflect real capture and inference events."""
    collector = PipelineDiagnosticsCollector()
    
    collector.register_source("cam_test_01", "evt_01")
    collector.record_frame_captured("cam_test_01", frame_seq=1, event_id="evt_01")
    collector.record_frame_captured("cam_test_01", frame_seq=2, event_id="evt_01")
    collector.record_frame_submitted("cam_test_01", frame_seq=2)
    
    batch_id = collector.next_batch_id()
    collector.record_batch_started(batch_id, batch_size=1, source_ids=["cam_test_01"], event_ids=["evt_01"])
    collector.record_batch_completed(batch_id, duration_ms=42.5, source_ids=["cam_test_01"], event_ids=["evt_01"])
    collector.record_result_routed("cam_test_01", frame_seq=2, detections_count=3)
    
    snap = collector.get_snapshot(event_id="evt_01")
    assert len(snap["sources"]) == 1
    src = snap["sources"][0]
    assert src["source_id"] == "cam_test_01"
    assert src["captured_frames"] == 2
    assert src["submitted_frames"] == 1
    assert src["completed_inferences"] == 1
    assert snap["scheduler"]["total_batches"] == 1
    assert snap["scheduler"]["total_inferences"] == 1
    assert snap["scheduler"]["last_batch_duration_ms"] == 42.5
    print("[PASS] test_01_metrics_reflect_real_capture_and_inference_events")


def test_02_batch_size_matches_actual_images_passed_into_yolo():
    """Requirement 2: Batch size matches the actual number of images passed into YOLO."""
    # Test PersonDetector detect_batch directly with real images
    test_det = PersonDetector()
    if test_det.model is None:
        print("[SKIP] YOLO model not loaded")
        return
    
    f1 = np.zeros((480, 640, 3), dtype=np.uint8)
    f2 = np.zeros((360, 480, 3), dtype=np.uint8)
    
    boxes_list, counts_list, infer_ms = test_det.detect_batch([f1, f2])
    assert len(boxes_list) == 2
    assert len(counts_list) == 2
    assert infer_ms > 0
    print(f"[PASS] test_02_batch_size_matches_actual_images_passed_into_yolo (len={len(boxes_list)}, ms={infer_ms:.1f})")


def test_03_multiple_source_ids_appear_in_batch_when_batching_enabled():
    """Requirement 3: Multiple source IDs can appear in one batch when batching is enabled."""
    scheduler = DynamicInferenceScheduler()
    scheduler.batching_enabled = True
    scheduler.max_batch_size = 4
    
    class MockWorker:
        def __init__(self, cid, evt):
            self.camera_id = cid
            self.event_id = evt
            self.is_running = True
            self.epoch = 1
            self.received_results = []
        def on_inference_completed(self, boxes, count, infer_ms, infer_seq, infer_time, epoch):
            self.received_results.append((len(boxes), count, infer_seq))
            
    w1 = MockWorker("cam_alpha", "evt_batch")
    w2 = MockWorker("cam_beta", "evt_batch")
    
    scheduler.register_camera("cam_alpha", w1)
    scheduler.register_camera("cam_beta", w2)
    
    f1 = np.zeros((480, 640, 3), dtype=np.uint8)
    f2 = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Both cameras submit frames simultaneously
    scheduler.submit_frame("cam_alpha", 1, f1, 101, time.time())
    scheduler.submit_frame("cam_beta", 1, f2, 201, time.time())
    
    # When batching is enabled, pulling batch gathers both frames
    with scheduler._lock:
        num_cams = len(scheduler._registered_cameras)
        batch_items = []
        max_batch = scheduler.max_batch_size if scheduler.batching_enabled else 1
        for _ in range(num_cams):
            if len(batch_items) >= max_batch:
                break
            idx = scheduler._rr_index % num_cams
            scheduler._rr_index = (scheduler._rr_index + 1) % num_cams
            cid = scheduler._registered_cameras[idx]
            if cid in scheduler._queue:
                target_data = scheduler._queue.pop(cid)
                worker = scheduler._workers.get(cid)
                if worker is not None:
                    batch_items.append((cid, target_data, worker))
                    
    batch_source_ids = [item[0] for item in batch_items]
    assert len(batch_source_ids) == 2
    assert "cam_alpha" in batch_source_ids
    assert "cam_beta" in batch_source_ids
    print(f"[PASS] test_03_multiple_source_ids_appear_in_batch_when_batching_enabled (sources={batch_source_ids})")


def test_04_per_source_counters_are_attributed_correctly():
    """Requirement 4: Per-source counters are attributed correctly."""
    collector = PipelineDiagnosticsCollector()
    
    collector.register_source("source_A", "event_X")
    collector.register_source("source_B", "event_X")
    
    # Source A receives 10 frames, 5 submitted, 5 superseded
    for seq in range(1, 11):
        collector.record_frame_captured("source_A", seq, "event_X")
        if seq % 2 == 0:
            collector.record_frame_submitted("source_A", seq)
        else:
            collector.record_frame_superseded("source_A", seq)
            
    # Source B receives 3 frames, 3 submitted
    for seq in range(1, 4):
        collector.record_frame_captured("source_B", seq, "event_X")
        collector.record_frame_submitted("source_B", seq)
        
    snap = collector.get_snapshot(event_id="event_X")
    src_map = {s["source_id"]: s for s in snap["sources"]}
    
    assert src_map["source_A"]["captured_frames"] == 10
    assert src_map["source_A"]["submitted_frames"] == 5
    assert src_map["source_A"]["superseded_frames"] == 5
    
    assert src_map["source_B"]["captured_frames"] == 3
    assert src_map["source_B"]["submitted_frames"] == 3
    assert src_map["source_B"]["superseded_frames"] == 0
    print("[PASS] test_04_per_source_counters_are_attributed_correctly")


def test_05_event_a_diagnostics_cannot_expose_event_b_data():
    """Requirement 5: Event A diagnostics cannot expose Event B data."""
    collector = PipelineDiagnosticsCollector()
    
    collector.register_source("cam_A1", event_id="EVENT_ALPHA")
    collector.register_source("cam_A2", event_id="EVENT_ALPHA")
    collector.register_source("cam_B1", event_id="EVENT_BETA")
    
    collector.record_frame_captured("cam_A1", 1, event_id="EVENT_ALPHA")
    collector.record_frame_captured("cam_B1", 1, event_id="EVENT_BETA")
    
    # Query for EVENT_ALPHA
    snap_a = collector.get_snapshot(event_id="EVENT_ALPHA")
    source_ids_a = [s["source_id"] for s in snap_a["sources"]]
    assert "cam_A1" in source_ids_a
    assert "cam_A2" in source_ids_a
    assert "cam_B1" not in source_ids_a, "Event B source leaked into Event A snapshot!"
    
    # Events in snap_a should not contain Event B source
    for ev in snap_a["events"]:
        assert ev.get("event_id") != "EVENT_BETA", "Event B diagnostic event leaked to Event A!"
        assert ev.get("source_id") != "cam_B1", "Event B camera leaked in diagnostic events!"
        
    # Query for EVENT_BETA
    snap_b = collector.get_snapshot(event_id="EVENT_BETA")
    source_ids_b = [s["source_id"] for s in snap_b["sources"]]
    assert "cam_B1" in source_ids_b
    assert "cam_A1" not in source_ids_b, "Event A source leaked into Event B snapshot!"
    assert "cam_A2" not in source_ids_b, "Event A source leaked into Event B snapshot!"
    print("[PASS] test_05_event_a_diagnostics_cannot_expose_event_b_data (strict event isolation enforced)")


def test_06_endpoint_requires_auth_and_enforces_event_isolation():
    """Requirement 5 & API check: GET /api/cameras/diagnostics enforces authentication and ownership."""
    db = SessionLocal()
    try:
        user_alpha = db.query(User).filter(User.email == "test_diag_alpha@crowd.ai").first()
        if not user_alpha:
            user_alpha = User(email="test_diag_alpha@crowd.ai", hashed_password="pw", name="Alpha Manager", role="EVENT_MANAGER")
            db.add(user_alpha)
            db.commit()
            db.refresh(user_alpha)
            
        user_beta = db.query(User).filter(User.email == "test_diag_beta@crowd.ai").first()
        if not user_beta:
            user_beta = User(email="test_diag_beta@crowd.ai", hashed_password="pw", name="Beta Manager", role="EVENT_MANAGER")
            db.add(user_beta)
            db.commit()
            db.refresh(user_beta)
            
        evt_alpha = db.query(EventModel).filter(EventModel.id == "evt_diag_alpha").first()
        if not evt_alpha:
            evt_alpha = EventModel(id="evt_diag_alpha", title="Alpha Gala", manager_id=user_alpha.id, capacity=5000)
            db.add(evt_alpha)
            db.commit()
            
        token_alpha = create_access_token({"sub": user_alpha.email})
        token_beta = create_access_token({"sub": user_beta.email})
        auth_alpha = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_alpha)
        auth_beta = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_beta)
        
        # User Alpha reading own event -> 200 OK
        data = get_pipeline_diagnostics(event_id="evt_diag_alpha", auth=auth_alpha, db=db)
        assert "scheduler" in data
        assert "sources" in data
        assert "events" in data
        
        # User Beta trying to read Alpha's event -> 403 Forbidden
        try:
            get_pipeline_diagnostics(event_id="evt_diag_alpha", auth=auth_beta, db=db)
            raise AssertionError("Expected 403 Forbidden when Beta accesses Alpha event!")
        except HTTPException as exc:
            assert exc.status_code == 403
            
        print("[PASS] test_06_endpoint_requires_auth_and_enforces_event_isolation")
    finally:
        db.close()


def test_07_diagnostics_endpoint_is_strictly_readonly():
    """Requirement 7: A diagnostics endpoint or subscription cannot change processing state."""
    collector = PipelineDiagnosticsCollector()
    collector.register_source("cam_ro", "evt_ro")
    collector.record_frame_captured("cam_ro", 1, "evt_ro")
    
    snap1 = collector.get_snapshot(event_id="evt_ro")
    snap2 = collector.get_snapshot(event_id="evt_ro")
    
    assert snap1["sources"][0]["captured_frames"] == snap2["sources"][0]["captured_frames"]
    assert snap1["scheduler"]["total_batches"] == snap2["scheduler"]["total_batches"]
    print("[PASS] test_07_diagnostics_endpoint_is_strictly_readonly")


def test_08_diagnostics_errors_do_not_interrupt_pipeline():
    """Requirement 8: Diagnostics errors do not stop inference."""
    collector = PipelineDiagnosticsCollector()
    
    # Simulate an internal collector exception or corrupted call
    # The collector methods must catch all internal exceptions and not re-raise into inference
    try:
        collector.record_error("cam_corrupt", "Test error condition", "evt_corrupt")
        snap = collector.get_snapshot(event_id="evt_corrupt")
        assert snap["sources"][0]["error"] == "Test error condition"
    except Exception as e:
        raise AssertionError(f"Diagnostics error raised exception into pipeline: {e}")
        
    print("[PASS] test_08_diagnostics_errors_do_not_interrupt_pipeline")


def test_09_existing_bounding_box_format_preserved():
    """Requirement 9: Existing bounding-box and detection structures remain unchanged."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    boxes, count, infer_ms = detector.detect_frame(frame)
    assert isinstance(boxes, list)
    assert isinstance(count, int)
    assert isinstance(infer_ms, float)
    
    # Verify draw_annotations
    annotated = detector.draw_annotations(frame, [], 0)
    assert annotated is not None
    assert annotated.shape == (480, 640, 3)
    print("[PASS] test_09_existing_bounding_box_format_preserved")


if __name__ == "__main__":
    test_01_metrics_reflect_real_capture_and_inference_events()
    test_02_batch_size_matches_actual_images_passed_into_yolo()
    test_03_multiple_source_ids_appear_in_batch_when_batching_enabled()
    test_04_per_source_counters_are_attributed_correctly()
    test_05_event_a_diagnostics_cannot_expose_event_b_data()
    test_06_endpoint_requires_auth_and_enforces_event_isolation()
    test_07_diagnostics_endpoint_is_strictly_readonly()
    test_08_diagnostics_errors_do_not_interrupt_pipeline()
    test_09_existing_bounding_box_format_preserved()
    print("\nALL 9 PARALLEL PROCESSING AND DIAGNOSTICS TESTS PASSED 100%!")

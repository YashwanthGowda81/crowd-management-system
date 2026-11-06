"""
VERIFICATION SUITE: 7-STEP EXACT REGRESSION SEQUENCE & 30-FRAME RUNTIME TRACE
Directly verifies the prompt's 7-step sequence and logs 30 consecutive displayed frames
on actual surveillance video (cam-vid-1793089633407.mp4).
"""

import os
import sys
import time
import math
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.ai.detector import TemporalPersonTracker, detector
from app.ai.stream_processor import CameraStreamWorker

def test_seven_step_sequence():
    print("=" * 80)
    print("TESTING EXACT 7-STEP OBSERVED REGRESSION SEQUENCE")
    print("=" * 80)
    
    tracker = TemporalPersonTracker(max_prediction_frames=25)
    dummy_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    
    # 1. A person is detected and assigned a track ID.
    det_1 = [100, 100, 150, 220, 0.92, None]
    tracker.update_detections([det_1], det_seq=1, det_time=1.00)
    boxes_1 = tracker.track_frame(dummy_frame, curr_seq=1, curr_time=1.00)
    assert len(boxes_1) == 1, f"Expected 1 box at frame 1, got {len(boxes_1)}"
    track_id_1 = boxes_1[0][5]
    state_1 = boxes_1[0][8]
    print(f"  Step 1: Detected person assigned Track ID={track_id_1}, state={state_1}, box={boxes_1[0][:4]}")
    assert state_1 == "confirmed"
    
    # 2. Next displayed frame arrives before the next YOLO result.
    # 3. The tracker predicts the person's new position.
    boxes_2 = tracker.track_frame(dummy_frame, curr_seq=2, curr_time=1.033)
    assert len(boxes_2) == 1, f"Expected 1 box at frame 2, got {len(boxes_2)}"
    assert boxes_2[0][5] == track_id_1, f"Track ID changed at frame 2"
    print(f"  Step 2 & 3: Frame 2 displayed before YOLO -> predicted box={boxes_2[0][:4]}, ID={boxes_2[0][5]}, age={boxes_2[0][7]}")
    
    # 4. A subsequent YOLO inference temporarily returns no detection (temporary miss).
    tracker.update_detections([], det_seq=3, det_time=1.066)
    assert track_id_1 in tracker.tracks, "Track was prematurely erased by empty YOLO result!"
    assert tracker.tracks[track_id_1].state == "lost", "Track should transition to 'lost', not 'removed'"
    print(f"  Step 4: YOLO returned [] (miss) -> Track {track_id_1} transitioned to state='lost', misses={tracker.tracks[track_id_1].misses}")
    
    # 5. The same track remains visible and moves using valid prediction across frames 3, 4, 5.
    for seq in [3, 4, 5]:
        t = 1.00 + seq * 0.033
        boxes = tracker.track_frame(dummy_frame, curr_seq=seq, curr_time=t)
        assert len(boxes) == 1, f"Box disappeared during temporary miss at frame {seq}!"
        assert boxes[0][5] == track_id_1, f"Track ID changed at frame {seq}!"
        assert boxes[0][8] == "lost", f"Box should reflect 'lost' (tracking/predicted) state at frame {seq}"
        print(f"  Step 5: Frame {seq} displayed during YOLO miss -> Box rendered! ID={boxes[0][5]}, state={boxes[0][8]}, age={boxes[0][7]}")
        
    # 6. A later YOLO result matches the person and updates the same track.
    det_6 = [108, 102, 158, 222, 0.89, None] # person moved slightly
    tracker.update_detections([det_6], det_seq=6, det_time=1.20)
    boxes_6 = tracker.track_frame(dummy_frame, curr_seq=6, curr_time=1.20)
    assert len(boxes_6) == 1, f"Expected 1 box at frame 6, got {len(boxes_6)}"
    assert boxes_6[0][5] == track_id_1, f"Track ID changed after re-detection! Expected {track_id_1}, got {boxes_6[0][5]}"
    assert boxes_6[0][8] == "confirmed", f"Track state should be restored to 'confirmed'"
    print(f"  Step 6: YOLO re-detected person -> Same Track ID={boxes_6[0][5]} re-confirmed! state={boxes_6[0][8]}")
    
    # 7. The box disappears after the track is genuinely lost and expired (e.g. 26 frames without detection).
    for seq in range(7, 35):
        t = 1.20 + (seq - 6) * 0.033
        tracker.track_frame(dummy_frame, curr_seq=seq, curr_time=t)
    
    final_boxes = tracker.track_frame(dummy_frame, curr_seq=35, curr_time=2.20)
    assert len(final_boxes) == 0, f"Box did not expire after 28 frames without detection! Got {len(final_boxes)}"
    print(f"  Step 7: Track genuinely lost for 28 frames (> max_prediction_frames=25) -> Box expired and removed cleanly (boxes={len(final_boxes)})")
    print("=" * 80)
    print("7-STEP REGRESSION SEQUENCE VERIFICATION: ALL 7 STEPS PASSED PERFECTLY!")
    print("=" * 80)

def trace_real_surveillance_video():
    video_path = os.path.join(BASE_DIR, "app", "uploads", "videos", "cam-vid-1793089633407.mp4")
    print(f"\nTRACE OF 25 CONSECUTIVE DISPLAYED FRAMES ON REAL CCTV: {os.path.basename(video_path)}")
    print("-" * 110)
    print(f"{'Disp Seq':<10} | {'Timestamp':<14} | {'YOLO Seq':<10} | {'Raw Dets':<10} | {'Active Tracks':<15} | {'Lost Tracks':<12} | {'Rendered Boxes (ID: [x1,y1,x2,y2])'}")
    print("-" * 110)
    
    worker = CameraStreamWorker(
        camera_id="cam-trace-eval",
        source=video_path,
        source_type="video",
        capacity=100,
        event_id="evt-trace"
    )
    worker.start()
    
    # Allow background threads to initialize and warm up YOLO
    time.sleep(1.0)
    
    trace_rows = []
    start_seq = worker.frame_seq
    
    # Collect 25 consecutive playback frames
    last_seq = -1
    consecutive_samples = 0
    t_start = time.perf_counter()
    
    while consecutive_samples < 25:
        curr_seq = worker.frame_seq
        if curr_seq != last_seq and curr_seq > start_seq:
            last_seq = curr_seq
            now_t = worker.last_observation_timestamp
            yolo_seq = worker.last_detection_frame_seq
            raw_dets_cnt = len(worker.latest_boxes)
            
            with worker.state_lock:
                tracks = list(worker.active_tracks)
                
            active_ids = [t[5] for t in tracks if len(t) > 8 and t[8] == "confirmed"]
            lost_ids = [t[5] for t in tracks if len(t) > 8 and t[8] == "lost"]
            rendered_summary = "; ".join([f"#{t[5]} ({t[8][0].upper()}): [{t[0]},{t[1]},{t[2]},{t[3]}]" for t in tracks[:3]])
            if len(tracks) > 3:
                rendered_summary += f" ... +{len(tracks)-3} more"
                
            trace_rows.append({
                "disp_seq": curr_seq,
                "timestamp": f"{now_t:.3f}",
                "yolo_seq": yolo_seq,
                "raw_dets": raw_dets_cnt,
                "active_tracks": str(active_ids[:5]),
                "lost_tracks": str(lost_ids[:5]),
                "summary": rendered_summary,
                "total_rendered": len(tracks)
            })
            consecutive_samples += 1
        time.sleep(0.01)
        
    worker.stop()
    
    for r in trace_rows:
        print(f"{r['disp_seq']:<10} | {r['timestamp']:<14} | {r['yolo_seq']:<10} | {r['raw_dets']:<10} | {r['active_tracks']:<15} | {r['lost_tracks']:<12} | {r['summary']}")
    print("-" * 110)
    print(f"Total Frames Traced: {len(trace_rows)}")
    print(f"Playback FPS: {worker.playback_fps:.1f} FPS | YOLO Inference FPS: {worker.processing_fps:.1f} FPS")
    print("=" * 110)

if __name__ == "__main__":
    test_seven_step_sequence()
    trace_real_surveillance_video()

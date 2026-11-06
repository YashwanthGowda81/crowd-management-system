"""
Diagnostic test: Run two CameraStreamWorkers concurrently on two real videos with different resolutions.
Inspect for:
1. Cross-camera bounding box bleeding / coordinate mixing
2. Thread safety of detector.detect_frame
3. Frame buffer isolation between workers
"""
import os
import sys
import time
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.ai.stream_processor import CameraStreamWorker, stream_manager
from app.ai.detector import detector

def run_concurrency_audit():
    v1 = os.path.join(BASE_DIR, "app", "uploads", "videos", "cam-vid-1786603016313.mp4") # 640x360
    v2 = os.path.join(BASE_DIR, "app", "uploads", "videos", "cam-vid-1793089633407.mp4") # 1280x720
    
    print(f"[TEST] Video 1: {os.path.basename(v1)} (expected 640x360)")
    print(f"[TEST] Video 2: {os.path.basename(v2)} (expected 1280x720)")
    
    w1 = CameraStreamWorker("cam-test-1", v1, "video", 100, "evt-audit")
    w2 = CameraStreamWorker("cam-test-2", v2, "video", 100, "evt-audit")
    
    w1.start()
    w2.start()
    
    cross_contamination_detected = False
    samples = 0
    start_time = time.time()
    
    while time.time() - start_time < 5.0:
        time.sleep(0.1)
        samples += 1
        
        # Check Worker 1 frame and boxes
        f1 = w1.last_annotated_frame
        f2 = w2.last_annotated_frame
        
        if f1 is not None and f2 is not None:
            h1, width1 = f1.shape[:2]
            h2, width2 = f2.shape[:2]
            
            with w1.state_lock:
                tracks1 = list(w1.active_tracks)
            with w2.state_lock:
                tracks2 = list(w2.active_tracks)
                
            # If any box in tracks1 has coordinates scaled for 1280x720 (e.g. x > 640 or y > 360)
            for b in tracks1:
                if b[2] > 640 or b[3] > 360:
                    print(f"[ERROR] Worker 1 (640x360) has out-of-bounds box: {b} from 1280x720 video!")
                    cross_contamination_detected = True
                    
            if samples % 10 == 0:
                print(f"[SAMPLE {samples}] W1 ({width1}x{h1}): {len(tracks1)} tracks | W2 ({width2}x{h2}): {len(tracks2)} tracks")
                if tracks1:
                    print(f"  W1 box sample: ID={tracks1[0][5]} {tracks1[0][:4]}")
                if tracks2:
                    print(f"  W2 box sample: ID={tracks2[0][5]} {tracks2[0][:4]}")

    w1.stop()
    w2.stop()
    
    print("\n[RESULT]")
    if cross_contamination_detected:
        print("CRITICAL DEFECT DETECTED: Cross-camera bounding box contamination!")
    else:
        print("Worker internal tracks did not have out-of-bound coordinates.")

if __name__ == "__main__":
    run_concurrency_audit()

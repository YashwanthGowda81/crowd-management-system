import os
import sys
import time
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.database import SessionLocal
from app.models import CameraModel
from app.ai.stream_processor import stream_manager
from app.ai.ingestion_manager import ingestion_coordinator

# Enable stream manager
stream_manager._allow_non_owner = True

db = SessionLocal()
cams = db.query(CameraModel).filter(CameraModel.status == "online").all()
print(f"Loaded {len(cams)} online cameras from DB:")

workers = []
for c in cams:
    print(f"Creating worker for {c.id} ({c.name}) source={c.rtsp_url}")
    w = stream_manager.get_or_create_worker(c.id, c.rtsp_url, c.source_type, c.capacity, c.event_id)
    workers.append((c, w))

print("All 4 workers started. Monitoring for 10 seconds...")
start_time = time.time()
while time.time() - start_time < 10.0:
    time.sleep(1.0)
    print(f"--- Second {int(time.time() - start_time)} ---")
    for c, w in workers:
        f = w.last_annotated_frame
        shape_str = f.shape[:2] if f is not None else "None"
        with w.state_lock:
            tracks = list(w.active_tracks)
            boxes = list(w.latest_boxes)
        print(f"[{c.id}] {c.name}: shape={shape_str} | yolo={w.yolo_detection_count} (boxes={len(boxes)}) | tracked={len(tracks)} | pFPS={w.playback_fps} | iFPS={w.processing_fps}")
        if tracks:
            # Check coordinate bounds
            w_max = f.shape[1] if f is not None else 1920
            h_max = f.shape[0] if f is not None else 1080
            bad_boxes = [b for b in tracks if b[0] < 0 or b[1] < 0 or b[2] > w_max or b[3] > h_max]
            if bad_boxes:
                print(f"  !!! ERROR: OUT OF BOUNDS BOXES IN {c.id}: {bad_boxes}")
            else:
                sample = tracks[0]
                print(f"  Sample track: ID={sample[5]} box={sample[:4]} state={sample[8] if len(sample)>8 else 'N/A'}")

for c, w in workers:
    stream_manager.stop_worker(c.id)

db.close()
print("Test completed.")

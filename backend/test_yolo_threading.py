import threading
import time
import cv2
import numpy as np
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
lock = threading.RLock()

# Create two distinct synthetic test images:
# Image 1: 640x360 black with a white rectangle at (100, 100, 200, 300)
# Image 2: 1280x720 black with a white rectangle at (900, 500, 1100, 700)
img1 = cv2.imread("app/uploads/videos/cam-vid-1786603016313.mp4") # Wait, read real frames
cap1 = cv2.VideoCapture("app/uploads/videos/cam-vid-1786603016313.mp4")
ret1, frame1 = cap1.read()
cap1.release()

cap2 = cv2.VideoCapture("app/uploads/videos/cam-vid-1793089633407.mp4")
ret2, frame2 = cap2.read()
cap2.release()

print(f"Frame 1 shape: {frame1.shape}") # (360, 640, 3)
print(f"Frame 2 shape: {frame2.shape}") # (720, 1280, 3)

results_thread1 = []
results_thread2 = []

def worker1():
    for _ in range(20):
        with lock:
            res = model.predict(frame1, conf=0.20, classes=[0], imgsz=480, verbose=False)
            boxes = []
            for r in res:
                for b in r.boxes:
                    boxes.append(b.xyxy[0].cpu().numpy().tolist())
            results_thread1.append(boxes)
        time.sleep(0.01)

def worker2():
    for _ in range(20):
        with lock:
            res = model.predict(frame2, conf=0.20, classes=[0], imgsz=480, verbose=False)
            boxes = []
            for r in res:
                for b in r.boxes:
                    boxes.append(b.xyxy[0].cpu().numpy().tolist())
            results_thread2.append(boxes)
        time.sleep(0.01)

t1 = threading.Thread(target=worker1)
t2 = threading.Thread(target=worker2)
t1.start()
t2.start()
t1.join()
t2.join()

print(f"Worker 1 results count: {len(results_thread1)}")
print(f"Worker 2 results count: {len(results_thread2)}")

# Check if any Worker 1 box exceeds (640, 360)
w1_leaks = [b for boxes in results_thread1 for b in boxes if b[2] > 640 or b[3] > 360]
print(f"Worker 1 out-of-bounds boxes (> 640x360): {len(w1_leaks)}")

# Check if any Worker 2 box has Worker 1 coordinates
print(f"Worker 1 average boxes per frame: {np.mean([len(b) for b in results_thread1])}")
print(f"Worker 2 average boxes per frame: {np.mean([len(b) for b in results_thread2])}")

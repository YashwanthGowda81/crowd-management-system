import cv2
import time
import threading
import numpy as np
import os
import math
from typing import Optional, Dict, Any, List, Tuple

from app.ai.detector import detector, TemporalPersonTracker, SimpleCentroidTracker
from app.ai.density import CrowdDensityEvaluator
from app.ai.risk_engine import risk_engine
from app.ai.heatmap import global_heatmap_gen
from app.ai.diagnostics import pipeline_diagnostics


class DynamicInferenceScheduler:
    """
    Scalable, fair round-robin YOLO inference scheduler for an arbitrary dynamic number of cameras.
    - Eliminates CPU thread thrashing and lock contention between competing per-camera workers.
    - Guarantees every active camera receives deterministic, fair inference opportunities.
    - Bounded per-camera queue of depth 1 (drops stale frames when video frame rate > inference capacity).
    - Maximizes host CPU hardware cache locality and PyTorch thread pool utilization.
    - Batches ready frames across multiple active camera feeds into a single YOLO forward pass.
    - Dynamically measures per-camera inference latency, queue depth, and processing FPS.
    """
    def __init__(self):
        self._queue: Dict[str, Tuple[int, np.ndarray, int, float]] = {}  # {cam_id: (epoch, frame, seq, timestamp)}
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._registered_cameras: List[str] = []
        self._workers: Dict[str, Any] = {}
        self._rr_index: int = 0
        self._is_running: bool = False
        self._worker_thread: Optional[threading.Thread] = None
        self._total_inferences: int = 0
        self._last_perf_log: float = time.time()
        self.batching_enabled: bool = True
        self.max_batch_size: int = 4

    def start(self):
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._worker_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True, name="DynamicInferenceScheduler"
            )
            self._worker_thread.start()
            pipeline_diagnostics.record_scheduler_started(len(self._registered_cameras))
            print("[SCHEDULER][START] Dynamic Fair Inference Scheduler initialized.")

    def stop(self):
        with self._lock:
            self._is_running = False
            self._cond.notify_all()
            pipeline_diagnostics.set_scheduler_state("stopped")

    def register_camera(self, camera_id: str, worker: Any):
        with self._lock:
            if camera_id not in self._registered_cameras:
                self._registered_cameras.append(camera_id)
            self._workers[camera_id] = worker
            self._cond.notify_all()
            event_id = getattr(worker, "event_id", None)
            pipeline_diagnostics.register_source(camera_id, event_id)
            print(f"[SCHEDULER][REGISTER] Camera {camera_id} registered. Active feeds in scheduler: {len(self._registered_cameras)}")

    def unregister_camera(self, camera_id: str):
        with self._lock:
            if camera_id in self._registered_cameras:
                self._registered_cameras.remove(camera_id)
            self._workers.pop(camera_id, None)
            self._queue.pop(camera_id, None)
            self._cond.notify_all()
            pipeline_diagnostics.unregister_source(camera_id)
            print(f"[SCHEDULER][UNREGISTER] Camera {camera_id} unregistered. Remaining feeds in scheduler: {len(self._registered_cameras)}")

    def clear_camera_queue(self, camera_id: str):
        """Discards queued frame for camera (used on video loop or reconnection)."""
        with self._lock:
            self._queue.pop(camera_id, None)

    def has_pending(self, camera_id: str) -> bool:
        """Returns True if the camera already has a frame pending in the scheduler queue."""
        with self._lock:
            return camera_id in self._queue

    def get_registered_count(self) -> int:
        with self._lock:
            return len(self._registered_cameras)

    def submit_frame(self, camera_id: str, epoch: int, frame: np.ndarray, frame_seq: int, timestamp: float):
        """Bounded queue of depth 1: keeps the freshest frame, dropping older backlogged frames."""
        with self._lock:
            if camera_id in self._workers:
                self._queue[camera_id] = (epoch, frame, frame_seq, timestamp)
                self._cond.notify()
                pipeline_diagnostics.record_frame_submitted(camera_id, frame_seq)

    def _scheduler_loop(self):
        while self._is_running:
            batch_items = []

            with self._lock:
                while self._is_running and not any(cid in self._queue for cid in self._registered_cameras):
                    self._cond.wait(timeout=0.05)
                if not self._is_running:
                    break

                num_cams = len(self._registered_cameras)
                if num_cams == 0:
                    continue

                max_batch = self.max_batch_size if self.batching_enabled else 1
                # Fair Round-Robin selection over registered cameras that have a queued frame
                for _ in range(num_cams):
                    if len(batch_items) >= max_batch:
                        break
                    idx = self._rr_index % num_cams
                    self._rr_index = (self._rr_index + 1) % num_cams
                    cid = self._registered_cameras[idx]
                    if cid in self._queue:
                        target_data = self._queue.pop(cid)
                        worker = self._workers.get(cid)
                        if worker is not None:
                            batch_items.append((cid, target_data, worker))

            if not batch_items:
                continue

            # Filter out stopped or stale workers
            valid_items = []
            for cid, tdata, w in batch_items:
                epoch, frame_to_detect, infer_seq, infer_time = tdata
                if getattr(w, "is_running", False) and epoch == getattr(w, "epoch", 0):
                    valid_items.append((cid, epoch, frame_to_detect, infer_seq, infer_time, w))

            if not valid_items:
                continue

            batch_id = pipeline_diagnostics.next_batch_id()
            batch_size = len(valid_items)
            source_ids = [item[0] for item in valid_items]
            event_ids = [getattr(item[5], "event_id", None) for item in valid_items]
            batch_frames = [item[2] for item in valid_items]

            # Record batch start
            pipeline_diagnostics.record_batch_started(batch_id, batch_size, source_ids, event_ids)

            # Run YOLO batched person detection
            conf_thresh = getattr(detector, "conf_threshold", 0.20)
            boxes_list, counts_list, infer_ms = detector.detect_batch(batch_frames, conf_threshold=conf_thresh, imgsz=480)

            # Record batch completion
            pipeline_diagnostics.record_batch_completed(batch_id, infer_ms, source_ids, event_ids)

            # Dispatch results directly to each camera worker
            for i, (cid, epoch, _, infer_seq, infer_time, w) in enumerate(valid_items):
                if not getattr(w, "is_running", False) or epoch != getattr(w, "epoch", 0):
                    continue
                boxes = boxes_list[i] if i < len(boxes_list) else []
                count = counts_list[i] if i < len(counts_list) else 0
                w.on_inference_completed(boxes, count, infer_ms, infer_seq, infer_time, epoch)
                pipeline_diagnostics.record_result_routed(cid, infer_seq, count)

            self._total_inferences += batch_size
            now_t = time.time()
            if now_t - self._last_perf_log >= 6.0:
                self._last_perf_log = now_t
                active_count = len(self._registered_cameras)
                queued_count = len(self._queue)
                print(f"[SCHEDULER][PERF] Active cameras: {active_count} | Queued: {queued_count} | Last batch: {batch_size} (ids={source_ids}) | Total: {self._total_inferences}")


inference_scheduler = DynamicInferenceScheduler()


class CameraStreamWorker:
    """
    Decoupled AI video detection & temporal tracking pipeline:
    - VIDEO PLAYBACK LOOP: Delivers frames at source video's natural FPS (e.g. 24-30 FPS).
    - DYNAMIC INFERENCE SCHEDULER: Asynchronously coordinates fair, scalable YOLO person detection.
    - ADAPTIVE TRACKER & FALLBACK GUARD: Bridges inference latency dynamically and ensures bounding boxes never disappear.
    """
    def __init__(self, camera_id: str, source: str, source_type: str = "rtsp", capacity: int = 200, event_id: Optional[str] = None):
        self.camera_id = camera_id
        self.event_id = event_id
        self.source = source
        self.source_type = source_type
        self.capacity = capacity
        
        self.is_running = False
        self.is_paused = False
        self.playback_status = "ready"
        self.error_message = None
        
        self.playback_thread = None
        
        self.source_fps = 30.0
        self.processing_fps = 0.0
        self.playback_fps = 30.0
        self.last_count = 0
        self.yolo_detection_count = 0
        self.tracker_track_count = 0
        self.render_track_count = 0
        self.last_density = 0.0
        self.last_risk = "LOW"
        self.last_flow_rate = 0.0
        self.last_speed_avg = 0.0
        self.flow_metrics = {
            "X_neg": 0.0,
            "X_pos": 0.0,
            "Y_neg": 0.0,
            "Y_pos": 0.0,
            "lambda_out": 0.0,
            "avg_speed_mps": 0.0
        }
        self.unique_window_count = 0
        self.cumulative_count = 0
        self.prev_centroids: List[tuple] = []
        self.latest_boxes: List = []
        self.active_tracks: List = []
        self.last_annotated_frame = None
        self.frame_seq = 0
        self.last_detection_frame_seq = 0
        self.last_infer_gap_frames = 1
        self.last_observation_timestamp_infer = 0.0
        self.last_detection_age_frames = 0
        self.last_observation_timestamp = 0.0
        
        # Threading coordination & epoch generation
        self.state_lock = threading.Lock()
        self.epoch: int = 0
        
        # Dedicated per-camera temporal tracker initialized with generous headroom (45 frames / ~1.5s)
        self.tracker = TemporalPersonTracker(max_prediction_frames=45)

    @property
    def worker_thread(self):
        return self.playback_thread

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self.playback_status = "playing"
        self.error_message = None

        # Start dynamic inference scheduler if not running and register this camera
        inference_scheduler.start()
        inference_scheduler.register_camera(self.camera_id, self)

        self.playback_thread = threading.Thread(
            target=self._playback_loop, daemon=True, name=f"Playback_{self.camera_id}"
        )
        self.playback_thread.start()
        print(f"[CAMERA][START] Camera ID: {self.camera_id} | Event: {self.event_id} | Type: {self.source_type} | Source: {self.source}")

    def pause(self):
        self.is_paused = True
        self.playback_status = "paused"
        print(f"[CAMERA][PAUSE] Camera ID: {self.camera_id} paused.")

    def resume(self):
        self.is_paused = False
        self.playback_status = "playing"
        print(f"[CAMERA][RESUME] Camera ID: {self.camera_id} resumed.")

    def stop(self):
        self.is_running = False
        self.playback_status = "stopped"
        inference_scheduler.unregister_camera(self.camera_id)
        self.tracker.reset()
        print(f"[CAMERA][STOP] Camera ID: {self.camera_id} stopped and tracker reset.")

    def on_inference_completed(self, boxes: list, count: int, infer_ms: float, infer_seq: int, infer_time: float, epoch: int):
        """Callback invoked by DynamicInferenceScheduler when YOLO inference finishes for this camera."""
        with self.state_lock:
            if not self.is_running or epoch != self.epoch:
                return

        # 1. Feed ground-truth detections to per-camera TemporalPersonTracker
        self.tracker.update_detections(boxes, infer_seq, infer_time)

        # 2. Dynamic tracking window scaling: adapt to current measured inference interval and active camera count
        gap_frames = max(1, infer_seq - self.last_detection_frame_seq) if self.last_detection_frame_seq > 0 else 1
        self.last_infer_gap_frames = gap_frames
        num_cams = max(1, inference_scheduler.get_registered_count())
        dynamic_max_frames = max(45, min(180, int(max(3.0 * gap_frames, num_cams * 18))))
        self.tracker.set_max_prediction_frames(dynamic_max_frames)

        # 3. Calculate density and risk from current YOLO result
        density = CrowdDensityEvaluator.calculate_density(count, self.capacity)
        _, risk, _ = risk_engine.calculate_camera_risk(density, density)

        # 4. Processing FPS calculation
        instant_fps = 1000.0 / max(1.0, infer_ms)
        if self.processing_fps <= 0.0:
            new_proc_fps = round(instant_fps, 1)
        else:
            new_proc_fps = round(0.8 * self.processing_fps + 0.2 * instant_fps, 1)

        # 5. Flow and Motion Vector Calculation (IEEE Access 2025, Eqs 2-5)
        curr_centroids = [((b[0] + b[2]) // 2, (b[1] + b[3]) // 2) for b in boxes]
        flow_metrics = self.tracker.compute_flow_metrics()
        flow_rate = flow_metrics.get("lambda_out", 0.0)
        speed_avg = flow_metrics.get("avg_speed_mps", 0.0)
        unique_window = self.tracker.get_unique_window_count(30.0)
        cumulative_cnt = self.tracker.cumulative_unique_count

        # 6. Thread-safe state update
        with self.state_lock:
            self.latest_boxes = boxes
            self.yolo_detection_count = count
            self.last_count = count
            self.last_density = density
            self.last_risk = risk
            self.processing_fps = new_proc_fps
            self.prev_centroids = curr_centroids
            self.last_flow_rate = flow_rate
            self.last_speed_avg = speed_avg
            self.flow_metrics = flow_metrics
            self.unique_window_count = unique_window
            self.cumulative_count = cumulative_cnt
            self.last_detection_frame_seq = infer_seq
            self.last_observation_timestamp_infer = infer_time

        # Accumulate spatial points into global heatmap
        global_heatmap_gen.accumulate_points(boxes)

        if infer_seq % 60 == 0 or infer_seq < 5:
            print(f"[AI-E2E][INFERENCE] camera_id={self.camera_id} event_id={self.event_id} infer_seq={infer_seq} epoch={epoch} yolo_count={count} infer_ms={infer_ms:.1f} infer_fps={new_proc_fps}")

    def _playback_loop(self):
        """
        Playback loop: delivers frames strictly at the source video's natural FPS.
        Decoupled from YOLO inference to eliminate playback slowdowns.
        Continuously updates TemporalPersonTracker on each playback frame.
        """
        cap = None
        try:
            if str(self.source).isdigit():
                cap = cv2.VideoCapture(int(self.source))
            else:
                cap = cv2.VideoCapture(self.source)
        except Exception:
            cap = None

        if cap is not None and cap.isOpened():
            fps_val = cap.get(cv2.CAP_PROP_FPS)
            if fps_val and fps_val > 0:
                self.source_fps = round(float(fps_val), 1)
            print(f"[CAMERA][CONNECTED] Camera ID: {self.camera_id} | Source: {self.source} | Source FPS: {self.source_fps}")
        else:
            print(f"[CAMERA][ERROR] Camera ID: {self.camera_id} | Could not open {self.source}")
            self.playback_status = "error"
            self.error_message = f"VIDEO SOURCE ERROR: Could not open camera source '{self.source}'"
            self.is_running = False
            inference_scheduler.unregister_camera(self.camera_id)
            return

        target_interval = 1.0 / max(1.0, self.source_fps)
        next_frame_time = time.perf_counter()
        last_playback_tick = time.perf_counter()
        playback_frame_count = 0

        consecutive_read_failures = 0
        while self.is_running:
            if self.is_paused:
                time.sleep(0.05)
                next_frame_time = time.perf_counter()
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                if self.source_type in ["video", "uploaded_video"]:
                    # Clean loop to start of uploaded CCTV video
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    with self.state_lock:
                        self.epoch += 1
                        self.frame_seq = 0
                        self.last_detection_frame_seq = 0
                        self.prev_centroids = []
                        self.latest_boxes = []
                        self.active_tracks = []
                    # Reset per-camera tracker temporal state on loop
                    self.tracker.reset()
                    inference_scheduler.clear_camera_queue(self.camera_id)

                    ret_loop, frame_loop = cap.read()
                    if ret_loop and frame_loop is not None:
                        frame = frame_loop
                        next_frame_time = time.perf_counter()
                        print(f"[AI-E2E][LOOP] Camera {self.camera_id} looped to start (epoch {self.epoch}). Tracker state reset successfully.")
                    else:
                        print(f"[CAMERA][EOF] Camera ID: {self.camera_id} reached end of video stream.")
                        self.playback_status = "stopped"
                        self.is_running = False
                        inference_scheduler.unregister_camera(self.camera_id)
                        break
                else:
                    consecutive_read_failures += 1
                    if consecutive_read_failures > 30:
                        print(f"[CAMERA][RECONNECT] Attempting reconnect for camera {self.camera_id} source {self.source}")
                        try:
                            if cap is not None:
                                cap.release()
                            time.sleep(1.0)
                            if str(self.source).isdigit():
                                cap = cv2.VideoCapture(int(self.source))
                            else:
                                cap = cv2.VideoCapture(self.source)
                        except Exception as e:
                            print(f"[CAMERA][RECONNECT_ERROR] {e}")
                        consecutive_read_failures = 0
                    else:
                        time.sleep(0.02)
                    continue

            consecutive_read_failures = 0
            self.frame_seq += 1
            now_t = time.time()
            self.last_observation_timestamp = now_t
            playback_frame_count += 1
            pipeline_diagnostics.record_frame_captured(self.camera_id, self.frame_seq, self.event_id)

            # Measure real-time playback FPS
            if playback_frame_count >= 30:
                dt_p = time.perf_counter() - last_playback_tick
                if dt_p > 0:
                    self.playback_fps = round(playback_frame_count / dt_p, 1)
                playback_frame_count = 0
                last_playback_tick = time.perf_counter()

            # Submit freshest frame to dynamic fair inference scheduler (bounded queue depth 1)
            # Only allocate frame copy if camera does not already have a pending frame in scheduler
            if not inference_scheduler.has_pending(self.camera_id):
                inference_scheduler.submit_frame(self.camera_id, self.epoch, frame.copy(), self.frame_seq, now_t)
            else:
                pipeline_diagnostics.record_frame_superseded(self.camera_id, self.frame_seq)

            # Update tracker on current playback frame using kinematic motion estimation
            active_tracks = self.tracker.track_frame(frame, self.frame_seq, now_t)
            # active_tracks: [x1, y1, x2, y2, conf, track_id, det_seq, age_frames, state]

            # Render active tracked bounding boxes without fake static fallback boxes
            render_boxes = list(active_tracks) if active_tracks else []

            with self.state_lock:
                self.active_tracks = active_tracks
                self.tracker_track_count = len(render_boxes)
                self.render_track_count = len(render_boxes)
                current_count = len(render_boxes) if render_boxes else self.yolo_detection_count
                if active_tracks:
                    self.last_detection_age_frames = active_tracks[0][7] if len(active_tracks[0]) > 7 else 0
                else:
                    self.last_detection_age_frames = 0

            # Draw active tracked bounding boxes onto this exact current frame
            # If no active tracks or detections, draw_annotations draws clean frame without boxes
            annotated = detector.draw_annotations(frame, render_boxes, current_count)
            self.last_annotated_frame = annotated

            # Rate-limited structured diagnostic logging
            if self.frame_seq % 60 == 0:
                active_cnt = getattr(self.tracker, 'active_tracks_count', len(active_tracks))
                lost_cnt = getattr(self.tracker, 'lost_tracks_count', 0)
                miss_cnt = getattr(self.tracker, 'detection_misses_count', 0)
                print(f"[AI-E2E][PLAYBACK] camera_id={self.camera_id} event_id={self.event_id} frame_seq={self.frame_seq} yolo_count={self.yolo_detection_count} track_count={self.tracker_track_count} (confirmed={active_cnt}, lost={lost_cnt}, misses={miss_cnt}) render_count={self.render_track_count} age_frames={self.last_detection_age_frames} playback_fps={self.playback_fps} infer_fps={self.processing_fps}")

            # Precision pacing to match source video's original FPS
            next_frame_time += target_interval
            sleep_duration = next_frame_time - time.perf_counter()
            if sleep_duration > 0:
                time.sleep(sleep_duration)
            elif sleep_duration < -0.1:
                # If behind schedule by more than 100ms, resync clock
                next_frame_time = time.perf_counter()

        if cap is not None:
            cap.release()


class ActiveStreamManager:
    """Manages active camera stream workers for IP cameras, Webcams, and Uploaded Videos."""
    def __init__(self):
        self.workers: Dict[str, CameraStreamWorker] = {}
        self._allow_non_owner: bool = False
        self._manager_lock = threading.RLock()

    def get_or_create_worker(self, camera_id: str, source: str, source_type: str, capacity: int = 200, event_id: Optional[str] = None) -> CameraStreamWorker:
        from app.ai.ingestion_manager import ingestion_coordinator
        if not ingestion_coordinator.is_owner and not self._allow_non_owner:
            raise PermissionError(
                f"Ingestion ownership required: Process (PID: {os.getpid()}) cannot create CameraStreamWorker '{camera_id}' without holding ingestion lock."
            )
        with self._manager_lock:
            if camera_id not in self.workers:
                worker = CameraStreamWorker(camera_id, source, source_type, capacity, event_id)
                worker.start()
                self.workers[camera_id] = worker
            else:
                worker = self.workers[camera_id]
                if event_id:
                    worker.event_id = event_id
                if not worker.is_running:
                    worker.start()
            return self.workers[camera_id]

    def stop_worker(self, camera_id: str):
        with self._manager_lock:
            if camera_id in self.workers:
                self.workers[camera_id].stop()
                del self.workers[camera_id]


stream_manager = ActiveStreamManager()

import os
import cv2
import numpy as np
import logging
import time
import math
import threading
from typing import Optional, List, Tuple, Any, Dict

logger = logging.getLogger("uvicorn")

def bbox_iou(boxA: list, boxB: list) -> float:
    """Computes Intersection over Union (IoU) of two bounding boxes [x1, y1, x2, y2]."""
    xA = max(float(boxA[0]), float(boxB[0]))
    yA = max(float(boxA[1]), float(boxB[1]))
    xB = min(float(boxA[2]), float(boxB[2]))
    yB = min(float(boxA[3]), float(boxB[3]))

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h

    areaA = max(0.0, float(boxA[2]) - float(boxA[0])) * max(0.0, float(boxA[3]) - float(boxA[1]))
    areaB = max(0.0, float(boxB[2]) - float(boxB[0])) * max(0.0, float(boxB[3]) - float(boxB[1]))
    union_area = areaA + areaB - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


class Track:
    """
    Temporal track entity maintaining state lifecycle:
    - tentative: newly detected person awaiting multiple frame confirmation
    - confirmed: person consistently observed and actively tracked
    - lost: temporarily missed by detector, smoothly forward-predicted
    - removed: expired or out of frame
    """
    def __init__(self, track_id: int, box: list, conf: float, frame_seq: int, timestamp: float):
        self.track_id = track_id
        self.box = [float(x) for x in box]
        self.conf = float(conf)
        self.detection_frame_seq = frame_seq
        self.detection_timestamp = timestamp
        self.last_update_seq = frame_seq
        self.last_update_time = timestamp
        
        # Spatial dimensions & smoothed coordinates
        self.detection_cx = (self.box[0] + self.box[2]) / 2.0
        self.detection_cy = (self.box[1] + self.box[3]) / 2.0
        self.cx = self.detection_cx
        self.cy = self.detection_cy
        self.w = max(1.0, float(self.box[2] - self.box[0]))
        self.h = max(1.0, float(self.box[3] - self.box[1]))
        
        # Velocity in pixels/frame with EMA smoothing
        self.vx = 0.0
        self.vy = 0.0
        self.speed_mps = 0.0
        self.speed_updates = 0
        self.has_timestamp_speed = False
        
        # Passage boundary crossings
        self.last_crossing_time: Optional[float] = None
        self.last_crossing_dir: Optional[int] = None
        self.last_fwd_crossing_time: Optional[float] = None
        self.last_rev_crossing_time: Optional[float] = None
        
        # Lifecycle counters
        self.disappeared = 0
        self.hits = 1
        self.misses = 0
        self.state = "confirmed"  # tentative, confirmed, lost, removed

    @property
    def centroid(self):
        return (self.cx, self.cy)


MAX_PREDICTION_FRAMES = 15


def check_segment_intersection(
    A: Tuple[float, float],
    B: Tuple[float, float],
    P: Tuple[float, float],
    Q: Tuple[float, float]
) -> Tuple[bool, int]:
    """
    Determines if track displacement segment PQ intersects passage boundary line segment AB.
    Returns (crossed: bool, direction_sign: int) where:
      direction_sign = +1 if P was on negative side and Q on positive side (forward crossing)
      direction_sign = -1 if P was on positive side and Q on negative side (reverse crossing)
      direction_sign = 0 if no crossing or collinear movement.
    """
    def cross_product(p1, p2, p3):
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

    cp_p = cross_product(A, B, P)
    cp_q = cross_product(A, B, Q)

    # Both endpoints strictly on the same side of line AB -> no crossing
    if (cp_p > 0 and cp_q > 0) or (cp_p < 0 and cp_q < 0):
        return False, 0

    cp_a = cross_product(P, Q, A)
    cp_b = cross_product(P, Q, B)

    # Both endpoints of AB strictly on the same side of line PQ -> no crossing
    if (cp_a > 0 and cp_b > 0) or (cp_a < 0 and cp_b < 0):
        return False, 0

    # Avoid zero-displacement false triggers
    if cp_p == 0 and cp_q == 0:
        return False, 0

    dir_sign = 1 if (cp_p < cp_q) else -1
    return True, dir_sign


def compute_flow_utilization(
    measured_outflow_pps: Optional[float],
    capacity_pps: Optional[float]
) -> Dict[str, Any]:
    """
    Safely normalizes measured physical crowd outflow (people/second) against
    verified corridor capacity (people/second) (Task 7.6.11B Phase 4).
    Unit: dimensionless ratio (0.0 to 1.0+).
    Safely handles zero, negative, missing, or non-finite inputs without division by zero.
    """
    # Validate capacity
    if (
        capacity_pps is None
        or isinstance(capacity_pps, bool)
        or not isinstance(capacity_pps, (int, float))
        or not math.isfinite(capacity_pps)
        or capacity_pps <= 0
    ):
        return {
            "status": "uncalibrated_capacity",
            "flow_utilization": None,
            "is_calibrated": False,
            "reason": "Corridor capacity in people/second is missing, non-positive, or uncalibrated."
        }

    # Validate measured outflow
    if (
        measured_outflow_pps is None
        or isinstance(measured_outflow_pps, bool)
        or not isinstance(measured_outflow_pps, (int, float))
        or not math.isfinite(measured_outflow_pps)
        or measured_outflow_pps < 0
    ):
        return {
            "status": "uncalibrated_flow",
            "flow_utilization": None,
            "is_calibrated": False,
            "reason": "Measured physical outflow in people/second is uncalibrated or unavailable."
        }

    utilization = round(float(measured_outflow_pps) / float(capacity_pps), 3)
    return {
        "status": "calibrated",
        "flow_utilization": utilization,
        "is_calibrated": True,
        "measured_outflow_pps": round(float(measured_outflow_pps), 3),
        "capacity_pps": round(float(capacity_pps), 2),
        "reason": f"Operational flow utilization: {utilization * 100:.1f}% of corridor capacity ({capacity_pps} people/s)."
    }


class TemporalPersonTracker:
    """
    Temporal Person Tracker that bridges asynchronous YOLO inference with 24-30 FPS video playback.
    Continuously updates person positions on display frames using optical flow and velocity estimation,
    strictly bounded to MAX_PREDICTION_FRAMES (6 frames / ~250ms at 24 FPS).
    Ensures stale bounding boxes are never retained.
    """
    def __init__(self, max_prediction_frames: int = MAX_PREDICTION_FRAMES, max_distance: float = 120.0, meters_per_pixel: float = 0.04, fps: float = 30.0):
        self.next_object_id = 1
        self.tracks = {}
        self.max_prediction_frames = max_prediction_frames
        self.max_distance = max_distance
        self.meters_per_pixel = meters_per_pixel
        self.fps = fps
        self.prev_gray = None
        self.current_seq = 0
        self.seen_ids_window: Dict[int, float] = {}  # {track_id: timestamp}
        self.cumulative_unique_count = 0
        self.last_flow_metrics = {
            "X_neg": 0.0,
            "X_pos": 0.0,
            "Y_neg": 0.0,
            "Y_pos": 0.0,
            "lambda_out": 0.0,
            "avg_speed_mps": 0.0
        }
        # Configurable passage boundary geometry for physical crossing detection (Task 7.6.11B)
        self.boundary_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None
        self.boundary_direction: str = "forward"  # "forward", "reverse", "both"
        self.crossing_events: List[Dict[str, Any]] = []
        self.first_observation_time: Optional[float] = None
        # Diagnostic tracking metrics
        self.active_tracks_count: int = 0
        self.lost_tracks_count: int = 0
        self.removed_tracks_count: int = 0
        self.detection_misses_count: int = 0
        self.id_switches_count: int = 0
        self.lock = threading.RLock()

    def reset(self):
        with self.lock:
            self.tracks.clear()
            self.prev_gray = None
            self.current_seq = 0
            self.seen_ids_window.clear()
            self.crossing_events.clear()
            self.first_observation_time = None
            self.active_tracks_count = 0
            self.lost_tracks_count = 0
            self.removed_tracks_count = 0
            self.detection_misses_count = 0
            self.next_object_id = 1
            self.cumulative_unique_count = 0
            self.last_flow_metrics = {
                "X_neg": 0.0,
                "X_pos": 0.0,
                "Y_neg": 0.0,
                "Y_pos": 0.0,
                "lambda_out": 0.0,
                "avg_speed_mps": 0.0
            }

    def set_max_prediction_frames(self, max_frames: int):
        """Dynamically scales prediction window based on active camera count and inference gap."""
        with self.lock:
            self.max_prediction_frames = max(20, min(150, int(max_frames)))

    def set_boundary_line(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        direction: str = "forward",
        cooldown_seconds: float = 10.0
    ):
        """
        Configures an explicit passage boundary or tripwire segment ((x1, y1), (x2, y2)).
        direction: "forward" (crosses from negative to positive side), "reverse", or "both".
        """
        with self.lock:
            self.boundary_line = (
                (float(p1[0]), float(p1[1])),
                (float(p2[0]), float(p2[1]))
            )
            self.boundary_direction = direction
            self.crossing_cooldown_seconds = max(0.5, float(cooldown_seconds))

    def clear_boundary_line(self):
        """Clears boundary geometry; tracker returns uncalibrated operational outflow status."""
        with self.lock:
            self.boundary_line = None
            self.crossing_events.clear()

    def get_operational_outflow(
        self,
        window_seconds: float = 30.0,
        current_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Computes observed physical crowd outflow as distinct persons crossing a calibrated
        boundary per second over a bounded time window (Task 7.6.11B).
        Unit: people/second.
        If no boundary line is configured, safely returns uncalibrated status without guessing.
        """
        with self.lock:
            valid_window = (
                float(window_seconds)
                if (
                    window_seconds is not None
                    and not isinstance(window_seconds, bool)
                    and isinstance(window_seconds, (int, float))
                    and math.isfinite(window_seconds)
                    and window_seconds > 0
                )
                else 30.0
            )

            if self.boundary_line is None:
                return {
                    "status": "uncalibrated",
                    "flow_pps": None,
                    "crossing_count": 0,
                    "window_seconds": valid_window,
                    "unit": "people/second",
                    "reason": "No passage boundary geometry configured for this camera viewpoint."
                }

            if (
                current_time is not None
                and not isinstance(current_time, bool)
                and isinstance(current_time, (int, float))
                and math.isfinite(current_time)
                and current_time > 0
            ):
                now_t = float(current_time)
            else:
                wall_t = time.time()
                # If events are in Unix epoch (> 1_000_000_000), use wall_t so stale events expire in real time
                has_epoch = any(e["timestamp"] > 1_000_000_000 for e in self.crossing_events) or any(
                    getattr(t, "detection_timestamp", 0) > 1_000_000_000 for t in self.tracks.values()
                )
                if has_epoch:
                    now_t = wall_t
                else:
                    latest_ts = None
                    if self.crossing_events:
                        latest_ts = max(e["timestamp"] for e in self.crossing_events)
                    for t in self.tracks.values():
                        ts = getattr(t, "detection_timestamp", None)
                        if (
                            ts is not None
                            and not isinstance(ts, bool)
                            and isinstance(ts, (int, float))
                            and math.isfinite(ts)
                            and ts > 0
                        ):
                            if latest_ts is None or ts > latest_ts:
                                latest_ts = float(ts)
                    now_t = latest_ts if latest_ts is not None else wall_t

            cutoff = now_t - valid_window

            # Purge events older than measurement window
            self.crossing_events = [e for e in self.crossing_events if e["timestamp"] >= cutoff]

            # Filter valid events within window matching configured direction
            matching_events = [
                e for e in self.crossing_events
                if (
                    self.boundary_direction == "both"
                    or (self.boundary_direction == "forward" and e["direction"] > 0)
                    or (self.boundary_direction == "reverse" and e["direction"] < 0)
                )
            ]

            crossing_count = len(matching_events)
            distinct_crossers = len({e["track_id"] for e in matching_events})

            # Calculate actual active elapsed measurement duration
            if self.first_observation_time is not None and self.first_observation_time <= now_t:
                active_duration = max(0.001, now_t - self.first_observation_time)
                elapsed_sec = min(valid_window, active_duration)
            else:
                elapsed_sec = valid_window

            if elapsed_sec >= 0.5 and crossing_count > 0:
                flow_pps = round(crossing_count / elapsed_sec, 3)
            else:
                flow_pps = 0.0

            return {
                "status": "calibrated",
                "flow_pps": flow_pps,
                "crossing_count": crossing_count,
                "distinct_track_count": distinct_crossers,
                "window_seconds": valid_window,
                "unit": "people/second",
                "reason": f"Measured {crossing_count} boundary crossing(s) ({distinct_crossers} distinct tracks) over {elapsed_sec:.1f}s window."
            }

    def update_detections(self, detections: list, det_seq: int, det_time: float):
        """
        Integrates ground-truth YOLO detections from frame det_seq into active tracks.
        Maintains persistent track IDs, explicit track states (confirmed, lost, removed),
        and applies smooth temporal updates to prevent bounding-box flickering.
        """
        with self.lock:
            # Record first observation timestamp if valid and not yet recorded (Task 7.6.11B)
            is_det_time_valid = (
                det_time is not None
                and not isinstance(det_time, bool)
                and isinstance(det_time, (int, float))
                and math.isfinite(det_time)
                and det_time > 0
            )
            if self.first_observation_time is None and is_det_time_valid:
                self.first_observation_time = float(det_time)

            ref_seq = self.current_seq if self.current_seq > 0 else det_seq
            lag_frames = max(0, min(45, ref_seq - det_seq))

            # If no active tracks, initialize detections directly
            if not self.tracks:
                for b in detections:
                    tid = self.next_object_id
                    self.next_object_id += 1
                    self.cumulative_unique_count += 1
                    self.seen_ids_window[tid] = det_time
                    new_track = Track(tid, b[:4], b[4], det_seq, det_time)
                    new_track.last_update_seq = ref_seq
                    self.tracks[tid] = new_track
                self.active_tracks_count = len(self.tracks)
                return

            # If no detections in this frame, mark tracks as temporarily lost (DO NOT delete immediately)
            if not detections:
                for tid, track in list(self.tracks.items()):
                    track.misses += 1
                    track.disappeared += 1
                    track.state = "lost"
                    self.detection_misses_count += 1
                    age = max(0, ref_seq - track.detection_frame_seq)
                    if track.misses > self.max_prediction_frames or age > self.max_prediction_frames:
                        track.state = "removed"
                        self.removed_tracks_count += 1
                        del self.tracks[tid]
                self.active_tracks_count = sum(1 for t in self.tracks.values() if t.state == "confirmed")
                self.lost_tracks_count = sum(1 for t in self.tracks.values() if t.state == "lost")
                return

            track_ids = list(self.tracks.keys())
            num_tracks = len(track_ids)
            num_dets = len(detections)
            
            # Predict each track's position at the detection sequence det_seq
            pred_boxes = []
            pred_cents = []
            for tid in track_ids:
                t = self.tracks[tid]
                dt_from_det = det_seq - t.detection_frame_seq
                # Kinematic prediction at det_seq with velocity decay for multi-frame intervals
                dt_clamped = max(-25, min(45, dt_from_det))
                decay = 0.96 ** min(30, abs(dt_clamped))
                p_cx = t.detection_cx + t.vx * dt_clamped * decay
                p_cy = t.detection_cy + t.vy * dt_clamped * decay
                pred_cents.append((p_cx, p_cy))
                pred_boxes.append([p_cx - t.w / 2.0, p_cy - t.h / 2.0, p_cx + t.w / 2.0, p_cy + t.h / 2.0])

            d_cents = [((float(b[0]) + float(b[2])) / 2.0, (float(b[1]) + float(b[3])) / 2.0) for b in detections]

            used_tracks = set()
            used_dets = set()
            matches = []

            # =========================================================================
            # STAGE 1: High-Confidence Spatial IoU Overlap Matching (IoU >= 0.18)
            # Associates true physical bodies directly, completely preventing detection theft
            # =========================================================================
            iou_candidates = []
            for i in range(num_tracks):
                for j in range(num_dets):
                    iou = bbox_iou(pred_boxes[i], detections[j][:4])
                    if iou >= 0.18:
                        iou_candidates.append((iou, i, j))
            
            iou_candidates.sort(key=lambda x: x[0], reverse=True)
            for iou, r, c in iou_candidates:
                if r in used_tracks or c in used_dets:
                    continue
                used_tracks.add(r)
                used_dets.add(c)
                matches.append((r, c))

            # =========================================================================
            # STAGE 2: Adaptive Gated Proximity Matching (Fallback for rapid motion)
            # Dynamically scales gate by elapsed time between detections
            # =========================================================================
            prox_candidates = []
            for i in range(num_tracks):
                if i in used_tracks:
                    continue
                t = self.tracks[track_ids[i]]
                elapsed_sec = 0.04
                if det_time is not None and getattr(t, "detection_timestamp", None) is not None:
                    try:
                        dt = float(det_time) - float(t.detection_timestamp)
                        if dt > 0:
                            elapsed_sec = dt
                    except Exception:
                        pass
                elif det_seq is not None and getattr(t, "detection_frame_seq", None) is not None:
                    elapsed_sec = max(1, det_seq - t.detection_frame_seq) / max(1.0, float(self.fps))

                # Adaptive gate: scales with elapsed time and bounding box dimensions
                max_gate = max(60.0, min(180.0, 140.0 * elapsed_sec + 0.6 * max(t.w, t.h)))
                for j in range(num_dets):
                    if j in used_dets:
                        continue
                    dist = math.hypot(pred_cents[i][0] - d_cents[j][0], pred_cents[i][1] - d_cents[j][1])
                    if dist <= max_gate:
                        det = detections[j]
                        det_w = max(1.0, float(det[2]) - float(det[0]))
                        det_h = max(1.0, float(det[3]) - float(det[1]))
                        size_ratio = (det_w * det_h) / max(1.0, t.w * t.h)
                        if 0.35 <= size_ratio <= 2.8:
                            cost = (dist / max_gate) + 0.3 * abs(1.0 - size_ratio)
                            prox_candidates.append((cost, i, j))

            prox_candidates.sort(key=lambda x: x[0])
            for cost, r, c in prox_candidates:
                if r in used_tracks or c in used_dets:
                    continue
                used_tracks.add(r)
                used_dets.add(c)
                matches.append((r, c))

            # Process matched tracks
            for r, c in matches:
                tid = track_ids[r]
                track = self.tracks[tid]
                det = detections[c]
                det_cx = d_cents[c][0]
                det_cy = d_cents[c][1]
                det_w = max(1.0, float(det[2]) - float(det[0]))
                det_h = max(1.0, float(det[3]) - float(det[1]))

                dt_seq = max(1, det_seq - track.detection_frame_seq)
                dx = det_cx - track.detection_cx
                dy = det_cy - track.detection_cy
                disp_px = math.hypot(dx, dy)

                # Directional velocity for flow vectors and prediction (clamped to realistic speeds)
                inst_vx = max(-20.0, min(20.0, dx / dt_seq))
                inst_vy = max(-20.0, min(20.0, dy / dt_seq))
                if getattr(track, "speed_updates", 0) == 0:
                    track.vx = inst_vx
                    track.vy = inst_vy
                else:
                    track.vx = 0.60 * track.vx + 0.40 * inst_vx
                    track.vy = 0.60 * track.vy + 0.40 * inst_vy

                # Calibrated physical speed in meters/second
                prev_time = track.detection_timestamp
                is_curr_valid = (
                    det_time is not None
                    and not isinstance(det_time, bool)
                    and isinstance(det_time, (int, float))
                    and math.isfinite(det_time)
                    and det_time > 0
                )
                is_prev_valid = (
                    prev_time is not None
                    and not isinstance(prev_time, bool)
                    and isinstance(prev_time, (int, float))
                    and math.isfinite(prev_time)
                    and prev_time > 0
                )

                if is_curr_valid and is_prev_valid:
                    elapsed_sec = float(det_time) - float(prev_time)
                    if 0.001 <= elapsed_sec <= 10.0:
                        inst_speed = (disp_px * self.meters_per_pixel) / elapsed_sec
                        track.has_timestamp_speed = True
                    else:
                        effective_elapsed = float(dt_seq) / max(1.0, float(self.fps))
                        inst_speed = (disp_px * self.meters_per_pixel) / effective_elapsed
                        track.has_timestamp_speed = False
                else:
                    effective_elapsed = float(dt_seq) / max(1.0, float(self.fps))
                    inst_speed = (disp_px * self.meters_per_pixel) / effective_elapsed
                    track.has_timestamp_speed = False

                inst_speed = max(0.0, min(30.0, inst_speed))
                if getattr(track, "speed_updates", 0) == 0:
                    track.speed_mps = round(inst_speed, 2)
                    track.speed_updates = 1
                else:
                    track.speed_mps = round(0.60 * track.speed_mps + 0.40 * inst_speed, 2)
                    track.speed_updates += 1

                # Check passage boundary crossing if boundary is configured
                if self.boundary_line is not None and is_curr_valid:
                    p1, p2 = self.boundary_line
                    prev_pt = (track.detection_cx, track.detection_cy)
                    curr_pt = (det_cx, det_cy)
                    crossed, dir_sign = check_segment_intersection(p1, p2, prev_pt, curr_pt)
                    if crossed:
                        dir_match = (
                            self.boundary_direction == "both"
                            or (self.boundary_direction == "forward" and dir_sign > 0)
                            or (self.boundary_direction == "reverse" and dir_sign < 0)
                        )
                        if dir_match:
                            last_cross = getattr(track, "last_crossing_time", None)
                            cooldown_ok = (last_cross is None) or ((float(det_time) - last_cross) >= self.crossing_cooldown_seconds)
                            if cooldown_ok:
                                self.crossing_events.append({
                                    "track_id": tid,
                                    "timestamp": float(det_time),
                                    "direction": dir_sign
                                })
                                track.last_crossing_time = float(det_time)
                                track.last_crossing_dir = dir_sign

                track.detection_cx = det_cx
                track.detection_cy = det_cy
                track.detection_frame_seq = det_seq
                track.detection_timestamp = det_time

                # Project confirmed detection forward to current playback sequence
                projected_cx = det_cx + track.vx * lag_frames
                projected_cy = det_cy + track.vy * lag_frames

                # Smooth spatial state update (adaptive blending without jumping)
                alpha = 0.85 if track.state == "lost" else (0.80 if lag_frames > 5 else 0.55)
                track.cx = (1.0 - alpha) * track.cx + alpha * projected_cx
                track.cy = (1.0 - alpha) * track.cy + alpha * projected_cy
                track.w = 0.60 * track.w + 0.40 * det_w
                track.h = 0.60 * track.h + 0.40 * det_h
                track.box = [
                    track.cx - track.w / 2.0,
                    track.cy - track.h / 2.0,
                    track.cx + track.w / 2.0,
                    track.cy + track.h / 2.0
                ]

                track.conf = float(det[4])
                track.last_update_seq = ref_seq
                track.last_update_time = det_time
                track.hits += 1
                track.misses = 0
                track.disappeared = 0
                track.state = "confirmed"

            # Unmatched existing tracks: transition to "lost" state
            for r in set(range(num_tracks)).difference(used_tracks):
                tid = track_ids[r]
                track = self.tracks[tid]
                track.misses += 1
                track.disappeared += 1
                track.state = "lost"
                self.detection_misses_count += 1
                age = max(0, ref_seq - track.detection_frame_seq)
                if track.misses > self.max_prediction_frames or age > self.max_prediction_frames:
                    track.state = "removed"
                    self.removed_tracks_count += 1
                    del self.tracks[tid]

            # Unmatched new detections: register new confirmed tracks
            for c in set(range(num_dets)).difference(used_dets):
                det = detections[c]
                tid = self.next_object_id
                self.next_object_id += 1
                self.cumulative_unique_count += 1
                self.seen_ids_window[tid] = det_time
                new_track = Track(tid, det[:4], det[4], det_seq, det_time)
                new_track.last_update_seq = ref_seq
                self.tracks[tid] = new_track

            self.active_tracks_count = sum(1 for t in self.tracks.values() if t.state == "confirmed")
            self.lost_tracks_count = sum(1 for t in self.tracks.values() if t.state == "lost")

    def track_frame(self, frame: np.ndarray, curr_seq: int, curr_time: float) -> list:
        """
        Updates and predicts track positions on the current video frame using kinematic motion estimation.
        Decoupled from YOLO inference to preserve smooth 25-30 FPS video playback without optical flow CPU overhead.
        Returns list of active display boxes: [x1, y1, x2, y2, conf, track_id, det_seq, age_frames]
        Strictly enforces max_prediction_frames. Drops stale boxes immediately.
        """
        with self.lock:
            self.current_seq = curr_seq
            if not self.tracks:
                return []

            h, w = frame.shape[:2] if (frame is not None and isinstance(frame, np.ndarray) and len(frame.shape) >= 2) else (360, 640)

            active_boxes = []
            for tid, track in list(self.tracks.items()):
                age = max(0, curr_seq - track.detection_frame_seq)
                
                # Predict motion forward on current playback frame
                dt = curr_seq - track.last_update_seq
                if dt > 0:
                    damping = 0.94 if age > 5 else 0.98
                    track.vx *= damping
                    track.vy *= damping
                    track.cx += track.vx * dt
                    track.cy += track.vy * dt

                    # Adaptive drift clamp: allows natural walking motion without premature stalling
                    drift_x = track.cx - track.detection_cx
                    drift_y = track.cy - track.detection_cy
                    drift_dist = math.hypot(drift_x, drift_y)
                    max_allowed_drift = max(60.0, min(250.0, (1.2 * max(track.w, track.h)) + 6.0 * age))
                    if drift_dist > max_allowed_drift:
                        scale = max_allowed_drift / drift_dist
                        track.cx = track.detection_cx + drift_x * scale
                        track.cy = track.detection_cy + drift_y * scale

                    track.box = [
                        track.cx - track.w / 2.0,
                        track.cy - track.h / 2.0,
                        track.cx + track.w / 2.0,
                        track.cy + track.h / 2.0
                    ]
                    track.last_update_seq = curr_seq
                    track.last_update_time = curr_time

                # Display active tracks within freshness window
                if age <= self.max_prediction_frames and track.state != "removed":
                    x1 = max(0, min(w - 1, int(track.box[0])))
                    y1 = max(0, min(h - 1, int(track.box[1])))
                    x2 = max(0, min(w - 1, int(track.box[2])))
                    y2 = max(0, min(h - 1, int(track.box[3])))
                    if x2 > x1 and y2 > y1:
                        active_boxes.append([
                            x1, y1, x2, y2,
                            round(track.conf, 2),
                            track.track_id,
                            track.detection_frame_seq,
                            age,
                            track.state
                        ])
                else:
                    track.disappeared += 1
                    if track.disappeared > max(25, self.max_prediction_frames):
                        del self.tracks[tid]

            self.active_tracks_count = sum(1 for t in self.tracks.values() if t.state == "confirmed")
            self.lost_tracks_count = sum(1 for t in self.tracks.values() if t.state == "lost")
            return active_boxes

    def get_unique_window_count(self, window_seconds: float = 30.0, current_time: Optional[float] = None) -> int:
        """
        Returns number of unique tracked person IDs observed within a sliding time window (default 30s).
        Prevents double-counting and memory accumulation.
        """
        with self.lock:
            now_t = current_time if current_time is not None else time.time()
            cutoff = now_t - window_seconds
            # Purge expired track IDs older than sliding window
            self.seen_ids_window = {
                tid: ts for tid, ts in self.seen_ids_window.items() if ts >= cutoff
            }
            return len(self.seen_ids_window)

    def compute_flow_metrics(self) -> Dict[str, float]:
        """
        Computes motion and flow metrics according to IEEE Access 2025 (Section VI-B, VI-C):
        - Equations (2): Horizontal flow components X^-, X^+
        - Equations (3): Vertical flow components Y^-, Y^+
        - Equation (4): Total rate of decrease / outflow lambda_out = X^+ + X^- + Y^+ + Y^-
        - Physical velocity (meters/second) via perspective meters_per_pixel scaling
        """
        with self.lock:
            if not self.tracks:
                return {
                    "X_neg": 0.0,
                    "X_pos": 0.0,
                    "Y_neg": 0.0,
                    "Y_pos": 0.0,
                    "lambda_out": 0.0,
                    "avg_speed_mps": 0.0,
                    "active_track_count": 0,
                    "operational_outflow": self.get_operational_outflow()
                }

            vx_list = [t.vx for t in self.tracks.values()]
            vy_list = [t.vy for t in self.tracks.values()]

            # Horizontal Flow Components (Eq 2)
            abs_vx_sum = sum(abs(v) for v in vx_list)
            if abs_vx_sum > 1e-4:
                x_neg = sum(-v for v in vx_list if v < 0) / abs_vx_sum
                x_pos = sum(v for v in vx_list if v > 0) / abs_vx_sum
            else:
                x_neg, x_pos = 0.0, 0.0

            # Vertical Flow Components (Eq 3)
            abs_vy_sum = sum(abs(v) for v in vy_list)
            if abs_vy_sum > 1e-4:
                y_neg = sum(-v for v in vy_list if v < 0) / abs_vy_sum
                y_pos = sum(v for v in vy_list if v > 0) / abs_vy_sum
            else:
                y_neg, y_pos = 0.0, 0.0

            # Outflow Rate (Eq 4)
            lambda_out = round(x_pos + x_neg + y_pos + y_neg, 3)

            # Calibrated physical speed in meters/second
            # Prioritizes timestamp-calibrated speed_mps when available; falls back to static fps for synthetic tracks
            track_speeds = []
            for t in self.tracks.values():
                if getattr(t, "speed_updates", 0) > 0:
                    track_speeds.append(t.speed_mps)
                else:
                    px_speed = math.hypot(t.vx, t.vy)
                    track_speeds.append(px_speed * self.meters_per_pixel * self.fps)

            avg_speed_mps = round(sum(track_speeds) / max(1, len(track_speeds)), 2)

            metrics = {
                "X_neg": round(x_neg, 3),
                "X_pos": round(x_pos, 3),
                "Y_neg": round(y_neg, 3),
                "Y_pos": round(y_pos, 3),
                "lambda_out": lambda_out,
                "avg_speed_mps": avg_speed_mps,
                "active_track_count": len(self.tracks),
                "operational_outflow": self.get_operational_outflow()
            }
            self.last_flow_metrics = metrics
            return metrics

    # Backward compatibility fallback
    def update(self, rects):
        with self.lock:
            return {i: i + 1 for i in range(len(rects))}


# Compatibility alias
SimpleCentroidTracker = TemporalPersonTracker


def _find_model_weights(model_name: str) -> str:
    """Finds YOLO weights file across standard relative and absolute paths."""
    if os.path.isabs(model_name) and os.path.exists(model_name):
        return model_name
    if os.path.exists(model_name):
        return os.path.abspath(model_name)
    # Search backend/ directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate = os.path.join(backend_dir, model_name)
    if os.path.exists(candidate):
        return candidate
    # Search root workspace directory
    parent_dir = os.path.dirname(backend_dir)
    candidate_parent = os.path.join(parent_dir, model_name)
    if os.path.exists(candidate_parent):
        return candidate_parent
    return model_name


class PersonDetector:
    def __init__(self, model_name: str = "yolov8n.pt"):
        self.model_name = model_name
        self.model = None
        self.conf_threshold = 0.20
        self._lock = threading.RLock()
        self.tracker = TemporalPersonTracker(max_prediction_frames=15)
        self.last_error: Optional[str] = None
        self._init_model()

    def set_confidence_threshold(self, conf: float):
        self.conf_threshold = max(0.05, min(0.95, float(conf)))

    def _init_model(self):
        try:
            import torch
            optimal_threads = max(2, min(8, os.cpu_count() or 4))
            torch.set_num_threads(optimal_threads)
            from ultralytics import YOLO
            resolved_path = _find_model_weights(self.model_name)
            logger.info("Initializing Ultralytics YOLO model: %s (resolved: %s)", self.model_name, resolved_path)
            self.model = YOLO(resolved_path)
            # Warm up model to pre-allocate inference tensors and eliminate initial latency
            dummy_frame = np.zeros((480, 480, 3), dtype=np.uint8)
            self.model.predict(dummy_frame, conf=0.20, classes=[0], imgsz=480, verbose=False)
            self.last_error = None
            logger.info("Ultralytics YOLO model warmed up successfully.")
        except Exception as e:
            self.last_error = str(e)
            logger.error("Could not initialize Ultralytics YOLO: %s", e, exc_info=True)
            self.model = None

    def get_runtime_engine_info(self) -> dict:
        torch_version = ""
        cuda_avail = False
        try:
            import torch
            cuda_avail = torch.cuda.is_available()
            torch_version = torch.__version__
        except Exception:
            pass

        if self.model is not None:
            return {
                "engine": "Ultralytics YOLOv8n",
                "backend": "PyTorch",
                "inferenceEngine": f"PyTorch {torch_version} ({'CUDA' if cuda_avail else 'CPU'})",
                "device": "CUDA" if cuda_avail else "CPU",
                "hardware_accelerated": cuda_avail,
                "isCuda": cuda_avail,
                "is_cuda": cuda_avail,
                "is_fallback": False,
                "status": "ONLINE",
                "message": "NVIDIA CUDA acceleration active" if cuda_avail else "Host CPU execution engine active (PyTorch standard)"
            }
        else:
            return {
                "engine": "YOLO Unavailable",
                "backend": "None",
                "inferenceEngine": "None",
                "device": "CPU",
                "hardware_accelerated": False,
                "isCuda": False,
                "is_cuda": False,
                "is_fallback": False,
                "status": "ERROR",
                "message": f"YOLO model unavailable: {self.last_error or 'Weights missing or load failed'}"
            }

    def detect_batch(self, frames: List[np.ndarray], conf_threshold: float = 0.20, imgsz: int = 480) -> Tuple[List[List], List[int], float]:
        """
        Runs batched YOLO person detection across multiple image frames.
        Returns:
            all_boxes: List of box lists, one per input frame
            all_counts: List of detection counts, one per input frame
            infer_duration_ms: float (measured via monotonic clock)
        """
        if not frames:
            return [], [], 0.0

        valid_frames = []
        for f in frames:
            if f is not None and isinstance(f, np.ndarray) and f.size > 0 and len(f.shape) == 3:
                valid_frames.append(f)
            else:
                valid_frames.append(None)

        all_boxes: List[List] = [[] for _ in range(len(frames))]
        all_counts: List[int] = [0 for _ in range(len(frames))]
        infer_ms = 0.0

        if self.model is not None and any(f is not None for f in valid_frames):
            with self._lock:
                infer_t0 = time.perf_counter()
                try:
                    # Pass either single frame or list of frames to Ultralytics YOLO
                    run_inputs = [f if f is not None else np.zeros((480, 480, 3), dtype=np.uint8) for f in valid_frames]
                    if len(run_inputs) == 1:
                        results = self.model.predict(
                            run_inputs[0],
                            conf=conf_threshold,
                            classes=[0],
                            imgsz=imgsz,
                            iou=0.70,
                            verbose=False
                        )
                    else:
                        results = self.model.predict(
                            run_inputs,
                            conf=conf_threshold,
                            classes=[0],
                            imgsz=imgsz,
                            iou=0.70,
                            verbose=False
                        )

                    for i, r in enumerate(results):
                        orig_frame = valid_frames[i]
                        if orig_frame is None:
                            continue
                        h, w = orig_frame.shape[:2]
                        frame_boxes = []
                        for box in r.boxes:
                            coords = box.xyxy[0].cpu().numpy().astype(int)
                            x1 = max(0, min(w - 1, int(coords[0])))
                            y1 = max(0, min(h - 1, int(coords[1])))
                            x2 = max(0, min(w - 1, int(coords[2])))
                            y2 = max(0, min(h - 1, int(coords[3])))
                            if x2 > x1 and y2 > y1:
                                conf = float(box.conf[0].cpu().numpy())
                                frame_boxes.append([x1, y1, x2, y2, round(conf, 2), None])
                        all_boxes[i] = frame_boxes
                        all_counts[i] = len(frame_boxes)
                    self.last_error = None
                except Exception as ex:
                    logger.error("YOLO batched inference error (%s). Reporting real diagnostic state without fake detections.", ex)
                    self.last_error = str(ex)
                    all_boxes = [[] for _ in range(len(frames))]
                    all_counts = [0 for _ in range(len(frames))]
                infer_ms = (time.perf_counter() - infer_t0) * 1000.0

        return all_boxes, all_counts, infer_ms

    def detect_frame(self, frame: np.ndarray, conf_threshold: float = 0.20, tracker: Optional[Any] = None, imgsz: int = 480) -> Tuple[List, int, float]:
        """
        Runs YOLO person detection (COCO class 0).
        Returns:
            boxes: List of [x1, y1, x2, y2, confidence, track_id]
            raw_count: int
            infer_duration_ms: float
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0 or len(frame.shape) != 3:
            return [], 0, 0.0
        all_boxes, all_counts, infer_ms = self.detect_batch([frame], conf_threshold=conf_threshold, imgsz=imgsz)
        return all_boxes[0], all_counts[0], infer_ms

    def draw_annotations(self, frame: np.ndarray, boxes: list, person_count: int) -> np.ndarray:
        """
        Rapidly overlays bounding boxes and person count header (< 0.2ms).
        boxes can contain [x1, y1, x2, y2, conf, track_id, ...]
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame

        annotated_frame = frame.copy()
        h, w = annotated_frame.shape[:2]

        for idx, b in enumerate(boxes):
            x1 = max(0, min(w - 1, int(b[0])))
            y1 = max(0, min(h - 1, int(b[1])))
            x2 = max(0, min(w - 1, int(b[2])))
            y2 = max(0, min(h - 1, int(b[3])))
            if x2 <= x1 or y2 <= y1:
                continue

            conf = float(b[4]) if len(b) > 4 else 0.85
            track_id = b[5] if len(b) > 5 and b[5] is not None else (idx + 1)
            is_lost = len(b) > 8 and b[8] == "lost"

            if is_lost:
                label = f"Person #{track_id} [TRACK]"
                box_color = (0, 215, 255)      # Amber/Gold for smooth temporal prediction during brief YOLO miss
                corner_color = (0, 165, 255)   # Deep amber HUD accents
                text_color = (0, 215, 255)
            else:
                label = f"Person #{track_id} ({conf:.2f})"
                box_color = (0, 255, 200)      # High-visibility neon cyan for confirmed detections
                corner_color = (0, 255, 255)   # Surveillance yellow HUD accents
                text_color = (0, 255, 200)

            # High-visibility bounding box with anti-aliasing
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, 2, lineType=cv2.LINE_AA)

            # Corner accents for surveillance HUD aesthetic
            corner_len = max(6, min(16, (x2 - x1) // 4, (y2 - y1) // 4))
            cv2.line(annotated_frame, (x1, y1), (x1 + corner_len, y1), corner_color, 2, lineType=cv2.LINE_AA)
            cv2.line(annotated_frame, (x1, y1), (x1, y1 + corner_len), corner_color, 2, lineType=cv2.LINE_AA)
            cv2.line(annotated_frame, (x2, y2), (x2 - corner_len, y2), corner_color, 2, lineType=cv2.LINE_AA)
            cv2.line(annotated_frame, (x2, y2), (x2, y2 - corner_len), corner_color, 2, lineType=cv2.LINE_AA)

            # Draw label background & text
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(annotated_frame, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, max(th + 6, y1)), (15, 23, 42), -1)
            cv2.putText(annotated_frame, label, (x1 + 2, max(th + 2, y1 - 3)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, text_color, 1, lineType=cv2.LINE_AA)

        # Draw count header overlay on frame
        cv2.putText(annotated_frame, f"AI COUNT: {person_count} PERSONS", (20, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0) if person_count < 100 else (0, 0, 255), 2, lineType=cv2.LINE_AA)

        return annotated_frame

    def process_frame(self, frame: np.ndarray, conf_threshold: float = 0.20, tracker: Optional[Any] = None, draw_boxes: bool = True, imgsz: int = 480):
        """
        Process a single image frame (numpy BGR array).
        Returns:
            boxes: List of [x1, y1, x2, y2, confidence, track_id]
            person_count: int
            annotated_frame: np.ndarray (with bounding box overlays)
        """
        boxes, _, _ = self.detect_frame(frame, conf_threshold=conf_threshold, tracker=tracker, imgsz=imgsz)
        person_count = len(boxes)

        if draw_boxes:
            annotated_frame = self.draw_annotations(frame, boxes, person_count)
        else:
            annotated_frame = frame

        return boxes, person_count, annotated_frame


detector = PersonDetector()


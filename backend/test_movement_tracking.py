"""
Unit & Algorithmic Tests for Task 5 (Movement & Flow Analysis) and Task 6 (Tracking Reliability)
IEEE Access 2025 Base Paper:
- Equations (2): Horizontal flow components X^-, X^+
- Equations (3): Vertical flow components Y^-, Y^+
- Equation (4): Total outflow rate lambda_out = X^+ + X^- + Y^+ + Y^-
- Equation (5): Boundary inflow lambda_in
- Speed Calibration: Pixel displacement to physical m/s
- Tracking Reliability: Persistent IDs, bounded age (6 frames), isolated state, sliding window counting
"""

import sys
import unittest
import time
import math
from unittest.mock import MagicMock
import numpy as np

# Allow tests to run when PyJWT is not installed in the execution environment
if "jwt" not in sys.modules:
    try:
        import jwt  # noqa: F401
    except ImportError:
        sys.modules["jwt"] = MagicMock()

from app.ai.detector import (
    TemporalPersonTracker,
    Track,
    check_segment_intersection,
    compute_flow_utilization
)

class TestMovementAndTrackingReliability(unittest.TestCase):
    def setUp(self):
        self.tracker = TemporalPersonTracker(max_prediction_frames=6, meters_per_pixel=0.05, fps=30.0)

    # =========================================================================
    # TASK 5: MOVEMENT & FLOW ANALYSIS (Equations 2, 3, 4, 5)
    # =========================================================================

    def test_flow_vector_equations_horizontal(self):
        """
        Verify Equation (2):
        X^- = sum(-v_xi if v_xi < 0) / sum(|v_xi|)
        X^+ = sum(v_xi if v_xi > 0) / sum(|v_xi|)
        X^- + X^+ == 1.0 when motion is present.
        """
        # Inject synthetic tracks with known horizontal velocities
        # Track 1: moving left, vx = -4.0
        # Track 2: moving left, vx = -6.0
        # Track 3: moving right, vx = +10.0
        # Total |vx| = |-4| + |-6| + |10| = 20.0
        # Expected X^- = (4 + 6) / 20 = 10 / 20 = 0.50
        # Expected X^+ = 10 / 20 = 0.50
        t1 = Track(1, [100, 100, 140, 180], 0.9, 1, time.time())
        t1.vx = -4.0
        t1.vy = 0.0

        t2 = Track(2, [200, 100, 240, 180], 0.9, 1, time.time())
        t2.vx = -6.0
        t2.vy = 0.0

        t3 = Track(3, [300, 100, 340, 180], 0.9, 1, time.time())
        t3.vx = 10.0
        t3.vy = 0.0

        self.tracker.tracks = {1: t1, 2: t2, 3: t3}
        metrics = self.tracker.compute_flow_metrics()

        self.assertAlmostEqual(metrics["X_neg"], 0.50, places=2)
        self.assertAlmostEqual(metrics["X_pos"], 0.50, places=2)
        self.assertAlmostEqual(metrics["X_neg"] + metrics["X_pos"], 1.0, places=2)

    def test_flow_vector_equations_vertical(self):
        """
        Verify Equation (3):
        Y^- = sum(-v_yi if v_yi < 0) / sum(|v_yi|)
        Y^+ = sum(v_yi if v_yi > 0) / sum(|v_yi|)
        """
        # Track 1: moving upward (negative Y in screen coords), vy = -8.0
        # Track 2: moving downward (positive Y in screen coords), vy = +2.0
        # Total |vy| = 8 + 2 = 10.0
        # Expected Y^- = 8 / 10 = 0.80
        # Expected Y^+ = 2 / 10 = 0.20
        t1 = Track(1, [100, 100, 140, 180], 0.9, 1, time.time())
        t1.vx = 0.0
        t1.vy = -8.0

        t2 = Track(2, [200, 100, 240, 180], 0.9, 1, time.time())
        t2.vx = 0.0
        t2.vy = 2.0

        self.tracker.tracks = {1: t1, 2: t2}
        metrics = self.tracker.compute_flow_metrics()

        self.assertAlmostEqual(metrics["Y_neg"], 0.80, places=2)
        self.assertAlmostEqual(metrics["Y_pos"], 0.20, places=2)

    def test_outflow_rate_lambda_out(self):
        """
        Verify Equation (4):
        lambda_out = X^+ + X^- + Y^+ + Y^-
        """
        t1 = Track(1, [100, 100, 140, 180], 0.9, 1, time.time())
        t1.vx = 5.0
        t1.vy = 5.0

        self.tracker.tracks = {1: t1}
        metrics = self.tracker.compute_flow_metrics()

        expected_lambda = metrics["X_pos"] + metrics["X_neg"] + metrics["Y_pos"] + metrics["Y_neg"]
        self.assertAlmostEqual(metrics["lambda_out"], expected_lambda, places=2)

    def test_speed_calibration_physical_units(self):
        """
        Verify physical speed conversion from pixel displacement to meters/sec:
        v_phys = avg_px_speed * meters_per_pixel * fps.
        """
        # Track moving at 10 pixels per frame.
        # With fps=30 and meters_per_pixel=0.05:
        # v_phys = 10 * 0.05 * 30 = 15.0 m/s.
        t1 = Track(1, [100, 100, 140, 180], 0.9, 1, time.time())
        t1.vx = 6.0
        t1.vy = 8.0  # hypot = 10.0 px/frame

        self.tracker.tracks = {1: t1}
        metrics = self.tracker.compute_flow_metrics()

        expected_speed = 10.0 * 0.05 * 30.0
        self.assertAlmostEqual(metrics["avg_speed_mps"], expected_speed, delta=0.5)

    # =========================================================================
    # TASK 6: TRACKING RELIABILITY & ISOLATION
    # =========================================================================

    def test_tracking_id_persistence_across_frames(self):
        """Verify that track ID persists across consecutive frames for moving detections."""
        t0 = time.time()
        # Frame 1: Detection at (100, 100, 150, 200)
        detections_f1 = [[100, 100, 150, 200, 0.95]]
        self.tracker.update_detections(detections_f1, det_seq=1, det_time=t0)

        active_tracks = list(self.tracker.tracks.values())
        self.assertEqual(len(active_tracks), 1)
        initial_id = active_tracks[0].track_id

        # Frame 2: Person moved slightly to (105, 102, 155, 202)
        detections_f2 = [[105, 102, 155, 202, 0.93]]
        self.tracker.update_detections(detections_f2, det_seq=2, det_time=t0 + 0.033)

        self.assertEqual(len(self.tracker.tracks), 1)
        self.assertIn(initial_id, self.tracker.tracks, "Track ID must persist across consecutive frames")

    def test_tracker_reset_clears_state(self):
        """Verify that tracker reset cleanly purges tracks and seen window."""
        self.tracker.update_detections([[50, 50, 90, 120, 0.88]], det_seq=1, det_time=time.time())
        self.assertGreater(len(self.tracker.tracks), 0)

        self.tracker.reset()
        self.assertEqual(len(self.tracker.tracks), 0)
        self.assertEqual(len(self.tracker.seen_ids_window), 0)
        self.assertEqual(self.tracker.last_flow_metrics["lambda_out"], 0.0)

    def test_camera_tracking_isolation(self):
        """Verify that separate tracker instances maintain complete state isolation (no leak)."""
        tracker_cam1 = TemporalPersonTracker()
        tracker_cam2 = TemporalPersonTracker()

        tracker_cam1.update_detections([[10, 10, 50, 80, 0.9]], det_seq=1, det_time=time.time())
        
        self.assertEqual(len(tracker_cam1.tracks), 1)
        self.assertEqual(len(tracker_cam2.tracks), 0, "Tracker 2 must not receive Tracker 1 state")

    def test_unique_sliding_window_counting(self):
        """Verify that unique track IDs are counted in a rolling time window and expired IDs are purged."""
        now = time.time()
        # Add 3 IDs at current time
        self.tracker.seen_ids_window = {
            1: now - 10.0,  # 10s old (inside 30s window)
            2: now - 20.0,  # 20s old (inside 30s window)
            3: now - 45.0   # 45s old (outside 30s window)
        }

        count = self.tracker.get_unique_window_count(window_seconds=30.0, current_time=now)
        self.assertEqual(count, 2, "Only IDs within last 30s should be counted")
        self.assertNotIn(3, self.tracker.seen_ids_window, "Expired ID must be purged")

    # =========================================================================
    # TASK 7.6.10: REGRESSION & MATHEMATICAL FIDELITY TESTS
    # =========================================================================

    def test_lambda_out_both_horizontal_and_vertical_nonzero(self):
        """
        Verify lambda_out when both horizontal and vertical movement are nonzero:
        X^+ + X^- == 1.0 and Y^+ + Y^- == 1.0 => lambda_out == 2.000.
        """
        t1 = Track(1, [100, 100, 140, 180], 0.9, 1, time.time())
        t1.vx = 4.0   # Horizontal motion
        t1.vy = 3.0   # Vertical motion

        self.tracker.tracks = {1: t1}
        metrics = self.tracker.compute_flow_metrics()

        self.assertAlmostEqual(metrics["X_pos"], 1.0, places=3)
        self.assertAlmostEqual(metrics["X_neg"], 0.0, places=3)
        self.assertAlmostEqual(metrics["Y_pos"], 1.0, places=3)
        self.assertAlmostEqual(metrics["Y_neg"], 0.0, places=3)
        self.assertAlmostEqual(metrics["lambda_out"], 2.0, places=3)

    def test_lambda_out_only_horizontal_movement(self):
        """
        Verify lambda_out when only horizontal movement is present (no vertical motion):
        X^+ + X^- == 1.0 and Y^+ == 0.0, Y^- == 0.0 => lambda_out == 1.000.
        """
        t1 = Track(1, [100, 100, 140, 180], 0.9, 1, time.time())
        t1.vx = 8.0
        t1.vy = 0.0

        self.tracker.tracks = {1: t1}
        metrics = self.tracker.compute_flow_metrics()

        self.assertAlmostEqual(metrics["X_pos"], 1.0, places=3)
        self.assertAlmostEqual(metrics["X_neg"], 0.0, places=3)
        self.assertAlmostEqual(metrics["Y_pos"], 0.0, places=3)
        self.assertAlmostEqual(metrics["Y_neg"], 0.0, places=3)
        self.assertAlmostEqual(metrics["lambda_out"], 1.0, places=3)

    def test_lambda_out_only_vertical_movement(self):
        """
        Verify lambda_out when only vertical movement is present (no horizontal motion):
        X^+ == 0.0, X^- == 0.0 and Y^+ + Y^- == 1.0 => lambda_out == 1.000.
        """
        t1 = Track(1, [100, 100, 140, 180], 0.9, 1, time.time())
        t1.vx = 0.0
        t1.vy = -6.0

        self.tracker.tracks = {1: t1}
        metrics = self.tracker.compute_flow_metrics()

        self.assertAlmostEqual(metrics["X_pos"], 0.0, places=3)
        self.assertAlmostEqual(metrics["X_neg"], 0.0, places=3)
        self.assertAlmostEqual(metrics["Y_pos"], 0.0, places=3)
        self.assertAlmostEqual(metrics["Y_neg"], 1.0, places=3)
        self.assertAlmostEqual(metrics["lambda_out"], 1.0, places=3)

    def test_lambda_out_headcount_invariance(self):
        """
        Verify that lambda_out is mathematically invariant to the number of moving people
        when directional proportions remain identical (e.g. 2 tracks vs 50 tracks).
        Demonstrates that headcount is normalized out by Eq (2) and Eq (3).
        """
        now = time.time()
        # Population A: 2 people moving northeast (vx=5.0, vy=-5.0)
        tracks_2 = {
            i: Track(i, [100 + i * 20, 100, 140 + i * 20, 180], 0.9, 1, now)
            for i in range(1, 3)
        }
        for t in tracks_2.values():
            t.vx = 5.0
            t.vy = -5.0

        self.tracker.tracks = tracks_2
        metrics_2 = self.tracker.compute_flow_metrics()

        # Population B: 50 people moving northeast with identical directional proportions
        tracks_50 = {
            i: Track(i, [10 + i * 5, 10, 50 + i * 5, 80], 0.9, 1, now)
            for i in range(1, 51)
        }
        for t in tracks_50.values():
            t.vx = 5.0
            t.vy = -5.0

        self.tracker.tracks = tracks_50
        metrics_50 = self.tracker.compute_flow_metrics()

        # Headcount changed by 25x, but lambda_out is identically 2.000 in both
        self.assertEqual(metrics_2["active_track_count"], 2)
        self.assertEqual(metrics_50["active_track_count"], 50)
        self.assertAlmostEqual(metrics_2["lambda_out"], 2.0, places=3)
        self.assertAlmostEqual(metrics_50["lambda_out"], 2.0, places=3)
        self.assertEqual(metrics_2["lambda_out"], metrics_50["lambda_out"])

    def test_lambda_out_speed_invariance(self):
        """
        Verify that lambda_out is mathematically invariant to moving speed
        when directional distribution remains identical (e.g. 0.2 px/frame vs 20 px/frame).
        Demonstrates that velocity magnitude is canceled out in Eq (2) and Eq (3).
        """
        now = time.time()
        # Slow group: 0.2 px/frame (~0.3 m/s)
        t_slow = Track(1, [100, 100, 140, 180], 0.9, 1, now)
        t_slow.vx = 0.2
        t_slow.vy = 0.2
        self.tracker.tracks = {1: t_slow}
        metrics_slow = self.tracker.compute_flow_metrics()

        # Fast group: 20.0 px/frame (~30.0 m/s)
        t_fast = Track(2, [100, 100, 140, 180], 0.9, 1, now)
        t_fast.vx = 20.0
        t_fast.vy = 20.0
        self.tracker.tracks = {2: t_fast}
        metrics_fast = self.tracker.compute_flow_metrics()

        # Speed changed by 100x, but lambda_out is identically 2.000 in both
        self.assertAlmostEqual(metrics_slow["lambda_out"], 2.0, places=3)
        self.assertAlmostEqual(metrics_fast["lambda_out"], 2.0, places=3)
        self.assertEqual(metrics_slow["lambda_out"], metrics_fast["lambda_out"])
        # However, calibrated physical speed reflects the difference
        self.assertGreater(metrics_fast["avg_speed_mps"], metrics_slow["avg_speed_mps"] * 50)

    def test_lambda_out_no_valid_movement(self):
        """
        Verify lambda_out when there is no valid movement:
        - Empty tracks: lambda_out == 0.0, avg_speed == 0.0.
        - Stationary tracks (velocities 0.0 or below 1e-4 threshold): lambda_out == 0.0.
        """
        # Case A: Empty tracks
        self.tracker.tracks = {}
        m_empty = self.tracker.compute_flow_metrics()
        self.assertEqual(m_empty["lambda_out"], 0.0)
        self.assertEqual(m_empty["avg_speed_mps"], 0.0)
        self.assertEqual(m_empty["X_pos"], 0.0)
        self.assertEqual(m_empty["Y_pos"], 0.0)

        # Case B: Stationary tracks (vx = 0.0, vy = 0.0)
        t_stat = Track(1, [100, 100, 140, 180], 0.9, 1, time.time())
        t_stat.vx = 0.0
        t_stat.vy = 0.0
        self.tracker.tracks = {1: t_stat}
        m_stat = self.tracker.compute_flow_metrics()
        self.assertEqual(m_stat["lambda_out"], 0.0)
        self.assertEqual(m_stat["avg_speed_mps"], 0.0)

        # Case C: Sub-threshold jitter (below 1e-4 threshold in detector.py lines 279, 287)
        t_jitter = Track(2, [100, 100, 140, 180], 0.9, 1, time.time())
        t_jitter.vx = 1e-5
        t_jitter.vy = 1e-5
        self.tracker.tracks = {2: t_jitter}
        m_jitter = self.tracker.compute_flow_metrics()
        self.assertEqual(m_jitter["lambda_out"], 0.0)

    def test_equivalent_physical_motion_at_30fps_and_10fps(self):
        """
        Task 7.6.11A Requirement 8:
        Verify that equivalent physical motion yields equivalent calibrated speed
        at approximately 30 FPS (~33.3 ms intervals) and 10 FPS (~100 ms intervals).
        - Target physical speed: 4.5 m/s (meters_per_pixel = 0.05).
        - At 30 FPS (dt = 33.3 ms): displacement = 3.0 px (3.0 * 0.05 / 0.0333 = 4.5 m/s).
        - At 10 FPS (dt = 100.0 ms): displacement = 9.0 px (9.0 * 0.05 / 0.1000 = 4.5 m/s).
        Both must yield 4.5 m/s (within 0.1 m/s), regardless of sequence number or processing frame rate.
        """
        t0 = 1000.0
        # Case 1: 30 fps playback (dt ~ 33.33 ms per frame)
        tracker_30 = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker_30.update_detections([[100, 100, 140, 180, 0.9]], det_seq=1, det_time=t0)
        tracker_30.update_detections([[103, 100, 143, 180, 0.9]], det_seq=2, det_time=t0 + 0.03333)
        metrics_30 = tracker_30.compute_flow_metrics()

        # Case 2: 10 fps playback (dt ~ 100.0 ms per frame)
        tracker_10 = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker_10.update_detections([[100, 100, 140, 180, 0.9]], det_seq=1, det_time=t0)
        tracker_10.update_detections([[109, 100, 149, 180, 0.9]], det_seq=2, det_time=t0 + 0.1000)
        metrics_10 = tracker_10.compute_flow_metrics()

        self.assertAlmostEqual(metrics_30["avg_speed_mps"], 4.50, delta=0.1)
        self.assertAlmostEqual(metrics_10["avg_speed_mps"], 4.50, delta=0.1)
        self.assertAlmostEqual(metrics_30["avg_speed_mps"], metrics_10["avg_speed_mps"], delta=0.1)

    def test_invalid_and_edge_case_timestamps(self):
        """
        Task 7.6.11A Requirement 5 & 9:
        Verify that missing, duplicate, non-finite, out-of-order, or extreme timestamps
        are handled safely without division by zero, NaN propagation, or implausibly large speeds.
        """
        t0 = 1000.0

        # Subcase A: Duplicate timestamp (dt = 0.0) -> must not divide by zero
        tr_dup = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tr_dup.update_detections([[100, 100, 140, 180, 0.9]], det_seq=1, det_time=t0)
        tr_dup.update_detections([[105, 100, 145, 180, 0.9]], det_seq=2, det_time=t0)  # dt = 0.0
        m_dup = tr_dup.compute_flow_metrics()
        self.assertTrue(math.isfinite(m_dup["avg_speed_mps"]))
        self.assertGreaterEqual(m_dup["avg_speed_mps"], 0.0)

        # Subcase B: Out-of-order / negative timestamp (dt < 0) -> must not produce negative speed
        tr_neg = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tr_neg.update_detections([[100, 100, 140, 180, 0.9]], det_seq=1, det_time=t0)
        tr_neg.update_detections([[105, 100, 145, 180, 0.9]], det_seq=2, det_time=t0 - 1.0)  # dt = -1.0
        m_neg = tr_neg.compute_flow_metrics()
        self.assertTrue(math.isfinite(m_neg["avg_speed_mps"]))
        self.assertGreaterEqual(m_neg["avg_speed_mps"], 0.0)

        # Subcase C: Non-finite timestamps (NaN, Inf) -> must not crash or propagate NaN
        tr_nan = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tr_nan.update_detections([[100, 100, 140, 180, 0.9]], det_seq=1, det_time=float('nan'))
        tr_nan.update_detections([[105, 100, 145, 180, 0.9]], det_seq=2, det_time=float('inf'))
        m_nan = tr_nan.compute_flow_metrics()
        self.assertTrue(math.isfinite(m_nan["avg_speed_mps"]))

        # Subcase D: Missing timestamps (None, False) -> fallback to frame rate
        tr_none = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tr_none.update_detections([[100, 100, 140, 180, 0.9]], det_seq=1, det_time=None)
        tr_none.update_detections([[103, 100, 143, 180, 0.9]], det_seq=2, det_time=None)
        m_none = tr_none.compute_flow_metrics()
        self.assertTrue(math.isfinite(m_none["avg_speed_mps"]))
        self.assertAlmostEqual(m_none["avg_speed_mps"], 4.5, delta=0.5)

        # Subcase E: Tiny microsecond interval (dt = 1e-6) -> must not explode speed (> 30 m/s)
        tr_tiny = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tr_tiny.update_detections([[100, 100, 140, 180, 0.9]], det_seq=1, det_time=t0)
        tr_tiny.update_detections([[110, 100, 150, 180, 0.9]], det_seq=2, det_time=t0 + 1e-6)
        m_tiny = tr_tiny.compute_flow_metrics()
        self.assertLessEqual(m_tiny["avg_speed_mps"], 30.0, "Speed must be clamped to safe physiological maximum")

    def test_first_observation_and_tracker_reset_speed(self):
        """
        Task 7.6.11A Requirement 9:
        Verify speed metrics on initial observation (no prior position) and after tracker reset.
        """
        t0 = time.time()
        tracker = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)

        # First observation: track exists but has no prior displacement -> speed must be 0.0
        tracker.update_detections([[50, 50, 90, 120, 0.95]], det_seq=1, det_time=t0)
        m_first = tracker.compute_flow_metrics()
        self.assertEqual(m_first["active_track_count"], 1)
        self.assertEqual(m_first["avg_speed_mps"], 0.0, "First observation has no displacement; speed must be 0.0")

        # Second observation with motion: speed becomes positive
        tracker.update_detections([[55, 50, 95, 120, 0.95]], det_seq=2, det_time=t0 + 0.1)
        m_second = tracker.compute_flow_metrics()
        self.assertGreater(m_second["avg_speed_mps"], 0.0)

        # Tracker reset: state cleared, speed must be 0.0
        tracker.reset()
        m_reset = tracker.compute_flow_metrics()
        self.assertEqual(m_reset["active_track_count"], 0)
        self.assertEqual(m_reset["avg_speed_mps"], 0.0)

    def test_fca_attribute_m_consumption_boundary(self):
        """
        Trace how compute_flow_metrics() output lambda_out is consumed by fca_engine.py:
        - fca_engine.py line 233: fuzzy_m = round(max(0.0, min(1.0, avg_flow / 4.0)), 3)
        - alpha = 0.50 cut for crowd concept incidence (recommendations.py line 386).
        - Demonstrates that when flow is 1D (only H or only V), lambda_out = 1.0,
          so fuzzy_m = 1.0 / 4.0 = 0.250 (never reaches alpha = 0.50).
        - Demonstrates that when flow is 2D (both H and V), lambda_out = 2.0,
          so fuzzy_m = 2.0 / 4.0 = 0.500 (barely satisfies alpha = 0.50).
        - Demonstrates that under normalized Eq (2)-(4), fuzzy_m can NEVER exceed 0.500.
        """
        from app.ai.fca_engine import FCAEngine
        fca = FCAEngine()

        zones = [{"id": "z1", "name": "Zone A", "capacity": 500, "current_count": 250, "density": 50.0}]

        # Scenario 1: Only horizontal movement -> lambda_out = 1.0
        cams_1d = [{"id": "c1", "location": "Zone A", "flow_rate": 1.0, "speed_avg": 1.4}]
        _, ctx_1d = fca.build_fuzzy_crowd_context(zones, cams_1d, [])
        self.assertAlmostEqual(ctx_1d["Zone A"]["M"], 0.250, places=3)
        self.assertLess(ctx_1d["Zone A"]["M"], 0.50, "1D flow can never satisfy alpha=0.50 cut")

        # Scenario 2: 2D movement -> lambda_out = 2.0
        cams_2d = [{"id": "c1", "location": "Zone A", "flow_rate": 2.0, "speed_avg": 1.4}]
        _, ctx_2d = fca.build_fuzzy_crowd_context(zones, cams_2d, [])
        self.assertAlmostEqual(ctx_2d["Zone A"]["M"], 0.500, places=3)
        self.assertGreaterEqual(ctx_2d["Zone A"]["M"], 0.50, "2D flow reaches exactly alpha=0.50")

        # Scenario 3: Theoretical maximum from detector.py (lambda_out cannot exceed 2.0)
        # Even if 500 people are stampeding in 2D, lambda_out == 2.0 => M == 0.500
        cams_max = [{"id": "c1", "location": "Zone A", "flow_rate": 2.0, "speed_avg": 3.5}]
        _, ctx_max = fca.build_fuzzy_crowd_context(zones, cams_max, [])
        self.assertEqual(ctx_max["Zone A"]["M"], 0.500, "M cannot exceed 0.500 under Eq (2)-(4) normalization")

    # =========================================================================
    # TASK 7.6.11B: PHYSICAL OUTFLOW RATE, CAPACITY NORMALIZATION & SAFETY
    # =========================================================================

    def test_operational_outflow_uncalibrated_when_no_boundary(self):
        """
        Phase 3 & Phase 6 Test 9:
        Verify that when no boundary geometry is configured on a camera viewpoint,
        the tracker safely reports status="uncalibrated" and flow_pps=None,
        never guessing or fabricating a physical flow rate.
        """
        tracker = TemporalPersonTracker(max_prediction_frames=6, meters_per_pixel=0.05, fps=30.0)
        # Even with moving detections:
        t0 = 1000.0
        tracker.update_detections([[100, 100, 140, 180, 0.9]], det_seq=1, det_time=t0)
        tracker.update_detections([[120, 100, 160, 180, 0.9]], det_seq=2, det_time=t0 + 1.0)

        outflow = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0 + 1.0)
        self.assertEqual(outflow["status"], "uncalibrated")
        self.assertIsNone(outflow["flow_pps"])
        self.assertEqual(outflow["unit"], "people/second")
        self.assertIn("No passage boundary geometry configured", outflow["reason"])

        metrics = tracker.compute_flow_metrics()
        self.assertIn("operational_outflow", metrics)
        self.assertEqual(metrics["operational_outflow"]["status"], "uncalibrated")
        self.assertIsNone(metrics["operational_outflow"]["flow_pps"])

    def test_operational_outflow_single_crossing_rate(self):
        """
        Phase 6 Test 1:
        Verify that one valid boundary crossing produces the exact expected event count
        and people/second flow rate over the elapsed time window.
        """
        tracker = TemporalPersonTracker(max_prediction_frames=6, meters_per_pixel=0.05, fps=30.0)
        # Configure vertical boundary line at x=100 from y=0 to y=300
        tracker.set_boundary_line(p1=(100.0, 0.0), p2=(100.0, 300.0), direction="both")

        t0 = 100.0
        # Frame 1 at t=100.0s: Person 1 at centroid cx=50.0, cy=100.0 (box: 30, 80, 70, 120)
        tracker.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=t0)
        # Frame 2 at t=102.0s: Person 1 moves across boundary to cx=150.0, cy=100.0 (box: 130, 80, 170, 120)
        tracker.update_detections([[130, 80, 170, 120, 0.9]], det_seq=2, det_time=t0 + 2.0)

        outflow = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0 + 2.0)
        self.assertEqual(outflow["status"], "calibrated")
        self.assertEqual(outflow["crossing_count"], 1)
        self.assertEqual(outflow["unit"], "people/second")
        # 1 crossing over 2.0 seconds elapsed => 0.500 people/second
        self.assertAlmostEqual(outflow["flow_pps"], 0.500, places=3)

    def test_operational_outflow_multiple_distinct_crossers(self):
        """
        Phase 6 Test 2:
        Verify that multiple distinct people crossing a boundary produce the correct
        proportional physical outflow rate.
        """
        tracker = TemporalPersonTracker(max_prediction_frames=6, meters_per_pixel=0.05, fps=30.0)
        tracker.set_boundary_line(p1=(100.0, 0.0), p2=(100.0, 500.0), direction="both")

        t0 = 200.0
        # 4 distinct people on left side of line (cx=50) at t=200.0
        dets_frame1 = [
            [30, 40, 70, 80, 0.9],    # cy = 60
            [30, 140, 70, 180, 0.9],  # cy = 160
            [30, 240, 70, 280, 0.9],  # cy = 260
            [30, 340, 70, 380, 0.9]   # cy = 360
        ]
        tracker.update_detections(dets_frame1, det_seq=1, det_time=t0)

        # All 4 cross to right side of line (cx=150) at t=202.0 (elapsed = 2.0s)
        dets_frame2 = [
            [130, 40, 170, 80, 0.9],
            [130, 140, 170, 180, 0.9],
            [130, 240, 170, 280, 0.9],
            [130, 340, 170, 380, 0.9]
        ]
        tracker.update_detections(dets_frame2, det_seq=2, det_time=t0 + 2.0)

        outflow = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0 + 2.0)
        self.assertEqual(outflow["status"], "calibrated")
        self.assertEqual(outflow["crossing_count"], 4)
        # 4 distinct persons / 2.0s = 2.000 people/second
        self.assertAlmostEqual(outflow["flow_pps"], 2.000, places=3)

    def test_operational_outflow_lingering_deduplication(self):
        """
        Phase 6 Test 3:
        Verify that one person hovering or lingering near a boundary is not
        repeatedly counted across multiple oscillations during the cooldown period.
        """
        tracker = TemporalPersonTracker(max_prediction_frames=6, meters_per_pixel=0.05, fps=30.0)
        tracker.set_boundary_line(p1=(100.0, 0.0), p2=(100.0, 300.0), direction="both", cooldown_seconds=10.0)

        t0 = 300.0
        # Initial: cx=50
        tracker.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=t0)
        # Crosses to cx=150 at t=301.0 -> crossing event 1 registered
        tracker.update_detections([[130, 80, 170, 120, 0.9]], det_seq=2, det_time=t0 + 1.0)

        outflow1 = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0 + 1.0)
        self.assertEqual(outflow1["crossing_count"], 1)

        # Lingers and steps back across line to cx=90 at t=302.0 (cooldown active: dt = 1.0 < 10.0s)
        tracker.update_detections([[70, 80, 110, 120, 0.9]], det_seq=3, det_time=t0 + 2.0)
        # Steps forward across line again to cx=110 at t=303.0 (cooldown active: dt = 2.0 < 10.0s)
        tracker.update_detections([[90, 80, 130, 120, 0.9]], det_seq=4, det_time=t0 + 3.0)

        outflow2 = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0 + 3.0)
        # Lingering crossing must NOT increment distinct count
        self.assertEqual(outflow2["crossing_count"], 1, "Lingering track must not be repeatedly counted")

    def test_operational_outflow_directional_filtering(self):
        """
        Phase 6 Test 4:
        Verify that crossing direction is distinguished when forward or reverse
        directionality is configured.
        """
        # Directional test using check_segment_intersection directly
        p1, p2 = (100.0, 0.0), (100.0, 300.0)
        # Forward crossing from left to right (P -> Q)
        crossed_fwd, dir_fwd = check_segment_intersection(p1, p2, (50.0, 150.0), (150.0, 150.0))
        # Reverse crossing from right to left (Q -> P)
        crossed_rev, dir_rev = check_segment_intersection(p1, p2, (150.0, 150.0), (50.0, 150.0))

        self.assertTrue(crossed_fwd)
        self.assertTrue(crossed_rev)
        self.assertEqual(dir_fwd, -dir_rev, "Opposite crossings must have opposite direction signs")

        # Configured forward-only tracker
        tracker_fwd = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker_fwd.set_boundary_line(p1, p2, direction="forward" if dir_fwd > 0 else "reverse")

        t0 = 400.0
        # Track 1 moves in the selected matching direction
        tracker_fwd.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=t0)
        tracker_fwd.update_detections([[130, 80, 170, 120, 0.9]], det_seq=2, det_time=t0 + 1.0)
        out_match = tracker_fwd.get_operational_outflow(window_seconds=10.0, current_time=t0 + 1.0)
        self.assertEqual(out_match["crossing_count"], 1)

        # Configured opposite-only tracker
        tracker_opp = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker_opp.set_boundary_line(p1, p2, direction="reverse" if dir_fwd > 0 else "forward")
        tracker_opp.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=t0)
        tracker_opp.update_detections([[130, 80, 170, 120, 0.9]], det_seq=2, det_time=t0 + 1.0)
        out_nonmatch = tracker_opp.get_operational_outflow(window_seconds=10.0, current_time=t0 + 1.0)
        self.assertEqual(out_nonmatch["crossing_count"], 0, "Non-matching direction must not be counted")

    def test_operational_outflow_camera_isolation(self):
        """
        Phase 6 Test 5:
        Verify that separate camera tracker instances maintain isolated boundary
        crossing state without cross-camera event leakage.
        """
        tracker_cam1 = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker_cam2 = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)

        # Camera 1 has boundary line; Camera 2 has none
        tracker_cam1.set_boundary_line(p1=(100.0, 0.0), p2=(100.0, 300.0), direction="both")

        t0 = 500.0
        tracker_cam1.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=t0)
        tracker_cam1.update_detections([[130, 80, 170, 120, 0.9]], det_seq=2, det_time=t0 + 1.0)

        out1 = tracker_cam1.get_operational_outflow(window_seconds=10.0, current_time=t0 + 1.0)
        out2 = tracker_cam2.get_operational_outflow(window_seconds=10.0, current_time=t0 + 1.0)

        self.assertEqual(out1["crossing_count"], 1)
        self.assertEqual(out1["status"], "calibrated")
        self.assertEqual(out2["crossing_count"], 0)
        self.assertEqual(out2["status"], "uncalibrated", "Camera 2 without boundary must stay uncalibrated")

    def test_operational_outflow_tracker_reset_and_window_expiry(self):
        """
        Phase 6 Test 6:
        Verify that tracker reset purges all crossing events, and events older
        than the sliding window naturally expire.
        """
        tracker = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker.set_boundary_line(p1=(100.0, 0.0), p2=(100.0, 300.0), direction="both")

        t0 = 600.0
        tracker.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=t0)
        tracker.update_detections([[130, 80, 170, 120, 0.9]], det_seq=2, det_time=t0 + 1.0)

        out_active = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0 + 1.0)
        self.assertEqual(out_active["crossing_count"], 1)

        # Querying 15 seconds later with window=10.0s -> crossing from t=601.0 has expired
        out_expired = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0 + 16.0)
        self.assertEqual(out_expired["crossing_count"], 0)
        self.assertEqual(out_expired["flow_pps"], 0.0)

        # Re-cross and verify reset() clears state
        tracker.update_detections([[30, 80, 70, 120, 0.9]], det_seq=3, det_time=t0 + 20.0)
        tracker.update_detections([[130, 80, 170, 120, 0.9]], det_seq=4, det_time=t0 + 21.0)
        self.assertEqual(len(tracker.crossing_events), 1)

        tracker.reset()
        self.assertEqual(len(tracker.crossing_events), 0)
        self.assertIsNone(tracker.first_observation_time)
        out_reset = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0 + 22.0)
        self.assertEqual(out_reset["crossing_count"], 0)
        self.assertEqual(out_reset["flow_pps"], 0.0)

    def test_operational_outflow_timestamp_edge_cases(self):
        """
        Phase 6 Test 7:
        Verify that missing, duplicate, non-finite, and out-of-order timestamps
        do not crash the crossing detector or generate non-finite/negative rates.
        """
        tracker = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker.set_boundary_line(p1=(100.0, 0.0), p2=(100.0, 300.0), direction="both")

        t0 = 700.0
        # Duplicate timestamp (dt = 0)
        tracker.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=t0)
        tracker.update_detections([[130, 80, 170, 120, 0.9]], det_seq=2, det_time=t0)

        # Non-finite timestamp (NaN, Inf)
        tracker.update_detections([[130, 80, 170, 120, 0.9]], det_seq=3, det_time=float('nan'))
        tracker.update_detections([[130, 80, 170, 120, 0.9]], det_seq=4, det_time=float('inf'))

        # Missing timestamp (None)
        tracker.update_detections([[130, 80, 170, 120, 0.9]], det_seq=5, det_time=None)

        out = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0)
        self.assertTrue(math.isfinite(out["flow_pps"]))
        self.assertGreaterEqual(out["flow_pps"], 0.0)

    def test_operational_outflow_empty_window_no_fabricated_flow(self):
        """
        Phase 6 Test 8:
        Verify that an empty or stationary window with a configured boundary
        reports exactly 0.0 people/second, never fabricating flow.
        """
        tracker = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker.set_boundary_line(p1=(100.0, 0.0), p2=(100.0, 300.0), direction="both")

        # Stationary detections (no line crossing)
        t0 = 800.0
        tracker.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=t0)
        tracker.update_detections([[30, 80, 70, 120, 0.9]], det_seq=2, det_time=t0 + 1.0)

        outflow = tracker.get_operational_outflow(window_seconds=10.0, current_time=t0 + 1.0)
        self.assertEqual(outflow["status"], "calibrated")
        self.assertEqual(outflow["crossing_count"], 0)
        self.assertEqual(outflow["flow_pps"], 0.0, "Stationary person must report 0.0 people/second")

    def test_flow_utilization_verified_capacity(self):
        """
        Phase 6 Test 10:
        Verify that a verified capacity in people/second and measured flow rate
        produce the expected dimensionless operational utilization ratio.
        """
        # Scenario A: 50% capacity utilization
        res_normal = compute_flow_utilization(measured_outflow_pps=3.0, capacity_pps=6.0)
        self.assertEqual(res_normal["status"], "calibrated")
        self.assertTrue(res_normal["is_calibrated"])
        self.assertAlmostEqual(res_normal["flow_utilization"], 0.500, places=3)
        self.assertEqual(res_normal["capacity_pps"], 6.0)
        self.assertEqual(res_normal["measured_outflow_pps"], 3.0)

        # Scenario B: Over-capacity condition (150% utilization)
        res_over = compute_flow_utilization(measured_outflow_pps=7.5, capacity_pps=5.0)
        self.assertEqual(res_over["status"], "calibrated")
        self.assertTrue(res_over["is_calibrated"])
        self.assertAlmostEqual(res_over["flow_utilization"], 1.500, places=3)

    def test_flow_utilization_uncalibrated_or_invalid_inputs(self):
        """
        Phase 6 Test 11:
        Verify that zero, missing, negative, non-finite, or incompatible capacity
        inputs are safely handled without division by zero.
        """
        # Division by zero guard: capacity = 0.0
        res_zero = compute_flow_utilization(measured_outflow_pps=2.0, capacity_pps=0.0)
        self.assertEqual(res_zero["status"], "uncalibrated_capacity")
        self.assertIsNone(res_zero["flow_utilization"])
        self.assertFalse(res_zero["is_calibrated"])

        # Negative capacity guard
        res_neg_cap = compute_flow_utilization(measured_outflow_pps=2.0, capacity_pps=-5.0)
        self.assertEqual(res_neg_cap["status"], "uncalibrated_capacity")
        self.assertIsNone(res_neg_cap["flow_utilization"])

        # Missing / None capacity guard
        res_none_cap = compute_flow_utilization(measured_outflow_pps=2.0, capacity_pps=None)
        self.assertEqual(res_none_cap["status"], "uncalibrated_capacity")
        self.assertIsNone(res_none_cap["flow_utilization"])

        # Missing / None flow guard
        res_none_flow = compute_flow_utilization(measured_outflow_pps=None, capacity_pps=5.0)
        self.assertEqual(res_none_flow["status"], "uncalibrated_flow")
        self.assertIsNone(res_none_flow["flow_utilization"])

        # Negative flow guard
        res_neg_flow = compute_flow_utilization(measured_outflow_pps=-1.0, capacity_pps=5.0)
        self.assertEqual(res_neg_flow["status"], "uncalibrated_flow")
        self.assertIsNone(res_neg_flow["flow_utilization"])

        # Non-finite inputs guard (NaN, Inf)
        res_nan = compute_flow_utilization(measured_outflow_pps=float('nan'), capacity_pps=5.0)
        self.assertEqual(res_nan["status"], "uncalibrated_flow")
        self.assertIsNone(res_nan["flow_utilization"])

        res_inf = compute_flow_utilization(measured_outflow_pps=2.0, capacity_pps=float('inf'))
        self.assertEqual(res_inf["status"], "uncalibrated_capacity")
        self.assertIsNone(res_inf["flow_utilization"])

    def test_flow_utilization_not_mislabeled_as_physical_flow(self):
        """
        Phase 6 Test 12 & 18:
        Verify that utilization ratio is dimensionless and not mislabeled as
        people/second, and that research lambda_out is not mixed with physical flow.
        """
        util = compute_flow_utilization(measured_outflow_pps=2.5, capacity_pps=5.0)
        self.assertNotIn("people/second", util.get("unit", ""))
        self.assertEqual(util["flow_utilization"], 0.500)

        # Confirm research lambda_out is dimensionless and kept separate in detector metrics
        tracker = TemporalPersonTracker()
        tracker.set_boundary_line((100.0, 0.0), (100.0, 300.0))
        tracker.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=100.0)
        tracker.update_detections([[130, 80, 170, 120, 0.9]], det_seq=2, det_time=102.0)
        metrics = tracker.compute_flow_metrics()

        # Research metric lambda_out exists alongside operational_outflow
        self.assertIn("lambda_out", metrics)
        self.assertIn("operational_outflow", metrics)
        self.assertEqual(metrics["operational_outflow"]["unit"], "people/second")
        # Research lambda_out is a float <= 2.0 (Eq 4)
        self.assertIsInstance(metrics["lambda_out"], float)
        self.assertIsInstance(metrics["operational_outflow"]["flow_pps"], float)

    def test_fca_research_parameters_and_algorithms_unmodified(self):
        """
        Phase 6 Test 14, 15, 16, 17:
        Verify that Galois closure, Algorithm 1 (check_crowd, extract_crowded_areas),
        Algorithm 2 (generate_crowd_prevention_plan), alpha=0.50, and threshold T=0.70
        remain completely intact and functional.
        """
        from app.ai.fca_engine import FCAEngine
        fca = FCAEngine()

        # 1. Verify Algorithm 1: check_crowd calculation
        kc_area = {"D": 0.95, "P": 0.85, "M": 0.90, "E": 0.90, "S": 0.80}
        intent = ["D", "M", "P", "S"]
        score = fca.check_crowd(kc_area, intent)
        self.assertAlmostEqual(score, 0.920, places=3)
        self.assertGreater(score, 0.70, "Algorithm 1 threshold T = 0.70 satisfied")

        # 2. Verify Algorithm 1 extraction
        Lc = [
            {"id": "c1", "intent": ["D", "M", "P", "S"], "extent": ["A1"]},
            {"id": "c2", "intent": [], "extent": ["A1", "A2"]}
        ]
        Kc = {
            "A1": {"D": 0.95, "P": 0.85, "M": 0.90, "E": 0.90, "S": 0.80},
            "A2": {"D": 0.20, "P": 0.10, "M": 0.15, "E": 0.00, "S": 0.10}
        }
        CA = fca.extract_crowded_areas(Lc, Kc, threshold=0.70)
        self.assertEqual(len(CA), 1)
        self.assertEqual(CA[0]["area"], "A1")
        self.assertEqual(CA[0]["concept_id"], "c1")

        # 3. Verify Algorithm 2: generate_crowd_prevention_plan
        La = [
            {"id": "c1", "extent": ["A1", "A2"], "intent": ["A3"]}
        ]
        zone_states = {
            "A1": {"capacity": 1000, "density": 88.0, "current_count": 880},
            "A2": {"capacity": 800, "density": 40.0, "current_count": 320},
            "A3": {"capacity": 1500, "density": 20.0, "current_count": 300}
        }
        plan_res = fca.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)
        self.assertEqual(plan_res["total_crowded_areas"], 1)
        self.assertEqual(plan_res["resolved_count"], 1)
        self.assertEqual(len(plan_res["plans"]), 1)
        self.assertIn("A1", plan_res["plans"][0]["crowded_sources"])
        self.assertIn("A3", plan_res["plans"][0]["recommended_destinations"])

    # =========================================================================
    # TASK 7.6.11C: FINAL INTEGRATION & ACCEPTANCE AUDIT TESTS
    # =========================================================================

    def test_operational_outflow_repeat_crossing_after_cooldown_retained(self):
        """
        Task 7.6.11C Item 2:
        Ensure legitimate repeat crossings after the cooldown window are not lost.
        Track 1 crosses at t=100.0s, and then legitimately crosses again at t=115.0s
        (dt = 15s >= 10s cooldown). Both crossing events must be retained.
        """
        tracker = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker.set_boundary_line((100.0, 0.0), (100.0, 300.0), direction="both", cooldown_seconds=10.0)

        # Crossing 1 at t=100.0 to 102.0 (cx: 50 -> 140, crosses boundary x=100)
        tracker.update_detections([[30, 80, 70, 120, 0.9]], det_seq=1, det_time=100.0)
        tracker.update_detections([[120, 80, 160, 120, 0.9]], det_seq=2, det_time=102.0)
        self.assertEqual(len(tracker.crossing_events), 1)

        # Track steps slightly to cx=145 at t=105.0 (stays on right side)
        tracker.update_detections([[125, 80, 165, 120, 0.9]], det_seq=3, det_time=105.0)

        # Track returns to left side (cx: 145 -> 60) at t=115.0 (dt = 13s >= 10s cooldown)
        # Displacement |145 - 60| = 85 px <= max_distance (120 px)
        # This is a legitimate repeat crossing in the reverse direction!
        tracker.update_detections([[40, 80, 80, 120, 0.9]], det_seq=4, det_time=115.0)
        self.assertEqual(len(tracker.crossing_events), 2, "Repeat crossing after cooldown must be recorded")

        outflow = tracker.get_operational_outflow(window_seconds=30.0, current_time=115.0)
        self.assertEqual(outflow["crossing_count"], 2)
        self.assertEqual(outflow["distinct_track_count"], 1)
        self.assertAlmostEqual(outflow["flow_pps"], round(2 / 15.0, 3), places=3)

    def test_operational_outflow_opposite_direction_tracks_independent(self):
        """
        Task 7.6.11C Item 2:
        Verify that separate tracks crossing in opposite directions at nearly the
        same time have independent cooldown states and neither is lost.
        """
        tracker = TemporalPersonTracker(meters_per_pixel=0.05, fps=30.0)
        tracker.set_boundary_line((100.0, 0.0), (100.0, 500.0), direction="both", cooldown_seconds=10.0)

        # Frame 1: Person 1 at cx=50 (left), Person 2 at cx=150 (right)
        dets_f1 = [
            [30, 80, 70, 120, 0.9],    # Person 1 (left)
            [130, 280, 170, 320, 0.9]  # Person 2 (right)
        ]
        tracker.update_detections(dets_f1, det_seq=1, det_time=200.0)

        # Frame 2 at t=201.0s:
        # Person 1 crosses to cx=150 (forward crossing)
        # Person 2 crosses to cx=50 (reverse crossing)
        dets_f2 = [
            [130, 80, 170, 120, 0.9],  # Person 1 crossed left -> right
            [30, 280, 70, 320, 0.9]    # Person 2 crossed right -> left
        ]
        tracker.update_detections(dets_f2, det_seq=2, det_time=201.0)

        self.assertEqual(len(tracker.crossing_events), 2, "Both opposite-direction crossings must be recorded")
        outflow = tracker.get_operational_outflow(window_seconds=10.0, current_time=201.0)
        self.assertEqual(outflow["crossing_count"], 2)
        self.assertEqual(outflow["distinct_track_count"], 2)

    def test_analytics_router_exposes_operational_outflow(self):
        """
        Task 7.6.11C Item 1:
        Verify that get_crowd_analysis in app.routers.analytics exposes
        operational_outflow, outflow_status, and safe exit_rate_per_min.
        """
        from app.routers.analytics import get_crowd_analysis
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        res = get_crowd_analysis(camera_id=None, event_id=None, auth=None, db=mock_db)

        self.assertIn("operational_outflow", res)
        self.assertIn("outflow_status", res)
        self.assertIn("exit_rate_per_min", res)
        self.assertIn("flow_decomposition", res)

        # When uncalibrated, exit_rate_per_min must be None (never a fabricated number)
        self.assertIsNone(res["exit_rate_per_min"])
        self.assertEqual(res["outflow_status"], "Outflow unavailable — boundary calibration required")
        self.assertEqual(res["operational_outflow"]["status"], "uncalibrated")
        self.assertIsNone(res["operational_outflow"]["flow_pps"])


if __name__ == "__main__":
    unittest.main()



from typing import List, Tuple, Dict, Any, Optional

class MultiCameraAggregator:
    """
    Multi-sensor spatial crowd aggregator.
    
    CRITICAL ARCHITECTURAL DISTINCTION:
    - Camera-level detected count: detected persons on a single camera stream.
    - Aggregated detections / Sensor-derived count: arithmetic sum of sensor detections.
    - Estimated zone count: occupancy adjusted for camera field-of-view (FOV) overlap.
    - Estimated area count: aggregated across all monitored zones in the venue.
    - Unique-person count: NOT claimed without cross-camera ReID (identity tracking).
    """

    @staticmethod
    def aggregate_zone_detections(
        camera_counts: List[int],
        overlap_ratio: float = 0.15
    ) -> Dict[str, Any]:
        """
        Aggregates multiple camera streams within a physical zone.
        Applies a FOV overlap discount factor when multiple cameras cover the same zone.
        """
        valid_counts = [int(c) for c in camera_counts if c is not None and c >= 0]
        num_cams = len(valid_counts)
        raw_detections = sum(valid_counts)

        if num_cams <= 1 or raw_detections == 0:
            estimated_occupancy = raw_detections
            discount_pct = 0.0
        else:
            # Overlap discount formula: accounts for field-of-view intersection among N cameras
            # If 2 cameras have 15% overlap, discount is 15% / 2 * 1 = 7.5%
            effective_overlap = min(0.60, max(0.0, overlap_ratio * ((num_cams - 1) / float(num_cams))))
            estimated_occupancy = int(round(raw_detections * (1.0 - effective_overlap)))
            discount_pct = round(effective_overlap * 100.0, 1)

        return {
            "camera_detections": valid_counts,
            "sensor_derived_count": raw_detections,
            "aggregated_detections": raw_detections,
            "estimated_zone_count": max(0, estimated_occupancy),
            "cameras_reporting": num_cams,
            "fov_overlap_discount_pct": discount_pct,
            "has_unique_tracking": False,
            "tracking_mode": "sensor_derived_with_fov_overlap_discount",
            "disclaimer": "Cross-camera identity tracking (ReID) is not enabled; count represents sensor-derived aggregated detections with overlap estimation."
        }

    @staticmethod
    def aggregate_area_detections(
        zone_estimates: List[int],
        venue_capacity: int = 10000
    ) -> Dict[str, Any]:
        """Aggregates all zone-level estimates into venue-wide occupancy."""
        total_estimated = sum(max(0, z) for z in zone_estimates if z is not None)
        occupancy_pct = (total_estimated / float(venue_capacity) * 100.0) if venue_capacity > 0 else 0.0

        return {
            "total_sensor_derived_count": total_estimated,
            "estimated_area_count": total_estimated,
            "total_venue_capacity": venue_capacity,
            "average_occupancy_pct": round(min(100.0, max(0.0, occupancy_pct)), 1),
            "has_unique_tracking": False,
            "disclaimer": "Venue count derived from multi-sensor zone aggregations; does not claim cross-camera unique identity tracking."
        }


class CrowdDensityEvaluator:
    @staticmethod
    def calculate_density(count: int, capacity: int) -> float:
        """
        Calculates occupancy density percentage: (Detected People / Configured Capacity) * 100
        Explicit formula without arbitrary multipliers.
        Safely handles non-positive capacity and preserves genuine overcapacity (>100%).
        """
        if capacity is None or capacity <= 0:
            return 0.0
        safe_count = max(0, int(count)) if count is not None else 0
        density_pct = (safe_count / float(capacity)) * 100.0
        return round(max(0.0, density_pct), 1)

    @staticmethod
    def calculate_zone_density(zone_count: int, zone_capacity: int) -> float:
        """Calculate density for an entire zone with configured zone capacity."""
        return CrowdDensityEvaluator.calculate_density(zone_count, zone_capacity)

    @staticmethod
    def calculate_area_density(total_count: int, venue_capacity: int) -> float:
        """Calculate density for entire monitored area / venue."""
        return CrowdDensityEvaluator.calculate_density(total_count, venue_capacity)

    @staticmethod
    def classify_risk(density_pct: float, restricted_breach: bool = False, exit_blocked: bool = False) -> str:
        """Transparent risk classification based on density, restricted area violations, and exits."""
        if density_pct >= 90.0 or (density_pct >= 75.0 and exit_blocked):
            return "critical"
        elif density_pct >= 75.0 or (density_pct >= 60.0 and restricted_breach):
            return "high"
        elif density_pct >= 45.0:
            return "medium"
        else:
            return "low"

    @staticmethod
    def evaluate_health(status: str, density_pct: float) -> str:
        if status == "offline":
            return "red"
        if density_pct >= 90.0:
            return "red"
        elif density_pct >= 75.0:
            return "yellow"
        else:
            return "green"

    @staticmethod
    def analyze_density_trend(history: List[float]) -> Tuple[str, float]:
        """
        Legacy tuple return for backward compatibility: (trend_category, growth_rate)
        """
        detailed = CrowdDensityEvaluator.calculate_detailed_trend(history)
        return detailed["density_trend"], detailed["growth_rate"]

    @staticmethod
    def calculate_detailed_trend(history: List[float]) -> Dict[str, Any]:
        """
        Empirical Crowd Accumulation & Trend Analysis from actual stored observations.
        Accurately labeled: 'Trend Analysis' (NOT claiming future predictive extrapolation).
        """
        if not history or len(history) < 2:
            return {
                "density_trend": "stable",
                "growth_rate": 0.0,
                "sustained_increase": False,
                "crowd_accumulation": 0.0,
                "congestion_development": "nominal",
                "risk_trend": "stable",
                "recent_trajectory": list(history) if history else [],
                "analysis_type": "Trend Analysis (Observation-Derived)"
            }

        first_val = history[0]
        last_val = history[-1]
        delta = last_val - first_val
        num_intervals = max(1, len(history) - 1)
        growth_rate = round(delta / float(num_intervals), 2)

        # Check sustained increase across consecutive observations
        consecutive_increases = 0
        for i in range(1, len(history)):
            if history[i] > history[i - 1]:
                consecutive_increases += 1
            else:
                consecutive_increases = 0
        sustained_increase = (consecutive_increases >= 3)

        # Trend categorization
        if delta > 15.0 and growth_rate >= 2.0:
            trend_cat = "surge"
        elif delta > 5.0 or sustained_increase:
            trend_cat = "increasing"
        elif delta < -5.0:
            trend_cat = "decreasing"
        else:
            trend_cat = "stable"

        # Congestion development assessment
        if last_val >= 85.0 and growth_rate > 0:
            congestion_dev = "critical_bottleneck"
            risk_trend = "escalating"
        elif last_val >= 70.0 and growth_rate > 0.5:
            congestion_dev = "congestion_forming"
            risk_trend = "escalating"
        elif delta < -3.0:
            congestion_dev = "clearing"
            risk_trend = "de-escalating"
        else:
            congestion_dev = "nominal"
            risk_trend = "stable"

        return {
            "density_trend": trend_cat,
            "growth_rate": growth_rate,
            "sustained_increase": sustained_increase,
            "crowd_accumulation": round(delta, 1),
            "congestion_development": congestion_dev,
            "risk_trend": risk_trend,
            "recent_trajectory": list(history),
            "analysis_type": "Trend Analysis (Observation-Derived)"
        }

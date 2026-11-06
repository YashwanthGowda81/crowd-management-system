from typing import List, Dict, Tuple, Optional

class RiskEngine:
    """
    Transparent Area-Wide Crowd Risk Engine.
    Combines Camera-level metrics, Zone-level metrics, Exit availability,
    Restricted area violations, Active Alerts, and Emergency status into
    calibrated risk scores and transparent operational risk levels.
    """

    @staticmethod
    def calculate_camera_risk(
        density_pct: float, 
        occupancy_pct: float, 
        restricted_violations: int = 0,
        flow_rate: float = 0.0
    ) -> Tuple[int, str, str]:
        """
        Calculates individual camera risk score (0-100), risk level, and explanation reason.
        Rules:
        - Density weighted at 50%
        - Occupancy weighted at 35%
        - Stagnation (low flow with high density) adds up to 10 points
        - Restricted area violations add 15 points each
        """
        stagnation_factor = 10 if (density_pct >= 70.0 and flow_rate <= 1.0) else 0
        base_score = int(density_pct * 0.5 + occupancy_pct * 0.35) + (restricted_violations * 15) + stagnation_factor
        risk_score = max(0, min(100, base_score))

        if risk_score >= 85:
            risk_level = "CRITICAL"
            reason = "Extreme crowd density with elevated stampede and crushing hazard"
        elif risk_score >= 70:
            risk_level = "HIGH"
            reason = "High occupancy with rapid crowd accumulation and flow constraints"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
            reason = "Moderate crowd movement and acceptable occupancy distribution"
        else:
            risk_level = "LOW"
            reason = "Safe crowd density and optimal space distribution"

        return risk_score, risk_level, reason

    @staticmethod
    def calculate_zone_risk(
        zone_density: float,
        camera_risks: List[str],
        unresolved_alerts_count: int = 0,
        exit_blocked: bool = False
    ) -> Tuple[int, str, str]:
        """
        Calculates Zone-level risk combining all cameras covering that zone,
        exit availability, and zone alerts.
        """
        # Critical camera weight
        crit_cams = sum(1 for r in camera_risks if str(r).upper() == "CRITICAL")
        high_cams = sum(1 for r in camera_risks if str(r).upper() == "HIGH")

        score = int(zone_density * 0.6) + (crit_cams * 18) + (high_cams * 8) + (unresolved_alerts_count * 8)
        if exit_blocked:
            score += 25

        score = max(0, min(100, score))

        if score >= 85 or exit_blocked and zone_density >= 70:
            level = "CRITICAL"
            reason = "Zone bottleneck: Critical crowd pressure or blocked egress route."
        elif score >= 65:
            level = "HIGH"
            reason = "Elevated zone occupancy; queue marshaling recommended."
        elif score >= 40:
            level = "MEDIUM"
            reason = "Steady zone circulation within standard capacity."
        else:
            level = "LOW"
            reason = "Normal flow through zone."

        return score, level, reason

    @staticmethod
    def evaluate_system_risk(
        cameras: List[Dict], 
        alerts: List[Dict],
        zones: Optional[List[Dict]] = None,
        zone_dicts: Optional[List[Dict]] = None,
        has_active_emergency: bool = False,
        trend_analysis: Optional[Dict] = None,
        crowd_threshold: float = 85.0,
        **kwargs
    ) -> Tuple[int, str]:
        """
        Evaluates Area-wide / Venue-wide crowd risk score (0-100%) and risk category.
        Rules:
        - If active emergency is triggered -> CRITICAL (95)
        - Zone criticalities propagate upward to venue level
        - Average density + weighted critical sensors + unresolved alerts
        - Empirical trend and bottleneck accumulation
        """
        if has_active_emergency:
            return 95, "CRITICAL"

        effective_zones = zones if zones is not None else (zone_dicts or [])

        if not cameras and not effective_zones:
            return 10, "LOW"

        # Calculate average density from active cameras
        active_cams = [c for c in cameras if c.get("density") is not None]
        avg_density = sum(c.get("density", 0) for c in active_cams) / max(1, len(active_cams)) if active_cams else 0.0

        critical_cams = sum(1 for c in cameras if str(c.get("risk", "")).lower() == "critical")
        high_cams = sum(1 for c in cameras if str(c.get("risk", "")).lower() == "high")

        critical_zones = sum(1 for z in effective_zones if str(z.get("risk_level", "")).lower() == "critical")
        high_zones = sum(1 for z in effective_zones if str(z.get("risk_level", "")).lower() == "high")

        unresolved_critical_alerts = sum(
            1 for a in alerts 
            if a.get("level") == "critical" and not a.get("resolved")
        )
        unresolved_warning_alerts = sum(
            1 for a in alerts 
            if a.get("level") in ["warning", "high"] and not a.get("resolved")
        )

        trend_factor = 0
        if trend_analysis:
            if trend_analysis.get("density_trend") == "surge":
                trend_factor += 10
            if trend_analysis.get("congestion_development") == "critical_bottleneck":
                trend_factor += 10
            elif trend_analysis.get("congestion_development") == "congestion_forming":
                trend_factor += 5

        base_score = (
            int(avg_density * 0.40) 
            + (critical_cams * 12) 
            + (high_cams * 6)
            + (critical_zones * 15)
            + (high_zones * 8)
            + (unresolved_critical_alerts * 12)
            + (unresolved_warning_alerts * 4)
            + trend_factor
        )
        risk_score = max(5, min(99, base_score))

        if risk_score >= 80 or critical_zones > 0 or critical_cams >= 2:
            category = "CRITICAL"
        elif risk_score >= 60 or high_cams >= 2 or high_zones >= 2:
            category = "HIGH"
        elif risk_score >= 35 or avg_density >= 45.0:
            category = "MEDIUM"
        else:
            category = "LOW"

        return risk_score, category

risk_engine = RiskEngine()

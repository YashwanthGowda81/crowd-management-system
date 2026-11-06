import time
import math
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Body, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func

_reservation_lock = threading.Lock()

from app.database import get_db
from app.models import (
    CameraModel,
    AlertModel,
    RecommendationModel,
    CapacityReservationModel,
    ZoneModel,
    EventModel,
    User,
    ZoneConnectionModel,
    CrowdAnalyticsModel
)
from app.ai.stream_processor import stream_manager
from app.schemas import (
    RecommendationResponse,
    CrowdedAreaResult,
    PreventionPlanItem,
    PreventionPlanResponse,
    ResearchLatticeResponse,
    FCALatticeResponse,
    FCANode,
    FCALink,
    CapacityReservationResponse,
    ReservationCompleteRequest,
    ReservationCancelRequest,
    ReservationReconcileRequest
)
from app.ai.fca_engine import fca_solver, CROWD_ATTRIBUTES
from app.auth_utils import decode_access_token

router = APIRouter(prefix="/recommendations", tags=["Decision Support"])
security = HTTPBearer(auto_error=False)

def get_current_user_from_auth(auth: Optional[HTTPAuthorizationCredentials], db: Session) -> Optional[User]:
    if not auth or not auth.credentials:
        return None
    try:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("sub"):
            return db.query(User).filter(User.email == payload["sub"]).first()
    except Exception:
        pass
    return None

# Documented freshness limits based on 30 FPS video interval (~33ms) and analytics snapshot cadence (10 frames)
LIVE_WORKER_FRESHNESS_LIMIT_SEC = 15.0
PERSISTED_ANALYTICS_FRESHNESS_LIMIT_SEC = 60.0


def fetch_camera_movement_telemetry(
    camera_id: str,
    target_event_id: Optional[str] = None,
    db: Optional[Session] = None,
    live_freshness_limit: float = LIVE_WORKER_FRESHNESS_LIMIT_SEC,
    persisted_freshness_limit: float = PERSISTED_ANALYTICS_FRESHNESS_LIMIT_SEC
) -> Optional[Dict[str, Any]]:
    """
    Retrieves the freshest valid movement flow and physical speed telemetry for a camera.
    Prioritizes active in-memory CameraStreamWorker when running and fresh (<= 15s).
    Falls back to latest persisted CrowdAnalyticsModel record if fresh (<= 60s).
    Enforces strict event-isolation and finite bounds checking.
    Returns None if no fresh, valid telemetry exists (never fabricates default measurements).
    """
    now_t = time.time()
    now_utc = datetime.utcnow()

    # 1. Attempt retrieval from active in-memory Stream Worker
    worker = stream_manager.workers.get(str(camera_id))
    if worker is not None:
        worker_event = getattr(worker, "event_id", None)
        # Verify event isolation
        if target_event_id is None or worker_event == target_event_id:
            # Check worker operational status
            is_running = getattr(worker, "is_running", False)
            is_paused = getattr(worker, "is_paused", False)
            playback_status = getattr(worker, "playback_status", "")
            if is_running and not is_paused and playback_status != "stopped":
                last_obs = getattr(worker, "last_observation_timestamp", 0.0)
                # Freshness verification: must be within live window
                if 0.0 < last_obs and (now_t - last_obs) <= live_freshness_limit:
                    flow_val = getattr(worker, "last_flow_rate", None)
                    speed_val = getattr(worker, "last_speed_avg", None)

                    # Validate finite numeric bounds
                    valid_flow = (
                        flow_val is not None
                        and not isinstance(flow_val, bool)
                        and isinstance(flow_val, (int, float))
                        and math.isfinite(flow_val)
                        and 0.0 <= flow_val <= 10.0
                    )
                    valid_speed = (
                        speed_val is not None
                        and not isinstance(speed_val, bool)
                        and isinstance(speed_val, (int, float))
                        and math.isfinite(speed_val)
                        and 0.0 <= speed_val <= 20.0
                    )
                    if valid_flow and valid_speed:
                        return {
                            "flow_rate": round(float(flow_val), 3),
                            "speed_avg": round(float(speed_val), 2),
                            "source": "worker",
                            "age_seconds": round(now_t - last_obs, 2)
                        }

    # 2. Fallback to latest persisted CrowdAnalyticsModel record in DB
    if db is not None:
        q = db.query(CrowdAnalyticsModel).filter(CrowdAnalyticsModel.camera_id == str(camera_id))
        if target_event_id:
            q = q.filter(CrowdAnalyticsModel.event_id == target_event_id)
        latest_record = q.order_by(CrowdAnalyticsModel.timestamp.desc()).first()

        if latest_record is not None:
            # Event isolation check
            if target_event_id is None or latest_record.event_id == target_event_id:
                rec_ts = latest_record.timestamp
                if isinstance(rec_ts, datetime):
                    age_seconds = (now_utc - rec_ts).total_seconds()
                    # Freshness verification: must be within persisted window (<= 60s)
                    if -5.0 <= age_seconds <= persisted_freshness_limit:
                        flow_val = latest_record.flow_rate
                        speed_val = latest_record.speed_avg
                        valid_flow = (
                            flow_val is not None
                            and not isinstance(flow_val, bool)
                            and isinstance(flow_val, (int, float))
                            and math.isfinite(flow_val)
                            and 0.0 <= flow_val <= 10.0
                        )
                        valid_speed = (
                            speed_val is not None
                            and not isinstance(speed_val, bool)
                            and isinstance(speed_val, (int, float))
                            and math.isfinite(speed_val)
                            and 0.0 <= speed_val <= 20.0
                        )
                        if valid_flow and valid_speed:
                            return {
                                "flow_rate": round(float(flow_val), 3),
                                "speed_avg": round(float(speed_val), 2),
                                "source": "database",
                                "age_seconds": round(max(0.0, age_seconds), 2)
                            }

    # 3. No valid or fresh measured telemetry available
    return None


def get_cameras_for_zone(zone: ZoneModel, cameras: List[CameraModel]) -> List[CameraModel]:
    """Finds all camera records configured to cover a specific zone."""
    z_id = str(zone.id or "").strip()
    z_name = str(zone.name or "").strip().lower()
    z_code = str(zone.code or "").strip().lower() if zone.code else ""

    matched = []
    for c in cameras:
        # Event isolation check
        if zone.event_id and c.event_id and str(c.event_id) != str(zone.event_id):
            continue

        c_zone_id = str(c.zone_id or "").strip()
        c_loc = str(c.location or "").strip().lower()
        c_name = str(c.name or "").strip().lower()

        # Priority 1: explicit zone_id
        if c_zone_id:
            if c_zone_id == z_id or c_zone_id.lower() == z_name or (z_code and c_zone_id.lower() == z_code):
                matched.append(c)
                continue

        # Priority 2: location / name match
        loc_matched = False
        if c_loc:
            if (z_name and z_name in c_loc) or (z_code and z_code in c_loc):
                loc_matched = True
            elif len(c_loc) >= 3 and z_name and c_loc in z_name:
                loc_matched = True

        name_matched = False
        if c_name:
            if (z_name and z_name in c_name) or (z_code and z_code in c_name):
                name_matched = True
            elif len(c_name) >= 3 and z_name and c_name in z_name:
                name_matched = True

        if loc_matched or name_matched:
            matched.append(c)

    return matched


LIVE_WORKER_FRESHNESS_LIMIT_SEC = 15.0
PERSISTED_FRAME_FRESHNESS_LIMIT_SEC = 15.0  # Unified 15-second freshness limit (Task 7.6.4)
MAX_ALLOWED_CLOCK_SKEW_SEC = 5.0


def check_camera_monitoring_health(
    camera: CameraModel,
    target_event_id: Optional[str] = None,
    db: Optional[Session] = None,
    live_freshness_limit: float = LIVE_WORKER_FRESHNESS_LIMIT_SEC,
    persisted_freshness_limit: float = PERSISTED_FRAME_FRESHNESS_LIMIT_SEC
) -> Tuple[bool, str]:
    """
    Evaluates monitoring and frame-freshness health for an individual camera (Task 7.6.1 & 7.6.4).
    A camera is healthy only when enabled, online, analyzing/playing, and actively
    producing fresh frame observations (<= 15.0s).
    Distinguishes genuine 0-person observations from missing/stale telemetry.
    Never relies on timer-generated CrowdAnalyticsModel rows for frame freshness.
    """
    cam_id_str = str(camera.id or "")
    cam_label = camera.name or cam_id_str

    if not camera.enabled:
        return False, f"Camera '{cam_label}' is disabled"

    if camera.status != "online":
        return False, f"Camera '{cam_label}' status is '{camera.status}' (expected 'online')"

    if camera.playback_status not in ("analyzing", "playing"):
        return False, f"Camera '{cam_label}' playback_status is '{camera.playback_status}' (expected 'analyzing' or 'playing')"

    if target_event_id and camera.event_id and camera.event_id != target_event_id:
        return False, f"Camera '{cam_label}' belongs to event '{camera.event_id}' (expected '{target_event_id}')"

    now_t = time.time()

    # 1. Check active stream worker in memory (if running on ingestion owner process)
    worker = stream_manager.workers.get(cam_id_str)
    if worker is not None:
        if not getattr(worker, "is_running", False):
            return False, f"Stream worker for camera '{cam_label}' is stopped"
        if getattr(worker, "is_paused", False):
            return False, f"Stream worker for camera '{cam_label}' is paused"
        if getattr(worker, "playback_status", "") in ("error", "stopped"):
            return False, f"Stream worker for camera '{cam_label}' playback status is '{worker.playback_status}'"

        last_obs = getattr(worker, "last_observation_timestamp", 0.0)
        frame_seq = getattr(worker, "frame_seq", 0)
        if last_obs <= 0.0 or frame_seq <= 0:
            return False, f"Camera '{cam_label}' has not received any valid frame observations"

        age = now_t - last_obs
        if age < -MAX_ALLOWED_CLOCK_SKEW_SEC:
            return False, f"Camera '{cam_label}' observation timestamp is in the future ({age:.1f}s)"
        if age > live_freshness_limit:
            return False, f"Camera '{cam_label}' stream telemetry is stale ({age:.1f}s > {live_freshness_limit}s)"

        return True, "healthy_live"

    # 2. Persisted trustworthy frame heartbeat on CameraModel (used by API worker processes)
    frame_ts = getattr(camera, "last_frame_timestamp", None)
    frame_seq = getattr(camera, "last_frame_seq", 0) or 0

    if frame_ts is None or frame_ts <= 0.0 or frame_seq <= 0:
        return False, f"No trustworthy frame observations recorded for camera '{cam_label}'"

    age_persisted = now_t - float(frame_ts)
    if age_persisted < -MAX_ALLOWED_CLOCK_SKEW_SEC:
        return False, f"Camera '{cam_label}' frame timestamp is in the future ({age_persisted:.1f}s)"
    if age_persisted > persisted_freshness_limit:
        return False, f"Camera '{cam_label}' persisted frame health is stale ({age_persisted:.1f}s > {persisted_freshness_limit}s)"

    return True, "healthy_persisted_frame"


def evaluate_zone_monitoring_health(
    zone: ZoneModel,
    cameras: List[CameraModel],
    target_event_id: Optional[str] = None,
    db: Optional[Session] = None,
    live_freshness_limit: float = LIVE_WORKER_FRESHNESS_LIMIT_SEC,
    persisted_freshness_limit: float = PERSISTED_FRAME_FRESHNESS_LIMIT_SEC
) -> Tuple[bool, str]:
    """
    Evaluates whether a zone has sufficient, reliable, and fresh camera monitoring (Task 7.6.1 & 7.6.4).
    Rules:
    1. A zone with 0 assigned cameras is unmonitored (fail closed).
    2. All cameras covering the zone must be healthy and fresh (<= 15.0s).
    3. Partial failure (any camera offline or stale) marks the entire zone unmonitored.
    """
    zone_cams = get_cameras_for_zone(zone, cameras)
    z_name = zone.name or zone.id

    if not zone_cams:
        return False, f"Zone '{z_name}' has no assigned camera coverage (unmonitored)"

    for cam in zone_cams:
        is_healthy, reason = check_camera_monitoring_health(
            cam,
            target_event_id=target_event_id,
            db=db,
            live_freshness_limit=live_freshness_limit,
            persisted_freshness_limit=persisted_freshness_limit
        )
        if not is_healthy:
            return False, f"Coverage failure in zone '{z_name}': {reason}"

    return True, f"All {len(zone_cams)} assigned camera(s) healthy and reporting fresh telemetry"


def _run_research_fca_pipeline(
    db: Session,
    target_event_id: Optional[str] = None
) -> Tuple[List[Dict], Dict[str, Dict[str, float]], List[Dict], List[Dict], Dict[str, Any], List[Dict]]:
    """
    Executes the IEEE Access 2025 FCA pipeline:
    1. Fuzzy crowd context Kc and crowd lattice Lc
    2. Algorithm 1: Extract crowded areas CA
    3. Area connectivity context Ka and area lattice La
    4. Algorithm 2: Generate crowd prevention plan P
    """
    # Fetch cameras
    cam_q = db.query(CameraModel).filter(CameraModel.enabled == True, CameraModel.status == "online")
    if target_event_id:
        cam_q = cam_q.filter(CameraModel.event_id == target_event_id)
    cameras = cam_q.all()

    # Query all configured cameras (including offline/disabled) for zone monitoring health evaluation
    all_cam_q = db.query(CameraModel)
    if target_event_id:
        all_cam_q = all_cam_q.filter((CameraModel.event_id == target_event_id) | (CameraModel.event_id == None))
    all_cameras = all_cam_q.all()

    # Fetch zones
    zone_q = db.query(ZoneModel)
    if target_event_id:
        zone_q = zone_q.filter(ZoneModel.event_id == target_event_id)
    zones = zone_q.all()

    # Fetch alerts
    alert_q = db.query(AlertModel).filter(AlertModel.resolved == False)
    if target_event_id:
        alert_q = alert_q.filter(AlertModel.event_id == target_event_id)
    alerts = alert_q.all()

    # Fetch zone connections
    conn_q = db.query(ZoneConnectionModel)
    if target_event_id:
        conn_q = conn_q.filter(ZoneConnectionModel.event_id == target_event_id)
    connections = conn_q.all()

    # Connect genuine telemetry to camera records
    cam_dicts = []
    for c in cameras:
        cd = {k: v for k, v in c.__dict__.items() if k != "_sa_instance_state"}
        telemetry = fetch_camera_movement_telemetry(c.id, target_event_id=target_event_id, db=db)
        if telemetry is not None:
            cd["flow_rate"] = telemetry["flow_rate"]
            cd["speed_avg"] = telemetry["speed_avg"]
            cd["telemetry_source"] = telemetry["source"]
            cd["telemetry_measured"] = True
        else:
            cd["flow_rate"] = None
            cd["speed_avg"] = None
            cd["telemetry_source"] = "unavailable"
            cd["telemetry_measured"] = False
        cam_dicts.append(cd)

    zone_dicts = [z.__dict__ for z in zones]
    alert_dicts = [a.__dict__ for a in alerts]
    conn_dicts = [cn.__dict__ for cn in connections]

    # 1. Crowd Fuzzy Context Kc (Paper Definition 5)
    c_objects, Kc = fca_solver.build_fuzzy_crowd_context(zone_dicts, cam_dicts, alert_dicts)

    # 2. Crowd Lattice Lc (Paper Definition 7)
    # Threshold Kc at alpha = 0.5 for concept incidence
    binary_crowd_rel: Dict[str, Set[str]] = {}
    for obj, scores in Kc.items():
        binary_crowd_rel[obj] = set(k for k, v in scores.items() if v >= 0.5)
    crowd_concepts = fca_solver.derive_closed_concepts(c_objects, binary_crowd_rel, ["D", "P", "M", "E", "S"])

    # 3. Algorithm 1: Extract Crowded Areas (Paper p. 11, T = 0.7)
    CA = fca_solver.extract_crowded_areas(crowd_concepts, Kc, threshold=0.7)

    # 4. Area Formal Context Ka & Area Lattice La (Paper Definitions 4 & 6)
    a_objects, Ka = fca_solver.build_area_context(zone_dicts, conn_dicts)
    area_concepts = fca_solver.derive_closed_concepts(a_objects, Ka, a_objects)

    # Fetch active capacity reservations for the target event
    reserved_by_destination: Dict[str, float] = defaultdict(float)
    if target_event_id:
        active_reservations = db.query(CapacityReservationModel).filter(
            CapacityReservationModel.event_id == target_event_id,
            CapacityReservationModel.status.in_(["approved", "in_transit", "cancellation_pending"])
        ).all()
        for res in active_reservations:
            reserved_by_destination[res.destination_zone] += float(res.diversion_volume)

    # Zone states dictionary for capacity checks (incorporating active reservations without mutating DB)
    zone_states: Dict[str, dict] = {}
    for z in zones:
        z_name = z.name or z.id
        phys_count = float(z.current_count or 0)
        cap = float(z.capacity or 500)
        res_vol = reserved_by_destination.get(z_name, 0.0)
        if not res_vol and z.id:
            res_vol = reserved_by_destination.get(z.id, 0.0)
        effective_count = phys_count + res_vol
        effective_density = min(100.0, (effective_count / cap) * 100.0) if cap > 0 else 100.0
        is_monitored, health_reason = evaluate_zone_monitoring_health(
            z, all_cameras, target_event_id=target_event_id, db=db
        )
        zone_states[z_name] = {
            "capacity": cap,
            "density": effective_density,
            "current_count": effective_count,
            "physical_count": phys_count,
            "reserved_volume": res_vol,
            "is_monitored": is_monitored,
            "monitoring_status": "healthy" if is_monitored else "unmonitored",
            "monitoring_reason": health_reason
        }

    blocked_edges: Set[Tuple[str, str]] = set()
    allowed_edges: Set[Tuple[str, str]] = set()
    for cn in connections:
        from_z = next((z.name for z in zones if z.id == cn.from_zone_id), cn.from_zone_id)
        to_z = next((z.name for z in zones if z.id == cn.to_zone_id), cn.to_zone_id)
        edge = (from_z, to_z)
        if cn.is_blocked:
            blocked_edges.add(edge)
            if cn.bidirectional:
                blocked_edges.add((to_z, from_z))
        else:
            allowed_edges.add(edge)
            if cn.bidirectional:
                allowed_edges.add((to_z, from_z))

    # 5. Algorithm 2: require a configured, unblocked physical passage in production.
    plan_result = fca_solver.generate_crowd_prevention_plan(
        area_concepts, CA, zone_states=zone_states, blocked_edges=blocked_edges,
        allowed_edges=allowed_edges
    )

    # Legacy binary concepts for backward compatibility
    legacy_objects, legacy_rel = fca_solver.build_formal_context(cam_dicts, alert_dicts, zone_dicts)
    legacy_concepts = fca_solver.derive_formal_concepts(legacy_objects, legacy_rel)

    return crowd_concepts, Kc, CA, area_concepts, plan_result, legacy_concepts


def format_prevention_plan_recommendation(plan: dict, target_event_id: Optional[str] = None) -> dict:
    """
    Formats an Algorithm 2 prevention plan into an operational recommendation record.
    Strict Invariants (Task 7.2):
    1. When is_capacity_verified is True, a verified-capacity label is used.
    2. When is_capacity_verified is False, None, or missing, the recommendation is strictly
       tagged as an unverified candidate route and NEVER uses the phrase 'Verified Route'.
    3. The engine's original reason and warning are fully preserved without contradiction.
    4. mitigation_capacity (physical capacity) is never misrepresented as remaining headroom or allocated crowd volume.
    """
    prefix = f"rec-fca-{target_event_id}" if target_event_id else "rec-fca"
    src_str = ", ".join(plan.get("crowded_sources", []))
    dst_str = ", ".join(plan.get("recommended_destinations", []))
    plan_rec_id = f"{prefix}-{plan.get('plan_id', 'unknown')}"
    primary_dst = plan.get("recommended_destinations", [])[0] if plan.get("recommended_destinations") else None

    # Treat missing, None, or non-True verification status conservatively as False
    is_verified = bool(plan.get("is_capacity_verified") is True)

    if is_verified:
        vol = plan.get("diversion_volume")
        if vol is not None and vol > 0:
            route_label = f"[Algorithm 2 Verified Route: Headroom Verified for {vol:.0f} Persons]"
        else:
            route_label = "[Algorithm 2 Verified Route: Capacity Headroom Verified]"
    else:
        route_label = "[Algorithm 2 Candidate Route: Unverified Headroom]"

    engine_reason = plan.get("reason", "")
    engine_warning = plan.get("warning", "")

    # Preserve original reason and warning without contradiction
    reason_parts = [engine_reason] if engine_reason else []
    if engine_warning and engine_warning not in engine_reason:
        reason_parts.append(f"Warning: {engine_warning}")
    reason_parts.append(route_label)
    formatted_reason = " ".join(reason_parts)

    return {
        "id": plan_rec_id,
        "event_id": target_event_id,
        "title": f"FCA Mitigation Plan: Divert crowd from {src_str} to {dst_str}",
        "priority": "high",
        "reason": formatted_reason,
        "confidence": 96,
        "zone": plan.get("crowded_sources", ["Monitored Zone"])[0] if plan.get("crowded_sources") else "Monitored Zone",
        "officer": "On-Duty Operations Dispatch",
        "status": "pending",
        "destination_zone": primary_dst,
        "diversion_volume": vol if is_verified else None,
        "is_capacity_verified": is_verified
    }



@router.get("", response_model=List[RecommendationResponse])
def get_recommendations(
    camera_id: Optional[str] = None, 
    event_id: Optional[str] = None, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Fetch decision recommendations derived from live camera feeds, alerts,
    and FCA Algorithms 1 and 2 (IEEE Access 2025).
    """
    user = get_current_user_from_auth(auth, db)
    target_event_id = event_id

    if user and event_id:
        evt = db.query(EventModel).filter(EventModel.id == event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot read recommendations for an event owned by another account."
            )
    elif not target_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id
        else:
            return []

    query = db.query(CameraModel).filter(CameraModel.enabled == True, CameraModel.status == "online")
    if target_event_id:
        query = query.filter(CameraModel.event_id == target_event_id)
    if camera_id:
        query = query.filter((CameraModel.id == camera_id) | (CameraModel.location == camera_id))
    
    cameras = query.all()
    if not cameras:
        if event_id:
            return db.query(RecommendationModel).filter(RecommendationModel.event_id == event_id).all()
        if camera_id:
            return db.query(RecommendationModel).filter(RecommendationModel.zone == camera_id).all()
        return db.query(RecommendationModel).all()

    # Execute Research FCA Pipeline
    crowd_concepts, Kc, CA, area_concepts, plan_result, legacy_concepts = _run_research_fca_pipeline(db, target_event_id)

    # 1. Base legacy recommendations from closures
    recs = fca_solver.generate_recommendations_from_fca(legacy_concepts, event_id=target_event_id)

    # 2. Integrate Algorithm 2 crowd prevention subplans safely
    for plan in plan_result.get("plans", []):
        recs.append(format_prevention_plan_recommendation(plan, target_event_id=target_event_id))

    # Store any new FCA derived recommendations into database
    for fr in recs:
        existing = db.query(RecommendationModel).filter(RecommendationModel.id == fr["id"]).first()
        if not existing:
            db.add(RecommendationModel(**fr))
    db.commit()

    if target_event_id:
        return db.query(RecommendationModel).filter(RecommendationModel.event_id == target_event_id).all()

    return db.query(RecommendationModel).all()


@router.get("/fca-lattice", response_model=ResearchLatticeResponse)
def get_fca_research_lattice(
    event_id: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Returns both the Crowd Lattice Lc and Area Lattice La DAG structures,
    along with Algorithm 1 crowded areas and Algorithm 2 prevention plans.
    """
    user = get_current_user_from_auth(auth, db)
    target_event_id = event_id
    if user and not target_event_id:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id

    crowd_concepts, Kc, CA, area_concepts, plan_result, legacy_concepts = _run_research_fca_pipeline(db, target_event_id)

    # Build Hasse diagram nodes & links for Crowd Lattice Lc
    c_nodes, c_links = fca_solver.build_lattice_graph(crowd_concepts)
    crowd_lattice_resp = {
        "objects": list(Kc.keys()),
        "attributes": CROWD_ATTRIBUTES,
        "nodes": c_nodes,
        "connections": [{"from": link["from"], "to": link["to"]} for link in c_links],
        "recommendations": []
    }

    # Build Hasse diagram nodes & links for Area Lattice La
    a_nodes, a_links = fca_solver.build_lattice_graph(area_concepts)
    area_lattice_resp = {
        "objects": list(Kc.keys()),
        "attributes": [{"key": k, "label": k, "weight": 1} for k in Kc.keys()],
        "nodes": a_nodes,
        "connections": [{"from": link["from"], "to": link["to"]} for link in a_links],
        "recommendations": []
    }

    return {
        "event_id": target_event_id,
        "crowd_lattice": crowd_lattice_resp,
        "area_lattice": area_lattice_resp,
        "fuzzy_context_summary": Kc,
        "crowded_areas": CA,
        "prevention_plans": plan_result.get("plans", [])
    }


@router.get("/crowded-areas", response_model=List[CrowdedAreaResult])
def get_crowded_areas(
    event_id: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Direct execution and retrieval of Algorithm 1: Extraction of Crowded Areas."""
    target_event_id = event_id
    user = get_current_user_from_auth(auth, db)
    if user and not target_event_id:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id

    _, _, CA, _, _, _ = _run_research_fca_pipeline(db, target_event_id)
    return CA


@router.get("/prevention-plans", response_model=PreventionPlanResponse)
def get_prevention_plans(
    event_id: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Direct execution and retrieval of Algorithm 2: Generation of Crowd Prevention Plan."""
    target_event_id = event_id
    user = get_current_user_from_auth(auth, db)
    if user and not target_event_id:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id

    _, _, CA, _, plan_result, _ = _run_research_fca_pipeline(db, target_event_id)
    return {
        "event_id": target_event_id,
        "total_crowded_areas": plan_result.get("total_crowded_areas", 0),
        "resolved_count": plan_result.get("resolved_count", 0),
        "unresolved_areas": plan_result.get("unresolved_areas", []),
        "plans": plan_result.get("plans", []),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }


@router.post("/{rec_id}/approve", response_model=Dict[str, Any])
def approve_recommendation(
    rec_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Approve an Algorithm 2 prevention plan with atomic destination capacity reservation (Task 7.5).
    - Requires authorized officer credentials.
    - Scoped strictly to the event of the recommendation.
    - Idempotent: repeated calls on approved plans preserve existing reservations without double-reserving.
    - Verifies explicit diversion volume; rejects unmeasured candidate routes.
    - Atomically checks physical count + active reservations; enforces capacity and < 75% density limits.
    """
    user = get_current_user_from_auth(auth, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Only authorized officers can approve crowd prevention plans."
        )

    rec = db.query(RecommendationModel).filter(RecommendationModel.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    # Event-level authorization
    if rec.event_id:
        evt = db.query(EventModel).filter(EventModel.id == rec.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot approve recommendations for an event owned by another account."
            )

    # Idempotency check: if already approved or in_transit, return existing reservation
    if rec.status in ("approved", "in_transit"):
        existing_res = db.query(CapacityReservationModel).filter(
            CapacityReservationModel.recommendation_id == rec.id
        ).first()
        if existing_res:
            return {
                "id": rec.id,
                "status": rec.status,
                "reservation": {
                    "id": existing_res.id,
                    "status": existing_res.status,
                    "destination_zone": existing_res.destination_zone,
                    "diversion_volume": existing_res.diversion_volume,
                    "approved_by": existing_res.approved_by,
                    "created_at": existing_res.created_at.isoformat() if existing_res.created_at else None
                },
                "message": f"Recommendation is already {rec.status}; existing reservation preserved."
            }

    if rec.status in ("completed", "rejected", "dismissed", "cancelled", "cancellation_pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve recommendation with terminal or cancelling status '{rec.status}'."
        )

    # Capacity verification check: must have explicit, reliable diversion volume
    if not rec.is_capacity_verified or rec.diversion_volume is None or rec.diversion_volume <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reserve capacity: Recommendation is an unverified candidate route with unmeasured diversion volume."
        )

    if not rec.destination_zone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reserve capacity: No primary destination specified in recommendation."
        )

    # Atomic revalidation and reservation
    with _reservation_lock:
        dest_zone = db.query(ZoneModel).filter(
            (ZoneModel.name == rec.destination_zone) | (ZoneModel.id == rec.destination_zone),
            ZoneModel.event_id == rec.event_id
        ).with_for_update().first()

        if not dest_zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destination zone '{rec.destination_zone}' not found in event '{rec.event_id}'."
            )

        # Camera Freshness Guard (Task 7.6.1): Revalidate destination monitoring health at approval time
        dest_cam_q = db.query(CameraModel)
        if rec.event_id:
            dest_cam_q = dest_cam_q.filter((CameraModel.event_id == rec.event_id) | (CameraModel.event_id == None))
        all_dest_cameras = dest_cam_q.all()
        is_monitored, health_reason = evaluate_zone_monitoring_health(
            dest_zone, all_dest_cameras, target_event_id=rec.event_id, db=db
        )
        if not is_monitored:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Monitoring health safeguard rejected: Destination '{rec.destination_zone}' is unmonitored or camera telemetry is stale/unreliable ({health_reason})."
            )

        # Sum of active reservations for this destination in the event (including in-transit cancellations awaiting reconciliation)
        active_vol_sum = db.query(func.coalesce(func.sum(CapacityReservationModel.diversion_volume), 0.0)).filter(
            CapacityReservationModel.event_id == rec.event_id,
            CapacityReservationModel.destination_zone == rec.destination_zone,
            CapacityReservationModel.status.in_(["approved", "in_transit", "cancellation_pending"]),
            CapacityReservationModel.recommendation_id != rec.id
        ).scalar() or 0.0

        phys_occ = float(dest_zone.current_count or 0)
        dest_cap = float(dest_zone.capacity or 500)
        vol = float(rec.diversion_volume)
        effective_occ = phys_occ + float(active_vol_sum)
        projected_occ = effective_occ + vol
        projected_dens = (projected_occ / dest_cap) * 100.0 if dest_cap > 0 else 100.0

        if projected_occ > dest_cap:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient headroom: Projected occupancy {projected_occ:.0f} exceeds physical capacity {dest_cap:.0f} in destination '{rec.destination_zone}'."
            )

        if projected_dens >= 75.0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Capacity safeguard rejected: Projected density {projected_dens:.1f}% in destination '{rec.destination_zone}' reaches or exceeds 75% threshold."
            )

        res_id = f"res-{rec.id}"
        reservation = CapacityReservationModel(
            id=res_id,
            recommendation_id=rec.id,
            event_id=rec.event_id or "",
            source_zone=rec.zone,
            destination_zone=rec.destination_zone,
            diversion_volume=vol,
            status="approved",
            approved_by=user.name or user.email,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(reservation)
        rec.status = "approved"
        rec.officer = user.name or user.email
        db.commit()

        return {
            "id": rec.id,
            "status": "approved",
            "reservation": {
                "id": reservation.id,
                "status": reservation.status,
                "destination_zone": reservation.destination_zone,
                "diversion_volume": reservation.diversion_volume,
                "approved_by": reservation.approved_by,
                "created_at": reservation.created_at.isoformat()
            },
            "message": f"Capacity reserved ({vol:.0f} persons) for destination '{rec.destination_zone}'."
        }


@router.post("/{rec_id}/in-transit", response_model=Dict[str, Any])
def start_diversion(
    rec_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Confirm physical crowd diversion has started on the ground."""
    user = get_current_user_from_auth(auth, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    rec = db.query(RecommendationModel).filter(RecommendationModel.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    if rec.event_id:
        evt = db.query(EventModel).filter(EventModel.id == rec.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Not authorized for this event.")

    if rec.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition to in_transit: Current status is '{rec.status}' (must be 'approved')."
        )

    reservation = db.query(CapacityReservationModel).filter(
        CapacityReservationModel.recommendation_id == rec.id
    ).first()
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active reservation found for this recommendation."
        )

    rec.status = "in_transit"
    reservation.status = "in_transit"
    reservation.updated_at = datetime.utcnow()
    db.commit()

    return {
        "id": rec.id,
        "status": "in_transit",
        "reservation_id": reservation.id,
        "message": "Diversion confirmed in transit; capacity reservation remains active."
    }


@router.post("/{rec_id}/complete", response_model=Dict[str, Any])
def complete_diversion(
    rec_id: str,
    body: Optional[ReservationCompleteRequest] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Mark an approved or in-transit diversion operation as completed.
    Reconciles and releases the destination capacity reservation without blindly incrementing physical count.
    """
    user = get_current_user_from_auth(auth, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    rec = db.query(RecommendationModel).filter(RecommendationModel.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    if rec.event_id:
        evt = db.query(EventModel).filter(EventModel.id == rec.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Not authorized for this event.")

    if rec.status not in ("approved", "in_transit"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete diversion: Current status is '{rec.status}' (must be 'approved' or 'in_transit')."
        )

    reservation = db.query(CapacityReservationModel).filter(
        CapacityReservationModel.recommendation_id == rec.id
    ).first()

    rec.status = "completed"
    if reservation:
        notes = body.reconciliation_notes if body and body.reconciliation_notes else f"Completed by officer {user.name or user.email}"
        reservation.status = "completed"
        reservation.reconciliation_notes = notes
        reservation.updated_at = datetime.utcnow()

    db.commit()

    return {
        "id": rec.id,
        "status": "completed",
        "reservation_status": reservation.status if reservation else None,
        "message": "Diversion operation marked completed. Destination capacity reservation released from active headroom."
    }


@router.post("/{rec_id}/cancel", response_model=Dict[str, Any])
def cancel_diversion(
    rec_id: str,
    body: Optional[ReservationCancelRequest] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Cancel an operation with safe in-transit handling (Task 7.5.2).
    - If approved (not yet started): immediately releases capacity reservation.
    - If in_transit: enters 'cancellation_pending' holding destination headroom until
      an authorized officer confirms reconciliation.
    - If already cancellation_pending and confirm_reconciled is provided with notes:
      finalizes cancellation and releases capacity reservation.
    - Idempotent: repeated cancellations preserve safe state.
    """
    user = get_current_user_from_auth(auth, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    rec = db.query(RecommendationModel).filter(RecommendationModel.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    if rec.event_id:
        evt = db.query(EventModel).filter(EventModel.id == rec.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Not authorized for this event.")

    reservation = db.query(CapacityReservationModel).filter(
        CapacityReservationModel.recommendation_id == rec.id
    ).first()

    # Idempotent return if already completely cancelled
    if rec.status == "cancelled" and (not reservation or reservation.status == "cancelled"):
        return {
            "id": rec.id,
            "status": "cancelled",
            "reservation_status": "cancelled" if reservation else None,
            "message": "Recommendation is already cancelled."
        }

    reason = body.reason if body and body.reason else f"Cancelled by officer {user.name or user.email}"
    confirm_reconciled = bool(body and getattr(body, "confirm_reconciled", False))
    raw_notes = getattr(body, "reconciliation_notes", None) if body else None
    cleaned_notes = raw_notes.strip() if (raw_notes and isinstance(raw_notes, str) and raw_notes.strip()) else None

    # Fix 1: When confirm_reconciled=True, require explicit, non-empty reconciliation_notes
    if confirm_reconciled and not cleaned_notes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reconciliation confirmation requires explicit, non-empty reconciliation notes confirming physical crowd status."
        )

    # Case 1: In-transit diversion without immediate reconciliation -> cancellation_pending
    if rec.status == "in_transit" and not confirm_reconciled:
        rec.status = "cancellation_pending"
        rec.override_reason = reason
        if reservation:
            reservation.status = "cancellation_pending"
            reservation.reconciliation_notes = f"Cancellation initiated while in-transit: {reason}. Awaiting physical clearance reconciliation."
            reservation.updated_at = datetime.utcnow()
        db.commit()
        return {
            "id": rec.id,
            "status": "cancellation_pending",
            "reservation_status": reservation.status if reservation else None,
            "message": "Diversion cancellation initiated. Operation is in-transit; capacity reservation remains held until explicit officer reconciliation."
        }

    # Case 2: Already in cancellation_pending and repeated without reconciliation
    if rec.status == "cancellation_pending" and not confirm_reconciled:
        return {
            "id": rec.id,
            "status": "cancellation_pending",
            "reservation_status": reservation.status if reservation else None,
            "message": "Cancellation is already pending officer reconciliation; capacity reservation remains held."
        }

    # Case 3: Approved (not in transit) OR explicit reconciliation confirmed
    rec.status = "cancelled"
    resolved_notes = f"[RECONCILED] {cleaned_notes} (Confirmed by officer {user.name or user.email})" if confirm_reconciled else reason
    rec.override_reason = resolved_notes
    if reservation:
        reservation.status = "cancelled"
        reservation.reconciliation_notes = resolved_notes
        reservation.updated_at = datetime.utcnow()

    db.commit()

    return {
        "id": rec.id,
        "status": "cancelled",
        "reservation_status": reservation.status if reservation else None,
        "message": "Diversion operation cancelled. Any active reservation released."
    }


@router.post("/{rec_id}/reconcile-cancellation", response_model=Dict[str, Any])
def reconcile_cancelled_diversion(
    rec_id: str,
    body: Optional[ReservationReconcileRequest] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Explicitly reconcile an in-transit diversion that was cancelled (Task 7.5.2).
    Requires an authorized officer to confirm that physical movement has been safely
    halted, redirected, or cleared before releasing reserved destination capacity.
    """
    user = get_current_user_from_auth(auth, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    rec = db.query(RecommendationModel).filter(RecommendationModel.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    if rec.event_id:
        evt = db.query(EventModel).filter(EventModel.id == rec.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Not authorized for this event.")

    reservation = db.query(CapacityReservationModel).filter(
        CapacityReservationModel.recommendation_id == rec.id
    ).first()

    # Idempotent: if already resolved and cancelled
    if rec.status == "cancelled" and (not reservation or reservation.status == "cancelled"):
        return {
            "id": rec.id,
            "status": "cancelled",
            "reservation_status": "cancelled" if reservation else None,
            "message": "Cancellation is already reconciled and capacity released."
        }

    # Enforce that operation was actually cancelled or in-transit
    if rec.status not in ("cancellation_pending", "in_transit"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reconcile cancellation: Current status is '{rec.status}' (must be 'cancellation_pending' or 'in_transit')."
        )

    notes = body.reconciliation_notes.strip() if (body and body.reconciliation_notes and body.reconciliation_notes.strip()) else None
    if not notes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reconciliation confirmation requires explicit notes confirming physical crowd status (e.g. halted, redirected, dispersed)."
        )

    action = getattr(body, "resolution_action", "halted") if body else "halted"
    if action not in ("halted", "redirected", "dispersed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resolution_action '{action}'. Must be one of: 'halted', 'redirected', 'dispersed'."
        )

    full_notes = f"[{action.upper()}] {notes} (Confirmed by officer {user.name or user.email})"

    rec.status = "cancelled"
    rec.override_reason = full_notes
    if reservation:
        reservation.status = "cancelled"
        reservation.reconciliation_notes = full_notes
        reservation.updated_at = datetime.utcnow()

    db.commit()

    return {
        "id": rec.id,
        "status": "cancelled",
        "reservation_status": reservation.status if reservation else None,
        "message": "Cancellation reconciled by authorized officer. Reserved destination capacity released."
    }


@router.post("/{rec_id}/reject")
def reject_recommendation(
    rec_id: str,
    reason: Optional[str] = Body(None, embed=True),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    rec = db.query(RecommendationModel).filter(RecommendationModel.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    user = get_current_user_from_auth(auth, db)
    if user and rec.event_id:
        evt = db.query(EventModel).filter(EventModel.id == rec.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    if rec.status in ("in_transit", "cancellation_pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject recommendation with status '{rec.status}'. Physical diversion is underway or awaiting reconciliation; use cancel and reconcile endpoints."
        )

    rec.status = "rejected"
    rec.override_reason = reason or "Manual officer override"

    # Also cancel any associated reservation
    reservation = db.query(CapacityReservationModel).filter(
        CapacityReservationModel.recommendation_id == rec.id
    ).first()
    if reservation and reservation.status == "approved":
        reservation.status = "rejected"
        reservation.reconciliation_notes = rec.override_reason
        reservation.updated_at = datetime.utcnow()

    db.commit()
    return {"id": rec.id, "status": "rejected", "override_reason": rec.override_reason}


@router.post("/{rec_id}/dismiss")
def dismiss_recommendation(
    rec_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    rec = db.query(RecommendationModel).filter(RecommendationModel.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    user = get_current_user_from_auth(auth, db)
    if user and rec.event_id:
        evt = db.query(EventModel).filter(EventModel.id == rec.event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    if rec.status in ("in_transit", "cancellation_pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dismiss recommendation with status '{rec.status}'. Physical diversion is underway or awaiting reconciliation; use cancel and reconcile endpoints."
        )

    rec.status = "dismissed"

    reservation = db.query(CapacityReservationModel).filter(
        CapacityReservationModel.recommendation_id == rec.id
    ).first()
    if reservation and reservation.status == "approved":
        reservation.status = "dismissed"
        reservation.updated_at = datetime.utcnow()

    db.commit()
    return {"id": rec.id, "status": "dismissed"}


@router.get("/reservations", response_model=List[CapacityReservationResponse])
def get_active_reservations(
    event_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieve capacity reservations with event-scoping and authorization."""
    user = get_current_user_from_auth(auth, db)
    target_event_id = event_id
    if user and event_id:
        evt = db.query(EventModel).filter(EventModel.id == event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    elif not target_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id
        else:
            return []

    query = db.query(CapacityReservationModel)
    if target_event_id:
        query = query.filter(CapacityReservationModel.event_id == target_event_id)
    if status_filter:
        query = query.filter(CapacityReservationModel.status == status_filter)

    return query.order_by(CapacityReservationModel.created_at.desc()).all()

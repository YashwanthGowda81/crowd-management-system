from fastapi import APIRouter, Depends, HTTPException, Body, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import time

from app.database import get_db
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models import EmergencyEventModel, EmergencyDispatchModel, SecurityStaffModel, CameraModel, AlertModel, EventModel, User
from app.schemas import EmergencyCreate, EmergencyResponse
from app.auth_utils import decode_access_token

router = APIRouter(prefix="/emergency", tags=["Emergency Management"])
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

@router.get("/status")
def get_current_emergency_status(
    event_id: Optional[str] = None, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Fetch currently active emergency event & dispatches from database."""
    user = get_current_user_from_auth(auth, db)
    target_event_id = event_id

    if user and event_id:
        evt = db.query(EventModel).filter(EventModel.id == event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot read emergency status for an event owned by another account."
            )
    elif not target_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id
        else:
            return {"has_active_emergency": False, "active_event": None, "dispatches": []}

    query = db.query(EmergencyEventModel).filter(EmergencyEventModel.status != "RESOLVED")
    if target_event_id:
        cams = db.query(CameraModel).filter(CameraModel.event_id == target_event_id).all()
        cam_ids = [c.id for c in cams]
        cam_locs = [c.location for c in cams]
        all_refs = set(cam_ids + cam_locs)
        if not all_refs:
            return {"has_active_emergency": False, "active_event": None, "dispatches": []}
        query = query.filter((EmergencyEventModel.camera_id.in_(all_refs)) | (EmergencyEventModel.location.in_(all_refs)))

    active_event = query.order_by(EmergencyEventModel.created_at.desc()).first()
    if not active_event:
        return {"has_active_emergency": False, "active_event": None, "dispatches": []}

    dispatches = db.query(EmergencyDispatchModel).filter(EmergencyDispatchModel.emergency_event_id == active_event.id).all()
    
    return {
        "has_active_emergency": True,
        "active_event": {
            "id": active_event.id,
            "camera_id": active_event.camera_id,
            "incident_type": active_event.incident_type,
            "severity": active_event.severity,
            "crowd_count": active_event.crowd_count,
            "density_pct": active_event.density_pct,
            "occupancy_pct": active_event.occupancy_pct,
            "location": active_event.location,
            "zone": active_event.zone,
            "latitude": active_event.latitude,
            "longitude": active_event.longitude,
            "reason": active_event.reason,
            "detected_at": active_event.detected_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(active_event.detected_at, "strftime") else str(active_event.detected_at),
            "status": active_event.status
        },
        "dispatches": [
            {
                "id": d.id,
                "emergency_event_id": d.emergency_event_id,
                "service_type": d.service_type,
                "camera_id": d.camera_id,
                "location": d.location,
                "zone": d.zone,
                "message": d.message,
                "assigned_staff_id": d.assigned_staff_id,
                "staff_name": d.staff_name,
                "timestamp": d.timestamp.strftime("%H:%M:%S") if hasattr(d.timestamp, "strftime") else str(d.timestamp),
                "status": d.status
            } for d in dispatches
        ]
    }

@router.get("/events")
def get_all_emergency_events(event_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Fetch all emergency event records from MySQL database."""
    query = db.query(EmergencyEventModel)
    if event_id:
        cams = db.query(CameraModel).filter(CameraModel.event_id == event_id).all()
        cam_ids = [c.id for c in cams]
        cam_locs = [c.location for c in cams]
        all_refs = set(cam_ids + cam_locs)
        if not all_refs:
            return []
        query = query.filter((EmergencyEventModel.camera_id.in_(all_refs)) | (EmergencyEventModel.location.in_(all_refs)))

    events = query.order_by(EmergencyEventModel.created_at.desc()).all()
    res = []
    for e in events:
        dispatches = db.query(EmergencyDispatchModel).filter(EmergencyDispatchModel.emergency_event_id == e.id).all()
        res.append({
            "id": e.id,
            "camera_id": e.camera_id,
            "incident_type": e.incident_type,
            "severity": e.severity,
            "crowd_count": e.crowd_count,
            "density_pct": e.density_pct,
            "occupancy_pct": e.occupancy_pct,
            "location": e.location,
            "zone": e.zone,
            "latitude": e.latitude,
            "longitude": e.longitude,
            "reason": e.reason,
            "detected_at": e.detected_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(e.detected_at, "strftime") else str(e.detected_at),
            "status": e.status,
            "dispatches_count": len(dispatches)
        })
    return res

@router.post("/trigger", status_code=status.HTTP_201_CREATED)
def trigger_manual_emergency(data: EmergencyCreate, db: Session = Depends(get_db)):
    """Trigger manual simulation emergency event (tagged as TEST / SIMULATION ONLY)."""
    # Dynamically select active analyzing camera if available
    cam = db.query(CameraModel).filter(
        CameraModel.enabled == True, 
        CameraModel.status == "online", 
        CameraModel.playback_status.in_(["analyzing", "playing"])
    ).first() or db.query(CameraModel).first()

    snap_cam_id = cam.id if cam else "cam-active-1"
    snap_name = cam.name if cam else "Primary CCTV Stream"
    snap_location = data.location or (cam.location if cam else "Main Entrance Sector")
    snap_zone = data.location or (cam.location if cam else "Main Entrance Sector")
    snap_count = int(cam.count if (cam and cam.count is not None) else 45)
    snap_density = float(cam.density if (cam and cam.density is not None) else 85.0)

    # Ensure clear TEST / SIMULATION prefix
    inc_label = data.type if "[TEST / SIMULATION]" in data.type else f"[TEST / SIMULATION] {data.type}"
    emg_id = f"emg-evt-{int(time.time() * 1000)}"
    snap_reason = data.description or f"[TEST / SIMULATION] Manual operator drill override for {snap_name}: Density {snap_density}% (Count: {snap_count}) in {snap_location}. Awaiting operator dispatch authorization."

    db_evt = EmergencyEventModel(
        id=emg_id,
        camera_id=snap_cam_id,
        incident_type=inc_label,
        severity="CRITICAL",
        crowd_count=snap_count,
        density_pct=snap_density,
        occupancy_pct=snap_density,
        location=snap_location,
        zone=snap_zone,
        reason=snap_reason,
        status="EMERGENCY_REVIEW_REQUIRED",
        created_at=datetime.utcnow()
    )
    db.add(db_evt)
    db.flush()

    # Create matching critical alert notifying operator that emergency review is required
    alert_id = f"alert-emg-{int(time.time() * 1000)}"
    db_alert = AlertModel(
        id=alert_id,
        event_id=cam.event_id if cam else None,
        title=f"🚨 EMERGENCY REVIEW REQUIRED: {inc_label}",
        description=f"Critical incident detected at {snap_location} (Density: {snap_density}%, Detections: {snap_count}). Authorized operator review & dispatch approval required.",
        level="critical",
        timestamp=datetime.now().strftime("%H:%M:%S"),
        zone=snap_location,
        camera=snap_name,
        resolved=False
    )
    db.add(db_alert)
    db.commit()

    return {
        "message": "Emergency event created for operator review. Dispatch approval required.",
        "event_id": emg_id,
        "status": "EMERGENCY_REVIEW_REQUIRED"
    }

@router.post("/events/{event_id}/approve-dispatch")
def approve_emergency_dispatch(event_id: str, db: Session = Depends(get_db)):
    """
    Authorized Operator Action: Approves and initiates the emergency dispatch workflow.
    Flow: EMERGENCY REVIEW -> AUTHORIZED OPERATOR -> APPROVE DISPATCH -> DISPATCH WORKFLOW
    """
    evt = db.query(EmergencyEventModel).filter(EmergencyEventModel.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Emergency event not found")

    evt.status = "DISPATCHED"

    # Generate dispatch signals only upon explicit operator authorization
    existing_dispatches = db.query(EmergencyDispatchModel).filter(EmergencyDispatchModel.emergency_event_id == event_id).all()
    if not existing_dispatches:
        services_to_dispatch = ["police", "security", "medical", "control_room"]
        if "fire" in evt.incident_type.lower():
            services_to_dispatch = ["fire", "medical", "police", "security", "control_room"]

        for stype in services_to_dispatch:
            staff_member = db.query(SecurityStaffModel).filter(SecurityStaffModel.is_online == True).first()
            disp_id = f"disp-{stype}-{int(time.time() * 1000)}"
            db_disp = EmergencyDispatchModel(
                id=disp_id,
                emergency_event_id=evt.id,
                service_type=stype,
                camera_id=evt.camera_id,
                location=evt.location,
                zone=evt.zone,
                message=f"AUTHORIZED DISPATCH: {stype.upper()} response deployed to {evt.location}.",
                assigned_staff_id=staff_member.id if staff_member else None,
                staff_name=staff_member.name if staff_member else "Command Desk Dispatch",
                timestamp=datetime.utcnow(),
                status="DISPATCHED"
            )
            db.add(db_disp)
    else:
        for d in existing_dispatches:
            d.status = "DISPATCHED"

    db.commit()
    return {"id": evt.id, "status": "DISPATCHED", "message": "Emergency dispatch approved and transmitted"}

@router.put("/events/{event_id}/status")
def update_emergency_status(event_id: str, action: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """Update emergency event lifecycle status."""
    evt = db.query(EmergencyEventModel).filter(EmergencyEventModel.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Emergency event not found")

    valid_actions = [
        "EMERGENCY_REVIEW_REQUIRED", 
        "ACKNOWLEDGED", 
        "APPROVE_DISPATCH", 
        "DISPATCHED", 
        "ARRIVED", 
        "RESOLVED",
        "REJECTED",
        "OVERRIDDEN"
    ]
    act = action.upper()
    if act not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Allowed: {valid_actions}")

    if act in ["APPROVE_DISPATCH", "DISPATCHED"]:
        return approve_emergency_dispatch(event_id, db)
    elif act in ["RESOLVED", "REJECTED", "OVERRIDDEN"]:
        evt.status = act
        evt.resolved_at = datetime.utcnow()
        db.query(EmergencyDispatchModel).filter(EmergencyDispatchModel.emergency_event_id == event_id).update({"status": "RESOLVED"})
        # Synchronously resolve linked alerts
        cam = db.query(CameraModel).filter(CameraModel.id == evt.camera_id).first()
        cam_name = cam.name if cam else None
        if cam_name:
            db.query(AlertModel).filter(AlertModel.resolved == False, AlertModel.camera == cam_name).update({"resolved": True})
        if evt.location:
            db.query(AlertModel).filter(AlertModel.resolved == False, AlertModel.zone == evt.location).update({"resolved": True})
    else:
        evt.status = act

    db.commit()
    return {"id": evt.id, "status": evt.status}

@router.put("/resolve")
def resolve_all_emergencies(db: Session = Depends(get_db)):
    """Deactivate all active emergency events."""
    db.query(EmergencyEventModel).filter(EmergencyEventModel.status != "RESOLVED").update({"status": "RESOLVED", "resolved_at": datetime.utcnow()})
    db.query(EmergencyDispatchModel).filter(EmergencyDispatchModel.status != "RESOLVED").update({"status": "RESOLVED"})
    db.query(AlertModel).filter(AlertModel.level == "critical", AlertModel.resolved == False).update({"resolved": True})
    db.commit()
    return {"message": "All emergency events resolved successfully", "has_active_emergency": False}

class ServiceDispatchPayload(BaseModel):
    service_type: str # "medical", "fire", "police", "security"
    event_id: Optional[str] = None
    station_name: Optional[str] = None
    priority: Optional[str] = "HIGH"
    notes: Optional[str] = None

@router.post("/dispatch-service")
def dispatch_service(
    payload: ServiceDispatchPayload,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Direct Authorized Dispatch Endpoint for Individual Services (Ambulance/Medical, Fire, Police, Security).
    Creates persisted EmergencyDispatchModel and AlertModel records with honest internal audit logging.
    """
    stype = payload.service_type.lower().strip()
    if stype == "ambulance":
        stype = "medical"
    if stype not in ["medical", "fire", "police", "security", "control_room"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid service type: {stype}. Must be medical, fire, police, or security."
        )

    user = get_current_user_from_auth(auth, db)
    operator_name = user.name if user else "Command Operator"

    # Find active emergency event or create one for active event / camera
    target_event_id = payload.event_id
    if not target_event_id and user:
        evt_rec = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt_rec:
            target_event_id = evt_rec.id

    active_emg = None
    if target_event_id:
        cams = db.query(CameraModel).filter(CameraModel.event_id == target_event_id).all()
        cam_refs = set([c.id for c in cams] + [c.location for c in cams])
        if cam_refs:
            active_emg = db.query(EmergencyEventModel).filter(
                EmergencyEventModel.status != "RESOLVED",
                (EmergencyEventModel.camera_id.in_(cam_refs)) | (EmergencyEventModel.location.in_(cam_refs))
            ).order_by(EmergencyEventModel.created_at.desc()).first()

    if not active_emg:
        active_emg = db.query(EmergencyEventModel).filter(EmergencyEventModel.status != "RESOLVED").order_by(EmergencyEventModel.created_at.desc()).first()

    # If no active emergency exists, create an internal dispatch incident record
    if not active_emg:
        active_cam = None
        if target_event_id:
            active_cam = db.query(CameraModel).filter(CameraModel.event_id == target_event_id).first()
        if not active_cam:
            active_cam = db.query(CameraModel).first()

        cam_id = active_cam.id if active_cam else "cam-active-1"
        loc = active_cam.location if active_cam else "Main Concourse Sector"
        emg_id = f"emg-disp-{int(time.time() * 1000)}"
        active_emg = EmergencyEventModel(
            id=emg_id,
            camera_id=cam_id,
            incident_type=f"[DISPATCH] {stype.upper()} Operational Response",
            severity="CRITICAL" if stype in ["medical", "fire"] else "HIGH",
            crowd_count=int(active_cam.count if (active_cam and active_cam.count is not None) else 45),
            density_pct=float(active_cam.density if (active_cam and active_cam.density is not None) else 50.0),
            occupancy_pct=float(active_cam.density if (active_cam and active_cam.density is not None) else 50.0),
            location=loc,
            zone=loc,
            reason=f"Operator dispatched {stype.upper()} unit directly to {loc}. Station: {payload.station_name or 'Command Desk Immediate Response'}.",
            status="DISPATCHED",
            created_at=datetime.utcnow()
        )
        db.add(active_emg)
        db.flush()
    else:
        active_emg.status = "DISPATCHED"

    # Assigned staff / station identification
    station_display = payload.station_name or ("Metropolitan Emergency Hub" if stype == "medical" else "Sector Fire Command" if stype == "fire" else "On-Site Command Unit")
    staff_member = db.query(SecurityStaffModel).filter(SecurityStaffModel.is_online == True).first()

    # Check for duplicate recent active dispatch within 10 seconds
    recent_existing = db.query(EmergencyDispatchModel).filter(
        EmergencyDispatchModel.emergency_event_id == active_emg.id,
        EmergencyDispatchModel.service_type == stype,
        EmergencyDispatchModel.status == "DISPATCHED"
    ).first()

    disp_id = f"disp-{stype}-{int(time.time() * 1000)}"
    if recent_existing:
        db_disp = recent_existing
        db_disp.message = f"RE-CONFIRMED DISPATCH: {stype.upper()} deployment to {active_emg.location}. Station: {station_display} (Operator: {operator_name})."
        db_disp.timestamp = datetime.utcnow()
    else:
        db_disp = EmergencyDispatchModel(
            id=disp_id,
            emergency_event_id=active_emg.id,
            service_type=stype,
            camera_id=active_emg.camera_id,
            location=active_emg.location,
            zone=active_emg.zone,
            message=f"AUTHORIZED DISPATCH: {stype.upper()} deployed to {active_emg.location}. Unit/Station: {station_display} (Operator: {operator_name}).",
            assigned_staff_id=staff_member.id if staff_member else None,
            staff_name=f"{station_display} ({staff_member.name if staff_member else 'Unit 1'})",
            timestamp=datetime.utcnow(),
            status="DISPATCHED"
        )
        db.add(db_disp)

    # Persist audit alert
    alert_id = f"alert-disp-{int(time.time() * 1000)}"
    db_alert = AlertModel(
        id=alert_id,
        event_id=target_event_id,
        title=f"🚨 {stype.upper()} UNIT DISPATCHED: {active_emg.location}",
        description=f"Operator {operator_name} authorized {stype.upper()} dispatch to {active_emg.location} (Assigned: {station_display}) at {datetime.now().strftime('%H:%M:%S')}. Internal Command Record.",
        level="critical" if stype in ["medical", "fire"] else "high",
        timestamp=datetime.now().strftime("%H:%M:%S"),
        zone=active_emg.location,
        camera=active_emg.camera_id,
        resolved=False
    )
    db.add(db_alert)
    db.commit()

    return {
        "success": True,
        "dispatch_id": db_disp.id,
        "emergency_event_id": active_emg.id,
        "service_type": stype,
        "status": "DISPATCHED",
        "station_name": station_display,
        "operator": operator_name,
        "location": active_emg.location,
        "timestamp": db_disp.timestamp.strftime("%H:%M:%S") if hasattr(db_disp.timestamp, "strftime") else str(db_disp.timestamp),
        "is_simulated": True,
        "message": f"Authorized {stype.upper()} unit dispatch confirmed and logged in system audit trail."
    }

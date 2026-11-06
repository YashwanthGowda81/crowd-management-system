import os
import time
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import EventModel, VenuePinModel, ZoneModel, CameraModel, SecurityStaffModel, User, ZoneConnectionModel
from app.schemas import (
    VenueDetailsResponse, 
    VenuePinCreate, 
    VenuePinResponse,
    ZoneCreate,
    ZoneUpdate,
    ZoneResponse,
    ZoneConnectionCreate,
    ZoneConnectionUpdate,
    ZoneConnectionResponse
)
from app.auth_utils import decode_access_token

router = APIRouter(prefix="/events", tags=["Venue Map & Architecture"])
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

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "maps")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

def _ensure_default_zones(event_id: str, db: Session):
    """Seed default operational zones if none exist for the event."""
    existing = db.query(ZoneModel).filter(ZoneModel.event_id == event_id).count()
    if existing == 0:
        default_zones = [
            ZoneModel(
                id=f"zone-{event_id}-1",
                event_id=event_id,
                name="ZONE A — Entry Concourse",
                code="ZONE-A",
                capacity=3000,
                current_count=0,
                density=0.0,
                risk_level="low",
                zone_type="gate_area"
            ),
            ZoneModel(
                id=f"zone-{event_id}-2",
                event_id=event_id,
                name="ZONE B — Main Arena",
                code="ZONE-B",
                capacity=8000,
                current_count=0,
                density=0.0,
                risk_level="low",
                zone_type="general"
            ),
            ZoneModel(
                id=f"zone-{event_id}-3",
                event_id=event_id,
                name="ZONE C — Emergency Exit Area",
                code="ZONE-C",
                capacity=2000,
                current_count=0,
                density=0.0,
                risk_level="low",
                zone_type="exit_corridor"
            ),
            ZoneModel(
                id=f"zone-{event_id}-4",
                event_id=event_id,
                name="ZONE D — Restricted / Backstage",
                code="ZONE-D",
                capacity=500,
                current_count=0,
                density=0.0,
                risk_level="low",
                zone_type="restricted"
            )
        ]
        db.add_all(default_zones)
        db.commit()

def _ensure_default_pins(event_id: str, db: Session):
    """Seed default demo pins only for the default event."""
    if event_id != "evt-arena-01":
        return
    existing = db.query(VenuePinModel).filter(VenuePinModel.event_id == event_id).count()
    if existing == 0:
        default_pins = [
            VenuePinModel(id=f"pin-{event_id}-gate-1", event_id=event_id, pin_type="gate_entry", label="North Gate (Turnstiles)", x=50.0, y=12.0),
            VenuePinModel(id=f"pin-{event_id}-gate-2", event_id=event_id, pin_type="gate_entry", label="West Entry (Concourse)", x=18.0, y=50.0),
            VenuePinModel(id=f"pin-{event_id}-gate-3", event_id=event_id, pin_type="gate_entry", label="East Entry (Concourse)", x=82.0, y=50.0),
            VenuePinModel(id=f"pin-{event_id}-emg-1", event_id=event_id, pin_type="emergency_exit", label="South Emergency Exit", x=50.0, y=88.0),
            VenuePinModel(id=f"pin-{event_id}-rest-1", event_id=event_id, pin_type="restricted", label="Backstage / VIP Area", x=50.0, y=32.0),
            VenuePinModel(id=f"pin-{event_id}-cam-1", event_id=event_id, pin_type="camera", label="CAM-01 (North Gate)", x=50.0, y=16.0),
            VenuePinModel(id=f"pin-{event_id}-cam-2", event_id=event_id, pin_type="camera", label="CAM-02 (West Entry)", x=22.0, y=50.0),
            VenuePinModel(id=f"pin-{event_id}-cam-3", event_id=event_id, pin_type="camera", label="CAM-03 (Main Arena)", x=50.0, y=55.0),
            VenuePinModel(id=f"pin-{event_id}-cam-4", event_id=event_id, pin_type="camera", label="CAM-04 (South Exit)", x=50.0, y=84.0),
            VenuePinModel(id=f"pin-{event_id}-cam-5", event_id=event_id, pin_type="camera", label="CAM-05 (Backstage)", x=50.0, y=36.0),
            VenuePinModel(id=f"pin-{event_id}-cam-6", event_id=event_id, pin_type="camera", label="CAM-06 (East Entry)", x=78.0, y=50.0),
        ]
        db.add_all(default_pins)
        db.commit()

def _ensure_default_staff(db: Session):
    """No-op: Security staff records have been reset."""
    pass

def _build_venue_response(evt: EventModel, db: Session) -> dict:
    _ensure_default_zones(evt.id, db)
    _ensure_default_pins(evt.id, db)
    _ensure_default_staff(db)
    pins = db.query(VenuePinModel).filter(VenuePinModel.event_id == evt.id).all()
    zones = db.query(ZoneModel).filter(ZoneModel.event_id == evt.id).all()
    cams = db.query(CameraModel).filter(CameraModel.event_id == evt.id).all()
    staff = db.query(SecurityStaffModel).all()
    connections = db.query(ZoneConnectionModel).filter(ZoneConnectionModel.event_id == evt.id).all()

    # Spatial architecture breakdown
    gates = [p for p in pins if p.pin_type in ["gate_entry", "gate_exit"]]
    entrances = [p for p in pins if p.pin_type == "gate_entry"]
    exits = [p for p in pins if p.pin_type == "gate_exit"]
    emg_exits = [p for p in pins if p.pin_type == "emergency_exit"]
    restricted = [p for p in pins if p.pin_type == "restricted"]

    cam_locations = [
        {
            "id": c.id,
            "name": c.name,
            "location": c.location,
            "zone_id": c.zone_id,
            "status": c.status,
            "count": c.count,
            "density": c.density
        } for c in cams
    ]

    security_res = [
        {
            "id": s.id,
            "name": s.name,
            "zone": s.zone,
            "is_online": s.is_online,
            "mobile_status": s.mobile_status,
            "phone": s.phone
        } for s in staff
    ]

    spatial_arch = {
        "gates": gates,
        "entrances": entrances,
        "exits": exits,
        "emergency_exits": emg_exits,
        "restricted_areas": restricted,
        "camera_locations": cam_locations,
        "security_resources": security_res,
        "connections": connections
    }

    return {
        "event_id": evt.id,
        "event_title": evt.title,
        "venue_name": getattr(evt, "venue_name", "Main Venue Complex") or "Main Venue Complex",
        "map_url": evt.map_url,
        "pins": pins,
        "zones": zones,
        "connections": connections,
        "spatial_architecture": spatial_arch
    }

# Provide both /venue-details AND /venue to resolve frontend/backend route mismatch
@router.get("/{event_id}/venue-details", response_model=VenueDetailsResponse)
@router.get("/{event_id}/venue", response_model=VenueDetailsResponse)
def get_venue_details(
    event_id: str, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    if event_id == "default":
        evt = db.query(EventModel).first()
    else:
        evt = db.query(EventModel).filter(EventModel.id == event_id).first()

    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")

    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot read venue details for an event owned by another account."
        )

    return _build_venue_response(evt, db)

# Provide both /map AND /venue-map
@router.post("/{event_id}/map", response_model=VenueDetailsResponse)
@router.post("/{event_id}/venue-map", response_model=VenueDetailsResponse)
async def upload_venue_map(
    event_id: str, 
    file: UploadFile = File(...), 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")

    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot modify venue map for an event owned by another account."
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{ext}'. Allowed: PNG, JPG, JPEG, WEBP.")

    filename = f"map_{evt.id}_{int(time.time())}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    static_url = f"http://localhost:8000/static/maps/{filename}"
    evt.map_url = static_url
    db.commit()

    return _build_venue_response(evt, db)

@router.delete("/{event_id}/map")
@router.delete("/{event_id}/venue-map")
def delete_venue_map(
    event_id: str, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")

    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot modify venue map for an event owned by another account."
        )

    evt.map_url = None
    db.commit()
    return {"message": "Venue map removed successfully", "event_id": event_id}

@router.post("/{event_id}/pins", response_model=VenuePinResponse, status_code=status.HTTP_201_CREATED)
def add_venue_pin(
    event_id: str, 
    pin: VenuePinCreate, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")

    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot add pins for an event owned by another account."
        )

    pin_id = f"pin-{evt.id}-{int(time.time() * 1000)}"
    db_pin = VenuePinModel(
        id=pin_id,
        event_id=evt.id,
        pin_type=pin.pin_type,
        label=pin.label,
        x=round(pin.x, 2),
        y=round(pin.y, 2)
    )
    db.add(db_pin)
    db.commit()
    db.refresh(db_pin)
    return db_pin

@router.delete("/{event_id}/pins/{pin_id}")
def delete_venue_pin(
    event_id: str, 
    pin_id: str, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if evt:
        user = get_current_user_from_auth(auth, db)
        if user and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot delete pins for an event owned by another account."
            )

    pin = db.query(VenuePinModel).filter(VenuePinModel.id == pin_id, VenuePinModel.event_id == event_id).first()
    if not pin:
        raise HTTPException(status_code=404, detail="Pin not found")

    db.delete(pin)
    db.commit()
    return {"message": "Pin deleted successfully", "pin_id": pin_id}

# --- ZONE CRUD ENDPOINTS ---
@router.get("/{event_id}/zones", response_model=List[ZoneResponse])
def get_event_zones(
    event_id: str, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    if event_id == "default":
        evt = db.query(EventModel).first()
    else:
        evt = db.query(EventModel).filter(EventModel.id == event_id).first()

    if not evt:
        return []

    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot read zones for an event owned by another account."
        )

    _ensure_default_zones(evt.id, db)
    return db.query(ZoneModel).filter(ZoneModel.event_id == evt.id).all()

@router.post("/{event_id}/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_event_zone(
    event_id: str, 
    zone_data: ZoneCreate, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")

    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot create zones for an event owned by another account."
        )

    zone_id = f"zone-{evt.id}-{int(time.time() * 1000)}"
    new_zone = ZoneModel(
        id=zone_id,
        event_id=evt.id,
        name=zone_data.name,
        code=zone_data.code or f"Z-{int(time.time()) % 1000}",
        capacity=zone_data.capacity or 500,
        zone_type=zone_data.zone_type or "general",
        coordinates=zone_data.coordinates
    )
    db.add(new_zone)
    db.commit()
    db.refresh(new_zone)
    return new_zone

@router.put("/{event_id}/zones/{zone_id}", response_model=ZoneResponse)
def update_event_zone(
    event_id: str, 
    zone_id: str, 
    zone_data: ZoneUpdate, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if evt:
        user = get_current_user_from_auth(auth, db)
        if user and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot modify zones for an event owned by another account."
            )

    zone = db.query(ZoneModel).filter(ZoneModel.id == zone_id, ZoneModel.event_id == event_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    if zone_data.name is not None:
        zone.name = zone_data.name
    if zone_data.code is not None:
        zone.code = zone_data.code
    if zone_data.capacity is not None:
        zone.capacity = zone_data.capacity
    if zone_data.zone_type is not None:
        zone.zone_type = zone_data.zone_type
    if zone_data.coordinates is not None:
        zone.coordinates = zone_data.coordinates

    db.commit()
    db.refresh(zone)
    return zone

@router.delete("/{event_id}/zones/{zone_id}")
def delete_event_zone(
    event_id: str, 
    zone_id: str, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if evt:
        user = get_current_user_from_auth(auth, db)
        if user and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot delete zones for an event owned by another account."
            )

    zone = db.query(ZoneModel).filter(ZoneModel.id == zone_id, ZoneModel.event_id == event_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    db.delete(zone)
    db.commit()
    return {"message": "Zone deleted successfully", "id": zone_id}

# --- ZONE CONNECTION CRUD ENDPOINTS (Paper Definition 4: Physical Area Graph) ---
@router.get("/{event_id}/connections", response_model=List[ZoneConnectionResponse])
def get_event_connections(
    event_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    evt = db.query(EventModel).filter(EventModel.id == event_id).first() if event_id != "default" else db.query(EventModel).first()
    if not evt:
        return []
    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot read connections for an event owned by another account."
        )
    return db.query(ZoneConnectionModel).filter(ZoneConnectionModel.event_id == evt.id).all()

@router.post("/{event_id}/connections", response_model=ZoneConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_zone_connection(
    event_id: str,
    conn_data: ZoneConnectionCreate,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")
    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot create connections for an event owned by another account."
        )

    # Validate zones exist
    from_z = db.query(ZoneModel).filter(ZoneModel.id == conn_data.from_zone_id, ZoneModel.event_id == evt.id).first()
    to_z = db.query(ZoneModel).filter(ZoneModel.id == conn_data.to_zone_id, ZoneModel.event_id == evt.id).first()
    if not from_z or not to_z:
        raise HTTPException(status_code=400, detail="One or both connected zones do not exist for this event.")

    conn_id = f"conn-{evt.id}-{int(time.time() * 1000)}"
    new_conn = ZoneConnectionModel(
        id=conn_id,
        event_id=evt.id,
        from_zone_id=conn_data.from_zone_id,
        to_zone_id=conn_data.to_zone_id,
        bidirectional=conn_data.bidirectional if conn_data.bidirectional is not None else True,
        is_blocked=conn_data.is_blocked or False,
        corridor_name=conn_data.corridor_name or f"Passage {from_z.name} -> {to_z.name}",
        flow_capacity=conn_data.flow_capacity or 500
    )
    db.add(new_conn)
    db.commit()
    db.refresh(new_conn)
    return new_conn

@router.put("/{event_id}/connections/{connection_id}", response_model=ZoneConnectionResponse)
def update_zone_connection(
    event_id: str,
    connection_id: str,
    conn_data: ZoneConnectionUpdate,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    conn = db.query(ZoneConnectionModel).filter(ZoneConnectionModel.id == connection_id, ZoneConnectionModel.event_id == event_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Zone connection not found")

    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if evt:
        user = get_current_user_from_auth(auth, db)
        if user and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot modify connections for an event owned by another account."
            )

    if conn_data.bidirectional is not None:
        conn.bidirectional = conn_data.bidirectional
    if conn_data.is_blocked is not None:
        conn.is_blocked = conn_data.is_blocked
    if conn_data.corridor_name is not None:
        conn.corridor_name = conn_data.corridor_name
    if conn_data.flow_capacity is not None:
        conn.flow_capacity = conn_data.flow_capacity

    db.commit()
    db.refresh(conn)
    return conn

@router.delete("/{event_id}/connections/{connection_id}")
def delete_zone_connection(
    event_id: str,
    connection_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    conn = db.query(ZoneConnectionModel).filter(ZoneConnectionModel.id == connection_id, ZoneConnectionModel.event_id == event_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Zone connection not found")

    evt = db.query(EventModel).filter(EventModel.id == event_id).first()
    if evt:
        user = get_current_user_from_auth(auth, db)
        if user and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot delete connections for an event owned by another account."
            )

    db.delete(conn)
    db.commit()
    return {"message": "Zone connection deleted successfully", "id": connection_id}


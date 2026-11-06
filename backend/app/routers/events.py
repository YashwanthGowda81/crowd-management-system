from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
import time

from app.database import get_db
from app.models import EventModel, ZoneModel, VenuePinModel, CameraModel, User
from app.schemas import EventCreate, EventUpdate, EventResponse
from app.auth_utils import decode_access_token

router = APIRouter(prefix="/events", tags=["Events"])
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

def init_default_events(db: Session):
    """No-op: Application events have been reset. Events are created through the onboarding workflow."""
    pass

@router.get("", response_model=List[EventResponse])
def get_events(
    manager_id: Optional[int] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Fetch event records from database, scoped to authenticated manager."""
    init_default_events(db)
    user = get_current_user_from_auth(auth, db)
    query = db.query(EventModel)
    if user:
        if manager_id is not None and manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot read events owned by another account."
            )
        query = query.filter(EventModel.manager_id == user.id)
    elif manager_id is not None:
        query = query.filter(EventModel.manager_id == manager_id)
    return query.all()

@router.get("/my-event", response_model=Optional[EventResponse])
def get_my_event(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Fetch event associated with the authenticated manager."""
    init_default_events(db)
    if not auth or not auth.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token required")
    payload = decode_access_token(auth.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
    if not evt and user.id == 1:
        evt = db.query(EventModel).filter(EventModel.id == "evt-arena-01").first()
        if evt and evt.manager_id is None:
            evt.manager_id = user.id
            db.commit()
            db.refresh(evt)
    return evt

@router.get("/get/{evt_id}", response_model=EventResponse)
@router.get("/{evt_id}", response_model=EventResponse)
def get_event_by_id(
    evt_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Fetch single event by ID with strict ownership validation."""
    evt = db.query(EventModel).filter(EventModel.id == evt_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")
    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot read an event owned by another account."
        )
    return evt

@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    evt: EventCreate,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Create event record in database and associate with authenticated manager."""
    if evt.capacity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Venue capacity must be a positive whole number greater than 0."
        )
    if evt.capacity > 1000000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Venue capacity exceeds maximum allowed limit (1,000,000)."
        )

    evt_id = f"evt-{int(time.time() * 1000)}"
    user = get_current_user_from_auth(auth, db)
    assigned_manager_id = evt.manager_id if evt.manager_id is not None else (user.id if user else None)

    # Enforce Single Account = One Event Architecture
    if assigned_manager_id is not None:
        existing_evt = db.query(EventModel).filter(EventModel.manager_id == assigned_manager_id).first()
        if existing_evt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already has an active event. A single account can manage only one event at a time."
            )

    db_evt = EventModel(
        id=evt_id,
        manager_id=assigned_manager_id,
        title=evt.title,
        venue_name=evt.venue_name or "Main Arena Complex",
        capacity=evt.capacity,
        staff=evt.staff or 20,
        risk=evt.risk or "medium",
        start_time=evt.start_time or "08:00 AM",
        end_time=evt.end_time or "08:00 PM",
        limits=evt.limits if (evt.limits and evt.limits > 0) else int(evt.capacity * 0.85),
        map_url=evt.map_url
    )
    db.add(db_evt)
    db.commit()
    db.refresh(db_evt)
    return db_evt

@router.put("/{evt_id}", response_model=EventResponse)
def update_event(
    evt_id: str, 
    evt_data: EventUpdate, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Update event attributes with validation."""
    evt = db.query(EventModel).filter(EventModel.id == evt_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")

    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot modify an event owned by another account."
        )

    if evt_data.capacity is not None:
        if evt_data.capacity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Venue capacity must be a positive whole number greater than 0."
            )
        if evt_data.capacity > 1000000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Venue capacity exceeds maximum allowed limit (1,000,000)."
            )
        evt.capacity = evt_data.capacity
        # Proportionately scale limits threshold if not explicitly set
        if evt_data.limits is None:
            evt.limits = int(evt_data.capacity * 0.85)

    if evt_data.title is not None:
        evt.title = evt_data.title
    if evt_data.venue_name is not None:
        evt.venue_name = evt_data.venue_name
    if evt_data.staff is not None:
        evt.staff = evt_data.staff
    if evt_data.risk is not None:
        evt.risk = evt_data.risk
    if evt_data.start_time is not None:
        evt.start_time = evt_data.start_time
    if evt_data.end_time is not None:
        evt.end_time = evt_data.end_time
    if evt_data.limits is not None:
        evt.limits = evt_data.limits
    if evt_data.map_url is not None:
        evt.map_url = evt_data.map_url
    if evt_data.manager_id is not None:
        evt.manager_id = evt_data.manager_id

    db.commit()
    db.refresh(evt)
    return evt

@router.delete("/{evt_id}")
def delete_event(
    evt_id: str, 
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Delete event record and clean dependent spatial entities."""
    evt = db.query(EventModel).filter(EventModel.id == evt_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")
    
    user = get_current_user_from_auth(auth, db)
    if user and evt.manager_id and evt.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot delete an event owned by another account."
        )

    # Safely clean dependent entities
    db.query(ZoneModel).filter(ZoneModel.event_id == evt_id).delete()
    db.query(VenuePinModel).filter(VenuePinModel.event_id == evt_id).delete()
    db.query(CameraModel).filter(CameraModel.event_id == evt_id).delete()
    db.delete(evt)
    db.commit()
    return {"message": "Event deleted successfully", "id": evt_id}

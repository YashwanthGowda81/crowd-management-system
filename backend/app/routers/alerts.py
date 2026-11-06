from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import time

from app.database import get_db
from app.models import AlertModel, CameraModel, ZoneModel
from app.schemas import AlertCreate, AlertResponse

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models import AlertModel, CameraModel, ZoneModel, EventModel, User
from app.auth_utils import decode_access_token

router = APIRouter(prefix="/alerts", tags=["Alerts"])
security = HTTPBearer(auto_error=False)

def get_current_user_from_auth(auth: Optional[HTTPAuthorizationCredentials], db: Session) -> Optional[User]:
    if not auth or not hasattr(auth, "credentials") or not auth.credentials:
        return None
    try:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("sub"):
            return db.query(User).filter(User.email == payload["sub"]).first()
    except Exception:
        pass
    return None

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    camera_id: Optional[str] = None,
    event_id: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Fetch real alerts stored in MySQL. Supports filtering by camera_id or camera name, and event_id."""
    user = get_current_user_from_auth(auth, db)
    target_event_id = event_id

    if user and event_id:
        evt = db.query(EventModel).filter(EventModel.id == event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot read alerts for an event owned by another account."
            )
    elif not target_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id
        else:
            return []

    query = db.query(AlertModel)
    if target_event_id:
        cam_names = [c.name for c in db.query(CameraModel).filter(CameraModel.event_id == target_event_id).all()]
        cam_ids = [c.id for c in db.query(CameraModel).filter(CameraModel.event_id == target_event_id).all()]
        zone_names = [z.name for z in db.query(ZoneModel).filter(ZoneModel.event_id == target_event_id).all()]
        zone_codes = [z.code for z in db.query(ZoneModel).filter(ZoneModel.event_id == target_event_id).all() if z.code]
        all_refs = set(cam_names + cam_ids + zone_names + zone_codes)
        event_filter = (AlertModel.event_id == target_event_id)
        if all_refs:
            event_filter = event_filter | (AlertModel.camera.in_(all_refs)) | (AlertModel.zone.in_(all_refs))
        query = query.filter(event_filter)
    if camera_id:
        query = query.filter((AlertModel.id == camera_id) | (AlertModel.camera == camera_id))
    return query.order_by(AlertModel.resolved.asc(), AlertModel.id.desc()).all()

@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(alert_data: AlertCreate, db: Session = Depends(get_db)):
    """Create new AI risk alert record in MySQL database."""
    alert_id = f"alert-{int(time.time() * 1000)}"
    timestamp_str = datetime.now().strftime("%H:%M:%S")

    db_alert = AlertModel(
        id=alert_id,
        title=alert_data.title,
        description=alert_data.description,
        level=alert_data.level,
        timestamp=timestamp_str,
        zone=alert_data.zone,
        camera=alert_data.camera,
        resolved=False
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.put("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: str, db: Session = Depends(get_db)):
    """Mark alert as resolved."""
    alert = db.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    db.commit()
    db.refresh(alert)
    return alert

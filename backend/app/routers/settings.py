from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SettingsModel
from app.schemas import SettingsSchema

router = APIRouter(prefix="/settings", tags=["System Settings"])

def init_default_settings(db: Session):
    if db.query(SettingsModel).count() == 0:
        default_settings = SettingsModel(
            id=1,
            ai_sensitivity=75,
            crowd_threshold=85,
            sound_alerts=True,
            auto_escalation=False,
            fca_auto_recommendation=False,
            language="English",
            theme="dark"
        )
        db.add(default_settings)
        db.commit()

@router.get("", response_model=SettingsSchema)
def get_settings(db: Session = Depends(get_db)):
    init_default_settings(db)
    return db.query(SettingsModel).filter(SettingsModel.id == 1).first()

@router.put("", response_model=SettingsSchema)
def update_settings(data: SettingsSchema, db: Session = Depends(get_db)):
    init_default_settings(db)
    settings = db.query(SettingsModel).filter(SettingsModel.id == 1).first()

    if data.ai_sensitivity is not None:
        settings.ai_sensitivity = data.ai_sensitivity
    if data.crowd_threshold is not None:
        settings.crowd_threshold = data.crowd_threshold
    if data.sound_alerts is not None:
        settings.sound_alerts = data.sound_alerts
    if data.auto_escalation is not None:
        settings.auto_escalation = data.auto_escalation
    if data.fca_auto_recommendation is not None:
        settings.fca_auto_recommendation = data.fca_auto_recommendation
    if data.language is not None:
        settings.language = data.language
    if data.theme is not None:
        settings.theme = data.theme

    db.commit()
    db.refresh(settings)
    return settings

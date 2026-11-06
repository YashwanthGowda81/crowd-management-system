from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models import User, EventModel, CameraModel
from app.schemas import UserLogin, UserRegister, UserResponse, OnboardingStatusResponse, EventResponse, CameraResponse, UserProfileUpdate
from app.auth_utils import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication & Operators"])
security = HTTPBearer(auto_error=False)

def init_default_users(db: Session):
    """No-op: Default accounts have been reset. Accounts must be provisioned through authorized administrative setup."""
    pass

def get_optional_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency for extracting current user if token is present, without throwing 401."""
    if not auth or not auth.credentials:
        return None
    try:
        payload = decode_access_token(auth.credentials)
        if not payload or not payload.get("sub"):
            return None
        return db.query(User).filter(User.email == payload["sub"]).first()
    except Exception:
        return None

def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency for securing routes with JWT Bearer tokens."""
    init_default_users(db)
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )
    payload = decode_access_token(auth.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Register a new surveillance operator / manager."""
    import re

    # 1. Normalize fields
    name = (data.name or "").strip()
    email = (data.email or "").strip().lower()
    password = data.password or ""

    # 2. Field validations
    if not name or len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name is required and must be at least 2 characters long."
        )

    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not email or not re.match(email_regex, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required."
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    if data.confirm_password is not None and password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and confirmation password do not match."
        )

    # 3. Prevent privilege escalation: Never allow registering an administrator account
    if data.role and data.role.strip().lower() in ["admin", "super admin", "administrator", "root"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot self-assign an administrator role."
        )

    # Assign standard least-privileged manager/operator role
    assigned_role = "Command Officer"

    # 4. Reject duplicate email addresses
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead."
        )

    # 5. Securely hash password and persist user
    db_user = User(
        email=email,
        hashed_password=hash_password(password),
        name=name,
        role=assigned_role,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # 6. Return safe response without password or hash
    return {
        "id": db_user.id,
        "email": db_user.email,
        "name": db_user.name,
        "role": db_user.role,
        "message": "Account registered successfully. Please sign in with your credentials."
    }

@router.post("/login", response_model=UserResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    if total_users == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No account is available. An administrator must provision an account before you can sign in."
        )

    normalized_email = (data.email or "").strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator credentials"
        )

    # If password was legacy plain text, upgrade to hash now
    if not user.hashed_password.startswith("pbkdf2_"):
        user.hashed_password = hash_password(data.password)
        db.commit()

    token = create_access_token(data={"sub": user.email, "role": user.role, "name": user.name})

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "token": token
    }

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role
    }

@router.put("/profile")
def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update profile details for the authenticated user."""
    if data.name is not None:
        trimmed = data.name.strip()
        if len(trimmed) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Full name must be at least 2 characters long."
            )
        current_user.name = trimmed

    if data.new_password:
        if not data.current_password or not verify_password(data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password verification failed. Please enter your valid current password."
            )
        if len(data.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long."
            )
        current_user.hashed_password = hash_password(data.new_password)

    db.commit()
    db.refresh(current_user)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "message": "Profile updated successfully."
    }

@router.get("/onboarding-status", response_model=OnboardingStatusResponse)
def get_onboarding_status(
    event_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates the actual persisted onboarding readiness for the authenticated manager:
    - If manager has NO event: returns status='needs_event', next_route='/event-setup'
    - If event exists but NO camera/video source: returns status='needs_source', next_route='/camera-setup'
    - If event and camera/source exist: returns status='complete', next_route='/dashboard'
    """
    # 1. Resolve manager's event
    target_event = None
    if event_id:
        target_event = db.query(EventModel).filter(
            EventModel.id == event_id,
            (EventModel.manager_id == current_user.id) | (EventModel.manager_id.is_(None))
        ).first()

    if not target_event:
        # Query event owned by manager
        target_event = db.query(EventModel).filter(EventModel.manager_id == current_user.id).first()

    if not target_event:
        return {
            "has_event": False,
            "event": None,
            "has_source": False,
            "source_count": 0,
            "cameras": [],
            "status": "needs_event",
            "next_route": "/event-setup"
        }

    # 2. Check for configured camera / video sources for this specific event
    cameras = db.query(CameraModel).filter(CameraModel.event_id == target_event.id).all()
    has_source = len(cameras) > 0

    if not has_source:
        return {
            "has_event": True,
            "event": target_event,
            "has_source": False,
            "source_count": 0,
            "cameras": [],
            "status": "needs_source",
            "next_route": "/camera-setup"
        }

    return {
        "has_event": True,
        "event": target_event,
        "has_source": True,
        "source_count": len(cameras),
        "cameras": cameras,
        "status": "complete",
        "next_route": "/dashboard"
    }

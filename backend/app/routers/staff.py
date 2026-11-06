import re
import time
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth_utils import decode_access_token
from app.database import get_db
from app.models import InstructionLogModel, SecurityStaffModel, User
from app.schemas import (
    InstructionLogCreate,
    InstructionLogResponse,
    SecurityStaffCreate,
    SecurityStaffResponse,
    SecurityStaffUpdate,
    CoordinationMessageCreate,
    CoordinationMessageResponse,
    CoordinationStatusUpdate,
)

router = APIRouter(prefix="/staff", tags=["Security Staff & Communication"])
security = HTTPBearer(auto_error=False)


def get_current_user_from_auth(
    auth: Optional[HTTPAuthorizationCredentials], db: Session
) -> Optional[User]:
    """Helper to extract authenticated user from Bearer token."""
    if not auth or not auth.credentials:
        return None
    try:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("sub"):
            return db.query(User).filter(User.email == payload["sub"]).first()
    except Exception:
        pass
    return None


def validate_phone_number(phone: str) -> str:
    """Validates international mobile numbers with country code."""
    cleaned = phone.strip()
    if len(cleaned) < 7:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mobile number must be at least 7 digits long, including country code (e.g. +1-555-0199 or +91-9876543210).",
        )
    # Check valid characters: optional leading +, digits, dashes, spaces, parentheses
    if not re.match(r"^\+?[0-9\s\-\.\(\)]{7,30}$", cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid mobile number format. Allowed characters: digits, '+', '-', '(', ')', spaces.",
        )
    digit_count = sum(c.isdigit() for c in cleaned)
    if digit_count < 7:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mobile number must contain at least 7 digits.",
        )
    return cleaned


def mask_phone_number(phone: str) -> str:
    """Masks mobile number for unauthorized or anonymous viewers."""
    if not phone or len(phone) < 6:
        return "*******"
    return phone[:3] + "****" + phone[-3:]


@router.get("", response_model=List[SecurityStaffResponse])
def get_security_staff(
    event_id: Optional[str] = None,
    role: Optional[str] = None,
    duty_status: Optional[str] = None,
    zone: Optional[str] = None,
    search: Optional[str] = None,
    include_inactive: bool = False,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Fetch security personnel and event coordinators from database.
    Strictly isolated by event when event_id is specified.
    Supports filtering by role, duty status, zone, and search by name/mobile.
    """
    user = get_current_user_from_auth(auth, db)
    query = db.query(SecurityStaffModel)

    # Event isolation
    if event_id:
        query = query.filter(SecurityStaffModel.event_id == event_id)

    # Active status filter
    if not include_inactive:
        query = query.filter(SecurityStaffModel.is_active == True)

    # Role filter
    if role and role.strip() and role.lower() != "all":
        query = query.filter(SecurityStaffModel.role == role.strip())

    # Duty status filter
    if duty_status and duty_status.strip() and duty_status.lower() != "all":
        query = query.filter(SecurityStaffModel.duty_status == duty_status.strip())

    # Zone filter
    if zone and zone.strip() and zone.lower() != "all":
        query = query.filter(SecurityStaffModel.zone == zone.strip())

    # Search filter
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(SecurityStaffModel.name).like(term),
                SecurityStaffModel.phone.like(f"%{search.strip()}%"),
                func.lower(SecurityStaffModel.organization).like(term),
            )
        )

    staff_list = query.order_by(SecurityStaffModel.name.asc()).all()

    # Protect phone numbers if user is unauthenticated
    if not user:
        # For public or unauthenticated reads, mask the mobile number
        for s in staff_list:
            s.phone = mask_phone_number(s.phone)

    return staff_list


@router.post("", response_model=SecurityStaffResponse, status_code=status.HTTP_201_CREATED)
def create_security_staff(
    data: SecurityStaffCreate,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Register a new ground personnel record (Security Guard, Event Coordinator, etc.)
    Associates the record with the target event and venue zone.
    """
    # Name validation
    name_clean = data.name.strip()
    if len(name_clean) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Personnel name must be at least 2 characters.",
        )

    # Phone validation
    phone_clean = validate_phone_number(data.phone)

    staff_id = f"staff-{int(time.time() * 1000)}"
    default_avatar = f"https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&fit=crop&q=80"

    new_staff = SecurityStaffModel(
        id=staff_id,
        event_id=data.event_id,
        name=name_clean,
        role=data.role or "Security Guard",
        zone=data.zone or "General",
        organization=data.organization,
        duty_status=data.duty_status or "On Duty",
        is_online=True if (data.duty_status or "On Duty") == "On Duty" else False,
        mobile_status="connected",
        battery=100,
        phone=phone_clean,
        avatar=default_avatar,
        status="idle",
        notes=data.notes,
        is_active=True,
    )

    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)
    return new_staff


@router.get("/{staff_id}", response_model=SecurityStaffResponse)
def get_staff_by_id(
    staff_id: str,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """View details of a specific personnel member."""
    user = get_current_user_from_auth(auth, db)
    staff = db.query(SecurityStaffModel).filter(SecurityStaffModel.id == staff_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Personnel record with ID '{staff_id}' not found.",
        )

    if not user:
        staff.phone = mask_phone_number(staff.phone)

    return staff


@router.put("/{staff_id}", response_model=SecurityStaffResponse)
def update_security_staff(
    staff_id: str,
    data: SecurityStaffUpdate,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Update details of an existing ground personnel member.
    Allows updating role, duty status, assigned zone, phone, or deactivating.
    """
    staff = db.query(SecurityStaffModel).filter(SecurityStaffModel.id == staff_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Personnel record with ID '{staff_id}' not found.",
        )

    if data.name is not None:
        name_clean = data.name.strip()
        if len(name_clean) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Personnel name must be at least 2 characters.",
            )
        staff.name = name_clean

    if data.phone is not None:
        staff.phone = validate_phone_number(data.phone)

    if data.role is not None:
        staff.role = data.role.strip()

    if data.event_id is not None:
        staff.event_id = data.event_id

    if data.zone is not None:
        staff.zone = data.zone.strip()

    if data.organization is not None:
        staff.organization = data.organization.strip()

    if data.duty_status is not None:
        staff.duty_status = data.duty_status.strip()
        if staff.duty_status == "On Duty":
            staff.is_online = True
        elif staff.duty_status in ("Off Duty", "Unavailable"):
            staff.is_online = False

    if data.is_online is not None:
        staff.is_online = data.is_online

    if data.mobile_status is not None:
        staff.mobile_status = data.mobile_status

    if data.battery is not None:
        staff.battery = data.battery

    if data.status is not None:
        staff.status = data.status

    if data.notes is not None:
        staff.notes = data.notes

    if data.is_active is not None:
        staff.is_active = data.is_active
        if not data.is_active:
            staff.duty_status = "Unavailable"
            staff.is_online = False

    db.commit()
    db.refresh(staff)
    return staff


@router.delete("/{staff_id}")
def delete_security_staff(
    staff_id: str,
    hard_delete: bool = False,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Deactivate or remove a ground personnel member.
    By default, sets is_active=False and duty_status='Unavailable'.
    """
    staff = db.query(SecurityStaffModel).filter(SecurityStaffModel.id == staff_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Personnel record with ID '{staff_id}' not found.",
        )

    personnel_name = staff.name
    if hard_delete:
        db.delete(staff)
        db.commit()
        return {
            "success": True,
            "message": f"Personnel '{personnel_name}' permanently deleted.",
            "staff_id": staff_id,
        }
    else:
        staff.is_active = False
        staff.duty_status = "Unavailable"
        staff.is_online = False
        db.commit()
        return {
            "success": True,
            "message": f"Personnel '{personnel_name}' deactivated successfully.",
            "staff_id": staff_id,
            "is_active": False,
        }


# Existing Instruction Logs Endpoints (Preserved for compatibility)
@router.get("/instructions", response_model=List[InstructionLogResponse])
def get_instruction_logs(db: Session = Depends(get_db)):
    """Fetch instruction logs from database."""
    return db.query(InstructionLogModel).order_by(InstructionLogModel.id.desc()).all()


@router.post("/instructions", response_model=InstructionLogResponse, status_code=status.HTTP_201_CREATED)
def create_instruction_log(data: InstructionLogCreate, db: Session = Depends(get_db)):
    """Create new dispatch instruction log in database."""
    inst_id = f"inst-{int(time.time() * 1000)}"
    timestamp_str = datetime.now().strftime("%H:%M:%S")

    db_inst = InstructionLogModel(
        id=inst_id,
        timestamp=timestamp_str,
        recipient=data.recipient,
        type=data.type or "individual",
        priority=data.priority or "normal",
        text=data.text,
        delivery_status="DELIVERED",
        read_status="READ",
    )
    db.add(db_inst)
    db.commit()
    db.refresh(db_inst)
    return db_inst


# Ground Coordination Workspace Guidance Messages
@router.get("/coordination", response_model=List[CoordinationMessageResponse])
def get_coordination_messages(
    event_id: Optional[str] = None,
    zone: Optional[str] = None,
    recipient_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Fetch officer-to-ground-team coordination guidance messages.
    Strictly isolated by event when event_id is specified.
    """
    query = db.query(InstructionLogModel)
    if event_id:
        query = query.filter(InstructionLogModel.event_id == event_id)
    if zone and zone != "all":
        query = query.filter(InstructionLogModel.zone == zone)
    if recipient_id and recipient_id != "all":
        query = query.filter(InstructionLogModel.recipient_id == recipient_id)
    if status_filter and status_filter.lower() != "all":
        query = query.filter(InstructionLogModel.status == status_filter)

    return query.order_by(InstructionLogModel.id.desc()).all()


@router.post("/coordination", response_model=CoordinationMessageResponse, status_code=status.HTTP_201_CREATED)
def create_coordination_message(
    data: CoordinationMessageCreate,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Record an officer-to-ground-team guidance message associated with the event and zone.
    Prevents duplicate submissions via client_mutation_id.
    Truthfully records delivery channel as 'internal' with explicit status.
    """
    user = get_current_user_from_auth(auth, db)
    officer_name = user.name if user and user.name else (user.email if user else "Command Officer")
    officer_id = user.id if user else None

    # Idempotency / Duplicate Prevention Check
    if data.client_mutation_id:
        existing = db.query(InstructionLogModel).filter(
            InstructionLogModel.client_mutation_id == data.client_mutation_id,
            InstructionLogModel.event_id == data.event_id
        ).first()
        if existing:
            return existing

    # Recipient validation: if recipient_id is provided, verify it belongs to this event
    if data.recipient_id:
        staff_rec = db.query(SecurityStaffModel).filter(SecurityStaffModel.id == data.recipient_id).first()
        if staff_rec and staff_rec.event_id and staff_rec.event_id != data.event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipient '{staff_rec.name}' is assigned to another event and cannot receive guidance for event '{data.event_id}'."
            )

    msg_id = f"coord-{int(time.time() * 1000)}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_msg = InstructionLogModel(
        id=msg_id,
        event_id=data.event_id,
        timestamp=timestamp_str,
        recipient=data.recipient,
        recipient_id=data.recipient_id,
        recipient_role=data.recipient_role,
        zone=data.zone,
        camera_id=data.camera_id,
        officer_name=officer_name,
        officer_id=officer_id,
        type="individual" if data.recipient_id else "group",
        priority=data.priority or "normal",
        text=data.text.strip(),
        status=data.status or "Internally Sent",
        delivery_status="DELIVERED",
        read_status="UNREAD",
        channel="internal",
        client_mutation_id=data.client_mutation_id,
        acknowledged_at=None
    )

    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg


@router.put("/coordination/{message_id}/status", response_model=CoordinationMessageResponse)
def update_coordination_status(
    message_id: str,
    data: CoordinationStatusUpdate,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Update lifecycle status of a guidance message (e.g. Acknowledged by ground personnel).
    Truthfully records acknowledgement timestamp when recipient confirms.
    """
    msg = db.query(InstructionLogModel).filter(InstructionLogModel.id == message_id).first()
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coordination message '{message_id}' not found."
        )

    msg.status = data.status
    if data.status == "Acknowledged":
        msg.acknowledged_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg.read_status = "READ"
    elif data.status == "Failed":
        msg.delivery_status = "FAILED"

    db.commit()
    db.refresh(msg)
    return msg


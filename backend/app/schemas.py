from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

# Zone Schemas
class ZoneBase(BaseModel):
    name: str
    code: Optional[str] = None
    capacity: Optional[int] = 500
    zone_type: Optional[str] = "general" # general, gate_area, exit_corridor, restricted, seating, food_court
    coordinates: Optional[str] = None

class ZoneCreate(ZoneBase):
    pass

class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    capacity: Optional[int] = None
    zone_type: Optional[str] = None
    coordinates: Optional[str] = None

class ZoneResponse(ZoneBase):
    id: str
    event_id: str
    current_count: int = 0
    density: float = 0.0
    risk_level: str = "low"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Camera Schemas
class CameraBase(BaseModel):
    name: str
    rtsp_url: str
    location: str
    zone_id: Optional[str] = None
    event_id: Optional[str] = None
    status: Optional[str] = "online"
    enabled: Optional[bool] = True
    resolution: Optional[str] = "1920x1080"
    fps: Optional[int] = 30
    capacity: Optional[int] = 200
    source_type: Optional[str] = "ip_camera" # ip_camera, webcam, video
    source_fps: Optional[float] = 30.0
    processing_fps: Optional[float] = 30.0
    playback_status: Optional[str] = "playing" # playing, paused, stopped, analyzing, ready

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    location: Optional[str] = None
    zone_id: Optional[str] = None
    event_id: Optional[str] = None
    status: Optional[str] = None
    enabled: Optional[bool] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    capacity: Optional[int] = None
    source_type: Optional[str] = None
    source_fps: Optional[float] = None
    processing_fps: Optional[float] = None
    playback_status: Optional[str] = None

class CameraResponse(CameraBase):
    id: str
    last_active: str
    count: Optional[int] = None
    density: Optional[float] = None
    risk: str
    health: str
    source_type: str
    source_fps: float
    processing_fps: float
    playback_status: str
    last_frame_timestamp: Optional[float] = None
    last_frame_seq: Optional[int] = 0

    class Config:
        from_attributes = True

# Alert Schemas
class AlertCreate(BaseModel):
    title: str
    description: str
    level: str
    zone: str
    camera: str

class AlertResponse(BaseModel):
    id: str
    title: str
    description: str
    level: str
    timestamp: str
    zone: str
    camera: str
    resolved: bool

    class Config:
        from_attributes = True

# Event Schemas
class EventCreate(BaseModel):
    title: str
    venue_name: Optional[str] = "Main Venue Complex"
    capacity: int
    staff: Optional[int] = 20
    risk: Optional[str] = "medium"
    start_time: Optional[str] = "08:00 AM"
    end_time: Optional[str] = "08:00 PM"
    limits: Optional[int] = 1000
    map_url: Optional[str] = None
    manager_id: Optional[int] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    venue_name: Optional[str] = None
    capacity: Optional[int] = None
    staff: Optional[int] = None
    risk: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limits: Optional[int] = None
    map_url: Optional[str] = None
    manager_id: Optional[int] = None

class EventResponse(EventCreate):
    id: str
    manager_id: Optional[int] = None

    class Config:
        from_attributes = True

# Venue Architecture Schemas
class VenuePinCreate(BaseModel):
    pin_type: str
    label: str
    x: float
    y: float

class VenuePinResponse(VenuePinCreate):
    id: str
    event_id: str

    class Config:
        from_attributes = True

# Zone Connection Schemas (Al-Oraiqat et al., IEEE Access 2025, Definition 4 & 6)
class ZoneConnectionBase(BaseModel):
    from_zone_id: str
    to_zone_id: str
    bidirectional: Optional[bool] = True
    is_blocked: Optional[bool] = False
    corridor_name: Optional[str] = None
    flow_capacity: Optional[int] = 500

class ZoneConnectionCreate(ZoneConnectionBase):
    pass

class ZoneConnectionUpdate(BaseModel):
    bidirectional: Optional[bool] = None
    is_blocked: Optional[bool] = None
    corridor_name: Optional[str] = None
    flow_capacity: Optional[int] = None

class ZoneConnectionResponse(ZoneConnectionBase):
    id: str
    event_id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SpatialHierarchySummary(BaseModel):
    gates: List[VenuePinResponse] = []
    entrances: List[VenuePinResponse] = []
    exits: List[VenuePinResponse] = []
    emergency_exits: List[VenuePinResponse] = []
    restricted_areas: List[VenuePinResponse] = []
    camera_locations: List[dict] = []
    security_resources: List[dict] = []
    connections: List[ZoneConnectionResponse] = []

class VenueDetailsResponse(BaseModel):
    event_id: str
    event_title: str
    venue_name: Optional[str] = "Main Venue Complex"
    map_url: Optional[str] = None
    pins: List[VenuePinResponse] = []
    zones: List[ZoneResponse] = []
    connections: List[ZoneConnectionResponse] = []
    spatial_architecture: Optional[SpatialHierarchySummary] = None

# Recommendation & FCA Schemas
class RecommendationResponse(BaseModel):
    id: str
    title: str
    priority: str
    reason: str
    confidence: int
    zone: str
    officer: str
    status: str
    override_reason: Optional[str] = None
    destination_zone: Optional[str] = None
    diversion_volume: Optional[float] = None
    is_capacity_verified: Optional[bool] = False

    class Config:
        from_attributes = True

class CapacityReservationResponse(BaseModel):
    id: str
    recommendation_id: str
    event_id: str
    source_zone: str
    destination_zone: str
    diversion_volume: float
    status: str
    approved_by: Optional[str] = None
    reconciliation_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ReservationCompleteRequest(BaseModel):
    reconciliation_notes: Optional[str] = None

class ReservationCancelRequest(BaseModel):
    reason: Optional[str] = None
    confirm_reconciled: Optional[bool] = False
    reconciliation_notes: Optional[str] = None

class ReservationReconcileRequest(BaseModel):
    reconciliation_notes: str
    resolution_action: Literal["halted", "redirected", "dispersed"] = "halted"

# Security Staff & Personnel Directory Schemas
class SecurityStaffBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Full name of the personnel")
    phone: str = Field(..., min_length=7, max_length=50, description="Mobile number including country code")
    role: str = Field(default="Security Guard", description="Security Guard, Event Coordinator, Team Leader, Medical Contact")
    event_id: Optional[str] = Field(default=None, description="Assigned event ID")
    zone: str = Field(default="Main Gate", description="Assigned venue zone, gate, corridor, or sector")
    organization: Optional[str] = Field(default=None, description="Team or organization")
    duty_status: str = Field(default="On Duty", description="On Duty, Off Duty, or Unavailable")
    notes: Optional[str] = Field(default=None, description="Responsibilities and notes")

class SecurityStaffCreate(SecurityStaffBase):
    pass

class SecurityStaffUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    event_id: Optional[str] = None
    zone: Optional[str] = None
    organization: Optional[str] = None
    duty_status: Optional[str] = None
    is_online: Optional[bool] = None
    mobile_status: Optional[str] = None
    battery: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class SecurityStaffResponse(SecurityStaffBase):
    id: str
    is_online: bool = True
    mobile_status: str = "connected"
    battery: int = 100
    avatar: Optional[str] = None
    status: str = "idle"
    is_active: bool = True

    class Config:
        from_attributes = True

class InstructionLogCreate(BaseModel):
    recipient: str
    type: Optional[str] = "individual"
    priority: Optional[str] = "normal"
    text: str
    event_id: Optional[str] = None
    zone: Optional[str] = None
    recipient_id: Optional[str] = None
    recipient_role: Optional[str] = None
    camera_id: Optional[str] = None
    client_mutation_id: Optional[str] = None

class InstructionLogResponse(InstructionLogCreate):
    id: str
    timestamp: str
    delivery_status: str
    read_status: str
    status: Optional[str] = "Internally Sent"
    officer_name: Optional[str] = None
    channel: Optional[str] = "internal"
    acknowledged_at: Optional[str] = None

    class Config:
        from_attributes = True

# Ground Coordination Guidance Message Schemas
class CoordinationMessageCreate(BaseModel):
    recipient_id: Optional[str] = None
    recipient: str = Field(..., min_length=1, description="Recipient name or broadcast group")
    recipient_role: Optional[str] = None
    event_id: str = Field(..., description="Target event ID for strict event isolation")
    zone: str = Field(..., min_length=1, description="Venue zone, gate, or corridor")
    camera_id: Optional[str] = None
    priority: Literal["normal", "high", "critical"] = "normal"
    text: str = Field(..., min_length=2, description="Operational guidance message")
    status: Optional[str] = "Internally Sent"
    channel: Optional[str] = "internal"
    client_mutation_id: Optional[str] = Field(None, description="Idempotency key for duplicate prevention")

class CoordinationStatusUpdate(BaseModel):
    status: Literal["Draft", "Queued", "Internally Sent", "Acknowledged", "Failed"]

class CoordinationMessageResponse(BaseModel):
    id: str
    event_id: Optional[str] = None
    timestamp: str
    recipient: str
    recipient_id: Optional[str] = None
    recipient_role: Optional[str] = None
    zone: Optional[str] = None
    camera_id: Optional[str] = None
    officer_name: Optional[str] = None
    officer_id: Optional[int] = None
    type: str = "individual"
    priority: str = "normal"
    text: str
    status: str = "Internally Sent"
    delivery_status: str = "DELIVERED"
    read_status: str = "READ"
    channel: str = "internal"
    client_mutation_id: Optional[str] = None
    acknowledged_at: Optional[str] = None

    class Config:
        from_attributes = True

# Emergency Log & Dispatch Schemas
class EmergencyCreate(BaseModel):
    type: str
    location: str
    description: str

class EmergencyResponse(BaseModel):
    id: str
    timestamp: str
    type: str
    location: str
    description: str
    police_status: str
    medical_status: str
    fire_status: str
    is_active: bool

    class Config:
        from_attributes = True

class EmergencyDispatchResponse(BaseModel):
    id: str
    emergency_event_id: str
    service_type: str
    camera_id: str
    location: str
    zone: str
    message: str
    assigned_staff_id: Optional[str] = None
    staff_name: Optional[str] = None
    timestamp: str
    status: str

    class Config:
        from_attributes = True

class EmergencyEventResponse(BaseModel):
    id: str
    camera_id: str
    incident_type: str
    severity: str
    crowd_count: int
    density_pct: float
    occupancy_pct: float
    location: str
    zone: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reason: str
    detected_at: str
    status: str
    created_at: str
    resolved_at: Optional[str] = None
    dispatches: List[EmergencyDispatchResponse] = []

    class Config:
        from_attributes = True

# System Settings Schemas
class SettingsSchema(BaseModel):
    ai_sensitivity: Optional[int] = 75
    crowd_threshold: Optional[int] = 85
    sound_alerts: Optional[bool] = True
    auto_escalation: Optional[bool] = False
    fca_auto_recommendation: Optional[bool] = False
    language: Optional[str] = "English"
    theme: Optional[str] = "dark"

    class Config:
        from_attributes = True

# Analytics & Heatmap Schemas
class LiveStatusResponse(BaseModel):
    system_status: str
    active_cameras: int
    total_count: int
    average_density: float
    system_risk_level: str
    timestamp: str

class HeatmapResponse(BaseModel):
    camera_id: str
    timestamp: str
    peak_density: float
    heatmap_base64: str
    image: Optional[str] = None

# Auth & User Schemas
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: Optional[str] = None
    role: Optional[str] = None

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    token: Optional[str] = None
    message: Optional[str] = None

class OnboardingStatusResponse(BaseModel):
    has_event: bool
    event: Optional[EventResponse] = None
    has_source: bool
    source_count: int = 0
    cameras: List[CameraResponse] = []
    status: str # "needs_event" | "needs_source" | "complete"
    next_route: str # "/event-setup" | "/camera-setup" | "/dashboard"

# Offline Video Analysis Job Schemas
class OfflineJobCreate(BaseModel):
    filename: str

class OfflineJobResponse(BaseModel):
    id: str
    filename: str
    status: str
    progress: int
    duration: str
    resolution: str
    file_size_mb: float
    total_frames: int
    frames_processed: int
    processing_fps: float
    peak_count: int
    avg_count: float
    peak_density: float
    risk_summary: str
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# FCA Lattice Schemas
class FCANode(BaseModel):
    id: str
    label: str
    extent: List[str]
    intent: List[str]
    x: float
    y: float
    formula: str
    action: str
    confidence: int

class FCALink(BaseModel):
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")

    class Config:
        populate_by_name = True

class FCALatticeResponse(BaseModel):
    objects: List[str]
    attributes: List[dict]
    nodes: List[FCANode]
    connections: List[FCALink]
    recommendations: List[RecommendationResponse]

# Base Paper IEEE Access 2025: Research Models
class CrowdedAreaResult(BaseModel):
    area: str
    crowd_score: float
    concept_id: str
    satisfied_intent: List[str]
    attribute_scores: dict
    is_crowded: bool
    reason: str

class PreventionPlanItem(BaseModel):
    plan_id: str
    crowded_sources: List[str]
    recommended_destinations: List[str]
    concept_id: str
    concept_extent: List[str]
    concept_intent: List[str]
    status: str = "pending_human_approval"
    mitigation_capacity: int = 0
    reason: str
    is_verified_evacuation: bool = False
    warning: Optional[str] = None
    is_capacity_verified: bool = False
    diversion_volume: Optional[float] = None

class PreventionPlanResponse(BaseModel):
    event_id: Optional[str] = None
    total_crowded_areas: int
    resolved_count: int
    unresolved_areas: List[str] = []
    plans: List[PreventionPlanItem] = []
    timestamp: str

class ResearchLatticeResponse(BaseModel):
    event_id: Optional[str] = None
    crowd_lattice: FCALatticeResponse
    area_lattice: FCALatticeResponse
    fuzzy_context_summary: dict
    crowded_areas: List[CrowdedAreaResult] = []
    prevention_plans: List[PreventionPlanItem] = []


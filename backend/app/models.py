from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="Officer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ZoneModel(Base):
    __tablename__ = "zones"
    
    id = Column(String(100), primary_key=True, index=True)
    event_id = Column(String(100), ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True) # e.g. "ZONE-A", "GATE-NORTH"
    capacity = Column(Integer, default=500)
    current_count = Column(Integer, default=0)
    density = Column(Float, default=0.0)
    risk_level = Column(String(50), default="low") # low, medium, high, critical
    zone_type = Column(String(50), default="general") # general, gate_area, exit_corridor, restricted, seating, food_court
    coordinates = Column(Text, nullable=True) # JSON coordinates or boundary
    created_at = Column(DateTime, default=datetime.utcnow)

class CameraModel(Base):
    __tablename__ = "cameras"
    
    id = Column(String(100), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    rtsp_url = Column(String(500), nullable=False)
    location = Column(String(255), nullable=False)
    zone_id = Column(String(100), nullable=True) # Assigned zone identifier
    event_id = Column(String(100), nullable=True) # Assigned event identifier
    status = Column(String(50), default="online")
    enabled = Column(Boolean, default=True)
    resolution = Column(String(50), default="1920x1080")
    fps = Column(Integer, default=30)
    last_active = Column(String(100), default="Just now")
    capacity = Column(Integer, default=200)
    count = Column(Integer, default=0)
    density = Column(Float, default=0.0)
    risk = Column(String(50), default="low")
    health = Column(String(50), default="green")
    source_type = Column(String(50), default="ip_camera") # ip_camera, webcam, video
    source_fps = Column(Float, default=30.0)
    processing_fps = Column(Float, default=30.0)
    playback_status = Column(String(50), default="playing") # playing, paused, stopped, analyzing, ready
    last_frame_timestamp = Column(Float, nullable=True, default=None)
    last_frame_seq = Column(Integer, nullable=True, default=0)

class EventModel(Base):
    __tablename__ = "events"
    
    id = Column(String(100), primary_key=True, index=True)
    manager_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    title = Column(String(255), nullable=False)
    venue_name = Column(String(255), default="Main Venue Complex")
    capacity = Column(Integer, nullable=False)
    staff = Column(Integer, default=20)
    risk = Column(String(50), default="medium")
    start_time = Column(String(100), default="08:00 AM")
    end_time = Column(String(100), default="08:00 PM")
    limits = Column(Integer, default=1000)
    map_url = Column(Text, nullable=True)

class VenuePinModel(Base):
    __tablename__ = "venue_pins"
    
    id = Column(String(100), primary_key=True, index=True)
    event_id = Column(String(100), ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    pin_type = Column(String(50), nullable=False) # gate_entry, gate_exit, emergency_exit, security, medical, fire, restricted, camera
    label = Column(String(255), nullable=False)
    x = Column(Float, nullable=False) # relative percentage (0.0 to 100.0)
    y = Column(Float, nullable=False) # relative percentage (0.0 to 100.0)

class CrowdAnalyticsModel(Base):
    __tablename__ = "crowd_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    camera_id = Column(String(100), index=True)
    event_id = Column(String(100), index=True, nullable=True)
    count = Column(Integer, nullable=False)
    density_pct = Column(Float, nullable=False)
    risk_level = Column(String(50), nullable=False)
    flow_rate = Column(Float, default=0.0)
    speed_avg = Column(Float, default=1.2)

class AlertModel(Base):
    __tablename__ = "alerts"
    
    id = Column(String(100), primary_key=True, index=True)
    event_id = Column(String(100), index=True, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    level = Column(String(50), nullable=False)
    timestamp = Column(String(100), nullable=False)
    zone = Column(String(255), nullable=False)
    camera = Column(String(255), nullable=False)
    resolved = Column(Boolean, default=False)

class SecurityStaffModel(Base):
    __tablename__ = "security_staff"
    
    id = Column(String(100), primary_key=True, index=True)
    event_id = Column(String(100), index=True, nullable=True)
    name = Column(String(255), nullable=False)
    role = Column(String(100), default="Security Guard", nullable=False)
    zone = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=True)
    duty_status = Column(String(50), default="On Duty", nullable=False)
    is_online = Column(Boolean, default=True)
    mobile_status = Column(String(50), default="connected")
    battery = Column(Integer, default=100)
    phone = Column(String(50), nullable=False)
    avatar = Column(Text, nullable=True)
    status = Column(String(50), default="idle")
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)


class InstructionLogModel(Base):
    __tablename__ = "instruction_logs"
    
    id = Column(String(100), primary_key=True, index=True)
    event_id = Column(String(100), index=True, nullable=True)
    timestamp = Column(String(100), nullable=False)
    recipient = Column(String(255), nullable=False)
    recipient_id = Column(String(100), nullable=True)
    recipient_role = Column(String(100), nullable=True)
    zone = Column(String(255), nullable=True)
    camera_id = Column(String(100), nullable=True)
    officer_name = Column(String(255), nullable=True)
    officer_id = Column(Integer, nullable=True)
    type = Column(String(50), default="individual")
    priority = Column(String(50), default="normal")
    text = Column(Text, nullable=False)
    status = Column(String(50), default="Internally Sent")
    delivery_status = Column(String(50), default="DELIVERED")
    read_status = Column(String(50), default="READ")
    channel = Column(String(50), default="internal")
    client_mutation_id = Column(String(100), index=True, nullable=True)
    acknowledged_at = Column(String(100), nullable=True)


class RecommendationModel(Base):
    __tablename__ = "recommendations"
    
    id = Column(String(100), primary_key=True, index=True)
    event_id = Column(String(100), index=True, nullable=True)
    title = Column(String(255), nullable=False)
    priority = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    confidence = Column(Integer, nullable=False)
    zone = Column(String(255), nullable=False)
    officer = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")
    override_reason = Column(Text, nullable=True)
    destination_zone = Column(String(255), nullable=True)
    diversion_volume = Column(Float, nullable=True)
    is_capacity_verified = Column(Boolean, default=False)

class CapacityReservationModel(Base):
    __tablename__ = "capacity_reservations"
    
    id = Column(String(100), primary_key=True, index=True)
    recommendation_id = Column(String(100), ForeignKey("recommendations.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    event_id = Column(String(100), ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    source_zone = Column(String(255), nullable=False)
    destination_zone = Column(String(255), index=True, nullable=False)
    diversion_volume = Column(Float, nullable=False)
    status = Column(String(50), default="approved", nullable=False)  # approved, in_transit, completed, cancelled, rejected
    approved_by = Column(String(255), nullable=True)
    reconciliation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ReportModel(Base):
    __tablename__ = "reports"
    
    id = Column(String(100), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text, nullable=False)

class EmergencyLogModel(Base):
    __tablename__ = "emergency_logs"
    
    id = Column(String(100), primary_key=True, index=True)
    timestamp = Column(String(100), nullable=False)
    type = Column(String(100), nullable=False)
    location = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    police_status = Column(String(50), default="none")
    medical_status = Column(String(50), default="none")
    fire_status = Column(String(50), default="none")
    is_active = Column(Boolean, default=True)

class EmergencyEventModel(Base):
    __tablename__ = "emergency_events"
    
    id = Column(String(100), primary_key=True, index=True)
    event_id = Column(String(100), index=True, nullable=True)
    camera_id = Column(String(100), index=True, nullable=False)
    incident_type = Column(String(100), nullable=False)
    severity = Column(String(50), default="CRITICAL")
    crowd_count = Column(Integer, default=0)
    density_pct = Column(Float, default=0.0)
    occupancy_pct = Column(Float, default=0.0)
    location = Column(String(255), nullable=False)
    zone = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    reason = Column(Text, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="DETECTED")  # DETECTED, ACKNOWLEDGED, DISPATCHED, ARRIVED, RESOLVED
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class EmergencyDispatchModel(Base):
    __tablename__ = "emergency_dispatches"
    
    id = Column(String(100), primary_key=True, index=True)
    emergency_event_id = Column(String(100), ForeignKey("emergency_events.id", ondelete="CASCADE"), index=True, nullable=False)
    service_type = Column(String(50), nullable=False)  # medical, police, fire, security, control_room
    camera_id = Column(String(100), nullable=False)
    location = Column(String(255), nullable=False)
    zone = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    assigned_staff_id = Column(String(100), nullable=True)
    staff_name = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="DISPATCHED")  # REQUESTED, DISPATCHED, ARRIVED, RESOLVED

class HeatmapHistoryModel(Base):
    __tablename__ = "heatmap_history"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    camera_id = Column(String(100), index=True)
    heatmap_base64 = Column(Text, nullable=False)
    peak_density = Column(Float, nullable=False)

class SettingsModel(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, default=1)
    ai_sensitivity = Column(Integer, default=75)
    crowd_threshold = Column(Integer, default=85)
    sound_alerts = Column(Boolean, default=True)
    auto_escalation = Column(Boolean, default=False)
    fca_auto_recommendation = Column(Boolean, default=False)
    language = Column(String(50), default="English")
    theme = Column(String(50), default="dark")

class OfflineAnalysisJobModel(Base):
    __tablename__ = "offline_analysis_jobs"
    
    id = Column(String(100), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    status = Column(String(50), default="queued")  # queued, processing, completed, failed
    progress = Column(Integer, default=0)
    duration = Column(String(50), default="00:00:00")
    resolution = Column(String(50), default="1920x1080")
    file_size_mb = Column(Float, default=0.0)
    total_frames = Column(Integer, default=0)
    frames_processed = Column(Integer, default=0)
    processing_fps = Column(Float, default=0.0)
    peak_count = Column(Integer, default=0)
    avg_count = Column(Float, default=0.0)
    peak_density = Column(Float, default=0.0)
    risk_summary = Column(String(50), default="LOW")
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class ZoneConnectionModel(Base):
    """
    Physical area connectivity graph edge representing actual passages/corridors
    between zones (Al-Oraiqat et al., IEEE Access 2025, Definitions 4 & 6).
    """
    __tablename__ = "zone_connections"
    
    id = Column(String(100), primary_key=True, index=True)
    event_id = Column(String(100), ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    from_zone_id = Column(String(100), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    to_zone_id = Column(String(100), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    bidirectional = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    corridor_name = Column(String(255), nullable=True)
    flow_capacity = Column(Integer, default=500)
    created_at = Column(DateTime, default=datetime.utcnow)

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import asyncio
import json
import logging
import time
from datetime import datetime

from app.database import SessionLocal
from app.models import (
    CameraModel, 
    AlertModel, 
    CrowdAnalyticsModel, 
    HeatmapHistoryModel, 
    EmergencyEventModel, 
    EmergencyDispatchModel, 
    SecurityStaffModel,
    ZoneModel,
    EventModel,
    SettingsModel,
    RecommendationModel
)
from app.ai.detector import detector
from app.ai.density import CrowdDensityEvaluator, MultiCameraAggregator
from app.ai.heatmap import heatmap_manager, global_heatmap_gen
from app.ai.fca_engine import fca_solver
from app.ai.risk_engine import risk_engine
from app.ai.stream_processor import stream_manager

logger = logging.getLogger("uvicorn")
router = APIRouter(tags=["WebSockets"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[WEBSOCKET] Client connected. Total active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"[WEBSOCKET] Client disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Persistence tracking for anti-noise false positive protection
camera_surge_persistence: Dict[str, int] = {}
recent_counts_history: List[float] = []

async def start_ai_processing_loop():
    """
    Asynchronous background worker running OpenCV + YOLO inference,
    multi-sensor Area/Zone Intelligence aggregation, Settings integration,
    and WebSocket broadcasting.
    """
    t = 0.0
    frame_counter = 0

    logger.info("[AI][ENGINE] Python OpenCV + YOLO AI Processing Engine Initialized.")
    logger.info("[AI][ENGINE] Background crowd surveillance processing running silently...")

    while True:
        await asyncio.sleep(0.3)  # Broadcast every 300ms (~3.3 FPS live telemetry)
        t += 0.3
        frame_counter += 1

        db = SessionLocal()
        try:
            # 1. Fetch system settings to affect runtime behavior
            sys_settings = db.query(SettingsModel).filter(SettingsModel.id == 1).first()
            crowd_threshold = float(sys_settings.crowd_threshold if sys_settings else 85.0)
            ai_sensitivity = int(sys_settings.ai_sensitivity if sys_settings else 75)
            auto_escalate = bool(sys_settings.auto_escalation if sys_settings else False)
            fca_auto_approve = bool(sys_settings.fca_auto_recommendation if sys_settings else False)

            # Map AI sensitivity (10-100) to detector confidence threshold (0.15 to 0.70)
            conf_threshold = round(max(0.15, min(0.70, 0.85 - (ai_sensitivity / 100.0) * 0.60)), 2)
            if hasattr(detector, "set_confidence_threshold"):
                detector.set_confidence_threshold(conf_threshold)

            cameras = db.query(CameraModel).all()
            alerts = db.query(AlertModel).all()
            zones = db.query(ZoneModel).all()
            events = db.query(EventModel).all()

            analyzing_cams = [
                c for c in cameras 
                if c.enabled and c.status == "online" and c.playback_status in ["analyzing", "playing"]
            ]

            # Ingestion owner synchronization: stop workers for cameras explicitly stopped, disabled, or deleted
            all_cam_map = {c.id: c for c in cameras}
            for active_cam_id in list(stream_manager.workers.keys()):
                cam_rec = all_cam_map.get(active_cam_id)
                if cam_rec is None or cam_rec.playback_status in ["stopped", "error"] or not cam_rec.enabled:
                    stream_manager.stop_worker(active_cam_id)

            active_emergency_event = None
            active_dispatches = []

            # 2. Process real computer vision detections for analyzing cameras
            if analyzing_cams:
                for cam in analyzing_cams:
                    worker = stream_manager.workers.get(cam.id)

                    if not worker and cam.rtsp_url and cam.playback_status in ["analyzing", "playing"]:
                        try:
                            worker = stream_manager.get_or_create_worker(
                                cam.id, cam.rtsp_url, cam.source_type or "video", cam.capacity or 200, cam.event_id
                            )
                        except Exception as worker_err:
                            logger.error(f"[AI][WORKER] Failed to start worker for camera {cam.id}: {worker_err}")
                            worker = None

                    if worker and worker.is_running and not worker.is_paused:
                        # Use REAL frame detection metrics from stream worker
                        cam.count = worker.last_count
                        cam.density = worker.last_density
                        cam.risk = worker.last_risk
                        cam.health = CrowdDensityEvaluator.evaluate_health(cam.status, cam.density)
                        cam.source_fps = worker.source_fps
                        cam.processing_fps = worker.processing_fps

                        # Trustworthy frame health signal
                        worker_obs_ts = getattr(worker, "last_observation_timestamp", 0.0)
                        worker_frame_seq = getattr(worker, "frame_seq", 0)
                        if worker_obs_ts > 0.0 and worker_frame_seq > 0:
                            cam.last_frame_timestamp = float(worker_obs_ts)
                            cam.last_frame_seq = int(worker_frame_seq)

                        if frame_counter % 10 == 0:
                            boxes_cnt = len(getattr(worker, 'latest_boxes', []))
                            active_cnt = len(getattr(worker, 'active_tracks', []))
                            print(f"[AI-E2E][TELEMETRY] camera_id={cam.id} event_id={cam.event_id} frame_seq={getattr(worker, 'frame_seq', 0)} yolo_count={cam.count} tracked_count={active_cnt} density={cam.density}% risk={cam.risk}")

                        # Accumulate points into camera and zone heatmaps
                        if hasattr(worker, "last_annotated_frame") and worker.prev_centroids:
                            fake_boxes = [[cx - 15, cy - 15, cx + 15, cy + 15, 0.85] for cx, cy in worker.prev_centroids]
                            heatmap_manager.accumulate_camera_boxes(cam.id, fake_boxes, cam.zone_id)

                        # Check anti-noise threshold using configured runtime crowd_threshold
                        is_over_threshold = (cam.density or 0.0) >= crowd_threshold or str(cam.risk).upper() in ["HIGH", "CRITICAL"]
                        if is_over_threshold:
                            camera_surge_persistence[cam.id] = camera_surge_persistence.get(cam.id, 0) + 1
                        else:
                            camera_surge_persistence[cam.id] = max(0, camera_surge_persistence.get(cam.id, 0) - 1)

                        # Trigger real AI Emergency / Alert when threshold is sustained
                        snap_density = float(cam.density or 0.0)
                        snap_count = int(cam.count or 0)
                        snap_location = str(cam.location or cam.name)
                        snap_zone = str(cam.location or cam.name)
                        snap_name = str(cam.name)

                        if camera_surge_persistence.get(cam.id, 0) >= 3:
                            # 1. Critical Emergency Event if density exceeds crowd_threshold or risk is CRITICAL
                            if snap_density >= crowd_threshold or str(cam.risk).upper() == "CRITICAL":
                                existing_emg = db.query(EmergencyEventModel).filter(
                                    EmergencyEventModel.camera_id == cam.id,
                                    EmergencyEventModel.status != "RESOLVED"
                                ).first()

                                if not existing_emg:
                                    emg_id = f"emg-evt-{int(time.time() * 1000)}"
                                    inc_type = "CRITICAL CROWD SURGE" if snap_density >= 90.0 else "SEVERE OVERCROWDING"
                                    snap_reason = f"Automated AI Detection: Density reached {snap_density}% (Threshold: {crowd_threshold}%) with {snap_count} persons at {snap_name}. Awaiting Operator Dispatch Approval."

                                    new_emg = EmergencyEventModel(
                                        id=emg_id,
                                        event_id=cam.event_id,
                                        camera_id=cam.id,
                                        incident_type=inc_type,
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
                                    db.add(new_emg)

                            # 2. Risk Alert (Critical or Warning)
                            alert_lvl = "critical" if (snap_density >= crowd_threshold or str(cam.risk).upper() == "CRITICAL") else "warning"
                            alert_title = f"🚨 CRITICAL OVERCROWDING: {snap_name}" if alert_lvl == "critical" else f"⚠️ HIGH CROWD DENSITY: {snap_name}"
                            alert_desc = f"Observed density {snap_density}% ({snap_count} detections) at {snap_location}. Safety threshold: {crowd_threshold}%."

                            existing_alert = db.query(AlertModel).filter(
                                AlertModel.camera == snap_name,
                                AlertModel.resolved == False
                            ).first()
                            if existing_alert:
                                existing_alert.level = alert_lvl
                                existing_alert.description = alert_desc
                                existing_alert.timestamp = datetime.now().strftime("%H:%M:%S")
                            else:
                                db_alert = AlertModel(
                                    id=f"alert-{int(time.time() * 1000)}",
                                    event_id=cam.event_id,
                                    title=alert_title,
                                    description=alert_desc,
                                    level=alert_lvl,
                                    timestamp=datetime.now().strftime("%H:%M:%S"),
                                    zone=snap_location,
                                    camera=snap_name,
                                    resolved=False
                                )
                                db.add(db_alert)
                            db.commit()

                        elif camera_surge_persistence.get(cam.id, 0) == 0 and str(cam.risk).upper() == "LOW":
                            # Auto-recovery: mark alerts resolved when conditions return to safe low density
                            active_alerts_for_cam = db.query(AlertModel).filter(
                                AlertModel.camera == snap_name,
                                AlertModel.resolved == False
                            ).all()
                            for al in active_alerts_for_cam:
                                al.resolved = True
                            if active_alerts_for_cam:
                                db.commit()

                        # Persist periodic analytics snapshot
                        if frame_counter % 10 == 0:
                            analytics_row = CrowdAnalyticsModel(
                                camera_id=cam.id,
                                event_id=cam.event_id,
                                count=cam.count,
                                density_pct=cam.density,
                                risk_level=cam.risk,
                                flow_rate=getattr(worker, "last_flow_rate", 0.0),
                                speed_avg=getattr(worker, "last_speed_avg", 0.0)
                            )
                            db.add(analytics_row)
                            db.commit()


            # 3. MULTI-SENSOR AREA INTELLIGENCE: Aggregate Camera -> Zone -> Venue
            # 3. MULTI-SENSOR AREA INTELLIGENCE: Aggregate Camera -> Zone -> Venue
            zone_telemetry = []
            for z in zones:
                # Find cameras belonging to this zone
                zone_cams = [
                    c for c in analyzing_cams 
                    if (c.zone_id == z.id) or (z.name.lower() in (c.location or "").lower()) or (z.code and z.code.lower() in (c.location or "").lower())
                ]
                
                # Multi-sensor aggregation with explicit FOV overlap handling
                zone_cam_counts = [c.count for c in zone_cams if c.count is not None]
                zone_agg = MultiCameraAggregator.aggregate_zone_detections(zone_cam_counts, overlap_ratio=0.15)
                
                z_raw_detections = zone_agg["aggregated_detections"]
                z_estimated_occupancy = zone_agg["estimated_zone_count"]
                z_density = CrowdDensityEvaluator.calculate_zone_density(z_estimated_occupancy, z.capacity or 500)
                z_cam_risks = [c.risk for c in zone_cams]
                
                # Check for active alerts in this zone
                z_unresolved_alerts = sum(1 for a in alerts if not a.resolved and (z.name.lower() in a.zone.lower() or a.zone.lower() in z.name.lower()))
                
                _, z_risk, _ = risk_engine.calculate_zone_risk(
                    z_density, 
                    z_cam_risks, 
                    unresolved_alerts_count=z_unresolved_alerts
                )

                # Update in DB
                z.current_count = z_estimated_occupancy
                z.density = z_density
                z.risk_level = z_risk

                zone_telemetry.append({
                    "id": z.id,
                    "event_id": z.event_id,
                    "name": z.name,
                    "code": z.code,
                    "capacity": z.capacity,
                    "current_count": z_estimated_occupancy,
                    "sensor_derived_count": z_raw_detections,
                    "estimated_zone_count": z_estimated_occupancy,
                    "density": z_density,
                    "risk_level": z_risk,
                    "zone_type": z.zone_type,
                    "assigned_cameras_count": len(zone_cams),
                    "is_monitored": len(zone_cams) > 0,
                    "monitoring_status": "healthy" if len(zone_cams) > 0 else "unmonitored",
                    "has_unique_tracking": False,
                    "fov_overlap_discount_pct": zone_agg["fov_overlap_discount_pct"]
                })

            db.commit()

            # Venue-Wide Multi-Sensor Aggregation
            total_raw_detections = sum(c.count for c in analyzing_cams if c.count is not None)
            total_estimated_occupancy = sum(z["estimated_zone_count"] for z in zone_telemetry) if zone_telemetry else total_raw_detections
            total_active_cams = len(analyzing_cams)
            avg_cam_density = (sum(c.density for c in analyzing_cams if c.density is not None) / total_active_cams) if total_active_cams else 0.0

            # Empirical Trend & Crowd Accumulation Analysis from real observations
            recent_counts_history.append(float(total_estimated_occupancy))
            if len(recent_counts_history) > 20:
                recent_counts_history.pop(0)
            detailed_trend = CrowdDensityEvaluator.calculate_detailed_trend(recent_counts_history)
            trend_category = detailed_trend["density_trend"]
            growth_rate = detailed_trend["growth_rate"]

            # Check active emergencies
            has_active_emg = db.query(EmergencyEventModel).filter(EmergencyEventModel.status != "RESOLVED").count() > 0

            # Evaluate transparent area-wide risk
            cam_dicts = [c.__dict__ for c in analyzing_cams]
            alert_dicts = [a.__dict__ for a in alerts]
            zone_dicts = zone_telemetry if zone_telemetry else [z.__dict__ for z in zones]
            sys_risk_score, sys_risk_cat = risk_engine.evaluate_system_risk(
                cam_dicts, 
                alert_dicts, 
                zones=zone_dicts,
                zone_dicts=zone_dicts, 
                has_active_emergency=has_active_emg,
                trend_analysis=detailed_trend,
                crowd_threshold=crowd_threshold
            )

            # CORRECTION: FCA recommendations must NEVER be automatically approved.
            # The correct behavior is: FCA -> generate/highlight recommendation -> authorized operator reviews -> operator approves/rejects/overrides.
            # High confidence highlights or elevates priority for operator review, but NEVER auto-approves.
            if fca_auto_approve and frame_counter % 15 == 0:
                pending_high_conf = db.query(RecommendationModel).filter(
                    RecommendationModel.status == "pending",
                    RecommendationModel.confidence >= 90
                ).all()
                for rec in pending_high_conf:
                    rec.priority = "critical" if rec.confidence >= 95 else "high"
                db.commit()

            # Active emergency details
            active_emg = db.query(EmergencyEventModel).filter(EmergencyEventModel.status != "RESOLVED").order_by(EmergencyEventModel.created_at.desc()).first()
            if active_emg:
                disps = db.query(EmergencyDispatchModel).filter(EmergencyDispatchModel.emergency_event_id == active_emg.id).all()
                active_emergency_event = {
                    "id": active_emg.id,
                    "event_id": active_emg.event_id,
                    "camera_id": active_emg.camera_id,
                    "incident_type": active_emg.incident_type,
                    "severity": active_emg.severity,
                    "crowd_count": active_emg.crowd_count,
                    "density_pct": active_emg.density_pct,
                    "occupancy_pct": active_emg.occupancy_pct,
                    "location": active_emg.location,
                    "zone": active_emg.zone,
                    "reason": active_emg.reason,
                    "detected_at": active_emg.detected_at.strftime("%H:%M:%S") if hasattr(active_emg.detected_at, "strftime") else str(active_emg.detected_at),
                    "status": active_emg.status
                }
                active_dispatches = [
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
                    } for d in disps
                ]

            active_emergency_count = db.query(EmergencyEventModel).filter(EmergencyEventModel.status != "RESOLVED").count()
            heatmap_base64 = heatmap_manager.area_generator.generate_base64_heatmap()

            # Hardware runtime environment
            hardware_info = detector.get_runtime_engine_info()

            # Authoritative event capacity lookup (prioritize active event over hardcoded defaults)
            active_evt_cap = None
            if analyzing_cams:
                first_cam_evt = next((c.event_id for c in analyzing_cams if c.event_id), None)
                if first_cam_evt:
                    matched_evt = next((e for e in events if e.id == first_cam_evt), None)
                    if matched_evt and matched_evt.capacity and matched_evt.capacity > 0:
                        active_evt_cap = int(matched_evt.capacity)

            if not active_evt_cap and events:
                first_valid_evt = next((e for e in events if e.capacity and e.capacity > 0), None)
                if first_valid_evt:
                    active_evt_cap = int(first_valid_evt.capacity)

            authoritative_total_capacity = active_evt_cap if active_evt_cap else (
                sum(z["capacity"] for z in zone_telemetry) if zone_telemetry else 5000
            )

            # Complete Area-Wide Telemetry Payload
            payload = {
                "type": "TELEMETRY_UPDATE",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "total_count": total_estimated_occupancy,
                "sensor_derived_count": total_raw_detections,
                "aggregated_detections": total_raw_detections,
                "estimated_area_count": total_estimated_occupancy,
                "has_unique_tracking": False,
                "average_density": round(avg_cam_density, 1),
                "risk_score": sys_risk_score,
                "risk_category": sys_risk_cat,
                "density_trend": trend_category,
                "growth_rate_pct": growth_rate,
                "trend_analysis": detailed_trend,
                "active_emergencies_count": active_emergency_count,
                "active_emergency_event": active_emergency_event,
                "emergency_dispatches": active_dispatches,
                "active_alerts_count": len([a for a in alerts if not a.resolved]),
                "heatmap_base64": heatmap_base64,
                "hardware_info": hardware_info,
                "zones": zone_telemetry,
                "area_summary": {
                    "total_count": total_estimated_occupancy,
                    "sensor_derived_count": total_raw_detections,
                    "estimated_area_count": total_estimated_occupancy,
                    "total_capacity": authoritative_total_capacity,
                    "average_density": round(avg_cam_density, 1),
                    "overall_risk": sys_risk_cat.lower(),
                    "high_risk_zones_count": sum(1 for z in zone_telemetry if str(z["risk_level"]).lower() in ["high", "critical"]),
                    "active_cameras_count": total_active_cams
                },
                "cameras": [
                    {
                        "id": c.id,
                        "event_id": c.event_id,
                        "name": c.name,
                        "location": c.location,
                        "zone_id": c.zone_id,
                        "count": c.count if c.enabled and c.playback_status in ["analyzing", "playing"] else 0,
                        "raw_detection_count": getattr(stream_manager.workers.get(c.id), "yolo_detection_count", c.count or 0),
                        "tracked_count": getattr(stream_manager.workers.get(c.id), "tracker_track_count", c.count or 0),
                        "detection_age_frames": getattr(stream_manager.workers.get(c.id), "last_detection_age_frames", 0),
                        "frame_seq": getattr(stream_manager.workers.get(c.id), "frame_seq", 0),
                        "observation_timestamp": datetime.fromtimestamp(getattr(stream_manager.workers.get(c.id), "last_observation_timestamp", time.time())).strftime("%H:%M:%S") if c.id in stream_manager.workers else datetime.now().strftime("%H:%M:%S"),
                        "density": c.density if c.enabled and c.playback_status in ["analyzing", "playing"] else 0.0,
                        "risk": c.risk if c.enabled and c.playback_status in ["analyzing", "playing"] else "low",
                        "health": c.health if c.enabled and c.playback_status in ["analyzing", "playing"] else "green",
                        "enabled": c.enabled,
                        "status": c.status,
                        "source_type": getattr(c, "source_type", "ip_camera"),
                        "playback_status": getattr(c, "playback_status", "ready"),
                        "source_fps": getattr(stream_manager.workers.get(c.id), "source_fps", getattr(c, "source_fps", 30.0)),
                        "playback_fps": getattr(stream_manager.workers.get(c.id), "playback_fps", getattr(c, "source_fps", 30.0)),
                        "processing_fps": getattr(stream_manager.workers.get(c.id), "processing_fps", getattr(c, "processing_fps", 30.0)),
                        "is_telemetry_valid": bool(c.id in stream_manager.workers and stream_manager.workers[c.id].is_running)
                    } for c in cameras
                ]
            }

            await manager.broadcast(payload)
        except Exception as e:
            logger.error("Error in AI WebSockets processing loop: %s", e)
        finally:
            db.close()

@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"[WEBSOCKET] Client message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket exception: %s", e)
        manager.disconnect(websocket)

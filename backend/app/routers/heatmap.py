import os
import re
import cv2
import math
import time
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.database import get_db
from app.models import CameraModel, ZoneModel, EventModel, VenuePinModel, User
from app.schemas import HeatmapResponse
from app.ai.heatmap import heatmap_manager, generate_venue_density_overlay, get_profile_for_density, HEATMAP_PROFILES
from app.ai.stream_processor import stream_manager
from app.auth_utils import decode_access_token

router = APIRouter(prefix="/heatmap", tags=["Heatmap"])
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


@router.get("/venue-overlay")
def get_venue_heatmap_overlay(
    event_id: Optional[str] = Query(None),
    demo_scenario: Optional[str] = Query(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Returns live venue crowd density heatmap overlay, spatial camera hotspots,
    monitored operational zone telemetry, and the uploaded venue blueprint for the selected event.
    
    Supports 4 calibrated rendering profiles:
    - LOW (< 45%): Cool Blue / Cyan
    - MEDIUM (45 - 74%): Cyan / Green / Yellow
    - HIGH (75 - 89%): Yellow / Orange / Red
    - CRITICAL (>= 90%): Intense Red / Crimson
    
    Telemetry Modes:
    - 'LIVE': Active video stream pipelines with fresh person detections (< 5s age)
    - 'STALE': Online camera feeds where frame processing is delayed or paused
    - 'DEMO': Isolated, deterministic demonstration scenarios (Sparse, Moderate, Dense Hall, Critical)
    - 'NO_DATA': No cameras configured or unmonitored event
    """
    user = get_current_user_from_auth(auth, db)
    target_event_id = event_id

    # Event authorization check
    if user and event_id:
        evt = db.query(EventModel).filter(EventModel.id == event_id).first()
        if evt and evt.manager_id and evt.manager_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot access venue heatmap for an event owned by another account."
            )
    elif not target_event_id and user:
        evt = db.query(EventModel).filter(EventModel.manager_id == user.id).first()
        if evt:
            target_event_id = evt.id
    
    if target_event_id:
        evt = db.query(EventModel).filter(EventModel.id == target_event_id).first()
    else:
        evt = db.query(EventModel).first()

    if not evt:
        return {
            "event_id": None,
            "event_title": "No Event Configured",
            "venue_name": "Unknown",
            "map_url": None,
            "total_occupancy": 0,
            "venue_capacity": 1000,
            "overall_density_pct": 0.0,
            "overall_risk": "low",
            "overall_profile": "LOW",
            "active_cameras_count": 0,
            "total_cameras_count": 0,
            "spatial_mapping_mode": "zone_and_pins",
            "heatmap_overlay_base64": "",
            "pins": [],
            "zones": [],
            "cameras": [],
            "last_updated": datetime.now().isoformat(),
            "telemetry_mode": "NO_DATA",
            "demo_scenario": None,
            "status": "no_event"
        }

    # Fetch event scoped records
    cams = db.query(CameraModel).filter(CameraModel.event_id == evt.id).all()
    zones = db.query(ZoneModel).filter(ZoneModel.event_id == evt.id).all()
    pins = db.query(VenuePinModel).filter(VenuePinModel.event_id == evt.id).all()

    # Detect uploaded map dimensions for pixel-perfect aspect alignment
    overlay_w, overlay_h = 1000, 750
    if evt.map_url:
        try:
            from app.routers.venue_map import UPLOAD_DIR
            filename = evt.map_url.split("/")[-1]
            local_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(local_path):
                m_img = cv2.imread(local_path)
                if m_img is not None:
                    overlay_h, overlay_w = m_img.shape[:2]
        except Exception:
            pass

    venue_cap = max(1, int(evt.capacity or 1000))

    # =========================================================================
    # DEMO SCENARIO MODE: Strictly isolated, deterministic benchmark datasets
    # =========================================================================
    if demo_scenario in ["sparse", "moderate", "dense_hall", "critical_corridor"]:
        scenario_profiles = {
            "sparse": {
                "name": "Sparse Occupancy (Low Density)",
                "profile": "LOW",
                "counts": [25, 18, 32, 20],
                "capacities": [100, 100, 150, 100],
                "zone_counts": [43, 52],
                "overall_density": 24.5,
                "overall_risk": "low"
            },
            "moderate": {
                "name": "Moderate Entrance Flow (Medium Density)",
                "profile": "MEDIUM",
                "counts": [115, 95, 130, 60],
                "capacities": [200, 200, 200, 200],
                "zone_counts": [210, 190],
                "overall_density": 58.0,
                "overall_risk": "medium"
            },
            "dense_hall": {
                "name": "Dense Main Hall Surge (High Density)",
                "profile": "HIGH",
                "counts": [165, 172, 158, 110],
                "capacities": [200, 200, 200, 200],
                "zone_counts": [337, 268],
                "overall_density": 82.5,
                "overall_risk": "high"
            },
            "critical_corridor": {
                "name": "Critical Choke-Point Bottleneck (Critical Surge)",
                "profile": "CRITICAL",
                "counts": [196, 188, 192, 165],
                "capacities": [200, 200, 200, 200],
                "zone_counts": [384, 357],
                "overall_density": 94.2,
                "overall_risk": "critical"
            }
        }

        sc = scenario_profiles[demo_scenario]
        demo_pins = []
        camera_hotspots: List[Dict[str, Any]] = []
        demo_cameras = []

        # Ensure at least 4 demo pins are rendered for rich scenario visualization
        cam_pins_existing = [p for p in pins if p.pin_type == "camera"]
        pins_to_map = [(p.id, p.label, p.x, p.y) for p in cam_pins_existing]
        default_coords = [
            ("demo-pin-1", "CAM1 - Main Entrance", 28.5, 45.0),
            ("demo-pin-2", "CAM2 - Central Concourse", 50.0, 50.0),
            ("demo-pin-3", "CAM3 - North Hall", 72.0, 38.0),
            ("demo-pin-4", "CAM4 - South Corridor", 48.0, 78.0)
        ]
        if len(pins_to_map) < 4:
            pins_to_map.extend(default_coords[len(pins_to_map):4])

        for idx, (p_id, p_label, px, py) in enumerate(pins_to_map):
            c_idx = idx % len(sc["counts"])
            cnt = sc["counts"][c_idx]
            cap = sc["capacities"][c_idx]
            dens = round((cnt / cap) * 100.0, 1)
            prof = get_profile_for_density(dens)
            risk_lvl = "critical" if dens >= 90 else "high" if dens >= 75 else "medium" if dens >= 45 else "low"

            demo_pins.append({
                "id": p_id,
                "label": p_label,
                "pin_type": "camera",
                "x": px,
                "y": py,
                "camera_id": f"demo-{p_id}",
                "count": cnt,
                "density": dens,
                "risk": risk_lvl,
                "profile": prof.name,
                "is_active": True,
                "observation_timestamp": datetime.now().isoformat()
            })
            camera_hotspots.append({
                "x": px,
                "y": py,
                "density": dens,
                "count": cnt,
                "radius": 75,
                "label": p_label
            })
            demo_cameras.append({
                "id": f"demo-{p_id}",
                "name": p_label,
                "location": f"Zone {idx + 1}",
                "status": "online",
                "playback_status": "playing",
                "count": cnt,
                "capacity": cap,
                "density": dens,
                "risk": risk_lvl,
                "profile": prof.name,
                "is_active": True,
                "is_stale": False,
                "observation_timestamp": datetime.now().isoformat(),
                "pin_mapped": True,
                "pin_x": px,
                "pin_y": py
            })

        # Also preserve non-camera facility pins if present
        for p in pins:
            if p.pin_type != "camera":
                demo_pins.append({
                    "id": p.id,
                    "label": p.label,
                    "pin_type": p.pin_type,
                    "x": p.x,
                    "y": p.y,
                    "camera_id": None,
                    "count": 0,
                    "density": 0.0,
                    "risk": "low",
                    "profile": "LOW",
                    "is_active": False,
                    "observation_timestamp": None
                })

        total_demo_occupancy = sum(c["count"] for c in demo_cameras)
        overlay_base64 = generate_venue_density_overlay(camera_hotspots, width=overlay_w, height=overlay_h) if evt.map_url else None
        if overlay_base64 == "":
            overlay_base64 = None

        return {
            "event_id": evt.id,
            "event_title": evt.title,
            "venue_name": getattr(evt, "venue_name", "Main Venue Complex") or "Main Venue Complex",
            "map_url": evt.map_url,
            "total_occupancy": total_demo_occupancy,
            "venue_capacity": venue_cap,
            "overall_density_pct": sc["overall_density"],
            "overall_risk": sc["overall_risk"],
            "overall_profile": sc["profile"],
            "active_cameras_count": len(demo_cameras),
            "total_cameras_count": len(demo_cameras),
            "spatial_mapping_mode": "zone_and_pins",
            "heatmap_overlay_base64": overlay_base64,
            "pins": demo_pins,
            "zones": [
                {
                    "id": f"demo-zone-{i+1}",
                    "name": f"Monitored Zone {i+1}",
                    "code": f"MZ-0{i+1}",
                    "capacity": 500,
                    "current_count": sc["zone_counts"][i % len(sc["zone_counts"])],
                    "density": round((sc["zone_counts"][i % len(sc["zone_counts"])] / 500.0) * 100.0, 1),
                    "risk_level": sc["overall_risk"],
                    "zone_type": "standard",
                    "assigned_cameras_count": 2,
                    "coordinates": None
                }
                for i in range(2)
            ],
            "cameras": demo_cameras,
            "last_updated": datetime.now().isoformat(),
            "telemetry_mode": "DEMO",
            "demo_scenario": demo_scenario,
            "status": "demo"
        }

    # =========================================================================
    # LIVE TELEMETRY MODE: Real YOLO detections, camera pins, observation timestamps
    # =========================================================================
    camera_data = []
    active_cameras_count = 0
    total_occupancy = 0
    fresh_cams_count = 0

    camera_pins = [p for p in pins if p.pin_type == "camera"]
    facility_pins = [p for p in pins if p.pin_type != "camera"]

    matched_camera_ids = set()
    camera_hotspots: List[Dict[str, Any]] = []
    now_ts = time.time()

    for cam in cams:
        worker = stream_manager.workers.get(cam.id)
        is_worker_running = worker is not None and getattr(worker, "is_running", False)
        
        # Real live count from worker or last DB recorded count
        live_count = int(getattr(worker, "last_count", cam.count or 0)) if is_worker_running else int(cam.count or 0)
        cam_capacity = max(1, int(cam.capacity or 200))
        cam_density = round((live_count / cam_capacity) * 100.0, 1)
        profile_obj = get_profile_for_density(cam_density)
        
        # Risk thresholds: <45% Low, 45-74% Med, 75-89% High, >=90% Crit
        if cam_density >= 90.0:
            cam_risk = "critical"
        elif cam_density >= 75.0:
            cam_risk = "high"
        elif cam_density >= 45.0:
            cam_risk = "medium"
        else:
            cam_risk = "low"

        is_active = is_worker_running or (cam.enabled and cam.status == "online" and cam.playback_status in ["analyzing", "playing"]) or (live_count > 0 and cam.enabled)
        
        # Timestamp and freshness evaluation
        obs_timestamp: Optional[str] = None
        is_stale = False
        if is_worker_running:
            worker_obs = getattr(worker, "last_observation_timestamp", 0.0)
            if worker_obs > 0:
                obs_age = now_ts - worker_obs
                is_stale = obs_age > 5.0
                obs_timestamp = datetime.fromtimestamp(worker_obs).isoformat()
            else:
                is_stale = False
                obs_timestamp = datetime.now().isoformat()
        elif getattr(cam, "last_frame_timestamp", None):
            obs_age = now_ts - cam.last_frame_timestamp
            is_stale = obs_age > 10.0
            obs_timestamp = datetime.fromtimestamp(cam.last_frame_timestamp).isoformat()
        else:
            is_stale = True if is_active else False
            obs_timestamp = datetime.now().isoformat() if is_active else None

        if is_active:
            active_cameras_count += 1
            total_occupancy += live_count
            if not is_stale:
                fresh_cams_count += 1

        # Attempt spatial pin matching
        matched_pin = None
        c_name = cam.name.lower().strip()
        c_id = cam.id.lower().strip()
        c_loc = (cam.location or "").lower().strip()
        norm_c_name = re.sub(r'[^a-zA-Z0-9]', '', c_name)

        for p in camera_pins:
            p_label = p.label.lower().strip()
            norm_p_label = re.sub(r'[^a-zA-Z0-9]', '', p_label)
            
            if (p_label in c_name or c_name in p_label or 
                p_label in c_loc or c_loc in p_label or 
                c_id == p.id.lower() or
                (norm_p_label and norm_p_label in norm_c_name) or
                (norm_c_name and norm_c_name in norm_p_label)):
                matched_pin = p
                matched_camera_ids.add(p.id)
                break

        pin_x = matched_pin.x if matched_pin else None
        pin_y = matched_pin.y if matched_pin else None

        camera_data.append({
            "id": cam.id,
            "name": cam.name,
            "location": cam.location,
            "zone_id": cam.zone_id,
            "status": cam.status,
            "playback_status": cam.playback_status,
            "count": live_count,
            "capacity": cam_capacity,
            "density": cam_density,
            "risk": cam_risk,
            "profile": profile_obj.name,
            "is_active": is_active,
            "is_stale": is_stale,
            "observation_timestamp": obs_timestamp,
            "pin_mapped": matched_pin is not None,
            "pin_x": pin_x,
            "pin_y": pin_y
        })

        if matched_pin and (is_active or live_count > 0):
            camera_hotspots.append({
                "x": matched_pin.x,
                "y": matched_pin.y,
                "density": cam_density,
                "count": live_count,
                "radius": 75,
                "label": cam.name
            })

    # Zone telemetry & zone center hotspots
    zone_data = []
    zone_cams_map: Dict[str, List[Dict[str, Any]]] = {}
    for cd in camera_data:
        zid = cd.get("zone_id")
        if zid:
            zone_cams_map.setdefault(zid, []).append(cd)

    for z in zones:
        z_cams = zone_cams_map.get(z.id, [])
        z_cap = max(1, int(z.capacity or 500))
        z_count = sum(c["count"] for c in z_cams) if z_cams else int(z.current_count or 0)
        z_density = round((z_count / z_cap) * 100.0, 1)
        z_prof = get_profile_for_density(z_density)

        if z_density >= 90.0:
            z_risk = "critical"
        elif z_density >= 75.0:
            z_risk = "high"
        elif z_density >= 45.0:
            z_risk = "medium"
        else:
            z_risk = "low"

        zone_data.append({
            "id": z.id,
            "name": z.name,
            "code": z.code,
            "capacity": z_cap,
            "current_count": z_count,
            "density": z_density,
            "risk_level": z_risk,
            "profile": z_prof.name,
            "zone_type": z.zone_type,
            "assigned_cameras_count": len(z_cams),
            "coordinates": z.coordinates
        })

    # Prepare pins list with camera metrics attached
    all_pins_response = []
    for p in pins:
        associated_cam = next((c for c in camera_data if c.get("pin_x") == p.x and c.get("pin_y") == p.y), None)
        all_pins_response.append({
            "id": p.id,
            "label": p.label,
            "pin_type": p.pin_type,
            "x": p.x,
            "y": p.y,
            "camera_id": associated_cam["id"] if associated_cam else None,
            "count": associated_cam["count"] if associated_cam else 0,
            "density": associated_cam["density"] if associated_cam else 0.0,
            "risk": associated_cam["risk"] if associated_cam else "low",
            "profile": associated_cam["profile"] if associated_cam else "LOW",
            "is_active": associated_cam["is_active"] if associated_cam else False,
            "is_stale": associated_cam.get("is_stale", False) if associated_cam else False,
            "observation_timestamp": associated_cam.get("observation_timestamp") if associated_cam else None
        })

    # Venue-wide overall density, risk and rendering profile
    overall_density_pct = round((total_occupancy / venue_cap) * 100.0, 1)
    overall_prof = get_profile_for_density(overall_density_pct)

    if overall_density_pct >= 90.0:
        overall_risk = "critical"
    elif overall_density_pct >= 75.0:
        overall_risk = "high"
    elif overall_density_pct >= 45.0:
        overall_risk = "medium"
    else:
        overall_risk = "low"

    # Determine Telemetry Mode
    if not evt.map_url:
        page_status = "no_map"
        telemetry_mode = "NO_DATA"
    elif active_cameras_count == 0:
        page_status = "idle"
        telemetry_mode = "NO_DATA"
    elif fresh_cams_count > 0:
        page_status = "live"
        telemetry_mode = "LIVE"
    else:
        page_status = "live"
        telemetry_mode = "STALE"

    # Generate OpenCV transparent PNG overlay
    overlay_base64 = generate_venue_density_overlay(camera_hotspots, width=overlay_w, height=overlay_h) if evt.map_url else None
    if overlay_base64 == "":
        overlay_base64 = None

    return {
        "event_id": evt.id,
        "event_title": evt.title,
        "venue_name": getattr(evt, "venue_name", "Main Venue Complex") or "Main Venue Complex",
        "map_url": evt.map_url,
        "total_occupancy": total_occupancy,
        "venue_capacity": venue_cap,
        "overall_density_pct": overall_density_pct,
        "overall_risk": overall_risk,
        "overall_profile": overall_prof.name,
        "active_cameras_count": active_cameras_count,
        "total_cameras_count": len(cams),
        "spatial_mapping_mode": "zone_and_pins",
        "heatmap_overlay_base64": overlay_base64,
        "pins": all_pins_response,
        "zones": zone_data,
        "cameras": camera_data,
        "last_updated": datetime.now().isoformat(),
        "telemetry_mode": telemetry_mode,
        "demo_scenario": None,
        "status": page_status
    }


@router.get("", response_model=HeatmapResponse)
def get_live_heatmap(
    cam_id: Optional[str] = Query(None),
    zone_id: Optional[str] = Query(None),
    scope: str = Query("camera"), # camera, zone, area, venue
    transparent: bool = Query(False),
    event_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Legacy heatmap route preserved for backwards compatibility."""
    target_id = "area-wide"
    density = 0.0

    if scope == "zone" and zone_id:
        zone = db.query(ZoneModel).filter(ZoneModel.id == zone_id).first()
        gen = heatmap_manager.get_zone_generator(zone_id)
        target_id = zone.id if zone else zone_id
        density = zone.density if zone else 0.0
        base64_str = gen.generate_base64_heatmap(transparent_zero=transparent)

    elif scope in ["area", "venue"]:
        query_cams = db.query(CameraModel).filter(CameraModel.enabled == True, CameraModel.status == "online")
        if event_id:
            query_cams = query_cams.filter(CameraModel.event_id == event_id)
        analyzing_cams = query_cams.all()
        if not analyzing_cams:
            return {
                "camera_id": "none",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "peak_density": 0.0,
                "heatmap_base64": "",
                "image": ""
            }
        density = (sum(c.density for c in analyzing_cams) / len(analyzing_cams)) if analyzing_cams else 0.0
        gen = heatmap_manager.area_generator
        base64_str = gen.generate_base64_heatmap(transparent_zero=transparent)

    else:
        # Camera scope
        if cam_id:
            cam = db.query(CameraModel).filter(CameraModel.id == cam_id).first()
            if cam and event_id and cam.event_id != event_id:
                cam = None
        else:
            q = db.query(CameraModel).filter(CameraModel.enabled == True, CameraModel.status == "online")
            if event_id:
                q = q.filter(CameraModel.event_id == event_id)
            cam = q.first()
            if not cam and not event_id:
                cam = db.query(CameraModel).first()

        target_id = cam.id if cam else "none"
        density = cam.density if cam else 0.0
        if cam:
            gen = heatmap_manager.get_camera_generator(cam.id)
            base64_str = gen.generate_base64_heatmap(transparent_zero=transparent)
        else:
            base64_str = ""

    return {
        "camera_id": target_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "peak_density": density,
        "heatmap_base64": base64_str,
        "image": base64_str
    }

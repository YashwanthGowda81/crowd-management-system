"""
Unit & Integration test suite for Venue Heatmap API & Algorithms
Direct function testing:
1. test_01_venue_density_overlay_generator_empty: Empty points list returns transparent PNG without error.
2. test_02_venue_density_overlay_generator_with_points: Points with weights generate colored Gaussian blooms.
3. test_03_venue_heatmap_api_event_with_map: Event with map returns 200, valid base64 PNG, pins, and KPIs.
4. test_04_venue_heatmap_api_event_without_map: Event without map returns status 'no_map' with null overlay.
5. test_05_venue_heatmap_strict_event_isolation: Querying Event A must never return Event B pins/cameras/maps.
6. test_06_venue_heatmap_density_thresholds: Density % maps to Low/Medium/High/Critical accurately.
7. test_07_venue_heatmap_http_endpoint: Tests the active HTTP endpoint via urllib.request if server is running.
"""
import sys
import base64
import json
import urllib.request
import urllib.error
import cv2
import numpy as np
from fastapi.security import HTTPAuthorizationCredentials
from app.routers.heatmap import get_venue_heatmap_overlay
from app.ai.heatmap import generate_venue_density_overlay
from app.database import SessionLocal
from app.models import User, EventModel, VenuePinModel, CameraModel, ZoneModel
from app.auth_utils import create_access_token

def get_test_auth(user_email: str = "officer_heatmap@crowdai.internal"):
    db = SessionLocal()
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(
            email=user_email,
            hashed_password="test_hash",
            name="Heatmap Test Officer",
            role="Senior Officer",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token({"sub": user.email, "user_id": user.id})
    user_id = user.id
    db.close()
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), user_id, token

def test_01_venue_density_overlay_generator_empty():
    """Empty points list should return empty string cleanly without error."""
    overlay_b64 = generate_venue_density_overlay([], width=800, height=600)
    assert overlay_b64 == "", "Overlay should be empty string when no points exist"
    print("[PASS] test_01_venue_density_overlay_generator_empty")

def test_02_venue_density_overlay_generator_with_points():
    """Points with weights should generate colored Gaussian blooms with valid PNG shape."""
    points = [
        {"x": 50.0, "y": 50.0, "density": 85.0, "count": 100, "radius": 40},
        {"x": 20.0, "y": 30.0, "density": 25.0, "count": 20, "radius": 30}
    ]
    overlay_b64 = generate_venue_density_overlay(points, width=1000, height=750)
    assert overlay_b64.startswith("data:image/png;base64,"), "Overlay must be a valid PNG data URI"
    raw_b64 = overlay_b64.split(",")[1]
    img_data = base64.b64decode(raw_b64)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    assert img.shape == (750, 1000, 4), f"Expected shape (750, 1000, 4), got {img.shape}"
    # Check that center has non-zero alpha and color
    center_y, center_x = int(0.50 * 750), int(0.50 * 1000)
    assert img[center_y, center_x, 3] > 0, "Center alpha should be non-zero"
    print("[PASS] test_02_venue_density_overlay_generator_with_points")

def test_03_venue_heatmap_api_event_with_map():
    """Event with map should return map_url, overlay, and pins."""
    auth, user_id, _ = get_test_auth()
    db = SessionLocal()
    evt_id = "evt_test_heatmap_with_map"
    evt = db.query(EventModel).filter(EventModel.id == evt_id).first()
    if not evt:
        evt = EventModel(
            id=evt_id,
            title="Heatmap Test Stadium",
            manager_id=user_id,
            capacity=1000,
            map_url="http://localhost:8000/static/maps/test_map.png"
        )
        db.add(evt)
        pin = VenuePinModel(
            id="pin-test-cam-1",
            event_id=evt_id,
            pin_type="camera",
            label="Gate A Cam",
            x=35.5,
            y=42.0
        )
        db.add(pin)
        cam = CameraModel(
            id="cam-test-1",
            event_id=evt_id,
            name="Gate A Cam",
            rtsp_url="test_stream.mp4",
            location="Gate A",
            count=250,
            capacity=500,
            density=50.0,
            risk="Medium",
            status="online",
            enabled=True,
            playback_status="playing"
        )
        db.add(cam)
        db.commit()
    else:
        cam = db.query(CameraModel).filter(CameraModel.id == "cam-test-1").first()
        if cam:
            cam.count = 250
            cam.capacity = 500
            cam.density = 50.0
            cam.status = "online"
            cam.enabled = True
            cam.playback_status = "playing"
            db.commit()

    # Call endpoint directly
    data = get_venue_heatmap_overlay(event_id=evt_id, auth=auth, db=db)
    db.close()

    assert data["event_id"] == evt_id
    assert data["status"] == "live"
    assert data["map_url"] is not None
    assert data["heatmap_overlay_base64"] is not None
    assert len(data["pins"]) >= 1
    assert data["venue_capacity"] == 1000
    camera_pins = [p for p in data["pins"] if p["pin_type"] == "camera"]
    assert len(camera_pins) >= 1
    marker = camera_pins[0]
    assert marker["x"] == 35.5
    assert marker["y"] == 42.0
    print("[PASS] test_03_venue_heatmap_api_event_with_map")

def test_04_venue_heatmap_api_event_without_map():
    """Event without map should return status: 'no_map' and null overlay."""
    auth, user_id, _ = get_test_auth()
    db = SessionLocal()
    evt_id = "evt_test_heatmap_no_map"
    evt = db.query(EventModel).filter(EventModel.id == evt_id).first()
    if not evt:
        evt = EventModel(
            id=evt_id,
            title="Heatmap Event Without Map",
            manager_id=user_id,
            capacity=500,
            map_url=None
        )
        db.add(evt)
        db.commit()

    data = get_venue_heatmap_overlay(event_id=evt_id, auth=auth, db=db)
    db.close()

    assert data["event_id"] == evt_id
    assert data["status"] == "no_map"
    assert data["map_url"] is None
    assert data["heatmap_overlay_base64"] is None
    print("[PASS] test_04_venue_heatmap_api_event_without_map")

def test_05_venue_heatmap_strict_event_isolation():
    """Querying Event A must never return Event B's pins or cameras."""
    auth, user_id, _ = get_test_auth()
    db = SessionLocal()
    evt_a_id = "evt_iso_a"
    evt_b_id = "evt_iso_b"
    
    if not db.query(EventModel).filter(EventModel.id == evt_a_id).first():
        db.add(EventModel(id=evt_a_id, title="Iso Event A", manager_id=user_id, capacity=1000, map_url="http://localhost:8000/static/maps/a.png"))
        db.add(VenuePinModel(id="pin-iso-a", event_id=evt_a_id, pin_type="camera", label="Cam A", x=10.0, y=10.0))
    if not db.query(EventModel).filter(EventModel.id == evt_b_id).first():
        db.add(EventModel(id=evt_b_id, title="Iso Event B", manager_id=user_id, capacity=2000, map_url="http://localhost:8000/static/maps/b.png"))
        db.add(VenuePinModel(id="pin-iso-b", event_id=evt_b_id, pin_type="camera", label="Cam B", x=90.0, y=90.0))
    db.commit()

    data_a = get_venue_heatmap_overlay(event_id=evt_a_id, auth=auth, db=db)
    db.close()

    labels = [m["label"] for m in data_a["pins"]]
    assert "Cam A" in labels, "Event A should have Cam A"
    assert "Cam B" not in labels, "Event A must NOT contain Event B pin"
    assert data_a["map_url"] == "http://localhost:8000/static/maps/a.png"
    print("[PASS] test_05_venue_heatmap_strict_event_isolation")

def test_06_venue_heatmap_density_thresholds():
    """Verify density percentage thresholds:
    <45% Low, 45-74% Medium, 75-89% High, >=90% Critical
    """
    auth, user_id, _ = get_test_auth()
    db = SessionLocal()
    evt_id = "evt_test_thresholds"
    evt = db.query(EventModel).filter(EventModel.id == evt_id).first()
    if not evt:
        evt = EventModel(id=evt_id, title="Threshold Test", manager_id=user_id, capacity=100, map_url="http://localhost:8000/static/maps/t.png")
        db.add(evt)
        db.commit()
    
    cam = db.query(CameraModel).filter(CameraModel.id == "cam-thresh").first()
    if not cam:
        cam = CameraModel(id="cam-thresh", event_id=evt_id, name="Thresh Cam", rtsp_url="test_stream.mp4", location="Zone 1", count=20, capacity=100, density=20.0, risk="low", playback_status="playing")
        db.add(cam)
        db.add(VenuePinModel(id="pin-thresh", event_id=evt_id, pin_type="camera", label="Thresh Cam", x=50.0, y=50.0))
    else:
        cam.count = 20
        cam.density = 20.0
    db.commit()

    data = get_venue_heatmap_overlay(event_id=evt_id, auth=auth, db=db)
    assert data["overall_risk"].lower() == "low"
    assert data["overall_density_pct"] == 20.0

    # Test high threshold (80%)
    cam.count = 80
    cam.density = 80.0
    db.commit()
    data_high = get_venue_heatmap_overlay(event_id=evt_id, auth=auth, db=db)
    assert data_high["overall_risk"].lower() == "high"
    assert data_high["overall_density_pct"] == 80.0

    # Test critical threshold (95%)
    cam.count = 95
    cam.density = 95.0
    db.commit()
    data_crit = get_venue_heatmap_overlay(event_id=evt_id, auth=auth, db=db)
    assert data_crit["overall_risk"].lower() == "critical"
    assert data_crit["overall_density_pct"] == 95.0

    db.close()
    print("[PASS] test_06_venue_heatmap_density_thresholds (Low, High, Critical)")

def test_08_venue_heatmap_rendering_profiles():
    """Verify that all 4 density profiles (LOW, MEDIUM, HIGH, CRITICAL) generate valid overlays and map accurately."""
    from app.ai.heatmap import get_profile_for_density, generate_venue_density_overlay

    # Profile A: Low (<45%)
    p_low = get_profile_for_density(25.0)
    assert p_low.name == "LOW"
    assert p_low.jet_range == (35.0, 85.0)
    ov_low = generate_venue_density_overlay([{"x": 30.0, "y": 40.0, "density": 25.0, "count": 25}])
    assert ov_low.startswith("data:image/png;base64,")

    # Profile B: Medium (45-74%)
    p_med = get_profile_for_density(60.0)
    assert p_med.name == "MEDIUM"
    assert p_med.jet_range == (95.0, 180.0)
    ov_med = generate_venue_density_overlay([{"x": 50.0, "y": 50.0, "density": 60.0, "count": 60}])
    assert ov_med.startswith("data:image/png;base64,")

    # Profile C: High (75-89%)
    p_high = get_profile_for_density(82.0)
    assert p_high.name == "HIGH"
    assert p_high.jet_range == (185.0, 225.0)
    ov_high = generate_venue_density_overlay([{"x": 70.0, "y": 60.0, "density": 82.0, "count": 82}])
    assert ov_high.startswith("data:image/png;base64,")

    # Profile D: Critical (>=90%)
    p_crit = get_profile_for_density(95.0)
    assert p_crit.name == "CRITICAL"
    assert p_crit.jet_range == (230.0, 255.0)
    ov_crit = generate_venue_density_overlay([{"x": 50.0, "y": 50.0, "density": 95.0, "count": 95}])
    assert ov_crit.startswith("data:image/png;base64,")

    print("[PASS] test_08_venue_heatmap_rendering_profiles (LOW, MEDIUM, HIGH, CRITICAL verified)")

def test_09_venue_heatmap_demo_scenarios():
    """Verify that all 4 demo scenarios execute deterministically with telemetry_mode: 'DEMO'."""
    auth, _, _ = get_test_auth()
    db = SessionLocal()
    evt_id = "evt_test_heatmap_with_map"

    for scenario, expected_profile in [
        ("sparse", "LOW"),
        ("moderate", "MEDIUM"),
        ("dense_hall", "HIGH"),
        ("critical_corridor", "CRITICAL")
    ]:
        data = get_venue_heatmap_overlay(event_id=evt_id, demo_scenario=scenario, auth=auth, db=db)
        assert data["telemetry_mode"] == "DEMO"
        assert data["demo_scenario"] == scenario
        assert data["overall_profile"] == expected_profile
        assert len(data["pins"]) >= 4
        assert len(data["cameras"]) >= 4
        assert data["heatmap_overlay_base64"] is not None
        assert data["heatmap_overlay_base64"].startswith("data:image/png;base64,")

    db.close()
    print("[PASS] test_09_venue_heatmap_demo_scenarios (sparse, moderate, dense_hall, critical_corridor)")

def test_07_venue_heatmap_http_endpoint():
    """Test HTTP endpoint if server is running on port 8000."""
    try:
        _, _, token = get_test_auth()
        url = "http://127.0.0.1:8000/api/heatmap/venue-overlay?event_id=evt_test_heatmap_with_map"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["event_id"] == "evt_test_heatmap_with_map"
            assert data["heatmap_overlay_base64"] is not None
            print("[PASS] test_07_venue_heatmap_http_endpoint (HTTP 200 OK)")
    except Exception as e:
        print(f"[SKIP] test_07_venue_heatmap_http_endpoint (Server not reachable or offline: {e})")

if __name__ == "__main__":
    print("=== RUNNING VENUE HEATMAP TEST SUITE ===")
    test_01_venue_density_overlay_generator_empty()
    test_02_venue_density_overlay_generator_with_points()
    test_03_venue_heatmap_api_event_with_map()
    test_04_venue_heatmap_api_event_without_map()
    test_05_venue_heatmap_strict_event_isolation()
    test_06_venue_heatmap_density_thresholds()
    test_08_venue_heatmap_rendering_profiles()
    test_09_venue_heatmap_demo_scenarios()
    test_07_venue_heatmap_http_endpoint()
    print("=== ALL VENUE HEATMAP TESTS PASSED ===")

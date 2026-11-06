import sys
import os
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, EventModel, CameraModel, AlertModel

def test_workflow_verification():
    print("=" * 80)
    print(" CROWD-AI v2.4 COMPLETE WORKFLOW & ONBOARDING VERIFICATION SUITE")
    print("=" * 80)

    client = TestClient(app)
    db = SessionLocal()

    # -------------------------------------------------------------
    # Scenario 1: Unauthenticated access to protected endpoints -> 401
    # -------------------------------------------------------------
    print("\n[SCENARIO 1] Testing unauthenticated access to protected onboarding & events endpoints...")
    res = client.get("/api/auth/onboarding-status")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    res2 = client.get("/api/events/my-event")
    assert res2.status_code == 401, f"Expected 401, got {res2.status_code}"
    print("  -> PASS: Unauthenticated access safely blocked with 401 Unauthorized.")

    # -------------------------------------------------------------
    # Scenario 2: Existing User 1 (Officer J. Doe) with complete setup -> Dashboard
    # -------------------------------------------------------------
    print("\n[SCENARIO 2] Verifying User 1 (Officer J. Doe) who has event & cameras...")
    res = client.post("/api/auth/login", json={"email": "surveillance.ops@smartcity.gov", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.status_code}"
    token_user1 = res.json()["token"]

    status1 = client.get("/api/auth/onboarding-status", headers={"Authorization": f"Bearer {token_user1}"}).json()
    assert status1["has_event"] is True, "User 1 should have an event"
    assert status1["has_source"] is True, "User 1 should have configured cameras"
    assert status1["status"] == "complete", f"User 1 status should be complete, got {status1['status']}"
    assert status1["next_route"] == "/dashboard", f"Expected /dashboard, got {status1['next_route']}"
    print(f"  -> PASS: User 1 onboarding is complete ({status1['source_count']} cameras). Destination: {status1['next_route']}.")

    # -------------------------------------------------------------
    # Scenario 3: New Manager lifecycle: Register -> No Event -> Event Setup
    # -------------------------------------------------------------
    test_email = "test.manager@smartcity.gov"
    # Clean any leftover test user
    db.query(CameraModel).filter(CameraModel.name.like("%Test Workflow%")).delete()
    db.query(EventModel).filter(EventModel.title == "Workflow Automated Test Event").delete()
    db.query(User).filter(User.email == test_email).delete()
    db.commit()

    print("\n[SCENARIO 3] Registering new manager without event -> Expect 'needs_event' -> /event-setup...")
    reg_res = client.post("/api/auth/register", json={
        "email": test_email,
        "password": "Password@123",
        "name": "Alex Vance",
        "role": "Security Director"
    })
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.status_code}"
    token_new = reg_res.json()["token"]
    user_id_new = reg_res.json()["id"]

    new_status = client.get("/api/auth/onboarding-status", headers={"Authorization": f"Bearer {token_new}"}).json()
    assert new_status["has_event"] is False, "New manager should have no event initially"
    assert new_status["status"] == "needs_event", f"Expected 'needs_event', got {new_status['status']}"
    assert new_status["next_route"] == "/event-setup", f"Expected '/event-setup', got {new_status['next_route']}"
    print("  -> PASS: New manager correctly flagged as 'needs_event'. Destination: /event-setup.")

    # -------------------------------------------------------------
    # Scenario 4: Create Event -> Manager association & Transition to Camera Setup
    # -------------------------------------------------------------
    print("\n[SCENARIO 4] Creating Event for new manager -> Expect 'needs_source' -> /camera-setup...")
    evt_payload = {
        "title": "Workflow Automated Test Event",
        "venue_name": "Testing Complex A",
        "capacity": 3000,
        "limits": 2500,
        "staff": 25,
        "risk": "medium",
        "start_time": "09:00 AM",
        "end_time": "09:00 PM"
    }
    create_evt_res = client.post("/api/events", json=evt_payload, headers={"Authorization": f"Bearer {token_new}"})
    assert create_evt_res.status_code == 201, f"Event creation failed: {create_evt_res.status_code}"
    new_evt = create_evt_res.json()
    new_evt_id = new_evt["id"]
    assert new_evt["manager_id"] == user_id_new, f"Event manager_id {new_evt['manager_id']} does not match user id {user_id_new}"
    print(f"  -> PASS: Event '{new_evt['title']}' created and associated with manager {user_id_new}.")

    # Test /api/events/my-event
    my_evt = client.get("/api/events/my-event", headers={"Authorization": f"Bearer {token_new}"}).json()
    assert my_evt["id"] == new_evt_id, "my-event endpoint did not return correct manager event"
    print(f"  -> PASS: /api/events/my-event successfully returned manager's event '{my_evt['title']}'.")

    # Verify status transition to needs_source
    evt_status = client.get("/api/auth/onboarding-status", headers={"Authorization": f"Bearer {token_new}"}).json()
    assert evt_status["has_event"] is True, "Should have event"
    assert evt_status["has_source"] is False, "Should have no source yet"
    assert evt_status["status"] == "needs_source", f"Expected 'needs_source', got {evt_status['status']}"
    assert evt_status["next_route"] == "/camera-setup", f"Expected '/camera-setup', got {evt_status['next_route']}"
    print("  -> PASS: Onboarding status updated to 'needs_source'. Destination: /camera-setup.")

    # -------------------------------------------------------------
    # Scenario 5: Option A — Register RTSP Camera for this event
    # -------------------------------------------------------------
    print("\n[SCENARIO 5] Option A: Registering RTSP camera for the event...")
    rtsp_payload = {
        "name": "Test Workflow RTSP Gate 1",
        "rtsp_url": "rtsp://192.168.10.200:554/live",
        "location": "North Entrance",
        "capacity": 200,
        "event_id": new_evt_id
    }
    rtsp_res = client.post("/api/cameras", json=rtsp_payload, headers={"Authorization": f"Bearer {token_new}"})
    assert rtsp_res.status_code == 201, f"RTSP creation failed: {rtsp_res.status_code}"
    rtsp_cam = rtsp_res.json()
    assert rtsp_cam["event_id"] == new_evt_id
    assert rtsp_cam["source_type"] == "rtsp"
    print(f"  -> PASS: RTSP camera '{rtsp_cam['name']}' registered and bound to event {new_evt_id}.")

    # Verify status is now complete
    rtsp_status = client.get("/api/auth/onboarding-status", headers={"Authorization": f"Bearer {token_new}"}).json()
    assert rtsp_status["has_source"] is True, "Should now have source"
    assert rtsp_status["status"] == "complete", f"Expected 'complete', got {rtsp_status['status']}"
    assert rtsp_status["next_route"] == "/dashboard", f"Expected '/dashboard', got {rtsp_status['next_route']}"
    print("  -> PASS: Status transitioned to complete with RTSP camera. Destination: /dashboard.")

    # Delete this camera to test Option B independently
    client.delete(f"/api/cameras/{rtsp_cam['id']}")

    # -------------------------------------------------------------
    # Scenario 6: Option B — Upload Video for crowd analysis without RTSP
    # -------------------------------------------------------------
    print("\n[SCENARIO 6] Option B: Uploading video without RTSP camera...")
    # Find existing small sample video or create dummy mp4 bytes
    video_path = os.path.join(os.path.dirname(__file__), "app", "uploads", "videos", "cam-vid-1792122375805.mp4")
    if os.path.exists(video_path):
        with open(video_path, "rb") as vf:
            file_bytes = vf.read(1024 * 50) # Sample bytes
    else:
        file_bytes = b"fake video bytes for testing"

    upload_res = client.post(
        "/api/cameras/upload-video",
        files={"file": ("test_footage.mp4", io.BytesIO(file_bytes), "video/mp4")},
        data={
            "name": "Test Workflow Uploaded CCTV 01",
            "location": "South Concourse",
            "capacity": 250,
            "event_id": new_evt_id
        }
    )
    assert upload_res.status_code == 201, f"Upload video failed: {upload_res.status_code}"
    vid_cam = upload_res.json()
    assert vid_cam["event_id"] == new_evt_id
    assert vid_cam["source_type"] == "video"
    print(f"  -> PASS: Video source '{vid_cam['name']}' created and associated with event {new_evt_id}.")

    # Verify status is complete with ONLY uploaded video
    vid_status = client.get("/api/auth/onboarding-status", headers={"Authorization": f"Bearer {token_new}"}).json()
    assert vid_status["has_source"] is True
    assert vid_status["status"] == "complete"
    assert vid_status["next_route"] == "/dashboard"
    print("  -> PASS: Uploaded video alone successfully completes source setup! Destination: /dashboard.")

    # -------------------------------------------------------------
    # Scenario 7: Event Isolation Verification
    # -------------------------------------------------------------
    print("\n[SCENARIO 7] Verifying cross-event data isolation...")
    user1_cams = client.get("/api/cameras?event_id=evt-arena-01").json()
    new_evt_cams = client.get(f"/api/cameras?event_id={new_evt_id}").json()

    assert all(c["event_id"] == "evt-arena-01" for c in user1_cams), "user1 cameras leak other events"
    assert all(c["event_id"] == new_evt_id for c in new_evt_cams), "new_evt cameras leak other events"
    assert not any(c["id"] == vid_cam["id"] for c in user1_cams), "Uploaded camera leaked into evt-arena-01"
    print(f"  -> PASS: Strict cross-event camera isolation verified (User 1 has {len(user1_cams)}, Test Event has {len(new_evt_cams)}).")

    # -------------------------------------------------------------
    # Clean up test entities
    # -------------------------------------------------------------
    client.delete(f"/api/cameras/{vid_cam['id']}")
    client.delete(f"/api/events/{new_evt_id}")
    db.query(User).filter(User.email == test_email).delete()
    db.commit()
    db.close()
    print("  -> Cleanup complete.")

    print("\n" + "=" * 80)
    print(" ALL 7 WORKFLOW & ONBOARDING SCENARIOS PASSED WITH ZERO REGRESSIONS")
    print("=" * 80)

if __name__ == "__main__":
    test_workflow_verification()

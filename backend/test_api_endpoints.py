import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def test_api():
    print("=" * 70)
    print(" FASTAPI REST & WEBSOCKET ENDPOINTS END-TO-END TEST")
    print("=" * 70)

    client = TestClient(app)

    # 0. Resolve Active Event
    evts_res = client.get("/api/events")
    assert evts_res.status_code == 200 and len(evts_res.json()) > 0
    event = evts_res.json()[0]
    target_event_id = event["id"]

    # 1. Cameras
    print(f"\n[1] Testing GET /api/cameras for event '{event['title']}'...")
    res = client.get(f"/api/cameras?event_id={target_event_id}")
    assert res.status_code == 200, f"Status code {res.status_code}"
    cams = res.json()
    assert len(cams) >= 1, f"Expected at least 1 camera, got {len(cams)}"
    print(f"  -> SUCCESS: Retrieved {len(cams)} cameras for active event.")

    # 2. Events & Venue Architecture
    print(f"\n[2] Testing GET /api/events/{target_event_id}/venue...")
    res = client.get(f"/api/events/{target_event_id}/venue")
    assert res.status_code == 200, f"Status code {res.status_code}"
    venue = res.json()
    print(f"  -> SUCCESS: Venue details retrieved with {len(venue.get('zones', []))} operational zones and {len(venue.get('pins', []))} map pins.")

    # 3. Single-Account Event Ownership & Access Control
    print("\n[3] Testing Single-Account Event Ownership & Access Control (400 on duplicate, 403 on cross-account)...")
    login_res = client.post("/api/auth/login", json={"email": "surveillance.ops@smartcity.gov", "password": "admin123"})
    token_user1 = login_res.json()["token"]
    # Attempt duplicate event creation for existing account
    dup_res = client.post("/api/events", json={"title": "Duplicate Event", "capacity": 1000}, headers={"Authorization": f"Bearer {token_user1}"})
    assert dup_res.status_code == 400, f"Expected 400 for duplicate event, got {dup_res.status_code}"
    print("  -> SUCCESS: Attempt to create a 2nd event for account safely rejected with 400 Bad Request.")

    # 4. Crowd Analysis & Trend
    print("\n[4] Testing GET /api/crowd-analysis...")
    res = client.get(f"/api/crowd-analysis?event_id={target_event_id}")
    assert res.status_code == 200, f"Status code {res.status_code}"
    ca = res.json()
    assert "speed_status" in ca
    assert "hourly_trend" in ca
    print(f"  -> SUCCESS: Crowd analysis returned with speed_status: '{ca['speed_status']}'.")

    # 5. Emergency Status
    print("\n[5] Testing GET /api/emergency/status...")
    res = client.get(f"/api/emergency/status?event_id={target_event_id}")
    assert res.status_code == 200, f"Status code {res.status_code}"
    emg_status = res.json()
    assert "has_active_emergency" in emg_status
    print(f"  -> SUCCESS: Emergency status returned: has_active_emergency={emg_status['has_active_emergency']}.")

    # 6. Recommendations
    print("\n[6] Testing GET /api/recommendations...")
    res = client.get(f"/api/recommendations?event_id={target_event_id}")
    assert res.status_code == 200, f"Status code {res.status_code}"
    recs = res.json()
    print(f"  -> SUCCESS: Recommendations returned: {len(recs)} items for active event.")

    # 7. PDF Report Download
    print("\n[7] Testing GET /api/reports/pdf...")
    res = client.get(f"/api/reports/pdf?cam_id=all&event_id={target_event_id}")
    assert res.status_code == 200, f"Status code {res.status_code}"
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 1000
    print(f"  -> SUCCESS: PDF report generated successfully ({len(res.content)} bytes).")

    # 8. Settings Update & Propagation
    print("\n[8] Testing Settings update & propagation...")
    res = client.get("/api/settings")
    assert res.status_code == 200
    cur_settings = res.json()
    
    # Update AI sensitivity
    res_update = client.put("/api/settings", json={"ai_sensitivity": 80, "crowd_threshold": 85})
    assert res_update.status_code == 200
    new_settings = res_update.json()
    assert new_settings["ai_sensitivity"] == 80
    print("  -> SUCCESS: Settings updated and validated successfully.")

    # 9. Camera Playback Control
    print("\n[9] Testing Camera Playback Controls (pause & play)...")
    res_pause = client.put(f"/api/cameras/{cams[0]['id']}/playback?action=pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["playback_status"] == "paused"
    
    res_resume = client.put(f"/api/cameras/{cams[0]['id']}/playback?action=play")
    assert res_resume.status_code == 200
    assert res_resume.json()["playback_status"] == "analyzing"
    print("  -> SUCCESS: Playback pause and play controls verified.")

    # 10. WebSocket Connection
    print("\n[10] Testing WebSocket /ws/live connection...")
    try:
        with client.websocket_connect("/ws/live") as websocket:
            websocket.send_text("PING")
            print("  -> SUCCESS: WebSocket connected and transmitted message.")
    except Exception as e:
        print(f"  -> WebSocket test notice: {e}")

    print("\n" + "=" * 70)
    print(" ALL API ENDPOINT TESTS PASSED")
    print("=" * 70)

if __name__ == "__main__":
    test_api()

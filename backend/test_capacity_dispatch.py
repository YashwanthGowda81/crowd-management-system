import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

def request_json(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}

def test_pipeline():
    print("=== TEST 1: Authentication & Event Capacity Persistence ===")
    status, login_res = request_json(f"{BASE_URL}/auth/login", method="POST", data={"email": "admin@crowd.ai", "password": "password123"})
    if status != 200 or "token" not in login_res:
        print(f"FAILED: Login failed: status={status}, res={login_res}")
        return False
    
    token = login_res["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("SUCCESS: Logged in as admin@crowd.ai")

    # Get my event
    status, evt = request_json(f"{BASE_URL}/events/my-event", method="GET", headers=headers)
    if status != 200 or not evt:
        print(f"FAILED: Could not fetch my-event: status={status}, res={evt}")
        return False
    
    evt_id = evt["id"]
    original_cap = evt.get("capacity", 5000)
    print(f"SUCCESS: Fetched active event {evt_id} with original capacity: {original_cap}")

    # Test invalid capacity <= 0
    status, bad_cap_res = request_json(f"{BASE_URL}/events/{evt_id}", method="PUT", headers=headers, data={"capacity": -50})
    if status == 400:
        print(f"SUCCESS: Negative capacity correctly rejected with 400: {bad_cap_res.get('detail')}")
    else:
        print(f"FAILED: Expected 400 for capacity -50, got {status}")
        return False

    status, bad_zero_res = request_json(f"{BASE_URL}/events/{evt_id}", method="PUT", headers=headers, data={"capacity": 0})
    if status == 400:
        print(f"SUCCESS: Zero capacity correctly rejected with 400: {bad_zero_res.get('detail')}")
    else:
        print(f"FAILED: Expected 400 for capacity 0, got {status}")
        return False

    # Test updating to a new capacity (e.g., 18500)
    new_cap = 18500
    status, updated_evt = request_json(f"{BASE_URL}/events/{evt_id}", method="PUT", headers=headers, data={"capacity": new_cap})
    if status != 200:
        print(f"FAILED: Updating capacity to {new_cap} failed: status={status}, res={updated_evt}")
        return False
    
    expected_limit = int(new_cap * 0.85)
    if updated_evt.get("capacity") == new_cap and updated_evt.get("limits") == expected_limit:
        print(f"SUCCESS: Updated capacity to {new_cap} and auto-calculated warning limits to {expected_limit}")
    else:
        print(f"FAILED: Mismatch in updated event data: {updated_evt}")
        return False

    # Verify re-fetch persistence
    status, refetch_evt = request_json(f"{BASE_URL}/events/{evt_id}", method="GET", headers=headers)
    if status == 200 and refetch_evt.get("capacity") == new_cap:
        print(f"SUCCESS: Capacity persisted and confirmed upon refresh: {refetch_evt.get('capacity')}")
    else:
        print(f"FAILED: Re-fetched capacity does not match {new_cap}: status={status}, res={refetch_evt}")
        return False

    print("\n=== TEST 2: Emergency Service Dispatch Workflow ===")
    # Test invalid service type
    status, bad_service_res = request_json(f"{BASE_URL}/emergency/dispatch-service", method="POST", headers=headers, data={
        "service_type": "alien_defense",
        "event_id": evt_id
    })
    if status == 400:
        print(f"SUCCESS: Invalid service type correctly rejected with 400: {bad_service_res.get('detail')}")
    else:
        print(f"FAILED: Expected 400 for invalid service, got {status}")
        return False

    # Test authorized Medical / Ambulance dispatch
    status, med_data = request_json(f"{BASE_URL}/emergency/dispatch-service", method="POST", headers=headers, data={
        "service_type": "medical",
        "event_id": evt_id,
        "station_name": "Station 4 - City General EMS Unit (Nearest)"
    })
    if status != 200:
        print(f"FAILED: Medical dispatch failed: status={status}, res={med_data}")
        return False
    
    if med_data.get("success") and med_data.get("status") == "DISPATCHED":
        print(f"SUCCESS: Medical dispatch created: {med_data['dispatch_id']}, Status: {med_data['status']}, Station: {med_data['station_name']}")
    else:
        print(f"FAILED: Unexpected dispatch response: {med_data}")
        return False

    # Test authorized Fire dispatch
    status, fire_data = request_json(f"{BASE_URL}/emergency/dispatch-service", method="POST", headers=headers, data={
        "service_type": "fire",
        "event_id": evt_id,
        "station_name": "Engine Company 12 - Metro Fire Command (Nearest)"
    })
    if status != 200:
        print(f"FAILED: Fire dispatch failed: status={status}, res={fire_data}")
        return False

    if fire_data.get("success") and fire_data.get("status") == "DISPATCHED":
        print(f"SUCCESS: Fire dispatch created: {fire_data['dispatch_id']}, Status: {fire_data['status']}, Station: {fire_data['station_name']}")
    else:
        print(f"FAILED: Unexpected dispatch response: {fire_data}")
        return False

    # Check emergency status to verify dispatches are persisted and returned
    status, emg_status_res = request_json(f"{BASE_URL}/emergency/status?event_id={evt_id}", method="GET", headers=headers)
    if status == 200:
        dispatches = emg_status_res.get("dispatches", [])
        med_disp = [d for d in dispatches if d["service_type"] == "medical"]
        fire_disp = [d for d in dispatches if d["service_type"] == "fire"]
        if med_disp and fire_disp:
            print(f"SUCCESS: Emergency status verifies persisted dispatches ({len(dispatches)} active dispatches in DB)")
        else:
            print(f"WARNING: Dispatches not in emergency status: {emg_status_res}")
    else:
        print(f"FAILED: Failed to fetch emergency status: {status}")
        return False

    print("\n=== ALL AUTOMATED ACCEPTANCE TESTS PASSED SUCCESSFULLY! ===")
    return True

if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)

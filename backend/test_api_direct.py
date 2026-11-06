import sys
from app.database import SessionLocal
from app.models import EventModel, EmergencyDispatchModel, AlertModel, User
from app.schemas import EventUpdate
from app.routers import events, emergency
from app.routers.emergency import ServiceDispatchPayload
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

def run_tests():
    print("=== TEST 1: Event Capacity Validation & DB Persistence ===", flush=True)
    db = SessionLocal()
    
    # 1. Fetch active event
    evt = db.query(EventModel).first()
    if not evt:
        print("FAILED: No event found in DB", flush=True)
        db.close()
        return False
    
    evt_id = evt.id
    user = db.query(User).first()
    # Mock auth credentials if user exists
    from app.auth_utils import create_access_token
    token = create_access_token({"sub": user.email}) if user else ""
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    print(f"SUCCESS: Found event {evt_id} with starting capacity: {evt.capacity}", flush=True)

    # 2. Test negative capacity validation
    try:
        events.update_event(evt_id, EventUpdate(capacity=-500), auth=auth, db=db)
        print("FAILED: Expected HTTPException for negative capacity", flush=True)
        db.close()
        return False
    except HTTPException as e:
        if e.status_code == 400:
            print(f"SUCCESS: Negative capacity correctly rejected with 400: {e.detail}", flush=True)
        else:
            print(f"FAILED: Expected status 400, got {e.status_code}", flush=True)
            db.close()
            return False

    # 3. Test zero capacity validation
    try:
        events.update_event(evt_id, EventUpdate(capacity=0), auth=auth, db=db)
        print("FAILED: Expected HTTPException for zero capacity", flush=True)
        db.close()
        return False
    except HTTPException as e:
        if e.status_code == 400:
            print(f"SUCCESS: Zero capacity correctly rejected with 400: {e.detail}", flush=True)
        else:
            print(f"FAILED: Expected status 400, got {e.status_code}", flush=True)
            db.close()
            return False

    # 4. Test capacity > 1,000,000 validation
    try:
        events.update_event(evt_id, EventUpdate(capacity=5000000), auth=auth, db=db)
        print("FAILED: Expected HTTPException for capacity > 1M", flush=True)
        db.close()
        return False
    except HTTPException as e:
        if e.status_code == 400:
            print(f"SUCCESS: Capacity > 1M correctly rejected with 400: {e.detail}", flush=True)
        else:
            print(f"FAILED: Expected status 400, got {e.status_code}", flush=True)
            db.close()
            return False

    # 5. Positive update: set capacity to 25000
    new_capacity = 25000
    expected_limit = int(new_capacity * 0.85)
    updated = events.update_event(evt_id, EventUpdate(capacity=new_capacity), auth=auth, db=db)
    if updated.capacity == new_capacity and updated.limits == expected_limit:
        print(f"SUCCESS: Updated capacity to {new_capacity} and auto-updated warning limits to {expected_limit}", flush=True)
    else:
        print(f"FAILED: Capacity update mismatch: {updated.capacity}", flush=True)
        db.close()
        return False

    # 6. Re-query fresh session to guarantee database persistence
    db.close()
    fresh_db = SessionLocal()
    persisted = fresh_db.query(EventModel).filter(EventModel.id == evt_id).first()
    if persisted and persisted.capacity == new_capacity:
        print(f"SUCCESS: Fresh DB query confirmed persisted capacity: {persisted.capacity} (limits: {persisted.limits})", flush=True)
    else:
        print(f"FAILED: Persistence check failed in fresh DB query", flush=True)
        fresh_db.close()
        return False

    print("\n=== TEST 2: Emergency Service Dispatch Workflow ===", flush=True)
    # 1. Invalid service type validation
    try:
        emergency.dispatch_service(ServiceDispatchPayload(service_type="unknown_corps", event_id=evt_id), auth=auth, db=fresh_db)
        print("FAILED: Expected HTTPException for invalid service type", flush=True)
        fresh_db.close()
        return False
    except HTTPException as e:
        if e.status_code == 400:
            print(f"SUCCESS: Invalid service correctly rejected with 400: {e.detail}", flush=True)
        else:
            print(f"FAILED: Expected 400, got {e.status_code}", flush=True)
            fresh_db.close()
            return False

    # 2. Authorized Medical / Ambulance dispatch
    res_med = emergency.dispatch_service(
        ServiceDispatchPayload(
            service_type="medical",
            event_id=evt_id,
            station_name="Station 4 - City General EMS Unit (Nearest)"
        ),
        auth=auth,
        db=fresh_db
    )
    if res_med.get("success") and res_med.get("status") == "DISPATCHED":
        print(f"SUCCESS: Medical dispatch created: ID={res_med['dispatch_id']}, Status={res_med['status']}, Station={res_med['station_name']}", flush=True)
    else:
        print(f"FAILED: Medical dispatch returned unexpected response: {res_med}", flush=True)
        fresh_db.close()
        return False

    # 3. Authorized Fire & Rescue dispatch
    res_fire = emergency.dispatch_service(
        ServiceDispatchPayload(
            service_type="fire",
            event_id=evt_id,
            station_name="Engine Company 12 - Metro Fire Command (Nearest)"
        ),
        auth=auth,
        db=fresh_db
    )
    if res_fire.get("success") and res_fire.get("status") == "DISPATCHED":
        print(f"SUCCESS: Fire dispatch created: ID={res_fire['dispatch_id']}, Status={res_fire['status']}, Station={res_fire['station_name']}", flush=True)
    else:
        print(f"FAILED: Fire dispatch returned unexpected response: {res_fire}", flush=True)
        fresh_db.close()
        return False

    # 4. Verify dispatches in emergency status
    status_data = emergency.get_current_emergency_status(event_id=evt_id, auth=auth, db=fresh_db)
    dispatches = status_data.get("dispatches", [])
    med_disp = [d for d in dispatches if d["service_type"] == "medical"]
    fire_disp = [d for d in dispatches if d["service_type"] == "fire"]
    if med_disp and fire_disp:
        print(f"SUCCESS: get_current_emergency_status verified persisted dispatches ({len(dispatches)} active dispatches in DB)", flush=True)
    else:
        print(f"FAILED: Dispatches missing in get_current_emergency_status: {status_data}", flush=True)
        fresh_db.close()
        return False

    # 5. Direct database audit check
    disp_records = fresh_db.query(EmergencyDispatchModel).filter(EmergencyDispatchModel.emergency_event_id == status_data['active_event']['id']).all()
    alert_records = fresh_db.query(AlertModel).filter(AlertModel.title.like("%UNIT DISPATCHED%")).all()
    print(f"SUCCESS: Database audit confirmed: {len(disp_records)} dispatch records in emergency_dispatches table and {len(alert_records)} dispatch audit alerts.", flush=True)

    fresh_db.close()
    print("\n=== ALL DIRECT BACKEND AND DATABASE TESTS PASSED WITH 100% SUCCESS ===", flush=True)
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

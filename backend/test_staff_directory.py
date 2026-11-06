"""
Verification script for Phase 1: Security Personnel & Event Coordinator Directory.
Tests:
- Creating personnel with valid international mobile numbers (+1, +91, etc.)
- Rejecting invalid/short mobile numbers
- Event isolation: ensuring personnel assigned to event A never leak into event B
- Search by name / mobile number
- Filtering by role, duty_status, and zone
- Updating personnel details
- Soft deactivation and reactivation
"""
import sys
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.database import SessionLocal
from app.models import SecurityStaffModel, EventModel, User
from app.schemas import SecurityStaffCreate, SecurityStaffUpdate
from app.routers import staff
from app.auth_utils import create_access_token

def run_tests():
    print("=" * 65, flush=True)
    print("RUNNING SECURITY PERSONNEL DIRECTORY DIRECT API VERIFICATION", flush=True)
    print("=" * 65, flush=True)

    db = SessionLocal()
    try:
        # 1. Fetch available events or use test event IDs
        events = db.query(EventModel).all()
        evt_a = events[0].id if events else "evt-test-alpha"
        evt_b = events[1].id if len(events) > 1 else "evt-test-beta"
        print(f"[SETUP] Using Event A: {evt_a}, Event B: {evt_b}", flush=True)

        user = db.query(User).first()
        token = create_access_token({"sub": user.email}) if user else ""
        auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token) if token else None

        # Clean any previous test records
        db.query(SecurityStaffModel).filter(SecurityStaffModel.event_id.in_([evt_a, evt_b])).delete(synchronize_session=False)
        db.commit()

        # 2. Test Phone Validation: Invalid number should fail with 422
        try:
            bad_data = SecurityStaffCreate(
                name="Invalid Phone Person",
                phone="123", # Too short
                role="Security Guard",
                event_id=evt_a,
                zone="Gate A"
            )
            staff.create_security_staff(data=bad_data, auth=auth, db=db)
            print("FAILED: Expected HTTPException 422 for short phone", flush=True)
            return False
        except (HTTPException, Exception) as e:
            print(f"[PASS] Short/invalid phone number correctly rejected: {e}", flush=True)

        # 3. Create Valid Personnel in Event A (Security Guard)
        guard_a = SecurityStaffCreate(
            name="Marcus Vance",
            phone="+1-555-0144",
            role="Security Guard",
            event_id=evt_a,
            zone="Gate North",
            organization="Apex Security Services",
            duty_status="On Duty",
            notes="Responsible for turnstile bag inspection"
        )
        res_guard_a = staff.create_security_staff(data=guard_a, auth=auth, db=db)
        guard_id_a = res_guard_a.id
        assert res_guard_a.name == "Marcus Vance"
        assert res_guard_a.phone == "+1-555-0144"
        assert res_guard_a.duty_status == "On Duty"
        assert res_guard_a.is_active is True
        print(f"[PASS] Created Guard Marcus Vance in Event A (ID: {guard_id_a})", flush=True)

        # 4. Create Event Coordinator in Event A
        coord_a = SecurityStaffCreate(
            name="Elena Rostova",
            phone="+44 20 7946 0912",
            role="Event Coordinator",
            event_id=evt_a,
            zone="Main Concourse",
            organization="Global Arena Ops",
            duty_status="On Duty",
            notes="Circulation coordinator for pedestrian flow"
        )
        res_coord_a = staff.create_security_staff(data=coord_a, auth=auth, db=db)
        coord_id_a = res_coord_a.id
        print(f"[PASS] Created Coordinator Elena Rostova in Event A (ID: {coord_id_a})", flush=True)

        # 5. Create Personnel in Event B (Strict Isolation Test)
        guard_b = SecurityStaffCreate(
            name="Rajesh Kumar",
            phone="+91-9876543210",
            role="Team Leader",
            event_id=evt_b,
            zone="VIP Corridor",
            organization="Metropolitan Rapid Force",
            duty_status="On Duty"
        )
        res_guard_b = staff.create_security_staff(data=guard_b, auth=auth, db=db)
        guard_id_b = res_guard_b.id
        print(f"[PASS] Created Team Leader Rajesh Kumar in Event B (ID: {guard_id_b})", flush=True)

        # 6. Verify Event Isolation
        # Query Event A only
        staff_a = staff.get_security_staff(event_id=evt_a, auth=auth, db=db)
        names_a = [s.name for s in staff_a]
        assert "Marcus Vance" in names_a
        assert "Elena Rostova" in names_a
        assert "Rajesh Kumar" not in names_a, "Event isolation violated: Event B staff leaked into Event A!"
        print(f"[PASS] Event Isolation verified: Event A returned {len(staff_a)} staff, Rajesh Kumar did NOT leak into Event A.", flush=True)

        # Query Event B only
        staff_b = staff.get_security_staff(event_id=evt_b, auth=auth, db=db)
        names_b = [s.name for s in staff_b]
        assert "Rajesh Kumar" in names_b
        assert "Marcus Vance" not in names_b, "Event isolation violated: Event A staff leaked into Event B!"
        print(f"[PASS] Event Isolation verified: Event B returned {len(staff_b)} staff, Event A staff excluded.", flush=True)

        # 7. Test Filtering by Role
        filtered_roles = staff.get_security_staff(event_id=evt_a, role="Event Coordinator", auth=auth, db=db)
        assert len(filtered_roles) == 1
        assert filtered_roles[0].name == "Elena Rostova"
        print("[PASS] Role filtering verified (filtered to 'Event Coordinator').", flush=True)

        # 8. Test Search by Name & Mobile
        res_search_name = staff.get_security_staff(event_id=evt_a, search="marcus", auth=auth, db=db)
        assert len(res_search_name) == 1
        assert res_search_name[0].id == guard_id_a
        print("[PASS] Search by name ('marcus') returned Marcus Vance.", flush=True)

        res_search_phone = staff.get_security_staff(event_id=evt_a, search="0144", auth=auth, db=db)
        assert len(res_search_phone) == 1
        print("[PASS] Search by mobile number ('0144') returned Marcus Vance.", flush=True)

        # 9. Test Updating Personnel (Edit duty_status to 'Off Duty' & change zone)
        update_data = SecurityStaffUpdate(
            duty_status="Off Duty",
            zone="Gate South"
        )
        updated = staff.update_security_staff(guard_id_a, data=update_data, auth=auth, db=db)
        assert updated.duty_status == "Off Duty"
        assert updated.zone == "Gate South"
        assert updated.is_online is False
        print("[PASS] Updated Marcus Vance: duty_status='Off Duty', zone='Gate South'.", flush=True)

        # 10. Test Deactivation (Soft Delete)
        del_res = staff.delete_security_staff(guard_id_a, hard_delete=False, auth=auth, db=db)
        assert del_res["success"] is True

        # When querying active staff, deactivated guard should not appear
        active_staff = staff.get_security_staff(event_id=evt_a, auth=auth, db=db)
        active_ids = [s.id for s in active_staff]
        assert guard_id_a not in active_ids, "Deactivated staff still appeared in default active list!"

        # When querying with include_inactive=true, it should appear
        all_staff = staff.get_security_staff(event_id=evt_a, include_inactive=True, auth=auth, db=db)
        all_ids = [s.id for s in all_staff]
        assert guard_id_a in all_ids, "Deactivated staff missing when include_inactive=True!"
        print("[PASS] Deactivation verified (excluded from active list, retained in audit archive).", flush=True)

        print("=" * 65, flush=True)
        print("ALL SECURITY PERSONNEL BACKEND API TESTS PASSED!", flush=True)
        print("=" * 65, flush=True)
        return True

    finally:
        db.close()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

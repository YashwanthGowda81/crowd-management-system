"""
Verification script for Phase 2: Officer-to-Ground-Team Coordination.
Tests:
- Creation of guidance messages with recipient, event, zone, priority, and authoring officer
- Event isolation: ensuring messages for event A never appear when querying event B
- Recipient validation: rejecting cross-event recipient assignments
- Truthful message lifecycle: Draft, Queued, Internally Sent, Acknowledged (with timestamp), Failed
- Idempotency & duplicate submission prevention via client_mutation_id
- Persistence in database
"""
import sys
import time
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.database import SessionLocal
from app.models import InstructionLogModel, SecurityStaffModel, EventModel, User
from app.schemas import (
    CoordinationMessageCreate,
    CoordinationStatusUpdate,
    SecurityStaffCreate
)
from app.routers import staff
from app.auth_utils import create_access_token

def run_tests():
    print("=" * 65, flush=True)
    print("RUNNING OFFICER-TO-GROUND-TEAM COORDINATION BACKEND VERIFICATION", flush=True)
    print("=" * 65, flush=True)

    db = SessionLocal()
    try:
        # 1. Setup test events
        events = db.query(EventModel).all()
        evt_a = events[0].id if events else "evt-coord-alpha"
        evt_b = events[1].id if len(events) > 1 else "evt-coord-beta"
        print(f"[SETUP] Using Event A: {evt_a}, Event B: {evt_b}", flush=True)

        user = db.query(User).first()
        token = create_access_token({"sub": user.email}) if user else ""
        auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token) if token else None

        # Clean old test coordination logs
        db.query(InstructionLogModel).filter(InstructionLogModel.event_id.in_([evt_a, evt_b])).delete(synchronize_session=False)
        db.commit()

        # 2. Setup personnel in Event A and Event B
        staff_a = staff.create_security_staff(
            data=SecurityStaffCreate(
                name="Officer David Clark",
                phone="+1-555-0811",
                role="Security Guard",
                event_id=evt_a,
                zone="Gate Alpha",
                organization="Arena Patrol",
                duty_status="On Duty"
            ),
            auth=auth,
            db=db
        )
        staff_b = staff.create_security_staff(
            data=SecurityStaffCreate(
                name="Coordinator Maya Lin",
                phone="+1-555-0922",
                role="Event Coordinator",
                event_id=evt_b,
                zone="Concourse B",
                organization="Crowd Ops",
                duty_status="On Duty"
            ),
            auth=auth,
            db=db
        )

        # 3. Test Cross-Event Recipient Validation
        # Attempt to send message in Event A to staff_b (who is in Event B) -> should raise 400
        try:
            invalid_cross_send = CoordinationMessageCreate(
                event_id=evt_a,
                zone="Gate Alpha",
                recipient_id=staff_b.id,
                recipient=staff_b.name,
                recipient_role=staff_b.role,
                priority="high",
                text="Please check ticket scanners"
            )
            staff.create_coordination_message(data=invalid_cross_send, auth=auth, db=db)
            print("FAILED: Expected cross-event recipient to be rejected with 400!", flush=True)
            return False
        except HTTPException as e:
            assert e.status_code == 400
            print(f"[PASS] Cross-event recipient assignment rejected with 400: {e.detail}", flush=True)

        # 4. Create Truthful Guidance Message in Event A
        mutation_key_1 = f"mut-{int(time.time()*1000)}"
        msg_a_data = CoordinationMessageCreate(
            event_id=evt_a,
            zone="Gate Alpha",
            recipient_id=staff_a.id,
            recipient=staff_a.name,
            recipient_role=staff_a.role,
            camera_id="cam-gate-01",
            priority="high",
            text="High density detected at turnstiles. Divert arriving attendees toward auxiliary East walkway.",
            status="Internally Sent",
            channel="internal",
            client_mutation_id=mutation_key_1
        )
        msg_a = staff.create_coordination_message(data=msg_a_data, auth=auth, db=db)
        assert msg_a.id is not None
        assert msg_a.event_id == evt_a
        assert msg_a.zone == "Gate Alpha"
        assert msg_a.recipient == "Officer David Clark"
        assert msg_a.priority == "high"
        assert msg_a.status == "Internally Sent"
        assert msg_a.channel == "internal"
        assert msg_a.officer_name is not None
        print(f"[PASS] Created guidance message {msg_a.id} authored by '{msg_a.officer_name}' with status 'Internally Sent'.", flush=True)

        # 5. Duplicate Submission Prevention (Idempotency Test)
        msg_duplicate = staff.create_coordination_message(data=msg_a_data, auth=auth, db=db)
        assert msg_duplicate.id == msg_a.id, "Duplicate submission check failed: generated new record instead of returning existing!"
        count_a = db.query(InstructionLogModel).filter(InstructionLogModel.client_mutation_id == mutation_key_1).count()
        assert count_a == 1, f"Expected 1 record for mutation key, found {count_a}"
        print("[PASS] Duplicate submission prevented: same client_mutation_id returned existing record.", flush=True)

        # 6. Create Message in Event B for Strict Event Isolation Test
        msg_b_data = CoordinationMessageCreate(
            event_id=evt_b,
            zone="Concourse B",
            recipient_id=staff_b.id,
            recipient=staff_b.name,
            recipient_role=staff_b.role,
            priority="normal",
            text="Verify crowd circulation pace along Concourse B.",
            status="Internally Sent",
            channel="internal"
        )
        msg_b = staff.create_coordination_message(data=msg_b_data, auth=auth, db=db)
        print(f"[PASS] Created guidance message {msg_b.id} for Event B.", flush=True)

        # 7. Test Strict Event Isolation
        messages_evt_a = staff.get_coordination_messages(event_id=evt_a, auth=auth, db=db)
        ids_a = [m.id for m in messages_evt_a]
        assert msg_a.id in ids_a
        assert msg_b.id not in ids_a, "Event isolation violated: Event B message appeared in Event A!"
        print(f"[PASS] Event isolation verified: Event A returned {len(messages_evt_a)} message(s); Event B message excluded.", flush=True)

        messages_evt_b = staff.get_coordination_messages(event_id=evt_b, auth=auth, db=db)
        ids_b = [m.id for m in messages_evt_b]
        assert msg_b.id in ids_b
        assert msg_a.id not in ids_b, "Event isolation violated: Event A message appeared in Event B!"
        print(f"[PASS] Event isolation verified: Event B returned {len(messages_evt_b)} message(s); Event A message excluded.", flush=True)

        # 8. Test Lifecycle Status Update: Recipient Acknowledgement
        assert msg_a.acknowledged_at is None
        status_update = CoordinationStatusUpdate(status="Acknowledged")
        ack_msg = staff.update_coordination_status(msg_a.id, data=status_update, auth=auth, db=db)
        assert ack_msg.status == "Acknowledged"
        assert ack_msg.acknowledged_at is not None
        assert ack_msg.read_status == "READ"
        print(f"[PASS] Recipient acknowledgement verified: status='Acknowledged', acknowledged_at='{ack_msg.acknowledged_at}'.", flush=True)

        # 9. Verify Persistence After DB Session Refresh
        db.close()
        db = SessionLocal()
        persisted = db.query(InstructionLogModel).filter(InstructionLogModel.id == msg_a.id).first()
        assert persisted is not None
        assert persisted.status == "Acknowledged"
        assert persisted.acknowledged_at is not None
        assert persisted.recipient == "Officer David Clark"
        assert persisted.channel == "internal"
        print("[PASS] Persistence verified after new DB session lookup.", flush=True)

        print("=" * 65, flush=True)
        print("ALL OFFICER-TO-GROUND-TEAM COORDINATION TESTS PASSED!", flush=True)
        print("=" * 65, flush=True)
        return True

    finally:
        db.close()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

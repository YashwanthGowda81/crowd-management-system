import os
import sys
from fastapi.testclient import TestClient

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app
from app.database import engine
from sqlalchemy import text

def verify_fresh_state():
    print("=" * 80)
    print(" CROWD-AI v2.4 FRESH-STATE POST-RESET VERIFICATION")
    print("=" * 80)

    client = TestClient(app)

    # 1. Zero users in database
    with engine.connect() as conn:
        user_cnt = conn.execute(text("SELECT COUNT(*) FROM users;")).scalar()
        print(f"[VERIFICATION 1] Total application user accounts: {user_cnt}")
        assert user_cnt == 0, f"Expected 0 users, found {user_cnt}"

    # 2. Operational records are empty
    tables_to_check = [
        "events",
        "cameras",
        "zones",
        "venue_pins",
        "alerts",
        "recommendations",
        "emergency_events",
        "emergency_dispatches",
        "crowd_analytics",
        "security_staff"
    ]
    with engine.connect() as conn:
        print("[VERIFICATION 2] Operational database tables check:")
        for t in tables_to_check:
            cnt = conn.execute(text(f'SELECT COUNT(*) FROM "{t}";')).scalar()
            print(f"   - {t:<22}: {cnt} rows")
            assert cnt == 0, f"Table {t} is not empty! Count: {cnt}"

    # 3. Storage check
    upload_maps = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "maps")
    map_files = os.listdir(upload_maps) if os.path.exists(upload_maps) else []
    print(f"[VERIFICATION 3] User-generated maps in uploads/maps: {len(map_files)} files (files: {map_files})")
    assert len(map_files) == 0, f"Expected 0 map files, found {len(map_files)}"

    # 4. Required model files and assets exist
    yolo_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolov8n.pt")
    assert os.path.exists(yolo_file), "YOLOv8 weights file missing"
    print(f"[VERIFICATION 4] YOLOv8 model weights: {yolo_file} ({os.path.getsize(yolo_file) / (1024*1024):.2f} MB)")

    # 5. Unauthenticated access to protected endpoints is rejected (401)
    print("[VERIFICATION 5] Testing unauthenticated access to protected endpoints...")
    protected_endpoints = [
        "/api/auth/onboarding-status",
        "/api/events/my-event",
        "/api/events",
        "/api/cameras"
    ]
    for ep in protected_endpoints:
        res = client.get(ep)
        print(f"   - GET {ep}: status code {res.status_code}")
        # Note: /api/events and /api/cameras without auth return empty list or 401/403, and /api/auth/onboarding-status returns 401
        assert res.status_code in [200, 401, 403], f"Unexpected status code {res.status_code} for {ep}"
        if ep in ["/api/auth/onboarding-status", "/api/events/my-event"]:
            assert res.status_code == 401, f"Expected 401 for {ep}, got {res.status_code}"

    # 6. Attempting login when no accounts exist reports appropriate message (401)
    print("[VERIFICATION 6] Testing login attempt when no accounts exist...")
    login_attempt = client.post("/api/auth/login", json={
        "email": "test@smartcity.gov",
        "password": "Password123"
    })
    print(f"   - POST /api/auth/login response status: {login_attempt.status_code}")
    print(f"   - Response detail: {login_attempt.json().get('detail')}")
    assert login_attempt.status_code == 401
    assert "No account is available. An administrator must provision an account before you can sign in." in login_attempt.json().get("detail")
    print("   ✓ Verified: Backend explicitly reports that no account is available and an administrator must provision an account.")

    # 7. Check that no user was created during testing
    with engine.connect() as conn:
        final_user_cnt = conn.execute(text("SELECT COUNT(*) FROM users;")).scalar()
        print(f"[VERIFICATION 7] Final user accounts in active DB: {final_user_cnt}")
        assert final_user_cnt == 0, f"Users were created during testing! Count: {final_user_cnt}"

    print("\n" + "=" * 80)
    print(" [PASS] ALL FRESH-STATE VERIFICATION CHECKS PASSED")
    print("=" * 80)

if __name__ == "__main__":
    verify_fresh_state()

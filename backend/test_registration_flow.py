import sys
import os
import json

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal
from app.models import User
from app.auth_utils import verify_password

client = TestClient(app)

def run_tests():
    print("==================================================")
    print("STARTING CROWD-AI REGISTRATION & LOGIN AUDIT SUITE")
    print("==================================================")

    db = SessionLocal()
    try:
        # Step 0: Ensure starting state
        initial_users = db.query(User).count()
        print(f"[*] Initial users in database: {initial_users}")

        # -------------------------------------------------------------
        # TEST 1: Login attempt when database has zero users
        # -------------------------------------------------------------
        print("\n[TEST 1] Testing login when zero users exist...")
        # If there are any users, clean them for this test
        if initial_users > 0:
            db.query(User).delete()
            db.commit()

        login_res = client.post("/api/auth/login", json={
            "email": "nobody@surveillance.gov",
            "password": "Password123!"
        })
        print(f"Status Code: {login_res.status_code}")
        print(f"Response: {login_res.json()}")
        assert login_res.status_code == 401, f"Expected 401, got {login_res.status_code}"
        assert "No account is available" in login_res.json().get("detail", ""), "Expected friendly zero-user message"
        print(">>> TEST 1 PASSED: Zero-user login handled safely with 401 and informational message.")

        # -------------------------------------------------------------
        # TEST 2: Validation errors for registration fields
        # -------------------------------------------------------------
        print("\n[TEST 2] Testing validation rules on registration...")

        # A: Short name
        res = client.post("/api/auth/register", json={
            "name": "A",
            "email": "valid@surveillance.gov",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!"
        })
        assert res.status_code == 400, f"Expected 400 for short name, got {res.status_code}"
        print("  - Short name (<2 chars) rejected: OK")

        # B: Invalid email format
        res = client.post("/api/auth/register", json={
            "name": "Valid Name",
            "email": "not-an-email",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!"
        })
        assert res.status_code == 400, f"Expected 400 for invalid email, got {res.status_code}"
        print("  - Invalid email format rejected: OK")

        # C: Short password
        res = client.post("/api/auth/register", json={
            "name": "Valid Name",
            "email": "valid@surveillance.gov",
            "password": "short",
            "confirm_password": "short"
        })
        assert res.status_code == 400, f"Expected 400 for short password, got {res.status_code}"
        print("  - Short password (<8 chars) rejected: OK")

        # D: Password mismatch
        res = client.post("/api/auth/register", json={
            "name": "Valid Name",
            "email": "valid@surveillance.gov",
            "password": "ValidPassword123!",
            "confirm_password": "DifferentPassword123!"
        })
        assert res.status_code == 400, f"Expected 400 for password mismatch, got {res.status_code}"
        print("  - Password confirmation mismatch rejected: OK")
        print(">>> TEST 2 PASSED: All invalid inputs properly rejected with 400.")

        # -------------------------------------------------------------
        # TEST 3: Privilege escalation prevention (Admin role rejection)
        # -------------------------------------------------------------
        print("\n[TEST 3] Testing privilege escalation prevention...")
        for bad_role in ["admin", "Super Admin", "administrator", "root"]:
            safe_suffix = bad_role.lower().replace(" ", "_")
            res = client.post("/api/auth/register", json={
                "name": "Attacker",
                "email": f"attacker_{safe_suffix}@surveillance.gov",
                "password": "SuperSecretPassword123!",
                "confirm_password": "SuperSecretPassword123!",
                "role": bad_role
            })
            assert res.status_code == 403, f"Expected 403 Forbidden for role '{bad_role}', got {res.status_code}"
        print(">>> TEST 3 PASSED: All administrator role escalation attempts rejected with 403 Forbidden.")

        # -------------------------------------------------------------
        # TEST 4: Successful User Registration
        # -------------------------------------------------------------
        print("\n[TEST 4] Testing valid user registration...")
        test_email = "commander.shepard@surveillance.gov"
        test_pass = "N7Normandy#2026"
        test_name = "Commander Shepard"

        reg_res = client.post("/api/auth/register", json={
            "name": test_name,
            "email": test_email,
            "password": test_pass,
            "confirm_password": test_pass
        })
        print(f"Status Code: {reg_res.status_code}")
        reg_data = reg_res.json()
        print(f"Response: {reg_data}")
        assert reg_res.status_code == 201, f"Expected 201, got {reg_res.status_code}"
        assert "password" not in reg_data, "Plaintext password exposed in response!"
        assert "hashed_password" not in reg_data, "Password hash exposed in response!"
        assert reg_data["email"] == test_email
        assert reg_data["name"] == test_name
        assert reg_data["role"] == "Command Officer"

        # Verify in DB
        db_user = db.query(User).filter(User.email == test_email).first()
        assert db_user is not None, "User record not found in database!"
        assert db_user.hashed_password != test_pass, "Password was stored in plaintext!"
        assert verify_password(test_pass, db_user.hashed_password), "Stored hash failed verification with plaintext password!"
        print(f"DB verification: User ID={db_user.id}, Role={db_user.role}, Hash prefix={db_user.hashed_password[:15]}...")
        print(">>> TEST 4 PASSED: User successfully registered, stored with secure hash, no secrets leaked.")

        # -------------------------------------------------------------
        # TEST 5: Duplicate Email Registration Rejection
        # -------------------------------------------------------------
        print("\n[TEST 5] Testing duplicate email rejection (case-insensitive)...")
        dup_res = client.post("/api/auth/register", json={
            "name": "Duplicate Shepard",
            "email": test_email.upper(),  # Test uppercase variation
            "password": "AnotherPassword123!",
            "confirm_password": "AnotherPassword123!"
        })
        print(f"Status Code: {dup_res.status_code}")
        print(f"Response: {dup_res.json()}")
        assert dup_res.status_code == 400, f"Expected 400 for duplicate email, got {dup_res.status_code}"
        assert "already exists" in dup_res.json().get("detail", "").lower()
        print(">>> TEST 5 PASSED: Duplicate registration safely blocked with 400.")

        # -------------------------------------------------------------
        # TEST 6: Login with Registered User
        # -------------------------------------------------------------
        print("\n[TEST 6] Testing login with newly registered credentials...")
        # 6A: Wrong password
        wrong_res = client.post("/api/auth/login", json={
            "email": test_email,
            "password": "WrongPassword999!"
        })
        assert wrong_res.status_code == 401, f"Expected 401 for bad password, got {wrong_res.status_code}"
        print("  - Wrong password rejected: OK")

        # 6B: Correct password (test case-insensitive email matching too)
        login_ok_res = client.post("/api/auth/login", json={
            "email": test_email.upper(),
            "password": test_pass
        })
        assert login_ok_res.status_code == 200, f"Expected 200 for valid login, got {login_ok_res.status_code}"
        login_ok_data = login_ok_res.json()
        token = login_ok_data.get("token")
        assert token is not None, "Missing token in login response"
        assert login_ok_data.get("email") == test_email
        print(f"  - Login successful! Token received: {token[:20]}...")
        print(">>> TEST 6 PASSED: Login endpoint authenticates registered user correctly.")

        # -------------------------------------------------------------
        # TEST 7: Onboarding status for new user (needs_event -> /event-setup)
        # -------------------------------------------------------------
        print("\n[TEST 7] Testing onboarding status for registered user...")
        auth_headers = {"Authorization": f"Bearer {token}"}
        status_res = client.get("/api/auth/onboarding-status", headers=auth_headers)
        assert status_res.status_code == 200, f"Expected 200, got {status_res.status_code}"
        status_data = status_res.json()
        print(f"Onboarding Status: {json.dumps(status_data, indent=2)}")
        assert status_data["has_event"] is False, "New user should not have an event yet"
        assert status_data["has_source"] is False, "New user should not have cameras yet"
        assert status_data["status"] == "needs_event", "Status must be 'needs_event'"
        assert status_data["next_route"] == "/event-setup", "Next route must be '/event-setup'"
        print(">>> TEST 7 PASSED: Onboarding engine correctly directs new user to /event-setup.")

        # -------------------------------------------------------------
        # TEST 8: Protected endpoints reject unauthenticated requests
        # -------------------------------------------------------------
        print("\n[TEST 8] Testing unauthenticated access to protected routes...")
        unauth_status = client.get("/api/auth/onboarding-status")
        assert unauth_status.status_code == 401, f"Expected 401, got {unauth_status.status_code}"
        
        unauth_event = client.get("/api/events/my-event")
        assert unauth_event.status_code == 401, f"Expected 401, got {unauth_event.status_code}"
        print(">>> TEST 8 PASSED: Protected endpoints require valid JWT bearer token.")

        # -------------------------------------------------------------
        # Step Final: Cleanup test user to keep DB in clean state
        # -------------------------------------------------------------
        print("\n[CLEANUP] Cleaning up test operator record to restore 0-user database state...")
        db.delete(db_user)
        db.commit()
        remaining_count = db.query(User).count()
        print(f"Users remaining in database after test: {remaining_count}")
        assert remaining_count == 0, "Database should have 0 users after cleanup"
        print(">>> CLEANUP COMPLETED: Database restored to fresh 0-account state.")

        print("\n==================================================")
        print("ALL REGISTRATION & LOGIN AUDIT CHECKS PASSED (8/8)")
        print("==================================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_tests()

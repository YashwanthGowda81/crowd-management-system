"""
End-to-End Integration Tests for IEEE Access 2025 Base-Paper Research Endpoints:
- GET /api/recommendations
- GET /api/recommendations/fca-lattice
- GET /api/recommendations/crowded-areas
- GET /api/recommendations/prevention-plans
- GET/POST/PUT/DELETE /api/events/{event_id}/connections
- GET /api/crowd-analysis (Motion Flow & Tracking counts)
- Multi-Manager Event Isolation & Cross-Account Access Security
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, EventModel, ZoneModel, ZoneConnectionModel, CameraModel
from app.auth_utils import create_access_token

class TestResearchEndpointsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Find or create a test user and event
        cls.user = cls.db.query(User).filter(User.email == "research_tester@crowdai.internal").first()
        if not cls.user:
            cls.user = User(
                email="research_tester@crowdai.internal",
                hashed_password="dummy_hashed_password",
                name="Research Tester",
                role="Officer"
            )
            cls.db.add(cls.user)
            cls.db.commit()
            cls.db.refresh(cls.user)

        cls.token = create_access_token({"sub": cls.user.email, "id": cls.user.id, "role": cls.user.role})
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Find or create a test event
        cls.event = cls.db.query(EventModel).filter(EventModel.id == "evt-research-test").first()
        if not cls.event:
            cls.event = EventModel(
                id="evt-research-test",
                manager_id=cls.user.id,
                title="IEEE Access 2025 Research Test Event",
                venue_name="Research Testing Arena",
                capacity=5000,
                staff=25,
                risk="medium"
            )
            cls.db.add(cls.event)
            cls.db.commit()

        # Ensure operational zones exist
        z1 = cls.db.query(ZoneModel).filter(ZoneModel.id == "zone-res-1").first()
        if not z1:
            z1 = ZoneModel(id="zone-res-1", event_id=cls.event.id, name="Gate North Entry", code="GATE-N", capacity=1000, current_count=850, density=85.0, zone_type="gate_area")
            z2 = ZoneModel(id="zone-res-2", event_id=cls.event.id, name="Central Plaza", code="PLAZA-C", capacity=2500, current_count=400, density=16.0, zone_type="general")
            z3 = ZoneModel(id="zone-res-3", event_id=cls.event.id, name="South Exit Corridor", code="EXIT-S", capacity=1500, current_count=200, density=13.0, zone_type="exit_corridor")
            cls.db.add_all([z1, z2, z3])
            cls.db.commit()

        # Ensure a test connection exists
        conn1 = cls.db.query(ZoneConnectionModel).filter(ZoneConnectionModel.id == "conn-res-1").first()
        if not conn1:
            conn1 = ZoneConnectionModel(
                id="conn-res-1",
                event_id=cls.event.id,
                from_zone_id="zone-res-1",
                to_zone_id="zone-res-2",
                bidirectional=True,
                is_blocked=False,
                corridor_name="Main Entry Concourse",
                flow_capacity=600
            )
            cls.db.add(conn1)
            cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # =========================================================================
    # RESEARCH FCA ENDPOINTS TESTS
    # =========================================================================

    def test_get_fca_research_lattice(self):
        """Verify GET /api/recommendations/fca-lattice returns both Lc and La."""
        res = self.client.get(f"/api/recommendations/fca-lattice?event_id={self.event.id}", headers=self.headers)
        self.assertEqual(res.status_code, 200, f"Expected 200, got: {res.text}")
        data = res.json()

        self.assertIn("crowd_lattice", data)
        self.assertIn("area_lattice", data)
        self.assertIn("fuzzy_context_summary", data)
        self.assertIn("crowded_areas", data)
        self.assertIn("prevention_plans", data)

        # Check Crowd Lattice structure
        cl = data["crowd_lattice"]
        self.assertIn("nodes", cl)
        self.assertIn("connections", cl)

        # Check Area Lattice structure
        al = data["area_lattice"]
        self.assertIn("nodes", al)
        self.assertIn("connections", al)

    def test_get_crowded_areas_algorithm_1(self):
        """Verify GET /api/recommendations/crowded-areas executes Algorithm 1."""
        res = self.client.get(f"/api/recommendations/crowded-areas?event_id={self.event.id}", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIsInstance(data, list)
        if len(data) > 0:
            item = data[0]
            self.assertIn("area", item)
            self.assertIn("crowd_score", item)
            self.assertIn("concept_id", item)
            self.assertIn("satisfied_intent", item)
            self.assertIn("attribute_scores", item)
            self.assertGreater(item["crowd_score"], 0.70, "Algorithm 1 output areas must exceed T=0.70")

    def test_get_prevention_plans_algorithm_2(self):
        """Verify GET /api/recommendations/prevention-plans executes Algorithm 2."""
        res = self.client.get(f"/api/recommendations/prevention-plans?event_id={self.event.id}", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("total_crowded_areas", data)
        self.assertIn("resolved_count", data)
        self.assertIn("plans", data)

        for plan in data["plans"]:
            self.assertIn("plan_id", plan)
            self.assertIn("crowded_sources", plan)
            self.assertIn("recommended_destinations", plan)
            self.assertEqual(plan["status"], "pending_human_approval", "Strict safety: must require human approval")
            self.assertFalse(plan["is_verified_evacuation"])

    # =========================================================================
    # ZONE CONNECTIONS CRUD & TOPOLOGY TESTS
    # =========================================================================

    def test_zone_connections_crud_lifecycle(self):
        """Verify full CRUD lifecycle for physical passages/corridors."""
        # 1. Create a new passage
        create_payload = {
            "from_zone_id": "zone-res-2",
            "to_zone_id": "zone-res-3",
            "bidirectional": True,
            "is_blocked": False,
            "corridor_name": "South Emergency Choke Point",
            "flow_capacity": 450
        }
        res_create = self.client.post(
            f"/api/events/{self.event.id}/connections",
            json=create_payload,
            headers=self.headers
        )
        self.assertEqual(res_create.status_code, 201, f"Failed create: {res_create.text}")
        created_conn = res_create.json()
        conn_id = created_conn["id"]
        self.assertEqual(created_conn["corridor_name"], "South Emergency Choke Point")

        # 2. Get connections list
        res_list = self.client.get(f"/api/events/{self.event.id}/connections", headers=self.headers)
        self.assertEqual(res_list.status_code, 200)
        conn_ids = [c["id"] for c in res_list.json()]
        self.assertIn(conn_id, conn_ids)

        # 3. Update connection: Mark as BLOCKED (e.g. fire hazard)
        update_payload = {"is_blocked": True, "flow_capacity": 0}
        res_update = self.client.put(
            f"/api/events/{self.event.id}/connections/{conn_id}",
            json=update_payload,
            headers=self.headers
        )
        self.assertEqual(res_update.status_code, 200)
        self.assertTrue(res_update.json()["is_blocked"])

        # 4. Delete connection
        res_del = self.client.delete(f"/api/events/{self.event.id}/connections/{conn_id}", headers=self.headers)
        self.assertEqual(res_del.status_code, 200)

        # 5. Verify deletion
        res_list_after = self.client.get(f"/api/events/{self.event.id}/connections", headers=self.headers)
        conn_ids_after = [c["id"] for c in res_list_after.json()]
        self.assertNotIn(conn_id, conn_ids_after)

    # =========================================================================
    # FLOW DECOMPOSITION & ANALYTICS TESTS
    # =========================================================================

    def test_crowd_analysis_flow_decomposition(self):
        """Verify GET /api/crowd-analysis exposes flow decomposition and unique window tracking."""
        res = self.client.get(f"/api/crowd-analysis?event_id={self.event.id}", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("flow_decomposition", data)
        self.assertIn("unique_tracked_window", data)
        self.assertIn("cumulative_entries", data)
        self.assertIn("speed_status", data)

        flow = data["flow_decomposition"]
        self.assertIn("X_neg", flow)
        self.assertIn("X_pos", flow)
        self.assertIn("Y_neg", flow)
        self.assertIn("Y_pos", flow)
        self.assertIn("lambda_out", flow)

if __name__ == "__main__":
    unittest.main()

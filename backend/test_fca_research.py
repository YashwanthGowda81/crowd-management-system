"""
Unit & Algorithmic Tests for IEEE Access 2025 Base-Paper Components:
- Task 1: Fuzzy Formal Concept Analysis (Kc, Ka, Membership Functions)
- Task 2: Mathematically Valid Concept Lattice Generation (Galois Closure, Covering Relation)
- Task 3: Algorithm 1 — Extraction of Crowded Areas (Threshold T = 0.70)
- Task 4: Algorithm 2 — Crowd-Prevention Plan Generation (Covering, Capacity, Safety)
"""

import sys
import unittest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Allow tests to run even when PyJWT is not installed in the execution environment
if "jwt" not in sys.modules:
    try:
        import jwt  # noqa: F401
    except ImportError:
        sys.modules["jwt"] = MagicMock()

from app.ai.fca_engine import FCAEngine, fca_solver, CROWD_ATTRIBUTES

class TestFCAEngineResearch(unittest.TestCase):
    def setUp(self):
        self.engine = FCAEngine()

    # =========================================================================
    # TASK 1: FUZZY FCA & MEMBERSHIP FUNCTIONS (Paper Definitions 4 & 5)
    # =========================================================================

    def test_fuzzy_crowd_context_creation(self):
        """Verify Crowd Fuzzy Context Kc = (A, F, R) generation with D, P, M, E, S attributes in [0, 1]."""
        zones = [
            {"id": "z1", "name": "Zone A — Main Gate", "density": 85.0, "current_count": 850, "capacity": 1000, "zone_type": "gate_area"},
            {"id": "z2", "name": "Zone B — Concourse", "density": 30.0, "current_count": 300, "capacity": 1000, "zone_type": "general"},
            {"id": "z3", "name": "Zone C — Backstage", "density": 10.0, "current_count": 50, "capacity": 500, "zone_type": "restricted"}
        ]
        cameras = [
            {"id": "c1", "location": "Zone A — Main Gate", "density": 85.0, "flow_rate": 3.6, "speed_avg": 0.3},
            {"id": "c2", "location": "Zone B — Concourse", "density": 30.0, "flow_rate": 0.8, "speed_avg": 1.3}
        ]
        alerts = [
            {"zone": "Zone A — Main Gate", "title": "Critical bottleneck surge", "level": "critical", "resolved": False}
        ]

        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras, alerts)

        self.assertEqual(len(objects), 3)
        self.assertIn("Zone A — Main Gate", Kc)
        self.assertIn("Zone B — Concourse", Kc)
        self.assertIn("Zone C — Backstage", Kc)

        # Check Zone A (Overcrowded gate with critical alert and slow crawl speed)
        za = Kc["Zone A — Main Gate"]
        self.assertGreaterEqual(za["D"], 0.80, "Zone A density should be >= 0.80")
        self.assertGreaterEqual(za["M"], 0.70, "Zone A movement flow should be elevated")
        self.assertEqual(za["E"], 1.0, "Zone A emergency factor should be 1.0 from critical alert")
        self.assertGreaterEqual(za["S"], 0.50, "Zone A speed stagnation anomaly should be elevated")

        # Check Zone B (Low crowd, normal walking speed)
        zb = Kc["Zone B — Concourse"]
        self.assertLess(zb["D"], 0.50, "Zone B density should be < 0.50")
        self.assertLess(zb["E"], 0.50, "Zone B emergency should be low")
        self.assertLess(zb["S"], 0.40, "Zone B speed anomaly should be low")

        # Verify all fuzzy values are bounded strictly within [0.0, 1.0]
        for obj, scores in Kc.items():
            for attr in ["D", "P", "M", "E", "S"]:
                self.assertTrue(0.0 <= scores[attr] <= 1.0, f"Attribute {attr} for {obj} must be in [0, 1]")

    def test_area_context_and_blocked_corridors(self):
        """Verify Area Formal Context Ka = (A, A, R) and exclusion of blocked physical passages."""
        zones = [
            {"id": "z1", "name": "Concourse North"},
            {"id": "z2", "name": "Central Hall"},
            {"id": "z3", "name": "South Exit"}
        ]
        connections = [
            {"from_zone_id": "z1", "to_zone_id": "z2", "bidirectional": True, "is_blocked": False},
            {"from_zone_id": "z2", "to_zone_id": "z3", "bidirectional": True, "is_blocked": True}  # Blocked exit corridor
        ]

        objects, Ka = self.engine.build_area_context(zones, connections)

        self.assertEqual(len(objects), 3)
        # Unblocked connection z1 <-> z2
        self.assertIn("Central Hall", Ka["Concourse North"])
        self.assertIn("Concourse North", Ka["Central Hall"])
        # Blocked corridor z2 <-> z3 must NOT be present in Ka relation
        self.assertNotIn("South Exit", Ka["Central Hall"], "Blocked passage must be excluded from Ka")
        self.assertNotIn("Central Hall", Ka["South Exit"], "Blocked passage must be excluded from Ka")

    def test_empty_and_boundary_contexts(self):
        """Verify graceful handling of empty contexts, single zones, and boundary zero inputs."""
        objects, Kc = self.engine.build_fuzzy_crowd_context([])
        self.assertTrue(len(objects) > 0, "Empty zones should fall back gracefully")
        for obj, scores in Kc.items():
            for v in scores.values():
                self.assertEqual(v, 0.0)

        # Single zone
        objects, Kc = self.engine.build_fuzzy_crowd_context([{"id": "z0", "name": "Solo Zone", "density": 0.0}])
        self.assertEqual(objects, ["Solo Zone"])
        self.assertEqual(Kc["Solo Zone"]["D"], 0.0)

    def test_unmatched_alert_does_not_contaminate_zone(self):
        """Test A: An unmatched critical alert references an exterior parking area,
        while the only configured zone is Concourse A. Verify that the unmatched alert
        does not increase Concourse A's emergency score."""
        zones = [{"id": "z1", "name": "Concourse A", "capacity": 1000, "density": 10.0}]
        cameras = [{"id": "c1", "location": "Concourse A", "density": 10.0}]
        alerts = [{
            "zone": "Exterior Parking Area B",
            "camera": "External Cam 4",
            "title": "Critical stampede warning",
            "level": "critical",
            "resolved": False
        }]
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras, alerts)
        self.assertEqual(objects, ["Concourse A"])
        self.assertEqual(Kc["Concourse A"]["E"], 0.0, "Unmatched critical alert must not increase Concourse A emergency score")
        self.assertEqual(Kc["Concourse A"]["P"], 0.40, "Unmatched alert must not elevate protocol risk")

    def test_unmatched_camera_does_not_contaminate_zone(self):
        """Test B: An unmatched high-density camera must not increase Concourse A's density or movement score."""
        zones = [{"id": "z1", "name": "Concourse A", "capacity": 1000, "density": 15.0}]
        cameras = [
            {"id": "c_unmatched", "location": "Highway Overpass 9", "name": "HWY-Cam", "density": 95.0, "flow_rate": 4.0, "speed_avg": 0.2}
        ]
        alerts = []
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras, alerts)
        self.assertEqual(objects, ["Concourse A"])
        self.assertEqual(Kc["Concourse A"]["D"], 0.15, "Unmatched camera must not increase Concourse A density")
        self.assertLess(Kc["Concourse A"]["M"], 0.20, "Unmatched camera flow must not contaminate Concourse A")

    def test_matched_camera_and_alert_contribute_correctly(self):
        """Test C: A correctly matched camera and a correctly matched critical alert
        must still contribute to their intended zone's membership scores."""
        zones = [
            {"id": "z1", "name": "Concourse A", "capacity": 1000, "density": 20.0},
            {"id": "z2", "name": "North Gate", "capacity": 1000, "density": 20.0}
        ]
        cameras = [
            {"id": "c1", "location": "North Gate Entry", "name": "Cam Gate", "density": 88.0, "flow_rate": 3.0, "speed_avg": 0.3}
        ]
        alerts = [
            {"zone": "North Gate Turnstiles", "camera": "Cam Gate", "title": "Critical surge", "level": "critical", "resolved": False}
        ]
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras, alerts)
        self.assertGreaterEqual(Kc["North Gate"]["D"], 0.88, "Matched camera must contribute to North Gate density")
        self.assertEqual(Kc["North Gate"]["E"], 1.0, "Matched alert must set North Gate emergency to 1.0")
        self.assertEqual(Kc["Concourse A"]["D"], 0.20)
        self.assertEqual(Kc["Concourse A"]["E"], 0.0)

    def test_unmatched_record_does_not_break_context_generation(self):
        """Test D: An unmatched record must not cause an exception or break FCA context generation
        when other valid zones exist."""
        zones = [
            {"id": "z1", "name": "Concourse A", "capacity": 1000, "density": 10.0},
            {"id": "z2", "name": "Concourse B", "capacity": 1000, "density": 20.0}
        ]
        cameras = [
            {"id": "c_valid", "location": "Concourse A", "density": 15.0},
            {"id": "c_invalid", "location": "Unknown Sector 99", "density": 90.0}
        ]
        alerts = [
            {"zone": "Completely Unknown Location", "title": "Fire alert", "level": "critical", "resolved": False}
        ]
        try:
            objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras, alerts)
        except Exception as e:
            self.fail(f"build_fuzzy_crowd_context raised an unexpected exception: {e}")

        self.assertEqual(len(objects), 2)
        self.assertIn("Concourse A", Kc)
        self.assertIn("Concourse B", Kc)
        self.assertEqual(Kc["Concourse A"]["E"], 0.0)
        self.assertEqual(Kc["Concourse B"]["E"], 0.0)

    def test_empty_zone_list_preserved_without_synthetic_operational_assignment(self):
        """Test E: Preserve the existing behavior for an empty zone list, without introducing
        synthetic operational assignments."""
        objects, Kc = self.engine.build_fuzzy_crowd_context([])
        self.assertEqual(objects, ["Area A1", "Area A2"])
        for obj in objects:
            for attr in ["D", "P", "M", "E", "S"]:
                self.assertEqual(Kc[obj][attr], 0.0)

    # =========================================================================
    # TASK 2: CONCEPT LATTICE GENERATION & GALOIS CLOSURE OPERATORS
    # =========================================================================

    def test_galois_closure_and_uniqueness(self):
        """
        Verify Galois derivation operators:
        Extent' = Intent and Intent' = Extent.
        Check that every derived concept is mathematically closed and unique.
        """
        objects = ["A1", "A2", "A3", "A4"]
        # Formal context incidence:
        # A1 has {D, M}
        # A2 has {D, M, P}
        # A3 has {P, S}
        # A4 has {D, M, P, S}
        relation = {
            "A1": {"D", "M"},
            "A2": {"D", "M", "P"},
            "A3": {"P", "S"},
            "A4": {"D", "M", "P", "S"}
        }
        all_attrs = ["D", "M", "P", "S"]

        concepts = self.engine.derive_closed_concepts(objects, relation, all_attrs)
        self.assertTrue(len(concepts) >= 4, "Should discover closed concepts")

        # Verify each concept satisfies Galois closure: Extent' = Intent and Intent' = Extent
        seen_pairs = set()
        for c in concepts:
            ext = c["extent"]
            intt = set(c["intent"])

            # Verify Extent' = Intent
            derived_intent = self.engine.galois_intent(ext, all_attrs, relation)
            self.assertEqual(derived_intent, intt, f"Galois closure failed: Extent' {derived_intent} != Intent {intt}")

            # Verify Intent' = Extent
            derived_extent = sorted(self.engine.galois_extent(intt, objects, relation))
            self.assertEqual(derived_extent, sorted(ext), f"Galois closure failed: Intent' {derived_extent} != Extent {ext}")

            # Verify uniqueness
            pair = (tuple(sorted(ext)), tuple(sorted(list(intt))))
            self.assertNotIn(pair, seen_pairs, "Duplicate formal concept generated")
            seen_pairs.add(pair)

    def test_lattice_covering_relation_and_acyclicity(self):
        """
        Verify that Hasse diagram edges represent strict immediate covering relationships
        without skipped transitive jumps or duplicate edges.
        """
        objects = ["A1", "A2", "A3"]
        relation = {
            "A1": {"D"},
            "A2": {"D", "M"},
            "A3": {"D", "M", "P"}
        }
        all_attrs = ["D", "M", "P"]

        concepts = self.engine.derive_closed_concepts(objects, relation, all_attrs)
        nodes, connections = self.engine.build_lattice_graph(concepts)

        self.assertEqual(len(nodes), len(concepts))
        
        # In a linear chain {D} -> {D, M} -> {D, M, P},
        # there should be covering edges between immediate levels,
        # but NO shortcut edge directly from {D} to {D, M, P} (transitive reduction)
        concept_by_intent_len = {len(c["intent"]): c["id"] for c in concepts}
        if 1 in concept_by_intent_len and 2 in concept_by_intent_len and 3 in concept_by_intent_len:
            id_1 = concept_by_intent_len[1]
            id_2 = concept_by_intent_len[2]
            id_3 = concept_by_intent_len[3]

            # Immediate covering edges should exist
            has_1_to_2 = any(conn["from"] == id_1 and conn["to"] == id_2 for conn in connections)
            has_2_to_3 = any(conn["from"] == id_2 and conn["to"] == id_3 for conn in connections)
            self.assertTrue(has_1_to_2, "Direct cover c1 -> c2 must exist")
            self.assertTrue(has_2_to_3, "Direct cover c2 -> c3 must exist")

            # Shortcut edge must NOT exist
            has_shortcut = any(conn["from"] == id_1 and conn["to"] == id_3 for conn in connections)
            self.assertFalse(has_shortcut, "Transitive jump c1 -> c3 must be removed by transitive reduction")

    # =========================================================================
    # TASK 3: ALGORITHM 1 — EXTRACTION OF CROWDED AREAS
    # =========================================================================

    def test_algorithm_1_crowded_areas_extraction(self):
        """
        Verify Algorithm 1 (IEEE Access 2025, p. 11):
        - Traverses Lc in decreasing size of Intent
        - Filters out low-crowd areas where c <= T (T=0.7)
        - Accurately classifies high-crowd areas
        """
        # Concept hierarchy:
        # c1: Intent={D, M, P, S}, Extent=[A1]
        # c2: Intent={D, M}, Extent=[A1, A2]
        # c3: Intent={}, Extent=[A1, A2, A3, A4] (Supremum)
        Lc = [
            {"id": "c1", "intent": ["D", "M", "P", "S"], "extent": ["A1"]},
            {"id": "c2", "intent": ["D", "M"], "extent": ["A1", "A2"]},
            {"id": "c3", "intent": [], "extent": ["A1", "A2", "A3", "A4"]}
        ]

        Kc = {
            # A1: High crowd across all criteria (c > 0.70)
            "A1": {"D": 0.95, "P": 0.85, "M": 0.90, "E": 0.90, "S": 0.80},
            # A2: Borderline density, low overall (c ~ 0.55 <= 0.70)
            "A2": {"D": 0.55, "P": 0.30, "M": 0.50, "E": 0.10, "S": 0.20},
            # A3 & A4: Clear low crowd (c < 0.30)
            "A3": {"D": 0.20, "P": 0.10, "M": 0.15, "E": 0.00, "S": 0.10},
            "A4": {"D": 0.10, "P": 0.10, "M": 0.05, "E": 0.00, "S": 0.05}
        }

        CA = self.engine.extract_crowded_areas(Lc, Kc, threshold=0.70)

        # Only A1 satisfies c > 0.70; A2, A3, A4 must be dismissed
        ca_names = [item["area"] for item in CA]
        self.assertIn("A1", ca_names, "A1 must be extracted as high-crowd area")
        self.assertNotIn("A2", ca_names, "A2 (c <= 0.70) must be dismissed as low-crowd")
        self.assertNotIn("A3", ca_names, "A3 (c <= 0.70) must be dismissed as low-crowd")
        self.assertNotIn("A4", ca_names, "A4 (c <= 0.70) must be dismissed as low-crowd")

        # Verify structured output fields
        a1_result = next(item for item in CA if item["area"] == "A1")
        self.assertGreater(a1_result["crowd_score"], 0.70)
        self.assertEqual(a1_result["concept_id"], "c1", "A1 must match concept with highest intent first")
        self.assertIn("D", a1_result["satisfied_intent"])

    # =========================================================================
    # TASK 4: ALGORITHM 2 — CROWD-PREVENTION PLAN GENERATION
    # =========================================================================

    def test_algorithm_2_plan_generation_and_safety(self):
        """
        Verify Algorithm 2 (IEEE Access 2025, p. 12):
        - Traverses La in decreasing size of Extent
        - Verifies cover(A', cpt.Intent) ensuring non-crowded destinations with capacity
        - Rejects candidate destinations that are also crowded or blocked
        - Flags status='pending_human_approval' (strict safety requirement)
        """
        # La concepts:
        # c1: Extent=[Area1, Area2, Area3], Intent=[Area4] (Area 4 connects to 1, 2, 3)
        # c2: Extent=[Area1, Area2], Intent=[Area3]
        La = [
            {"id": "c1", "extent": ["Area1", "Area2", "Area3"], "intent": ["Area4"]},
            {"id": "c2", "extent": ["Area1", "Area2"], "intent": ["Area3"]}
        ]

        # Area1 is crowded (from Algorithm 1)
        CA = [
            {"area": "Area1", "crowd_score": 0.88, "concept_id": "c_high", "satisfied_intent": ["D", "M"]}
        ]

        zone_states = {
            "Area1": {"capacity": 1000, "density": 88.0, "current_count": 880},
            "Area2": {"capacity": 800, "density": 40.0, "current_count": 320},
            "Area3": {"capacity": 600, "density": 25.0, "current_count": 150},
            "Area4": {"capacity": 1500, "density": 20.0, "current_count": 300}
        }

        # Scenario A: Unblocked route to Area 4
        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)

        self.assertEqual(result["total_crowded_areas"], 1)
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(len(result["plans"]), 1)

        plan = result["plans"][0]
        self.assertIn("Area1", plan["crowded_sources"])
        self.assertIn("Area4", plan["recommended_destinations"])
        self.assertEqual(plan["status"], "pending_human_approval", "Plans must require human operator approval")
        self.assertFalse(plan["is_verified_evacuation"], "Must be candidate prevention plan, not emergency evacuation")

        # Scenario B: Corridor to Area 4 is BLOCKED
        blocked_edges = {("Area1", "Area4"), ("Area4", "Area1")}
        result_blocked = self.engine.generate_crowd_prevention_plan(
            La, CA, zone_states=zone_states, blocked_edges=blocked_edges
        )

        # Plan should reject Area 4 and fall back to c2 (Area 3) or report limitation
        plan_blocked = result_blocked["plans"][0]
        self.assertNotIn("Area4", plan_blocked["recommended_destinations"], "Blocked corridor must be rejected")
        self.assertIn("Area3", plan_blocked["recommended_destinations"])

        # Scenario C: All destinations overcrowded (>75% density)
        overcrowded_states = {
            "Area1": {"capacity": 1000, "density": 88.0},
            "Area3": {"capacity": 600, "density": 85.0},
            "Area4": {"capacity": 1500, "density": 90.0}
        }
        result_no_route = self.engine.generate_crowd_prevention_plan(
            La, CA, zone_states=overcrowded_states
        )
        self.assertEqual(len(result_no_route["plans"]), 0, "Cannot propose destinations that are already overcrowded")
        self.assertIn("Area1", result_no_route["unresolved_areas"], "Must report unresolved area when no safe plan exists")

        # Production mode: an explicit topology is required. A candidate in a
        # concept intent is not enough to prove a physical passage exists.
        result_without_edge = self.engine.generate_crowd_prevention_plan(
            La, CA, zone_states=zone_states, allowed_edges=set()
        )
        self.assertEqual(result_without_edge["plans"], [])
        self.assertIn("Area1", result_without_edge["unresolved_areas"])

        # Unknown destination state must not be treated as zero occupancy/free capacity.
        result_missing_state = self.engine.generate_crowd_prevention_plan(
            La, CA, zone_states={"Area1": zone_states["Area1"]}, allowed_edges={("Area1", "Area4")}
        )
        self.assertEqual(result_missing_state["plans"], [])

    def test_algorithm_2_corridor_directionality_and_blocked_edges(self):
        """
        Verify Algorithm 2 corridor directionality and blocked edge safety (Task 5):
        1. One-way A -> B passage permits evacuation A -> B but forbids B -> A.
        2. Bidirectional A <-> B passage permits evacuation in either direction.
        3. Blocked passage is rejected in either direction.
        4. When allowed_edges is None, baseline behavior without physical filter is preserved.
        """
        # Concept hierarchy connecting Area1 and Area2:
        # c_a_to_b: Extent=[Area1], Intent=[Area2] (Area2 can receive crowd from Area1)
        # c_b_to_a: Extent=[Area2], Intent=[Area1] (Area1 can receive crowd from Area2)
        La = [
            {"id": "c_a_to_b", "extent": ["Area1"], "intent": ["Area2"]},
            {"id": "c_b_to_a", "extent": ["Area2"], "intent": ["Area1"]}
        ]

        zone_states = {
            "Area1": {"capacity": 1000, "density": 20.0, "current_count": 200},
            "Area2": {"capacity": 1000, "density": 20.0, "current_count": 200}
        }

        # 1. ONE-WAY CORRIDOR: Area1 -> Area2 allowed, Area2 -> Area1 disallowed
        one_way_edges = {("Area1", "Area2")}

        # 1a: Area2 is crowded; evacuation into Area1 MUST BE REJECTED (reverse of one-way)
        ca_area2 = [{"area": "Area2", "crowd_score": 0.85, "concept_id": "c_crowd"}]
        res_reverse = self.engine.generate_crowd_prevention_plan(
            La, ca_area2, zone_states=zone_states, allowed_edges=one_way_edges
        )
        self.assertEqual(res_reverse["plans"], [], "Reverse travel on one-way corridor must be rejected")
        self.assertIn("Area2", res_reverse["unresolved_areas"])

        # 1b: Area1 is crowded; evacuation into Area2 MUST BE PERMITTED (forward of one-way)
        ca_area1 = [{"area": "Area1", "crowd_score": 0.85, "concept_id": "c_crowd"}]
        res_forward = self.engine.generate_crowd_prevention_plan(
            La, ca_area1, zone_states=zone_states, allowed_edges=one_way_edges
        )
        self.assertEqual(len(res_forward["plans"]), 1, "Forward travel on one-way corridor must succeed")
        self.assertEqual(res_forward["plans"][0]["crowded_sources"], ["Area1"])
        self.assertEqual(res_forward["plans"][0]["recommended_destinations"], ["Area2"])

        # 2. BIDIRECTIONAL CORRIDOR: Area1 <-> Area2 permits evacuation in both directions
        bidirectional_edges = {("Area1", "Area2"), ("Area2", "Area1")}
        res_bi_from_1 = self.engine.generate_crowd_prevention_plan(
            La, ca_area1, zone_states=zone_states, allowed_edges=bidirectional_edges
        )
        self.assertEqual(len(res_bi_from_1["plans"]), 1, "Bidirectional passage permits Area1 -> Area2")
        self.assertEqual(res_bi_from_1["plans"][0]["recommended_destinations"], ["Area2"])

        res_bi_from_2 = self.engine.generate_crowd_prevention_plan(
            La, ca_area2, zone_states=zone_states, allowed_edges=bidirectional_edges
        )
        self.assertEqual(len(res_bi_from_2["plans"]), 1, "Bidirectional passage permits Area2 -> Area1")
        self.assertEqual(res_bi_from_2["plans"][0]["recommended_destinations"], ["Area1"])

        # 3. BLOCKED PASSAGE: Blocked passage rejected in either direction
        blocked_1_to_2 = {("Area1", "Area2")}
        res_blocked_fwd = self.engine.generate_crowd_prevention_plan(
            La, ca_area1, zone_states=zone_states, blocked_edges=blocked_1_to_2, allowed_edges=bidirectional_edges
        )
        self.assertEqual(res_blocked_fwd["plans"], [], "Blocked passage must be rejected in forward direction")
        self.assertIn("Area1", res_blocked_fwd["unresolved_areas"])

        blocked_2_to_1 = {("Area2", "Area1")}
        res_blocked_rev = self.engine.generate_crowd_prevention_plan(
            La, ca_area1, zone_states=zone_states, blocked_edges=blocked_2_to_1, allowed_edges=bidirectional_edges
        )
        self.assertEqual(res_blocked_rev["plans"], [], "Blocked passage must be rejected even if reverse edge blocked")
        self.assertIn("Area1", res_blocked_rev["unresolved_areas"])

        # 4. PRESERVE BASELINE WHEN allowed_edges IS NONE
        res_none_edges = self.engine.generate_crowd_prevention_plan(
            La, ca_area1, zone_states=zone_states, allowed_edges=None
        )
        self.assertEqual(len(res_none_edges["plans"]), 1, "When allowed_edges is None, baseline concept connectivity is preserved")
        self.assertEqual(res_none_edges["plans"][0]["recommended_destinations"], ["Area2"])


class TestRealMovementTelemetryIntegration(unittest.TestCase):
    """
    Focused Regression & Validation Tests for Task 3:
    Connecting Real Movement Telemetry to FCA Engine (IEEE Access 2025).
    """
    def setUp(self):
        self.engine = FCAEngine()

    def test_flow_values_produce_expected_movement_membership_scores(self):
        """1. Different valid flow values produce the expected different movement membership scores."""
        zones = [
            {"id": "z1", "name": "Zone A — High Flow", "density": 50.0},
            {"id": "z2", "name": "Zone B — Low Flow", "density": 50.0}
        ]
        cameras = [
            {"id": "c1", "location": "Zone A — High Flow", "density": 50.0, "flow_rate": 2.0},
            {"id": "c2", "location": "Zone B — Low Flow", "density": 50.0, "flow_rate": 0.4}
        ]
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras)
        self.assertAlmostEqual(Kc["Zone A — High Flow"]["M"], 0.50, places=2)
        self.assertAlmostEqual(Kc["Zone B — Low Flow"]["M"], 0.10, places=2)
        self.assertGreater(Kc["Zone A — High Flow"]["M"], Kc["Zone B — Low Flow"]["M"])

    def test_speed_values_produce_expected_speed_anomaly_scores(self):
        """2. Normal walking speed and low-speed stagnation produce the expected different speed-anomaly scores."""
        zones = [
            {"id": "z1", "name": "Zone A — Crush Stagnation", "density": 80.0},
            {"id": "z2", "name": "Zone B — Normal Flow", "density": 80.0}
        ]
        cameras = [
            {"id": "c1", "location": "Zone A — Crush Stagnation", "density": 80.0, "speed_avg": 0.1},
            {"id": "c2", "location": "Zone B — Normal Flow", "density": 80.0, "speed_avg": 1.3}
        ]
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras)
        # Low speed (0.1 m/s) stagnation: 1.0 - (0.1 / 0.4) * 0.5 = 0.875
        self.assertAlmostEqual(Kc["Zone A — Crush Stagnation"]["S"], 0.875, places=3)
        # Normal speed (1.3 m/s): nominal low anomaly score 0.15
        self.assertAlmostEqual(Kc["Zone B — Normal Flow"]["S"], 0.15, places=2)
        self.assertGreaterEqual(Kc["Zone A — Crush Stagnation"]["S"], 0.50)
        self.assertLess(Kc["Zone B — Normal Flow"]["S"], 0.50)

    def test_missing_telemetry_does_not_masquerade_as_measured_movement(self):
        """3. Missing telemetry does not masquerade as measured movement or speed anomaly."""
        zones = [
            {"id": "z1", "name": "Zone A — Dense Without Sensors", "density": 90.0}
        ]
        cameras = [
            {"id": "c1", "location": "Zone A — Dense Without Sensors", "density": 90.0}
            # No flow_rate, no speed_avg
        ]
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras)
        # High density (0.90) must NOT artificially trigger verified M or S attributes
        self.assertLess(Kc["Zone A — Dense Without Sensors"]["M"], 0.50, "Unmeasured movement must be capped below alpha = 0.50")
        self.assertLess(Kc["Zone A — Dense Without Sensors"]["S"], 0.50, "Unmeasured speed must be capped below alpha = 0.50")

        # Thresholding at alpha = 0.50 for concept derivation
        binary_rel = {
            obj: set(attr for attr, score in scores.items() if score >= 0.50)
            for obj, scores in Kc.items()
        }
        self.assertNotIn("M", binary_rel["Zone A — Dense Without Sensors"], "Missing flow telemetry must never be classified as verified movement")
        self.assertNotIn("S", binary_rel["Zone A — Dense Without Sensors"], "Missing speed telemetry must never be classified as verified speed anomaly")

    def test_stale_telemetry_is_not_treated_as_current(self):
        """4. Stale telemetry is rejected by freshness limits (<= 15s for worker, <= 60s for DB)."""
        from app.routers.recommendations import fetch_camera_movement_telemetry
        from app.ai.stream_processor import stream_manager

        # Case A: Live worker with stale observation timestamp (> 15s)
        mock_worker = MagicMock()
        mock_worker.event_id = "evt-test-freshness"
        mock_worker.is_running = True
        mock_worker.is_paused = False
        mock_worker.playback_status = "playing"
        mock_worker.last_observation_timestamp = time.time() - 30.0  # 30 seconds ago (stale)
        mock_worker.last_flow_rate = 3.5
        mock_worker.last_speed_avg = 0.2

        stream_manager.workers["cam-stale-worker"] = mock_worker
        try:
            telemetry = fetch_camera_movement_telemetry("cam-stale-worker", target_event_id="evt-test-freshness", db=None)
            self.assertIsNone(telemetry, "Stale worker telemetry (> 15s) must be rejected")
        finally:
            stream_manager.workers.pop("cam-stale-worker", None)

        # Case B: Persisted DB record older than 60s
        mock_db = MagicMock()
        stale_record = MagicMock()
        stale_record.camera_id = "cam-stale-db"
        stale_record.event_id = "evt-test-freshness"
        stale_record.timestamp = datetime.utcnow() - timedelta(seconds=120)  # 2 minutes ago (stale)
        stale_record.flow_rate = 3.0
        stale_record.speed_avg = 0.3

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = stale_record
        mock_db.query.return_value = mock_query

        telemetry = fetch_camera_movement_telemetry("cam-stale-db", target_event_id="evt-test-freshness", db=mock_db)
        self.assertIsNone(telemetry, "Stale database record (> 60s) must be rejected")

        # Case C: Fresh DB record within 60s
        fresh_record = MagicMock()
        fresh_record.camera_id = "cam-fresh-db"
        fresh_record.event_id = "evt-test-freshness"
        fresh_record.timestamp = datetime.utcnow() - timedelta(seconds=10)  # 10s ago (fresh)
        fresh_record.flow_rate = 1.6
        fresh_record.speed_avg = 1.2
        mock_query.first.return_value = fresh_record

        telemetry = fetch_camera_movement_telemetry("cam-fresh-db", target_event_id="evt-test-freshness", db=mock_db)
        self.assertIsNotNone(telemetry, "Fresh database record (<= 60s) must be accepted")
        self.assertEqual(telemetry["flow_rate"], 1.6)
        self.assertEqual(telemetry["speed_avg"], 1.2)
        self.assertEqual(telemetry["source"], "database")

    def test_unmatched_camera_cannot_contaminate_another_zone(self):
        """5. An unmatched camera cannot contaminate another zone."""
        zones = [
            {"id": "z1", "name": "Concourse A", "density": 20.0},
            {"id": "z2", "name": "Concourse B", "density": 20.0}
        ]
        cameras = [
            {
                "id": "c_unmatched",
                "location": "Unrelated Parking Outer Perimeter",
                "density": 95.0,
                "flow_rate": 3.8,
                "speed_avg": 0.1
            }
        ]
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras)
        self.assertEqual(objects, ["Concourse A", "Concourse B"])
        # Neither Concourse A nor Concourse B should receive the unmatched camera's movement or speed
        self.assertLess(Kc["Concourse A"]["M"], 0.20)
        self.assertLess(Kc["Concourse B"]["M"], 0.20)
        self.assertEqual(Kc["Concourse A"]["S"], 0.15)
        self.assertEqual(Kc["Concourse B"]["S"], 0.15)

    def test_cross_event_telemetry_isolation(self):
        """6. Telemetry from another event cannot affect the selected event's FCA context."""
        from app.routers.recommendations import fetch_camera_movement_telemetry

        # Mock DB where record belongs to Event B
        mock_db = MagicMock()
        event_b_record = MagicMock()
        event_b_record.camera_id = "cam-evt-b"
        event_b_record.event_id = "evt-foreign-B"
        event_b_record.timestamp = datetime.utcnow()
        event_b_record.flow_rate = 3.6
        event_b_record.speed_avg = 0.2

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = event_b_record
        mock_db.query.return_value = mock_query

        # Querying with target_event_id="evt-target-A" when record has "evt-foreign-B"
        telemetry = fetch_camera_movement_telemetry("cam-evt-b", target_event_id="evt-target-A", db=mock_db)
        self.assertIsNone(telemetry, "Cross-event telemetry must be rejected under event isolation")

    def test_empty_location_camera_does_not_contaminate_first_zone(self):
        """Task 3.1 Test 1: An empty-location camera with high flow does not contaminate the first zone."""
        zones = [
            {"id": "z1", "name": "Concourse A", "density": 20.0},
            {"id": "z2", "name": "Concourse B", "density": 20.0}
        ]
        cameras = [
            {"id": "c_empty", "location": "", "name": "", "zone_id": None, "flow_rate": 4.0, "speed_avg": 0.1}
        ]
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras)
        self.assertEqual(objects, ["Concourse A", "Concourse B"])
        # Concourse A must remain completely uncontaminated
        self.assertLess(Kc["Concourse A"]["M"], 0.20, "Empty-location camera must not contaminate Concourse A movement")
        self.assertEqual(Kc["Concourse A"]["S"], 0.15, "Empty-location camera must not contaminate Concourse A speed")
        self.assertEqual(Kc["Concourse A"]["D"], 0.20, "Empty-location camera must not contaminate Concourse A density")
        # Concourse B must also remain uncontaminated
        self.assertLess(Kc["Concourse B"]["M"], 0.20)
        self.assertEqual(Kc["Concourse B"]["S"], 0.15)

    def test_whitespace_location_camera_does_not_contaminate_any_zone(self):
        """Task 3.1 Test 2: A whitespace-only location camera does not contaminate any zone."""
        zones = [
            {"id": "z1", "name": "Concourse A", "density": 20.0},
            {"id": "z2", "name": "Concourse B", "density": 20.0}
        ]
        cameras = [
            {"id": "c_ws", "location": "   \t\n  ", "name": "  ", "zone_id": "   ", "flow_rate": 4.0, "speed_avg": 0.1}
        ]
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras)
        self.assertEqual(objects, ["Concourse A", "Concourse B"])
        self.assertLess(Kc["Concourse A"]["M"], 0.20)
        self.assertEqual(Kc["Concourse A"]["S"], 0.15)
        self.assertLess(Kc["Concourse B"]["M"], 0.20)
        self.assertEqual(Kc["Concourse B"]["S"], 0.15)

    def test_camera_with_valid_zone_id_matches_when_id_differs_from_display_name(self):
        """Task 3.1 Test 3: A camera with valid zone_id matches corresponding zone when zone ID differs from display name."""
        zones = [
            {"id": "uuid-zone-987", "name": "North Gate Turnstiles", "density": 30.0},
            {"id": "uuid-zone-654", "name": "South Concourse Plaza", "density": 30.0}
        ]
        cameras = [
            {
                "id": "c1",
                "zone_id": "uuid-zone-987",
                "location": "Ticketing Checkpoint B",
                "name": "CAM-TICKETS",
                "density": 85.0,
                "flow_rate": 2.4,
                "speed_avg": 0.2
            }
        ]
        objects, Kc = self.engine.build_fuzzy_crowd_context(zones, cameras)
        self.assertEqual(objects, ["North Gate Turnstiles", "South Concourse Plaza"])
        # North Gate Turnstiles should receive c1's telemetry via zone_id match
        self.assertEqual(Kc["North Gate Turnstiles"]["D"], 0.85, "Camera must match North Gate by zone_id")
        self.assertAlmostEqual(Kc["North Gate Turnstiles"]["M"], 0.60, places=2)  # 2.4 / 4.0 = 0.60
        self.assertGreaterEqual(Kc["North Gate Turnstiles"]["S"], 0.50)  # low speed stagnation (0.2 m/s)
        # South Concourse Plaza must remain uncontaminated
        self.assertEqual(Kc["South Concourse Plaza"]["D"], 0.30)
        self.assertLess(Kc["South Concourse Plaza"]["M"], 0.20)
        self.assertEqual(Kc["South Concourse Plaza"]["S"], 0.15)


class TestAlgorithm2CumulativeCapacityChecks(unittest.TestCase):
    """
    Focused Verification Tests for Task 7:
    Cumulative Destination Capacity Safeguards in Algorithm 2 (IEEE Access 2025).
    """
    def setUp(self):
        self.engine = FCAEngine()

    def test_two_sources_cannot_both_allocate_to_insufficient_destination(self):
        """
        1. Two sources explicitly requiring 400 people each cannot both allocate to
           a destination with capacity 500 and current occupancy 200.
        """
        La = [
            {"id": "c1", "extent": ["Area1"], "intent": ["DestA"]},
            {"id": "c2", "extent": ["Area2"], "intent": ["DestA"]}
        ]
        CA = [
            {"area": "Area1", "crowd_score": 0.85, "diversion_volume": 400},
            {"area": "Area2", "crowd_score": 0.85, "diversion_volume": 400}
        ]
        zone_states = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 400},
            "Area2": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 400},
            "DestA": {"capacity": 500, "density": 40.0, "current_count": 200}
        }

        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)

        # DestA has cap 500 and curr 200. 200 + 400 = 600 > 500.
        # Neither Area1 nor Area2 can be allocated to DestA.
        allocated_dests = [d for p in result["plans"] for d in p["recommended_destinations"]]
        self.assertNotIn("DestA", allocated_dests, "Destination cannot accept diversion that exceeds physical capacity")
        self.assertLess(allocated_dests.count("DestA"), 2, "Two 400-person sources cannot both allocate to capacity 500, curr 200")
        self.assertEqual(result["resolved_count"], 0)
        self.assertIn("Area1", result["unresolved_areas"])
        self.assertIn("Area2", result["unresolved_areas"])

        # Also test with larger destination where one source fits (capacity 900, curr 200)
        # Area1 (400) + 200 = 600 <= 900 (66.7% < 75%). Fits.
        # Area2 (400) + 600 = 1000 > 900 (111% >= 75%). Second source CANNOT also allocate to DestA!
        zone_states_900 = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 400},
            "Area2": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 400},
            "DestA": {"capacity": 900, "density": 22.2, "current_count": 200}
        }
        res_900 = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states_900)
        allocated_900 = [d for p in res_900["plans"] for d in p["recommended_destinations"]]
        self.assertEqual(allocated_900.count("DestA"), 1, "Only one 400-person source can allocate; DestA cannot accept both")
        self.assertEqual(res_900["resolved_count"], 1)
        self.assertIn("Area2", res_900["unresolved_areas"])

    def test_second_source_uses_alternative_destination_when_safe(self):
        """
        2. A second source can use an alternative destination only when its
           projected occupancy remains below 75% and within physical capacity.
        """
        # Area1 connects to DestA.
        # Area2 connects to DestA and DestB.
        La = [
            {"id": "c1", "extent": ["Area1"], "intent": ["DestA"]},
            {"id": "c2_primary", "extent": ["Area2"], "intent": ["DestA"]},
            {"id": "c2_alt", "extent": ["Area2"], "intent": ["DestB"]}
        ]
        CA = [
            {"area": "Area1", "crowd_score": 0.85, "diversion_volume": 300},
            {"area": "Area2", "crowd_score": 0.85, "diversion_volume": 300}
        ]
        # DestA has capacity 600, curr 100.
        # Plan 1 for Area1: 100 + 300 = 400 <= 600 (400/600 = 66.7% < 75%). DestA is safe for Area1.
        # For Area2 on DestA: 400 + 300 = 700 > 600 (exceeds capacity and density >= 75%). DestA rejected.
        # For Area2 on DestB (cap 800, curr 100): 100 + 300 = 400 <= 800 (50.0% < 75%). DestB accepted!
        zone_states = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 300},
            "Area2": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 300},
            "DestA": {"capacity": 600, "density": 16.7, "current_count": 100},
            "DestB": {"capacity": 800, "density": 12.5, "current_count": 100}
        }

        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)

        self.assertEqual(len(result["plans"]), 2)
        self.assertEqual(result["resolved_count"], 2)
        self.assertEqual(result["unresolved_areas"], [])

        plan1 = result["plans"][0]
        self.assertEqual(plan1["crowded_sources"], ["Area1"])
        self.assertEqual(plan1["recommended_destinations"], ["DestA"])
        self.assertTrue(plan1["is_capacity_verified"])

        plan2 = result["plans"][1]
        self.assertEqual(plan2["crowded_sources"], ["Area2"])
        self.assertEqual(plan2["recommended_destinations"], ["DestB"])
        self.assertTrue(plan2["is_capacity_verified"])

        # Also verify that if DestB projected density were >= 75%, DestB would be REJECTED
        # DestB cap 450, curr 100. 100 + 300 = 400 / 450 = 88.9% >= 75.0%
        zone_states_tight = dict(zone_states)
        zone_states_tight["DestB"] = {"capacity": 450, "density": 22.2, "current_count": 100}
        res_tight = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states_tight)
        self.assertEqual(res_tight["resolved_count"], 1)
        self.assertIn("Area2", res_tight["unresolved_areas"], "Alternative destination must be rejected when projected density >= 75%")

    def test_affected_source_unresolved_when_no_safe_destination_exists(self):
        """
        3. When no safe destination exists, affected source areas remain unresolved.
        """
        La = [
            {"id": "c1", "extent": ["Area1"], "intent": ["DestA"]},
            {"id": "c2", "extent": ["Area2"], "intent": ["DestA", "DestB"]}
        ]
        CA = [
            {"area": "Area1", "crowd_score": 0.85, "diversion_volume": 300},
            {"area": "Area2", "crowd_score": 0.85, "diversion_volume": 300}
        ]
        # DestA has cap 600, curr 100 -> takes Area1 (new curr 400).
        # DestB is already at 80% density (cap 1000, curr 800, density 80.0%).
        zone_states = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 300},
            "Area2": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 300},
            "DestA": {"capacity": 600, "density": 16.7, "current_count": 100},
            "DestB": {"capacity": 1000, "density": 80.0, "current_count": 800}
        }

        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)

        self.assertEqual(result["resolved_count"], 1)
        self.assertIn("Area2", result["unresolved_areas"])
        self.assertEqual(result["status"], "partial")

    def test_valid_single_plan_retains_existing_behavior(self):
        """
        4. A valid single-plan scenario retains its existing behavior.
        """
        La = [
            {"id": "c1", "extent": ["Area1", "Area2", "Area3"], "intent": ["Area4"]}
        ]
        CA = [
            {"area": "Area1", "crowd_score": 0.88, "concept_id": "c_high"}
        ]
        zone_states = {
            "Area1": {"capacity": 1000, "density": 88.0, "current_count": 880},
            "Area2": {"capacity": 800, "density": 40.0, "current_count": 320},
            "Area3": {"capacity": 600, "density": 25.0, "current_count": 150},
            "Area4": {"capacity": 1500, "density": 20.0, "current_count": 300}
        }

        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)

        self.assertEqual(result["total_crowded_areas"], 1)
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(result["unresolved_areas"], [])
        self.assertEqual(len(result["plans"]), 1)

        plan = result["plans"][0]
        self.assertIn("Area1", plan["crowded_sources"])
        self.assertIn("Area4", plan["recommended_destinations"])
        self.assertEqual(plan["status"], "pending_human_approval")
        self.assertFalse(plan["is_verified_evacuation"])
        # Diversion volume was unmeasured, so capacity is unverified with explicit warning
        self.assertFalse(plan["is_capacity_verified"])
        self.assertIn("unmeasured", plan["warning"])

    def test_missing_or_invalid_diversion_volumes_never_claim_verified_capacity(self):
        """
        5. Missing or invalid diversion volumes never result in a quantitatively verified capacity claim.
        """
        La = [{"id": "c1", "extent": ["Area1"], "intent": ["DestA"]}]
        CA = [{"area": "Area1", "crowd_score": 0.85}]

        # 5a: Missing diversion volume
        states_missing = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850},
            "DestA": {"capacity": 1000, "density": 20.0, "current_count": 200}
        }
        res_missing = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=states_missing)
        self.assertEqual(len(res_missing["plans"]), 1)
        self.assertFalse(res_missing["plans"][0]["is_capacity_verified"], "Missing volume must not claim capacity verification")
        self.assertIsNone(res_missing["plans"][0]["diversion_volume"])
        self.assertIn("unmeasured", res_missing["plans"][0]["warning"])

        # 5b: Negative diversion volume
        states_neg = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": -150},
            "DestA": {"capacity": 1000, "density": 20.0, "current_count": 200}
        }
        res_neg = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=states_neg)
        self.assertFalse(res_neg["plans"][0]["is_capacity_verified"], "Negative volume must not claim capacity verification")

        # 5c: NaN diversion volume
        states_nan = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": float("nan")},
            "DestA": {"capacity": 1000, "density": 20.0, "current_count": 200}
        }
        res_nan = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=states_nan)
        self.assertFalse(res_nan["plans"][0]["is_capacity_verified"], "NaN volume must not claim capacity verification")

        # 5d: Non-numeric string diversion volume
        states_str = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": "unknown"},
            "DestA": {"capacity": 1000, "density": 20.0, "current_count": 200}
        }
        res_str = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=states_str)
        self.assertFalse(res_str["plans"][0]["is_capacity_verified"], "String volume must not claim capacity verification")

        # 5e: Boolean diversion volume
        states_bool = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": True},
            "DestA": {"capacity": 1000, "density": 20.0, "current_count": 200}
        }
        res_bool = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=states_bool)
        self.assertFalse(res_bool["plans"][0]["is_capacity_verified"], "Boolean volume must not claim capacity verification")

    def test_repeated_plans_account_for_prior_allocations(self):
        """
        6. Repeated plans account for prior allocations.
        """
        La1 = [{"id": "c1", "extent": ["Area1"], "intent": ["DestA"]}]
        CA1 = [{"area": "Area1", "crowd_score": 0.85, "diversion_volume": 350}]
        initial_states = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 350},
            "Area2": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 200},
            "DestA": {"capacity": 700, "density": 14.3, "current_count": 100}
        }

        # First run: Area1 diverts 350 into DestA (curr becomes 100 + 350 = 450; 450/700 = 64.3% < 75%)
        res1 = self.engine.generate_crowd_prevention_plan(La1, CA1, zone_states=initial_states)
        self.assertEqual(res1["resolved_count"], 1)
        working_states = res1["working_zone_states"]
        self.assertEqual(working_states["DestA"]["current_count"], 450)
        self.assertAlmostEqual(working_states["DestA"]["density"], (450 / 700) * 100.0, places=2)

        # Second run: Area2 attempts to divert 200 into DestA using the updated states
        # DestA has cap 700, curr 450. 450 + 200 = 650. Projected density 650/700 = 92.9% >= 75.0%
        La2 = [{"id": "c2", "extent": ["Area2"], "intent": ["DestA"]}]
        CA2 = [{"area": "Area2", "crowd_score": 0.85, "diversion_volume": 200}]
        res2 = self.engine.generate_crowd_prevention_plan(La2, CA2, zone_states=working_states)
        self.assertEqual(res2["resolved_count"], 0, "Repeated plan must reject destination that was filled by prior plan")
        self.assertIn("Area2", res2["unresolved_areas"])

    def test_input_zone_states_and_database_state_not_mutated(self):
        """
        7. Input zone_states and database-backed state are not mutated.
        """
        import copy
        input_states = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 300},
            "DestA": {"capacity": 800, "density": 25.0, "current_count": 200}
        }
        original_copy = copy.deepcopy(input_states)

        La = [{"id": "c1", "extent": ["Area1"], "intent": ["DestA"]}]
        CA = [{"area": "Area1", "crowd_score": 0.85, "diversion_volume": 300}]

        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=input_states)

        self.assertEqual(result["resolved_count"], 1)
        # Verify the caller-owned dictionary and its nested dicts were not modified
        self.assertEqual(input_states, original_copy)
        self.assertEqual(input_states["DestA"]["current_count"], 200)
        self.assertEqual(input_states["DestA"]["density"], 25.0)

    def test_existing_task_5_directed_corridor_and_blocked_edge_tests_continue_to_pass(self):
        """
        8. Existing Task 5 directed-corridor and blocked-edge tests continue to pass.
        """
        La = [
            {"id": "c_a_to_b", "extent": ["Area1"], "intent": ["Area2"]}
        ]
        ca_area1 = [{"area": "Area1", "crowd_score": 0.85, "diversion_volume": 100}]
        zone_states = {
            "Area1": {"capacity": 1000, "density": 85.0, "current_count": 850, "diversion_volume": 100},
            "Area2": {"capacity": 1000, "density": 20.0, "current_count": 200}
        }

        # Directed edge forward: permitted
        res_fwd = self.engine.generate_crowd_prevention_plan(
            La, ca_area1, zone_states=zone_states, allowed_edges={("Area1", "Area2")}
        )
        self.assertEqual(len(res_fwd["plans"]), 1)
        self.assertTrue(res_fwd["plans"][0]["is_capacity_verified"])

        # Directed edge reverse only: rejected
        res_rev = self.engine.generate_crowd_prevention_plan(
            La, ca_area1, zone_states=zone_states, allowed_edges={("Area2", "Area1")}
        )
        self.assertEqual(len(res_rev["plans"]), 0)

        # Blocked edge: rejected
        res_blocked = self.engine.generate_crowd_prevention_plan(
            La, ca_area1, zone_states=zone_states, blocked_edges={("Area1", "Area2")}, allowed_edges={("Area1", "Area2")}
        )
        self.assertEqual(len(res_blocked["plans"]), 0)


class TestRecommendationVerificationFormatting(unittest.TestCase):
    """
    Focused Verification Tests for Task 7.2:
    Fix Misleading Capacity Verification Status Formatting and Schema Exposure.
    """
    def setUp(self):
        from app.routers.recommendations import format_prevention_plan_recommendation
        from app.schemas import PreventionPlanItem, PreventionPlanResponse, RecommendationResponse
        self.format_func = format_prevention_plan_recommendation
        self.PreventionPlanItem = PreventionPlanItem
        self.PreventionPlanResponse = PreventionPlanResponse
        self.RecommendationResponse = RecommendationResponse

    def test_verified_plan_receives_verified_label_only_when_engine_marks_verified(self):
        """1. Verified plans receive the appropriate verified label only when the engine marks capacity verified."""
        plan_with_volume = {
            "plan_id": "plan-fca-1",
            "crowded_sources": ["Gate North Entry"],
            "recommended_destinations": ["Central Plaza"],
            "reason": "Algorithm 2 Verified Route: Candidate destinations ['Central Plaza'] are unblocked.",
            "warning": "Candidate prevention plan requires operational review before executing physical crowd diversion.",
            "is_capacity_verified": True,
            "diversion_volume": 350.0,
            "mitigation_capacity": 2500
        }
        rec = self.format_func(plan_with_volume, target_event_id="evt-101")
        self.assertIn("[Algorithm 2 Verified Route: Headroom Verified for 350 Persons]", rec["reason"])
        self.assertNotIn("Candidate Route: Unverified Headroom", rec["reason"])

        # Verified plan without explicit volume
        plan_without_volume = dict(plan_with_volume)
        plan_without_volume["diversion_volume"] = None
        rec_no_vol = self.format_func(plan_without_volume, target_event_id="evt-101")
        self.assertIn("[Algorithm 2 Verified Route: Capacity Headroom Verified]", rec_no_vol["reason"])

    def test_unverified_plan_never_contains_phrase_verified_route(self):
        """2. Unverified plans never receive the phrase 'Verified Route'."""
        plan_unverified = {
            "plan_id": "plan-fca-2",
            "crowded_sources": ["Gate North Entry"],
            "recommended_destinations": ["Central Plaza"],
            "reason": "Algorithm 2 Candidate Route: Candidate destinations ['Central Plaza'] are unblocked but crowd diversion volume is unmeasured.",
            "warning": "Candidate prevention plan requires operational review. Crowd diversion volume unmeasured; destination capacity headroom cannot be quantitatively verified.",
            "is_capacity_verified": False,
            "diversion_volume": None,
            "mitigation_capacity": 2500
        }
        rec = self.format_func(plan_unverified, target_event_id="evt-101")
        self.assertNotIn("Verified Route", rec["reason"], "Unverified plan must NEVER contain the phrase 'Verified Route'")
        self.assertIn("[Algorithm 2 Candidate Route: Unverified Headroom]", rec["reason"])

    def test_missing_or_none_verification_status_treated_as_unverified(self):
        """3. Missing or None verification status is treated as unverified."""
        # 3a: None verification status
        plan_none = {
            "plan_id": "plan-fca-3",
            "crowded_sources": ["Concourse A"],
            "recommended_destinations": ["Concourse B"],
            "reason": "Candidate route without verification flag.",
            "is_capacity_verified": None,
            "mitigation_capacity": 1000
        }
        rec_none = self.format_func(plan_none)
        self.assertNotIn("Verified Route", rec_none["reason"])
        self.assertIn("[Algorithm 2 Candidate Route: Unverified Headroom]", rec_none["reason"])

        # 3b: Missing key entirely (legacy plan dict)
        plan_legacy = {
            "plan_id": "plan-fca-4",
            "crowded_sources": ["Concourse A"],
            "recommended_destinations": ["Concourse B"],
            "reason": "Legacy plan without verification key.",
            "mitigation_capacity": 1000
        }
        rec_legacy = self.format_func(plan_legacy)
        self.assertNotIn("Verified Route", rec_legacy["reason"])
        self.assertIn("[Algorithm 2 Candidate Route: Unverified Headroom]", rec_legacy["reason"])

    def test_original_engine_reason_and_warning_are_preserved(self):
        """4. The original reason and warning are preserved."""
        plan = {
            "plan_id": "plan-fca-5",
            "crowded_sources": ["Zone A"],
            "recommended_destinations": ["Zone B"],
            "reason": "Algorithm 2 Candidate Route: Zone B is unblocked and non-crowded.",
            "warning": "Crowd diversion volume unmeasured; destination capacity headroom cannot be quantitatively verified.",
            "is_capacity_verified": False
        }
        rec = self.format_func(plan)
        self.assertIn("Algorithm 2 Candidate Route: Zone B is unblocked and non-crowded.", rec["reason"])
        self.assertIn("Warning: Crowd diversion volume unmeasured; destination capacity headroom cannot be quantitatively verified.", rec["reason"])
        self.assertIn("[Algorithm 2 Candidate Route: Unverified Headroom]", rec["reason"])

    def test_api_schema_exposes_verification_status_and_defaults_safely(self):
        """5. The API response exposes the correct verification status when applicable."""
        # Verified item
        item_verified = self.PreventionPlanItem(
            plan_id="p1",
            crowded_sources=["Gate 1"],
            recommended_destinations=["Plaza 1"],
            concept_id="c1",
            concept_extent=["Gate 1"],
            concept_intent=["Plaza 1"],
            reason="Verified route",
            is_capacity_verified=True,
            diversion_volume=250.0
        )
        self.assertTrue(item_verified.is_capacity_verified)
        self.assertEqual(item_verified.diversion_volume, 250.0)

        # Legacy item lacking fields: must default safely to unverified (False, None)
        item_legacy = self.PreventionPlanItem(
            plan_id="p2",
            crowded_sources=["Gate 2"],
            recommended_destinations=["Plaza 2"],
            concept_id="c2",
            concept_extent=["Gate 2"],
            concept_intent=["Plaza 2"],
            reason="Legacy route"
        )
        self.assertFalse(item_legacy.is_capacity_verified, "Legacy item must default to is_capacity_verified=False")
        self.assertIsNone(item_legacy.diversion_volume)

        # PreventionPlanResponse serialization
        resp = self.PreventionPlanResponse(
            total_crowded_areas=2,
            resolved_count=2,
            plans=[item_verified, item_legacy],
            timestamp="2026-10-23 00:00:00"
        )
        self.assertTrue(resp.plans[0].is_capacity_verified)
        self.assertFalse(resp.plans[1].is_capacity_verified)

    def test_existing_recommendation_response_contract_compatibility(self):
        """6. Existing recommendation response behavior remains compatible."""
        plan = {
            "plan_id": "plan-fca-compat",
            "crowded_sources": ["Turnstiles North"],
            "recommended_destinations": ["Concourse South"],
            "reason": "Direct corridor unblocked.",
            "is_capacity_verified": True,
            "diversion_volume": 120.0
        }
        rec_dict = self.format_func(plan, target_event_id="evt-contract-test")
        rec_model = self.RecommendationResponse(**rec_dict)
        self.assertEqual(rec_model.id, "rec-fca-evt-contract-test-plan-fca-compat")
        self.assertEqual(rec_model.status, "pending")
        self.assertEqual(rec_model.priority, "high")
        self.assertEqual(rec_model.confidence, 96)
        self.assertEqual(rec_model.zone, "Turnstiles North")
        self.assertIn("[Algorithm 2 Verified Route: Headroom Verified for 120 Persons]", rec_model.reason)


class TestAlgorithm2SinglePrimaryDestinationAllocation(unittest.TestCase):
    """
    Focused Regression Tests for Task 7.3:
    Single-Primary-Destination Allocation Safeguards in Algorithm 2.
    """
    def setUp(self):
        self.engine = FCAEngine()
        from app.routers.recommendations import format_prevention_plan_recommendation
        from app.schemas import PreventionPlanItem, PreventionPlanResponse, RecommendationResponse
        self.format_func = format_prevention_plan_recommendation
        self.PreventionPlanItem = PreventionPlanItem
        self.PreventionPlanResponse = PreventionPlanResponse
        self.RecommendationResponse = RecommendationResponse

    def test_source_with_known_diversion_volume_and_two_eligible_destinations_receives_exactly_one_primary_destination(self):
        """1. A source with a known diversion volume and two eligible destinations receives exactly one primary destination."""
        La = [
            {"id": "cpt-multi-dest", "extent": ["Source1"], "intent": ["DestA", "DestB"]}
        ]
        CA = [
            {"area": "Source1", "crowd_score": 0.85, "diversion_volume": 100.0}
        ]
        zone_states = {
            "Source1": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": 100.0},
            "DestA": {"capacity": 500, "current_count": 50, "density": 10.0},
            "DestB": {"capacity": 500, "current_count": 50, "density": 10.0}
        }

        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)

        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(len(result["plans"]), 1)
        subplan = result["plans"][0]
        # Must contain EXACTLY one primary destination
        self.assertEqual(len(subplan["recommended_destinations"]), 1)
        self.assertIn(subplan["recommended_destinations"][0], ["DestA", "DestB"])
        self.assertEqual(subplan["recommended_destinations"], ["DestA"])  # DestA wins tie-break
        # Capacity reporting must match the selected destination's capacity, not sum
        self.assertEqual(subplan["mitigation_capacity"], 500)
        self.assertTrue(subplan["is_capacity_verified"])
        self.assertEqual(subplan["diversion_volume"], 100.0)

    def test_selected_destination_has_lowest_projected_density_with_deterministic_tie_breaker(self):
        """2. The selected destination has the lowest projected density, with deterministic tie-breaking."""
        # 2a: Lowest projected density wins
        La_density = [
            {"id": "cpt-dens", "extent": ["Source1"], "intent": ["DestHigh", "DestLow"]}
        ]
        CA = [
            {"area": "Source1", "crowd_score": 0.85, "diversion_volume": 50.0}
        ]
        zone_states_density = {
            "Source1": {"capacity": 1000, "current_count": 800, "density": 80.0, "diversion_volume": 50.0},
            # DestHigh: curr 100, cap 500 -> projected (150/500)*100 = 30%
            "DestHigh": {"capacity": 500, "current_count": 100, "density": 20.0},
            # DestLow: curr 50, cap 500 -> projected (100/500)*100 = 20%
            "DestLow": {"capacity": 500, "current_count": 50, "density": 10.0}
        }
        res_density = self.engine.generate_crowd_prevention_plan(La_density, CA, zone_states=zone_states_density)
        self.assertEqual(len(res_density["plans"]), 1)
        self.assertEqual(res_density["plans"][0]["recommended_destinations"], ["DestLow"])

        # 2b: Deterministic alphabetical tie-breaking when projected densities are equal
        La_tie = [
            {"id": "cpt-tie", "extent": ["Source1"], "intent": ["DestZ", "DestA"]}
        ]
        zone_states_tie = {
            "Source1": {"capacity": 1000, "current_count": 800, "density": 80.0, "diversion_volume": 50.0},
            # Both have identical 10% density (50 / 500) and same projected density 20% (100 / 500)
            "DestZ": {"capacity": 500, "current_count": 50, "density": 10.0},
            "DestA": {"capacity": 500, "current_count": 50, "density": 10.0}
        }
        res_tie = self.engine.generate_crowd_prevention_plan(La_tie, CA, zone_states=zone_states_tie)
        self.assertEqual(len(res_tie["plans"]), 1)
        self.assertEqual(res_tie["plans"][0]["recommended_destinations"], ["DestA"], "DestA must win tie-break over DestZ")

        # 2c: Direct helper verification
        selected = fca_solver._select_primary_destination(["DestZ", "DestA"], zone_states_tie, required_volume=50.0, has_reliable_volume=True)
        self.assertEqual(selected, "DestA")

    def test_full_diversion_volume_added_to_only_selected_destination(self):
        """3. The full diversion volume is added to only the selected destination."""
        La = [
            {"id": "cpt-vol", "extent": ["Source1"], "intent": ["DestA", "DestB"]}
        ]
        CA = [
            {"area": "Source1", "crowd_score": 0.85, "diversion_volume": 120.0}
        ]
        zone_states = {
            "Source1": {"capacity": 1000, "current_count": 800, "density": 80.0, "diversion_volume": 120.0},
            "DestA": {"capacity": 1000, "current_count": 100, "density": 10.0},
            "DestB": {"capacity": 1000, "current_count": 200, "density": 20.0}
        }
        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)
        self.assertEqual(len(result["plans"]), 1)
        self.assertEqual(result["plans"][0]["recommended_destinations"], ["DestA"])

        working = result["working_zone_states"]
        # DestA received the full 120 persons: 100 + 120 = 220
        self.assertEqual(working["DestA"]["current_count"], 220.0)
        self.assertEqual(working["DestA"]["density"], 22.0)
        # DestB was NOT allocated and remains at initial state
        self.assertEqual(working["DestB"]["current_count"], 200.0)
        self.assertEqual(working["DestB"]["density"], 20.0)

    def test_later_source_can_use_alternative_destination_when_safe(self):
        """4. A later source can use an alternative destination when it is safe."""
        # Concept 1 covers Source1 -> intent [DestA, DestB]
        # Concept 2 covers Source2 -> intent [DestA, DestB]
        La = [
            {"id": "cpt-src1", "extent": ["Source1"], "intent": ["DestA", "DestB"]},
            {"id": "cpt-src2", "extent": ["Source2"], "intent": ["DestA", "DestB"]}
        ]
        CA = [
            {"area": "Source1", "crowd_score": 0.90, "diversion_volume": 150.0},
            {"area": "Source2", "crowd_score": 0.85, "diversion_volume": 150.0}
        ]
        zone_states = {
            "Source1": {"capacity": 1000, "current_count": 900, "density": 90.0, "diversion_volume": 150.0},
            "Source2": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": 150.0},
            # DestA has cap 300, curr 60 (20%). With vol=150: 210/300 = 70.0% < 75%. Safe for one source!
            "DestA": {"capacity": 300, "current_count": 60, "density": 20.0},
            # DestB has cap 500, curr 100 (20%). With vol=150: 250/500 = 50.0% < 75%. Safe for one source!
            "DestB": {"capacity": 500, "current_count": 100, "density": 20.0}
        }
        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)

        self.assertEqual(result["resolved_count"], 2)
        self.assertEqual(result["unresolved_areas"], [])
        self.assertEqual(len(result["plans"]), 2)

        plan_dests = [p["recommended_destinations"][0] for p in result["plans"]]
        self.assertEqual(set(plan_dests), {"DestA", "DestB"})
        self.assertEqual(result["plans"][0]["recommended_destinations"], ["DestB"])
        self.assertEqual(result["plans"][1]["recommended_destinations"], ["DestA"])

    def test_destination_reaching_or_exceeding_75_percent_is_rejected(self):
        """5. A destination that would reach or exceed 75% projected density is rejected."""
        # 5a: Exactly 75.0% projected density is strictly rejected
        La = [
            {"id": "cpt-75", "extent": ["Source1"], "intent": ["Dest75"]}
        ]
        CA = [
            {"area": "Source1", "crowd_score": 0.85, "diversion_volume": 50.0}
        ]
        # cap 200, curr 100 -> projected: (100 + 50) / 200 = 150/200 = 75.0% (must be rejected)
        zone_states_exact = {
            "Source1": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": 50.0},
            "Dest75": {"capacity": 200, "current_count": 100, "density": 50.0}
        }
        res_exact = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states_exact)
        self.assertEqual(res_exact["resolved_count"], 0)
        self.assertEqual(res_exact["unresolved_areas"], ["Source1"])
        self.assertEqual(len(res_exact["plans"]), 0)

        # 5b: Over 75% projected density (e.g. 80%) is rejected
        zone_states_over = {
            "Source1": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": 60.0},
            "Dest75": {"capacity": 200, "current_count": 100, "density": 50.0}
        }
        res_over = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states_over)
        self.assertEqual(res_over["resolved_count"], 0)
        self.assertEqual(res_over["unresolved_areas"], ["Source1"])
        self.assertEqual(len(res_over["plans"]), 0)

    def test_destination_exceeding_physical_capacity_is_rejected(self):
        """6. A destination that would exceed physical capacity is rejected."""
        La = [
            {"id": "cpt-cap", "extent": ["Source1"], "intent": ["DestSmall"]}
        ]
        CA = [
            {"area": "Source1", "crowd_score": 0.85, "diversion_volume": 300.0}
        ]
        # cap 250, curr 10 -> projected: 10 + 300 = 310 > 250 (exceeds physical capacity)
        zone_states = {
            "Source1": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": 300.0},
            "DestSmall": {"capacity": 250, "current_count": 10, "density": 4.0}
        }
        res = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)
        self.assertEqual(res["resolved_count"], 0)
        self.assertEqual(res["unresolved_areas"], ["Source1"])
        self.assertEqual(len(res["plans"]), 0)

    def test_unresolved_when_no_single_destination_is_safe(self):
        """7. If no single destination is safe, the source remains unresolved."""
        # Concept has 2 candidate destinations, but NEITHER can hold the full 200 persons.
        # We must NOT split the crowd across them!
        La = [
            {"id": "cpt-split-risk", "extent": ["Source1"], "intent": ["Dest1", "Dest2"]}
        ]
        CA = [
            {"area": "Source1", "crowd_score": 0.85, "diversion_volume": 200.0}
        ]
        zone_states = {
            "Source1": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": 200.0},
            # Dest1 cap 150: exceeds cap (200 > 150)
            "Dest1": {"capacity": 150, "current_count": 0, "density": 0.0},
            # Dest2 cap 220: curr 100 -> projected (300/220) > 100% (exceeds cap and density)
            "Dest2": {"capacity": 220, "current_count": 100, "density": 45.45}
        }
        res = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)
        self.assertEqual(res["resolved_count"], 0)
        self.assertEqual(res["unresolved_areas"], ["Source1"])
        self.assertEqual(len(res["plans"]), 0, "Must not create a plan when no single destination can safely accommodate the full crowd")

    def test_missing_or_invalid_diversion_volume_never_produces_capacity_verified_claim(self):
        """8. Missing or invalid diversion volume never produces a capacity-verified claim."""
        import math
        invalid_values = [None, -50.0, float("nan"), float("inf"), True, False, "unknown"]

        for val in invalid_values:
            La = [{"id": "cpt-invalid", "extent": ["Source1"], "intent": ["DestA"]}]
            CA = [{"area": "Source1", "crowd_score": 0.85, "diversion_volume": val}]
            zone_states = {
                "Source1": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": val},
                "DestA": {"capacity": 500, "current_count": 50, "density": 10.0}
            }
            res = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)
            self.assertEqual(len(res["plans"]), 1, f"Failed for invalid volume: {val}")
            plan = res["plans"][0]
            self.assertFalse(plan["is_capacity_verified"], f"is_capacity_verified must be False for invalid volume: {val}")
            self.assertIsNone(plan["diversion_volume"], f"diversion_volume must be None for invalid volume: {val}")
            self.assertNotIn("Verified Route", plan["reason"], f"Must not claim Verified Route for invalid volume: {val}")
            self.assertIn("unmeasured", plan["reason"].lower(), f"Must state unmeasured for invalid volume: {val}")
            # Working states current_count must NOT have been incremented
            self.assertEqual(res["working_zone_states"]["DestA"]["current_count"], 50.0)

    def test_caller_owned_zone_states_remains_unchanged(self):
        """9. Caller-owned zone_states remains unchanged."""
        import copy
        zone_states = {
            "Source1": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": 100.0},
            "DestA": {"capacity": 500, "current_count": 50, "density": 10.0},
            "DestB": {"capacity": 500, "current_count": 50, "density": 10.0}
        }
        original_states = copy.deepcopy(zone_states)

        La = [{"id": "cpt-copy", "extent": ["Source1"], "intent": ["DestA", "DestB"]}]
        CA = [{"area": "Source1", "crowd_score": 0.85, "diversion_volume": 100.0}]

        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(zone_states, original_states, "Caller-owned zone_states must not be mutated")
        self.assertEqual(zone_states["DestA"]["current_count"], 50)
        self.assertEqual(zone_states["DestB"]["current_count"], 50)

    def test_existing_single_plan_behavior_remains_valid(self):
        """10. Existing single-plan behavior remains valid where assumptions are satisfied."""
        La = [{"id": "cpt-single", "extent": ["Source1"], "intent": ["DestA"]}]
        CA = [{"area": "Source1", "crowd_score": 0.85, "diversion_volume": 80.0}]
        zone_states = {
            "Source1": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": 80.0},
            "DestA": {"capacity": 600, "current_count": 100, "density": 16.67}
        }
        result = self.engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(len(result["plans"]), 1)
        plan = result["plans"][0]
        self.assertEqual(plan["recommended_destinations"], ["DestA"])
        self.assertEqual(plan["status"], "pending_human_approval")
        self.assertTrue(plan["is_capacity_verified"])
        self.assertEqual(plan["diversion_volume"], 80.0)
        self.assertEqual(plan["mitigation_capacity"], 600)
        self.assertFalse(plan["is_verified_evacuation"])

    def test_task_5_directed_corridor_and_blocked_edges_remain_passing(self):
        """11. Task 5 directed-corridor and blocked-edge tests remain passing."""
        La = [{"id": "cpt-edge", "extent": ["Source1"], "intent": ["DestA"]}]
        CA = [{"area": "Source1", "crowd_score": 0.85, "diversion_volume": 50.0}]
        zone_states = {
            "Source1": {"capacity": 1000, "current_count": 850, "density": 85.0, "diversion_volume": 50.0},
            "DestA": {"capacity": 500, "current_count": 50, "density": 10.0}
        }
        # 11a: Blocked edge rejects route
        res_blocked = self.engine.generate_crowd_prevention_plan(
            La, CA, zone_states=zone_states, blocked_edges={("Source1", "DestA")}
        )
        self.assertEqual(len(res_blocked["plans"]), 0)
        self.assertEqual(res_blocked["unresolved_areas"], ["Source1"])

        # 11b: One-way reverse edge rejects forward route
        res_rev = self.engine.generate_crowd_prevention_plan(
            La, CA, zone_states=zone_states, allowed_edges={("DestA", "Source1")}
        )
        self.assertEqual(len(res_rev["plans"]), 0)

        # 11c: Allowed forward edge succeeds
        res_fwd = self.engine.generate_crowd_prevention_plan(
            La, CA, zone_states=zone_states, allowed_edges={("Source1", "DestA")}
        )
        self.assertEqual(len(res_fwd["plans"]), 1)
        self.assertEqual(res_fwd["plans"][0]["recommended_destinations"], ["DestA"])

    def test_task_7_2_verification_label_and_api_schema_remain_passing(self):
        """12. Task 7.2 verification-label and API-schema tests remain passing."""
        # Format single primary destination plan
        plan_verified = {
            "plan_id": "plan-fca-t73-1",
            "crowded_sources": ["Gate 1"],
            "recommended_destinations": ["Plaza North"],
            "reason": "Algorithm 2 Verified Route: Primary destination Plaza North is unblocked.",
            "warning": "Candidate prevention plan requires operational review before executing physical crowd diversion.",
            "is_capacity_verified": True,
            "diversion_volume": 150.0,
            "mitigation_capacity": 800
        }
        rec_ver = self.format_func(plan_verified, target_event_id="evt-t73")
        self.assertIn("[Algorithm 2 Verified Route: Headroom Verified for 150 Persons]", rec_ver["reason"])
        self.assertIn("Plaza North", rec_ver["title"])

        plan_unver = {
            "plan_id": "plan-fca-t73-2",
            "crowded_sources": ["Gate 1"],
            "recommended_destinations": ["Plaza North"],
            "reason": "Algorithm 2 Candidate Route: Primary destination Plaza North is unblocked but crowd diversion volume is unmeasured.",
            "warning": "Candidate prevention plan requires operational review. Crowd diversion volume unmeasured; destination capacity headroom cannot be quantitatively verified.",
            "is_capacity_verified": False,
            "diversion_volume": None,
            "mitigation_capacity": 800
        }
        rec_unver = self.format_func(plan_unver, target_event_id="evt-t73")
        self.assertIn("[Algorithm 2 Candidate Route: Unverified Headroom]", rec_unver["reason"])
        self.assertNotIn("Verified Route", rec_unver["reason"])

        # Pydantic schema validation
        item = self.PreventionPlanItem(
            plan_id="p-t73",
            crowded_sources=["Gate 1"],
            recommended_destinations=["Plaza North"],
            concept_id="c-t73",
            concept_extent=["Gate 1"],
            concept_intent=["Plaza North"],
            reason="Verified single primary destination",
            is_capacity_verified=True,
            diversion_volume=150.0
        )
        self.assertEqual(len(item.recommended_destinations), 1)
        self.assertEqual(item.recommended_destinations[0], "Plaza North")
        self.assertTrue(item.is_capacity_verified)


class TestTask75PersistentCapacityReservationAndLifecycle(unittest.TestCase):
    """
    Focused Regression Tests for Task 7.5:
    Persistent Capacity Reservations, Concurrency Protection, and Officer-Controlled Lifecycle.
    """
    def setUp(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        from pydantic import ValidationError
        from app.database import Base
        from app.models import User, EventModel, ZoneModel, RecommendationModel, CapacityReservationModel
        from app.auth_utils import create_access_token
        from app.routers.recommendations import (
            approve_recommendation,
            start_diversion,
            complete_diversion,
            cancel_diversion,
            reconcile_cancelled_diversion,
            reject_recommendation,
            dismiss_recommendation,
            get_active_reservations,
        )

        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.test_engine)
        self.TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        self.db = self.TestSessionLocal()

        class MockResponse:
            def __init__(self, status_code, data=None):
                self.status_code = status_code
                self._data = data if data is not None else {}
            def json(self):
                return self._data

        class DirectRouterClient:
            def __init__(self, session_factory):
                self.session_factory = session_factory

            def _parse_auth(self, headers):
                if not headers or "Authorization" not in headers:
                    return None
                auth_header = headers["Authorization"]
                if not auth_header.startswith("Bearer "):
                    return None
                token = auth_header[len("Bearer "):]
                return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            def post(self, url, json=None, headers=None):
                db = self.session_factory()
                auth = self._parse_auth(headers)
                try:
                    parts = url.strip("/").split("/")
                    rec_id = parts[2] if len(parts) > 2 else ""
                    action = parts[3] if len(parts) > 3 else None

                    if action == "approve":
                        data = approve_recommendation(rec_id=rec_id, auth=auth, db=db)
                        return MockResponse(200, data)
                    elif action == "in-transit":
                        data = start_diversion(rec_id=rec_id, auth=auth, db=db)
                        return MockResponse(200, data)
                    elif action == "complete":
                        from app.schemas import ReservationCompleteRequest
                        req_body = ReservationCompleteRequest(**(json or {})) if json else None
                        data = complete_diversion(rec_id=rec_id, body=req_body, auth=auth, db=db)
                        return MockResponse(200, data)
                    elif action == "cancel":
                        from app.schemas import ReservationCancelRequest
                        req_body = ReservationCancelRequest(**(json or {})) if json else None
                        data = cancel_diversion(rec_id=rec_id, body=req_body, auth=auth, db=db)
                        return MockResponse(200, data)
                    elif action == "reconcile-cancellation":
                        from app.schemas import ReservationReconcileRequest
                        req_body = ReservationReconcileRequest(**(json or {})) if json else None
                        data = reconcile_cancelled_diversion(rec_id=rec_id, body=req_body, auth=auth, db=db)
                        return MockResponse(200, data)
                    elif action == "reject":
                        reason = (json or {}).get("reason") if isinstance(json, dict) else None
                        data = reject_recommendation(rec_id=rec_id, reason=reason, auth=auth, db=db)
                        return MockResponse(200, data)
                    elif action == "dismiss":
                        data = dismiss_recommendation(rec_id=rec_id, auth=auth, db=db)
                        return MockResponse(200, data)
                    elif len(parts) >= 4 and parts[1] == "cameras" and parts[3] == "analyze":
                        cam_id = parts[2]
                        from app.routers.cameras import analyze_camera
                        data = analyze_camera(cam_id=cam_id, auth=auth, db=db)
                        return MockResponse(200, data)
                    else:
                        return MockResponse(404, {"detail": "Not found"})
                except HTTPException as e:
                    return MockResponse(e.status_code, {"detail": e.detail})
                except ValidationError as e:
                    return MockResponse(400, {"detail": str(e)})
                finally:
                    db.close()

            def get(self, url, headers=None, params=None):
                db = self.session_factory()
                auth = self._parse_auth(headers)
                try:
                    parts = url.strip("/").split("/")
                    if parts[-1] == "reservations":
                        event_id = (params or {}).get("event_id")
                        data = get_active_reservations(event_id=event_id, auth=auth, db=db)
                        return MockResponse(200, data)
                    elif len(parts) >= 4 and parts[1] == "cameras" and parts[3] == "stream":
                        cam_id = parts[2]
                        from app.routers.cameras import stream_camera_video
                        data = stream_camera_video(cam_id=cam_id, auth=auth, db=db)
                        return MockResponse(200, {"type": "streaming", "media_type": getattr(data, "media_type", "multipart/x-mixed-replace; boundary=frame")})
                    return MockResponse(404, {"detail": "Not found"})
                except HTTPException as e:
                    return MockResponse(e.status_code, {"detail": e.detail})
                except ValidationError as e:
                    return MockResponse(400, {"detail": str(e)})
            def put(self, url, json=None, headers=None, params=None):
                db = self.session_factory()
                auth = self._parse_auth(headers)
                try:
                    parts = url.strip("/").split("/")
                    if len(parts) >= 4 and parts[1] == "cameras" and parts[3] == "playback":
                        cam_id = parts[2]
                        action = (params or {}).get("action") or ((json or {}).get("action") if isinstance(json, dict) else None)
                        from app.routers.cameras import control_camera_playback
                        data = control_camera_playback(cam_id=cam_id, action=action, auth=auth, db=db)
                        return MockResponse(200, data)
                    return MockResponse(404, {"detail": "Not found"})
                except HTTPException as e:
                    return MockResponse(e.status_code, {"detail": e.detail})
                except ValidationError as e:
                    return MockResponse(400, {"detail": str(e)})
                finally:
                    db.close()

        self.client = DirectRouterClient(self.TestSessionLocal)

        # Seed users
        self.user1 = User(id=1, email="officer1@venue.com", hashed_password="pw", name="Officer One", role="Officer")
        self.user2 = User(id=2, email="officer2@other.com", hashed_password="pw", name="Officer Two", role="Officer")
        self.db.add(self.user1)
        self.db.add(self.user2)

        # Seed events
        self.event1 = EventModel(id="evt-test-1", manager_id=1, title="Festival Day 1", capacity=5000)
        self.event2 = EventModel(id="evt-test-2", manager_id=2, title="Festival Day 2", capacity=5000)
        self.db.add(self.event1)
        self.db.add(self.event2)

        # Seed zones for event1
        self.zoneA = ZoneModel(id="z-test-a", event_id="evt-test-1", name="Turnstiles A", capacity=1000, current_count=800, density=80.0)
        self.zoneB = ZoneModel(id="z-test-b", event_id="evt-test-1", name="Concourse B", capacity=500, current_count=50, density=10.0)
        self.zoneC = ZoneModel(id="z-test-c", event_id="evt-test-1", name="Plaza C", capacity=200, current_count=100, density=50.0)
        self.db.add(self.zoneA)
        self.db.add(self.zoneB)
        self.db.add(self.zoneC)

        # Seed default healthy camera for Concourse B (Task 7.6.1 Camera Freshness Guard)
        from app.models import CameraModel
        from app.ai.stream_processor import stream_manager
        now_t = time.time()
        self.camB = CameraModel(
            id="cam-test-b", event_id="evt-test-1", name="Concourse B Camera",
            rtsp_url="rtsp://stream.local/cam-b",
            zone_id="z-test-b", location="Concourse B", status="online", enabled=True,
            playback_status="analyzing", count=50, density=10.0,
            last_frame_timestamp=now_t, last_frame_seq=100
        )
        self.camC = CameraModel(
            id="cam-test-c", event_id="evt-test-1", name="Plaza C Camera",
            rtsp_url="rtsp://stream.local/cam-c",
            zone_id="z-test-c", location="Plaza C", status="online", enabled=True,
            playback_status="analyzing", count=100, density=50.0,
            last_frame_timestamp=now_t, last_frame_seq=100
        )
        self.db.add(self.camB)
        self.db.add(self.camC)

        self.db.commit()

        class MockHealthyWorker:
            def __init__(self, count=50, density=10.0):
                self.is_running = True
                self.is_paused = False
                self.playback_status = "playing"
                self.last_observation_timestamp = time.time()
                self.frame_seq = 100
                self.last_count = count
                self.last_density = density

            def stop(self):
                self.is_running = False
                self.playback_status = "stopped"

            def start(self):
                self.is_running = True
                self.playback_status = "playing"

            def resume(self):
                self.is_paused = False
                self.playback_status = "playing"

        self.MockHealthyWorker = MockHealthyWorker
        stream_manager.workers["cam-test-b"] = MockHealthyWorker(count=50, density=10.0)
        stream_manager.workers["cam-test-c"] = MockHealthyWorker(count=100, density=50.0)

        self.token_user1 = create_access_token({"sub": "officer1@venue.com"})
        self.token_user2 = create_access_token({"sub": "officer2@other.com"})
        self.headers_user1 = {"Authorization": f"Bearer {self.token_user1}"}
        self.headers_user2 = {"Authorization": f"Bearer {self.token_user2}"}

    def tearDown(self):
        from app.database import Base
        from app.ai.stream_processor import stream_manager
        stream_manager.workers.pop("cam-test-b", None)
        stream_manager.workers.pop("cam-test-b2", None)
        stream_manager.workers.pop("cam-test-c", None)
        stream_manager.workers.pop("cam-test-c-other", None)
        self.db.close()
        Base.metadata.drop_all(bind=self.test_engine)
        self.test_engine.dispose()

    def test_01_creating_pending_recommendation_does_not_reserve_capacity(self):
        """1. Creating a pending recommendation does not reserve capacity."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-pending",
            event_id="evt-test-1",
            title="Divert Turnstiles A to Concourse B",
            priority="high",
            reason="Algorithm 2 Verified Route",
            confidence=96,
            zone="Turnstiles A",
            officer="Dispatcher",
            status="pending",
            destination_zone="Concourse B",
            diversion_volume=100.0,
            is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        active_res = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.event_id == "evt-test-1",
            CapacityReservationModel.status.in_(["approved", "in_transit"])
        ).count()
        self.assertEqual(active_res, 0, "Pending recommendation must not create active reservations")

    def test_02_unverified_plan_cannot_reserve_capacity(self):
        """2. An unverified plan cannot reserve capacity."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-unverified",
            event_id="evt-test-1",
            title="Divert crowd without volume",
            priority="high",
            reason="Candidate route with unmeasured volume",
            confidence=96,
            zone="Turnstiles A",
            officer="Dispatcher",
            status="pending",
            destination_zone="Concourse B",
            diversion_volume=None,
            is_capacity_verified=False
        )
        self.db.add(rec)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-test-unverified/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 400, "Unverified plan approval must be rejected with 400 Bad Request")
        self.assertIn("unverified", resp.json()["detail"].lower())

        res_count = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.recommendation_id == "rec-test-unverified"
        ).count()
        self.assertEqual(res_count, 0)
        self.assertEqual(self.db.query(RecommendationModel).filter_by(id="rec-test-unverified").first().status, "pending")

    def test_03_valid_approval_creates_exactly_one_reservation(self):
        """3. A valid approval creates exactly one reservation."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-valid",
            event_id="evt-test-1",
            title="Divert 120 persons to Concourse B",
            priority="high",
            reason="Algorithm 2 Verified Route: Headroom Verified for 120 Persons",
            confidence=96,
            zone="Turnstiles A",
            officer="Dispatcher",
            status="pending",
            destination_zone="Concourse B",
            diversion_volume=120.0,
            is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-test-valid/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "approved")
        self.assertEqual(data["reservation"]["diversion_volume"], 120.0)
        self.assertEqual(data["reservation"]["destination_zone"], "Concourse B")

        reservations = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.recommendation_id == "rec-test-valid"
        ).all()
        self.assertEqual(len(reservations), 1)
        self.assertEqual(reservations[0].status, "approved")
        self.assertEqual(reservations[0].diversion_volume, 120.0)

    def test_04_repeating_same_approval_does_not_reserve_twice(self):
        """4. Repeating the same approval does not reserve twice (Idempotency)."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-idempotent",
            event_id="evt-test-1",
            title="Divert 100 persons",
            priority="high",
            reason="Verified route",
            confidence=96,
            zone="Turnstiles A",
            officer="Dispatcher",
            status="pending",
            destination_zone="Concourse B",
            diversion_volume=100.0,
            is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # First approval
        resp1 = self.client.post("/api/recommendations/rec-test-idempotent/approve", headers=self.headers_user1)
        self.assertEqual(resp1.status_code, 200)

        # Second approval call (same recommendation)
        resp2 = self.client.post("/api/recommendations/rec-test-idempotent/approve", headers=self.headers_user1)
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("already approved", resp2.json()["message"])

        # DB must contain exactly 1 reservation, not 2
        res_list = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.recommendation_id == "rec-test-idempotent"
        ).all()
        self.assertEqual(len(res_list), 1)
        self.assertEqual(res_list[0].diversion_volume, 100.0)

    def test_05_insufficient_headroom_rejects_approval_without_partial_database_changes(self):
        """5. Insufficient headroom rejects approval without partial database changes."""
        from app.models import RecommendationModel, CapacityReservationModel
        # Plaza C: capacity 200, count 100 (50%). Adding 60 persons -> 160 / 200 = 80% >= 75%. Must reject!
        rec = RecommendationModel(
            id="rec-test-overcapacity",
            event_id="evt-test-1",
            title="Divert 60 persons to Plaza C",
            priority="high",
            reason="Verified route",
            confidence=96,
            zone="Turnstiles A",
            officer="Dispatcher",
            status="pending",
            destination_zone="Plaza C",
            diversion_volume=60.0,
            is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-test-overcapacity/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409, "Must return 409 Conflict when headroom is insufficient")
        self.assertIn("75%", resp.json()["detail"])

        # Verify rollback: status remains pending, 0 reservations in DB
        db_rec = self.db.query(RecommendationModel).filter_by(id="rec-test-overcapacity").first()
        self.assertEqual(db_rec.status, "pending")
        self.assertEqual(self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-overcapacity").count(), 0)

    def test_06_concurrent_approvals_competing_for_same_destination_cannot_exceed_capacity(self):
        """6. Concurrent approvals competing for the same destination cannot exceed capacity."""
        import threading
        from app.models import RecommendationModel, CapacityReservationModel
        # Plaza C: capacity 200, count 0 (reset to 0 for clear competition).
        # Max safe volume is < 150 (75%).
        # We submit two competing plans of 80 persons each (80 + 80 = 160 = 80% > 75%).
        plaza = self.db.query(self.zoneC.__class__).filter_by(id="z-test-c").first()
        plaza.current_count = 0
        self.db.commit()

        rec1 = RecommendationModel(
            id="rec-compete-1", event_id="evt-test-1", title="Plan 1", priority="high",
            reason="Route 1", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Plaza C", diversion_volume=80.0, is_capacity_verified=True
        )
        rec2 = RecommendationModel(
            id="rec-compete-2", event_id="evt-test-1", title="Plan 2", priority="high",
            reason="Route 2", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Plaza C", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec1)
        self.db.add(rec2)
        self.db.commit()

        results = []
        def approve_worker(rec_id):
            res = self.client.post(f"/api/recommendations/{rec_id}/approve", headers=self.headers_user1)
            results.append((rec_id, res.status_code))

        t1 = threading.Thread(target=approve_worker, args=("rec-compete-1",))
        t2 = threading.Thread(target=approve_worker, args=("rec-compete-2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        status_codes = [status for _, status in results]
        self.assertIn(200, status_codes, "Exactly one approval must succeed")
        self.assertIn(409, status_codes, "The competing approval that would exceed threshold must be rejected with 409")

        # In DB, exactly 1 reservation exists
        active_reservations = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.destination_zone == "Plaza C",
            CapacityReservationModel.status == "approved"
        ).all()
        self.assertEqual(len(active_reservations), 1)
        self.assertEqual(active_reservations[0].diversion_volume, 80.0)

    def test_07_event_isolation_prevents_cross_event_reservation_access(self):
        """7. Event isolation prevents cross-event reservation access."""
        from app.models import RecommendationModel
        rec = RecommendationModel(
            id="rec-evt1", event_id="evt-test-1", title="Event 1 Route", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # User 2 owns event 2, not event 1
        resp = self.client.post("/api/recommendations/rec-evt1/approve", headers=self.headers_user2)
        self.assertEqual(resp.status_code, 403, "User from another event must be rejected with 403 Forbidden")

    def test_08_unauthorized_users_cannot_approve_or_resolve_reservations(self):
        """8. Unauthorized users cannot approve or resolve reservations."""
        # Missing auth header
        resp_no_auth = self.client.post("/api/recommendations/rec-any/approve")
        self.assertEqual(resp_no_auth.status_code, 401)

        # Invalid token
        resp_bad_auth = self.client.post("/api/recommendations/rec-any/approve", headers={"Authorization": "Bearer invalid.jwt.token"})
        self.assertEqual(resp_bad_auth.status_code, 401)

    def test_09_in_transit_requires_valid_approved_reservation(self):
        """9. in_transit requires a valid approved reservation."""
        from app.models import RecommendationModel
        rec = RecommendationModel(
            id="rec-test-transit", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Calling in-transit on pending recommendation must fail
        resp_pending = self.client.post("/api/recommendations/rec-test-transit/in-transit", headers=self.headers_user1)
        self.assertEqual(resp_pending.status_code, 400)

        # Approve first
        self.client.post("/api/recommendations/rec-test-transit/approve", headers=self.headers_user1)

        # Calling in-transit on approved recommendation succeeds
        resp_approved = self.client.post("/api/recommendations/rec-test-transit/in-transit", headers=self.headers_user1)
        self.assertEqual(resp_approved.status_code, 200)
        self.assertEqual(resp_approved.json()["status"], "in_transit")

    def test_10_completion_requires_authorized_confirmation_and_follows_reconciliation(self):
        """10. Completion requires authorized confirmation and follows reconciliation rule."""
        from app.models import RecommendationModel, CapacityReservationModel, ZoneModel
        rec = RecommendationModel(
            id="rec-test-comp", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-comp/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-comp/in-transit", headers=self.headers_user1)

        # Cross-account completion rejected
        resp_unauth = self.client.post("/api/recommendations/rec-test-comp/complete", headers=self.headers_user2)
        self.assertEqual(resp_unauth.status_code, 403)

        # Authorized completion
        resp_comp = self.client.post(
            "/api/recommendations/rec-test-comp/complete",
            json={"reconciliation_notes": "Officers confirmed crowd successfully cleared corridor"},
            headers=self.headers_user1
        )
        self.assertEqual(resp_comp.status_code, 200)
        self.assertEqual(resp_comp.json()["status"], "completed")

        # Verify DB state
        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-comp").first()
        self.assertEqual(res.status, "completed")
        self.assertIn("Officers confirmed", res.reconciliation_notes)

        # ZoneModel.current_count is NOT blindly incremented (remains 50)
        zoneB = self.db.query(ZoneModel).filter_by(name="Concourse B").first()
        self.assertEqual(zoneB.current_count, 50)

    def test_11_rejected_or_dismissed_pending_recommendations_have_no_reservation(self):
        """11. Rejected or dismissed pending recommendations have no reservation."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-rej", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-rej/reject", json={"reason": "Officer chose alternative corridor"}, headers=self.headers_user1)
        self.assertEqual(self.db.query(RecommendationModel).filter_by(id="rec-test-rej").first().status, "rejected")
        self.assertEqual(self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-rej").count(), 0)

    def test_12_resolved_reservations_are_not_counted_as_active_headroom_consumption(self):
        """12. Resolved reservations are not counted as active headroom consumption."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-res-release", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Approve (reserves 100)
        self.client.post("/api/recommendations/rec-test-res-release/approve", headers=self.headers_user1)
        active_vol_1 = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.destination_zone == "Concourse B",
            CapacityReservationModel.status.in_(["approved", "in_transit"])
        ).count()
        self.assertEqual(active_vol_1, 1)

        # Complete (resolves reservation)
        self.client.post("/api/recommendations/rec-test-res-release/complete", headers=self.headers_user1)
        active_vol_2 = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.destination_zone == "Concourse B",
            CapacityReservationModel.status.in_(["approved", "in_transit"])
        ).count()
        self.assertEqual(active_vol_2, 0, "Resolved reservation must not count toward active headroom consumption")

    def test_13_physical_occupancy_is_not_manually_incremented_by_approval_or_completion(self):
        """13. Physical occupancy is not manually incremented by recommendation approval or completion."""
        from app.models import RecommendationModel, ZoneModel
        rec = RecommendationModel(
            id="rec-test-phys-count", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=150.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        zone = self.db.query(ZoneModel).filter_by(name="Concourse B").first()
        initial_count = zone.current_count
        self.assertEqual(initial_count, 50)

        self.client.post("/api/recommendations/rec-test-phys-count/approve", headers=self.headers_user1)
        self.assertEqual(self.db.query(ZoneModel).filter_by(name="Concourse B").first().current_count, initial_count)

        self.client.post("/api/recommendations/rec-test-phys-count/in-transit", headers=self.headers_user1)
        self.assertEqual(self.db.query(ZoneModel).filter_by(name="Concourse B").first().current_count, initial_count)

        self.client.post("/api/recommendations/rec-test-phys-count/complete", headers=self.headers_user1)
        self.assertEqual(self.db.query(ZoneModel).filter_by(name="Concourse B").first().current_count, initial_count)

    def test_14_reservations_do_not_expire_automatically(self):
        """14. Reservations do not expire automatically (officer-controlled resolution)."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-no-expire", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-no-expire/approve", headers=self.headers_user1)

        # Check reservation
        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-no-expire").first()
        self.assertEqual(res.status, "approved")
        self.assertIsNotNone(res.created_at)

    def test_15_cancel_releases_active_reservation(self):
        """15. Cancelling an approved operation immediately releases reserved capacity."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-cancel", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-cancel/approve", headers=self.headers_user1)
        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-cancel").first()
        self.assertEqual(res.status, "approved")

        resp = self.client.post("/api/recommendations/rec-test-cancel/cancel", json={"reason": "Crowd spontaneously dispersed"}, headers=self.headers_user1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "cancelled")

        self.db.expire_all()
        res_cancelled = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-cancel").first()
        self.assertEqual(res_cancelled.status, "cancelled")
        self.assertIn("Crowd spontaneously dispersed", res_cancelled.reconciliation_notes)

        # Active reservations count is now 0
        active_count = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.destination_zone == "Concourse B",
            CapacityReservationModel.status.in_(["approved", "in_transit", "cancellation_pending"])
        ).count()
        self.assertEqual(active_count, 0)

    def test_16_cancelling_in_transit_enters_cancellation_pending_and_holds_headroom(self):
        """16. Cancelling an in-transit diversion transitions to cancellation_pending and preserves reservation."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-cancel-transit", event_id="evt-test-1", title="Plan in transit", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Approve and start transit
        self.client.post("/api/recommendations/rec-test-cancel-transit/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-cancel-transit/in-transit", headers=self.headers_user1)

        # Cancel while in-transit
        resp = self.client.post(
            "/api/recommendations/rec-test-cancel-transit/cancel",
            json={"reason": "Crowd corridor obstructed near Gate 2"},
            headers=self.headers_user1
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "cancellation_pending")
        self.assertEqual(data["reservation_status"], "cancellation_pending")

        # Verify DB state: status is cancellation_pending, NOT cancelled
        self.db.expire_all()
        rec_db = self.db.query(RecommendationModel).filter_by(id="rec-test-cancel-transit").first()
        res_db = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-cancel-transit").first()
        self.assertEqual(rec_db.status, "cancellation_pending")
        self.assertEqual(res_db.status, "cancellation_pending")

        # Capacity reservation STILL counts in active headroom
        active_count = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.destination_zone == "Concourse B",
            CapacityReservationModel.status.in_(["approved", "in_transit", "cancellation_pending"])
        ).count()
        self.assertEqual(active_count, 1, "In-transit cancellation must continue holding reserved capacity")

    def test_17_cancellation_pending_blocks_competing_recommendation_from_exceeding_capacity(self):
        """17. Cancellation_pending volume continues to block competing approvals from exceeding capacity."""
        from app.models import RecommendationModel, ZoneModel
        # Plaza C: capacity 200, current count 50. Max safe volume < 100 ((50+100)/200 = 75%).
        # Plan 1: 60 persons. Approved and in-transit, then cancelled into cancellation_pending.
        plaza = self.db.query(ZoneModel).filter_by(id="z-test-c").first()
        plaza.current_count = 50
        self.db.commit()

        rec1 = RecommendationModel(
            id="rec-cp-plan1", event_id="evt-test-1", title="Plan 1", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Plaza C", diversion_volume=60.0, is_capacity_verified=True
        )
        rec2 = RecommendationModel(
            id="rec-cp-plan2", event_id="evt-test-1", title="Plan 2 Competing", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Plaza C", diversion_volume=50.0, is_capacity_verified=True
        )
        self.db.add(rec1)
        self.db.add(rec2)
        self.db.commit()

        self.client.post("/api/recommendations/rec-cp-plan1/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-cp-plan1/in-transit", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-cp-plan1/cancel", json={"reason": "Corridor blocked"}, headers=self.headers_user1)

        # Plan 2 attempts to approve 50 persons into Plaza C (50 count + 60 pending + 50 = 160 / 200 = 80% >= 75%)
        resp_compete = self.client.post("/api/recommendations/rec-cp-plan2/approve", headers=self.headers_user1)
        self.assertEqual(resp_compete.status_code, 409, "Must reject competing plan while earlier diversion is unreconciled")
        self.assertIn("75%", resp_compete.json()["detail"])

    def test_18_explicit_officer_reconciliation_safely_releases_reservation(self):
        """18. Explicit officer reconciliation safely finalizes cancellation and frees headroom."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-reconcile-flow", event_id="evt-test-1", title="Plan for reconciliation", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=120.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-reconcile-flow/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-reconcile-flow/in-transit", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-reconcile-flow/cancel", json={"reason": "Crowd rerouted"}, headers=self.headers_user1)

        # Officer confirms physical reconciliation via dedicated endpoint
        resp_rec = self.client.post(
            "/api/recommendations/rec-test-reconcile-flow/reconcile-cancellation",
            json={
                "reconciliation_notes": "Marshals confirmed crowd successfully cleared corridor and redirected to Plaza C",
                "resolution_action": "redirected"
            },
            headers=self.headers_user1
        )
        self.assertEqual(resp_rec.status_code, 200)
        data = resp_rec.json()
        self.assertEqual(data["status"], "cancelled")

        # In DB, status is cancelled and notes recorded
        self.db.expire_all()
        rec_db = self.db.query(RecommendationModel).filter_by(id="rec-test-reconcile-flow").first()
        res_db = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-reconcile-flow").first()
        self.assertEqual(rec_db.status, "cancelled")
        self.assertEqual(res_db.status, "cancelled")
        self.assertIn("REDIRECTED", res_db.reconciliation_notes)
        self.assertIn("Marshals confirmed", res_db.reconciliation_notes)

        # Active headroom is now released
        active_count = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.destination_zone == "Concourse B",
            CapacityReservationModel.status.in_(["approved", "in_transit", "cancellation_pending"])
        ).count()
        self.assertEqual(active_count, 0)

    def test_19_reconciliation_requires_non_empty_confirmation_notes(self):
        """19. Reconciliation requires non-empty confirmation notes."""
        from app.models import RecommendationModel
        rec = RecommendationModel(
            id="rec-test-empty-notes", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-empty-notes/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-empty-notes/in-transit", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-empty-notes/cancel", headers=self.headers_user1)

        # Empty notes
        resp_empty = self.client.post(
            "/api/recommendations/rec-test-empty-notes/reconcile-cancellation",
            json={"reconciliation_notes": "   "},
            headers=self.headers_user1
        )
        self.assertEqual(resp_empty.status_code, 400)
        self.assertIn("notes", resp_empty.json()["detail"].lower())

    def test_20_cancellation_and_reconciliation_are_idempotent(self):
        """20. Cancellation and reconciliation requests are idempotent."""
        from app.models import RecommendationModel
        rec = RecommendationModel(
            id="rec-test-idem-cancel", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-idem-cancel/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-idem-cancel/in-transit", headers=self.headers_user1)

        # First cancel -> cancellation_pending
        resp1 = self.client.post("/api/recommendations/rec-test-idem-cancel/cancel", headers=self.headers_user1)
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()["status"], "cancellation_pending")

        # Second cancel -> remains cancellation_pending
        resp2 = self.client.post("/api/recommendations/rec-test-idem-cancel/cancel", headers=self.headers_user1)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["status"], "cancellation_pending")

        # Reconcile
        resp_rec1 = self.client.post(
            "/api/recommendations/rec-test-idem-cancel/reconcile-cancellation",
            json={"reconciliation_notes": "All cleared"},
            headers=self.headers_user1
        )
        self.assertEqual(resp_rec1.status_code, 200)
        self.assertEqual(resp_rec1.json()["status"], "cancelled")

        # Reconcile again (repeated) -> idempotent 200
        resp_rec2 = self.client.post(
            "/api/recommendations/rec-test-idem-cancel/reconcile-cancellation",
            json={"reconciliation_notes": "All cleared"},
            headers=self.headers_user1
        )
        self.assertEqual(resp_rec2.status_code, 200)
        self.assertEqual(resp_rec2.json()["status"], "cancelled")

    def test_21_cross_event_and_unauthorized_cancellation_and_reconciliation_blocked(self):
        """21. Cross-event and unauthorized users cannot cancel or reconcile."""
        from app.models import RecommendationModel
        rec = RecommendationModel(
            id="rec-test-auth-cancel", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-auth-cancel/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-auth-cancel/in-transit", headers=self.headers_user1)

        # Unauthorized (no token)
        self.assertEqual(self.client.post("/api/recommendations/rec-test-auth-cancel/cancel").status_code, 401)
        self.assertEqual(self.client.post("/api/recommendations/rec-test-auth-cancel/reconcile-cancellation").status_code, 401)

        # Forbidden (user2 from event 2)
        self.assertEqual(self.client.post("/api/recommendations/rec-test-auth-cancel/cancel", headers=self.headers_user2).status_code, 403)
        self.assertEqual(self.client.post("/api/recommendations/rec-test-auth-cancel/reconcile-cancellation", json={"reconciliation_notes": "test"}, headers=self.headers_user2).status_code, 403)

    def test_22_reject_or_dismiss_cannot_bypass_in_transit_or_cancellation_pending(self):
        """22. Rejection or dismissal cannot be used to bypass in-transit or cancellation_pending reservations."""
        from app.models import RecommendationModel
        rec = RecommendationModel(
            id="rec-test-bypass", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-bypass/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-bypass/in-transit", headers=self.headers_user1)

        # Attempt to reject while in-transit
        resp_rej = self.client.post("/api/recommendations/rec-test-bypass/reject", headers=self.headers_user1)
        self.assertEqual(resp_rej.status_code, 400, "Cannot reject an in-transit diversion")

        # Attempt to dismiss while in-transit
        resp_dis = self.client.post("/api/recommendations/rec-test-bypass/dismiss", headers=self.headers_user1)
        self.assertEqual(resp_dis.status_code, 400, "Cannot dismiss an in-transit diversion")

    def test_23_confirm_reconciled_with_missing_notes_rejected(self):
        """23. In cancel_diversion, confirm_reconciled=True with missing notes is rejected (Fix 1)."""
        from app.models import RecommendationModel
        rec = RecommendationModel(
            id="rec-test-missing-notes", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-missing-notes/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-missing-notes/in-transit", headers=self.headers_user1)

        # 1. confirm_reconciled=True with missing notes
        resp1 = self.client.post(
            "/api/recommendations/rec-test-missing-notes/cancel",
            json={"confirm_reconciled": True},
            headers=self.headers_user1
        )
        self.assertEqual(resp1.status_code, 400)
        self.assertIn("notes", resp1.json()["detail"].lower())

        # 2. confirm_reconciled=True with generic reason but missing notes - must NOT fall back to generic reason
        resp2 = self.client.post(
            "/api/recommendations/rec-test-missing-notes/cancel",
            json={"confirm_reconciled": True, "reason": "Officer generic reason"},
            headers=self.headers_user1
        )
        self.assertEqual(resp2.status_code, 400)
        self.assertIn("notes", resp2.json()["detail"].lower())

    def test_24_confirm_reconciled_with_null_empty_and_whitespace_notes_rejected(self):
        """24. In cancel_diversion and reconcile endpoint, null, empty, and whitespace-only notes are rejected (Fix 1)."""
        from app.models import RecommendationModel
        rec = RecommendationModel(
            id="rec-test-ws-notes", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-ws-notes/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-ws-notes/in-transit", headers=self.headers_user1)

        # Null notes
        resp_null = self.client.post(
            "/api/recommendations/rec-test-ws-notes/cancel",
            json={"confirm_reconciled": True, "reconciliation_notes": None},
            headers=self.headers_user1
        )
        self.assertEqual(resp_null.status_code, 400)

        # Empty string notes
        resp_empty = self.client.post(
            "/api/recommendations/rec-test-ws-notes/cancel",
            json={"confirm_reconciled": True, "reconciliation_notes": ""},
            headers=self.headers_user1
        )
        self.assertEqual(resp_empty.status_code, 400)

        # Whitespace-only notes
        resp_ws = self.client.post(
            "/api/recommendations/rec-test-ws-notes/cancel",
            json={"confirm_reconciled": True, "reconciliation_notes": "   \t \n "},
            headers=self.headers_user1
        )
        self.assertEqual(resp_ws.status_code, 400)

    def test_25_valid_explicit_reconciliation_notes_release_reservation(self):
        """25. Valid explicit reconciliation notes release the reservation only after successful confirmation."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-valid-notes", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-valid-notes/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-valid-notes/in-transit", headers=self.headers_user1)

        # Confirm cancellation directly with explicit, non-empty reconciliation notes
        resp = self.client.post(
            "/api/recommendations/rec-test-valid-notes/cancel",
            json={
                "confirm_reconciled": True,
                "reconciliation_notes": "Crowd flow safely halted; all patrons absorbed by buffer areas."
            },
            headers=self.headers_user1
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "cancelled")
        self.assertEqual(resp.json()["reservation_status"], "cancelled")

        # Verify DB state
        db_rec = self.db.query(RecommendationModel).filter(RecommendationModel.id == "rec-test-valid-notes").first()
        self.assertEqual(db_rec.status, "cancelled")
        self.assertIn("[RECONCILED]", db_rec.override_reason)
        self.assertIn("Crowd flow safely halted", db_rec.override_reason)
        self.assertIn("Officer One", db_rec.override_reason)

        db_res = self.db.query(CapacityReservationModel).filter(CapacityReservationModel.recommendation_id == "rec-test-valid-notes").first()
        self.assertEqual(db_res.status, "cancelled")
        self.assertIn("[RECONCILED]", db_res.reconciliation_notes)

        # Verify capacity is released
        active_res = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.event_id == "evt-test-1",
            CapacityReservationModel.status.in_(["approved", "in_transit", "cancellation_pending"])
        ).count()
        self.assertEqual(active_res, 0)

    def test_26_invalid_resolution_action_rejected(self):
        """26. Invalid resolution_action values are rejected (Fix 2)."""
        from pydantic import ValidationError
        from app.schemas import ReservationReconcileRequest
        from app.models import RecommendationModel

        # Pydantic schema validation test
        with self.assertRaises(ValidationError):
            ReservationReconcileRequest(reconciliation_notes="Notes", resolution_action="aborted")

        with self.assertRaises(ValidationError):
            ReservationReconcileRequest(reconciliation_notes="Notes", resolution_action="")

        with self.assertRaises(ValidationError):
            ReservationReconcileRequest(reconciliation_notes="Notes", resolution_action="unknown_action")

        # Endpoint rejection test
        rec = RecommendationModel(
            id="rec-test-action-rej", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-action-rej/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-action-rej/in-transit", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-action-rej/cancel", headers=self.headers_user1)

        # Invalid action via API client
        resp_invalid = self.client.post(
            "/api/recommendations/rec-test-action-rej/reconcile-cancellation",
            json={"reconciliation_notes": "Staff cleared corridor", "resolution_action": "aborted"},
            headers=self.headers_user1
        )
        self.assertEqual(resp_invalid.status_code, 400)

        resp_empty_action = self.client.post(
            "/api/recommendations/rec-test-action-rej/reconcile-cancellation",
            json={"reconciliation_notes": "Staff cleared corridor", "resolution_action": ""},
            headers=self.headers_user1
        )
        self.assertEqual(resp_empty_action.status_code, 400)

    def test_27_all_three_permitted_resolution_actions_accepted(self):
        """27. All three permitted resolution actions ('halted', 'redirected', 'dispersed') are accepted."""
        from app.models import RecommendationModel

        actions = ["halted", "redirected", "dispersed"]
        for act in actions:
            rec_id = f"rec-test-action-{act}"
            rec = RecommendationModel(
                id=rec_id, event_id="evt-test-1", title=f"Plan {act}", priority="high",
                reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
                status="pending", destination_zone="Concourse B", diversion_volume=50.0, is_capacity_verified=True
            )
            self.db.add(rec)
            self.db.commit()

            self.client.post(f"/api/recommendations/{rec_id}/approve", headers=self.headers_user1)
            self.client.post(f"/api/recommendations/{rec_id}/in-transit", headers=self.headers_user1)
            self.client.post(f"/api/recommendations/{rec_id}/cancel", headers=self.headers_user1)

            resp = self.client.post(
                f"/api/recommendations/{rec_id}/reconcile-cancellation",
                json={"reconciliation_notes": f"Movement successfully {act}", "resolution_action": act},
                headers=self.headers_user1
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["status"], "cancelled")

            db_rec = self.db.query(RecommendationModel).filter(RecommendationModel.id == rec_id).first()
            self.assertEqual(db_rec.status, "cancelled")
            self.assertIn(f"[{act.upper()}]", db_rec.override_reason)

        # Also verify default value 'halted' when resolution_action is omitted
        rec_def = RecommendationModel(
            id="rec-test-action-default", event_id="evt-test-1", title="Plan Default", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=50.0, is_capacity_verified=True
        )
        self.db.add(rec_def)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-action-default/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-action-default/in-transit", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-action-default/cancel", headers=self.headers_user1)

        resp_def = self.client.post(
            "/api/recommendations/rec-test-action-default/reconcile-cancellation",
            json={"reconciliation_notes": "Movement stopped by marshals"},
            headers=self.headers_user1
        )
        self.assertEqual(resp_def.status_code, 200)
        db_rec_def = self.db.query(RecommendationModel).filter(RecommendationModel.id == "rec-test-action-default").first()
        self.assertIn("[HALTED]", db_rec_def.override_reason)

    def test_28_invalid_requests_leave_recommendation_and_reservation_unchanged(self):
        """28. Invalid requests leave recommendation and reservation statuses unchanged."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-state-unchanged", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-state-unchanged/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-state-unchanged/in-transit", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-state-unchanged/cancel", headers=self.headers_user1)

        # Baseline check: state is cancellation_pending
        db_rec = self.db.query(RecommendationModel).filter(RecommendationModel.id == "rec-test-state-unchanged").first()
        db_res = self.db.query(CapacityReservationModel).filter(CapacityReservationModel.recommendation_id == "rec-test-state-unchanged").first()
        self.assertEqual(db_rec.status, "cancellation_pending")
        self.assertEqual(db_res.status, "cancellation_pending")

        # Invalid 1: whitespace notes on reconcile
        self.client.post(
            "/api/recommendations/rec-test-state-unchanged/reconcile-cancellation",
            json={"reconciliation_notes": "   "},
            headers=self.headers_user1
        )
        self.db.refresh(db_rec)
        self.db.refresh(db_res)
        self.assertEqual(db_rec.status, "cancellation_pending")
        self.assertEqual(db_res.status, "cancellation_pending")

        # Invalid 2: invalid resolution_action on reconcile
        self.client.post(
            "/api/recommendations/rec-test-state-unchanged/reconcile-cancellation",
            json={"reconciliation_notes": "Valid notes", "resolution_action": "invalid"},
            headers=self.headers_user1
        )
        self.db.refresh(db_rec)
        self.db.refresh(db_res)
        self.assertEqual(db_rec.status, "cancellation_pending")
        self.assertEqual(db_res.status, "cancellation_pending")

        # Invalid 3: confirm_reconciled=True without notes on cancel
        self.client.post(
            "/api/recommendations/rec-test-state-unchanged/cancel",
            json={"confirm_reconciled": True},
            headers=self.headers_user1
        )
        self.db.refresh(db_rec)
        self.db.refresh(db_res)
        self.assertEqual(db_rec.status, "cancellation_pending")
        self.assertEqual(db_res.status, "cancellation_pending")

    def test_29_cancellation_before_transit_still_works(self):
        """29. Pre-transit cancellation releases reservation immediately without requiring reconciliation notes."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-pretransit-cancel", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Approve (not in transit)
        self.client.post("/api/recommendations/rec-test-pretransit-cancel/approve", headers=self.headers_user1)

        # Cancel with normal reason before transit
        resp = self.client.post(
            "/api/recommendations/rec-test-pretransit-cancel/cancel",
            json={"reason": "Crowd surge abated naturally before gate opened"},
            headers=self.headers_user1
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "cancelled")
        self.assertEqual(resp.json()["reservation_status"], "cancelled")

        # Verify DB state
        db_rec = self.db.query(RecommendationModel).filter(RecommendationModel.id == "rec-test-pretransit-cancel").first()
        self.assertEqual(db_rec.status, "cancelled")
        self.assertEqual(db_rec.override_reason, "Crowd surge abated naturally before gate opened")

        db_res = self.db.query(CapacityReservationModel).filter(CapacityReservationModel.recommendation_id == "rec-test-pretransit-cancel").first()
        self.assertEqual(db_res.status, "cancelled")

        # Capacity is released
        active_res = self.db.query(CapacityReservationModel).filter(
            CapacityReservationModel.event_id == "evt-test-1",
            CapacityReservationModel.status.in_(["approved", "in_transit", "cancellation_pending"])
        ).count()
        self.assertEqual(active_res, 0)

    def test_30_cancellation_pending_capacity_protection_event_isolation_and_idempotency_intact(self):
        """30. Existing cancellation-pending capacity protection, event isolation, and idempotency remain intact."""
        from app.models import RecommendationModel, CapacityReservationModel
        rec = RecommendationModel(
            id="rec-test-safeguards", event_id="evt-test-1", title="Plan", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=80.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        self.client.post("/api/recommendations/rec-test-safeguards/approve", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-safeguards/in-transit", headers=self.headers_user1)
        self.client.post("/api/recommendations/rec-test-safeguards/cancel", headers=self.headers_user1)

        # 1. Capacity protection: cancellation_pending is included in active reservations
        active_res_list = self.client.get(
            "/api/recommendations/reservations",
            params={"event_id": "evt-test-1"},
            headers=self.headers_user1
        ).json()
        pending_res = [r for r in active_res_list if getattr(r, "recommendation_id", None) == "rec-test-safeguards"]
        self.assertEqual(len(pending_res), 1)
        self.assertEqual(pending_res[0].status, "cancellation_pending")
        self.assertEqual(float(pending_res[0].diversion_volume), 80.0)

        # 2. Event isolation: officer2 (event 2) cannot cancel or reconcile operation 1
        resp_iso_cancel = self.client.post(
            "/api/recommendations/rec-test-safeguards/cancel",
            headers=self.headers_user2
        )
        self.assertEqual(resp_iso_cancel.status_code, 403)

        resp_iso_rec = self.client.post(
            "/api/recommendations/rec-test-safeguards/reconcile-cancellation",
            json={"reconciliation_notes": "Unauthorized attempt", "resolution_action": "halted"},
            headers=self.headers_user2
        )
        self.assertEqual(resp_iso_rec.status_code, 403)

        # 3. Idempotency: repeated cancel remains cancellation_pending
        resp_idem = self.client.post("/api/recommendations/rec-test-safeguards/cancel", headers=self.headers_user1)
        self.assertEqual(resp_idem.status_code, 200)
        self.assertEqual(resp_idem.json()["status"], "cancellation_pending")

        # Now reconcile with valid notes
        resp_reconciled = self.client.post(
            "/api/recommendations/rec-test-safeguards/reconcile-cancellation",
            json={"reconciliation_notes": "Corridor confirmed empty", "resolution_action": "dispersed"},
            headers=self.headers_user1
        )
        self.assertEqual(resp_reconciled.status_code, 200)
        self.assertEqual(resp_reconciled.json()["status"], "cancelled")

        # Repeated reconcile returns 200 idempotently
        resp_reconciled_again = self.client.post(
            "/api/recommendations/rec-test-safeguards/reconcile-cancellation",
            json={"reconciliation_notes": "Corridor confirmed empty", "resolution_action": "dispersed"},
            headers=self.headers_user1
        )
        self.assertEqual(resp_reconciled_again.status_code, 200)
        self.assertEqual(resp_reconciled_again.json()["status"], "cancelled")

    def test_31_healthy_camera_with_genuine_zero_person_observation(self):
        """31. Healthy camera with a genuine zero-person observation is monitored and approved."""
        import time
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Set count to 0 with fresh timestamp
        self.camB.count = 0
        self.camB.density = 0.0
        self.db.commit()

        stream_manager.workers["cam-test-b"] = self.MockHealthyWorker(count=0, density=0.0)

        rec = RecommendationModel(
            id="rec-test-zero-obs", event_id="evt-test-1", title="Plan Zero", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Approval must succeed because observed 0 from a healthy live camera is valid
        resp = self.client.post("/api/recommendations/rec-test-zero-obs/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 200, f"Expected 200 but got {resp.status_code}: {resp.json()}")
        self.assertEqual(resp.json()["status"], "approved")

        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-zero-obs").first()
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "approved")

    def test_32_disconnected_camera_blocks_destination(self):
        """32. Disconnected camera marks zone unmonitored and blocks approval."""
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Disconnect camera worker and set status to offline
        stream_manager.workers.pop("cam-test-b", None)
        self.camB.status = "offline"
        self.camB.playback_status = "error"
        self.db.commit()

        rec = RecommendationModel(
            id="rec-test-disconnected", event_id="evt-test-1", title="Plan Disconnected", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-test-disconnected/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409, "Disconnected camera must block approval with 409 Conflict")
        self.assertIn("unmonitored", resp.json()["detail"].lower())

        # Verify DB rollback
        self.db.expire_all()
        rec_db = self.db.query(RecommendationModel).filter_by(id="rec-test-disconnected").first()
        self.assertEqual(rec_db.status, "pending")
        self.assertEqual(self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-disconnected").count(), 0)

    def test_33_stale_frame_telemetry_blocks_destination(self):
        """33. Stale frame telemetry (> 15s for live worker) blocks destination approval."""
        import time
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Worker is running, but timestamp is 30 seconds old (> 15.0s limit)
        stale_worker = self.MockHealthyWorker(count=50, density=10.0)
        stale_worker.last_observation_timestamp = time.time() - 30.0
        stream_manager.workers["cam-test-b"] = stale_worker

        rec = RecommendationModel(
            id="rec-test-stale", event_id="evt-test-1", title="Plan Stale", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-test-stale/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409, "Stale telemetry must block approval with 409 Conflict")
        self.assertIn("unmonitored", resp.json()["detail"].lower())

        # No reservation created
        self.assertEqual(self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-stale").count(), 0)

    def test_34_multiple_cameras_partial_coverage_failure_blocks_destination(self):
        """34. Zone with multiple cameras and partial coverage failure is treated as unmonitored."""
        from app.models import CameraModel, RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Add second camera to Concourse B
        camB2 = CameraModel(
            id="cam-test-b2", event_id="evt-test-1", name="Concourse B Camera 2",
            rtsp_url="rtsp://stream.local/cam-b2",
            zone_id="z-test-b", location="Concourse B", status="offline", enabled=True,
            playback_status="error", count=0, density=0.0
        )
        self.db.add(camB2)
        self.db.commit()

        # camB is healthy, but camB2 is offline (no worker)
        self.assertIn("cam-test-b", stream_manager.workers)
        self.assertNotIn("cam-test-b2", stream_manager.workers)

        rec = RecommendationModel(
            id="rec-test-partial-fail", event_id="evt-test-1", title="Plan Partial Fail", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-test-partial-fail/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409, "Partial camera failure must block approval with 409 Conflict")
        self.assertIn("unmonitored", resp.json()["detail"].lower())

        # No reservation created
        self.assertEqual(self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-partial-fail").count(), 0)

    def test_35_unknown_monitoring_health_blocks_destination(self):
        """35. Zone with unknown monitoring health (0 cameras assigned) is blocked from recommendations and approval."""
        from app.models import ZoneModel, RecommendationModel, CapacityReservationModel
        from app.routers.recommendations import evaluate_zone_monitoring_health
        from app.ai.fca_engine import FCAEngine

        # Create Zone with 0 cameras assigned
        zone_unmon = ZoneModel(
            id="z-test-unmon", event_id="evt-test-1", name="Unmonitored Zone D",
            capacity=500, current_count=50, density=10.0
        )
        self.db.add(zone_unmon)
        self.db.commit()

        # 1. Health evaluation check directly
        is_monitored, reason = evaluate_zone_monitoring_health(zone_unmon, [], "evt-test-1", self.db)
        self.assertFalse(is_monitored)
        self.assertIn("unmonitored", reason.lower())

        # 2. Algorithm 2 prevention plan generation excludes unmonitored destination
        engine = FCAEngine()
        La = [{"id": "cpt-unmon", "extent": ["Turnstiles A"], "intent": ["Unmonitored Zone D"]}]
        CA = [{"area": "Turnstiles A", "crowd_score": 0.85, "diversion_volume": 100.0}]
        zone_states = {
            "Turnstiles A": {"capacity": 1000, "current_count": 800, "density": 80.0, "diversion_volume": 100.0},
            "Unmonitored Zone D": {"capacity": 500, "current_count": 50, "density": 10.0, "is_monitored": False}
        }
        res_plan = engine.generate_crowd_prevention_plan(La, CA, zone_states=zone_states)
        self.assertEqual(res_plan["resolved_count"], 0, "Unmonitored zone must be excluded from prevention plans")
        self.assertEqual(res_plan["unresolved_areas"], ["Turnstiles A"])

        # 3. Direct approval gate check fails closed
        rec = RecommendationModel(
            id="rec-test-unmon-dest", event_id="evt-test-1", title="Plan Unmonitored", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Unmonitored Zone D", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-test-unmon-dest/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409, "Unknown monitoring health must fail closed with 409 Conflict")
        self.assertIn("unmonitored", resp.json()["detail"].lower())
        self.assertEqual(self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-unmon-dest").count(), 0)

    def test_36_camera_becoming_unhealthy_between_recommendation_and_approval(self):
        """36. Camera becoming unhealthy between recommendation generation and approval is rejected at approval."""
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Recommendation was generated when camera was assumed healthy
        rec = RecommendationModel(
            id="rec-test-time-drift", event_id="evt-test-1", title="Plan Time Drift", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Before officer approves, camera drops offline
        stream_manager.workers.pop("cam-test-b", None)
        self.camB.status = "offline"
        self.db.commit()

        # Officer attempts to approve: gate revalidates live health inside the lock and rejects
        resp = self.client.post("/api/recommendations/rec-test-time-drift/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("unmonitored", resp.json()["detail"].lower())

        self.db.expire_all()
        self.assertEqual(self.db.query(RecommendationModel).filter_by(id="rec-test-time-drift").first().status, "pending")
        self.assertEqual(self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-time-drift").count(), 0)

    def test_37_recovery_after_fresh_frames_resume(self):
        """37. Recovery after fresh frames resume restores destination eligibility and allows approval."""
        import time
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # 1. Initially unhealthy: worker missing, status offline
        stream_manager.workers.pop("cam-test-b", None)
        self.camB.status = "offline"
        self.db.commit()

        rec = RecommendationModel(
            id="rec-test-recovery", event_id="evt-test-1", title="Plan Recovery", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Approval fails
        resp_fail = self.client.post("/api/recommendations/rec-test-recovery/approve", headers=self.headers_user1)
        self.assertEqual(resp_fail.status_code, 409)

        # 2. Camera recovers: worker running, fresh observation, status online
        self.camB.status = "online"
        self.camB.playback_status = "analyzing"
        self.db.commit()

        stream_manager.workers["cam-test-b"] = self.MockHealthyWorker(count=50, density=10.0)

        # 3. Officer retries approval -> succeeds
        resp_success = self.client.post("/api/recommendations/rec-test-recovery/approve", headers=self.headers_user1)
        self.assertEqual(resp_success.status_code, 200)
        self.assertEqual(resp_success.json()["status"], "approved")

        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-recovery").first()
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "approved")

    def test_38_event_isolation_and_capacity_safeguards_intact(self):
        """38. Event isolation and capacity/reservation protections remain intact."""
        from app.models import CameraModel, ZoneModel, RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # 1. Event isolation: Camera belongs to Event 2, Zone belongs to Event 1
        # Create an Event 1 zone with NO Event 1 cameras
        zone_iso = ZoneModel(
            id="z-test-iso", event_id="evt-test-1", name="Isolated Zone",
            capacity=500, current_count=50, density=10.0
        )
        self.db.add(zone_iso)
        # Create healthy camera belonging to Event 2 that happens to name "Isolated Zone"
        cam_other_evt = CameraModel(
            id="cam-test-c-other", event_id="evt-test-2", name="Event 2 Camera",
            rtsp_url="rtsp://stream.local/cam-evt2",
            zone_id="z-test-iso", location="Isolated Zone", status="online", enabled=True,
            playback_status="analyzing", count=50, density=10.0
        )
        self.db.add(cam_other_evt)
        self.db.commit()
        stream_manager.workers["cam-test-c-other"] = self.MockHealthyWorker(count=50, density=10.0)

        rec_iso = RecommendationModel(
            id="rec-test-iso-cam", event_id="evt-test-1", title="Plan Cross-Event Cam", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Isolated Zone", diversion_volume=100.0, is_capacity_verified=True
        )
        self.db.add(rec_iso)
        self.db.commit()

        # Approval must fail because foreign-event camera cannot monitor Event 1 zone
        resp_iso = self.client.post("/api/recommendations/rec-test-iso-cam/approve", headers=self.headers_user1)
        self.assertEqual(resp_iso.status_code, 409)
        self.assertIn("unmonitored", resp_iso.json()["detail"].lower())

        # 2. Existing capacity safeguards remain intact even when camera is 100% healthy
        # Concourse B: capacity 500, current count 50.
        # Diversion volume 400 -> projected count = 450 / 500 = 90% >= 75%.
        # Camera is healthy, but capacity must still reject!
        rec_cap = RecommendationModel(
            id="rec-test-healthy-but-overcap", event_id="evt-test-1", title="Plan Overcap", priority="high",
            reason="Verified route", confidence=96, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=400.0, is_capacity_verified=True
        )
        self.db.add(rec_cap)
        self.db.commit()

        resp_cap = self.client.post("/api/recommendations/rec-test-healthy-but-overcap/approve", headers=self.headers_user1)
        self.assertEqual(resp_cap.status_code, 409)
        self.assertIn("75%", resp_cap.json()["detail"])

    def test_39_timer_generated_analytics_records_do_not_refresh_frame_health(self):
        """39. Timer-generated CrowdAnalyticsModel records do not refresh frame health (Task 7.6.4)."""
        from app.models import CameraModel, RecommendationModel, CapacityReservationModel, CrowdAnalyticsModel
        from app.ai.stream_processor import stream_manager
        from datetime import datetime, timezone

        # 1. Stale frame health (older than 15s limit)
        stream_manager.workers.pop("cam-test-b", None)
        self.camB.last_frame_timestamp = time.time() - 35.0
        self.camB.last_frame_seq = 40
        self.db.commit()

        # 2. Insert fresh timer-generated analytics record (created 1 second ago)
        timer_analytics = CrowdAnalyticsModel(
            camera_id="cam-test-b",
            event_id="evt-test-1",
            timestamp=datetime.now(timezone.utc),
            count=50,
            density_pct=10.0,
            risk_level="NORMAL",
            flow_rate=1.2,
            speed_avg=1.4
        )
        self.db.add(timer_analytics)
        self.db.commit()

        # 3. Create recommendation targeting Concourse B
        rec = RecommendationModel(
            id="rec-test-timer-stale", event_id="evt-test-1", title="Plan Timer Stale", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=50.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # 4. Approval MUST reject with 409 because timer record does not satisfy frame freshness
        resp = self.client.post("/api/recommendations/rec-test-timer-stale/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("unmonitored", resp.json()["detail"].lower())

        # Verify no reservation was created
        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-timer-stale").first()
        self.assertIsNone(res)

    def test_40_frozen_stream_becomes_unhealthy_even_if_worker_thread_alive(self):
        """40. A frozen stream becomes unhealthy even if its worker thread remains alive (Task 7.6.4)."""
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Live worker is running and alive, but has stopped receiving new frames (frozen stream)
        frozen_time = time.time() - 25.0
        stream_manager.workers["cam-test-b"] = self.MockHealthyWorker(count=50, density=10.0)
        stream_manager.workers["cam-test-b"].last_observation_timestamp = frozen_time
        stream_manager.workers["cam-test-b"].frame_seq = 150

        # Persisted frame heartbeat also frozen
        self.camB.last_frame_timestamp = frozen_time
        self.camB.last_frame_seq = 150
        self.db.commit()

        rec = RecommendationModel(
            id="rec-test-frozen-stream", event_id="evt-test-1", title="Plan Frozen Stream", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=50.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-test-frozen-stream/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("unmonitored", resp.json()["detail"].lower())

    def test_41_crashed_ingestion_owner_becomes_unhealthy_after_frame_health_limit(self):
        """41. A crashed ingestion owner becomes unhealthy after the 15-second frame-health limit (Task 7.6.4)."""
        from app.models import RecommendationModel
        from app.ai.stream_processor import stream_manager

        # Ingestion owner died; this API process has no local worker
        stream_manager.workers.pop("cam-test-b", None)

        # Case A: Owner died 5 seconds ago (within 15.0s window) -> still valid
        self.camB.last_frame_timestamp = time.time() - 5.0
        self.camB.last_frame_seq = 200
        self.db.commit()

        rec_recent = RecommendationModel(
            id="rec-test-crash-recent", event_id="evt-test-1", title="Plan Crash Recent", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=50.0, is_capacity_verified=True
        )
        self.db.add(rec_recent)
        self.db.commit()

        resp_recent = self.client.post("/api/recommendations/rec-test-crash-recent/approve", headers=self.headers_user1)
        self.assertEqual(resp_recent.status_code, 200)

        # Case B: 18 seconds have passed since crash (> 15.0s limit) -> must fail closed
        self.camB.last_frame_timestamp = time.time() - 18.0
        self.db.commit()

        rec_stale = RecommendationModel(
            id="rec-test-crash-stale", event_id="evt-test-1", title="Plan Crash Stale", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=30.0, is_capacity_verified=True
        )
        self.db.add(rec_stale)
        self.db.commit()

        resp_stale = self.client.post("/api/recommendations/rec-test-crash-stale/approve", headers=self.headers_user1)
        self.assertEqual(resp_stale.status_code, 409)
        self.assertIn("unmonitored", resp_stale.json()["detail"].lower())

    def test_42_secondary_api_worker_rejects_stale_persisted_frame_health(self):
        """42. Secondary API worker rejects stale, future, or invalid persisted frame-health evidence (Task 7.6.4)."""
        from app.models import RecommendationModel
        from app.ai.stream_processor import stream_manager

        stream_manager.workers.pop("cam-test-b", None)

        # Subcase 1: Stale timestamp (20 seconds old)
        self.camB.last_frame_timestamp = time.time() - 20.0
        self.camB.last_frame_seq = 100
        self.db.commit()

        rec1 = RecommendationModel(
            id="rec-test-sec-stale", event_id="evt-test-1", title="Plan Sec Stale", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=20.0, is_capacity_verified=True
        )
        self.db.add(rec1)
        self.db.commit()
        resp1 = self.client.post("/api/recommendations/rec-test-sec-stale/approve", headers=self.headers_user1)
        self.assertEqual(resp1.status_code, 409)

        # Subcase 2: Future timestamp beyond allowed clock-skew (+10 seconds)
        self.camB.last_frame_timestamp = time.time() + 10.0
        self.db.commit()
        rec2 = RecommendationModel(
            id="rec-test-sec-future", event_id="evt-test-1", title="Plan Sec Future", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=20.0, is_capacity_verified=True
        )
        self.db.add(rec2)
        self.db.commit()
        resp2 = self.client.post("/api/recommendations/rec-test-sec-future/approve", headers=self.headers_user1)
        self.assertEqual(resp2.status_code, 409)

        # Subcase 3: No frame timestamp recorded (None)
        self.camB.last_frame_timestamp = None
        self.db.commit()
        rec3 = RecommendationModel(
            id="rec-test-sec-none", event_id="evt-test-1", title="Plan Sec None", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=20.0, is_capacity_verified=True
        )
        self.db.add(rec3)
        self.db.commit()
        resp3 = self.client.post("/api/recommendations/rec-test-sec-none/approve", headers=self.headers_user1)
        self.assertEqual(resp3.status_code, 409)

        # Subcase 4: Sequence number is 0 (no actual frame processed)
        self.camB.last_frame_timestamp = time.time()
        self.camB.last_frame_seq = 0
        self.db.commit()
        rec4 = RecommendationModel(
            id="rec-test-sec-seq0", event_id="evt-test-1", title="Plan Sec Seq0", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=20.0, is_capacity_verified=True
        )
        self.db.add(rec4)
        self.db.commit()
        resp4 = self.client.post("/api/recommendations/rec-test-sec-seq0/approve", headers=self.headers_user1)
        self.assertEqual(resp4.status_code, 409)

    def test_43_freshly_processed_frames_restore_eligibility(self):
        """43. Freshly processed frames restore eligibility for capacity reservation (Task 7.6.4)."""
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Start with stale camera
        stream_manager.workers.pop("cam-test-b", None)
        self.camB.last_frame_timestamp = time.time() - 50.0
        self.camB.last_frame_seq = 10
        self.db.commit()

        rec = RecommendationModel(
            id="rec-test-fresh-restore", event_id="evt-test-1", title="Plan Fresh Restore", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=50.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # 1. Approval rejected when stale
        resp_stale = self.client.post("/api/recommendations/rec-test-fresh-restore/approve", headers=self.headers_user1)
        self.assertEqual(resp_stale.status_code, 409)

        # 2. Fresh frame received and processed
        now_t = time.time()
        self.camB.last_frame_timestamp = now_t
        self.camB.last_frame_seq = 11
        self.camB.status = "online"
        self.camB.playback_status = "analyzing"
        self.db.commit()

        # 3. Retrying approval succeeds immediately
        resp_success = self.client.post("/api/recommendations/rec-test-fresh-restore/approve", headers=self.headers_user1)
        self.assertEqual(resp_success.status_code, 200)
        self.assertEqual(resp_success.json()["status"], "approved")

        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-fresh-restore").first()
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "approved")

    def test_44_healthy_camera_reporting_zero_people_distinguishable_from_no_fresh_frames(self):
        """44. Healthy camera reporting 0 people is distinguishable from camera with no fresh frames (Task 7.6.4)."""
        from app.models import RecommendationModel
        from app.ai.stream_processor import stream_manager

        # Zone B has 0 people, but camera is 100% healthy and fresh
        self.zoneB.current_count = 0
        self.zoneB.density = 0.0
        self.camB.count = 0
        self.camB.density = 0.0
        now_t = time.time()
        self.camB.last_frame_timestamp = now_t
        self.camB.last_frame_seq = 300
        self.db.commit()

        stream_manager.workers["cam-test-b"] = self.MockHealthyWorker(count=0, density=0.0)
        stream_manager.workers["cam-test-b"].last_observation_timestamp = now_t
        stream_manager.workers["cam-test-b"].frame_seq = 300

        rec_zero_healthy = RecommendationModel(
            id="rec-test-zero-healthy", event_id="evt-test-1", title="Plan Zero Healthy", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=50.0, is_capacity_verified=True
        )
        self.db.add(rec_zero_healthy)
        self.db.commit()

        # Approval into Concourse B succeeds because 0 count is genuine and verified fresh
        resp_healthy = self.client.post("/api/recommendations/rec-test-zero-healthy/approve", headers=self.headers_user1)
        self.assertEqual(resp_healthy.status_code, 200)

        # Plaza C also has 0 count, but has NO fresh frames
        self.zoneC.current_count = 0
        self.zoneC.density = 0.0
        self.camC.count = 0
        self.camC.density = 0.0
        self.camC.last_frame_timestamp = None
        self.camC.last_frame_seq = 0
        self.db.commit()
        stream_manager.workers.pop("cam-test-c", None)

        rec_zero_unmonitored = RecommendationModel(
            id="rec-test-zero-unmonitored", event_id="evt-test-1", title="Plan Zero Unmonitored", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Plaza C", diversion_volume=30.0, is_capacity_verified=True
        )
        self.db.add(rec_zero_unmonitored)
        self.db.commit()

        # Approval into Plaza C fails closed because 0 count is unmonitored / missing frames
        resp_unmonitored = self.client.post("/api/recommendations/rec-test-zero-unmonitored/approve", headers=self.headers_user1)
        self.assertEqual(resp_unmonitored.status_code, 409)
        self.assertIn("unmonitored", resp_unmonitored.json()["detail"].lower())

    def test_45_duplicate_ingestion_ownership_prevented(self):
        """45. Duplicate ingestion ownership is prevented and explicitly rejected (Task 7.6.4)."""
        import tempfile
        import os
        from app.ai.ingestion_manager import IngestionCoordinator

        # Use an isolated temp lock file
        temp_dir = tempfile.mkdtemp()
        lock_file = os.path.join(temp_dir, "test_ingestion.lock")

        coord1 = IngestionCoordinator(lock_file_path=lock_file)
        coord2 = IngestionCoordinator(lock_file_path=lock_file)

        try:
            # 1. First process acquires ownership
            acquired1 = coord1.acquire_ownership()
            self.assertTrue(acquired1)
            self.assertTrue(coord1.is_owner)

            # 2. Second process tries to acquire ownership -> must fail
            acquired2 = coord2.acquire_ownership()
            self.assertFalse(acquired2)
            self.assertFalse(coord2.is_owner)

            # 3. First process releases ownership
            coord1.release_ownership()
            self.assertFalse(coord1.is_owner)

            # 4. Second process can now acquire ownership
            acquired2_retry = coord2.acquire_ownership()
            self.assertTrue(acquired2_retry)
            self.assertTrue(coord2.is_owner)

            coord2.release_ownership()
            self.assertFalse(coord2.is_owner)
        finally:
            coord1.release_ownership()
            coord2.release_ownership()
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass

    def test_46_event_isolation_and_partial_camera_coverage_failure_enforced(self):
        """46. Event isolation and partial camera-coverage failure remain enforced (Task 7.6.4)."""
        from app.models import CameraModel, RecommendationModel
        from app.ai.stream_processor import stream_manager

        # Add a secondary camera to Concourse B
        cam_b_secondary = CameraModel(
            id="cam-test-b-sec", event_id="evt-test-1", name="Concourse B Camera 2",
            rtsp_url="rtsp://stream.local/cam-b-sec",
            zone_id="z-test-b", location="Concourse B", status="offline", enabled=True,
            playback_status="error", count=0, density=0.0,
            last_frame_timestamp=None, last_frame_seq=0
        )
        self.db.add(cam_b_secondary)
        self.db.commit()

        # Primary camera B is healthy
        self.camB.last_frame_timestamp = time.time()
        self.camB.last_frame_seq = 400
        self.camB.status = "online"
        self.camB.playback_status = "analyzing"
        self.db.commit()

        rec = RecommendationModel(
            id="rec-test-partial-cov", event_id="evt-test-1", title="Plan Partial Coverage", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=40.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Approval must fail because one of the cameras covering Concourse B is offline / errored
        resp = self.client.post("/api/recommendations/rec-test-partial-cov/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("unmonitored", resp.json()["detail"].lower())

    def test_47_failed_health_validation_creates_no_reservation_and_preserves_existing(self):
        """47. Failed health validation creates no reservation and preserves existing reservations (Task 7.6.4)."""
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # 1. Existing valid reservation in Concourse B
        res_existing = CapacityReservationModel(
            id="res-existing-1",
            recommendation_id="rec-existing-1",
            event_id="evt-test-1",
            source_zone="Turnstiles A",
            destination_zone="Concourse B",
            diversion_volume=50.0,
            status="in_transit",
            approved_by="Dispatcher"
        )
        self.db.add(res_existing)
        self.db.commit()

        # 2. Camera B becomes stale / unmonitored
        stream_manager.workers.pop("cam-test-b", None)
        self.camB.last_frame_timestamp = time.time() - 60.0
        self.db.commit()

        # 3. Attempt approval of new recommendation
        rec_new = RecommendationModel(
            id="rec-test-fail-health-preserves", event_id="evt-test-1", title="Plan Fail Health", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=30.0, is_capacity_verified=True
        )
        self.db.add(rec_new)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-test-fail-health-preserves/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409)

        # 4. Verify new recommendation remains pending and has no reservation
        rec_db = self.db.query(RecommendationModel).filter_by(id="rec-test-fail-health-preserves").first()
        self.assertEqual(rec_db.status, "pending")
        res_new = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-fail-health-preserves").first()
        self.assertIsNone(res_new)

        # 5. Verify existing reservation is completely preserved and untouched
        res_check = self.db.query(CapacityReservationModel).filter_by(id="res-existing-1").first()
        self.assertIsNotNone(res_check)
        self.assertEqual(res_check.status, "in_transit")
        self.assertEqual(res_check.diversion_volume, 50.0)

    def test_48_all_baseline_and_lifecycle_invariants_pass(self):
        """48. Full operational lifecycle and research invariants remain intact (Task 7.6.4)."""
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Ensure healthy camera
        now_t = time.time()
        self.camB.last_frame_timestamp = now_t
        self.camB.last_frame_seq = 500
        self.camB.status = "online"
        self.camB.playback_status = "analyzing"
        self.db.commit()
        stream_manager.workers["cam-test-b"] = self.MockHealthyWorker(count=50, density=10.0)

        # Lifecycle: approve -> in-transit -> cancel -> reconcile
        rec = RecommendationModel(
            id="rec-test-lifecycle-full", event_id="evt-test-1", title="Plan Full Lifecycle", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=50.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # 1. Approve
        r1 = self.client.post("/api/recommendations/rec-test-lifecycle-full/approve", headers=self.headers_user1)
        self.assertEqual(r1.status_code, 200)

        # 2. In-Transit
        r2 = self.client.post("/api/recommendations/rec-test-lifecycle-full/in-transit", headers=self.headers_user1)
        self.assertEqual(r2.status_code, 200)

        # 3. Cancel while in-transit -> cancellation_pending
        r3 = self.client.post("/api/recommendations/rec-test-lifecycle-full/cancel", json={"reason": "Hazard detected"}, headers=self.headers_user1)
        self.assertEqual(r3.status_code, 200)
        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-lifecycle-full").first()
        self.assertEqual(res.status, "cancellation_pending")

        # 4. Reconcile cancellation with required notes and valid action
        r4 = self.client.post(
            "/api/recommendations/rec-test-lifecycle-full/reconcile-cancellation",
            json={"resolution_action": "halted", "reconciliation_notes": "Officers halted all movement safely."},
            headers=self.headers_user1
        )
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()["reservation_status"], "cancelled")
        self.db.expire_all()
        res_final = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-lifecycle-full").first()
        self.assertEqual(res_final.status, "cancelled")

    def test_49_camera_restart_invalidates_persisted_heartbeat(self):
        """49. Camera restart invalidates previous persisted heartbeat in DB (Task 7.6.6)."""
        from app.models import CameraModel

        # Camera B starts healthy with fresh telemetry
        now_t = time.time()
        self.camB.last_frame_timestamp = now_t
        self.camB.last_frame_seq = 100
        self.camB.status = "online"
        self.camB.playback_status = "analyzing"
        self.db.commit()

        # Restart camera playback via API
        resp = self.client.put(
            "/api/cameras/cam-test-b/playback",
            json={"action": "restart"},
            headers=self.headers_user1
        )
        self.assertEqual(resp.status_code, 200)

        # Verify DB heartbeat was invalidated
        self.db.expire_all()
        cam = self.db.query(CameraModel).filter_by(id="cam-test-b").first()
        self.assertIsNone(cam.last_frame_timestamp)
        self.assertEqual(cam.last_frame_seq, 0)
        self.assertEqual(cam.playback_status, "analyzing")

    def test_50_secondary_worker_rejects_camera_immediately_after_restart(self):
        """50. Secondary worker rejects camera immediately after restart (Task 7.6.6)."""
        from app.models import RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Restart camera
        self.client.put(
            "/api/cameras/cam-test-b/playback",
            json={"action": "restart"},
            headers=self.headers_user1
        )

        # Simulate secondary API process: no local stream worker in memory
        stream_manager.workers.pop("cam-test-b", None)

        # Create recommendation targeting restarted camera's zone
        rec = RecommendationModel(
            id="rec-test-restart-reject", event_id="evt-test-1", title="Plan Restart Reject", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=30.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Approval must fail closed with 409 Conflict
        resp = self.client.post("/api/recommendations/rec-test-restart-reject/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("unmonitored", resp.json()["detail"].lower())

        # Verify no reservation created
        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-restart-reject").first()
        self.assertIsNone(res)

    def test_51_fresh_post_restart_heartbeat_restores_eligibility(self):
        """51. Fresh post-restart frame heartbeat restores approval eligibility (Task 7.6.6)."""
        from app.models import CameraModel, RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Camera was restarted and has null heartbeat
        self.camB.last_frame_timestamp = None
        self.camB.last_frame_seq = 0
        self.db.commit()
        stream_manager.workers.pop("cam-test-b", None)

        rec = RecommendationModel(
            id="rec-test-restart-restore", event_id="evt-test-1", title="Plan Restart Restore", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=25.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Rejected before new frame
        resp_stale = self.client.post("/api/recommendations/rec-test-restart-restore/approve", headers=self.headers_user1)
        self.assertEqual(resp_stale.status_code, 409)

        # New genuine frame received from restarted stream
        now_t = time.time()
        self.camB.last_frame_timestamp = now_t
        self.camB.last_frame_seq = 1
        self.camB.status = "online"
        self.camB.playback_status = "analyzing"
        self.db.commit()

        # Eligibility immediately restored
        resp_ok = self.client.post("/api/recommendations/rec-test-restart-restore/approve", headers=self.headers_user1)
        self.assertEqual(resp_ok.status_code, 200)
        self.assertEqual(resp_ok.json()["status"], "approved")

        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-restart-restore").first()
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "approved")

    def test_52_failed_restart_does_not_clear_healthy_telemetry(self):
        """52. Failed restart operation does not clear healthy telemetry (Task 7.6.6)."""
        from app.models import CameraModel

        # Camera B starts healthy
        saved_ts = 1700000000.0
        saved_seq = 250
        self.camB.last_frame_timestamp = saved_ts
        self.camB.last_frame_seq = saved_seq
        self.db.commit()

        # Unauthorized user (user2 for event2) attempts to restart event1 camera
        resp_unauth = self.client.put(
            "/api/cameras/cam-test-b/playback",
            json={"action": "restart"},
            headers=self.headers_user2
        )
        self.assertEqual(resp_unauth.status_code, 403)

        # Verify telemetry was NOT cleared
        self.db.expire_all()
        cam = self.db.query(CameraModel).filter_by(id="cam-test-b").first()
        self.assertEqual(cam.last_frame_timestamp, saved_ts)
        self.assertEqual(cam.last_frame_seq, saved_seq)

    def test_53_lock_exclusivity_and_pid_diagnostics(self):
        """53. Ingestion lock exclusivity and PID diagnostics verified (Task 7.6.6)."""
        import tempfile
        import os
        from app.ai.ingestion_manager import IngestionCoordinator

        temp_dir = tempfile.mkdtemp()
        lock_file = os.path.join(temp_dir, "diag_ingestion.lock")

        coord1 = IngestionCoordinator(lock_file_path=lock_file)
        coord2 = IngestionCoordinator(lock_file_path=lock_file)

        try:
            # 1. Process 1 acquires lock
            self.assertTrue(coord1.acquire_ownership())
            self.assertEqual(coord1.get_owner_pid(), os.getpid())

            # 2. Process 2 is excluded
            self.assertFalse(coord2.acquire_ownership())
            # Process 2 can still read leader PID without PermissionError
            owner_pid = coord2.get_owner_pid()
            self.assertEqual(owner_pid, os.getpid())
        finally:
            coord1.release_ownership()
            coord2.release_ownership()
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass

    def test_54_lock_recovery_behavior_works(self):
        """54. Lock recovery after termination or release verified (Task 7.6.6)."""
        import tempfile
        import os
        from app.ai.ingestion_manager import IngestionCoordinator

        temp_dir = tempfile.mkdtemp()
        lock_file = os.path.join(temp_dir, "recovery_ingestion.lock")

        coord1 = IngestionCoordinator(lock_file_path=lock_file)
        coord2 = IngestionCoordinator(lock_file_path=lock_file)

        try:
            coord1.acquire_ownership()
            self.assertFalse(coord2.acquire_ownership())

            # Release lock
            coord1.release_ownership()
            self.assertFalse(coord1.is_owner)

            # Recovery acquisition
            self.assertTrue(coord2.acquire_ownership())
            self.assertEqual(coord2.get_owner_pid(), os.getpid())
            coord2.release_ownership()
        finally:
            coord1.release_ownership()
            coord2.release_ownership()
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass

    def test_55_failed_camera_health_preserves_active_reservations(self):
        """55. Failed camera health preserves existing active reservations (Task 7.6.6)."""
        from app.models import CameraModel, RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # 1. Seed active in_transit reservation
        res_existing = CapacityReservationModel(
            id="res-restart-preserve-1",
            recommendation_id="rec-restart-preserve-1",
            event_id="evt-test-1",
            source_zone="Turnstiles A",
            destination_zone="Concourse B",
            diversion_volume=50.0,
            status="in_transit",
            approved_by="Dispatcher"
        )
        self.db.add(res_existing)
        self.db.commit()

        # 2. Camera restarts -> heartbeat invalidated
        self.camB.last_frame_timestamp = None
        self.camB.last_frame_seq = 0
        self.db.commit()
        stream_manager.workers.pop("cam-test-b", None)

        # 3. New recommendation approval fails closed
        rec_new = RecommendationModel(
            id="rec-restart-new-fail", event_id="evt-test-1", title="Plan Fail", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=30.0, is_capacity_verified=True
        )
        self.db.add(rec_new)
        self.db.commit()

        resp = self.client.post("/api/recommendations/rec-restart-new-fail/approve", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 409)

        # 4. Existing reservation is untouched
        res_check = self.db.query(CapacityReservationModel).filter_by(id="res-restart-preserve-1").first()
        self.assertIsNotNone(res_check)
        self.assertEqual(res_check.status, "in_transit")
        self.assertEqual(res_check.diversion_volume, 50.0)

    def test_56_follower_api_worker_cannot_start_camera_worker_via_preview(self):
        """56. Follower API worker cannot start a CameraStreamWorker via MJPEG preview (Task 7.6.8A)."""
        from app.ai.stream_processor import stream_manager
        from app.ai.ingestion_manager import ingestion_coordinator

        # Ensure process is not ingestion owner
        ingestion_coordinator._is_owner = False
        stream_manager.workers.pop("cam-test-b", None)

        # Request MJPEG preview stream as follower
        resp = self.client.get("/api/cameras/cam-test-b/stream", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 503)
        self.assertIn("ingestion owner process", resp.json()["detail"].lower())

        # Verify no worker was created in follower memory
        self.assertNotIn("cam-test-b", stream_manager.workers)

    def test_57_ingestion_owner_can_supply_preview_frames(self):
        """57. Ingestion owner process can supply preview frames without error (Task 7.6.8A)."""
        from app.ai.stream_processor import stream_manager
        from app.ai.ingestion_manager import ingestion_coordinator

        try:
            # Simulate running on the ingestion owner process
            ingestion_coordinator._is_owner = True
            stream_manager.workers["cam-test-b"] = self.MockHealthyWorker(count=50, density=10.0)

            resp = self.client.get("/api/cameras/cam-test-b/stream", headers=self.headers_user1)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("multipart/x-mixed-replace", resp.json().get("media_type", ""))
        finally:
            ingestion_coordinator._is_owner = False
            stream_manager.workers.pop("cam-test-b", None)

    def test_58_failed_preview_request_does_not_modify_reservations(self):
        """58. Failed preview request does not create workers or alter active reservations (Task 7.6.8A)."""
        from app.models import CapacityReservationModel
        from app.ai.stream_processor import stream_manager
        from app.ai.ingestion_manager import ingestion_coordinator

        ingestion_coordinator._is_owner = False
        stream_manager.workers.pop("cam-test-b", None)

        # Seed existing active in_transit reservation
        res_existing = CapacityReservationModel(
            id="res-preview-preserve-1",
            recommendation_id="rec-preview-preserve-1",
            event_id="evt-test-1",
            source_zone="Turnstiles A",
            destination_zone="Concourse B",
            diversion_volume=45.0,
            status="in_transit",
            approved_by="Dispatcher"
        )
        self.db.add(res_existing)
        self.db.commit()

        # Follower preview request rejected with 503
        resp = self.client.get("/api/cameras/cam-test-b/stream", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 503)

        # Confirm reservation is completely untouched
        res_check = self.db.query(CapacityReservationModel).filter_by(id="res-preview-preserve-1").first()
        self.assertIsNotNone(res_check)
        self.assertEqual(res_check.status, "in_transit")
        self.assertEqual(res_check.diversion_volume, 45.0)
        self.assertNotIn("cam-test-b", stream_manager.workers)

    def test_59_fresh_camera_analysis_invalidates_stale_heartbeat(self):
        """59. Fresh camera analysis session invalidates previous heartbeat (Task 7.6.8A)."""
        from app.models import CameraModel, RecommendationModel
        from app.ai.stream_processor import stream_manager
        from app.ai.ingestion_manager import ingestion_coordinator

        ingestion_coordinator._is_owner = False
        stream_manager.workers.pop("cam-test-b", None)

        # Seed Camera B with pre-existing healthy heartbeat from previous session
        now_t = time.time()
        self.camB.last_frame_timestamp = now_t
        self.camB.last_frame_seq = 200
        self.camB.status = "ready"
        self.camB.playback_status = "ready"
        self.db.commit()

        # Start fresh analysis session via POST /api/cameras/{cam_id}/analyze
        resp = self.client.post("/api/cameras/cam-test-b/analyze", headers=self.headers_user1)
        self.assertEqual(resp.status_code, 200)

        # Verify DB heartbeat was invalidated
        self.db.expire_all()
        cam = self.db.query(CameraModel).filter_by(id="cam-test-b").first()
        self.assertIsNone(cam.last_frame_timestamp)
        self.assertEqual(cam.last_frame_seq, 0)
        self.assertEqual(cam.playback_status, "analyzing")

        # Approval must fail closed immediately after analyze until genuine frame is processed
        rec = RecommendationModel(
            id="rec-test-analyze-reject", event_id="evt-test-1", title="Plan Analyze Reject", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=30.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        resp_appr = self.client.post("/api/recommendations/rec-test-analyze-reject/approve", headers=self.headers_user1)
        self.assertEqual(resp_appr.status_code, 409)
        self.assertIn("unmonitored", resp_appr.json()["detail"].lower())

    def test_60_fresh_frame_evidence_restores_eligibility_after_analyze(self):
        """60. Fresh frame evidence restores approval eligibility after fresh analysis session (Task 7.6.8A)."""
        from app.models import CameraModel, RecommendationModel, CapacityReservationModel
        from app.ai.stream_processor import stream_manager

        # Camera B starts with invalidated heartbeat from analyze (simulate secondary worker)
        stream_manager.workers.pop("cam-test-b", None)
        self.camB.last_frame_timestamp = None
        self.camB.last_frame_seq = 0
        self.camB.status = "online"
        self.camB.playback_status = "analyzing"
        self.db.commit()

        rec = RecommendationModel(
            id="rec-test-analyze-restore", event_id="evt-test-1", title="Plan Analyze Restore", priority="high",
            reason="Route", confidence=95, zone="Turnstiles A", officer="Dispatcher",
            status="pending", destination_zone="Concourse B", diversion_volume=35.0, is_capacity_verified=True
        )
        self.db.add(rec)
        self.db.commit()

        # Approval fails before new frame
        resp_fail = self.client.post("/api/recommendations/rec-test-analyze-restore/approve", headers=self.headers_user1)
        self.assertEqual(resp_fail.status_code, 409)

        # Worker produces genuine fresh frame
        now_t = time.time()
        self.camB.last_frame_timestamp = now_t
        self.camB.last_frame_seq = 1
        self.db.commit()

        # Approval succeeds immediately
        resp_ok = self.client.post("/api/recommendations/rec-test-analyze-restore/approve", headers=self.headers_user1)
        self.assertEqual(resp_ok.status_code, 200)
        self.assertEqual(resp_ok.json()["status"], "approved")

        res = self.db.query(CapacityReservationModel).filter_by(recommendation_id="rec-test-analyze-restore").first()
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "approved")

    def test_61_stream_manager_blocks_non_owner_direct_worker_creation(self):
        """61. ActiveStreamManager raises PermissionError when follower attempts worker creation (Task 7.6.8A)."""
        from app.ai.stream_processor import stream_manager
        from app.ai.ingestion_manager import ingestion_coordinator

        ingestion_coordinator._is_owner = False
        with self.assertRaises(PermissionError) as ctx:
            stream_manager.get_or_create_worker("cam-test-blocked", "test.mp4", "video")

        self.assertIn("Ingestion ownership required", str(ctx.exception))
        self.assertNotIn("cam-test-blocked", stream_manager.workers)


if __name__ == "__main__":
    unittest.main()






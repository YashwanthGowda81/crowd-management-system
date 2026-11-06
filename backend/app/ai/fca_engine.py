"""
FCA Engine — Formal Concept Analysis & Fuzzy Formal Concept Analysis (FFCA)
Research Implementation based on IEEE Access, 2025:
"A Synergy Between Machine Learning and Formal Concept Analysis for Crowd Detection"
Authors: Anas M. Al-Oraiqat, Oleksandr Drieiev, Sattam Almatarneh, Mohammadnoor Injadat,
         Karim A. Al-Oraiqat, Hanna Drieieva, Yassin M. Y. Hasan

Mathematical Foundations:
- Definition 1: Formal Context K = (G, M, I)
- Definition 2: Formal Concept (Extent E, Intent I) with Galois closure: E' = I and I' = E
- Definition 3: Derivation operators A' = {m in M | forall g in A: gIm}, B' = {g in G | forall m in B: gIm}
- Definition 4: Area Formal Context Ka = (A, A, R) for physical area connectivity
- Definition 5: Crowd Formal Context Kc = (A, F, R) with features F = {D, P, M, E, S}
- Definition 6: Area Lattice La derived from Ka
- Definition 7: Crowd Lattice Lc derived from Kc
- Algorithm 1: Extraction of Crowded Areas (T = 0.7)
- Algorithm 2: Generation of Crowd Prevention Plan (topological cover check with human-in-the-loop safety)
"""

import math
from typing import List, Dict, Set, Tuple, Any, Optional

# Standard research crowd features defined in IEEE Access 2025 paper (Section V, Table 2)
CROWD_ATTRIBUTES = [
    {"key": "D", "label": "Crowd Density (High Occupancy)", "weight": 4, "description": "Normalized crowd density in zone"},
    {"key": "P", "label": "Protocol Absence / Risk", "weight": 3, "description": "Absence of safety protocol or marshal coverage (normalized)"},
    {"key": "M", "label": "Movement / Turbulent Flow", "weight": 3, "description": "High dynamic flow rate or rapid accumulation"},
    {"key": "E", "label": "Emergency / Hazard Level", "weight": 4, "description": "Active emergency incident or blocked egress alert"},
    {"key": "S", "label": "Speed Anomaly / Stagnation", "weight": 2, "description": "Stagnation or sudden velocity anomaly"}
]


class FCAEngine:
    """
    Formal Concept Analysis and Fuzzy FCA Galois Engine for Crowd Surveillance.
    Supports both legacy binary alert contexts and research Area Context Ka / Fuzzy Crowd Context Kc.
    """

    def __init__(self):
        self.crowd_attributes = CROWD_ATTRIBUTES
        # Legacy attribute definitions for backward compatibility
        self.attribute_definitions = [
            {"key": "CriticalDensity", "label": "Critical Density (>=90%)", "weight": 4},
            {"key": "HighDensity", "label": "High Density (>=75%)", "weight": 3},
            {"key": "CrowdSurge", "label": "Rapid Crowd Accumulation", "weight": 3},
            {"key": "ExitBlocked", "label": "Exit / Egress Obstruction", "weight": 4},
            {"key": "GateCongestion", "label": "Gate Turnstile Bottleneck", "weight": 3},
            {"key": "RestrictedIntrusion", "label": "Restricted Area Breach", "weight": 3},
            {"key": "ChildSeparated", "label": "Unaccompanied Minor Alert", "weight": 2},
            {"key": "LowSecurityPresence", "label": "Low Security / Staff Ratio", "weight": 2}
        ]

    # =========================================================================
    # TASK 1: FUZZY FORMAL CONTEXT & MEMBERSHIP FUNCTIONS (Paper Definitions 4 & 5)
    # =========================================================================

    def build_fuzzy_crowd_context(
        self,
        zones: List[dict],
        cameras: List[dict] = None,
        alerts: List[dict] = None
    ) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
        """
        Builds the Crowd Fuzzy Formal Context Kc = (A, F, R) (Paper Definition 5, Table 2).
        Objects A: Monitored Areas / Zones.
        Features F: {D: Density, P: Protocol Risk, M: Movement, E: Emergency, S: Speed Anomaly}.
        Relation R: Continuous fuzzy truth degree mu(a, f) in [0.0, 1.0].
        """
        objects: List[str] = []
        fuzzy_context: Dict[str, Dict[str, float]] = {}

        cameras = cameras or []
        alerts = alerts or []

        # Map cameras and alerts to zones
        zone_cam_map: Dict[str, List[dict]] = {}
        zone_alert_map: Dict[str, List[dict]] = {}

        # 1. Register zones
        if zones:
            for z in zones:
                z_name = z.get("name") or z.get("id") or "Zone"
                if z_name not in objects:
                    objects.append(z_name)
                    fuzzy_context[z_name] = {"D": 0.0, "P": 0.0, "M": 0.0, "E": 0.0, "S": 0.0}
                    zone_cam_map[z_name] = []
                    zone_alert_map[z_name] = []

        # If no explicit zones provided, derive objects from camera locations
        if not objects:
            for c in cameras:
                c_loc = c.get("location") or c.get("name") or "Area"
                if c_loc not in objects:
                    objects.append(c_loc)
                    fuzzy_context[c_loc] = {"D": 0.0, "P": 0.0, "M": 0.0, "E": 0.0, "S": 0.0}
                    zone_cam_map[c_loc] = []
                    zone_alert_map[c_loc] = []

        # Safe fallback if completely empty
        if not objects:
            objects = ["Area A1", "Area A2"]
            fuzzy_context["Area A1"] = {"D": 0.0, "P": 0.0, "M": 0.0, "E": 0.0, "S": 0.0}
            fuzzy_context["Area A2"] = {"D": 0.0, "P": 0.0, "M": 0.0, "E": 0.0, "S": 0.0}
            return objects, fuzzy_context

        # Lookup table for zone metadata by object key
        zone_dict_by_name = { (z.get("name") or z.get("id") or "Zone"): z for z in zones } if zones else {}

        # Map cameras to nearest/matching zone object
        for c in cameras:
            matched_obj = None
            c_zone_id = str(c.get("zone_id") or "").strip()
            c_loc = str(c.get("location") or "").strip().lower()
            c_name = str(c.get("name") or "").strip().lower()

            # Priority 1: Match by explicit zone_id against zone ID, display name, zone code, or object key
            if c_zone_id:
                for obj in objects:
                    z = zone_dict_by_name.get(obj, {})
                    z_id = str(z.get("id") or "").strip()
                    z_name = str(z.get("name") or "").strip()
                    z_code = str(z.get("code") or "").strip().lower()
                    if c_zone_id == z_id or c_zone_id == z_name or c_zone_id == obj or (z_code and c_zone_id.lower() == z_code):
                        matched_obj = obj
                        break

            # Priority 2: If no zone_id matched, match only when meaningful location or camera name is present
            if not matched_obj and (c_loc or c_name):
                for obj in objects:
                    z = zone_dict_by_name.get(obj, {})
                    z_name = str(z.get("name") or "").strip()
                    z_code = str(z.get("code") or "").strip().lower()
                    obj_l = obj.strip().lower()
                    z_name_l = z_name.lower() if z_name else obj_l

                    loc_matched = False
                    if c_loc:
                        # Zone name in location description (e.g. "North Gate" in "North Gate Entry")
                        if (obj_l and obj_l in c_loc) or (z_name_l and z_name_l in c_loc):
                            loc_matched = True
                        # Or location in zone name (requiring >= 3 characters to prevent trivial accidental matches)
                        elif len(c_loc) >= 3 and ((obj_l and c_loc in obj_l) or (z_name_l and c_loc in z_name_l)):
                            loc_matched = True
                        elif z_code and z_code in c_loc:
                            loc_matched = True

                    name_matched = False
                    if c_name:
                        if (obj_l and obj_l in c_name) or (z_name_l and z_name_l in c_name):
                            name_matched = True
                        elif len(c_name) >= 3 and ((obj_l and c_name in obj_l) or (z_name_l and c_name in z_name_l)):
                            name_matched = True
                        elif z_code and z_code in c_name:
                            name_matched = True

                    if loc_matched or name_matched:
                        matched_obj = obj
                        break

            if matched_obj:
                zone_cam_map.setdefault(matched_obj, []).append(c)

        # Map active alerts to zone object
        for a in alerts:
            if not a.get("resolved", False):
                a_ref = ((a.get("zone") or "") + " " + (a.get("camera") or "")).strip().lower()
                matched_obj = None
                if a_ref:
                    for obj in objects:
                        obj_l = obj.strip().lower()
                        if obj_l and (obj_l in a_ref or (len(a_ref) >= 3 and a_ref in obj_l)):
                            matched_obj = obj
                            break
                if matched_obj:
                    zone_alert_map.setdefault(matched_obj, []).append(a)

        # 2. Compute Fuzzy Membership Degrees mu(a, f) in [0.0, 1.0]
        # Mathematical formulas correspond to paper Section V & VI

        for obj in objects:
            z_data = zone_dict_by_name.get(obj, {})
            cams = zone_cam_map.get(obj, [])
            alts = zone_alert_map.get(obj, [])

            # --- Attribute D: Crowd Density ---
            # Paper p. 6: indicates whether crowd level returned by model is high.
            # Continuous membership degree:
            # - If zone density_pct is available: density_pct / 100.0 clamped to [0, 1]
            # - Or count / capacity ratio
            dens_values = []
            if "density" in z_data:
                dens_values.append(float(z_data.get("density", 0.0)) / 100.0)
            elif "current_count" in z_data and z_data.get("capacity", 0) > 0:
                dens_values.append(float(z_data.get("current_count", 0)) / float(z_data.get("capacity", 1)))
            for c in cams:
                dens_values.append(float(c.get("density", 0.0)) / 100.0)

            d_val = max(dens_values) if dens_values else 0.0
            fuzzy_d = round(max(0.0, min(1.0, d_val)), 3)

            # --- Attribute P: Safety Protocol Absence / Risk ---
            # Paper p. 6: "The absence of a safety protocol requires a crowd prevention plan to avoid
            # dangerous situation... we normalized the values of such type of attributed area: entry value 1"
            # If zone has no protocol, or staffing is inadequate, protocol risk is high (1.0).
            # If safety protocol exists and is followed, protocol risk is low (0.0).
            z_type = str(z_data.get("zone_type", "")).lower()
            if "restricted" in z_type or "vip" in z_type:
                # Sensitive area requires stricter safety protocol
                fuzzy_p = 0.85
            elif "exit" in z_type:
                fuzzy_p = 0.60
            else:
                fuzzy_p = 0.40

            # Elevated if security alert exists in this area
            for a in alts:
                t_str = (a.get("title", "") + " " + a.get("description", "")).lower()
                if "security" in t_str or "unattended" in t_str or "breach" in t_str or "intrusion" in t_str:
                    fuzzy_p = max(fuzzy_p, 0.90)

            # --- Attribute M: Movement / Dynamic Crowd Flow ---
            # Paper p. 6 & 10: motion vector magnitude and flow rate
            flow_values = []
            for c in cams:
                fr = c.get("flow_rate")
                if fr is not None and not isinstance(fr, bool) and isinstance(fr, (int, float)):
                    if math.isfinite(fr) and 0.0 <= fr <= 20.0:
                        flow_values.append(float(fr))

            if flow_values:
                # Valid measured flow rate
                avg_flow = sum(flow_values) / len(flow_values)
                fuzzy_m = round(max(0.0, min(1.0, avg_flow / 4.0)), 3)
            else:
                # Honest handling of missing telemetry:
                # Density-derived estimate capped strictly below alpha = 0.50 (max 0.40)
                # to prevent unmeasured data from falsely triggering verified movement anomaly
                fuzzy_m = round(min(0.40, fuzzy_d * 0.5), 3)

            # --- Attribute E: Emergency / Hazard Level ---
            # Paper p. 6: presence of emergency situations, exit blocks, stampede surge
            fuzzy_e = 0.0
            for a in alts:
                lvl = str(a.get("level", "")).lower()
                desc = (a.get("title", "") + " " + a.get("description", "")).lower()
                if "critical" in lvl or "stampede" in desc or "surge" in desc:
                    fuzzy_e = max(fuzzy_e, 1.0)
                elif "high" in lvl or "block" in desc or "fire" in desc:
                    fuzzy_e = max(fuzzy_e, 0.85)
                elif "medium" in lvl:
                    fuzzy_e = max(fuzzy_e, 0.50)
                else:
                    fuzzy_e = max(fuzzy_e, 0.25)

            # --- Attribute S: Speed Anomaly / Stagnation ---
            # Paper p. 6 & 10: velocity vector anomalies.
            # Crowd stagnation (crush) or panic rush:
            speed_values = []
            for c in cams:
                sp = c.get("speed_avg")
                if sp is not None and not isinstance(sp, bool) and isinstance(sp, (int, float)):
                    if math.isfinite(sp) and 0.0 <= sp <= 30.0:
                        speed_values.append(float(sp))

            if speed_values:
                avg_speed = sum(speed_values) / len(speed_values)
                # Normal human walking speed: ~1.2 to 1.4 m/s.
                # Speed < 0.4 m/s indicates severe crowd crush/bottleneck stagnation (when crowd is present).
                # Speed > 2.2 m/s indicates stampede/running.
                if avg_speed < 0.4:
                    if fuzzy_d > 0.05:
                        fuzzy_s = round(1.0 - (avg_speed / 0.4) * 0.5, 3)  # 0.5 to 1.0 (verified crush anomaly)
                    else:
                        fuzzy_s = 0.10  # Zero speed in an empty area is not a crowd crush
                elif avg_speed > 2.2:
                    fuzzy_s = round(min(1.0, (avg_speed - 2.2) / 1.5 + 0.6), 3)  # 0.6 to 1.0 (verified stampede anomaly)
                else:
                    fuzzy_s = 0.15  # Verified normal walking speed (low anomaly)
            else:
                # Honest handling of missing speed telemetry:
                # Baseline nominal score strictly below alpha = 0.50 so an unmeasured sensor
                # is never silently classified as a verified speed anomaly.
                fuzzy_s = 0.15

            if not hasattr(self, "last_crowd_telemetry_meta"):
                self.last_crowd_telemetry_meta = {}
            self.last_crowd_telemetry_meta[obj] = {
                "movement_measured": bool(flow_values),
                "speed_measured": bool(speed_values),
                "flow_sample_count": len(flow_values),
                "speed_sample_count": len(speed_values)
            }

            fuzzy_context[obj] = {
                "D": fuzzy_d,
                "P": round(fuzzy_p, 3),
                "M": fuzzy_m,
                "E": round(fuzzy_e, 3),
                "S": fuzzy_s
            }

        return objects, fuzzy_context

    def build_area_context(
        self,
        zones: List[dict],
        connections: List[dict] = None
    ) -> Tuple[List[str], Dict[str, Set[str]]]:
        """
        Builds the Area Formal Context Ka = (A, A, R) (Paper Definition 4, Table 1).
        Objects A: Monitored areas.
        Attributes A: Same set of monitored areas.
        Relation R: Binary connection relation where a1Ra2 indicates a direct physical passage
                    allowing crowd migration between area a1 and area a2.
        Excludes blocked or restricted passages.
        """
        objects: List[str] = []
        relation: Dict[str, Set[str]] = {}

        # 1. Populate area objects
        zone_id_to_name: Dict[str, str] = {}
        for z in zones:
            z_id = z.get("id") or z.get("name")
            z_name = z.get("name") or z_id
            zone_id_to_name[z_id] = z_name
            if z_name not in objects:
                objects.append(z_name)
                relation[z_name] = set()

        if not objects:
            objects = ["Area A1", "Area A2"]
            relation["Area A1"] = set(["Area A2"])
            relation["Area A2"] = set(["Area A1"])
            return objects, relation

        # 2. Populate edges from explicit connections
        if connections:
            for conn in connections:
                if conn.get("is_blocked", False):
                    # Blocked passageway cannot participate in migration (Paper Section V)
                    continue

                from_id = conn.get("from_zone_id")
                to_id = conn.get("to_zone_id")
                from_name = zone_id_to_name.get(from_id, from_id)
                to_name = zone_id_to_name.get(to_id, to_id)

                if from_name in relation and to_name in relation and from_name != to_name:
                    relation[from_name].add(to_name)
                    if conn.get("bidirectional", True):
                        relation[to_name].add(from_name)

        # Do not invent adjacency when the venue has no configured passages.
        # Definition 4 models actual area-to-area connections; unknown topology is
        # an empty relation, not a sequential chain of zones.
        return objects, relation

    # =========================================================================
    # TASK 2: VALID CONCEPT LATTICE GENERATION & DERIVATION OPERATORS
    # =========================================================================

    def galois_extent(self, intent: Set[str], objects: List[str], relation: Dict[str, Set[str]]) -> List[str]:
        """
        Derivation operator B' = {g in G | forall m in B: gIm} (Paper Definition 3).
        Given attribute set B (intent), returns all objects sharing all attributes in B.
        If intent is empty, returns all objects G (Supremum Extent).
        """
        if not intent:
            return list(objects)
        return [obj for obj in objects if intent.issubset(relation.get(obj, set()))]

    def galois_intent(self, extent: List[str], all_attributes: List[str], relation: Dict[str, Set[str]]) -> Set[str]:
        """
        Derivation operator A' = {m in M | forall g in A: gIm} (Paper Definition 3).
        Given object set A (extent), returns all common attributes shared by all objects in A.
        If extent is empty, returns all attributes M (Infimum Intent).
        """
        if not extent:
            return set(all_attributes)

        common: Optional[Set[str]] = None
        for obj in extent:
            obj_attrs = relation.get(obj, set())
            if common is None:
                common = set(obj_attrs)
            else:
                common = common.intersection(obj_attrs)
        return common if common is not None else set()

    def derive_closed_concepts(
        self,
        objects: List[str],
        relation: Dict[str, Set[str]],
        all_attributes: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Derives all mathematically closed formal concepts (E, I) satisfying:
        E' = I and I' = E (Paper Definition 2).
        Uses closed-intent intersection closure to guarantee mathematical completeness,
        uniqueness (no duplicates), and inclusion of Supremum and Infimum.
        """
        if not objects:
            return []

        # Collect base closed intents from each object: {g}''
        closed_intents: List[Set[str]] = []

        # 1. Supremum concept: Intent = (G)'
        supremum_intent = self.galois_intent(objects, all_attributes, relation)
        closed_intents.append(supremum_intent)

        # 2. Infimum concept: Intent = all_attributes if any object has all, else closure of M
        infimum_extent = self.galois_extent(set(all_attributes), objects, relation)
        infimum_intent = self.galois_intent(infimum_extent, all_attributes, relation)
        if infimum_intent not in closed_intents:
            closed_intents.append(infimum_intent)

        # 3. Base intents for each single object
        for obj in objects:
            intent_g = relation.get(obj, set())
            # Close intent: (intent_g')'
            closed_i = self.galois_intent(self.galois_extent(intent_g, objects, relation), all_attributes, relation)
            if closed_i not in closed_intents:
                closed_intents.append(closed_i)

        # 4. Successive meet-intersections until fixed point is reached
        changed = True
        max_iterations = 25
        iteration = 0
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            n = len(closed_intents)
            for i in range(n):
                for j in range(i + 1, n):
                    intersect = closed_intents[i].intersection(closed_intents[j])
                    # Close the intersection
                    ext = self.galois_extent(intersect, objects, relation)
                    closed_inter = self.galois_intent(ext, all_attributes, relation)
                    if closed_inter not in closed_intents:
                        closed_intents.append(closed_inter)
                        changed = True

        # Sort intents by cardinality ascending (Top/Supremum first)
        closed_intents.sort(key=lambda s: (len(s), sorted(list(s))))

        # Build formal concept dictionaries
        concepts = []
        for idx, intent in enumerate(closed_intents, 1):
            extent = self.galois_extent(intent, objects, relation)
            intent_list = sorted(list(intent))
            extent_list = sorted(list(extent))

            action = self._determine_action_for_intent(intent_list, extent_list)
            confidence = min(99, 80 + len(intent_list) * 4)

            concepts.append({
                "id": f"c{idx}",
                "label": f"Concept {idx} ({len(extent_list)} Extent, {len(intent_list)} Intent)",
                "extent": extent_list,
                "intent": intent_list,
                "formula": f"({{{', '.join(extent_list[:3]) + ('...' if len(extent_list) > 3 else '')}}}, {{{', '.join(intent_list)}}})",
                "action": action,
                "confidence": confidence
            })

        return concepts

    def build_lattice_graph(self, concepts: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Builds the Concept Lattice DAG (Hasse diagram) with strict transitive reduction.
        An edge c1 -> c2 exists iff c1 is an IMMEDIATE subconcept of c2 (c1 covers c2 in extent,
        or c1 has subconcept relation c1 < c2 and there exists no c3 such that c1 < c3 < c2).
        Eliminates duplicate edges and incorrect cardinality-jump skips.
        """
        if not concepts:
            return [], []

        # 1. Stratify concepts by Intent cardinality for SVG layout
        layers: Dict[int, List[Dict]] = {}
        for c in concepts:
            layer_idx = len(c["intent"])
            layers.setdefault(layer_idx, []).append(c)

        sorted_layers = sorted(layers.keys())
        total_layers = len(sorted_layers)
        y_step = 300.0 / max(1, total_layers - 1) if total_layers > 1 else 150.0

        nodes = []
        node_map: Dict[str, Dict] = {}

        for l_idx, layer_key in enumerate(sorted_layers):
            layer_nodes = layers[layer_key]
            y = 50.0 + l_idx * y_step
            count = len(layer_nodes)
            x_step = 400.0 / max(1, count + 1)

            for n_idx, c in enumerate(layer_nodes):
                x = 50.0 + (n_idx + 1) * x_step
                node_data = {
                    "id": c["id"],
                    "label": c["label"],
                    "extent": c["extent"],
                    "intent": c["intent"],
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "formula": c.get("formula", ""),
                    "action": c.get("action", ""),
                    "confidence": c.get("confidence", 90)
                }
                nodes.append(node_data)
                node_map[c["id"]] = node_data

        # 2. Mathematically correct Covering Relation (Transitive Reduction)
        # c1 < c2 iff Intent(c1) is proper subset of Intent(c2)
        # c1 is covered by c2 iff c1 < c2 and NO c3 exists with c1 < c3 < c2
        connections: List[Dict[str, str]] = []
        n = len(concepts)

        # Precompute concept intents as sets
        intent_sets = [set(c["intent"]) for c in concepts]

        for i in range(n):
            set_i = intent_sets[i]
            for j in range(n):
                if i == j:
                    continue
                set_j = intent_sets[j]

                # Check if set_i is proper subset of set_j (c_i is superconcept in extent, subconcept in intent)
                if set_i.issubset(set_j) and set_i != set_j:
                    # Check if there is any intermediate concept k such that set_i < set_k < set_j
                    is_immediate = True
                    for k in range(n):
                        if k == i or k == j:
                            continue
                        set_k = intent_sets[k]
                        if set_i.issubset(set_k) and set_k.issubset(set_j) and set_k != set_i and set_k != set_j:
                            is_immediate = False
                            break
                    if is_immediate:
                        connections.append({
                            "from": concepts[i]["id"],
                            "to": concepts[j]["id"]
                        })

        # Deduplicate
        seen = set()
        clean_conns = []
        for conn in connections:
            pair = (conn["from"], conn["to"])
            if pair not in seen:
                seen.add(pair)
                clean_conns.append(conn)

        return nodes, clean_conns

    # =========================================================================
    # TASK 3: ALGORITHM 1 — EXTRACTION OF CROWDED AREAS (Paper Section VI-D, p. 11)
    # =========================================================================

    def check_crowd(self, kc_area: Dict[str, float], intent: List[str]) -> float:
        """
        Line 7 in Algorithm 1: c = checkCrowd(Kc[a], cpt.Intent) (Paper p. 11).
        Measures the aggregate fuzzy crowd truth degree of area 'a' under intent criteria.
        Paper specifies: high crowd requires high crowd density (D in cpt.Intent) and
        satisfaction of multi-criteria crowd parameters.
        """
        if not intent:
            return float(kc_area.get("D", 0.0))

        # Sum truth degrees of attributes present in the formal concept's intent
        scores = [float(kc_area.get(attr, 0.0)) for attr in intent]
        avg_score = sum(scores) / max(1, len(scores))

        # High crowd requirement from paper p. 11:
        # "the area a in A that has a high crowd density (D in cpt.Intent) will be checked"
        if "D" in intent:
            # Weighted with density prominence
            dens_val = float(kc_area.get("D", 0.0))
            return round(0.6 * dens_val + 0.4 * avg_score, 3)
        else:
            return round(avg_score * 0.7, 3)

    def extract_crowded_areas(
        self,
        Lc: List[Dict],
        Kc: Dict[str, Dict[str, float]],
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Algorithm 1: Extraction of Crowded Areas (Paper IEEE Access 2025, p. 11).
        
        Require: crowd lattice Lc, crowd formal context Kc, threshold T = 0.7
        Ensure: Set CA of crowded areas with supporting concept information and attributes.
        """
        if not Lc or not Kc:
            return []

        # 1. Sort Lc's concepts in decreasing size of Intent (line 1)
        # Crowded areas satisfy most of the crowd criteria.
        sorted_lc = sorted(Lc, key=lambda cpt: len(cpt.get("intent", [])), reverse=True)

        # 2. Initialize A = Supremum.Extent (line 2)
        # The supremum is the top concept with minimal intent / maximal extent
        supremum = min(Lc, key=lambda cpt: len(cpt.get("intent", [])))
        A = set(supremum.get("extent", []))

        # 3. Initialize CA = empty set (line 3)
        CA: List[Dict[str, Any]] = []
        found_in_ca: Set[str] = set()

        # 4. While A != empty:
        while A:
            progress = False
            # 5. For each cpt in Lc:
            for cpt in sorted_lc:
                cpt_intent = cpt.get("intent", [])
                cpt_extent = cpt.get("extent", [])

                # 6. For each a in cpt.Extent:
                for a in cpt_extent:
                    if a in A:
                        # 7. c = checkCrowd(Kc[a], cpt.Intent)
                        kc_a = Kc.get(a, {"D": 0.0, "P": 0.0, "M": 0.0, "E": 0.0, "S": 0.0})
                        c = self.check_crowd(kc_a, cpt_intent)

                        # 8. If a in A and c > T:
                        if c > threshold:
                            # 9. Add a to CA
                            CA.append({
                                "area": a,
                                "crowd_score": c,
                                "concept_id": cpt.get("id"),
                                "satisfied_intent": cpt_intent,
                                "attribute_scores": kc_a,
                                "is_crowded": True,
                                "reason": f"FCA Algorithm 1: Crowd score c={c:.2f} > T={threshold} under intent criteria {cpt_intent}."
                            })
                            found_in_ca.add(a)
                            # 10. Remove a from A
                            A.remove(a)
                            progress = True
                            break
                if progress:
                    break

            # If no concept in Lc elevated any remaining area above threshold,
            # dismiss low-crowd areas as specified by the paper (p. 11 line 14)
            if not progress:
                break

        return CA

    # =========================================================================
    # TASK 4 & TASK 7: ALGORITHM 2 — CROWD-PREVENTION PLAN GENERATION (Paper p. 12)
    # =========================================================================

    def _parse_diversion_volume(self, val: Any) -> Optional[float]:
        """
        Parses an explicitly provided diversion volume.
        Returns float >= 0 if explicitly provided, finite, and non-negative.
        Returns None if missing, invalid, boolean, negative, NaN, or infinite.
        Does NOT invent fallback numbers or percentages.
        """
        if val is None or isinstance(val, bool):
            return None
        if isinstance(val, (int, float)):
            if math.isfinite(val) and val >= 0:
                return float(val)
            return None
        if isinstance(val, str) and val.strip():
            try:
                num = float(val.strip())
                if math.isfinite(num) and num >= 0:
                    return num
            except (ValueError, TypeError):
                return None
        return None

    def _resolve_source_diversion_volume(
        self,
        src: str,
        zone_state: Optional[Dict[str, Any]],
        ca_dict: Optional[Dict[str, Any]]
    ) -> Tuple[bool, float]:
        """
        Resolves explicit diversion volume for a source area.
        Never assumes current_count or headcount is diversion volume.
        Returns (True, volume) if explicitly provided, valid, finite, and non-negative.
        Returns (False, 0.0) if unmeasured, missing, or invalid.
        """
        # 1. Check zone_state
        if isinstance(zone_state, dict):
            if "diversion_volume" in zone_state:
                parsed = self._parse_diversion_volume(zone_state["diversion_volume"])
                if parsed is not None:
                    return True, parsed
            if "required_diversion" in zone_state:
                parsed = self._parse_diversion_volume(zone_state["required_diversion"])
                if parsed is not None:
                    return True, parsed

        # 2. Check ca_dict
        if isinstance(ca_dict, dict):
            if "diversion_volume" in ca_dict:
                parsed = self._parse_diversion_volume(ca_dict["diversion_volume"])
                if parsed is not None:
                    return True, parsed
            if "required_diversion" in ca_dict:
                parsed = self._parse_diversion_volume(ca_dict["required_diversion"])
                if parsed is not None:
                    return True, parsed

        return False, 0.0

    def _check_cover(
        self,
        A_prime: Set[str],
        candidate_destinations: Set[str],
        CA_names: Set[str],
        zone_states: Dict[str, dict],
        blocked_edges: Set[Tuple[str, str]],
        allowed_edges: Optional[Set[Tuple[str, str]]] = None,
        required_volume: float = 0.0,
        has_reliable_volume: bool = False
    ) -> Tuple[bool, List[str], str]:
        """
        Evaluates cover(A', cpt.Intent) (Paper Algorithm 2, line 7).
        Checks if the non-crowded areas in cpt.Intent can safely mitigate crowding in A'.
        Strict Safety Invariants:
        1. Destination zones must NOT be in CA (cannot evacuate into a crowded area).
        2. When an explicit physical-edge set is supplied, a direct directed edge must exist;
           blocked edges are always rejected.
        3. Destination state must be present, capacity > 0, and current density below 75%.
        4. When reliable diversion volume is provided, projected occupancy must not exceed
           physical capacity, and projected density must remain strictly below 75%.
        5. When diversion volume is unmeasured/invalid, destination is not quantitatively approved.
        """
        valid_destinations = []
        for d in candidate_destinations:
            # Must not be crowded
            if d in CA_names:
                continue

            # Check capacity & density if state is available
            d_state = zone_states.get(d)
            if not d_state or not isinstance(d_state, dict):
                continue

            # Camera Freshness Guard (Task 7.6.1): Exclude unmonitored zones from new destination recommendations
            if d_state.get("is_monitored") is False:
                continue

            # Physical capacity validation
            d_cap_raw = d_state.get("capacity")
            if d_cap_raw is None or isinstance(d_cap_raw, bool):
                continue
            try:
                d_cap = float(d_cap_raw)
            except (ValueError, TypeError):
                continue
            if not math.isfinite(d_cap) or d_cap <= 0:
                continue

            # Resolve current occupancy and density
            d_curr = None
            if "current_count" in d_state and d_state["current_count"] is not None and not isinstance(d_state["current_count"], bool):
                try:
                    c_val = float(d_state["current_count"])
                    if math.isfinite(c_val) and c_val >= 0:
                        d_curr = c_val
                except (ValueError, TypeError):
                    pass

            d_dens = None
            if "density" in d_state and d_state["density"] is not None and not isinstance(d_state["density"], bool):
                try:
                    dens_val = float(d_state["density"])
                    if math.isfinite(dens_val) and dens_val >= 0:
                        d_dens = dens_val
                except (ValueError, TypeError):
                    pass

            # Derive missing metric if one is available
            if d_curr is None and d_dens is not None:
                d_curr = (d_dens / 100.0) * d_cap
            if d_dens is None and d_curr is not None:
                d_dens = (d_curr / d_cap) * 100.0

            # Missing or invalid occupancy data
            if d_curr is None or d_dens is None:
                continue

            # Current density must be below 75%
            if d_dens >= 75.0:
                continue

            # Quantitative capacity checks when diversion volume is reliably known
            if has_reliable_volume:
                projected_occupancy = d_curr + required_volume
                projected_density = (projected_occupancy / d_cap) * 100.0

                # Reject if projected occupancy exceeds physical capacity
                if projected_occupancy > d_cap:
                    continue

                # Reject if reliably calculated projected density is >= 75%
                if projected_density >= 75.0:
                    continue

            # Verify a real, unblocked direct connection to every crowded source.
            all_sources_connected = True
            for src in A_prime:
                edge = (src, d)
                reverse_edge = (d, src)
                if edge in blocked_edges or reverse_edge in blocked_edges:
                    all_sources_connected = False
                    break
                if allowed_edges is not None and edge not in allowed_edges:
                    all_sources_connected = False
                    break

            if all_sources_connected:
                valid_destinations.append(d)

        if valid_destinations:
            if has_reliable_volume:
                reason = (
                    f"Algorithm 2 Verified Route: Candidate destinations {sorted(valid_destinations)} are unblocked, "
                    f"non-crowded, and have verified capacity headroom for {required_volume:.0f} people from {sorted(list(A_prime))}."
                )
            else:
                reason = (
                    f"Algorithm 2 Candidate Route: Candidate destinations {sorted(valid_destinations)} are unblocked "
                    f"and currently below 75% density, but crowd diversion volume is unmeasured (capacity headroom unverified)."
                )
            return True, valid_destinations, reason
        else:
            return False, [], "No safe unblocked destination in concept intent satisfies capacity or non-crowded constraints."

    def _select_primary_destination(
        self,
        eligible_destinations: List[str],
        working_states: Dict[str, dict],
        required_volume: float = 0.0,
        has_reliable_volume: bool = False
    ) -> Optional[str]:
        """
        Deterministically selects exactly one primary destination from eligible candidates (Task 7.3).
        
        Selection rules:
        1. Prefer a destination that safely accommodates the entire known diversion volume.
        2. Among eligible destinations, prefer the lowest projected density after allocation.
        3. Use a stable destination identifier (name) as the final tie-breaker.
        """
        if not eligible_destinations:
            return None

        def sort_key(d: str) -> Tuple[bool, float, str]:
            d_state = working_states.get(d, {})
            cap = float(d_state.get("capacity", 500)) if isinstance(d_state, dict) else 500.0
            curr = float(d_state.get("current_count", 0)) if isinstance(d_state, dict) else 0.0
            vol = required_volume if has_reliable_volume else 0.0
            proj_occ = curr + vol
            is_unsafe = bool(has_reliable_volume and (proj_occ > cap or (cap > 0 and (proj_occ / cap) * 100.0 >= 75.0)))
            proj_dens = (proj_occ / cap) * 100.0 if cap > 0 else 100.0
            return (is_unsafe, proj_dens, str(d))

        ranked = sorted(eligible_destinations, key=sort_key)
        return ranked[0]

    def generate_crowd_prevention_plan(
        self,
        La: List[Dict],
        CA: List[Dict],
        zone_states: Dict[str, dict] = None,
        blocked_edges: Set[Tuple[str, str]] = None,
        allowed_edges: Optional[Set[Tuple[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Algorithm 2: Generation of Crowd Prevention Plan (Paper IEEE Access 2025, p. 12).
        
        Require: Areas' lattice La, Set CA of crowded areas (from Algorithm 1).
        Ensure: Crowd plan P (list of mitigation subplans with candidate prevention routes).
        
        Safety Invariants:
        1. All outputs are tagged status='pending_human_approval'.
        2. Never automatically executes or claims safety without unblocked physical connectivity.
        3. Never mutates caller-owned zone_states or database records (working copy only).
        4. Selects exactly one safe primary destination per subplan (Task 7.3).
        5. Diversion volume is allocated to only the selected primary destination.
        6. Destinations are rejected if projected count > capacity or projected density >= 75%.
        7. Missing/unreliable diversion volume is tagged is_capacity_verified=False with an explicit warning.
        """
        zone_states = zone_states or {}
        blocked_edges = blocked_edges or set()

        if not La or not CA:
            return {
                "total_crowded_areas": len(CA),
                "resolved_count": 0,
                "unresolved_areas": [c["area"] for c in CA if isinstance(c, dict) and "area" in c],
                "plans": [],
                "status": "idle"
            }

        # Deep-enough copy of zone_states: caller-owned dictionaries must NEVER be mutated
        working_states: Dict[str, dict] = {}
        for z_name, z_data in zone_states.items():
            working_states[z_name] = dict(z_data) if isinstance(z_data, dict) else z_data

        # Map CA by area name
        ca_by_area = {c["area"]: c for c in CA if isinstance(c, dict) and "area" in c}
        CA_names = set(ca_by_area.keys())
        unresolved_CA = set(CA_names)

        # 1. Sort La's concepts in decreasing size of Extent (line 1)
        sorted_la = sorted(La, key=lambda cpt: len(cpt.get("extent", [])), reverse=True)

        # 2. Initialize P = empty set (line 2)
        P: List[Dict[str, Any]] = []

        # 3. Initialize i = 0 (line 3)
        i = 0
        plan_counter = 1

        # 4. while (CA != empty):
        while unresolved_CA and i < len(sorted_la):
            # 5. Set cpt = La[i]
            cpt = sorted_la[i]
            cpt_extent = set(cpt.get("extent", []))
            cpt_intent = set(cpt.get("intent", []))

            # 6. Set A' = CA intersect cpt.Extent
            A_prime = unresolved_CA.intersection(cpt_extent)

            if A_prime and cpt_intent:
                # Resolve diversion volume honestly for A_prime
                has_reliable_vol = True
                total_required_vol = 0.0

                for src in A_prime:
                    src_state = working_states.get(src, {})
                    src_ca = ca_by_area.get(src, {})
                    is_valid, vol = self._resolve_source_diversion_volume(src, src_state, src_ca)
                    if is_valid:
                        total_required_vol += vol
                    else:
                        has_reliable_vol = False
                        total_required_vol = 0.0
                        break

                # 7. if cover(A', cpt.Intent)
                can_cover, safe_dests, cover_reason = self._check_cover(
                    A_prime=A_prime,
                    candidate_destinations=cpt_intent,
                    CA_names=CA_names,
                    zone_states=working_states,
                    blocked_edges=blocked_edges,
                    allowed_edges=allowed_edges,
                    required_volume=total_required_vol,
                    has_reliable_volume=has_reliable_vol
                )

                if can_cover and safe_dests:
                    # Task 7.3: Select exactly ONE primary destination from eligible candidates
                    primary_dest = self._select_primary_destination(
                        eligible_destinations=safe_dests,
                        working_states=working_states,
                        required_volume=total_required_vol,
                        has_reliable_volume=has_reliable_vol
                    )

                    # Revalidate selected primary destination against working_states
                    dest_valid = False
                    if primary_dest:
                        p_state = working_states.get(primary_dest)
                        if p_state and isinstance(p_state, dict):
                            if p_state.get("is_monitored") is False:
                                dest_valid = False
                            else:
                                p_cap = float(p_state.get("capacity", 500))
                                p_curr = float(p_state.get("current_count", 0))
                                if p_cap > 0:
                                    if has_reliable_vol:
                                        proj_occ = p_curr + total_required_vol
                                        proj_dens = (proj_occ / p_cap) * 100.0
                                        dest_valid = (proj_occ <= p_cap and proj_dens < 75.0)
                                    else:
                                        p_dens = float(p_state.get("density", (p_curr / p_cap) * 100.0))
                                        dest_valid = (p_dens < 75.0)

                    if dest_valid and primary_dest:
                        # Update working_states for the selected primary destination only
                        if has_reliable_vol and total_required_vol > 0:
                            p_state = working_states[primary_dest]
                            p_cap = float(p_state.get("capacity", 500))
                            p_curr = float(p_state.get("current_count", 0))
                            new_curr = p_curr + total_required_vol
                            p_state["current_count"] = new_curr
                            if p_cap > 0:
                                p_state["density"] = min(100.0, (new_curr / p_cap) * 100.0)

                        if has_reliable_vol:
                            subplan_reason = (
                                f"Algorithm 2 Verified Route: Primary destination {primary_dest} is unblocked, "
                                f"non-crowded, and has verified capacity headroom for {total_required_vol:.0f} people from {sorted(list(A_prime))}."
                            )
                        else:
                            subplan_reason = (
                                f"Algorithm 2 Candidate Route: Primary destination {primary_dest} is unblocked "
                                f"and currently below 75% density, but crowd diversion volume is unmeasured (capacity headroom unverified)."
                            )

                        subplan = {
                            "plan_id": f"plan-fca-{plan_counter}",
                            "crowded_sources": sorted(list(A_prime)),
                            "recommended_destinations": [primary_dest],
                            "concept_id": cpt.get("id"),
                            "concept_extent": cpt.get("extent", []),
                            "concept_intent": cpt.get("intent", []),
                            "status": "pending_human_approval",
                            "mitigation_capacity": int(working_states.get(primary_dest, {}).get("capacity", 500)),
                            "reason": subplan_reason,
                            "is_verified_evacuation": False,  # Candidate prevention plan, not emergency evacuation
                            "is_capacity_verified": has_reliable_vol,
                            "diversion_volume": total_required_vol if has_reliable_vol else None,
                            "warning": (
                                "Candidate prevention plan requires operational review before executing physical crowd diversion."
                                if has_reliable_vol
                                else "Candidate prevention plan requires operational review. Crowd diversion volume unmeasured; destination capacity headroom cannot be quantitatively verified."
                            )
                        }

                        # 8. Update P = P union (A', primary_dest)
                        P.append(subplan)
                        plan_counter += 1

                        # 9. Update CA = CA - A'
                        unresolved_CA = unresolved_CA - A_prime
                    else:
                        # Revalidation failed; increment i to try next concept
                        i += 1
                else:
                    # 11. Increment i = i + 1
                    i += 1
            else:
                i += 1

        return {
            "total_crowded_areas": len(CA_names),
            "resolved_count": len(CA_names) - len(unresolved_CA),
            "unresolved_areas": sorted(list(unresolved_CA)),
            "plans": P,
            "status": "complete" if not unresolved_CA else "partial",
            "working_zone_states": working_states
        }

    # =========================================================================
    # BACKWARD COMPATIBILITY LAYER (Preserves all existing callers)
    # =========================================================================

    def build_formal_context(
        self,
        cameras: List[dict],
        alerts: List[dict],
        zones: List[dict] = None
    ) -> Tuple[List[str], Dict[str, Set[str]]]:
        """
        Legacy binary formal context builder. Kept for full backward compatibility
        with existing tests and API callers.
        """
        objects = []
        relation: Dict[str, Set[str]] = {}

        zone_map: Dict[str, dict] = {}
        if zones:
            for z in zones:
                z_name = z.get("name", "Zone")
                if z_name not in objects:
                    objects.append(z_name)
                    relation[z_name] = set()
                    zone_map[z_name] = z
                    z_dens = z.get("density", 0.0)
                    if z_dens >= 90.0:
                        relation[z_name].add("CriticalDensity")
                        relation[z_name].add("HighDensity")
                    elif z_dens >= 75.0:
                        relation[z_name].add("HighDensity")

        for cam in cameras:
            loc_name = cam.get("location") or cam.get("name") or "Area"
            if loc_name not in relation:
                objects.append(loc_name)
                relation[loc_name] = set()

            dens = cam.get("density", 0.0)
            if dens >= 90.0:
                relation[loc_name].add("CriticalDensity")
                relation[loc_name].add("HighDensity")
            elif dens >= 75.0:
                relation[loc_name].add("HighDensity")

            flow = cam.get("flow_rate", 0.0)
            if dens >= 70.0 and flow >= 3.0:
                relation[loc_name].add("CrowdSurge")

            if "gate" in loc_name.lower() and dens >= 65.0:
                relation[loc_name].add("GateCongestion")

        for alert in alerts:
            if not alert.get("resolved", False):
                zone_or_cam = alert.get("zone") or alert.get("camera") or ""
                matched_obj = None
                for obj in objects:
                    if obj.lower() in zone_or_cam.lower() or zone_or_cam.lower() in obj.lower():
                        matched_obj = obj
                        break
                if not matched_obj and objects:
                    matched_obj = objects[0]

                if matched_obj:
                    title = alert.get("title", "").lower() + " " + alert.get("description", "").lower()
                    if "child" in title:
                        relation[matched_obj].add("ChildSeparated")
                    if "exit" in title or "block" in title or "egress" in title:
                        relation[matched_obj].add("ExitBlocked")
                    if "intrusion" in title or "restricted" in title or "breach" in title:
                        relation[matched_obj].add("RestrictedIntrusion")
                    if "surge" in title or "stampede" in title:
                        relation[matched_obj].add("CrowdSurge")
                        relation[matched_obj].add("CriticalDensity")

        if not objects:
            objects = ["Main Arena Sector", "North Gate Turnstiles"]
            relation["Main Arena Sector"] = set()
            relation["North Gate Turnstiles"] = set()

        return objects, relation

    def derive_formal_concepts(self, objects: List[str], relation: Dict[str, Set[str]]) -> List[Dict]:
        """
        Legacy concept derivation caller. Uses the mathematically closed concept generator
        to ensure mathematically sound concepts without breaking legacy return formats.
        """
        # Determine all attributes in context
        all_attrs: Set[str] = set()
        for s in relation.values():
            all_attrs.update(s)
        return self.derive_closed_concepts(objects, relation, sorted(list(all_attrs)))

    def _determine_action_for_intent(self, intent: List[str], extent: List[str]) -> str:
        intent_set = set(intent)
        zones_str = ", ".join(extent[:2]) if extent else "monitored perimeter"

        if "CriticalDensity" in intent_set and "ExitBlocked" in intent_set:
            return f"CRITICAL FCA DIRECTIVE: Evacuation hazard at {zones_str}. Open secondary emergency exits and redirect queue."
        elif "CriticalDensity" in intent_set:
            return f"HIGH FCA DIRECTIVE: Extreme crowd pressure at {zones_str}. Restrict incoming turnstiles and deploy safety barrier squad."
        elif "GateCongestion" in intent_set:
            return f"FCA DIRECTIVE: Turnstile bottleneck at {zones_str}. Open alternate entry lanes and broadcast audio guidance."
        elif "RestrictedIntrusion" in intent_set:
            return f"SECURITY DIRECTIVE: Perimeter breach verified at {zones_str}. Dispatch nearest on-duty security guard."
        elif "ChildSeparated" in intent_set:
            return f"SAFETY DIRECTIVE: Minor separation alert at {zones_str}. Alert floor marshal and public address desk."
        elif "HighDensity" in intent_set:
            return f"OPERATIONAL DIRECTIVE: High density accumulation at {zones_str}. Position crowd marshals for queue spacing."
        # Research attribute actions (D, P, M, E, S)
        elif "D" in intent_set and "E" in intent_set:
            return f"CRITICAL FCA ACTION: High density combined with emergency condition at {zones_str}. Prepare smart diversion plan."
        elif "D" in intent_set and "M" in intent_set:
            return f"HIGH FCA ACTION: Dynamic crowd surge and rapid accumulation at {zones_str}. Modulate queue throughput."
        elif "D" in intent_set:
            return f"FCA ACTION: High density detected at {zones_str}. Consult crowd prevention plan."
        else:
            return f"STANDARD SURVEILLANCE: Normal flow across {zones_str}. Maintain automated AI computer vision monitoring."

    def generate_recommendations_from_fca(self, concepts: List[Dict], event_id: Optional[str] = None) -> List[Dict]:
        """
        Generates prioritized recommendations from derived concepts. All recommendations
        strictly remain status='pending' requiring human operator authorization.
        """
        recs = []
        rec_id = 1
        prefix = f"rec-fca-{event_id}" if event_id else "rec-fca"

        for concept in concepts:
            intent = set(concept.get("intent", []))
            extent = concept.get("extent", [])

            if "CriticalDensity" in intent and "ExitBlocked" in intent:
                for zone in extent:
                    recs.append({
                        "id": f"{prefix}-{rec_id}",
                        "event_id": event_id,
                        "title": f"Open Auxiliary Exit Paths & Divert Crowd at {zone}",
                        "priority": "high",
                        "reason": f"FCA Galois Derivation: Extent={extent} satisfies Intent={{CriticalDensity, ExitBlocked}}. Immediate evacuation protocol required.",
                        "confidence": 98,
                        "zone": zone,
                        "officer": "On-Duty Command Dispatch",
                        "status": "pending"
                    })
                    rec_id += 1
            elif "GateCongestion" in intent:
                for zone in extent:
                    recs.append({
                        "id": f"{prefix}-{rec_id}",
                        "event_id": event_id,
                        "title": f"Open Auxiliary Turnstiles & Deploy Staging Line at {zone}",
                        "priority": "high",
                        "reason": f"FCA Galois Derivation: Extent={extent} satisfies Intent={{GateCongestion}}. Gate throughput constrained.",
                        "confidence": 94,
                        "zone": zone,
                        "officer": "Gate Supervisor Unit",
                        "status": "pending"
                    })
                    rec_id += 1
            elif "HighDensity" in intent or ("D" in intent and "M" in intent):
                for zone in extent:
                    recs.append({
                        "id": f"{prefix}-{rec_id}",
                        "event_id": event_id,
                        "title": f"Deploy Security Rapid Squad to {zone}",
                        "priority": "high",
                        "reason": f"FCA Galois Derivation: Extent={extent} satisfies Intent={sorted(list(intent))}. Physical queue management needed.",
                        "confidence": 92,
                        "zone": zone,
                        "officer": "On-Duty Security Dispatch",
                        "status": "pending"
                    })
                    rec_id += 1
            elif "ChildSeparated" in intent:
                for zone in extent:
                    recs.append({
                        "id": f"{prefix}-{rec_id}",
                        "event_id": event_id,
                        "title": f"Broadcast Minor Separation Alert in {zone}",
                        "priority": "medium",
                        "reason": f"FCA Galois Derivation: Extent={extent} satisfies Intent={{ChildSeparated}}. Dispatch floor marshal.",
                        "confidence": 89,
                        "zone": zone,
                        "officer": "Floor Marshal Duty Desk",
                        "status": "pending"
                    })
                    rec_id += 1
            elif "RestrictedIntrusion" in intent:
                for zone in extent:
                    recs.append({
                        "id": f"{prefix}-{rec_id}",
                        "event_id": event_id,
                        "title": f"Investigate Perimeter Breach in {zone}",
                        "priority": "high",
                        "reason": f"FCA Galois Derivation: Extent={extent} satisfies Intent={{RestrictedIntrusion}}. Check access control logs.",
                        "confidence": 95,
                        "zone": zone,
                        "officer": "Rapid Response Security Squad",
                        "status": "pending"
                    })
                    rec_id += 1

        return recs


# Global singleton instance
fca_solver = FCAEngine()

# BASE PAPER COMPONENT MAPPING
## "A Synergy Between Machine Learning and Formal Concept Analysis for Crowd Detection" — IEEE Access, 2025

**Authors:** Anas M. Al-Oraiqat, Oleksandr Drieiev, Sattam Almatarneh, Mohammadnoor Injadat, Karim A. Al-Oraiqat, Hanna Drieieva, Yassin M. Y. Hasan  
**Digital Object Identifier:** 10.1109/ACCESS.2025.3545559  
**Status Audit Date:** October 2026

---

### Detailed Component Mapping Table

| Paper requirement | Algorithm/definition | Code file and function | Test evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Area Formal Context $K^a$** | Definition 4 ($K^a = (A, A, R)$ where $R$ models direct physical inter-area connectivity, excluding blocked passages) | `backend/app/ai/fca_engine.py`: `FCAEngine.build_area_context()` | `test_fca_research.py::test_area_context_and_blocked_corridors` | Implemented and tested |
| **Fuzzy Crowd Formal Context $K^c$** | Definition 5 ($K^c = (A, F, R)$ where $F=\{D, P, M, E, S\}$ with fuzzy truth degrees $[0, 1]$) | `backend/app/ai/fca_engine.py`: `FCAEngine.build_fuzzy_crowd_context()` | `test_fca_research.py::test_fuzzy_crowd_context_creation` | Implemented and tested |
| **Formal Concept Derivation & Closure** | Definitions 2 & 3 (Galois derivation: $A'=\{m \mid \forall g \in A, gIm\}$, $B'=\{g \mid \forall m \in B, gIm\}$, $E'=I, I'=E$) | `backend/app/ai/fca_engine.py`: `FCAEngine.derive_closed_concepts()`, `galois_extent()`, `galois_intent()` | `test_fca_research.py::test_galois_closure_and_uniqueness` | Implemented and tested |
| **Concept Lattice Construction ($L^c$ and $L^a$)** | Definitions 6 & 7 (Complete lattice DAG with transitive reduction covering relation and layer stratification) | `backend/app/ai/fca_engine.py`: `FCAEngine.build_lattice_graph()` | `test_fca_research.py::test_lattice_covering_relation_and_acyclicity` | Implemented and tested |
| **Algorithm 1: Extraction of Crowded Areas** | Algorithm 1 (Sort $L^c$ decreasing by $|Intent|$, check $c = \text{checkCrowd}(K^c[a], cpt.Intent) > T=0.7$, filter low-crowd areas) | `backend/app/ai/fca_engine.py`: `FCAEngine.extract_crowded_areas()`, `check_crowd()` | `test_fca_research.py::test_algorithm_1_crowded_areas_extraction`, `test_research_integration.py::test_get_crowded_areas_algorithm_1` | Implemented and tested |
| **Area Physical Connectivity Model** | Physical graph nodes (zones) and passages (edges with blocked status and flow capacity) | `backend/app/models.py`: `ZoneConnectionModel`; `backend/app/routers/venue_map.py` | `test_research_integration.py::test_zone_connections_crud_lifecycle` | CRUD and explicit connectivity implemented; missing topology is not fabricated |
| **Algorithm 2: Crowd Prevention Plan Generation** | Algorithm 2 (Sort $L^a$ decreasing by $|Extent|$, candidate mitigation $A'=CA \cap cpt.Extent$, evaluate `cover(A', cpt.Intent)`) | `backend/app/ai/fca_engine.py`: `FCAEngine.generate_crowd_prevention_plan()`, `_check_cover()` | `test_fca_research.py::test_algorithm_2_plan_generation_and_safety`, `test_research_integration.py::test_get_prevention_plans_algorithm_2` | Implemented and tested |
| **Motion Vectors & Flow Decomposition** | Equations (2) & (3) ($X^-, X^+, Y^-, Y^+$ directional components normalized by velocity magnitude) | `backend/app/ai/detector.py`: `TemporalPersonTracker.compute_flow_metrics()` | `test_movement_tracking.py::test_flow_vector_equations_horizontal`, `test_flow_vector_equations_vertical` | Implemented and tested |
| **Inflow & Outflow Rate** | Equations (4) & (5) ($\lambda_{out} = X^+ + X^- + Y^+ + Y^-$, $\lambda_{in}$ aggregation) | `backend/app/ai/detector.py`: `TemporalPersonTracker.compute_flow_metrics()`; `backend/app/ai/stream_processor.py` | `test_movement_tracking.py::test_outflow_rate_lambda_out` | Implemented and tested |
| **Physical Speed vs Pixel Displacement** | Conversion using perspective calibration factor (`meters_per_pixel`) to physical meters/sec | `backend/app/ai/detector.py` & `backend/app/routers/analytics.py` | `test_movement_tracking.py::test_speed_calibration_physical_units` | Implemented and tested |
| **Tracking Consistency & State Isolation** | Temporal tracking with bounded prediction age (6 frames), isolated tracker per camera worker, sliding-window unique count | `backend/app/ai/detector.py`: `TemporalPersonTracker`; `backend/app/ai/stream_processor.py` | `test_movement_tracking.py::test_tracking_id_persistence_across_frames`, `test_camera_tracking_isolation`, `test_unique_sliding_window_counting` | Implemented and tested |
| **Human Approval & Route Safety Verification** | Prevention plans remain pending human operator authorization; unverified or blocked routes rejected | `backend/app/routers/recommendations.py`; `backend/app/ai/fca_engine.py` | `test_fca_research.py::test_algorithm_2_plan_generation_and_safety` | Implemented and tested |
| **U-Net Thermal Person Detection (Paper Section VI-A)** | U-Net architecture specifically trained on thermal/infrared imagery [18] | `backend/app/ai/detector.py` (Ultralytics YOLOv8n + OpenCV fallback) | Unit tests run on standard RGB/CCTV streams | Partially implemented (system uses standard RGB YOLOv8/OpenCV detector; U-Net thermal weights are proprietary to [18] and not provided in repository) |


## Fidelity and verification notes (updated 2026-10-22)

- The paper's binary Galois derivation is implemented over a thresholded incidence relation for lattice construction. The continuous fuzzy scores in `Kc` are project-side membership estimates; they are not themselves a fuzzy-Galois derivation.
- `check_crowd()` currently uses a project-defined weighted aggregation because the paper's pseudocode names `checkCrowd` without specifying a complete numeric formula. Do not describe that aggregation as the paper's exact formula.
- The production prevention-plan route check now requires an explicit, configured, unblocked edge and a known destination density/capacity. Empty topology is not replaced with a synthetic chain. Missing topology/state means no verified candidate is returned.
- The repository's tests are algorithmic/integration checks; they do not prove equivalence to the paper's trained thermal U-Net. This project uses YOLO/OpenCV alternatives and requires separate runtime validation with the actual installed model, camera sources, and database configuration.

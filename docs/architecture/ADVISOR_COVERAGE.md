# Advisor coverage matrix — the read-only domain advisor fleet

> The 11 domain advisors are the main surface of the **read-only advisor** role class
> (see `AGENT_ROLES.md`). Each is a single-responsibility checker that receives **dict
> copies** of case artifacts and emits **advisory `Findings`** — it never mutates a case,
> never gates a verdict. All are loaded at module top via `_load_advisor()` and dispatched
> inside `assemble_stack()`.
>
> Source: `ui/backend/services/advisor_stack.py`. Verified read-only audit 2026-06-06:
> **all 11 are production-dispatched — none is fixture-only.**

| # | Advisor | Domain | Defect class | What it checks | Wiring |
|---|---|---|---|---|---|
| 1 | `face_orientation_advisor` | geometry | A4 | surface-normal orientation deviation | production-dispatched (L698–710) |
| 2 | `inlet_outlet_validator` | boundary | A5 | inlet/outlet emission / role protocol (V81) | production-dispatched (L712–723) |
| 3 | `bc_type_name_validity_advisor` | boundary | D10 | invalid OpenFOAM BC type names | production-dispatched (L738–75x) |
| 4 | `virtual_interface_detector` | geometry | A2-v2 | virtual/unmatched interfaces, should-have-been-shared | production-dispatched (L755–767) |
| 5 | `shm_dict_validator` | mesh | A8 | snappyHexMesh dict validity (V99 widening) | production-dispatched (L769–787) |
| 6 | `stl_face_label_validator` | mesh | D11 | STL face-label consistency across 3 paths | production-dispatched (L801–827) |
| 7 | `extra_body_advisor` | geometry | D6 | extra/debris bodies inside fluid region | production-dispatched (L859–879) |
| 8 | `thermo_polynomial_range_advisor` | thermo | A10 | JANAF/cp polynomial validity range | production-dispatched (L881–896) |
| 9 | `unit_detector` | geometry | — | STEP unit inference (MM/M/UNKNOWN) from header + bbox | production-dispatched (L898–915) |
| 10 | `solver_block_advisor` | solver | — | fvSolution/control solver-block validity | production-dispatched (L923–939) |
| 11 | `thin_wall_advisor` | mesh | — | thin-wall patches at risk of under-resolution | production-dispatched (L941–963) |

**Coverage by domain**: geometry 5 · mesh 3 · boundary 2 · solver 1 · thermo 1.

**Honesty notes**
- Every advisor is read-only by contract: the `advisor_stack` docstring four-question gate
  asserts "LLM offline OK (no anthropic/openai/corpus dependency)" and "AI advisory only —
  never calls anything that mutates a case directory".
- This matrix is descriptive (read-only audit), not a gate. If an advisor is added/removed,
  update this table; consider a round-trip test asserting the table matches the dispatch list
  (roadmap P2, `.demo/AGENT_SYSTEM_MAP.md` §5).
- An internal `advisor_stack.py` docstring still says "8 geometry_ingest advisors" — stale vs
  the verified 11 dispatched. Doc-only drift; flagged for a future cleanup commit.

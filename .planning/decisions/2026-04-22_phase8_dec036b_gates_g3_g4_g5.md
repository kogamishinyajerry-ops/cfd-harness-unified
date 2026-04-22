---
decision_id: DEC-V61-036b
timestamp: 2026-04-22T11:00 local
scope: |
  Phase 8 Sprint 1 — Hard comparator gates G3/G4/G5 bundled. Sibling DEC
  to DEC-V61-036 (G1 landed). Closes the "honest label, bad physics"
  PASS-washing flavor that G1 did not cover:
    - G3 velocity_overflow: |U|_max > 100·U_ref in last VTK (catches BFS
      U≈1e20, TFP U≈1.1e4).
    - G4 turbulence_negativity: k/epsilon/omega min < 0 at last solver
      iteration OR field max grossly above sanity scale (catches BFS
      epsilon max=1.03e+30, k min=-6.41e+30).
    - G5 continuity_divergence: |sum_local| > 1e-2 OR |cumulative| > 1.0
      (catches BFS sum_local=5.24e+18, cumulative=-1434.64).
  Per Codex round 1 (DEC-V61-036 review) these 3 gates share log-parse +
  VTK-read infrastructure and bundle cleanly. G2 (unit/profile), G6
  (stuck residuals), DEC-V61-038 (attestor) land separately.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: pending (pre-merge required; self-pass-rate ≤ 0.70)
codex_rounds: 0
codex_verdict: pending
codex_tool_report_path: []
counter_status: |
  v6.1 autonomous_governance counter 22 → 23 (DEC-V61-036a G1) → 24
  (DEC-V61-036b G3/G4/G5). Next retro at counter=30.
reversibility: |
  Fully reversible. New module src/comparator_gates.py + integration
  calls in phase5_audit_run.py + concern types in _derive_contract_status.
  Revert = 4 files restored. No fixture regeneration required because
  the gates operate on reports/phase5_fields/* and log.simpleFoam which
  are themselves reproducible artifacts.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
github_merge_sha: pending
github_merge_method: pre-merge Codex verdict required
external_gate_self_estimated_pass_rate: 0.60
  (Three new gates + new module + fixture-writer integration + concern
  schema extension. Threshold calibration is the main risk surface — too
  tight flips LDC to FAIL spuriously; too loose misses the blowups.
  Codex round 1 physics audit on DEC-036 provides ground-truth: gates
  MUST fire on BFS/duct/TFP/cylinder and MUST NOT fire on LDC.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-036 (G1 landed a9d0831 + b3ed913).
  - Codex round-1 CFD physics audit on DEC-V61-036 (2026-04-22):
    BFS + duct + TFP + cylinder fields catastrophic; needs G3+G4+G5.
  - RETRO-V61-001 cadence: gate bundling is OK if each gate has its own
    assertion + test, which this DEC honors.
---

# DEC-V61-036b: Gates G3 + G4 + G5

## Evidence (from Codex round-1 BFS log dump)

```
time step continuity errors : sum local = 5.24523e+18, global = -1328.63, cumulative = -1434.64
bounding epsilon, min: 7.38706e-17 max: 1.03929e+30 average: 1.37234e+27
bounding k, min: -6.41351e+30 max: 2.32895e+31 average: 1.39855e+29
```

BFS simpleFoam kEpsilon ran to `simpleFoam` exit=0 with continuity blown
up by 18 orders of magnitude and k/ε field magnitudes in the 1e+30 range.
Current harness prints "solver completed" and the comparator finds a
`reattachment_length` fallback = 0.04415 ≈ 0 against the gold 6.26, which
G1 now catches. But if a future regression emits `reattachment_length=6.26`
with the same field blowup (e.g., a hardcoded canonical value like
cylinder_wake's Strouhal at `foam_agent_adapter.py:7956`), G1 misses it.
G3/G4/G5 are the defense-in-depth layer.

## Gate definitions

### G3 velocity_overflow
- **Trigger**: `max(|U|)` over final-time VTK cell centres exceeds
  `K * U_ref` (K=100 default, per-case override in future).
- **U_ref**: resolved from `task_spec.boundary_conditions` (inlet U for
  internal, lid U for LDC, free-stream for external). When unresolvable,
  default 1.0 m/s and emit a WARN marker.
- **Fallback when VTK unavailable**: parse epsilon max from
  `bounding epsilon, min: X max: Y` log line at last iter. If Y > 1e+10,
  treat as proxy evidence of velocity overflow since ε ~ u³/L implies
  u ~ ε^(1/3) L^(1/3), and ε=1e+10 with L=O(1) means u=O(1e+3).
- **Decision**: FAIL (not WARN) — a solver that exits 0 with |U| > 100·U_ref
  is not physical.
- **Concern code**: `VELOCITY_OVERFLOW`

### G4 turbulence_negativity
- **Trigger**: any of k, epsilon, omega has a negative minimum at the
  **last reported** `bounding X, min: ..., max: ...` line in the log.
  Silent-clipping during early iters is OK (solver-internal bounding),
  but final-iteration negative values indicate an inconsistent state.
- **Additional trigger**: field max > 1e+10 for k or epsilon (sanity
  overflow, catches BFS case where positive values rocket without ever
  going negative at last iter).
- **Decision**: FAIL.
- **Concern code**: `TURBULENCE_NEGATIVE`

### G5 continuity_divergence
- **Trigger**: last-iteration `sum local` > 1e-2 OR `|cumulative|` > 1.0.
- **Rationale**: for steady incompressible SIMPLE/PISO, sum_local should
  decay to 1e-5 or better at convergence. sum_local=1e-2 already indicates
  the pressure-velocity coupling is broken; `|cumulative|>1.0` is a hard
  divergence signal.
- **Decision**: FAIL.
- **Concern code**: `CONTINUITY_DIVERGED`

## Implementation outline

### New module `src/comparator_gates.py` (~250 LOC)
```python
@dataclass
class GateViolation:
    gate_id: Literal["G3", "G4", "G5"]
    concern_type: str   # VELOCITY_OVERFLOW / TURBULENCE_NEGATIVE / CONTINUITY_DIVERGED
    summary: str
    detail: str
    evidence: dict      # threshold, observed, etc

def parse_solver_log(log_path: Path) -> LogStats:
    """Regex-extract final bounding lines, continuity line, FOAM FATAL
    detection, residual history."""

def read_final_velocity_max(vtk_dir: Path) -> float | None:
    """pyvista read of latest-time VTK; returns max |U| or None if
    unavailable (handled as WARN, not FAIL)."""

def check_all_gates(
    log_path: Path | None,
    vtk_dir: Path | None,
    U_ref: float,
) -> list[GateViolation]:
    violations = []
    log = parse_solver_log(log_path) if log_path and log_path.is_file() else None
    violations.extend(_check_g3_velocity_overflow(log, vtk_dir, U_ref))
    violations.extend(_check_g4_turbulence_negativity(log))
    violations.extend(_check_g5_continuity_divergence(log))
    return violations
```

### Integration at fixture-write time
`scripts/phase5_audit_run.py::_audit_fixture_doc` calls
`check_all_gates(log_path, vtk_dir, U_ref)` after G1 extraction and
stamps each violation as an `audit_concerns[]` entry.

### Verdict engine
`ui/backend/services/validation_report.py::_derive_contract_status`
extends its G1 hard-FAIL concern set to include `VELOCITY_OVERFLOW`,
`TURBULENCE_NEGATIVE`, `CONTINUITY_DIVERGED`.

## Backward compat — expected gate outcomes on current 10 fixtures

| case | G3 | G4 | G5 | current status | post-G1+G345 status |
|---|---|---|---|---|---|
| lid_driven_cavity | pass (|U|≈1.0) | skip (laminar) | pass (sum_local≈1e-6) | FAIL (6 profile pts) | FAIL (G1 ok; profile fails) |
| backward_facing_step | FAIL (ε max=1e+30) | FAIL (k min=-6e+30) | FAIL (cum=-1434) | FAIL via G1 | FAIL via G1+G3+G4+G5 (defense) |
| circular_cylinder_wake | FAIL (Co≈5.9) | FAIL | FAIL (cum≈15.5) | FAIL via G1 | FAIL via G1+G3/4/5 |
| turbulent_flat_plate | FAIL (U≈1.1e4) | FAIL (k≈2e8) | likely FAIL | FAIL (comparator) | FAIL (ditto) |
| duct_flow | FAIL | FAIL | FAIL | FAIL via G1 | FAIL via G1+G3/4/5 |
| differential_heated_cavity | pass (small U) | skip | pass | FAIL (+29%) | FAIL (unchanged) |
| plane_channel_flow | pass | FAIL? | pass? | FAIL via G1 | FAIL via G1 (+ maybe G4) |
| impinging_jet | check | check | depends on stuck res | FAIL (honest label) | FAIL; DEC-038 catches stuck res |
| naca0012_airfoil | pass | pass? | pass | FAIL (3 Cp pts) | FAIL (unchanged) |
| rayleigh_benard_convection | pass | skip | pass | FAIL (Nu+151%) | FAIL (unchanged) |

LDC must stay clean — critical backward-compat assertion.

## Tests

`ui/backend/tests/test_comparator_gates.py` (new):
- `test_g3_velocity_overflow_fail_synthetic_vtk` — crafted VTK with U=500, U_ref=1 → FAIL
- `test_g4_turbulence_negative_at_last_iter_fail` — log with final `bounding k, min: -5.0` → FAIL
- `test_g4_turbulence_max_overflow_fail` — log with `bounding epsilon, min: 1e-5, max: 1e+30` → FAIL
- `test_g5_sum_local_above_1e-2_fail` — log with `sum local = 0.5` → FAIL
- `test_g5_cumulative_above_1_fail` — log with `cumulative = -1434.64` → FAIL
- `test_gates_bfs_integration` — reads the real BFS audit log → 3 violations (G3 proxy + G4 + G5)
- `test_gates_ldc_no_fire` — reads a synthetic clean log → 0 violations
- `test_validation_report_fails_on_gate_concern` — fixture with VELOCITY_OVERFLOW concern → contract_status FAIL

## Counter + Codex

23 → 24. Pre-merge Codex review required (self-pass 0.60).

## Related
- DEC-V61-036 G1 (a9d0831 + b3ed913) — upstream; G1 + G3/4/5 compose AND-gated
- DEC-V61-038 (attestor) — complementary; A1-A6 run pre-extraction, G3/4/5 run post-extraction
- Codex round-1 physics audit on DEC-V61-036 — evidence source

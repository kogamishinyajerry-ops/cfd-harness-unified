---
decision_id: DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2
title: case_006 ONERA M6 substrate iteration 2 · solver_block_advisor LANDED (V27+V28) · V-row capture 3/9 → 5/9 firm
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 1 · M-V64A-CASE-006-SUBSTRATE-V2 (V63-A close DEC §8 carry-over #6)
notion_sync_status: synced 2026-05-15 (https://www.notion.so/361c68942bed81539184f80e396436b2)
confidence: med
---

## Status

Accepted (autonomous_governance: true; counter +1). Sub-DEC scope under
existing V64-A charter (`DEC-V64-A-charter` Accepted 2026-05-15):

- 1 new advisor module (`solver_block_advisor.py`, ~165 LOC) under
  `ui/backend/services/geometry_ingest/`
- 4 atomic insertions into `ui/backend/services/advisor_stack.py` (~40
  LOC additions · zero deletions · zero modifications to existing
  dispatch behavior)
- 1 new substrate-input file (`solver_block_inputs.yaml`, ~50 LOC) under
  `case_006/inputs/` — historical pre-fix snapshot derived verbatim
  from V27 + V28 corpus entries
- 1 new verification runner (`scripts/v64_case_006_substrate_v2/`,
  ~140 LOC) mirroring B42's `run_extended.py` pattern
- 1 new test module (`test_solver_block_advisor.py`, 10 tests)
- This DEC + accompanying retro
  (`.planning/retrospectives/2026-05-15_case_006_substrate_extension_v2.md`)

Backward compatibility preserved: B42's three input files
(`thin_wall_inputs.yaml`, `interface_bodies.json`, `interface_specs.json`)
remain in place and continue to drive the B42-LANDED advisors. v1 retro
§4.4 "Diff diagonal" measurements (advisor_count=8, finding_count=12,
critical_count=12, evidence_refs=20) reproduce byte-identically on
re-running B42's `run_extended.py`.

## Goal

Close V63-A close DEC §8 carry-over #6 (verbatim from V63-A close DEC
§8 row 6 · `2026-05-15_v63_close_dec.md`):

> | 6 | case_006 V-row 3/9 → 6+/9 (V26-V28/V31/V32 + D4 uncovered) |
> | M-CASE-006-SUBSTRATE sub-DEC | V64-A Tier 1: **M-V64A-CASE-006-SUBSTRATE-V2** |

V64-A Done dimension #6 advance (verbatim from V64-A charter):

> **≥ 1 case 拿到 ≥7/9 · ≥2 cases 拿到 ≥5/9 · 不准 alias 灌水**

This sub-DEC pushes case_006 specifically from **3/9 firm (B42 V63-A)** to
**5/9 firm**. Combined with case_011 (7/9 over-met · V63-A) and case_004
(5/9 · V63-A), the V64-A "≥2 cases ≥5/9" clause is now over-met **3 / 2**.

## Scope

### In-scope (LANDED in this sub-DEC)

1. **New advisor module** — `solver_block_advisor` (#11 LANDED advisor)
   covers two rules:
   - R1 (V27): rhoCentralFoam / rhoCentralDyMFoam without
     `adjustTimeStep yes` → critical
   - R2 (V28): same density-based-symmetric solver class with DILU /
     FDILU preconditioner on the symmetric matrix path → critical (one
     finding per field)

   Pure-function design (no I/O · no LLM · no FreeCAD dependency).
   Frozen dataclasses (`SolverBlockSnapshot`, `SolverBlockFinding`,
   `SolverBlockReport`) — V130 advisory-only contract.

2. **Stack integration** — `advisor_stack.py`:
   - `_load_advisor("solver_block_advisor")` registration at L172
   - `_V_ROWS_PER_ADVISOR["solver_block_advisor"] = ("V27", "V28")`
   - `_normalize_solver_block(report) → tuple[Finding, ...]` helper
   - `assemble_stack(..., solver_block_snapshot: SolverBlockSnapshot |
     None = None, ...)` kwarg + dispatch block

3. **case_006 substrate v2 input** —
   `~/Desktop/case_006_onera_m6_transonic/inputs/solver_block_inputs.yaml`:
   ```yaml
   solver: rhoCentralFoam
   adjust_time_step: false   # V27 trigger
   delta_t: 1.0              # V27 context: ~20,000× too large
   preconditioners:           # V28 trigger: case_005 rhoSimpleFoam inheritance pre-fix
     U: DILU
     e: DILU
     k: DILU
     omega: DILU
   ```
   With `_meta` provenance block citing V27 + V28 corpus entries as
   verbatim source.

4. **V64-A v2 verification runner** —
   `scripts/v64_case_006_substrate_v2/run_extended_v2.py`. Loads B42's
   v1 inputs (via import) PLUS the new
   `solver_block_inputs.yaml`. Writes `stack_report_python_extended_v2.json`.
   4Q-Q1 LLM-offline gate enforced via `os.environ.pop(...)` at module
   import time + outer `env -i HOME PATH .venv/bin/python` invocation.

5. **Tests** — `test_solver_block_advisor.py` (10 tests, all green):
   B55 case_006 pre-fix snapshot · adjustTimeStep yes/None branches ·
   valid symmetric preconditioner suppression · FDILU asymmetric flag ·
   non-density-based solver silence · rhoCentralDyMFoam dynamic-mesh
   variant dispatch · canonical S15-compliant config silence · 2 frozen-
   dataclass mutation tests.

### V-row selection decision (B55 SURFACE outcome)

Brief originally proposed substrate-only iteration on V26-V32 + D4
(carry-over #6 plan-file scope). Main-session SURFACE turn (per CLAUDE.md
v2.3 "advisor-not-driver" + "find stack-actionable or surface to user"
discipline) verified that **no V-row in {V26 / V27 / V28 / V31 / V32 / D4}
was substrate-actionable on the existing 10-advisor stack**:

- V26 / V31 / V32 require new advisor modules (codex_output_validator /
  codex_protocol_validator / infra workaround documentation), not
  substrate inputs.
- V27 / V28 do not appear in any LANDED advisor's `_V_ROWS_PER_ADVISOR`
  tuple → substrate-only addition would not produce a stack finding.
- D4 already marginal-fires per B42 §5 via thin_wall_advisor; promotion
  to firm requires `geometry_surgery.decimate_to_tier` (canonical per
  defect_manifest) to be wrapped as a finding-emitting advisor — not
  substrate work.

User chose **option C** ("land a new advisor"). Cheapest path producing
the required ≥2 firm-capture gain = `solver_block_advisor` covering V27 +
V28 (pure-config validation, no CAD parsing, single substrate input,
tabular rule logic, forward-compatible with V53 rhoPimpleFoam-transonic
inverse pattern under the same table-driven approach).

### Out-of-scope (explicitly deferred · sub-DEC queue)

1. `codex_output_validator` for V26 + V31 (would push case_006 to 7/9
   firm; needs canonical CAD-formula registry + defect→advisor mapping
   table; new sub-DEC required)
2. D4 marginal → firm via V31 protocol-revision ratification (B42 §5
   classification semantics preserved for cross-retro consistency;
   decision deferred to a future ratification turn)
3. `solver_block_advisor` forward-extension to V53 (rhoPimpleFoam +
   transonic-yes inverse pattern: PCG/DIC on the asymmetric p matrix);
   table-driven design admits but rule addition out of B55 scope; case_016
   substrate v2 is the natural home
4. case_dir CAD / STL / parts_manifest / defect_manifest mutations
   (substrate-only scope; preserves B42 reproducibility)
5. ARC-GOAL.md update (B55 + B56 parallel; main session reconciles to
   avoid rebase contention)
6. Notion sync (Status=Accepted but session-end batch per CLAUDE.md v2.3
   "Notion 仅 sync Status=Accepted")

## V1→V2 substrate diff

| dimension | V63-A v1 (B42) | V64-A v2 (B55) | delta |
|---|---|---|---|
| substrate-input files | 3 | 4 | +1 (`solver_block_inputs.yaml`) |
| LANDED advisors stack-wide | 10 | 11 | +1 (`solver_block_advisor`) |
| `_V_ROWS_PER_ADVISOR` keys | 10 | 11 | +1 |
| V-row coverage stack-wide | 22 V-rows | 24 V-rows | +V27 +V28 |
| `assemble_stack` kwargs | 16 | 17 | +1 (`solver_block_snapshot`) |
| advisor module LOC | 0 added | ~165 added | +165 (single file) |
| stack-side LOC | 0 added | ~40 added | additive only |
| tests | 73 (existing) | 83 (10 new) | +10 |

## Stack pre/post evidence

(Verbatim from
`scripts/v64_case_006_substrate_v2/stack_report_python_extended_v2.json`;
re-runnable byte-identically under
`env -i HOME PATH .venv/bin/python -m
scripts.v64_case_006_substrate_v2.run_extended_v2`.)

**Pre (B42 v1 baseline):**
```
advisor_count:     8
finding_count:     12
critical_count:    12
evidence_refs:     20 V-rows (V10 V20 V22 V25 V29 V33 V36 V41 V42 V43
                   V50 V52 V79 V81 V86 V87 V93 V96 V99 V100)
env_keys_present:  all four false
```

**Post (B55 v2):**
```
advisor_count:     9     (+1: solver_block_advisor)
finding_count:     17    (+5)
critical_count:    17    (+5)
evidence_refs:     22 V-rows (+V27, +V28)
env_keys_present:  all four false
new findings:
  - critical · v27_adjusttimestep_required @ controlDict.adjustTimeStep
  - critical · v28_dilu_on_symmetric @ fvSolution.solvers.U.preconditioner
  - critical · v28_dilu_on_symmetric @ fvSolution.solvers.e.preconditioner
  - critical · v28_dilu_on_symmetric @ fvSolution.solvers.k.preconditioner
  - critical · v28_dilu_on_symmetric @ fvSolution.solvers.omega.preconditioner
```

## V-row capture matrix v2 (case_006 9 documented failure modes)

| mode | B42 v1 | **B55 v2** | reason for current state |
|---|---|---|---|
| V26 | NO | **NO** | codex_output_validator not LANDED (out-of-scope; sub-DEC queue) |
| V27 | NO | **YES ✓** | solver_block_advisor LANDED 2026-05-15 |
| V28 | NO | **YES ✓** | solver_block_advisor LANDED 2026-05-15 |
| V29 | YES ✓ | **YES ✓** | D10 (V63-A) · unchanged |
| V30 | YES ✓ | **YES ✓** | thin_wall substrate (B42 V63-A) · unchanged |
| V31 | NO | **NO** | protocol-revision-level; out-of-stack |
| V32 | NO | **NO** | infra-level; out-of-stack |
| D1 | YES ✓ | **YES ✓** | A2-v2 substrate (B42 V63-A) · unchanged |
| D4 | marginal | **marginal** | canonical advisor (geometry_surgery) not LANDED; classification preserved from B42 |

**3 / 9 firm + D4 marginal (B42 v1) → 5 / 9 firm + D4 marginal (B55 v2). ≥5/9 firm: MET.**

## Backward compatibility

- B42's three substrate files (`thin_wall_inputs.yaml`,
  `interface_bodies.json`, `interface_specs.json`) untouched. B42's
  runner `scripts/v63_case_006_substrate/run_extended.py` continues to
  reproduce its retro §4.2 output byte-identically.
- `test_advisor_stack.py` 31 tests green post-edit · `solver_block_snapshot`
  default `None` preserves all prior dispatch behavior on the existing
  fixtures.
- 100% B42 substrate adoption preserved: case_006 v2 runs the v1 inputs
  + v2 inputs together. No B42-LANDED advisor dispatch lost; finding
  count grows monotonically (12 → 17).

## Surface scan (v2.3 §"Pre-implementation discipline" optional · trailer)

ROADMAP scan: V64-A charter §"Cross-cutting code paths" predicts ≥3 paths
including `case_*/inputs/*.yaml + *.json (substrate v2)` and
`.planning/methodology/industrial_case_solver_findings.md (V-row corpus)`.
This sub-DEC adds a 5th path category — new advisor module under
`geometry_ingest/` — that fits charter scope ("V-series corpus
extensions" §6 path #5 allows V101+; landing an advisor *covering*
existing V27/V28 is a stack-side mirror of the same charter direction).

Existing-implementation grep: `grep -rin "solver_block" ui/backend/
scripts/` returned zero matches before this sub-DEC. `grep -rin
"adjustTimeStep" ui/backend/services/geometry_ingest/` returned zero
matches. Clean surface; new top-level service file under
`ui/backend/services/geometry_ingest/` mandates the scan-clean trailer.

Commit 1 carries `Surface-scan: clean — solver_block_advisor name absent
from ui/backend/services/ + scripts/ + tests/`.

## v2.3 governance compliance

- DEC scope-driven: sub-DEC under V64-A charter (no new charter trigger ·
  V64-A predicted ≥3 paths already · this sub-DEC uses 5 paths within
  charter scope: geometry_ingest/ + advisor_stack.py + case_006/inputs/ +
  scripts/ + tests/)
- Cadence floor THRESHOLD 30: counter +1; well below threshold
- DEC frontmatter: 6 required fields present (decision_id / title /
  status / parent_dec / phase / notion_sync_status) · plus confidence
- v2.2 1-sync-trigger: not auth / not signing / not operator endpoint →
  Codex sync review not required. Confidence: med · self-judgment that
  the surface is small + tests + integration verification justifies
  skipping Codex.
- Kogami: opt-in only; user did not invoke.
- Notion: Status=Accepted but `notion_sync_status: pending` until
  session-end batch sync.

## Audit trail / commit chain

3 atomic commits each carrying `confidence: med`:

1. `feat(v64-case006-v2): land solver_block_advisor (V27+V28) + stack wire + case_006 substrate v2`
2. `docs(v64-case006-v2): retro · V-row 3/9 → 5/9 firm verified on case_006`
3. `docs(v64-case006-v2): sub-DEC DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2 Accepted`

## References

- V64-A charter: `.planning/decisions/2026-05-15_v64_charter_dec.md`
- V63-A close DEC §8 row 6: `.planning/decisions/2026-05-15_v63_close_dec.md`
- B42 v1 retro: `.planning/retrospectives/2026-05-15_case_006_substrate_extension.md`
- B55 v2 retro: `.planning/retrospectives/2026-05-15_case_006_substrate_extension_v2.md`
- V-series corpus V27 + V28: `.planning/methodology/industrial_case_solver_findings.md`
- S15 playbook entry: `.planning/methodology/solver_convergence_playbook.md`
- B42 v1 sub-DEC: `.planning/decisions/2026-05-15_v63_sub_case_006_substrate.md`
- Stack v2 output: `scripts/v64_case_006_substrate_v2/stack_report_python_extended_v2.json`

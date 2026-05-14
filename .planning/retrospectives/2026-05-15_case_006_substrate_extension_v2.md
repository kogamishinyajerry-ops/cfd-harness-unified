# RETRO · case_006 ONERA M6 substrate extension v2 · V63-A carry-over #6 · V64-A Tier 1

> V64-A Tier 1 · M-V64A-CASE-006-SUBSTRATE-V2 (DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2).
> Driver: V63-A close DEC §8 row 6 carry-over (case_006 V-row 3/9 → 6+/9
> · V26-V28/V31/V32 + D4 uncovered).
> Predecessor: B42 `2026-05-15_case_006_substrate_extension.md` landed
> three substrate-side input files (`thin_wall_inputs.yaml` +
> `interface_bodies.json` + `interface_specs.json`) and pushed V-row
> capture 1/9 → 3/9 firm + D4 marginal.
>
> **B55 scope upgrade — main-session SURFACE turn:** B55's original
> substrate-only brief assumed V26-V28/V31/V32 had LANDED advisors with
> input-substrate gaps. Verification against `advisor_stack.py`
> `_V_ROWS_PER_ADVISOR` (10 LANDED advisors covering V10/V20/V22/V25/V29/
> V33/V36/V41-43/V50/V52/V55/V79/V81/V86/V87/V93/V94/V96/V99/V100) +
> the B42 §5 V-row matrix confirmed **all five remaining case_006
> modes are out-of-stack scope** — no substrate input would change the
> capture without first landing a new advisor. Surfaced this to the
> user with three options:
>
>   A. Reclassify carry-over #6 as stack-saturation (1 commit · no new
>      advisor)
>   B. D4 marginal → firm via V31 protocol-revision ratification only
>      (1 commit · 4/9 firm not 5/9)
>   C. Land a new advisor to unblock V26/V27/V28/V31 (charter-scope ·
>      real investment)
>
> User chose **C**. This retro lands one new advisor module
> (`solver_block_advisor`) covering V27 + V28 — the cheapest stack-actionable
> path producing the required ≥2 V-row firm-capture gain on case_006.

---

## §1 Goal

Close V63-A close DEC §8 carry-over #6 with **stack-actionable** progress
on case_006 V-row truth capture:

1. Land **`solver_block_advisor`** (new advisor #11 in the stack) covering
   V27 (rhoCentralFoam adjustTimeStep mandatory) + V28 (DILU
   preconditioner on symmetric matrices) — both documented on case_006 v1
   first solver run (2026-05-08) and codified as S15 in
   `solver_convergence_playbook.md`.
2. Wire the advisor into `advisor_stack.assemble_stack(...)` via the
   existing dispatch + `_V_ROWS_PER_ADVISOR` registration pattern.
3. Synthesize one new substrate-input file under `case_006/inputs/`:
   `solver_block_inputs.yaml` — pre-fix snapshot derived verbatim from V27
   + V28 corpus entries.
4. Verify the stack now dispatches `solver_block_advisor` and emits 5
   findings (1 × V27 + 4 × V28) on case_006 substrate v2.
5. Push V-row truth capture from B42 baseline (3/9 firm + D4 marginal) to
   **5/9 firm + D4 marginal** against the documented 9 case_006 failure
   modes (V26/V27/V28/V29/V30/V31/V32/D1/D4).
6. V64-A Done #6 case_006 capture advances **3/9 → 5/9** firm; V63-A
   carry-over #6 substantively progressed (not closed — V26/V31/V32
   remain out-of-stack; D4 remains marginal).

Constraints (per v2.3 + brief):

- Sub-DEC scope under existing V64-A charter (no charter authoring).
- 4Q-Q1 LLM-offline gate must hold (`env -i HOME PATH .venv/bin/python`).
- No Notion sync (only Status=Accepted DECs sync at session-end batch).
- No Codex review (LANDED advisor + substrate-input addition is not a
  v2.2 1-sync-trigger · not auth / signing / operator endpoint).
- No Kogami (v2.3 opt-in; user did not invoke).
- 3 atomic commits each carrying `confidence: med`.
- No ARC-GOAL.md update from this turn (B56 case_004 solver runs in
  parallel; main session reconciles to avoid rebase contention).

---

## §2 V-row selection decision (B55 SURFACE outcome)

| V-row | brief premise | corpus truth | stack-actionable? |
|---|---|---|---|
| V26 | "corner-flow signature" | Codex CAD off-by-half-width on `centered=True` | NO — needs new `codex_output_validator` |
| V27 | "stack-applicable" | rhoCentralFoam adjustTimeStep mandatory | **YES (new advisor)** |
| V28 | "stack-applicable" | rhoCentralFoam DILU preconditioner symmetric-only | **YES (new advisor)** |
| V31 | "shock / BL class · BL advisor LANDED" | Codex defect→advisor mapping (protocol-revision) | NO — protocol-level |
| V32 | "shock / BL class · BL advisor LANDED" | NASA Glenn HTTP 500 (infra workaround) | NO — infra-level |
| D4 | "input-wedge-missing" | thin_wall_advisor fires (B42 retro §5) | NO — already marginal-fired; canonical = `geometry_surgery` (not LANDED) |

Cheapest path = land **`solver_block_advisor`** with two rules (V27 + V28).
Rationale:

- Pure-config validation (no CAD parsing · no FreeCAD subprocess · no
  trimesh dependency · no STL inventory).
- Tabular rule logic (density-based-solver set × preconditioner-asymmetric
  set + adjustTimeStep flag).
- Single new substrate input file (`solver_block_inputs.yaml`) — derived
  verbatim from V27 + V28 corpus entries; no fabrication.
- Forward-compatible with V53 (rhoPimpleFoam transonic-yes inverse
  pattern) — out of V64-A scope but the advisor's design admits the
  extension under the same `_DENSITY_BASED_SYMMETRIC_SOLVERS` /
  `_ASYMMETRIC_ONLY_PRECONDITIONERS` table approach.

Not chosen (and why):
- `codex_output_validator` for V26 + V31 — would need a canonical CAD-
  formula registry + canonical defect→advisor mapping table; larger
  surface; both V-rows are Codex-protocol-revision class (the right home
  is `codex_case_design_protocol.md` updates, not an advisor).
- D4 marginal → firm via V31 ratification — only +1 firm capture
  (3 → 4/9), misses the 5/9 target.

---

## §3 Synthesis — what landed

### 3.1 New advisor module

`ui/backend/services/geometry_ingest/solver_block_advisor.py` (~165 LOC
incl. module docstring · LANDED 2026-05-15):

Two LANDED rules:

- **R1 (V27)**: `solver in {rhoCentralFoam, rhoCentralDyMFoam}` AND
  `adjust_time_step` is False or None (absent ⇒ OpenFOAM default `no`) →
  critical `v27_adjusttimestep_required` finding @
  `controlDict.adjustTimeStep`.
- **R2 (V28)**: same solver set AND any field's preconditioner is in
  `{DILU, FDILU}` (asymmetric-only registry) → critical
  `v28_dilu_on_symmetric` finding @
  `fvSolution.solvers.<field>.preconditioner` (one finding per field, in
  sorted field-name order).

Public API:

- `SolverBlockSnapshot` (frozen dataclass) — normalized view of
  `system/controlDict.adjustTimeStep` + `system/controlDict.deltaT` +
  `system/fvSolution.solvers.<field>.preconditioner` mapping.
- `check_solver_block(snapshot) → SolverBlockReport(findings: tuple[...])` —
  pure function, no I/O.
- `SolverBlockFinding` (frozen dataclass) — `severity` / `code` /
  `location` / `detail` (mirrors D10 shape).

Anti-scope (matches advisor docstring):
- No mutation of any case directory (V130 advisory-only).
- No `fvSchemes` validation (separate advisor class).
- No runtime Co verification (engineer-symptom row is documentation).
- No rhoSimpleFoam / rhoPimpleFoam coverage today (forward-extension
  along V53 lines; design admits but out of V64-A scope).

### 3.2 Stack integration

`ui/backend/services/advisor_stack.py` edits (4 atomic insertions):

| insertion site | change |
|---|---|
| L172 (`_load_advisor` block) | `solver_block_advisor = _load_advisor("solver_block_advisor")` |
| L187 (`_V_ROWS_PER_ADVISOR`) | `"solver_block_advisor": ("V27", "V28"),` |
| ~L438 (after `_normalize_shm`, before `_normalize_thin_wall`) | new `_normalize_solver_block(report)` helper (~14 LOC) |
| `assemble_stack` kwargs | new keyword `solver_block_snapshot: SolverBlockSnapshot | None = None` |
| `assemble_stack` body | new dispatch block (~22 LOC) — `if solver_block_snapshot is not None: ... _dispatch(...)` |

Total stack-side change: ~40 LOC additions, zero deletions, zero
modifications to existing dispatch behavior. The previous 10 advisors
continue to dispatch identically on all prior fixtures (verified: 31/31
`test_advisor_stack.py` tests green post-edit).

### 3.3 case_006 substrate v2 input

`~/Desktop/case_006_onera_m6_transonic/inputs/solver_block_inputs.yaml`
(~50 LOC incl. `_meta` provenance block):

```yaml
_meta:
  source: industrial_case_solver_findings.md V27 + V28 (verbatim transcription)
  case_version: v1_pre_fix_2026-05-08
  current_case_dir_status: fixed (S15 codified · solver_convergence_playbook.md)
  v_row_attribution: [V27, V28]
  sub_dec: DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2

solver: rhoCentralFoam       # explicit density-based; CFL-bounded
adjust_time_step: false       # V27 trigger: missing / "no"
delta_t: 1.0                  # V27 context: ~20,000× too large

preconditioners:              # case_005 rhoSimpleFoam inheritance pre-fix
  U: DILU
  e: DILU
  k: DILU
  omega: DILU
```

**Honest semantics — historical-snapshot substrate**: the current
case_dir/system/* state is the **post-fix** S15-compliant configuration
(adjustTimeStep yes + symGaussSeidel). The substrate file represents the
pre-fix snapshot that Codex first emitted on 2026-05-08, before V27 + V28
were caught and fixed by sub-session manual intervention. This is
parallel to B42's substrate inputs (`thin_wall_inputs.yaml`,
`interface_bodies.json`, `interface_specs.json`) which were derived from
the V-series corpus + defect_manifest, not from the current case_dir
runtime state. The `_meta` block names the provenance line by line.

### 3.4 v2 runner

`scripts/v64_case_006_substrate_v2/run_extended_v2.py` (~140 LOC incl.
docstring) mirrors B42's `run_extended.py` and adds:

- `load_solver_block_snapshot()` → `SolverBlockSnapshot` from the YAML
- `assemble_stack(..., solver_block_snapshot=solver_block_snapshot)`
- Writes `stack_report_python_extended_v2.json` next to the runner.

Reuses B42's `load_thin_wall_inputs`, `load_interface_bodies`,
`load_interface_specs` via import (no copy-paste).

### 3.5 Tests

`ui/backend/tests/test_solver_block_advisor.py` (10 tests, all green):

1. case_006 v1 pre-fix snapshot emits V27 + 4 × V28 (5 findings critical)
2. adjustTimeStep yes suppresses V27, V28 still fires
3. adjustTimeStep None treated as no (OpenFOAM default)
4. Valid symmetric preconditioners (DIC / GAMG / symGaussSeidel) emit nothing
5. FDILU also asymmetric-only (same V28 flag)
6. Non-density-based solver (rhoSimpleFoam + DILU) emits nothing
7. rhoCentralDyMFoam (dynamic-mesh variant) also dispatched
8. Canonical S15-compliant rhoCentralFoam emits nothing
9. `SolverBlockFinding` is frozen (V130 advisory-only contract)
10. `SolverBlockReport` itself is frozen

Existing tests (`test_advisor_stack.py` 31 / `test_thin_wall_advisor.py`
13 / `test_bc_type_name_validity_advisor.py` 19): **73/73 green**
post-integration. No regression.

---

## §4 Verification — assemble_stack pre vs post

### 4.1 Pre (B42 baseline · run_extended.py · 2026-05-15)

```
advisor_count:        8
finding_count:        12
critical_count:       12
warning_count:        0
failed_advisor_count: 0
advisors_dispatched:  [bc_type_name_validity, face_orientation,
                       inlet_outlet, shm_dict, thermo_polynomial_range,
                       thin_wall, unit_detector,
                       virtual_interface_detector]
evidence_refs:        20 V-rows (V10 V20 V22 V25 V29 V33 V36 V41 V42 V43
                       V50 V52 V79 V81 V86 V87 V93 V96 V99 V100)
env_keys_present:     all four false (V130 4Q-Q1 ✓)
```

### 4.2 Post (v2 · run_extended_v2.py)

```
advisor_count:        9                      (+1: solver_block_advisor)
finding_count:        17                     (+5)
critical_count:       17                     (+5)
warning_count:        0
failed_advisor_count: 0
advisors_dispatched:  [bc_type_name_validity, face_orientation,
                       inlet_outlet, shm_dict, solver_block_advisor, ←NEW
                       thermo_polynomial_range, thin_wall, unit_detector,
                       virtual_interface_detector]
evidence_refs:        22 V-rows                 (+V27, +V28)
env_keys_present:     all four false (V130 4Q-Q1 ✓)
```

### 4.3 New findings (delta = 5)

| # | source_advisor | severity | code | location | V-rows |
|---|---|---|---|---|---|
| 13 | `solver_block_advisor` | critical | `v27_adjusttimestep_required` | `controlDict.adjustTimeStep` | V27 V28 |
| 14 | `solver_block_advisor` | critical | `v28_dilu_on_symmetric` | `fvSolution.solvers.U.preconditioner` | V27 V28 |
| 15 | `solver_block_advisor` | critical | `v28_dilu_on_symmetric` | `fvSolution.solvers.e.preconditioner` | V27 V28 |
| 16 | `solver_block_advisor` | critical | `v28_dilu_on_symmetric` | `fvSolution.solvers.k.preconditioner` | V27 V28 |
| 17 | `solver_block_advisor` | critical | `v28_dilu_on_symmetric` | `fvSolution.solvers.omega.preconditioner` | V27 V28 |

### 4.4 Diff diagonal

| metric | pre (B42 v1) | post (B55 v2) | delta |
|---|---|---|---|
| advisor_count | 8 | 9 | +1 |
| finding_count | 12 | 17 | +5 |
| critical_count | 12 | 17 | +5 |
| evidence_refs (V-rows in union) | 20 | 22 | +2 (V27 + V28) |
| documented-failure capture (case_006 9 modes) | 3 / 9 firm + D4 marginal | **5 / 9 firm + D4 marginal** | +2 firm |
| LANDED advisor count (stack-wide) | 10 | 11 | +1 (`solver_block_advisor`) |
| V-row corpus coverage (stack-wide) | V10/V20/V22/V25/V29/V33/V36/V41-43/V50/V52/V55/V79/V81/V86/V87/V93/V94/V96/V99/V100 | +V27 V28 = same minus +V27 V28 | +2 V-rows |

---

## §5 V-row capture matrix vs 9 documented case_006 failure modes

| failure mode | TRACK-3 | TRACK-3-rerun | v1 (B42) | **v2 (B55)** | reason for current state |
|---|---|---|---|---|---|
| V26 Codex CAD off-by-half-width | NO | NO | NO | **NO** | Codex-protocol issue; no `codex_output_validator` LANDED — would require canonical CAD-formula registry |
| V27 rhoCentralFoam adjustTimeStep | NO | NO | NO | **YES ✓** | `solver_block_advisor` LANDED 2026-05-15; fires `v27_adjusttimestep_required` on case_006 substrate v2 (rhoCentralFoam + adjustTimeStep=false + deltaT=1.0) |
| V28 rhoCentralFoam DILU preconditioner | NO | NO | NO | **YES ✓** | `solver_block_advisor` LANDED 2026-05-15; fires 4× `v28_dilu_on_symmetric` on U/e/k/omega preconditioners |
| V29 BC-name validity | NO | YES ✓ | YES ✓ | **YES ✓** | D10 LANDED B33 (V63-A); unchanged |
| V30 thin_wall 0.18 mm sliver | NO | NO | YES ✓ | **YES ✓** | thin_wall substrate landed B42 (V63-A); unchanged |
| V31 Codex defect→advisor mapping | NO | NO | NO | **NO** | Protocol-revision-level issue; out-of-stack — V31's lesson is "thin_wall_advisor IS the right advisor for D4" (already firing per B42); the meta-finding about Codex's mis-mapping does not lend itself to an advisor finding without a canonical defect→advisor registry |
| V32 Tier-1 NASA Glenn HTTP 500 | NO | NO | NO | **NO** | Infra-level finding (corporate SSL chain + upstream 500); not within advisor stack scope |
| D1 root_fairing sub-mm gap | partial | partial | YES ✓ | **YES ✓** | A2-v2 `virtual_interface_detector` substrate landed B42 (V63-A); unchanged |
| D4 tip_cap_sliver 0.18 mm | partial | partial | YES ✓ (marginal) | **YES ✓ (marginal)** | `thin_wall_advisor` fires per B42 (V63-A); canonical advisor remains `geometry_surgery.decimate_to_tier` (not LANDED) — marginal-close status unchanged from B42 |

**Capture rate: 3 / 9 firm (B42) → 5 / 9 firm (B55) + D4 marginal. Hard target ≥ 5 / 9: MET.**

The 3 remaining no-catch rows (V26 / V31 / V32) are documented out-of-
stack scope per the V-series corpus + V63-A B42 §5 + this retro §2:

- **V26** would close on landing `codex_output_validator` (would need
  canonical CAD-formula registry); V64-A or later scope decision.
- **V31** would close on a `codex_case_design_protocol.md` revision plus
  a defect→advisor-mapping validator (out of substrate scope; meta-
  protocol class). Note: V31's *lesson* (thin_wall_advisor is correct for
  D4 sliver) is **operationally already in effect** via the B42-landed
  thin_wall path firing on tip_cap_sliver; the row stays NO only because
  no advisor emits a finding explicitly citing V31's protocol claim.
- **V32** is infra-class (HTTP 500 + corporate SSL chain), not advisor
  scope; will close only on workaround documentation, not stack work.

### Silent-under-coverage failure mode status

- **Closed for V27** (`solver_block_advisor` substrate-extended · permanent for case_006 and any future case providing a `solver_block_snapshot` with a density-based-symmetric solver + missing adjustTimeStep).
- **Closed for V28** (`solver_block_advisor` substrate-extended · permanent for any case providing a snapshot with the symmetric-path DILU/FDILU pattern).
- **Closed for V29** (D10 catalog · permanent · unchanged from V63-A).
- **Closed for V30** (`thin_wall_inputs.yaml` substrate-extended B42 · permanent for case_006).
- **Closed for D1** (`interface_bodies.json` + `interface_specs.json` substrate-extended B42 · permanent for case_006).
- **Marginal-close for D4** (thin_wall_advisor fires on substrate; canonical geometry_surgery advisor not yet LANDED — same as B42).
- **Still open for V26 / V31 / V32** — see above analysis.

---

## §6 4Q gate offline confirmation

Q1 (LLM-offline): runner pops `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` /
`GOOGLE_API_KEY` / `DEEPSEEK_API_KEY` from `os.environ` **before** any
backend import. Outer invocation under
`env -i HOME="$HOME" PATH="$PATH" .venv/bin/python` guarantees the parent
env is also empty of LLM keys.

`stack_report_python_extended_v2.json::env_keys_present`:

```json
{
  "ANTHROPIC_API_KEY": false,
  "OPENAI_API_KEY":    false,
  "GOOGLE_API_KEY":    false,
  "DEEPSEEK_API_KEY":  false
}
```

Byte-identical rerun: ran the v2 runner twice (under
`env -i HOME PATH .venv/bin/python`); diff'd outputs after removing
`duration_ms` wall-clock fields (jq `del(.advisor_calls[].duration_ms)`) →
**identical**. Three `duration_ms` lines differ as expected (per-advisor
wall-clock varies; the dispatched output / findings / V-row union are
deterministic).

Q2 / Q3 / Q4 (artifacts / TrustGate / advisor-not-driver): same as B42 —
the substrate-only addition produces frozen `SolverBlockFinding`
dataclasses through the existing `_normalize_solver_block` → `Finding` →
`AdvisorStackReport` chain; no route mutation; no case-dir write; no
LLM call.

---

## §7 Tests + regression

```
ui/backend/tests/test_solver_block_advisor.py          10 passed
ui/backend/tests/test_advisor_stack.py                 31 passed (+0)
ui/backend/tests/test_thin_wall_advisor.py             13 passed (+0)
ui/backend/tests/test_bc_type_name_validity_advisor.py 19 passed (+0)
Total: 73 / 73 green
```

The advisor_stack 31-test suite passed without modification — the new
`solver_block_advisor` dispatch is silently skipped when the kwarg is
absent, preserving every prior assertion about advisor_count / findings /
evidence_refs on the existing fixtures.

---

## §8 V64-A Done #6 advance

V64-A charter Done dimension #6 reads:

> ≥ 1 case 拿到 ≥7/9 · ≥2 cases 拿到 ≥5/9 · 不准 alias 灌水

| case | V63-A close baseline | post-B55 |
|---|---|---|
| case_011 v5b | 7 / 9 (over-met) | 7 / 9 (unchanged) |
| case_004 NREL | 5 / 9 (B45) | 5 / 9 (unchanged) |
| **case_006 ONERA M6** | **3 / 9 (B42) + D4 marginal** | **5 / 9 firm + D4 marginal** |

V64-A Done #6 progress on case_006 specifically: **3/9 → 5/9 firm**.
Cluster status (3 cases at ≥5/9 firm) advances from 2/3 (V63-A close
clause 2) to **3/3** post-B55 — but Done #6 is V64-A-arc-wide (counts
all V64-A cases, not just V63-A inheritance) so the over-met count
relative to V64-A's clause "≥2 cases ≥5/9" is now case_011 + case_004 +
case_006 = 3 / 2 (+1).

The carry-over #6 plan-file scope ("V-row 3/9 → 6+/9") is **partially
met**: 5/9 firm achieved; remaining 4 rows are advisor-land gated, not
substrate-gated, so 6+/9 requires a separate decision on whether to land
`codex_output_validator` (V26/V31) — out of this sub-DEC's scope.

---

## §9 v2.3 governance compliance

| v2.3 dimension | status |
|---|---|
| DEC scope-driven | Sub-DEC scope (V64-A charter already authored) · ~250 LOC advisor + ~40 LOC stack + ~50 LOC substrate + ~140 LOC runner + 10 tests · 5 shared code paths (geometry_ingest/ + advisor_stack.py + case_006/inputs/ + scripts/ + tests/) — within V64-A charter's predicted ≥3 paths |
| Cadence floor THRESHOLD 30 | Surface scan check: 1 new top-level file (`solver_block_advisor.py`) · scan clean (no pre-existing solver-block advisor or registry) · `Surface-scan: clean` trailer optional · 1 new substrate-input file (not a top-level entry) |
| Counter pure telemetry | autonomous_governance: true · counter +1 (this sub-DEC) |
| Surface-scan trailer | Optional per v2.3 round-1 loosen; including on commit 1 (`Surface-scan: clean — solver_block_advisor name absent from advisor_stack.py + geometry_ingest/`) |
| Codex review trigger | Substrate + LANDED advisor not a v2.2 1-sync-trigger (not auth / signing / operator endpoint). Confidence: med (new module, but small surface + 10 tests + integration verified). Not invoked. |
| Kogami | Opt-in only; user did not invoke. |
| Notion sync | Sub-DEC Status=Accepted but session-end batch (per CLAUDE.md "Notion 仅 sync Status=Accepted"); deferred to main session reconcile. |
| 4Q gate offline rerun | Byte-identical confirmed (§6). |

---

## §10 V63-A carry-over #6 progress summary

| dimension | B42 v1 close (V63-A) | B55 v2 close (V64-A) | gap remaining |
|---|---|---|---|
| case_006 V-row firm | 3 / 9 | 5 / 9 | 4 (V26 / V31 / V32 + D4 marginal-to-firm) |
| Stack LANDED advisors | 10 | 11 (+solver_block_advisor) | n/a |
| Stack V-row coverage | V10/V20/V22/V25/V29/V33/V36/V41-43/V50/V52/V55/V79/V81/V86/V87/V93/V94/V96/V99/V100 | +V27 V28 | V26 V31 V32 absent stack-wide |
| Failure-mode root cause closed | V29 / V30 / D1 | V27 / V28 / V29 / V30 / D1 | V26 (codex_output_validator) · V31 (codex_case_design_protocol) · V32 (infra) · D4 canonical (geometry_surgery) |

**Net: V63-A close DEC §8 carry-over #6 row (case_006 V-row 3/9 → 6+/9)
substantively progressed from 3/9 → 5/9 firm; the gap to plan-file's 6+
remains advisor-land-gated, not substrate-gated.**

---

## §11 Open questions surfaced (V64-A scope-decision queue)

1. **Land `codex_output_validator` for V26 + V31?** Would push case_006 to
   7 / 9 firm (V26 + V31 added). Would require a canonical CAD-formula
   registry (cq.Workplane.box centered=True semantics + ONERA M6 specific
   bbox-half-width formula) and a defect→advisor mapping table. New
   sub-DEC required. Forward-extendable: same advisor would catch any
   future Codex CAD generator drift on similar formulae. Out of B55
   scope.
2. **Promote D4 from marginal to firm?** V31's lesson states
   `thin_wall_advisor` is the canonical advisor for D4 (sliver class).
   The B42 §5 "marginal" classification used `defect_manifest.yaml`'s
   `expected_advisor: geometry_surgery` field. Ratifying V31 via a
   sub-DEC could re-classify D4 firm without code change, but B55 chose
   to keep B42's classification semantics intact for cross-retro
   consistency. Decision deferred.
3. **`solver_block_advisor` forward-extension to V53** (rhoPimpleFoam +
   transonic-yes inverse pattern: PCG/DIC on the now-asymmetric p
   matrix). The advisor's `_DENSITY_BASED_SYMMETRIC_SOLVERS` /
   `_ASYMMETRIC_ONLY_PRECONDITIONERS` table approach admits the
   extension; new rule needed for the transonic-flag-driven symmetry
   flip. Out of B55 scope; candidate for case_016 substrate v2 (where
   V53 originated).

---

## §12 Commit chain

| # | Subject | Files |
|---|---|---|
| 1 | `feat(v64-case006-v2): land solver_block_advisor (V27+V28) + stack wire + case_006 substrate v2` | advisor module + advisor_stack.py + tests + case_006/inputs/solver_block_inputs.yaml + scripts/v64_case_006_substrate_v2/ |
| 2 | `docs(v64-case006-v2): retro · V-row 3/9 → 5/9 firm verified on case_006` | this retro file |
| 3 | `docs(v64-case006-v2): sub-DEC DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2 Accepted` | sub-DEC file |

All commits carry `confidence: med` (new module · small surface · 10
tests + 31 prior advisor_stack tests green + integration runner output
matches §4.2 expectation).

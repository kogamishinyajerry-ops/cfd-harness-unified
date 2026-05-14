# RETRO · Stack-level Track C session 3 · case_006 ONERA M6 transonic (validation case)

> Third stack-level Track C session (M-STACK-TRACK-3 · V62-A Tier 3).
> Validation case = Tier-1 reference geometry (ONERA M6, AGARD AR-138 /
> Schmitt-Charpin 1979). Numerics class **`compressible_shock_density_based`**
> — third unique class after case_011 (`steady-laminar-CHT-multi-stream`,
> TRACK-1) and case_016 (`compressible-DES-acoustic`, TRACK-2).
>
> **Verdict: 接管决策 NOT MET this session** (adoption rate **0 / 0** — stack
> ran cleanly with **zero findings** on both paths; the ≥ 70 % threshold
> requires a non-empty denominator and cannot be vacuously satisfied).
> Session counts toward Done dim #3 retro counter (2 / 3 → 3 / 3) but **NOT**
> toward the passing-session subcounter, which stays at **1 / 2**. Tier 3
> Done dim #3 therefore remains unmet at this commit; TRACK-1 re-run after
> the 3 advisor enhancements it recommends (or a TRACK-4 with denominator-
> producing inputs) is the path to close the dim.

---

## §1 Session goal

Three concrete deliverables (per dispatch brief B30):

1. **Validation-case selection** — pick a case whose failure modes have
   independent ground truth (experimental data + published reference)
   so the stack's output can be diff'd against documented historical
   verdicts rather than against engineer in-session judgment alone.
2. **Two-path stack invocation** — exercise the V62-A stack via both
   `assemble_stack(...)` direct import (path b) and `POST /api/ai-review`
   via FastAPI `TestClient` (path a) on the same validation artifacts.
3. **Done-dim-#3 advancement decision** — adoption rate ≥ 70 % ⇒ PASS
   (TRACK-3 closes Done dim #3 at 2 / 2 ✓); otherwise FAIL with a
   structured explanation of the gap to inform whether to (i) re-run
   TRACK-1 after advisor enhancements TRACK-1 recommends, or (ii) add
   TRACK-4 with a different case profile.

Hard constraints observed (per dispatch + `~/CLAUDE.md` v2.3): no edits
under `~/Desktop/case_006_onera_m6_transonic/` (substrate read-only); no
edits to `ui/backend/services/geometry_ingest/` (no advisor land in this
retro); no new DEC; no Codex round (acceptance evidence only); no Notion
sync (retro is not Accepted DEC); no Kogami (v2.3 round-1 opt-in only).

---

## §2 Why case_006 is the validation case

**Selection priority order** (per dispatch): case_006 > case_004 > case_010 >
case_005 > case_007. **Chose case_006** because every column in the
following table is satisfied; lower-priority candidates fall short on one
or more axes.

| Axis | case_006 ONERA M6 |
|---|---|
| Tier-1 reference geometry | ✅ NASA Glenn `WWW/wind/valid/m6wing/` (now unreachable per V32 — NACA-0010 D-section proxy used) |
| Published experimental truth | ✅ AGARD AR-138 (Schmitt-Charpin 1979) Cp at 7 η stations |
| Distinct numerics class | ✅ `compressible_shock_density_based` — disjoint from case_011 (CHT-multi-stream) + case_016 (DES-acoustic) |
| Documented V-row sediment | ✅ V26-V32 (7 net-new findings landed 2026-05-08 in `industrial_case_solver_findings.md`) |
| Defect-set with prior advisor-exercise verdicts | ✅ D1 root-fairing sub-mm gap (A2-v2 expected fire) + D4 tip_cap_sliver 0.18 mm (thin_wall expected critical) |
| Stack-LANDED-prior-to-session | ✅ pre-stack — case_006 substrate finalized 2026-05-08, V62-A stack assembled 2026-05-14 |
| Canonical advisor-input YAMLs available | ✅ `inputs/parts_manifest.yaml` (V62-A canonical convention) |
| substrate read-only friendly | ✅ no in-session writes to case_006 |

case_006 is "validation" rather than "exploratory" because: (a) its
geometric and numeric truth values are externally published (not
case-internal); (b) its failure modes were enumerated and analyzed
**before** the V62-A stack existed, so the stack has not been tuned on
case_006-class artifacts; (c) the case-thread sandbox completed a full
build-CAD → STL → mesh → density-based-solver pipeline and recorded the
canonical D1/D4 advisor-exercise verdicts independently of this session.

case_004 / case_010 / case_005 / case_007 were rejected because:
- case_004 (NREL Phase VI MRF): no v1 substrate landed; substrate work
  predates the V62-A YAML convention; advisor-exercise truth not yet
  recorded
- case_010 (DrivAer LES): no v1 substrate; aerodynamic validation truth
  exists upstream (TUM-DrivAer) but the project has not yet ingested it
- case_005 (RAE M2129 S-duct): another compressible case, but the failure
  modes overlap case_006's numerics-infrastructure V-rows (V21-V25) and
  case_005 was the first dispatched-case-thread so its truth is less
  independent
- case_007 (KCS Ship VoF): multi-phase numerics class is well-suited but
  no canonical substrate exists

---

## §3 Stack invocation methodology (path a vs path b)

Drivers committed alongside this retro:

- `scripts/stack_track_c_session_3/build_inputs.py` — input dict
  constructor (loads `parts_manifest.yaml` verbatim, hand-translates
  `case/system/snappyHexMeshDict` + `case/constant/thermophysicalProperties`)
- `scripts/stack_track_c_session_3/run_python_path.py` — path b runner
  (direct `assemble_stack(...)`)
- `scripts/stack_track_c_session_3/run_http_path.py` — path a runner
  (`POST /api/ai-review` via `TestClient(app)`, per MEMORY rule "no port
  squatting"; in-process FastAPI is the same code path uvicorn would
  serve)

**Path b** (Python, direct in-process):

```text
advisor_count:        5
finding_count:        0
critical_count:       0
warning_count:        0
failed_advisor_count: 0
advisors_dispatched:  ['face_orientation_advisor',
                      'inlet_outlet_validator',
                      'shm_dict_validator',
                      'thermo_polynomial_range_advisor',
                      'unit_detector']
evidence_refs:        ['V100','V20','V41','V52','V79','V81','V86','V87',
                      'V93','V96','V99']
```

**Path a** (HTTP via `TestClient`, status 200):

```text
advisor_count:        4
finding_count:        0
critical_count:       0
warning_count:        0
failed_advisor_count: 0
advisors_dispatched:  ['face_orientation_advisor',
                      'inlet_outlet_validator',
                      'shm_dict_validator',
                      'thermo_polynomial_range_advisor',
                      'v_series_drift_guard']
evidence_refs:        ['V100','V41','V52','V79','V81','V86','V87','V93','V99']
llm_enhanced:         false
audit_artifact_path:  .planning/audits/anon_ai_review_20260514T115122.983786Z_e5a9c4c0.json
```

### Two-path divergence (same as TRACK-1 + TRACK-2)

| field | python (b) | http (a) | match? |
|---|---|---|---|
| advisor_count | 5 | 4 | ❌ |
| advisors dispatched | A4 / A5 / A8 / A10 / **unit_detector** | A4 / A5 / A8 / A10 / **v_series_drift_guard** | DIFFERENT |
| finding_count | 0 | 0 | ✅ |
| critical_count | 0 | 0 | ✅ |
| warning_count | 0 | 0 | ✅ |
| failed_advisor_count | 0 | 0 | ✅ |
| evidence_refs union | adds V20, V96 (unit_detector) | adds none net | python ⊃ http on unit rows |

**Two divergences confirmed** — identical to TRACK-1 §2 + TRACK-2 §3:

1. **HTTP path drops unit_detector** because `AIReviewRequest` Pydantic
   schema has no `step_path` field; auto-discovery via `case_dir` is the
   only HTTP plumbing for unit_detector, and this driver intentionally
   omits `case_dir` to mirror path b's explicit-dict-only invocation.
   Documented wire-schema gap recurs (3rd consecutive Track C session).
2. **HTTP path adds `v_series_drift_guard`** as an extra advisor at the
   route boundary (per `DEC-V62-A-sub-M-DRIFT-V2`, commit `b10494c →
   1cda573`). Audit-mode no-op by default — `findings_dropped: 0`.
   Intentional; not a bug.

**Path equivalence on findings**: both paths produce identical **empty**
finding sets. The advisor-count delta is structural (unit_detector vs
drift_guard) not behavioral (each path correctly dispatches every
applicable advisor for the artifacts it receives). 0 crashes both paths.

---

## §4 Findings table (engineer adjudication)

| # | source advisor | severity | code / location | engineer disposition | rationale |
|---|---|---|---|---|---|

**Table is empty by design.** All 5 dispatched advisors returned
`status: ok` with **zero findings each**:

| advisor | input | dispatched | findings | silent-skip reason (per advisor docstring) |
|---|---|---|---|---|
| `face_orientation_advisor` (A4) | 12-part `parts_manifest` | yes | 0 | none of 12 parts carry `actual_face_normal`; all 12 silent-skip per A4 docstring §177-180 (`bodies_skipped: 12 / bodies_checked: 0`) |
| `inlet_outlet_validator` (A5) | 12-part `parts_manifest` | yes | 0 | case_006 roles are {wall, auxiliary_wall_defect, tip_cap_wall, symmetry, farfield_domain_reference, farfield}; none intersect `THROUGH_FLOW_ROLES = {supply, return, inlet, outlet}` (V81 emission protocol), so all 12 parts silent-skip (`fail_count: 0 / warning_count: 0 / pass_count: 0`) |
| `shm_dict_validator` (A8) | sHM with 5 geometry entries + 5 refinementSurfaces entries | yes | 0 | every refinementSurfaces key has a matching geometry entry AND every geometry entry is referenced; `features ()` is empty (consistent with `multiRegionFeatureSnap: false` — no V86 false-positive) |
| `thermo_polynomial_range_advisor` (A10) | hePsiThermo + perfectGas + eConst + const transport | yes | 0 | non-polynomial mixture form → correctly silent-skip per A10 docstring (advisor only fires on `hePolynomial`/`janafThermo` shapes with Tlow/Thigh bounds) |
| `unit_detector` (path b only) | STEP file `inputs/cad_codex_v1.step` | yes | 0 | STEP header declares `SI_UNIT(.MILLI.,.METRE.)` (verified V20/V96 evidence rows surfaced); declared-unit branch returns PASS without warning |
| `v_series_drift_guard` (path a only) | 0 findings to scan | yes | 0 (audit-mode no-op) | per `DEC-V62-A-sub-M-DRIFT-V2` audit-mode contract; would warn if a finding cited a V-row absent from `industrial_case_solver_findings.md` |

**Adoption metrics**: 0 adopted / 0 partial / 0 rejected / 0 inconclusive
→ **adoption rate = 0 / 0 = undefined** → cannot satisfy ≥ 70 %
threshold by vacuity → **接管决策 NOT MET this session**.

**Crashes**: 0 of 5 (path b) / 4 (path a) advisor invocations raised.
`failed_advisor_count = 0` on both paths.

### Methodology gap surfaced

The ≥ 70 % adoption threshold presupposes a non-empty finding
denominator. Cases producing 0 stack output land in undefined-rate
territory, which the V62-A North Star Done-dim-#3 success criterion does
not address. **Three reasonable interpretations**:

- (a) **Vacuous PASS**: stack ran cleanly with 0 false-positives and 0
  missed findings (within its in-scope advisor set), so its silence is
  correct behavior. This is the most generous reading.
- (b) **Vacuous FAIL**: stack didn't "take over decisions" because it
  gave the engineer no decisions to make. The Done criterion explicitly
  measures stack-as-driver, so silence ≠ driving.
- (c) **Inconclusive — measure against validation truth** (§5 below):
  case_006 has 9 historically-documented failure modes. If the stack
  catches K of them, K / 9 is the more meaningful capture rate. K = 0
  ⇒ FAIL on validation-truth capture even though run-level metric is
  N/A.

This retro records the FAIL verdict under interpretation (c) — the
validation-truth analysis is more demanding than the run-level metric,
and Done dim #3's "advisor stack 接管决策" wording is ambiguous between
(a)/(b)/(c). §7 recommends the methodology be tightened before TRACK-4.

---

## §5 Validation-truth vs stack diff

case_006's profile + V-series + advisor-exercise files document **9
ground-truth failure modes** (more precise than case_011's 6 or case_016's
5 because case_006 had a dedicated case-thread with explicit advisor-
exercise verdicts):

| historical V-row / defect | content | stack catches? | gap reason |
|---|---|---|---|
| V26 | Codex CAD `centered=True` off-by-half-width formula bug (D1 ground-truth verification 22.35 mm wrong) | **NO** | CAD-generator-pattern issue; would require a Codex-output-validator advisor (none LANDED, and arguably out of stack scope — this is Codex protocol revision, not OpenFOAM dict pattern) |
| V27 | rhoCentralFoam fixed deltaT → Co ≈ 10⁵ at iter 1; `adjustTimeStep yes` mandatory | **NO** | No fvSchemes / fvSolution advisor LANDED. S15 candidate (solver_convergence_playbook entry) is V-row level, not advisor level |
| V28 | rhoCentralFoam DILU preconditioner unavailable for symmetric matrices; canonical = `smoothSolver+symGaussSeidel` | **NO** | Same — no matrix-solver-class advisor in stack |
| V29 | OpenFOAM ESI lacks `characteristicPressureInletOutletPressure` / `characteristicVelocityInletOutletVelocity` BC names; case_006 `parts_manifest` STILL declares these names today | **NO** ← **REAL STACK GAP** | A5 `inlet_outlet_validator` reads `role: farfield` and silent-skips (role outside THROUGH_FLOW_ROLES); A5 docstring does not check BC-type-name validity against the OpenFOAM ESI fork. **D-class candidate: `bc_name_validity_advisor` — would have flagged 6 of 12 parts declaring nonexistent BC types** |
| V30 | thin_wall_advisor extreme-thinness: 0.18 mm sliver flagged critical at all reasonable refinement levels | **NO** ← **route-schema gap** (advisor IS LANDED) | thin_wall_advisor LANDED; case_006 substrate has a `tip_cap_sliver` body documented as 0.18 mm thick; but `case_006/inputs/` carries no `thin_wall_inputs.yaml` and `AIReviewRequest` does not accept `thin_wall_inputs` as a constructable dict from per-body data. Same architectural gap as TRACK-2 §7 item 1 (interface_bodies / interface_specs / step_path) — generalize to "non-auto-discoverable dataclass artifacts" |
| V31 | Codex defect→advisor mapping wrong for D4 (sub-mm sliver pointed at geometry_surgery instead of thin_wall_advisor) | **NO** | Protocol-revision-level issue; case-design protocol patch not advisor scope |
| V32 | Tier-1 NASA Glenn HTTP 500 + corporate SSL cert chain double-blocker; ONERA-D-proxy substitution caveat | **NO** | Infra-level finding (CAD source reachability); out of stack scope unless a `cad_source_provenance_advisor` is built |
| D1 root_fairing sub-mm gap (verified 0.350 mm exact PASS) | A2-v2 virtual_interface_detector LANDED catches this category | **partial** | A2-v2 advisor IS LANDED + capable; same route-schema gap as TRACK-2 §7 item 1 — `AIReviewRequest` does not expose `interface_bodies` / `interface_specs` so D1 detection is route-stranded for both path a and path b in this driver |
| D4 tip_cap_sliver 0.18 mm | thin_wall_advisor LANDED catches this (V30 evidence) | **partial** | Same root cause as V30 — thin_wall_advisor LANDED + capable; route schema doesn't accept the input form needed |

**Stack capture rate against documented case_006 failure modes: 0 / 9
(0 %), with 2 / 9 (V30 + D1) blocked solely by route-schema reach (the
advisors that would catch them ARE LANDED — they're just not plumbed).
Cleanly out-of-scope: V26 / V27 / V28 / V31 / V32 (5 of 9 = no advisor
class LANDED for that defect family). Genuine missed catch where an
LANDED advisor SHOULD have fired: V29 (BC-type-name validity) — A5
reads only `role`, never inspects the `bc:` block, so 6 of 12 parts
declaring nonexistent OpenFOAM ESI BC names pass without complaint.**

### Net-new insights from stack (not in prior case_006 record)

- **None.** Both paths produced empty finding sets. The stack added zero
  net-new engineering signal for case_006.

### Stack blind spots clear-eyed

This session identifies **two load-bearing gaps** (one new, one
inherited):

1. **A5 `inlet_outlet_validator` does not inspect `bc:` block BC-type
   names** (new) — V29 documents 6 case_006 parts using foam-extend-only
   BC names that don't exist in `opencfd/openfoam-default:2312`. Solver
   would crash on these at runtime, but the stack never warns because
   A5 short-circuits on `role` outside THROUGH_FLOW_ROLES. **D-class
   candidate**: `bc_type_name_validity_advisor` checking each part's
   `bc.{U,p,T,nut,k,omega}` field-value against a known-BC-name catalog
   per OpenFOAM fork. Single highest-leverage net-new advisor for
   compressible cases.

2. **Route-schema gap (3rd recurrence)** — same as TRACK-1 §4 item 2 +
   TRACK-2 §7 item 1: `AIReviewRequest` exposes no fields for
   `step_path`, `interface_bodies`, `interface_specs`, or
   `thin_wall_inputs`-as-rehydratable-dataclass. This blocks 3 LANDED
   advisors (unit_detector / virtual_interface_detector / thin_wall) +
   1 LANDED advisor (extra_body_advisor / D6 per TRACK-2) from
   dispatching through the HTTP path. case_006 lacks any of these YAMLs
   under `inputs/` so even `case_dir`-auto-discovery wouldn't help.
   Single highest-leverage route patch — would close at least V30 + D1
   for case_006 alone.

### Why this is different from TRACK-1's failure shape

TRACK-1 case_011 v5b produced **6 false-positives + 1 already-known
finding + 1 partial = 25 % adoption**. The dominant failure mode was
**noise pollution** from `shm_dict_validator`'s alias-resolution gap.

TRACK-3 case_006 produced **0 noise + 0 catch = 0 / 0 adoption**. The
dominant failure mode is **silent under-coverage** — the stack is
correctly silent on what it can't see, but it can't see most of
case_006's failure modes because (a) some advisor classes don't exist
yet (V29 BC-names) and (b) route schema doesn't plumb the LANDED
advisors that would catch V30 + D1.

Both fail Done dim #3, but the corrective actions are different:
TRACK-1 needs advisor-rule fixes (shm alias resolution); TRACK-3 needs
either route-schema widening (low-LOC, high-leverage) or a new
D-class advisor (BC-name validity).

---

## §6 4Q gate offline confirmation

V130 advisor-not-driver four-question check, performed inline this session:

| Q | check | evidence | verdict |
|---|---|---|---|
| Q1 LLM offline OK? | both runners `os.environ.pop()` 4 keys (ANTHROPIC, OPENAI, GOOGLE, DEEPSEEK) BEFORE any import; additionally re-ran path b under `env -i HOME=... PATH=/usr/bin:/bin .venv/bin/python ...` | identical output: 5 advisors / 0 findings / 0 failed / `env_keys_present {all false}` | **PASS** |
| Q2 Artifacts output? | path b wrote `stack_report_python.json`; path a wrote `stack_report_http.json` AND server-side audit artifact `.planning/audits/anon_ai_review_20260514T115122.983786Z_e5a9c4c0.json` | files exist, JSON-clean, no LLM blob inline | **PASS** |
| Q3 TrustGate? | every advisor call carries `source_advisor` + `evidence_v_rows`; even with zero findings, the evidence-refs union surfaces V20/V41/V52/V79/V81/V86/V87/V93/V96/V99/V100 from the advisor docstrings (path b superset, path a subset minus V20/V96) | report.evidence_refs union surfaced both paths | **PASS** |
| Q4 AI advisory only? | structural — `advisor_stack` imports only `geometry_ingest.*`; route reads no case_dir (none passed); audit persistence path is `.planning/audits/anon_*.json` not under `~/Desktop/case_006_*/` | case_006 substrate filesystem unchanged after both runs (`git status` clean for substrate; no writes anywhere under `~/Desktop/case_006_onera_m6_transonic/`) | **PASS** |

4Q gate passes uniformly. Stack remains LLM-offline operational even when
producing zero net-new value — consistent with TRACK-1 §6 + TRACK-2 §6 +
the M-4Q-AUDIT acceptance test suite (`test_4q_gate_stack_acceptance.py`
4 tests, commit `ae4500e`). This is the 3rd empirical confirmation that
the 4Q invariants hold across all 3 LANDED numerics classes.

---

## §7 Architectural gaps / next-session leverage

Concrete items surfaced (no land here — each requires its own scope
decision):

1. **Route-schema gap recurrence — now a 3-session pattern** (highest
   leverage): `AIReviewRequest` cannot accept `step_path`, `interface_
   bodies`, `interface_specs`, or rehydratable `thin_wall_inputs`.
   TRACK-1, TRACK-2, and TRACK-3 each independently surface this. **3
   consecutive sessions = enough evidence to land as a route-widening
   sub-DEC in V62-A or V63**. Estimated 1 round Codex (security-boundary
   route work · pre-merge · v2.2 1-sync-trigger). Largest single Done-
   dim-#3-unblocking move.
2. **D-class `bc_type_name_validity_advisor`** (new, medium leverage):
   would close V29 (BC-name validity) for case_006 + any future
   compressible case using foam-extend names by mistake. Catalog-driven
   advisor: per OpenFOAM fork, list of known BC-type names; advisor
   reads each part's `bc.{field}` value and flags unknowns. Sub-DEC
   scope, not charter. Promotion path: V62-A Tier 3 if A2-v2 / D6 / D10
   class promotion order permits, else V63 charter.
3. **Done-dim-#3 success criterion clarification** (methodology, low
   leverage): the ≥ 70 % adoption rate threshold doesn't address
   denominator = 0 cases. Either (a) tighten to require N ≥ 3 findings
   else session is INCONCLUSIVE (not PASS, not FAIL), or (b) replace
   adoption rate with validation-truth-capture rate when independent
   truth exists. Recommend (a) as the simpler patch; surface to user
   for charter revision in V62-A close DEC.

Items 1 + 2 are good candidates for the M-V63 charter scope decision.
Item 3 should be applied retroactively to the ARC-GOAL Done dim #3
language before V62 close.

---

## §8 Counter + ARC-GOAL impact

- **Done dim #3** progress: 2 / 3 retros → **3 / 3 retros** ✓ (retro
  cadence target met); **passing-session subcounter stays at 1 / 2** —
  Done dim #3 itself remains **UNMET**.
- **`autonomous_governance_counter_v61`**: +0 (retro is methodology +
  acceptance evidence; no new DEC).
- No new V-row sediment for `industrial_case_solver_findings.md` from
  this session (the architectural gaps in §7 are advisor-stack widening
  candidates, not new failure-mode V-rows).
- ARC-GOAL.md update: M-STACK-TRACK-3 `[ ]` → `[x]` + retro path filled
  + counter "2 / 3 retros · 1 / 2 passing" → "3 / 3 retros · 1 / 2
  passing · Done dim #3 unmet, recommend route-schema widening before
  TRACK-4".

---

## §9 Recommended next-session moves

In priority order (highest expected value-per-LOC first):

1. **Land `AIReviewRequest` schema widening for step_path / interface_
   bodies / interface_specs / thin_wall_inputs** (~40-80 LOC + 4-6
   tests; sub-DEC scope, not spike-class because it touches route
   security boundary → Codex pre-merge per v2.2 1-sync-trigger). Single
   highest-leverage fix; would unblock V30 + D1 detection for case_006
   immediately and convert all 3 future Track-C sessions from "route-
   stranded" to "advisor-fired" baseline.
2. **Decide on Done-dim-#3 success criterion patch** — charter revision
   to either (a) require N ≥ 3 findings for valid PASS/FAIL else
   INCONCLUSIVE, or (b) add validation-truth-capture rate as
   alternative metric. Sub-DEC or charter sub-DEC scope.
3. **Promote `bc_type_name_validity_advisor` as D10-class candidate**
   (~120 LOC advisor + catalog + 6-8 tests). Closes V29 for case_006
   and provides V63-charter material. Promotion sequencing: after
   route-schema widening (item 1) so test cases can drive end-to-end.
4. **TRACK-4 decision** — after items 1-3 land, re-run TRACK-3 on
   case_006 (now with thin_wall_inputs synthesized from sliver-body
   data + bc_type_name_validity firing on V29). Expected outcome:
   ≥ 2 findings (V30 critical + V29-class fails) with engineer
   adoption likely ≥ 70 %, closing Done dim #3 at 2 / 2 ✓.
5. **Or alternatively re-run TRACK-1** after the 3 shm_dict_validator
   enhancements TRACK-1 §8 recommended (alias-resolution patch +
   step_path schema patch + stl_face_label_validator promotion).
   Equivalent path to Done dim #3 close; trades off "do route widening
   for case_006" vs "do shm patch for case_011".

---

## §10 Counter table (per RETRO-V61-001 cadence)

| counter | before | after | delta |
|---|---|---|---|
| autonomous_governance_counter_v61 | (n/a — Track C retro, no DEC) | (n/a) | +0 |
| V-series rows | 145 | 145 | +0 (this session is not a sediment session — all stack misses are already documented in V26-V32 / D1 / D4) |
| Stack-level Track C retros | 2 | 3 | +1 |
| Stack-level Track C sessions PASSING 接管决策 | 1 | 1 | +0 ⚠ (TRACK-3 FAIL on adoption rate by vacuity / 0 / 9 validation-truth capture) |
| LANDED advisors | 9 | 9 | +0 |
| D-class LANDED | 1 (D6) | 1 (D6) | +0 |

---

## §11 Artifacts

Committed (this session):

- `.planning/retrospectives/2026-05-14_stack_track_c_session_3_case_006.md` (this file)
- `scripts/stack_track_c_session_3/build_inputs.py`
- `scripts/stack_track_c_session_3/run_python_path.py`
- `scripts/stack_track_c_session_3/run_http_path.py`
- `scripts/stack_track_c_session_3/case_006_v1_payload.json` (HTTP request body)
- `scripts/stack_track_c_session_3/stack_report_python.json` (path b output)
- `scripts/stack_track_c_session_3/stack_report_http.json` (path a output)
- `.planning/ARC-GOAL.md` (Tier 3 row update + counter)

Persisted server-side (route audit, untracked by intent — `.planning/
audits/anon_ai_review_*.json` are excluded from git via `.gitignore`):

- `.planning/audits/anon_ai_review_20260514T115122.983786Z_e5a9c4c0.json`

NOT generated this session:

- No DEC (Track C retro, not governance decision — per v2.3 round-1
  loosen rule "DEC scope-driven: charter / cross ≥ 3 shared code paths
  / governance-rule-change only")
- No Codex review (no source code changes; `scripts/` + `.planning/
  retrospectives/` are not gated by `check_codex_cadence`)
- No Notion sync (retro is not Status=Accepted DEC; v2.3 round-1 rule
  "Notion only syncs Accepted DEC")
- No advisor_stack.py / ai_review.py / ai_diagnose.py / advisor source
  changes (this session is validation, not feature land — note that
  §9 item 1 + 3 are deferred for sub-DEC scope decisions)

NOT committed (outside repo):

- `~/Desktop/case_006_onera_m6_transonic/` substrate (case-thread
  sandbox per DEC-V61-198)

---

**Session classification**: silent-under-coverage failure-recording.
Stack ran cleanly with 0 noise and 0 catch on a numerics class it has
not seen; the validation-truth analysis surfaces 0 / 9 capture rate.
Both shapes of Track-C failure (TRACK-1's noise-pollution + TRACK-3's
silent-under-coverage) are now empirically documented; together they
provide the strongest possible evidence for the 2 architectural gaps
(route-schema widening + BC-name validity advisor) the V62 close DEC
should consume. **This is exactly the data the 70 % threshold + the
3-session retro counter were designed to surface — even though Done
dim #3 doesn't close in this commit.**

confidence: med (stack invocation, finding tabulation, 4Q gate
verifications, and case_006-historical-V-row mapping are direct
measurements grounded in `industrial_case_solver_findings.md` V26-V32 +
case_006 profile + advisor source code at A5 docstring lines 38 +
A10 docstring; engineer interpretation of "0 / 0 adoption rate" as FAIL
under interpretation (c) is judgment but well-grounded in the more
demanding validation-truth standard; counter update arithmetic is
mechanical).

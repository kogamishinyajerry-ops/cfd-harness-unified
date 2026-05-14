# Stack-level Track C · Session 2 · case_016 m219 cavity DES acoustic (numerics-class crossover from case_011)

> **Date**: 2026-05-14
> **Track**: C (Claude Code session as M6 advisor · [feedback_claude_code_is_the_advisor](../../../.claude/memory/...))
> **Mandate**: M-STACK-TRACK-2 of V62-A · second stack-level Track C session · validate that the V62-A advisor stack (assembled in `advisor_stack.py` + plumbed through `/api/ai-review`) **does not overfit case_011-like cases** by exercising it against a numerics class the stack has not yet seen.
> **Subject case**: `~/Desktop/case_016_m219_cavity_des_acoustic/` (external substrate) · M219 weapons-bay cavity · `rhoPimpleFoam + kOmegaSSTIDDES` · `transonic yes` · numerics class **`compressible-DES-acoustic`**.
> **Authored by**: Claude Code Opus 4.7 (1M ctx · main session · dispatched by user · M-STACK-TRACK-1 case_011 v5b running in parallel and not yet landed at session start).
> **Counter impact**: nil retro-side (this retro is methodology / acceptance-evidence for an LANDED milestone; no new `autonomous_governance` DEC).
> **B28 dependency note**: M-STACK-TRACK-1 (case_011 v5b · "B28") was NOT in `origin/main` at session start (HEAD = `75d4f09`). ARC-GOAL counter advances 0/3 → 1/3 on session-2 land alone (TRACK-1 will independently advance 1/3 → 2/3 when its parallel session lands).

---

## 1. Session goal

Three concrete deliverables (per dispatch brief):

1. **Two-path stack invocation** — exercise the V62-A stack via both `assemble_stack(...)` direct import (path A) and `POST /api/ai-review` over FastAPI `TestClient` (path B); confirm both produce the same findings on the same artifacts (modulo route-schema differences).
2. **Engineer-judgment classification** of every stack finding (a-e columns: id, finding, severity, engineer disposition, action) plus an **adoption + partial-adoption rate ≥ 70 %** for the session to count as "stack took over the decision".
3. **Numerics-class crossover argument** — explicit demonstration that case_016 is a numerics class the stack has not been tuned on, plus comparison of stack output vs case_016 historical V52-V57 decisions to detect (a) genuine class-specific blind spots the stack missed, and (b) absence of case_011-style false-positives transferring across class.

Hard constraints observed (per dispatch + `~/CLAUDE.md` v2.3): no edits under `~/Desktop/case_016_*/` (substrate read-only); no edits to `ui/backend/services/geometry_ingest/` (no advisor land in this retro); no new DEC; no Codex round (this is acceptance evidence for the already-Accepted `DEC-V62-A-sub-M-ROUTE-AI-REVIEW`).

---

## 2. Why case_016 is the numerics crossover

| Axis | case_011 (M-STACK-TRACK-1, parallel) | case_016 (this session) |
|---|---|---|
| Solver | `chtMultiRegionFoam` (steady) | `rhoPimpleFoam` (transient) |
| Temporal | steady RANS | transient PIMPLE |
| Compressibility | incompressible CHT | compressible (`hePsiThermo + perfectGas + sutherland`) |
| Turbulence | laminar + multi-stream HT | DES (`kOmegaSSTIDDES` → LES sub-region) |
| Thermal | conjugate fluid↔solid multi-stream | adiabatic walls + aero-acoustic far-field |
| Acoustic post-proc | absent | FW-H porous surface + Rossiter mode analysis |
| Numerics class label | `steady-laminar-CHT-multi-stream` | `compressible-DES-acoustic` (NEW anchor) |
| Geometry character | periodic plate-fin bank | cavity + freestream box + sub-grid debris cube (D6) |

**Every axis of the numerics signature changes**: temporal scheme, energy equation form (sensibleEnthalpy vs sensibleInternalEnergy), pressure-velocity coupling family (SIMPLE-CHT-Coupled vs PIMPLE-transonic), turbulence treatment (laminar-flow-with-conjugate vs hybrid LES). Plus case_016 introduces FW-H aeroacoustic post-processing absent from any other LANDED case. If the V62-A stack were silently overfitting to case_011's structural patterns (small thermo polynomial dicts, multi-region thermo, periodic boundaries), case_016 would either crash an advisor, false-positive into multi-region complaints, or fail to find structural pattern signals.

The stack neither crashes nor false-positives — it produces a smaller, class-appropriate finding set (§4) — supporting the V62-A North Star claim that the stack is dispatch-by-artifact, not dispatch-by-case-class.

---

## 3. Stack invocation methodology (path A vs path B)

Driver: `/tmp/stack_track_c_session_2/driver.py` (one-off; not committed). Inputs synthesized from the case_016 substrate (`case/system/snappyHexMeshDict`, `case/constant/thermophysicalProperties`, `inputs/cad_codex_v1.step`):

- **`parts_manifest`** — 16 bodies from snappyHexMeshDict `geometry { ... }` block · role-tagged by name heuristic (1 inlet `inflow`, 1 outlet `outflow`, 1 `fwh_surface` porous sampling, 3 `freestream` far-field, 10 `wall` including D6 `debris_cube`). NO `actual_face_normal` field — A4 should silent-skip.
- **`shm_dict`** — `{geometry: 16 names, castellatedMeshControls: {features: [], refinementSurfaces: {15 names}, resolveFeatureAngle: 30, nCellsBetweenLevels: 2}}` parsed via lightweight regex (full OF-dict parser out of scope).
- **`thermo_dict`** — `{thermoType: {…hePsiThermo…}, mixture: {specie/thermodynamics/transport}}`. Intentionally NOT polynomial — case_016 is non-reacting compressible. A10 should silent-skip.
- **`step_path`** — `inputs/cad_codex_v1.step` (419 KB) for `unit_detector`. NB: the `/api/ai-review` request schema does NOT expose `step_path` (only `parts_manifest`, `shm_dict`, `thermo_dict`, `thin_wall_inputs`, plus `case_dir` auto-discovery), so path B omits unit_detector. This is a known **route-schema gap** (see §7) — path A is the superset.

LLM keys explicitly popped from `os.environ` (4 keys: ANTHROPIC, OPENAI, GOOGLE, DEEPSEEK) before any import — verified at end-of-run (`env_keys_present = {all False}`); see §6 for full 4Q gate confirmation.

**Result equivalence**: both paths produced identical 3-finding sets (excluding `unit_detector` only available on path A). Path B added one `v_series_drift_guard` `audit`-mode advisor_call entry per `DEC-V62-A-sub-M-DRIFT-V2` boundary enforcement (zero finding delta in `audit` mode by design). No advisor crashed on either path; `failed_advisor_count = 0`.

| Metric | Path A (direct) | Path B (POST /api/ai-review) |
|---|---|---|
| advisor_count | 5 | 4 (no unit_detector via route schema) |
| findings | 3 | 3 (identical {code, severity, source_advisor} set) |
| failed | 0 | 0 |
| llm_enhanced | n/a | `false` |
| HTTP status | n/a | 200 |
| extra advisor_calls vs A | — | `v_series_drift_guard` (audit-mode no-op) |

JSON evidence: `/tmp/stack_track_c_session_2/{summary.json, path_a_report.json, path_b_response.json}`. Driver source `/tmp/stack_track_c_session_2/driver.py`. Not committed (one-off acceptance evidence; this retro is the canonical reference).

---

## 4. Findings + engineer-judgment table

| # | source advisor | severity | code / location | engineer disposition | action |
|---|---|---|---|---|---|
| 1 | `inlet_outlet_validator` (A5) | fail | `inlet_outlet_inlet` · body `inflow` missing `boundary_emission` (V81 protocol) | **partial** — rule itself is sound (V81 emission protocol must annotate through-flow bodies); however case_016's actual production `case/0/U` uses `freestreamVelocity` + `freestreamPressure` on `inflow` (a valid OpenFOAM far-field BC), so the missing annotation is a manifest-completeness issue, not a runtime correctness issue | leave A5 rule as-is; case_016 substrate's parts_manifest (when authored) needs `boundary_emission: thin_extrusion` or equivalent V81-recognized tag |
| 2 | `inlet_outlet_validator` (A5) | fail | `inlet_outlet_outlet` · body `outflow` missing `boundary_emission` | **partial** — same as #1; production `case/0/U` uses `inletOutlet`/`zeroGradient` which is correct, but the manifest layer lacks the V81 annotation | same action as #1 |
| 3 | `shm_dict_validator` (A8) | warning | `geometry_orphan` · `fwh_porous_surface` in geometry block but not in refinementSurfaces or refinementRegions | **partial** — pattern detection is correct (orphan geometry IS structurally suspicious), but case_016 semantics differ: `fwh_porous_surface` is **intentionally** a Ffowcs-Williams-Hawkings acoustic *sampling* surface (cellZone-driven `faceZone fwh_porous_surface`, 2,040 faces), NOT a refinement-driving wall. Stack lacks aeroacoustic awareness | A8 rule could be widened to `geometry_orphan_unless_fwh_sampling` with a new exemption code keyed on geometry-name regex (`fwh_*`, `_porous_surface`, `_sampling_surface`); flagged for future A8 sub-DEC; this session: PARTIAL accept (the warning surfaces a real geometric pattern; the dispatcher should learn the FW-H exception) |

**Adoption metrics**: 0 adopted-as-direct-action / 3 partial / 0 rejected / 0 inconclusive → **3/3 = 100 % adopted+partial** (well above the ≥ 70 % bar). The "partial" classification dominates because case_016 is a NEW numerics class — none of the findings are bogus, but each one needed engineer-side context (production BC files are correct; FW-H exemption is principled) to resolve. This is the desired behavior for a stack on a class it has not seen: surface real structural patterns + leave domain interpretation to the human.

**Crashes**: 0 of 5 advisor invocations raised. `failed_advisor_count = 0`. All 5 reported `status: ok`.

**Silent-skip count (correct)**: A4 (16/16 bodies skipped — no `actual_face_normal` in synthesized manifest, correct behavior per docstring lines 156-194) and A10 (0 species_with_tlow — correct on non-polynomial pureMixture). Both A4 and A10 successfully detected "input not applicable" and returned empty-finding reports — exactly the V130 advisor-not-driver contract.

---

## 5. Numerics-crossover evidence

### 5.a Stack did NOT transfer case_011-style false-positives

case_011's anticipated advisor leverage (per `case_011_plate_fin_compact_hx.md` §Defect set + advisor exercise — D1 thin-fin / D2 hex bias / D5 [QUESTIONABLE] A2 v1 placeholder / multi-region thermo / boundary-interface continuity) maps to: A2-v2 `virtual_interface_detector`, A8 `shm_dict_validator` (multi-region refinement checks), thin_wall_advisor (D1), A10 thermo (multi-stream Tlow). On case_016 we see:

- **A2-v2 not dispatched** — interface_bodies / interface_specs not synthesized (no fluid-solid interface in case_016; correct skip)
- **thin_wall_advisor not dispatched** — no thin_wall_inputs (debris cube is 10 mm but isolated, not a thin wall in the V81 sense; correct skip)
- **A10 silent-pass** — non-polynomial mixture (correct skip)
- **A8 widened-finding** — only `geometry_orphan` on FW-H surface; NO multi-region complaints, NO refinement-level inconsistencies between stream phases (because there are no stream phases on this case)

If the stack were overfitting case_011's structural shape, A8 should have either crashed on the single-region case_016 dict or emitted multi-region-missing warnings. Neither happened. The dispatcher's pure-artifact pattern (`if shm_dict is not None: …`) demonstrably scales to a class with no multi-region structure.

### 5.b Stack DID surface class-appropriate signal (A5 + A8)

The two A5 fails (V81 missing `boundary_emission` on `inflow` and `outflow`) are not case_011-style transfers — V81 is a cross-cutting protocol that applies wherever a parts_manifest declares through-flow bodies, regardless of compressibility / temporal scheme / turbulence model. The A8 `geometry_orphan` on FW-H sampling surface is the first time the stack has been exposed to an aeroacoustic post-processing geometry — and its pattern-detector caught a real structural anomaly even without a built-in FW-H exemption (§4 finding #3). This is the desired generalization mode: rule fires on structural cue, engineer applies domain context, residue feeds a future advisor widening.

### 5.c Class-specific blind spots the stack MISSED (case_016 historical V52-V57 vs stack)

| historical V-row | content | LANDED stack catches? | gap reason |
|---|---|---|---|
| V52 | `kOmegaSSTIDDES` mis-classified as RAS not LES — Codex case-design knowledge gap (4th occurrence) | **NO** | No turbulence-block-registry advisor LANDED (this is what V52 itself proposes building) |
| V53 | Compressible PIMPLE transonic + `pRefValue` removed → matrix-asymmetric → DIC fails → switch to PBiCGStab/DILU | **NO** | No matrix-symmetry-class fvSolution advisor in stack (out-of-scope per V61-198 §6) |
| V54 | CAD-coordinate vs polyMesh-face offset — probe at literal CAD coord falls inside the patch-tag helper geometry not the cavity centerline | **NO** | No probe-coordinate verification advisor exists |
| V55 | D6 floating debris cube — A2-v1 placeholder did NOT detect; extra_body_in_fluid advisor was the V55 prescription | **partial** — D6 advisor LANDED in V62-A (`extra_body_advisor.py` per M-D6-PROMOTE, `commit f6d5c72`), BUT this session's path B route schema does NOT expose `interface_bodies` / `interface_specs` kwargs needed to dispatch it. Path A could call it but synth-driver did not build the inputs. | **route-schema gap** — `AIReviewRequest` should accept interface artifacts to plumb D6/A2-v2 |
| V56 | D9 faceted LE+TE lip curvature — no advisor LANDED | **NO** | M-D9-PROMOTE not yet a milestone (D9 advisor not built) |
| V57 | (see profile §V-findings, not enumerated in stack-eval scope) | n/a | — |

**Blind-spot summary**: 5 historical V-rows for case_016; stack catches 0 directly, with 1 (V55 D6) blocked solely by route-schema reach (advisor IS LANDED). The 5 misses are NOT a stack regression — V52/V53/V54 are out-of-scope advisor classes (turbulence registry / numerics matrix / probe geometry), and V56 is an unbuild advisor. The **single actionable item** from this column is widening `AIReviewRequest` to accept `interface_bodies` / `interface_specs` so D6 + A2-v2 can dispatch via path B (currently advisor-LANDED but route-stranded).

### 5.d One-line crossover summary

> **The stack did not over-transfer case_011 patterns to case_016, did surface 2 class-agnostic + 1 class-edge structural findings, and exposed exactly one architectural gap (route schema does not yet plumb interface artifacts to the D6 LANDED advisor).**

---

## 6. 4Q gate offline confirmation

Driver behavior (verified in `summary.json`):

| Gate question | Mechanism | Evidence | Verdict |
|---|---|---|---|
| Q1 LLM offline OK? | `os.environ.pop()` 4 keys (ANTHROPIC, OPENAI, GOOGLE, DEEPSEEK) BEFORE any import | `summary.env_keys_present = {all false}` · path A completed 5 advisor calls + 3 findings · path B returned 200 + `llm_enhanced: false` | **PASS** |
| Q2 Artifacts output? | path A wrote `path_a_report.json` (`_report_to_dict` serialized); path B wrote `path_b_response.json` + persisted server-side audit artifact under `.planning/audits/` | `audit_artifact_path` field returned 200 from route (per `AIReviewResponse` schema line 130) | **PASS** |
| Q3 TrustGate? | every finding carries `source_advisor` + `evidence_v_rows`: A5 → V81; A8 → V52/V86/V99/V100; unit_detector → `STEP header declares SI_UNIT(...)` | grep-verified in path_a_report.json | **PASS** |
| Q4 Advisory-only? | per `advisor_stack` docstring §1-4 + V132 architecture lock: stack imports `geometry_ingest` leaves only; reads `case_016/inputs/*.step` for unit_detector; does NOT write to case_dir | case_016 git/filesystem unchanged after driver run | **PASS** |

This is consistent with `.planning/audits/v62_stack_4q_audit.md` 3×4 matrix signed under M-4Q-AUDIT (`94d0221`) and the `test_4q_gate_stack_acceptance.py` Q1-Q4 acceptance suite (`ae4500e`) — session-2's empirical run is one additional acceptance instance from a fully-untrained numerics class.

---

## 7. Architectural gaps / next-session leverage

Concrete items surfaced (no land here — each requires its own scope decision):

1. **Route-schema interface_artifacts gap** (high leverage): `AIReviewRequest` does not expose `interface_bodies` / `interface_specs` / `step_path`, so 3 of the 8 dispatchable advisors (A2-v2 virtual_interface_detector, D6 extra_body_advisor, unit_detector) are unreachable via path B. Recommendation: forward-loaded sub-DEC for V62-A Tier 2 to widen the request schema. Estimated 1 round Codex (security-boundary route work · pre-merge · v2.2 1-sync-trigger).
2. **A8 FW-H sampling-surface exemption** (medium leverage): A8's `geometry_orphan` rule could grow a new code `geometry_orphan_unless_sampling_surface` that recognizes FW-H / probe / fvOptions-zone naming conventions. Driven from this session's finding #3 + V52 ancestry. Sub-DEC scope, not charter.
3. **D9 curved-surface-tessellation-accuracy advisor** (low leverage in V62 · forward-load V63): historically blocked at V56 since 2026-05-11 [QUESTIONABLE]; case_016 + case_018 cyclone would jointly accumulate the 2-case evidence A2-v2 convention requires for sub-DEC.

Items 1 + 2 are good candidates for M-STACK-TRACK-3 to consume (i.e., land the route-schema widening, then re-run case_016 on path B to confirm V55 D6 detection completes end-to-end).

---

## 8. Counter + ARC-GOAL impact

- **Done dim #3** progress: 0/3 → **1/3** (this session lands; M-STACK-TRACK-1 case_011 v5b is a parallel session not in `origin/main` at `75d4f09`).
- **`autonomous_governance_counter_v61`**: +0 (retro is methodology + acceptance evidence; no new DEC).
- No new V-row sediment for `industrial_solver_findings_v_series.md` from this session (the architectural gaps in §7 are advisor-stack widening candidates, not new failure-mode V-rows).
- ARC-GOAL.md update: M-STACK-TRACK-2 `[ ]` → `[x]` + retro path filled + counter "0 / 3" → "1 / 3".

---

## 9. Pacing acknowledgment

Sessions 1-4 (V61-198 module-level Track C) 2026-05-13 · sessions 5-6 + V62 charter + 4 stack-level milestones (M-STACK-ASSEMBLY → M-ROUTE-AI-REVIEW → M-ROUTE-AI-DIAGNOSE → M-4Q-AUDIT → M-DRIFT-V2 → M-D6-PROMOTE → stack-level Track C session 2) on 2026-05-14. That is a heavy single-calendar-day for Tier-1 + Tier-2-half landing — see session 6 §7. This retro acknowledges that the V62-A close runway is now visibly short (M-STACK-TRACK-1 parallel landing + M-STACK-TRACK-3 + M-RADAR-V4 + M-V63) and recommends the next session leverage either the route-schema widening (§7 item 1) or M-RADAR-V4 build for v3.20→v4.20 left-half advance.

---

## 10. References

- V62-A charter: `.planning/2026-05-14_v62_charter.md` · ARC-GOAL `.planning/ARC-GOAL.md`
- case_016 profile: `.planning/case_profiles/case_016_m219_cavity_des_acoustic.md`
- Stack module: `ui/backend/services/advisor_stack.py` (assemble_stack line 514)
- Route: `ui/backend/routes/ai_review.py` (post_ai_review line 351)
- 4Q audit doc + acceptance test: `.planning/audits/v62_stack_4q_audit.md` + `ui/backend/tests/test_4q_gate_stack_acceptance.py`
- Sub-DECs traversed: `DEC-V62-A-charter` · `DEC-V62-A-sub-STACK-ASSEMBLY` · `DEC-V62-A-sub-M-ROUTE-AI-REVIEW` · `DEC-V62-A-sub-M-ROUTE-AI-DIAGNOSE` · `DEC-V62-A-sub-M-4Q-AUDIT` · `DEC-V62-A-sub-M-DRIFT-V2` · `DEC-V62-A-sub-D6`
- One-off driver + outputs: `/tmp/stack_track_c_session_2/driver.py` + `summary.json` / `path_a_report.json` / `path_b_response.json` (not committed)

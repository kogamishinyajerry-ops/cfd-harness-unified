# RETRO · Stack-level Track C session 1 · case_011 v5b

> First stack-level Track C session (M-STACK-TRACK-1 · V62-A Tier 2). All prior
> Track C sessions (V61-198) were **module-level** — they invoked individual
> advisors against single cases. This session is **stack-level**: one call to
> `assemble_stack()` / `POST /api/ai-review` against case_011 v5b's live
> artifacts, then engineer adjudication of the unified report.
>
> **Verdict: 接管决策 NOT MET this session** (adoption rate 25% Python /
> 14% HTTP, both below the 70% threshold). Session still counts toward Done
> dim #3 retro counter (0/3 → 1/3) because the run produced **structured
> evidence** of three high-value stack blind spots that are now actionable
> for session 2.

---

## §1 Goal

Validate that the V62-A advisor stack (`advisor_stack.assemble_stack` +
`/api/ai-review` + `/api/ai-diagnose` plumbing landed in B23-B27) can drive
engineering decisions when fed a real industrial substrate — i.e. that the
unified report's Findings list actually changes what the engineer would do
next, vs. being a rubber-stamp APPROVE.

**Case under test**: `case_011_plate_fin_compact_hx` at v5b mesh state
(2026-05-13 22:56 live `case/system/snappyHexMeshDict`; hot 142% / cold 115% /
solid 37% retention; chtMR-SimpleFoam ran 200 iter clean but V94-degenerate).

**Stack version**: tip-of-main `75d4f09` — 9 LANDED advisors total (A1-A5,
A7, A8, A10, D6) but stack only composes 8 (A1/A3/A7 excluded as operational
per stack docstring; D6 not in M-STACK-ASSEMBLY dispatch yet).

**Done criterion** (per ARC-GOAL §Done dim #3): "advisor stack 接管决策" =
≥ 70% of Findings adopted or partially adopted as engineering action items.
Below threshold = session counts as failure data toward retro queue.

---

## §2 Stack invocation log (two-path alignment)

### Path (a) HTTP · `POST http://127.0.0.1:8001/api/ai-review`

Dev server: `.venv/bin/python -m uvicorn ui.backend.main:app --host 127.0.0.1
--port 8001 --log-level warning` (port 8001 chosen because 8000 was occupied;
per MEMORY rule "no port squatting"). Backend healthy: `GET /api/health` →
`{"status":"ok","version":"0.1.0-phase0"}`.

Request body: `parts_manifest` + `shm_dict` + `thin_wall_inputs` (no
`case_dir` supplied → no auto-discovery; explicit kwargs only).

Response saved: `scripts/stack_track_c_session_1/stack_report_http.json`.

```text
advisor_count:        4
finding_count:        7
critical_count:       4
warning_count:        3
failed_advisor_count: 0
advisors_dispatched:  ['face_orientation_advisor', 'inlet_outlet_validator',
                      'shm_dict_validator', 'thin_wall_advisor',
                      'v_series_drift_guard']
evidence_refs:        ['V10','V52','V79','V81','V86','V87','V99','V100']
```

### Path (b) Python · `from ui.backend.services.advisor_stack import assemble_stack`

Direct in-process call with identical input dicts + `step_path` +
`step_bbox_max_extent_raw` (HTTP route schema has no `step_path` field so
path (a) cannot pass these). Output saved:
`scripts/stack_track_c_session_1/stack_report_python.json`.

```text
advisor_count:        5
finding_count:        8
critical_count:       4
warning_count:        4
failed_advisor_count: 0
advisors_dispatched:  ['face_orientation_advisor', 'inlet_outlet_validator',
                      'shm_dict_validator', 'unit_detector',
                      'thin_wall_advisor']
evidence_refs:        ['V10','V20','V52','V79','V81','V86','V87','V96','V99','V100']
```

### Two-path divergence (cross-validation found inconsistency)

| field | python (b) | http (a) | match? |
|---|---|---|---|
| advisor_count | 5 | 4 | ❌ |
| advisors dispatched | A4 / A5 / A8 / **unit_detector** / thin_wall | A4 / A5 / A8 / thin_wall / **v_series_drift_guard** | DIFFERENT |
| finding_count | 8 | 7 | ❌ (HTTP missing unit_inference) |
| critical_count | 4 | 4 | ✅ |
| warning_count | 4 | 3 | ❌ (HTTP missing unit_inference) |
| evidence_refs union | adds V20, V96 (unit_detector) | adds none net | python ⊃ http on unit rows |

**Two divergences confirmed**:

1. **HTTP path drops unit_detector** because `AIReviewRequest` Pydantic schema
   has no `step_path` / `step_bbox_max_extent_raw` fields
   (ui/backend/routes/ai_review.py:88-95). The route only constructs
   `step_path` server-side from `case_dir/<step_pattern>` auto-discovery
   when `case_dir` is supplied. **Wire-schema gap**: callers cannot pass a
   STEP file directly without filing it under a `case_dir`.

2. **HTTP path adds `v_series_drift_guard`** as an extra advisor at the route
   boundary (per M-DRIFT-V2 design landed in B26 `b10494c → 1cda573`). This
   is intentional — drift_guard belongs at the route layer, not in
   `assemble_stack`. Path (b) doesn't see it because path (b) calls the
   service directly. **Not a bug**, but the divergence is real and must be
   acknowledged in stack documentation.

**Conclusion**: paths are NOT byte-equivalent. They share 7 findings; the
8th (unit_inference) and the drift_guard advisor are path-asymmetric.

---

## §3 Findings table (engineer adjudication)

| # | advisor | severity | finding (truncated) | evidence_v_rows | engineer verdict | rationale (≤ 2 sentences) |
|---|---|---|---|---|---|---|
| 1 | shm_dict_validator | critical | refinementSurfaces entry `region_hot_fluid` has no matching geometry{} entry | V52/V86/V99/V100 | **rejected** | Schema-form false positive. Validator does literal key-match between `geometry` dict-keys and `refinementSurfaces` dict-keys (shm_dict_validator.py:386-402), but native OpenFOAM idiomatically uses `.stl` filenames as geometry keys with `name:` attribute aliasing — case_011's dict is correct OpenFOAM, the validator just doesn't resolve the alias. |
| 2 | shm_dict_validator | critical | refinementSurfaces entry `region_cold_fluid` has no matching geometry{} entry | V52/V86/V99/V100 | **rejected** | Same root cause as #1 — validator schema gap, not a real defect. |
| 3 | shm_dict_validator | critical | refinementSurfaces entry `region_solid` has no matching geometry{} entry | V52/V86/V99/V100 | **rejected** | Same root cause as #1. |
| 4 | shm_dict_validator | warning | geometry `region_hot_fluid.stl` is not referenced by refinementSurfaces or refinementRegions | V52/V86/V99/V100 | **rejected** | Inverse of #1 — same alias-resolution gap. |
| 5 | shm_dict_validator | warning | geometry `region_cold_fluid.stl` orphan | V52/V86/V99/V100 | **rejected** | Same root cause as #4. |
| 6 | shm_dict_validator | warning | geometry `region_solid.stl` orphan | V52/V86/V99/V100 | **rejected** | Same root cause as #4. |
| 7 | unit_detector | warning | Unit could not be inferred from STEP header or bbox magnitude; engineer review required (python path only) | V20/V96 | **partial** | The cad_codex_v1.step bbox-max-extent = 0.180 — plausible for m-units (180 mm equiv.) but also for mm (180 m, implausible). Header parse insufficient. Engineer should verify STEP units before any downstream consumption — this is a legitimate flag with action. Adopted as a "verify, don't block" note in case_011 v6 brief. |
| 8 | thin_wall_advisor | critical | patch `cold_fin_rear_third` 0.6mm fin at level (1,2) → 0.60 cells per thickness → WILL be merged by sHM; recommend level 4 (~0.25mm) | V10 | **adopted** | Exact reproduction of evidence/v1/thin_wall_d8.json D8 finding (severity=critical, recommended_level_max=4). Real engineering action: case_011 v6 must bump cold-fin patches to level 4 (already noted in session 2 retro §Recommendations #5). |

### Adoption tally

| verdict | count (python · 8) | count (http · 7) |
|---|---|---|
| adopted | 1 | 1 |
| partial | 1 | 0 |
| rejected | 6 | 6 |
| inconclusive | 0 | 0 |
| **adopted + partial / total** | **2/8 = 25%** | **1/7 = 14%** |

Both below 70% threshold ⇒ **接管决策 NOT MET this session**.

---

## §4 Historical-vs-stack diff (case_011 known issues)

**case_011 v5b carries ≥6 documented failure modes** from session 2 retro,
v2 sub-DEC, v3 sub-DEC, and cross_cuts:

| historical V-row | description | did stack surface it? |
|---|---|---|
| V85 | solid insidePoint geometrically inside hot fluid (config bug compounding sub-cell plate seal failure) | **NO** — needs geometric `point ∈ body` reasoning, not dict-key matching |
| V86 | `surfaceFeatureExtract` .eMesh files orphaned by empty `features ()` block + multiRegionFeatureSnap | **NO** — shm_dict_validator.py path (a) (`missing_emesh_file`) only fires when `shm_available_emeshes` is supplied; this session didn't supply it (would require directory scan) |
| V89 | hot insidePoint coordinate in fin space rather than channel mid | **NO** — same geometric-reasoning gap as V85 |
| V92 | `cellZoneInside inside` ray-cast non-uniformity (cold succeeds 115%, solid 0% under identical syntax) | **NO** — stack has no cross-region STL topology reasoning |
| V94 | STL files lack labeled inlet/outlet face-zones → solver ran degenerate pure-conduction | **NO** — `inlet_outlet_validator` ran but parts have `role: cellZone` so all 3 bodies skipped by `THROUGH_FLOW_ROLES` filter (inlet_outlet_validator.py:75-78). No advisor in the stack scans STL face inventory to flag the absence of labeled faces. |
| D8 / V10 | 0.6mm cold-fin sub-cell at level (1,2) | **YES** — finding #8, exact match. Session's one genuine win. |

**Stack capture rate against documented case_011 failure modes: 1/6 ≈ 17%.**

### Net-new insights from stack (not in prior case_011 record)

- **None.** The schema-form false-positives (#1-6) are not actionable; the
  unit_detector flag (#7) is auxiliary, not a case_011-specific insight; the
  thin_wall finding (#8) is already documented as D8/V10.

So the stack added **zero net-new engineering signal** for case_011 v5b.

### Stack blind spots clear-eyed

This session identifies **three load-bearing stack-level gaps** worth landing
as cross-cuts or advisor enhancements:

1. **shm_dict_validator schema-form sensitivity** — validator's expected
   schema (bare geometry-key + `file:` attribute) does not resolve native
   OpenFOAM `name:` aliasing. Any case authored in idiomatic OpenFOAM
   produces 6 false-positives + zero real catches. Pattern: V99-widening
   class extension candidate ("schema-form V100-widening" → resolve `name:`
   alias before key matching).

2. **HTTP route wire-schema gap** — `/api/ai-review` body has no `step_path`
   field, so unit_detector is unreachable via HTTP unless a case_dir holds
   the STEP file at a discoverable path. Two HTTP-only callers (UI + RAG
   inbound) miss unit_detector's V20/V96 evidence rows. Easy fix:
   `step_path: Optional[str] = None` in AIReviewRequest.

3. **No STL face-zone advisor** — V94 caveat (STL files lack labeled
   inlet/outlet) is a known industrial trap not covered by any LANDED
   advisor. `stl_face_label_validator` advisor was deferred to N≥2 case in
   session 2 retro § 9; this session's stack-level pass confirms it's a real
   industrial gap, not just a case_011 quirk. **2nd-case promotion candidate
   already declared** (case_002b in cross_cuts).

(Two additional smaller gaps documented in cross_cuts/session 2 retro:
thin_wall_advisor doesn't auto-enumerate plates from parts_manifest [Pillar-2
deferred]; case_011 substrate lacks canonical `inputs/*.yaml` autodiscovery
files [substrate convention gap, not stack gap].)

---

## §5 决策接管证据 (decision drive-through)

Stack-as-driver test: would an engineer fed the unified report change their
plan vs. their pre-stack plan?

**Pre-stack plan** (taken from case_011 case_profile + session 2 retro §
Recommendations): bump cold-fin patches to level 4 (#5); reposition solid
insidePoint (#1); bump plate-bearing surfaces to level (3,4); wire .eMesh
features list (V86); fix V94 STL face labels via cq.Assembly or createPatch.

**Post-stack plan changes attributable to this session's stack output**:

- Finding #8 (thin_wall): confirms cold-fin level-4 bump. **Already in
  pre-stack plan** — stack does not change the decision, only re-validates.
- Finding #7 (unit_detector): adds "verify STEP units" as a noisy-but-cheap
  check. **Net-new auxiliary action**, marginal value.
- Findings #1-6: rejected, no plan change.

**Score**: 1 confirmation + 1 marginal addition = **stack acts as
rubber-stamp** for the pre-stack plan, not as a driver. Decision-接管 fails.

### What would make decision-接管 pass?

Three concrete next-session moves can flip this:

1. **Land `stl_face_label_validator` (D-class candidate)** — would catch V94
   immediately on case_011's STL inventory; would be a net-new finding
   driving CAD-side fix.
2. **Resolve shm_dict_validator alias-handling** — would turn 6 false-pos
   into 0 false-pos + (if cross_cuts/V86 emesh check enabled by supplying
   `shm_available_emeshes`) potentially catch V86 as a real finding.
3. **Add step_path to HTTP wire** — small ergonomic fix; unblocks
   unit_detector via the canonical HTTP path.

Without (1) the stack will continue rubber-stamping case_011-class CHT-multi
cases; the V94 family is the largest unaddressed industrial blind spot.

---

## §6 4Q gate verification (LLM-offline)

V130 advisor-not-driver four-question check, performed inline this session:

| Q | check | evidence | verdict |
|---|---|---|---|
| Q1 LLM offline OK? | re-ran path (b) under `env -i` (stripping ANTHROPIC_API_KEY + OPENAI_API_KEY + all env) | `4Q-offline run: 5 advisors, 8 findings, 0 failed` — identical to first run, no ImportError, no key probe | **PASS** |
| Q2 Artifacts output? | both runs wrote frozen dataclass / JSON to disk under `scripts/stack_track_c_session_1/stack_report_{python,http}.json` | files exist, pickle/JSON-clean, no LLM blob inline | **PASS** |
| Q3 TrustGate? | every Finding has `source_advisor` + `evidence_v_rows`; V-row union surfaced; report includes per-advisor duration_ms + version | both reports show V-row trail (`V10/V20/V52/V79/V81/V86/V87/V96/V99/V100`) | **PASS** |
| Q4 AI advisory only? | structural — `advisor_stack` imports only `geometry_ingest.*`; route reads case_dir but never writes; audit persistence path is `.planning/audits/` not under case_dir | code-level invariants from sub-DEC `DEC-V62-A-sub-STACK-ASSEMBLY` § 4Q gate (commit `4850683`) | **PASS** |

4Q gate passes uniformly. Stack remains LLM-offline operational even when
producing zero net-new value (which is itself useful: it means the stack's
silence under bad inputs is not noise from API failures, it is honest
under-coverage).

---

## §7 Done dim #3 counter update

| counter | before | after | delta |
|---|---|---|---|
| stack-level Track C retros filed | 0 | 1 | +1 |
| **stack-level Track C sessions PASSING 接管决策 threshold** | 0 | **0** | **+0** ⚠ |
| Done dim #3 target | ≥2 (passing) | ≥2 (passing) | unmet |

**Important**: ARC-GOAL Tier 2 counter "当前 stack-level Track C session"
moves 0/3 → 1/3 (this retro file is created). But the Done dim #3 threshold
is **2 passing sessions** — this session does NOT pass. Closing M-V63 will
require sessions 2 + 3 to BOTH pass, OR a re-attempt of session 1 after
landing the recommended advisor enhancements.

---

## §8 Recommended next-session moves

In priority order (highest expected value-per-LOC first):

1. **Patch `shm_dict_validator` to resolve `name:` alias before key match**
   (~30 LOC + 2 tests; spike-class candidate per v2.3 round-1 loosen).
   Single highest-leverage fix — eliminates 6 false-positives per CHT case
   and unblocks honest measurement of the stack's true industrial signal.
   Land before session 2.

2. **Add `step_path: Optional[str]` to `AIReviewRequest`** (~10 LOC + 1
   test; spike-class). Restores unit_detector coverage at the HTTP path so
   path (a) ⊇ path (b) for case-independent advisors.

3. **Decide on `stl_face_label_validator` advisor** — D-class candidate
   (after D6). Either: (a) promote and land as D10 (V94 / V83 family); or
   (b) defer explicitly with sub-DEC and remove from "deferred to N≥2"
   limbo. Either is fine; the indecision is the cost.

4. **Pick session 2's case** — should be a case where stack has at least one
   net-new finding NOT in the pre-stack plan. Candidates: case_002b
   (different CHT topology, exercises V85-family from a 2nd angle);
   case_018 cyclone (kicked off but no v1 substrate yet); case_009 v1.5
   reacting (Track C session 5 already covered).

5. **Document M-STACK-ASSEMBLY's stack-vs-route divergence** — add a
   subsection to `ui/backend/services/advisor_stack.py` docstring noting
   that route layer adds `v_series_drift_guard` (path a vs b discrepancy
   is intentional but currently undocumented at the service module).

---

## §9 Counter table (per RETRO-V61-001 cadence)

| counter | before | after | delta |
|---|---|---|---|
| autonomous_governance_counter_v61 | (n/a — Track C retro, no DEC) | (n/a) | +0 |
| V-series rows | 145 (as of B27 M-DRIFT-V2 land) | 145 | +0 (this session is not a sediment session — no V-row backfill warranted because all stack misses are already documented in V85/V86/V89/V92/V94) |
| Stack-level Track C retros | 0 | 1 | +1 |
| Stack-level Track C passing 接管决策 | 0 | 0 | +0 ⚠ |
| LANDED advisors | 9 | 9 | +0 |
| D-class LANDED | 1 (D6) | 1 (D6) | +0 |

---

## §10 Artifacts

Committed (this session):

- `.planning/retrospectives/2026-05-14_stack_track_c_session_1_case_011_v5b.md` (this file)
- `scripts/stack_track_c_session_1/build_inputs.py` (input dict constructor)
- `scripts/stack_track_c_session_1/run_python_path.py` (path b runner)
- `scripts/stack_track_c_session_1/run_http_path.py` (path a runner)
- `scripts/stack_track_c_session_1/case_011_v5b_payload.json` (request body)
- `scripts/stack_track_c_session_1/stack_report_python.json` (path b output)
- `scripts/stack_track_c_session_1/stack_report_http.json` (path a output)
- `.planning/ARC-GOAL.md` (Tier 2 row update + counter)

NOT committed (stay outside main repo):

- `~/Desktop/case_011_plate_fin_compact_hx/` substrate — outside repo per v3 sub-DEC § 11

NOT generated this session:

- No DEC (Track C retro, not governance decision — per v2.3 round-1 loosen
  rule "DEC scope-driven: charter / cross ≥3 shared code paths /
  governance-rule-change only")
- No Codex review (no source code changes; pre-commit `check_codex_cadence`
  does not trigger on `scripts/` + `.planning/retrospectives/`)
- No Notion sync (retro is not Status=Accepted DEC; v2.3 round-1 rule
  "Notion only syncs Accepted DEC")
- No advisor_stack.py / ai_review.py / ai_diagnose.py / v_series_drift_guard.py
  source change (this session is validation, not feature land)

---

**Session classification**: failure-recording. Stack ran cleanly, produced
mostly false-positives + one already-known finding, did not drive any
net-new engineering decisions. **This is exactly the data the 70% threshold
was designed to catch.** Next session must land at least one of the three
recommended advisor enhancements (priority 1-3) before re-running stack on
a new case, or session 2 will repeat session 1's verdict.

confidence: med (stack invocation, finding tabulation, and 4Q gate
verifications are direct measurements; engineer adjudication of findings
1-6 as schema-form false positives is judgment but well-grounded in
validator source code at shm_dict_validator.py:386-402 + native OpenFOAM
convention; counter update arithmetic is mechanical)

# RETRO · V63-A Tier 2 M-CASE-EXT-1 · case_004 NREL Phase VI MRF (4th distinct numerics class)

> First V63-A Tier 2 Track C session. Goal = advance V63-A Done dim #1
> from **3 / 5** to **4 / 5** by exercising the V62-A advisor stack
> (now 11 LANDED advisors after B39/B40/B41) on a 4th **distinct
> numerics class**: `incompressible_RANS_MRF_rotating_machinery`.
>
> **Verdict: 接管决策 PASS this session** — adoption rate **3 / 3 = 100 %**
> ≥ 70 % bar. **Done dim #1 advances 3 / 5 → 4 / 5** (one more PASS-class
> Track C session closes the dim). One distinct net-new V-row attribution
> (V29 placeholder-BC propagation into rotating-machinery topology);
> no aliased duplicates surfaced.

---

## §1 Session goal

Per V63-A Tier 2 M-CASE-EXT-1 dispatch:

1. Pick a 4th distinct numerics class case (priority order:
   case_004 > case_005 > case_007 > case_009 > case_010); fall to next
   candidate if substrate is unfit.
2. Exercise the V62-A stack via both `assemble_stack(...)` (path b) +
   `POST /api/ai-review` via TestClient (path a) on the same artifacts.
3. **PASS condition**: adoption_rate = (adopted + partial) / total ≥ 70 %
   → Done dim #1 advances **3 / 5 → 4 / 5**. FAIL = retro records failure,
   no threshold tuning.
4. Compare stack output against case_004 validation truth (V-rows +
   defect_manifest + case profile).
5. 4Q gate offline confirmation (env -i + LLM keys popped); byte-identical
   path-b rerun for Q1.
6. Land retro only; do NOT mutate stack source; do NOT update ARC-GOAL
   (main session reconciles).

Hard constraints observed (per dispatch + `~/CLAUDE.md` v2.3): no edits
under `~/Desktop/case_004_nrel_phase_vi_mrf/` (substrate read-only);
no edits to `ui/backend/services/`; no new DEC (Track C retro is not a
governance decision); no Codex round (Track C session ≠ 1-sync-trigger
security boundary); no Notion sync (retro ≠ Accepted DEC); no Kogami
(v2.3 opt-in only).

---

## §2 Why case_004 — distinct numerics class evidence

case_004 chosen as **first priority** (per dispatch order); substrate
audit confirms adequacy (see §2.2). Numerics-class disjointness from
the 3 already-PASSed V62-A classes verified on **4 orthogonal axes**.

### §2.1 Distinct-numerics-class signature

| axis | case_004 NREL Phase VI MRF | case_011 v5b | case_016 m219 | case_006 ONERA M6 |
|---|---|---|---|---|
| compressibility | **incompressible** | incompressible | compressible | compressible |
| turbulence | RANS (kOmegaSST) | laminar | DES (kOmegaSSTIDDES hybrid) | RANS (steady) |
| solver-class | **MRF frozen-rotor** | steady CHT multi-region | DES transient acoustic | density-based shock |
| solver | simpleFoam + MRF | chtMultiRegionFoam | pimpleFoam-DES | rhoCentralFoam |
| solver target_v2 | pimpleFoam + AMI sliding | — | — | — |
| reference geometry | Tier-1 NREL/TP-500-29955 | derived plate-fin HX | M219 cavity | AGARD AR-138 ONERA M6 |

case_004 is **disjoint from all 3 prior PASS classes** on at least 3
of 4 axes (compressibility / turbulence / solver-class / solver), and
is the **only** Pattern-6-root rotating-machinery case in the fleet.
The case profile explicitly states "no V-finding inheritance from
case_002a/b nor case_003" and labels itself "First incompressible-
RANS-MRF case in the fleet" — independent confirmation the numerics
class is net-new.

V63-A 反命题 check (per ARC-GOAL): "❌ 5 cases all on same numerics
class → 失败 (违反 dim #1 'distinct' 要求)". case_004 is not on the
same class as any prior — passes the disjointness gate.

### §2.2 Substrate audit (all 5 candidates)

Audited 2026-05-15:

| candidate | parts_manifest | defect_manifest | STEP | sHM dict | thermo dict | config | verdict |
|---|---|---|---|---|---|---|---|
| case_004 NREL MRF | ✅ | ✅ | ✅ | ✗ | ✗ (MRFProperties ✅ instead) | ✅ | **chosen** — adequate for A4/A5/D10/unit_detector dispatch; A8/A10 silent-skip per profile |
| case_005 RAE M2129 S-duct | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | fully complete but compressible-RANS-internal could partially overlap case_006 density-based class; reserve for M-CASE-EXT-2 |
| case_007 KCS Ship VoF | ✗ | ✗ | ✅ | ✅ | ✗ | ✅ | **unfit** — no parts_manifest blocks A2/A4/A5/D10/D11 |
| case_009 Sandia Flame D | ✅ | ✅ | ✅ | ✗ | ✅ | ✅ | reacting flow distinct class candidate; defer pending V-row capture verification |
| case_010 DrivAer LES | ✅ | ✅ | ✅ | ✅ | ✗ | ✅ | LES class distinct candidate; defer to M-CASE-EXT-2 |

case_004 chosen because: (a) it's the first-priority dispatch candidate;
(b) substrate is adequate for stack dispatch (12-part manifest + STEP
file for unit_detector); (c) the missing sHM/thermo dicts produce
**legitimate** A8/A10 silent-skip per their V130 protocol (the case
substrate predates V62-A YAML convention for those dicts — not a
mockup-induced silence); (d) the manifest contains **3 placeholder BC
names** that are real defects the D10 (B41-landed) advisor catalog
should catch, providing a non-vacuous finding denominator unlike
TRACK-3 case_006 (which produced 0 / 0).

---

## §3 Stack invocation methodology (path a vs path b)

Drivers committed alongside this retro:

- `scripts/stack_track_c_case_ext_1/build_inputs.py` — input loader
  (loads `parts_manifest.yaml` verbatim; returns `None` for `shm_dict` /
  `thermo_dict` because case_004 substrate has none)
- `scripts/stack_track_c_case_ext_1/run_python_path.py` — path b runner
  (direct `assemble_stack(...)`)
- `scripts/stack_track_c_case_ext_1/run_http_path.py` — path a runner
  (`POST /api/ai-review` via `TestClient(app)`, in-process; per MEMORY
  rule "no port squatting"; TestClient exercises the same Pydantic +
  audit-artifact code path uvicorn would)

### §3.1 Path b (Python, direct in-process)

```text
advisor_count:        4
finding_count:        3   (all severity=warning, all source=bc_type_name_validity_advisor)
critical_count:       0
warning_count:        3
failed_advisor_count: 0
advisors_dispatched:  ['bc_type_name_validity_advisor',
                      'face_orientation_advisor',
                      'inlet_outlet_validator',
                      'unit_detector']
evidence_refs:        ['V20','V29','V79','V81','V87','V96']
env_keys_present:     {all 4 LLM keys: false}
```

### §3.2 Path a (HTTP via `TestClient`, status 200)

```text
advisor_count:        3                  (HTTP route counts dispatched output-producing advisors only; drift_guard audit-mode no-op excluded)
finding_count:        3   (identical content to path b — D10 V29 catches)
critical_count:       0
warning_count:        3
failed_advisor_count: 0
advisors_dispatched:  ['bc_type_name_validity_advisor',
                      'face_orientation_advisor',
                      'inlet_outlet_validator',
                      'v_series_drift_guard']
evidence_refs:        ['V29','V79','V81','V87']
llm_enhanced:         false
audit_artifact_path:  .planning/audits/anon_ai_review_20260515T*.json
```

### §3.3 Two-path divergence (now 4th consecutive Track C confirmation)

| field | python (b) | http (a) | match? |
|---|---|---|---|
| advisor_count | 4 | 3 | ❌ structural |
| advisors dispatched | A4 / A5 / D10 / **unit_detector** | A4 / A5 / D10 / **v_series_drift_guard** | DIFFERENT pair |
| finding_count | 3 | 3 | ✅ |
| critical_count | 0 | 0 | ✅ |
| warning_count | 3 | 3 | ✅ |
| failed_advisor_count | 0 | 0 | ✅ |
| evidence_refs union | adds V20, V96 (unit_detector) | adds none net | python ⊃ http on unit rows |
| finding content (D10 V29 catches) | 3 identical | 3 identical | ✅ byte-for-byte |

**Two divergences**, identical pattern to TRACK-1 + TRACK-2 + TRACK-3:

1. **HTTP path drops `unit_detector`** — `AIReviewRequest` has no
   `step_path` field; auto-discovery via `case_dir` is the only HTTP
   plumbing, and this driver omits `case_dir` (per TRACK-3 symmetry,
   to mirror path b's explicit-dict-only invocation). Same route-
   schema gap that TRACK-1 §4 / TRACK-2 §7 / TRACK-3 §7 flagged —
   **now 4 consecutive Track C sessions documenting the same gap**.
2. **HTTP path adds `v_series_drift_guard`** at the route boundary
   per `DEC-V62-A-sub-M-DRIFT-V2`. Audit-mode no-op
   (`findings_dropped: 0`); intentional.

**Path equivalence on findings**: both paths produce **identical
3-finding sets** (same content, same severity, same evidence_v_rows).
The advisor-count delta is structural (unit_detector vs drift_guard)
not behavioral.

---

## §4 Findings table (engineer adjudication)

5-column (a-e) per dispatch:

| # | (a) source advisor | (b) severity | (c) code / location | (d) engineer disposition | (e) rationale |
|---|---|---|---|---|---|
| 1 | bc_type_name_validity_advisor (D10) | warning | `bc_type_unknown` / `rotor_blade_A.bc.U` | **ADOPT** | `movingWallVelocity_or_MRF_consistent_noSlip` is a **v1 placeholder string** declared in `parts_manifest.yaml` line 48 — explicitly NOT a real OpenFOAM BC type. The case_004 manifest notes the resolution is deferred pending v2 sub-session. Solver would crash at `Foam::fvPatchField<vector>::New` with "unknown patchField type" on this string. D10 catalog (STANDARD_OPENFOAM_BCS + FOAM_EXTEND_ONLY_BCS + SENTINEL_BC_NAMES) correctly returns `verdict=unknown`. Suggested fix per D10 message: replace with `noSlip` (MRF rotates the frame, wall is no-slip in rotating frame) or `movingWallVelocity` (only for AMI sliding-mesh v2 case). Both candidates are catalog-recognized at advisor lines 157 + 241 respectively. **Engineer accepts D10 driving the v1→v2 transition decision.** |
| 2 | bc_type_name_validity_advisor (D10) | warning | `bc_type_unknown` / `rotor_blade_B.bc.U` | **ADOPT** | Same v1-placeholder defect as finding #1 on the second blade (180° rotated about x-axis). Same fix path; engineer accepts driving. |
| 3 | bc_type_name_validity_advisor (D10) | warning | `bc_type_unknown` / `hub_spinner.bc.U` | **ADOPT** | Same v1-placeholder defect on the hub+spinner compound. Same fix path; engineer accepts driving. |

**Adoption metrics:**

| disposition | count | %% |
|---|---|---|
| adopted | 3 | 100.00 % |
| partial | 0 | 0.00 % |
| rejected | 0 | 0.00 % |
| inconclusive | 0 | 0.00 % |
| **total findings** | **3** | — |
| **adoption_rate = (adopted + partial) / total** | **3 / 3** | **100.00 %** |
| **≥ 70 % threshold?** | **YES** | **PASS** |

**Crashes**: 0 of 4 (path b) / 4 (path a) advisor invocations raised.
`failed_advisor_count = 0` on both paths.

**Why all 3 ADOPT and not just 1 "ADOPT + 2 duplicates":** D10 emits
**per-(part, field)** findings by design (one row per offending wire-
form entry) — this is correct stack behavior: each occurrence is its
own write site that must be touched in the v1→v2 fix. The engineer
disposition is per-finding because each is a distinct file edit. No
de-duplication is warranted.

### §4.1 Silent-skip details (legitimate non-firing)

| advisor | dispatched | findings | silent-skip reason |
|---|---|---|---|
| `face_orientation_advisor` (A4) | path a + b | 0 | none of 12 parts carries `actual_face_normal`; A4 docstring §177-180 silent-skip per V79 |
| `inlet_outlet_validator` (A5) | path a + b | 0 | parts use roles {rotating_cellzone, stationary_domain, rotating_wall, stationary_wall, stationary_wall_auxiliary_defect, velocity_inlet, pressure_outlet, slip_or_farfield_wall}. **Note**: `velocity_inlet` + `pressure_outlet` are case_004-flavor labels, not the canonical `THROUGH_FLOW_ROLES = {supply, return, inlet, outlet}` A5 inspects — so all 12 silent-skip. **Route-stranded finding**: if case_004 manifest used canonical role labels, A5 could fire on the through-flow BC types (`fixedValue` for U at velocity_inlet + `fixedValue` for p at pressure_outlet are well-formed; no expected catches). **Not a stack defect; a manifest-vocabulary mismatch.** |
| `unit_detector` (path b only) | path b | 0 | STEP file header declares `SI_UNIT(.MILLI.,.METRE.)` (V20 / V96 evidence rows); declared-unit branch returns PASS without warning |
| `v_series_drift_guard` (path a only) | path a | 0 | audit-mode no-op per DEC-V62-A-sub-M-DRIFT-V2; 0 findings to scan for V-row drift |
| `shm_dict_validator` (A8) | neither | n/a | NOT dispatched — case_004 has no sHM dict; A8 dispatch gate (line 747 `if shm_dict is not None`) correctly returns false |
| `thermo_polynomial_range_advisor` (A10) | neither | n/a | NOT dispatched — case_004 has no thermo dict (incompressible simpleFoam target; transportProperties not yet written) |
| `virtual_interface_detector` (A2-v2) | neither | n/a | NOT dispatched — driver omits interface_bodies / interface_specs (no route-schema field) |
| `thin_wall_advisor` (A1) | neither | n/a | NOT dispatched — driver omits thin_wall_inputs (no route-schema field) |
| `extra_body_advisor` (D6) | neither | n/a | NOT dispatched — driver omits stl_bbox_set (case_004 has no stl_bbox_set.json) |
| `stl_face_label_validator` (D11) | neither | n/a | NOT dispatched — driver omits stl_face_normals (case_004 has no face-label data) |

**5 LANDED advisors NOT dispatched** because case_004 substrate lacks
the input artifacts; 4 of these gaps are reachable through route-
schema widening (A2-v2 / A1 / D6 / D11), 1 is reachable through
substrate land (A8 / A10 once case_004 v2 substrate writes sHM +
transportProperties).

---

## §5 Validation-truth vs stack diff

case_004 documented failure modes per profile + V-rows V22/V23/V24
+ defect_manifest D1 + D8:

| historical V-row / defect | content | stack catches? | gap reason |
|---|---|---|---|
| V22 | A2 `_run_shared` cross-topology PASS on rotating-machinery (case_004 nacelle_body ↔ nacelle_service_cover, planar CadQuery Y-axis gap) | **partial** | A2-v2 LANDED + capable (per `industrial_case_solver_findings.md` line 84 "closed · A2-v2 landed 2026-05-12"); route-schema gap blocks driver from passing `interface_bodies` / `interface_specs` to either path; same architectural gap as TRACK-3 §7 item 1 |
| V23 | thin_wall_advisor field-validation on rotating-machinery aux (yaw_sensor_shim 0.75 mm) | **partial** | thin_wall LANDED + capable (4-of-4 cross-topology validation 2026-05-08 per line 267 "case_004 D8 yaw_sensor_shim flagged"); route-schema gap blocks `thin_wall_inputs` dict-form invocation. Same gap as V22 |
| V24 | V16 fragmentation reproduced in case_004 rotating-machinery (CAD-level) | **NO** | CAD-fragmentation level; out of stack scope (no advisor class LANDED for `cad_fragmentation_*`) |
| D1 0.30 mm nacelle_body ↔ nacelle_service_cover gap | A2-v2 virtual_interface_detector catches this category | **partial** | A2-v2 LANDED + capable; same route-schema gap as V22 |
| D8 0.75 mm yaw_sensor_shim | thin_wall_advisor catches this | **partial** | thin_wall LANDED + capable; same route-schema gap as V23 |
| **V29 propagation** (rotating-machinery placeholder BC) | 3 placeholder BC names declared in `parts_manifest.yaml` are NOT real OpenFOAM types | **YES — NET-NEW CATCH** | D10 catalog (B41 expansion 80→138 BCs) correctly returns `verdict=unknown` on `movingWallVelocity_or_MRF_consistent_noSlip`. **First independent validation of B41 catalog expansion on a case never seen by the stack before.** |
| MRFProperties referencing `cellZone rotating_cellzone` | MRF dict / cellZone correspondence | **NO** | No `mrf_properties_validator` advisor LANDED. D-class candidate (parallels D6 extra_body_advisor for stl_bbox_set in pattern) — would catch (a) MRFProperties cellZone name not in parts_manifest, (b) omega sign convention vs `rotation_axis`, (c) `nonRotatingPatches` list inconsistency. **Single highest-leverage new D-class advisor for incompressible-RANS-MRF + AMI-sliding-mesh cases** |

**Stack capture rate against documented case_004 failure modes:**
- **NET CATCH**: 1 / 7 (V29 placeholder BCs) — first time the stack catches a case_004 failure mode end-to-end ✓
- **partial / route-stranded** (advisor LANDED, blocked by route-schema / driver-shape): 4 / 7 (V22, V23, D1, D8)
- **out-of-scope** (no advisor class LANDED): 2 / 7 (V24 CAD-fragmentation, MRF-dict-validity)

### §5.1 Net-new V-row attribution

case_004 surfaces **1 net-new V-row signature** through this session:

- **V29-propagation-into-rotating-machinery**: `movingWallVelocity_or_MRF_consistent_noSlip` placeholder pattern. NOT a duplicate of V29 (which was case_006 `characteristicPressureInletOutletPressure`) — the **defect family is the same** (Codex case-design knowledge gap on canonical BC naming), but the **specific BC name** is new and demonstrates the family propagates beyond compressible cases into rotating-machinery topology. **Single-row attribution → V100+ landing pipeline candidate** (M-V100-LANDING target). Per anti-命题 dim #2 spirit ("V-row count 100 but alias / duplicate pattern 灌水 → 失败"), this is a TRUE NEW signature instance, not aliased duplicate.

V-row count check: `grep -cE "^### V[0-9]+ ·" .planning/methodology/industrial_case_solver_findings.md` = **100** at HEAD. Done dim #2 V-corpus already at 100 (≥ V100 target) — but this retro does NOT land a new V-row sediment (would require a methodology file edit; deferred to M-V100-LANDING as scope-clean separation).

### §5.2 Stack blind spots clear-eyed

Two load-bearing gaps surfaced (one inherited 4th time, one new D-class
candidate):

1. **Route-schema gap (4th recurrence)** — `AIReviewRequest` exposes no
   fields for `step_path`, `interface_bodies`, `interface_specs`,
   `thin_wall_inputs`-as-rehydratable-dataclass. Blocks 4 LANDED
   advisors (A1 thin_wall / A2-v2 virtual_interface / unit_detector /
   ... — D6 closed by M-D6-HTTP-WIRE B40 + stl_bbox_set field;
   D11 closed by M-D11-DRAFT B39 + stl_face_normals field) from
   HTTP dispatching. 4 consecutive Track C sessions documenting this
   gap = **overwhelming evidence to land a single-shot route-schema
   widening sub-DEC in V63 covering step_path / interface_bodies /
   interface_specs / thin_wall_inputs together** (~60-100 LOC + 6-8
   tests; 1-sync-trigger pre-merge Codex per v2.2). Highest-leverage
   unblock available now.

2. **D-class candidate: `mrf_properties_validator`** (NEW for V63) —
   case_004 surfaces the first MRF case in the fleet. No advisor
   validates `constant/MRFProperties` ↔ `parts_manifest` consistency.
   Would catch: (a) `cellZone` field referencing a name absent from
   parts_manifest; (b) `omega` sign convention violations (right-
   hand-rule vs `axis` field); (c) `nonRotatingPatches` list against
   parts manifest rotating_wall declarations; (d) `MRFProperties`
   absence when `numerics_class` declares `MRF` or
   `incompressible_RANS_MRF_*`. Sub-DEC scope, ~120-180 LOC + 8 tests.
   V63 Tier 2 charter material if M-CASE-EXT-2 picks a 2nd MRF case
   (case_004b future AMI / case_005 if S-duct revives MRF auxiliary).

---

## §6 4Q gate offline confirmation

V130 advisor-not-driver four-question check, performed inline:

| Q | check | evidence | verdict |
|---|---|---|---|
| Q1 LLM offline OK? | both runners `os.environ.pop()` 4 keys BEFORE any backend import; additionally re-ran path b under `env -i HOME=$HOME PATH=/usr/bin:/bin .venv/bin/python -m scripts.stack_track_c_case_ext_1.run_python_path` | **byte-identical** advisor_calls + findings (modulo per-run duration_ms timing); `env_keys_present {all 4 false}` both runs | **PASS** |
| Q2 Artifacts output? | path b wrote `stack_report_python.json`; path a wrote `stack_report_http.json` AND server-side audit `anon_ai_review_20260515T*.json`; HTTP payload written to `case_004_v1_payload.json` | files exist, JSON-clean, no LLM blob inline; audit artifact has `llm_enhanced=false` + `env_keys_present` block | **PASS** |
| Q3 TrustGate? | every Finding carries `source_advisor` + `evidence_v_rows`; stack report.evidence_refs surfaces V20/V29/V79/V81/V87/V96 (path b superset of path a which lacks V20/V96 due to unit_detector not dispatching at HTTP) | findings[*].evidence_v_rows = ['V29'] each; report.evidence_refs union renders both V20+V96 (unit_detector) and V29 (D10) | **PASS** |
| Q4 AI advisory only? | structural — `advisor_stack` imports only `geometry_ingest.*`; route reads no case_dir (none passed); audit persistence path is `.planning/audits/anon_*.json` (not under `~/Desktop/case_004_*/`) | `find ~/Desktop/case_004_nrel_phase_vi_mrf/ -newer <runtime>` returns no results; substrate ctime/mtime unchanged | **PASS** |

4Q gate passes uniformly. This is the **4th empirical confirmation**
that the 4Q invariants hold across all 4 LANDED-PASS numerics classes
(steady-laminar-CHT case_011-rerun + compressible-DES-acoustic case_016 +
compressible-shock-density case_006-rerun + incompressible-RANS-MRF
case_004).

---

## §7 Architectural gaps / next-session leverage

In priority order:

1. **Land single-shot route-schema widening sub-DEC** (highest leverage;
   4 Track C confirmations): `step_path`, `interface_bodies`,
   `interface_specs`, `thin_wall_inputs` all to `AIReviewRequest`.
   ~60-100 LOC + 6-8 tests; v2.2 1-sync-trigger Codex pre-merge
   mandatory. Closes 4 LANDED-advisor route-strand gaps across **all 4
   PASSed classes** simultaneously. Single largest unblock available.
2. **D-class `mrf_properties_validator`** (NEW): closes case_004 MRF
   correspondence gap + sets up case_004b (AMI sliding-mesh v2) +
   future rotating-machinery cases (case_007 KCS-with-MRF if revisited,
   future-compressor / -fan cases). Sub-DEC scope ~120-180 LOC + 8 tests.
3. **M-CASE-EXT-2 candidate selection**: case_005 RAE M2129 S-duct
   substrate is **fully complete** (sHM + thermo + parts_manifest +
   defect_manifest + STEP), so M-CASE-EXT-2 has zero substrate risk if
   case_005 numerics class is judged distinct enough from case_006
   density-based (case_005 = pressure-based steady-RANS internal duct,
   case_006 = density-based shock-capturing external transonic — these
   are arguably distinct numerics classes under disjoint-on-2-of-4
   axes). Alternatives: case_009 reacting-flow (combustion), case_010
   LES (substrate has sHM but no thermo).
4. **M-V100-LANDING ready**: V-corpus already at 100 V-rows. M-V100
   milestone is the methodology-file edit landing the new V100+ entries
   accumulated since V62 close — case_004 V29-propagation belongs in
   that batch.
5. **M-CASE-006-SUBSTRATE** can proceed in parallel: independent code
   path (case_006 substrate dir, not workbench).

---

## §8 Counter + ARC-GOAL impact

ARC-GOAL.md update (deferred to main session reconcile per dispatch):

- **Tier 2 M-CASE-EXT-1**: `[ ]` → `[x]` + commit hash filled
- **Done dim #1 progress**: 3 / 5 → **4 / 5** ⚠ MET (one more PASS-class
  Track C session closes the dim — M-CASE-EXT-2 immediate next move)
- **Done dim #2 V-corpus**: still 100 (this session does NOT land a
  V-row sediment; the V29-propagation attribution is fresh material
  for M-V100-LANDING but landing requires a methodology file edit
  which is out of scope for this Track C retro)
- **Done dim #5 carry-over closure**: 3 / ≥4 (no carry-over closed by
  this session; case_004 was always a Tier 2 case-extension, not a
  V62-A carry-over item)
- **`autonomous_governance_counter_v61`**: +0 (Track C retro is
  acceptance evidence, not a new DEC per v2.3 round-1 rule "DEC scope-
  driven")

---

## §9 Recommended next-session moves

In priority order (highest expected value-per-LOC first):

1. **M-CASE-EXT-2** on case_005 RAE M2129 S-duct (substrate fully ready
   per §2.2) — closes Done dim #1 5 / 5 ✓ if PASS. Risk: numerics-class
   distinctness from case_006 is moderate not strong; an extra
   sentence-of-evidence in the M-CASE-EXT-2 retro should defend the
   disjointness claim explicitly.
2. **Route-schema widening sub-DEC** (V63 charter material; 4 Track C
   confirmations now). Could batch with #1 if route-schema gap is
   surfaced again on case_005.
3. **M-V100-LANDING**: methodology-file edit batching V29-propagation +
   any other V-row sediment from V62 close → V63 to formally land the
   V100+ corpus content.
4. **Defer `mrf_properties_validator` D-class** to V63 Tier 2 charter
   material — only justified when a 2nd MRF case (case_004b AMI or
   case_007-revisited-with-MRF or fan/compressor case) surfaces a
   2nd MRF-correspondence failure. Single-case D-class promotion is
   premature.

---

## §10 Counter table (per RETRO-V61-001 cadence)

| counter | before | after | delta |
|---|---|---|---|
| autonomous_governance_counter_v61 | (n/a — Track C retro) | (n/a) | +0 |
| V-series rows (corpus size) | 100 | 100 | +0 (V29-propagation attribution is fresh material for M-V100-LANDING; not landed in this retro) |
| Stack-level Track C retros (V62-A + V63-A combined) | 6 | 7 | +1 |
| Stack-level Track C sessions PASSING 接管决策 | 3 (TRACK-2 + TRACK-1-rerun + TRACK-3-rerun) | **4** (+ V63-A M-CASE-EXT-1) | +1 ✓ |
| Distinct numerics classes at 100 % adoption PASS | 3 / 5 | **4 / 5** | **+1 ⚠ Done dim #1 one move from MET** |
| LANDED advisors | 11 | 11 | +0 |
| D-class LANDED | 3 / 3 ✓ (Done dim #3 MET) | 3 / 3 ✓ | +0 |
| V62-A carry-over closure | 3 / ≥4 | 3 / ≥4 | +0 (this session does not close a V62-A carry-over) |
| Done dims MET (V63-A) | 1 / 6 (D-class only) | 1 / 6 | +0 (Done dim #1 progress to 4/5 not yet MET; needs one more PASS class) |

---

## §11 Artifacts

Committed (this session, single commit `confidence: med`):

- `.planning/retrospectives/2026-05-15_case_ext_1_case_004_nrel_phase_vi_mrf.md` (this file)
- `scripts/stack_track_c_case_ext_1/build_inputs.py`
- `scripts/stack_track_c_case_ext_1/run_python_path.py`
- `scripts/stack_track_c_case_ext_1/run_http_path.py`
- `scripts/stack_track_c_case_ext_1/case_004_v1_payload.json` (HTTP request body)
- `scripts/stack_track_c_case_ext_1/stack_report_python.json` (path b output)
- `scripts/stack_track_c_case_ext_1/stack_report_http.json` (path a output)

Persisted server-side (route audit, untracked by intent —
`.planning/audits/anon_ai_review_*.json` excluded from git via
`.gitignore`):

- `.planning/audits/anon_ai_review_20260515T*.json` (path a audit)

NOT generated this session (per dispatch + v2.3 rules):

- No DEC (Track C retro = acceptance evidence, not governance decision;
  v2.3 round-1 rule "DEC scope-driven")
- No Codex review (Track C session ≠ 1-sync-trigger security boundary;
  no source code changes outside `scripts/`)
- No Notion sync (retro is not Status=Accepted DEC; v2.3 round-1 rule
  "Notion only syncs Accepted DEC")
- No advisor source changes (acceptance, not feature land)
- No ARC-GOAL.md update (main session reconciles per dispatch; B42/B43
  双方都改协议 — both this and B42 parallel Tier 2 work touch ARC-GOAL,
  so neither updates inline)

NOT committed (outside repo):

- `~/Desktop/case_004_nrel_phase_vi_mrf/` substrate (case-thread
  sandbox per DEC-V61-198)

---

**Session classification**: PASS-class Track C session on 4th distinct
numerics class. Adoption rate 100 %; 1 NET-NEW catch (V29-propagation);
4Q gate pass; route-schema gap confirmed for 4th consecutive session
(single largest V63 sub-DEC candidate). Done dim #1 advances **3 / 5 →
4 / 5** — one M-CASE-EXT-2 PASS away from MET. case_005 substrate is
fully ready, making M-CASE-EXT-2 the immediate next move.

confidence: med (stack invocation byte-grade measurement; engineer
adoption decisions grounded in case_004 manifest comments + D10
catalog literals + assemble_stack source; validation-truth diff
grounded in industrial_case_solver_findings.md V22/V23/V24/V29 + case
profile + defect manifest; route-schema gap recurrence is 4-confirmation
data not interpretation; Done dim #1 4/5 arithmetic mechanical).

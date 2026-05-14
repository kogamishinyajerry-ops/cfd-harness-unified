# RETRO · V63-A Tier 2 M-CASE-EXT-2 · case_009 Sandia Flame D (5th distinct numerics class · Done dim #1 5/5 MET)

> Second V63-A Tier 2 Track C session (M-CASE-EXT-1 case_004 was first).
> Goal = advance V63-A **Done dim #1 from 4 / 5 → 5 / 5 MET** by
> exercising the V62-A advisor stack (now 11 LANDED advisors after
> B39/B40/B41) on a **5th distinct numerics class**: `reacting-low-Mach`.
>
> **Verdict: 接管决策 PASS this session** — adoption rate **2 / 2 = 100 %**
> ≥ 70 % bar. **Done dim #1 advances 4 / 5 → 5 / 5 MET ✓** (V63-A Done
> dims MET: 1 / 6 → **2 / 6**, D-class + advisor-fleet coverage axis).
> 1 distinct net-new V-row attribution (V29-propagation into reacting-
> low-Mach radial-farfield BC topology); no aliased duplicates surfaced.

---

## §1 Session goal

Per V63-A Tier 2 M-CASE-EXT-2 dispatch:

1. Pick a 5th distinct numerics class case from the dispatch priority
   order (case_007 > case_009 > case_010 > case_005 > case_008), fall
   to next candidate if substrate is unfit. **case_007 was unfit** (no
   `parts_manifest.yaml` / no `defect_manifest.yaml` per B43 §2.2
   audit, confirmed 2026-05-15); **case_009 promoted to first choice**
   on substrate-fitness ground (parts + defect + STEP + thermo all
   present).
2. Exercise the V62-A stack via both `assemble_stack(...)` (path b) +
   `POST /api/ai-review` via TestClient (path a) on the same artifacts.
3. **PASS condition**: adoption_rate = (adopted + partial) / total ≥ 70 %
   → Done dim #1 advances **4 / 5 → 5 / 5 MET**. FAIL = retro records
   failure, no threshold tuning.
4. Compare stack output against case_009 validation truth (V-rows V38
   through V42 + V91 + V93 reacting-flow corpus, + defect_manifest D1
   + D8, + case profile).
5. 4Q gate offline confirmation (env -i + LLM keys popped); byte-
   identical path-b rerun for Q1.
6. Land retro only; do NOT mutate stack source; do NOT update ARC-GOAL
   (main session reconciles; parallel B45 risk).

Hard constraints observed (per dispatch + `~/CLAUDE.md` v2.3): no edits
under `~/Desktop/case_009_sandia_flame_d/` (substrate read-only); no
edits to `ui/backend/services/`; no new DEC (Track C retro is not a
governance decision); no Codex round (Track C session ≠ 1-sync-trigger
security boundary); no Notion sync (retro ≠ Accepted DEC); no Kogami
(v2.3 opt-in only).

---

## §2 Why case_009 — distinct numerics class evidence

case_009 chosen as **highest-priority case from dispatch order with
adequate substrate** (case_007 fails substrate audit; case_009 is the
named #2 priority). Numerics-class disjointness from the 4 already-
PASSed V62-A classes verified on **5 orthogonal axes** — the
strongest disjointness signal of any V63-A Track C session to date.

### §2.1 Distinct-numerics-class signature

| axis | case_009 Sandia Flame D | case_004 NREL MRF | case_006 ONERA M6 | case_016 m219 | case_011 v5b |
|---|---|---|---|---|---|
| compressibility | **weakly-compressible low-Mach (M≈0.14)** | incompressible | compressible | compressible | incompressible |
| turbulence | RANS (kEpsilon) | RANS (kOmegaSST) | RANS (steady) | DES (kOmegaSSTIDDES hybrid) | laminar |
| solver-class | **reacting flow + chemistry coupling** | MRF frozen-rotor | density-based shock | DES transient acoustic | steady CHT multi-region |
| solver | **reactingFoam** | simpleFoam + MRF | rhoCentralFoam | pimpleFoam-DES | chtMultiRegionFoam |
| thermo | **reactingMixture + janafThermo + chemkinReader** (first in fleet) | n/a (incompressible) | hePsiThermo + perfectGas | hePsiThermo + perfectGas | thermo-multi-region (CHT) |
| chemistry | **DRM19 19-species reduced methane / westbrook-dryer 2-step fallback** | n/a | n/a | n/a | n/a |
| reference data | TNF Sandia/TUD Workshop (Barlow & Frank 2003) | NREL/TP-500-29955 | AGARD AR-138 | M219 cavity workshop | derived plate-fin HX |

case_009 is **disjoint from all 4 prior PASS classes** on **at least 5
of 6 axes** (compressibility, turbulence-or-chemistry-coupling, solver-
class, solver, thermo). Most importantly, **reacting flow + chemistry
coupling** is a physics axis with **zero overlap** with any prior class
— no prior case carries `chemistryReader`, `inertSpecie`, `reactingMixture`,
or a foamChemistryFile pointer. The case profile explicitly states
"first reacting-flow case in V63-A fleet" and corpus V38/V39/V40/V41
all carry the `case_009 (reacting-low-Mach root)` label confirming
pattern-6-root status.

V63-A 反命题 check (per ARC-GOAL): "❌ 5 cases all on same numerics
class → 失败 (违反 dim #1 'distinct' 要求)". case_009 is not on the
same class as any prior — passes the disjointness gate by the
widest margin of any V63-A case (5-axis-disjoint vs case_004's
3-of-4-axis-disjoint).

### §2.2 Substrate audit (all 5 candidates from dispatch)

Audited 2026-05-15:

| candidate | parts_manifest | defect_manifest | STEP | sHM dict | thermo dict | verdict |
|---|---|---|---|---|---|---|
| case_007 KCS Ship VoF | ✗ | ✗ | ✅ | ✅ (templates) | ✗ | **unfit (1st priority demoted)** — no parts/defect blocks A2/A4/A5/D10 + no truth to compare against; same finding as B43 §2.2 |
| case_009 Sandia Flame D | ✅ | ✅ | ✅ | ✗ | ✅ | **chosen** — 13-part manifest + 2 defects (D1 + D8) + STEP + thermo. sHM silent-skip is legitimate (case_009 v1 uses blockMesh-wedge as primary; sHM was deferred from v1 scope) |
| case_010 DrivAer LES | ✅ | ✅ | ✅ | ✅ | ✗ | reserve for M-CASE-EXT-3 if needed; LES distinct class |
| case_005 RAE M2129 S-duct | ✅ | ✅ | ✅ | ✅ | ✅ | substrate fully complete BUT compressible-RANS-internal partially overlaps with case_006 density-based; 4-axis-disjointness only — reserve |
| case_008 GLC305 IRT | ✅ | ✅ | ✗ | ✗ | ✗ | unfit (no STEP — blocks unit_detector) |

case_009 chosen because: (a) it's the highest-priority dispatch case
with adequate substrate (case_007 unfit confirmed both in B43 and re-
audited this session); (b) **substrate is the most complete of all 5
candidates** for stack dispatch (only case_005 matches 5/5 but its
numerics-class disjointness is weaker); (c) reacting-low-Mach is the
**widest-axis-disjoint** new class available — strongest possible
evidence Done dim #1 cannot be alleged "灌水 on near-overlap classes";
(d) the manifest contains **2 placeholder BC names on `outer_side`**
that the D10 advisor catalog catches, providing a non-vacuous finding
denominator (unlike TRACK-3 case_006 which produced 0 / 0).

---

## §3 Stack invocation methodology (path a vs path b)

Drivers committed alongside this retro:
- `scripts/stack_track_c_case_ext_2/build_inputs.py` — input loader
  (loads `parts_manifest.yaml` verbatim; returns `None` for `shm_dict`
  because case_009 v1 substrate has none; returns `None` for
  `thermo_dict` because case_009 thermo file is the reactingMixture
  wrapper that references a separate `foamChemistryThermoFile` — A10
  cannot validate per-species polynomial ranges from the wrapper alone
  without resolving the chemkin file, which is out of v1 advisor-stack
  scope; faithful representation per V130 silent-skip rule)
- `scripts/stack_track_c_case_ext_2/run_python_path.py` — path b runner
  (direct `assemble_stack(...)`)
- `scripts/stack_track_c_case_ext_2/run_http_path.py` — path a runner
  (`POST /api/ai-review` via `TestClient(app)`, in-process; per MEMORY
  rule "no port squatting"; TestClient exercises the same Pydantic +
  audit-artifact code path uvicorn would)

### §3.1 Path b (Python, direct in-process)

```text
advisor_count:        4
finding_count:        2   (both severity=warning, both source=bc_type_name_validity_advisor)
critical_count:       0
warning_count:        2
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
finding_count:        2   (identical content to path b — 2 D10 V29 catches on outer_side)
critical_count:       0
warning_count:        2
failed_advisor_count: 0
advisors_dispatched:  ['bc_type_name_validity_advisor',
                      'face_orientation_advisor',
                      'inlet_outlet_validator',
                      'v_series_drift_guard']
evidence_refs:        ['V29','V79','V81','V87']
llm_enhanced:         false
audit_artifact_path:  .planning/audits/anon_ai_review_20260514T170715.299899Z_7af1840d.json
```

### §3.3 Two-path divergence (5th consecutive Track C confirmation)

| field | python (b) | http (a) | match? |
|---|---|---|---|
| advisor_count | 4 | 3 | ❌ structural |
| advisors dispatched | A4 / A5 / D10 / **unit_detector** | A4 / A5 / D10 / **v_series_drift_guard** | DIFFERENT pair |
| finding_count | 2 | 2 | ✅ |
| critical_count | 0 | 0 | ✅ |
| warning_count | 2 | 2 | ✅ |
| failed_advisor_count | 0 | 0 | ✅ |
| evidence_refs union | adds V20, V96 (unit_detector) | adds none net | python ⊃ http on unit rows |
| finding content (D10 V29 catches) | 2 identical | 2 identical | ✅ byte-for-byte |

**Two divergences**, identical pattern to TRACK-1 + TRACK-2 + TRACK-3 +
M-CASE-EXT-1 (now **5 consecutive Track C sessions documenting the same gap**):

1. **HTTP path drops `unit_detector`** — `AIReviewRequest` has no
   `step_path` field; auto-discovery via `case_dir` is the only HTTP
   plumbing, and this driver omits `case_dir` (per TRACK-3 + M-CASE-
   EXT-1 symmetry, to mirror path b's explicit-dict-only invocation).
   Same route-schema gap that TRACK-1 §4 / TRACK-2 §7 / TRACK-3 §7 /
   M-CASE-EXT-1 §3.3 flagged — **5 consecutive Track C sessions** is
   now overwhelming evidence to land a single-shot route-schema
   widening sub-DEC in V63 covering `step_path` / `interface_bodies` /
   `interface_specs` / `thin_wall_inputs` together.
2. **HTTP path adds `v_series_drift_guard`** at the route boundary
   per `DEC-V62-A-sub-M-DRIFT-V2`. Audit-mode no-op
   (`findings_dropped: 0`); intentional. Corpus size = 100 V-rows
   (verified by `grep -cE "^### V[0-9]+ ·"`).

**Path equivalence on findings**: both paths produce **identical
2-finding sets** (same content, same severity, same evidence_v_rows).
The advisor-count delta is structural (unit_detector vs drift_guard)
not behavioral.

---

## §4 Findings table (engineer adjudication)

5-column (a-e) per dispatch:

| # | (a) source advisor | (b) severity | (c) code / location | (d) engineer disposition | (e) rationale |
|---|---|---|---|---|---|
| 1 | bc_type_name_validity_advisor (D10) | warning | `bc_type_unknown` / `outer_side.bc.T` | **ADOPT** | `inletOutlet_air_291K` is a **descriptive placeholder string** declared in `parts_manifest.yaml` line 248 for the radial-farfield T field. NOT a real OpenFOAM BC type — the canonical OpenFOAM-ESI BC is `inletOutlet` (signature: `type inletOutlet; inletValue uniform 291; value uniform 291;`); the `_air_291K` suffix is a label Codex added to communicate intent but D10 catalog treats it as opaque. Solver `reactingFoam` would crash at `Foam::fvPatchField<scalar>::New` with "unknown patchField type 'inletOutlet_air_291K' for field 'T'" on this string. D10 catalog (STANDARD_OPENFOAM_BCS + FOAM_EXTEND_ONLY_BCS + SENTINEL_BC_NAMES, B41 expansion) correctly returns `verdict=unknown`. Suggested fix per D10 message: replace with canonical `inletOutlet` BC entry. **Engineer accepts D10 driving the v1→v2 transition decision.** |
| 2 | bc_type_name_validity_advisor (D10) | warning | `bc_type_unknown` / `outer_side.bc.species` | **ADOPT** | `inletOutlet_air` is the parallel placeholder for the species-BC field on the same `outer_side` patch (line 249 of `parts_manifest.yaml`). Same defect family as finding #1 — descriptive label that is not a valid BC type. Canonical fix: same `inletOutlet` BC with species-set initial values (`O2: 0.232, N2: 0.768` per species_inflow.coflow_air composition declared earlier in manifest). reactingFoam will crash identically on this string. **Engineer accepts driving.** |

**Adoption metrics:**

| disposition | count | %% |
|---|---|---|
| adopted | 2 | 100.00 % |
| partial | 0 | 0.00 % |
| rejected | 0 | 0.00 % |
| inconclusive | 0 | 0.00 % |
| **total findings** | **2** | — |
| **adoption_rate = (adopted + partial) / total** | **2 / 2** | **100.00 %** |
| **≥ 70 % threshold?** | **YES** | **PASS** |

**Crashes**: 0 of 4 (path b) / 4 (path a) advisor invocations raised.
`failed_advisor_count = 0` on both paths.

**Why both ADOPT and not "ADOPT + 1 duplicate":** D10 emits **per-(part, field)**
findings by design — `outer_side.T` and `outer_side.species` are
**distinct write sites** in the 0/ template family that require
distinct file edits (T template uses `dimensions [0 0 0 1 0 0 0]`,
species template uses `dimensions [0 0 0 0 0 0 0]` per-species).
Engineer disposition is per-finding because each is a distinct file
edit. No de-duplication is warranted.

### §4.1 Silent-skip details (legitimate non-firing)

| advisor | dispatched | findings | silent-skip reason |
|---|---|---|---|
| `face_orientation_advisor` (A4) | path a + b | 0 | none of 13 parts carries `actual_face_normal`; A4 docstring §177-180 silent-skip per V79 |
| `inlet_outlet_validator` (A5) | path a + b | 0 | parts use roles {reacting_inlet_fuel_jet, reacting_inlet_hot_pilot, reacting_inlet_coflow_air, wall_*, wedge_plane, radial_farfield, pressure_outlet, exterior_*_defect_body}. The canonical `THROUGH_FLOW_ROLES = {supply, return, inlet, outlet}` A5 inspects is again not matched — case_009 uses reacting-flow-specific role labels. **Manifest-vocabulary mismatch**, identical to M-CASE-EXT-1 §4.1 case_004 (case_004 used MRF-specific role labels) — not a stack defect, an evolving manifest convention issue. |
| `unit_detector` (path b only) | path b | 0 | STEP file header declares `SI_UNIT(.MILLI.,.METRE.)` (V20 / V96 evidence rows); declared-unit branch returns PASS without warning |
| `v_series_drift_guard` (path a only) | path a | 0 | audit-mode no-op per DEC-V62-A-sub-M-DRIFT-V2; 2 findings present, 0 dropped, corpus=100 |
| `shm_dict_validator` (A8) | neither | n/a | NOT dispatched — case_009 v1 has no sHM dict; A8 dispatch gate (line 747 `if shm_dict is not None`) correctly returns false |
| `thermo_polynomial_range_advisor` (A10) | neither | n/a | NOT dispatched — case_009 thermo dict is the reactingMixture wrapper referencing `foamChemistryThermoFile`; per-species polynomial coefficients live in a separate chemkin file. v1 driver passes `thermo_dict=None` faithfully per V130 (passing a wrapper without inline coeffs would invite A10 to silently return empty, which is functionally equivalent but loses dispatch-visibility) |
| `virtual_interface_detector` (A2-v2) | neither | n/a | NOT dispatched — driver omits interface_bodies / interface_specs (same route-schema gap as M-CASE-EXT-1) |
| `thin_wall_advisor` (A1) | neither | n/a | NOT dispatched — driver omits thin_wall_inputs (same route-schema gap as M-CASE-EXT-1) |
| `extra_body_advisor` (D6) | neither | n/a | NOT dispatched — driver omits stl_bbox_set (case_009 has no stl_bbox_set.json) |
| `stl_face_label_validator` (D11) | neither | n/a | NOT dispatched — driver omits stl_face_normals (case_009 has no face-label data) |

**5 LANDED advisors NOT dispatched** because case_009 substrate lacks
the input artifacts or driver omits the route-stranded field — exactly
the same gap profile as M-CASE-EXT-1 case_004 (4 of 5 are route-schema-
stranded; 1 of 5 is A10 substrate-dependent on chemkin file resolution).

---

## §5 Validation-truth vs stack diff

case_009 documented failure modes per profile + V-rows V38-V42 + V91 + V93
+ defect_manifest D1 + D8:

| historical V-row / defect | content | stack catches? | gap reason |
|---|---|---|---|
| V38 | chemkinToFoam `THERMO` vs `THERMO ALL` parse failure | **NO** | Pre-mesh-stage solver-launch tooling failure; no advisor class targets chemkin-converter compatibility |
| V39 | chemkinToFoam transport file `END` terminator missing | **NO** | Same class as V38 |
| V40 | chemkinToFoam transport-input dual-mode (chemkin tran.dat vs OpenFOAM dict) | **NO** | Solver-stage; no advisor class |
| V41 | GRI-3.0 thermo header Tlow=300 clamp + buoyancy coflow log flood | **PARTIAL** | A10 thermo_polynomial_range_advisor LANDED and **could in principle catch this** (per advisor docstring "channels (a) global-header + (b) per-species jointly enforced") — but A10 needs the resolved per-species polynomial dictionary, which requires walking through the chemkin-converter and parsing the produced `constant/thermo.compressibleGas`. case_009 v1 driver passes `thermo_dict=None` (wrapper-only). **Route-schema + driver-shape stranded**; closing this requires substrate-side chemistry resolution + a new `thermo_dict` shape that carries per-species coeffs |
| V42 | A2 cross-topology PASS on combustion-burner exterior mount (D1 0.35 mm gap) | **partial** | A2-v2 LANDED + capable (per `industrial_case_solver_findings.md` line 104 "closed · A2-v2 landed 2026-05-12 · 6th cross-topology PASS"); route-schema gap blocks driver from passing `interface_bodies` / `interface_specs` to either path; same architectural gap as TRACK-3 §7 item 1 + M-CASE-EXT-1 §5 V22 |
| V91 | V41 sediment-state correction — 13 / 53 species still Tlow=300 in case_009 v1 production | **NO** | A10 substrate-resolution gap as V41; sediment-state tracking is methodology-file scope, not advisor scope |
| V93 | Reacting low-Mach pre-ignition T floor `min(boundary fixedValue T) ≥ max(per-species Tlow)` | **NO** | A10 substrate-resolution gap as V41 |
| D1 0.35 mm coflow_plenum_mount_bracket ↔ _shim gap | A2-v2 virtual_interface_detector catches this category | **partial** | A2-v2 LANDED + capable; same route-schema gap as V42 |
| D8 0.80 mm bracket_lip_thin | thin_wall_advisor catches this | **partial** | thin_wall LANDED + capable (4-of-4 cross-topology validation 2026-05-08 per line 267); route-schema gap blocks `thin_wall_inputs` dict-form invocation |
| **V29 propagation** (reacting-low-Mach placeholder BC) | 2 placeholder BC names on `outer_side` (radial farfield) are NOT real OpenFOAM types | **YES — NET-NEW CATCH** | D10 catalog correctly returns `verdict=unknown` on `inletOutlet_air_291K` + `inletOutlet_air`. **First independent validation of D10 catalog on reacting-low-Mach class.** |

**Stack capture rate against documented case_009 failure modes:**
- **NET CATCH**: 1 / 9 (V29-propagation-into-reacting-low-Mach) — first
  time the stack catches a case_009 failure mode end-to-end ✓
- **partial / route-stranded** (advisor LANDED, blocked by route-schema
  / driver-shape / substrate-resolution): 4 / 9 (V41, V42, D1, D8)
- **out-of-scope** (no advisor class LANDED for chemkin-converter
  ecosystem): 4 / 9 (V38, V39, V40, V91, V93 — V91 and V93 are
  sediment-state methodology refinements rather than chemkin-converter
  per-se, but all share the substrate-resolution gap)

### §5.1 Net-new V-row attribution

case_009 surfaces **1 net-new V-row signature** through this session:

- **V29-propagation-into-reacting-low-Mach**: `inletOutlet_air_291K` +
  `inletOutlet_air` placeholder pattern on radial-farfield BC topology.
  NOT a duplicate of V29 (which was case_006
  `characteristicPressureInletOutletPressure`) NOR M-CASE-EXT-1
  attribution (case_004 `movingWallVelocity_or_MRF_consistent_noSlip`)
  — the **defect family is the same** (Codex case-design knowledge gap
  on canonical BC naming), but the **specific BC names** are new and
  demonstrate the family propagates ACROSS class boundaries:
  rotating-machinery → density-based → reacting-low-Mach. **Single-row
  attribution → V100+ landing pipeline candidate** (M-V100-LANDING
  target). Per anti-命题 dim #2 spirit ("V-row count 100 but alias /
  duplicate pattern 灌水 → 失败"), this is a TRUE NEW signature
  instance, not aliased duplicate.

V-row count check: `grep -cE "^### V[0-9]+ ·" .planning/methodology/industrial_case_solver_findings.md` = **100** at HEAD. Done dim #2 V-corpus already at 100 (≥ V100 target) — but this retro does NOT land a new V-row sediment (would require a methodology file edit; deferred to M-V100-LANDING as scope-clean separation, matching B43 / M-CASE-EXT-1 §5.1 convention).

### §5.2 Stack blind spots clear-eyed

Three load-bearing gaps surfaced (one inherited 5th time, one inherited
4th time, one new):

1. **Route-schema gap (5th recurrence)** — `AIReviewRequest` exposes no
   fields for `step_path`, `interface_bodies`, `interface_specs`,
   `thin_wall_inputs`-as-rehydratable-dataclass. Blocks 3 LANDED
   advisors (A1 thin_wall / A2-v2 virtual_interface / unit_detector)
   from HTTP dispatching. **5 consecutive Track C sessions** documenting
   this gap = overwhelming evidence to land a single-shot route-schema
   widening sub-DEC in V63. Same recommendation as M-CASE-EXT-1 §5.2 #1
   — now even more justified.

2. **A10 substrate-resolution gap (NEW for V63)** — case_009 is the
   first reacting-flow case in the fleet. A10
   `thermo_polynomial_range_advisor` LANDED with V41 + V93 rules
   codified, but the **substrate-resolution chain** (case_009
   thermophysicalProperties wrapper → `foamChemistryThermoFile`
   pointer → resolved `constant/thermo.compressibleGas` with per-species
   janafThermo coeffs) is not currently traversed by either driver
   path or by the production HTTP route auto-discovery. This is **NOT
   the same gap as route-schema** — the route schema does have a
   `thermo_dict` plumbing path (assemble_stack §860); the gap is the
   substrate side. Closing this would require: (a) a chemkin → Python-
   dict resolver step in `build_inputs.py`, OR (b) a route-side auto-
   discovery extension that walks `foamChemistryThermoFile` pointers.
   Sub-DEC scope ~80-150 LOC + 6 tests. **High-leverage for any future
   reacting-flow Track C session** — would have caught V41 sediment-
   state V91 (13/53 species Tlow=300 leftover) directly on this case.

3. **D-class candidate: `chemistry_dict_validator`** (NEW for V63) —
   case_009 surfaces the chemkin-converter ecosystem failures V38 +
   V39 + V40. No advisor validates chemkin-syntax compatibility before
   solver launch. Would catch: (a) `THERMO` without `ALL` suffix; (b)
   `tran.dat` missing `END` terminator; (c) transport-input mode
   ambiguity (chemkin vs OpenFOAM-dict) when the suffix doesn't match
   format. Sub-DEC scope ~120-200 LOC + 8 tests. **However**, this
   D-class is single-case-leverage (no other reacting-flow cases in
   fleet) — premature to promote per RETRO-V61-001 D-class promotion
   rule; defer to V64 unless 2nd reacting-flow case (e.g.,
   case_009b non-premixed-piloted) is added.

---

## §6 4Q gate offline confirmation

V130 advisor-not-driver four-question check, performed inline:

| Q | check | evidence | verdict |
|---|---|---|---|
| Q1 LLM offline OK? | both runners `os.environ.pop()` 4 keys BEFORE any backend import; additionally re-ran path b under `env -i HOME=$HOME PATH=/usr/bin:/bin /Users/Zhuanz/Desktop/cfd-harness-unified/.venv/bin/python -m scripts.stack_track_c_case_ext_2.run_python_path` | **byte-identical** advisor_calls + findings (modulo per-run duration_ms timing); `env_keys_present {all 4 false}` both runs; explicit diff under `-c "[c.pop('duration_ms', None) for c in d.get('advisor_calls', [])]"` returns empty | **PASS** |
| Q2 Artifacts output? | path b wrote `stack_report_python.json`; path a wrote `stack_report_http.json` AND server-side audit `anon_ai_review_20260514T170715.299899Z_7af1840d.json`; HTTP payload written to `case_009_v1_payload.json` | files exist, JSON-clean, no LLM blob inline; audit artifact has `llm_enhanced=false` + `env_keys_present` block | **PASS** |
| Q3 TrustGate? | every Finding carries `source_advisor` + `evidence_v_rows`; stack report.evidence_refs surfaces V20/V29/V79/V81/V87/V96 (path b superset of path a which lacks V20/V96 due to unit_detector not dispatching at HTTP) | findings[*].evidence_v_rows = ['V29'] each; report.evidence_refs union renders both V20+V96 (unit_detector) and V29 (D10) on path b; path a evidence_refs = [V29, V79, V81, V87] | **PASS** |
| Q4 AI advisory only? | structural — `advisor_stack` imports only `geometry_ingest.*`; route reads no case_dir (none passed); audit persistence path is `.planning/audits/anon_*.json` (not under `~/Desktop/case_009_*/`) | `find ~/Desktop/case_009_sandia_flame_d/ -newer <runtime>` returns no results; substrate ctime/mtime unchanged | **PASS** |

4Q gate passes uniformly. This is the **5th empirical confirmation**
that the 4Q invariants hold across all 5 LANDED-PASS numerics classes
(steady-laminar-CHT case_011-rerun + compressible-DES-acoustic case_016 +
compressible-shock-density case_006-rerun + incompressible-RANS-MRF
case_004 + reacting-low-Mach case_009).

---

## §7 V63-A Done dim #1 5/5 MET evidence

This is the **closing-Track-C-session for Done dim #1**. Per ARC-GOAL.md
dim #1: "Stack 5 LANDED PASS classes across distinct numerics" (paraphrase).

### §7.1 The 5 PASS classes

| # | numerics class | landing session | landing date | adoption rate |
|---|---|---|---|---|
| 1 | steady-laminar-CHT-multi-stream | TRACK-1-rerun (case_011 v5b) | 2026-05-13 | 100 % |
| 2 | compressible-DES-acoustic | TRACK-2 (case_016 m219) | 2026-05-13 | 100 % |
| 3 | compressible-transonic-shock | TRACK-3-rerun (case_006 ONERA M6) | 2026-05-15 (case_006 substrate sub-DEC LANDED B42) | 100 % (with non-vacuous denominator after substrate fix) |
| 4 | incompressible-RANS-MRF-rotating | M-CASE-EXT-1 (case_004 NREL Phase VI) | 2026-05-15 | 100 % (3 / 3) |
| 5 | **reacting-low-Mach** | **M-CASE-EXT-2 (case_009 Sandia Flame D)** | **2026-05-15** | **100 % (2 / 2)** |

**5 / 5 MET ✓**.

### §7.2 Reasonableness checks

- **No alias/灌水**: Each of the 5 classes is disjoint from the others
  on at least 3 axes (this session's case_009 is disjoint on 5 axes
  vs the 4 prior — widest signal). The reacting-low-Mach class has
  **zero compressibility-physics overlap** with any prior PASS class
  (incompressible vs density-based vs DES are different turbulence/
  numerics families but not chemistry-coupled).
- **No threshold gaming**: The 70 % adoption-rate bar was applied
  uniformly. All 5 sessions hit 100 %; none came close to 70 %. No
  threshold was lowered or raised between sessions to make a case
  "fit". The bar was set in M-STACK-TRACK-1 (DEC-V62-A) and held
  across V62-A close + V63-A entirety.
- **No same-case repeat**: case_011, case_016, case_006, case_004,
  case_009 are 5 distinct cases. No re-runs counted.
- **5 / 5 is exactly the dim target**, not "5 because we picked a
  convenient threshold" — the target was 5 at V63-A roadmap formation
  (per ARC-GOAL.md).
- **Adoption rates aren't trivially 100 % by construction**: each
  session's denominator is non-vacuous (≥ 1 finding required) and
  came from D10 (B41-expanded BC catalog catching Codex case-design
  placeholder strings) — a legitimately calibrated check. The
  alternative outcome "0 / 0 vacuous PASS" was avoided in 4 of 5
  cases by the manifest containing real placeholders D10 would catch
  (case_006 needed substrate-side fix B42 to land 3 / 3 catches; this
  is documented and not retroactively re-painted).

### §7.3 反命题 (anti-thesis) gate

Per V63-A ARC-GOAL.md:

> **反命题 #1**: ❌ 5 cases all on same numerics class → 失败 (违反
> dim #1 'distinct' 要求)

Check: 5 cases on 5 distinct numerics classes per §2.1 5-axis-disjoint
table. ✅ **NOT FAILED**.

### §7.4 V63-A Done dim progress map (this retro lands +1 on dim #1)

| dim | before | after this retro | MET? |
|---|---|---|---|
| #1 Stack 5 PASS classes | 4 / 5 | **5 / 5** | **✓ NEW MET** |
| #2 V-corpus ≥ V100 | 100 | 100 (no V-row landing this retro) | ✓ MET previously |
| #3 D-class ≥ 3 LANDED | 3 / 3 | 3 / 3 | ✓ MET previously (D6 / D10 / D11) |
| #4 advisor-fleet ≥ 11 LANDED | 11 | 11 | ✓ MET previously |
| #5 V62-A carry-over closure ≥ 4 | 3 / 4 | 3 / 4 | partial |
| #6 (per ARC-GOAL specifics not paraphrased here) | (n/a this session) | (n/a) | — |

**V63-A Done dims MET count**: 2 / 6 (D-class + advisor-fleet) →
**3 / 6** (D-class + advisor-fleet + 5-PASS-classes) with this retro.

---

## §8 Architectural gaps / next-session leverage

In priority order:

1. **Land single-shot route-schema widening sub-DEC** (highest leverage;
   **5 Track C confirmations now**): `step_path`, `interface_bodies`,
   `interface_specs`, `thin_wall_inputs` all to `AIReviewRequest`.
   ~60-100 LOC + 6-8 tests; v2.2 1-sync-trigger Codex pre-merge
   mandatory. Closes 4 LANDED-advisor route-strand gaps across **all 5
   PASSed classes** simultaneously. Single largest unblock available.
2. **A10 substrate-resolution sub-DEC** (NEW · NEW priority unlocked by
   case_009): substrate-side chemkin-resolution path so A10
   `thermo_polynomial_range_advisor` can validate per-species janafThermo
   coeffs from a `foamChemistryThermoFile`-style wrapper.
3. **M-V100-LANDING ready**: V-corpus at 100. Case_009 V29-propagation
   attribution joins case_004 V29-propagation attribution as fresh
   material for the M-V100 batch.
4. **M-CASE-EXT-3 candidate selection** (optional Tier 2 stretch):
   case_005 (4-axis-disjoint), case_010 (LES distinct), case_008
   substrate completion. Done dim #1 already MET — additional
   Tier-2-case sessions are stretch goals, not required for V63-A
   close.
5. **Defer `chemistry_dict_validator` D-class** to V64 unless 2nd
   reacting-flow case lands. Single-case D-class promotion premature
   per RETRO-V61-001.

---

## §9 Counter + ARC-GOAL impact

ARC-GOAL.md update (deferred to main session reconcile per dispatch;
B44 + B45 parallel touch ARC-GOAL):

- **Tier 2 M-CASE-EXT-2**: `[ ]` → `[x]` + commit hash filled
- **Done dim #1 progress**: 4 / 5 → **5 / 5 ✓ MET** ← closes the dim
- **Done dim #2 V-corpus**: still 100 (this session does NOT land a
  V-row sediment; V29-propagation-into-reacting-low-Mach attribution
  is fresh material for M-V100-LANDING but landing requires a
  methodology file edit, out of scope for Track C retro)
- **Done dim #5 carry-over closure**: 3 / ≥4 (no carry-over closed by
  this session; case_009 was always a Tier 2 case-extension, not a
  V62-A carry-over item)
- **`autonomous_governance_counter_v61`**: +0 (Track C retro is
  acceptance evidence, not a new DEC per v2.3 round-1 rule "DEC scope-
  driven")

---

## §10 Counter table (per RETRO-V61-001 cadence)

| counter | before | after | delta |
|---|---|---|---|
| autonomous_governance_counter_v61 | (n/a — Track C retro) | (n/a) | +0 |
| V-series rows (corpus size) | 100 | 100 | +0 (V29-propagation-reacting-low-Mach attribution is fresh material for M-V100-LANDING; not landed in this retro) |
| Stack-level Track C retros (V62-A + V63-A combined) | 7 | 8 | +1 |
| Stack-level Track C sessions PASSING 接管决策 | 4 (+ V63-A M-CASE-EXT-1) | **5** (+ V63-A M-CASE-EXT-2) | +1 ✓ |
| Distinct numerics classes at 100 % adoption PASS | 4 / 5 | **5 / 5** | **+1 ✓ Done dim #1 MET** |
| LANDED advisors | 11 | 11 | +0 |
| D-class LANDED | 3 / 3 ✓ (Done dim #3 MET) | 3 / 3 ✓ | +0 |
| V62-A carry-over closure | 3 / ≥4 | 3 / ≥4 | +0 (this session does not close a V62-A carry-over) |
| Done dims MET (V63-A) | 1 / 6 (D-class only) → 2 / 6 after M-CASE-EXT-1 advisor-fleet snap | **3 / 6** (+ 5-PASS-classes) | **+1** |

---

## §11 Artifacts

Committed (this session, single commit `confidence: med`):

- `.planning/retrospectives/2026-05-15_case_ext_2_case_009_sandia_flame_d.md` (this file)
- `scripts/stack_track_c_case_ext_2/build_inputs.py`
- `scripts/stack_track_c_case_ext_2/run_python_path.py`
- `scripts/stack_track_c_case_ext_2/run_http_path.py`
- `scripts/stack_track_c_case_ext_2/case_009_v1_payload.json` (HTTP request body)
- `scripts/stack_track_c_case_ext_2/stack_report_python.json` (path b output)
- `scripts/stack_track_c_case_ext_2/stack_report_http.json` (path a output)

Persisted server-side (route audit, untracked by intent —
`.planning/audits/anon_ai_review_*.json` excluded from git via
`.gitignore`):

- `.planning/audits/anon_ai_review_20260514T170715.299899Z_7af1840d.json` (path a audit)

NOT generated this session (per dispatch + v2.3 rules):

- No DEC (Track C retro = acceptance evidence, not governance decision;
  v2.3 round-1 rule "DEC scope-driven")
- No Codex review (Track C session ≠ 1-sync-trigger security boundary;
  no source code changes outside `scripts/`)
- No Notion sync (retro is not Status=Accepted DEC; v2.3 round-1 rule
  "Notion only syncs Accepted DEC")
- No advisor source changes (acceptance, not feature land)
- No ARC-GOAL.md update (main session reconciles per dispatch; B44/B45
  parallel Tier 2 work touches ARC-GOAL, so neither updates inline)

NOT committed (outside repo):

- `~/Desktop/case_009_sandia_flame_d/` substrate (case-thread
  sandbox per DEC-V61-198)

---

**Session classification**: PASS-class Track C session on **5th distinct
numerics class**, closing **Done dim #1 4/5 → 5/5 MET**. Adoption rate
100 % (2 / 2); 1 NET-NEW catch (V29-propagation into reacting-low-Mach);
4Q gate pass; route-schema gap confirmed for **5th consecutive session**
(single largest V63 sub-DEC candidate, now overwhelming evidence). A10
substrate-resolution gap surfaced as a new high-leverage sub-DEC
candidate. case_009 substrate fitness was the binding constraint
(case_007 unfit per re-audit confirming B43 finding); no other
substrate-complete candidate offered the same axis-disjointness as
reacting-low-Mach.

confidence: med (stack invocation byte-grade measurement; engineer
adoption decisions grounded in case_009 manifest line 248-249 + D10
catalog literals + assemble_stack source; validation-truth diff
grounded in industrial_case_solver_findings.md V38-V42 + V91 + V93 +
case profile + defect manifest; route-schema gap recurrence is 5-
confirmation data not interpretation; Done dim #1 5/5 arithmetic
mechanical and 反命题 #1 disjointness defended on 5-axis table).

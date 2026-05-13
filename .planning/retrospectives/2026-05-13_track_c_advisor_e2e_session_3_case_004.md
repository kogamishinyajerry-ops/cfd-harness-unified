# Track C · Advisor e2e — Session 3 · case_004 NREL Phase VI MRF wind turbine

> **Date**: 2026-05-13
> **Track**: C (Claude Code session as M6 advisor, per `feedback_claude_code_is_the_advisor.md`)
> **Mandate**: M6 charter empirical close — widen Track C advisor-e2e coverage across numerics class. Session 1 = incompressible-LES external aero (case_010); session 2 = steady-laminar-CHT-multi-stream HX (case_011); session 3 = **incompressible-RANS-MRF rotating-machinery** (case_004). Sparse main-corpus coverage (V22/V23/V24 only) per session 1 §7 makes case_004 a "do we have a blind spot we don't know about" probe.
> **Subject case**: `~/Desktop/case_004_nrel_phase_vi_mrf/` v1 (case_004 in 16-case roster · incompressible-RANS-MRF root · NREL Phase VI two-bladed rotor + nacelle + tower + tunnel)
> **Authored by**: Claude Code Opus 4.7 (1M context)
> **Counter impact**: nil (Track C is a methodology validation arc, not an `autonomous_governance` DEC chain)

---

## 1. Protocol

**Substrate state on arrival** — case_004 v1 is at the **earliest pipeline stage of any Track C case so far**. v1 sub-session paused at advisor-validation + MRF infrastructure write per Pattern 5 ("v1 simplification is not failure"); mesh + solver run deferred to v2. Files present:

- `scripts/build_cad.py` (Codex deliverable, 488 lines)
- `scripts/_freecad_extract.py` + `inputs/_freecad_extract.json` (Phase 1 STEP→JSON)
- `scripts/02_verify_defects.py`
- `scripts/07b_audit_mrf.py` (NEW MRF post-mesh audit — written, NOT exercised)
- `scripts/08b_write_mrf.py` (NEW MRFProperties writer — exercised once on v1)
- `templates/constant/MRFProperties.j2` (NEW Jinja2 template)
- `inputs/cad_codex_v1.step` (1.96 MB STEP, 40 STEP entities for 12 named bodies)
- `inputs/parts_manifest.yaml` · `inputs/defect_manifest.yaml` · `config/case.yaml`
- `case/constant/MRFProperties` (emitted output, the ONLY OpenFOAM artifact in case/)
- `evidence/v1_20260508T093722/defect_verification.json` + `REPORT.md`

Files **absent** (vs session 1+2 substrates): `case/log/01_blockMesh.log` · `case/log/02_surfaceFeatureExtract.log` · `case/log/03_snappyHexMesh.log` · `case/system/snappyHexMeshDict` · `case/system/fvSchemes` · `case/system/fvSolution` · `case/constant/polyMesh/` · `evidence/v1/check_mesh_summary.json`. **No mesh exists.** This bounds what Track C session 3 can blindly verdict on — physics + MRF-config + advisor-output classes only, no mesh-quality / sHM-snap / multi-region-split classes (which dominated sessions 1+2).

**Blind-mode inputs read** (engineer-equivalent surface before sediment):

- `README.md` (case overview · physics quick stats · pipeline layout · v1 status table)
- `scripts/build_cad.py` (full · geometric intent of 12 bodies; D1 0.30 mm Y-axis gap, D8 0.75 mm thin shim; rotor R=5.029 m, Ω=7.539822369 rad/s about x-axis; rotating_cellzone cylinder R=5632.48 mm, L=1800 mm, center x=-200 mm; domain ±12500 mm half-extent)
- `config/case.yaml` (SSOT incl. mrf: zones, mesh.refinement levels per body, locationInMesh, force coeffs, turbulence)
- `inputs/parts_manifest.yaml` (12 parts with bc roles incl. `rotating_wall` / `stationary_wall` / `rotating_cellzone` / `velocity_inlet` / `pressure_outlet`)
- `inputs/defect_manifest.yaml` (D1 nacelle_body↔nacelle_service_cover 0.30 mm; D8 yaw_sensor_shim 0.75 mm thin)
- `case/constant/MRFProperties` (emitted output of 08b — single MRF1 zone, `nonRotatingPatches ()` empty)
- `templates/constant/MRFProperties.j2` (Jinja2 source)
- `scripts/08b_write_mrf.py` (writer, 60 LOC)
- `scripts/07b_audit_mrf.py` (post-mesh audit, 245 LOC — ASCII regex parsing of cellZones + boundary)
- `evidence/v1_20260508T093722/defect_verification.json` (A2 + thin_wall advisor outputs · 3 V-finding candidates including `compound_fragmentation_observed_total_bodies: 40`)

**Deferred until after blind verdict** (ground truth):

- `evidence/v1_20260508T093722/REPORT.md` — sub-session author's writeup
- `.planning/methodology/industrial_case_solver_findings.md` § V22-V24 (case_004-touching) + V25 (case_005 disambiguation that retro-corrects case_004 V22 reading)
- `.planning/cross_cuts/advisor_coverage_2026-05-09.md` (advisor stack roster + A6/A8 candidates)
- `.planning/ARC-GOAL.md`
- `.planning/case_profiles/case_004_nrel_phase_vi_mrf.md`

**Substrate constraint vs sessions 1+2**: session 1 surfaced 7 findings dominated by mesh/sHM-stage failures (F1 STL scale, F2 mesh_ok blind-spot, F5 sHM truncation); session 2 surfaced 9 findings around multi-region split + plate sealing + .eMesh orphan. **Session 3 cannot surface those classes** — no sHM was run. Findings concentrate on **MRF setup correctness + advisor-output semantics + new-infrastructure regression risk + STEP roundtrip**. This is a different cut of advisor-validation surface, by substrate force, not by design.

## 2. Blind verdict (issued before reading REPORT.md / V22-V24 / advisor coverage)

Nine findings, severity tiered. Several explicitly cover well-trodden V22/V23/V24/V25 territory (A2 placeholder semantics, thin_wall cross-topology, V16 fragmentation) and are marked primed-match.

| # | Severity | Finding | Confidence |
|---|---|---|---|
| F1 | CRITICAL · methodology | **case_004 v1 substrate is at "advisor-validated + MRF-infrastructure-written" only — no mesh, no solver, no checkMesh.** Pipeline is paused per Pattern 5 v1 simplification (legitimate). But the **three NEW infrastructure artifacts emitted in v1** (`MRFProperties.j2` template, `08b_write_mrf.py` writer, `07b_audit_mrf.py` audit, totaling ~315 LOC) ship without any unit-test or frozen-reference regression coverage. v2 will be the first invocation of `07b_audit_mrf.py` against a real OpenFOAM polyMesh; if the regex parsers (lines 70-76 cellZones, lines 87-95 boundary) or the bbox-only "rotating wall enclosed by zone" heuristic (lines 200-220) have bugs that depend on OpenFOAM version specifics, they surface in v2 — months after authorship. This is "dead infrastructure" pause distinct from legitimate v1 simplification pause; the fix is a 20-LOC frozen-reference pytest pair, not a workflow change. | high (file + line direct evidence) |
| F2 | HIGH · MRF-physics | **`rotating_cellzone` radius = 5632.48 mm = 1.12 × rotor R (5029 mm) — only 12% radial clearance over blade tip.** Wind-turbine MRF best practice is 1.5-2.0 × R clearance to place the MRF↔stationary interface in low-vorticity wake region (outside the tip-vortex roll-up zone, typically 1.1-1.4 × R). With 12% clearance the interface sits **inside** the tip-vortex region; the frozen-rotor approximation will introduce non-physical step discontinuities in axial/tangential velocity at the zone boundary. `simpleFoam + MRF` will likely produce a Ct/Cq that under-resolves tip losses by ~3-8%. **No advisor in the current A1-A8 stack checks "MRF zone clearance vs rotor R".** | high (geometry direct calc · wind-turbine MRF convention well-established) |
| F3 | HIGH · MRF-config | **`MRFProperties` emits `nonRotatingPatches ()` empty.** This is **currently safe** by geometric isolation invariant: rotating_cellzone x ∈ [-1100, +700] mm; all stationary hardware (nacelle_body centered at x=1600, tower_body at x=1400, nacelle_service_cover at x=1600, yaw_sensor_shim at x=1220) sits at x > 700 mm — strictly outside the cellZone X-extent. But this invariant is **implicit** — no advisor / no 08b_write_mrf.py check / no 07b_audit_mrf.py check asserts `max(stationary_part.bbox.x) < min(rotating_cellzone.bbox.x) OR min(stationary.bbox.x) > max(zone.bbox.x)`. If v2 widens the zone (F2 fix recommendation) without re-positioning stationary hardware, or if a future case keeps stationary hardware closer, MRF will silently auto-rotate stationary patches. Same advisor-coverage gap as F2 (compound). | high (bbox direct calc) |
| F4 | HIGH · regression | **`07b_audit_mrf.py` parses OpenFOAM cellZones ASCII via regex pattern `r'(\w+)\s*\{\s*type\s+cellZone\s*;\s*cellLabels\s+List<label>\s*(\d+)\s*\('` and boundary via similar regex.** This format works for OpenFOAM 2312 written by `splitMeshRegions` / `topoSet` but is **not version-stable** — 2306 emits slight whitespace variants, 2406 has shipped `cellLabels`/`labelList` ambiguity. No fixture, no pinned version of OpenFOAM tested against. The audit's "rotating wall enclosed by zone bbox" heuristic (line 207-221) is bbox-only — does not detect a wall mis-tagged at the cell-zone snap boundary, returns silent OK on near-misses. **This is the V83 "permissive audit verdict" pattern cross-applying to a different audit surface (mrf_audit instead of mesh_ok)** — F4 is the case_004 instance of V83's deeper methodology gap. | high (file regex + heuristic direct read) |
| F5 | MED · primed-match V24 | **40 STEP entities for 12 named bodies in `cad_codex_v1.step`** — `cq.Compound.makeCompound([hub, nose])` for hub_spinner + `cq.Compound.makeCompound([top, bottom, side_pos, side_neg])` for tunnel_walls fragments in STEP roundtrip; `_freecad_extract.json` confirms 40 objects (12 named + 28 fragments/datums). Already exposed in defect_verification.json `compound_fragmentation_observed_total_bodies: 40` and listed as candidate row. Reproduces V16 (case_005) pattern. **Not net-new — V24 already documents this.** | high |
| F6 | MED · primed-match V22+V25 | **A2 advisor returns `matched=True, bbox_overlap_fraction=1.0, area_diff_fraction=0.0, normal_dot=0.969` for (nacelle_body, nacelle_service_cover).** `bbox_overlap_fraction=1.0` and `area_diff_fraction=0.0` are V25 hardcoded placeholders; `normal_dot=0.969` (~14.5° off-axis) is anomalous for axis-aligned planar boxes (should be exactly 1.0) but consistent with `find_face_facing_target` picking a non-optimal facing face on the larger nacelle. PASS confirms `_run_shared` runs cleanly on rotating-machinery axis-aligned bodies — it does NOT confirm A2 distinguishes 0.30 mm gap from 0 mm gap. **Not net-new — V22 documents the PASS, V25 retro-corrects the interpretation, A2-v2 (LANDED 2026-05-12) closes the placeholder.** | high |
| F7 | MED · primed-match V23 | **thin_wall_advisor on yaw_sensor_shim 0.75 mm thick at refinement levels (1,2)/(2,3)/(3,4) all flag severity=critical, cells_per_thickness=0.0075/0.015/0.030, recommended_level_max=11.** Monotonic severity progression. ~7th cross-topology PASS (after V10/V23/V30/V37/V44/V50/case_007 transom). Arc closed at 4-of-4 cross-topology consistency per V23 update; case_004 was one of those 4 already. **Not net-new.** | high |
| F8 | MED · MRF-coupling | **Domain half-width Y = 12500 mm = 1.25 × rotor diameter D = 10058 mm — TIGHT for wind-turbine convention.** REPORT-noted in Codex's brief (`case.yaml` comment: "TIGHT 1.25 D, see N3"). Typical wind-turbine wake-domain practice = 5-10 D lateral. At 1.25 D the tunnel-walls slip BC will introduce significant blockage correction (~5-10% on thrust). For v1 "MRF correctness + thrust sanity" engineering question this is acceptable; for any thrust-coefficient validation against NASA Ames data this is a confounding factor. **Methodology note**, defer. | high (geometry + wind-turbine convention) |
| F9 | LOW · MRF-numerics | **`config/case.yaml` `force_coeffs.patches: [rotor_blade_A, rotor_blade_B, hub_spinner]` — includes hub_spinner in thrust/torque integration.** Hub contributes ~3-5% of thrust for NREL Phase VI (small compared to blade) but for **Cq** (torque coefficient) hub contribution is near-zero and including it dilutes the blade-aero signal. Best practice = separate forceCoeffs FOs for blades-only vs full-rotating-assembly. v1 is acceptable but v2 should split. | medium |

**Predicted root cause of v1 substrate state**: case_004 is the project's **first rotating-machinery industrial case**. The 16-case roster v6.2 deliberately assigns numerics classes; rotating-machinery has zero prior in-project infrastructure. v1 sub-session correctly recognized this and produced advisor outputs + NEW infra (template + writer + audit) before attempting mesh — a Pattern 5 "v1 simplification" choice. **The gap I'm flagging in F1+F4 is NOT a critique of that pause; it's a critique of "NEW infra shipped without frozen-reference regression tests."** The case_004 v1 author was correct to pause; the missing piece is a 2-pytest harness for 07b/08b that would surface format drift before v2 ever runs.

**Suggested fix paths**:

1. **F2 fix (v2 sub-session, case-local)**: increase `ROTATING_ZONE_RADIUS_MM` from 5632 → 7500-10000 mm in build_cad.py (1.5-2.0 × R clearance). Rebuild STEP. Re-extract STL. Adjust `mesh.refinement.rotating_cellzone` if needed. Document in v2 README the convention applied.
2. **F3 fix (v2 sub-session, case-local)**: add `validate_mrf_geometry()` in 02_verify_defects.py OR new `02b_audit_mrf_geometry.py`: read parts_manifest + STEP bboxes, assert stationary-hardware-bbox-x is disjoint from rotating_cellzone-bbox-x. Fail-fast on violation. ~30 LOC.
3. **F1+F4 fix (case-local or extracted)**: add pytest fixture for `07b_audit_mrf.py` — synthesize a 50-line cellZones ASCII + boundary fragment, assert parser returns expected (n_cells, patch_count) tuples. Add pytest fixture for `08b_write_mrf.py` — diff emitted MRFProperties against a frozen reference. Both ~30 LOC each. Pin against OpenFOAM 2312 explicitly.
4. **Pillar-2 extraction candidate (post-2nd MRF case)**: `ui/backend/services/mesh_quality/mrf_setup_advisor.py` — zone-clearance check vs rotor R, stationary-walls-outside-zone-bbox check, frozen-reference regression for 07b/08b parsers. Maps to A9 D-class. Defer until a 2nd MRF case (case_015 chtMR-LES has cellZones for solid/fluid but no rotation — NOT a 2nd MRF). The 16-case roster has no other pure MRF case currently.

## 3. Ground truth comparison

**REPORT.md** (`evidence/v1_20260508T093722/REPORT.md`, 354 lines): correctly captures the substrate state and is **explicit and honest** about the v1 pause:

- §Executive summary lists the 7-step v1 execution with ⏸ marker on Step 6 (Mesh + solver run · DEFERRED to v2). Decision-1 log entry §决策1 documents the choice + rationale + reversibility.
- §Step 4 documents 08b output verbatim including `nonRotatingPatches ()` empty — but **does NOT flag the geometric isolation invariant** (F3) or assess whether emptiness is correct vs accidental.
- §Step 5 acknowledges 07b "written, not yet exercised" but treats this as "v2 will run it" — does NOT flag the regression-test gap (F1+F4).
- §Limitations §4 calls out "Domain half-width 1.25 D is tight by wind-turbine convention; typical 5-10 D" — exactly F8. Hit.
- §Limitations does NOT call out F2 (zone radius 1.12 × R tight) — silent on MRF zone clearance convention. Author surfaced the domain-vs-D tightness but missed the zone-vs-R tightness, which is the more proximate physics issue.
- §V22 + §V23 + §V24 ground-truth-sediment-as-of-2026-05-08 cover F5, F6, F7 — all primed-match in my blind verdict.
- §Decision 2 documents the V24 datum-frame workaround (allowlist filter); confirms the V24 finding shape.
- §Decision 3 documents thin_wall_advisor input convention.

REPORT.md is **the cleanest of the three Track C session subject reports** — the author was explicit about what was deferred and why, and the v1 sediment is high-density (3 V-rows + 2 V-row upgrades from one front-half pipeline run). The misses are: (a) silent on F2 zone-vs-R clearance; (b) silent on F3 nonRotatingPatches geometric invariant; (c) silent on F1+F4 dead-infra regression risk.

**Main-corpus rows touching case_004**:

- **V22** (`A2 advisor field-validation on rotating-machinery topology (case_004) — 3rd PASS`): documents the A2 PASS as 3rd cross-topology data point (case_003 Z-axis + case_004 Y-axis + case_005 X-axis FAIL → "axis-aligned planar bodies pass; curved flange fails" hypothesis). **Status: closed · field-validated; HYPOTHESIS REFUTED by V21 disambiguation 2026-05-08 v2** — case_005 flat annular ends ARE axis-aligned planar, so the hypothesis-bifurcation collapsed and V25 took over: "A2's `_run_shared` returns the same matched=True placeholder regardless of actual gap distance." So V22's PASS in case_004 confirms only that the advisor algorithm runs cleanly on rotating-machinery axis-aligned bodies — NOT that it detects the 0.30 mm gap. A2-v2 LANDED 2026-05-12 (DEC-V61-198-sub-A2v2) closes V25 placeholder gap.
- **V23** (`thin_wall_advisor field-validation on rotating-machinery aux hardware (case_004) — first cross-topology to case_002a/b`): documents thin_wall PASS at severity=critical across 3 refinement scenarios. **Status: VALIDATED 2026-05-08 4-of-4** (case_002a curved CATIA + case_003 planar + case_004 rotating-aux + case_007 ship-hydro) — arc closed.
- **V24** (`V16 fragmentation pattern reproduction in case_004 (rotating-machinery topology)`): documents 40 STEP entities for 12 bodies (12 named + 8 compound fragments + 21 FreeCAD datum frames with sentinel ~1e92 mm bboxes). **Status: partial** — case-local allowlist workaround; main-project A1 extension still queued.

**Advisor coverage roster** (`advisor_coverage_2026-05-09.md`):

- **A6** = `hvac_adpi.py` (HVAC ADPI/throw/dumping post-processor) — 1 sediment from case_012, DEFERRED pending 2nd HVAC-class case. case_004 is rotating-machinery, NOT HVAC. **case_004 produces ZERO 2nd evidence for A6.**
- **A8** = `shm_dict_validator.py` (typo / dict-validation class) — 1 sediment from case_012 (V52), DEFERRED pending 2nd typo-class case. case_004 has **no snappyHexMeshDict written** (deferred to v2 sub-session) → no surface for typo-class evidence. **case_004 produces ZERO 2nd evidence for A8.**
- **A4** (face_orientation) + **A5** (inlet_outlet_validator) + **A7** (step_canonicalizer) all LANDED 2026-05-12/13. **A1/A3 deferred.** **A9 / D-class slots are open**.

**No main-corpus row primarily about MRF setup correctness** — case_004 is the only MRF case to date, V22-V24 are advisor-class outputs not MRF-class methodology. The blind findings F2 (zone clearance), F3 (nonRotatingPatches invariant), F1+F4 (dead-infra regression) are **all net-new to the canonical corpus**.

## 4. Score

| Blind finding | vs corpus + REPORT | Verdict |
|---|---|---|
| F1 dead-infra regression risk (07b/08b shipped w/o frozen-ref pytest) | REPORT.md acknowledges 07b "not yet exercised" but does NOT flag regression-test gap; not in V22-V24; not in cross-cuts | **NEW → V88 backfill (compound row, sub-mechanism a)** |
| F2 rotating_cellzone radius 1.12 × R inadequate vs 1.5-2.0 × R convention | not in REPORT.md (which flags domain 1.25 D only); not in corpus | **NEW → V88 backfill (sub-mechanism b · primary physics-correctness finding)** |
| F3 nonRotatingPatches () empty relies on implicit geometric isolation invariant | not in REPORT.md; not in corpus | **NEW → V88 backfill (sub-mechanism c)** |
| F4 07b/08b regex+bbox heuristic format-fragile across OF versions; bbox-only enclosure heuristic = V83 cross-application | not in REPORT.md; not in corpus; cross-applies V83 to mrf_audit surface | **partial NEW** — folded into V88 sub-mechanism a; V83 cross-application note added |
| F5 V16 compound fragmentation 40 vs 12 | V24 exact match | primed-match (hit · V24 already documents) |
| F6 A2 placeholder semantic w/ normal_dot=0.969 | V22 + V25 + A2-v2 LANDED already cover | primed-match (hit) |
| F7 thin_wall D8 7th cross-topology critical | V23 (4-of-4 VALIDATED) | primed-match (hit · arc closed) |
| F8 domain half-width 1.25 D tight | REPORT.md §Limitations §4 explicit | hit (REPORT-acknowledged) |
| F9 force_coeffs includes hub in blade thrust integration | not surfaced anywhere; minor v2 polish | retro note (LOW priority) |

**Tally**: 3 net-new compound sub-mechanisms landed as **V88** (F2 + F3 + F1) + 1 partial-cross-application (F4 → V83 extension folded into V88 sub-mechanism a) + 1 REPORT-acknowledged hit (F8) + 3 primed-match (F5/F6/F7 — V24/V22/V23 all already field-validated) + 1 retro-only polish note (F9).

The Track C session caught **one load-bearing methodology gap** that the case_004 sub-session author + main-corpus sedimentation pipeline both missed:

- **MRF setup (rotating-machinery) has zero pre-mesh advisor coverage** — three independent sub-mechanisms (zone clearance vs rotor R, stationary-walls-outside-zone-bbox invariant, NEW-infrastructure regression-test gap) all surface in case_004 v1, all uncovered by A1-A8 stack. This is a **NEW advisor-coverage class** not previously surfaced.

## 5. What this validates / what it doesn't

**Validates**:

- The Track C protocol reproduces on a **third numerics class** with substantially less substrate than sessions 1+2. case_010 had full sHM logs + 4M mesh; case_011 had full multi-region split; case_004 has **only CAD + advisor outputs + NEW infra**. Yet the advisor model still surfaces 3 net-new findings (V88 sub-mechanisms). **Blind-verdict capability is robust to substrate depth.**
- **Rotating-machinery numerics class has a distinct blind-spot class** orthogonal to incompressible-LES (session 1) and steady-CHT-multi-stream (session 2). MRF zone clearance vs rotor R, nonRotatingPatches stationary-wall invariant, and NEW-infrastructure regression-test gap are MRF-specific gaps not surfacing in cases without rotation. **Pattern 6 inheritance** does NOT cover them — they need MRF-specific advisor surface.
- **V83 cross-application widens**: session 1 surfaced V83 (mesh_ok blind-spot in check_mesh_summary.json); session 2 cross-applied V83 to mesh_summary.json verdict semantics; session 3 cross-applies V83 to **mrf_audit bbox-only enclosure heuristic**. **3rd cross-application of V83 across 3 distinct audit surfaces in 3 sessions** raises confidence that V83's "intent-cross-reference" methodology gap is genuinely deep, not surface-specific. Sub-DEC for `audit_verdict_semantics_advisor` (cross-cuts all audit-script surfaces) is now overdetermined per Pillar-2 (2-case escalation already done; 3-case overdetermined).

**Does NOT validate**:

- **A6/A8 2nd-evidence pathway is NOT advanced by case_004.** A6 = HVAC ADPI; case_004 is rotating-machinery, no thermal-comfort surface. A8 = shm_dict_validator; case_004 has **no snappyHexMeshDict written** (v2 deferred). Both A6 and A8 promotion gates remain at 1-case sediment after session 3. **Negative result on session 3's primary leverage point** — case_004 substrate state foreclosed the question.
- An M6 RAG-backed advisor with constrained retrieval. Session 3 loaded ~15k tokens of substrate (smaller than session 1+2 due to no logs). A constrained retrieval would face the same "is rotating_cellzone radius vs rotor R covered by retrieval set?" question; if the retrieval doesn't pull build_cad.py line 56 (`ROTATING_ZONE_RADIUS_MM = 1.12 * ROTOR_RADIUS_MM`) and parts_manifest.yaml `radius_mm: 5632.48` simultaneously, the F2 finding is lost.
- That `mrf_setup_advisor` is the correct A9 architecture. V88 is 1-case sediment; Pillar-2 extraction requires 2nd MRF case — which the 16-case roster doesn't yet contain. **Deferred extraction.**

**Caveats**:

- **Pacing accelerated**: session 1 + session 2 + session 3 all on 2026-05-13, ~3-4 hours apart. Session 1 §7 recommended ≥1 week between sessions; we're at 3 sessions same-day. Captured in §10 below. Risk: **inter-session priming** — session 3 was warm with session 1's V82/V83 mental model and session 2's V85/V86 model, plausibly biased me to look for `audit_verdict_permissive` patterns in 07b_audit_mrf.py (F4). Net-positive in this case (F4 surfaces a real V83 cross-application widening), but worth tracking.
- **Substrate constraint shapes finding distribution**: session 3 cannot surface mesh-stage failures (no mesh exists). The 3 net-new findings (V88 a/b/c) are **all MRF-config + NEW-infra-coverage**, not mesh-quality. If case_004 v2 lands with full mesh, a session 4-or-5 on case_004 v2 would surface a different finding set. This session does NOT field-validate **mesh-stage advisor capability** on case_004; only config/advisor-output capability.
- **No fix-verification appendix** (unlike session 1 §9 V82 in-place fix). F1+F2+F3 fixes are case_004 v2 sub-session work (build_cad.py + 02b_audit_mrf_geometry + pytest harnesses) — not Track C session 3 scope. The v2 sub-session has clear instructions in F1-F4 fix-paths §2 to incorporate.
- **A6/A8 2nd-evidence: confirmed not produced by case_004.** Honest negative report. A6/A8 promotion gates still need: A6 → 2nd HVAC-class case (case_012 + one more; case_015 chtMR-LES with HVAC-relevant surface not yet substrate-ready); A8 → 2nd typo-class case (any sHM-dict-bug case after case_012 V52). Track C sessions 4+ should prioritize cases with substrate depth that can surface either class.

## 6. Concrete deliverables (this session)

1. **V88 backfill** — `industrial_case_solver_findings.md` § V88 + `docs/openfoam_corpus/industrial_solver_findings_v_series.md` (runtime corpus mirror, synced same commit per pre-commit `check_corpus_sync.py` hook landed 2026-05-13 commit `d53afbc`). Documents compound row: MRF setup (rotating-machinery) has zero pre-mesh advisor coverage — three sub-mechanisms surface in case_004 v1 (zone clearance vs rotor R, stationary-walls-outside-zone-bbox invariant, NEW-infrastructure regression-test gap). Cross-applies V83 intent-cross-reference pattern to mrf_audit bbox-only enclosure heuristic. A9 candidate registered for `mrf_setup_advisor.py` post-2nd-MRF-case.
2. **ARC-GOAL.md M-TRACK-3** row checked off with retro file path + Track C counter incremented 2 → 3. V-series count 87 → 88. End-to-end numerics class count UNCHANGED (case_004 v1 has no solver run; +0).
3. **This retro file**.

**No source code changes this session.** F1-F4 fixes are case_004 v2 sub-session actions (case-local: build_cad.py zone radius + 02b_audit_mrf_geometry + pytest fixtures for 07b/08b). Pillar-2 extraction (`mrf_setup_advisor.py`) is deferred until a 2nd MRF case appears in the roster.

**Lessons-flagged for A6/A8 promotion (the session's primary leverage point per briefing)**:

- A6 (HVAC ADPI) — case_004 produces ZERO 2nd evidence. A6 still at 1-case sediment (case_012). **A6 promotion gate UNCHANGED**, candidate defers continuing.
- A8 (shm_dict_validator) — case_004 has no sHM dict, produces ZERO 2nd evidence. A8 still at 1-case sediment (case_012 V52). **A8 promotion gate UNCHANGED**, candidate defers continuing.
- **Honest negative**: case_004 substrate state (no sHM, no HVAC physics) foreclosed both A6 and A8 evidence channels by construction. The briefing's leverage-point hypothesis ("case_004 might surface A6/A8 2nd evidence") was a reasonable prior but did not pan out. Session 4 should target a case with substrate depth that includes sHM dict OR HVAC physics for A6/A8 channel.

## 7. Suggested next Track C sessions

Per session 1 §7 and session 2 §7 recommendations + session 3 substrate-constraint learnings:

- **Session 4** (recommended): **case_009 Sandia Flame D** (reacting low-Mach combustion · numerics class). Per session 1 §7 recommendation + session 2 §7 reaffirmation. V38-V42 cluster covers chemkin loader / mechanism file format. **Substrate readiness check needed before commit** — case_009 sandbox should have full sHM logs + REPORT.md + non-trivial advisor outputs. Likely surfaces: thermo header bounds vs operating-T conflicts (V41 family); species count vs solver matrix scaling; A6 (HVAC) is NOT applicable here (reacting != HVAC); A8 (sHM dict) potentially applicable if Sandia Flame case has sHM dict bugs.
- **Session 5**: **case_007 KCS ship VOF** (multiphase-VOF · numerics class). Already probed in session 1 §10 (negative on V82 reproduction). Full Track C session would surface VOF-specific failures (interface tracking, surface tension, wallDist for kOmegaSST). Sample-size grows to 4 numerics classes.
- **Session 6**: **case_015 chtMR LES/CHT** (compound numerics class — LES + CHT, possibly with HVAC-relevant interior). V47-V51 cluster makes this **densely covered** in main corpus; would validate corpus-completeness baseline. Critically — **if case_015 has HVAC-comfort metrics (ADPI/throw/dumping) in its evidence outputs**, this is the strongest candidate for **A6 2nd evidence**. Check `case_015` substrate before committing.
- **Sessions 7+** (post-arc-target): case_004 v2 (mesh + solver landed) as a re-session would test V88 fix-verification (analogous to session 1 §9 V82 re-run). Defer until case_004 v2 sub-session lands.

**Pacing reset**: sessions 1+2+3 all on 2026-05-13 = ~3 sessions / 1 day. Aggregate token spend in this session window ≈ 180-200k tokens across all three retros + V-row authoring. Session 4+ should resume **weekly cadence** to avoid continued main-session context-overload, unless user explicitly directs same-day continuation for arc-velocity reasons. The risk addressed by clustering = "context warm + arc momentum"; the risk incurred = inter-session priming bias (observable in session 2 F4 and session 3 F4 both surfacing as V83 cross-applications). The bias is mostly net-positive but should be tracked across the arc.

**Substrate readiness check before scheduling session 4**: `ls ~/Desktop/case_009*/case/log/` to confirm sHM completed; check `evidence/v1*/REPORT.md` exists; check `~/Desktop/case_009*/scripts/` for the pipeline depth (case_004 only had Phase 0-2 + 8b; if case_009 is similarly Phase-0-only, swap to case_015 or another with full pipeline).

**A6/A8 leverage update**: after session 3 confirms A6/A8 cannot be surfaced from case_004, the prioritization for sessions 4+ shifts to substrate that can plausibly produce 2nd evidence. case_015 chtMR-LES (if it has thermal-comfort post-processing) is the strongest A6 candidate. Any case with shipped snappyHexMeshDict (almost all 16-case roster except case_004 v1) is A8-capable.

## 8. Cross-references

- **Parent feedback**: `feedback_claude_code_is_the_advisor.md` (M6 charter advisor button → replaced by Track C dogfooding)
- **Parent DEC**: V61-198 (industrial-case container pivot)
- **V-rows landed this session**: V88 (compound)
- **V-row cross-applied (3rd application widening)**: V83 (case_010 mesh_ok blind-spot) — V88 sub-mechanism a notes that V83's intent-cross-reference prescription cross-applies to mrf_audit's bbox-only "rotating wall enclosed by zone" heuristic. **3rd cross-application of V83 across 3 audit surfaces → V83 methodology gap is overdetermined for Pillar-2 advisor extraction (`audit_verdict_semantics_advisor`)**
- **V-rows referenced (3rd PASS in arc) but not amended**: V22 (A2 on rotating-machinery), V23 (thin_wall on aux hardware), V24 (V16 fragmentation reproduction) — all closed/VALIDATED prior to this session; case_004 substrate adds no new evidence to these arcs
- **A6/A8 promotion status post-session-3**: A6 hvac_adpi UNCHANGED at 1-case sediment; A8 shm_dict_validator UNCHANGED at 1-case sediment. Neither advanced by case_004
- **A9 candidate registered**: `mrf_setup_advisor.py` (zone clearance + stationary-wall isolation + frozen-reference regression for 07b/08b) — defer to 2nd MRF case
- **ARC-GOAL row**: M-TRACK-3 main-line table
- **Session 1 retro**: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_1_case_010.md`
- **Session 2 retro**: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_2_case_011.md`

## 9. F1-F4 fix-verification (NOT performed this session)

Unlike session 1 §9 (V82 fix verified in-place on case_010 sandbox), session 3 does **not** include a fix-verify appendix. Reasons:

1. **Briefing constraint**: "不写代码（advisor 验证，不开发）". Session 3 is verification, not development.
2. **F1-F4 fixes are case-local v2 sub-session scope**: (a) build_cad.py `ROTATING_ZONE_RADIUS_MM` 5632 → 7500-10000 mm + STEP rebuild + STL re-extract; (b) new `02b_audit_mrf_geometry.py` ~30 LOC; (c) pytest fixtures for 07b/08b ~60 LOC + frozen reference fragments. Multi-step, scoped to v2 dispatch.
3. **v2 sub-session is not yet dispatched** for case_004; the kickoff in `.planning/methodology/kickoff/case_004_nrel_phase_vi_mrf.md` and case_proposal_queue mark v1 PAUSED. When v2 dispatches, the kickoff should incorporate V88 sub-mechanism a/b/c fix paths as MANDATORY initial deliverables (analogous to case_011 v2 incorporating V85's plate-bumping + insidePoint repositioning).

**Path to V88 promotion from `open` to `fix-verified · 1 case`**:
1. case_004 v2 sub-session lands with: (a) zone radius ≥ 1.5 × R; (b) 02b_audit_mrf_geometry passes stationary-wall-outside-zone invariant; (c) 07b/08b pytest harness landed in case_004 OR upstream (`tests/` in main repo if extracted as A9 candidate).
2. Track C session re-visits case_004 v2 (same protocol, fresh blind reading) — confirms no new MRF-config findings + flags any v2-specific issues.
3. Update V88 Status `open` → `fix-verified · 1 case` with evidence table analogous to session 1 §9.
4. Promotion to `validated · cross-case (≥2 MRF cases)` deferred until 2nd MRF case lands.

**What this leaves unverified**: V88 Status is `open`. A9 extraction is Pillar-2-deferred. The 16-case roster has no other current MRF candidate — Track C session 7+ may need to wait for Phase-2 industrial cases or a new MRF case dispatch.

## 10. Pacing + protocol notes

**Pacing**: accelerated per user direction 2026-05-13 — session 3 ran same-day as session 1 (~6-7 hours after session 1 start, ~3 hours after session 2 close). Session 1 §7 recommended ≥1 week cadence; sessions 1+2 caveat in §5 noted "session 2 was 1-day cadence after session 1"; session 3 continues this acceleration to "3 sessions / 1 day." Captured in §5 caveat. Per main-session direction (briefing §5), this is acceptable because Track C arc 主线推进 — accumulating data points while context + protocol are warm. The risk addressed = "user is making sustained arc progress and wants to land another data point while the protocol mental model is fresh"; the risk incurred = (a) inter-session priming (visible in F4 surfacing as V83 cross-application, mirroring session 2 F4); (b) main session token-budget consumption (~80k tokens cumulatively across 3 retros + 2 V-rows authoring as of this session close).

**Protocol drift from sessions 1+2**:
- **No briefing cross_cuts pre-load** (unlike session 2 §5 which acknowledged contamination from `v_series_case_011_append_2026-05-09.md`). case_004 has no `cross_cuts/case_004_append*.md`; the session 3 briefing required reads do not include any case-specific draft sediment. Strict-blind protocol restored.
- **Substrate depth dramatically less** (no logs, no sHM, no fvSchemes, no checkMesh): forces finding distribution toward MRF-config / advisor-output / NEW-infrastructure classes. Sessions 1+2 were dominated by mesh-stage findings; session 3 is dominated by config + infra-coverage findings. **This is a feature, not a bug** — it tests the advisor's range across substrate depths. The shape of findings reflects the substrate, and that's the right answer.
- **No §10 cross-case probe appendix** (unlike session 1 §10 which probed case_007 sHM log for V82 reproduction). For V88 there is no analogous quick probe — V88 is rotating-machinery-specific; the 16-case roster has no other current MRF case to probe.

**Track C arc state after session 3** (per ARC-GOAL Done Definition):
- Done Definition #1 "Track C session 通过 case 数": 2 → **3** (target: ≥ 6)
- Done Definition #2 "LANDED advisor 数 (含 D-class ≥ 1)": **6 UNCHANGED** (A1, A2-v2, A3, A4, A5, A7 LANDED · A6/A8 still at 1-case sediment after session 3 confirms case_004 produces 0 evidence; A9 mrf_setup_advisor newly registered as candidate)
- Done Definition #3 "V-series 行数": 87 → **88** (target: ≥ 100)
- Done Definition #4 "End-to-end solver 跑通 numerics class 数": **1 UNCHANGED** (case_004 v1 has no mesh + no solver; +0 — this metric advances only on cases with full-pipeline runs)
- Done Definition #5 capability radar left-half: UNCHANGED (Track C doesn't directly move radar; V88 sub-mechanisms add small +0.05Δ to CAD+网格 axis only when MRF advisor lands)
- Done Definition #6 capability radar right-half: UNCHANGED

**Triggered redirect conditions** (per ARC-GOAL):
- "Track C 中 ≥ 2 case 同类 advisor 盲点" → session 3 surfaces a NEW class (MRF setup) not shared with sessions 1+2; no class repeats yet → no harvest-003 trigger
- Other redirect conditions unchanged

**Open questions to surface for next-session decision**:
1. **case_004 v2 dispatch priority**: V88 makes case_004 v2 (mesh + solver + advisor re-run) more attractive than before — promotes V88 from `open` to `fix-verified` and adds an end-to-end MRF data point (Done Definition #4 numerics-class +1). Recommend prioritizing case_004 v2 over a new Track C session if dispatch capacity allows.
2. **A6/A8 substrate strategy**: sessions 4+ should explicitly target substrate that can plausibly surface A6/A8 2nd evidence. Pre-flight substrate check before scheduling.
3. **V83 promotion to overdetermined Pillar-2 candidate**: 3 cross-applications across 3 sessions (sessions 1+2+3 — check_mesh_summary verdict + mesh_summary verdict + mrf_audit bbox enclosure heuristic). Should `audit_verdict_semantics_advisor` (or similar cross-cutting audit-verdict-pattern advisor) be elevated from "deferred" to "next-after-A4/A5" priority? Worth raising in next ARC review.

— EOF —

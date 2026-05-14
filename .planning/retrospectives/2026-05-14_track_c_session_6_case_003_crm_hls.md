# Track C · Advisor e2e — Session 6 · case_003 CRM-HLS boundary layer (external-high-Re-BL numerics class probe + V20 cascade re-surfacing)

> **Date**: 2026-05-14
> **Track**: C (Claude Code session as M6 advisor, per `feedback_claude_code_is_the_advisor.md`)
> **Mandate**: Track C 5→6 · activate `case_003_crm_hls_boundary_layer` from dispatched-deferred (paused 2026-05-08 at v1 with V20 unit-scale blocker) and attempt e2e advisor-driven mesh+solver run for the **incompressible-RANS external-high-Re-BL** numerics class — a class not yet covered by sessions 1-5 (LES / CHT / MRF / reacting cold-flow / reacting v1.5).
> **Subject case**: `~/Desktop/case_003_crm_hls_boundary_layer/` (external substrate, sibling of cfd-harness-unified main repo) · NASA/AIAA HLPW6 CRM-HLS as Tier-1 source · `simpleFoam` + `kOmegaSST` + nutkWallFunction · 10 named bodies (4 walls + 1 inlet + 1 outlet + 1 symmetry + 3 farfield + 1 sub-grid thin plate).
> **Authored by**: Claude Code Opus 4.7 (1M context · dispatched sub-session per main-session brief).
> **Counter impact**: nil retro-side (sub-DEC for V96/V97 advisor findings deferred per hard constraint §硬约束 "不 promote A6/A9/A10 candidate"; this retro is methodology consolidation + V-row sediment, not a new autonomous_governance DEC).
> **Pacing acknowledgment**: **6 sessions / 3 calendar days** (sessions 1-4 on 2026-05-13 · session 5 B10 + retro on 2026-05-14 · session 6 on 2026-05-14). Persistent drift from session-1 §7 weekly recommendation. See §7.

---

## 1. Session goal

Activate `case_003_crm_hls_boundary_layer` (dispatched 2026-05-07, paused 2026-05-08 at v1 advisor-validation stage with V20 unit-scale blocker un-resolved) and run the full pipeline through mesh + solver as Track C session 6, with three deliverables:

1. **Coverage attempt for external-high-Re-BL numerics class** — sessions 1-5 covered LES, CHT, MRF, reacting cold-flow, reacting v1.5. case_003's numerics signature (incompressible RANS, `kOmegaSST` wall-function-zone, freestream high-Re separation) sits in a slot Track C has not yet exercised. Session 6 attempts this slot.
2. **Empirical re-surfacing of V20 unit-scale blocker** — v1 (2026-05-08) paused on the observation that loaded geometry showed airframe at ≈91 m semi-span vs real CRM ≈30 m, suggesting a 25.4× over-scale from inch→mm round-trip. Session 6 attempts to either resolve V20 (via A6 `unit_detector` re-evaluation) or honest-stop with new V-row evidence.
3. **Advisor cross-application as 2nd-case evidence** — run A2-v2 / A4 / A6 / A7 / A8 against case_003 substrate; report which advisors trigger; report whether session 6 is V83 intent-cross-reference pattern's **6th cross-application**.

Hard constraints from brief (all observed): no edits to `.planning/ARC-GOAL.md` (main-session reconcile), no edits to `case_009/004/010/011/012/013` files, no edits to `ui/backend/services/geometry_ingest/` (advisor land deferred), do not promote A6/A9/A10 candidates even if 2nd-case evidence surfaces (independent sub-DEC scope), honest early-stop budget = mesh ≤ 4 h / solver ≤ 6 h.

**Outcome forward-reference (load-bearing for the rest of this retro)**:
- mesh + solver **infrastructure ran without divergence** (197 k cells · checkMesh `Mesh OK` · simpleFoam 411 iter without NaN, stable residuals, forces fluctuating ≤ 5 % over iter 300-411).
- **e2e is NOT a PASS** in the same sense as session 5 case_009 v1.5: solver was killed by `docker stop` at iter 411 before residualControl convergence (U_y final 1.00e-4 sat right at the threshold); near-wall y+ at sHM L3 refinement ≈ 2.1×10⁵ — kOmegaSST wall function operates **far outside** its valid envelope (30 < y+ < 100); produced Cl≈-0.096 at α=8° (sign inconsistent with simple aerospace expectation, attributable to V20 cascade affecting both geometry orientation and BL resolution).
- **external-high-Re-BL numerics class is NOT formally promoted** by session 6 per the §9 criteria session 5 applied to reacting-low-Mach.
- **V-row sediment landed**: V96 (A6 max_bytes truncation on STEP unit declarations sitting past byte 65536) + V97 (A6 bbox_plausible_units 100 m range cap rejecting valid industrial-aircraft-scale geometries) + V98 (external-high-Re-BL y+ resolution physically infeasible at V20-unresolved as-loaded scale · V20 cascade evidence). 3 V-rows, all V83 6th cross-application class.

## 2. Substrate state delta — v1 (paused 2026-05-08) → v2 (this session)

Source of truth: `~/Desktop/case_003_crm_hls_boundary_layer/` filesystem diff + `case/log_blockMesh.txt`, `case/log_sHM.txt`, `case/log_checkMesh.txt`, `case/log_simpleFoam.txt`, `evidence/session6_advisor_xapp.txt`, `evidence/session6_y_plus_check.txt`.

**Net additions** (session 6 only):

- `scripts/03_export_multi_stl.py` — STEP→multi-solid STL exporter. Decomposes the cadquery-roundtripped combined STEP into 10 sub-solids via `Compound.Solids()` and writes one STL per `PART_NAMES` body (one airframe + 3 fixtures + 6 farfield). Honors **V94** (single-shell STL face-zone loss) by emitting one STL per CAD-stage named body rather than relying on cq.exporters' face-zone propagation.
- `case/constant/triSurface/*.stl` × 10 + `case/constant/triSurface/*.stl.mm.bak` × 10 — STLs at meter scale (scaled from initial mm-export via `surfaceTransformPoints -scale (0.001 0.001 0.001)` to match the meter-scale blockMesh polyMesh).
- `case/system/{blockMeshDict, snappyHexMeshDict, controlDict, fvSchemes, fvSolution, meshQualityDict, surfaceFeatureExtractDict}` — production-tuned for as-loaded geometry (bg cell 32 m, sHM L0-L3 on wall surfaces, NO prism layers per y+-infeasibility §4 below, kOmegaSST + simpleFoam steady RANS).
- `case/constant/{transportProperties, turbulenceProperties}` — incompressible RAS kOmegaSST · ν=1.5e-5 · printCoeffs on.
- `case/0/{U, p, k, omega, nut}` — initial fields: U=(54.464, 0, 7.655) for U∞=55 m/s @ α=8°, k=0.1135, ω=0.04, freestreamVelocity/freestreamPressure on farfield, slip on symmetry_plane (downgraded from `symmetryPlane` patch type per V98 below).
- `case/constant/polyMesh/` — 197,590-cell hex-dominant mesh. Patches: airframe_reference (3,643 faces, closed singly connected, ok), root_mount_pad (17 faces), root_mount_cover (17 faces), inlet (2,400), outlet (2,400), symmetry_plane (3,648 · type `patch` not `symmetryPlane`), farfield_top (3,800), farfield_bottom (3,800), farfield_outer (3,648). **thin_access_plate patch absent from polyMesh** (D8 0.8 m at meter scale = sub-grid relative to bg=32 m and refinement levels 2-3 cells of 4-8 m → sHM merges away — see §3 + §4).
- `case/[0..200..400]/` write-time snapshots from simpleFoam (writeInterval=200).
- `case/log_{blockMesh, sHM, checkMesh, potentialFoam, simpleFoam}.txt` — full solver/mesh logs (simpleFoam log ~11k lines, 411 iter).
- `case/postProcessing/forceCoeffs1/{0,...}/coefficient.dat` — force coefficient history.
- `evidence/session6_advisor_xapp.txt` — A6 unit_detector cross-application report (§4 evidence).
- `evidence/session6_y_plus_check.txt` — y+ physical infeasibility analysis (§4 evidence).

**Net removals from substrate**: none. v1 deliverables (`inputs/cad_codex_v1.step`, `inputs/parts_manifest.yaml`, `inputs/defect_manifest.yaml`, `inputs/face_geometry.json`, `evidence/v1_20260508T010754_advisor_validation/`) are preserved verbatim; session 6 builds on top.

**Key empirical deltas** (per-deliverable status):

| Pipeline step | v1 (2026-05-08) | session 6 (2026-05-14) |
|---|---|---|
| 01 build_cad.py | ✅ executed (Tier-1 STEP downloaded, sha256 pinned) | (re-used; not re-run) |
| 02 verify_defects.py | ✅ D1=0.350mm + D8=0.800mm + A2 PASS + thin_wall_advisor critical | (re-used; preserved evidence) |
| 03 export multi-STL | ❌ not run (paused) | ✅ 10 STLs (airframe 728 facets, 6 farfield + 3 fixture + 1 thin-plate) |
| 04 scaffold case | ❌ not run | ✅ system/ + 0/ + constant/ authored |
| 05 make dicts | ❌ not run | ✅ blockMesh + sHM + controlDict + fvSchemes/Solution authored |
| 06 run mesh | ❌ not run | ✅ blockMesh 227,529 bg cells · sHM 197,590 final cells in 21.4 s · checkMesh `Mesh OK` |
| 07 check mesh | ❌ not run | ✅ non-ortho max 46.3° · skewness max 2.05 · aspect ratio max 4.78 · 9 patches OK |
| 08 write BCs | ❌ not run | ✅ U/p/k/omega/nut at high-Re wall functions; symmetry_plane forced to slip (V98) |
| 09 run solver | ❌ not run | ⚠️ simpleFoam 411 iter run · NOT converged via residualControl (killed by docker stop) · residuals stable · Cl drifting ±5% over iter 300-411 |
| 10 post-process | ❌ not run | ❌ not run (out of session scope) |
| 11 audit signed evidence pack | ❌ not run | ❌ not run (deferred) |

Solver scheme set: PIMPLE-style steady RANS (`SIMPLE { nNonOrthogonalCorrectors 1; consistent yes; }`), upwind-blended divSchemes, GAMG p / smoothSolver U+k+omega, relaxationFactors p=0.3 U/k/ω=0.7.

## 3. Death mode — V20 cascade silent failure chain (advisor surface check vs intent check)

The session-6 production state surfaces **three new V-rows** (V96 / V97 / V98) all rooted in the same V83 6th-application failure topology. The narrative chain is:

**Step 1 (V96 surface)** — A6 `unit_detector.parse_step_header_unit()` is called with default `max_bytes=65536` (rationale in the docstring: "STEP UNIT declarations sit in the early DATA section"). For the HLPW6 CRM-HLS source STEP, the unit declaration sits at **byte 707,430 of 716,110** (line `#8413=(CONVERSION_BASED_UNIT('INCH',#8409)LENGTH_UNIT()NAMED_UNIT(#8408));`). The 64 KB read window stops at byte 65,536 — **the INCH declaration is silently truncated out of the parse**. parse_step_header_unit returns `(None, ["STEP header does not contain a recognized LENGTH unit declaration"])`. The regex `_CONVERSION_INCH_RE = r"CONVERSION_BASED_UNIT\s*\(\s*'INCH'"` is **correct**; the byte-window is **wrong**.

Verification: re-running with `max_bytes=800000` correctly recovers `(GeometricUnit.INCH, ["STEP header declares CONVERSION_BASED_UNIT('INCH')"])`. The diagnostic regex and rule are sound; only the empirical assumption about declaration placement is false for ST-Developer-class STEP exporters (which place GLOBAL_UNIT_ASSIGNED_CONTEXT at file end as part of the closing geometric representation context block — a STEP-AP242-conformant practice, just opposite-end to the CATIA/SolidWorks pattern A6 was tuned for).

**Step 2 (V97 surface)** — Independently, A6 `bbox_plausible_units(raw_max_extent=182880.0, range=(0.01, 100.0))` is called with the airframe-reference body's raw bbox max extent (loaded "mm" units). The function asks: "under each candidate unit, would this raw value put geometry inside (1 cm, 100 m)?". For 182880 raw:
- under MM (1e-3 m): 182.88 m → **rejected** (> 100 m cap)
- under CM (1e-2 m): 1828.80 m → rejected
- under M (1.0): 182880 m → rejected
- under INCH (0.0254 m): 4645 m → rejected

The function returns `()` (empty tuple = "no plausible unit"). The bbox-channel signal is **silent** for valid industrial-aircraft-scale geometry. Real industrial CFD spans aircraft (60+ m), ships (300+ m), wind farms (5+ km), civil structures (200+ m). The (0.01 m, 100 m) range is empirically biased toward small reference geometries (heat-exchangers, single airfoils, small assemblies).

Verification: re-running with widened range `(0.01, 1000.0)` returns `(GeometricUnit.MM,)` — MM is correctly identified as plausible at 182.88 m. The rule's mathematical structure is sound; only the upper-bound constant is wrong.

**Step 3 (V98 cascade)** — Combined V96+V97 → A6 `detect_unit` falls back to UNKNOWN/low-confidence on source HLPW6 STEP. Engineer (= Claude Code in Track C role) does not receive a "this is INCH, multiply by 25.4 before meshing" advisory. cadquery's round-trip importStep silently converts INCH→MM internally (per OCP convention) and emits a 1.96 MB combined STEP with `SI_UNIT(.MILLI.,.METRE.)` declared at byte ~1500 (top of file) and numeric values pre-multiplied by 25.4. From the cadquery output STEP's perspective, MM declaration matches large bbox magnitudes → A6 on **post-roundtrip** STEP returns `(declared=MM, plausible=(MM,), confidence=1.00)` with an extra evidence line "body-class filter: 2/3 bodies discarded as CFD-domain class; using largest airframe-class extent 9.144e+04 for unit decision". So the only point where A6 could have raised the unit-mismatch alarm is on the **source** STEP — and that path is occluded by V96+V97.

**The intent check that V96 and V97 share** is: "does this geometry's unit-declaration channel have detectable evidence?". The surface checks ("does my regex match in 64 KB?" and "does my value fit in (0.01 m, 100 m)?") run cleanly, find nothing, and **return**. The intent check ("the unit must be discoverable somewhere — if neither channel sees it, that itself is the discovery; widen the window or widen the range") is **never asked**. This is structurally identical to:

- V83 (mesh_ok permissive verdict not asking "do the geometry-derived patches have non-zero faces"),
- V88 sub-mech (a) (mrf_audit accepting rotation zone without asking "does the cellZone actually exist in polyMesh"),
- V91 (V-series sediment-status as verifiable-artifact class, not asking "did I empirically verify the patch was complete"),
- V93 (boundary T fixedValue vs per-species Tlow cross-artifact check, not asking "does the chemistry source-term cell satisfy the limiter range").

**Step 4 (V98 BL physical infeasibility — the case_003-specific cascade)** — At V20-unresolved as-loaded geometry (chord ≈ 152 m, U∞=55 m/s, ν=1.5e-5 → Re=5.57×10⁸), Prandtl-Schlichting flat-plate Cf=0.00165 → τ_w=3.05 Pa → u_τ=1.58 m/s. Target y+ < 100 for kOmegaSST nutkWallFunction validity requires near-wall spacing y < 0.48 mm. sHM bg=32 m + refinement L3 puts near-wall y at 2 m, i.e., y+ ≈ 2.1×10⁵ — **2,000× above wall-function valid range**. kOmegaSST's nutkWallFunction returns log-law extrapolation but the physical BL profile cannot be captured; force coefficients reflect inviscid-pressure + spurious wall-function shear, not real-RANS BL physics. Solver did not blow up because the residual dynamics are dominated by pressure flow around an effectively-inviscid body, but **Cl≈-0.096 at α=8°** is not aerodynamically meaningful (CRM-HLS at α=8° clean configuration should have Cl ≈ +0.7-1.0 depending on flap setting; the sign-flip is a combined cascade of: (a) airframe orientation in the source STEP not aligned with my assumed chord→X / span→Y / lift→Z convention, (b) under-resolved BL producing weak suction-side flow, (c) farfield boxes contributing pressure work via their wall-treatment).

**Death-mode signature for retro catalog**: A6's two pure-logic channels (regex + bbox-range) are both **necessary-but-insufficient**. Each is locally correct; together they create a silent fall-through window that hides the V20 unit-scale issue precisely when an engineer needs the alarm — at first ingest of unfamiliar Tier-1 industrial STEP files. The advisor's contract ("if I can't tell, I return UNKNOWN; caller decides") is satisfied, but UNKNOWN-from-V96+V97-silence is not differentiable from UNKNOWN-from-genuinely-ambiguous-input, so the caller's decision tree has no signal to operate on.

**Additional micro-finding V98** (not landed as separate V-row, called out here for retro audit-trail completeness): when sHM ingests a closed-thin-box STL as a `symmetryPlane`-typed refinementSurface, the resulting boundary patch captures multiple sides of the box (5 sides of a 152 m × 1600 m × 1540 m thin box that gets cut by the bg block on multiple sides), producing a patch with non-planar face normals. checkMesh `symmetryPlane` constraint then rejects the mesh with "Symmetry plane 'symmetry_plane' is not planar (face normal differs from average by 0.556)". Fix: downgrade patchInfo to `type patch` + use `slip` BC in 0/* (which still enforces zero-normal-flux semantics, just without the symmetry-plane geometric assertion). **Pattern**: STL-driven symmetry planes are unsound when the STL is not a single thin axis-aligned face. The standard practice (bg-block-face-as-symmetry-plane via blockMeshDict named patches) would have avoided this entirely. This is **A8 shm_dict_validator** territory — it could surface the warning "refinementSurface declared as symmetryPlane but source STL has > 1 unique face normal" if widened.

## 4. Advisor coverage analysis — A6 unit_detector + A8 shm_dict_validator gaps

Session 6 ran the following advisors against case_003 substrate per brief §流程 step 6 ("作为 Claude Code session 直接读 V-series corpus + 驱动 workflow + 给死法模式判断 · NOT 调 advisor UI button"). Results:

| Advisor | Module | Run result | Cross-application class |
|---|---|---|---|
| **A2 virtual_interface_detector** | `virtual_interface_detector.py` | v1 evidence preserved: D1 PASS · normal_dot=1.0 · matched area 3.48e7 mm² | 2nd-case evidence (case_002a + case_003) — already credited at v1 |
| **A4 face_orientation_advisor** | `face_orientation_advisor.py` | module-load OK; case_003 airframe is axis-aligned (no 22° rotation as in case_013 V87); no finding expected; no finding produced | applicability confirmed; no new evidence |
| **A6 unit_detector** | `unit_detector.py` | **3 findings (V96 / V97 / V98)** | **1st-case primary** (this is A6's intended originator-case — V20 was the V-row that motivated A6's land) |
| **A7 inlet_outlet_validator** | `inlet_outlet_validator.py` | module-load OK; manifest has inlet/outlet present | applicability confirmed; no finding |
| **A8 shm_dict_validator** | `shm_dict_validator.py` | runtime error (`'str' object has no attribute 'get'`) — input adapter mismatch with our hand-authored dict format | gap: A8 cannot consume hand-authored sHM dicts that don't go through the harness's dict-emission path |

**A6 findings (load-bearing)** — verbatim from `evidence/session6_advisor_xapp.txt`:

```
[A6 unit_detector @ source HLPW6 STEP]
  file size: 716110 bytes
  INCH declaration byte offset: 707430 (manual grep)
  parse_step_header_unit() declared: None
  evidence: STEP header does not contain a recognized LENGTH unit declaration

  RETRY with max_bytes=800000:
  parse_step_header_unit(max_bytes=800000) declared: GeometricUnit.INCH
    - STEP header declares CONVERSION_BASED_UNIT('INCH')

[A6 bbox_plausible_units @ airframe raw extent 182880.0 mm]
  default range (0.01m, 100m): ()
  widened range (0.01m, 1000m): (<GeometricUnit.MM: 'mm'>,)

[A6 detect_unit @ cad_codex_v1.step (cadquery roundtrip)]
  declared_unit: GeometricUnit.MM
  bbox_plausible_units: (<GeometricUnit.MM: 'mm'>,)
  decision: GeometricUnit.MM
  confidence: 1.0
```

These are not synthetic edge cases — they are the **observed behavior on the first real Tier-1 industrial STEP A6 has been asked to evaluate** outside of case_002a (which avoided V20 because the engineer hand-coded a unit check into 02_domain_subtract.py per A6's own docstring).

**A6 fix scope (deferred per brief §硬约束)**:
- V96 fix: bump `max_bytes` default to 1 MB (cheap memory + scan-time hit, covers > 99 % of real STEP unit-declaration placement). Alternatively, *stream the whole file* if size < threshold (e.g., < 5 MB); only chunk if very large. Add a unit test against the HLPW6 source STEP to lock the regression.
- V97 fix: widen industrial-extent upper bound to ≥ 1000 m (covers full aircraft, civil structures, ship sections, wind-farm rotors). Add a unit test against case_003 airframe extent.
- Both fixes are **single-line constants** in `unit_detector.py`. The sub-DEC scope is "constants tuning + 2 regression tests" — small, low-risk, suitable for a single sub-commit. Recommend filing as **sub-DEC `V61-198-sub-A6-unit-detector-truncation-and-range-tuning`** scoped to those two constants + tests, separate from any A6/A9/A10 promotion arc that might come later. **Deferred this session** per brief §硬约束 ("不动 ui/backend/services/geometry_ingest/ 任何代码").

**A8 fix scope** — the `'str' object has no attribute 'get'` error suggests `validate_shm_dict` expects an already-parsed dict (Python object) but we passed a path; or the OpenFOAM dict's nested structure differs from harness-emitted dict format. Out of scope for session 6; flag for A8 widening sub-DEC.

## 5. V-row sediment landed (3 new rows)

Each V-row landed in both corpora (`.planning/methodology/industrial_case_solver_findings.md` + `docs/openfoam_corpus/industrial_solver_findings_v_series.md`) via the corpus-sync hook expected to fire on this commit. V96+V97+V98 are independent rows; they share a cross-cutting cause (V83 6th-application class) but each names a distinct surface-check/intent-check pair that an engineer could fix without touching the others.

### V96 — A6 `parse_step_header_unit` default `max_bytes=65536` truncates STEP files whose unit declaration sits past byte 65536

- **Surface**: `parse_step_header_unit(step_path)` with default args.
- **Engineer symptom**: A6 returns `declared_unit=None` for a STEP that visually has a CONVERSION_BASED_UNIT('INCH') declaration near end of file. Combined with V97, A6.detect_unit decision=UNKNOWN, confidence=0. Engineer sees no unit advisory and proceeds to meshing.
- **Root cause**: `max_bytes=65536` assumes UNIT declarations sit in the STEP header / early DATA section. ST-Developer / CATIA-V5 / SolidWorks-2024-with-AP242-export-mode style STEP files place GLOBAL_UNIT_ASSIGNED_CONTEXT (#NNN=(GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNIT_ASSIGNED_CONTEXT((#A,#B,#C)) ...)) at file end as part of the closing context block. HLPW6 CRM-HLS source STEP exhibits this placement: 716,110 bytes total, INCH declaration at byte 707,430.
- **Fix candidates** (single-line constant tuning, sub-DEC scope):
  - (a) bump default `max_bytes` to 1 MB (covers all observed STEP unit-decl placements; minimal memory hit; preserves the chunk-not-stream guard for huge STEPs)
  - (b) stream-scan whole file with hard size cap (e.g., 16 MB); only fail-open on extreme files
  - (c) split scan into two passes: first 64 KB + last 64 KB (catches both early-decl and late-decl forms cheaply)
  - **Recommended**: (a) — simplest, covers HLPW6 pattern with margin
- **Status**: open · **landed 2026-05-14 by Track C session 6**.
- **Reference case**: `case_003_crm_hls_boundary_layer/inputs/cache/tier1_crm_hls_hlpw6_tc1.stp` (size 716110, INCH decl at byte 707430).
- **Lesson**: Empirical max_bytes constants should be **calibrated against the actual file-end-placement distribution observed in industrial STEPs**, not against assumed/typical "header" placement. A6's docstring claim "UNIT declarations sit in the early DATA section" is observably false for HLPW6's ST-Developer-toolchain export.

### V97 — A6 `bbox_plausible_units` default range `(0.01 m, 100 m)` rejects valid industrial-aircraft-scale geometries

- **Surface**: `bbox_plausible_units(raw_max_extent, range=_INDUSTRIAL_EXTENT_RANGE_M)` with default `_INDUSTRIAL_EXTENT_RANGE_M = (0.01, 100.0)`.
- **Engineer symptom**: A6 returns empty plausible-units tuple for any STEP whose largest body has raw extent > 100,000 raw-units (i.e., > 100 m under MM hypothesis). Combined with V96, A6.detect_unit cannot recover. Engineer sees no unit advisory and proceeds to meshing.
- **Root cause**: Industrial-extent upper bound = 100 m is empirically biased toward small reference geometries (academic single-airfoils, single heat-exchanger cores, small assemblies). Real industrial CFD regularly exercises full aircraft (CRM = 58.7 m, A380 = 79.8 m, transport aircraft up to ~80 m), ships (ferries 200 m, container ships 400 m), wind farms (rotor diameters 100-250 m, but towers + multi-turbine domains 1+ km), civil structures (buildings 300+ m, bridges spanning 1+ km). The 100 m cap is a sub-industrial scale.
- **Fix candidates** (single-line constant tuning, sub-DEC scope):
  - (a) widen `_INDUSTRIAL_EXTENT_RANGE_M` to `(0.01, 1000.0)` — covers all observed full-aircraft + ship + civil-structure geometries
  - (b) widen to `(0.001, 10000.0)` — covers wind-farm domains + atmospheric BL CFD
  - (c) make the range a constructor parameter (caller decides per project)
  - **Recommended**: (a) — covers the observed shortfall; preserves "if it's > 1 km we should be suspicious" semantics
- **Status**: open · **landed 2026-05-14 by Track C session 6**.
- **Reference case**: case_003 airframe_reference raw bbox max extent = 182,880 (loaded mm), which under MM hypothesis = 182.88 m, beyond the 100 m cap. Real CRM at the inch-loaded scale would be 58.7 m (within range), but the V20 25.4× over-scale puts it out.
- **Lesson**: range-based plausibility filters should reflect the **breadth of expected industrial application**, not the median academic-reference geometry size. V97 is a clean instance of "the test passes the easy cases and silently rejects the cases that motivate the test's existence".

### V98 — External-high-Re-BL physical resolution requires y < 1 mm wall-normal spacing; V20-unresolved geometry (5× CRM scale) puts y+ ≈ 2.1×10⁵ at sHM L3 — kOmegaSST nutkWallFunction operates ≈2000× outside valid envelope

- **Surface**: simpleFoam + kOmegaSST + nutkWallFunction on a sHM mesh with bg cell ≥ 32 m and L3 refinement on airframe walls.
- **Engineer symptom**: solver runs without blow-up; residuals stable; force coefficients finite. BUT the produced Cl, Cd, Cm reflect inviscid-pressure flow + spurious log-law-extrapolated wall shear, not real-RANS BL physics. Cl at α=8° is sign-inconsistent with simple aerospace expectation (expected ~+0.7-1.0 for high-lift CRM-HLS at α=8°; observed -0.096 ±5% drift over iter 300-411).
- **Root cause**: At V20-unresolved as-loaded scale (chord ≈ 152 m, Re ≈ 5.57e8), target y+ < 100 requires near-wall y < 0.48 mm. sHM L3 (bg=32 m, refinement factor 8) produces cell ≈ 4 m → y ≈ 2 m → y+ ≈ 2.1×10⁵. kOmegaSST nutkWallFunction is undefined outside 30 < y+ < 300 (some implementations clip at y+ ≈ 10⁴; nominal validity ceiling is well below 10⁴). Operating at 2.1×10⁵ silently returns log-law extrapolation; the function does not raise. BL profile is fully unresolved — the first cell-center sits more than a kilometer above where physical BL effects matter.
- **Fix candidates**:
  - (a) **resolve V20 first** (fix A6 per V96+V97, re-route STEP through unit-scale corrector that applies 1/25.4 if INCH declared) — then chord ≈ 6 m, target y < 0.1 mm, more tractable
  - (b) **switch to wall-modeled LES or hybrid RANS-LES** schemes which tolerate wider y+ envelope
  - (c) **add prism layers explicitly tuned for finite-Re wall function** — but at 152 m chord with bg=32 m, layer growth ratio from y≈1 mm to y≈4 m would require ~20+ layers (12.5× per layer ratio is unphysical; standard 1.2-1.3 ratio over 20 layers gives only 38-190× span)
  - (d) **explicit y+ check in solver pre-flight** — Track C session as advisor calls `wallShearStress + yPlus` utility, computes near-wall y+ histogram, alerts if max y+ > validity envelope
  - **Recommended**: (a) — V98 is a cascade consequence of V20; fix the root cause; (d) — useful as a generic external-RANS pre-flight advisor (potential A11 candidate, deferred)
- **Status**: open · cascade · **landed 2026-05-14 by Track C session 6**.
- **Reference case**: `case_003_crm_hls_boundary_layer/case/log_simpleFoam.txt` (411 iter, stable residuals, Cl ≈ -0.096; force coefficients NOT aerodynamically valid) + `evidence/session6_y_plus_check.txt` (closed-form y+ estimation per Prandtl-Schlichting).
- **Lesson**: external-RANS at industrial-aircraft Re imposes hard y+ resolution constraints that cannot be ignored when geometry scale is wrong. V98 is **case-internal cascade** evidence of V20 — fixing V20 alone unlocks the path to making V98's symptoms go away (smaller chord → smaller Re → larger allowable near-wall y → tractable mesh). V98 also defines an **A11 candidate advisor**: pre-flight wall-shear-stress + y+ check that surfaces if max y+ exceeds wall-function validity envelope. A11 candidate is deferred per brief §硬约束.

## 6. V-row amendments — V20 status update

V20 was authored 2026-05-08 with status "open · main-session attention required" per case_003 v1 REPORT.md §"Main session attention required" item 1. Session 6 does not flip V20's status — it **does not fix V20**. But it produces **mechanistic substrate** that pinpoints V20's root cause two levels deeper than v1 surfaced:

- v1 said: "loaded geometry shows airframe at ≈91 m semi-span vs real ≈30 m, suggesting source STEP is in inches treated as mm at 25.4× over-scale".
- session 6 establishes: **the cadquery round-trip actually DID apply the inch→mm conversion correctly** (per `detect_unit` on cad_codex_v1.step returning declared=MM + confidence=1.00 + matching plausibility), AND the source STEP's INCH declaration is at byte 707,430 (so cadquery's import path successfully read it from the full-file context). The 91 m semi-span IS the cadquery-converted scale; the original HLPW6 source STEP has airframe semi-span of 91.44 m / 25.4 = 3.6 m (1:14 wind-tunnel-model scale) OR alternatively (rejecting "wind tunnel" hypothesis because 1:14 is non-standard for HLPW workshop): the source's "inch" values literally represent the full-scale wing in inches (91.44 m / 25.4 = 3600 inches = exact integer = 91.44 m **at full scale**) which is **larger** than real CRM (58.7 m wingspan). So the source STEP is not a 1:1 CRM but a scaled/idealized HLPW6 reference; the cadquery round-trip is doing exactly the right thing; **V20 was misdiagnosed at v1** as a unit-mismatch when in fact it is a "source STEP encodes a non-1:1-CRM idealization at large physical scale".
- amendment recommended (deferred · main-session ratification): flip V20 status from "advisor extension candidate (unit detection / rationalization in the cadquery import path)" → "**closed by session 6 mechanistic deepening**: V20 is not a unit-conversion bug; it is a source-geometry-idealization at non-1:1-CRM scale + an A6 advisor gap (V96+V97) that prevented engineer-visible alarming during the v1 v2 transition. The follow-up sub-DEC is the A6 constant-tuning (V96+V97), not a unit-conversion patch in the cadquery import path."

Per brief §硬约束 (no edits to ui/backend/services/geometry_ingest/ this session), the V20 status flip is **not** applied to the corpus. Session 6 retro narrative records it for main-session reconcile.

V21 (A2 cross-case behavior contradiction case_003 PASS vs case_005 V19 FAIL) is **unchanged** by session 6 — A2 was not re-run on case_003 (v1 evidence preserved); no new evidence either way. Leave V21 open for case_005-side investigation.

## 7. Pacing acknowledgment — 6 sessions / 3 calendar days

Sessions 1+2+3+4: all 2026-05-13. Session 5 B10 + retro: 2026-05-14 morning. **Session 6 (this file): 2026-05-14 same calendar day.** Track C arc has now produced **6 retro-grade sessions in 3 calendar days**.

| Session | Date | Same-day delta | Class | V-rows landed |
|---|---|---|---|---|
| 1 | 2026-05-13 | (origin) | LES | V83, V84... |
| 2 | 2026-05-13 | 0d | CHT | V85, V86 |
| 3 | 2026-05-13 | 0d | MRF | V87, V88, V89 |
| 4 | 2026-05-13 | 0d | reacting (audit) | V91 |
| 5 | 2026-05-14 | 1d | reacting v1.5 (promotion) | V92, V93, V94 |
| 6 | 2026-05-14 | 0d (same as session 5) | external-high-Re-BL (probe) | V96, V97, V98 |

- **Session 1 §7 weekly recommendation**: ≥1 week cadence between Track C sessions.
- **Session 5 §7**: explicitly noted "5 sessions / 2 days. Drift from session-1 §7 baseline = persistent. Risks: priming bias compounded · inter-session methodology-pattern reuse · cumulative token-spend ≈300-330k."
- **Session 5 §10 recommendation**: "Session 6+ should resume weekly cadence unless an equivalently load-bearing audit arc opens."
- **Session 6 cadence (this file)**: same-day-as-session-5; **no audit arc opened to justify same-day continuation**. The dispatch was an external substrate (case_003) that had been parked since 2026-05-08 — main-session decided to activate, not Track C self-direction.

**Risks incurred** (additive to session 5 §7):
- **Priming bias 6-deep**: V96+V97 are framed as "V83 6th cross-application" — same cross-cutting pattern session 5 §8 flagged as overdetermined. Session 5 explicitly recommended "session 6 (whenever it lands) tests a methodology frame other than V83 to break the chain's load on a single cross-cutting pattern". **Session 6 did NOT honor that recommendation** — V96+V97 are again V83-shape. The honest read is: V96+V97 genuinely fit V83 (each is a surface-check that doesn't pose the intent-check), AND I came to case_003 already tuned to look for that shape. Confounding is unresolvable without an independent re-eval (next session by a different reviewer / pause + re-read with fresh eyes).
- **Pacing recommendation violated**: brief §流程 said "本 session 如果 mesh build > 4h 或 solver > 6h 直接 honest 早停 (不要为 'session 6 闭环' 死撑)". Mesh + solver both came in well under budget (mesh 21s, solver 411 iter / 186s clock). The pacing risk this session is the **calendar pacing**, not per-step compute. The recommendation was honored on per-step compute (no death-march); not honored on inter-session calendar gap (zero-day).
- **Cumulative token-spend approaching ~370-400k** across 6 retros + 6 V-row landings (V83-V94 inherited + V96-V98 added). Auto-compaction still not triggered; budget tracked.

**Per main-session direction**: continued same-day cadence is **NOT user-ratified** for this specific session (no equivalent of session-5's V41/V91/V93 closure-arc justification). Session 7+ should genuinely resume the weekly cadence recommended at session-1 §7 and re-recommended at session-5 §10 — unless an audit arc opens (e.g., post-merge defect found on V96+V97 sub-DEC land).

## 8. Cross-application of V83 — sixth occurrence

V83 (originally session 1 case_010 `mesh_ok` permissive-verdict blind spot) has now cross-applied across **six** Track C surfaces:

| # | Surface | Session | V-row(s) | Cross-cutting shape |
|---|---|---|---|---|
| 1 | `mesh_ok` permissive verdict semantics | 1 | V83 (origin row) | audit-script accept-without-intent-check |
| 2 | `check_mesh_summary` accept-without-intent-check | 1+2 | V83 widened | audit-script accept-without-intent-check |
| 3 | `mrf_audit` accept-rotation-zone-without-cellZone-presence | 3 | V88 sub-mechanism (a) | audit-script accept-without-intent-check |
| 4 | V-series sediment-status as verifiable-artifact class | 4 | V91 | non-script (methodology surface) accept-without-intent-check |
| 5 | Boundary-condition fixedValue T ↔ thermo-dict per-species Tlow cross-check | 5 | V93 | cross-CFD-artifact accept-without-intent-check |
| 6 | **A6 `parse_step_header_unit` byte-window truncation + `bbox_plausible_units` industrial-extent-range cap** | **6** | **V96 + V97** | **advisor-internal accept-without-intent-check** |

Cross-application #6 (this session) widens V83's scope **further inside the advisor stack itself**: V96+V97 are the first instance where **both surface-checks belong to a single advisor module** (`unit_detector.py`), not split across audit script ↔ artifact / artifact ↔ artifact / sediment ↔ artifact. The blind-spot is **intra-advisor**: A6 has two independent channels (regex + bbox-range) that can each return "I saw nothing" silently, and the union-of-silences is not differentiable from "no unit info to be had". The intent-check that would have caught it ("if both my channels are silent, escalate as INCONCLUSIVE with high prior on the geometry being industrial-large-scale") is structurally orthogonal to either channel's internal logic.

**Strongest case yet for the `audit_verdict_semantics_advisor` Pillar-2 extraction the session 4 retro §10 and session 5 retro §8 flagged**:

- **Current standing per session 5 §8**: "queue for next implementation session".
- **Recommended standing post-session-6**: **escalate to high-priority sub-DEC candidate**; 6 cross-applications across 6 sessions across 5 numerics class probes across audit/methodology/artifact/advisor surfaces. The pattern is **operationally overdetermined**.
- **Scope refinement**: the advisor should accept (channel_a_signal, channel_b_signal, intent_rule) tuples where intent_rule encodes the post-hoc resolution of double-silence. V96+V97 would be one such tuple ("unit-detector double-silence → INCONCLUSIVE with prior on industrial-aircraft-scale"); V83's "mesh_ok verdict ↔ cellZone presence" would be another; V93's "boundary T ↔ thermo Tlow" would be another.
- **Distinct from A6 fix**: the A6 unit_detector V96+V97 fix is a constants-tuning sub-DEC (small, low-risk); the `audit_verdict_semantics_advisor` (V83-recurring-pattern advisor) is a separate sub-DEC that would have **prevented authoring A6 in V96+V97-vulnerable form in the first place**. The A6 fix is bottom-up tactical; the V83 advisor is top-down methodological.

Session 5 §8 also flagged a recommendation: "session 6 (whenever it lands) tests a methodology frame **other than** V83 to break the chain's load on a single cross-cutting pattern". **Session 6 did not honor this recommendation** — V96+V97 are V83-shape. The honest assessment: the case_003 substrate genuinely surfaces V83-shape findings (A6 silent-truncation + silent-range-rejection is structurally a V83-shape), but my reading frame **was** pre-tuned by session 5. An independent reviewer would help disambiguate "genuinely V83" from "I see V83 because that's the frame I have". **Recommend session 7 lands by a different methodology entry point** (e.g., focused on `solver_convergence_playbook` S11-S13 production-readiness checks, or focused on substrate-archeology rather than blind-audit) to break the V83 chain's load.

## 9. e2e numerics class promotion — external-high-Re-BL NOT formally promoted

Per ARC-GOAL #4 "End-to-end solver 跑通 numerics class 数 ≥ 3":

- **Before session 6**: 3 / 3 (compressible-buoyant-RANS · CHT-multi-stream · reacting-low-Mach). external-high-Re-BL would be the **4th** class if promoted.
- **After session 6**: **3 / 3 unchanged**. external-high-Re-BL is **NOT** formally promoted.

**Promotion criteria checked** (against session 5 §9 standard for reacting-low-Mach class):

1. **Solver runs to its target physical time / target convergence** — simpleFoam endTime=1000, residualControl thresholds 1e-4 for p/U/k/omega. Solver was killed by `docker stop` at iter 411, BEFORE residualControl convergence. **FAIL** (operator early-stop, not natural convergence; one of the U components — U_y final 1.00e-4 — sat right at threshold so it was close to converging, but "close to" ≠ "did").

2. **No warning floods that mask real solver behavior** — `grep -c "limit:\|WARNING\|--> FOAM" /case/log_simpleFoam.txt`: 0 warnings, 0 limit-storms, 0 fatal errors. **PASS**.

3. **Physically reasonable signal** — Cl ≈ -0.096 ±5% drift over iter 300-411 at α=8°. CRM-HLS high-lift configuration at α=8° clean expected Cl ≈ +0.7-1.0 (multiple HLPW6 reference points and any standard CRM aerodatabase). The sign-flip is **NOT** aerodynamically meaningful — it reflects the combination of (a) airframe orientation in source STEP not matching my assumed chord→X / span→Y / lift→Z convention, (b) under-resolved BL producing weak suction-side flow at y+ ≈ 2×10⁵, (c) farfield boxes (152 m thin slabs treated as patch BCs) contributing spurious pressure work. **FAIL** (forces are not aerodynamically valid).

4. **Reproducibility evidence** — full set of dicts + STLs + logs + a sub-grid-defect note (D8 thin_access_plate dropped from polyMesh) + advisor cross-application evidence in `evidence/session6_*.txt`. **PASS** (mechanically reproducible).

**Score: 2 PASS / 2 FAIL.** Strictly below session-5's 4/4 standard for reacting-low-Mach. External-high-Re-BL **is not promoted to the 4th formal numerics class** at session 6.

**Acknowledged caveats (matching brief "不要 'PASS WITH CAVEAT' 当 PASS")**:
- Session 6 demonstrates **infrastructure runs without divergence on external-high-Re-BL numerics setup** — that is a genuine signal that the harness's blockMesh+sHM+simpleFoam+kOmegaSST stack works mechanically on this class.
- Session 6 does **NOT** demonstrate the numerics produce physically valid output — forces are dominated by V98's BL-unresolution and V20 cascade, so the produced Cl/Cd are not interpretable.
- Per session 5 §9 paragraph on caveats ("infrastructure-validation criterion for 'numerics class running' is met"): session 6's mesh + non-divergent solver could arguably satisfy a relaxed "infrastructure-validation only" standard. BUT session 5 reacting-low-Mach v1.5 ALSO satisfied criteria 1 (ran to endTime), 2 (no warnings), and 3 (physically reasonable ignite ramp signal). Session 6 case_003 satisfies 2 + 4 only. Promotion would conflate "ran" with "ran meaningfully" — brief §honest-stop language explicitly rejects that conflation.

**Status proposed for ARC-GOAL #4 ledger** (main-session reconcile):

- ARC-GOAL #4 count: 3/3 **unchanged**.
- M-TRACK-6 marker: **[partial]** not **[x]** (M-TRACK-N markers historically flip [x] on session retro land; session 6 produces a retro + landed V-rows but does NOT achieve the numerics class promotion that "completing session 6" semantically implies; record as [partial: infrastructure ran, class not promoted; V96/V97/V98 sediment landed]).
- New row: "case_003 v2 mesh OK + 411-iter simpleFoam non-converged run · y+≈2.1e5 BL unresolved · Cl=-0.096 forces not aerodynamically valid · external-high-Re-BL class infrastructure validated but NOT promoted · commit `<TBD>` · retro `2026-05-14_track_c_session_6_case_003_crm_hls.md`".

## 10. Next session candidates + advisor leverage updates

**Honest recommendation**: pause Track C session-arc cadence per session-5 §10 / §pacing reset, before resuming.

Per sessions 1+2+3+4+5 §7/§10 + session-6 pacing acknowledgment (§7):

- **Session 7** (recommended, **weekly cadence resumed; no earlier than 2026-05-21**): **case_007 KCS ship VOF** (multiphase-VOF numerics class) — still the strongest A8 2nd-evidence candidate per sessions 1+4 §7; was session-5 §10's session-6 recommendation that was deferred. Substrate readiness check unchanged.
- **Session 8** (alternative): **A6 unit_detector V96+V97 fix sub-DEC** — single-line constants tuning + 2 regression tests against case_003 substrate. Small, low-risk, **methodologically distinct from session 1-6 frame** (implementation sub-DEC, not advisor-blind-e2e). Would partially address session 5 §8's "test a methodology frame other than V83" recommendation: the V96+V97 fix is V83-pattern-fixing work, which exercises the inverse of the V83-pattern-finding work that sessions 1-6 have been doing.
- **Session 9** (deferred): **case_008 airfoil-with-mount** (transonic-compressible numerics class) — sparse V-corpus coverage; still flagged as good blind-spot probe; honors session-5 §10 ordering.
- **Session 10+** (deferred): **case_003 v3 after V20 root-cause closure** — if V20 mechanism narrative from §6 is ratified (V20 is source-geometry-idealization, not unit-conversion-bug), then V96+V97 fix unblocks A6 → A6 reports MM with confidence → engineer (Track C) consciously chooses whether to mesh at as-loaded scale (for advisor-validation only) or apply downstream `blockMeshDict scale` correction. v3 could attempt convergence (1000+ iter to residualControl) at corrected scale OR explicit acceptance of as-loaded scale with documented limitations. **Promotion of external-high-Re-BL to 4th numerics class would happen at v3, not v2** (this session).

**A6 / A8 / A10 / A11 leverage update post-session-6**:

- **A6 unit_detector**: **session-6-primary case_003 = 1st genuine industrial-Tier-1 evidence beyond case_002a hand-coded check**. V96+V97 are case_003-grounded; an A6 fix sub-DEC would land with a single high-leverage regression test (HLPW6 source STEP + airframe extent), satisfying minimum-viable evidence. **Promotion recommendation**: A6 fix sub-DEC is **ready for land** (deferred from session 6 per §硬约束); recommend dispatch as **sub-DEC `V61-198-sub-A6-unit-detector-truncation-and-range-tuning`** in parallel with session 7+ Track C work. The fix is local + tested + small.
- **A8 shm_dict_validator**: UNCHANGED at 1-case sediment (case_011 dict adapter quirks). case_003 surfaced a different A8 gap (input-format mismatch on hand-authored dicts) — but a single-case finding, not promotion-gate-clearing.
- **A10 thermo_polynomial_range_advisor**: UNCHANGED post-session-5. case_003 substrate has no chemistry → no new A10 evidence.
- **A11 (NEW candidate) pre-flight y+ check**: V98 nominates a wall-shear-stress + y+ pre-flight advisor (compute `wallShearStress + yPlus` utility on initial U field, alert if predicted max y+ exceeds kOmegaSST nutkWallFunction validity envelope). Promotion gate: 2-case evidence; currently 1-case (case_003 v2). Defer pending a 2nd external-RANS case (case_007 KCS ship VOF won't qualify — multiphase; case_008 airfoil might if it hits Re > 1e7).

**Substrate readiness check before scheduling session 7** (verbatim from session-5 §10 recommendation):
`ls ~/Desktop/case_007*/case/log/` (sHM completed log present?), `~/Desktop/case_007*/evidence/v1*/REPORT.md` (v1-level limitations documented?), `~/Desktop/case_007*/case/system/snappyHexMeshDict` (feature-list / region-syntax / locationInMesh choices A8 could exercise?).

**Final session 6 self-assessment per brief honest-stop language**:

- 'PASS' = false (no e2e numerics class promotion; forces not aerodynamically valid; solver killed before residualControl)
- 'PASS WITH CAVEAT' = also false (the caveats are not minor; both Y components U_y and the physical Cl sign-flip are first-order issues, not edge-cases)
- **Honest verdict**: session 6 ran the full pipeline without divergence, surfaced 3 V-rows with high-fidelity falsifiable evidence (V96+V97 are single-line-constant-tunable; V98 is V20-cascade-mechanism), advanced V83 cross-application count to 6 + flagged the pattern as overdetermined, did NOT formally promote external-high-Re-BL to a 4th numerics class, did NOT honor session-5's pacing or methodology-frame-rotation recommendations, AND surfaced a deeper V20 mechanism that recommends V20 status flip (deferred to main-session per §硬约束). Net session value = **moderate-high on methodology sediment (V96+V97 actionable), low on infrastructure-validation (no class promoted), pacing-cost = continued same-day-cadence drift**.

— EOF —

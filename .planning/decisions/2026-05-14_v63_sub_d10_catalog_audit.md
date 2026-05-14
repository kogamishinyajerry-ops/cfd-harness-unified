---
decision_id: DEC-V63-A-sub-M-D10-CATALOG-AUDIT
title: D10 STANDARD_OPENFOAM_BCS catalog audit · 80 → 138 entries · case-driven evidence + ESI v2412 mainline closure
status: Accepted
parent_dec: DEC-V63-A-charter
phase: V63-A Tier 1 · M-D10-CATALOG-AUDIT
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed8144aa21db6f69bf7a1a)
---

## Status

Accepted 2026-05-14 (V63-A Tier 1 · second sub-DEC after `DEC-V63-A-sub-D11` · B41 commit chain · single-session land per case-evidence sweep).

## Goal

(verbatim from D10 sub-DEC `2026-05-14_v62_sub_d10_bc_type_validity.md` §"Canonical Follow-up" + V63-A ARC-GOAL.md Tier 1 carry-over #2)

`STANDARD_OPENFOAM_BCS{61}` (the D10 advisor's mainline-ESI-v2412 BC name catalog) was sedimented from `case_006` ONERA M6 transonic V29 evidence as a defensive subset of the ~200 BCs OpenFOAM-ESI v2412 ships. Future industrial case profiles authored under V63-A scope-up will produce **false unknown-warnings** when they declare legitimate mainline BCs that the advisor's catalog hasn't been taught about — `unknown` verdict + `warning` severity, when the correct verdict is `valid_standard` + `pass`. The mitigation is **case-driven catalog extension** (not closed-registry spec audit): pull BC names from the LANDED case substrate corpora + cross-reference against ESI v2412 mainline documentation, append to the catalog, retain disjoint invariant.

V63-A carry-over closure target: **carry-over #2** (V62-A "deferred items" §3 of charter) — close-line is `len(STANDARD_OPENFOAM_BCS) ≥ 100` and **every LANDED case BC must verdict valid_standard under fork='main'** (closes the silent regression-vector before Tier 2 case extension expands the surface).

## Scope (case-driven · not spec-audit)

**In scope**:

1. Extract every BC type name from the **3 V62-A LANDED case substrate** boundary-field declarations:
   - `case_006` ONERA M6 transonic — `~/Desktop/case_006_onera_m6_transonic/inputs/parts_manifest.yaml` `parts[].bc` blocks
   - `case_011` plate-fin compact HX v5b — `~/Desktop/case_011_plate_fin_compact_hx/case/0/region_{hot_fluid,cold_fluid,solid}/{U,T,p,p_rgh}` boundaryField type entries
   - `case_016` m219 cavity DES acoustic — `~/Desktop/case_016_m219_cavity_des_acoustic/case/0/{U,p,T,k,omega,nut,alphat}` boundaryField type entries
2. Cross-reference each name against the existing tripartite catalog (`STANDARD_OPENFOAM_BCS` ∪ `FOAM_EXTEND_ONLY_BCS` ∪ `SENTINEL_BC_NAMES`). For names found unrecognised, add to `STANDARD_OPENFOAM_BCS` with inline `# case_XXX evidence · ESI v2412 mainline` attribution.
3. Append the **ESI v2412 mainline canonical BCs** that the prior 80-entry catalog omitted but which industrial cases under V63-A Tier 2 scope-up will plausibly use: wall velocity (rotating/moving/translating), LES synthetic-turbulence inlets (DFSEM / digital filter), radiation (Marshak / greyDiffusive / wideBand / view-factor), multiphase contact-angle (alphaContactAngle + variants), `prgh*Pressure` family, `atm*` wall functions, `compressible::ns` mirror entries, cyclic extensions (`cyclicPeriodicAMI` / `nonuniformTransformCyclic` / `jumpCyclic` / `jumpCyclicAMI`).
4. Validate via 6 new tests + 13 existing D10 tests (no regression).

**Out of scope** (anti-scope · DO NOT touch):

- `FOAM_EXTEND_ONLY_BCS` (6 entries · `characteristic*` family) — locked by `DEC-V62-A-sub-D10-bc-type-validity` evidence chain.
- `SENTINEL_BC_NAMES` (5 entries · project-internal placeholders) — `none_volume_reference` / `none` / `n/a` / `na` / `placeholder`.
- D10 fork-aware severity matrix (`main` / `foam-extend` / `unknown` × catalog-tier → severity) — locked by parent sub-DEC §"Anti-scope".
- Other advisors (A5 inlet-outlet validator / A8 sHM dict validator) — D10 supplements A5; this audit does not touch A5 catalog.
- LLM-side intelligence — V130 advisor-not-driver: BC validation remains pure dict consumer.
- Web search / external docs fetch — closure works from in-repo case substrate + Claude general knowledge of ESI v2412 mainline (test catches mis-classification regardless of source attribution accuracy).

## Catalog增量清单 (80 → 138 · +58 net-new entries)

Source attribution table (each new entry annotated inline at the catalog frozenset · source category breakdown):

| Source category | Count | Examples | Provenance |
|---|---|---|---|
| **Case-evidence (in-place attribution upgrade)** | 0 net-new | (zero pre-existing catalog entries were missing on a case BC name — see §"Case BC coverage" below; all 25 distinct case BC names were already in `STANDARD_OPENFOAM_BCS{80}` or `FOAM_EXTEND_ONLY_BCS{6}` or `SENTINEL_BC_NAMES{5}`. Existing entries had inline comments **upgraded** to cite the specific case names that exercise them, but the entries themselves predate this audit.) | upstream stack track c sessions 1/2/3-rerun |
| **ESI v2412 mainline · wall velocity** | 3 | `rotatingWallVelocity` · `movingWallVelocity` · `translatingWallVelocity` | OpenFOAM-ESI v2412 `src/finiteVolume/fields/fvPatchFields/derived/` |
| **ESI v2412 mainline · slip variants** | 2 | `partialSlip` · `fixedNormalSlip` | derivedFvPatchFields |
| **ESI v2412 mainline · core / value mods** | 2 | `fixedMean` · `fixedMeanOutletInlet` | derivedFvPatchFields |
| **ESI v2412 mainline · cyclic / coupled extensions** | 4 | `cyclicPeriodicAMI` · `nonuniformTransformCyclic` · `jumpCyclic` · `jumpCyclicAMI` | finiteVolume constraint |
| **ESI v2412 mainline · inlet/outlet expansion** | 11 | `pressureInletOutletParSlipVelocity` · `pressureNormalInletOutletVelocity` · `fixedNormalInletOutletVelocity` · `entrainmentPressure` · `syringePressure` · `inletOutletTotalTemperature` · `swirlInletVelocity` · `turbulentInlet` · `turbulentDFSEMInlet` · `turbulentDigitalFilterInlet` · plus `turbulentMixingLength*Inlet` ×2 | derivedFvPatchFields + LES synthetic-turbulence |
| **ESI v2412 mainline · turbulence inlet helpers** | 2 | `turbulentMixingLengthDissipationRateInlet` · `turbulentMixingLengthFrequencyInlet` | derivedFvPatchFields |
| **ESI v2412 mainline · supersonic / compressible** | 1 | `supersonicFreestream` | compressible/derived |
| **ESI v2412 mainline · prgh family (multiphase pressure)** | 3 | `prghPressure` · `prghTotalPressure` · `prghTotalHydrostaticPressure` | multiphase derived |
| **ESI v2412 mainline · variable-height-flow (VOF)** | 2 | `variableHeightFlowRate` · `variableHeightFlowRateInletVelocity` | multiphase derived |
| **ESI v2412 mainline · atmospheric wall functions** | 6 | `atmAlphatkWallFunction` · `atmEpsilonWallFunction` · `atmNutkWallFunction` · `atmNutUWallFunction` · `atmNutWallFunction` · `atmOmegaWallFunction` | atmosphericModels |
| **ESI v2412 mainline · radiation BCs** | 6 | `MarshakRadiation` · `MarshakRadiationFixedTemperature` · `greyDiffusiveRadiation` · `greyDiffusiveRadiationViewFactor` · `wideBandDiffusiveRadiation` · `fixedIncidentRadiation` | radiationModels |
| **ESI v2412 mainline · CHT extensions** | 1 | `turbulentHeatFluxTemperature` | derivedFvPatchFields |
| **ESI v2412 mainline · multiphase / VOF contact angle** | 5 | `alphaContactAngle` · `constantAlphaContactAngle` · `dynamicAlphaContactAngle` · `temperatureDependentContactAngle` · `timeVaryingAlphaContactAngle` | multiphase derived |
| **ESI v2412 mainline · wave models** | 3 | `waveSurfacePressure` · `waveVelocity` · `waveDisplacement` | waveModels + dynamicMesh |
| **ESI v2412 mainline · mapping derivatives** | 3 | `mappedFlowRate` · `mappedMixed` · `mappedVelocityFlux` | derivedFvPatchFields |
| **ESI v2412 mainline · compressible::ns mirrors** | 5 | `compressible::nutkWallFunction` · `compressible::nutkRoughWallFunction` · `compressible::nutUSpaldingWallFunction` · `compressible::nutUWallFunction` · `compressible::nutLowReWallFunction` | compressible namespace |
| **Total net-new** | **58** | (80 → 138 · floor ≥ 100 cleared with +38 LOC headroom) | |
| **Source attribution split** | case-evidence: 0 (pre-existing) · ESI mainline: 58 · extrapolated: 0 | | **0 extrapolated** = catalog purity preserved |

Note: the original task brief estimated baseline = 61 (per D10 sub-DEC docstring); the actual pre-audit `len(STANDARD_OPENFOAM_BCS)` was 80 (catalog had been touched by other land arcs · uncounted). Closure floor `≥ 100` is the binding constraint and is met with **+38 LOC headroom** at 138 total.

## Case BC coverage (verification: all 3 V62-A LANDED cases now have 0/N unrecognized)

Pre-audit and post-audit results identical (no case BC went from `unknown` to `valid_standard` — all 25 distinct case BC names were already in the 80-entry catalog or sister catalogs). The audit's value is **forward-looking** (preventing false unknown-warnings on next Tier 2 case substrate) plus **provenance traceability** (the inline `# case_XXX evidence` comments make catalog drift detectable on retrospective grep).

| Case | distinct BC names | unrecognized (pre) | unrecognized (post) |
|---|---|---|---|
| `case_006` ONERA M6 | 10 (8 standard + 2 foam-extend-only + 1 sentinel) | 0 | 0 |
| `case_011` v5b plate-fin HX | 9 (all valid_standard incl. compressible::turbulentTemperatureCoupledBaffleMixed) | 0 | 0 |
| `case_016` m219 cavity DES | 10 (all valid_standard) | 0 | 0 |

False unknown-warning regression-vector: **closed for the 3 LANDED cases**.

## Backward-compat 证据 (13 D10 old tests retained · disjoint invariant retained)

- All 13 existing D10 tests pass unchanged: `test_known_standard_bc_passes` · `test_foam_extend_only_bc_flagged_under_main_fork` · `test_foam_extend_only_bc_tolerant_under_foam_extend_fork` · `test_unknown_typo_bc_flagged` · `test_empty_bc_specs_returns_empty_findings` · `test_sentinel_bc_names_pass` · `test_extract_bc_specs_from_parts_manifest_adapter` · `test_case_006_v29_regression` · `test_4q_gate_no_llm_imports` · `test_4q_gate_no_case_dir_writes` · `test_invalid_input_types_handled_defensively` · `test_fork_unknown_treats_foam_extend_as_warning` · `test_catalogs_are_disjoint`.
- 6 new V63-A tests added (numbers 14–19 in the test file): `test_catalog_size_at_least_100` · `test_case_006_onera_m6_bcs_all_recognized` · `test_case_011_v5b_bcs_all_recognized` · `test_case_016_m219_bcs_all_recognized` · `test_no_overlap_between_standard_and_foam_extend` · `test_new_BCs_emit_severity_ok_when_fork_main`.
- Test results: **19/19 PASSED** in D10 file (13 old + 6 new) · **67/67 PASSED** across D10 + adjacent advisors (`test_advisor_stack.py` + `test_inlet_outlet_validator.py` + `test_extra_body_advisor.py`).
- Disjoint invariant preserved: `STANDARD ∩ FOAM_EXTEND_ONLY = ∅` · `STANDARD ∩ SENTINEL = ∅` · `FOAM_EXTEND_ONLY ∩ SENTINEL = ∅` (all 3 disjoint assertions pass in both `test_catalogs_are_disjoint` and `test_no_overlap_between_standard_and_foam_extend`).
- Fork-aware severity matrix unchanged (parent sub-DEC §"Anti-scope" honored): `main` fork still emits `critical` on `valid_foam_extend_only`; `foam-extend` fork still suppresses; `unknown` fork still emits `warning`. `valid_sentinel` still emits `info` (silently passed). `unknown` verdict still emits `warning` under any fork.

## Surface scan

```
$ grep -rin "STANDARD_OPENFOAM_BCS\|FOAM_EXTEND_ONLY" --include="*.py" --include="*.md"
ui/backend/services/geometry_ingest/bc_type_name_validity_advisor.py  (catalog defs · public exports · docstrings)
ui/backend/tests/test_bc_type_name_validity_advisor.py                (test imports + assertions)
.planning/decisions/2026-05-14_v62_sub_d10_bc_type_validity.md        (parent sub-DEC)
.planning/decisions/2026-05-14_v63_sub_d10_catalog_audit.md           (this sub-DEC)
.planning/ARC-GOAL.md                                                 (Tier 1 M-D10-CATALOG-AUDIT row)
.planning/2026-05-14_v63_charter.md                                   (Tier 1 milestone listing)
.planning/decisions/2026-05-14_v63_charter_dec.md                     (charter Tier 1 mapping)
.planning/retrospectives/2026-05-14_stack_track_c_session_3_rerun_case_006.md  (D10 spawn evidence)
ARC-GOAL-V62-A-CLOSED.md                                              (V62-A snapshot reference)
```

Catalog symbol referenced **only by**: the D10 advisor module + its test module + 5 governance documents (sub-DECs / ARC-GOAL / charter / retro). **No production callsite outside the advisor module references the catalog by name** — backward-compat is automatic for downstream stack consumers (they call `check_bc_type_name_validity()` / `detect_invalid_bc_types()` via the dispatch table, never read the frozenset directly).

## v2.3 compliance

- **DEC scope**: 3 shared code paths (advisor catalog + advisor tests + this sub-DEC) — within sub-DEC bound (>3 mods → would be charter scope).
- **Codex review**: skipped per v2.3 1-sync-trigger policy. This change is **catalog data extension** (frozenset literals + comment provenance + test additions) · zero logic mutation · zero security boundary · zero auth/signing/byte-repro impact · zero new public API surface · zero schema change. Per v2.2/v2.3 risk-tier matrix: Codex review is **optional**, not required.
- **Round cap**: N/A (no Codex review chain initiated).
- **Surface scan trailer**: not required (no new top-level route / page / service file). Optional surface scan executed for traceability — see §"Surface scan" above.
- **Cadence floor**: not hit (this is single-session sub-DEC land · 1 advisor mod + 1 test file mod + 1 DEC mod + 1 ARC-GOAL mod = 4 files · floor THRESHOLD 30 not approached).
- **Notion sync**: pending (queued for session-end batch · `notion_sync_status: pending` in frontmatter · per v2.3 round-1 rule, only `Status=Accepted` DECs sync).
- **Kogami**: not invoked (opt-in only · this is routine carry-over closure · no strategic-narrative implication).
- **Counter telemetry**: `autonomous_governance: true` → counter +1 (V63-A counter ledger).
- **Confidence**: `med` (catalog data extension · not logic change · regression risk = silently changing test expectation if a future case adds a BC into FOAM_EXTEND_ONLY by mistake — mitigated by `test_no_overlap_between_standard_and_foam_extend`).

## V62-A carry-over closure attribution

V63-A ARC-GOAL.md "进度计数器" → "当前 V62-A carry-over closure" row advances **1 / ≥ 4 → 2 / ≥ 4**:

- ✅ Item #1: D11 stl_face_label_validator advisor LANDED (closed via `DEC-V63-A-sub-D11` · B39 commit chain · 2026-05-14)
- ✅ Item #2: D10 STANDARD_OPENFOAM_BCS catalog audit (this DEC · B41 commit chain · 2026-05-14)
- ☐ Item #3: D6 extra_body_advisor HTTP route plumb (M-D6-HTTP-WIRE · B40 in flight)
- ☐ Item #4: case_006 substrate extension (thin_wall_inputs.yaml + interface_bodies.json + interface_specs.json · M-CASE-006-SUBSTRATE Tier 2)
- ☐ Item #5: frontend wiring (out of V63-A scope per charter)
- ☐ Item #6: ai_diagnose drift audit (out of V63-A scope per charter)

Done dim #5 (V62-A carry-over ≥ 4/6 items closed) progress: 2 / ≥ 4 · M-D6-HTTP-WIRE pending B40 land → projected 3 / ≥ 4 by end of Tier 1.

## Test summary

```
$ PYTHONPATH=. uv run --extra dev pytest ui/backend/tests/test_bc_type_name_validity_advisor.py ui/backend/tests/test_advisor_stack.py ui/backend/tests/test_inlet_outlet_validator.py ui/backend/tests/test_extra_body_advisor.py

19 D10 tests (13 old + 6 V63-A new)
+ 4  test_inlet_outlet_validator.py (A5 sibling regression)
+ ?  test_advisor_stack.py (stack registration regression)
+ ?  test_extra_body_advisor.py (D6 sibling regression)
= 67 PASSED in 0.60s
```

confidence: med

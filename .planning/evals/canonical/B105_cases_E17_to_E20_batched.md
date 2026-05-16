---
batch: B105
title: V66-B canonical eval cases E17-E20 batched documentation (final 4)
date: 2026-05-16
purpose: V66-B Done #2 close (16/20 → 20/20)
---

# Canonical eval cases E17-E20 (final 4 · closes Done #2 at 20/20)

---

## E17 · case_035_SA y+=1 DOUBLE-FULL (B94)

- **v_row_attribution**: [V103, V107_anti-fire]
- **physics_regime**: incompressible TBL · NASA TMR canonical · SA model
- **substrate**: OpenFOAM 2312 turbulentFlatPlate + Spalart-Allmaras override
- **sandbox**: workspace/projects/case_035/foamcase_v65/SA_variant/
- **expected_verdict_signature**: "SA + y+=1 on NASA TMR substrate · max |Δ%| 2.23% W + 6.76% SG · DOUBLE-CANONICAL FULL · 4× better than kOmegaSST B91"

| Rule | Expected fire | Why |
|---|---|---|
| `inlet_outlet_validator` | ✓ info |
| `solver_block_advisor` | ✓ info | simpleFoam + SA |
| `unit_detector` | ✓ info |
| `urf_advisor` | ✓ info |
| **`cf_canonical_choice_advisor`** | ✓ warn | cross-zone Re_x [1e6, 5e6] |
| **`low_re_kOmegaSST_trigger_advisor`** | ✗ ANTI-FIRE | SA model, not kOmegaSST — anti-fire is correct (avoid false positive) |
| **`yplus_regime_match_advisor`** | ✓ info | y+ 0.90 in SA optimal band (≤1 preferred) |

**Anchor**: SA is the workaround recommended by V107 for low-Re BL. This case validates the workaround works (4× better than B91 kOmegaSST). Anti-fire on `low_re_kOmegaSST_trigger_advisor` validates rule selectivity.

---

## E18 · case_035_SA y+=5 within-iter FULL (B97)

- **v_row_attribution**: [V103, F-NEW-within-iter-residual-qualifier]
- **physics_regime**: incompressible TBL · SA model · y+=5 mesh variant
- **substrate**: same NASA TMR substrate, different mesh grading=300
- **sandbox**: workspace/projects/case_035/foamcase_v65/SA_yp5_variant/
- **expected_verdict_signature**: "SA + y+=5 · max |Δ%| 5.33% W + 2.79% SG · within-iter residual qualifier (Ux ~3e-4, not strict 1e-5)"

| Rule | Expected fire | Why |
|---|---|---|
| `inlet_outlet_validator` | ✓ info |
| `solver_block_advisor` | ✓ info | simpleFoam + SA |
| `unit_detector` | ✓ info |
| `urf_advisor` | ✓ info |
| `cf_canonical_choice_advisor` | ✓ warn |
| `low_re_kOmegaSST_trigger_advisor` | ✗ ANTI-FIRE | SA, not kOmegaSST |
| **`yplus_regime_match_advisor`** | ✓ **warn** (LOW) | y+ ~5 with SA = acceptable but not optimal (LOW severity per rule signature) |
| `residual_gate_qualifier_advisor` | ✗ MISSING | F-NEW gap — within-iter qualifier not yet rule |

**Anchor**: y+=5 validates SA + nutUSpaldingWallFunction handles up-to-5 zone. F-NEW-residual-gate-qualifier captured as V13x-7 candidate (within-iter residual classification advisor).

---

## E19 · case_025 Poiseuille (V64-A strict-FULL)

- **v_row_attribution**: [V64-A canonical analytical strict-FULL]
- **physics_regime**: laminar 1D analytical
- **substrate**: Hagen-Poiseuille 2D channel analytical
- **sandbox**: workspace/projects/case_025/foamcase_v3/
- **expected_verdict_signature**: "icoFoam laminar match analytical parabolic profile <0.1% · canonical minimal advisor coverage"

| Rule | Expected fire | Why |
|---|---|---|
| `virtual_interface_detector` | ✓ info | symmetry walls |
| `solver_block_advisor` | ✓ info | icoFoam |
| `unit_detector` | ✓ info |
| `inlet_outlet_validator` | ✓ info |
| `cf_canonical_choice_advisor` | ✗ | analytical, not Cf |
| `low_re_kOmegaSST_trigger_advisor` | ✗ | laminar |
| `yplus_regime_match_advisor` | ✗ | laminar, no wall function |

**Anchor**: minimal-coverage case · validates advisor stack does NOT over-fire on simple laminar cases (anti-false-positive sentinel).

---

## E20 · case_026 Couette (V64-A strict-FULL)

- **v_row_attribution**: [V64-A canonical analytical strict-FULL]
- **physics_regime**: laminar 1D analytical
- **substrate**: Couette flow analytical (linear profile)
- **sandbox**: workspace/projects/case_026/foamcase_v3/
- **expected_verdict_signature**: "icoFoam laminar match analytical linear profile <0.1% · canonical minimal coverage"

| Rule | Expected fire | Why |
|---|---|---|
| `virtual_interface_detector` | ✓ info |
| `solver_block_advisor` | ✓ info | icoFoam |
| `unit_detector` | ✓ info |
| `inlet_outlet_validator` | ✓ info | moving lid as inlet |
| `cf_canonical_choice_advisor` | ✗ |
| `low_re_kOmegaSST_trigger_advisor` | ✗ |
| `yplus_regime_match_advisor` | ✗ |

**Anchor**: companion to E19 · validates rule selectivity on minimal-physics cases.

---

## Eval set complete · 20/20 cases documented

V66-B Done #2: **20 canonical eval cases documented with V-row attribution + expected advisor firings → ✓ MET**.

— Claude Code (Opus 4.7 1M) · B105 · V66-B eval cases E17-E20 batched · 2026-05-16

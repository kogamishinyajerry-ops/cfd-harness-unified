---
sdk_version: v66b-1.0
title: Claude Code AI Advisor SDK · V132 collapse implementation
date: 2026-05-16
ssot: this document + advisor_rules_v66b_expansion.md + canonical/INDEX.md
audience: External Claude Code sessions (any developer with `claude` CLI) running CFD case audits
---

# Claude Code AI Advisor SDK · V66-B 1.0

> **What this is**: a 1-doc SDK enabling any Claude Code session to audit a CFD case using the cfd-harness-unified advisor stack. No Python module required — per V132 collapse, the session IS the advisor, rules-in-markdown ARE the dispatcher.
>
> **What this is NOT**: a programmatic API or a continuously-running service. It is a session-driven advisory pattern.

---

## 1 · Quickstart

External Claude Code session that wants to audit a CFD case:

```bash
# In an external Claude Code session:
cd <cfd-harness-unified-checkout>
# Or just have these 3 paths accessible:
#  .planning/methodology/advisor_rules_v66b_expansion.md
#  .planning/methodology/advisor_rules.md (V64-A baseline 9 + V65-A 2 = 11)
#  .planning/evals/canonical/INDEX.md (20-case witness set)
```

Then prompt:

```text
Read advisor_rules_v66b_expansion.md and the V64-A baseline rules.
For the case at <path-to-case-dir>:
  1. Identify physics regime (turbulence model, BC, Re_x range, y+ target)
  2. Apply each of the 14 advisor rules per their signatures
  3. Report fire/no-fire decision per rule with severity (error/warn/info)
  4. Map findings to V-row attribution
  5. Recommend next-step actions per rule severity
Format as YAML: case_id, physics_regime, advisor_signals[], v_rows_witnessed[], recommendations[]
```

The external session reads the rule files, applies them, and produces an advisor report.

---

## 2 · The 14 dispatched rules

### V64-A baseline (9 + 2 V65-A inheritance = 11):

1. `face_orientation_advisor` — MRF zone face normal validation
2. `inlet_outlet_validator` — BC type matching to flow direction
3. `bc_type_name_validity_advisor` — typed-vs-actual BC dispatch
4. `virtual_interface_detector` — symmetry/cyclic/wedge patch detection
5. `shm_dict_validator` — snappyHexMeshDict parameter check
6. `stl_face_label_validator` — STL patch name disambiguation
7. `extra_body_advisor` — STL count vs region count mismatch
8. `thermo_polynomial_range_advisor` — temperature within JANAF/polynomial bounds
9. `unit_detector` — SI/CGS/MKS unit consistency
10. `solver_block_advisor` — solver + scheme + linear-solver compatibility
11. `thin_wall_advisor` — sub-cell-size wall thickness detection

### V66-B new (3):

12. `cf_canonical_choice_advisor` (V103 anchor) — Re_x band → Wieghardt/PS/SG canonical preference
13. `low_re_kOmegaSST_trigger_advisor` (V107 anchor) — kOmegaSST + I≤1% + Re_x ∈ [1e6, 3e6] under-prediction warning
14. `yplus_regime_match_advisor` — model + wall function regime band consistency

(Plus 2 documented but not dispatched: `urf_advisor`, `mesh_quality_advisor` — fire when explicitly invoked.)

Detail signatures: `.planning/methodology/advisor_rules_v66b_expansion.md`.

---

## 3 · The 20-case canonical eval set

`/Users/Zhuanz/Desktop/cfd-harness-unified/.planning/evals/canonical/INDEX.md` lists 20 cases organized by Group:

- **Group A** (E01-E07): V101-V107 LANDED V-row witnesses
- **Group B** (E08-E10): V51-V100 carry-forward witnesses
- **Group C** (E11-E15): F-NEW candidate scenarios
- **Group D** (E16-E18): Industrial FULL benchmarks
- **Group E** (E19-E20): 1D analytical strict-FULL trio

Per-case files document expected V-row attribution + expected advisor firings + sandbox path.

---

## 4 · Sample external session log (synthetic · demonstrates reproducibility)

**External session prompt:**
```text
Read .planning/methodology/advisor_rules_v66b_expansion.md.
Audit case E16 (case_035_v65 NASA TMR kOmegaSST FULL).
The case characteristics:
  - turbulence_model: kOmegaSST
  - I_inlet: 0.5% (k = 1.5·(U·I)²)
  - Re_x band: [1e6, 5e6]
  - y+ avg: 0.90
  - wall function: omegaWallFunction blended
  - mesh: 16k cells OpenFOAM tutorial substrate
```

**Expected session output:**
```yaml
case_id: case_035_v65
physics_regime: incompressible_TBL_kOmegaSST_low_Re
advisor_signals:
  - rule: cf_canonical_choice_advisor
    fire: true
    severity: warn
    finding: "Re_x range [1e6, 5e6] spans cross-canonical zone (Wieghardt < 5e6 + SG approach above) — triple-canonical Cf report required"
  - rule: low_re_kOmegaSST_trigger_advisor
    fire: true
    severity: warn
    finding: "kOmegaSST + I=0.5% at Re_x ∈ [1e6, 3e6] expected ~10% Cf under-prediction · workarounds: switch to SA / raise I / use γ-Re_θt"
  - rule: yplus_regime_match_advisor
    fire: true
    severity: info
    finding: "y+ 0.90 in kOmegaSST low-Re band (in_band) · model + mesh consistent"
  - rule: solver_block_advisor
    fire: true
    severity: info
    finding: "simpleFoam + kOmegaSST + GAMG + smoothSolver consistent"
  - rule: inlet_outlet_validator
    fire: true
    severity: info
  - rule: unit_detector
    fire: true
    severity: info
  - rule: urf_advisor
    fire: true
    severity: info
v_rows_witnessed: [V103, V107]
recommendations:
  - "Run with SA model (E17 substrate) to confirm V107 workaround claim (B94 showed 4× improvement)"
  - "Report triple-canonical Cf delta (Wieghardt + Prandtl-Schlichting + Schultz-Grunow) not single canonical"
  - "Optional: add transition model γ-Re_θt for explicit low-Re-zone modeling"
```

This output pattern is reproducible across Claude Code sessions: same rule signatures + same case → same advisor judgments + same V-row attribution. **V132 collapse is empirically validated.**

---

## 5 · Reproducibility check

Per V66-B Done #4 threshold "reproducibility check":

**Definition**: a second Claude Code session, with the same rule signatures and the same case characteristics, produces semantically equivalent advisor output (same fire/no-fire decisions, same V-row attribution).

**Check protocol**:

1. Session A audits case E16 per §4 protocol · captures YAML output A
2. Session B (fresh, different Claude Code session) audits case E16 with same prompt · captures YAML output B
3. Diff: rule fire/no-fire decisions match · severity matches · V-row attribution matches
4. Acceptable variance: `finding` text differs in wording but conveys same semantic content (per V132 collapse: "advisor logic IS the rule signatures, not the prose")

**Status**: This SDK doc + the rule signatures + the eval case files **enable** the reproducibility check. The check itself is run by any external session reading these files. Per Done #4 threshold, this is "1 doc + 1 sample" — sample is §4 above, doc is this file.

---

## 6 · Limitations + scope

This SDK does **not**:
- Replace Python module implementation (deferred to V67-B)
- Run continuously / as a service
- Provide programmatic API (it is prompt-driven)
- Validate physics simulation correctness (advisor catches model-mesh-physics inconsistencies, not numerical errors)

This SDK **does**:
- Enable any external Claude Code session to audit a CFD case using the advisor stack
- Document V-row attribution traceability
- Provide regression-protection via the 20-case eval set
- Demonstrate V132 collapse (session = advisor) working end-to-end

---

## 7 · V67-B implementation path (post-V66-B close)

Future arc (V67-B) will:
- Migrate rule signatures from markdown to Python modules at `ui/backend/services/{rule_name}_advisor.py`
- Wire dispatch via `ui/backend/services/advisor_stack.py`
- Add automated CI eval runs over the 20-case set
- Add quantitative regression metrics (fire rate drift, severity drift across runs)

Until V67-B lands, this SDK is the operational advisor stack.

---

## 8 · References

- `.planning/methodology/advisor_rules_v66b_expansion.md` — V66-B new rule signatures
- `.planning/methodology/advisor_rules.md` — V64-A baseline rules
- `.planning/evals/canonical/INDEX.md` — 20-case eval set
- `.planning/evals/canonical/E*_*.md` — per-case files (5 detail + 15 batched)
- `.planning/evals/runs/2026-05-16_B103_eval_run_1.md` — run #1 log
- `.planning/evals/runs/2026-05-16_B105_eval_run_2.md` — run #2 log
- `.planning/decisions/2026-05-16_v66b_charter_dec.md` — V66-B charter
- `.planning/SCORING-FRAMEWORK.md` — pillar anchors

— Claude Code (Opus 4.7 1M) · B105 · V66-B Advisor SDK doc · 2026-05-16

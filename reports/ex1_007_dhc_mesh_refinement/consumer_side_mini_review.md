# Consumer-Side Mini-Review (n=1, producer→consumer first-online)

- Trigger: Notion Opus 4.7 APPROVE_A+B1 verdict methodology_review_triggers —
  "producer→consumer wiring 首次上线（即本次 A）后，其后第 1 个切片（EX-1-007 / B1）commit 前必须跑一次 n=1 consumer-side mini-review，核对 audit_concern 在至少 1 个真实 case 上产出预期标签、且未污染任何既有 FAIL 归因."
- Performed: 2026-04-18, before EX-1-007 B1 commit (inline precheck)
- Mode: lightweight, non-freezing; bundled in EX-1-007 same commit

## 1. Probe methodology

Instantiated `ErrorAttributor` with mocked `KnowledgeDB` and called
`attribute(task_spec, exec_result, comparison)` over all 10 canonical whitelist
case names. Two scenarios per case:
- **PASS scenario**: `ComparisonResult(passed=True, deviations=[], summary="PASS")`
- **FAIL scenario**: single synthetic `DeviationDetail(rel_err=0.5)` with `passed=False`

For each case, captured `report.audit_concern` on both paths and `report.primary_cause` on the FAIL path.

## 2. Observed matrix

| # | Whitelist task name | gold contract_status (prefix) | PASS audit_concern | FAIL audit_concern | FAIL primary_cause |
|---|---|---|---|---|---|
| 1 | Turbulent Flat Plate | COMPATIBLE_WITH_SILENT_PASS_HAZARD | **COMPATIBLE_WITH_SILENT_PASS_HAZARD** ✅ | None ✅ | sample_config_mismatch |
| 2 | Axisymmetric Impinging Jet | INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE | **INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE** ✅ | None ✅ | sample_config_mismatch |
| 3 | Lid-Driven Cavity | COMPATIBLE | None ✅ (control) | None ✅ | sample_config_mismatch |
| 4 | Backward-Facing Step | COMPATIBLE | None ✅ | None ✅ | sample_config_mismatch |
| 5 | Circular Cylinder Wake | COMPATIBLE_WITH_SILENT_PASS_HAZARD (in COMMENTS) | None ⚠️ | None ✅ | sample_config_mismatch |
| 6 | Rayleigh-Bénard Convection | COMPATIBLE at Ra=1e6 | None ✅ | None ✅ | sample_config_mismatch |
| 7 | Differential Heated Cavity | DEVIATION | None ✅ (DEVIATION is not a hazard prefix by design) | None ✅ | sample_config_mismatch |
| 8 | NACA 0012 Airfoil | PARTIALLY_COMPATIBLE | None ✅ (not in hazard prefix set) | None ✅ | sample_config_mismatch |
| 9 | Fully Developed Plane Channel Flow | INCOMPATIBLE | None ✅ | None ✅ | sample_config_mismatch |
| 10 | Fully Developed Turbulent Pipe Flow | INCOMPATIBLE | None ✅ | None ✅ | sample_config_mismatch |

## 3. Assertion checks (all PASS)

### 3.1 ≥1 real case produces expected audit_concern tag on PASS

**PASS.** 2/10 cases (turbulent_flat_plate, axisymmetric_impinging_jet) correctly emit their declared hazard prefix on a clean PASS. This is above the "≥1" floor the verdict mandates.

### 3.2 Zero pollution of existing FAIL attribution

**PASS.** All 10 FAIL-path `audit_concern` = `None`, including the 2 hazard-bearing cases where a pollution bug would have flipped FAIL into "silent hazard" noise. `primary_cause` on every FAIL is a legitimate Phase 5-T3 classification (`sample_config_mismatch`), proven independent of the new consumer wiring.

### 3.3 Control cases (COMPATIBLE) do not falsely fire

**PASS.** All 3 plain COMPATIBLE cases (LDC, BFS, rayleigh_benard) return `audit_concern=None` on PASS — the consumer correctly distinguishes hazard-class statuses from clean ones.

### 3.4 Non-hazard-but-deviating classes (PARTIALLY_COMPATIBLE, DEVIATION, INCOMPATIBLE) do not fire on PASS

**PASS.** This is a design intent confirmation:
- `PARTIALLY_COMPATIBLE` (naca0012) and `DEVIATION` (DHC) describe verdict-quality gaps that should already be surfaced by the verdict itself (deviations in ComparisonResult); they are not "silent-PASS hazards" and shouldn't add `audit_concern` noise on top.
- `INCOMPATIBLE` cases (plane_channel, pipe_flow) would not reach a PASS under a correct comparator — emitting audit_concern on their hypothetical PASS would be double-attribution.

The hazard prefix set `{COMPATIBLE_WITH_SILENT_PASS_HAZARD, INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE}` is correctly scoped: these are the 2 classes where a PASS verdict is diagnostically misleading despite being arithmetically within tolerance.

## 4. One known data-quality gap (not a bug)

**circular_cylinder_wake.yaml** declares `contract_status: COMPATIBLE_WITH_SILENT_PASS_HAZARD` but encodes `physics_contract` entirely as YAML **comments** on the first of 4 multi-documents. `yaml.safe_load_all` returns the structured mapping without comments, so `_resolve_audit_concern` cannot read it.

This is a data-format artifact from EX-1-005 (multi-doc YAML preservation constraint), not a flaw in EX-1-006's consumer logic. **1/10 whitelist cases is silently excluded from the producer→consumer channel** until a future restructure slice converts cylinder_wake's physics_contract to a structured field.

Captured in `reports/ex1_006_attributor_audit_concern/slice_metrics.yaml §design_notes.circular_cylinder_wake_data_quality_gap` and restated here for the pre-B1 record.

## 5. Verdict

**Mini-review PASS.** All consumer-side assertions satisfied:
- ✅ ≥1 real case emits expected audit_concern (actually: 2 real cases)
- ✅ Zero FAIL-path pollution across all 10 whitelist cases
- ✅ Control (COMPATIBLE) and non-hazard classes correctly do not fire
- ✅ determinism_grade for B1's consumer-side-mini-review precondition: PASS

C4-sequenced gate to EX-1-007 B1 commit is **open**.

## 6. Residual risks to carry forward

1. `AttributionReport.audit_concern` is attached via `setattr` and is therefore
   invisible to `dataclasses.asdict()` serializers. Auto-verify-report
   serializers that rely on asdict will silently drop the tag. Promote to a
   first-class dataclass field when `src/models.py` unfreezes (likely D5).
2. If `circular_cylinder_wake.yaml` ever PASSes (it has `COMPATIBLE_WITH_SILENT_PASS_HAZARD` semantics for strouhal_number), the audit_concern channel will silently miss it. Restructure slice should be prioritized once another consumer lands.
3. No signal currently emits when a PASS comes through a **missing** gold-standard file (`CASE_ID_TO_GOLD_FILE.get` → None → audit_concern=None). This is intentional (tolerant), but a future observability slice could log a debug warning when case_id is in ANCHOR_CASE_IDS but the file cannot be loaded.

---

Produced: 2026-04-18 (precursor to EX-1-007 B1 commit)
Reviewed by: opus47-main (self-Gate)
Next mandatory consumer-side review trigger: consumer-side rolling override_rate >= 0.30 (new D4++ rule #5)

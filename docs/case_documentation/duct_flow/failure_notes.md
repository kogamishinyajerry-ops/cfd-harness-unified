# Failure notes — duct_flow

> Free-form yaml/markdown — not a P4 KOM schema artifact.

## FM-DCT-1: Geometry mislabeled as pipe (case rename history)

- **Tag**: `geometry_label_lie`
- **Trigger**: pre-DEC-V61-011 case_id was `fully_developed_pipe` and gold used Moody / Colebrook smooth-pipe correlation, but the adapter's `SIMPLE_GRID` generator emits a **rectangular** duct (square at AR=1), not a circular pipe
- **Symptom**: case passed verdict numerically (f=0.0181 Colebrook vs 0.0185 Jones, within 2%), but the `physics_contract.geometry_assumption` stated "circular pipe" while the adapter generated a square duct — a silent metadata lie that did not flip a verdict but corrupted the ground-truth claim
- **Detected**: docs/whitelist_audit.md Gate Q-2 audit, 2026-04-20
- **Status**: RESOLVED — DEC-V61-011 (Gate Q-2 Path A, 2026-04-20) consolidated the case to `duct_flow` with Jones 1976 rectangular-duct correlation. Numerical gold value (0.0181 → 0.0185, within 2%) preserves comparator verdicts; physics labeling becomes honest. `legacy_case_ids` field preserves alias resolution for historical correction-log references.

## FM-DCT-2: Closely-coincident numerical values masked the regime error

- **Tag**: `numerical_coincidence_hides_metadata_lie`
- **Trigger**: at Re=50000, Jones smooth square-duct f and Colebrook smooth pipe f are within 2% (0.88 ratio · 0.0206 ≈ 0.0181 vs. Colebrook 0.0206 → see `f_duct = 0.88·f_pipe`). The 10% tolerance band absorbed the gap with margin.
- **Symptom**: verdict was PASS for the wrong reason — comparator math was internally consistent, but `geometry_assumption` claim and physical mesh disagreed
- **Detected**: same Gate Q-2 audit
- **Status**: ACKNOWLEDGED — this is a **failure-of-failure-detection**, not a solver bug. The 10% tolerance was wide enough to swallow the regime-mismatch numeric drift. Lesson: tolerance-passing verdict is necessary but not sufficient for physics correctness.

## Pattern themes

- **geometry_label_lie**: high-level case metadata claims geometry G but adapter generates G'. Recurs at backward_facing_step (flat-channel pre-052), impinging_jet (planar-slice not axisymmetric), differential_heated_cavity (Ra=1e10 unresolvable mesh historical). P4 should require `geometry_assertion: callable` that checks adapter mesh vs declared topology before solver runs.
- **numerical_coincidence_hides_metadata_lie**: when two regime-distinct correlations happen to agree numerically, tolerance-passing verdicts mask the regime mismatch. P4 should add `physics_assumption_validation` independent of numerical comparison — e.g., assert `geometry_topology_match` and `regime_match` as preconditions, not as part of the verdict.

---
spec_id: EXECUTOR_ABSTRACTION_hybrid_init_invariant
title: P2-T1 prerequisite · §X.Y hybrid-init OpenFOAM-truth invariant + companion unit-test spec
status: PROPOSED_FOR_RATIFICATION_INTO_NOTION_EXECUTOR_ABSTRACTION (2026-04-26 · per DEC-V61-073 H4 amendment · CFDJerry to ratify into Notion EXECUTOR_ABSTRACTION canonical doc before P2-T1 starts)
authored_by: Claude Code Opus 4.7 (1M context · landing DEC-V61-073 amendments)
authored_at: 2026-04-26
authored_under: 治理收口 anchor session · post-independent-audit amendment wave
parent_audit: Notion @Opus 4.7 independent audit DEC-AUDIT-2026-04-26 (H4 finding)
parent_dec: DEC-V61-073
target_canonical_doc: EXECUTOR_ABSTRACTION (Notion: ecee8d970e8148ec8c714eba8f250110)
notion_sync_status: pending
ratification_pre_condition_for: P2-T1 (DEC-V61-074 · ExecutorMode ABC + 4-mode skeleton)
---

# §X.Y · Hybrid-Init OpenFOAM-Truth Invariant (P2-T1 prerequisite)

> **Purpose**: Audit H4 identified that the original EXECUTOR_ABSTRACTION
> canonical doc claims "contract preserved" for hybrid-init mode without
> formalizing what that contract is. Per Pivot Charter "OpenFOAM 是唯一
> 真相源", hybrid-init must produce canonical numerical artifacts that are
> bit-identical to a pure docker-openfoam run for the same case + same
> seed. This spec formalizes that invariant + provides the companion
> unit-test specification.

## §X.Y.1 · Invariant statement (formal)

For any whitelist case `c ∈ Cases`, any `seed s`, and any `ExecutorMode m`:

```
canonical_artifacts(execute(m=hybrid-init, c, s)) ≡_bytes canonical_artifacts(execute(m=docker-openfoam, c, s))
```

where:

- `canonical_artifacts(...)` is the set of files committed to
  `reports/{case_id}/artifacts/` after run completion that the
  AuditPackage manifest pins as physical-truth-source artifacts
  (specifically: `solver_log_tail`, `final_residuals`, `postProcessing/`
  output, `system/controlDict`, `system/blockMeshDict`, `0/` initial
  field files **after solver writes them back**).
- `≡_bytes` is byte-for-byte equality.
- `seed s` is captured by `controlDict.startTime + writeInterval +
  randomSeed` triple where applicable.

The surrogate-as-initializer step in hybrid-init mode produces
**non-canonical** artifacts (initializer warm-start fields under
`reports/{case_id}/initializer/`) that are explicitly excluded from
`canonical_artifacts(...)`. The invariant requires that the surrogate's
contribution is washed out by the OpenFOAM solver convergence; if it
isn't, the case is malformed for hybrid-init use and the executor must
return `MODE_NOT_APPLICABLE_FOR_THIS_CASE`.

## §X.Y.2 · TrustGate-aware routing (audit Q5(b) finding)

When TrustGate evaluates a `RunReport` produced by `m=hybrid-init`, the
gate must:

1. Verify the canonical_artifacts byte-equality property held against
   the executor's claimed reference run (auditor responsibility — the
   manifest `executor` field exposes the reference SHA).
2. Treat the surrogate-as-initializer step as **out-of-scope** for the
   gate verdict. TrustGate consumes only canonical_artifacts.
3. Emit `MetricStatus.WARN` with note `hybrid_init_invariant_unverified`
   if the reference run is not present (e.g., first-ever hybrid-init
   run for this case). The case-profile owner must then trigger a
   reference docker-openfoam run to anchor the invariant.

This guarantees TrustGate verdicts are **executor-agnostic** in their
truth source while still recording the executor identity in provenance.

## §X.Y.3 · Companion unit-test specification

Three test classes must exist in `tests/test_executor_modes/` before
P2-T1 ratification:

### `test_hybrid_init_invariant_byte_equality`

For each whitelist case with both a docker-openfoam reference and a
hybrid-init run:

```python
def test_hybrid_init_byte_equal_to_docker_openfoam(case_id):
    ref_run = execute(mode=DOCKER_OPENFOAM, case_id=case_id, seed=42)
    hybrid_run = execute(mode=HYBRID_INIT, case_id=case_id, seed=42)
    assert canonical_artifacts(ref_run) == canonical_artifacts(hybrid_run)
```

### `test_hybrid_init_initializer_artifacts_excluded`

```python
def test_hybrid_init_initializer_artifacts_not_in_canonical_set(case_id):
    run = execute(mode=HYBRID_INIT, case_id=case_id, seed=42)
    canonical = canonical_artifacts(run)
    initializer_files = list((run.reports_root / "initializer").rglob("*"))
    assert all(f not in canonical for f in initializer_files)
```

### `test_trust_gate_emits_warn_when_invariant_unverified`

```python
def test_trust_gate_warns_on_first_hybrid_init_run(case_id):
    # No reference docker-openfoam run yet
    run = execute(mode=HYBRID_INIT, case_id=case_id, seed=42)
    tg = build_trust_gate_report(run)
    assert tg.has_warning("hybrid_init_invariant_unverified")
```

## §X.Y.4 · Out-of-scope (clarifications)

This invariant does **not** require:

- That hybrid-init be faster than docker-openfoam (it might or might
  not be; surrogate may speed convergence or might be net-slower).
- That hybrid-init succeed on every case (some cases legitimately have
  no usable surrogate model; those return `MODE_NOT_APPLICABLE`).
- That the surrogate model itself be deterministic (only its effect on
  canonical_artifacts must be).

## §X.Y.5 · Ratification path

1. **CFDJerry** ratifies this amendment into the Notion
   EXECUTOR_ABSTRACTION canonical doc (page id
   `ecee8d970e8148ec8c714eba8f250110`) by adding §X.Y as a new section.
2. **Claude Code (next session)** mirrors the Notion text into a repo
   amendment file (this file becomes the canonical mirror).
3. **DEC-V61-074 (P2-T1)** kickoff explicitly references this §X.Y as
   prerequisite-met, blocked otherwise.

## Cross-references

- **DEC-V61-073** · `2026-04-26_v61_073_independent_audit_amendments.md` · H4 amendment
- **EXECUTOR_ABSTRACTION** · Notion: ecee8d970e8148ec8c714eba8f250110
- **P2-T0 spike** · `.planning/specs/EXECUTOR_ABSTRACTION_compatibility_spike.md` · byte-reproducibility precedent
- **Pivot Charter** · OpenFOAM-truth-source pillar
- **METRICS_AND_TRUST_GATES** · Notion: e5abaf8cefba4ac48f1deb24cb4b00ee · TrustGate executor-aware routing addition

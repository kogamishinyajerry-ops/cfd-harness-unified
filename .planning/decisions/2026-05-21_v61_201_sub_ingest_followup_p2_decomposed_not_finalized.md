---
decision_id: DEC-V61-201-SUB-INGEST-P2-DECOMPOSED-NOT-FINALIZED
title: Allow decomposed-only ingest when reference_comparison is not finalized
status: Proposed
parent_dec: DEC-V61-201-SUB-INGEST
phase: post-merge follow-up
notion_sync_status: not_applicable_proposed
---

## Why

Codex R7 (86gs, effort=xhigh) on `feature/audit-ingest-mode` raised
this finding as P2 alongside a P1 (over-broad guard). Per user
discipline-rule on 2026-05-21 ("strict stop-and-queue at 7 rounds"),
both R7 findings were deferred rather than iterated.

The R4 P2-b fix added a BLOCK on pure-decomposed cases
(`processor*/<time>/` with no top-level `<time>/`) because
`audit/qoi.py` and `qoi/wall_shear.py` only read top-level time dirs.
The reasoning was: if ingest accepts a decomposed case but QoI silently
falls back, the user gets a confusing half-working report.

R7 P2 observation: `audit/qoi.py::run()` ONLY reads time directories
on the `reference_comparison.status == "finalized"` code path. For
manifests with `placeholder` / `not_finalized` references (the common
case for cases without staged reference data), QoI + reference both
MOCK out anyway and never touch the time directories. The R4 BLOCK
is therefore too aggressive — it rejects decomposed cases the rest
of the pipeline could already handle.

## What

Relax the `case_decomposed_not_reconstructed` BLOCK from
"unconditional" to "only when reference_comparison.status ==
'finalized'". In `backends/openfoam.py::ingest()`:

```python
if not has_top_level_time_dir:
    ref_status = (
        manifest.get("reference_comparison", {}) or {}
    ).get("status", "")
    if ref_status == "finalized":
        return {
            "status": "BLOCKED",
            "summary": "...case is decomposed and reference is finalized...",
            "details": {
                "reason": "case_decomposed_not_reconstructed_with_finalized_reference",
                "next_step": "Run reconstructPar OR set reference_comparison.status to placeholder/not_finalized",
                ...
            },
        }
    # else: accept the decomposed case + emit a WARN-level marker so
    # the user knows QoI extraction would fail if they later finalize
    # the reference.
```

## Scope class

Spike-class:
- 1 file edit (`backends/openfoam.py`), ~10 LOC
- 2 tests (decomposed + not_finalized → accepted; decomposed + finalized
  → still BLOCKs with refined reason)
- 1 test update (the existing R4-P2 BLOCK test now needs to use a
  finalized-reference manifest)
- No schema change, no governance change

## Why deferred and not merged into parent DEC

Same as the P1 deferral: user hard-stop at 7 rounds. R7 P2 is a UX
improvement, not a correctness break — the R4 BLOCK is overly
restrictive but not incorrect. Decomposed cases with not_finalized
references currently need `reconstructPar` first; that's an extra
step but not a wrong answer.

## Acceptance criteria

- [ ] Relaxed BLOCK condition: only fire when ref status is "finalized"
- [ ] Decomposed-only + not_finalized reference → accepted, ingest
      proceeds with placeholder QoI/reference gates (mirroring the
      existing not_finalized path on serial cases)
- [ ] Decomposed-only + finalized reference → still BLOCKs with
      sharpened reason `case_decomposed_not_reconstructed_with_finalized_reference`
- [ ] All 405 existing tests still pass (the R4 BLOCK test updates
      to use a finalized-reference manifest)

## Risks

Very low. The relaxed condition is conservative — when reference is
finalized, the BLOCK is unchanged. The new accept path mirrors what
the rest of the pipeline already does for serial not_finalized cases.

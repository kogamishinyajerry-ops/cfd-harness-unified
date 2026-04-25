# DEC-V61-060 · Codex Stage B Re-Review · Round 4

**Reviewer**: Codex GPT-5.4 (sajihsmipoal@gmail.com — picassoer651 hung 1h26m, switched)
**Submitted at**: 2026-04-26 ~00:30 +0800 (initial); retried ~02:00 +0800
**Verdict**: CHANGES_REQUIRED
**Stage C go/no-go**: NO_GO

## Findings (1H + 1L)

### F1-HIGH · Fail-closed contract still broken for non-finite boundary metadata

File refs: rbc_extractors.py:259, :336

R3 fix closed `u_vecs[i][1]` IndexError + non-finite field arrays.
But did NOT cover non-finite BOUNDARY METADATA. Codex verified at
runtime:
- `extract_w_max(..., wall_coord_hot=NaN)` returns `status: ok`
- `extract_w_max(..., wall_coord_cold=Inf)` returns `status: ok`
- `extract_nu_asymmetry(...)` returns `status: ok` + value=NaN/Inf
  when `wall_coord_hot/cold`, `T_hot/cold_wall`, or `fixedGradient`
  `bc_gradient` are non-finite

Required edit: validate all boundary scalars entering the stencil
path; reject any non-finite gradient/Nu/asymmetry result. Add
regression tests for NaN/Inf in those boundary fields.

### F2-LOW · Docstring drift

File refs: rbc_extractors.py:28, :60, :122

Three docstring inconsistencies:
1. Module header still says "B.2/B.3 land in subsequent commits" —
   they did.
2. `_u_vecs_well_formed` says it validates `(ux, uy, uz)` triples,
   but code only requires `len ≥ 2` + finite uy.
3. `RBCBoundary.g` doc still says default value exists; code now
   defaults to None.

Required edit: sync docstrings/comments to shipped code.

## Verbatim fix landed

DEC-V61-060 Stage B-final-fix-v2 commit (next). 5-condition exception:
- diff-level match Codex Required edit: ✓
- ≤2 files (1 src + 1 tests): ✓
- no public API change (additive guards, no signature shift): ✓
- PR body cites R4 F1-HIGH + F2-LOW: ✓

→ Re-submission as Stage B R5 next (within budget=5).

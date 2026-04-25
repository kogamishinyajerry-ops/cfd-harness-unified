# DEC-V61-060 · Codex Stage B Review · Round 3

**Reviewer**: Codex GPT-5.4 (picassoer651@gmail.com — sajihsmipoal hung 40 min, switched)
**Submitted at**: 2026-04-25 ~23:30 +0800 (initial); retried ~24:00 +0800
**Verdict**: CHANGES_REQUIRED
**Stage C go/no-go**: NO_GO

## Findings (1H + 1M)

### F1-HIGH · Fail-closed contract not actually closed on malformed/non-finite inputs

File refs: rbc_extractors.py:238, :301, :362; tests:218, :285

extract_w_max + extract_roll_count_x assumed every u_vecs entry has uy
at index 1 → IndexError on malformed `u_vecs=[(0.0,), ...]`.
extract_nu_asymmetry/extract_w_max also propagated NaN and emitted
`status: "ok"` if t_vals or g were non-finite. Breaks Stage B
contract: invalid extractor inputs should degrade to {}, not crash
or emit ok+nan.

Required edit: explicit tuple-arity + math.isfinite(...) validation
before indexing or returning. Add unit tests for malformed u_vecs,
NaN in t_vals, NaN in g.

### F2-MED · g default silently bakes canonical case into extractor contract

File refs: rbc_extractors.py:105; tests:24, :201

`RBCBoundary.g = 3.0e-4` (and beta = 1/300) defaults silently encode
the AR=4 / Pr=10 case. Stage C wiring could omit case-derived g and
still get plausible-looking w_max_nondim — exactly the silent
assumption to catch.

Required edit: make g/beta required (or default None + fail-closed
when absent). Update tests to pass g/beta explicitly so Stage C
wiring proves it uses case-derived physics.

## Comments (no findings)

- No wall-gradient stencil misuse. Top-wall reflection defensible
  for magnitude-only Nu use case.
- H/20 wall trim + 5%·Lx side trim look reasonable. Graded-grid
  probe still recovered w_max≈1.57 + roll_count=2.
- Stale doc string at line 326: `(sign_changes + 1) // 2` — code
  correctly uses `(N // 2) + 1`. Fix during cleanup.
- No plane-architecture violation, no missing comparator-facing
  output key, no test name/assertion mismatch.
- Synthetic fixtures good for unit math. Adapter-derived "real"
  fixture is nice-to-have before closeout, not blocking.

## Verbatim fix landed

DEC-V61-060 Stage B-final-fix commit (next). 5-condition exception:
- diff-level match Codex Required edit ✓
- ≤2 files (1 src + 1 tests) ✓
- No public API change (RBCBoundary signature additive optional)
- PR body cites R3 F1-HIGH + F2-MED ✓

→ Re-submission as Stage B R4 next.

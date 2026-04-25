# DEC-V61-060 · Codex Stage A Review · Round 2

**Reviewer**: Codex GPT-5.4 (mahbubaamyrss@gmail.com)
**Submitted at**: 2026-04-25 ~22:55 +0800
**Verdict**: APPROVE
**Stage B go/no-go**: GO

## Findings

NONE.

## Review Notes

### F1-HIGH structurally closed

Pr now resolves BC override → whitelist → 0.71 fallback. Resolved value
propagates to alpha (line 2223), g (line 2239), physicalProperties
emission (line 2521), and declared_Pr in _verify_buoyant_case_plumbing
(lines 3471-3475 + parse-back 3519-3559).

In-venv probe confirmation by Codex:
- Canonical RBC: Pr=10.0, alpha=1.0e-6, |g|=3.0e-4
- DHC: Pr=0.71, alpha≈1.408e-5, |g|≈4.225e-3 (UNCHANGED — no regression)

(Codex correction: my R2-prompt g estimates 0.030/0.42 were off by 100×.
Actual values from in-venv probe are 3e-4/4.2e-3. Either way, no
findings — DHC unchanged is what matters.)

### F2-MED closed

_make_nc_spec helper no longer pre-seeds Pr. RBC round-trip test
exercises whitelist resolution. New guards at lines 2807-2837 and
2839-2850 actively trip on regression — Codex manually forced both
regression modes in a throwaway probe.

### 5-condition exception accepted

Single A-final commit acceptable. Diff stays inside two files (the same
files implicated by R1), no API shift. R1 archive records the
one-commit exception as acceptable because splitting would leave code
and guards temporarily inconsistent.

### No third Stage A correctness bug

Only surviving Pr=0.71 path for canonical RBC is the intentional legacy
fallback when whitelist resolution unavailable — matches the required
chain.

## Verification note

Codex could not replay 31/31 PASS claim because workspace Python
tooling is split between system pytest and repo .venv. Approval based
on line-by-line review + direct in-venv generator probes of the
patched path.

## Stage A complete

7 commits total: A.0 (citation pivot) + A.1 (Lx≠Ly split) + A.2
(extractor wall_orientation branch) + A.3 (bottom-heated topology) +
A.4 (horizontal-wall BL grading) + A.5 (integration smoke + invariant)
+ A-final (Pr propagation + Stage A.0 pivot test guards).

→ Stage B (multi-dim extractors) may begin.

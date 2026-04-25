# DEC-V61-060 · Codex Stage A Review · Round 1

**Reviewer**: Codex GPT-5.4 (kogamishinyajerry@gmail.com — switched from sajihsmipoal after first attempt hung 40 min with 0 CPU)
**Submitted at**: 2026-04-25 ~22:00 +0800 (initial); retried ~22:45 +0800
**Verdict**: CHANGES_REQUIRED
**Stage B go/no-go**: NO_GO

## Findings (1H + 1M)

### F1-HIGH · Benchmark pivot never reaches the generated RBC case physics

File refs: src/foam_agent_adapter.py:2149, :2207, :2223, :2503, :3455

A.0 docs pivoted RBC to Pr=10/AR=4/Nu=17.7, but generator hard-codes
Pr=0.71 (line 2149), derives alpha/g from legacy value, writes Pr=0.71
to constant/physicalProperties, verifies declared_Pr=0.71. Reproduced
emitted RBC case directly: geometry/topology repaired but physics file
is still legacy air-like regime.

Required edit: resolve Pr from canonical metadata (BC override → whitelist
→ legacy default), recompute alpha/g, emit Pr=10 for canonical RBC, pass
resolved Pr into _verify_buoyant_case_plumbing.

### F2-MED · Stage A tests don't actually guard the A.0 parameter pivot

File refs: tests/test_foam_agent_adapter.py:1405, :1447, :1708, :2695

_make_nc_spec helper still seeds Pr=0.71; generic RBC round-trip test
still uses aspect_ratio=2.0; A.5 smoke checks geometry/topology/BC
plumbing but never inspects constant/physicalProperties. So 29-test
slice proves Lx/Ly + topology + wall_orientation repair, NOT the A.0
literature pivot.

Required edit: add A.5 smoke assertion on Pr=10 in physicalProperties;
update stale RBC fixtures from AR=2/Pr=0.71 → AR=4/Pr=10; update
tampered-Pr plumbing test.

## Comments (no findings, informational)

1. AR=4 / Pr=10 pivot defensible (better than broken Chaivat /
   paywalled Goldhirsch). Source verified against Pandey & Schumacher
   tutorial PDF.
2. H=1 cavity height reference matches Eq.(12) Ra=αg·ΔT·H³/(νκ).
3. H_char = Ly (RBC) vs Lx (DHC) matches Eq.(22-23).
4. wall_coord_hot OK as-is (orientation disambiguates axis).
5. Patch-name stability OK; no downstream BC-file break detected.
6. 4:1 y-grading marginally adequate (~3.09 cells across δ_T/H).
   Clears explicit "≥3 cells" bar but only narrowly.
7. A.5 smoke needs Pr=10 assertion (F2-MED). 0/U optional. fvSolution
   not blocking.

## Confirmed NO findings

- A.2/A.3 wall_orientation plumbing mismatch: NONE
- A.3 patch-name swap downstream break: NONE
- A.0 ref_value=17.7 mismatch with cited source: NONE
- A.4 grading <3 cells in BL: NONE (3.09 cells)
- Regression in claimed Stage A test slice: NONE (Codex reproduced
  29 PASS via `uv run --isolated --with pyyaml --with pytest python -m pytest -q tests/test_foam_agent_adapter.py -k 'RBCMultiDim or BuoyantCasePlumbingVerification'`)

## Verbatim fix landed

DEC-V61-060 A-final commit f3dfc6e. 5-condition exception satisfied:
- diff-level match Codex Required edit ✓
- ≤2 files (1 src + 1 tests) ✓
- No public API change ✓
- PR body cites R1 F1-HIGH + F2-MED ✓
- Total LOC borderline (~30 operative + ~20 tests); accepted as single
  bug-fix unit per verbatim spirit (splitting would interleave broken state)

→ Re-submission as Stage A R2 requested next.

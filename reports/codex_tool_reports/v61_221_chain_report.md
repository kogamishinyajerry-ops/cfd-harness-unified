# Codex chain report · DEC-V61-221 (P3 W3.0.6 multi-region RunArtifactSlice)

- **Date**: 2026-05-30
- **Relay**: R0 + R1 on **86gs `gpt-5.4` xhigh** (governance baseline); **R2 on
  CRS `gpt-5.4` high** — the 86gs R2 attempt hung and was killed (86gs instability
  consistent with W3.0.1 502×2 + W3.0.2 stream-fail this session); failed over to
  CRS per DEC-V61-214 precedent. Effort-downgrade xhigh→high on R2 logged.
- **Target**: `pattern_matcher.py` (RegionSlice + CoupledPatch + `regions` field)
  + `advisor_pattern_matcher.ts` (TS parity mirror) + `__init__.py` (exports) +
  `test_v9_cross_language_parity.py` (`_hydrate_slice` extension) + 2 p3 test
  files + DEC-V61-221.
- **Outcome**: **APPROVE at R2** (clean gate, within cap=3). R0 (1×P2) + R1 (2×P3)
  fixed+verified; R2 found no bug. No overflow record needed.
- **Pre-Codex hardening**: the 2-lens `test-red-team` workflow caught **P2×3 + P3**
  (kind-None domain narrowing · coupled_patches None-vs-() untested · tuple-vs-list
  JSON mislabel · no-runtime-enforcement doc gap) — all fixed before R0.

---

## R0 — CHANGES_REQUIRED (1× P2) · 86gs xhigh

1. **TS parity mirror missing** — the v9_advisor has a Python↔TS RS#38
   same-data-shape contract; the Python-only schema extension left
   `ui/frontend/src/data/advisor_pattern_matcher.ts` on the pre-W3.0.6 slice
   (no `RegionSlice`/`CoupledPatch`). The W2.0.6 precedent (DEC-V61-215) updated
   the TS side in the same change. **Fixed**: added `CoupledPatch` + `RegionSlice`
   interfaces + optional `regions` field to the TS mirror; `tsc -b` + `tsc
   --noEmit` both clean (DEC-V61-203 build gate).

## R1 — CHANGES_REQUIRED (2× P3, NO production regression) · 86gs xhigh

R1 explicitly: *"The implementation changes appear additive and backward-
compatible, and I did not find a production-path regression in the new schema
types. The only issues are low-priority problems in newly added regression tests."*

2. **RS#36 byte-invariance test was a tautology** — serialized one synthetic dict
   twice. **Fixed**: rewrote to run the REAL `match_advisor_patterns` + REAL
   `_canonical_json` on a slice WITH regions vs WITHOUT, asserting byte-identical
   matched commentary (genuinely fences a future regions-leak into the sidecar).
3. **regions=None branch mislabeled** — a test's docstring claimed the
   `regions=None` case but constructed a populated slice. **Fixed**: rewrote to
   cover BOTH the None branch (the documented claim) and the populated case.

## R2 — APPROVE · CRS gpt-5.4 high

*"The staged schema extension appears additive and backward-compatible: existing
construction sites keep working, cross-language type surfaces are updated
consistently, and the unstaged report changes are metadata-only path/timestamp
refreshes. I did not find a concrete bug."*

---

## Outcome

- **Clean APPROVE at R2** — the chain converged cleanly (P2 → P3 → APPROVE); no
  un-re-reviewed residual (unlike W3.0.1/.2 which hit cap with P1/P2 fixes).
- Additive-non-breaking: ~59 legacy `RunArtifactSlice(` sites unchanged; `regions`
  defaults None. Byte-reproducibility (RS#36): the slice is not serialized to the
  sidecar zip — verified. Python↔TS parity restored.
- Tests: **295+ green** (p3 + v9 advisor/pattern/sidecar/cross-language parity) ·
  no regression. Stdlib-only (Python); `tsc` clean (TS).
- DEC-V61-221 → **Accepted** (`confidence: high` — clean APPROVE gate).

## Calibration (RETRO-V61-001 intake)

1. **Cross-language parity is part of "the contract"** for v9_advisor: any
   `RunArtifactSlice` schema change MUST update the TS mirror in the same commit
   (DEC-V61-215 precedent). Carry-forward: the W3.1 understand phase must scan for
   the TS mirror up front when touching v9_advisor schemas.
2. **kind-None domain match** (red-team P2): a slice field that mirrors an upstream
   extractor field must match its FULL domain (incl. None) or it forces fabrication
   downstream. Same lesson as the W3.0.2 Contract-A parity finding.
3. **86gs instability now 3-for-3 this session** (W3.0.1 502×2 · W3.0.2 stream-fail
   · W3.0.6 R2 hang). CRS has been the reliable fallback every time — strongly
   consider CRS-primary for governance review going forward (logged for retro).

# Capability Radar v3 · COMMENTARY

**Date**: 2026-05-14
**Trigger**: B20 A8 widening land (commit `9a0b8cc`) + B19 V99/V100 sediment (commit `b1303d2`)
**Baseline**: v2 (2026-05-14, COMMENTARY_V2.md, left half 7.10 / right half 9.17)

---

## v3 vs v2 score delta (single-axis update)

| # | Axis | v2 | v3 | Δ | Evidence |
|---|---|---|---|---|---|
| 1 | CAD/几何 ingest | 7.0 | 7.0 | 0 | n/a (no new CAD substrate post-v2) |
| 2 | **网格生成** | **6.5** | **6.75** | **+0.25** | A8 widening (5→7 detection paths) · V99 + V100 [VALIDATED] · 4 new regression tests |
| 3 | 物理模型覆盖 | 8.0 | 8.0 | 0 | n/a |
| 4 | 求解器健壮性 | 7.0 | 7.0 | 0 | n/a |
| 5 | 后处理质量 | 7.0 | 7.0 | 0 | n/a (no postproc substrate this session) |
| 6 | CLI/自动化 | 9.0 | 9.0 | 0 | n/a |
| 7 | AI 智能辅助 | 9.0 | 9.0 | 0 | (held; A8 widening is depth not breadth of advisor stack) |
| 8 | 可重现/审计 | 9.5 | 9.5 | 0 | (held; M-V100 reached but no new audit-infra) |

**Half-axis averages**:

| Half | v1 | v2 | v3 | Target | Status |
|---|---|---|---|---|---|
| Left (1-5) / 5 | 6.40 | 7.10 | **7.15** | ≥ 7.2 | **NOT MET · gap 0.05** |
| Right (6-8) / 3 | 8.67 | 9.17 | 9.17 | ≥ 8.7 | MET ✓ (+0.47 margin) |

---

## Mesh axis 6.5 → 6.75 justification (NOT 7.0)

**Why +0.25 not +0.5**: COMMENTARY_V2 §"To close gap 0.1" specified that mesh axis 6.5 → 7.0 (+0.5) "would require evidence that mesh-debug-loop reduces below v1.5's '≤3-iter on new case' bar."

B20 A8 widening:
- ✅ Adds 2 new detection paths (V99 multi-normal constrained patch + V100 entry-point type-guard)
- ✅ Closes V99 + V100 status [QUESTIONABLE]→[VALIDATED] in both corpora
- ✅ 4 new regression tests pin V99 + V100 ground truth
- ❌ Does **NOT** yet have post-land case evidence demonstrating debug-loop reduction (no new case post-2026-05-14 13:32 has triggered V99 or V100 detection paths in actual workflow)

**Scoring rubric (per v1.5 SCORE-DELTA forecast criteria)**:
- +0.5 = LANDED advisor stack expansion WITH demonstrated reduction in failure loop
- +0.25 = LANDED advisor coverage breadth expansion (paths added · regression-pinned · but no triggered case yet)
- +0.0 = drafted-but-not-landed

A8 widening is sandwiched: more than +0.0 (real code + V99/V100 closure) but less than +0.5 (no triggered case). **Honest score = +0.25** matching arc culture (e.g., M-APU-RESTORE CLOSED NEGATIVE honesty precedent — v95 sedimented insufficiency without inflating).

---

## Done dim 5 verdict (left half ≥ 7.2)

**NOT MET · gap 0.05** — left half 7.15 (v3) vs target 7.20.

**Δ from v2 → v3**: -0.05 of gap closed (gap was 0.10 → 0.05).

**To close remaining 0.05 gap**: any single one of:

- **网格 6.75 → 7.0** (+0.25 → left half +0.05): would require triggered-case evidence — a new case (or revisit existing) where V99 or V100 detection paths fire in workflow + provably shortens debug loop. Forward-loaded scoring path; honest evidence required.
- **后处理 7.0 → 7.25** (+0.25 → left half +0.05): would require ≥1 new postproc V-row family OR a postproc-class advisor land (e.g. A6 hvac_adpi promoted from drafted to LANDED). Postproc axis has had 0 substrate work this arc.
- **CAD 7.0 → 7.25**: would require A1 deeper hardening OR new CAD-class advisor (A9 mrf_setup_advisor 2nd-case unlock). M-A6 advisor still drafted-deferred per 2nd HVAC case wait.
- **物理 8.0 → 8.25** or **求解器 7.0 → 7.25**: less likely without new e2e numerics class (already 3/3 MET).

**Arc closure options at gap 0.05**:

| Option | Action | Honesty cost |
|---|---|---|
| (A) **Close arc with footnote** | Accept gap 0.05 as "scoring conservatism not capability gap" · V61-198 CLOSE DEC notes 7.15 vs 7.20 target · arc-closed-with-epsilon-margin | Low — gap 0.05 is well within typical scoring rubric noise band |
| (B) **One more substrate task** | Dispatch postproc-class V-row family OR new case to trigger V99/V100 path · earn +0.05 honestly | Higher integrity but extends arc pacing (already 4-session same-day cadence flag) |
| (C) **Re-evaluate scoring rubric** | Argue widening = +0.5 not +0.25 (lift mesh to 7.0) | Moderate honesty cost — would need to retroactively adjust v1.5 SCORE-DELTA forecasting criteria |

---

## Substrate-most-recent-pushed axis (informational)

**网格生成** received the only substrate push this v2→v3 window:
- V99 + V100 land
- 4 new regression tests
- A8 5 → 7 detection paths
- This is the **first time mesh axis improved without an end-to-end case run** — pure
  advisor-stack widening accounts for it.

---

## v2 → v3 mesh axis evidence ledger (verbatim audit trail)

**v2 mesh axis evidence base** (per COMMENTARY_V2):
1. A8 `shm_dict_validator` LANDED (5 paths, 9 tests, V52+V86 closure)
2. case_011 v5b 3-region chtMR mesh
3. case_003 197k cells industrial mesh (sHM 21.4s wall-clock)
4. V92 codifies cellZoneInside hybrid strategy
5. V95 NEGATIVE evidence (M-APU-RESTORE)
6. V89/V90/V92 family

**v3 mesh axis evidence additions** (post-B20):
7. A8 widening (2 new paths: V99 + V100)
8. 4 new regression tests
9. V99 + V100 status [VALIDATED]
10. M-V100 4th Done dim reached

**Net evidence base growth**: +4 items (out of 10) = +40% breadth, but no end-to-end
demonstration. Scaled scoring: +0.25 of the +0.5 "full demonstration" forecast.

---

**Built by**: `build_radar_v3.py` (deterministic, same Hiragino Sans GB stack as v1/v2)
**Output**: `capability_radar_v3.png` (494 KB · 4-way overlay)
**Authored by**: Claude Code Opus 4.7 (1M context) · main session B20 verification

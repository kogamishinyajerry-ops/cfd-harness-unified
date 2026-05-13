# Capability Radar · SCORE-DELTA v1 → v1.5 early-signal (session 5)

**Generated**: 2026-05-13 by Claude Code Opus 4.7 (subagent · radar pre-validation task)
**Status**: early-signal · NOT M-RADAR-V2 milestone deliverable
**Reference baseline**: `COMMENTARY.md` (v1, 2026-05-13)
**Scope**: re-score 8 axes (cfd-harness column only) after session 5 LANDED set:
  - M-A4 (commit `8183394`) — face_orientation_advisor + 9-test suite + V79/V87 closure
  - M-V81 (commit `7f11b16`) — A5 inlet_outlet_validator + 9-test suite + V81 closure
  - M-DRIFT (commit `d53afbc`) — corpus drift-prevention pre-commit hook

**Hard constraints respected**:
- B5 in-flight (case_011 v2) **NOT credited**; evaluation uses committed state only
- `build_radar.py` NOT modified · `capability_radar.png` NOT overwritten
- M-RADAR-V2 (Tier 3) reserved for true re-paint with M-V100 substrate behind it

---

## 1 · Per-axis Δ table

| # | Axis | v1 | v1.5 | Δ | Reason |
|---|---|---|---|---|---|
| 1 | CAD/几何 ingest | 6 | **6.5** | +0.5 | A4 + A5 stack onto existing A1/A2-v2/A7 → 5 advisors now intercept CAD-layer issues (face orientation + inlet/outlet labelling). But no NEW industrial-CAD complexity (CATIA / NX / Creo native, complex BREP) validated this session; advisors are dict-consumers verifying existing pipeline output, not extending ingest capability. Capped at +0.5. |
| 2 | 网格生成 | 6 | **6** | 0 | No structural mesh capability change. A8 still drafted. case_002a F4b sHM arc in flight but uncommitted at evaluation time. Refusing the temptation to claim +0.5 for "advisors that hint at mesh issues" — those are advisor wins, not mesher wins. |
| 3 | 物理模型覆盖 | 7 | **7** | 0 | No new numerics class walked through e2e this session. case_011 v1 mesh broken → no solver run on CHT-multi-stream. B5 (case_011 v2 chtMultiRegionSimpleFoam) in flight but **not credited** per instructions. Counter still 1/3 at commit time. |
| 4 | 求解器健壮性 | 6 | **6** | 0 | V-series +3 (V85/V86/V87) but these sediments are predominantly D7 face-orientation + session 2 features-list orphaning + HX cold-fin mesh struggle — not solver-numerics robustness wins. No new under-relaxation / scheme-mode discoveries. |
| 5 | 后处理质量 | 7 | **7** | 0 | No new ParaView / trame / HD-report tooling. No change. |
| 6 | CLI/自动化 | 9 | **9** | 0 | M-DRIFT is audit-layer infrastructure (commit-msg hook prevents V-row drift), not CLI workflow extension. Baseline already at 9 with 100% scriptable workflow; no headroom in this axis from this session's work. |
| 7 | AI 智能辅助 | 8 | **8.5** | +0.5 | Advisor stack 4 → 6 LANDED (A1, A2-v2, A3, A7 + A4, A5). 75% of charted A1–A8 candidates now in code. BUT: Track C session 2 (case_011) was still **human-driven walkthrough with advisor cross-check**, not advisor-led decisioning. M6 charter "advisor接管决策" thesis NOT YET empirically demonstrated. +0.5 reflects code-stack growth; the next +0.5 is gated on Track C session evidence of advisor-driven decisions. |
| 8 | 可重现/审计 | 9 | **9.5** | +0.5 | COMMENTARY.md §8 explicitly listed the gap as "暂无自动 drift-prevention hook（刚提议但未 land）". M-DRIFT closes exactly that gap. Drift hook now live in `.git/hooks/commit-msg` chain, enforces V-row methodology + runtime parity at commit time. The remaining 0.5 to reach 10.0 sits with the "no project hits 10" principle from COMMENTARY §"评分会怎么变". |

---

## 2 · Half-axis averages

| Half | v1 | v1.5 | Target | Status |
|---|---|---|---|---|
| **Left** (CAD + 网格 + 物理 + 求解器 + 后处理) / 5 | (6+6+7+6+7)/5 = **6.4** | (6.5+6+7+6+7)/5 = **6.5** | ≥ 7.2 | **+0.1 Δ · 0.7 still to go · advisor-only path cannot close this** |
| **Right** (CLI + AI + 审计) / 3 | (9+8+9)/3 = **8.7** | (9+8.5+9.5)/3 = **9.0** | ≥ 8.7 (maintain) | **+0.3 Δ · exceeds maintenance threshold · margin secured** |

---

## 3 · Early-signal to main session (≤ 200 字)

**Left half can NOT reach 7.2 by advisor-land work alone.** Session 5 landed 2 advisors (M-A4 + M-V81) + a drift hook and only moved left half by +0.1 (6.4 → 6.5). The remaining 0.7 sits in 网格 / 物理 / 求解器 / 后处理 — axes that move on **industrial substrate work**, not advisor code:

- 网格 6 → 7+ needs case_002a F4b sHM convergence + Track C session showing mesh debug loop shrinks (V73-V78 7-iter → ≤3-iter on new case)
- 物理 7 → 8 needs e2e numerics class counter 1 → 2 (M-TRACK-3 NREL MRF or B5 case_011 v2 CHT)
- 求解器 6 → 7 needs ≥ 1 new solver-numerics-class V-row family (not D7/sediment-only)

**Recommendation**: Tier 1 advisor-land is structurally complete; pivot to Tier 2 **substrate-first** ordering — **Track C session 3 (M-TRACK-3 NREL MRF)** ahead of M-A6/M-A8. Adviser stack is fine at 6/8 if next 2 advisors are unblocked by substrate evidence rather than scheduled by alphabet.

**Right half safe**: 9.0 ≥ 8.7 maintenance with +0.3 margin. No regression risk in audit/AI/CLI axes from current trajectory. No competitor news (Siemens Industrial Copilot / ANSYS Discovery AI) surfaced this session warranting STAR-CCM+ AI projection change from "2 → 5+ within 24m" baseline.

---

## 4 · What v1.5 explicitly does NOT claim

- ❌ Does NOT trigger M-RADAR-V2 milestone tick — that requires re-paint with M-V100 substrate behind it
- ❌ Does NOT touch `build_radar.py` SCORES dict — v1 PNG stays canonical for governance archive
- ❌ Does NOT credit case_011 v2 (B5 in flight) — re-evaluate post-B5 land
- ❌ Does NOT amend COMMENTARY.md — this file is the amendment overlay; COMMENTARY stays v1 truth

---

## 5 · Reconciliation cue for M-RADAR-V2 (future Tier 3 work)

When M-RADAR-V2 actually fires, the milestone author should:
1. Read this file first to know v1.5 estimates
2. Re-evaluate honestly — substrate work between now and then may move axes differently than this advisor-only delta projects
3. Decide whether to publish v1.5 as a separate snapshot or skip to v2 with full COMMENTARY rewrite
4. The +0.1 / +0.3 deltas here are **early-signal projections**, not commitments — actual v2 scoring is M-RADAR-V2's prerogative

---

**confidence**: medium · scoring is calibrated against COMMENTARY.md v1 rationale lines; uncertainty band ±0.5 per axis is realistic given subjective 0-10 scale.

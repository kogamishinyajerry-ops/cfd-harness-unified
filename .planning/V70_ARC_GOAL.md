# ARC-GOAL · V70 CFD Capability Breadth × Novice Onboarding × Industrial-UI Benchmark · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v70_charter_dec.md` (Accepted B159 · 2026-05-16)
> **Predecessor**: DEC-V69-close (B157 · 4 sub-DECs · Pillar 6 99 · Pillar 7 88)
> **Target**: Pillar 6 99→99.5 · Pillar 7 88→90 · Pillar 8/9/10 floor (each ≥70 first-anchor) · weighted ≥95
> **User mandate** (6th invocation): "全都要" + explicit 3-pillar expansion (CFD-breadth + novice-UX + industrial-UI)

## North Star (charter §2 verbatim)

> "工程师在没有教程的情况下，10 分钟内完成第一次 lid_driven_cavity 全流程仿真 · 同时一个 CFD 老手在 5 分钟内能从 workbench 跑出 NACA 0012 翼型在 Re=3M 的 RANS k-omega-SST 收敛解 · 同时把 workbench 截图甩给 ANSYS Fluent / STAR-CCM+ 重度用户看，至少 1 个用户在 6 个 UI 评估维度上的 3 个维度给出 'comparable or better than commercial' 评分 · 同时 V69 已建立的 advisor SSOT 规模扩展到 ≥30 canonical eval cases · 覆盖 ≥4 turbulence models × ≥3 compressibility regimes × ≥2 steadiness regimes"

## Done dim checklist (9 dims · all required for V70 close · FULL delivery)

- [x] **V70-DONE-1 · CFD capability matrix** — `.planning/cfd_capability_matrix.md` · 59 cells · 33 PR + 26 GAP-TRACKED + 0 empty → 100% PR+GAP (≥80% threshold EXCEEDED)
- [x] **V70-DONE-2 · Canonical eval set 20→30** — E01..E30 individual files · 6 turbulence × 3 compressibility × 2 steadiness · 32/32 pytest PASS · ≥150 firings/30 cases
- [x] **V70-DONE-3 · Novice onboarding artifacts** — `/workbench/tutorial` + EngineerControlRail with 10 tooltips + FirstTimeBanner + 1400-word onboarding guide + 3 novice e2e specs PASS
- [x] **V70-DONE-4 · Industrial-UI benchmark report** — 7 axes × 5 GUIs (Fluent/STAR-CCM+/SimScale/Simcenter/OpenFOAM-GUI) + 3 V70-UI-IMPROVEMENT tags LANDED · anti-marketing gate MET (5/7 axes admit commercial better)
- [x] **V70-DONE-5 · 3 new fleet agents** — `score_cfd_breadth.sh` + `score_novice_onboarding.sh` + `score_industrial_ui.sh` · merged into `score_all.sh` aggregator
- [x] **V70-DONE-6 · SCORING-FRAMEWORK Pillars 8/9/10** — anchor tables authored in `.planning/SCORING-FRAMEWORK.md` · 0-100 ladders per pillar
- [x] **V70-DONE-7 · E2E for new artifacts** — 7 V70 e2e (3 novice + 2 shortcut + visual baselines 19-22 generated) · all PASS
- [x] **V70-DONE-8 · 4 new visual baselines** — 18 → 22 PNG (V70 surfaces locked: FirstTimeBanner / TutorialPage full / ShortcutPalette overlay / Tutorial Step 4 scroll)
- [x] **V70-DONE-9 · Pillar 6 99→99.5 + Pillar 7 88→90 + Pillar 8/9/10 floor** — close DEC §4-§5 per-driver delta accounting

## Sub-DEC progress

- [x] **V70.1 · CFD capability matrix + missing regime closure** — LANDED B161
- [x] **V70.2 · Canonical eval set 20→30** — LANDED B162
- [x] **V70.3 · Novice onboarding (tutorial + tooltips + banner)** — LANDED B163
- [x] **V70.4 · Industrial-UI benchmark + 3 improvements** — LANDED B164
- [x] **V70.5 · Fleet 3 new agents + SCORING-FRAMEWORK Pillar 8/9/10 zones** — LANDED B160 + B161 (split-committed)
- [x] **V70.6 · E2E + 4 visual baselines + arc close** — LANDED B165

## Fleet criteria (10 pillars)

| # | Agent | V69 criteria | V70 criteria |
|---|---|---|---|
| 1 | Code Quality | binary 100 | (unchanged) |
| 2 | Physics | + canonical eval ≥20 | **+ canonical eval ≥30** |
| 3 | UX | ≥11 specs PASS | **≥13 specs PASS** |
| 4 | Visualization | ≥18 PNG | **≥22 PNG** |
| 5 | Smoke | unchanged | unchanged |
| 6 | Functional | 4 sub-DECs · 7 Done | **6 sub-DECs · 9 Done** |
| 7 | Stability | unchanged | unchanged |
| 8 NEW | CFD-Breadth | n/a | turb ≥4 · compressibility ≥3 · steadiness ≥2 · BCs ≥10 · meshing ≥2 |
| 9 NEW | Novice-Onboarding | n/a | tutorial route · 6 tooltips · banner · novice e2e ≥1 · doc ≥1000w |
| 10 NEW | Industrial-UI | n/a | benchmark doc · 6 axes · 3 GUIs · ≥3 improvements · 2 baselines |

## Iteration tracker

| Iter | Date | min(10) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V70 baseline) | 2026-05-16 | TBD | TBD | TBD | charter LANDED · expected lows: cfd_breadth · novice · industrial_ui (all 0 at iter-0) | TBD |

## Reverse-stop log (charter §6 mirror)

- V132 MUTATING_ROUTES net diff > 0
- Capability matrix uncovers structural fraud (workbench can't run a claimed regime)
- Onboarding tutorial >10 min for fresh Claude session
- Industrial-UI benchmark drifts into marketing (no honest "ANSYS better at X")
- New fleet agents introduce flakiness
- ≥3 new canonical eval cases fail to parse on first run

## Counter telemetry

- V70 charter: B159
- V70.1: B160 estimated
- Subsequent: B161-B167 estimated

— V70 ARC-GOAL · 2026-05-16

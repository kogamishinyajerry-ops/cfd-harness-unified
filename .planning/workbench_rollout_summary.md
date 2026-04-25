---
title: "Industrial CFD Workbench · Rollout Summary"
status: COMPLETE_2026-04-25
stages_landed: 6/6
last_polish_commit: c2b3f12
---

# Industrial CFD Workbench · Rollout Summary

**Origin**: User request 2026-04-25 — "如何把这个项目打造成一款工业级的 CFD workbench？让一名刚接触系统的新手 CFD 工程师，也能像使用 ANSYS 或 STAR-CCM+ 一样：每个步骤有清晰的指引、交互、对应部件与产物的渲染显示。"

**Authority**: Codex GPT-5.4 (xhigh) 5-persona meeting transcript at `reports/codex_tool_reports/industrial_workbench_meeting_2026-04-25.md` (Sarah / David / Maya / Kai / Lin — 新手 / 15y PM / UX / WebGL veteran / CFD educator).

**Architecture choice**: hand-written SVG + Tailwind. 3D libs (vtk.js 30 MB, three.js 37 MB, @react-three/fiber, trame-vtk) explicitly REJECTED per Codex bundle-size analysis. Each viz primitive is 6–12 KB raw.

---

## Stage Map

| Stage | Surface | Backend | Frontend | Commit |
|---|---|---|---|---|
| 1 · Shell-split | `/learn/cases/<id>` 5-tab modular layout | n/a | LearnCaseDetailPage 3294→197 LOC + 8 modules | `7537049` |
| 2 · CaseFrame | First-screen geometry/BC/materials/solver | `GET /api/cases/{id}/workbench-basics` | 5 SVG renderers (rectangle/step/airfoil/cylinder/jet_impingement) | `e34f4b4` → `b4a6c04` |
| 3 · MeshTrust | Grid-convergence trust band | `GET /api/cases/{id}/mesh-metrics` (reuses existing GCI service) | `<MeshQC>` 4-chip red/yellow/green | `f44386a` |
| 4 · GuardedRun | Pre-Run preflight checkpoints | `GET /api/cases/{id}/preflight` (5 categories × 10 cases) | `<RunRail>` category-grouped, auto-expand-on-fail | `63f12f2` |
| 5 · GoldOps | System-pulse 10×4 verdict grid | `GET /api/batch-matrix` | `<BatchMatrix>` colored grid + per-row trend + monotonicity | `71734c1` |
| 6 · ExportPack | Audit-ready tabular export | `GET /api/exports/batch.csv` + per-run + manifest | `<ExportPanel>` + `<RunExportPanel>` | `58ee919` |
| Polish | Cross-stage UX cohesion | n/a | `<CaseHealthStrip>` 3-chip pulse + RunExportPanel wire-in | `c2b3f12` |

## Sarah's 12-step Journey → Surface Map

| # | Sarah step | Surface |
|---|---|---|
| 1 | 选案 | LearnHomePage catalog grid |
| 2 | 看几何 | CaseFrame geometry SVG (Stage 2) |
| 3 | 设物性 | CaseFrame materials block |
| 4 | 设边界 | CaseFrame BC pin-map table |
| 5 | 选模型 | CaseFrame solver block |
| 6 | 看网格 | MeshTab + MeshQC band (Stage 3) |
| 7 | 查质量 | MeshQC GCI/Richardson/asymptotic verdicts |
| 8 | 跑基线 | RunTab + RunRail preflight (Stage 4) |
| 9 | 盯收敛 | MeshTab sparkline + GCI table |
| 10 | 对 gold | CompareTab + ScientificComparisonReportSection |
| 11 | 批量扫 | LearnHomePage BatchMatrix (Stage 5) |
| 12 | 出报告 | LearnHomePage ExportPanel + Pro Workbench audit-package |

---

## Live Data Statistics (verified 2026-04-25T14:10Z)

| Metric | Value |
|---|---|
| Stage 2 · workbench-basics endpoints | 10/10 returning 200 |
| Stage 2 · case shapes covered | rectangle / step / airfoil / cylinder / jet_impingement |
| Stage 3 · GCI computable | 8/10 (RBC + impinging_jet honestly degrade to gray on oscillating convergence) |
| Stage 4 · preflight categories | 5 (adapter / schema / gold_standard / physics / mesh) |
| Stage 4 · cross-case overall verdicts | DHC pass; BFS/RBC/flat_plate/duct partial; LDC/cylinder/plane_channel/NACA/jet fail |
| Stage 5 · batch matrix cells | 40 cells (10 × 4) — 12 PASS / 8 HAZARD / 20 FAIL / 0 UNKNOWN |
| Stage 5 · monotonic-improvement rows | 10/10 (no row regresses with refinement) |
| Stage 6 · export schema columns | 34 |
| Stage 6 · batch CSV rows | 81 (across all available runs, not just mesh sweep) |
| Stage 6 · export verdict distribution | 48 FAIL / 13 HAZARD / 20 PASS |

## Codex Anti-Pattern Guards Observed

Each stage encodes a specific guard against the meeting's anti-patterns:

| Anti-pattern | Where guarded |
|---|---|
| 把报告页伪装成工作台 | CaseFrame.tsx — terse hints (3 captions × 1 line max), structured data only, no prose mirror of StoryTab |
| 假安全感 (mesh metrics 全绿但物理仍错) | MeshQC.tsx footer — verbatim "Mesh QC 全绿 ≠ 案例物理对" + gray-state on oscillating-convergence |
| 信息过载 (BatchMatrix 沦为 spreadsheet) | BatchMatrix.tsx — per-row trend column compresses 4 cells to 1 arrow; monotonicity counter footer |
| 网格质量证书伪装 | Real cross-case variance surfaced (LDC 2Y/2G, DHC 1R/3G, RBC 3 gray) — no fake-green |
| 证据不一致 (PDF ≠ xlsx data divergence) | Stage 6 CSV/PDF share `build_validation_report` — single source of truth |
| 红条但无 actionable evidence | RunRail.tsx — fail rows auto-expand showing evidence_ref + consequence |

---

## Architectural Decisions

### Hand-written SVG over 3D libs
Codex bundle-size analysis: vtk.js 30.3 MB, three.js 37.0 MB, @react-three/fiber 2.17 MB+three, trame-vtk 1.64 MB+WebSocket all rejected. Each Stage primitive 6–12 KB raw. Total Stage 2-6 frontend addition: ~30 KB JS / 2.5 KB CSS.

### Soft-skip pattern for partial coverage
Endpoints return 404 (not 500) when authoring is incomplete. Frontend components return `null` on 404 so untreated cases gracefully fall through to the legacy hero/illustration. Adding a new authored case is purely additive; no code changes needed.

### Schema-version forward-compat
- `workbench-basics.schema_drift_warning` softens patch_id mismatches to amber banner instead of 500
- `mesh-metrics.qc_band` admits 4 verdicts (green/yellow/red/gray) — gray = honest "can't compute"
- `preflight.PreflightStatus` admits "partial" alongside pass/fail/skip
- `export_csv.COLUMNS` is a stable list — adding columns is forward-compat; renaming/removing requires schema_version bump

### CSV chosen over xlsx (Stage 6 format substitution)
Rationale: project has no openpyxl runtime dep. CSV is functionally equivalent for audit (Excel/Sheets/pandas open natively). Future xlsx upgrade is a one-import swap. Schema is captured in `COLUMNS` constant — version-stable.

---

## Deferred Items (not blocking close)

| Item | Stage | Rationale for deferral |
|---|---|---|
| First-visit guided tour | 4 | RunRail's auto-expand-on-fail + tone-aware footer already provides inline pedagogy |
| `<ContractOverlay>` light SVG primitive | 5 | Existing `ScientificComparisonReportSection` (529 LOC, HTML-iframe) already serves the gold-vs-measurement overlay surface |
| Manifest table (full export audit log) | 6 | Stage 6 manifest endpoint already captures schema_version + counts + exporter; full audit log with timestamps is a separate "export-tracking" feature |
| xlsx export (vs current CSV) | 6 | Awaits openpyxl runtime dep; CSV is functionally equivalent for audit consumers today |

## Future Stages (out of original 6-stage scope)

The 6 stages cover Sarah's 12-step journey end-to-end. Natural future extensions if demand emerges:

- **3D streamline / iso-surface viewer** — explicitly REJECTED in this rollout per Codex bundle analysis. Would warrant a separate RFC if a case-specific scientific question genuinely requires it.
- **Live solver streaming** — exists in Pro Workbench `/runs/<case>` (Stream); could be surfaced inline to RunTab as a follow-on.
- **Pro Workbench polish** — audit-package builder UI could absorb similar viz-first treatment as `/learn` did.

---

## Where To Look (new-contributor map)

- **Backend**:
  - schemas: `ui/backend/schemas/{workbench_basics,mesh_metrics,preflight,batch_matrix}.py`
  - services: `ui/backend/services/{preflight,batch_matrix,export_csv}.py`
  - routes: `ui/backend/routes/{workbench_basics,mesh_metrics,preflight,batch_matrix,exports}.py`
  - registered in: `ui/backend/main.py`
- **Frontend**:
  - shared types: `ui/frontend/src/types/{workbench_basics,mesh_metrics,preflight,batch_matrix,exports}.ts`
  - api client: `ui/frontend/src/api/client.ts`
  - per-case primitives: `ui/frontend/src/pages/learn/case_detail/{CaseFrame,MeshQC,RunRail,CaseHealthStrip}.tsx`
  - system-level primitives: `ui/frontend/src/components/learn/{BatchMatrix,ExportPanel}.tsx`
- **Authoring**:
  - workbench data: `knowledge/workbench_basics/<case_id>.yaml`
  - whitelist: `knowledge/whitelist.yaml`
  - gold standards: `knowledge/gold_standards/<case_id>.yaml`

---

## Roadmap Document

Authoritative roadmap with per-stage triggers + close conditions: `.planning/roadmaps/workbench_rollout_roadmap.md`. This document is the current-state snapshot; the roadmap is the trigger-based plan.

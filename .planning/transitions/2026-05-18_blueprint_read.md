# Blueprint Read · Industrial-Minimalist UI · 2026-05-18

> Source: `/Users/Zhuanz/Downloads/AI CFD workbench Blueprint/` · 8 PNG images (GPT image-2 generated)
> Partner doc: `2026-05-18_industrial_minimalist_pivot.md` (savepoint)
>
> This file decodes the 8 blueprint images into design tokens, layout grid, view modes, and a component-by-component mapping to existing V91 code paths. It is the bridge between user's external blueprint and Claude-side implementation.

---

## 1 · Design language (extracted across 8 images · consistent)

### 1.1 Color tokens

| Token | Hex (approx) | Used for |
|---|---|---|
| `bg.canvas` | `#0B1116` | 3D viewport · main canvas background (near-black with cool tint) |
| `bg.shell` | `#0E141A` | Page background outside cards |
| `bg.surface` | `#161C24` | Side panels (left rail · right rail) |
| `bg.surface-raised` | `#1C232C` | KPI chips · status cards · BottomBar |
| `border.subtle` | `#222932` | 1px dividers between panels |
| `text.primary` | `#E8ECF1` | Headlines · KPI numbers |
| `text.secondary` | `#8B95A3` | Labels · captions · tree items |
| `text.tertiary` | `#5A6471` | Disabled · placeholder |
| `accent.healthy` | `#3DC97F` | ✓ check marks · active-step glow · "通过" pill · healthy KPI delta |
| `accent.active` | `#F0A93B` | current-pipeline-step glow · selection ring (image-8 active thumbnail) · "求解中" indicator |
| `accent.warn` | `#E8A24B` | ⚠ caution status · drift warning |
| `accent.crit` | `#E5564E` | error · failure verdict (sparingly used) |
| `accent.brand` | `#5BB4FF` | links · interactive hover · AI assistant icon |
| `cfd.colormap` | blue→cyan→green→yellow→orange→red | velocity / pressure / temperature contours (standard rainbow) |

**Color discipline (matches user's prior pivot constraint):** accents < 5% of pixels · backgrounds 90%+ · grayscale dominates · color = signal, never decoration.

### 1.2 Typography

| Role | Size | Weight | Note |
|---|---|---|---|
| Wordmark "CFD 全流程工作台" | 12px | 400 | Top-left, muted |
| Run identity (center top) | 12px | 400 | "APU 舱通风 · R-042 · 计算时间 · Cluster-01 [128 核]" — single line, comma-separated |
| KPI number | 28-32px | 600 | Tabular numerals · `font-variant-numeric: tabular-nums` |
| KPI label | 11px | 400 | Below number, muted |
| Tree item | 12px | 400 | LeftRail file list |
| Pipeline step label | 10-11px | 500 | Under dot indicator |
| Status card title | 12-13px | 500 | RightPanel headlines |
| Status card body | 11px | 400 | One-line subtitle max (NO paragraph) |
| Button (CTA in status card) | 11px | 500 | "采纳建议" / "查看负载" / "启动几何分析" |

**Font family**: SF Pro Text / Inter for Latin, PingFang SC / Noto Sans CJK SC for Chinese. Tabular nums on all KPI displays.

### 1.3 Spacing & density

- Panel padding: 12-16px
- Card internal padding: 10-12px
- Card-to-card gap: 8px
- KPI chip width: ~120-140px · height ~72px
- LeftRail tab icon strip: 36px wide
- LeftRail tree column: 180px wide (total left zone ~220px)
- RightPanel: 280-320px
- TopBar height: 32px
- BottomBar pipeline strip: 56-64px
- KPI strip (above pipeline): 80-90px

**Density signal**: information-per-pixel is HIGH on rails (dense trees, dense status pills) but the MainCanvas breathes — that contrast IS the "industrial-minimalist" feel.

### 1.4 Iconography

- LeftRail uses 16px monochrome line icons in a vertical tab strip (案例 / 物体 / 几何 / 网格 / 物理 / 边界 / 仪表 / 求解 / 后处理 / 设计探索)
- RightPanel status cards prefix with 16px filled status icon (✓ ⚠ ★ ⓘ)
- Pipeline steps use 12px filled dots + check overlay
- BottomBar action chips include small icon prefix (≤16px)

---

## 2 · 5-zone layout grid (constant across all 8 views)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ TopBar (32px) · wordmark · run identity · AI助手 button                     │
├────────┬───────────────────────────────────────────────────┬───────────────┤
│        │                                                   │               │
│        │                                                   │               │
│  Left  │                MainCanvas                         │  RightPanel   │
│  Rail  │                (viewport · charts · DOE grid)     │  "AI 助理"     │
│  220px │                                                   │  280-320px    │
│        │                                                   │               │
│        │                                                   │               │
│        ├───────────────────────────────────────────────────┤               │
│        │ KPI strip (4-6 chips · 80px)                      │               │
├────────┴───────────────────────────────────────────────────┴───────────────┤
│ BottomBar · pipeline 7-step strip · 56px                                    │
└────────────────────────────────────────────────────────────────────────────┘
```

- **TopBar**: brand · context (current run · cluster · iters) · AI assistant toggle
- **LeftRail**: vertical icon tabs (left edge) + scrollable tree (right column inside rail)
- **MainCanvas**: morphs by mode — 3D viewport / mesh / DOE grid / residual+history charts
- **RightPanel**: stack of compact AI status cards (1-line title + 1-line subtitle + 1 CTA each, NEVER multi-paragraph)
- **KPI strip**: 4-6 numeric chips horizontally — always visible, content morphs by step
- **BottomBar**: 7-step pipeline (导入 → 几何 → 网格 → 物理 → 边界 → 求解 → 后处理 [→ 设计探索]) with dots; active = orange glow, done = green check

---

## 3 · View modes (one per image · same 5-zone frame, different MainCanvas content)

| # | Image | Active step | MainCanvas content | KPI strip | RightPanel cards |
|---|---|---|---|---|---|
| 1 | (1) Solver running | 求解 (orange glow) | Velocity vectors around engine in box · 3D | 18.76M / 2.3e-05 / 248.6 / 3.62 kg/s / 96.4 / 65% | "求解器运行中" · "GPU 满载" · "下个 200 步" |
| 2 | (2) Geometry intake | 几何 | Color-coded CAD parts (inlet/outlet/rotor/heat-wall labels) | 17部件 / 2实例 / 2.0mm 容差 / 18.76M est-cells | "几何已就绪" · "启动几何分析" · "建议合并 2 个实例" |
| 3 | (3) Physics setup | 物理 | Velocity field overlay on engine | 物理模型 5 / 边界 5 / 计算工况 / 28.6M est-cells | "推荐 SST k-ω" · "稳态流动" · "应用预设" |
| 4 | (4) Mesh inspection | 网格 | Wireframe mesh detail on box | 5 histograms (skewness / aspect / orthogonality / quality / size) | "网格生成完成" · "18.86M 单元 · 0.128 max skew" · "评估" |
| 5 | (5) Boundary assignment | 边界 | Engine with labeled inlet/outlet/hot-wall/rotor-zone arrows | 28 入口 / 27 出口 / 6 壁面 / 1 转子域 | "AI 边界识别完成" · "确认边界 6 处" · "应用 AI 提案" |
| 6 | (6) Solver convergence | 求解 | Residuals chart + temperature time-history (split-grid) | 2.8e-06 / 248.6 / 3.62 / 96.4 / 1250/2000 iter | "收敛趋势良好" · "通过验证 200 步" · "GPU 满载" |
| 7 | (7) Post-process | 后处理 | Velocity contour + 3 small line charts + radial chart | 248.6 / 3.62 / 96.4 / 65% / +4.2% | "对比基准" · "增益 +4.2%" · "通过" (green pill big) |
| 8 | (8) Design exploration | 设计探索 | 3×3 grid of mini-thumbnails + scatter plot below + selection ring | 28 / 212.6 / 94.1 / 18.42m³ | "推荐 5 个设计" · "实验比对就绪" · "导出报告" |

**Insight**: same frame, MainCanvas+KPI+RightPanel content swap per active step. This is a **mode pattern**, not 8 separate pages. One root component + 8 mode renderers.

---

## 4 · Component-by-component mapping to existing V91 code

| Blueprint element | Existing code path | Action |
|---|---|---|
| **TopBar** wordmark + run identity | `ui/frontend/src/pages/workbench/v3/components/TopBarV3.tsx` (search) | **REWRITE minimalist** — drop dense action ribbon, keep only wordmark · run-context · AI toggle |
| **LeftRail** vertical icon tabs | NEW — does not exist in current V3 | **NEW component**: `LeftRailMinimalist.tsx` (36px icon strip + 180px tree) |
| LeftRail tree (file/case/object hierarchy) | partial: case browser exists but **TOO PROMINENT** | **HIDE teaching cases** per pivot · tree now shows current-run objects only |
| **MainCanvas** 3D viewport | `MainCanvasV3.tsx` + `viewport_kernel.ts` (V91 restored `setCameraPreset`) | **KEEP** infrastructure · re-skin frame (drop overlays · let viewport breathe) |
| MainCanvas mode swap (mesh / DOE grid / charts) | partial: residuals + advisor tabs exist | **REFACTOR** into mode-renderer pattern keyed by active pipeline step |
| **KPI strip** numeric chips | partial: scattered in `BottomPanelV3` | **EXTRACT** into `KpiStripV2.tsx` · binds to manifest `key_quantities` + comparator `gold_delta` |
| **RightPanel** AI status cards (compact pills) | `AdvisorContent.tsx` PostRunAdvisorV9 | **REPLACE** verbose cards with `AdvisorPillStack.tsx` · consumes `MatchedCommentary[]` from V91 matcher · renders 1-line title + 1-line summary + 1 CTA · progressive disclosure for full commentary |
| Status pill severity → color | V91 rule corpus has `severity: advise/warn/info` | **MAP**: advise→`accent.healthy` · warn→`accent.warn` · info→`text.secondary` |
| **BottomBar** 7-step pipeline | partial: 5-step strip exists in `WorkbenchShellV3` | **EXTEND** to 7 steps + add 设计探索 conditional · refresh dot/glow visual |
| Pipeline step state (done/active/pending) | run state in `run_state.py` + `useRunStateV8` | **REUSE** state hook · just re-skin |
| Pipeline active-step glow (orange) | NEW visual | **NEW CSS**: `accent.active` keyframe pulse 2s |
| 3D camera presets (front/top/iso) | `viewport_kernel.ts` `setCameraPreset` (V91 restored) | **KEEP** · expose 3 camera buttons in TopBar or MainCanvas overlay |
| DOE grid (image 8 · 3×3 thumbnails) | NEW — does not exist | **NEW component**: `DoeGrid.tsx` · placeholder until DOE/design-exploration data layer exists (currently stub) |
| Comparator verdict pill ("通过" big green in image 7) | comparator output exists | **NEW visual**: `VerdictPill.tsx` consumes comparator verdict |
| Histogram strip (image 4 · 5 mesh-quality histograms) | partial: `MeshQualityCard` exists | **REFACTOR** to horizontal sparkline-histogram strip in KPI position |
| Boundary-condition labels on 3D model (image 5) | NEW — 3D annotations | **NEW**: `ViewportAnnotations.tsx` overlays sprite labels on viewport using BC zones from sHM dict |

---

## 5 · Gap analysis (what V91 does NOT yet have)

These are the items where the new blueprint demands surface area beyond what V91 closed delivers:

| Gap | Severity | Why |
|---|---|---|
| **G1 · 3D viewport annotations** (inlet/outlet/hot-wall sprite labels) | Medium | Needed for image 5 · current viewport has no annotation layer · need to wire boundary zones → 3D sprite labels |
| **G2 · DOE / design-exploration data layer** | High (but later) | Image 8 shows 3×3 parameter sweep + scatter — no backend support yet · this is a future arc, not Day-1 |
| **G3 · 3D camera preset UI** | Low | `setCameraPreset` exists in kernel · just needs 3 buttons in chrome |
| **G4 · 5-histogram horizontal strip** | Low | `MeshQualityCard` data exists · just visual refactor |
| **G5 · Run identity in TopBar** | Low | `R-042 · 计算时间 · Cluster-01 [128 核]` requires reading run_id + start_time + cluster_meta · all already in manifest |
| **G6 · Progressive disclosure for advisor commentary** | Medium | V91 matcher returns full commentary string · new UI wants 1-line summary + expand-on-click · need to define summary derivation (first sentence? first 30 chars? new field?) |
| **G7 · "Hide teaching cases" enforcement** | Medium | Current `CaseBrowserV3` exposes case_001..016 prominently · per pivot constraint must hide · need feature flag or replacement |
| **G8 · KPI delta indicators** (+4.2% green badge in image 7) | Low | Comparator already produces `gold_delta` · just visual binding |
| **G9 · BottomBar pipeline step "设计探索"** | Low | Add 7th step (currently 6) · conditional render when DOE arc lands |

---

## 6 · Suggested phased landing (DO NOT execute without user gate)

### Phase A · Foundation (skeleton + tokens · 1-2 days)
- A1. Extract design tokens (§1.1-1.3) into `ui/frontend/src/theme/industrial_minimalist.ts` · CSS custom properties · Tailwind-extension OR plain CSS vars (TBD which the codebase uses)
- A2. Build `WorkbenchShellV4.tsx` (parallel to V3, feature-flagged behind `?ui=v4` query param) with empty 5-zone grid · NO content
- A3. Visual baseline test for the empty shell

### Phase B · Migrate load-bearing zones (3-5 days)
- B1. TopBar minimalist rewrite
- B2. LeftRail icon-tab strip + tree (teaching cases hidden behind dev flag)
- B3. KPI strip · binds to existing manifest contracts
- B4. BottomBar 7-step pipeline · uses existing run state
- B5. MainCanvas wrapper (viewport unchanged, just frame re-skinned)

### Phase C · RightPanel advisor refactor (CORE PIVOT WIN · 1-2 days)
- C1. `AdvisorPillStack.tsx` replaces `PostRunAdvisorV9` verbose card UI
- C2. Consumes `MatchedCommentary[]` directly from V91 matcher (no schema change to data layer)
- C3. Progressive disclosure: pill collapsed = title + 1-line · click expands to full commentary + provenance
- C4. Severity → color mapping
- C5. CTA buttons (e.g. "采纳建议") · for V91 corpus these are mostly informational, so initial CTAs = `查看详情` / `定位证据`

### Phase D · Per-mode MainCanvas renderers (5-7 days, can parallelize)
- D1. Geometry mode (image 2)
- D2. Mesh mode (image 4 · histograms)
- D3. Physics mode (image 3 · overlay)
- D4. Boundary mode (image 5 · annotations · **GAP G1 lands here**)
- D5. Solver mode (image 1 · velocity vectors) + (image 6 · residuals split)
- D6. Post mode (image 7 · contour + verdict pill)
- D7. DOE mode (image 8) — STUB until DOE backend lands (GAP G2)

### Phase E · Cutover (decision gate · later)
- E1. Side-by-side run V3 vs V4 with same data · regression-baseline visual diffs
- E2. After parity + 4Q-gate + V132=9 verified · flip default to V4 · keep V3 reachable for 1 arc
- E3. Delete V3 only after 1-arc grace period · single big-bang commit

---

## 7 · Risks / open questions for user

1. **Q1**: Tokens — do you want me to use existing CSS-vars approach in `ui/frontend/src/index.css`, OR a TS theme module, OR Tailwind extension? (Need to grep current convention before deciding.)
2. **Q2**: V4 shell parallel-build (behind `?ui=v4` flag) vs in-place upgrade of V3? Parallel is safer (V91 close gate stays valid) but doubles surface area temporarily.
3. **Q3**: AI assistant CTA actions — current V91 corpus is advisor-not-driver (V130). Do CTAs trigger any side effect, or are they all "查看详情/证据" disclosures? (Recommend: all disclosures · zero side effects · preserves V130.)
4. **Q4**: DOE mode (image 8) — confirm this is aspirational (future arc) not Day-1? My phasing puts it as stub.
5. **Q5**: 中英文 — the blueprints are all Chinese. Should I localize from Day-1 (zh-CN primary, en fallback) or Chinese-first only?
6. **Q6**: Teaching-case "hidden backstage" — acceptable to gate `CaseBrowserV3` behind a dev-mode env var (e.g. `VITE_CFD_SHOW_TEACHING_CASES=1`) so engineering still has access, end users don't?

---

## 8 · What does NOT change (anchored by §5 of pivot savepoint)

- V130 7 defense layers
- V132 endpoint lock = 9
- HMAC byte-reproducibility on `audit_package.zip`
- JSON SSOT canonical (`v9_advisor_rules.json`)
- Cross-language matcher parity (TS ↔ Python · 6 fixtures × 8 rules)
- OpenFOAM backend authority
- Gold-standard comparator verdict

The new UI **consumes** these contracts unchanged. Pivot is presentation-only.

---

— Blueprint Read · 2026-05-18 · awaiting user gating on §6 phasing + §7 open questions

# Blueprint v3 · Unified Product Vision · 2026-05-07

> **Authored**: 2026-05-07 by Claude Code Opus 4.7 (1M context)
> **Triggered by**: User consolidation of three-narrative drift (V&V-first → Beginner full-stack → AI-as-advisor) into single product blueprint
> **Concept reference**: `~/Downloads/cfd_harness_workbench_ui_concept.svg`
> **Memory mirror**: `~/.claude/projects/-Users-Zhuanz/memory/project_cfd_harness_blueprint_v3.md` + `feedback_cfd_four_question_gate.md`
> **Notion mirror**: `cfd-harness-unified` command center top callout (synced 2026-05-07)
> **Supersedes (as product blueprint layer)**: implicit drift between Pivot Charter (2026-04-22) + Addendum 3 (2026-04-28) + V130 (2026-05-06)
> **Does NOT supersede**: roadmap_v2 (M1-M6 file), DEC-V61-130 charter, individual sub-DECs

---

## 1. North star · single sentence

> 一个工程师主导的 CFD 工作台：用户用普通 CAE 交互完成几何、网格、物理、边界、求解、后处理；系统用 OpenFOAM 产出真实 artifacts；Metrics 和 TrustGate 负责判断可信度；Correction / Decision Trail / Audit Package 负责把每一次失败、修正和证据沉淀下来；AI 只在「审查」和「诊断」两个入口中给建议。

## 2. Why three narratives, why now consolidate

| Layer | Era | Owner-statement |
|---|---|---|
| **Path B** — V&V-first regulated workbench | 2026-04 (Pivot Charter) | "可审计的 CFD 证据工作台 · 每次 run 都能追溯 measurement ↔ gold-standard ↔ tolerance ↔ citation ↔ commit SHA ↔ decision trail" |
| **Beginner full-stack workbench** | 2026-04-27 (Addendum 3) | "一个有本科 CFD 基础的新手，30 分钟内 STL→mesh→solve→verdict→report" |
| **AI is advisor, not actor** | 2026-05-06 (V130) | "Workbench 必须 LLM 离线时也能跑全流程 · AI 仅 GET + advise" |

Three layers stack non-conflicting but appeared as "missing blueprint" because no single artifact made the synthesis explicit. Blueprint v3 IS that synthesis.

## 3. Three users, one workbench

| User | Path through workbench | Design implication |
|---|---|---|
| Beginner engineer (BSc CFD basis) | Import → Mesh → Setup BC → Solve → Results · 30-min target · zero-config | Beginner preset on every step; "Run" buttons obvious; no jargon-only labels |
| Senior CFD engineer | mesh sizing field · BC patch annotation · solver dict · RawDict override | "Power" toggle on every panel; engineer-driven control surface; advanced disclosure |
| Auditor / regulator | Gold standards · CaseProfile · MetricsRegistry · TrustGate · DecisionTrail · Audit Package | Evidence Stack always visible; HMAC + zip; copy-paste-ready citations |

UI is the **shared entry**. Page count must NOT scale with user-type count.

## 4. UI four-region stable layout (concept SVG anchor)

```
┌─────────────────────── TopBar (case · OpenFOAM truth · TrustGate · LLM offline OK · Audit % · AI=advisor) ─────────────────┐
│                                                                                                                              │
│  ┌──────────────────┐ ┌─────────────────────────────────────────────────────────┐ ┌────────────────────────────────────────┐│
│  │  Process Spine   │ │  Viewport (mode-switched per Step)                       │ │  Engineer Control Rail                ││
│  │                  │ │  + Artifacts / Metrics / Trust drawer                    │ │                                        ││
│  │  5-Step:         │ │                                                          │ │  CompletenessCard (top, fixed)         ││
│  │   1. Import      │ │  Geometry GLB | Mesh Wireframe | BC Faces |              │ │  Step parameters (Beginner/Power)      ││
│  │   2. Mesh ◀ N2   │ │  Field Slice | Residuals | Report Grid                   │ │  Manual Rescue / RawDict Override      ││
│  │   3. Setup BC    │ │                                                          │ │  AI 审查 / AI 诊断 (advisory only)     ││
│  │   4. Solve       │ │  Metrics row: cells / faces / TrustGate /                │ │  Step navigation                       ││
│  │   5. Results     │ │  residual / audit hash / live residuals                  │ │                                        ││
│  │                  │ │                                                          │ │                                        ││
│  │  Evidence Stack: │ │  Report grid (2x2): |U|+streamlines /                    │ │                                        ││
│  │   Gold standards │ │  pressure / vorticity / centerline                       │ │                                        ││
│  │   CaseProfile    │ │                                                          │ │                                        ││
│  │   RunHistory     │ │                                                          │ │                                        ││
│  │   DecisionTrail  │ │                                                          │ │                                        ││
│  │   AuditPackage   │ │                                                          │ │                                        ││
│  │                  │ │                                                          │ │                                        ││
│  │  N1-N6 ribbon    │ │                                                          │ │                                        ││
│  └──────────────────┘ └─────────────────────────────────────────────────────────┘ └────────────────────────────────────────┘│
│                                                                                                                              │
│  Truth Chain: Engineer Action → FastAPI Route → OpenFOAM Docker → Artifacts → MetricsRegistry → TrustGate → Report+Audit    │
│                                                                                            (AI cannot mutate case)           │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Hard constraint**: N2-N6 must build INTO this layout. No new top-level pages.

## 5. Four-question gate (every PR / DEC / UI change must answer)

1. **LLM 离线时，工程师能不能完成这一步？** — 离线无法跑 = V130 violation
2. **这一步有没有清晰的 artifacts 输出？** — 无 OpenFOAM artifacts = 失去真相源
3. **TrustGate / completeness / audit trail 能不能解释这一步的可信度？** — 不能 = 失去护城河
4. **AI 是否只提供审查或诊断，而没有直接调用 mutating route？** — Mutation = SSOT registry (`MUTATING_ROUTES` / `KNOWN_MUTATION_FUNCTIONS`) 拦截

PR body / DEC frontmatter MUST display answers (even if 4×Yes — visible explicit affirmation).

## 6. N2-N6 convergence sequence (bound to UI 4-region)

| N | Milestone | UI region anchor | Acceptance shape (4-question gate baseline) |
|---|---|---|---|
| **N1** | AI auto-mutation deprecation | Engineer Control Rail (no "Apply" buttons on AI surface) | ✅ DONE (V130+V131+V132+V133) |
| **N2** | Mesh control parity | Step 2 Viewport + Mesh parameter rail | charter ✅ V134 · N2.1 ✅ V135 · N2.2/N2.3/N2.4 next |
| **N3** | Physics / materials | Step 3+ panel; CaseProfile contract | not started |
| **N4** | BC / solver unification | Step 3+4 merged "physics setup workbench" | not started |
| **N5** | Post-processing report | Step 5 report-bundle upgrade | not started |
| **N6** | AI advisor stack | Engineer Control Rail bottom (review + diagnose only) | not started |

## 7. What NOT to do

- ❌ Add a 6th step to the spine (e.g., "Validate", "Calibrate") — fold into existing 5
- ❌ Build an "AI Workbench" sibling page — AI lives in the Control Rail panel only
- ❌ Auto-apply any AI suggestion to case state — copy-paste only, engineer types
- ❌ Add features that require LLM online to function — N6 advisor stack itself must degrade gracefully
- ❌ Plan based on calendar dates — dependency-driven only (per `feedback_no_schedule_gating.md`)

## 8. Living artifacts (this blueprint must not silently rot)

| Artifact | Purpose | Update trigger |
|---|---|---|
| `.planning/strategic/blueprint_v3_2026-05-07.md` (this file) | Source of truth | Every N-phase close re-validates Section 4-6 |
| `~/.claude/projects/-Users-Zhuanz/memory/project_cfd_harness_blueprint_v3.md` | Cross-session memory | Always-current mirror |
| Notion command center top callout | Human-readable mirror | Session-end batch sync (per V133) |
| `~/Downloads/cfd_harness_workbench_ui_concept.svg` | Visual anchor | Update only on layout change (rare) |

If a sub-DEC's PR cannot answer four-question gate cleanly, **stop and consult this file** before proceeding.

— EOF —

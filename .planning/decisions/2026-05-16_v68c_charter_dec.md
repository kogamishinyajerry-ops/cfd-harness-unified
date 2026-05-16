---
decision_id: DEC-V68-C-charter
title: V68-C "AI Advisor Integration & Material Wiring" arc charter · ProposalCard real /ai-review+/ai-diagnose + MaterialCard /physics route + case_002a metadata-entry + V68-D continued spike · Pillar 6 97→98 + Pillar 7 82→85 · ≥99 fleet mandate
status: Accepted
parent_dec: DEC-V68-B-close
phase: V68-C
notion_sync_status: pending
predecessor: DEC-V68-B-close
batch: B139
confidence: high
autonomous_governance: true
verdict: ARC_CHARTER_ACCEPTED
v_row_landed: none (charter)
substrate: V68-B close DEC §9 follow-on candidates · user mandate "全都要" (C + F core, E partial, D continued spike)
---

# DEC-V68-C-charter · V68-C "AI Advisor Integration & Material Wiring"

## 1 · Decision

Launch successor arc **V68-C "AI Advisor Integration & Material Wiring"** consolidating user-mandated "全都要" merged scope:
- **C (M3 physics-material wiring)**: MaterialCard reads real `GET /api/cases/:id/physics` (returns material_dict_text + regime_dict_text from `constant/physicalProperties` + `constant/momentumTransport`)
- **F (AI advisor real route integration)**: ProposalCard exercises real `GET /api/cases/:id/ai-review` + `/ai-diagnose` (backend routes already exist · ai_advisor.py · need front-end wiring + LLM-offline fallback tests)
- **E partial (case_002a metadata-entry)**: add APU bay placeholder to whitelist as `case_kind=imported_user` with documented `gold_pending` flag · listable via `/api/cases` but visibly disclaimer'd ("⏳ gold standard authoring in progress · V68-E.2 follow-on")
- **D continued spike (OpenFOAM-WASM)**: extend `.planning/research/openfoam_wasm_feasibility.md` with **iter-2 findings** (docker-based emsdk install attempt + dependency-stub triage · still NO actual compile · still spike-class · still ≤30 LOC)

User mandate (continuation of V67-C / V68-A / V68-B "全都要" pattern): *"全权开发 · 7-agent fleet · 真实测评 · 使用手感 · 可视化追踪 · ≥99 分以上 · 一直迭代"*. V68-C is **4th arc** in the single-day pattern (V110 advisor-class · 4th application).

## 2 · Rationale · why all four (C+F+E-partial+D-continued) in one arc

| Component | Single-day feasible? | Why combined |
|---|---|---|
| **C M3 material wiring** | YES (4-6h) | Backend `/api/cases/:id/physics` already exists · gap = frontend MaterialCard hook + tests |
| **F AI advisor route** | YES (4-6h) | Backend ai_advisor.py already exists · gap = ProposalCard wiring + LLM-offline behavior tests |
| **E case_002a metadata** | PARTIAL (3-4h) | Gold standard authoring multi-day; metadata-entry alone single-day · explicit `gold_pending=true` flag is honest |
| **D OpenFOAM-WASM** | NO (14-22 weeks) | V68-B.6 spike confirmed · continued spike-class artifact (no compile attempt) |

Combined arc adds C + F = ~12 prod LOC each + tests · E = ~80 LOC config + DEC · D = research-only doc extension. Total LOC est: ~250 prod + 200 test · within single-day budget given the V67-C/V68-A/V68-B pattern execution time.

Pillar 6 ceiling: 97 → **98** (+1 raw · +0.1 weighted · MaterialCard real wiring is the marginal lift)
Pillar 7 ceiling: 82 → **85** (+3 raw · +0.15 weighted · AI advisor real route integration finally exercises Pillar 7 SSOT against real backend in the workbench surface)

Combined weighted advance: **+0.25** (vs V68-B's +0.20 · slightly more headroom because Pillar 7 had more raw room).

## 3 · North Star

> "工程师打开 `/workbench/case/naca0012_airfoil?step=3`，看到 MaterialCard 真实显示 `constant/physicalProperties` (icoFoam → transportProperties: `nu=1e-3`) + `constant/momentumTransport` (laminar)。打开 ProposalCard，点 [审 review] 真实 GET /ai-review · 返回 review verdict + comments；点 [诊 diagnose] 真实 GET /ai-diagnose · 返回 diagnosis + 建议。两个 AI 路由 LLM-offline 时仍返回 graceful 'advisor offline' 状态，UI 不挂。case_002a APU bay 在 `/workbench` index 可见，标 `⏳ gold pending`，点开能跳到对应 case page (即便 gold 还没补完)。OpenFOAM-WASM iter-2 spike 记录 docker-based emsdk 路径 + 进一步的 dep triage。"

## 4 · Done Definition (7 dims · all FULL-MET for V68-C close · same standard as V68-A/B)

| # | Done dim | Threshold | Verification |
|---|---|---|---|
| 1 | M3 MaterialCard real-data wiring | `usePhysicsState` hook hits real `GET /api/cases/:id/physics` · MaterialCard renders material + regime · graceful fallback when route 404s | hook tests + 1 vitest component test |
| 2 | ProposalCard AI review real route | `useAiReview` hook (or extends existing path) hits real `GET /api/cases/:id/ai-review` · returns ReviewResponse · displayed in ProposalCard | hook tests + 1 vitest interaction test |
| 3 | ProposalCard AI diagnose real route | Same shape as #2 but for `/ai-diagnose` · returns DiagnoseResponse | hook tests + 1 vitest interaction test |
| 4 | LLM-offline graceful fallback | AI hooks return blueprint-safe state ('advisor offline · advisory-only') when backend returns 503/500 · V130 invariant preserved · UI doesn't crash | LLM-offline fallback tests · 4 cases |
| 5 | case_002a APU bay metadata entry | Whitelist YAML includes case_002a entry with `case_kind=imported_user` + `gold_pending=true` flag · listable via `/api/cases` · disclaimer surfaces in UI list | backend pytest + frontend integration test |
| 6 | E2E against real backend (extended) | 41+ e2e PASS (was 37 V68-B · +4 V68-C cases for physics + ai-review + ai-diagnose + case_002a metadata reachability) | playwright test |
| 7 | Pillar 6 ≥98 + Pillar 7 ≥85 dual re-anchor + V68-D continued spike | SCORING-FRAMEWORK.md Pillar 6 + Pillar 7 anchor language updated · `openfoam_wasm_feasibility.md` iter-2 section added · close DEC §10+§11 | close DEC |

**Close gate**: 7/7 Done dims FULL-MET (no SCAFFOLDING discount) + fleet min(7) ≥99 for 2 consecutive iter.

## 5 · Sub-DEC seeds (4 sub-DECs · serial · V68-D as continued-spike inside V68-C.4)

### V68-C.1 · MaterialCard real-data wiring + usePhysicsState hook
- New `usePhysicsState(caseId)` hook against `/api/cases/:id/physics`
- MaterialCard or equivalent surface in Step 3 step body uses the hook
- LOC est: ~80 prod + 60 test
- Confidence: med

### V68-C.2 · ProposalCard AI advisor real route (review + diagnose)
- Wire ProposalCard to existing `/ai-review` + `/ai-diagnose` routes
- 4 LLM-offline fallback tests (review-503, review-500, diagnose-503, diagnose-500 → all return graceful state)
- LOC est: ~70 prod + 100 test
- Confidence: med

### V68-C.3 · case_002a APU bay metadata entry
- Append case_002a entry to whitelist.yaml (or imported corpus structure) with `case_kind=imported_user` + `gold_pending=true`
- Backend listable via `/api/cases` (validates the V68-B real-serving still works for new entries)
- Frontend Index page shows disclaimer ⏳
- LOC est: ~40 config + 60 test
- Confidence: med (corpus integration · risk: existing tests may expect 10-count whitelist)

### V68-C.4 · E2E + V68-D iter-2 spike + close
- 4 new playwright cases (physics endpoint render · ai-review smoke · ai-diagnose smoke · case_002a listing)
- V68-D iter-2 spike: extend WASM feasibility doc with docker-based emsdk findings + dep stub triage
- Close DEC + Pillar 6 + Pillar 7 anchor updates
- LOC est: ~120 test + 0 LOC code (spike still research-only)
- Confidence: med

## 6 · 7-agent fleet (v68c_fleet/ clone with further tightened criteria)

| # | Agent | V68-B criteria | V68-C criteria (further tightened) |
|---|---|---|---|
| 1 Code Quality | binary 100 | (unchanged) |
| 2 Physics | mass_balance+corpus+bc_routes | **+ whitelist count assertion** (10 → 11 with case_002a) |
| 3 UX/Playability | ≥7 specs PASS | **≥9 specs PASS** for FULL flow=60 |
| 4 Visualization | ≥4 viewport-mode + ≥12 PNG | **≥4 viewport-mode + ≥16 PNG** (adds 4 V68-C states) |
| 5 Smoke | + backend HTTP /api/cases probe | **+ /api/cases/:id/physics + /ai-review + /ai-diagnose probes** (3 new endpoints) |
| 6 Functional | 4/4 LANDED + 7/7 Done | **4/4 LANDED (V68-D spike doesn't count) + 7/7 Done** |
| 7 Stability | vitest flake | (unchanged) |

## 7 · Iteration loop (mandatory · same as V67-C / V68-A / V68-B pattern)

Identical iteration loop. Reverse-stop triggers unchanged. **V68-C is 4th application of V110 advisor-class pattern · stability now thoroughly evidenced.**

## 8 · v2.3 governance compliance

- DEC scope: charter (cross ≥3 paths: backend tests + frontend MaterialCard + ProposalCard + whitelist YAML + fleet scripts)
- Codex 1-sync-trigger: NOT applicable (no auth/signing/security boundary)
- Kogami opt-in: NOT invoked
- Confidence: high (charter · 3 prior arcs validate pattern · scope verified · backend routes pre-existing)
- Counter: B139 autonomous_governance=true · +1
- **Spike-class clause**: V68-D continued spike inside V68-C.4 follows v2.3 round-1 (no DEC · ≤30 LOC code change · 1 research doc extension · commit message confidence trailer)

## 9 · 4Q gate baseline answers

| Q | A | Justification |
|---|---|---|
| LLM offline · workbench full pipeline | ✓ YES | LLM-offline fallback is explicit Done dim #4 · AI hooks return graceful state when backend returns 5xx · UI doesn't crash |
| Artifacts produced | ✓ YES | usePhysicsState + AI hook code + LLM-offline fallback tests + case_002a entry + iter-2 spike + 4 sub-DECs + iter scores |
| TrustGate / completeness / audit trail | ✓ YES | useCaseStatus path unchanged (V68-B SSOT preserved) · MaterialCard + ProposalCard are advisory surfaces that don't mutate audit verdict |
| AI advisory-only · no mutating route | ✓ YES | V132 MUTATING_ROUTES baseline still 9 · all new wiring is GET-only · audit re-runs each iter |

## 10 · Out of scope (explicit non-goals)

- **NOT** authoring case_002a gold standard (V68-E.2 follow-on · multi-day · charter §1 explicit)
- **NOT** OpenFOAM-WASM compile attempt (V68-D research-only · continued spike)
- **NOT** new LLM dependencies (AI routes use existing backend logic · no new model integration)
- **NOT** rewriting V67-C/V68-A/V68-B prior surfaces (additive only)
- **NOT** touching V132 MUTATING_ROUTES (locked)
- **NOT** Pillar 1-5 advances (Pillar 6+7 only)

## 11 · Predicted trajectory

- iter 0 (post-charter baseline): functional drops to 0 (new criteria: 0/4 V68-C sub-DECs LANDED · 0/7 V68-C Done dims · visualization may drop if PNG count <16 with new threshold)
- iter 1 (V68-C.1 MaterialCard): functional partial · 1/4 + 1-2/7
- iter 2-4: sub-DECs land incrementally
- iter 5+: ≥99 for 2 consecutive · close ratified

V68-C may temporarily REGRESS in iter 0 because criteria tighten. Honest pattern continues.

## 12 · Failure modes to flag

If any below trigger during execution, **surface to user immediately**:
- physics route 404s when `case_dir` doesn't exist (might affect whitelist cases that aren't imported)
- ai-review or ai-diagnose route returns unexpected shape (V61 era integration · may need adapter)
- case_002a corpus integration breaks existing 10-case whitelist tests
- pixel-diff 0.01 threshold causes existing baselines to fail on rerun (font rendering drift)
- V68-D iter-2 spike reveals catastrophic blocker (e.g. docker daemon broken)

— Claude Code (Opus 4.7 1M) · B139 · V68-C charter · 2026-05-16

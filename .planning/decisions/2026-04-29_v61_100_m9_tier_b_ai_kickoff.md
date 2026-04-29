---
decision_id: DEC-V61-100
title: M9 Tier-B AI kickoff — productized pick→annotate→re-run loop + arbitrary-STL classifier roadmap [Era 1 LOOP SPINE first milestone under workbench long-horizon roadmap]
status: Accepted (2026-04-30 · gating swap to Claude-Code-automated-smoke per CFDJerry workflow directive 2026-04-30) · Step 1 IMPLEMENTED at commit aa4d3f1 (Codex APPROVE_WITH_COMMENTS) · Step 2 IMPLEMENTED at commit 11b81ba (Codex 3-round arc R3 APPROVE) · Step 3 IMPLEMENTED at commits faa2e08 + a54f4b7 + 6ae9a3b (Codex 3-round arc R3 APPROVE) · scripts/smoke/dogfood_loop.py exit 0 covering all three steps including multi-q non-cube path
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-29
authored_under: workbench_long_horizon_roadmap_2026-04-29.md (Era 1 LOOP SPINE M9 row · "Tier-B AI · face-pick selection + AI BC inference iteration") + DEC-V61-098 (M-AI-COPILOT Tier-A · Tier-B explicit deferral row in §F)
parent_decisions:
  - DEC-V61-098 (M-AI-COPILOT Tier-A · binding parent — Tier-B was explicitly deferred from §F failure-modes table; Tier-A surface 7-round Codex arc all closed at commit 0abdd74)
  - DEC-V61-099 (post-R3 staging fix · the live-run defect that proved Tier-A was production-ready · closed at 7a15833)
  - DEC-V61-093 (Pivot Charter Addendum 3 · §4.c HARD ORDERING — M9 sits AFTER M-AI-COPILOT Tier-A in the dogfood window · this DEC respects that ordering)
  - DEC-V61-087 (v6.2 three-layer governance · NOT modified · Kogami trigger evaluation deferred to Step 2 backend kickoff)
  - RETRO-V61-001 (risk-tier triggers · multi-file frontend + UX-driven impl trigger pre-merge Codex per ≤70% self-pass-rate gate)
parent_artifacts:
  - .planning/strategic/workbench_long_horizon_roadmap_2026-04-29.md (Era 1 LOOP SPINE M9 row · roadmap commit 972fc4f)
  - .planning/dogfood/M_AI_COPILOT_v0.md (Tier-A dogfood guide · "Next milestone after closure" section names M9 explicitly)
  - reports/codex_tool_reports/dec_v61_100_m9_step1_round1.md (Codex APPROVE_WITH_COMMENTS on Step 1 · 2 non-blocker observations flagged for Step 2 hardening)

# Tier-A→Tier-B continuity
The four interaction primitives, dialog-first UX, and persistent annotations from DEC-V61-098 Tier-A are the substrate. M9 Tier-B does NOT modify the contract — it replaces the dogfood-only `force_uncertain` mock with a real classifier and lets the loop iterate until confident.

implementation_paths_step_1:
  - ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx (MODIFIED · envelope-mode opt-in via `?ai_mode=force_uncertain | force_blocked`; DialogPanel rendering; resume handler that PUTs face_annotations + re-runs envelope · landed at aa4d3f1)
  - ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx (4 new envelope-mode tests · 6 total)

implementation_paths_step_2_pending:
  - ui/backend/services/ai_actions/classifier/ (NEW package · arbitrary-STL geometric classifier · replaces the force_uncertain mock with real heuristics)
  - ui/backend/services/case_annotations/ (POSSIBLE EXTENSION · classifier may need helper utilities for face_id-based reasoning)
  - ui/backend/services/ai_actions/__init__.py (MODIFIED · setup_bc_with_annotations consults classifier when `force_uncertain` is unset; emits real UnresolvedQuestion list)
  - ui/backend/schemas/ai_action.py (POSSIBLE EXTENSION · richer Question metadata if classifier needs e.g. confidence-per-face scoring)
  - ui/backend/tests/test_ai_classifier.py (NEW · contract tests for the classifier — given fixture mesh, returns expected envelope shape)

read_paths:
  - reports/codex_tool_reports/dec_v61_098_*.md (Tier-A 7-round audit trail · informs Codex risk-tier expectations)
  - .planning/dogfood/M_AI_COPILOT_v0.md (Tier-A dogfood guide · the smoke runbook this milestone extends)

prerequisite_status:
  v61_098_acceptance: Implementation Complete · Awaiting CFDJerry visual smoke (per dogfood guide) — Tier-B Step 1 builds ON TOP of Tier-A's 8 commits (d06d41d..0abdd74) which are pushed to origin and Codex-verified across 7 rounds. M9 Step 1 (this DEC) was CLASS-1 docs-only-OUTPUT-equivalent (frontend wiring of already-shipped backend); no new contract, no new persistent state. Step 2 will require V61-098 Accepted before backend changes (Kogami trigger evaluation may apply).
  break_freeze_quota: Tier-A consumes the FINAL §11.1 BREAK_FREEZE slot (3/3) per V61-098 frontmatter. M9 Step 1 lands UNDER the same quota slot since it's a layered extension of the Tier-A surface; no new quota required. M9 Step 2 (backend classifier) routes through normal feature freeze (post-Tier-A-Acceptance).

notion_sync_status: pending (will sync after Step 1 review fully closed + Step 2 plan firms up)
autonomous_governance: true

codex_tool_report_path:
  step_1_round_1: reports/codex_tool_reports/dec_v61_100_m9_step1_round1.md (APPROVE_WITH_COMMENTS · 2026-04-29 commit aa4d3f1 · no blocking findings · 127/127 frontend pass · 2 non-blocker observations flagged for Step 2 hardening)
  step_2_round_1: reports/codex_tool_reports/dec_v61_100_m9_step2_round1.md (CHANGES_REQUIRED · 2026-04-29 · 2 HIGH findings — cube returned confident on any user_authoritative pin · non-cube returned confident with no executor able to honor it)
  step_2_round_2: reports/codex_tool_reports/dec_v61_100_m9_step2_round2.md (CHANGES_REQUIRED · 2026-04-29 · 1 HIGH — lid-named pin off top plane was silently overridden by setup_ldc_bc · narrow R1 fix wasn't honest at the executor level)
  step_2_round_3: reports/codex_tool_reports/dec_v61_100_m9_step2_round3.md (APPROVE · 2026-04-29 commit 11b81ba · _top_plane_face_ids() helper mirrors setup_ldc_bc's lid detection exactly · classifier-executor parity verified · borderline tolerance probe matches · full loop closure proven · 34/34 in slice)
  step_3_round_1: reports/codex_tool_reports/dec_v61_100_step3_r1.md (CHANGES_REQUIRED · 2026-04-29 commit faa2e08 · 1 MED ai_mode-flip race + 1 LOW bare-pick leak into AnnotationPanel)
  step_3_round_2: reports/codex_tool_reports/dec_v61_100_step3_r2.md (CHANGES_REQUIRED · 2026-04-29 commit a54f4b7 · LOW resolved · MED partially-closed — confident-path branch reachable after nested getFaceAnnotations() await)
  step_3_round_3: reports/codex_tool_reports/dec_v61_100_step3_r3.md (APPROVE · 2026-04-29 commit 6ae9a3b · ≤6 LOC verbatim fix · isStale() re-check at confident-path · M9 Step 3 ready to merge)
codex_review_required: true
codex_review_phase: pre-merge (per RETRO-V61-001 · multi-file frontend + UX flow change triggers)
codex_triggers:
  - 多文件前端改动 (Step 1: Step3SetupBC + tests · Step 2 will likely add backend services touching ≥3 files)
  - UI 交互模式变更 (Step 1: new dialog round-trip path activated by URL param; Step 2: real classifier may surface multi-question scenarios that exercise additional UX states)
  - API 契约变更 + adapter boundary (Step 2: ai_actions wrapper extension may shift envelope shape — Codex review essential)
  - ≤70% self-pass-rate (Step 2 self-estimated 50% — first real classifier always discovers issues)

kogami_review:
  step_1_required: false (frontend-only · single-file substantive change · Codex APPROVE_WITH_COMMENTS sufficient · Tier-A's Kogami evaluation already passed at V61-098)
  step_2_required: TBD (backend classifier with new heuristics → if it changes risk-tier or introduces autonomous_governance rule shifts → Kogami trigger applies; otherwise inherits V61-098's "no Kogami required" finding)

---

## §A · Why M9 Tier-B is the right next milestone

Per the long-horizon roadmap (commit 972fc4f), Era 1 LOOP SPINE has 6 milestones (M9-M14). M9 was named explicitly as **"Tier-B AI · face-pick selection + AI BC inference iteration"**. The roadmap framing positioned this as the milestone that productizes the pick→annotate→re-run loop into a complete iteration, not just a one-shot.

DEC-V61-098 Tier-A delivered the foundation:
- face_annotations.yaml persistent storage
- face_id stable hash
- AIActionEnvelope schema
- Backend `force_uncertain`/`force_blocked` flags for dogfood
- Frontend DialogPanel + AnnotationPanel + FacePickContext
- Step3SetupBC face-pick → AnnotationPanel save flow

M9 Tier-B closes the loop: the dialog substrate becomes real (not a mock), and engineers iterate with the AI until confident.

## §B · M9 Step 1 (LANDED at aa4d3f1)

**Scope**: Wire the existing DialogPanel into `[AI 处理]` envelope round-trip. Activate via `?ai_mode=force_uncertain` URL param.

**What works now**:
- Engineer navigates to `/workbench/<case-id>?step=3&ai_mode=force_uncertain`
- An "AI-COPILOT envelope mode" amber banner appears at the top of the right rail
- Click `[AI 处理]` → backend returns uncertain envelope with mock lid_orientation question
- DialogPanel renders below with the question
- Engineer clicks the lid face in the 3D viewport → pick routes to the lid_orientation question (NOT the AnnotationPanel)
- Click `[继续 AI 处理]` → backend `PUT /face-annotations` with the picked face_id (annotated_by='human', confidence='user_authoritative') → re-run envelope → returns confident → step completes

**What's still mocked**:
- `force_uncertain` query param. The backend always returns the same hardcoded `lid_orientation` question regardless of the actual mesh.

**Codex verdict**: APPROVE_WITH_COMMENTS. Two non-blocker observations:
1. Single-active-question pick routing is intentionally lossy under rapid double-picks (acceptable for force_uncertain dogfood; harden when classifier emits multi-question scenarios)
2. Stale envelope state on mid-session ai_mode toggle is a UX oddity, not a correctness problem

## §C · M9 Step 2 (PENDING — backend classifier)

The real arbitrary-STL classifier replaces `force_uncertain`. Open design questions:

| Question | Tentative answer |
|---|---|
| Where does the classifier live? | `ui/backend/services/ai_actions/classifier/` — new package, sibling to `ai_actions/__init__.py` |
| What's the classification surface? | `classify_setup_bc(case_dir, annotations) → AIActionEnvelope` |
| What heuristics? | Mesh-based: detect cube → confident LDC defaults · detect non-cube → uncertain (ask for inlet/outlet labels) · detect non-watertight → blocked. Additional heuristics: aspect ratio, principal axis alignment, face count distribution. |
| LLM-driven later? | Out of scope for Step 2. Step 3 (or M14 auto V&V) can integrate an LLM classifier on top of the geometric heuristics. |
| How does annotations.yaml feed back? | Classifier reads existing user_authoritative entries first; if all required questions are pinned, returns confident immediately. |

## §D · Step ordering

| Step | What | Status |
|---|---|---|
| 1 | Frontend envelope-mode wiring + DialogPanel integration | DONE (aa4d3f1, Codex APPROVE_WITH_COMMENTS) |
| 2 | Backend classifier (heuristic-only, no LLM) + replace force_uncertain default with real classification | PENDING — likely 5-8 commits, Codex pre-merge mandatory |
| 3 | Multi-question scenario hardening (lid + inlet + outlet at once) + pick-routing improvements per Codex Step 1 comments | PENDING — depends on Step 2 surfacing real multi-question payloads |
| 4 | Dogfood smoke + DEC closure | PENDING — CFDJerry validates with 2-3 real geometries |

## §E · Failure modes (what Step 2 Codex will key on)

| Class | Mode | Mitigation |
|---|---|---|
| Classifier correctness | Heuristics misclassify a valid LDC cube as non-cube → blocks the dogfood path | Regression test: every existing LDC fixture must classify confident |
| Determinism | Non-deterministic classifier output across runs | Pure function of (mesh + annotations); no random seeds |
| Annotations feedback | Classifier ignores user_authoritative entries → infinite loop of "asking the same question" | Classifier MUST read annotations and treat user_authoritative as locked |
| API surface | Backend changes envelope shape and breaks Tier-A frontend | Pin existing AIActionEnvelope shape; only ADD optional fields if needed |

## §F · §11.1 BREAK_FREEZE accounting

DEC-V61-098 §F frontmatter consumed slot 3/3 of the §11.1 BREAK_FREEZE quota. M9 Tier-B Step 1 (aa4d3f1) is layered on top of that surface — no new persistent state, no new API contracts, no new components. Per the §11.1 advisory hook output that ran on commit aa4d3f1 ("§11.1 Workbench feature freeze · advisory ... Passed"), this commit was accepted as a within-quota extension.

M9 Step 2 (backend classifier) will introduce new persistent state (classifier package) and may shift the envelope contract. That goes through normal feature freeze evaluation; this DEC documents the routing intent so Step 2 doesn't surprise the freeze hook.

## §G · Self-pass-rate estimate

| Step | Self-estimate | Codex result |
|---|---|---|
| 1 | 80% | APPROVE_WITH_COMMENTS (matched — 2 non-blocker observations is exactly the band you'd expect for 80% confidence) |
| 2 | 50% | TBD — first real classifier always discovers issues; pre-merge Codex mandatory per RETRO-V61-001 ≤70% gate |

## §H · Notion sync plan

Sync this DEC after Step 1 review fully closed (already done — APPROVE_WITH_COMMENTS, no R2 needed). Step 2 will get its own Notion sync after closure. Cadence per project rule: every DEC syncs immediately after landing; this DEC syncs once Step 2 plan is firmer.

---
decision_id: DEC-V61-101
title: Minimal laminar channel executor — closes M9 dialog→annotate→re-run loop on the FIRST non-LDC geometry
status: Accepted (2026-04-30 · gating swap to Claude-Code-automated-smoke per CFDJerry workflow directive 2026-04-30) · Step 1 (executor + classifier extension + wrapper dispatch) IMPLEMENTED at commits b7986ba + e470618 + 44d1716 (Codex 2-round arc R2 APPROVE) · scripts/smoke/dogfood_loop.py §4c channel full loop exit 0
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-29
authored_under: workbench_long_horizon_roadmap_2026-04-29.md (Era 1 LOOP SPINE — between M9 Tier-B AI and M11 Mesh Wizard / M12 multi-solver) · DEC-V61-100 M9 Step 3 dogfood guide §4c "channel-executor pending M11/M12" gap line
parent_decisions:
  - DEC-V61-100 (M9 Tier-B AI · multi-q non-cube classifier landed at 11b81ba; THIS DEC closes the executor side of that loop · without it, the engineer pins inlet+outlet for nothing — annotations save but no dicts written)
  - DEC-V61-098 (M-AI-COPILOT Tier-A · face_annotations.yaml + face_id contract that the channel patch splitter consumes)
  - DEC-V61-093 (Pivot Charter Addendum 3 · §4.c HARD ORDERING — this DEC sits AFTER M9 in the dogfood window, layered as a small unblocker rather than a milestone of its own)
  - RETRO-V61-001 (risk-tier triggers · multi-file backend + new executor + ≤70% self-pass-rate triggers pre-merge Codex)
  - RETRO-V61-053 (executable_smoke_test mandate · this DEC requires a route-layer E2E test analogous to dec_v61_100_step3_e2e_r1)
parent_artifacts:
  - .planning/strategic/workbench_long_horizon_roadmap_2026-04-29.md (M11/M12 sit downstream · this DEC is a bounded laminar slice that doesn't pre-empt either)
  - .planning/dogfood/M_AI_COPILOT_v0.md §4c (channel multi-q smoke runbook · expected to upgrade from "blocked" to "confident · dicts written")

# Why now
M9 Tier-B AI's classifier emits inlet+outlet questions for non-cube geometries (channel, pipe, duct). The engineer pins faces, the dialog re-runs, and the classifier returns BLOCKED with "non-LDC executor pending". That's a dead-end UX: the engineer's pins are saved but no simulation is possible.

A minimal laminar (icoFoam) channel executor changes the BLOCKED to CONFIDENT for the simplest non-LDC geometry — straight ducts at low-Re. This is a bounded slice of M11/M12: no turbulence model, no BL prism control, no mesh wizard. Just patch splitting from face_ids + sensible default BCs.

# Scope (Step 1)
implementation_paths:
  - ui/backend/services/case_solve/bc_setup.py (MODIFIED · adds setup_channel_bc(case_dir, *, case_id, inlet_face_ids, outlet_face_ids) → BCSetupResult; uses face_id() to map pinned face_ids to boundary indices, reorders polyMesh/faces+owner+boundary into 3 patches inlet/outlet/walls, writes 7 icoFoam dicts with channel BCs)
  - ui/backend/services/ai_actions/classifier/__init__.py (MODIFIED · classify_setup_bc on non_cube WITH inlet+outlet pinned: replace blocked-with-pending message with confident result · ClassificationResult adds optional inlet_face_ids/outlet_face_ids for the wrapper to forward · add geometric verification helper analogous to _top_plane_face_ids that confirms the pinned face_ids actually exist on the boundary)
  - ui/backend/services/ai_actions/__init__.py (MODIFIED · setup_bc_with_annotations confident path branches on cls.geometry_class: ldc_cube→setup_ldc_bc, non_cube→setup_channel_bc; resolves inlet/outlet face_ids from cls.inlet_face_ids/outlet_face_ids)
  - ui/backend/tests/test_setup_channel_bc.py (NEW · unit tests for patch splitting + dict writing on the 1×1×10 channel fixture from test_ai_classifier)
  - ui/backend/tests/test_ai_classifier.py (MODIFIED · add test_classifier_channel_with_pinned_inlet_outlet_returns_confident; replaces the existing blocked-when-pinned test with the new confident-when-pinned behavior)
  - ui/backend/tests/test_setup_bc_envelope_route.py (MODIFIED · add route-layer E2E test analogous to dec_v61_100_step3_e2e: channel mesh → POST envelope=1 → uncertain → PUT inlet+outlet pins → POST envelope=1 → confident · dicts on disk)
  - .planning/dogfood/M_AI_COPILOT_v0.md (MODIFIED · §4c upgrade — channel path now expected to return confident · executor writes inlet/outlet/walls dicts)

read_paths:
  - ui/backend/services/case_solve/bc_setup.py:_split_lid_walls (the LDC patch-splitter is the structural template · channel splitter follows the same shape but routes by face_id instead of plane test)
  - ui/backend/services/case_annotations/__init__.py:face_id (face_id stable hash · channel splitter computes face_id for each boundary face and matches against pinned set)
  - reports/codex_tool_reports/dec_v61_100_m9_step2_round3.md (Codex M9 R3 APPROVE · classifier-executor parity precedent · this DEC must maintain the same parity discipline: if the classifier verified the pin geometrically, the executor MUST honor it; if the executor changes, the classifier verification must update to match)

# Out of scope (preserved for downstream milestones)
- Turbulence models (M12 — k-ω SST, k-ε, Spalart-Allmaras)
- Boundary layer prism control (M11 Mesh Wizard)
- Mesh refinement zones (M11)
- Compressible flow (rhoSimpleFoam) (M12)
- Heat transfer / buoyancy (M12)
- BC value editing UI (engineer cannot yet override default U_inlet=(1,0,0), p_outlet=0, ν=0.01)
- Multi-inlet / multi-outlet (only ONE inlet + ONE outlet supported per dialog)
- Curved/elbow ducts (the patch splitter reorders by face_id list — works on any topology — BUT untested beyond straight 1×1×10 channel; add fixtures in a separate DEC if engineer reports issues)

# Default BCs (locked in this DEC)
- inlet: U=fixedValue (1 0 0) m/s · p=zeroGradient
- outlet: U=zeroGradient · p=fixedValue 0 Pa
- walls: U=noSlip · p=zeroGradient
- ν: 0.01 m²/s (laminar regime; for 1×1×10 channel, Re=U·D/ν=1·1/0.01=100 — well below transition)
- Solver: icoFoam (PISO transient laminar incompressible · same as LDC)

These are LOCKED defaults for now. Engineer can post-edit dicts manually; UI to override surfaces in M12.

# Geometric verification rule (classifier↔executor parity)
**Classifier returns confident only if** (in this order):
1. geometry_class == non_cube (aspect ratio fails LDC-cube test)
2. ≥1 face with `name~='inlet'` AND `confidence='user_authoritative'` is in face_annotations.yaml
3. ≥1 face with `name~='outlet'` AND `confidence='user_authoritative'` is in face_annotations.yaml
4. The inlet face_id(s) appear on the polyMesh boundary (resolved via face_id() over boundary face vertices)
5. The outlet face_id(s) appear on the polyMesh boundary
6. Inlet and outlet face_id sets are disjoint (engineer can't pick the same face for both)

**Executor (setup_channel_bc) MUST honor** the pinned face_id set exactly. No silent override (the lesson from Codex M9 Step 2 R2 — name-based heuristics that don't match face_id verification cause silent overrides).

prerequisite_status:
  v61_098_acceptance: Implementation Complete · Awaiting CFDJerry visual smoke (face_id contract is the foundation here)
  v61_100_acceptance: Implementation Complete · Awaiting CFDJerry visual smoke on multi-q channel path (this DEC upgrades the §4c smoke from "blocked" to "confident · dicts written")
  break_freeze_quota: NOT consumed — V61-098 used the final §11.1 BREAK_FREEZE slot. This DEC routes through the normal feature-freeze process per §11.1 §H.

notion_sync_status: pending (Codex APPROVE'd at R2 commit 44d1716; awaiting next Notion-MCP-online window for sync)
codex_tool_report_path:
  step_1_round_1: reports/codex_tool_reports/dec_v61_101_step1_r1.md (CHANGES_REQUIRED · 2026-04-30 commit b7986ba · 1 HIGH partial-stale-pin acceptance + 1 MED channel-error HTTP mapping + 1 LOW Re calculation)
  step_1_round_2: reports/codex_tool_reports/dec_v61_101_step1_r2.md (APPROVE · 2026-04-30 commit e470618 · 0 findings · 34/34 in classifier+route slice · Re≈100 verified · HTTP precedence preserved)
autonomous_governance: true

codex_review_required: true
codex_review_phase: pre-merge (per RETRO-V61-001 · multi-file backend + new executor + ≤70% self-pass-rate)
codex_triggers:
  - 多文件 backend 改动 (3 production files + 3 test files)
  - 新 executor (setup_channel_bc · BC values + dict structure must be physically sensible)
  - byte-reproducibility-sensitive (face_id consumption · same risk as V61-098 per RETRO-V61-001 third bullet)
  - ≤70% self-pass-rate (50% — first-time channel patch splitting · BC defaults untested on real engineering geometries)

kogami_review:
  step_1_required: false (backend executor following established M-AI-COPILOT contract · no new strategic surface · no autonomous_governance rule changes · DEC-V61-087 §4.2 docs-only-output-equivalent exception applies — Codex APPROVE sufficient)

external_gate_self_estimated_pass_rate: 50

# Counter accounting
- counter +1 (autonomous_governance: true)
- Codex per-risky-PR: required pre-merge
- Kogami: not triggered

# Acceptance for §E DEC closure (Claude-Code-automated smoke)
DEC flips to `Accepted` when scripts/smoke/dogfood_loop.py exits 0:
- [x] §4a LDC cube full loop (uncertain → pin lid → confident · dicts written)
- [x] §4c channel full loop (uncertain → pin inlet+outlet → confident · 3-patch split + channel BC dicts)
- [x] §7 negative paths (lid-on-side stays uncertain · bogus pins → channel_pin_mismatch question)
- [x] Frontend Vite dev server boot probe (200 OK · HTML hydrated)
- [x] Backend test slice green (test_ai_classifier + test_setup_bc_envelope_route)
- [x] LDC backwards-compat preserved (existing tests green)

The previous "CFDJerry ratification" gate is removed per the
2026-04-30 workflow directive: human-driven visual smoke is no
longer part of the automated dev workflow because CFDJerry can't
be agent-triggered. Visual checks engineers may still want to do
manually (vtk.js GLTF rendering, emerald active-slot glow,
cross-tab 409 UX) are documented in the dogfood guide as
"human-only" notes but not as DEC gates.

---
decision_id: DEC-V61-095
title: M-RENDER-API kickoff — backend geometry / mesh / field render endpoints (trimesh.export · glTF binary · second milestone under Pivot Charter Addendum 3)
status: Accepted (2026-04-28 · CLASS-1 docs-only governance kickoff per V61-086/089/093/094 precedent · Codex SKIPPED · Kogami NOT triggered per V61-094 P2 #1 bounding clause [4-condition self-check passed: no charter mod · no line-A extension beyond M-VIZ · counter <20 since RETRO-V61-005 · no risk-tier change] · CFDJerry explicit ratification 2026-04-28)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-28
authored_under: Pivot Charter Addendum 3 §4.a + §4.c HARD ORDERING (DEC-V61-093 Accepted 2026-04-28)
parent_decisions:
  - DEC-V61-093 (Pivot Charter Addendum 3 ratification · binding parent — §4.a M-RENDER-API endpoint surface · §4.c HARD ORDERING)
  - DEC-V61-094 (M-VIZ kickoff · ratifying parent precedent — closed 2026-04-28 commit 36c4a78 · framing inherited per M-VIZ Kogami review P2 #1 bounding clause)
  - DEC-V61-087 (v6.2 three-layer governance · NOT modified)
  - DEC-V61-088 (pre-implementation surface scan · routine startup discipline)
  - DEC-V61-089 (two-track invariant · render endpoints serve both tracks)
  - DEC-V61-091 (M5.1 verdict cap · cap remains dormant; M7-redefined wires it)
  - DEC-V61-092 (workbench nav-discoverability · unchanged)
  - RETRO-V61-001 (risk-tier triggers · multi-file backend + new routes + adapter-boundary near rendering pipeline trigger Codex)
parent_artifacts:
  - docs/governance/PIVOT_CHARTER_ADDENDUM_3_2026-04-28.md (charter binding · §4.a + §4.c)
  - .planning/strategic/m_render_api_kickoff/brief_2026-04-28.md (one-pager)
  - .planning/strategic/m_render_api_kickoff/spec_v2_2026-04-28.md (tier-split spec)
  - .planning/ROADMAP.md (Line-A/Line-B isolation contract — anticipatory line-A paths already declared in commit 8fdb0a3 PRE-M-VIZ; M-RENDER-API needs no further extension)
  - ui/backend/routes/geometry_render.py (existing M-VIZ Tier-A · M-RENDER-API extends this module with B.1 endpoint)
  - ui/backend/services/case_scaffold/ (M5.0 case_dir source)
  - ui/backend/services/meshing_gmsh/ (M6.0 polyMesh source for B.2)
  - reports/phase5_fields/ (run-history field source for B.3)
  - examples/imports/{ldc_box,cylinder,naca0012}.stl (M-VIZ-shared smoke fixtures)
prerequisite_status:
  v61_094_acceptance: confirmed (M-VIZ closed 2026-04-28 · commit 36c4a78 · Step-7 visual smoke PASSED · Codex APPROVE_WITH_COMMENTS at round 5 + verbatim halt)
  v61_093_acceptance: confirmed (Pivot Charter Addendum 3 §4.a + §4.c binding)
  line_a_contract: confirmed (anticipatory ui/backend/services/render/** + ui/backend/routes/geometry_render.py declared line-A in commit 8fdb0a3 · 2026-04-28 PRE-M-VIZ. NO further ROADMAP extension needed for M-RENDER-API.)
  m6_0_acceptance: confirmed (gmsh + sHM pipeline outputs polyMesh under <case_dir>/constant/polyMesh/)
  m5_1_acceptance: confirmed (cap dormant; M7-redefined wires it. M-RENDER-API field endpoint reads from completed-run output directories regardless of cap state.)
  workbench_extra_dep: confirmed (trimesh already a [workbench] dep · M5.0 ingest depends on it · zero new dependencies needed for Tier-A)
notion_sync_status: pending (sync after CFDJerry Acceptance · DEC + brief + spec_v2 paired per V61-094 §Sync precedent)
autonomous_governance: true
library_choice: trimesh.export (working assumption · subject to ratification override before Status=Accepted)
codex_tool_report_path: pending (per-implementation-arc Codex fires on Step 8 of spec_v2 §Sequence)
codex_review_required: true
codex_triggers:
  - 多文件后端改动 (3 new routes + new services/render/ module + extension to existing geometry_render.py)
  - API 契约变更 / adapter boundary (3 new endpoint surfaces)
  - 新几何/数据格式生成 (STL → glTF, polyMesh → wireframe glTF, field → glTF-accessor or binary-stream)
  - 用户 UX 批评后的首次实现 (Pivot Charter Addendum 3 §4.a binding constraint this milestone delivers)
kogami_review:
  required: false
  rationale: |
    Per V61-094 Kogami review P2 #1 bounding clause (Accepted
    2026-04-28): "M-RENDER-API / M-PANELS / M-AI-COPILOT inherit
    M-VIZ's framing precedent and do NOT re-fire Kogami unless they
    independently meet a Must-trigger condition (charter modification ·
    line-A contract extension beyond M-VIZ's claim · counter ≥20 ·
    explicit risk-tier change)."

    Self-check:
      - Charter modification? NO. Inherits Addendum 3 §4.a + §4.c.
      - Line-A contract extension beyond M-VIZ? NO. Anticipatory paths
        ui/backend/services/render/** declared in 8fdb0a3 PRE-M-VIZ
        already cover M-RENDER-API's surface.
      - Counter ≥20 since RETRO-V61-005 close? NO. Currently +8..9.
      - Explicit risk-tier change? NO. Backend-only adapter-boundary
        change · medium risk per spec_v2.

    All four bounding-clause conditions return NO → Kogami NOT
    triggered. Strategic-layer review NOT required for this kickoff.
    Codex code-layer review remains mandatory per RETRO-V61-001.
---

# DEC-V61-095 · M-RENDER-API kickoff — backend geometry / mesh / field render endpoints

## Why

Pivot Charter Addendum 3 §4.a (Accepted 2026-04-28 via DEC-V61-093)
defines the M-RENDER-API endpoint surface. §4.c HARD ORDERING places
M-RENDER-API immediately after M-VIZ, before M-PANELS / M-AI-COPILOT.

M-VIZ Tier-A (DEC-V61-094) shipped a single anticipatory STL-serve
endpoint to feed the Viewport. M-RENDER-API expands the surface to the
full set of render-data endpoints the forthcoming step-panel UI needs:

- `/geometry/render` — STL + future formats → browser-friendly glTF
- `/mesh/render` — polyMesh → wireframe glTF (the M-PANELS Step-3
  "Mesh" surface)
- `/results/<run>/field/<name>` — sampled scalar field (the M-PANELS
  Step-5 "Results" surface)

Without M-RENDER-API ratified, M-PANELS would have to either invent
its own backend endpoints (violating Addendum 3 §4.a's binding
contract) or stall. M-RENDER-API is the data-surface gate.

This DEC is the kickoff plan. It does not implement the milestone; it
ratifies the implementation plan + scope + library choice. After
ratification, implementation work begins per spec_v2 §Sequence.

## Pre-implementation surface scan (per DEC-V61-088)

Performed 2026-04-28 before authoring this DEC:

1. **ROADMAP scan**: Pivot Charter Addendum 3 §4.a lists M-RENDER-API
   as the second milestone after M-VIZ. No prior milestone covers
   render-data endpoints beyond M-VIZ Tier-A's STL-serve.

2. **Existing-implementation grep**:
   - `ui/backend/routes/geometry_render.py` — exists from M-VIZ Step 3
     (commit b4074c5 + R1 fix 4811c27). Already line-A. M-RENDER-API
     extends this module with B.1 endpoint.
   - `ui/backend/services/render/` — directory does NOT yet exist;
     anticipatory line-A path declared in ROADMAP commit 8fdb0a3 still
     unconsumed.
   - `/api/cases/<id>/geometry/render` route — does not exist.
   - `/api/cases/<id>/mesh/render` route — does not exist.
   - `/api/cases/<id>/results/<run>/field/<name>` route — does not exist.
   - `trimesh.export(file_type='glb')` — verified 2026-04-28 returns
     valid binary glb (header magic `b'glTF'`, 12-tri cube → 960
     bytes). trimesh is in [workbench] extra; no new dep needed.

3. **§11.1 workbench-freeze scope check**:
   - Patterns from `tools/methodology_guards/workbench_freeze.sh`:
     `ui/backend/services/workbench_*` · `ui/frontend/pages/workbench/*`
     · `ui/frontend/src/pages/workbench/*`.
   - This DEC's planned paths:
     - `ui/backend/routes/geometry_render.py` (extension of existing
       NEW path · NOT in freeze)
     - `ui/backend/services/render/**` (NEW · line-A · NOT in freeze)
     - `ui/frontend/src/visualization/glb_loader.ts` (NEW · line-A ·
       NOT in freeze)
     - `ui/frontend/src/visualization/Viewport.tsx` modification
       (existing line-A path · NOT in freeze)
     - `ui/frontend/src/visualization/viewport_kernel.ts` modification
       (existing line-A path · NOT in freeze)
   - **NO BREAK_FREEZE escape needed for M-RENDER-API.** ImportPage.tsx
     is NOT touched in Tier-A.
   - §11.1 escape-hatch 30-day quota: count remains 1 (from M-VIZ Step
     6 commit e453ba0 BREAK_FREEZE on ImportPage.tsx). Well under the
     ≥3 retro trigger.

## Scope

### In scope · this DEC ratifies (planning + library choice)

1. **Library choice**: trimesh.export (working assumption ratified by
   CFDJerry; subject to override window before Status=Accepted).
   Already in [workbench] extra → zero new dependencies.

2. **Tier-A MVP scope** (per spec_v2 §Tier A):
   - 3 backend endpoints: `/geometry/render` (B.1) + `/mesh/render`
     (B.2) + `/results/<run>/field/<name>` (B.3)
   - Cache layer at `<case_dir>/.render_cache/` with mtime invalidation
   - Frontend Viewport `format` prop + `glb_loader.ts`
   - Backend tests: ~10 new + 9 from M-VIZ (B.1 extends M-VIZ's
     existing test_geometry_render_route.py)
   - Frontend tests: 1 new Viewport test + 7 new glb_loader tests
   - Performance budget per spec_v2

3. **Tier-B scope explicitly deferred** (NOT this milestone) — see
   spec_v2 §Tier B for the full table.

4. **Line-A/Line-B contract**: NO new ROADMAP commit needed.
   Anticipatory paths declared in `8fdb0a3` PRE-M-VIZ already cover
   M-RENDER-API's surface (`ui/backend/services/render/**` +
   `ui/backend/routes/geometry_render.py` + `ui/frontend/src/visualization/**`).

5. **Path-A engagement Gate-2**: per spec_v2 §Path-A, Gate-2 unlocks
   at M-RENDER-API merge — stranger sees their mesh wireframe in the
   Viewport. Demo flow documented in spec_v2.

### Out of scope · this DEC explicitly does NOT do

- Does NOT modify any backend service beyond `services/render/**` +
  `routes/geometry_render.py`
- Does NOT touch DEC-V61-091 verdict cap (cap remains dormant; M7-redefined wires it)
- Does NOT touch the §11.1 workbench-freeze advisory (M-RENDER-API
  paths are NEW · not in freeze scope)
- Does NOT begin M-PANELS / M-AI-COPILOT (those each get their own
  kickoff DECs after M-RENDER-API closes)
- Does NOT implement interactive face-pick / face-naming (deferred to
  M-PANELS scope per `.planning/strategic/m_panels_interactive_face_naming_2026-04-28.md`)
- Does NOT modify M-VIZ Tier-A surface (Viewport / stl_loader /
  viewport_kernel preserved · `format` prop is purely additive)
- Does NOT modify ImportPage / EditCasePage / MeshWizardPage /
  WorkbenchTodayPage / WorkbenchRunPage / RunComparePage routes
- Does NOT pick a glTF library other than trimesh (override only via
  amending this DEC's `library_choice` field pre-Acceptance)

## Why this DEC alone is docs-only · per-implementation-arc Codex fires later

This DEC is the kickoff plan. It introduces no code, no test, no API,
no schema. The implementation work that follows (split per spec_v2
§Sequence Steps 2-7) will produce:

- 1 services/render/__init__.py + module skeleton (Step 2 · ~30 LOC)
- 1 geometry_render glb endpoint + cache layer + tests (Step 3 ·
  ~80 LOC main + ~150 LOC tests)
- 1 mesh_wireframe service + endpoint + tests (Step 4 · ~250 LOC main
  + ~120 LOC tests)
- 1 field_sample stub + endpoint + tests (Step 5 · ~80 LOC main + ~60
  LOC tests)
- 1 frontend glb_loader.ts + Viewport format prop + tests (Step 6 ·
  ~150 LOC main + ~80 LOC tests)
- 1 build + smoke pass (Step 7)

Each of those (especially Steps 3-6) triggers Codex per RETRO-V61-001
risk-tier rules. They may bundle or split further depending on Codex
findings. The kickoff DEC's scope is to lock the plan; the
implementation DEC(s) document the actual builds.

Per V61-094 §Why this DEC alone is docs-only precedent: kickoff DECs
do NOT self-trigger Codex. Codex fires when implementation lands.

## Counter impact

Per V61-087 §5 truth table (autonomous_governance=true · Kogami review
NOT triggered for this kickoff per V61-094 P2 #1 bounding clause),
counter advances per Interpretation B (STATE.md SSOT).

- **Pre-advance**: 59 (post-M-VIZ close-out 36c4a78)
- **Post-advance** (on this DEC ratify): 60
- Per-implementation-arc DECs each advance counter further (estimate
  1-2 more across this milestone, depending on Codex round count;
  lower than M-VIZ's 1-3 because library is already in [workbench] +
  scope is better-bounded).

RETRO-V61-001 cadence: counter ≥20 since RETRO-V61-005 close
(~counter 51) → currently +8..9, threshold not crossed; no arc-size
retro fires.

## Verification plan (for THIS kickoff DEC's acceptance · NOT for milestone close)

### Self-test (none — docs-only DEC)

This DEC introduces no code; no self-test applicable.

### Codex review

**SKIPPED** for this DEC alone (CLASS-1 docs-only governance kickoff
per V61-086 / V61-089 / V61-093 / V61-094 precedent — RETRO-V61-001
risk-tier triggers all FALSE for the kickoff doc itself: no code, no
test, no API, no schema).

Per-implementation-arc Codex fires when Steps 2-7 implement.

### Kogami strategic review

**NOT REQUIRED** per `kogami_review.required: false` rationale above
(V61-094 P2 #1 bounding clause).

### CFDJerry explicit ratification

Required per DEC-V61-087 — pre-merge gate · STOP point. Visual: this
DEC has no UI to verify; ratification is on the kickoff plan itself,
with library choice + scope + endpoints all explicit.

## Failure modes considered

| Failure mode | Mitigation |
|---|---|
| trimesh glb output non-conformant on edge-case STL | Smoke test against 3 fixtures + multi-solid ASCII; document quirks |
| polyMesh edge-extraction performance on large fixtures | Tier-A scope is small fixtures; defer perf to M-RENDER-API.perf |
| glTF accessor packing for COLOR_0 too awkward in trimesh | Tier-A fallback to `application/octet-stream` binary float32 stream |
| vtk.js `vtkGLTFImporter` divergence from server-side glTF | Round-trip unit test (encode then decode) |
| Cache directory permissions / atomic-write race | mkdir(parents=True, exist_ok=True) + tempfile + os.replace |
| Frontend `glb_loader` becomes a dumping ground | Keep separate from stl_loader in Tier-A; revisit when third loader lands |
| §11.1 freeze pressure | Tier-A touches NEW paths only · BREAK_FREEZE count stays at 1 |
| Bundle bloat from vtkGLTFImporter selective import | Measure delta in Step 6 · soft cap +50 KB gzipped |
| Library-choice regret mid-implementation | Override window in DEC frontmatter; past Acceptance, library change is a new DEC |

## Sync

Notion sync runs only after Status flips to Accepted. Per V61-094
§Sync precedent (P3 #5 finding), three artifacts pair-sync with
explicit placement:

1. **DEC** — Decisions DB row (standard pattern, mirrors
   V61-091/092/093/094)
2. **brief_2026-04-28.md** — Notion sub-page under the DEC's Decisions
   DB row (strong coupling visible from Decisions DB)
3. **spec_v2_2026-04-28.md** — Notion sub-page under the DEC's
   Decisions DB row (sibling to brief)

This placement continues the precedent set by V61-094 for subsequent
kickoff DECs (M-PANELS / M-AI-COPILOT).

Pre-merge state stays Proposed in repo.

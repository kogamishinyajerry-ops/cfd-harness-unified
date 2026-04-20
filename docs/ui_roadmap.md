# UI MVP Roadmap

Authored 2026-04-20. Companion to `docs/product_thesis.md` and
`docs/ui_design.md`. Covers per-phase gate criteria, risk register,
calendar estimates, and rollback paths.

Each phase = one feature branch = one PR = one `DEC-V61-00N` decision
record = one Notion mirror. Merge method: **regular merge commit**
(留痕 > 聪明).

## Phase 0 — Scaffold + Validation Report (**in flight**)

**Branch**: `feat/ui-mvp-phase-0`
**Decision**: DEC-V61-002 (this session)
**Calendar estimate**: single session (doc + scaffold + 1 screen)

**Scope**:
1. Product thesis + UI design + roadmap docs
2. `ui/backend/` FastAPI scaffold with 3 routes
3. `ui/frontend/` Vite + React + TS + Tailwind + shadcn scaffold
4. Screen 4 Validation Report wired to 3 real cases (DHC,
   cylinder_wake, turbulent_flat_plate)
5. `ui/README.md` runbook
6. `pyproject.toml` optional `[ui]` dep group

**Gate criteria** (all must PASS before merging PR #2):
- [ ] `docs/product_thesis.md` · `docs/ui_design.md` · `docs/ui_
      roadmap.md` land in the PR
- [ ] `ui/backend/` boots via `uvicorn ui.backend.main:app`; GET
      `/api/health` returns `{"status": "ok"}`
- [ ] GET `/api/cases` returns a list containing all 10 whitelist IDs
- [ ] GET `/api/validation-report/differential_heated_cavity` returns
      JSON with `reference_value`, `measured_value`, `tolerance`,
      `pass_fail`, `audit_concerns[]`, `preconditions[]`
- [ ] `ui/frontend/` boots via `pnpm run dev`; renders Screen 4 for
      each of DHC / cylinder_wake / turbulent_flat_plate
- [ ] Screen 4 band chart renders; measured dot position visually
      corresponds to pass/hazard/fail color
- [ ] `pyproject.toml` `[ui]` group install via `uv pip install -e
      ".[ui]"` succeeds on a clean venv
- [ ] `.planning/STATE.md` updated with new goal tree G-UI-0..G-UI-5
- [ ] `.planning/external_gate_queue.md` contains a Q-4 entry
      placeholder for Phase 5 commercial-signing gate
- [ ] DEC-V61-002 frontmatter `notion_sync_status` updated with
      Notion page URL
- [ ] PR #2 merged via regular merge commit (no squash, no rebase)

**Explicit non-goals** (Phase 0):
- No WebSocket (residual streaming is Phase 3)
- No VTK.js / 3D viewport
- No auth / users / projects (backend binds to 127.0.0.1)
- No GitHub Actions / CI (wired in Phase 1)
- No visual regression or Playwright
- No production build / deploy

**Risks**:
- FastAPI imports from `src/` may discover hidden tight coupling —
  mitigation: use `from src.auto_verifier import …` read-only; if
  any import errors, wrap in a try/except and surface as a warning
  rather than editing `src/**`
- Real `slice_metrics.yaml` files per case may not exist for all
  three seed cases — mitigation: fall back to synthesized fixture
  yamls committed under `ui/backend/tests/fixtures/` and note the
  deviation in the Phase 0 gate review
- Vite + shadcn setup in a non-Node-preferred repo may conflict
  with `.gitignore` — mitigation: comprehensive `ui/.gitignore`

**Rollback**: single `git revert -m 1 <phase-0-merge-sha>`; removes
all Phase 0 artifacts.

## Phase 1 — Case Editor

**Branch**: `feat/ui-mvp-phase-1-case-editor`
**Decision**: DEC-V61-003 (future)
**Calendar estimate**: 2-3 focused sessions

**Scope**:
- Screen 2 Case Editor, three-column layout
- Monaco editor + `monaco-yaml` integration
- Custom language-server bridge calling `POST /api/lint-case` (new
  endpoint)
- Schema tree fed from `knowledge/schemas/whitelist_case.yaml`
  (to be added via Codex tool dispatch if it doesn't exist)
- Contract panel reading live from editor buffer + gold_standards
- `SAVE` round-trips through FastAPI; writes to a scratch `draft_`
  prefix, NOT directly to `knowledge/whitelist.yaml` (hard floor #2
  protection)

**Gate criteria**:
- [ ] Opening an existing case loads its YAML verbatim
- [ ] Introducing a schema violation shows a red squiggle within
      200ms
- [ ] Agent-suggested lines (sourced from a mocked agent-diff file)
      render with violet left-border
- [ ] `RUN-PRECHECK` button calls `POST /api/precheck-case` which
      returns physics-contract evaluation without running the
      solver
- [ ] No path by which the editor can overwrite `knowledge/
      whitelist.yaml` directly; all saves hit a draft area
- [ ] Testing: 3 synthetic bad-yaml fixtures lint with specific
      expected error types
- [ ] GitHub Actions `ui-ci.yml` first version (typecheck + pytest)

**Risks**: Monaco + monaco-yaml bundle size; mitigation: code-split
the editor and lazy-load on route entry.

## Phase 2 — Decisions Queue + Notion sync

**Branch**: `feat/ui-mvp-phase-2-decisions`
**Decision**: DEC-V61-004 (future)
**Calendar estimate**: 2-3 focused sessions

**Scope**:
- Screen 5 Decisions Queue (Kanban)
- Bidirectional Notion sync:
  - On page load: `GET /api/decisions` pulls from Notion Decisions
    DB + merges with local `.planning/decisions/*.md`
  - On create: `POST /api/decisions` writes BOTH locally AND to
    Notion
  - On status transition: `PATCH /api/decisions/{id}` updates both
- External-gate-queue ingestion: parse `external_gate_queue.md` at
  load; surface Q-1/Q-2/Q-4 as non-draggable cards in a dedicated
  "EXTERNAL GATE" lane

**Gate criteria**:
- [ ] Queue renders all existing 7 Decisions DB entries + any new
      DEC-V61-003 / 004 entries
- [ ] Drag DEC-V61-003 Draft → Proposed → Accepted works; invalid
      transitions (e.g. Proposed → Draft) are rejected with
      tooltip
- [ ] Creating a new decision writes to Notion within 3s and a
      local `.planning/decisions/YYYY-MM-DD_<slug>.md` file
- [ ] Notion create failure triggers local-only save + visible
      banner "Notion offline — will re-sync on reconnect"
- [ ] autonomous-governance counter (v6.1-era) visible in UI;
      matches STATE.md counter
- [ ] Hard-floor #3 guard: no UI path deletes a decision; archive
      is the strongest action

**Risks**: Notion MCP may go offline mid-operation (history:
UNREACHABLE stretches); mitigation: queue + retry with
exponential backoff, expose sync status chip in header.

## Phase 3 — Run Monitor + WebSocket

**Branch**: `feat/ui-mvp-phase-3-run-monitor`
**Decision**: DEC-V61-005 (future)
**Calendar estimate**: 3-4 focused sessions

**Scope**:
- Screen 3 Run Monitor
- WebSocket endpoint `WS /api/run-stream/{run_id}` yielding residual
  rows + audit_concern deltas
- VTK.js viewport (mesh + scalar field; decimated OpenFOAM data
  served via `GET /api/run/{run_id}/field/{field_name}`)
- Checkpoint / Resume / Stop controls wired to FoamAgentExecutor via
  Codex-dispatched tool endpoints (hard floor #2 requires src/
  changes via Codex)

**Gate criteria**:
- [ ] End-to-end MockExecutor run visible: start → stream residuals
      → complete → show final Validation Report (Phase 0's Screen
      4 reused)
- [ ] Residual plot tick updates within 500ms of new row
- [ ] VTK.js renders the DHC 256² mesh + temperature field
- [ ] Checkpoint button produces a `.run_state/` dir listed in the
      run's audit-package manifest
- [ ] No `src/foam_agent_adapter.py` edit without Codex dispatch +
      `Execution-by: codex-gpt54` trailer

**Risks**: VTK.js bundle size + OpenFOAM field format conversion;
mitigation: Phase 3 starts with probe-line plots only; field
visualization via OpenFOAM VTK export + vtk.js reader added late.

## Phase 4 — Project Dashboard + CI hardening

**Branch**: `feat/ui-mvp-phase-4-dashboard`
**Decision**: DEC-V61-006 (future)
**Calendar estimate**: 2-3 focused sessions

**Scope**:
- Screen 1 Project Dashboard (10-case contract matrix)
- Auth: OAuth via an identity provider (Auth0 or Ory; choice made
  at Phase 4 kickoff)
- Multi-project model: a project has its own whitelist scope + its
  own audit-package signing key
- Plotly integration for more elaborate charts in the dashboard
- Playwright end-to-end tests for all 4 shipped screens

**Gate criteria**:
- [ ] Login via OAuth → project picker → dashboard loads in <2s
- [ ] 10-case matrix cells all render; hover reveals mini band chart
- [ ] Clicking a cell drills into Screen 4 (Validation Report)
- [ ] "Decisions this week" timeline matches decisions-queue
      content
- [ ] Playwright suite has 1 test per screen; all green on PR CI
- [ ] Multi-project: can create a second project, switch, see
      scoped data

**Risks**: auth is load-bearing and ratchet-difficult to remove
later; validate provider choice against Phase 5 enterprise-SAML
requirement before merging Phase 4.

## Phase 5 — Audit Package Builder (**commercial gate**)

**Branch**: `feat/ui-mvp-phase-5-audit-package`
**Decision**: DEC-V61-007 (future)
**Calendar estimate**: 4-5 focused sessions — highest-risk phase

**Scope**:
- Screen 6 Audit Package Builder (4-step wizard)
- Byte-reproducible zip bundle
- HMAC-SHA256 signing with per-project key; key management via
  environment variable in Phase 5, external key store deferred
- PDF rendering via `weasyprint` (Python, avoids browser Chrome
  dependency for server-side rendering)
- Framework templates: FDA V&V40, DO-178C, NQA-1, ASME V&V40 generic
- Verification CLI: `python -m audit_package verify <bundle.zip>`

**Gate criteria**:
- [ ] A DHC audit package exports in <10s on a reference machine
- [ ] Running the export twice with identical inputs produces
      byte-identical zips (hashed)
- [ ] HMAC verification reproduces via 5-line bash script in
      `ui/backend/audit_package/VERIFY.md`
- [ ] PDF renders offline (no external CDN calls)
- [ ] V&V40 template output reviewed by an FDA-experienced
      compliance officer (named in the gate, e.g. "Kogami's
      regulatory contact X") and returned with APPROVED
- [ ] Q-4 external-gate item (commercial-signing scheme review)
      CLOSED by Kogami or external Gate

**Risks**:
- **Byte-reproducibility is hard**: zip metadata timestamps,
  filesystem-dependent ordering, Python dict ordering in older
  runtimes. Mitigation: explicit canonical-output pipeline with
  a unit test asserting hash stability across 10 runs.
- **V&V40 template correctness**: wrong template shape ruins the
  product's credibility. Mitigation: external compliance-officer
  review is a gate criterion, not a nice-to-have.
- **Signing-key management**: naive env-var key leaks when ops
  folks SSH into the host. Mitigation: document the limitation
  clearly; add "KMS-backed key" as a Phase 6 follow-up.

## Post-MVP roadmap (informational only)

Not part of the MVP; captured here for strategic coherence.

| Phase | Concept | Estimated delivery |
|---|---|---|
| Phase 6 | Enterprise auth (SAML, SCIM), on-prem deploy packaging | Q3 2026 |
| Phase 7 | Second solver (SU2 or code_saturne) + executor abstraction refactor | Q4 2026 |
| Phase 8 | DOE / parametric sweep UI + HPC queue integration (Slurm, LSF) | Q1 2027 |
| Phase 9 | Compressible flow + ENSS + broader physics coverage | 2027 |
| Phase 10 | VS Code extension as secondary distribution channel | 2027 |

## Risk register (cross-phase)

| Risk | Likelihood | Impact | Owner | Mitigation |
|---|---|---|---|---|
| OpenFOAM binary compatibility drift (v9 → v10 → v11) | Medium | High | Kogami | Pin OpenFOAM version per customer deploy; regression test matrix |
| Compliance reviewer rejects audit package format | Low | Catastrophic | Kogami + reg contact | Phase 5 gate external review before ship |
| Anthropic APP sole-primary regime changes | Low | Medium | APP | v6.1 → v6.2 protocol is documented; revert path is available |
| Regulated buyer prefers ANSYS+audit-addon vs new vendor | Medium | High | Kogami (GTM) | Emphasize audit-as-product; price to allow adoption alongside ANSYS |
| `knowledge/whitelist.yaml` 10-case coverage insufficient for real customer cases | High | Medium | Kogami | Phase 1 adds custom-case-addition workflow with compliant contract authoring |
| Python asyncio + FastAPI latency under load | Medium | Medium | APP (backend owner) | Load test at Phase 4; add Redis cache + background task queue if p99 > 500ms |

## What triggers a stop-for-gate call

Per v6.1 hard floors, the following conditions halt autonomous
execution and escalate to Kogami or external Gate:

1. Any edit to `src/**`, `tests/**`, or `knowledge/gold_standards/**`
   is needed to complete a phase — must dispatch via Codex tool with
   `Execution-by: codex-gpt54` trailer; APP does not self-edit these
2. Any tolerance-value numeric change to `knowledge/gold_standards/
   *.yaml` — external Gate only (hard floor #1)
3. Whitelist membership add/remove/relabel — external Gate only
   (hard floor #2). Note: adding UI-only "draft" whitelist entries in
   a scratch namespace is allowed; promoting to real whitelist needs
   Gate
4. Three consecutive Codex-dispatched attempts fail on the same
   change — hard floor #4 trips; escalate immediately
5. Phase 5 commercial-signing-scheme review (Q-4) must be CLOSED by
   external Gate before Phase 5 merges

All other decisions are autonomous under `claude-opus47-app` Sole
Primary Driver authority.

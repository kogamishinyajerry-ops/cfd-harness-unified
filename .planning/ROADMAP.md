# ROADMAP

## Current

### Phase 5b — LDC simpleFoam migration + Ghia 1982 match
- Status: Infrastructure complete (DEC-V61-029) + Q-5 CLOSED via Path A (DEC-V61-030). LDC audit comparator: 11/17 PASS at 5% tolerance; 6/17 FAIL are physical residuals of uniform-grid vs Ghia's graded mesh — optional sub-phase-2 graded-mesh work could close them. 7 remaining FAIL-case sub-phases (5c..5j) queued with mandatory gold cross-check as first step.
- Goal: Migrate `lid_driven_cavity` case generator from icoFoam (transient PISO) to simpleFoam (steady-state SIMPLE) and tune mesh/schemes so `scripts/phase5_audit_run.py lid_driven_cavity` yields `audit_real_run` verdict=PASS against Ghia 1982 u_centerline at 5% tolerance. First of 8 per-case Phase 5b sub-phases; establishes the solver-swap pattern that the remaining 7 FAIL cases (BFS, TFP, duct_flow, impinging_jet, naca0012, DHC, RBC) will copy in Phase 5c..5j.
- Upstream: Phase 5a shipped (commits 3d1d3ec, d4cf7a1, 7a3c48b) — real-solver pipeline + HMAC signing + PDF + audit fixtures for all 10 whitelist cases; baseline 2 PASS / 8 FAIL.
- Required outputs:
  - Updated `src/foam_agent_adapter.py::_generate_lid_driven_cavity` emitting simpleFoam case dir (controlDict + fvSchemes + fvSolution rewrite) with 129×129 mesh.
  - Regenerated `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` with `comparator_passed: true`.
  - Backend 79/79 pytest green (no regression on teaching fixtures).
  - Signed audit package via `POST /api/cases/lid_driven_cavity/runs/audit_real_run/audit-package/build` now carries `measurement.comparator_verdict=PASS`.
- Non-goals (separate sub-phases): tuning the other 7 FAIL cases; simpleFoam generalization; second-order schemes upgrade; turbulence models.
- Constraints: `src/` is 三禁区 #1 — this phase WILL edit >5 LOC, Codex review mandatory per RETRO-V61-001.
- Frozen governance edges: none (Q-1/Q-2/Q-3/Q-4 all closed).
- **Plans:** 3 plans
  - [ ] 05b-01-PLAN.md — Rewrite `_generate_lid_driven_cavity` + `_render_block_mesh_dict` in `src/foam_agent_adapter.py` (simpleFoam + 129×129 + frontAndBack empty)
  - [ ] 05b-02-PLAN.md — Regenerate `audit_real_run_measurement.yaml` fixture; verify backend 79/79 + frontend tsc clean
  - [ ] 05b-03-PLAN.md — Codex post-edit review + DEC-V61-NNN + atomic git commit + STATE/ROADMAP update

### Phase 7: Scientific-grade CFD vs gold reporting
- Status: Proposed (not yet activated)
- Goal: Upgrade audit reports from "single-scalar verdict" to publication-grade CFD vs gold evidence — full-field visualizations, multi-point profile overlays, formal error norms, residual histories, and Richardson grid-convergence indices — so every `audit_real_run` produces a PDF/HTML a CFD reviewer would accept alongside a paper's Figure/Table. Root cause addressed: current comparator extracts one scalar per run; VTK fields, residual logs, and y+ distributions are never persisted, so the report HTML at `/validation-report/*` has no visual or statistical depth to defend the 11/17 PASS / 6/17 FAIL LDC verdict.
- Upstream: Phase 5a pipeline (commits 3d1d3ec, d4cf7a1, 7a3c48b) produces raw OpenFOAM case dirs but discards fields after scalar extraction. Phase 5b/Q-5 established Ghia 1982 as the reference transcription bar. `/learn` currently ships static placeholder flow-field PNGs — not derived from audit runs.
- Required outputs (end-of-Phase-7):
  - `scripts/phase5_audit_run.py` additionally emits `foamToVTK` / `sample` / `yPlus` artifacts into `reports/phase5_fields/{case}/{timestamp}/`
  - `scripts/render_case_report.py` converts VTK + CSV profiles into PNG contours, Plotly JSON profiles, and residual log plots under `reports/phase5_renders/{case}/{timestamp}/`
  - Per-case HTML + PDF CFD-vs-gold report with 8 sections (verdict, paper cite, profile overlay, pointwise deviation heatmap, field contours, residual convergence, grid-convergence table + GCI, solver metadata)
  - Signed audit-package zip embeds the new PDF + PNG assets with SHA256 in manifest (L4 canonical spec)
  - `/learn/{case}` fetches renders from backend API instead of loading static PNGs; `/validation-report/{case}` embeds the new comparison HTML
- Non-goals: new physics cases; solver-swap outside Phase 5c..5j; interactive ParaView in-browser (Trame migration is AI-CFD Knowledge Harness v1.6.0 scope); DNS-grade statistics beyond RMS / L2 / L∞.
- Constraints: Phase 7a touches `src/foam_agent_adapter.py` (三禁区 #1, >5 LOC, Codex mandatory per RETRO-V61-001). Phase 7e extends signed-manifest schema — byte-reproducibility sensitive path, Codex mandatory. Phase 7c HTML template is user-facing documentation; follow brand/voice in `~/.claude/get-shit-done/references/ui-brand.md`.
- Frozen governance edges: none at Phase 7 start (Q-1..Q-5 all closed). New Q-gates may be filed if paper-citation chase surfaces schema issues (precedent: Q-5 found gold wrong; Q-4 BFS re-sourced to Le/Moin/Kim).
- **Sub-phases:** 6 sub-phases (7a..7f). Sprint 1 = depth-first on LDC (7a+7b+7c-MVP); Sprint 2 = breadth across other 9 cases + GCI + zip + frontend (7c-full + 7d + 7e + 7f).

### Phase 7a: Field post-processing capture (Sprint 1, ~2-3 days)
- Status: COMPLETE (DEC-V61-031, 2026-04-21). 3 waves landed: adapter functions{} + executor capture + driver manifest; backend route/service/18 pytest; Codex 3 rounds → APPROVED_WITH_COMMENTS (2 HIGH security issues caught + fixed: URL basename collision + run_id path-traversal). Real LDC OpenFOAM integration produced 8 artifacts, HTTP manifest + subpath download + traversal 404 verified live. 97/97 pytest. v6.1 counter 16→17.
- Goal: Extend `scripts/phase5_audit_run.py` + `src/foam_agent_adapter.py` so every audit_real_run persists full VTK fields, sampled CSV profiles, and residual.log to `reports/phase5_fields/{case}/{timestamp}/`.
- Required outputs:
  - `controlDict` `functions {}` block emitted with `sample`, `yPlus`, `residuals` function objects (adapter change)
  - Post-run `foamToVTK` invocation inside Docker runner; stage output to host `reports/phase5_fields/`
  - New `ui/backend/schemas/validation.py::FieldArtifact` Pydantic model
  - New `GET /api/runs/{run_id}/field-artifacts` route returning asset URLs + SHA256
  - pytest coverage: new fixture asserts VTK + CSV + residual.log presence for LDC
- Constraints: Codex mandatory (三禁区 #1 + adapter >5 LOC). Must not regress 79/79 pytest.
- **Plans:** 3 plans
  - [x] 07a-01-PLAN.md — Adapter + driver edits (controlDict functions{} + _capture_field_artifacts + driver timestamp + manifest)
  - [ ] 07a-02-PLAN.md — Backend route + schema + service + tests (FieldArtifact models + field_artifacts route + 10 pytest cases)
  - [ ] 07a-03-PLAN.md — Integration + Codex review + DEC-V61-031 + atomic commit

### Phase 7b: Render pipeline (Sprint 1, ~2 days)
- Status: Planned
- Goal: New `scripts/render_case_report.py` converts 7a's VTK + CSV into `reports/phase5_renders/{case}/{timestamp}/`: `contour_u.png`, `contour_p.png`, `streamline.png`, `profile_u_centerline.html` (Plotly JSON), `residuals.png`.
- Required outputs:
  - matplotlib for 2D contours (CI-reproducible); PyVista headless (`PYVISTA_OFF_SCREEN=1`) for 3D streamlines
  - Plotly JSON for interactive profile (frontend consumer)
  - Rendering deterministic (fixed seeds, locked matplotlib rcParams)
  - pytest coverage: byte-stable PNG checksum across re-runs on same VTK
- Constraints: new script, no src/ touch → autonomous_governance allowed. Add `pyvista`, `plotly`, `matplotlib` to `pyproject.toml` [render] extra.

### Phase 7c: CFD-vs-gold comparison report template (Sprint 1 MVP + Sprint 2 fan-out, ~3 days)
- Status: Planned — **core deliverable, the "說服力" centerpiece**
- Goal: Per-case HTML + WeasyPrint PDF report with 8 sections:
  1. Verdict card (PASS / FAIL + L2 / L∞ / RMS / max |dev|%)
  2. Paper citation block (Ghia 1982 / Le-Moin-Kim 1997 / etc. + Figure/Table + native tabulation)
  3. Profile overlay (sim solid line + gold scatter markers on paper's native grid)
  4. Pointwise deviation heatmap along sampling axis
  5. Field contours (U / p / vorticity / Cf depending on case class)
  6. Residual convergence (log y-axis, all solved fields)
  7. Grid-convergence table with Richardson p_obs + GCI_21/32 (from 7d)
  8. Solver metadata (OpenFOAM version, Docker digest, commit SHA, schemes, tolerances)
- Required outputs:
  - `ui/backend/services/comparison_report.py` renders Jinja2 template → HTML
  - `ui/backend/services/comparison_report_pdf.py` HTML → WeasyPrint PDF
  - `POST /api/cases/{case}/runs/{run_id}/comparison-report/build` route
  - Sprint 1 MVP: LDC only; Sprint 2: other 9 cases
  - `/validation-report/{case}` frontend route embeds the HTML
- Constraints: WeasyPrint requires `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (already in `.zshrc`). HTML/PDF templates checked into `ui/backend/templates/` to keep Codex diff visible.

### Phase 7d: Richardson grid-convergence index (Sprint 2, ~1 day)
- Status: Planned
- Goal: Compute observed order of accuracy `p_obs` and Grid Convergence Index `GCI_21` / `GCI_32` from existing `mesh_20/40/80/160` fixtures per Roache 1994.
- Required outputs:
  - `ui/backend/services/grid_convergence.py` implementing Richardson extrapolation + GCI formula
  - New columns in 7c's "grid-convergence table" section
  - pytest coverage: analytic fixture (known p=2 solution) + LDC regression (p_obs should fall in [1.0, 2.0])
- Constraints: pure numerical, no src/ or adapter touch → autonomous_governance allowed.

### Phase 7e: Signed audit-package integration (Sprint 2, ~1 day)
- Status: Planned
- Goal: Embed 7c PDF + 7b PNG/JSON into HMAC-signed audit-package zip; extend manifest schema to L4 canonical.
- Required outputs:
  - `audit_package.py` manifest `artifacts.field_renders[]` + `artifacts.comparison_report.pdf_sha256` blocks
  - `docs/specs/audit_package_canonical_L4.md` supersedes L3 build_fingerprint spec
  - zip byte-reproducibility preserved (re-run produces identical HMAC)
  - pytest coverage: `test_phase5_byte_repro.py` extended to cover new artifacts
- Constraints: **Byte-reproducibility-sensitive path → Codex mandatory** per RETRO-V61-001 new trigger #2. L3→L4 schema rename touches manifest builder + signer + verifier → ≥3 files → Codex mandatory per RETRO-V61-001 new trigger #3.

### Phase 7f: Frontend render consumption (Sprint 2, ~1 day)
- Status: Planned
- Goal: Replace static placeholder flow-field PNGs in `/learn/{case}` with live fetches from 7a's `/api/runs/{run_id}/field-artifacts` + 7b's `/api/runs/{run_id}/renders`.
- Required outputs:
  - `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` flow-field block fetches real renders; falls back to reference-run renders if the slider mesh has no artifacts yet
  - `ui/frontend/src/pages/ValidationReportPage.tsx` embeds 7c HTML via iframe or direct component
  - frontend tsc --noEmit clean; visual acceptance via dev server
- Constraints: multi-file frontend change → Codex mandatory per existing trigger. Must not regress the 3 deep-link buttons added in commit 7a3c48b.

### Phase 8 — Delivery hardening
- Status: Active (legacy lane)
- Goal: keep the visual acceptance surface reproducible, cache-resilient, and synced to GitHub/Notion without crossing external-gate boundaries.
- Required outputs: canonical HTML, timestamped snapshot HTML, machine-readable manifest, deep acceptance package, synced control-plane records.
- Frozen governance edges: `Q-1 DHC gold-reference`, `Q-2 R-A-relabel`.

### Phase 9 — Planning only
- Status: Planned
- Goal: comparator/model-routing follow-on work after a fresh activation review.
- Rule: no Phase 9 activation work starts until Phase 8 hardening closes and external-gate constraints are explicitly reviewed.

## Completed

- Phase 1–7: completed and retained as historical implementation/archive context in `.planning/STATE.md`.
- Phase 8 baseline reporting upgrade: landed up to `088e2a3`, including Chinese-first visual acceptance deck and raster evidence panels.

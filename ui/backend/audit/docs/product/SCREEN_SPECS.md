# Screen Specs (Phase 0 — three screens)

Only three screens are in scope. All are read-only. All derive content from
artifacts on disk. None contain mutation controls in Phase 0.

## Screen 1 — Case Contract

**Purpose:** show what the case promises.

**Source artifacts:**
- `cases/<case>/case_manifest.yaml`
- `src/cfdtrust/schemas/case_manifest.schema.json` (used to render section badges)

**Content blocks:**
- header: `case_id`, `case_family`, `solver_backend`, `solver`
- physics section (regime, fluid, turbulence model, steady/compressible flags)
- geometry contract (required patches, dimensionality, unit system)
- mesh contract (checkMesh required?, BL required?, y+ targets, quality thresholds)
- bc contract (inlet / outlet / wall / turbulence_fields)
- solver contract (residual targets, max iterations, QoI stability window)
- qoi list with declared tolerances
- reference_comparison status banner — explicit when `status != finalized`

**Empty-state:** "No `case_manifest.yaml` found. The case is incomplete."

## Screen 2 — Run Timeline

**Purpose:** show what happened when the trust loop ran.

**Source artifacts:**
- `cases/<case>/artifacts/solver.log`
- `cases/<case>/artifacts/residuals.csv`
- `cases/<case>/artifacts/trust_report.json` (for gate statuses)

**Content blocks:**
- prominent MOCKED banner whenever `solver_execution != "real"`
- per-iteration residuals chart (line plot, log scale on y)
- gate strip: `geometry / mesh / bc / solver / qoi / reference` with PASS/WARN/FAIL/MOCKED chips
- log tail (last N lines of `solver.log`) — read-only
- generated_at timestamp

**Empty-state:** "No run artifacts yet. Run `python -m cfdtrust.cli report cases/<case>`."

## Screen 3 — Trust Report

**Purpose:** show the verdict and what is missing to reach the next status level.

**Source artifacts:**
- `cases/<case>/artifacts/trust_report.json`

**Content blocks:**
- overall_status badge (PASS/WARN/FAIL/BLOCKED/MOCKED)
- solver_execution and validation_status, side by side
- gate table with status + artifact path links
- limitations array, displayed verbatim
- next_actions array, displayed verbatim
- AI advisor block (Phase 4 placeholder in Phase 0)

**Empty-state:** "No trust_report.json yet."

## Out of scope for Phase 0 screens

- editing case manifests
- starting / stopping solver runs
- choosing turbulence models
- comparing two cases side by side
- managing projects / folders / users
- exporting reports to PDF
- chat with AI advisor (visible after Phase 4)

---
decision_id: DEC-V61-102
title: M-RESCUE · Manual override foundation — every AI-authored dict becomes engineer-editable
status: Accepted (2026-04-30 · authored under user direction "完全交给你决策" + "工程师在AI表现不佳的情况下，甚至无法手动介入，拯救算例" deep-planning consensus)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-30
authored_under: workbench_long_horizon_roadmap_2026-04-29.md (Era 1 LOOP SPINE — slots in as M9.7, AFTER DEC-V61-101 minimal channel executor and BEFORE M10 STEP/IGES intake) · user direction 2026-04-30 — "我觉得在CAD几何操作、算例设置方面，功能必须完全覆盖，否则项目就是不完整的，工程师在AI表现不佳的情况下，甚至无法手动介入，拯救算例"
parent_decisions:
  - DEC-V61-093 (Pivot Charter Addendum 3 · §4.c HARD ORDERING — this DEC sits AFTER V61-101 in the dogfood window; it's an architectural foundation milestone that all post-M10 work depends on, NOT a feature milestone of its own)
  - DEC-V61-097 (Phase-1A LDC dogfood · setup_ldc_bc hardcoded dict authoring · this DEC introduces the override path that loosens that hardcoding without breaking it)
  - DEC-V61-101 (Minimal channel executor · setup_channel_bc hardcoded dict authoring · same override pattern applies here)
  - DEC-V61-098 (M-AI-COPILOT Tier-A · annotations.yaml is the existing precedent for engineer-authoritative state coexisting with AI-suggested state · M-RESCUE generalizes that pattern from face_annotations to ALL OpenFOAM dicts)
  - RETRO-V61-001 (risk-tier triggers · multi-file backend route + manifest schema change + first-impl after UX feedback all trigger pre-merge Codex)
parent_artifacts:
  - .planning/strategic/workbench_long_horizon_roadmap_2026-04-29.md (Era 1 §M9-M14 critical path · this DEC is the cross-cutting foundation that M10-M14 inherit · without it the engineer can't rescue an AI-mis-classified case at any stage)
  - reports/codex_tool_reports/dec_v61_101_round3.md (Codex M9.5 R3 APPROVE precedent for classifier-executor parity discipline · M-RESCUE adds a third party — manual override — that must not break the parity invariant)
counter_impact: +1 (autonomous_governance: true · architectural foundation DEC, no external gate required)
self_estimated_pass_rate: 70% (multi-file backend route + manifest schema migration + Monaco editor frontend integration + override tracking on every existing dict-author path · structurally surface-large but each piece is bounded)

# Why now

The 2026-04-30 dogfood loop surfaced two regressions (cylinder face selection + simulation crawl) that were each fixable by code changes. But the user observation underlying both was deeper:

> "在CAD几何操作、算例设置方面，功能必须完全覆盖，否则项目就是不完整的，工程师在AI表现不佳的情况下，甚至无法手动介入，拯救算例"

Today, every Step in the workbench writes OpenFOAM dicts via hardcoded string templates inside `bc_setup.py` / equivalent. When AI picks the wrong patch type, wrong solver, wrong fvSchemes scheme, wrong relaxation factor, **the engineer's only recovery path is `docker exec` into the openfoam container**. That's not a workbench — that's an AI demo with a case browser around it.

The roadmap (M10 STEP/IGES, M11 Mesh Wizard, M12 multi-solver, M13 paraview-grade post, M14 V&V) compounds this problem: each new milestone adds more AI-authored dicts but no path for the engineer to override. By M12 the surface is large enough that "AI is wrong somewhere in 30+ dict fields" becomes the dominant failure mode, and the workbench remains unrescuable.

M-RESCUE is the architectural counterpart: **every AI-authored OpenFOAM dict gains a raw-editor route + manifest-tracked override status, BEFORE any further milestone widens the AI authoring surface.** It's a 2-week foundation phase that all of M10-M14 build on top of.

# Scope

## Phase 1 · Backend (1 week)

### 1.1 case_manifest schema upgrade — SSOT for case state

`ui/backend/services/case_manifest/` (NEW module)

Current `case_manifest.yaml` is import-time metadata only (bbox, source_filename, ingest report). It does NOT track:
- Which solver / turbulence model is configured
- Which BC patches and their types
- Which numerics fields differ from solver-profile defaults
- Whether each field's source is `ai` (AI-authored) or `user` (manually overridden)

New schema (additive — old keys preserved for backwards-compat):

```yaml
# Existing (unchanged)
source: imported
case_id: ...
ingest_report_summary: ...

# New (M-RESCUE)
schema_version: 2  # bump signals manifest is RESCUE-aware

physics:
  solver: pimpleFoam        # source: ai | user
  turbulence_model: laminar # source: ai | user
  end_time: 5
  delta_t: 0.005
  source: {solver: ai, turbulence_model: ai, end_time: ai, delta_t: ai}

bc:
  inlet:
    patch_type: fixedValue
    fields: {U: [1, 0, 0], p: zeroGradient}
    source: {patch_type: ai, fields: ai}
  outlet:
    patch_type: zeroGradient
    fields: {U: zeroGradient, p: 0}
    source: {patch_type: ai, fields: ai}
  walls:
    patch_type: noSlip
    fields: {U: [0, 0, 0], p: zeroGradient}
    source: {patch_type: ai, fields: ai}

numerics:
  fv_schemes_overrides: {}  # populated only when user manually edits
  fv_solution_overrides: {}
  source: {fv_schemes_overrides: ai, fv_solution_overrides: ai}

overrides:
  raw_dict_files:
    "system/controlDict": {source: user, edited_at: "2026-04-30T10:23:00Z"}
    "system/fvSchemes":   {source: ai}
  # When raw_dict_files[path].source == "user", regenerating from manifest
  # must skip that file (or surface a confirm-overwrite prompt).

history:
  - {timestamp: "2026-04-30T08:14Z", action: "import",       source: user}
  - {timestamp: "2026-04-30T08:24Z", action: "setup_bc",     source: ai}
  - {timestamp: "2026-04-30T10:23Z", action: "edit_dict",    source: user, path: "system/controlDict"}
```

Deliverables:
- `services/case_manifest/schema.py` — Pydantic models for the new shape
- `services/case_manifest/io.py` — read/write with schema_version migration (v1 → v2)
- `services/case_manifest/overrides.py` — `mark_override(case_dir, path, source)` helper
- All existing `setup_*_bc` callers wrapped to write source=ai entries on success
- Unit tests: schema migration v1→v2 lossless, override marking idempotent

### 1.2 Raw dict editor backend route

`ui/backend/routes/case_dicts.py` (NEW)

Two endpoints:

```
GET  /api/cases/{case_id}/dicts/{path:path}
  → returns the file content + override metadata
  → 404 if path not in allowlist
  → 404 if file doesn't exist (returns expected default text via solver profile if known)

POST /api/cases/{case_id}/dicts/{path:path}
  body: {content: str, expected_etag: str (optional · for race protection)}
  → writes content to case_dir / path
  → marks manifest.overrides.raw_dict_files[path] = {source: user, edited_at: now}
  → 409 if expected_etag mismatches current file mtime
  → 422 if content fails schema validation (unless ?force=1)
  → 200 with {new_etag, manifest_after}
```

**Path allowlist** (security boundary):
```
ALLOWED_RAW_DICT_PATHS = {
    "system/controlDict",
    "system/fvSchemes",
    "system/fvSolution",
    "system/decomposeParDict",
    "constant/momentumTransport",
    "constant/transportProperties",
    "constant/g",
    # 0/ fields explicitly excluded — they're authored by setup_bc and have
    # face_id-tied invariants that raw editing would silently break.
    # Editing those is M-RESCUE Phase 2 (BC value editor with schema validation).
}
```

**Schema validation** (light-weight, not a full OpenFOAM parser):
- Confirm `FoamFile { ... }` header present
- Reject obvious typos (unbalanced braces, unterminated strings)
- For `controlDict`: confirm `application` field exists (else solver dispatch breaks)
- Force-override flag (`?force=1`) bypasses all validation for the "I know what I'm doing" path

Deliverables:
- `routes/case_dicts.py`
- `services/case_dicts/validator.py` (light schema check)
- `services/case_dicts/allowlist.py` (the path set)
- 12 unit tests covering the GET/POST happy paths + 5 rejection cases
- 1 route-layer E2E test: AI authors → user edits raw → user re-runs solve → manifest shows source=user

### 1.3 Case state inspector route

```
GET /api/cases/{case_id}/state-preview
  → returns: {
      manifest: full v2 manifest,
      dict_summary: [{path, exists, source, etag, line_count}],
      next_action_will_overwrite: [list of paths the next [AI 处理] would clobber]
    }
```

Powers the frontend "Preview before AI 处理" modal. The `next_action_will_overwrite` list is the conflict-warning surface: if the user manually edited `system/controlDict` and then clicks Step 4's [AI 处理], the modal shows "This will overwrite your manual changes to system/controlDict — continue or cancel?".

Deliverables:
- `routes/case_inspect.py` (NEW route)
- `services/case_inspect/preview.py`
- 4 unit tests covering: clean case, AI-authored case, mixed AI+user case, missing-files case

## Phase 2 · Frontend (1 week)

### 2.1 Raw dict editor component

`ui/frontend/src/components/RawDictEditor.tsx` (NEW)

Monaco-based editor (already a transitive dep via vtk.js? confirm; otherwise add `@monaco-editor/react`).

UI states:
- **Default view**: read-only render of current dict, with "Edit raw" toggle button
- **Edit mode**: Monaco editor with OpenFOAM grammar (use `c++` mode as fallback if no grammar pkg available — the curly-brace syntax + comments line up well enough)
- **Source badge**: 🤖 "AI-authored" / ✋ "Manually edited at 10:23 AM" / ⚠️ "AI proposed but you changed N lines"
- **Validation feedback**: warnings inline (yellow), errors block Save (red)
- **Save / Reset to AI default** buttons
- **Confirm-overwrite prompt** when Save would conflict with concurrent AI write (etag mismatch)

### 2.2 Wiring into Steps 3 + 4

- Step 3 (`Step3SetupBC.tsx`): add a collapsed "Advanced: edit raw dicts" section below the AI envelope. Expanding shows tabs for `controlDict`, `fvSchemes`, `fvSolution`, `transportProperties`.
- Step 4 (`Step4SolveRun.tsx`): same collapsible section. Plus a top-of-step "Solver: pimpleFoam (AI choice) [Switch...]" link that opens a solver-selection modal.

### 2.3 Solver selection modal (T1 minimum)

`ui/frontend/src/pages/workbench/step_panel_shell/SolverPickerModal.tsx` (NEW)

5 solvers in T1 registry:
- `icoFoam` — laminar incompressible transient (LDC default)
- `pimpleFoam` — laminar/turbulent incompressible transient (channel default · this DEC's V61-101 cleanup)
- `simpleFoam` — laminar/turbulent incompressible STEADY
- `buoyantPimpleFoam` — laminar/turbulent incompressible transient with buoyancy
- `rhoPimpleFoam` — compressible transient

Each entry: name + 1-line description + "compatible with: [BC types]" + "this case currently has: [✓/✗]" indicators + Pick button.

Picking switches the `physics.solver` field in manifest, regenerates `controlDict`/`fvSchemes`/`fvSolution` from the new solver profile, preserves any user-edited dicts (skips overwrite if `overrides.raw_dict_files[path].source == "user"` with confirm).

### 2.4 Restart-from-timestep UI

In Step 4 below the [AI 处理] button: dropdown populated from `/api/cases/{id}/time-dirs` — pick non-zero start time → patches `controlDict.startTime` accordingly → next solve continues from that snapshot.

Deliverables:
- 4 new TSX components
- 8 new vitest tests (RawDictEditor save / cancel / validation / conflict; SolverPicker compatibility check; RestartFromTimestep happy path)
- Step 3 + Step 4 modifications wiring the new components in

## Phase 3 · Solver registry + profile abstraction (3 days)

`ui/backend/services/solver_profiles/` (NEW module)

```python
@dataclass(frozen=True, slots=True)
class SolverProfile:
    name: str                                    # "pimpleFoam"
    binary: str                                  # "pimpleFoam"
    flow_type: Literal["incompressible", "compressible"]
    transient: bool
    supports_turbulence: tuple[str, ...]         # ("laminar", "kOmegaSST", ...)
    supports_buoyancy: bool
    required_bc_kinds: dict[str, tuple[str, ...]]  # {"U": ("inlet", "outlet", "wall"), ...}
    default_schemes: dict[str, str]
    default_fvsolution: dict[str, dict]
    default_controldict: dict[str, str | int | float]

PROFILES: dict[str, SolverProfile] = {
    "icoFoam": ...,
    "pimpleFoam": ...,
    "simpleFoam": ...,
    "buoyantPimpleFoam": ...,
    "rhoPimpleFoam": ...,
}
```

This abstraction REPLACES the hardcoded dict-string templates currently inlined in `bc_setup.py`. Every solver profile knows how to author its own dicts; the BC setup path picks the profile by name and delegates.

Migration:
- `setup_ldc_bc` rewritten to use `SolverProfile["icoFoam"]` (LDC stays on icoFoam — no behavior change)
- `setup_channel_bc` rewritten to use `SolverProfile["pimpleFoam"]` (already migrated in commit `a1b5e29` informally; this DEC makes the abstraction formal)
- New `switch_solver(case_dir, target_profile_name)` service for the UI's solver-picker modal

Deliverables:
- `services/solver_profiles/__init__.py` with the 5 profiles
- `services/solver_profiles/dict_authoring.py` — generic dict writer
- Migration of `setup_ldc_bc` + `setup_channel_bc` to use profiles
- Existing tests must continue to pass byte-for-byte (regression guard on the old hardcoded strings)
- 5 new tests (one per profile) confirming dict outputs match the expected reference files

# Out of scope (preserved for downstream milestones)

- **0/ field editing UI** (BC value editor with schema validation per patch type — M-RESCUE Phase 4 / M11)
- **Mesh wizard / mesh quality controls** (M11 explicitly · this DEC does not touch Step 2)
- **Turbulence models** (M12 explicitly · solver profiles include the `supports_turbulence` field but only `laminar` is wired in T1)
- **CAD operations / STEP-IGES intake** (M10)
- **Probe / force coefficients / slice-plane viewer** (M13)
- **Auto V&V / mesh-independence** (M14)
- **Multi-region / CHT / multiphase** (Era 2/3 explicitly)

# Default behaviors (locked in this DEC)

- **manifest schema_version=2** is the new default for newly-created cases
- **schema_version=1 cases** auto-migrate to v2 on first read (lossless: existing fields preserved, new fields populated with `source=ai` for everything)
- **Path allowlist** is the security boundary — additions require a follow-up DEC
- **Validation defaults to permissive** — only obvious file-corrupting issues block Save without `?force=1`
- **Solver switching always preserves user-edited dicts** with confirm-overwrite prompt
- **Restart-from-timestep is non-destructive** — original 0/ directory and prior time dirs preserved

# Codex review posture

This DEC is risk-tier-triggered (multi-file backend, schema change, first impl after UX feedback). Per RETRO-V61-001:
- **Pre-merge Codex required** for the Phase 1 backend slice (manifest schema + case_dicts route)
- **Pre-merge Codex required** for the Phase 3 solver profiles migration (refactors existing setup_*_bc — risk of behavior drift on byte-reproducibility)
- Phase 2 frontend can ride post-merge if self-pass-rate ≥80% on the submitted slice; ≤70% triggers pre-merge

# Kogami review posture

Per DEC-V61-087 §4 trigger taxonomy, M-RESCUE is a **strategic-layer architectural foundation DEC** introducing a new design pattern (manifest-as-SSOT + override tracking) that all subsequent milestones depend on. Kogami review **required** before Phase 1 begins (advisory gate · advisory not blocking but documented).

Trigger artifact = this DEC + the existing roadmap Era 1 + the `case_manifest` schema upgrade proposal in §1.1.

# Acceptance criteria

Phase 1 acceptance:
- `pytest ui/backend/tests/test_case_manifest.py` 100% pass (schema migration + override marking)
- `pytest ui/backend/tests/test_case_dicts_route.py` 100% pass (12 unit + 1 E2E)
- `pytest ui/backend/tests/test_case_inspect.py` 100% pass (4 cases)
- All existing tests still pass (no regression on byte-repro of LDC + channel paths)

Phase 2 acceptance:
- `npx vitest run` 100% pass with 8 new tests
- Manual smoke: open a case → Step 3 → expand "Advanced: edit raw dicts" → edit `controlDict` → save → check manifest shows source=user → click [AI 处理] → confirm-overwrite modal appears → cancel → manual edit preserved

Phase 3 acceptance:
- LDC dogfood case bytes-identical between pre-migration and post-migration `setup_ldc_bc` output (`scripts/smoke/dogfood_loop.py §4a` exit 0 with no diff)
- Channel dogfood case bytes-identical (`§4c` exit 0)
- 5 solver profile unit tests pass

DEC acceptance (rolls all three together):
- All Phase 1+2+3 tests pass
- `scripts/smoke/dogfood_loop.py` exits 0
- Codex APPROVE on Phase 1 slice + Phase 3 slice
- This file's `status:` line updated to `Implemented at commits <sha1> + <sha2> + <sha3>`

# Open question (deferred to Phase 1 implementation)

**Q1**: When raw-edited `controlDict` declares `application icoFoam` but manifest has `physics.solver: pimpleFoam`, who wins? Options:
- (A) controlDict file is the truth → reverse-sync manifest on next read
- (B) manifest is the truth → reject the raw edit unless user changes solver explicitly via SolverPicker
- (C) Surface mismatch as an error in the inspect-preview, ask user to reconcile

Tentative answer: **(C)** — explicit reconciliation. The "manifest as SSOT" principle says manifest wins, but mid-edit silent revert is hostile UX. Surface, ask, let user pick.

To be confirmed during Phase 1 review.

---

# Implementation tracking (filled during execution)

- [ ] Phase 1.1 case_manifest schema (commits: ...)
- [ ] Phase 1.2 case_dicts route (commits: ...)
- [ ] Phase 1.3 case_inspect route (commits: ...)
- [ ] Phase 1 Codex review (round count: ...)
- [ ] Phase 2.1 RawDictEditor component (commits: ...)
- [ ] Phase 2.2 Step 3 + Step 4 wiring (commits: ...)
- [ ] Phase 2.3 SolverPickerModal (commits: ...)
- [ ] Phase 2.4 Restart-from-timestep (commits: ...)
- [ ] Phase 3 solver profile migration (commits: ...)
- [ ] Phase 3 Codex review (round count: ...)
- [ ] Final dogfood smoke pass (script exit 0)
- [ ] Notion sync of this DEC

---

notion_sync_status: pending
codex_tool_report_path: pending
autonomous_governance: true

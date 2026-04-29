# M-AI-COPILOT (collab-first) · Pre-Implementation Surface Scan — 2026-04-29

**DEC**: DEC-V61-098
**Spec step**: spec_v2 §E Step 1
**Authority**: DEC-V61-088 (pre-implementation surface scan discipline)

This document closes Step 1 of the M-AI-COPILOT implementation arc. It maps every assumption spec_v2 makes against the live codebase and flags discrepancies before backend skeleton work begins.

---

## §1 · Scan results (4 spec_v2 grep targets)

### 1.1 · vtk.js CellPicker availability ✅

**Spec_v2 assumption**: `@kitware/vtk.js/Rendering/Core/CellPicker` resolves; if not, add to package.json.

**Verified**:
- `ui/frontend/package.json:18` declares `@kitware/vtk.js: ^35.11.0`
- `ui/frontend/node_modules/@kitware/vtk.js/Rendering/Core/CellPicker.{js,d.ts}` both present
- Sibling `AbstractPicker.{js,d.ts}` also present (base class — no extra dep needed)

**Conclusion**: NO new dep. Import path in spec_v2 §A6 is correct.

### 1.2 · face_id naming collisions ✅

**Spec_v2 assumption**: greenfield contract (no existing `face_id` references).

**Verified**:
- Grep `face_id|faceId|face-id|FaceId` across `ui/backend` + `ui/frontend/src` returns 6 hits
- ALL hits are `face_idx` (integer face index) in `polymesh_parser.py` + `bc_glb.py`
- ZERO hits on the new naming `face_id` (string hash)

**Conclusion**: greenfield. The new `fid_<16hex>` contract introduces no shadowing.

### 1.3 · pyyaml already imported ✅

**Spec_v2 assumption**: `import yaml` already in case_setup neighbors.

**Verified**: `import yaml` exists in 13+ backend modules:
- `ui/backend/services/case_drafts.py`
- `ui/backend/services/decisions.py`
- `ui/backend/services/run_history.py`
- `ui/backend/services/preflight.py`
- `ui/backend/services/case_scaffold/manifest_writer.py`
- `ui/backend/services/wizard.py`
- `ui/backend/services/comparison_report.py`
- `ui/backend/services/grid_convergence.py`
- `ui/backend/services/validation_report.py`
- `ui/backend/services/export_csv.py`
- `ui/backend/services/batch_matrix.py`
- `ui/backend/routes/case_export.py`
- `ui/backend/routes/workbench_basics.py`
- 4 test modules

**Conclusion**: NO new dep. PyYAML transitively present.

### 1.4 · awaiting_user / StepStatus state collision ✅ (with type-extension follow-through required)

**Spec_v2 assumption**: `awaiting_user` is a NEW StepStatus (not already in use).

**Verified**:
- `ui/frontend/src/pages/workbench/step_panel_shell/types.ts:12` — current shape:
  ```typescript
  export type StepStatus = "pending" | "active" | "completed" | "error";
  ```
- ZERO existing `awaiting_user` / `awaitingUser` literal usages anywhere in `ui/frontend/src`
- `StepTree.tsx:19,29` declares two `Record<StepStatus, string>` maps (`STATUS_DOT`, `ROW_VARIANT`) — these are TYPE-EXHAUSTIVE so the compiler will reject the extension until both maps gain an `awaiting_user` entry
- `StepPanelShell.tsx:176` initializes `stepStates` to `"pending"` — no init-time issue

**Conclusion**: greenfield literal, but extending `StepStatus` to a 5-state union forces edits in 2 known compile-time locations:
1. `types.ts:12` — add `"awaiting_user"` to the union
2. `StepTree.tsx:19,29` — add an `awaiting_user` color/dot/row-variant entry to BOTH `Record<StepStatus, string>` maps (amber dot per spec_v2 §C)

Type-checker will block on these — no silent regression risk.

---

## §2 · Greenfield contract probes (spec_v2 §B)

| Symbol | Existing? | Notes |
|---|---|---|
| `AIActionEnvelope` | NO | Greenfield · spec_v2 §B.2 |
| `UnresolvedQuestion` | NO | Greenfield · spec_v2 §B.2 |
| `face_annotation(s)` | NO | Greenfield · spec_v2 §B.1 |
| `FaceAnnotation` | NO | Greenfield · spec_v2 §B.1 |
| `annotations_revision` | NO | Greenfield · spec_v2 §B.2 |
| `annotation_revision` | NO | Greenfield · spec_v2 §B.2 |
| `user_authoritative` | NO | Greenfield · spec_v2 §B.1 |

ALL 7 contract symbols return zero hits across `ui/backend/**` + `ui/frontend/src/**`. No backward-compat consideration.

---

## §3 · Existing AI-action surface map

For context — what spec_v2 §A5 modifies and what stays untouched:

### 3.1 · `setup-bc` route (modify · §A5)
- Route: `ui/backend/routes/case_solve.py:75` — `POST /api/import/{case_id}/setup-bc`
- Returns: `SetupBcSummary` from `ui/backend/schemas/case_solve.py:7`
- Implementation: `ui/backend/services/case_solve/bc_setup.py` (called from `case_solve.split_boundary`)
- Plan: add `?envelope=1` query param → returns `AIActionEnvelope` shape; legacy callers without flag continue to receive `SetupBcSummary` (backward-compat per spec_v2 §B.4)

### 3.2 · `[AI 处理]` button locations (read-only · context)
- `ui/frontend/src/pages/workbench/StepPanelShell.tsx:62,84,89,102,113` — Step 1 has NO AI 处理 (upload is the engineer's gesture); Step 2 = mesh-gen; Step 3 = setup-bc; Step 4 = solve; Step 5 = results
- M-AI-COPILOT Tier-A only converts Step 3 to envelope mode (per spec_v2 §A5 "A5 only converts Step 3"). Steps 2/4/5 remain in legacy non-envelope shape.

### 3.3 · Audit-package surface (forward note · §F "hidden state" failure mode)
- Routes registered in `ui/backend/main.py:32-38`
- Implementation in `src/audit_package/{manifest,serialize}.py` (separate src tree)
- Plan: extend audit-package to include `face_annotations.yaml` in the bundle so per-face BC decisions are part of the canonical audit (separate Tier-A line item per spec_v2 §F).

---

## §4 · Discrepancies flagged before implementation

### 4.1 · Service-package path: spec_v2 vs DEC frontmatter ⚠️

**spec_v2 §A1-A4** specifies NEW packages:
- `ui/backend/services/case_annotations/`
- `ui/backend/services/ai_actions/`
- `ui/backend/routes/case_annotations.py`

**DEC frontmatter `implementation_paths`** instead listed:
- `ui/backend/services/case_setup/face_annotations.py` (ambiguous — does it mean a flat module under a new package, or a new top-level dir?)
- `ui/backend/services/case_setup/ai_envelope.py`
- `ui/backend/services/case_setup/setup_bc_runner.py`

**Resolution (chosen during scan)**: Follow **spec_v2 §A** verbatim. Create new sibling packages:
- `ui/backend/services/case_annotations/__init__.py` — reader/writer + `face_id` hash
- `ui/backend/services/ai_actions/__init__.py` — envelope wrapper
- `ui/backend/schemas/ai_action.py` — Pydantic schemas
- `ui/backend/routes/case_annotations.py` — GET/PUT route

The DEC `implementation_paths` will be reconciled in the next commit (one-liner frontmatter update OR rolled into the Step 2 backend skeleton commit body).

This matches existing flat `services/` layout precedent (`case_drafts/`, `case_scaffold/`, `case_solve/`, `case_visualize/`) rather than nesting under a new `case_setup/` umbrella that doesn't exist today.

### 4.2 · No existing `case_setup/` package ⚠️

`ls ui/backend/services/case_setup* 2>&1` returns "no matches found". Existing setup-bc logic lives in `ui/backend/services/case_solve/bc_setup.py`. The spec_v2 path `case_annotations/` is the correct new home; `case_setup/` would create a parallel naming axis that conflicts with the existing `case_solve/bc_setup.py`.

### 4.3 · `awaiting_user` type extension cascades (compile-time only) ✅

Listed in §1.4 above — `types.ts:12` + `StepTree.tsx:19,29` (two Records). TypeScript will surface both — no silent miss risk.

---

## §5 · Implementation plan refinements (locked before Step 2)

1. **Step 2 backend skeleton commit** creates:
   - `ui/backend/services/case_annotations/__init__.py` (face_id hash + read/write helpers)
   - `ui/backend/services/case_annotations/_yaml_io.py` (PyYAML wrapper · resolve(strict=True) on case_dir per V61-097 R3 symlink-containment precedent)
   - `ui/backend/schemas/ai_action.py` (Pydantic models)
   - `ui/backend/tests/test_case_annotations.py` (round-trip + face_id stability under `gmshToFoam` regen)
   - `ui/backend/tests/test_ai_action_schema.py` (envelope validation + revision monotonicity)

2. **face_id hash test** — must include a regen-stability case: write polyMesh → compute hashes → re-run `gmshToFoam` on identical geometry → recompute → assert all face_ids match. This is the critical novel-failure-mode test per spec_v2 §F (Stability class).

3. **Symlink containment** — `case_annotations._yaml_io` MUST mirror the `_bc_source_files()` pattern from `bc_glb.py:192` (resolve(strict=True) + relative_to(case_root)). Codex round 1 of V61-097 flagged this for `bc_glb`; same pattern applies here per "byte-reproducibility sensitive paths" trigger in CLAUDE.md.

4. **Backward-compat invariant** — `setup-bc` without `?envelope=1` MUST return identical bytes to today's `SetupBcSummary`. Add a regression test in Step 3 that diffs the bytes against a recorded fixture.

---

## §6 · Open questions deferred to Codex round 1

1. **`gmshToFoam` determinism** — spec_v2 §I.1 noted "probable yes; verify with regen test". Step 2 test will verify. Codex will probe whether the 9-decimal rounding is sufficient (vs 12 decimals or sorted-tuple-of-rounded-tuples).
2. **vtk.js CellPicker latency at LDC scale** — Tier-A doesn't measure; Tier-B does. Codex may flag as a forward note but cannot block Tier-A.
3. **Annotation file location in audit package** — Tier-A line item flagged in §3.3; will be addressed in Step 4 (route + test) or Step 11 (dogfood log) depending on bundle-builder coupling.

---

## §7 · Conclusion · Step 1 CLEARED

All 4 spec_v2 §E Step 1 grep targets verified. Greenfield contracts confirmed. One frontmatter discrepancy (DEC `implementation_paths` vs spec_v2 §A) resolved in favor of spec_v2.

**Step 2 (backend skeleton) UNBLOCKED.** Implementation begins with the `case_annotations/` package + `face_id` hash + tests.

# M-AI-COPILOT (collab-first) Tier-A · Dogfood Guide

> **DEC**: DEC-V61-098 · **State**: Accepted (Claude-Code-automated smoke 2026-04-30)
> **Date**: 2026-04-29 (initial) · 2026-04-30 (CFDJerry-gate retired)
> **Authored by**: Claude Code Opus 4.7 (1M context)
> **Smoke target**: `scripts/smoke/dogfood_loop.py` (run via
> `PYTHONPATH=. .venv/bin/python scripts/smoke/dogfood_loop.py`)
> **Why retired the human gate**: CFDJerry can't be agent-triggered, so
> the dev workflow can't depend on a human review step. The smoke
> script now covers everything an agent can verify (HTTP loop, BC
> dict generation, frontend boot); items that genuinely require human
> eyes (vtk.js rendering, glow effects, cross-tab UX) are noted as
> "human-only" below but are NOT acceptance gates.

---

## What landed

The M-AI-COPILOT Tier-A surface gives the engineer a way to **pin
`user_authoritative` annotations onto individual boundary faces** by
clicking the face in the 3D viewport during Step 3.

This is the collab-first foundation: it doesn't yet wire the AI
dialog (DialogPanel + envelope mode) into the [AI 处理] flow, but the
underlying contract — face_id stable hash + face_annotations.yaml
revision tokens + sticky invariant — is fully live.

### Pieces shipped

| Layer | Component | Status |
|---|---|---|
| Backend | `case_annotations/` package · face_id() + load/save_annotations | ✓ (Steps 2+3 · 28 tests) |
| Backend | `AIActionEnvelope` schema | ✓ (17 tests) |
| Backend | `setup-bc?envelope=1` route | ✓ (7 tests) |
| Backend | `GET/PUT /face-annotations` route | ✓ (10 tests) |
| Backend | `GET /face-index` (cell-id → face_id) | ✓ (9 tests) |
| Frontend | Viewport pickMode + face_id resolution | ✓ (4 tests · 15 total in Viewport) |
| Frontend | AnnotationPanel · DialogPanel | ✓ (14 tests across both) |
| Frontend | FacePickContext + Step3SetupBC integration · 409 re-fetch | ✓ (2 tests) |
| | **Total** | **~50 new tests · 119 backend pass · 123 frontend pass** |

### Codex audit trail

7 Codex rounds across 3 review packets — all closed:

| Packet | Round 1 | Round 2 | Round 3 |
|---|---|---|---|
| Steps 2+3 (case_annotations + envelope schema) | CHANGES_REQUIRED (HIGH .tmp symlink, MED signed-zero, LOW error_detail) | CHANGES_REQUIRED (HIGH lock-file containment) | APPROVE |
| Steps 6+7a (face-index + viewport + panels) | CHANGES_REQUIRED (HIGH primitive ordering — vtk.js actor map collision) | RESOLVED | — |
| Step 7b (FacePickContext + Step3 integration) | CHANGES_REQUIRED (HIGH 409 conflict re-fetch) | RESOLVED | — |

Reports under `reports/codex_tool_reports/dec_v61_098_*.md`.

---

## How to smoke-test

### 1. Start the backend + frontend

```bash
cd ui/backend && CFD_BACKEND_PORT=8010 ./.venv/bin/uvicorn ui.backend.main:app --port 8010 --reload
# (separate terminal)
cd ui/frontend && CFD_FRONTEND_PORT=5181 npm run dev
```

(Ports per project memory rule — never squat 5180/8000 used by other projects.)

### 2. Run the LDC dogfood path

1. Open `http://localhost:5181/workbench/<some-imported-case>` in the browser.
2. Step 1 should be `completed` automatically (case exists ⇒ import scaffold ran).
3. Step 2 — click `[AI 处理]` → mesh generates (gmsh + gmshToFoam). Verify wireframe appears.
4. Step 3 — click `[AI 处理]` → setup-bc splits patches into `lid` + `fixedWalls` + `frontAndBack`. The center pane switches from "viewport empty hint" to the colored 3D scene (lid red, walls gray, front/back semi-transparent blue).
5. **NEW** — once Step 3 reads `completed`, the viewport accepts left-clicks on faces.

### 3. Smoke the new face-pick UX

The acceptance criteria:

- **Click any face on the lid (top of cube).** The right-rail task panel surfaces an `AnnotationPanel` below the BC summary. The face_id badge truncates to ~12 chars.
- **Type a name** (e.g., `lid_main`). **Pick patch_type** (e.g., `wall`). **Optionally add notes** (e.g., `fixedValue U=(1 0 0)`).
- **Click Save.** The PUT goes through; the panel disappears (picked face cleared).
- **Click another face on the side walls.** A fresh AnnotationPanel surfaces.
- **Click the same face you just saved.** The form should be **pre-filled** with the saved name + patch_type + notes (re-seeded from existing annotation).
- **Modify the name and Save.** Should succeed.

### 4a. Smoke the real M9 Tier-B AI classifier (DEC-V61-100 Step 2)

The default envelope mode now invokes the real geometric classifier
(no `?ai_mode=` query param needed). Heuristics:

- LDC cube + no annotations → `uncertain` · 1 lid_orientation question
- LDC cube + lid pin verified on top plane → `confident` · runs setup_ldc_bc
- LDC cube + lid-named pin OFF top plane → `uncertain` (specific message
  pointing at the actual top-plane face_ids · prevents silent override)
- Channel/non-cube → `uncertain` until inlet+outlet pinned, then `blocked`
  with "non-LDC executor pending M10/M11" message
- No polyMesh / <8 vertices → `blocked`

Smoke runbook (LDC cube · default behavior · NO query param):

1. Navigate to `/workbench/<ldc-case-id>?step=3` (no `ai_mode`).
2. Click `[AI 处理]`. Expected:
   - DialogPanel surfaces with `lid_orientation` question
   - confidence badge: `uncertain`
   - prompt: "Cube geometry detected (aspect ratio ~1.000). Default lid: top face (+z, max_z=...). Click the lid face in the viewport to confirm (name it 'lid' in the dialog)."
3. Click the **top** face of the cube. Verify face hint shows "Picked: fid_xxx".
4. Click `[继续 AI 处理]`. Expected:
   - PUT face_annotations writes user_authoritative entry (name='lid', face_id matches top plane)
   - Wrapper re-runs envelope · classifier verifies face_id ∈ top_plane set → confident
   - setup_ldc_bc actually writes dicts (`0/`, `system/`)
   - Step completes
5. **Negative path**: try clicking a SIDE face and confirming with name='lid'. Expected: classifier stays uncertain with message "You pinned a face named 'lid', but it isn't on the top (+z) plane the LDC solver uses." — engineer must click the actual top face.

### 4b. Legacy dogfood substrate (DEC-V61-098 Step 1)

This validates the productized pick→annotate→re-run loop on the
**mock** substrate (force_uncertain mock — bypasses the real classifier
for testing the dialog UX without geometric verification).

1. Navigate to `/workbench/<case-id>?step=3&ai_mode=force_uncertain`.
2. An amber **"AI-COPILOT envelope mode"** banner appears at the top of the right rail. The banner confirms the dialog substrate is active.
3. Click `[AI 处理]`. Instead of completing immediately, the right rail surfaces a **DialogPanel** (amber outline) with:
   - confidence badge: `uncertain`
   - summary: "Set up LDC defaults: lid=N faces, walls=M faces. Please confirm the lid orientation."
   - one question (`lid_orientation`): "Confirm which face is the moving lid (default: top, +z). Click the lid face in the 3D viewport to confirm or select a different face."
   - face hint: "Click a face in the viewport to select." (amber)
4. **Click the lid face** (top of cube · z=1) in the viewport. Expected:
   - face hint changes to "Picked: fid_xxx…" (emerald)
   - the AnnotationPanel does NOT surface (the pick routes to the dialog question, not the panel)
   - `[继续 AI 处理]` button arms (no longer disabled)
5. Click `[继续 AI 处理]`. Expected:
   - the picked face is saved as `face_annotations.yaml` entry with `confidence: user_authoritative` and `annotated_by: human`
   - envelope re-runs with force flags cleared
   - returns `confident` (mock backend always confidents on re-run)
   - DialogPanel disappears, `✓ AI processing complete (envelope mode)` success surface appears
   - step completes (Step 4 unlocks)
6. Try `?ai_mode=force_blocked` for the blocked variant. Expected: rose-outline DialogPanel, [继续 AI 处理] still arms after picking the face, re-run completes.

**Negative tests** (optional but useful):
- Click `[AI 处理]` with `ai_mode=force_uncertain` but DON'T pick a face. Verify `[继续 AI 处理]` stays disabled.
- Open two tabs · in tab A start envelope-mode flow · in tab B do a manual face annotation save · come back to tab A and resume → expect mid-dialog 409 message "Annotations changed mid-dialog. Refreshed — please retry."

### 4c. Smoke the M9 Step 3 multi-question slot routing (DEC-V61-100 Step 3)

The geometric classifier (Step 2) emits **two** unresolved face questions
on non-cube channel geometries (`inlet_face` + `outlet_face`). Step 3
(commits faa2e08 + a54f4b7 + 6ae9a3b · Codex 3-round arc R3 APPROVE)
hardens the multi-q UX so the engineer never silently picks the wrong
slot.

Smoke runbook (channel · default behavior · NO query param):

1. Import a non-cube geometry (anything where the bounding box is NOT
   ~1:1:1 — a straight rectangular duct works). Run Step 2 mesh.
2. Step 3 → `[AI 处理]`. Expected:
   - DialogPanel surfaces with **two** rows: `inlet_face` + `outlet_face`
   - confidence badge: `uncertain`
   - both rows show the hint **"Click 'Select this face' to direct your
     next pick here."** (NOT the legacy "click a face to select")
   - `[继续 AI 处理]` is **disabled** until both have a picked face_id
3. Click in the viewport directly (without first clicking "Select this
   face"). Expected: nothing happens — no row gets a `Picked: …` hint,
   AnnotationPanel does NOT surface (Codex R1 Finding 2 closure).
4. Click **"Select this face"** on the `inlet_face` row. Expected:
   - that row's button label flips to `Active` (and goes disabled)
   - the row gets an emerald border
   - hint changes to **"Click a face in the viewport now."**
   - `data-question-active="true"` on the row (devtools)
5. Click an actual face in the viewport. Expected:
   - the picked face_id binds to `inlet_face` (hint shows `Picked: fid_…`)
   - active highlight clears (button is back to `Re-pick`)
   - the OTHER row (`outlet_face`) is **still empty** — auto-fallback is
     deliberately disabled in multi-q mode (Codex R1 Finding 1 closure)
6. Click **"Select this face"** on `outlet_face`, then pick the outlet.
   Expected: same routing pattern; both rows now have picks.
7. Click `[继续 AI 处理]`. Expected (UPGRADED at DEC-V61-101 · commits
   b7986ba + e470618 + 44d1716): PUT face_annotations writes BOTH
   user_authoritative entries; envelope re-runs; classifier returns
   **`confident`** (no longer "blocked: pending M11/M12"). Wrapper
   invokes `setup_channel_bc` which:
   - Splits `polyMesh/boundary` into 3 named patches: `inlet` /
     `outlet` (both `type patch`) + `walls` (`type wall`)
   - Writes the icoFoam laminar dict tree: `0/U` (inlet=fixedValue
     (1 0 0) · outlet=zeroGradient · walls=noSlip), `0/p`
     (inlet=zeroGradient · outlet=fixedValue 0 · walls=zeroGradient),
     `constant/physicalProperties` (ν=0.01), `constant/momentumTransport`
     (laminar), and `system/{controlDict, fvSchemes, fvSolution}`
   - Reports the channel summary: `inlet=N face · outlet=M face ·
     walls=K faces · Re≈100 (icoFoam laminar)` for unit-cross-section
     channels (Re uses min nonzero bbox extent as L_char)
   - Step 4 unlocks · engineer can run icoFoam against the channel

**Negative tests:**
- Click "Select this face" on inlet, pick face A; click "Select this
  face" on outlet, pick face B — expect inlet=A, outlet=B (no race).
  This is the rapid-double-pick scenario Codex Step 1 R1 flagged.
- Toggle `?ai_mode=force_uncertain` mid-session (after a real-classifier
  envelope is open). Expected: dialog clears immediately + any in-flight
  envelope request from the previous mode is dropped (no late-arriving
  state writes — Codex R1+R2 Finding 1 closure via aiModeGenRef).
- **Stale-pin path** (DEC-V61-101 R1 HIGH closure): pin inlet+outlet,
  then re-mesh Step 2 (so face_ids change). Click `[继续 AI 处理]` →
  expect 422 `channel_pin_mismatch` with message "stale pins after
  classifier verification" or "no boundary face matched any inlet
  pin". Re-pick faces → cycle resumes normally.
- **Same-face-as-both** (DEC-V61-101 disjointness): pin one face as
  `inlet_a`, then pin the SAME face as `outlet_b`. Click resume →
  expect classifier `uncertain` with `channel_pin_mismatch` question
  explaining which face_id was double-pinned.

### 6. Smoke the 409 conflict path (advanced)

This validates the Codex Step 7b R1 fix — useful but not required for visual smoke:

1. Open the case in **two browser tabs**.
2. Pick a face in tab A; type a name; **don't save yet**.
3. In tab B: pick the **same face**, type a different name, **save** → revision bumps from 1→2.
4. Back in tab A: click Save → expect inline error `Revision conflict (was 1, latest 2). Refreshed — please retry.`
5. Click Save again in tab A → succeeds with `if_match_revision: 2` (the panel auto-refreshed to the latest doc).

### 7. Smoke checks for regressions

- Steps 1/2/4/5 viewport: pickMode must be **disabled** outside Step 3. Click on viewport in Step 1 → no AnnotationPanel surfaces.
- Step 4 [AI 处理] (solver) and Step 5 (results) — should work exactly as before.
- StepPanelShell tests: 16 frontend test files all green (run `cd ui/frontend && npx vitest run`).

---

## Known scope gaps (deferred)

These are NOT broken — they're explicitly out of Tier-A scope:

| Gap | Where it goes |
|---|---|
| ~~`[AI 处理]` doesn't yet route through envelope mode (no DialogPanel rendering)~~ | ✅ CLOSED at M9 Step 1 commit aa4d3f1 |
| Face-pick highlighting (selected face glow on the picked face) | M11 Mesh Wizard (face-pick UI extension) |
| ~~Annotations don't auto-influence the next `[AI 处理]` envelope~~ | ✅ CLOSED at M9 Step 2 commit 11b81ba (real classifier consumes face_annotations.yaml) |
| `face_annotations.yaml` doesn't appear in audit-package zip yet | separate Tier-A line item per spec §F |
| Multi-face batch save | not in scope — engineer saves one face at a time |
| ~~Channel/non-cube executor (after multi-q `inlet_face`+`outlet_face` are pinned, classifier returns `blocked`)~~ | ✅ CLOSED at DEC-V61-101 commits b7986ba + e470618 + 44d1716 (laminar icoFoam channel executor · Codex R2 APPROVE) |
| Turbulence models (channel currently always laminar) | M12 multi-solver routing |
| Boundary layer prism control (no y+ targeting) | M11 Mesh Wizard |
| BC value override UI (engineer can't yet edit U_inlet=(1,0,0), p_outlet=0, ν=0.01) | M12 |
| Multi-inlet / multi-outlet (only ONE of each per dialog) | M12 / out of M9 scope |

---

## Acceptance for §E Step 11 (DEC closure)

DEC flips to `Accepted` when `scripts/smoke/dogfood_loop.py` exits 0.
The script covers:

- §4a LDC cube full loop (uncertain → pin lid → confident · dicts on disk)
- §4c channel full loop (uncertain → pin inlet+outlet → confident · 3-patch split)
- §7 negative paths (lid-on-side stays uncertain · bogus pins → channel_pin_mismatch)
- Backend pytest slice (97 tests) + frontend vitest (131 tests)
- Vite dev server boot probe (HTTP 200 · HTML hydrated)
- **Step 4 real icoFoam solve in Docker** (opt-in via `--with-solver` ·
  ~3 min · validates that the BC dicts the executor writes actually
  converge end-to-end on a real meshed LDC). Skipped by default to
  keep the fast-loop smoke fast; run before merging big changes:
  `PYTHONPATH=. .venv/bin/python scripts/smoke/dogfood_loop.py --with-solver`

The §11.1 BREAK_FREEZE quota counter went to 3/3 at this acceptance;
further workbench/** changes route through the normal feature-freeze
process.

## Human-only checks (not part of automated gate)

These remain useful for engineers running the dev server in a real
browser, but the dev workflow does NOT block on them:

- vtk.js GLTFImporter rendering the BC scene (color tint per patch)
- Emerald glow on the active face-question slot
- Cross-tab 409 conflict UX flow (advanced §6)
- Real face-pick from the 3D viewport (the smoke uses HTTP shortcuts)
- Channel real-solver smoke (the `--with-solver` opt-in currently
  validates LDC only — channel solve will be added once a small
  channel STL fixture lands in `examples/imports/`)

---

## Counter & retro accounting

- `autonomous_governance_counter_v61`: +1 (this DEC)
- RETRO-V61-001 risk-tier triggers fully discharged: byte-reproducibility-sensitive (face_id contract) + new API contract (/face-index) + multi-file frontend + UX-driven first impl + ≤70% self-pass-rate
- Kogami: NOT triggered (4-condition self-check still passes after implementation)
- Codex 7-round arc: counter +0 (within-arc Codex review cadence per RETRO-V61-001 — does not multiply the main counter)

## Next milestone after closure

Per `.planning/strategic/workbench_long_horizon_roadmap_2026-04-29.md`:

- **M9 — Tier-B AI** (Era 1 LOOP SPINE first milestone): productize the
  pick→annotate→re-run loop. The collab DialogPanel (already built and
  tested at 7 tests) wires into `[AI 处理]`'s envelope-mode response so
  the AI's `unresolved_questions` get rendered, the engineer answers
  them by picking faces + selecting options, and `[继续 AI 处理]`
  re-runs setup-bc with the answers folded into the annotations doc.

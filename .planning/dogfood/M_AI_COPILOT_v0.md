# M-AI-COPILOT (collab-first) Tier-A · Dogfood Guide

> **DEC**: DEC-V61-098 · **State**: Implementation Complete · Awaiting visual smoke
> **Date**: 2026-04-29
> **Authored by**: Claude Code Opus 4.7 (1M context)
> **Smoke target**: CFDJerry · Step 10 of spec_v2 §E

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

### 4. Smoke the 409 conflict path (advanced)

This validates the Codex Step 7b R1 fix — useful but not required for visual smoke:

1. Open the case in **two browser tabs**.
2. Pick a face in tab A; type a name; **don't save yet**.
3. In tab B: pick the **same face**, type a different name, **save** → revision bumps from 1→2.
4. Back in tab A: click Save → expect inline error `Revision conflict (was 1, latest 2). Refreshed — please retry.`
5. Click Save again in tab A → succeeds with `if_match_revision: 2` (the panel auto-refreshed to the latest doc).

### 5. Smoke checks for regressions

- Steps 1/2/4/5 viewport: pickMode must be **disabled** outside Step 3. Click on viewport in Step 1 → no AnnotationPanel surfaces.
- Step 4 [AI 处理] (solver) and Step 5 (results) — should work exactly as before.
- StepPanelShell tests: 16 frontend test files all green (run `cd ui/frontend && npx vitest run`).

---

## Known scope gaps (deferred)

These are NOT broken — they're explicitly out of Tier-A scope:

| Gap | Where it goes |
|---|---|
| `[AI 处理]` doesn't yet route through envelope mode (no DialogPanel rendering) | Step 7c (next session) |
| Face-pick highlighting (selected face glow) | Tier-B / M9 |
| Annotations don't auto-influence the next `[AI 处理]` envelope | Tier-B / M9 |
| `face_annotations.yaml` doesn't appear in audit-package zip yet | separate Tier-A line item per spec §F |
| Multi-face batch save | not in scope — engineer saves one face at a time |

---

## Acceptance for §E Step 11 (DEC closure)

The DEC flips from `Implementation Complete · Awaiting CFDJerry visual smoke` to `Accepted` when:

- [ ] CFDJerry runs the smoke (steps 2-3 above) and reports the face-pick → name → save cycle works for at least 2 faces
- [ ] No regression in Steps 1/2/4/5 (the existing LDC dogfood path still completes end-to-end)
- [ ] One sentence of ratification in this file under "CFDJerry ratification" section below

After ratification, the §11.1 BREAK_FREEZE quota counter goes to 3/3 (final slot), and any further workbench/** changes route through the normal feature freeze process.

## CFDJerry ratification

(awaiting smoke)

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

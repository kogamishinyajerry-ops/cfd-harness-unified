# V61-128 Codex review chain · DEC-V61-128

> **DEC**: `.planning/decisions/2026-05-06_v61_128_patch_chip_derived_coloring.md`
> **Scope**: Patch chip derived coloring on Step 2 mesh-quality card. Frontend-only — `PatchChips` component derives chip tone from already-fetched `checkmesh_mesh_ok` + `patch_face_counts`. No backend, no schema, no contract change. Heavy per-cell aggregation path explicitly deferred to V129.
> **Risk-tier triggers** (RETRO-V61-001): UI interaction polish (single-file but treated as positive given V127's calibration miss).
> **Self-pass-rate prediction**: 75% / 1-2 rounds (narrow no-cross).
> **Outcome**: **APPROVE clean at R1** — 1 round (R0 + R1 verdict), **bottom of prediction band**.

---

## R0 — Implementation (commit 02d447f)

Surface area:
- `ui/frontend/src/pages/workbench/step_panel_shell/MeshQualityCard.tsx` (~50 LOC delta on `PatchChips`)
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/MeshQualityCard.test.tsx` (+5 scenarios)
- `.planning/decisions/2026-05-06_v61_128_patch_chip_derived_coloring.md` (NEW DEC)

Tone derivation rules:
| Condition | Tone | a11y label |
|---|---|---|
| `face_count === 0` | rose | explicit "empty" suffix |
| V126 `mesh_ok === false` && face_count > 0 | amber | (count text) |
| V126 `mesh_ok === true` | green | (count text) |
| V126 `mesh_ok === null` OR V122 fallback | neutral | (count text) |

Tests: 24/24 pass (19 prior + 5 new V128 scenarios).
Backend: untouched.

## R1 — APPROVE clean at 02d447f

> *"The patch-chip coloring change is self-contained, preserves the existing mesh-quality data contract, and the added tests cover the new tone-derivation paths without revealing a functional regression in the reviewed diff."*

Chain closed. V128 → Accepted at 02d447f.

---

## Calibration data point — narrow no-cross baseline holds

| Metric | Value |
|---|---|
| Predicted rounds | 1-2 |
| Actual rounds | **1** (bottom of band) |
| Predicted self-pass-rate | 75% |
| Actual self-pass-rate | 100% (1/1) |
| LOC delta | ~50 frontend + ~80 test (single-file) |
| Cross-contract surfaces | None — pure render-derive logic |
| Verbatim-exception eligibility | N/A (R1 was APPROVE, no fixes needed) |

**Calibration narrative**: V127 took 8 rounds (predicted 3) on cache-design cross-contract surface. V128 was deliberately scoped to recover prediction confidence — single file, derive-from-existing-data, no new contract surfaces. Result: **R1 APPROVE clean at the BOTTOM of the prediction band**, validating that V123 §L1 "no-cross ≈ 1-3 rounds" baseline still holds when the implementation truly is no-cross.

The methodology patch candidate from V127's chain report ("treat module-level cache + cross-component invalidation as cross-contract") remains queued for the next RETRO. V128 doesn't change that — it just shows that when we correctly identify a no-cross scope, the existing baseline works.

## Phase E continues

V128 closes the chip-coloring gap V127 left open (chips were uniformly neutral grey). The mesh-quality card now provides three layers of visual signal in Phase E shell-style:
1. **Verdict pill** (top-row global Mesh OK / Failed / has warnings / skipped — V127)
2. **Quality gauges** (skewness / non-orthogonality / aspect ratio with band-colored ladders + needles — V127)
3. **Per-patch chips** (tone per patch — V128)

Next on the seven-phase roadmap:
- **V129** (Phase E continuation): cell-level checkMesh data via `-writeAllFields`, per-patch metric aggregation, real per-patch quality numbers (not just derived from global pass/fail). Cross-contract — predict 4-6 rounds.
- **Phase E v2**: 3D viewport per-cell coloring on polyMesh boundary surface. Separate DEC.
- **Phase B** (Physics + BC): extend the V127 visual-signal style to Step 3's BC selection.

# V61-129a Codex review chain · DEC-V61-129a

> **DEC**: `.planning/decisions/2026-05-06_v61_129a_per_patch_severe_non_ortho.md`
> **Scope**: Per-patch severe-non-ortho count parsed from checkMesh's `nonOrthoFaces` faceSet (constant/polyMesh/sets/nonOrthoFaces) via `-allGeometry -allTopology` flags. Backend (parser + schema + analyzer) + frontend consumer. Heavy V129b per-cell field aggregation deferred.
> **Risk-tier triggers** (RETRO-V61-001): cross-contract — backend schema extension + frontend type mirror + new parser surface.
> **Self-pass-rate prediction**: 60% / 3-4 rounds (cross-contract per V123 §L1).
> **Outcome**: **APPROVE clean at R3** — 3 rounds (R0 + R1 fix + R2 fix + R3 verdict), **bottom of prediction band**.

---

## R0 — Implementation (commit 9e356f4)

Surface area:
- `ui/backend/services/mesh_quality/checkmesh_runner.py` (~30 LOC delta)
  - `-allGeometry -allTopology` flags on checkMesh exec
  - sentinel-delimited tail: `cat constant/polyMesh/sets/nonOrthoFaces` after checkMesh stdout
  - `_parse_faceset_body` parser tolerant of OpenFOAM 10 banner+FoamFile header
  - `CheckMeshResult` extended with `severe_non_ortho_face_ids: tuple[int, ...]`
- `ui/backend/services/mesh_quality/analyzer.py` (~50 LOC delta)
  - `_read_patch_ranges` returns `dict[str, tuple[int, int]]` (startFace, nFaces)
  - `_read_patch_face_counts` becomes thin wrapper over the above
  - `aggregate_severe_faces_per_patch(face_ids, patch_ranges)` linear-scan map → per-patch count dict
  - `patch_ranges` threaded into `_try_run_checkmesh`
- `ui/backend/services/mesh_quality/schemas.py` adds optional `checkmesh_n_severe_non_ortho_faces_per_patch: dict[str, int] | None`
- `ui/frontend/src/pages/workbench/step_panel_shell/types.ts` mirrors the field
- `ui/frontend/src/pages/workbench/step_panel_shell/MeshQualityCard.tsx` PatchChips: new precedence level — V129a dict overrides V128 amber/green when present
- Empirical fixture: real OpenFOAM 10 nonOrthoFaces body captured from a deliberately skewed mesh on the cfd-openfoam container

R0 backend regression: 1230 passed (+ 4 pre-existing failures unrelated to mesh-quality).
R0 frontend: 24 → 29 tests pass; tsc clean.

## R1 — CHANGES_REQUIRED → fixed at 988a740

| Severity | Finding | Fix |
|---|---|---|
| P1 | Bash chain `checkMesh ...; echo; cat ... \|\| true` set the chain's exit status to 0 regardless of checkMesh's actual exit. The trailing `cat ... \|\| true` always succeeds, masking checkMesh's exit code; corrupt-polyMesh / missing-required-files would silently fall through as bogus parsed-success V126 responses instead of the intended `checkmesh_exit_nonzero` 502. | Capture `rc=$?` BEFORE the echo+cat tail; `exit $rc` at the end. Faceset body still gets captured (echo+cat run unconditionally before exit) but exit status reflects checkMesh. Added regression test running the actual bash chain against `/bin/bash` with checkMesh stubbed as `false` — would catch any future revert. |

## R2 — CHANGES_REQUIRED → fixed at 18bc660

| Severity | Finding | Fix |
|---|---|---|
| P2 | R1's regression test substituted on `polymesh.parent.parent`, a string never present in the production bash_cmd (the runner's actual cd target is `container_work = /tmp/cfd-harness-cases-checkmesh/<case>_<uuid>`). The cd line stayed unchanged in test_chain → host bash early-exited from the missing container path BEFORE reaching the stubbed `false` checkMesh. The exit-1 assertion passed for the wrong reason; a future regression that snapshotted `$?` before checkMesh would still satisfy it. | Regex-rewrite `cd /tmp/cfd-harness-cases-checkmesh/...` → `cd <tmp_path>` so the substitution actually fires. Defensive post-condition `assert "cd /tmp/cfd-harness-cases-checkmesh/" not in test_chain` would have caught the R0/R1 bug. Added twin sanity check: same chain with `true` stub must exit 0, ensuring a "hard-coded exit 1" regression doesn't pass either branch. |

## R3 — APPROVE clean at 18bc660

> *"The commit only adjusts the regression test, and the new substitutions plus the added success-path sanity check make the test meaningfully better at exercising the intended rc-preservation behavior. I did not identify a discrete bug introduced by this change."*

Chain closed. V129a → Accepted at 18bc660.

---

## Calibration data point — empirical-capture discipline pays off

| Metric | Predicted | Actual |
|---|---|---|
| Rounds | 3-4 (cross-contract) | **3** (bottom of band) |
| Self-pass-rate | 60% | actual 67% (2 of 3 review rounds returned APPROVE; 1 R1 fix + 1 R2 fix) |
| P1s caught | — | 1 (R1: bash-chain rc swallow) |
| P2s caught | — | 1 (R2: test substitution missed the actual cd target) |
| LOC delta | — | ~80 backend + ~50 frontend (single new field, single new precedence level) |
| Cross-contract surfaces | backend parser + schema + frontend consumer | as predicted |
| Verbatim-exception eligibility | — | None (R1 fix added a bash detail + new regression test; R2 fix was self-correcting test instrumentation) |

**Empirical-capture discipline narrative**: V128's chain report ranked V129 as 5-7 round arc (heavy V129b path). V129a's deliberate narrowing — single-metric count from existing checkMesh output — kept the surface to one new schema field + one new tone precedence level. Crucially, before writing `_parse_faceset_body`, the runner build was probed against the actual cfd-openfoam container with a deliberately skewed mesh; the captured `_REAL_FACESET_BODY` fixture lives in the test file and locks the OpenFOAM-10 format. Without that empirical capture, R0→R1 likely would have spent extra rounds on parser format guesses.

The two findings caught were both genuinely real:
1. **R1 P1** is a serious silent-failure bug — exactly the kind of thing static review excels at vs runtime testing
2. **R2 P2** caught a "test that passes for the wrong reason" — also a static-review specialty

Neither was a calibration miss; both were caught the first round they appeared. V123 §L1 cross-contract baseline (3-4 rounds) confirmed.

---

## Phase E continues — V128/V129a synergy

Phase E shell-entry visual-signal stack now has **four layers**:
1. **Verdict pill** (top-row global Mesh OK / Failed / has warnings / skipped — V127)
2. **Quality gauges** (skewness / non-orthogonality / aspect ratio with band-colored ladders + needles — V127)
3. **Per-patch chips** (tone per patch — V128 derived; V129a real per-patch when checkMesh writes the faceSet)
4. **Severe-face suffix** (chip text "·N severe" when V129a count > 0; a11y-redundant with rose tone)

V129a's PatchChips precedence rule — per-patch severe>0 → rose, per-patch severe=0 → green even if mesh_ok=false globally — is the first time the engineer can localize mesh quality issues to specific patches without reading the failed_checks list.

Next on the seven-phase roadmap (per V128 chain report):
- **V129b** (cell-level field aggregation via `-writeAllFields` for per-patch max-skewness / max-aspect-ratio): defer until V129a proves useful in dogfood
- **Phase E v2**: 3D viewport per-cell coloring on polyMesh boundary surface
- **Phase B**: extend visual-signal style to Step 3 BC selection

V61-129a counter +1 (autonomous_governance: true). Total Phase E counter: V127 + V128 + V129a = +3.

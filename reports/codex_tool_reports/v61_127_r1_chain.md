# V61-127 Codex review chain · DEC-V61-127

> **DEC**: `.planning/decisions/2026-05-05_v61_127_mesh_quality_card.md`
> **Scope**: Mesh-quality card · Fluent-style gauges + per-patch chips · Phase E shell entry. New `MeshQualityCard.tsx` (~500 LOC) + `Step2Mesh.tsx` mount + `api/client.ts` extension (`getMeshQuality(case_id, { runCheckmesh })` + cache-busting `mesh:mutated` event dispatch). First deliberately Fluent-styled UI element in the workbench.
> **Risk-tier triggers** (RETRO-V61-001): multi-file frontend + UI interaction mode change + first user-visible Fluent-style polish.
> **Self-pass-rate prediction**: 70% / 3 rounds (no-cross-contract per V123 §L1).
> **Outcome**: **APPROVE clean at R8** — 8 rounds total, **significantly above prediction band**. See "Calibration miss" below.

---

## R0 — Implementation (commit 1404496)

Surface area:
- `ui/frontend/src/pages/workbench/step_panel_shell/MeshQualityCard.tsx` (NEW · ~500 LOC)
- `ui/frontend/src/pages/workbench/step_panel_shell/types.ts` extended with `MeshQualityReport` discriminated union (V122/V126), `MeshQualitySeverity`, `MeshQualityWarning`
- `ui/frontend/src/api/client.ts` adds `getMeshQuality(caseId, { runCheckmesh })` returning the union
- `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step2Mesh.tsx` mounts the card under the existing mesh-success card
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/MeshQualityCard.test.tsx` (NEW · 8 scenarios)

R0 backend regression: untouched (frontend-only DEC).

## R1 — CHANGES_REQUIRED → fixed at 2cded93

| Severity | Finding | Fix |
|---|---|---|
| P2-1 | `meshGenSeq>0` gate broke the "review existing mesh" workflow — Step 2 marks complete from the /mesh/render probe but meshGenSeq stays 0 unless user re-runs mesh | Always-mount when `caseId` set; rely on card's 404 → idle self-hide for unmeshed cases |
| P2-2 | Aspect-ratio gauge mapped linearly with `clampPercent(value, axisMax=1e4)` → 100 (warning band) sat at 1% of the bar, visually invisible | `scale="log"` param; `(log10(v+1)) / (log10(axisMax+1))` |

## R2 — CHANGES_REQUIRED → fixed at 67e6d06

| Severity | Finding | Fix |
|---|---|---|
| P2-1 | Step 2 ↔ 3/4 navigation re-runs Docker checkMesh against the same polyMesh; ~20-60s extra per round-trip | Module-level `meshQualityCache: Map<caseId, LoadState>`; cache hit on remount renders instantly |
| P2-2 | Log scale anchored at 0, not 1 — `log10(0)` undefined, "good" band 0-10 collapsed visually | Canonical `(log10(v) - log10(axisMin)) / (log10(axisMax) - log10(axisMin))` with `axisMin=1` for aspect ratio |

7-of-8 tests broke after R2 (module cache leaked across tests). Added `__clearMeshQualityCacheForTests` export, called in `beforeEach`.

## R3 — CHANGES_REQUIRED → fixed at 871cb49

| Severity | Finding | Fix |
|---|---|---|
| P1 | Cache key `${caseId}:${meshGenSeq}` was broken because `meshGenSeq` lives in `Step2Mesh` local state and resets to 0 on remount → cache always missed on Step 2↔3 nav | Cache keyed on `caseId` alone; explicit `invalidateMeshQualityCache(caseId)` from Step2Mesh's `triggerMesh`; module-level `ai-coach:proposal-applied` listener for AI-driven regenerate |
| P2 | V126 graceful-degradation responses (checkmesh_mesh_ok=null, container down) were cached → operator starting the container later still saw stale "skipped" entry | Detect `report_kind === "v126" && checkmesh_mesh_ok === null`; skip `cache.set` for that branch |

## R4 — CHANGES_REQUIRED → fixed at a2d66ff

| Severity | Finding | Fix |
|---|---|---|
| P2 | Cache invalidation lived in Step2Mesh's `triggerMesh` only. Step 3 BC setup rewrites `constant/polyMesh/boundary` (line 1022 in `bc_setup_from_stl_patches.py`) and the legacy `/workbench/case/:caseId/mesh` wizard re-runs `api.meshImported` — neither triggered cache busting | Move cache invalidation INTO the api client: dispatch `mesh:mutated` window event from `meshImported`/`setupBC`/`setupBCWithEnvelope` success paths; MeshQualityCard module-level listener handles it; remove now-redundant explicit `invalidateMeshQualityCache(caseId)` in Step2Mesh |

## R5 — CHANGES_REQUIRED → fixed at bd5e566

| Severity | Finding | Fix |
|---|---|---|
| P2 | `setupBCWithEnvelope` dispatched `mesh:mutated` for every 200 — but blocked/uncertain envelope paths (force_blocked=1, classifier short-circuit) return 200 BEFORE touching polyMesh, spuriously invalidating the cache and regressing R3's caching | Gate on `result.confidence === "confident"` |

## R6 — CHANGES_REQUIRED → fixed at 0bedd71

| Severity | Finding | Fix |
|---|---|---|
| P2 | R5 gate missed the `force_uncertain` dogfood path. Backend (`ai_actions/__init__.py setup_bc_with_annotations`): `force_uncertain=1` runs `setup_ldc_bc` THEN wraps response as 'uncertain' — polyMesh IS written even though wire envelope is 'uncertain' | Dispatch on `confidence === "confident"` OR `options.forceUncertain === true`; the wire envelope can't disambiguate force_uncertain from classifier-uncertain (both 'uncertain'); caller's request flag does |

Backend polyMesh-mutation map captured inline as a comment block in `client.ts`.

## R7 — CHANGES_REQUIRED → fixed at 5fe9021

| Severity | Finding | Fix |
|---|---|---|
| P3 | Both-debug-flags-set case: spec_v2 §A3 makes `force_blocked` win server-side, response is 'blocked', polyMesh untouched. R6's gate dispatched anyway because `forceUncertain === true` | Gate on response confidence FIRST, then caller intent: `confident` always; `uncertain && forceUncertain` writes; `uncertain` alone (classifier short-circuit) skips; `blocked` never |

Severity dropped P2→P3, signal verdict was approaching.

## R8 — APPROVE clean at 5fe9021

> *"The change aligns the frontend's `mesh:mutated` dispatch with the backend contract when both debug force flags are present, and the added test covers that precedence rule. I did not identify any regressions or correctness issues in the modified code."*

Chain closed. V127 → Accepted at 5fe9021.

---

## Calibration miss — predicted 3, actual 8

| Metric | Predicted | Actual |
|---|---|---|
| Rounds | 3 (no-cross baseline) | **8** (R0 + 7 review rounds) |
| Self-pass-rate | 70% | actual ~12% (1/8 rounds passed) |
| P1s caught | — | 1 (R3: cache-key local-state bug) |
| P2s caught | — | 8 (R1 always-mount + log scale, R2 perf cache + log anchor, R3 graceful-degrade caching, R4 cache producer fan-out, R5 envelope-confidence gate, R6 force_uncertain semantics) |
| P3s caught | — | 1 (R7 both-flags precedence) |
| Verbatim-exception eligibility | — | None (most rounds touched ≥2 files OR exceeded 20-LOC ceiling) |

**Why the prediction missed**: V123 §L1 calibration baseline (no-cross ≈ 1-3 rounds) holds for **isolated component or backend-route DECs**. V127 became cross-contract on the **cache-design surface**: each finding R3-R7 was a different facet of the cache-invalidation contract between (a) the api client (event producer), (b) the MeshQualityCard module-level listener (event consumer), (c) Step2Mesh's local invalidation, (d) the backend's polyMesh-mutation contract on each of three routes (meshImported / setupBC / setupBCWithEnvelope), and (e) the envelope-mode `confidence × force_flag` truth table. The DEC's risk register flagged none of these; the surface scan disposition ("extend") was correct but understated the contract surface area.

**Methodology patch candidate** (for next RETRO):
> When introducing **module-level caches with cross-component invalidation**, treat the cache producer ↔ consumer ↔ external-mutation contract as a cross-contract surface for §L1 prediction purposes, regardless of whether the implementation is single-file. Predict 4-6 rounds, not 1-3.

The chain is genuinely productive — every Codex finding was correct and caught a real regression vector — but the calibration baseline drifted.

---

## Phase E (Fluent shell UX) shell entry — closed

V127 ships the first deliberately Fluent-styled UI element. The 3D-viewport-with-per-cell-coloring variant (Phase E v2) lands in a separate DEC after polyMesh surface extraction is wired (out of scope V127).

V127 closes the Phase A→E handoff: the engineer can now SEE checkMesh data (skewness / non-orthogonality / aspect ratio gauges + per-patch chips + verdict pill), not just have the AI read it. The cache surface is hardened against every known polyMesh-mutation path (meshImported, setupBC, setupBCWithEnvelope including dogfood force flags, ai-coach regenerate_mesh proposals).

Next: base review for cadence trailer; push V127 chain to origin/main; choose Phase E v2 (per-cell viewport coloring) or Phase B (Physics + BC) per the seven-phase roadmap.

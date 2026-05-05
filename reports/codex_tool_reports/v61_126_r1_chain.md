# V61-126 Codex review chain · DEC-V61-126

> **DEC**: `.planning/decisions/2026-05-05_v61_126_checkmesh_integration.md`
> **Scope**: Docker checkMesh integration · opt-in `?run_checkmesh=true` query param augments V122 mesh-quality report with OpenFOAM-derived skewness, non-orthogonality, aspect-ratio metrics + mesh_ok verdict.
> **Risk-tier triggers**: new top-level service file (checkmesh_runner.py), Docker SDK + OpenFOAM container coupling, schema extension, route extension with new query param, cross-contract per V123 §L1.
> **Self-pass-rate prediction**: 50% / 4-6 rounds (cross-contract: container management is a new contract surface).
> **Outcome**: **APPROVE clean at R6** — 6 rounds total, at the top of the cross-contract prediction band.

---

## R0 — Implementation (commit dfd63d2)

Surface area:
- `services/mesh_quality/checkmesh_runner.py` (NEW · ~280 LOC) mirroring `to_foam.py` Docker SDK pattern
- `services/mesh_quality/schemas.py` extended with 6 optional `checkmesh_*` fields
- `services/mesh_quality/__init__.py` exports `CheckMeshError`, `CheckMeshResult`, `run_checkmesh`
- `services/mesh_quality/analyzer.py` adds `run_checkmesh` kwarg + `_try_run_checkmesh` graceful-degradation wrapper
- `routes/mesh_quality.py` adds `run_checkmesh: bool = False` query param + `CheckMeshError` → HTTP 502
- `services/llm_coach/prompts.py` mesh section surfaces checkMesh metrics
- `tests/test_checkmesh_runner.py` (NEW · 16 tests · all pass)

R0 backend regression: 1239 passed, 5 pre-existing failures unrelated.

## R1 — CHANGES_REQUIRED → fixed at 1d188de

| Severity | Finding | Fix |
|---|---|---|
| P1 | checkMesh refuses to start without `system/controlDict` | Stage `_MINIMAL_CONTROL_DICT` via heredoc `bash exec_run` |
| P2-1 | `container_work` derived from case_dir.name only — concurrent calls clobber each other | Append `uuid.uuid4().hex[:12]` per-call; tail bash `rm -rf` for cleanup |
| P2-2 | V122 backward-compat: adding fields to base schema serialized null checkmesh_* in every response | Split into base `MeshQualityReport` (V122) + `MeshQualityReportV126(MeshQualityReport)` extension; `analyze_mesh_quality` returns the right type; route uses `response_model=None`; prompts duck-types via `getattr` |

## R2 — CHANGES_REQUIRED → fixed at 536a9cd

| Severity | Finding | Fix |
|---|---|---|
| P2-1 | `response_model=None` erased OpenAPI 200-response schema entirely | Replace with union `MeshQualityReportV126 \| MeshQualityReport` |
| P2-2 | UUID workspace cleanup only on happy path — put_archive fail / controlDict raise leaks orphan dirs forever | Wrap full lifecycle in `try/finally` with best-effort `rm -rf` cleanup |

## R3 — CHANGES_REQUIRED → fixed at e774324

| Severity | Finding | Fix |
|---|---|---|
| P2 | Union still non-discriminable: V126 subclasses base + base allows extras → V126 payload validates against both branches | `model_config = ConfigDict(extra="forbid")` on base schema |

## R4 — CHANGES_REQUIRED → fixed at 899bc39

| Severity | Finding | Fix |
|---|---|---|
| P2 | Even with extra="forbid", base-shape payload still validates against V126 (all checkmesh_* optional) — overlap remains | Add required `report_kind: Literal["v122"]` / `Literal["v126"]` discriminator field to each schema; expose `MeshQualityReportResponse` as Pydantic Annotated discriminated union via `Field(discriminator="report_kind")` |

OpenAPI emission verified post-R4: `oneOf` with explicit `discriminator: {propertyName: "report_kind", mapping: {v122: ..., v126: ...}}`.

## R5 — CHANGES_REQUIRED → fixed at f783457

| Severity | Finding | Fix |
|---|---|---|
| P2 | `report_kind` had `default="v122"` / `"v126"` → Pydantic emitted it as OPTIONAL in OpenAPI's `required` array, schema-driven clients still saw it as optional | Change to `Field(...)` (required); analyzer.py + 3 tests now pass `report_kind` explicitly at construction |

OpenAPI emission verified post-R5: `Base required: ['report_kind', ...]`, `V126 required: ['report_kind', ...]`.

## R6 — APPROVE clean at f783457

> *"The change consistently updates the only in-repo construction sites after making `report_kind` required, and the schema/analyzer changes align with the intended OpenAPI discriminator fix. I did not find a discrete regression in the touched production paths."*

Chain closed. V126 → Accepted at f783457.

---

## CRS fallback datapoint (per V61-119 §L2)

While 86gs R3 was processing for ~33min (relay buffering, low CPU = network-bound), launched a parallel CRS-backend review of the same R2 commit. **CRS gpt-5.4 high gave APPROVE; 86gs gpt-5.4 xhigh caught the discriminable-union finding R3 surfaced.** This validates V119 §L2 protocol: CRS high < 86gs xhigh for governance reviews; **don't fall back to CRS for risk-tier reviews even when 86gs is slow** — accept the latency.

---

## Calibration data point — V123 §L1 cross-contract baseline confirmed

| Metric | Value |
|---|---|
| Predicted rounds | 4-6 (cross-contract) |
| Actual rounds | **6** (top of band) |
| P1s caught | 1 (controlDict missing) |
| P2s caught | 6 (workspace UUID, schema split, response_model=None, cleanup leak, extra=forbid, discriminator overlap, defaulted discriminator) |
| Cross-contract surfaces | container management (Docker SDK + OpenFOAM utility) + OpenAPI schema discrimination |
| Verbatim-exception eligibility | None (R1 was 167+ LOC across 7 files; later rounds were 1-2 file each but failed LOC ≤20 ceiling) |

V125 §L1 distinction (cross-contract vs no-cross): cumulative validation across V124 (3 rounds, no-cross), V125 (3 rounds, no-cross), V126 (6 rounds, cross-contract). Calibration baseline holds: no-cross ≈ 3 rounds, cross-contract ≈ 4-6 rounds. **V126 sits at the top of the cross-contract band — three of the six rounds were OpenAPI schema-discrimination iterations that landed entirely on schemas.py + routes/mesh_quality.py**, suggesting OpenAPI contract design is itself a sub-surface that benefits from explicit upfront design work rather than iterative discovery.

V126 closes Phase A (Meshing 三明治) per the user-agreed seven-phase roadmap. Next: re-run base review for cadence trailer + push 45 commits to GitHub origin/main.

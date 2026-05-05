---
decision_id: DEC-V61-126
title: Docker `checkMesh` integration · real skewness / non-orthogonality / aspect ratio metrics from OpenFOAM checkMesh · closes Phase A meshing 三明治
status: Proposed (2026-05-05 · pre-implementation surface scan complete; Codex pre-merge MANDATORY per RETRO-V61-001 multi-file backend + new operator-facing endpoint + AI-system-prompt extension + container management triggers)
codex_tool_report_path: reports/codex_tool_reports/v61_126_r1_chain.md (to be created)
codex_review_relay: CRS gpt-5.4 high (default per V61-119 §L2 protocol)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-05
authored_under: User 2026-05-05 mandate "按照你的规划、建议，授权你全权推进，记得同步Notion、Github" — V125 closed cleanly at 3 rounds, validating §L1 calibration baseline doubly. V126 starts the **Phase A → E pivot** per the agreed seven-phase roadmap; specifically Phase A item 3 (Docker checkMesh integration) closing the meshing 三明治 with real OpenFOAM-grade quality metrics. Per V123 §L1 lesson, this DEC explicitly **crosses container management surface** (mature V108+ pattern) — predicted round count is between V124/V125's 3 rounds (no-cross) and V123's 9 rounds (path-state safety cross): aim 4-6 rounds.
parent_decisions:
  - DEC-V61-122 (mesh-quality adviser foundation · V126 augments MeshQualityReport with optional checkMesh-derived fields; the existing analyzer + route already surfaces them via the V61-122 contract)
  - DEC-V61-123 (mesh-regenerate tool · V126's checkMesh runs against the polyMesh V123 just produced; chain works as "AI proposes regenerate → mesh lands → AI sees both V122 bbox metrics AND V126 checkMesh quality metrics in next snapshot")
  - DEC-V61-119 (LLM coach SSE backend + system prompt composer · V126 extends `_format_mesh_quality_section` to surface checkMesh fields when present)
  - DEC-V61-088 (pre-implementation surface scan · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · multi-file backend + new operator endpoint + AI-prompt extension + container management triggers Codex pre-merge)
parent_artifacts:
  - ui/backend/services/meshing_gmsh/to_foam.py (existing Docker exec pattern · 329 LOC · 12+ rounds of Codex hardening · V126's checkmesh_runner.py mirrors this surface exactly: docker.from_env → containers.get → status check → put_archive(polyMesh subset) → exec_run(checkMesh) → parse exec_result.output → typed errors. NO get_archive of files needed because checkMesh writes to stdout)
  - ui/backend/services/mesh_quality/analyzer.py (V122 analyzer · V126 extends with `run_checkmesh: bool = False` kwarg that augments the report with fields when True; default-False preserves V122 fast-path callers)
  - ui/backend/services/mesh_quality/schemas.py (V122 MeshQualityReport · V126 extends with optional `checkmesh_*` fields; absent when run_checkmesh=False or when container is unavailable)
  - ui/backend/routes/mesh_quality.py (V122 route · V126 adds `?run_checkmesh=true` query param)
  - ui/backend/services/llm_coach/prompts.py (V122 mesh section composer · V126 surfaces checkMesh fields when present in the report)
counter_impact: +1 (autonomous_governance: true · new backend service module + container management surface + system-prompt extension + new route query param. Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter 84→85 (counter ≥ 20 trigger continues to be deferred per ongoing user mandate "按你的顺序和建议，继续推进"), not governance-rule change. Codex pre-merge MANDATORY per RETRO-V61-001 (multi-file backend + new operator endpoint + container management) — all three triggers fire.)
notion_sync_status: synced 2026-05-05 (https://www.notion.so/DEC-V61-126-Docker-checkMesh-integration-real-skewness-non-orthogonality-aspect-ratio-metr-357c68942bed81ffa781dc2ab6d8f8d8)
self_estimated_pass_rate: 50% (predicted 4-6 rounds · §L1 contract-crossing baseline. Container management surface is mature (V108+ has 12+ rounds in to_foam.py), but parser logic + checkMesh output stability across OpenFOAM versions is new. Honest middle estimate between V124/V125's 3 rounds (no-cross) and V123's 9 rounds (path-state safety cross). The to_foam.py template covers ~80% of the Docker-side hardening; the new surface is the parser + augmentation logic.)

---

# DEC-V61-126 · Docker checkMesh integration

## Why now

The mesh-quality 三明治 has the AI's KNOWLEDGE (V122 reports cell count, bbox, patches) and HAND (V123/V124/V125 regenerate_mesh with 3 sizing knobs). What's still missing is what an experienced aviation CFD engineer expects from Fluent or StarCCM the moment they look at a mesh: **skewness, non-orthogonality, aspect ratio**. V122's bbox-derived approximations don't measure these — only OpenFOAM's `checkMesh` does.

V126 closes that gap: a `checkmesh_runner` service that exec's `checkMesh -case .` inside the cfd-openfoam container, parses the stdout for the canonical metrics, and surfaces them in `MeshQualityReport`. The AI now sees real quality data; the V61-119 system prompt section can reason about "your mesh has max skewness 0.85 — the Fluent default reject threshold is 0.95 but for k-ω SST anything over 0.7 risks convergence issues". The engineer sees the same numbers Fluent would show.

This is **Phase A item 3** (item 1+2 = V122+V123 already done; item 4 = 3D viewport quality coloring is V127 next, will be the first deliverable that has visible Fluent-like UX).

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: `checkMesh` returns 12 hits across `ui/backend/`, all in tests or string-matching contexts (none invoke checkMesh as a runner). The closest precedent is `to_foam.py` which exec's `gmshToFoam` in the container — V126 mirrors that 329-LOC template exactly. **Disposition: parallel new** (new module under `services/mesh_quality/`, sibling to `analyzer.py`; reuses Docker SDK patterns from `to_foam.py` but does NOT import them — same module-isolation discipline V108 uses).

**Existing-implementation grep** (`grep -rn "checkmesh\|check_mesh\|checkMesh" ui/backend/services/`): zero hits in the services layer. V126 is greenfield at the meshquality level; the Docker pattern reuse is template-level, not code-import.

## V1 scope (deliberately narrow per V123 §L1)

The V126 PR ships exactly:

1. **New `checkmesh_runner.py`** (~250 LOC) under `services/mesh_quality/`:
   - `run_checkmesh(case_dir, *, container_name) -> CheckMeshResult`
   - `CheckMeshError(failing_check: str)` typed error with enum: `polymesh_missing` · `container_unavailable` · `container_not_running` · `docker_sdk_error` · `checkmesh_exit_nonzero` · `parse_error`
   - `_parse_checkmesh_output(stdout) -> dict` — regex parser for max non-orthogonality, max skewness, max aspect ratio, "Mesh OK" / "Failed N mesh checks" lines, severe-non-orthogonal face count
   - All Docker SDK error paths from `to_foam.py` mirrored: `docker.from_env()` ImportError, `containers.get` NotFound, `container.status != "running"`, `put_archive` failure, `exec_run` DockerException, `OSError` from host filesystem during tarball build
2. **`CheckMeshResult` dataclass** — frozen, with fields: `max_non_orthogonality_deg`, `max_skewness`, `max_aspect_ratio`, `mesh_ok` (bool), `n_severe_non_ortho_faces`, `failed_checks` (list[str]), `raw_log_excerpt` (str, last ~50 lines for diagnosis).
3. **`MeshQualityReport` schema extension** — add 6 optional fields (`checkmesh_*`); all default-None so V122 callers that don't request checkMesh see no change. Schema-side test ensures backward compatibility.
4. **`analyze_mesh_quality` extension** — add `run_checkmesh: bool = False` kwarg. When True, invoke `run_checkmesh`; on success augment the report; on `CheckMeshError(container_unavailable | container_not_running)` log warning + leave fields None (graceful degradation — engineer sees V122 bbox metrics); on other errors raise (parse_error etc are real bugs, surface them).
5. **Route extension** — `GET /api/cases/{case_id}/mesh-quality?run_checkmesh=true` query param plumbs through. Default-False preserves V122 fast-path.
6. **System prompt extension** — `_format_mesh_quality_section` surfaces checkMesh fields when present: "checkMesh: max non-orthogonality 32.5°, max skewness 0.7, max aspect ratio 4.5, Mesh OK." Absent when fields are None.
7. **Tests** — checkmesh_runner: parse OK output · parse FAILED output · parse with severe-non-ortho count · container unavailable raises typed error · graceful degradation in analyze_mesh_quality when container down. Schema: backward-compat (no fields = V122 shape preserved). Route: ?run_checkmesh=true plumbs through. Prompt: surfaces fields when present.

## V1 deliberately excluded (push to V127+)

| Excluded axis | Why excluded | Successor |
|---|---|---|
| AI-coach `regenerate_mesh` auto-runs checkMesh after meshing | Adds another implicit Docker call to the mutation path; the engineer (or a separate explicit AI proposal) can request it via the route's query param. V127+ once UX flow stabilizes | V127+ |
| Cell-quality histogram (binned distribution of skewness/AR) | V1 ships summary stats only — single max value per metric. Histogram needs more parsing + a richer schema | V127+ |
| Visual mesh quality overlay in 3D viewport (red/yellow/green coloring) | The viewport itself doesn't exist yet (V127 will add it); the coloring overlay layers on top | V128+ |
| Aviation-specific quality thresholds in the AI prompt (e.g. "k-ω SST needs skewness < 0.7") | V126 just surfaces the numbers; the AI's interpretation comes when the system prompt grows aviation knowledge in Phase B | Phase B |
| Timeout / cancel for long-running checkMesh on huge meshes | checkMesh is fast (~5-30s on meshes ≤5M cells); large-mesh users can use the route's existing FastAPI default | V127+ |
| `checkMesh -allTopology -allGeometry` (verbose mode) | V1 uses default flags only. Verbose mode adds parser surface | V128+ |

## Risk surface

- **Container management contract crossing** (per V123 §L1): the `to_foam.py` 329-LOC template covers ~80% of the Docker hardening. V126's parser is the new surface — Codex's most likely findings will be parse-edge-cases (missing fields when checkMesh hits a non-standard mesh, OpenFOAM-version-specific output format variations).
- **OpenFOAM version stability**: the cfd-openfoam container ships OpenFOAM 10. checkMesh output format has been stable since OpenFOAM 4.x for the canonical metrics; the `Mesh non-orthogonality Max: X average: Y` line and `Max skewness = Z` line are 10+ years stable. Risk: low.
- **Graceful-degradation contract**: when container is unavailable, V126 must NOT fail the V122 happy path. The augmentation is opt-in via `run_checkmesh=true` query param; if the request opts in but Docker is down, route surfaces 503 with structured detail (not 500). If `run_checkmesh=false` (default), behavior is exactly V122.
- **Lock contract**: V123/V124/V125's `case_lock` covers polyMesh writes. V126 only READS polyMesh (put_archive doesn't mutate host); does NOT need case_lock. Concurrent V126 calls share the same checkMesh result per case — idempotent.
- **Tarball scope**: tar only `constant/polyMesh/` subset (typically 1-50 MB) instead of full case_dir to reduce wall-clock time.

## Implementation plan

```python
# services/mesh_quality/checkmesh_runner.py

CONTAINER_NAME = "cfd-openfoam"
CONTAINER_WORK_BASE = "/tmp/cfd-harness-cases-checkmesh"


class CheckMeshError(RuntimeError):
    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


@dataclass(frozen=True, slots=True)
class CheckMeshResult:
    max_non_orthogonality_deg: float | None
    max_skewness: float | None
    max_aspect_ratio: float | None
    mesh_ok: bool
    n_severe_non_ortho_faces: int | None
    failed_checks: list[str]
    raw_log_excerpt: str


# Regex bank — checkMesh output is 10+ years stable for these lines.
_RE_NON_ORTHO = re.compile(
    r"Mesh non-orthogonality Max:\s*([\d.eE+-]+)\s+average:\s*([\d.eE+-]+)"
)
_RE_SKEWNESS = re.compile(r"Max skewness\s*=\s*([\d.eE+-]+)")
_RE_ASPECT = re.compile(r"Max aspect ratio\s*=\s*([\d.eE+-]+)")
_RE_SEVERE_NON_ORTHO = re.compile(
    r"Number of severely non-orthogonal[^:]*:\s*(\d+)"
)
_RE_MESH_OK = re.compile(r"^Mesh OK\.?\s*$", re.MULTILINE)
_RE_FAILED = re.compile(r"Failed (\d+) mesh checks?\.")


def run_checkmesh(
    case_dir: Path,
    *,
    container_name: str = CONTAINER_NAME,
) -> CheckMeshResult:
    """Run ``checkMesh`` inside the cfd-openfoam container against the
    case's polyMesh and return parsed quality metrics.

    Mirrors to_foam.py's Docker SDK error contract: container missing,
    container not running, docker SDK error, exec_run failure all
    surface as CheckMeshError(failing_check=...).
    """
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        raise CheckMeshError(
            f"polyMesh directory missing at {polymesh}",
            failing_check="polymesh_missing",
        )

    try:
        import docker
        import docker.errors
    except ImportError as exc:
        raise CheckMeshError(
            "docker SDK is not installed", failing_check="docker_sdk_missing"
        ) from exc

    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        if container.status != "running":
            raise CheckMeshError(
                f"container '{container_name}' not running",
                failing_check="container_not_running",
            )
    except docker.errors.NotFound as exc:
        raise CheckMeshError(
            f"container '{container_name}' not found",
            failing_check="container_unavailable",
        ) from exc
    except docker.errors.DockerException as exc:
        raise CheckMeshError(
            f"docker client init failed: {exc}",
            failing_check="docker_sdk_error",
        ) from exc

    container_work = f"{CONTAINER_WORK_BASE}/{case_dir.name}"
    try:
        container.exec_run(
            cmd=["bash", "-c", f"mkdir -p {container_work}/constant"]
        )
        container.put_archive(
            path=f"{container_work}/constant",
            data=_make_polymesh_tarball(polymesh),
        )
    except docker.errors.DockerException as exc:
        raise CheckMeshError(
            f"docker SDK error preparing checkMesh workspace: {exc}",
            failing_check="docker_sdk_error",
        ) from exc

    bash_cmd = (
        f"source /opt/openfoam10/etc/bashrc && "
        f"cd {container_work} && "
        f"checkMesh 2>&1"
    )
    try:
        exec_result = container.exec_run(cmd=["bash", "-c", bash_cmd])
    except docker.errors.DockerException as exc:
        raise CheckMeshError(
            f"docker SDK error invoking checkMesh: {exc}",
            failing_check="docker_sdk_error",
        ) from exc

    # checkMesh exit code can be 0 even when "Failed N mesh checks" —
    # OpenFOAM 10's checkMesh distinguishes "fatal config error" (nonzero
    # exit) from "mesh has issues but is parseable" (zero exit + Failed
    # marker in output). The parser handles the issue distinction; only
    # treat nonzero as a hard error.
    output = exec_result.output.decode("utf-8", errors="replace")
    if exec_result.exit_code != 0:
        raise CheckMeshError(
            f"checkMesh exit_code={exec_result.exit_code}",
            failing_check="checkmesh_exit_nonzero",
        )

    return _parse_checkmesh_output(output)


def _parse_checkmesh_output(stdout: str) -> CheckMeshResult:
    non_ortho = _RE_NON_ORTHO.search(stdout)
    skewness = _RE_SKEWNESS.search(stdout)
    aspect = _RE_ASPECT.search(stdout)
    severe = _RE_SEVERE_NON_ORTHO.search(stdout)
    mesh_ok = bool(_RE_MESH_OK.search(stdout))
    failed = _RE_FAILED.search(stdout)
    failed_checks: list[str] = []
    if failed and not mesh_ok:
        # Re-scan for "***" marker lines which list specific failures.
        for line in stdout.splitlines():
            if "***" in line and "OK" not in line:
                failed_checks.append(line.strip(" *"))
    raw_excerpt = "\n".join(stdout.splitlines()[-50:])
    return CheckMeshResult(
        max_non_orthogonality_deg=float(non_ortho.group(1)) if non_ortho else None,
        max_skewness=float(skewness.group(1)) if skewness else None,
        max_aspect_ratio=float(aspect.group(1)) if aspect else None,
        mesh_ok=mesh_ok,
        n_severe_non_ortho_faces=int(severe.group(1)) if severe else None,
        failed_checks=failed_checks,
        raw_log_excerpt=raw_excerpt,
    )
```

## Acceptance criteria

- AC-1: `run_checkmesh(case_dir)` against a synthetic polyMesh in a running cfd-openfoam container returns a `CheckMeshResult` with all 5 numeric fields populated and `mesh_ok=True`.
- AC-2: When polyMesh is missing, raises `CheckMeshError(failing_check="polymesh_missing")` BEFORE any Docker call.
- AC-3: When container is not found, raises `CheckMeshError(failing_check="container_unavailable")`.
- AC-4: When container exists but is stopped, raises `CheckMeshError(failing_check="container_not_running")`.
- AC-5: Parser handles "Mesh OK" output and "Failed N mesh checks" output equally.
- AC-6: `analyze_mesh_quality(case_dir, run_checkmesh=True)` augments the report with checkMesh fields; `run_checkmesh=False` (default) returns identical V122 shape.
- AC-7: When `run_checkmesh=True` and container is unavailable, `analyze_mesh_quality` logs warning and returns V122 fields only — does NOT raise (graceful degradation).
- AC-8: Route `?run_checkmesh=true` plumbs through; default False preserves V122 fast-path.
- AC-9: System prompt's mesh section surfaces checkMesh fields when present, absent when None.
- AC-10: All V122 backward-compatibility tests pass without modification.

## Test plan

- `test_run_checkmesh_polymesh_missing_raises_typed_error` — synthetic case dir without constant/polyMesh
- `test_run_checkmesh_container_unavailable_raises_typed_error` — mock `docker.containers.get` to raise NotFound
- `test_run_checkmesh_container_not_running_raises_typed_error` — mock container with status="exited"
- `test_run_checkmesh_docker_sdk_error_raises_typed_error` — mock from_env to raise DockerException
- `test_parse_checkmesh_output_canonical_ok_format` — fixture: real checkMesh "Mesh OK" output → all fields populated
- `test_parse_checkmesh_output_failed_checks_format` — fixture: real "Failed 2 mesh checks" output → mesh_ok=False, failed_checks populated
- `test_parse_checkmesh_output_with_severe_non_orthogonal_faces` — fixture with "Number of severely non-orthogonal (> 70 degrees) faces: 5"
- `test_parse_checkmesh_output_handles_missing_metrics_gracefully` — partial output (e.g. checkMesh aborted mid-stream) → fields default to None, no exception
- `test_analyze_mesh_quality_with_checkmesh_augments_report` — mock run_checkmesh, assert fields land on MeshQualityReport
- `test_analyze_mesh_quality_with_checkmesh_graceful_degradation_on_container_down` — mock run_checkmesh to raise container_unavailable; analyze still returns V122 shape with checkmesh_* = None
- `test_mesh_quality_report_schema_v122_backward_compat` — instantiate MeshQualityReport without checkmesh_* fields; succeeds with defaults
- `test_route_run_checkmesh_query_param_plumbs_through` — GET /api/cases/{id}/mesh-quality?run_checkmesh=true invokes the augment path
- `test_route_default_omits_checkmesh` — GET without query param returns V122-shape body
- `test_prompt_mesh_section_surfaces_checkmesh_fields_when_present` — V61-119 prompt composer with V126-augmented report
- `test_prompt_mesh_section_omits_checkmesh_when_absent` — backward compat for V122 reports without checkmesh_* fields

## Process note

V126 is the first DEC of the post-V125 arc and the first to deliberately cross a pre-existing safety contract (container management) per V123 §L1 lesson, with eyes open to the higher round count. The to_foam.py template covers most of the Docker hardening; the genuinely-new surface is the parser + augmentation + graceful-degradation contract. Honest 50% / 4-6 rounds prediction.

If V126 lands at 4-6 rounds, the §L1 distinction is reinforced (cross-contract baseline ≈ 4-9 rounds; V123 was the tail of that range). If V126 lands at 7+ rounds, V123 wasn't an outlier — cross-contract DECs need additional discipline still to be worked out. RETRO candidate intake either way.

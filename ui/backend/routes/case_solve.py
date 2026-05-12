"""Phase-1A LDC solve routes (DEC-V61-097).

Three POST/GET endpoints:

* ``POST /api/import/{case_id}/setup-bc`` — split polyMesh + author dicts.
* ``POST /api/import/{case_id}/solve`` — run icoFoam in cfd-openfoam.
* ``GET  /api/cases/{case_id}/results-summary`` — parse final U field.

These wire the missing back half of the M-PANELS demo flow that
DEC-V61-096 deferred to M-AI-COPILOT / M7-redefined / M-VIZ.results.
The deferral is now lifted (per user direction 2026-04-29: full demo
end-to-end on the LDC fixture).

Scope: LDC only. The cylinder + naca0012 demos require an external-
flow pipeline (blockMesh + sHM) that is NOT shipped here; their
demo buttons remain "import + mesh only" pending Phase-2.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from ui.backend.schemas.ai_action import AIActionEnvelope
from ui.backend.schemas.case_solve import (
    ResultsRejection,
    ResultsSummaryWire,
    SetupBcRejection,
    SetupBcSummary,
    SolveRejection,
    SolveSummary,
)
from ui.backend.services.ai_actions import (
    AIActionError,
    setup_bc_with_annotations,
)
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR
from ui.backend.services.ai_actions.classifier import classify_setup_bc
from ui.backend.services.case_annotations import (
    AnnotationsIOError,
    annotations_exclusive_lock,
    load_annotations,
)
from ui.backend.services.case_solve import (
    BCSetupError,
    ResultsExtractError,
    SolverRunError,
    extract_results_summary,
    run_icofoam,
    setup_channel_bc,
    setup_ldc_bc,
    stream_icofoam,
)
from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    StlPatchBCError,
    setup_bc_from_stl_patches,
)
from ui.backend.services.case_solve.solver_streamer import (
    SolveAlreadyRunning,
    _prepare_stream_icofoam,
)


router = APIRouter()


def _resolve_case_dir(case_id: str) -> Path:
    if not is_safe_case_id(case_id):
        raise HTTPException(
            status_code=400,
            detail=SetupBcRejection(
                failing_check="bad_case_id",
                detail=f"unsafe case_id: {case_id!r}",
            ).model_dump(),
        )
    case_dir = IMPORTED_DIR / case_id
    if not case_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=SetupBcRejection(
                failing_check="case_not_found",
                detail=f"imported case {case_id!r} not found",
            ).model_dump(),
        )
    return case_dir


def _setup_bc_failure_to_http(exc: BCSetupError) -> HTTPException:
    """Map a ``BCSetupError`` to the appropriate HTTPException, shared
    by the legacy ``setup_bc`` route and the envelope-mode wrapper.
    """
    msg = str(exc)
    if "axis-aligned cube" in msg or "no boundary faces match" in msg:
        return HTTPException(
            status_code=400,
            detail=SetupBcRejection(
                failing_check="not_an_ldc_cube", detail=msg
            ).model_dump(),
        )
    # DEC-V61-101: channel executor user-actionable failures. Stale
    # pins after classifier verification (mesh regen mid-flight) and
    # missing pin matches both come back as the engineer's problem to
    # solve by re-picking, so they're 422 (semantic — request shape
    # OK, content rejected) rather than 500 (server-side fault).
    if (
        "stale pins after classifier verification" in msg
        or "no boundary face matched any" in msg
        or "all boundary faces classified as inlet/outlet" in msg
        or "classifier contract violated" in msg
    ):
        return HTTPException(
            status_code=422,
            detail=SetupBcRejection(
                failing_check="channel_pin_mismatch", detail=msg
            ).model_dump(),
        )
    if "no constant/polyMesh" in msg or "boundary file" in msg:
        return HTTPException(
            status_code=409,
            detail=SetupBcRejection(
                failing_check="mesh_missing", detail=msg
            ).model_dump(),
        )
    # DEC-V61-131 N1.1 R6 (Codex 86gs R5 P2 close): the apply route
    # now passes the unresolved case_dir through to setup_*_bc so
    # case_lock's O_NOFOLLOW symlink-escape guard runs. CaseLockError
    # surfaces inside setup_*_bc as ``BCSetupError`` whose message
    # carries "could not acquire case lock for setup_..." plus the
    # underlying CaseLockError message ("possible symlink escape" or
    # "lock_acquire_failed"). Map the symlink-containment substring to
    # 422 with the canonical V108/V109 ``symlink_escape`` failing_check
    # so callers see the same typed rejection as other case-mutation
    # routes; otherwise it would fall through to 500/write_failed and
    # break the V61-109 contract.
    if "possible symlink escape" in msg or "symlink_escape" in msg:
        return HTTPException(
            status_code=422,
            detail=SetupBcRejection(
                failing_check="symlink_escape", detail=msg
            ).model_dump(),
        )
    return HTTPException(
        status_code=500,
        detail=SetupBcRejection(
            failing_check="write_failed", detail=msg
        ).model_dump(),
    )


@router.post(
    "/import/{case_id}/setup-bc",
    tags=["case-solve"],
)
def setup_bc(
    case_id: str,
    envelope: int = Query(
        default=0,
        ge=0,
        le=1,
        description=(
            "When 1, return AIActionEnvelope (M-AI-COPILOT collab "
            "shape) instead of legacy SetupBcSummary. Backward-compat: "
            "default 0 preserves V61-097 callers."
        ),
    ),
    force_uncertain: int = Query(
        default=0,
        ge=0,
        le=1,
        description=(
            "(envelope=1 only) When 1, force confidence='uncertain' "
            "with one mock dialog question. Tier-A LDC dogfood path "
            "for the dialog flow without needing real arbitrary-STL "
            "AI ambiguity."
        ),
    ),
    force_blocked: int = Query(
        default=0,
        ge=0,
        le=1,
        description=(
            "(envelope=1 only) When 1, force confidence='blocked' "
            "with one mock dialog question. Mutually exclusive with "
            "force_uncertain; if both are passed, force_blocked wins."
        ),
    ),
    bc_kind: str | None = Query(
        default=None,
        description=(
            "DEC-V61-131 N1.1: when the engineer's [应用 AI 建议] click "
            "drives this route, the frontend passes the AI's "
            "suggested_bc_kind ('ldc' or 'channel'). Apply-time "
            "classifier is required to still agree; mismatches surface "
            "as 422 channel_pin_mismatch (recoverable re-pick flow) "
            "instead of falling through to setup_ldc_bc with a "
            "misleading not_an_ldc_cube. None = legacy auto behavior."
        ),
    ),
    if_match_revision: int | None = Query(
        default=None,
        ge=0,
        description=(
            "DEC-V61-131 N1.1 R2 P2 close: bind apply to the same "
            "annotations revision the AI envelope consumed when it "
            "produced the accepted advisory. If the current revision "
            "differs (another tab edited pins between accept and "
            "apply), surface 409 annotations_revision_conflict so the "
            "engineer re-runs the envelope before applying. None = "
            "skip the revision check (legacy callers)."
        ),
    ),
    from_stl_patches: int = Query(
        default=0,
        ge=0,
        le=1,
        description=(
            "DEC-V61-103: when 1, drive BC dict authoring from named "
            "polyMesh patches (multi-patch CAD imports) instead of "
            "the LDC lid/fixedWalls split. Mutually exclusive with "
            "envelope; if both are passed, from_stl_patches wins."
        ),
    ),
    inlet_speed: float | None = Query(
        default=None,
        gt=0.0,
        description=(
            "Adversarial-loop iter05/iter06 follow-up: override the "
            "default inlet velocity magnitude (m/s). Only honored when "
            "from_stl_patches=1. Required for stability on geometries "
            "where the default (0.5 m/s) produces a Courant number > 1 "
            "for the auto-meshed cell size."
        ),
    ),
    delta_t: float | None = Query(
        default=None,
        gt=0.0,
        description=(
            "Adversarial-loop iter05 follow-up: override the icoFoam "
            "timestep (s). Only honored when from_stl_patches=1. Lower "
            "values are required for Courant stability on small cells "
            "or high-velocity inlets."
        ),
    ),
    end_time: float | None = Query(
        default=None,
        gt=0.0,
        description=(
            "Override icoFoam endTime (s). Only honored when "
            "from_stl_patches=1. Default 5.0s."
        ),
    ),
    nu: float | None = Query(
        default=None,
        gt=0.0,
        description=(
            "Override kinematic viscosity (m²/s). Only honored when "
            "from_stl_patches=1. Default 1e-3 (water-like)."
        ),
    ),
    solver_name: str | None = Query(
        default=None,
        description=(
            "DEC-V61-111: select OpenFOAM solver. Only honored when "
            "from_stl_patches=1. Supported: 'pimpleFoam' (default · "
            "transient PIMPLE), 'simpleFoam' (steady-state SIMPLE). "
            "'icoFoam' is upgraded to 'pimpleFoam' with a warning per "
            "V61-107.5 (icoFoam on STL meshes produces NaN regardless "
            "of dt). Unrecognized values default to 'pimpleFoam' with "
            "a warning."
        ),
    ),
):
    """Author OpenFOAM dicts for the case in one of three modes.

    * Default (V61-097): split single patch into ``lid``/``fixedWalls``
      and author icoFoam Re=100 — LDC demo path.
    * ``?envelope=1`` (V61-098): wrap legacy outcome with
      ``AIActionEnvelope`` for the M-AI-COPILOT dialog flow.
    * ``?from_stl_patches=1`` (V61-103): read named patches from
      ``constant/polyMesh/boundary`` (preserved through gmsh by
      DEC-V61-102's defect-2a fix), map each to a default BC class
      via the project table (inlet/outlet/walls/symmetry/...), author
      the 7 icoFoam dicts referencing the actual patch names. The
      engineer can then fine-tune any field via the V61-102 raw-dict
      editor without re-running setup-bc.

    All three modes are idempotent.
    """
    case_dir = _resolve_case_dir(case_id)

    if from_stl_patches:
        # Build kwarg dict so callers that pass nothing get the
        # function's defaults (single source of truth in
        # setup_bc_from_stl_patches), and explicit None Query values
        # don't clobber those defaults.
        bc_kwargs: dict = {}
        if inlet_speed is not None:
            bc_kwargs["inlet_speed"] = inlet_speed
        if delta_t is not None:
            bc_kwargs["delta_t"] = delta_t
        if end_time is not None:
            bc_kwargs["end_time"] = end_time
        if nu is not None:
            bc_kwargs["nu"] = nu
        if solver_name is not None:
            bc_kwargs["solver_name"] = solver_name
        try:
            result = setup_bc_from_stl_patches(case_dir, case_id=case_id, **bc_kwargs)
        except StlPatchBCError as exc:
            status = {
                "mesh_not_setup": 409,
                "no_named_patches": 409,
                "write_failed": 500,
                "case_lock_failed": 409,
                # DEC-V61-107.5 / Codex R12 P1: case has partial
                # user-override on the {controlDict, fvSchemes,
                # fvSolution} group. 409 (Conflict) — engineer must
                # reconcile the override state before retrying.
                "solver_dicts_partial_override": 409,
                # DEC-V61-112 Phase 4 R4 P2 closure: server-side
                # deployment fault (YAML missing or malformed) — must
                # surface as 5xx so retry/alerting logic sees a server
                # error, NOT the default-400 client-error fallback.
                "solver_profile_load_failed": 500,
            }.get(exc.failing_check, 400)
            raise HTTPException(
                status_code=status,
                detail=SetupBcRejection(
                    failing_check=exc.failing_check,
                    detail=str(exc),
                ).model_dump(),
            ) from exc
        return JSONResponse(
            content={
                "case_id": result.case_id,
                "patches": [
                    {"name": name, "bc_class": cls.value}
                    for name, cls in result.patches
                ],
                "inlet_speed": result.inlet_speed,
                "inlet_velocities": [
                    {"name": name, "U": list(u)}
                    for name, u in result.inlet_velocities
                ],
                "nu": result.nu,
                "delta_t": result.delta_t,
                "end_time": result.end_time,
                "solver_name": result.solver_name,
                "written_files": list(result.written_files),
                "skipped_user_overrides": list(result.skipped_user_overrides),
                "warnings": list(result.warnings),
            },
            status_code=200,
        )

    if envelope:
        try:
            env = setup_bc_with_annotations(
                case_dir=case_dir,
                case_id=case_id,
                force_uncertain=bool(force_uncertain),
                force_blocked=bool(force_blocked),
            )
        except AIActionError as exc:
            # AIActionError wraps either a BCSetupError (LDC or channel
            # executor) or an AnnotationsIOError. Map BC failures to
            # the same HTTP shape as the legacy route; surface other
            # tags as 422 with the failing_check.
            #
            # Codex DEC-V61-101 R1 MED closure: setup_channel_bc_failed
            # was previously falling through to the 422 branch, losing
            # the BCSetupError → 4xx/5xx contract that the LDC path has.
            failing = getattr(exc, "failing_check", "ai_action_failed")
            if failing in ("setup_bc_failed", "setup_channel_bc_failed"):
                raise _setup_bc_failure_to_http(BCSetupError(str(exc))) from exc
            raise HTTPException(
                status_code=422,
                detail=SetupBcRejection(
                    failing_check=failing,
                    detail=str(exc),
                ).model_dump(),
            ) from exc
        return JSONResponse(
            content=env.model_dump(),
            status_code=200,
        )

    # DEC-V61-131 N1.1 mutation route: classify first, then dispatch
    # the right executor. Pre-N1.1 the AI envelope path branched
    # between LDC and channel internally; with the envelope hard-strip
    # advisory-only, this mutation route is now the apply-button
    # surface and must reproduce that branching so confident-channel
    # cases route through ``setup_channel_bc`` instead of erroring out
    # of ``setup_ldc_bc`` with ``not_an_ldc_cube``.
    #
    # bc_kind / if_match_revision (Codex N1.1 R1 P1+P2 close):
    # the apply path enforces the AI's advisory contract:
    #   * if_match_revision binds the apply to the same annotations
    #     revision the envelope consumed (no "accept A, apply B" race);
    #   * bc_kind requires the apply-time classifier to agree with the
    #     advisory's geometry_class — a stale-pin classifier-uncertain
    #     surfaces 422 channel_pin_mismatch (recoverable re-pick) instead
    #     of falling through to setup_ldc_bc with a misleading
    #     not_an_ldc_cube.
    # Legacy LDC dogfood callers (no params) preserve the pre-N1.1
    # behavior: classifier optionally upgrades to channel; classifier
    # uncertain still falls through to setup_ldc_bc.
    # Codex N1.1 R3 P2 close: resolve the case_dir to its real
    # filesystem path BEFORE acquiring the annotations lock, and use
    # the resolved path for every operation inside the lock. Without
    # this, a rename/replace race between the route's case_dir lookup
    # and load_annotations() could let the lock guard a stale path
    # while classification + execution operate on the new one.
    # save_annotations applies the same pattern (locks
    # _resolve_annotations_path(case_dir).parent), so this binding
    # makes the apply path's lock domain identical.
    #
    # Codex N1.1 R18 P1 close (branch-level review): containment
    # check BEFORE resolve. ``case_dir.resolve(strict=True)`` follows
    # any symlink at the case_dir level, so if
    # ``user_drafts/imported/<case_id>`` has been replaced by a
    # symlink pointing outside IMPORTED_DIR, the lock + load +
    # classify would operate on the symlink target. Verify (a)
    # case_dir is not itself a symlink, and (b) the resolved
    # parent matches IMPORTED_DIR.resolve() — V61-109 containment
    # contract on the apply path mirrors the O_NOFOLLOW guards in
    # _resolve_annotations_path.
    try:
        if case_dir.is_symlink():
            raise HTTPException(
                status_code=422,
                detail=SetupBcRejection(
                    failing_check="symlink_escape",
                    detail=f"case_dir {case_dir} is a symlink",
                ).model_dump(),
            )
        resolved_case_dir = case_dir.resolve(strict=True)
        expected_parent = IMPORTED_DIR.resolve()
        if resolved_case_dir.parent != expected_parent:
            raise HTTPException(
                status_code=422,
                detail=SetupBcRejection(
                    failing_check="symlink_escape",
                    detail=(
                        f"case_dir {case_dir} resolves outside the "
                        f"imported jail (parent {resolved_case_dir.parent}"
                        f" != {expected_parent})"
                    ),
                ).model_dump(),
            )
    except HTTPException:
        raise
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=409,
            detail=SetupBcRejection(
                failing_check="case_disappeared",
                detail=f"could not resolve {case_dir}: {exc}",
            ).model_dump(),
        ) from exc

    # Codex N1.1 R2 P1 close: hold the annotations-exclusive lock for
    # the entire load → classify → revision-check → dispatch sequence.
    # Without the lock, a concurrent PUT /face-annotations could land
    # between load_annotations() and the executor call, slipping past
    # the if_match_revision equality check while the executor still
    # uses the pre-write classifier output. annotations_exclusive_lock
    # serializes against save_annotations (the only mutator of
    # face_annotations.yaml), so within this block the revision is
    # frozen for the engineer's accepted advisory.
    use_channel = False
    cls_inlet: tuple[str, ...] = ()
    cls_outlet: tuple[str, ...] = ()
    cls_for_apply = None
    annotations_for_apply: dict | None = None
    apply_summary: SetupBcSummary | None = None
    try:
        with annotations_exclusive_lock(resolved_case_dir):
            # Codex N1.1 R18 P2 close (branch-level review): the apply
            # path used to silently swallow load_annotations() and
            # classify_setup_bc() failures and fall through to the
            # legacy LDC dogfood. That swallowed real failures
            # (parse_error / schema_version_mismatch / symlink_escape
            # on the annotations side, classifier crashes on the
            # geometry side) on the new advisory-apply contract,
            # potentially returning a misleading channel_pin_mismatch
            # OR running setup_ldc_bc against corrupt annotations.
            # Now: when bc_kind / if_match_revision are present (the
            # new advisory-apply contract), surface IO errors as 422
            # / 409 / 500 with the failing_check tag. Legacy callers
            # (no params) keep the swallow-and-fall-through behavior
            # so the LDC dogfood path doesn't break on malformed
            # annotations the caller didn't ask the apply contract
            # to enforce.
            is_advisory_apply = (
                bc_kind is not None or if_match_revision is not None
            )
            try:
                annotations_for_apply = load_annotations(
                    resolved_case_dir, case_id=case_id
                )
                cls_for_apply = classify_setup_bc(
                    resolved_case_dir, annotations=annotations_for_apply
                )
                if (
                    cls_for_apply.confidence == "confident"
                    and cls_for_apply.geometry_class == "non_cube"
                ):
                    use_channel = True
                    cls_inlet = cls_for_apply.inlet_face_ids
                    cls_outlet = cls_for_apply.outlet_face_ids
            except AnnotationsIOError as exc:
                if is_advisory_apply:
                    status_map = {
                        "case_dir_missing": 404,
                        "parse_error": 422,
                        "symlink_escape": 422,
                        "schema_version_mismatch": 422,
                    }
                    status = status_map.get(exc.failing_check, 500)
                    raise HTTPException(
                        status_code=status,
                        detail=SetupBcRejection(
                            failing_check=exc.failing_check,
                            detail=str(exc),
                        ).model_dump(),
                    ) from exc
                # Legacy contract: fall through to LDC dogfood.
            except Exception as exc:  # noqa: BLE001 — defensive
                if is_advisory_apply:
                    raise HTTPException(
                        status_code=500,
                        detail=SetupBcRejection(
                            failing_check="classify_failed",
                            detail=f"classifier raised: {exc}",
                        ).model_dump(),
                    ) from exc
                # Legacy contract: fall through to LDC dogfood.

            if if_match_revision is not None and annotations_for_apply is not None:
                current_rev = annotations_for_apply.get("revision", 0)
                if current_rev != if_match_revision:
                    raise HTTPException(
                        status_code=409,
                        detail=SetupBcRejection(
                            failing_check="annotations_revision_conflict",
                            detail=(
                                f"Annotations changed between AI "
                                f"advisory (revision {if_match_revision})"
                                f" and apply (revision {current_rev}). "
                                f"Re-run the AI envelope before applying."
                            ),
                        ).model_dump(),
                    )

            if bc_kind == "channel" and not use_channel:
                questions: list[dict] = []
                question_summary = "channel pins changed since AI advisory"
                if cls_for_apply is not None:
                    for q in cls_for_apply.questions:
                        try:
                            questions.append(q.model_dump())
                        except AttributeError:
                            questions.append(dict(q))  # type: ignore[arg-type]
                    if cls_for_apply.summary:
                        question_summary = cls_for_apply.summary
                raise HTTPException(
                    status_code=422,
                    detail=SetupBcRejection(
                        failing_check="channel_pin_mismatch",
                        detail=question_summary,
                    ).model_dump()
                    | {"unresolved_questions": questions},
                )

            # Codex N1.1 R19 P1 close (branch-level review): symmetric
            # guard for bc_kind="ldc". If the engineer accepted an LDC
            # advisory but the mesh changed before applying (e.g.,
            # another tab regenerated the mesh and the classifier now
            # reports a confident channel geometry), running
            # setup_ldc_bc against the new geometry would silently
            # apply wrong BCs. Surface 422 ldc_mismatch so the engineer
            # re-runs the AI advisory and re-classifies.
            if (
                bc_kind == "ldc"
                and cls_for_apply is not None
                and cls_for_apply.confidence == "confident"
                and cls_for_apply.geometry_class == "non_cube"
            ):
                ldc_questions: list[dict] = []
                for q in cls_for_apply.questions:
                    try:
                        ldc_questions.append(q.model_dump())
                    except AttributeError:
                        ldc_questions.append(dict(q))  # type: ignore[arg-type]
                ldc_summary = (
                    cls_for_apply.summary
                    or "geometry changed since LDC advisory — classifier now reports a non-cube/channel"
                )
                raise HTTPException(
                    status_code=422,
                    detail=SetupBcRejection(
                        failing_check="ldc_mismatch",
                        detail=ldc_summary,
                    ).model_dump()
                    | {"unresolved_questions": ldc_questions},
                )

            # Dispatch the executor under the same annotations lock so
            # the BCs we author are tied to the revision we just
            # verified. setup_*_bc takes its own .case_lock (different
            # lock file), so reentrance is not an issue.
            # Codex N1.1 R4 P1 close: pass the UNRESOLVED case_dir
            # (not resolved_case_dir) to setup_*_bc so their internal
            # case_lock() retains its O_NOFOLLOW symlink-escape check.
            # Resolving here previously bypassed V61-109 containment;
            # the lock above already binds the annotations critical
            # section to the resolved dir, so the executor can use
            # the unresolved path safely.
            if use_channel:
                try:
                    ch_result = setup_channel_bc(
                        case_dir,
                        case_id=case_id,
                        inlet_face_ids=cls_inlet,
                        outlet_face_ids=cls_outlet,
                    )
                except BCSetupError as exc:
                    raise _setup_bc_failure_to_http(exc) from exc
                apply_summary = SetupBcSummary(
                    case_id=ch_result.case_id,
                    bc_kind="channel",
                    n_inlet_faces=ch_result.n_inlet_faces,
                    n_outlet_faces=ch_result.n_outlet_faces,
                    n_wall_faces=ch_result.n_wall_faces,
                    nu=ch_result.nu,
                    reynolds=ch_result.reynolds,
                    written_files=list(ch_result.written_files),
                )
            else:
                try:
                    ldc_result = setup_ldc_bc(case_dir, case_id=case_id)
                except BCSetupError as exc:
                    raise _setup_bc_failure_to_http(exc) from exc
                apply_summary = SetupBcSummary(
                    case_id=ldc_result.case_id,
                    bc_kind="ldc",
                    n_lid_faces=ldc_result.n_lid_faces,
                    n_wall_faces=ldc_result.n_wall_faces,
                    lid_velocity=ldc_result.lid_velocity,
                    nu=ldc_result.nu,
                    reynolds=ldc_result.reynolds,
                    written_files=list(ldc_result.written_files),
                    warnings=list(ldc_result.warnings),
                )
    except AnnotationsIOError as exc:
        # annotations_exclusive_lock itself raises AnnotationsIOError
        # on symlink_escape / lock acquire failures. Map to 422 so the
        # caller sees a typed rejection rather than a 500.
        raise HTTPException(
            status_code=422,
            detail=SetupBcRejection(
                failing_check=exc.failing_check,
                detail=str(exc),
            ).model_dump(),
        ) from exc

    assert apply_summary is not None  # one of the two branches set it
    return apply_summary


@router.post(
    "/import/{case_id}/solve-stream",
    tags=["case-solve"],
)
def solve_stream(case_id: str) -> StreamingResponse:
    """Run icoFoam with **live** SSE streaming so the UI can update a
    residual chart in real time.

    Setup failures (case missing, bc not setup, container down) raise
    HTTPException BEFORE the first byte is yielded — those become
    HTTP 4xx/5xx with the same shape as the blocking ``/solve`` route.
    Failures DURING the run land as in-stream ``error`` events; the
    HTTP status stays 200 because the stream has already started.
    """
    case_dir = _resolve_case_dir(case_id)

    # Validate eagerly so we can return a real HTTP error code instead
    # of a 200-with-error-event. The streamer also checks these but
    # raising here gives the route a chance to attach the structured
    # SolveRejection contract.
    if not (case_dir / "system" / "controlDict").is_file():
        raise HTTPException(
            status_code=409,
            detail=SolveRejection(
                failing_check="bc_not_setup",
                detail=f"no system/controlDict at {case_dir}",
            ).model_dump(),
        )

    # Codex round-1 HIGH-1: preflight must run BEFORE we hand a
    # generator to StreamingResponse. ``_prepare_stream_icofoam`` is a
    # plain function (not a generator), so any SolverRunError raised
    # here surfaces as an HTTPException synchronously — instead of as
    # a 200 response with a torn iterator.
    try:
        prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
    except SolveAlreadyRunning as exc:
        # HIGH-2: a prior run for this case is still active. Reject
        # with 409 so the client can wait + retry.
        raise HTTPException(
            status_code=409,
            detail=SolveRejection(
                failing_check="solve_already_running",
                detail=str(exc),
            ).model_dump(),
        ) from exc
    except SolverRunError as exc:
        msg = str(exc)
        if msg.startswith("mesh_missing:"):
            # B-ext-5.2 F13 mitigation — same as blocking /solve route.
            status = 409
            failing = "mesh_missing"
        elif msg.startswith("mesh_bc_mismatch:"):
            status = 409
            failing = "mesh_bc_mismatch"
        elif "container" in msg.lower() and (
            "not running" in msg.lower() or "not found" in msg.lower()
        ):
            status = 503
            failing = "container_unavailable"
        else:
            status = 502
            failing = "post_stage_failed"
        raise HTTPException(
            status_code=status,
            detail=SolveRejection(
                failing_check=failing,
                detail=msg,
            ).model_dump(),
        ) from exc

    return StreamingResponse(
        stream_icofoam(prepared=prepared),
        media_type="text/event-stream",
        headers={
            # SSE wants no buffering by intermediaries; declare
            # explicitly so reverse proxies (nginx etc) flush each
            # event instead of accumulating.
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/import/{case_id}/solve",
    response_model=SolveSummary,
    tags=["case-solve"],
)
def solve(case_id: str) -> SolveSummary:
    """Run icoFoam inside the cfd-openfoam container. Blocks until the
    solver finishes (≈60s wall-time for the default LDC config).
    """
    from datetime import datetime, timezone

    from ui.backend.services.run_history import (
        new_run_id,
        write_run_artifacts,
    )

    case_dir = _resolve_case_dir(case_id)
    started_at = datetime.now(timezone.utc)
    try:
        result = run_icofoam(case_host_dir=case_dir)
    except SolverRunError as exc:
        msg = str(exc)
        if "no system/controlDict" in msg:
            raise HTTPException(
                status_code=409,
                detail=SolveRejection(
                    failing_check="bc_not_setup",
                    detail=msg,
                ).model_dump(),
            ) from exc
        if msg.startswith("mesh_missing:"):
            # B-ext-5.2 F13 mitigation: pre-flight caught missing
            # polyMesh before spawning solver. 409 Conflict so the
            # persona can re-run /mesh instead of seeing a generic 502
            # solver_diverged on a cryptic FOAM IO error.
            raise HTTPException(
                status_code=409,
                detail=SolveRejection(
                    failing_check="mesh_missing",
                    detail=msg,
                ).model_dump(),
            ) from exc
        if msg.startswith("mesh_bc_mismatch:"):
            # B-ext-3 F10 fix: pre-flight catches a stale-BC-after-/mesh
            # state. 409 Conflict — engineer must re-run setup-bc to
            # bring the BC files back in sync with the regenerated mesh.
            raise HTTPException(
                status_code=409,
                detail=SolveRejection(
                    failing_check="mesh_bc_mismatch",
                    detail=msg,
                ).model_dump(),
            ) from exc
        if "container" in msg.lower() and (
            "not running" in msg.lower() or "not found" in msg.lower()
        ):
            raise HTTPException(
                status_code=503,
                detail=SolveRejection(
                    failing_check="container_unavailable",
                    detail=msg,
                ).model_dump(),
            ) from exc
        if "exited with code" in msg:
            raise HTTPException(
                status_code=502,
                detail=SolveRejection(
                    failing_check="solver_diverged",
                    detail=msg,
                ).model_dump(),
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=SolveRejection(
                failing_check="post_stage_failed",
                detail=msg,
            ).model_dump(),
        ) from exc

    # B-ext-4.2 F11 fix (DEC-V61-188): persist run artifacts to
    # reports/{case_id}/runs/{run_id}/ so /api/cases/{id}/run-history
    # surfaces the run. Pre-fix the route was wired only by
    # RealSolverDriver (M3 closed-loop main-line); /solve was running
    # icoFoam directly without persisting anything, leaving
    # /run-history with empty runs:[] after every successful solve.
    run_id = new_run_id()
    try:
        write_run_artifacts(
            case_id=case_id,
            run_id=run_id,
            started_at=started_at,
            task_spec=None,
            source_origin="ui_solve_route",
            success=result.converged,
            exit_code=0,
            verdict_summary=(
                "converged" if result.converged else "ran_but_not_converged"
            ),
            duration_s=result.wall_time_s,
            key_quantities={
                "end_time_reached": result.end_time_reached,
                "n_time_steps_written": result.n_time_steps_written,
            },
            residuals={
                "p": result.last_initial_residual_p,
                "Ux": result.last_initial_residual_U[0],
                "Uy": result.last_initial_residual_U[1],
                "Uz": result.last_initial_residual_U[2],
                "continuity": result.last_continuity_error,
            },
        )
    except (OSError, ValueError):
        # Run-history persistence is best-effort; never fail the
        # /solve response on artifact-write errors. The pre-flight
        # mesh-BC check + container availability check are the
        # load-bearing guards.
        pass

    # B-ext-6.1 F15 fix layer 1 (DEC-V61-196): create
    # <case_dir>/<run_id> → <final_time_dir> symlink so the existing
    # /api/cases/{id}/results/{run_id}/field/{name} route resolves to
    # the OpenFOAM time-step files. The route looks at
    # <case_dir>/<run_id>/<name>; without the symlink it returns 404
    # run_not_found because OpenFOAM writes time-step output under
    # <case_dir>/0/, <case_dir>/0.5/, etc., NOT under <case_dir>/<run_id>/.
    # Best-effort: if symlink creation fails (race, FS without
    # symlink support), the route still returns 404 — same as before.
    try:
        if result.time_directories:
            final_time_name = result.time_directories[-1]
            target = case_dir / final_time_name
            link = case_dir / run_id
            if target.is_dir() and not link.exists():
                link.symlink_to(final_time_name, target_is_directory=True)
    except OSError:
        pass

    return SolveSummary(
        case_id=result.case_id,
        end_time_reached=result.end_time_reached,
        last_initial_residual_p=result.last_initial_residual_p,
        last_initial_residual_U=result.last_initial_residual_U,
        last_continuity_error=result.last_continuity_error,
        n_time_steps_written=result.n_time_steps_written,
        time_directories=list(result.time_directories),
        wall_time_s=result.wall_time_s,
        converged=result.converged,
        run_id=run_id,
    )


@router.get(
    "/cases/{case_id}/results-summary",
    response_model=ResultsSummaryWire,
    tags=["case-solve"],
)
def results_summary(case_id: str) -> ResultsSummaryWire:
    """Parse the final U field, return summary statistics. Read-only:
    re-running this is cheap and idempotent.
    """
    case_dir = _resolve_case_dir(case_id)
    try:
        summary = extract_results_summary(case_dir, case_id=case_id)
    except ResultsExtractError as exc:
        msg = str(exc)
        if "icoFoam hasn't run" in msg:
            raise HTTPException(
                status_code=409,
                detail=ResultsRejection(
                    failing_check="solve_not_run",
                    detail=msg,
                ).model_dump(),
            ) from exc
        raise HTTPException(
            status_code=500,
            detail=ResultsRejection(
                failing_check="results_malformed",
                detail=msg,
            ).model_dump(),
        ) from exc

    return ResultsSummaryWire(
        case_id=summary.case_id,
        final_time=summary.final_time,
        cell_count=summary.cell_count,
        u_magnitude_min=summary.u_magnitude_min,
        u_magnitude_max=summary.u_magnitude_max,
        u_magnitude_mean=summary.u_magnitude_mean,
        u_x_mean=summary.u_x_mean,
        u_x_min=summary.u_x_min,
        u_x_max=summary.u_x_max,
        is_recirculating=summary.is_recirculating,
    )

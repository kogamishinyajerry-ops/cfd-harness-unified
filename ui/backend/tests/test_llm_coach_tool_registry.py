"""DEC-V61-121 · LLM coach tool-registry + audit unit tests.

Coverage:
  * registry list includes the V1 tool
  * unknown tool raises UnknownToolError
  * bad args raise ToolArgError with structured errors
  * happy path dispatches into V108 upsert_override
  * V108 IO error translates to ToolDispatchError(underlying_service_error)
  * audit.write_audit appends a new entry with required fields
  * audit reads existing file + appends; preserves prior entries
  * audit handles missing audit dir / corrupt file paths
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ui.backend.services.case_solve.bc_setup_from_stl_patches import BCClass
from ui.backend.services.llm_coach import (
    AuditWriteError,
    SetPatchBcTypeArgs,
    ToolArgError,
    ToolDispatchError,
    UnknownToolError,
    dispatch,
    list_tools,
    write_audit,
)


def _make_minimal_case_dir(root: Path, case_id: str = "lid_driven_cavity") -> Path:
    """Build a case dir that V108's upsert_override will accept.

    The store needs a writable directory with no symlink shenanigans;
    V108's code path also wants a polyMesh boundary if it's going to
    re-classify, but upsert_override itself only writes the override
    file, so a bare case dir is enough for this test.
    """
    case_dir = root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


# ────────── list_tools ──────────


def test_list_tools_includes_v1_set_patch_bc_type():
    tools = list_tools()
    names = [t.name for t in tools]
    assert "set_patch_bc_type" in names


def test_list_tools_v1_tool_describes_args():
    [tool] = [t for t in list_tools() if t.name == "set_patch_bc_type"]
    desc = tool.description
    assert "patch_name" in desc
    assert "bc_class" in desc
    # The four enum members must be enumerated for the LLM.
    assert "velocity_inlet" in desc
    assert "no_slip_wall" in desc


# ────────── dispatch — error paths ──────────


def test_dispatch_unknown_tool_raises_unknown_tool_error(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    with pytest.raises(UnknownToolError) as exc_info:
        dispatch(case_dir, "no_such_tool", {"x": 1})
    assert exc_info.value.tool_name == "no_such_tool"
    assert exc_info.value.failing_check == "unknown_tool"


def test_dispatch_bad_args_raises_tool_arg_error(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    # bc_class is a Literal; "garbage" must fail Pydantic validation.
    with pytest.raises(ToolArgError) as exc_info:
        dispatch(
            case_dir,
            "set_patch_bc_type",
            {"patch_name": "walls", "bc_class": "garbage"},
        )
    assert exc_info.value.tool_name == "set_patch_bc_type"
    assert exc_info.value.failing_check == "arg_validation_failed"
    assert len(exc_info.value.validation_errors) >= 1


def test_dispatch_missing_required_arg_raises_tool_arg_error(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    with pytest.raises(ToolArgError):
        dispatch(case_dir, "set_patch_bc_type", {"bc_class": "no_slip_wall"})


def test_dispatch_empty_patch_name_raises_tool_arg_error(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    with pytest.raises(ToolArgError):
        dispatch(
            case_dir,
            "set_patch_bc_type",
            {"patch_name": "", "bc_class": "no_slip_wall"},
        )


# ────────── dispatch — happy path ──────────


def test_dispatch_set_patch_bc_type_writes_override(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    result = dispatch(
        case_dir,
        "set_patch_bc_type",
        {"patch_name": "walls", "bc_class": "no_slip_wall"},
    )
    assert result.tool == "set_patch_bc_type"
    assert "walls" in result.summary
    assert "no_slip_wall" in result.summary
    # state_after exposes the merged overrides.
    assert result.state_after["overrides"]["walls"] == "no_slip_wall"
    # Underlying file written by V108's store.
    override_file = case_dir / "system" / "patch_classification.yaml"
    assert override_file.is_file()


def test_dispatch_idempotent_for_same_args(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    args = {"patch_name": "inlet", "bc_class": "velocity_inlet"}
    r1 = dispatch(case_dir, "set_patch_bc_type", args)
    r2 = dispatch(case_dir, "set_patch_bc_type", args)
    # Same final state on both calls.
    assert r1.state_after == r2.state_after


def test_dispatch_overrides_replace_prior_classification(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    dispatch(
        case_dir,
        "set_patch_bc_type",
        {"patch_name": "outlet", "bc_class": "pressure_outlet"},
    )
    result = dispatch(
        case_dir,
        "set_patch_bc_type",
        {"patch_name": "outlet", "bc_class": "symmetry"},
    )
    assert result.state_after["overrides"]["outlet"] == "symmetry"


# ────────── SetPatchBcTypeArgs schema ──────────


def test_set_patch_bc_type_args_accepts_all_four_bc_classes():
    for bc in ("velocity_inlet", "pressure_outlet", "no_slip_wall", "symmetry"):
        SetPatchBcTypeArgs(patch_name="x", bc_class=bc)


def test_set_patch_bc_type_args_rejects_unrelated_bc_class():
    with pytest.raises(ValueError):
        SetPatchBcTypeArgs(patch_name="x", bc_class="not_a_real_bc_class")


def test_set_patch_bc_type_args_rejects_extra_keys(tmp_path):
    """Codex R1 P3: a malformed proposal carrying stray keys must
    fail validation, not silently drop the extras. The registry
    boundary's job is to reject off-contract payloads before
    dispatch."""
    case_dir = _make_minimal_case_dir(tmp_path)
    with pytest.raises(ToolArgError) as exc_info:
        dispatch(
            case_dir,
            "set_patch_bc_type",
            {
                "patch_name": "walls",
                "bc_class": "no_slip_wall",
                "note": "should be rejected",
            },
        )
    # Pydantic surfaces the offending key path in the validation error.
    err_dump = str(exc_info.value.validation_errors)
    assert "note" in err_dump or "extra" in err_dump.lower()


# ────────── audit.write_audit ──────────


def test_write_audit_creates_file_and_returns_audit_id(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    audit_id = write_audit(
        case_dir,
        tool="set_patch_bc_type",
        args={"patch_name": "walls", "bc_class": "no_slip_wall"},
        model_used="deepseek-v4-pro",
        conversation_turn_id=None,
    )
    assert isinstance(audit_id, str)
    assert len(audit_id) >= 16
    audit_path = case_dir / "system" / "ai_audit" / "applied.yaml"
    assert audit_path.is_file()
    doc = yaml.safe_load(audit_path.read_text())
    assert doc["schema_version"] == 1
    assert len(doc["entries"]) == 1
    entry = doc["entries"][0]
    assert entry["tool"] == "set_patch_bc_type"
    assert entry["args"] == {"patch_name": "walls", "bc_class": "no_slip_wall"}
    assert entry["audit_id"] == audit_id
    assert entry["model_used"] == "deepseek-v4-pro"
    # applied_at is ISO-8601 with Z suffix.
    assert entry["applied_at"].endswith("Z")


def test_write_audit_appends_to_existing_file(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    a1 = write_audit(
        case_dir,
        tool="set_patch_bc_type",
        args={"patch_name": "walls", "bc_class": "no_slip_wall"},
        model_used="x",
        conversation_turn_id=None,
    )
    a2 = write_audit(
        case_dir,
        tool="set_patch_bc_type",
        args={"patch_name": "inlet", "bc_class": "velocity_inlet"},
        model_used="y",
        conversation_turn_id=None,
    )
    audit_path = case_dir / "system" / "ai_audit" / "applied.yaml"
    doc = yaml.safe_load(audit_path.read_text())
    assert [e["audit_id"] for e in doc["entries"]] == [a1, a2]
    assert doc["entries"][0]["args"]["patch_name"] == "walls"
    assert doc["entries"][1]["args"]["patch_name"] == "inlet"


def test_write_audit_creates_parent_dirs(tmp_path):
    # Case dir exists but `system/` doesn't yet.
    case_dir = tmp_path / "freshcase"
    case_dir.mkdir()
    write_audit(
        case_dir,
        tool="set_patch_bc_type",
        args={"patch_name": "x", "bc_class": "symmetry"},
        model_used=None,
        conversation_turn_id=None,
    )
    assert (case_dir / "system" / "ai_audit" / "applied.yaml").is_file()


def test_write_audit_rejects_corrupt_existing_file(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    audit_dir = case_dir / "system" / "ai_audit"
    audit_dir.mkdir(parents=True)
    (audit_dir / "applied.yaml").write_text("not: a: valid: yaml: structure: ::: ::")
    with pytest.raises(AuditWriteError):
        write_audit(
            case_dir,
            tool="set_patch_bc_type",
            args={"patch_name": "x", "bc_class": "symmetry"},
            model_used=None,
            conversation_turn_id=None,
        )


def test_write_audit_serializes_concurrent_writers(tmp_path):
    """Codex R1 P2: two writers racing to append should produce
    BOTH entries — not lose one to a clobbering rename. We test
    the post-condition (both audit_ids present) rather than
    drive a thread harness; the case_lock ensures the read-modify-
    write window is serialized so even back-to-back single-thread
    calls preserve every entry."""
    case_dir = _make_minimal_case_dir(tmp_path)
    audit_ids = []
    for i in range(5):
        a = write_audit(
            case_dir,
            tool="set_patch_bc_type",
            args={
                "patch_name": f"patch_{i}",
                "bc_class": "no_slip_wall",
            },
            model_used="x",
            conversation_turn_id=None,
        )
        audit_ids.append(a)
    audit_path = case_dir / "system" / "ai_audit" / "applied.yaml"
    doc = yaml.safe_load(audit_path.read_text())
    persisted_ids = [e["audit_id"] for e in doc["entries"]]
    assert persisted_ids == audit_ids
    assert len(set(persisted_ids)) == 5


def test_write_audit_rejects_schema_version_mismatch(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    audit_dir = case_dir / "system" / "ai_audit"
    audit_dir.mkdir(parents=True)
    (audit_dir / "applied.yaml").write_text(
        yaml.safe_dump({"schema_version": 99, "entries": []})
    )
    with pytest.raises(AuditWriteError):
        write_audit(
            case_dir,
            tool="set_patch_bc_type",
            args={"patch_name": "x", "bc_class": "symmetry"},
            model_used=None,
            conversation_turn_id=None,
        )


# ────────── DEC-V61-123 · regenerate_mesh tool ──────────


def _stub_mesh_result(case_id: str = "lid_driven_cavity", **overrides):
    """Construct a MeshResult-shaped object the handler can return.

    We use the real dataclass so the handler's attribute access is
    type-checked end-to-end."""
    from ui.backend.services.meshing_gmsh import MeshResult

    defaults = dict(
        case_id=case_id,
        mesh_mode="power",
        cell_count=350_000,
        face_count=2_100_000,
        point_count=400_000,
        polyMesh_path=Path("/tmp/imported") / case_id / "constant" / "polyMesh",
        msh_path=Path("/tmp/imported") / case_id / "imported.msh",
        generation_time_s=42.5,
        warning=None,
    )
    defaults.update(overrides)
    return MeshResult(**defaults)


def test_list_tools_includes_regenerate_mesh():
    """V123: regenerate_mesh appears in the registry alongside V121's
    set_patch_bc_type."""
    names = [t.name for t in list_tools()]
    assert "regenerate_mesh" in names


def test_regenerate_mesh_tool_describes_args():
    [tool] = [t for t in list_tools() if t.name == "regenerate_mesh"]
    desc = tool.description
    assert "mesh_mode" in desc
    assert "beginner" in desc
    assert "power" in desc


def test_dispatch_regenerate_mesh_happy_path(tmp_path):
    """DEC-V61-131 N1.1: regenerate_mesh is advisory-only. Dispatch
    returns ApplyResult describing the suggested density; no pipeline
    is invoked, no polyMesh is mutated."""
    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v131")
    result = dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    assert result.tool == "regenerate_mesh"
    assert "AI suggests" in result.summary
    assert "'power' mode" in result.summary
    assert result.state_after["advisory"] is True
    assert result.state_after["suggestion"]["axis"] == "mesh_mode"
    assert result.state_after["suggestion"]["mesh_mode"] == "power"


def test_dispatch_regenerate_mesh_summary_advises_step_2(tmp_path):
    """DEC-V61-131 N1.1: the advisory summary tells the engineer to
    apply via Step 2's [AI 处理] button — the only mesh-mutation
    surface that survives the strip."""
    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v131_advice")
    result = dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "beginner"})
    assert "Step 2" in result.summary
    assert "AI 处理" in result.summary
    assert "N1.1" in result.summary or "V130" in result.summary


def test_regenerate_mesh_rejects_extra_keys(tmp_path):
    """V121 trust-boundary discipline: extra="forbid" rejects
    off-contract keys, never silently drops them."""
    case_dir = _make_minimal_case_dir(tmp_path)
    with pytest.raises(ToolArgError):
        dispatch(
            case_dir,
            "regenerate_mesh",
            {"mesh_mode": "power", "lc_override": 0.001},
        )


def test_regenerate_mesh_rejects_invalid_mode(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    with pytest.raises(ToolArgError):
        dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "ultra"})


def test_regenerate_mesh_missing_mode_raises_arg_error(tmp_path):
    case_dir = _make_minimal_case_dir(tmp_path)
    with pytest.raises(ToolArgError):
        dispatch(case_dir, "regenerate_mesh", {})


# DEC-V61-131 N1.1: the V123 R1 P2-1 / P2-2 / R2 P2-1 contracts that
# previously routed MeshPipelineError → underlying_service_error and
# CaseLockError → underlying_service_error are NO LONGER reachable via
# the regenerate_mesh tool dispatch path: the handler does not call
# ``mesh_imported_case`` or acquire ``case_lock`` anymore. Tests that
# asserted those translations are removed; the legacy mesh route
# (``POST /api/import/{case_id}/mesh``) still exercises those contracts
# directly and is covered by ``test_mesh_imported_route.py`` /
# ``test_meshing_gmsh.py``.


def test_regenerate_mesh_disappeared_case_dir_advisory_still_rejects(
    tmp_path,
):
    """DEC-V61-131 N1.1: even though the handler is advisory-only, a
    request against a vanished case_dir still surfaces
    inner_failing_check='case_disappeared' — surfacing a suggestion
    against a non-existent case is misleading. The pre-check must NOT
    create the case_dir."""
    case_dir = tmp_path / "ldc_v131_gone"
    with pytest.raises(ToolDispatchError) as exc_info:
        dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    assert exc_info.value.failing_check == "underlying_service_error"
    assert exc_info.value.inner_failing_check == "case_disappeared"
    assert not case_dir.exists()


def test_regenerate_mesh_idempotent_re_dispatch(tmp_path):
    """DEC-V61-131 N1.1: advisory dispatch is naturally idempotent —
    two calls with same args produce the same advisory ApplyResult.
    No mesh pipeline is invoked, no polyMesh write occurs."""
    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v131_idem")
    r1 = dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    r2 = dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    assert r1.state_after == r2.state_after
    assert r1.summary == r2.summary
    # polyMesh must remain absent (or unchanged) — advisory dispatch
    # does not write.
    assert not (case_dir / "constant" / "polyMesh").exists()


# ────────── DEC-V61-125 · lc_override arg ──────────


def test_regenerate_args_accepts_lc_override():
    """V125: lc_override alone (no mesh_mode, no target_cell_count) is
    a valid args payload."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    args = RegenerateMeshArgs(lc_override=0.005)
    assert args.lc_override == 0.005
    assert args.mesh_mode is None
    assert args.target_cell_count is None


def test_regenerate_args_rejects_lc_override_zero():
    """V125: lc_override must be >0 (Pydantic gt=0 constraint)."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    with pytest.raises(ValueError):
        RegenerateMeshArgs(lc_override=0)


def test_regenerate_args_rejects_lc_override_negative():
    """V125: negative lc is meaningless and must reject."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    with pytest.raises(ValueError):
        RegenerateMeshArgs(lc_override=-0.001)


def test_regenerate_args_rejects_lc_override_with_mesh_mode():
    """V125: 3-way mutual exclusion — lc_override + mesh_mode rejects."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    with pytest.raises(ValueError):
        RegenerateMeshArgs(mesh_mode="power", lc_override=0.005)


def test_regenerate_args_rejects_lc_override_with_target_cell_count():
    """V125: 3-way mutual exclusion — lc_override + target_cell_count
    rejects."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    with pytest.raises(ValueError):
        RegenerateMeshArgs(target_cell_count=100_000, lc_override=0.005)


def test_regenerate_args_rejects_all_three_set():
    """V125: 3-way mutual exclusion — all three set rejects."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    with pytest.raises(ValueError):
        RegenerateMeshArgs(
            mesh_mode="power",
            target_cell_count=100_000,
            lc_override=0.005,
        )


def test_dispatch_regenerate_mesh_lc_override_rejected_unsupported_axis(tmp_path):
    """DEC-V61-131 N1.1 R19 P2 close (Codex 86gs branch-level review):
    lc_override has no Step 2 manual-replay UI, so accepting an
    advisory on this axis would produce advice the engineer can't
    apply. Dispatch raises ToolDispatchError(unsupported_axis)
    instead of returning a dead-end advisory."""
    from ui.backend.services.llm_coach.tool_registry import ToolDispatchError

    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v131_lc")
    with pytest.raises(ToolDispatchError) as ctx:
        dispatch(case_dir, "regenerate_mesh", {"lc_override": 0.005})
    assert ctx.value.failing_check == "unsupported_axis"
    assert ctx.value.inner_failing_check == "lc_override"


def test_dispatch_regenerate_mesh_lc_override_message_points_to_mesh_mode(tmp_path):
    """R19 P2 close: the rejection message tells the engineer how to
    proceed (use mesh_mode beginner/power, or apply manually via
    Step 2 advanced)."""
    from ui.backend.services.llm_coach.tool_registry import ToolDispatchError

    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v131_lc_msg")
    with pytest.raises(ToolDispatchError) as ctx:
        dispatch(case_dir, "regenerate_mesh", {"lc_override": 0.005})
    msg = str(ctx.value)
    assert "mesh_mode" in msg
    assert "beginner" in msg or "power" in msg


def test_regenerate_mesh_tool_description_mentions_lc_override():
    """V125: tool description string surfaces lc_override + gt=0
    constraint so the LLM knows the schema."""
    [tool] = [t for t in list_tools() if t.name == "regenerate_mesh"]
    desc = tool.description
    assert "lc_override" in desc
    # The "positive" constraint must be discoverable.
    assert "positive" in desc.lower() or "gt=0" in desc or "> 0" in desc


def test_run_gmsh_rejects_zero_lc_override_directly(tmp_path):
    """V125 R1 P3: a direct backend caller of run_gmsh_on_imported_case
    that bypasses the RegenerateMeshArgs Pydantic gt=0 validation MUST
    still fail fast — the parent-layer guard rejects non-positive
    characteristic_length_override before the subprocess spawn so a
    bad value can't silently fall through to default-sized meshing."""
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        run_gmsh_on_imported_case,
    )

    stl_path = tmp_path / "x.stl"
    stl_path.write_text("dummy")  # path needs to exist; validation
                                   # fires before the subprocess opens it
    msh_path = tmp_path / "x.msh"
    with pytest.raises(ValueError, match="must be positive"):
        run_gmsh_on_imported_case(
            stl_path=stl_path,
            output_msh_path=msh_path,
            characteristic_length_override=0.0,
        )


def test_run_gmsh_rejects_negative_lc_override_directly(tmp_path):
    """V125 R1 P3 negative path: a negative override is also invalid."""
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        run_gmsh_on_imported_case,
    )

    stl_path = tmp_path / "x.stl"
    stl_path.write_text("dummy")
    msh_path = tmp_path / "x.msh"
    with pytest.raises(ValueError, match="must be positive"):
        run_gmsh_on_imported_case(
            stl_path=stl_path,
            output_msh_path=msh_path,
            characteristic_length_override=-0.001,
        )


def test_run_gmsh_lc_override_validation_respects_target_cell_count_precedence(
    tmp_path, monkeypatch
):
    """V125 R2 P2: when target_cell_count is also set, the documented
    precedence (target_cell_count > characteristic_length_override >
    mesh_mode) means the override is ignored. Therefore a stale
    sentinel 0.0 carried over from an older call shape must NOT
    raise — validation is gated to fire only when the override is
    actually going to be consumed."""
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    class _FakeProc:
        exitcode = 0

        def start(self):
            pass

        def join(self):
            pass

    class _FakeCtx:
        def Queue(self):
            from queue import Queue as _Q

            q = _Q()
            q.put(("backend_error", "test stub — no real gmsh invoked"))
            return q

        def Process(self, target, args):
            return _FakeProc()

    monkeypatch.setattr(
        "ui.backend.services.meshing_gmsh.gmsh_runner.multiprocessing.get_context",
        lambda _: _FakeCtx(),
    )
    stl_path = tmp_path / "x.stl"
    stl_path.write_text("dummy")
    msh_path = tmp_path / "x.msh"
    # 0.0 is non-positive, but target_cell_count is set — so the
    # override is ignored by precedence and validation must NOT fire.
    try:
        runner_mod.run_gmsh_on_imported_case(
            stl_path=stl_path,
            output_msh_path=msh_path,
            target_cell_count=100_000,
            characteristic_length_override=0.0,
        )
    except ValueError as exc:
        if "must be positive" in str(exc):
            pytest.fail(
                "Validation must NOT fire when target_cell_count "
                "supersedes the override (R2 P2 precedence rule)."
            )
    except Exception:
        # Any other exception is fine — only the must-be-positive
        # ValueError is forbidden in this scenario.
        pass


def test_run_gmsh_accepts_none_lc_override(tmp_path, monkeypatch):
    """V125 R1 P3 negative control: None is a legal override value
    (means 'use mesh_mode default' — the validation must NOT reject
    None, only non-positive numbers)."""
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod

    # Block before subprocess spawn so we don't actually run gmsh —
    # we just want to verify the new ValueError guard doesn't fire on
    # None. Patch ctx.Process so .start() is a no-op.
    class _FakeProc:
        exitcode = 0

        def start(self):
            pass

        def join(self):
            pass

    class _FakeCtx:
        def Queue(self):
            from queue import Queue as _Q

            q = _Q()
            # Pre-populate so the parent's empty-queue detection passes
            q.put(("backend_error", "test stub — no real gmsh invoked"))
            return q

        def Process(self, target, args):
            return _FakeProc()

    monkeypatch.setattr(
        "ui.backend.services.meshing_gmsh.gmsh_runner.multiprocessing.get_context",
        lambda _: _FakeCtx(),
    )
    stl_path = tmp_path / "x.stl"
    stl_path.write_text("dummy")
    msh_path = tmp_path / "x.msh"
    # The value None must pass the new guard (the run will then fail
    # later for unrelated reasons in our stub, which is fine — we only
    # care that the ValueError guard does NOT fire).
    try:
        runner_mod.run_gmsh_on_imported_case(
            stl_path=stl_path,
            output_msh_path=msh_path,
            characteristic_length_override=None,
        )
    except ValueError as exc:
        if "must be positive" in str(exc):
            pytest.fail(
                "None must NOT trigger the positive-only validation guard"
            )
    except Exception:
        # Any other failure is fine for this test — we're only
        # asserting that the ValueError guard doesn't reject None.
        pass


def test_regenerate_args_v124_target_cell_count_path_unchanged():
    """V125 regression: V124 target_cell_count-only path still
    validates and dispatches correctly after the 3-way validator
    refactor."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    args = RegenerateMeshArgs(target_cell_count=100_000)
    assert args.target_cell_count == 100_000
    assert args.mesh_mode is None
    assert args.lc_override is None


def test_regenerate_args_v123_mesh_mode_path_unchanged():
    """V125 regression: V123 mesh_mode-only path still validates
    after the 3-way validator refactor."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    args = RegenerateMeshArgs(mesh_mode="power")
    assert args.mesh_mode == "power"
    assert args.target_cell_count is None
    assert args.lc_override is None


# ────────── DEC-V61-124 · target_cell_count arg ──────────


def test_regenerate_args_accepts_target_cell_count():
    """V124: target_cell_count alone (no mesh_mode) is a valid args
    payload."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    args = RegenerateMeshArgs(target_cell_count=100_000)
    assert args.target_cell_count == 100_000
    assert args.mesh_mode is None


def test_regenerate_args_accepts_mesh_mode_only():
    """V124: existing V123 mesh_mode-only path still works."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    args = RegenerateMeshArgs(mesh_mode="power")
    assert args.mesh_mode == "power"
    assert args.target_cell_count is None


def test_regenerate_args_rejects_both_set():
    """V124: mutual exclusion — both fields set at once must fail."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    with pytest.raises(ValueError):
        RegenerateMeshArgs(mesh_mode="power", target_cell_count=100_000)


def test_regenerate_args_rejects_neither_set():
    """V124: mutual exclusion — neither field set must also fail (no
    ambiguous default)."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    with pytest.raises(ValueError):
        RegenerateMeshArgs()


def test_regenerate_args_target_cell_count_floor():
    """V124: target_cell_count must be >= 1000 (Pydantic ge=1000)."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    with pytest.raises(ValueError):
        RegenerateMeshArgs(target_cell_count=999)
    # 1000 is the floor and must accept.
    RegenerateMeshArgs(target_cell_count=1_000)


def test_regenerate_args_target_cell_count_ceiling():
    """V124: target_cell_count must be <= 50_000_000 (matches V61-105
    hard cap)."""
    from ui.backend.services.llm_coach.tool_registry import RegenerateMeshArgs

    with pytest.raises(ValueError):
        RegenerateMeshArgs(target_cell_count=50_000_001)
    # Exact cap accepts.
    RegenerateMeshArgs(target_cell_count=50_000_000)


def test_dispatch_regenerate_mesh_target_cell_count_rejected_unsupported_axis(tmp_path):
    """DEC-V61-131 N1.1 R19 P2 close: same rejection contract as
    lc_override — target_cell_count has no Step 2 manual-replay UI."""
    from ui.backend.services.llm_coach.tool_registry import ToolDispatchError

    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v131_target")
    with pytest.raises(ToolDispatchError) as ctx:
        dispatch(
            case_dir, "regenerate_mesh", {"target_cell_count": 500_000}
        )
    assert ctx.value.failing_check == "unsupported_axis"
    assert ctx.value.inner_failing_check == "target_cell_count"


def test_dispatch_regenerate_mesh_target_cell_count_message_points_to_mesh_mode(tmp_path):
    """R19 P2 close: rejection message routes the engineer to
    mesh_mode."""
    from ui.backend.services.llm_coach.tool_registry import ToolDispatchError

    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v131_target_msg")
    with pytest.raises(ToolDispatchError) as ctx:
        dispatch(
            case_dir, "regenerate_mesh", {"target_cell_count": 500_000}
        )
    msg = str(ctx.value)
    assert "mesh_mode" in msg
    assert "beginner" in msg or "power" in msg


def test_dispatch_regenerate_mesh_v123_mesh_mode_path_advisory(tmp_path):
    """DEC-V61-131 N1.1: mesh_mode='power' still routes through the
    advisory handler with the correct axis label."""
    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v131_regress")
    result = dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    assert "'power' mode" in result.summary
    assert result.state_after["suggestion"]["axis"] == "mesh_mode"
    assert result.state_after["suggestion"]["mesh_mode"] == "power"


def test_regenerate_mesh_tool_description_mentions_target_cell_count():
    """V124: tool description string surfaces target_cell_count + bounds
    so the LLM knows the schema."""
    [tool] = [t for t in list_tools() if t.name == "regenerate_mesh"]
    desc = tool.description
    assert "target_cell_count" in desc
    # Bounds must be discoverable for the LLM.
    assert "1000" in desc or "1,000" in desc or "1k" in desc
    assert "50000000" in desc or "50,000,000" in desc or "50M" in desc


# ────────── V124 cube-formula sanity (lc-from-target_cell_count) ──────────


def test_lc_from_target_cell_count_matches_beginner_preset_for_30k():
    """V124 AC-5: for a unit cube (diagonal=sqrt(3)) and target=30k,
    the V124 formula must match the V123 beginner preset (d/30) within
    5%. This regression-protects the formula calibration."""
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        _default_characteristic_length,
        _lc_from_target_cell_count,
    )
    import math

    diagonal = math.sqrt(3.0)  # unit cube
    lc_v124 = _lc_from_target_cell_count(diagonal, 30_000)
    lc_v123_beginner = _default_characteristic_length(diagonal, "beginner")
    # Within 5% of the V123 preset.
    assert abs(lc_v124 - lc_v123_beginner) / lc_v123_beginner < 0.05


def test_lc_from_target_cell_count_matches_power_preset_for_250k():
    """V124 AC-6: the formula must also match the V123 power preset
    (d/60) at target=250k within 5%."""
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        _default_characteristic_length,
        _lc_from_target_cell_count,
    )
    import math

    diagonal = math.sqrt(3.0)
    lc_v124 = _lc_from_target_cell_count(diagonal, 250_000)
    lc_v123_power = _default_characteristic_length(diagonal, "power")
    assert abs(lc_v124 - lc_v123_power) / lc_v123_power < 0.05


def test_classify_cell_count_target_mode_suppresses_beginner_soft_warning():
    """V124 R1 P2: when target_cell_count is the path the engineer
    chose, classify_cell_count under 'target' mode must NOT emit the
    'larger than typical beginner sizing' warning that beginner mode
    fires above 5M cells. The engineer explicitly asked for this
    count; the hard cap is the only relevant safety check."""
    from ui.backend.services.meshing_gmsh.cell_budget import (
        classify_cell_count,
    )

    verdict = classify_cell_count(10_000_000, "target")
    assert verdict.ok is True
    assert verdict.warning is None  # NOT the beginner soft-warning
    # mesh_mode passed through honestly.
    assert verdict.mesh_mode == "target"


def test_classify_cell_count_target_mode_still_enforces_hard_cap():
    """V124 R1 P2: even under 'target' mode the 50M hard cap must
    still reject — the V61-105 resource safety contract is
    independent of which path supplied lc."""
    from ui.backend.services.meshing_gmsh.cell_budget import (
        classify_cell_count,
        POWER_HARD_CAP_CELLS,
    )

    verdict = classify_cell_count(POWER_HARD_CAP_CELLS + 1, "target")
    assert verdict.ok is False
    assert verdict.rejection_reason is not None
    assert "hard cap" in verdict.rejection_reason


def test_mesh_summary_schema_serializes_target_mode():
    """V124 R2 P1: MeshSummary.mesh_mode_used MUST accept 'target' so a
    caller plumbing target_cell_count through /api/import/{case_id}/mesh
    (or any other route that builds MeshSummary from MeshResult)
    doesn't 500 on response-model validation. The R2 finding caught
    that the schema's MeshMode literal was scoped to beginner/power
    only — the schema-side expansion is the load-bearing fix."""
    from ui.backend.schemas.mesh_imported import MeshSummary

    s = MeshSummary(
        cell_count=10_000_000,
        face_count=60_000_000,
        point_count=12_000_000,
        mesh_mode_used="target",
        polyMesh_path="/tmp/x/constant/polyMesh",
        msh_path="/tmp/x/imported.msh",
        generation_time_s=120.5,
        warning=None,
    )
    assert s.mesh_mode_used == "target"


def test_mesh_request_schema_rejects_target_mode():
    """V124 R2 P1 negative control: MeshRequest must NOT accept
    'target' as input — the import-mesh POST route does not yet
    plumb target_cell_count, and accepting 'target' as a mesh_mode
    input would silently fall through to default beginner sizing.
    Splitting input vs output literals keeps that boundary honest."""
    from ui.backend.schemas.mesh_imported import MeshRequest

    with pytest.raises(ValueError):
        MeshRequest(mesh_mode="target")  # type: ignore[arg-type]


def test_classify_cell_count_beginner_soft_warning_still_fires():
    """V124 R1 P2 negative control: the V123 beginner-mode soft warning
    contract is unchanged — beginner > 5M still warns."""
    from ui.backend.services.meshing_gmsh.cell_budget import (
        classify_cell_count,
        BEGINNER_SOFT_CAP_CELLS,
    )

    verdict = classify_cell_count(BEGINNER_SOFT_CAP_CELLS + 1, "beginner")
    assert verdict.ok is True
    assert verdict.warning is not None
    assert "larger than typical beginner sizing" in verdict.warning


def test_lc_from_target_cell_count_degenerate_diagonal_returns_zero():
    """V124: a zero or negative diagonal (degenerate input) returns 0
    so the caller falls back to gmsh's default sizing."""
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        _lc_from_target_cell_count,
    )

    assert _lc_from_target_cell_count(0.0, 100_000) == 0.0
    assert _lc_from_target_cell_count(-1.0, 100_000) == 0.0
    assert _lc_from_target_cell_count(1.0, 0) == 0.0


def test_regenerate_mesh_does_not_acquire_case_lock(tmp_path):
    """DEC-V61-131 N1.1 advisory contract: dispatch must NOT acquire
    the case_lock. The pre-N1.1 path took ``case_lock`` for the duration
    of ``mesh_imported_case`` to serialize concurrent regenerate
    accepts; with the strip, the handler does no I/O against the case
    contents and therefore should not write a ``.case_lock`` file."""
    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v131_nolock")
    lock_path = case_dir / ".case_lock"
    assert not lock_path.exists()
    dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    # No lock file should have been created — advisory handler does
    # not touch case state.
    assert not lock_path.exists()

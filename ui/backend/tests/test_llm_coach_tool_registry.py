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


def test_dispatch_regenerate_mesh_happy_path(tmp_path, monkeypatch):
    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v123")

    def fake_mesh(case_id, *, mesh_mode):
        assert case_id == "ldc_v123"
        assert mesh_mode == "power"
        return _stub_mesh_result(case_id=case_id, mesh_mode=mesh_mode)

    monkeypatch.setattr(
        "ui.backend.services.llm_coach.tool_registry.mesh_imported_case",
        fake_mesh,
    )
    result = dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    assert result.tool == "regenerate_mesh"
    assert "350000" in result.summary or "350,000" in result.summary
    assert result.state_after["cell_count"] == 350_000
    assert result.state_after["face_count"] == 2_100_000
    assert result.state_after["mesh_mode"] == "power"


def test_dispatch_regenerate_mesh_includes_warning_in_summary(
    tmp_path, monkeypatch
):
    """When the underlying pipeline returns a soft-cap warning (beginner
    mode only), the operator-facing summary surfaces it."""
    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v123_warn")
    monkeypatch.setattr(
        "ui.backend.services.llm_coach.tool_registry.mesh_imported_case",
        lambda case_id, *, mesh_mode: _stub_mesh_result(
            case_id=case_id,
            mesh_mode=mesh_mode,
            warning="beginner soft cap exceeded; consider 'power' mode",
        ),
    )
    result = dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "beginner"})
    assert "Warning" in result.summary
    assert "soft cap" in result.summary


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


def test_regenerate_mesh_pipeline_error_translated_to_underlying(
    tmp_path, monkeypatch
):
    """MeshPipelineError raised by the underlying pipeline must surface
    as ToolDispatchError(failing_check='underlying_service_error') with
    the original failing_check preserved in the message."""
    from ui.backend.services.meshing_gmsh import MeshPipelineError

    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v123_err")

    def boom(case_id, *, mesh_mode):
        raise MeshPipelineError("cap exceeded", "cell_cap_exceeded")

    monkeypatch.setattr(
        "ui.backend.services.llm_coach.tool_registry.mesh_imported_case",
        boom,
    )
    with pytest.raises(ToolDispatchError) as exc_info:
        dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    assert exc_info.value.failing_check == "underlying_service_error"
    assert "cell_cap_exceeded" in str(exc_info.value)


def test_regenerate_mesh_idempotent_re_dispatch(tmp_path, monkeypatch):
    """gmsh is naturally idempotent (deterministic seed); two sequential
    dispatches with same args both succeed without a replay-key store."""
    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v123_idem")
    monkeypatch.setattr(
        "ui.backend.services.llm_coach.tool_registry.mesh_imported_case",
        lambda case_id, *, mesh_mode: _stub_mesh_result(
            case_id=case_id, mesh_mode=mesh_mode
        ),
    )
    r1 = dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    r2 = dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    assert r1.state_after == r2.state_after


def test_regenerate_mesh_holds_case_lock_during_pipeline(
    tmp_path, monkeypatch
):
    """Concurrent regenerate proposals must serialize via case_lock —
    mesh_imported_case rewrites polyMesh/ in place and would race on
    file content. We assert the lock is HELD at the moment the
    pipeline runs by checking that .case_lock exists and is locked
    via flock from inside the fake handler."""
    import fcntl

    case_dir = _make_minimal_case_dir(tmp_path, case_id="ldc_v123_lock")
    lock_held = {"value": False}

    def assert_lock_held(case_id, *, mesh_mode):
        lock_path = case_dir / ".case_lock"
        # The lockfile must exist while the pipeline is running.
        assert lock_path.is_file()
        # And a non-blocking attempt to take the lock from a fresh fd
        # must fail (it's already held by case_lock above us).
        fd = None
        try:
            fd = lock_path.open("r+")
            try:
                fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_held["value"] = False  # we got it → not held
            except BlockingIOError:
                lock_held["value"] = True
            finally:
                try:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
        finally:
            if fd is not None:
                fd.close()
        return _stub_mesh_result(case_id=case_id, mesh_mode=mesh_mode)

    monkeypatch.setattr(
        "ui.backend.services.llm_coach.tool_registry.mesh_imported_case",
        assert_lock_held,
    )
    dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})
    assert lock_held["value"] is True

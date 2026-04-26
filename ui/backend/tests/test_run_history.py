"""Tests for ui.backend.services.run_history (M3).

Covers the write/list/get roundtrip + safety / defense behaviours.
All tests use tmp_path for the artifact root — never write to the real
reports/ tree.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from ui.backend.services.run_history import (
    get_run_detail,
    list_recent_runs_across_cases,
    list_runs,
    new_run_id,
    run_dir,
    write_run_artifacts,
)


def _make_fake_task_spec(name: str = "Lid-Driven Cavity", Re: float = 100.0):
    """Lightweight stand-in for src.models.TaskSpec — only the attributes
    write_run_artifacts._task_spec_to_excerpt actually reads."""
    class _FakeEnum:
        def __init__(self, value): self.value = value

    class _FakeSpec:
        pass
    s = _FakeSpec()
    s.name = name
    s.Re = Re
    s.Ra = None
    s.Re_tau = None
    s.Ma = None
    s.geometry_type = _FakeEnum("SIMPLE_GRID")
    s.flow_type = _FakeEnum("INTERNAL")
    s.steady_state = _FakeEnum("STEADY")
    s.compressibility = _FakeEnum("INCOMPRESSIBLE")
    return s


def test_new_run_id_is_filesystem_safe() -> None:
    rid = new_run_id()
    # Must not contain the colons that would break common filesystem APIs
    # on FAT32 / unusual mounts. ISO format colons → dashes.
    assert ":" not in rid
    # Sanity: looks ISO-like (year-month-day...Z).
    assert "T" in rid and rid.endswith("Z")


def test_run_dir_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        run_dir("../escape", "any", root=tmp_path)
    with pytest.raises(ValueError):
        run_dir("ok", "../../escape", root=tmp_path)


def test_write_then_list_then_get_roundtrip(tmp_path: Path) -> None:
    started = datetime(2026, 4, 26, 3, 12, 30, tzinfo=timezone.utc)
    write_run_artifacts(
        case_id="lid_driven_cavity",
        run_id="2026-04-26T03-12-30Z",
        started_at=started,
        task_spec=_make_fake_task_spec(Re=400.0),
        source_origin="draft",
        success=True,
        exit_code=0,
        verdict_summary="OpenFOAM converged · 12.5s · 1 key quantity",
        duration_s=12.5,
        key_quantities={"u_max": 0.61},
        residuals={"Ux": 1.2e-5, "p": 5.6e-4},
        error_message=None,
        root=tmp_path,
    )
    # Files exist + parse cleanly.
    target = tmp_path / "lid_driven_cavity" / "runs" / "2026-04-26T03-12-30Z"
    assert (target / "measurement.yaml").exists()
    assert (target / "verdict.json").exists()
    assert (target / "summary.json").exists()
    measurement = yaml.safe_load((target / "measurement.yaml").read_text())
    assert measurement["key_quantities"] == {"u_max": 0.61}
    assert measurement["residuals"] == {"Ux": 1.2e-5, "p": 5.6e-4}
    verdict = json.loads((target / "verdict.json").read_text())
    assert verdict["success"] is True
    assert verdict["exit_code"] == 0
    summary = json.loads((target / "summary.json").read_text())
    assert summary["source_origin"] == "draft"
    assert summary["task_spec"]["Re"] == 400.0
    assert summary["task_spec"]["geometry_type"] == "SIMPLE_GRID"

    # list_runs picks it up.
    listing = list_runs("lid_driven_cavity", root=tmp_path)
    assert len(listing) == 1
    row = listing[0]
    assert row.run_id == "2026-04-26T03-12-30Z"
    assert row.success is True
    assert row.exit_code == 0
    assert row.task_spec_excerpt["Re"] == 400.0

    # get_run_detail returns the full record.
    detail = get_run_detail("lid_driven_cavity", "2026-04-26T03-12-30Z", root=tmp_path)
    assert detail.success is True
    assert detail.task_spec["Re"] == 400.0
    assert detail.key_quantities == {"u_max": 0.61}
    assert detail.residuals == {"Ux": 1.2e-5, "p": 5.6e-4}


def test_list_runs_newest_first(tmp_path: Path) -> None:
    started = datetime(2026, 4, 26, 3, 0, 0, tzinfo=timezone.utc)
    for run_id in ["2026-04-26T03-00-00Z", "2026-04-26T03-15-00Z", "2026-04-26T03-30-00Z"]:
        write_run_artifacts(
            case_id="lid_driven_cavity",
            run_id=run_id,
            started_at=started,
            task_spec=_make_fake_task_spec(),
            source_origin="whitelist",
            success=True,
            exit_code=0,
            verdict_summary="ok",
            duration_s=1.0,
            key_quantities={},
            residuals={},
            root=tmp_path,
        )
    listing = list_runs("lid_driven_cavity", root=tmp_path)
    ids = [r.run_id for r in listing]
    # Sorted reverse-lex == newest first because run_ids are ISO timestamps.
    assert ids == [
        "2026-04-26T03-30-00Z",
        "2026-04-26T03-15-00Z",
        "2026-04-26T03-00-00Z",
    ]


def test_list_runs_skips_partial_dirs(tmp_path: Path) -> None:
    """A run_dir that has summary.json but not verdict.json (in-progress)
    must be skipped, not crash list_runs."""
    started = datetime(2026, 4, 26, 3, 0, 0, tzinfo=timezone.utc)
    write_run_artifacts(
        case_id="lid_driven_cavity",
        run_id="2026-04-26T03-00-00Z",
        started_at=started,
        task_spec=_make_fake_task_spec(),
        source_origin="whitelist",
        success=True, exit_code=0, verdict_summary="ok",
        duration_s=1.0, key_quantities={}, residuals={},
        root=tmp_path,
    )
    # Inject a malformed run dir.
    rogue = tmp_path / "lid_driven_cavity" / "runs" / "2026-04-26T03-99-00Z"
    rogue.mkdir(parents=True)
    (rogue / "summary.json").write_text("{}")  # missing verdict.json
    listing = list_runs("lid_driven_cavity", root=tmp_path)
    assert len(listing) == 1
    assert listing[0].run_id == "2026-04-26T03-00-00Z"


def test_list_runs_empty_for_unknown_case(tmp_path: Path) -> None:
    assert list_runs("never_existed", root=tmp_path) == []


def test_get_run_detail_404_on_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        get_run_detail("never_existed", "2026-04-26T03-00-00Z", root=tmp_path)


def test_get_run_detail_404_on_partial_dir(tmp_path: Path) -> None:
    rogue = tmp_path / "lid_driven_cavity" / "runs" / "2026-04-26T03-00-00Z"
    rogue.mkdir(parents=True)
    (rogue / "summary.json").write_text("{}")  # no verdict, no measurement
    with pytest.raises(FileNotFoundError):
        get_run_detail("lid_driven_cavity", "2026-04-26T03-00-00Z", root=tmp_path)


def test_list_recent_runs_across_cases_newest_first(tmp_path: Path) -> None:
    """Cross-case feed must merge runs from multiple case buckets and
    sort by started_at descending. Pre-existing legacy reports/ buckets
    (deep_acceptance/, phase5_audit/, ...) that don't follow the M3
    case_id alphabet must be silently ignored, not crash."""
    # Two LDC runs and one cylinder run, intentionally written out of
    # chronological order to exercise the sort.
    plan = [
        ("lid_driven_cavity", datetime(2026, 4, 26, 5, 0, 0, tzinfo=timezone.utc)),
        ("circular_cylinder_wake", datetime(2026, 4, 26, 6, 0, 0, tzinfo=timezone.utc)),
        ("lid_driven_cavity", datetime(2026, 4, 26, 4, 0, 0, tzinfo=timezone.utc)),
    ]
    for case_id, started in plan:
        rid = started.isoformat().replace("+00:00", "Z").replace(":", "-")
        write_run_artifacts(
            case_id=case_id,
            run_id=rid,
            started_at=started,
            task_spec=_make_fake_task_spec(),
            source_origin="whitelist",
            success=True,
            exit_code=0,
            verdict_summary=f"converged · {case_id}",
            duration_s=10.0,
            key_quantities={},
            residuals={},
            root=tmp_path,
        )
    # Legacy bucket that uses an alphabet outside the case_id rule —
    # underscore is fine but we add a name with a forbidden char to
    # confirm it's skipped, not crashed on.
    legacy = tmp_path / "phase5_audit" / "live_2026-04-21.log"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("not a run dir")

    recent = list_recent_runs_across_cases(limit=50, root=tmp_path)
    assert len(recent) == 3
    # Newest first by started_at.
    assert recent[0].case_id == "circular_cylinder_wake"
    assert recent[0].run_id.startswith("2026-04-26T06-")
    assert recent[1].run_id.startswith("2026-04-26T05-")
    assert recent[2].run_id.startswith("2026-04-26T04-")


def test_list_recent_runs_respects_limit(tmp_path: Path) -> None:
    for hour in range(5):
        started = datetime(2026, 4, 26, hour, 0, 0, tzinfo=timezone.utc)
        rid = started.isoformat().replace("+00:00", "Z").replace(":", "-")
        write_run_artifacts(
            case_id="lid_driven_cavity",
            run_id=rid,
            started_at=started,
            task_spec=_make_fake_task_spec(),
            source_origin="whitelist",
            success=True,
            exit_code=0,
            verdict_summary="ok",
            duration_s=1.0,
            key_quantities={},
            residuals={},
            root=tmp_path,
        )
    recent = list_recent_runs_across_cases(limit=2, root=tmp_path)
    assert len(recent) == 2
    # Highest hour comes first.
    assert recent[0].run_id.startswith("2026-04-26T04-")


def test_list_recent_runs_empty_root(tmp_path: Path) -> None:
    assert list_recent_runs_across_cases(limit=50, root=tmp_path) == []


def test_failure_run_persists_error_message(tmp_path: Path) -> None:
    started = datetime(2026, 4, 26, 4, 0, 0, tzinfo=timezone.utc)
    write_run_artifacts(
        case_id="lid_driven_cavity",
        run_id="2026-04-26T04-00-00Z",
        started_at=started,
        task_spec=_make_fake_task_spec(Re=10000.0),  # reckless Re for LDC
        source_origin="draft",
        success=False,
        exit_code=137,
        verdict_summary="OpenFOAM diverged at t=4.2s",
        duration_s=4.2,
        key_quantities=None,
        residuals=None,
        error_message="continuity error 1e62, max(Co)=98.7",
        root=tmp_path,
    )
    detail = get_run_detail("lid_driven_cavity", "2026-04-26T04-00-00Z", root=tmp_path)
    assert detail.success is False
    assert detail.exit_code == 137
    assert "continuity error" in (detail.error_message or "")

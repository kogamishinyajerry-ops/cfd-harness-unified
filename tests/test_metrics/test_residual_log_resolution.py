"""DEC-V61-059 Codex round-5 F8 regression: downstream consumer
discovery must include `log.pisoFoam` for the plane-channel laminar
route. Stage B's artifact dir contains only `log.pisoFoam`; before
this fix, `_resolve_log_path` returned None on it.
"""

from __future__ import annotations

from pathlib import Path

from src.metrics.residual import _resolve_log_path


def test_resolve_log_path_finds_pisofoam(tmp_path: Path) -> None:
    log = tmp_path / "log.pisoFoam"
    log.write_text("Time = 0\nExecutionTime = 0 s\n", encoding="utf-8")
    found = _resolve_log_path({"case_dir": str(tmp_path)}, {})
    assert found == log, (
        "Stage B post-R3 plane-channel artifact dirs only contain "
        "log.pisoFoam (icoFoam → pisoFoam swap). _resolve_log_path "
        "must discover that filename."
    )


def test_resolve_log_path_simplefoam_still_works(tmp_path: Path) -> None:
    """Companion: don't regress simpleFoam discovery while widening."""
    log = tmp_path / "log.simpleFoam"
    log.write_text("Time = 0\n", encoding="utf-8")
    assert _resolve_log_path({"case_dir": str(tmp_path)}, {}) == log

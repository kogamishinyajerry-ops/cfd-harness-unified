"""Fixtures for report engine tests."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def temp_reports(tmp_path: Path, repo_root: Path) -> Path:
    target = tmp_path / "reports"
    shutil.copytree(repo_root / "reports", target)
    return target


@pytest.fixture
def run_subprocess():
    def _run(args):
        return subprocess.run(args, capture_output=True, text=True, check=False)

    return _run


"""Shared fixtures for AutoVerifier tests."""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def copy_case_fixture(tmp_path, fixture_root):
    def _copy(case_id: str) -> Path:
        source = fixture_root / case_id
        destination = tmp_path / case_id
        shutil.copytree(source, destination)
        return destination

    return _copy


@pytest.fixture
def directory_hash():
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        if not path.exists():
            digest.update(b"<missing>")
            return digest.hexdigest()

        for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
            digest.update(str(file_path.relative_to(path)).encode("utf-8"))
            digest.update(file_path.read_bytes())
        return digest.hexdigest()

    return _hash


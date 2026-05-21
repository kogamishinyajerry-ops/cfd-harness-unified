"""Shared pytest fixtures.

Post-merge layout (cfd-harness-unified/ui/backend/audit/):
  audit/
    cfdtrust/             # the trust-contract package (importable as `cfdtrust`)
    cfdtrust_tests/       # this directory
    cases/                # canonical case dirs
    tools/                # cwos_*.py (added in Phase D)
    .cwos/                # CWOS state (added in Phase D)
    docs/                 # PROGRESS, ROADMAP, status/red_team_round*.md (Phase D)
    pyproject.toml        # optional audit-local pyproject (Phase B verification)

Pre-merge AI-CFD-V2 layout was `src/cfdtrust/` + `tools/` + `tests/` +
`cases/` at repo root. Path constants have been re-pointed for the new
home; tests that need REPO_ROOT now get the `audit/` subsystem root,
not the cfd-harness-unified repo root.
"""
from __future__ import annotations

import sys
from pathlib import Path

# REPO_ROOT here means the audit subsystem root, NOT cfd-harness-unified root.
# The audit subsystem is intentionally self-contained per its dual-governance
# contract (see ui/backend/audit/README.md).
REPO_ROOT = Path(__file__).resolve().parent.parent  # → audit/
TOOLS = REPO_ROOT / "tools"

# Make `cfdtrust` importable without requiring an install step.
# `audit/cfdtrust/` is the package dir; adding audit/ to sys.path lets
# `import cfdtrust` resolve.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
# Make `cwos_paths` (and other tools/ utilities) importable in tests so the
# shared path-safety contract has exactly one definition. tools/ is created
# in Phase D — until then this path simply doesn't exist and that's fine.
if TOOLS.exists() and str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pytest


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def sample_case_dir() -> Path:
    return REPO_ROOT / "cases" / "flat_plate_rans_sst"

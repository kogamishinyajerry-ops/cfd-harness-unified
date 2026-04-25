"""Tests for ``src._plane_guard`` (ADR-002 W2 Impl Mid).

Coverage targets (ADR-002 §4.1 AC-A3):
  * (a) allowed import — Control → Execution: no raise
  * (b) forbidden import (strict_scope) — Execution → Evaluation: raises
  * (c) test-allowlist permits — same forbidden pair without strict_scope
  * (d) ``strict_scope()`` disables the test allowlist
  * (e) ``importlib.import_module`` dynamic dispatch caught
  * (f) ``__import__`` builtin caught

Plus essential lifecycle / mode / dedup tests:
  * install / uninstall is idempotent
  * external caller (no src.* in chain) is permissive
  * Mode.OFF is a no-op
  * WARN mode logs structured JSON without raising
  * WARN-mode dedup emits each (source, target, contract) once

The forbidden-import test exercises a synthetic plane crossing by
``exec()`` ing the import statement against globals whose ``__spec__``
declares a fake ``src.*`` source name. This avoids modifying any real
``src/`` module to violate its own contract.
"""

from __future__ import annotations

import importlib
import json
import logging
import sys
from importlib.machinery import ModuleSpec
from typing import Optional

import pytest

from src._plane_assignment import Plane
from src._plane_guard import (
    FORBIDDEN_PAIRS,
    LayerViolationError,
    Mode,
    PlaneGuardFinder,
    install_guard,
    is_installed,
    strict_scope,
    uninstall_guard,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def evict_test_targets():
    """Pop common cross-plane targets so the meta_path finder is consulted.

    Python short-circuits import when ``sys.modules`` already holds the
    key. For these tests we need the finder to actually run, so we
    evict candidate target modules and restore them after.
    """
    targets = [
        "src.result_comparator",
        "src.metrics",
        "src.knowledge_db",
        "src.task_runner",
        "src.foam_agent_adapter",
    ]
    saved = {}
    for name in targets:
        if name in sys.modules:
            saved[name] = sys.modules.pop(name)
    yield
    for name, module in saved.items():
        sys.modules[name] = module


@pytest.fixture
def guard_on(evict_test_targets):
    """Install the guard in ON mode and tear down afterwards."""
    uninstall_guard()  # Ensure clean state.
    install_guard(Mode.ON)
    try:
        yield
    finally:
        uninstall_guard()


@pytest.fixture
def guard_warn(evict_test_targets, caplog):
    """Install the guard in WARN mode + capture logs."""
    uninstall_guard()
    caplog.set_level(logging.WARNING, logger="src._plane_guard")
    install_guard(Mode.WARN)
    try:
        yield caplog
    finally:
        uninstall_guard()


def _exec_in_fake_plane(source_name: str, code: str) -> None:
    """Run ``code`` with globals that fake the caller's ``__spec__.name``.

    The guard's multi-frame walk reads ``frame.f_globals['__spec__'].name``
    first; setting that name to a real ``PLANE_OF`` entry makes the
    walk classify the exec frame as that plane. This is the cleanest
    way to drive synthetic plane crossings without modifying any real
    ``src/`` module to violate its own contract.
    """
    fake_spec = ModuleSpec(name=source_name, loader=None)
    exec_globals = {"__spec__": fake_spec, "__name__": source_name}
    exec(code, exec_globals)


# ---------------------------------------------------------------------------
# AC-A3 (a) · allowed import (Control → Execution)
# ---------------------------------------------------------------------------


def test_a3a_allowed_control_to_execution(guard_on):
    """Control is allowed to import Execution (dispatch direction)."""
    with strict_scope():
        # Should not raise — (Control, Execution) not in FORBIDDEN_PAIRS.
        _exec_in_fake_plane(
            "src.task_runner",
            "import src.foam_agent_adapter",
        )


# ---------------------------------------------------------------------------
# AC-A3 (b) · forbidden import (Execution → Evaluation) under strict_scope
# ---------------------------------------------------------------------------


def test_a3b_forbidden_execution_to_evaluation_raises(guard_on):
    """Execution → Evaluation is HARD NO; under strict_scope the guard raises."""
    with strict_scope():
        with pytest.raises(LayerViolationError) as exc_info:
            _exec_in_fake_plane(
                "src.foam_agent_adapter",
                "import src.result_comparator",
            )
    err = exc_info.value
    assert err.source_module == "src.foam_agent_adapter"
    assert err.source_plane == Plane.EXECUTION.value
    assert err.target_module == "src.result_comparator"
    assert err.target_plane == Plane.EVALUATION.value
    assert err.contract_name == "execution-never-imports-evaluation"
    # Subclass relationship preserved.
    assert isinstance(err, ImportError)


# ---------------------------------------------------------------------------
# AC-A3 (c) · test-allowlist permits forbidden pair without strict_scope
# ---------------------------------------------------------------------------


def test_a3c_test_allowlist_permits_forbidden_pair(guard_on):
    """Without strict_scope the test's own ``tests.*`` frame grants bypass."""
    # No strict_scope here — the calling frame's __name__ is
    # ``tests.test_plane_guard`` which matches the allowlist regex.
    _exec_in_fake_plane(
        "src.foam_agent_adapter",
        "import src.result_comparator",
    )


# ---------------------------------------------------------------------------
# AC-A3 (d) · strict_scope disables the allowlist
# ---------------------------------------------------------------------------


def test_a3d_strict_scope_disables_allowlist(guard_on):
    """strict_scope makes the same call from (c) raise."""
    with strict_scope():
        with pytest.raises(LayerViolationError):
            _exec_in_fake_plane(
                "src.foam_agent_adapter",
                "import src.result_comparator",
            )


def test_a3d_strict_scope_is_reentrant(guard_on):
    """Nested strict_scope unwinds correctly (counted exit)."""
    with strict_scope():
        with strict_scope():
            with pytest.raises(LayerViolationError):
                _exec_in_fake_plane(
                    "src.foam_agent_adapter",
                    "import src.result_comparator",
                )
        # Still inside outer scope; should still raise.
        with pytest.raises(LayerViolationError):
            _exec_in_fake_plane(
                "src.foam_agent_adapter",
                "import src.result_comparator",
            )
    # Outside scope; allowlist permits again.
    _exec_in_fake_plane(
        "src.foam_agent_adapter",
        "import src.result_comparator",
    )


# ---------------------------------------------------------------------------
# AC-A3 (e) · importlib.import_module dynamic dispatch caught
# ---------------------------------------------------------------------------


def test_a3e_importlib_import_module_caught(guard_on):
    """``importlib.import_module`` routes through meta_path → finder fires."""
    with strict_scope():
        with pytest.raises(LayerViolationError):
            _exec_in_fake_plane(
                "src.foam_agent_adapter",
                "import importlib; importlib.import_module('src.result_comparator')",
            )


# ---------------------------------------------------------------------------
# AC-A3 (f) · __import__ builtin caught
# ---------------------------------------------------------------------------


def test_a3f_dunder_import_caught(guard_on):
    """The ``__import__`` builtin also passes through meta_path."""
    with strict_scope():
        with pytest.raises(LayerViolationError):
            _exec_in_fake_plane(
                "src.foam_agent_adapter",
                "__import__('src.result_comparator')",
            )


# ---------------------------------------------------------------------------
# Lifecycle / mode behavior
# ---------------------------------------------------------------------------


def test_install_is_idempotent():
    """Repeated install_guard returns the existing finder, not a new one."""
    uninstall_guard()
    first = install_guard(Mode.ON)
    second = install_guard(Mode.ON)
    try:
        assert first is second
        assert is_installed()
    finally:
        uninstall_guard()
    assert not is_installed()


def test_mode_off_is_noop():
    """``Mode.OFF`` returns ``None`` and does not register a finder."""
    uninstall_guard()
    result = install_guard(Mode.OFF)
    assert result is None
    assert not is_installed()


def test_uninstall_when_not_installed_is_noop():
    """Calling uninstall without an install raises nothing."""
    uninstall_guard()
    uninstall_guard()  # Second call — must not raise.
    assert not is_installed()


def test_invalid_mode_raises_value_error():
    """Unknown mode strings are rejected at install time."""
    with pytest.raises(ValueError):
        install_guard("aggressive")


def test_external_caller_is_permissive(guard_on):
    """If the walk finds no ``src.*`` frame the guard returns ``None``."""
    # Globals with neither __spec__ nor __name__ from src.*; the walk
    # will not find a src.* hit, so the call should be permissive.
    # Using strict_scope to make sure test-allowlist doesn't mask
    # the result.
    with strict_scope():
        # Doing an import here to a known src.* target; from a fake
        # external module, this should not raise.
        _exec_in_fake_plane(
            "some.external.package",
            "import src.result_comparator",
        )


# ---------------------------------------------------------------------------
# WARN mode (A7b log schema, R-new-2 dedup)
# ---------------------------------------------------------------------------


def test_warn_mode_logs_without_raising(guard_warn):
    """In WARN mode the same violation logs JSON and does not raise."""
    caplog = guard_warn
    with strict_scope():
        # Should NOT raise.
        _exec_in_fake_plane(
            "src.foam_agent_adapter",
            "import src.result_comparator",
        )
    records = [
        r for r in caplog.records
        if r.name == "src._plane_guard"
    ]
    assert len(records) == 1
    payload = json.loads(records[0].getMessage())
    # A7b minimum schema (5 fields).
    assert set(payload.keys()) >= {
        "incident_id",
        "source_module",
        "target_module",
        "contract_name",
        "severity",
    }
    assert payload["source_module"] == "src.foam_agent_adapter"
    assert payload["target_module"] == "src.result_comparator"
    assert payload["contract_name"] == "execution-never-imports-evaluation"
    assert payload["severity"] == "warn"


def test_warn_mode_dedups_repeat_violations(guard_warn):
    """Same (source, target, contract) tuple emits exactly once per process."""
    caplog = guard_warn
    with strict_scope():
        for _ in range(5):
            # Need to evict between calls so the import actually re-routes.
            sys.modules.pop("src.result_comparator", None)
            _exec_in_fake_plane(
                "src.foam_agent_adapter",
                "import src.result_comparator",
            )
    records = [r for r in caplog.records if r.name == "src._plane_guard"]
    assert len(records) == 1


def test_warn_mode_dedup_does_not_collapse_distinct_violations(guard_warn):
    """Different (source, target, contract) tuples emit independently."""
    caplog = guard_warn
    with strict_scope():
        # First violation: Execution → Evaluation
        _exec_in_fake_plane(
            "src.foam_agent_adapter",
            "import src.result_comparator",
        )
        # Second violation: Evaluation → Execution (different contract).
        sys.modules.pop("src.foam_agent_adapter", None)
        _exec_in_fake_plane(
            "src.result_comparator",
            "import src.foam_agent_adapter",
        )
    records = [r for r in caplog.records if r.name == "src._plane_guard"]
    assert len(records) == 2
    contracts = {json.loads(r.getMessage())["contract_name"] for r in records}
    assert contracts == {
        "execution-never-imports-evaluation",
        "evaluation-never-imports-execution",
    }


# ---------------------------------------------------------------------------
# FORBIDDEN_PAIRS surface
# ---------------------------------------------------------------------------


def test_forbidden_pairs_match_importlinter_contracts():
    """Sanity check — runtime forbidden table mirrors static contracts."""
    expected_contracts = {
        "execution-never-imports-evaluation",
        "evaluation-never-imports-execution",
        "knowledge-no-reverse-import",
        "models-stays-pure",
        "plane-guard-bootstrap-purity",
    }
    assert set(FORBIDDEN_PAIRS.values()) == expected_contracts


# ---------------------------------------------------------------------------
# Frame-walk env var (Draft-rev3 minor #1 — CFD_PLANE_GUARD_FRAME_LIMIT)
# ---------------------------------------------------------------------------


def test_frame_limit_env_var_respected(monkeypatch, evict_test_targets):
    """Setting CFD_PLANE_GUARD_FRAME_LIMIT to 1 should stop the walk early."""
    uninstall_guard()
    monkeypatch.setenv("CFD_PLANE_GUARD_FRAME_LIMIT", "1")
    install_guard(Mode.ON)
    try:
        # With limit=1 the walk only inspects the immediate caller of
        # find_spec (importlib internals), so the synthetic
        # src.foam_agent_adapter frame at depth ≥ 2 is not discovered.
        # Result: source plane unresolved → permissive (no raise).
        with strict_scope():
            _exec_in_fake_plane(
                "src.foam_agent_adapter",
                "import src.result_comparator",
            )
    finally:
        uninstall_guard()


def test_frame_limit_invalid_value_falls_back_to_default(monkeypatch, evict_test_targets):
    """Non-int / non-positive values silently fall back to default 20."""
    uninstall_guard()
    monkeypatch.setenv("CFD_PLANE_GUARD_FRAME_LIMIT", "not-an-int")
    install_guard(Mode.ON)
    try:
        with strict_scope():
            with pytest.raises(LayerViolationError):
                _exec_in_fake_plane(
                    "src.foam_agent_adapter",
                    "import src.result_comparator",
                )
    finally:
        uninstall_guard()

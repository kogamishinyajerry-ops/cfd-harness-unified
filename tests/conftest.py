"""Test-session-wide fixtures (ADR-002 §2.3 / Opus G-9 follow-up B-Q3).

Plane-guard test isolation: pytest sessions MUST run with the guard's
``CFD_HARNESS_PLANE_GUARD`` env var stripped. Two motivations:

  (i)  Dev-shell leakage — a developer who has ``export
       CFD_HARNESS_PLANE_GUARD=on`` in their shell would inadvertently
       run pytest under guard-on, surfacing test imports as violations
       and breaking the test allowlist's intended carve-out.
  (ii) Fork inheritance — ``multiprocessing.get_context('fork')`` test
       children inherit the parent's environment; any leaked env var
       activates the guard in the child process and produces
       non-deterministic test behavior.

This fixture is the single source of truth for plane-guard test
isolation. Tests that need the guard installed use explicit fixtures
(see ``tests/test_plane_guard.py::guard_on``,
``tests/test_plane_guard_edge.py::warn_guard``); they MUST NOT depend
on the env var.

After the test session, the saved env var is restored so dev-shell
state is preserved across pytest runs.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _plane_guard_test_isolation(tmp_path_factory):
    """Strip CFD_HARNESS_PLANE_GUARD env + redirect guard write paths to session tmp.

    Two responsibilities:

    (1) Strip ``CFD_HARNESS_PLANE_GUARD`` env var for the entire
        session — protects against dev-shell leakage and
        ``multiprocessing.get_context('fork')`` env inheritance into
        children. Defensive uninstall on teardown.

    (2) Redirect ``src._plane_guard._find_repo_root`` to a session
        tmp dir for the entire session (RETRO-V61-006 MP-D / dogfood
        baseline 2026-04-25). Any A13 / A18 events recorded during
        legitimate test exercise of the bypass (e.g.
        ``test_a3c_test_allowlist_permits_forbidden_pair``) write into
        the session tmp instead of polluting ``reports/plane_guard/``
        and the CI dogfood artifacts. Without this redirect the test
        suite produced ~2 false-positive incidents per CI run, which
        alone would trigger the §2.4 rollback evaluator (threshold 3
        in 14 days) after just 2 CI runs.

    Tests that need to verify path-resolution semantics directly
    (``test_jsonl_paths_anchor_to_repo_root_regardless_of_cwd``)
    monkeypatch ``_find_repo_root`` explicitly within their scope,
    cleanly overriding this session-wide redirect.
    """
    saved_env = os.environ.pop("CFD_HARNESS_PLANE_GUARD", None)
    session_tmp = tmp_path_factory.mktemp("plane_guard_session_writes")
    saved_root_fn = None
    try:
        from src import _plane_guard as _gm  # noqa: WPS433

        saved_root_fn = _gm._find_repo_root  # noqa: SLF001
        _gm._find_repo_root = lambda: str(session_tmp)  # noqa: SLF001
    except Exception:  # pragma: no cover - defensive only
        pass
    yield
    if saved_root_fn is not None:
        try:
            from src import _plane_guard as _gm  # noqa: WPS433

            _gm._find_repo_root = saved_root_fn  # noqa: SLF001
        except Exception:  # pragma: no cover - defensive only
            pass
    if saved_env is not None:
        os.environ["CFD_HARNESS_PLANE_GUARD"] = saved_env
    # Best-effort uninstall — ignore if guard module not importable
    # (would only happen if the test environment is broken).
    try:
        from src._plane_guard import uninstall_guard

        uninstall_guard()
    except Exception:  # pragma: no cover - defensive only
        pass

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
def _plane_guard_test_isolation():
    """Strip CFD_HARNESS_PLANE_GUARD for the entire test session.

    Defensive uninstall on teardown: if some test path activated the
    guard explicitly via ``install_guard()`` and forgot to clean up,
    the session-end uninstall ensures no finder leaks into a follow-on
    pytest invocation in the same process (rare but possible under
    pytest-xdist or --forked).
    """
    saved = os.environ.pop("CFD_HARNESS_PLANE_GUARD", None)
    yield
    if saved is not None:
        os.environ["CFD_HARNESS_PLANE_GUARD"] = saved
    # Best-effort uninstall — ignore if guard module not importable
    # (would only happen if the test environment is broken).
    try:
        from src._plane_guard import uninstall_guard

        uninstall_guard()
    except Exception:  # pragma: no cover - defensive only
        pass

"""cfd-harness-unified: 统一 AI-CFD 知识编译器.

Runtime plane-guard auto-install hookup (ADR-002 §2.3 W3 W3 activation
model): when ``CFD_HARNESS_PLANE_GUARD`` is set to ``warn`` or ``on``,
the bootstrap pair ``src._plane_guard`` registers a ``sys.meta_path``
finder before any other ``src.*`` module loads. Default (env var unset
or ``off``) keeps zero runtime overhead — no finder loaded, no behavior
change vs. pre-W3 state.

Test isolation note: ``tests/conftest.py`` declares an autouse
session-scope fixture that strips this env var before pytest collection
to prevent dev-shell leakage and fork-inheritance bugs. Tests that need
the guard installed use explicit fixtures, never the env var.
"""

import os as _os

_CFD_PLANE_GUARD_MODE = _os.environ.get("CFD_HARNESS_PLANE_GUARD", "off").lower()
if _CFD_PLANE_GUARD_MODE not in ("", "off"):
    # Lazy import — avoids loading the guard module when off, keeping
    # the OFF-default path zero-import-cost. Bootstrap-purity contract
    # ensures src._plane_guard imports only stdlib + src._plane_assignment,
    # so this triggers no other src.* loads.
    from ._plane_guard import install_guard as _install_guard
    _install_guard(_CFD_PLANE_GUARD_MODE)

del _os, _CFD_PLANE_GUARD_MODE

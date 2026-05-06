"""Single-source-of-truth registry of case-mutating endpoints + Python
mutation function symbols.

Per DEC-V61-130 §2 Principle B and DEC-V61-132 §2.1.

Two registries are kept in this module:

1. ``MUTATING_ROUTES`` — HTTP-surface SSOT. Set of ``(method, path_pattern)``
   pairs that mutate case state on disk. Used by reviewers and by the
   AI advisor contract test (Layer-B, FastAPI route-level case-state
   diff) as the human-facing list of routes that AI dispatch paths
   must NEVER call.

2. ``KNOWN_MUTATION_FUNCTIONS`` — Python-symbol SSOT. Set of
   ``(module_path, symbol_name)`` pairs naming every Python function
   that, when invoked, mutates case state. Used by the AI advisor
   contract test (Layer-A patched-function sentinel + Layer-C static
   namespace-binding check). This is the layer that the contract test
   actually polices, given AI dispatch in this codebase is in-process
   Python function calls (not outbound HTTP).

Both registries are append-only modulo deprecation: adding a new
mutation surface requires citing the upstream DEC in the change log
below; deprecating a surface requires removing both the registry
entry AND the route handler / function definition in the same commit.

Change log
----------
- DEC-V61-130 (2026-05-06): charter establishing AI-is-advisor contract;
  initial 5 routes enumerated in §2 Principle B.
- DEC-V61-131 (2026-05-06): N1.1 envelope hard-strip + regenerate_mesh
  deprecate. The MUTATING_ROUTES list and KNOWN_MUTATION_FUNCTIONS list
  did not yet exist — V131 stripped the call sites from AI dispatch
  paths.
- DEC-V61-132 (2026-05-06): N1.2 — this module created. Initial registry
  contents lifted from V130 §2 Principle B.
"""
from __future__ import annotations

import re
from typing import Iterator

__all__ = [
    "MUTATING_ROUTES",
    "KNOWN_MUTATION_FUNCTIONS",
    "is_mutating_route",
    "iter_mutation_symbols",
]


# HTTP-surface SSOT.
#
# Each pair is ``(method, path_pattern)``. ``path_pattern`` uses
# ``{case_id}`` as a placeholder for case-id segments; ``is_mutating_route``
# normalizes incoming paths before matching.
MUTATING_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        # POST /api/import/{case_id}/mesh — meshImported (writes polyMesh)
        ("POST", "/api/import/{case_id}/mesh"),
        # POST /api/import/{case_id}/setup-bc — setupBC (writes 0/U, 0/p,
        # system/controlDict; envelope=1 mode is hard-stripped at backend
        # per V131, but the route still mutates when called without
        # envelope=1 — engineer-driven [应用 AI 建议] click)
        ("POST", "/api/import/{case_id}/setup-bc"),
        # PUT /api/cases/{case_id}/face-annotations — face_annotations writer
        ("PUT", "/api/cases/{case_id}/face-annotations"),
        # POST /api/cases/{case_id}/dicts — dict mutator
        ("POST", "/api/cases/{case_id}/dicts"),
        # POST /api/cases/{case_id}/run — solver kick (writes run log,
        # field outputs)
        ("POST", "/api/cases/{case_id}/run"),
    }
)


# Python-symbol SSOT.
#
# Each pair is ``(module_path, symbol_name)`` referring to a function whose
# invocation mutates case state on disk. The Layer-A patched-function
# sentinel (in ``tests/test_ai_advisor_contract.py``) monkey-patches every
# entry here; if any AI dispatch entrypoint calls one, the test fails.
#
# Important: this is the operative gate. The HTTP-surface list above is
# the human-facing reference; the Python-symbol list is what the test
# actually polices, because AI dispatch in this codebase is in-process
# function calls.
KNOWN_MUTATION_FUNCTIONS: frozenset[tuple[str, str]] = frozenset(
    {
        # BC setup writers (case_solve package re-exports both from
        # bc_setup module)
        ("ui.backend.services.case_solve", "setup_ldc_bc"),
        ("ui.backend.services.case_solve", "setup_channel_bc"),
        ("ui.backend.services.case_solve.bc_setup", "setup_ldc_bc"),
        ("ui.backend.services.case_solve.bc_setup", "setup_channel_bc"),
        # Mesh writer
        ("ui.backend.services.meshing_gmsh.pipeline", "mesh_imported_case"),
        ("ui.backend.services.meshing_gmsh", "mesh_imported_case"),
    }
)


# case_id segments accept hex-id and uuid-id schemas; future case-id
# schemas not matching this regex require an explicit registry entry
# with a different placeholder.
_CASE_ID_PATTERN = re.compile(r"[0-9a-fA-F][0-9a-fA-F-]+")


def _normalize_path(path: str) -> str:
    """Replace concrete case_id segments with the literal ``{case_id}``."""
    parts = path.split("/")
    out: list[str] = []
    for part in parts:
        if part and _CASE_ID_PATTERN.fullmatch(part):
            out.append("{case_id}")
        else:
            out.append(part)
    return "/".join(out)


def is_mutating_route(method: str, path: str) -> bool:
    """Return True iff ``(method, path)`` matches any registered mutating
    route, after normalizing case_id segments to ``{case_id}``.

    Parameters
    ----------
    method
        HTTP method (case-insensitive; normalized to upper-case).
    path
        Request path. Concrete case_id segments matching
        ``[0-9a-fA-F][0-9a-fA-F-]+`` are normalized to ``{case_id}``
        before matching.
    """
    norm_method = method.upper()
    norm_path = _normalize_path(path)
    return (norm_method, norm_path) in MUTATING_ROUTES


def iter_mutation_symbols() -> Iterator[tuple[str, str]]:
    """Yield ``(module_path, symbol_name)`` for every entry in
    ``KNOWN_MUTATION_FUNCTIONS``.

    Used by the Layer-C static namespace-binding test in
    ``tests/test_ai_advisor_contract.py`` to assert no AI dispatch
    module imports any of these symbols.
    """
    yield from KNOWN_MUTATION_FUNCTIONS

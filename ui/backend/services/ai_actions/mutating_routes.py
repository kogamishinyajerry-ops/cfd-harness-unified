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
- DEC-V61-137 (2026-05-07): N2.3 — adds the snappyHexMesh addLayers
  POST endpoint and the corresponding pipeline function symbol.
"""
from __future__ import annotations

from typing import Iterator

__all__ = [
    "MUTATING_ROUTES",
    "KNOWN_MUTATION_FUNCTIONS",
    "is_mutating_route",
    "iter_mutation_symbols",
]


# HTTP-surface SSOT.
#
# Each pair is ``(method, path_pattern)``. ``path_pattern`` may use:
#   * ``{case_id}`` — placeholder for any case-id segment (positional:
#     the segment immediately after ``/api/import/`` or ``/api/cases/``).
#   * ``{rest}`` — wildcard tail segment matching one or more remaining
#     segments. Only meaningful as the final segment of the pattern.
# ``is_mutating_route`` normalizes incoming paths against these
# placeholders before matching.
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
        # POST /api/cases/{case_id}/dicts/{rest} — dict mutator
        # (V132 R1 P2 close: real route is /dicts/{relative_path:path};
        # FastAPI :path consumes the rest of the URL, so the registry
        # entry uses {rest} wildcard for the path tail)
        ("POST", "/api/cases/{case_id}/dicts/{rest}"),
        # POST /api/import/{case_id}/solve — solver kick (writes run
        # log + field outputs); blocking variant.
        # (V132 R1 P2 close: pre-R1 entry was "/api/cases/{case_id}/run"
        # which does not exist; the actual entrypoint is on the
        # import-prefixed path with verb "solve")
        ("POST", "/api/import/{case_id}/solve"),
        # POST /api/import/{case_id}/solve-stream — SSE streaming
        # variant of the same solver mutation; same artifacts written.
        ("POST", "/api/import/{case_id}/solve-stream"),
        # POST /api/import/{case_id}/mesh/prism-layers — DEC-V61-137
        # N2.3: snappyHexMesh addLayers stage on top of the existing
        # polyMesh. Refreshes constant/polyMesh in place; AI dispatch
        # paths must NEVER call this route.
        ("POST", "/api/import/{case_id}/mesh/prism-layers"),
        # POST /api/cases/{case_id}/physics — DEC-V61-142 (N3.3):
        # commit MaterialContract + RegimeContract to constant/
        # physicalProperties + momentumTransport. V130 Principle B —
        # engineer applies, AI advises; AI dispatch must NEVER call.
        ("POST", "/api/cases/{case_id}/physics"),
        # POST /api/cases/{case_id}/bc-contract — DEC-V61-146 (N4.1):
        # commit structured per-patch BCContract to 0.orig/{U, p}.
        # V130 Principle B — engineer applies, AI advises; AI dispatch
        # must NEVER call.
        ("POST", "/api/cases/{case_id}/bc-contract"),
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
        # snappyHexMesh addLayers writer (DEC-V61-137 · N2.3)
        ("ui.backend.services.meshing_snappy.pipeline", "apply_prism_layers"),
        ("ui.backend.services.meshing_snappy", "apply_prism_layers"),
        # Physics dict writer (DEC-V61-142 · N3.3) — translates
        # MaterialContract + RegimeContract → constant/physicalProperties
        # + constant/momentumTransport. AI dispatch paths MUST NEVER
        # call this; engineer-driven via POST /api/cases/{id}/physics.
        ("ui.backend.services.physics.writer", "write_physics_dicts"),
        ("ui.backend.services.physics", "write_physics_dicts"),
        # BC contract writer (DEC-V61-146 · N4.1) — translates
        # BCContract → 0.orig/{U, p}. AI dispatch MUST NEVER call;
        # engineer-driven via POST /api/cases/{id}/bc-contract.
        ("ui.backend.services.case_bc.writer", "write_bc_dicts"),
        ("ui.backend.services.case_bc", "write_bc_dicts"),
    }
)


# Path roots whose immediately-following segment is the case_id.
# (V132 R1 P1 close: pre-R1 used a regex matching only hex/UUID
# segments, but real imported case ids look like
# ``imported_2026-04-30T00-00-00Z_<hex>`` — the hex regex did not
# match. Switching to a positional rule: the segment right after
# /api/import/ or /api/cases/ IS the case_id, regardless of its
# content shape.)
_CASE_ID_ROOTS: frozenset[tuple[str, str]] = frozenset(
    {("api", "import"), ("api", "cases")}
)


def _normalize_path(path: str) -> list[str]:
    """Split ``path`` on '/' and replace the segment immediately after
    a known case-id root with the literal ``{case_id}``. Returns the
    segment list (callers compare segment-by-segment to support the
    ``{rest}`` wildcard)."""
    parts = path.split("/")
    # parts[0] is empty for absolute paths; parts[1] = "api",
    # parts[2] in {"import", "cases"}, parts[3] = case_id segment.
    if len(parts) >= 4 and (parts[1], parts[2]) in _CASE_ID_ROOTS:
        parts[3] = "{case_id}"
    return parts


def is_mutating_route(method: str, path: str) -> bool:
    """Return True iff ``(method, path)`` matches any registered
    mutating route, after normalizing the case_id segment to
    ``{case_id}`` and accepting ``{rest}`` as a one-or-more-segment
    tail wildcard.

    Parameters
    ----------
    method
        HTTP method (case-insensitive; normalized to upper-case).
    path
        Request path. The segment immediately after ``/api/import/``
        or ``/api/cases/`` is normalized to ``{case_id}`` regardless
        of its content shape (handles imported_*, hex, uuid, etc).
    """
    norm_method = method.upper()
    norm_parts = _normalize_path(path)

    for reg_method, reg_pattern in MUTATING_ROUTES:
        if reg_method != norm_method:
            continue
        reg_parts = reg_pattern.split("/")
        if reg_parts and reg_parts[-1] == "{rest}":
            # Wildcard tail: registry pattern matches if its
            # leading segments equal the corresponding incoming
            # segments AND there is at least one extra segment to
            # cover the {rest} placeholder.
            head = reg_parts[:-1]
            if len(norm_parts) > len(head) and norm_parts[: len(head)] == head:
                return True
        else:
            if norm_parts == reg_parts:
                return True
    return False


def iter_mutation_symbols() -> Iterator[tuple[str, str]]:
    """Yield ``(module_path, symbol_name)`` for every entry in
    ``KNOWN_MUTATION_FUNCTIONS``.

    Used by the Layer-C static namespace-binding test in
    ``tests/test_ai_advisor_contract.py`` to assert no AI dispatch
    module imports any of these symbols.
    """
    yield from KNOWN_MUTATION_FUNCTIONS

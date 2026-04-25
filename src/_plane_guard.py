"""Runtime four-plane import guard (ADR-002 W2 Impl Mid).

Implements the ``sys.meta_path`` finder that catches the dynamic-import
patterns from ADR-002 §1.1 (importlib.import_module, __import__,
spec_from_file_location, etc.) before they breach plane boundaries.
Pairs with the static ``import-linter`` layer (ADR-001) to give
defense-in-depth — static catches commit-time syntax, runtime catches
dynamic dispatch and post-pivot P2 ExecutorMode-style refactors.

Bootstrap constraint (ADR-002 §4.1 A12, Draft-rev4 R-new-3): this
module imports **only stdlib** and ``src._plane_assignment`` (the
SSOT — also Bootstrap plane). Both modules are listed under
``Plane.BOOTSTRAP`` in ``PLANE_OF``; the
``plane-guard-bootstrap-purity`` import-linter contract forbids them
from importing any other ``src.*`` module to prevent meta_path
self-recursion. v1.0 is single-module-per-Bootstrap-source —
multi-file decomposition is deferred to ADR-002 v1.1.

Activation model (ADR-002 §2.3, revised Draft-rev4): the guard is
**not** auto-installed. Callers (typically ``src/__init__.py`` or
explicit test fixtures) call ``install_guard(mode=...)`` with one of
three modes:

  * ``Mode.OFF`` — never installed; ``install_guard(Mode.OFF)`` is a
    no-op for orchestration symmetry.
  * ``Mode.WARN`` — installed; violations log a structured JSON line
    via ``logging.getLogger("src._plane_guard")`` and **do not** raise.
    Per-process dedup by ``(source, target, contract)`` tuple
    (Draft-rev4 R-new-2 anti-flood).
  * ``Mode.ON`` — installed; violations raise ``LayerViolationError``.

W2 Impl Mid scope: finder mechanism, multi-frame walk, test
allowlist (with ``strict_scope`` self-test escape hatch), structured
log schema. Edge-case suite (fork/forkserver, threading stress,
reload, namespace package, C-extension, exec/eval external dynamic
import) lands W2 Impl Late per §5 timeline split.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import uuid
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from typing import Dict, Optional, Tuple

from src._plane_assignment import Plane, plane_of


__all__ = [
    "LayerViolationError",
    "Mode",
    "PlaneGuardFinder",
    "install_guard",
    "uninstall_guard",
    "is_installed",
    "strict_scope",
    "FORBIDDEN_PAIRS",
]


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class Mode:
    """Activation modes — strings (not Enum) to keep env-var parsing trivial."""

    OFF = "off"
    WARN = "warn"
    ON = "on"

    _VALID = frozenset({OFF, WARN, ON})

    @classmethod
    def _validate(cls, value: str) -> str:
        if value not in cls._VALID:
            raise ValueError(
                f"Invalid plane-guard mode {value!r}; expected one of {sorted(cls._VALID)}"
            )
        return value


class LayerViolationError(ImportError):
    """Raised in ``Mode.ON`` when an import crosses a forbidden plane boundary.

    Subclass of ``ImportError`` so existing
    ``try: import X; except ImportError`` code paths still observe the
    failure. Diagnostic fields are exposed as instance attributes for
    downstream tooling (audit pipelines, IDE integrations).
    """

    def __init__(
        self,
        *,
        source_module: str,
        source_plane: str,
        target_module: str,
        target_plane: str,
        contract_name: str,
    ) -> None:
        self.source_module = source_module
        self.source_plane = source_plane
        self.target_module = target_module
        self.target_plane = target_plane
        self.contract_name = contract_name
        super().__init__(
            _format_violation_message(
                source_module=source_module,
                source_plane=source_plane,
                target_module=target_module,
                target_plane=target_plane,
                contract_name=contract_name,
            )
        )


# ---------------------------------------------------------------------------
# Forbidden plane-pair table (mirrors .importlinter contracts 1-5)
# ---------------------------------------------------------------------------


# Each forbidden ``(source_plane, target_plane)`` maps to the contract
# name in ``.importlinter``. The runtime layer enforces the same set
# the static layer enforces; both consume ``PLANE_OF`` from the SSOT.
FORBIDDEN_PAIRS: Dict[Tuple[Plane, Plane], str] = {
    # Contract 1: Execution must not import Evaluation
    (Plane.EXECUTION, Plane.EVALUATION): "execution-never-imports-evaluation",
    # Contract 2: Evaluation must not import Execution
    (Plane.EVALUATION, Plane.EXECUTION): "evaluation-never-imports-execution",
    # Contract 3: Knowledge must not import Control/Execution/Evaluation
    (Plane.KNOWLEDGE, Plane.CONTROL): "knowledge-no-reverse-import",
    (Plane.KNOWLEDGE, Plane.EXECUTION): "knowledge-no-reverse-import",
    (Plane.KNOWLEDGE, Plane.EVALUATION): "knowledge-no-reverse-import",
    # Contract 4: Shared (models) must not import any other plane
    (Plane.SHARED, Plane.CONTROL): "models-stays-pure",
    (Plane.SHARED, Plane.EXECUTION): "models-stays-pure",
    (Plane.SHARED, Plane.EVALUATION): "models-stays-pure",
    (Plane.SHARED, Plane.KNOWLEDGE): "models-stays-pure",
    # Contract 5: Bootstrap must not import any non-bootstrap plane
    (Plane.BOOTSTRAP, Plane.CONTROL): "plane-guard-bootstrap-purity",
    (Plane.BOOTSTRAP, Plane.EXECUTION): "plane-guard-bootstrap-purity",
    (Plane.BOOTSTRAP, Plane.EVALUATION): "plane-guard-bootstrap-purity",
    (Plane.BOOTSTRAP, Plane.KNOWLEDGE): "plane-guard-bootstrap-purity",
    (Plane.BOOTSTRAP, Plane.SHARED): "plane-guard-bootstrap-purity",
}


# ---------------------------------------------------------------------------
# Frame-walk configuration
# ---------------------------------------------------------------------------


# §2.4 test-allowlist regex (frozen as dotted form per Draft-rev3 minor #2).
_TEST_ALLOWLIST_RE = re.compile(r"^tests($|\.)")

# Default frame walk limit (§2.1, env-configurable per Draft-rev3 minor #1).
_DEFAULT_FRAME_LIMIT = 20


def _frame_limit() -> int:
    """Resolve the multi-frame walk depth limit.

    ``CFD_PLANE_GUARD_FRAME_LIMIT`` overrides the default; invalid or
    non-positive values silently fall back to the default to avoid
    accidentally disabling enforcement.
    """
    raw = os.environ.get("CFD_PLANE_GUARD_FRAME_LIMIT", "")
    if not raw:
        return _DEFAULT_FRAME_LIMIT
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_FRAME_LIMIT
    return value if value > 0 else _DEFAULT_FRAME_LIMIT


# ---------------------------------------------------------------------------
# Mutable runtime state (locked)
# ---------------------------------------------------------------------------


_STATE_LOCK = threading.Lock()
_INSTALLED_FINDER: Optional["PlaneGuardFinder"] = None
# Per-process dedup set for WARN mode (§2.3 R-new-2). Bounded by
# ``max_dedup_entries`` on install; exceeded → log "dedup cap hit"
# and clear (Opus G-9 follow-up B-Q4 explicit-cap defensive guard).
_DEDUP_KEYS: set[Tuple[str, str, str]] = set()
_DEDUP_MAX_ENTRIES = 10_000  # default; overridden via install_guard kwarg
# strict_scope nesting depth (per-thread).
_STRICT_DEPTH = threading.local()


def _is_strict_scope_active() -> bool:
    return getattr(_STRICT_DEPTH, "depth", 0) > 0


class _StrictScope:
    """Context manager that disables the test-allowlist (AC-A3 d).

    Used by tests for the guard itself: without ``strict_scope`` the
    test's own ``tests.*`` frame would bypass the check, masking real
    behavior.
    """

    def __enter__(self) -> "_StrictScope":
        depth = getattr(_STRICT_DEPTH, "depth", 0)
        _STRICT_DEPTH.depth = depth + 1
        return self

    def __exit__(self, *exc: object) -> None:
        _STRICT_DEPTH.depth = max(0, getattr(_STRICT_DEPTH, "depth", 0) - 1)


def strict_scope() -> _StrictScope:
    """Return a context manager that disables the test-allowlist."""
    return _StrictScope()


# ---------------------------------------------------------------------------
# Frame-walk helpers
# ---------------------------------------------------------------------------


def _frame_module_name(frame: object) -> Optional[str]:
    """Resolve a frame's module name via ``__spec__.name`` → ``__name__``.

    Returns ``None`` when neither is set (typical for ``exec()`` /
    ``eval()`` with empty globals, frozen importlib internals, or
    bare-globals contexts). Callers treat ``None`` as "unmapped frame,
    continue walking".
    """
    if frame is None:
        return None
    f_globals = getattr(frame, "f_globals", None)
    if f_globals is None:
        return None
    spec = f_globals.get("__spec__")
    if spec is not None:
        spec_name = getattr(spec, "name", None)
        if spec_name:
            return spec_name
    name = f_globals.get("__name__")
    return name if name else None


def _resolve_source_plane(
    start_frame: object,
) -> Tuple[Optional[Plane], Optional[str], bool, bool]:
    """Walk frames from ``start_frame`` up to the limit looking for an ``src.*`` caller.

    Returns ``(plane, module_name, found_test_frame, saw_unmapped_dynamic)``:
      * ``plane`` — first ``src.*`` plane encountered, or ``None`` if
        the walk reaches the limit / stack top without a hit (treat as
        external; permissive fallback per ADR-002 §2.1).
      * ``module_name`` — the matched module dotted name.
      * ``found_test_frame`` — ``True`` if any frame in the walk
        matched ``^tests($|\\.)`` (the §2.4 allowlist). The walk
        intentionally continues past the first ``src.*`` hit so that a
        fixture chain ``tests.conftest → src.x → src.y`` still grants
        test scope.
      * ``saw_unmapped_dynamic`` — ``True`` if any frame had truly
        empty globals (no ``__spec__``, no ``__name__``); typical of
        ``exec()`` / ``eval()`` injected scopes. Draft-rev3 minor #1
        uses this to log an external_dynamic_import WARN observability
        event when the walk exits without a ``src.*`` hit.
    """
    limit = _frame_limit()
    frame = start_frame
    walked = 0
    src_plane: Optional[Plane] = None
    src_name: Optional[str] = None
    found_test = False
    saw_unmapped_dynamic = False

    while frame is not None and walked < limit:
        name = _frame_module_name(frame)
        if name is None:
            # Frame had neither __spec__ nor __name__ set — typical of
            # exec()/eval() with truly empty globals. Walk-internal
            # importlib frames also report None here (their __name__
            # exists but is `_frozen_importlib_external` etc., NOT
            # None). The None signal therefore specifically picks out
            # the dynamic-injection case.
            f_globals = getattr(frame, "f_globals", None)
            if f_globals is not None and not f_globals.get("__name__"):
                saw_unmapped_dynamic = True
        else:
            if not found_test and _TEST_ALLOWLIST_RE.match(name):
                found_test = True
            if src_plane is None and name.startswith("src."):
                p = plane_of(name)
                if p is not None:
                    src_plane = p
                    src_name = name
        frame = getattr(frame, "f_back", None)
        walked += 1

    return src_plane, src_name, found_test, saw_unmapped_dynamic


def _emit_external_dynamic_import_warning(*, target_module: str) -> None:
    """Log an external dynamic-import observability event.

    Draft-rev3 minor #1: when ``exec()`` / ``eval()`` scopes with empty
    globals dynamically import an ``src.*`` module from outside the
    project, classify as ``<external>`` (permissive — do not raise) but
    surface a WARN-level structured-JSON line via the
    ``src._plane_guard.external_dynamic_import`` sub-logger so the
    bypass route is auditable rather than silent.
    """
    log_record = {
        "incident_id": str(uuid.uuid4()),
        "source_module": "<external_dynamic>",
        "target_module": target_module,
        "contract_name": "external_dynamic_import",
        "severity": "dynamic_external",
    }
    logging.getLogger(
        "src._plane_guard.external_dynamic_import"
    ).warning(json.dumps(log_record))


# ---------------------------------------------------------------------------
# Violation message format (stable; A7b log schema parses these fields)
# ---------------------------------------------------------------------------


# ADR-002 §2.5 verbatim message format — AC-A9 mandates the "Most
# likely fixes:" section. Suggestions are derived from the contract
# name so the dev sees the canonical fix path for the specific
# forbidden pair rather than a generic prose blob.
_FIX_SUGGESTIONS: Dict[str, Tuple[str, str, str]] = {
    "execution-never-imports-evaluation": (
        "read the comparator output from an ExecutionResult artifact field "
        "rather than invoking the comparator directly from Execution.",
        "move the needed logic down to src.models (shared types) if the "
        "helper is pure type logic.",
        "if this is a legitimate test, mark the caller file with a tests/ "
        "prefix or use src._plane_guard.strict_scope() in reverse for the "
        "self-test pathway.",
    ),
    "evaluation-never-imports-execution": (
        "read the execution artifact via ExecutionResult fields rather "
        "than importing the executor module directly from Evaluation.",
        "move shared scaffolding (e.g. solver-log shape) to src.models so "
        "Evaluation can consume the type without depending on Execution.",
        "if this is a legitimate test, mark the caller file with a tests/ "
        "prefix or use src._plane_guard.strict_scope() to assert from a "
        "self-test.",
    ),
    "knowledge-no-reverse-import": (
        "Knowledge Plane is downstream-only; replace this import with the "
        "read-only view or write-only event interface defined in "
        "src.knowledge_db.",
        "if you need a richer Knowledge → Control coupling, open an ADR "
        "amendment — the four-plane invariant prohibits the reverse edge "
        "without an explicit governance decision.",
        "if this is a legitimate test, mark the caller file with a tests/ "
        "prefix or use src._plane_guard.strict_scope().",
    ),
    "models-stays-pure": (
        "src.models is the type-only escape hatch — keep it dependency-free. "
        "If the helper needs runtime logic, host it in the consuming plane.",
        "if the helper is pure types, place it in src.models directly "
        "rather than importing from another plane into models.",
        "if this is a legitimate test, mark the caller file with a tests/ "
        "prefix or use src._plane_guard.strict_scope().",
    ),
    "plane-guard-bootstrap-purity": (
        "Bootstrap modules (src._plane_assignment, src._plane_guard) MUST "
        "stay stdlib-only to avoid meta_path finder self-recursion. Refactor "
        "the dependency to keep the leaf bootstrap.",
        "if you genuinely need a bootstrap helper, open ADR-002 v1.1 — the "
        "v1.0 single-pair invariant locks bootstrap unit to exactly two "
        "files (Draft-rev4 R-new-3).",
        "if this is a legitimate test, mark the caller file with a tests/ "
        "prefix or use src._plane_guard.strict_scope().",
    ),
}


def _format_violation_message(
    *,
    source_module: str,
    source_plane: str,
    target_module: str,
    target_plane: str,
    contract_name: str,
) -> str:
    fixes = _FIX_SUGGESTIONS.get(
        contract_name,
        (
            "review ADR-001 §2.1 plane assignment to confirm both modules' "
            "planes are correctly classified.",
            "if a new plane crossing is genuinely required, open an ADR "
            "amendment rather than working around the contract.",
            "if this is a legitimate test, mark the caller file with a "
            "tests/ prefix or use src._plane_guard.strict_scope().",
        ),
    )
    # ADR-002 §2.5 message format uses Title-case plane names in the
    # user-facing string. Canonical lowercase ``Plane.value`` is
    # preserved on the exception instance attributes and structured
    # log JSON for downstream-tool stability.
    return (
        f"runtime plane-crossing import forbidden.\n"
        f"  source module: {source_module} ({source_plane.capitalize()} plane)\n"
        f"  target module: {target_module} ({target_plane.capitalize()} plane)\n"
        f"  rule: {contract_name}\n"
        f"  authority: ADR-001 §2.2 · SYSTEM_ARCHITECTURE v1.0 §2\n"
        f"\n"
        f"Most likely fixes:\n"
        f"  (a) {fixes[0]}\n"
        f"  (b) {fixes[1]}\n"
        f"  (c) {fixes[2]}"
    )


# ---------------------------------------------------------------------------
# The finder
# ---------------------------------------------------------------------------


class PlaneGuardFinder(MetaPathFinder):
    """``sys.meta_path`` finder enforcing the plane forbidden-pairs table.

    The finder never *loads* modules — it only inspects the
    ``(source_plane, target_plane)`` pair via the multi-frame walk and
    either returns ``None`` (allow the real loader to proceed) or
    raises / logs a violation. This keeps the guard non-invasive: it
    cannot accidentally short-circuit legitimate imports.
    """

    def __init__(self, *, mode: str = Mode.ON) -> None:
        self.mode = Mode._validate(mode)

    # ``find_spec`` signature is fixed by ``importlib.abc.MetaPathFinder``.
    def find_spec(
        self,
        fullname: str,
        path: Optional[object] = None,
        target: Optional[object] = None,
    ) -> Optional[ModuleSpec]:
        # Fast-path: only intercept ``src.*``.
        if not fullname.startswith("src."):
            return None

        target_plane = plane_of(fullname)
        if target_plane is None:
            # Unmapped src.* module — treat as external (permissive).
            return None

        # Source-plane resolution. Skip our own frame (find_spec) by
        # starting at the caller (importlib internals or the user
        # frame; the walk transparently skips importlib stdlib frames
        # because their ``__name__`` does not match ``src.*`` or
        # ``tests``).
        try:
            start_frame = sys._getframe(1)
        except ValueError:
            return None  # No caller frame; unusual path, stay permissive.

        src_plane, src_name, found_test, saw_unmapped_dynamic = _resolve_source_plane(
            start_frame
        )

        # Test-allowlist: any ``tests.*`` frame in the walk grants
        # bypass UNLESS strict_scope is active (self-test pathway).
        if found_test and not _is_strict_scope_active():
            return None

        if src_plane is None:
            # External code (no ``src.*`` frame in the walk) — permissive.
            # Draft-rev3 minor #1 (Opus W2 Gate round-2): if at least
            # one frame in the walk had EMPTY globals (typical of
            # `exec()` / `eval()` injected scopes), surface this as a
            # WARN-level observability event so external dynamic
            # imports of `src.*` are auditable. Does NOT raise — pure
            # logging.
            if saw_unmapped_dynamic:
                _emit_external_dynamic_import_warning(target_module=fullname)
            return None

        contract = FORBIDDEN_PAIRS.get((src_plane, target_plane))
        if contract is None:
            return None  # Allowed transition.

        # Forbidden pair detected. Pass canonical lowercase
        # ``Plane.value`` strings; the error message renders
        # Title-case for user-facing display per ADR-002 §2.5; the
        # structured-log JSON and the LayerViolationError instance
        # attributes keep lowercase for downstream-tool stability.
        self._handle_violation(
            source_module=src_name or "<unknown>",
            source_plane=src_plane.value,
            target_module=fullname,
            target_plane=target_plane.value,
            contract_name=contract,
        )
        return None

    def _handle_violation(
        self,
        *,
        source_module: str,
        source_plane: str,
        target_module: str,
        target_plane: str,
        contract_name: str,
    ) -> None:
        if self.mode == Mode.ON:
            raise LayerViolationError(
                source_module=source_module,
                source_plane=source_plane,
                target_module=target_module,
                target_plane=target_plane,
                contract_name=contract_name,
            )

        if self.mode != Mode.WARN:
            return  # Mode.OFF would not have been installed; defensive.

        # WARN-mode dedup by (source, target, contract) tuple — Draft-rev4
        # R-new-2 anti-flood. Each unique tuple emits exactly one log
        # line per process lifetime, bounded by ``_DEDUP_MAX_ENTRIES``
        # (B-Q4 defensive cap). At cap, log a "dedup cap hit" notice
        # and clear so subsequent unique violations are still
        # observable rather than silently dropped.
        key = (source_module, target_module, contract_name)
        with _STATE_LOCK:
            if key in _DEDUP_KEYS:
                return
            if len(_DEDUP_KEYS) >= _DEDUP_MAX_ENTRIES:
                logging.getLogger("src._plane_guard").warning(
                    json.dumps({
                        "incident_id": str(uuid.uuid4()),
                        "source_module": "<dedup_cap>",
                        "target_module": "<dedup_cap>",
                        "contract_name": "dedup_cap_hit",
                        "severity": "warn",
                        "cap": _DEDUP_MAX_ENTRIES,
                    })
                )
                _DEDUP_KEYS.clear()
            _DEDUP_KEYS.add(key)

        # A7b structured log payload (5 required fields, extensions
        # allowed but never field-removed without ADR-002 revision).
        log_record = {
            "incident_id": str(uuid.uuid4()),
            "source_module": source_module,
            "target_module": target_module,
            "contract_name": contract_name,
            "severity": "warn",
        }
        logging.getLogger("src._plane_guard").warning(json.dumps(log_record))


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def install_guard(
    mode: str = Mode.ON,
    *,
    max_dedup_entries: int = 10_000,
) -> Optional[PlaneGuardFinder]:
    """Install the finder at ``sys.meta_path[0]`` if not already present.

    ``Mode.OFF`` is a no-op (returns ``None``) for caller symmetry —
    callers can dispatch on the env var without an extra branch.
    Repeat ``install_guard`` calls return the existing finder; the
    mode is **not** updated by repeat calls (uninstall first if you
    need to change mode).

    ``max_dedup_entries`` (Opus G-9 follow-up B-Q4) bounds the WARN-mode
    dedup set so a long-lived prod process cannot accumulate
    unbounded memory on novel violation tuples. Default 10000 is
    ~100× expected steady-state (~100 unique tuples). On cap-hit a
    "dedup_cap_hit" event is logged and the set is cleared so
    subsequent unique violations are still observable.
    """
    Mode._validate(mode)
    if max_dedup_entries < 1:
        raise ValueError(
            f"max_dedup_entries must be >= 1, got {max_dedup_entries}"
        )
    global _INSTALLED_FINDER, _DEDUP_MAX_ENTRIES
    with _STATE_LOCK:
        if mode == Mode.OFF:
            return None
        if _INSTALLED_FINDER is not None:
            return _INSTALLED_FINDER
        finder = PlaneGuardFinder(mode=mode)
        sys.meta_path.insert(0, finder)
        _INSTALLED_FINDER = finder
        _DEDUP_MAX_ENTRIES = max_dedup_entries
        return finder


def uninstall_guard() -> None:
    """Remove the finder from ``sys.meta_path`` and reset module state.

    Idempotent: calling when no guard is installed is a no-op. Resets
    the WARN-mode dedup set so a fresh install starts with empty state
    (important for tests that flip modes within a single process).
    """
    global _INSTALLED_FINDER
    with _STATE_LOCK:
        if _INSTALLED_FINDER is None:
            return
        try:
            sys.meta_path.remove(_INSTALLED_FINDER)
        except ValueError:
            pass
        _INSTALLED_FINDER = None
        _DEDUP_KEYS.clear()


def is_installed() -> bool:
    """Return ``True`` if the guard is currently registered on ``sys.meta_path``."""
    with _STATE_LOCK:
        return _INSTALLED_FINDER is not None

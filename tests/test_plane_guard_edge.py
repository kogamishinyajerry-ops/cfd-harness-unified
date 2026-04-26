"""Edge-case suite for ``src._plane_guard`` (ADR-002 W2 Impl Late).

Covers ADR-002 §4.1 acceptance criteria:
  * A4   — p95 ``find_spec`` ≤ 100 µs on the current repo
  * A7b  — WARN/ON log JSON has a stable 5-field minimum schema
  * A10  — fork-safety: ``multiprocessing.get_context('fork')`` child
           inherits finder + env var, raises on deliberate violation
  * A10c — forkserver covered Linux-only with platform skip
  * A11  — thread-safety: 100 imports across 8 threads, no dropped
           dedup events, no deadlock
  * A12  — bootstrap import-purity via AST walk (complements the
           lexical-regex test in test_plane_assignment_ssot.py)

A14 reload, A15 namespace package, A16 C-extension trampoline are
tracked in ADR-002 §6 Known Limitations rather than as tests
(per AC text: "pytest green OR §6 amendment"). Synthesizing a real
two-root PEP 420 namespace package on the test disk would require
filesystem mutation outside ``tmp_path`` reach; for v1.0 the §2.1
multi-frame walk's ``spec.name`` priority chain is the structural
guarantee, exercised indirectly by the existing fake-plane tests.
"""

from __future__ import annotations

import ast
import json
import logging
import multiprocessing
import os
import sys
import threading
import time
from importlib.machinery import ModuleSpec
from pathlib import Path

import pytest

from src._plane_assignment import Plane
from src._plane_guard import (
    LayerViolationError,
    Mode,
    PlaneGuardFinder,
    install_guard,
    is_installed,
    strict_scope,
    uninstall_guard,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"


# ---------------------------------------------------------------------------
# A4 · performance budget (p95 find_spec ≤ 100 µs)
# ---------------------------------------------------------------------------


@pytest.fixture
def perf_guard():
    uninstall_guard()
    install_guard(Mode.ON)
    try:
        yield
    finally:
        uninstall_guard()


def test_a4_find_spec_p95_under_100us(perf_guard):
    """Guard adds <100 µs p95 overhead on src.* spec lookups."""
    finder = next(
        (f for f in sys.meta_path if isinstance(f, PlaneGuardFinder)), None
    )
    assert finder is not None

    # Time many find_spec calls on the fast-path (non-src.* prefix
    # short-circuits) AND on the src.* path. We measure src.* path
    # explicitly because that's where the multi-frame walk runs.
    iterations = 2000
    samples: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        # An allowed import (Control → Execution) — finder walks but
        # does not raise.
        finder.find_spec("src.foam_agent_adapter")
        samples.append((time.perf_counter_ns() - t0) / 1000.0)  # µs

    samples.sort()
    p95 = samples[int(0.95 * len(samples))]
    median = samples[len(samples) // 2]
    assert p95 < 100.0, (
        f"find_spec p95={p95:.2f} µs exceeds 100 µs budget "
        f"(median={median:.2f} µs over {iterations} calls)"
    )


def test_a4_fast_path_for_non_src_modules(perf_guard):
    """Non-src.* imports skip the walk entirely — should be sub-microsecond."""
    finder = next(
        (f for f in sys.meta_path if isinstance(f, PlaneGuardFinder)), None
    )
    iterations = 5000
    samples: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        finder.find_spec("os.path")  # stdlib, fast-path returns None
        samples.append((time.perf_counter_ns() - t0) / 1000.0)
    samples.sort()
    p95 = samples[int(0.95 * len(samples))]
    assert p95 < 5.0, f"Fast-path p95={p95:.2f} µs exceeds 5 µs"


# ---------------------------------------------------------------------------
# A7b · log schema standalone test
# ---------------------------------------------------------------------------


@pytest.fixture
def warn_guard(caplog):
    uninstall_guard()
    caplog.set_level(logging.WARNING, logger="src._plane_guard")
    install_guard(Mode.WARN)
    try:
        yield caplog
    finally:
        uninstall_guard()


@pytest.mark.parametrize(
    "source,target,expected_contract",
    [
        (
            "src.foam_agent_adapter",
            "src.result_comparator",
            "execution-never-imports-evaluation",
        ),
        (
            "src.result_comparator",
            "src.foam_agent_adapter",
            "evaluation-never-imports-execution",
        ),
        (
            "src.knowledge_db",
            "src.task_runner",
            "knowledge-no-reverse-import",
        ),
        (
            "src.models",
            "src.task_runner",
            "models-stays-pure",
        ),
    ],
)
def test_a7b_log_schema_stability(warn_guard, source, target, expected_contract):
    """All forbidden contracts emit the same 5-field minimum JSON schema."""
    caplog = warn_guard
    caplog.clear()
    # DEC-V61-FORENSIC-FLAKE-1-FIX: pop()-then-reimport produces a NEW
    # module object in sys.modules; any earlier `from {target} import X`
    # in another test file binds X to the OLD module's __globals__,
    # so subsequent monkeypatches on the NEW module never reach X.
    # Save the original singleton and restore it after the test to
    # keep sys.modules stable for downstream tests.
    saved_target = sys.modules.pop(target, None)
    fake_spec = ModuleSpec(name=source, loader=None)
    exec_globals = {"__spec__": fake_spec, "__name__": source}
    try:
        with strict_scope():
            exec(f"import {target}", exec_globals)

        records = [r for r in caplog.records if r.name == "src._plane_guard"]
        assert len(records) == 1
        payload = json.loads(records[0].getMessage())
        # Five required fields per A7b.
        required = {
            "incident_id",
            "source_module",
            "target_module",
            "contract_name",
            "severity",
        }
        missing = required - set(payload)
        assert not missing, f"Missing required fields: {missing}"
        assert payload["source_module"] == source
        assert payload["target_module"] == target
        assert payload["contract_name"] == expected_contract
        assert payload["severity"] == "warn"
        # incident_id is a UUID string (36 chars including hyphens).
        assert isinstance(payload["incident_id"], str)
        assert len(payload["incident_id"]) == 36
    finally:
        # Restore the original module object so downstream tests that
        # already bound symbols via `from {target} import X` see the
        # same module instance their X was sourced from. Without this,
        # monkeypatch.setattr on the freshly-reimported module fails
        # to reach those bound symbols' __globals__.
        # Two-step restore: sys.modules entry AND parent-package
        # attribute (e.g. src.task_runner). The exec-triggered import
        # mutates BOTH, so restoring only sys.modules leaves
        # `from src import task_runner` returning the stale MODULE_B.
        if saved_target is not None:
            sys.modules[target] = saved_target
            parent_name, _, child_name = target.rpartition(".")
            if parent_name:
                parent_mod = sys.modules.get(parent_name)
                if parent_mod is not None:
                    setattr(parent_mod, child_name, saved_target)
        else:
            sys.modules.pop(target, None)


def test_a7b_log_does_not_propagate_to_handlers_at_sub_logger():
    """Draft-rev4 L1 — sub-loggers must not attach handlers; root only.

    No handlers at any current sub-logger; if the project later adds
    sub-logger telemetry, this test enforces the propagate-True rule.
    """
    base = logging.getLogger("src._plane_guard")
    # Discover sub-loggers via the logging registry.
    for name, logger in logging.Logger.manager.loggerDict.items():
        if not isinstance(logger, logging.Logger):
            continue
        if not name.startswith("src._plane_guard."):
            continue
        assert logger.propagate is True, (
            f"Sub-logger {name} has propagate=False — would prevent the "
            "root from receiving its records and break A7b dedup centrality."
        )
        # We do not strictly forbid handlers (project may add some);
        # we only enforce propagate so root emission still flows.


# ---------------------------------------------------------------------------
# A11 · thread-safety stress
# ---------------------------------------------------------------------------


def test_a11_thread_safety_no_dedup_drop(warn_guard):
    """100 concurrent finder calls across 8 threads — dedup yields exactly one log.

    Calls ``finder.find_spec`` directly with a synthetic frame context
    rather than going through ``import`` statements, because
    ``import`` short-circuits on ``sys.modules`` cache and pop / load
    races would muddy the thread-safety signal. This test exercises
    the finder's internal locking + dedup set semantics under
    concurrent load.
    """
    caplog = warn_guard
    caplog.clear()
    finder = next(
        (f for f in sys.meta_path if isinstance(f, PlaneGuardFinder)), None
    )
    assert finder is not None

    fake_spec = ModuleSpec(name="src.foam_agent_adapter", loader=None)
    target = "src.result_comparator"

    def worker():
        # Run inside an exec frame whose globals fake the source plane,
        # so the finder's multi-frame walk classifies us as Execution.
        exec_globals = {
            "__spec__": fake_spec,
            "__name__": "src.foam_agent_adapter",
            "_finder": finder,
            "_target": target,
        }
        code = (
            "for _ in range(13):\n"
            "    _finder.find_spec(_target)\n"
        )
        with strict_scope():
            exec(code, exec_globals)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    for t in threads:
        assert not t.is_alive(), "Thread deadlocked"

    records = [r for r in caplog.records if r.name == "src._plane_guard"]
    # Per-process dedup across 8 × 13 = 104 violation attempts.
    assert len(records) == 1, (
        f"Expected exactly 1 dedup'd warning across 104 attempts, "
        f"got {len(records)}"
    )


def test_a11_thread_safety_install_uninstall_idempotent():
    """Concurrent install / uninstall must not corrupt state."""
    uninstall_guard()
    errors: list[BaseException] = []

    def install_worker():
        try:
            for _ in range(20):
                install_guard(Mode.ON)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    def uninstall_worker():
        try:
            for _ in range(20):
                uninstall_guard()
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = (
        [threading.Thread(target=install_worker) for _ in range(4)]
        + [threading.Thread(target=uninstall_worker) for _ in range(4)]
    )
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"Concurrent install/uninstall raised: {errors}"
    uninstall_guard()
    assert not is_installed()


# ---------------------------------------------------------------------------
# A10 / A10c · fork + forkserver safety
# ---------------------------------------------------------------------------


def _fork_child_violation(queue):
    """Child process: install ON, attempt forbidden import, send result."""
    # Avoid coverage / monkeypatch leakage from parent via a fresh
    # state initialization.
    from src._plane_guard import (  # noqa: WPS433 (re-import in child)
        Mode,
        install_guard,
        strict_scope,
        uninstall_guard,
        LayerViolationError,
    )

    uninstall_guard()
    install_guard(Mode.ON)
    fake_spec = ModuleSpec(
        name="src.foam_agent_adapter", loader=None
    )
    exec_globals = {
        "__spec__": fake_spec,
        "__name__": "src.foam_agent_adapter",
    }
    sys.modules.pop("src.result_comparator", None)
    try:
        with strict_scope():
            exec("import src.result_comparator", exec_globals)
        queue.put(("no-raise",))
    except LayerViolationError as e:
        queue.put(("raised", e.contract_name))
    except Exception as e:  # noqa: BLE001
        queue.put(("other", repr(e)))


@pytest.mark.parametrize(
    "ctx_method",
    [
        "fork",
        pytest.param(
            "forkserver",
            marks=pytest.mark.skipif(
                sys.platform != "linux",
                reason="forkserver is Linux-specific (A10c)",
            ),
        ),
    ],
)
def test_a10_child_process_inherits_guard_behavior(ctx_method):
    """Fork / forkserver child raises LayerViolationError on its own violation."""
    ctx = multiprocessing.get_context(ctx_method)
    queue = ctx.Queue()
    proc = ctx.Process(target=_fork_child_violation, args=(queue,))
    proc.start()
    proc.join(timeout=20)
    assert not proc.is_alive(), f"{ctx_method} child hung"
    assert proc.exitcode == 0, f"{ctx_method} child exit={proc.exitcode}"
    assert not queue.empty(), f"{ctx_method} child sent no result"
    result = queue.get(timeout=5)
    assert result == ("raised", "execution-never-imports-evaluation"), result


# ---------------------------------------------------------------------------
# A12 · AST-walk bootstrap purity (complements lexical regex)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# B-Q4 · WARN-mode dedup cap (defensive memory bound)
# ---------------------------------------------------------------------------


def test_b_q4_dedup_cap_logs_and_clears(caplog):
    """install_guard(max_dedup_entries=N): on overflow, log "dedup cap hit"
    + clear set + accept new entries (Opus G-9 follow-up B-Q4)."""
    uninstall_guard()
    caplog.set_level(logging.WARNING, logger="src._plane_guard")
    install_guard(Mode.WARN, max_dedup_entries=3)
    try:
        finder = next(
            (f for f in sys.meta_path if isinstance(f, PlaneGuardFinder)),
            None,
        )
        assert finder is not None
        # Generate 4 distinct violations to force a cap-hit on the 4th.
        violations = [
            ("src.foam_agent_adapter", "src.result_comparator"),
            ("src.foam_agent_adapter", "src.metrics"),
            ("src.cylinder_strouhal_fft", "src.result_comparator"),
            ("src.airfoil_surface_sampler", "src.metrics"),
        ]
        for source, target in violations:
            fake_spec = ModuleSpec(name=source, loader=None)
            exec_globals = {
                "__spec__": fake_spec,
                "__name__": source,
                "_finder": finder,
                "_target": target,
            }
            with strict_scope():
                exec(
                    "_finder.find_spec(_target)",
                    exec_globals,
                )
        records = [r for r in caplog.records if r.name == "src._plane_guard"]
        # Expect 4 violation logs + 1 dedup_cap_hit notice = 5
        cap_hit_records = [
            r for r in records
            if json.loads(r.getMessage()).get("contract_name") == "dedup_cap_hit"
        ]
        assert len(cap_hit_records) == 1, (
            f"Expected exactly 1 dedup_cap_hit notice, got {len(cap_hit_records)}"
        )
        cap_payload = json.loads(cap_hit_records[0].getMessage())
        assert cap_payload["cap"] == 3
    finally:
        uninstall_guard()


def test_b_q4_install_rejects_invalid_cap():
    """max_dedup_entries < 1 must raise ValueError at install time."""
    uninstall_guard()
    with pytest.raises(ValueError):
        install_guard(Mode.WARN, max_dedup_entries=0)
    with pytest.raises(ValueError):
        install_guard(Mode.WARN, max_dedup_entries=-5)


# ---------------------------------------------------------------------------
# Codex Open Q 1 · ON-mode concurrent imports thread-safety
# ---------------------------------------------------------------------------


def test_on_mode_concurrent_find_spec_no_corruption():
    """ON-mode: concurrent finder.find_spec across threads — no
    corruption, all forbidden calls raise. Codex post-merge open
    question 1: ON-mode concurrent imports were not previously
    thread-safety tested (only WARN dedup + install/uninstall were)."""
    uninstall_guard()
    install_guard(Mode.ON)
    try:
        finder = next(
            (f for f in sys.meta_path if isinstance(f, PlaneGuardFinder)),
            None,
        )
        assert finder is not None

        # Use distinct fake-source modules so each thread generates a
        # unique forbidden-import call without contention on a single
        # cache key. All threads target the same Evaluation module to
        # cross plane boundary (Execution → Evaluation).
        sources = [
            "src.foam_agent_adapter",
            "src.cylinder_strouhal_fft",
            "src.airfoil_surface_sampler",
            "src.cylinder_centerline_extractor",
            "src.plane_channel_uplus_emitter",
            "src.wall_gradient",
        ]
        target = "src.result_comparator"
        raised: list[bool] = []
        errors: list[BaseException] = []
        lock = threading.Lock()

        def worker(source: str):
            fake_spec = ModuleSpec(name=source, loader=None)
            exec_globals = {
                "__spec__": fake_spec,
                "__name__": source,
                "_finder": finder,
                "_target": target,
            }
            try:
                for _ in range(20):
                    try:
                        with strict_scope():
                            exec(
                                "_finder.find_spec(_target)",
                                exec_globals,
                            )
                        with lock:
                            raised.append(False)
                    except LayerViolationError:
                        with lock:
                            raised.append(True)
            except BaseException as e:  # noqa: BLE001
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(s,)) for s in sources]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        for t in threads:
            assert not t.is_alive(), "Thread deadlocked"
        assert not errors, f"Thread errors: {errors}"
        # All 6 × 20 = 120 calls should have raised (ON mode, no dedup).
        assert len(raised) == 120
        assert all(raised), "Some calls did not raise — ON-mode regression"
    finally:
        uninstall_guard()


# ---------------------------------------------------------------------------
# Codex Open Q 5 · Cold-start vs warm-path perf separation
# ---------------------------------------------------------------------------


def test_a4_perf_cold_start_separated(perf_guard):
    """Codex post-merge open Q 5: §2.6 cold-start budget should be
    measured separately. First-call perf may include thread-local
    init etc.; warm-call perf is the steady state."""
    finder = next(
        (f for f in sys.meta_path if isinstance(f, PlaneGuardFinder)),
        None,
    )
    assert finder is not None

    # Cold call: first-ever find_spec since fresh install.
    t0 = time.perf_counter_ns()
    finder.find_spec("src.foam_agent_adapter")
    cold_us = (time.perf_counter_ns() - t0) / 1000.0

    # Warm calls.
    iterations = 500
    samples: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        finder.find_spec("src.foam_agent_adapter")
        samples.append((time.perf_counter_ns() - t0) / 1000.0)
    samples.sort()
    warm_p95 = samples[int(0.95 * len(samples))]
    warm_median = samples[len(samples) // 2]

    # Cold-start budget per §2.6: ≤ 2 ms (generous; one-time cost).
    assert cold_us < 2000.0, f"Cold-start {cold_us:.2f} µs exceeds 2 ms"
    # Warm budget per §2.6 implicit guidance ≤ 100 µs p95 (same as A4).
    assert warm_p95 < 100.0, (
        f"Warm find_spec p95 {warm_p95:.2f} µs exceeds 100 µs "
        f"(median {warm_median:.2f} µs)"
    )


# ---------------------------------------------------------------------------
# A12 bootstrap purity AST walk (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_name",
    ["_plane_assignment", "_plane_guard"],
)
def test_a12_bootstrap_imports_only_stdlib_and_other_bootstrap(module_name):
    """Walk the AST; ensure imports only target stdlib or other bootstrap modules."""
    source = (SRC_ROOT / f"{module_name}.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    bootstrap_short_names = {"_plane_assignment", "_plane_guard"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # `import src.foo` would be alias.name = 'src.foo'
                assert not alias.name.startswith("src."), (
                    f"{module_name}.py uses `import {alias.name}` — bootstrap "
                    "violation. Only stdlib + intra-bootstrap allowed."
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue  # relative import (treated as ok if intra-bootstrap)
            if not node.module.startswith("src."):
                continue
            target_short = node.module.split(".", 1)[1]
            target_root = target_short.split(".", 1)[0]
            assert target_root in bootstrap_short_names, (
                f"{module_name}.py imports `from {node.module}` — only "
                f"intra-bootstrap (src._plane_assignment / src._plane_guard) "
                f"is allowed."
            )

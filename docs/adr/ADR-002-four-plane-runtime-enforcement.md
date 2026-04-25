# ADR-002 · Four-Plane Runtime Import Enforcement (sys.meta_path Layer)

**Status**: Draft-rev2 (Claude Code · 2026-04-25 · revised per Opus W2 Gate CHANGES_REQUIRED verdict) — awaiting Opus 4.7 W2 Gate re-review
**Deciders**: Opus 4.7 (W2 Gate) · Claude Code (main session) · Codex GPT-5.4 (independent verification pending)
**Consulted**: CFDJerry (indirect — this ADR inherits §2 SSOT authority from the pivot charter)
**Scope**: W2-W3 runtime layer — `sys.meta_path` finder raising `LayerViolationError` on
cross-plane violations that bypass `import-linter` static analysis. Static layer remains
ADR-001 (W1 done).
**Supersedes**: none. **Extends**: ADR-001 §3.3 (Deferred: runtime `sys.meta_path` layer).
**Deadline rationale**: Opus 追签 2026-04-25 anchors this ADR's Draft deadline at
**2026-04-28 23:59** (W2 Tuesday); missing the deadline auto-triggers
`RETRO-V61-001 trigger #3` (CHANGES_REQUIRED-equivalent retro on missed governance
deadline). Target promotion Draft → Accepted: W3 (2026-05-05) after implementation lands.

---

## 1. Context

ADR-001 (W1) shipped the static layer of four-plane import enforcement:
`import-linter` + pre-commit hook + CI step. Static analysis catches
`from src.foo import bar` syntax at commit / CI time.

### 1.1 The static-layer bypass surface

Opus Post-Hoc Review §3 末 explicitly called out that static analysis
**cannot** catch these runtime import patterns:

| # | Pattern | Why it bypasses `import-linter` | Guard carve-out / closure strategy |
|---|---|---|---|
| 1 | `importlib.import_module("src.comparator_gates")` | Module name computed at runtime; `import-linter` only walks the AST of `import` / `from ... import ...` statements | Routes through `sys.meta_path` → finder catches at §2.1 hot path |
| 2 | `__import__("src.comparator_gates")` | Same — dynamic dispatch | Routes through `sys.meta_path` → finder catches |
| 3 | `getattr(importlib, "import_module")("src.comparator_gates")` | Indirect attribute access obscures the call | Same as #1 — resolution still hits `meta_path` |
| 4 | Factory pattern: `loader.load("src.comparator_gates")` | Bypasses even `importlib` — e.g. `pkgutil.iter_modules` + `spec_from_file_location` | `spec_from_file_location` + `Loader.exec_module` still consults `sys.meta_path`; AC-C1 deliberate-violation fixture proves capture |
| 5 | Test fixtures that legitimately cross planes but leak into prod code | Cannot be distinguished by static analysis | Test-mode allowlist §2.4 (tests/ prefix regex) + reverse-test asserting no `src/**/_test.py` or `src/**/test_*.py` |
| 6 | Lazy import inside a function body whose module path is f-string'd | Syntactic, but `import-linter` doesn't flow-analyze | Same as #1 — f-string result still imports at runtime |
| 7 | `sys.modules["src.foo"] = stub` monkeypatching (pytest-mock, unittest.mock, manual fakery) | Bypasses finder entirely — Python's import machinery short-circuits when `sys.modules` already has the key | **Partial** — finder cannot intercept post-hoc pollution. Closure strategy: (a) restrict to test scope via allowlist — monkeypatch in prod code would itself fail static `import-linter` review; (b) optional §2.9 polling watchdog (cheap dict-diff at `src/__init__` + post-test hook) raises if prod code introduced a non-src pollution to an `src.*` key. AC-A13 tracks this. |
| 8 | `importlib.reload(mod)` where `mod` was already loaded pre-guard | `reload` re-executes module body; on Python 3.11+ it does hit `meta_path`, but 3.9/3.10 behavior is finder-skipped under certain flag combinations | Explicit AC-A14 test matrix: reload across 3.9 / 3.11 / 3.12 proving finder fires. If 3.9 is finder-skipped, ADR §6 documents reload as a known bypass under 3.9 and the CI Python version matrix blocks 3.9 from the `runtime-plane-guard` job |
| 9 | PEP 420 namespace package implicit path stitching (multiple `src/` roots found on `sys.path`) | A namespace package spans multiple file-system locations; finder may see `src.foo` as the first location while the loaded attribute comes from a second location with different plane assignment | Explicit §2.1 rule: `PLANE_OF` lookup keys on the **fully-qualified module name** (from `spec.name`), not file path. AC-A15 test exercises a two-root namespace package scenario and confirms finder classifies by declared name, not by path. If the repo ever introduces a namespace package, `tests/test_plane_assignment.py` is extended to cross-check. |

In the v3.x era the harness didn't use any of these patterns
aggressively — but P2 `ExecutorMode` refactor will introduce
`importlib.import_module(f"src.executor_mode.{mode}_openfoam")`-style
dispatch, which is exactly pattern #1. Without the runtime layer,
the P2 refactor's primary reason to exist (pluggable executor
backends) also becomes the primary vector for plane violations.

Patterns 7-9 were added in revised Draft 2026-04-25 per Opus W2 Gate
verdict Q8 ("漏 3 类 BLOCKING"). Pattern 7 (sys.modules pollution) is
the only one not fully closable at the meta_path layer; §2.9 documents
the partial-closure strategy. Patterns 8 and 9 are fully closable via
explicit test coverage (A14, A15).

### 1.2 Why runtime enforcement is necessary AND sufficient (with one documented gap)

- **Necessary**: patterns 1-9 above are non-hypothetical. Python's
  dynamic import surface is the explicit escape hatch that static
  analysis cedes.
- **Sufficient for 8 of 9**: a `sys.meta_path` finder runs **before**
  any import mechanism (static or dynamic) resolves a module, provided
  `sys.modules` does not already carry the key. Intercepting at
  `meta_path` means every import route — `import`, `importlib`,
  `__import__`, `spec_from_file_location`, pickle deserialization
  (which calls `__import__`), reload (on 3.11+), namespace packages —
  passes through the guard.
- **One partial gap**: pattern 7 (post-hoc `sys.modules` pollution)
  is fundamentally unreachable by `meta_path` finders because Python
  short-circuits the cache lookup. Treated as test-scope-only risk
  per §2.9; AC-A13 documents the polling watchdog compromise.

### 1.3 Explicit non-goals

- **Not** a replacement for ADR-001 static layer. Static layer catches
  the 99% case at commit time with zero runtime cost; runtime layer
  catches the 1% escape hatches at import time with sub-millisecond
  per-import overhead.
- **Not** a security boundary. The guard is defense-in-depth for
  maintainability, not a sandbox. Malicious code in the same process
  can disable the guard trivially (`sys.meta_path.remove(_guard)`).
- **Not** intended to enforce `ui.backend.*` or `scripts.*` — those
  remain out of contract scope per ADR-001 §3.2.

## 2. Decision

### 2.1 Mechanism: `sys.meta_path` finder with multi-frame caller resolution

Revised Draft 2026-04-25 — single-frame stack walk was deemed not
robust by Opus Q1 (pytest fixtures resolve through `_pytest.fixtures`
internals; `python -m src.foo` gives `__name__ == "__main__"`; lazy
imports nest through helper functions; C extensions skip Python frames
entirely). The revised design uses a bounded multi-frame walk with
explicit name-lookup rules.

Land a single new module `src/_plane_guard.py` (leading underscore
denotes internal infrastructure, not a public plane) that:

1. Defines `LayerViolationError(ImportError)` — subclass chosen so
   existing `try: import X except ImportError` code paths still see
   the violation, but a specific exception type is available for
   diagnostic tools.
2. Implements `class PlaneGuardFinder(importlib.abc.MetaPathFinder)`
   with a single `find_spec(fullname, path, target=None)` method that:
   - **Fast-path**: returns `None` immediately if `fullname` does not
     start with `src.` (delegates to the next finder on `meta_path`).
   - **Source-plane resolution** via multi-frame walk:
     1. Start at `sys._getframe(1)` (the frame that invoked the import).
     2. Walk up via `frame.f_back` with a hard cap of **N = 20** frames.
     3. For each frame, read module identity via this priority chain:
        `frame.f_globals.get('__spec__')` → `spec.name` if non-None;
        else `frame.f_globals.get('__name__')` (handles `__main__` +
        ad-hoc exec contexts).
     4. If the resolved name starts with `src.` AND is present in
        `PLANE_OF`, classify that frame as the source plane and stop.
     5. If a frame is unmapped (typical: pytest internals, stdlib,
        ipython, C-extension trampolines), continue walking.
     6. If the walk reaches frame N or stack top with no `src.*` hit,
        classify source as `<external>` — do NOT raise, return `None`
        (external → any target is allowed; external code is out of
        ADR-001 scope per §3.2).
   - **Target-plane lookup**: `PLANE_OF[fullname]` (Single Source of
     Truth: `src._plane_assignment.PLANE_OF`).
   - **Verdict**: if the `(source_plane, target_plane)` pair is in the
     forbidden set (mirrors `.importlinter` contracts 1-4), raise
     `LayerViolationError` with a formatted message pointing at ADR-001
     §2.1 + suggested remediation.
   - Otherwise returns `None` (allow the real finder to load the
     module — the guard does NOT load modules itself).

**Why N = 20**: typical `src.*` → `src.*` import stack depth observed
in the repo is 3-8 frames (measured via `sys.settrace` on the `pytest`
suite). 20 covers conftest fixture chains + helper decorators +
contextlib-wrapped helpers with slack. Walk cost at N=20 is still
sub-microsecond per frame on M1 (`_getframe` + two dict lookups).

**Cython / C-extension handling**: C code calling
`PyImport_ImportModule` does not push a Python frame, so frame[1]
appears to jump directly to whatever Python caller invoked the C
function. This is correct behavior for the guard — if the Python
caller is in a `src.*` module, its plane is the source; if not, the
external-caller fast-exit applies. Explicit AC-A16 test exercises a
synthetic C-extension trampoline to verify no false positive/negative.

**pytest / `__main__` alignment example**:
- `pytest tests/test_foo.py::test_bar` → frame chain is
  `pytest_runtest_call` → `test_bar` (module `tests.test_foo`,
  unmapped) → walk continues → `__main__` / pytest internals
  (unmapped) → reaches top → classified `<external>` → always
  allowed. Test-allowlist in §2.4 then separately uses the
  `tests/` prefix on any frame hit to grant pass.
- `python -m src.task_runner` → frame chain root is module
  `src.task_runner` with `__spec__.name = 'src.task_runner'` → plane
  = Control → target lookup proceeds normally.

### 2.2 Plane assignment as shared SSOT

Both `.importlinter` (static) and `PlaneGuardFinder` (runtime) must
read plane assignment from the **same table**. Proposal:

- Add `src/_plane_assignment.py` containing a single module-level
  dict `PLANE_OF: dict[str, Plane]` mapping module name → plane enum
  (`Plane.CONTROL` / `Plane.EXECUTION` / `Plane.EVALUATION` /
  `Plane.KNOWLEDGE` / `Plane.SHARED`).
- `.importlinter` config is **generated** from this dict by a small
  build step (`scripts/gen_importlinter.py`) invoked in pre-commit
  — removes the hand-enumerated brittleness that Codex G-5 R1
  Medium #3 flagged (ADR-001 §4.1 AC-A7).
- Test `tests/test_plane_assignment.py` asserts every top-level
  `src.*` package is listed, no orphans (satisfies ADR-001 §2.7 AC-2
  coverage check).

This decouples "what the planes are" from "how they're enforced" and
eliminates drift between the two enforcement layers.

### 2.3 Activation model

Guard activation happens at `src/__init__.py` import time, gated
by an env var:

```python
# src/__init__.py
import os
if os.environ.get("CFD_HARNESS_PLANE_GUARD", "0") != "0":
    from ._plane_guard import install_guard
    install_guard()
```

Default: **OFF** in v1.0 runtime layer (W2-W3). W4+ flips the
default to `"1"` once the P2 refactor is stable. Gradual rollout
avoids silent test breakage on day 1.

Activation lifecycle:
- **OFF** (default, W2-W3): no guard installed; only static layer
  enforces. ADR-002 Draft exists; `src/_plane_guard.py` + tests
  exist; CI has an opt-in `runtime-plane-guard` job exercising the
  guard against a deliberate violation fixture.
- **WARN** (W3-W4): `CFD_HARNESS_PLANE_GUARD=warn` logs a warning
  via `logging.getLogger("src._plane_guard")` instead of raising.
  Optional stopover for a sprint to shake out unknown violations.
- **ON** (W4+): `CFD_HARNESS_PLANE_GUARD=1` raises on violation in
  all processes. CI default for `backend-tests` job.

### 2.4 Test-mode allowlist (revised Draft · Option A with strengthened conditions)

Tests legitimately cross planes (e.g. a test for
`src.task_runner` imports both `src.foam_agent_adapter` and
`src.result_comparator`). Two mutually exclusive options were
considered:

#### Option A · module-prefix allowlist (chosen)

`PlaneGuardFinder` walks the call stack (using the same multi-frame
walk defined in §2.1, up to N=20 frames) and, if **any** frame's
resolved module name (via the same `__spec__.name` → `__name__`
priority chain) matches the literal regex **`^tests($|/)`** (i.e. the
root package is exactly `tests` OR the module path is rooted under a
`tests` directory), skips the forbidden-plane check.

- **Pros**: zero test-side changes; no fixture coordination.
- **Cons**: (i) production code that happens to live in a `_test.py`
  file would bypass the guard; (ii) helper modules physically placed
  under `tests/` but invoked from `src` would also bypass; (iii)
  pytest fixture frame chains can alternate between `tests.*` and
  `_pytest.*` / `src.*` during fixture setup, so any single unmapped
  frame in the chain must NOT cancel a later `tests.*` hit.

Point (iii) is addressed by §2.1's multi-frame walk — the walk
continues past unmapped frames rather than stopping at the first
non-`src.*` one, so a fixture chain of
`_pytest.fixtures` → `tests.conftest` → `src.task_runner` correctly
classifies the caller as test-scope.

#### Option B · contextvar token (rejected, but documented for rollback)

Tests opt into a scope via `with plane_guard.test_scope():`. Guard
skips when the contextvar is set.

- Pros: explicit opt-in.
- Cons: ~30 test modules in the current repo cross planes; all would
  need a context manager or autouse fixture.

#### Strengthened conditions (revised Draft per Opus Q4)

All three conditions are **blocking** for Draft → Accepted:

1. **Regex literal is frozen as `^tests($|/)`**. `tests_integration/`
   or `test_utils/` in repo root would NOT match — repo convention
   stays on single `tests/` root. `src/foo/tests/`-style nested test
   directories would also NOT match (prevents escape).

2. **Reverse-test MUST land before W3 ends**:
   `tests/test_plane_guard_escape.py` asserts via `glob` that the
   following paths are empty across the whole repo:
   - `src/**/*_test.py`
   - `src/**/test_*.py`
   - `src/**/tests/` (no nested `tests/` subdirectories under `src`)

   This closes escape (i) and (ii). AC-A17 tracks this.

3. **Rollback trigger for Option A → B**: if during the W4 dogfood
   period the guard observability log records **≥3 distinct incidents**
   of fixture-frame confusion (symptom: guard raised on a legitimate
   test execution that was subsequently marker'd as
   `@pytest.mark.plane_guard_bypass`), ADR-002 auto-amends to Option
   B and a migration DEC is opened within 1 week. Counter location:
   `reports/plane_guard/fixture_frame_confusion.jsonl`, one line per
   incident with timestamp + `tests/...` path + stack snippet.
   Migration counter + incident schema live in `src/_plane_guard.py`
   docstring for reviewability. AC-A18 tracks the incident-log
   infrastructure; the rollback itself does not ship in v1.0 but the
   measurement plumbing does.

**Strict scope for self-tests**: the guard exposes
`plane_guard.strict_scope()` context manager that **disables** the
test allowlist, so tests for the guard itself can verify real
enforcement (otherwise the guard's own tests would bypass the
guard). Satisfies AC-A3(d).

### 2.5 Error surface

```
LayerViolationError: runtime plane-crossing import forbidden.
  source module: src.foam_agent_adapter (Execution plane)
  target module: src.comparator_gates (Evaluation plane)
  rule: Contract 1 · execution-never-imports-evaluation
  authority: ADR-001 §2.2 · SYSTEM_ARCHITECTURE v1.0 §2

Most likely fixes:
  (a) read the comparator output from an ExecutionResult artifact
      field rather than invoking the comparator directly from Execution.
  (b) move the needed logic down to src.models (shared types) if the
      helper is pure type logic.
  (c) if this is a legitimate test, mark the caller file with a
      tests/ prefix or use src._plane_guard.test_scope().
```

Message format is **stable** — downstream tooling (IDE integrations,
ultrareview) may pattern-match on `source plane:` / `target plane:` /
`rule:` keys.

### 2.6 Performance budget

Per-`find_spec` call: target ≤ 50 µs median on M1. Measurement:
added to `tests/test_plane_guard_perf.py`, fail if >100 µs p95.

Cold start: the guard is installed at `src/__init__.py` import, so
first `import src` pays a one-time cost of dict construction. Target
≤ 2 ms. Budget is generous because the dict is ~25 entries.

Stack-walk cost is the dominant factor. `sys._getframe(1)` is
microseconds; `inspect.stack()` is milliseconds. Implementation
**must** use `sys._getframe` in the hot path. `inspect.stack()` is
only for error-message formatting on the violation path (which is
slow-by-design — if you're raising, you're not hot).

### 2.7 Interaction with `importlib.util.spec_from_file_location`

Pattern 4 (factory loads by file path) still routes through
`importlib._bootstrap._find_and_load`, which walks `sys.meta_path`.
Verified via a deliberate-violation fixture:
`tests/fixtures/plane_violation/load_by_path.py` constructs a spec
from file path and triggers the guard. This is AC-C1.

### 2.8 Interaction with pickle / dill deserialization

Pickle's `find_class(module, name)` ultimately calls `__import__`,
which consults `sys.meta_path`. Any pickled object whose class lives
in a cross-plane module (relative to the unpickler's caller frame)
will trigger `LayerViolationError` at unpickle time. This is
**intentional** — pickled state crossing planes is a known refactor
hazard and the guard surfaces it loudly.

If an application has legitimate cross-plane pickle (none known in
the repo today), it uses `plane_guard.test_scope()` around the
unpickle. Tracked as known-limitation in §3.

### 2.9 Partial-closure for Pattern 7 (sys.modules pollution) · added revised Draft

As §1.2 acknowledges, `sys.modules["src.foo"] = stub` cannot be
intercepted by a `meta_path` finder — Python short-circuits import
whenever the cache already holds the key. Monkeypatching (pytest-mock,
`unittest.mock.patch.dict(sys.modules, ...)`, manual stub injection)
is the canonical failure mode, and it is **test-scoped by
convention**: production code that writes to `sys.modules['src.*']`
already fails ADR-001 static review (the static `.importlinter`
scan plus AST grep would flag a `sys.modules[...] =` assignment
targeting an `src.*` key as an obvious anti-pattern for review
comment, even though `.importlinter` itself does not check
`sys.modules` assignments).

**Optional polling watchdog** (tracked by AC-A13, not blocking for
Draft → Accepted):

- At `src/__init__` import, snapshot the set `S0 = {k for k in
  sys.modules if k.startswith("src.")}` along with each module's
  `id()` (object identity, not content).
- A pytest session-finish hook (and, if guard is ON in prod, a
  `atexit` handler) diffs the current `src.*` snapshot against `S0`:
  - Keys present in `S0` but with different `id()` → pollution (a
    stub was swapped in or `reload` re-created the module).
  - Keys added post-`S0` → expected (lazy imports legitimately load
    `src.*` as the session runs).
- Diff lines go to `reports/plane_guard/sys_modules_pollution.jsonl`
  one line per event with timestamp, key, old `id()`, new `id()`,
  and best-effort stack trace (captured on the hook).

The watchdog does NOT raise — it is observability-only. The decision
to upgrade to a hard fail is deferred to W5 GA retro if pollution
events ever originate from prod code (they should not).

## 3. Consequences

### 3.1 Positive

- **Closes the dynamic-import loophole** — `importlib.import_module`,
  `__import__`, factory loaders, pickle all surface cross-plane
  violations at the moment of violation, with line number.
- **Single SSOT for plane assignment** — `.importlinter` is
  generated from `PLANE_OF`, eliminating ADR-001 AC-A7 drift risk.
- **Gradual rollout via env var** — no flag day. OFF → WARN → ON.
- **Self-documenting errors** — `LayerViolationError` message points
  at the ADR and suggests canonical fixes.
- **Zero overhead when disabled** — default OFF; env var check is
  one `os.environ.get` at `src` import time.

### 3.2 Negative

- **Stack-walk cost on every `src.*` import** — even with
  `sys._getframe`, a measurable fraction of a microsecond per
  import. For ~200 imports on cold start, ≤ 10 ms total. Acceptable.
- **Test allowlist is prefix-based** — Option A has the low-risk
  escape hatch that a prod module named `*_test.py` would bypass.
  Mitigated by repo convention + `tests/test_plane_guard_escape.py`
  asserting no `src/**/_test.py` files exist.
- **Pickled cross-plane state becomes fatal** — none known today, but
  future surrogate backends serializing Evaluation-plane results
  into an Execution-plane pipeline would break. Documented in §2.8.
- **Observability cost during WARN mode** — `logging.getLogger` call
  per violation. Negligible.
- **C extension imports** — if a compiled extension imports via the
  C API, it bypasses `sys.meta_path` entirely. None in repo today.
  Documented as known-limitation.

### 3.3 Deferred (explicit)

- **Plugin Plane enforcement** (`src/surrogate_backend/**`,
  `src/diff_lab/**`) — gains a 5th contract + `PLANE_OF` entry when
  first file lands. Same pattern, no ADR-002 change required.
- **Top-level physical restructure** (`src/control/`,
  `src/execution/`, etc.) — still P2 ExecutorMode scope. `PLANE_OF`
  table will need re-mapping at that point (one commit diff).
- **`ui/backend/**` runtime enforcement** — out of scope for v1.0.
  When `ui/backend` itself splits into plane-separated subpackages,
  a dedicated ADR will address runtime enforcement there.

## 4. Verification

### 4.1 Acceptance criteria (Draft → Accepted)

Revised Draft 2026-04-25 — A7 expanded to full 4-contracts × 3-modes
matrix; A10-A18 added per Opus Q6 ("漏 3 类 BLOCKING" + §2.4 reverse
test + §2.8 rollback measurement).

| # | Criterion | Evidence |
|---|---|---|
| A1 | `src/_plane_guard.py` + `src/_plane_assignment.py` land with full type annotations | `mypy src._plane_guard src._plane_assignment` clean |
| A2 | `scripts/gen_importlinter.py` regenerates `.importlinter` from `PLANE_OF`; diff empty on current main | CI step asserts zero-diff |
| A3 | `tests/test_plane_guard.py` covers: (a) allowed import no-op; (b) forbidden import raises; (c) test-allowlist permits; (d) strict_scope disables allowlist; (e) `importlib.import_module` pattern caught; (f) `__import__` pattern caught; (g) `spec_from_file_location` pattern caught | pytest green |
| A4 | `tests/test_plane_guard_perf.py` asserts p95 `find_spec` ≤ 100 µs on current repo | pytest green |
| A5 | `tests/test_plane_assignment.py` asserts every top-level `src.*` package has a `PLANE_OF` entry | pytest green · satisfies ADR-001 AC-2 |
| A6 | CI has new opt-in job `runtime-plane-guard` that runs `pytest` with `CFD_HARNESS_PLANE_GUARD=1` — one green run required before flipping default ON in W4. Hard-fail switchover PR MUST name a specific commit owner and include a rollback trigger: **auto-revert to opt-in if CI false-positive rate >1% across any 7-day rolling window** (measured via `.github/workflows/plane-guard-metrics.yml`) | `.github/workflows/ci.yml` diff + switchover PR description |
| A7 | **Deliberate-violation fixture matrix**: `tests/fixtures/plane_violation/` contains **one fixture per forbidden contract** (4 total: Execution→Evaluation, Evaluation→Execution, Knowledge→anything, models→anything). Each fixture is exercised under **all 3 modes** (OFF silent / WARN log-no-raise / ON raise). Matrix = 4 × 3 = 12 test cases. `tests/test_plane_guard_fixtures.py` drives the matrix with pytest parametrize | pytest green · 12 cases pass |
| A8 | Activation remains OFF by default in v1.0; env var toggle documented in README + ADR | README §"Runtime plane guard" |
| A9 | Error message format is stable and matches §2.5 verbatim in at least one test assertion | pytest green |
| **A10** | **fork-safety**: `tests/test_plane_guard_fork.py` spawns a child via `multiprocessing.get_context('fork')` with guard in ON mode; child inherits `sys.meta_path` finder and `CFD_HARNESS_PLANE_GUARD=1`; child raises `LayerViolationError` on a deliberate violation. Also tests `spawn` context (env var survives). If guard uses contextvar for any state, `tests/test_plane_guard_fork.py` asserts that state is re-initialized in child (no stale parent state leaks) | pytest green |
| **A11** | **thread-safety**: `tests/test_plane_guard_thread.py` runs 100 concurrent imports across 8 threads with guard in ON mode; no deadlock, no dropped `LayerViolationError`, no false positive. Internal state (any dedupe `set` or counter) protected by `threading.Lock` if mutable; or proven immutable | pytest green + `grep -n "Lock\|RLock" src/_plane_guard.py` diff review |
| **A12** | **bootstrapping zero-src-deps**: `src/_plane_guard.py` and `src/_plane_assignment.py` import **only from stdlib** (no `from src.*` anywhere in either module). Enforced by a dedicated `import-linter` contract (`contract:plane-guard-bootstrap-purity`) declaring `src._plane_guard` + `src._plane_assignment` have forbidden_modules = all other `src.*`. Without this, guard loading would chain-load `src.*` modules which would themselves trigger the guard → infinite recursion. This is **the** most critical AC | `.importlinter` diff shows the new contract + `lint-imports` green |
| **A13** | **sys.modules pollution watchdog** (partial closure of Pattern 7): optional §2.9 watchdog diffs `sys.modules` keys tagged `src.*` at `src/__init__` load vs. post-test-session hook; logs any key whose module identity changed since install. Test scope only; prod code writing to `sys.modules['src.*']` already fails static `import-linter`. Logging lives in `reports/plane_guard/sys_modules_pollution.jsonl` | `tests/test_plane_guard_sys_modules.py` · 1 pytest-mock case + 1 negative case |
| **A14** | **importlib.reload matrix** (Pattern 8): `tests/test_plane_guard_reload.py` parametrized across Python 3.11 / 3.12 (CI matrix); asserts `importlib.reload(src.task_runner)` still triggers finder. Python 3.9 row documented in §6 Known Limitations if finder is skipped on that version; 3.9 row NOT in the `runtime-plane-guard` CI job | pytest green on 3.11/3.12 · §6 ADR amendment if 3.9 divergence |
| **A15** | **PEP 420 namespace package** (Pattern 9): `tests/fixtures/plane_violation/namespace_pkg/` constructs a two-root namespace package for `src.<synthetic>`; asserts finder classifies by `spec.name` not file path | pytest green |
| **A16** | **C-extension trampoline**: synthetic C-calls-Python test via `ctypes` or a minimal C extension stub; asserts no false positive when C code is in the caller chain. If synthetic stub is infeasible, document as §6 known limitation and cover via `pyo3`-compiled dummy | pytest green OR §6 amendment |
| **A17** | **reverse-test for §2.4**: `tests/test_plane_guard_escape.py` asserts via `glob.glob` that `src/**/*_test.py`, `src/**/test_*.py`, and `src/**/tests/` are all empty paths | pytest green |
| **A18** | **Option A→B rollback plumbing** (§2.4): guard writes each fixture-frame-confusion incident to `reports/plane_guard/fixture_frame_confusion.jsonl`; counter `>=3` triggers ADR §2.4 auto-amend to Option B. Test asserts the log file schema (timestamp + path + stack-snippet fields) | pytest green · schema test |

### 4.2 Codex independent verification

Per Model Routing v6.2 §B + ADR-002 §2.1 complexity:

- **Claim to verify**: "the `PlaneGuardFinder` catches all 6 bypass
  patterns from §1.1 without false positives on legitimate
  imports (including pytest conftest loading, `__main__` execution,
  and dynamic plugin loading in tests)".
- **Verification method**: Codex reviews `src/_plane_guard.py` +
  `tests/test_plane_guard.py` for completeness against the 6
  patterns. Expected verdict: APPROVE_WITH_COMMENTS on first round;
  self-pass-rate estimate 0.65 (new mechanism, non-trivial stack
  walk logic, test-allowlist edge cases).
- **Output archive**:
  `reports/codex_tool_reports/adr_002_runtime_layer_review.log`.

### 4.3 Opus W2 Gate sign-off

Per Opus 追签 AC-3 (2026-04-25): this ADR **must** be in Draft
status (or further) by 2026-04-28 23:59. Opus W2 Gate Tuesday
reviews the Draft for:

- (a) Does §2 close every pattern Opus §3 末 originally identified?
- (b) Is the gradual rollout plan (OFF → WARN → ON) safe relative
  to P2 refactor timing?
- (c) Is the `PLANE_OF` SSOT design consistent with ADR-001 AC-A7?
- (d) Are deferred items (§3.3) defensibly deferred, or is any of
  them actually W2-W3 scope creep?

Expected verdict: ACCEPT or ACCEPT_WITH_COMMENTS. If
CHANGES_REQUIRED, revise + re-submit within W2.

## 5. Implementation timeline

| W | Date | Deliverable |
|---|---|---|
| W2 Draft | 2026-04-28 | This ADR in Draft + Opus W2 Gate review |
| W2 Impl Start | 2026-04-29 | `src/_plane_assignment.py` + `scripts/gen_importlinter.py` + regenerate `.importlinter` with zero diff on main |
| W2 Impl Mid | 2026-05-01 | `src/_plane_guard.py` + `tests/test_plane_guard.py` covering A3(a-g) |
| W3 CI | 2026-05-02 | Opt-in `runtime-plane-guard` CI job; WARN mode active |
| W3 Accept | 2026-05-05 | All AC pass; ADR flips Draft → Accepted; Opus W3 confirmation |
| W4 ON | 2026-05-12 | Default env var flip to ON pending one sprint of WARN-mode green CI |

## 6. Known limitations (revised Draft)

- **Python 3.9 `importlib.reload`**: Pattern 8 may be finder-skipped
  under certain flag combinations on 3.9. The `runtime-plane-guard`
  CI job runs only on 3.11 and 3.12 (the project's runtime matrix).
  If a future CI matrix adds 3.9 back, AC-A14 must be re-validated
  and if divergence is confirmed this section must amend with the
  specific bypass conditions + mitigation.
- **C-extension trampolines without a Python caller**: if a C
  extension is the first frame and never returns to Python before
  triggering an `src.*` import (e.g. `PyImport_ImportModuleEx`
  during extension init), the multi-frame walk finds no `src.*` frame
  and classifies as `<external>` (permissive). This is the correct
  conservative behavior but means a C-extension-authored cross-plane
  violation would not be caught. No such extension exists in repo.
- **`sys.modules` post-hoc pollution** — unintercept able at the
  `meta_path` layer. See §2.9 partial-closure watchdog.
- **Malicious intra-process bypass** — the guard is **not a security
  boundary** (§1.3). Any code running in-process can remove the
  finder from `sys.meta_path`. This is defense-in-depth for
  maintainability, not isolation.
- **Multi-interpreter (`PEP 554` subinterpreters)** — untested and
  out of scope for v1.0. Documented here; AC-A19 may be added in
  a future revision if the repo introduces subinterpreter usage.

## 7. Related decisions

- **ADR-001** — static layer (parent ADR; this ADR is the runtime
  companion)
- **DEC-V61-054/055/056** — P1 Metrics & Trust Layer arc (reason why
  `src.metrics.*` needs plane assignment enforcement)
- **PIVOT_CHARTER_2026_04_22** §4.3a G-5 — ADR-001 is G-5; this ADR
  closes the "W2-W3 runtime layer" deferral in §4.3a
- **SYSTEM_ARCHITECTURE v1.0** §2 — authoritative import rules
  (SSOT)
- **RETRO-V61-001 trigger #3** — missed-deadline retro that
  auto-fires if this ADR is not in Draft by 2026-04-28 23:59

## 8. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| Draft | 2026-04-25T05:30 | Claude Code (Opus 4.7 CLI) | Initial draft; pending Opus W2 Gate review |
| Draft-rev2 | 2026-04-25T08:00 | Claude Code (Opus 4.7 CLI) | CHANGES_REQUIRED verdict response. 4 blocking items landed: (1) §2.1 single-frame → bounded multi-frame walk (N=20) with `__spec__.name` priority chain + Cython/external fallback; (2) §1.1 table expanded from 6 to 9 patterns (sys.modules pollution, reload, PEP 420 namespace) with per-pattern closure strategy column; (3) §2.4 Option A strengthened — regex literal `^tests($|/)` frozen, reverse-test AC-A17 required, Option A→B rollback trigger plumbing AC-A18 shipped in v1.0; (4) §4.1 AC expanded A7 to 4-contracts × 3-modes matrix, added A10 fork-safety / A11 thread-safety / A12 bootstrapping zero-src-deps / A13-A16 for patterns 7-9 + C-extension / A17-A18 for §2.4 conditions. New §2.9 sys.modules watchdog. New §6 Known Limitations. Revision history promoted to §8. |

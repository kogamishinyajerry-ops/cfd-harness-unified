# ADR-002 · Four-Plane Runtime Import Enforcement (sys.meta_path Layer)

**Status**: Draft (Claude Code · 2026-04-25) — awaiting Opus 4.7 W2 Gate review
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

| # | Pattern | Why it bypasses `import-linter` |
|---|---|---|
| 1 | `importlib.import_module("src.comparator_gates")` | Module name computed at runtime; `import-linter` only walks the AST of `import` / `from ... import ...` statements |
| 2 | `__import__("src.comparator_gates")` | Same — dynamic dispatch |
| 3 | `getattr(importlib, "import_module")("src.comparator_gates")` | Indirect attribute access obscures the call |
| 4 | Factory pattern: `loader.load("src.comparator_gates")` | Bypasses even `importlib` — e.g. `pkgutil.iter_modules` + `spec_from_file_location` |
| 5 | Test fixtures that legitimately cross planes but leak into prod code | Cannot be distinguished by static analysis |
| 6 | Lazy import inside a function body whose module path is f-string'd | Syntactic, but `import-linter` doesn't flow-analyze |

In the v3.x era the harness didn't use any of these patterns
aggressively — but P2 `ExecutorMode` refactor will introduce
`importlib.import_module(f"src.executor_mode.{mode}_openfoam")`-style
dispatch, which is exactly pattern #1. Without the runtime layer,
the P2 refactor's primary reason to exist (pluggable executor
backends) also becomes the primary vector for plane violations.

### 1.2 Why runtime enforcement is necessary AND sufficient

- **Necessary**: patterns 1-6 above are non-hypothetical. Python's
  dynamic import surface is the explicit escape hatch that static
  analysis cedes.
- **Sufficient**: a `sys.meta_path` finder runs **before** any import
  mechanism (static or dynamic) resolves a module. Intercepting at
  `meta_path` means every single route — `import`, `importlib`,
  `__import__`, `spec_from_file_location`, pickle deserialization
  (which calls `__import__`), anything — passes through the guard.

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

### 2.1 Mechanism: `sys.meta_path` finder

Land a single new module `src/_plane_guard.py` (leading underscore
denotes internal infrastructure, not a public plane) that:

1. Defines `LayerViolationError(ImportError)` — subclass chosen so
   existing `try: import X except ImportError` code paths still see
   the violation, but a specific exception type is available for
   diagnostic tools.
2. Implements `class PlaneGuardFinder(importlib.abc.MetaPathFinder)`
   with a single `find_spec(fullname, path, target=None)` method that:
   - Fast-path: returns `None` immediately if `fullname` does not
     start with `src.` (delegates to the next finder on `meta_path`).
   - Looks up the **source plane** by walking the call stack one
     frame back (`inspect.stack()[1]` or `sys._getframe(1)`) and
     finding the caller's module name.
   - Looks up the **target plane** via the plane assignment table
     (Single Source of Truth: `src._plane_assignment.PLANE_OF`).
   - If the `(source_plane, target_plane)` pair is in the forbidden
     set (mirrors `.importlinter` contracts 1-4), raises
     `LayerViolationError` with a formatted message pointing at
     ADR-001 §2.1 + suggested remediation.
   - Otherwise returns `None` (allow the real finder to load the
     module — the guard does NOT load modules itself).

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

### 2.4 Test-mode allowlist

Tests legitimately cross planes (e.g. a test for
`src.task_runner` imports both `src.foam_agent_adapter` and
`src.result_comparator`). Two mutually exclusive options under
consideration:

#### Option A · module-prefix allowlist (recommended)

`PlaneGuardFinder` walks the call stack and, if **any** frame's
module name starts with `tests.` or ends with `_test.py`, skips the
check. Simple, no fixture coordination needed.

Pros: zero test-side changes.
Cons: production code that happens to live in a `_test.py` file
bypasses the guard (low risk — repo convention segregates
`src/` from `tests/`).

#### Option B · contextvar token

Tests opt into a scope via `with plane_guard.test_scope():`. Guard
skips when the contextvar is set.

Pros: explicit opt-in.
Cons: every cross-plane test fixture needs the context manager or
pytest marker; boilerplate.

**Decision**: Option A, with one additional constraint — the guard
also exposes a `plane_guard.strict_scope()` context manager that
**disables** the test allowlist, so tests for the guard itself can
verify real enforcement. Satisfies AC-B1 (self-test coverage).

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

| # | Criterion | Evidence |
|---|---|---|
| A1 | `src/_plane_guard.py` + `src/_plane_assignment.py` land with full type annotations | `mypy src._plane_guard src._plane_assignment` clean |
| A2 | `scripts/gen_importlinter.py` regenerates `.importlinter` from `PLANE_OF`; diff empty on current main | CI step asserts zero-diff |
| A3 | `tests/test_plane_guard.py` covers: (a) allowed import no-op; (b) forbidden import raises; (c) test-allowlist permits; (d) strict_scope disables allowlist; (e) `importlib.import_module` pattern caught; (f) `__import__` pattern caught; (g) `spec_from_file_location` pattern caught | pytest green |
| A4 | `tests/test_plane_guard_perf.py` asserts p95 `find_spec` ≤ 100 µs on current repo | pytest green |
| A5 | `tests/test_plane_assignment.py` asserts every top-level `src.*` package has a `PLANE_OF` entry | pytest green · satisfies ADR-001 AC-2 |
| A6 | CI has new opt-in job `runtime-plane-guard` that runs `pytest` with `CFD_HARNESS_PLANE_GUARD=1` — one green run required before flipping default ON in W4 | `.github/workflows/ci.yml` diff |
| A7 | Deliberate-violation fixture proves CI fails loudly when guard is ON | PR description shows red CI on sentinel branch |
| A8 | Activation remains OFF by default in v1.0; env var toggle documented in README + ADR | README §"Runtime plane guard" |
| A9 | Error message format is stable and matches §2.5 verbatim in at least one test assertion | pytest green |

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

## 6. Related decisions

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

## 7. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| Draft | 2026-04-25 | Claude Code (Opus 4.7 CLI) | Initial draft; pending Opus W2 Gate review |

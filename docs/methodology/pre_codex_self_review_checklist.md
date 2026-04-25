# Pre-Codex Self-Review Checklist

> **Status**: Active (v1.0)
> **Effective**: 2026-04-25 (post RETRO-V61-006 MP-A promotion)
> **Authority**: RETRO-V61-006 §"What broke" #1 — W4 prep R1 missed the writer-without-callsite class of bug because self-review did not include this check; Codex caught it via subprocess repro after a 0.20+ delta calibration miss
> **Companion**: `docs/governance/CODEX_REVIEW_RUBRIC.md` (Codex-side challenge duties · the mirror image of this file)

## 1. What this is

Claude Code CLI's **pre-flight checklist before invoking Codex** for any risky-PR review per RETRO-V61-001 baseline. The intent is to catch the easy-to-miss class of bugs in self-review so Codex spends its budget on harder findings, not on first-pass smell tests.

Each check is a 1-2 minute grep / inspection. Running them takes <10 minutes total. Skipping them is what produced RETRO-V61-006's R1 0.85 → CHANGES_REQUIRED 3 HIGH miss.

## 2. The checklist

Run **before** writing the Codex prompt (so missing items get fixed pre-Codex, not discovered during review):

### 2.1 Writer / observer / hook callsite check (MP-A)

For every NEW public function in the PR, especially observability writers (`record_*`, `emit_*`, `log_*`, `snapshot_*`, etc.), grep for non-test callers:

```bash
# Replace <function_name> with each new function's name
grep -rn "<function_name>(" src/ scripts/ ui/ \
  | grep -v "^tests/" | grep -v "_test\.py:" | grep -v "/test_"
```

**Pass criterion**: at least one non-test callsite OR explicit documentation that the function is intended for direct external invocation only (e.g., a CLI entrypoint or a test-only helper).

**Fail mode** (RETRO-V61-006 F1): writer exists, has comprehensive unit tests, but no production callsite → Codex catches it. The W4 prep R1 A18 writer hit this exactly.

### 2.2 atexit / process-exit registration check (MP-B)

For every NEW module-level state introduced via `src/__init__.py` auto-install or similar import-time activation:

```bash
# Find new module-level state
grep -nE "^_[A-Z_]+\s*=" src/<module>.py

# Verify atexit registration
grep -n "atexit" src/<module>.py
```

**Pass criterion**: any module-level state activated under auto-install MUST have a corresponding `atexit.register(...)` (or pytest session-finish equivalent) for diff / teardown. Plain `del` in `uninstall_*()` is insufficient because users / `src/__init__.py` rarely call uninstall.

**Fail mode** (RETRO-V61-006 F2): A13 watchdog ran diff inside `uninstall_guard()` only; auto-install processes exit without uninstall → A13 silent in main observation path.

### 2.3 Path resolution (cwd vs repo-root) check

For every NEW file-write helper that targets `reports/` / `.planning/` / artifact directories:

```bash
# Find new write helpers
grep -nE "^def _?(resolve|write|save|append|emit|record)_.*path" src/

# Verify they don't use cwd-relative paths
grep -A5 "def _?(resolve|write).*path" src/<module>.py | grep -E "os\.getcwd|^[^\.]/|\.\."
```

**Pass criterion**: write helpers anchor to `_find_repo_root()` (or equivalent project-root discovery) by default. cwd-relative paths are acceptable ONLY for explicitly-cwd-scoped output (e.g., a CLI tool that writes to user's pwd).

**Fail mode** (RETRO-V61-006 F3): writer wrote cwd-relative; reader wrote repo-root-anchored → silent path divergence masked the signal. This is the **third recurrence** of this class of bug post-pivot (V61-053, V61-049, W4 prep F3); a fourth recurrence triggers extraction to `src/_path_utils.py`.

### 2.4 CI infrastructure healthy (MP-G)

Before invoking Codex on any PR that depends on CI signal (observability instrumentation, dogfood-window setup, etc.):

```bash
gh run list --limit=5 --json conclusion | jq -r '.[].conclusion' | sort | uniq -c
```

**Pass criterion**: at least 1 of last 5 runs conclude `success`. If all 5 are `failure` or `cancelled`, the PR's CI signal is unverified — fix the CI before invoking Codex.

**Fail mode** (RETRO-V61-006 addendum 2): 40 consecutive CI failures masked the W4 stage-1 dogfood pytest. CI runs produced empty .jsonl artifacts that would have been mis-read as "0 incidents = GO" at 5/9 review.

### 2.5 Subprocess / real-stack repro coverage (MP-C-revised)

For any PR introducing observability instrumentation (writers / watchdogs / hooks) AND/OR shipping CI workflow changes:

**Pass criterion**: the PR's test matrix includes ≥1 test that exercises the instrumentation via subprocess (`subprocess.run`) or real-stack frame walk (`sys._getframe()`), not just monkeypatched fakes. If absent, **self-est cap = 0.70** (was 0.75 pre-RETRO-V61-006 addendum 2 · revised 0.75 → 0.70 per Opus 4.7 audit Item b).

**Binding rule (W4 toggle PR · Gate #1 trigger)**: the W4 toggle PR is BOTH instrumentation (flips dogfood pytest from non-blocking to blocking) AND CI workflow change (modifies `.github/workflows/ci.yml`). Combined with the stair-anchor probationary drop 0.87 → 0.85, the binding self-est cap for W4 toggle PR is `min(0.85, 0.70) = 0.70`. The dogfood close review template's commit-message draft self-est must reflect this. **Calendar form "2026-05-11 deadline" deprecated 2026-04-25T17:30** per Opus 4.7 ACCEPT_WITH_COMMENTS 9-gates refactor — see RETRO-V61-006 Addendum 5 + OPS-2026-04-25-001 §7 Gate #1.

**Fail mode** (RETRO-V61-006 calibration): 11 unit tests passed but real-stack repro caught 3 HIGH findings Codex used to verify F1/F2/F3.

### 2.6 CI installation surface ≠ local dev surface (Gap #5)

For any PR that adds a new top-level third-party `import` statement OR removes one:

```bash
# Find all top-level third-party imports in src/ + tests/
grep -rhE "^(import|from) [a-zA-Z][a-zA-Z0-9_]*" src/ tests/ \
  | awk '{print $2}' | awk -F'.' '{print $1}' | sort -u \
  > /tmp/imports.txt

# Diff against pyproject.toml [project].dependencies
grep -A20 "^dependencies = \[" pyproject.toml | head -30 > /tmp/declared.txt
```

**Pass criterion**: every top-level third-party import in `/tmp/imports.txt` (excluding stdlib, first-party `src.*` / `tests.*`) must appear in `pyproject.toml` `[project].dependencies` OR in an `[project.optional-dependencies]` group that the CI install command activates (default: `pip install -e ".[dev]"`).

**Fail mode** (RETRO-V61-006 Gap #5): local dev environments had `numpy` + `jinja2` in global Python / .venv so all tests passed locally; CI's fresh `pip install -e ".[dev]"` had no such fallback → 40 consecutive CI failures with `ModuleNotFoundError`. Tests "passing locally" does NOT certify "tests passing on a clean CI environment".

## 3. Calibration coupling

These checks correspond directly to MP-A through MP-G in RETRO-V61-006:
- §2.1 ↔ MP-A
- §2.2 ↔ MP-B
- §2.3 ↔ implicit (4th recurrence triggers `src/_path_utils.py` extraction)
- §2.4 ↔ MP-G
- §2.5 ↔ MP-C (revised cap 0.75 → 0.70)
- §2.6 ↔ Gap #5 (CI installation surface)

MP-D (test pollution fix), MP-E (cross-track `git add -p` discipline) and MP-F (`pre-commit install` on session start) are operational, not pre-Codex; they live in OPS-2026-04-25-001 §9 + commit-message-tag protocol + `bin/dev-session-init` script.

Gap #6 (artifact emptiness ≠ artifact absence) is a dogfood close review template rule, not pre-Codex; it lives in `.planning/dogfood/dogfood_close_review_template.md` Step 1 (verify `ci_warn_pytest.log` shows `<N> passed` BEFORE reading `.jsonl` count). Template renamed from `2026-05-09_review_template.md` 2026-04-25T17:30 per Opus 4.7 9-gates refactor.

## 4. When to run

### 4.1 Per-PR cadence (signal-driven · Opus 4.7 9-gates refactor Gate #7)

**Required**:
- Every risky-class PR (per RETRO-V61-001 baseline + RETRO-V61-006 expansions — see CLAUDE.md "v6.1 自主治理规则 · Codex-per-risky-PR baseline")
- Every 10th merged PR sample 1 non-risky for Codex sweep — drift detection against risk classifier itself

**Skip allowed**:
- Verbatim 5/5 exception rounds (R2+ on already-Codex-reviewed PRs where the fix is literal-Codex-recommendation-mapping ≤20 LOC ≤2 files)
- Doc-only commits

**Calendar form "weekly fallback" deprecated 2026-04-25T17:30** per Opus 4.7 ACCEPT_WITH_COMMENTS 9-gates refactor (RETRO-V61-006 Addendum 5 Gate #7). The "drift detection" purpose of weekly fallback is precisely served by 10-merge sampling and aligns with development cadence rather than wall clock. If 10 PRs take 1 day, sweep daily; if 10 PRs take 1 month, sweep monthly. **Long zero-PR periods → no sweep needed (no surface to drift)**.

## 5. Revision log

| version | date | author | change |
|---|---|---|---|
| v1.0 | 2026-04-25 | Claude Code Opus 4.7 CLI | Initial promotion of MP-A through MP-G from RETRO-V61-006 (W4 prep arc retro). Replaces ad-hoc self-review with explicit checklist. |

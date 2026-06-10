# V72A-FOLLOWUP-1 · Full-suite collection fragility on fresh checkouts (pre-existing)

status: OPEN (found 2026-06-10 during V72.A scaffold verification · NOT caused by V72.A)
severity: P2 (CI masked; bites any fresh worktree / new contributor / clean CI runner)

## Symptom

`pytest tests/` on a FRESH checkout of c4d275d (pristine worktree, zero
modifications, project venv) fails collection of 8 files:

    tests/p4/test_bfs_lowre_wiring.py        tests/p4/test_supersonic_wedge_taskrunner.py
    tests/test_auto_verifier/test_task_runner_integration.py
    tests/test_e2e_mock.py                   tests/test_notion_client.py
    tests/test_task_runner.py                tests/test_task_runner_executor_mode.py
    tests/test_task_runner_trust_gate.py

all with:

    ImportError: cannot import name 'Client' from partially initialized module
    'notion_client' (most likely due to a circular import) (src/notion_client.py)

The same 8 files pass when run directly (`pytest tests/p4/` is green), and the
full tree collects clean in the long-lived cfd-audit-merge worktree (local
accumulated state masks it). Reproduction evidence (2026-06-10):
pristine `git worktree add --detach /tmp/cfd-pristine-c4d275d c4d275d` →
`pytest --collect-only -q tests/` → "1988 tests collected, 8 errors".

## Root cause

`tests/test_skill_index/conftest.py` and `tests/test_notion_sync/conftest.py`
both do `sys.path.insert(0, str(REPO_ROOT / "src"))` so their tests can import
src modules as TOP-LEVEL names. With `src/` on sys.path, the stdlib import
machinery resolves the absolute `from notion_client import Client` inside
`src/notion_client.py` (task_runner dependency) to `src/notion_client.py`
ITSELF (shadowing the PyPI `notion-client` package) → circular self-import.
Deterministic minimal repro in ANY worktree:

    python -c "import sys; sys.path.insert(0,'src'); import src.task_runner"

Three conftests carry the pattern: `tests/test_auto_verifier/conftest.py`,
`tests/test_skill_index/conftest.py`, `tests/test_notion_sync/conftest.py`.

## Why cfd-audit-merge (and only it) is green — PROVEN 2026-06-10

The project venv carries an editable install:
`.venv/lib/python3.13/site-packages/__editable__.cfd_harness_unified-0.1.0.pth`
containing the single line `/Users/Zhuanz/Desktop/cfd-audit-merge/src` — so in
the audit-merge worktree, `SRC_ROOT` is ALREADY in sys.path (at the END, after
site-packages) and the conftests' `if str(SRC_ROOT) not in sys.path` guard
SKIPS the `insert(0)`. PyPI `notion_client` stays unshadowed → green. In every
other checkout the guard misses, `insert(0)` fires, and the shadow bites.
Confirmed both ways: pristine c4d275d worktree reproduces the 8 errors;
audit-merge runs the same files green. DEC-V61-236's "2088 passed" is real but
holds ONLY in the .pth-blessed worktree. Side risk worth noting: the .pth also
means any OTHER checkout's test run has audit-merge's src as a tail-of-path
fallback for top-level imports.

## Why CI never bit

CI runs explicit-include pytest invocations (per DEC-V61-114 pattern), not a
flat `pytest tests/`; the poisoning conftests and the task_runner importers
don't meet in the same process in the wrong order there.

## Proposed fix (own slice; NOT done in V72.A — cross-cutting, needs its own review)

Preferred: remove the `sys.path.insert(0, src)` pattern from the two conftests
and convert their tests to `from src.X import ...` package imports (matches
every other test in the tree). Alternative (weaker): make
`src/notion_client.py` import the PyPI client defensively. The first option
deletes the entire shadowing class; ~2 conftests + a handful of import lines.

## V72.A interim verification protocol (this slice · what was actually run)

The shadow is set-dependent, so sharding does not dodge it outside the blessed
worktree. Protocol used instead (all green 2026-06-10):
  * `pytest tests/p4/` → 111 passed, 2 skipped (38 new dam-break + all wedge/BFS)
  * each of the 8 affected files run as its own invocation → 7 green;
    `tests/test_auto_verifier/test_task_runner_integration.py` fails on ANY
    non-blessed checkout (its own directory's conftest poisons before import —
    deterministic, pre-existing; green in cfd-audit-merge)
  * `lint-imports --config .importlinter` → 5 contracts kept, 0 broken
  * attribution: pristine c4d275d worktree shows the IDENTICAL 8-file error
    set with zero V72.A files present

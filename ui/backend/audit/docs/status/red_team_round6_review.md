# Red Team Round-6 Review — Tier-2 Meta Scan

**Scope:** adversarial re-scan of the Tier-2 batch (F-04 + F-05 + F-06 + F-07 + F-08, original review).
**Author:** test-red-team agent.
**Date:** 2026-05-20.
**Previous round:** `red_team_round5_review.md` (Tier-2/β closed 5 original HIGH).
**Verdict:** FAIL — 1 MEDIUM (live-reproduced) + 1 LOW.

---

## Method

For each Tier-2 fix I asked one adversarial question, then tried to break it on the live tree:

| Original ID | Fix surface                                  | Attack tried                                         |
|-------------|----------------------------------------------|------------------------------------------------------|
| F-04        | `solver.execute` honors `solver_backend`     | manifest without `solver_backend` key                |
| F-05        | `cmd_audit` is structural-only               | does `audit` still write `solver.log` as side effect?|
| F-06        | CLI exit codes for FAIL / BLOCKED            | does `run` on missing case exit non-zero?            |
| F-07        | `--agent` allowlist from `.claude/agents/`   | what if the allowlist source is empty / missing?     |
| F-08        | `--evidence` path validation at PASS time    | does it leak when AGENTS_DIR is gone (F-07 fails)?   |

Of those five, **F-07 broke on the live tree.**

---

## Findings

### R6-F-01 — MEDIUM — `--agent` allowlist fails open when `.claude/agents/` is missing or empty

**File:** `tools/cwos_event.py:60-64`.

```python
known = cwos_agents.known_agent_names(AGENTS_DIR)
if known and args.agent not in known:
    raise SystemExit(
        f"unknown agent '{args.agent}'. Declared agents: {sorted(known)}.\n"
        "To add a new agent, create .claude/agents/<name>.md with YAML frontmatter `name: <name>` first.",
    )
```

The guard is conditioned on `known` being truthy. If `cwos_agents.known_agent_names(AGENTS_DIR)` returns an empty set — either because the directory does not exist, or it exists but contains no `.md` files with a `name:` field — the check is skipped entirely and any string is accepted as `--agent`.

This is a textbook **fail-open** pattern: the trust gate disappears in exactly the conditions where an attacker (or a misconfigured agent) would benefit most. The intent of F-07 was "no event can land with an unrecognized agent name"; the implementation is "no event can land with an unrecognized agent name *unless the allowlist source is missing.*"

**Live reproduction (dir missing):**

```bash
$ mv .claude/agents /tmp/agents-backup-r6
$ PYTHONPATH=src python3 tools/cwos_event.py \
    --agent ghost-of-cfd-r6 \
    --task-id R6-PROBE \
    --status RUNNING \
    --summary "fail-open probe"
{ "time": "...", "agent": "ghost-of-cfd-r6", "task_id": "R6-PROBE", "status": "RUNNING", ... }
exit=0
```

**Live reproduction (dir present but empty):**

```bash
$ mv .claude/agents .claude/agents.bak && mkdir .claude/agents
$ PYTHONPATH=src python3 tools/cwos_event.py \
    --agent ghost-empty-dir \
    --task-id R6-PROBE-C \
    --status RUNNING \
    --summary "empty-dir probe"
{ "time": "...", "agent": "ghost-empty-dir", ... }
exit=0
```

In both cases the event was written to `.cwos/agent_events.jsonl` under an undeclared agent name with exit 0. F-08 still works (evidence path validation is independent), but the integrity of the agent dimension of the audit log is gone.

**Why this matters (project principle 9):** the CWOS event log is the single ledger Red Team uses to decide whether a task is `done`. If an attacker can scrub `.claude/agents/`, they can backfill PASS events under any name, then re-populate the directory — leaving no trace in `git log` of `.claude/agents/` if they revert the deletion.

**Fix sketch (do NOT auto-apply; presented for the next round):**

```python
known = cwos_agents.known_agent_names(AGENTS_DIR)
if not known:
    raise SystemExit(
        f"agent allowlist is empty: no agents declared under {AGENTS_DIR}. "
        "Create at least one .claude/agents/<name>.md with `name:` frontmatter "
        "before writing events. The allowlist cannot fail open."
    )
if args.agent not in known:
    raise SystemExit(...)
```

That is, treat "allowlist source missing" as a hard error (BLOCKED), not as "no enforcement." A negative test should then assert that with `AGENTS_DIR` empty or absent the tool exits non-zero for **every** agent name.

**Severity rationale (MEDIUM not HIGH):** the bypass requires either (a) write access to `.claude/agents/` or (b) running in a fresh checkout that has not yet committed agents. Most real attackers reaching (a) already win, but in CI sandboxes / fresh clones this is a meaningful trust gap. Bumped above LOW because the gate is silently absent — there is no warning, no log line, no "fail-open" header in the event.

---

### R6-F-02 — LOW — `test_cwos_event_accepts_known_agent` writes a SMOKE event to the real `.cwos/agent_events.jsonl`

**File:** `tests/test_red_team_safety.py:711-741`.

```python
def test_cwos_event_accepts_known_agent(repo_root: Path, tmp_path: Path):
    ...
    smoke_id = f"SMOKE-{os.getpid()}-{id(tmp_path)}"
    res = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "cwos_event.py"),
         "--agent", "project-governor",
         "--task-id", smoke_id,
         "--status", "RUNNING",
         "--summary", "test_cwos_event_accepts_known_agent smoke"],
        capture_output=True, text=True, env=env, cwd=str(repo_root),
    )
    try:
        assert res.returncode == 0, ...
    finally:
        # strip SMOKE-... lines from the real log
        ...
```

The test bypasses the `tmp_path` isolation everywhere else in the suite and runs the subprocess against the live repo log. Cleanup is a try/finally string-strip. Risks:

1. **Kill-9 / `pytest --pdb` interruption** between `subprocess.run` and `finally` leaves a `SMOKE-...` event in `.cwos/agent_events.jsonl`. Won't fail tests next run, but pollutes the audit log.
2. **Parallel test runs** (`pytest -n auto`) could race: two SMOKE events with different `os.getpid()` are fine, but the rewrite-the-whole-file cleanup loses one if both finalize simultaneously.
3. **Project principle 14** ("Project truth must live in repo files") suggests the canonical event log should not be touched by tests at all.

**Why LOW:** no live-repro of corruption was attempted (the failure mode is opportunistic), and the test does try to clean up. The shape of the fix is well known — either monkeypatch `EVENTS_PATH` in `cwos_event.py`, or expose it as an env-var override so the test can point at `tmp_path / agent_events.jsonl`. Same pattern already used for `derive_agent_matrix(agents_dir=..., repo_root=...)`.

---

## What I tried that did NOT break

For honesty — these all behave correctly under attack:

- **`solver.execute` without `solver_backend` key in manifest** — returns `BLOCKED` with `reason: unknown_backend`. F-04 holds.
- **`cmd_audit` re-running solver** — even after `rm -rf artifacts/`, `cfdtrust audit` writes geometry/mesh/bc artifacts only; no `solver.log` or `residuals.csv` appears. F-05 holds.
- **`cfdtrust run` on a non-existent case dir** — `ManifestError` → exit 2. F-06 holds.
- **F-08 PASS evidence path validation under F-07 fail-open** — when `.claude/agents/` is restored, F-08 still rejects `phantom.py` and `/etc/hosts` independently. F-08 is not coupled to F-07.
- **Phantom evidence with `--status PASS`** — rejected, exit non-zero, no event written. F-08 holds.
- **Absolute evidence path** — rejected. cwos_paths.path_is_safe_relative correctly blocks `/etc/hosts`.

These are the bright spots from this round.

---

## Cumulative severity trend

| Round                  | CRIT | HIGH | MED | LOW | Total |
|------------------------|------|------|-----|-----|-------|
| 1 (bootstrap)          | 3    | 5    | 6   | 2   | 16    |
| 2 (Tier-1 meta)        | 0    | 1    | 4   | 2   | 7     |
| 3 (T1 fix meta)        | 1    | 1    | 2   | 1   | 5     |
| 4 (R3 batch w/ helper) | 0    | 0    | 0   | 0   | 0     |
| 5 meta                 | 0    | 0    | 3   | 3   | 6     |
| 5 fix (α)              | 0    | 0    | 0   | 0   | 0     |
| Tier-2 (β) self-check  | 0    | 0    | 0   | 0   | 0     |
| **6 (Tier-2 meta)**    | **0**| **0**| **1**| **1**| **2** |

Monotonic decrease since round 3, with the exception of round-5 where extracting `cwos_status` revealed 3 latent MEDIUMs that the old in-place implementation hid. Round-6 is consistent with the trend.

---

## Verdict

**FAIL** on the round-6 meta scan, due to R6-F-01.

R6-F-01 is a real bypass — small attack surface, silent failure mode, but it punctures the F-07 contract under a realistic configuration drift. R6-F-02 is bookkeeping; it does not affect the trust loop.

Tier-2 itself was a correct batch — five HIGH from the original review are closed. R6-F-01 is a *gap in the new code*, not a regression in the old.

---

## Recommended next options for the owner

1. **(α) Fix R6-F-01 only.** Two-line change in `cwos_event.py` (treat empty allowlist as BLOCKED) plus one new negative test. Then re-run meta scan as round-7.
2. **(β) Fix R6-F-01 + R6-F-02.** Same as (α) plus expose `EVENTS_PATH` as env-var override in `cwos_event.py` and rewrite the positive test to use `tmp_path`.
3. **(γ) Accept R6-F-01 as a known limitation, document it in `RISK_REGISTER.md`, move to Tier-3 cleanup (gitignore, ARCHITECTURE.md path alignment).**
4. **(δ) Defer all of the above and start Phase 1 OpenFOAM adapter.** F-04 makes this safe — declaring `solver_backend: openfoam` already BLOCKS until the adapter lands; R6-F-01 does not affect Phase 1's critical path.

My recommendation: **(α)** — fix R6-F-01, ship one negative test, re-scan. Cheap and closes the only live bypass.

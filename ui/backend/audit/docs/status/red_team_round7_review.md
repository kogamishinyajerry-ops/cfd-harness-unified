# Red Team Round-7 Review — α-fix Meta Scan

**Scope:** adversarial re-scan of the round-6 α fix (close R6-F-01: empty allowlist now hard-BLOCKS).
**Author:** test-red-team agent.
**Date:** 2026-05-20.
**Previous round:** `red_team_round6_review.md` (FAIL on R6-F-01 + R6-F-02).
**Verdict:** PASS on R6-F-01 closure, FAIL on overall (2 LOW findings outside R6-F-01 scope).

---

## Method

Attack matrix against the new code surface introduced by α:

| # | Probe                                          | Target                                              | Expected     | Observed     |
|---|------------------------------------------------|-----------------------------------------------------|--------------|--------------|
| 1 | `.claude/agents/` missing                      | new guard in cwos_event.py                          | exit 1, no event | exit 1, no event |
| 2 | `.claude/agents/` empty                        | new guard in cwos_event.py                          | exit 1, no event | exit 1, no event |
| 3 | `.claude/agents/` is a regular FILE (not dir)  | known_agent_names + new guard                       | exit 1, no event | exit 1, no event |
| 4 | `.claude/agents/` is a BROKEN symlink          | known_agent_names + new guard                       | exit 1, no event | exit 1, no event |
| 5 | `.claude/agents/` is a SYMLINK to outside repo | known_agent_names                                   | exit 1 / warning | **exit 0, event written** |
| 6 | `.claude/agents/` has `.md` without `name:`    | parse_frontmatter + known_agent_names + guard       | exit 1, no event | exit 1, no event |
| 7 | Positive: populated allowlist + known agent    | regression check                                    | exit 0, event written | exit 0, event written |

Five out of seven hardened correctly. Probe 5 surfaced a new, narrow finding (below).

The sandbox-repo testing pattern introduced in α was independently audited as part of this scan (probes ran against `/tmp/r7-clean/`, not the real repo). Confirmed:
- script's `REPO_ROOT = Path(__file__).resolve().parent.parent` correctly relocates to the sandbox
- `EVENTS_PATH` and `AGENTS_DIR` follow REPO_ROOT
- real `.cwos/agent_events.jsonl` is never touched by the sandbox subprocess

That isolation is now load-bearing for future tests — worth flagging as a project asset.

---

## Findings

### R7-F-01 — LOW — `.claude/agents/` can be a symlink to outside the repo, expanding the allowlist invisibly to git

**File:** `tools/cwos_agents.py:48-55` (root cause), exposed via `tools/cwos_event.py:60-75` (the new guard) and `tools/cwos_render_dashboard.py:88` (Agent Matrix).

```python
def known_agent_names(agents_dir: Path) -> Set[str]:
    out: Set[str] = set()
    if not agents_dir.exists():
        return out
    for p in sorted(agents_dir.glob("*.md")):
        ...
```

`Path.exists()` follows symlinks. `.glob("*.md")` on a symlinked directory lists the target's contents. So if `.claude/agents` is a symlink pointing at, say, `/tmp/whatever`, the script reads agent declarations from `/tmp/whatever/*.md` — silently from git's perspective.

**Live reproduction:**

```bash
$ ln -s /tmp/r7-symlink-target /tmp/r7-clean/.claude/agents
$ cat /tmp/r7-symlink-target/sneaky.md
---
name: sneaky-agent
role: smuggled
---
$ PYTHONPATH=src python3 tools/cwos_event.py \
    --agent sneaky-agent --task-id R7-SYMLINK --status RUNNING --summary "..."
{ "agent": "sneaky-agent", "task_id": "R7-SYMLINK", ... }
exit=0
```

The event landed under `sneaky-agent` — an identity that exists only in `/tmp/`, not in any committed file.

**Severity rationale — LOW (not MED):**

1. **Attacker already needs write access to `.claude/`** to replace the dir with a symlink. Anyone with that access can equally well drop a real `.md` file with whatever `name:` they want — symlinks aren't strictly necessary to forge agent identity.
2. **Defense-in-depth is intact:** `tools/cwos_render_dashboard.py:80-88` builds the cockpit Agent Matrix from the same `AGENTS_DIR`. A symlink-smuggled `sneaky-agent` would appear in the cockpit's Agent Matrix on the next refresh — visible in `docs/status/COCKPIT.md` and PR-diffable. So the smuggling is not silent end-to-end; it's only silent to git's view of `.claude/agents/`.
3. **Affects identity-of-record, not trust gates:** F-08 (evidence path validation) still operates correctly under R7-F-01 — phantom evidence is still rejected regardless of who claims to author the event.

**Fix sketch (do NOT auto-apply this round):**

Add to `cwos_agents.known_agent_names`:

```python
if not agents_dir.exists():
    return out
if agents_dir.is_symlink():
    # The allowlist directory must be a real directory tracked by git,
    # not a symlink pointing at an arbitrary location.
    return out  # caller's empty-allowlist guard will BLOCK
for p in sorted(agents_dir.glob("*.md")):
    ...
```

Treating "directory is a symlink" identically to "directory is empty" lets the existing R6-F-01 guard in `cwos_event.py` handle it — no second error-handling branch needed. A negative test then asserts that symlinking `.claude/agents` to a populated outside dir produces exit 1.

Subtlety: legitimate use cases for symlinking `.claude/agents` exist (e.g., monorepo with shared agent registry). If such a case ever lands, a `CWOS_AGENTS_DIR_ALLOW_SYMLINK=1` opt-in env-var is the right escape hatch. Not needed today.

---

### R7-F-02 — LOW (informational) — error message leaks the absolute path of `AGENTS_DIR`

**File:** `tools/cwos_event.py:67-72`.

```python
raise SystemExit(
    f"agent allowlist is empty: no agents declared under {AGENTS_DIR}. "
    ...
)
```

The error includes the full absolute path:

```
agent allowlist is empty: no agents declared under /Users/Zhuanz/Desktop/AI-CFD-V2/.claude/agents.
```

For Phase 0 local-dev this is fine. If the project ever ships a hosted demo of the CLI (`cfdtrust` exposed as a service or in CI logs), the path could leak user/installation context. Fix would be `AGENTS_DIR.relative_to(REPO_ROOT)` when REPO_ROOT is known, with `try/except ValueError` fallback to the absolute path.

**Severity rationale:** informational. Not a security boundary in the current deployment context (single-user local CLI). Worth one line in `RISK_REGISTER.md` if/when we move toward hosted runs.

---

## What I tried that did NOT break

- **AGENTS_DIR is a regular file** — `known_agent_names` returns empty set (`.glob("*.md")` on a file path yields nothing); guard BLOCKs.
- **AGENTS_DIR is a broken symlink** — `Path.exists()` returns False (resolves through the symlink); guard BLOCKs with the same allowlist-empty message.
- **AGENTS_DIR has one `.md` with no `name:` field** — `parse_frontmatter` returns `{}`, `name` is None, agent skipped; guard BLOCKs.
- **F-08 still rejects phantom evidence in sandbox** — confirmed: with a legit agent declared and `--status PASS --evidence "phantom.py"`, the script rejects with exit 1 before any event is written.
- **Sandbox test pattern leaks nothing** — verified by running all 3 new tests + a deliberate kill-9 simulation: real `.cwos/agent_events.jsonl` unchanged.

The α fix closes R6-F-01 completely on the documented attack surface. R7-F-01 is a NEW, related-but-narrower vector (symlink of the directory itself, not bypass of the allowlist semantics). They are separable.

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
| 6 (Tier-2 meta)        | 0    | 0    | 1   | 1   | 2     |
| 6 fix (α)              | 0    | 0    | 0   | 0   | 0     |
| **7 (α meta)**         | **0**| **0**| **0**| **2**| **2** |

Severity continues monotonically downward. First round to surface ZERO MEDIUM-or-higher findings. Both R7 findings are LOW (one with an explicit cockpit defense-in-depth mitigation).

---

## Verdict

**FAIL** on the round-7 meta scan as a whole, but **PASS** on the question that triggered round-7: *did α actually close R6-F-01?*

α did. R6-F-01 is closed on every documented attack surface and on three additional adjacent surfaces (file-as-dir, broken symlink, missing-name `.md`).

R7-F-01 is a small NEW finding tangent to R6-F-01 — it is about `.claude/agents/` *as a path*, not about the allowlist semantics. The cockpit Agent Matrix provides defense-in-depth (any smuggled agent appears visibly).

The sandbox-repo test pattern introduced in α is solid and reusable. Recommend it as the default for any future test that involves mutating `.claude/` or `.cwos/`.

---

## Recommended next options for the owner

1. **(α)** Fix R7-F-01 only — 2-line change to `cwos_agents.known_agent_names` rejecting symlinked dirs + 1 negative test. ~10 min.
2. **(β)** Fix R7-F-01 + R6-F-02 — also migrate `test_cwos_event_accepts_known_agent` to the sandbox pattern. ~25 min. **Recommended** — cleans up both LOW from R7 and the deferred LOW from R6 in one batch.
3. **(γ)** Document R7-F-01 + R7-F-02 in `RISK_REGISTER.md` and move to Tier-3 cleanup. ~30 min.
4. **(δ)** Start Phase 1 OpenFOAM adapter. R7-F-01 does not block Phase 1's critical path; cockpit visibility provides adequate safety for solo-dev use.

My recommendation: **(β)** — combined batch is small and finally drains the lingering LOW queue. After (β), the next meta scan is highly likely to be the first zero-finding round, which is the natural moment to start Phase 1.

# Red Team Round-8 Review — β-fix Meta Scan

**Scope:** adversarial re-scan of the round-7 β batch (close R7-F-01 directory-symlink vector + delete R6-F-02 legacy test).
**Author:** test-red-team agent.
**Date:** 2026-05-20.
**Previous round:** `red_team_round7_review.md` (FAIL on overall, 2 LOW).
**Verdict:** PASS on β's stated intent, FAIL on overall (2 LOW, both attacking the same symlink-class vector at a different depth).

---

## Method

Six probes against the new code surface introduced by β + the deletion of the legacy R6-F-02 test:

| # | Probe                                                                                        | Expected         | Observed          |
|---|----------------------------------------------------------------------------------------------|------------------|-------------------|
| 1 | `.claude/agents/` is real dir; one `.md` file inside is a SYMLINK to outside repo            | exit 1, no event | **exit 0, event written** |
| 2 | `.claude/agents/` is a symlink to a symlink to a real dir (chain)                            | exit 1, no event | exit 1, no event  |
| 3 | Cockpit `derive_agent_matrix` consistency with the new is_symlink guard                      | filtered out     | **listed in Agent Matrix** |
| 4 | Implicit smoke coverage of "all 13 real agent files parse" after deleting legacy test        | still tested     | ✓ covered by `test_frontmatter_works_on_all_real_agent_files` |
| 5 | Hardlink to a directory (defeat is_symlink check)                                            | OS refuses       | OS refuses (Linux/macOS reject hardlinks to dirs) |
| 6 | Positive control via sandbox-α pattern (regression check)                                    | exit 0, event in sandbox log | exit 0, event in sandbox log |

Two probes (1 and 3) revealed the same root cause: the β fix and the cockpit's enumeration are not unified.

---

## Findings

### R8-F-01 — LOW — file-level `.md` symlink bypass survives the β fix

**File:** `tools/cwos_agents.py:48-58` (specifically the loop body after the `is_symlink()` guard).

```python
def known_agent_names(agents_dir: Path) -> Set[str]:
    out: Set[str] = set()
    if not agents_dir.exists():
        return out
    if agents_dir.is_symlink():      # β fix — guards the DIRECTORY itself
        return out
    for p in sorted(agents_dir.glob("*.md")):
        fm = parse_frontmatter(p.read_text())  # ← p may itself be a symlink
        name = fm.get("name")
        if isinstance(name, str) and name.strip():
            out.add(name.strip())
    return out
```

The β fix only checks whether `agents_dir` is a symlink. If the directory is a real directory but contains a symlinked `.md` file pointing at content outside the repo, `Path.glob` happily returns it and `Path.read_text` follows the symlink. Same smuggling shape as R7-F-01, one level deeper in the tree.

**Live reproduction:**

```bash
$ mkdir /tmp/r8-out
$ cat > /tmp/r8-out/sneaky.md <<'EOF'
---
name: file-level-sneaky
---
EOF
$ ln -s /tmp/r8-out/sneaky.md /tmp/r8-clean/.claude/agents/sneaky.md
$ test -L /tmp/r8-clean/.claude/agents       # → no (dir is real)
$ test -L /tmp/r8-clean/.claude/agents/sneaky.md  # → yes (file is symlink)
$ PYTHONPATH=src python3 tools/cwos_event.py \
    --agent file-level-sneaky --task-id R8-P1 --status RUNNING ...
{ "agent": "file-level-sneaky", "task_id": "R8-P1", ... }
exit=0
```

The event landed under a smuggled identity. The β fix did not catch this — it was scoped to the directory's `is_symlink()`, not to each entry inside.

**Severity rationale — LOW (same logic as R7-F-01):**

1. Attacker needs write access to `.claude/agents/`. Once they have that, they can drop a real `.md` with any `name:` value — symlinks aren't necessary to forge identity.
2. Defense-in-depth: the smuggled agent appears in the cockpit's Agent Matrix on next refresh (see R8-F-02 — actually a different finding, but the visibility coincidentally still helps here).
3. F-08 evidence path validation operates correctly regardless of who claims authorship.

**Fix sketch (do NOT auto-apply this round):**

Two reasonable shapes:

```python
# Shape A: skip individual symlinked .md files
for p in sorted(agents_dir.glob("*.md")):
    if p.is_symlink():
        continue
    fm = parse_frontmatter(p.read_text())
    ...
```

```python
# Shape B: reject the entire directory if any .md is a symlink (stricter)
for p in sorted(agents_dir.glob("*.md")):
    if p.is_symlink():
        return set()  # collapse to empty → caller BLOCKs
    ...
```

Shape A is closer to "principle of least surprise" — a legitimate symlinked file gets silently ignored, the rest of the directory still works. Shape B is harsher but signals louder: the WHOLE allowlist is poisoned if any single entry is symlinked. For Phase 0 with no legitimate symlink use case, Shape A suffices and matches the existing "missing-name silently skipped" pattern in the same function.

### R8-F-02 — LOW (mechanism debt) — cockpit Agent Matrix enumerates `.md` files independently of `known_agent_names`, so any allowlist fix must be applied in TWO places

**Files:**
- `tools/cwos_agents.py:48-58` — `known_agent_names`, used by `cwos_event.py`
- `tools/cwos_render_dashboard.py:79-93` — `derive_agent_matrix`, used by the cockpit

Both functions independently call `agents_dir.glob("*.md")` and parse frontmatter. The β fix added `is_symlink()` to one (`known_agent_names`) but not the other. Result: a smuggled agent that `cwos_event.py` BLOCKs (after β) still appears as a row in `COCKPIT.md`'s Agent Matrix.

**Live demonstration:**

```bash
# .claude/agents/legit.md (real)         — name: legit-agent
# .claude/agents/sneak.md → /tmp/.../    — name: cockpit-sneaky (symlink)

>>> derive_agent_matrix(agents_dir=Path('.claude/agents'), repo_root=Path('.'))
[
  ('legit-agent', 'real local agent', '.claude/agents/legit.md'),
  ('cockpit-sneaky', 'smuggled via file-level symlink', '.claude/agents/sneak.md'),
]
```

The smuggled row appears in the cockpit. Worse, this same code path would also list a directory-symlink smuggled agent (R7-F-01 — closed in β only for `cwos_event.py`, NOT for the cockpit).

**The round-4 "pattern break" principle is being violated here.** The whole point of `tools/cwos_paths.py` and `tools/cwos_agents.py` was that two places must not independently re-implement a safety-relevant predicate. The β fix put `is_symlink()` in only one of them.

**Severity rationale — LOW (mechanism, not exploit):**

- This is not an additional exploit beyond R8-F-01 — it is the SUBSTRATE of R8-F-01 and the residue of R7-F-01.
- The cockpit listing a smuggled agent is the "defense-in-depth visibility" I cited as a mitigation for R7-F-01 (round-7 review). That mitigation is now both a feature AND a bug:
  - Feature: smuggled agents are visible in the cockpit, not hidden.
  - Bug: the cockpit accepts them silently, no warning row, no `[SYMLINK — REJECTED]` annotation.
- Long-term debt: any future safety check on `cwos_agents.known_agent_names` will need to be mirrored in `derive_agent_matrix` or it diverges.

**Fix sketch (one-round-from-now):**

The right move is to make `derive_agent_matrix` use `cwos_agents.known_agent_names()` as the source of names, then read `description:` per name from the corresponding file (still using `parse_frontmatter`, still rejecting symlinks via Shape A from R8-F-01). That gives:

- single source of truth for "which agents are real"
- the cockpit, the event writer, and the test suite all observe the same set
- a future safety check (e.g. "agent file must be checked into git") only needs to land in `known_agent_names`

For this round we just diagnose. The fix to R8-F-01 (Shape A) naturally closes the agent-enumeration side of R8-F-02; the cockpit-side unification can land at the same time or one round later.

---

## What I tried that did NOT break

- **Symlink chain** (`.claude/agents → /tmp/A → /tmp/B`): `is_symlink()` returns True at the first hop; BLOCKs correctly. β fix is robust to indirection.
- **Hardlink to directory**: Linux/macOS kernels refuse hardlinks to directories (`ln /tmp/dir /tmp/foo` returns "Operation not permitted"). Not a viable attack vector. Skip.
- **Deleting the legacy `test_cwos_event_accepts_known_agent`**: confirmed that `test_frontmatter_works_on_all_real_agent_files` (line 266) still tests parsing of all 13 real agent files end-to-end. No regression coverage hole.
- **Positive-control regression via sandbox-α pattern**: `test_cwos_event_accepts_known_agent_in_sandbox` continues to pass — legitimate flow not affected by the new `is_symlink` guard.
- **Cockpit Bright Spots, Trust Loop Status, Decisions Needed**: none of these enumerate the agents/ directory. R8-F-02 is scoped to the Agent Matrix.

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
| 7 (α meta)             | 0    | 0    | 0   | 2   | 2     |
| 7 fix (β)              | 0    | 0    | 0   | 0   | 0     |
| **8 (β meta)**         | **0**| **0**| **0**| **2**| **2** |

Severity ceiling still LOW for the second consecutive non-zero round. Both R8 findings live in the same code surface (`cwos_agents` ↔ `derive_agent_matrix`), suggesting one combined fix closes both. Still no MED/HIGH/CRITICAL.

---

## Verdict

**FAIL** on the round-8 meta scan overall.

**PASS** on β's stated intent: the directory-level symlink smuggling vector (R7-F-01) is closed in `cwos_event.py`, and the residue-risk legacy test (R6-F-02) is gone. Both R8 findings are tangential — same class of vector at a different depth (file inside dir vs the dir itself) plus the unification debt that the β fix did not collapse.

The symlink-class vector is now well-mapped: directory-level (closed), chain (closed), file-level (open as R8-F-01), agent-matrix-listing-anything-glob-returns (open as R8-F-02). One round of fixes closes the remaining surface.

---

## Recommended next options for the owner

1. **(α)** Fix R8-F-01 (Shape A) only — 2-line change in `known_agent_names` to skip symlinked `.md` files + 1 negative test. ~10 min.
2. **(β)** Fix R8-F-01 + R8-F-02 — Shape A plus unify `derive_agent_matrix` to use `known_agent_names` as its identity source, description lookup per name. ~25 min. **Recommended** — drains the entire symlink-class vector AND restores the round-4 single-source-of-truth pattern for agent enumeration.
3. **(γ)** Document R8-F-01 + R8-F-02 + R7-F-02 in `RISK_REGISTER.md` as known LOWs and move to Tier-3 cleanup. ~30 min.
4. **(δ)** Start Phase 1 OpenFOAM adapter. None of the LOW findings block Phase 1; cockpit visibility provides adequate safety for solo-dev use.

My recommendation: **(β)** — for the same reason the round-4 cwos_paths.py extraction was a turning point. Centralizing the agent-enumeration code path means the next time we add a safety predicate, we add it in one place, not two. After (β) the next meta scan is a strong candidate for the first zero-finding round.

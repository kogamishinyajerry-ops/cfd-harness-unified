---
note_id: NOTE-2026-04-26-attribution-collision
title: Concurrent-session `git add -A` collision mitigation playbook
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-26
authored_under: P2-T1.b session close
incident_count: 2 (DEC-V61-074 P2-T1.a R2 @ 20afaaf · DEC-V61-074 P2-T1.b.1 @ f599129)
severity: governance hygiene · audit-trail correctness
status: forward-looking · mitigation patterns documented for next sessions
---

# Concurrent-session `git add -A` collision mitigation playbook

## Why this note exists

Two governance incidents on DEC-V61-074 had the **same root cause**:
this session's `git add <specific-files>` was followed by another
concurrent session's `git add -A` running between this session's
stage-and-commit, capturing this session's staged files into the
parallel session's commit.

| Incident | Commit (misaligned) | Stolen content | Date |
| --- | --- | --- | --- |
| P2-T1.a R2 | `20afaaf` (parallel session's "land Opus Gate authority verdict") | StrEnum + RunReport hardening + fallback test fix | 2026-04-26 (T1.a session) |
| P2-T1.b.1 | `f599129` (parallel session's "DEC-V61-085 PROPOSED synced") | manifest tagging + spec-derived contract_hash + 8 tests | 2026-04-26 (T1.b session) |

In both cases:
- Functional state is correct (the right code landed in tree)
- Attribution is misaligned (commit message titled X, content is mostly Y)
- The DEC frontmatter / closure addendum documents the misalignment
  for audit-trail integrity

## Why the brief's rule is necessary but insufficient

The session brief explicitly bans `git add -A` in this session
(specific filenames only). That binds **this** session — but **not**
the parallel `claude-opus47-app` session, which still runs
`git add -A` at its own discretion. So the rule prevents *this
session* from sweeping *other* work, but does not prevent *other
sessions* from sweeping *this work*.

## Mitigations (next session must adopt at least one)

### Mitigation A · Single-tool-call stage+commit (lowest friction)

Combine `git add <specific>` and `git commit -m "..."` into ONE
Bash tool call. The shell-level atomicity makes the window between
stage and commit essentially zero — too small for a parallel
session's `git add -A` to interleave.

```bash
git add src/foo.py tests/test_foo.py && git commit -m "..." 2>&1 | tail -5
```

**Status**: T1.b.2 + T1.b.3 + T1.b.4 used this pattern. All three
landed with clean attribution (commits `69c0ed6`, `c7ede01`,
`2a5e9c4`).

**Caveat**: doesn't help if the commit message is large and authored
across several iterations.

### Mitigation B · `git stash` barrier (heavier, full isolation)

Before `git add`, push everything else to a stash so the parallel
session's `git add -A` finds nothing to sweep:

```bash
git stash push -u -m "barrier-pre-add"        # push untracked + unstaged
git add src/foo.py tests/test_foo.py
git commit -m "..."
git stash pop                                  # restore other work
```

**Status**: not used in this session. Adds 2 commands and a small
restore failure mode if commit fails.

### Mitigation C · Heredoc commit message in tempfile (avoid shell parse glitches)

Long heredoc commit messages occasionally trip up Mitigation A
(the shell parsing window is wider than expected). Pattern from this
session's T1.b.4 attempt that initially failed:

```bash
# Write message to file first
cat > /tmp/commit_msg.txt <<'EOF'
... long message ...
EOF

# Then atomic stage+commit
git add <files> && git commit -F /tmp/commit_msg.txt 2>&1 | tail -5
```

**Status**: T1.b.4 used this pattern after the heredoc-in-shell
attempt failed. Worked cleanly.

### Mitigation D (future) · Git pre-commit hook validating commit content matches subject line

Most expensive. A pre-commit hook that parses the commit subject and
asserts the diff's primary file paths match the subject's stated
scope. Catches incidents at commit time rather than via post-hoc
forensics. **Not in this session's scope.**

## Default for next session

Use Mitigation A by default. Reach for B if:
- Commit involves trust-core 5 files (signed-manifest path)
- Multiple `claude-opus47-app` Notion-sync commits expected
  during the same window
- Commit message authoring is iterative

Use Mitigation C when commit message is >50 lines.

## Acknowledgement of remaining risk

Even with all mitigations, a sufficiently coincident `git add -A`
during a >0-millisecond stage+commit window can still steal staged
content. The mitigations reduce the window, not eliminate it. If
attribution misalignment recurs **a third time** on the same
session-pair pattern, escalate to:

- Direct conversation with the parallel session's owner (often the
  user, who runs both Claude instances) to coordinate window
  blackouts
- A scripted lock file (`.git/concurrent-session.lock`) that both
  sessions check before any `git add`
- Forge `claude-opus47-app`'s session brief to ban `git add -A` too

## Cross-references

- DEC-V61-074 frontmatter: T1.a R2 attribution note (line ~17)
- DEC-V61-074 closure addendum: T1.b.1 attribution note section
- T1.b.4 closure commit `2a5e9c4`: addendum citation to this note's
  recommendation list

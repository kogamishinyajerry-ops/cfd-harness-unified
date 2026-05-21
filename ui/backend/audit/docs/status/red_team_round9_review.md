# Red Team Round-9 Review — SSOT-fix Meta Scan

**Scope:** adversarial re-scan of the round-8 β SSOT extraction (`_safe_md_files` + `declared_agents` + cockpit delegation).
**Author:** test-red-team agent.
**Date:** 2026-05-20.
**Previous round:** `red_team_round8_review.md` (FAIL, 2 LOW).
**Verdict:** PASS on β's stated intent, FAIL on overall (3 LOW — all polish/debt, none exploit).

---

## Method

Probed three surfaces:

1. **Behavior changes from old → new code path** for the Agent Matrix (8 layouts: empty desc, no desc, int desc, no name, int name, list name, in-repo symlink, real `.claude/agents/`)
2. **Cross-consistency invariant** (`matrix_names == allowlist_names`) on each layout
3. **Vestigial code surface** — what callers of the old paths still exist

Cross-consistency held on every probed layout (8/8). The SSOT promise is intact. Findings below are behavior shifts that don't break security but worth recording.

---

## Findings

### R9-F-01 — LOW — empty-string `description:` no longer falls back to placeholder

**File:** `tools/cwos_agents.py:declared_agents`.

```python
desc = fm.get("description")
if desc is None:
    desc = "(no description in frontmatter)"
elif not isinstance(desc, str):
    desc = str(desc)
```

The OLD `derive_agent_matrix` did `fm.get("description") or "(no description in frontmatter)"` — any falsy value (including `""`) triggered the fallback. The NEW logic only falls back on `None`. An agent file with `description: ""` now produces an empty cell in the cockpit's Agent Matrix instead of the placeholder.

**Live demo:**

```
Agent file:    description: ""
Old behavior:  "(no description in frontmatter)"
New behavior:  "" (empty cell)
```

**Severity LOW — cosmetic:** the cockpit is rendered to humans who can see an empty cell and treat it as a missing-description signal anyway. No security boundary. Fix is one line (`if not desc:` instead of `if desc is None:`), but `not desc` would also collapse description `False` or `0` which is unlikely-but-possible.

### R9-F-02 — LOW — in-repo `.md` symlinks are filtered, removing a degree of flexibility

**File:** `tools/cwos_agents.py:_safe_md_files`.

```python
for p in sorted(agents_dir.glob("*.md")):
    if p.is_symlink():
        continue
    out.append(p)
```

`is_symlink()` doesn't care whether the symlink target is inside or outside the repo. A legitimate refactoring move — e.g., `agents/v2-backend.md → agents/v1-backend.md` for backward-compat aliasing during a rename — would be silently filtered out.

**Live demo:**

```
.claude/agents/real.md         (file)        → ('real-agent', ..., '.claude/agents/real.md')
.claude/agents/inner_link.md   (→ real.md)   → NOT listed
```

Both `cwos_event.py` and the cockpit Agent Matrix observe the filtered set, so they stay consistent (the SSOT promise holds). But the project has no escape hatch yet.

**Severity LOW:** no current Phase 0 use case for in-repo `.md` symlinks; the docstring already mentions the `CWOS_AGENTS_DIR_ALLOW_SYMLINK=1` opt-in for the directory case. The same opt-in could later extend to per-file symlinks if/when a rename-aliasing need arises. Mechanism debt, not exploit.

### R9-F-03 — LOW (mechanism debt) — vestigial `_parse_frontmatter` in `cwos_render_dashboard.py`

**File:** `tools/cwos_render_dashboard.py:67-76`.

After β `derive_agent_matrix` delegates to `cwos_agents.declared_agents()`, the module-private `_parse_frontmatter` is no longer called from production code. The only callers are tests (4 references in `tests/test_red_team_safety.py:229-273`).

This creates a subtle audit-confusion vector: a future maintainer reads `cwos_render_dashboard.py`, sees `_parse_frontmatter`, assumes it powers the cockpit, and may unknowingly diverge it from `cwos_agents.parse_frontmatter`. The same shape of debt R8-F-02 just collapsed at the agent-enumeration layer reappears at the parse-frontmatter layer.

**Severity LOW — debt, not exploit:**
- The two parsers have slightly different semantics (`cwos_render_dashboard._parse_frontmatter` coerces every value to `str`; `cwos_agents.parse_frontmatter` keeps YAML-native types). Production now uses the YAML-native path; tests verify the str-coerce path. They could diverge silently.
- Fix: delete `cwos_render_dashboard._parse_frontmatter`; migrate the 4 test references to `cwos_agents.parse_frontmatter` with explicit assertions about value types. Or: hoist the str-coerce as a tested helper inside `cwos_agents` if it's actually needed.

---

## What I tried that did NOT break

- **Cross-consistency (`derive_agent_matrix` names == `known_agent_names`)**: holds on all 8 layouts probed (empty desc, no desc, int desc, no name, int name `12345`, list name `[foo, bar]`, in-repo symlink, real `.claude/agents/`). SSOT promise verified.
- **All 13 real `.claude/agents/*.md` files**: resolve through `declared_agents()` with correct names and description lengths 111-190 chars. Real-surface contract preserved.
- **Missing `name:` field**: now correctly filters out (was previously falling back to `p.stem` as name in the old `derive_agent_matrix`). Improvement: a file without a `name:` should not be claiming any agent identity. Test `test_frontmatter_works_on_all_real_agent_files` (line 266) already asserts `name:` is present on all real files, so no regression.
- **Non-string `name:` (int, list, dict)**: now correctly filters out. Improvement over the old cockpit `_parse_frontmatter` which silently coerced ints to strings — that path could have masked typos like `name: 2026 (intended as v2026 codename)`.
- **`_safe_md_files` chokepoint**: directory-symlink (R7-F-01), per-file symlink (R8-F-01), missing dir all collapse to `[]` cleanly. The single shared guard surface is the strongest part of the round-8 fix.

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
| 8 (β meta)             | 0    | 0    | 0   | 2   | 2     |
| 8 fix (β SSOT)         | 0    | 0    | 0   | 0   | 0     |
| **9 (β SSOT meta)**    | **0**| **0**| **0**| **3**| **3** |

Severity ceiling LOW for the third consecutive non-zero round. **All R9 findings are polish or mechanism debt — none constitute a security boundary failure.** R9-F-01 is cosmetic (empty cells render where placeholder would have). R9-F-02 is debt (an opt-in escape hatch the project doesn't need yet). R9-F-03 is debt (vestigial parser that production no longer uses).

There is no exploitable bypass in the round-8 β code.

---

## Pattern observation (for the project memory)

Each fix in rounds 5-8 surfaced narrower issues in the next meta scan:

```
Round 6: MEDIUM in cwos_event allowlist (fail-open semantics)
Round 7: LOW in cwos_agents (dir-symlink) + LOW (path leak)
Round 8: LOW in cwos_agents (per-file symlink) + LOW (cockpit SSOT debt)
Round 9: LOW (cosmetic) + LOW (in-repo symlink flexibility) + LOW (vestigial parser)
```

The findings are converging on **stylistic / debt / cosmetic** rather than **exploitable / semantic**. This is the natural shape of a hardened code surface — the remaining noise is the noise of subjective preferences, not the noise of bugs.

The trust harness scaffold has reached the point where additional adversarial rounds yield diminishing security returns. Phase 0's Definition of Done ("the trust loop can be invoked end-to-end with mocked solver clearly labeled") has been met. The natural next step is Phase 1 (`src/cfdtrust/backends/openfoam.py`), with the remaining LOWs logged in `RISK_REGISTER.md` as known polish items.

---

## Verdict

**PASS** on β's stated intent (SSOT extraction, both R8 findings closed).

**FAIL** on overall (3 new LOWs) — but all three findings are polish/debt, not exploit. R9 is the first round whose findings would not block Phase 1.

---

## Recommended next options for the owner

1. **(α)** Fix R9-F-03 only — delete vestigial `_parse_frontmatter` in `cwos_render_dashboard.py`, migrate 4 test references to `cwos_agents.parse_frontmatter`. ~10 min.
2. **(β)** Fix R9-F-01 + R9-F-03 — also restore empty-string description fallback. ~15 min.
3. **(γ)** Log all 4 outstanding LOWs (R7-F-02, R9-F-01, R9-F-02, R9-F-03) in `RISK_REGISTER.md` as known items, declare scaffold-hardening DONE, and start Phase 1. **Recommended** — the marginal return of round-10 hardening is low; Phase 1 OpenFOAM adapter is the real next-wedge work.
4. **(δ)** Tier-3 cleanup first (gitignore, ARCHITECTURE.md path alignment), then start Phase 1.

My recommendation: **(γ)**. Round 9 is the natural exit point from the red-team / fix loop. Three consecutive rounds with severity ceiling at LOW + findings converging on debt rather than exploit = the harness is hardened enough for the next phase. Starting Phase 1 with a clean baseline and explicit-known-debts is more useful than chasing the next LOW.

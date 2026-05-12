# PLAN.md `passes` column · N2+ task tables (v2.3 · DEC-V61-199)

> Established by **DEC-V61-199 Rule 2** (Anthropic agent canon adoption, 2026-05-12).
> Source: Anthropic *Effective harnesses for long-running agents* (2025).
> Applies from **N2 onwards**. N1.x and earlier phases are not retroactively refactored.

## The rule

Every task row in a PLAN.md task table must satisfy **both** conditions before the task counts as done:

1. `status: COMPLETED` — implementation committed
2. `passes: true` — E2E gate cleared

`passes` flips to `true` **only after** one of:

- E2E smoke (`scripts/smoke/dogfood_loop.py` or phase-specific equivalent) executed clean
- `pytest` suite covering this task's surface ran green
- Human verification recorded (e.g., browser walkthrough for UI; manifest comparison for backend)

`status: COMPLETED` alone is **not sufficient**. A task that compiled and was committed but was never end-to-end exercised stays at `passes: false`.

## Why

Root-cause analysis of the N1.1 22-round Codex review chain (RETRO-V61-N1.1, DEC-V61-133 driver) surfaced multiple contributors. One of them: the absence of a hard E2E gate between "I edited the file" and "the feature works end-to-end through the actual entry point". Reviewers caught accessor-class defects in static review, but runtime-emergent defects only showed up in live runs (RETRO-V61-053 addendum, "post-R3 defect" pattern).

The `passes` column is the **minimum prevention mechanism**: it forces the author to articulate which observable signal demonstrates end-to-end working before declaring done. It does **not** replace Codex review; it complements it by surfacing the gap Codex cannot reach (static review of code paths that look correct but degrade under real conditions).

## Format

```markdown
| # | Task | status | passes | verification |
|---|------|--------|--------|--------------|
| 1 | Wire BCSetupError translation for STL patches | COMPLETED | true | pytest test_bc_setup_from_stl_patches.py::test_stl_translation green |
| 2 | Add operator endpoint /admin/promote | COMPLETED | false | E2E smoke not yet run — depends on task 5 |
| 3 | Refactor session storage to file-based | COMPLETED | true | manual: signed out / signed back in / artifact present |
```

The `verification` column is mandatory when `passes: true` — it is the single sentence that future-you (or a reviewer) reads to know **what concrete check produced the green**.

## What `passes: false` permits

A task at `status: COMPLETED · passes: false` may be merged to the working branch (code is in the repo, dependencies can build on top) but **may not be cited** as evidence of phase completion. Phase verifier (`gsd-verifier` agent or human gate) reads the `passes` column and refuses to close a phase that has any `passes: false` rows.

If a task cannot reach `passes: true` because the verification path itself is not yet built (e.g., E2E harness is task 5 and this is task 3), the row carries a `blocked_by: #5` annotation in the verification column. Phase close still refuses; the dependency must be resolved.

## Anti-scope

- **No new artifact**. The `passes` column lives inside the existing PLAN.md task table. Anthropic's harness paper uses a separate `feature_list.json`; we deliberately do not add that — PLAN.md already structures task state, we add a column not a file.
- **No retroactive refactor**. N1.x phase PLAN.md files do not get back-edited. Audit those phases via RETRO docs, not via column rewrites.
- **No JSON / schema validation tooling**. The column is read by humans (and `gsd-verifier`). No CI check enforces it; the enforcement is reviewer-driven.

## When `passes` is irrelevant

Single-task spike-class work (≤30 LOC + 1 test per v2.3 spike-class definition) bypasses the column entirely — there is no PLAN.md table to begin with. The commit message's `confidence:<h/m/l>` tag is the equivalent honesty signal.

## Failure modes to watch

1. **passes: true rubber-stamping** — author flips the column without running the verification. Mitigation: the `verification` cell must name a concrete artifact (test name, smoke run timestamp, manifest path), not a vague claim. Retro-driven calibration if observed.
2. **verification cell rot** — test name in the cell no longer exists in the suite (renamed/deleted). Mitigation: at phase close, `gsd-verifier` spot-checks 2-3 rows by running the named verification.
3. **scope creep into passes** — author adds extra columns (`reviewed`, `documented`, `notion_synced`). Resist; passes column has one job. Add cross-cutting state elsewhere (DEC frontmatter, INDEX.md).

## Parent

- DEC-V61-199 §2 Rule 2
- `~/CLAUDE.md /goal Pattern A` (originator of the rule in personal canon)
- Anthropic harness paper §"feature list with passes flag"

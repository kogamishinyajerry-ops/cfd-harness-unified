---
retro_id: RETRO-V61-006
title: ADR-002 W4 prep · Codex R1 CHANGES_REQUIRED · 3 HIGH silent-runtime-failure findings + same-day clean-close
date: 2026-04-25
trigger: incident-retro (RETRO-V61-001 trigger #3 · PR CHANGES_REQUIRED) — 同日 closeout, small-scale retro
related_artifacts:
  - src/_plane_guard.py (A13 atexit hook + A18 finder-internal wiring + _find_repo_root)
  - scripts/plane_guard_rollback_eval.py (unchanged)
  - tests/test_plane_guard_observability.py (+6 tests · 17 total)
  - reports/codex_tool_reports/adr_002_w4_prep_review.log (R1 verdict line 4751-4794)
  - reports/codex_tool_reports/adr_002_w4_prep_round2.log (R2 verdict line 3201-3214)
  - 5 commits: b10ca9e (R1 init) → 995dfc2 (W4 stage-1 CI) → 264121c (R1 fixes) → 3a720f1 (R2 doc-drift fixes) → e213bbe (STATE.md arc-close)
counter_at_retro: 32 (no change — R1 incident retro is `counter_impact: none` per RETRO type spec; no DEC was opened for the W4 prep arc)
notion_page: 34dc6894-2bed-813c-86e3-e3da4c5c3806 (Decisions DB · RETRO-V61-006 page · Status=Closed)
notion_sync_status: synced 2026-04-25 (https://www.notion.so/RETRO-V61-006-ADR-002-W4-prep-Codex-R1-CHANGES_REQUIRED-3-HIGH-silent-runtime-failure-findings--34dc68942bed813c86e3e3da4c5c3806)
---

## Incident summary

Codex GPT-5.4-xhigh review of W4 prep init commit `b10ca9e` (A13 sys.modules pollution watchdog + A18 fixture-frame confusion .jsonl + 14-day rolling-window evaluator + 11 tests passing) returned **CHANGES_REQUIRED** with 3 HIGH-severity findings — all material runtime gaps invisible to unit tests:

1. **HIGH F1** (`src/_plane_guard.py:677-706`) — `record_fixture_frame_confusion()` writer existed but had **zero real callsites** beyond unit tests. Docstring promised a `@pytest.mark.plane_guard_bypass` fixture path, but the session fixture in `tests/conftest.py` only stripped env / uninstalled. Net: the §2.4 rollback counter would never increment in actual dogfood usage; Option A→B trigger could never fire.

2. **HIGH F2** (`src/_plane_guard.py:199-201, 741-814`) — A13 watchdog ran `diff_pollution_snapshot()` only inside `uninstall_guard()`. But the auto-install path from `src/__init__.py:18-25` installs once and exits without calling uninstall. Codex reproduced via subprocess: snapshot a `src.*` module, exit cleanly → no pollution log written. Net: A13 silent in its main observation path.

3. **HIGH F3** (`src/_plane_guard.py:716-723`) — `_resolve_jsonl_path()` returned cwd-relative `reports/...` path; evaluator at `scripts/plane_guard_rollback_eval.py:31-33` always read `REPO_ROOT/reports/...`. Codex reproduced from temp cwd: writer wrote to tmpdir; evaluator read repo-root → silent zero-incident report. Net: even after F1+F2 wiring, signal could be silently masked.

All 3 fixes landed in commit `264121c` (270 insertions / 15 deletions; +6 new tests). Codex R2 returned **APPROVE_WITH_COMMENTS** with 2 LOW doc-drift items, fixed in `3a720f1` under RETRO-V61-001 verbatim 5/5 exception. Arc closed same day.

## Calibration

| Round | Self-estimate | Codex verdict | Calibration |
|---|---|---|---|
| R1 | 0.85 (clean tests + simple semantics; expected 1-2 LOW on lock discipline / incident_id schema / cli inversion docs) | CHANGES_REQUIRED 3 HIGH | **Material under-calibration** — missed entire class of "silent failure" modes that subprocess / real-stack repro catches but unit tests do not |
| R2 | 0.83 (R1 closed all 3 HIGH; expected LOW or APPROVE_WITH_COMMENTS — possible nits on monkeypatch fidelity / atexit double-fire / repo-root caching) | APPROVE_WITH_COMMENTS 2 LOW (doc drift) | On target — predicted exact severity tier |

**Stair-anchor (RETRO-V61-004 convention)**: 0.87 ceiling **held** — Codex APPROVE-clean (zero comments) was not produced in either round, so 0.90 unlock did not trigger. Next round opportunity: any future risky-PR Codex review on plane-guard surface.

**Calibration health**: R1 0.85 was the most over-confident self-estimate in the post-pivot arc to date. Three previous risky-PR rounds (V61-053 R3, ADR-001 G-5 R1, ADR-002 W2 R3) all came in within 0.05 of actual. R1 0.85 → CHANGES_REQUIRED 3 HIGH = 0.20 + delta — exceeded prior worst (V61-018 60% honest → CHANGES_REQUIRED, 0.10 delta).

## What worked

1. **Codex subprocess + real-stack repro discipline** — all 3 HIGH findings included reproduction commands Claude could replicate, not just static-read findings. F2's "subprocess swap then exit, observe missing log line" repro was high-fidelity; F3's "cwd from tmpdir, observe writer/evaluator divergence" was directly testable. This is a methodology pattern to keep encouraging in the Codex prompt.

2. **Verbatim 5/5 exception escape valve** — R2 APPROVE_WITH_COMMENTS 2 LOW doc-drift items qualified for RETRO-V61-001 exception (≤20 LOC, 1 file, no API change, references R2 finding numbers in body). Saved a third Codex round and prevented stair-cycling on doc-only changes.

3. **Same-day clean-close under user time-bypass** — without "无需时序约束" authorization, the R1 → R2 cycle would have spanned 24-48h and dogfood window 2026-04-25 → 2026-05-09 would have lost ≥1 day of observation. Time-bypass was correctly applied.

4. **Stair-anchor discipline survived under stress** — at no point did Claude claim 0.90 self-est to "redeem" the R1 miss. R2 self-est 0.83 explicitly noted "ceiling 0.87 not unlocked".

## What broke

1. **Self-review missed entire class of "writer-without-callsite" smell**. The A18 writer + the A18-specifically-mentioned `@pytest.mark.plane_guard_bypass` marker existed nowhere but in docstring. A 30-second `grep` of "plane_guard_bypass" or "record_fixture_frame_confusion(" callsites in non-test code would have caught F1. **Methodology gap**: pre-Codex self-review checklist did not include "grep for new public function names from non-test callers".

2. **atexit / process-exit semantics consistently underweighted**. F2 was the second occurrence of "registered hook missing on the auto-install path" class of bug in the post-pivot arc (first was tests/conftest.py initial draft missing `autouse=True scope=session`). **Action**: add to mental checklist for any new module-level state introduced under auto-install.

3. **Path resolution (cwd vs repo-root) class of bug**. F3 was the third recurrence post-pivot:
   - V61-053 had relative-vs-absolute path bug in audit fixture writer
   - V61-049 had similar in deep_acceptance package directory
   - F3 in W4 prep
   **Pattern**: any new file-write helper that targets `reports/` or `.planning/` should anchor to `_find_repo_root()` by default. Consider extracting to `src/_path_utils.py` if a fourth recurrence happens (currently 3 — not yet warranting a shared util but flagged for next observation).

4. **R1 self-estimate 0.85 was sourced from "clean tests + simple semantics"** without weighting the runtime-integration surface. The 3 HIGH findings all involve runtime paths that unit tests skipped because they didn't simulate the full process-exit / cwd-divergence / find_spec-bypass-with-forbidden-pair scenarios. **Calibration anchor**: when introducing observability instrumentation (writers, watchdogs, hooks), pre-emptively assume self-est cap 0.75 until subprocess / real-stack repro is part of the test matrix.

## Methodology patches (proposed for next risky-PR)

| Patch | Description | Authority |
|---|---|---|
| **MP-2026-04-25-A** | Pre-Codex self-review checklist add: "grep for new public function names from non-test callers" — catches writer-without-callsite class of bug | RETRO-V61-006 §"What broke" #1 |
| **MP-2026-04-25-B** | When new module-level state is introduced via auto-install / src/__init__.py, mandate atexit / process-exit registration as part of design, not afterthought | RETRO-V61-006 §"What broke" #2 |
| **MP-2026-04-25-C** | Self-est cap 0.75 (override 0.87 stair ceiling) for any PR introducing observability instrumentation (writers / watchdogs / hooks) until subprocess / real-stack repro is part of the test matrix | RETRO-V61-006 §"What broke" #4 |

These are proposals, not committed methodology changes — `MP-XXX` patches sit in retro until a future risky-PR consumes them or a counter-N retro promotes them to STATE.md / CLAUDE.md updates.

## Counter status

- counter_at_retro: 32 (unchanged from RETRO-V61-003 baseline; W4 prep arc commits b10ca9e/995dfc2/264121c/3a720f1/e213bbe are governance-class, not DEC-class — no `autonomous_governance: true` DECs opened)
- Next cadence retro at counter=40 per RETRO-V61-003 schedule.

## Open questions

1. **Should W4 prep have been split into 2 PRs?** R1's 3 HIGH could conceivably have been caught by splitting "instrumentation (b10ca9e)" from "wiring (264121c)" into separate Codex rounds. Verdict: **No** — the wiring without instrumentation has no semantic content; reviewer would have nothing to verify. The actual error was self-review depth, not PR granularity.

2. **Is dogfood window 2026-04-25 → 2026-05-09 enough to surface plane-guard-class bugs?** Open. Window is read-only; no synthetic injection planned. If 5/9 review surfaces zero incidents, that's evidence W4 prep is correctly aimed but not evidence W4 prep is bug-free. Future addendum if signal differs.

3. **Should MP-2026-04-25-C extend to all instrumentation in the codebase?** Possibly. Other observability code (correction_recorder, audit_package signing) was written without subprocess repro. Defer to a counter-40 cadence retro for arc-wide methodology promotion.

## Addendum 2026-04-25T20:05 +0800 · OPS-2026-04-25-001 §5 reverse-direction protocol violation

While drafting this retro and the dogfood baseline, line B session absorbed line A's pending uncommitted work (`.planning/retrospectives/2026-04-25_retro_w4_prep_r1_incident.md`, `reports/plane_guard/baseline_2026-04-25.md`, `tests/conftest.py`, `tests/test_plane_guard_observability.py`, `.gitignore` line A patches) into its own commit `e7909ac` (`[line-b] docs(intake): DEC-V61-057 · DHC Type I 5-dim · v1 intake`). Most likely cause: line B used `git add -A` or `git add .` while line A had files in working tree but not yet staged; line B's commit then included both.

Net effect:
- Files landed on origin/main correctly (no work lost)
- Commit ownership taxonomy violated (`[line-b]` tag now contains line A artifacts)
- The dual-track-isolation pre-commit hook would have warned line B at commit-msg stage if installed (line B has not yet run `pre-commit install`)
- No CI / dogfood signal impact (.jsonl files were tmp-redirected before this incident)

Methodology patches added (proposed for v6.1 amendment):
- **MP-2026-04-25-E**: cross-track add-all is the most likely "how" of line ownership violations. Recommend explicit `git add <path>` or `git add -p` (interactive patch) discipline during dogfood window. Add to OPS-2026-04-25-001 §9 commit-granularity guidance.
- **MP-2026-04-25-F**: line B should `pre-commit install` immediately on session start so the dual-track-isolation warn-not-block hook fires. Until installed, it's documentation only.

This addendum is a one-time post-hoc documentation. The actual fix path (move incorrectly-attributed files to a `[line-a]` revert+recommit) is rejected — git history rewrite during dogfood window is more risk than benefit, and the file *content* is correct regardless of which commit message bears the tag.

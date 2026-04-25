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

**Stair-anchor probationary drop (Opus 4.7 audit 2026-04-25T15:10)**: 0.87 → **0.85** for the **NEXT SINGLE PR** (W4 toggle PR). Auto-recovery to 0.87 on a clean Codex APPROVE (zero comments) of that PR. Rationale: R1 0.85 → CHANGES_REQUIRED was the 0.20+ delta single-PR miss in post-pivot history; one probationary PR confirms the calibration recovery is real, not lucky. Note: applies in addition to MP-C-revised cap 0.70 for instrumentation+CI-workflow PRs (W4 toggle is both, so the binding cap is `min(0.85, 0.70) = 0.70` for that PR specifically).

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

5. **CI installation surface ≠ local dev surface (Gap #5 · Opus 4.7 audit 2026-04-25T15:10)**. Pyproject deps were sufficient for local dev (numpy + jinja2 already in user's global Python / .venv) but insufficient for fresh CI install (`pip install -e ".[dev]"` on a fresh ubuntu-latest container). The 40-CI-failure streak proves "tests pass locally" does not certify "tests pass on a clean environment". **Pattern**: any time a runtime import is added without a matching pyproject declaration, the bug is silent locally. **Action**: future PRs that add a top-level third-party import must run `grep -rhE "^(import|from) [a-zA-Z]" src/ tests/` then diff against `pyproject.toml` `[project].dependencies` BEFORE commit; the pre-Codex checklist (`docs/methodology/pre_codex_self_review_checklist.md`) gains §2.6 for this.

6. **Artifact emptiness ≠ artifact absence (Gap #6 · Opus 4.7 audit 2026-04-25T15:10)**. CI artifacts that are empty (zero `.jsonl` lines because pytest never executed) read identically to artifacts that are correctly empty (zero incidents because zero violations occurred). The 5/9 review template's "0 incidents = GO" rule is ambiguous between these two semantics. **Pattern**: silence-as-signal protocols must distinguish "process completed cleanly with zero events" from "process never ran". **Action**: 5/9 review template `.planning/dogfood/2026-05-09_review_template.md` Step 1 should explicitly verify the `ci_warn_pytest.log` shows `<N> passed` (process ran) before reading `.jsonl` count. Without `ci_warn_pytest.log` confirmation, an empty-`.jsonl` artifact is INDETERMINATE, not "0 incidents".

## Methodology patches (proposed for next risky-PR)

| Patch | Description | Authority |
|---|---|---|
| **MP-2026-04-25-A** | Pre-Codex self-review checklist add: "grep for new public function names from non-test callers" — catches writer-without-callsite class of bug | RETRO-V61-006 §"What broke" #1 |
| **MP-2026-04-25-B** | When new module-level state is introduced via auto-install / src/__init__.py, mandate atexit / process-exit registration as part of design, not afterthought | RETRO-V61-006 §"What broke" #2 |
| **MP-2026-04-25-C** | Self-est cap 0.75 (override 0.87 stair ceiling) for any PR introducing observability instrumentation (writers / watchdogs / hooks) until subprocess / real-stack repro is part of the test matrix | RETRO-V61-006 §"What broke" #4 |

These are proposals, not committed methodology changes — `MP-XXX` patches sit in retro until a future risky-PR consumes them or a counter-N retro promotes them to STATE.md / CLAUDE.md updates.

**Update 2026-04-25T21:25 + 2026-04-25T21:50 (Opus 4.7 audit Item b expansion)**: immediate-promotion set expanded from 2 (originally MP-A + MP-G per Kogami batch approval) to **4**:
- ✅ **MP-A LANDED** (commit `8e74606`): `docs/methodology/pre_codex_self_review_checklist.md` §2.1 + `docs/governance/CODEX_REVIEW_RUBRIC.md` §1.4
- ✅ **MP-C-revised LANDED** (commit `<phase 1 hash>`): cap 0.75 → **0.70** for instrumentation+CI-workflow PRs. Binding: W4 toggle PR drafting MUST cap self-est at min(0.85 stair-anchor probationary, 0.70 MP-C) = **0.70**. The 5/9 review template (`.planning/dogfood/2026-05-09_review_template.md`) commit-message draft is updated accordingly.
- ✅ **MP-E LANDED** (commit `<phase 2 hash>`): permanent rule added to OPS-2026-04-25-001 §9 — `git add -p` (interactive patch) discipline during dogfood window; `git add -A` / `git add .` strongly discouraged. Lands in same PR as the §3 dual-track-isolation v2 supersede.
- ✅ **MP-G LANDED** (commit `8e74606` + Opus revisions in `<phase 1 hash>`): `docs/methodology/ops_note_protocol.md` §5 sixth mandatory rule, Opus-revised to 7-day rolling 3-tier (Green ≥80% / Yellow 70-80% / Red <70%) + `workflow_path` (file path) + (c) attestation fallback for first-of-kind no-prior-runs corner case.

Still **deferred** to counter-40 cadence retro:
- MP-B (atexit registration as design step) — covered in pre-Codex checklist §2.2; doesn't need separate promotion document yet
- MP-F (line B `pre-commit install` on session start) — operational reminder; addressed by `bin/dev-session-init` script in §3 v2 supersede landing

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

## Addendum 2026-04-25T20:50 +0800 · CI dogfood window dead-on-arrival · 40-CI-failure unblocker

While installing pre-commit hooks and running line A's first dogfood-period CI verification (`gh run list`), discovered **40 consecutive CI failures** dating back well before the dogfood window opened. Root cause: `numpy` and `jinja2` were never declared in `pyproject.toml` as runtime deps even though `src/cylinder_centerline_extractor.py` and `src/report_engine/generator.py` import them. Local dev shells / .venv had these in their global Python so nobody noticed. CI (which runs `pip install -e ".[dev]"` on a fresh GitHub Actions ubuntu-latest container) had nothing to fall back on, exiting with `ModuleNotFoundError: No module named 'numpy'` at pytest collection time.

**Critical impact on the W4 prep arc and dogfood window**:
- The W4 stage-1 dogfood pytest step (`if: always()` + `continue-on-error: true`) ran but ALSO failed on the same import error — produced **empty .jsonl artifacts** for every CI run since 2026-04-25T05:18 (W4 stage-1 commit `995dfc2`).
- 5/9 review would have read empty artifacts as "0 incidents = GO" without knowing that no tests actually exercised the plane-guard. Net: the W4 toggle PR could have flipped to hard-fail mode based on no signal at all.
- The dogfood window 2026-04-25 → 2026-05-09 was **dead-on-arrival** until 2026-04-25T20:50 (commit `0208929` fixed deps + pre-commit hook self-containment).

**Methodology patch added** (proposed):
- **MP-2026-04-25-G** · Any multi-day signal-collection plan (dogfood window / observation period / shadow-mode evaluation) must have **CI infrastructure healthy** as pre-flight check #1. The `.planning/dogfood/2026-05-09_review_template.md` already lists this — but the methodology gap is that the OPS-2026-04-25-001 plan didn't verify CI BEFORE declaring the window open. **Action**: future OPS notes that depend on CI signal must require a "last successful CI run within last 24h" assertion in the OPS frontmatter or §3 isolation mechanism block.

**MP-2026-04-25-C revised** (originally "self-est cap 0.75 for observability instrumentation"):
- The W4 prep R1 self-est miss (0.85 → CHANGES_REQUIRED 3 HIGH) plus this 40-failure CI miss together suggest the cap should be **even lower** for instrumentation that depends on CI being functional. The prior cap of 0.75 was based on "subprocess repro is part of test matrix"; the new evidence is that the repro can pass locally while CI is silently broken. **Revised cap**: 0.70 for any PR introducing observability instrumentation that ships CI workflow changes (W4 stage-1 was both — it added the WARN-mode dogfood pytest step + assumed CI was running).

**Counter-40 cadence retro should consume MP-A through MP-G** for arc-wide methodology promotion.

### Confirmation 2026-04-25T21:05 +0800 · first genuine dogfood signal captured

Post deps fix (`0208929`), commit `0229af9` triggered CI run `24925115531`:
- **Backend pytest job: SUCCESS** — `748 passed, 1 skipped in 55.54s` (was 0 passed / 5 collection errors per all 40 prior runs)
- **W4 stage-1 dogfood pytest step: SUCCESS** — `748 passed, 1 skipped in 54.65s` under `CFD_HARNESS_PLANE_GUARD=warn`
- **Rollback evaluator output**: `OK: 0 fixture-frame confusion incidents in last 14d (threshold 3)`
- **Artifact `plane-guard-dogfood-0229af9...` uploaded** (13.5 KB) containing only `ci_warn_pytest.log`; no `.jsonl` files = 0 incidents recorded (matches local baseline `reports/plane_guard/baseline_2026-04-25.md` exactly)
- Frontend job: still failing (separate `ui/frontend/package-lock.json` cache-path issue · pre-existing · NOT a dogfood-window blocker · line A leaves to another time)

This commit (`0229af9`) is the **first run that produced genuine dogfood signal**. Prior 40 runs were instrumentation-equivalent of a sensor in a dead circuit. The 5/9 review now has a real anchor: CI runs 0229af9 onwards are the data set.

---

## Addendum 3 · Opus 4.7 §3 v2 ACCEPT_WITH_COMMENTS direction-survey verdicts (2026-04-25T16:30)

After Phase 1/2/3 amendments landed (3e8dc01 / a84948d / 1034c20 / f9b42e5), Claude Code CLI prepared a 6-direction further-optimization survey for Notion Opus 4.7 independent review. Opus returned **ACCEPT_WITH_COMMENTS** with maturity 0.68 → 0.72 (+0.04), conditional on direction 4 landing before 5/9.

### Direction priority verdicts (Opus authoritative)

| # | Direction | Priority | Action | Reason |
|---|---|---|---|---|
| 1 | `src/_path_utils.py` extraction (anti-F3-recurrence) | **P2** | Defer until 4th recurrence | Rule-of-three supports now, but dogfood static-period (no-push-main) is harder constraint; 治理一致性 > 工程洁癖 |
| 2 | SessionStart hook auto-runs `dev-session-init` | **P3 reject** | Do not pursue | Implicit state opposes dogfood-window's "状态必须可审计" core; pre-commit install already idempotent, painless |
| 3 | OPS retire 5/19 hook handling: (a) delete (b) generalize (c) leave | **P1** | Decide now (verdict (a)) execute 5/19 | Avoid last-minute pickup; (b) generalize is N=1 over-fit; (a) delete + git-history retention is clean |
| 4 | A13/A18 4-tuple dedup | **P0** | **Land before 5/9** | Directly determines 5/9 GO/NO-GO; without dedup, finder re-entry inflates 1 real incident to 2-3 lines and trips §2.4 ≥3 on noise |
| 5 | W4 toggle Codex prompt rewrite (data-validity audit, not diff audit) | **P1** | Land before 5/11 | Diff is 1 LOC and trivially correct; Codex's job is to audit the 5/9 data validity. Use Opus's draft. |
| 6 | OPS protocol v2 full revision | **P3 reject** | Wait for OPS-002/003 | N=1 → v2 is textbook over-generalization; let patterns accumulate first |

### Blind spot proposal — escape-hatch usage rate metric (P0)

Opus identified a metric the 5/9 review template was missing: how many commits in the dogfood window used escape tags (`[cross-track-ack:…]` / `[shared]` / `[deps]` / `[ops]` / `CROSS_TRACK_ACK=1`)? If usage rate >20%, hook policy is too strict and 5/19 default flip will create line B / cross-track friction at scale.

**Implementation**: Step 1.5 in `2026-05-09_review_template.md` (landed alongside this addendum). Decision thresholds: <10% calibrated, 10-20% acceptable + log in W4 commit, >20% defer toggle.

**Initial measurement (2026-04-25T16:00, mid-window)**:
- Total commits since 2026-04-25 00:00: **84**
- Commits with at least one escape tag: **9** (`[ops]` × 6, `[shared]` × 3, `[deps]` × 2)
- Escape rate: **9 / 84 = 10.7%** (well within calibrated band)
- `[cross-track-ack:…]` usage: **0** (no legitimate §4.1 events occurred — clean signal)

### Maturity calibration update

| Snapshot | Maturity | Self-est | Delta | Notes |
|---|---|---|---|---|
| Pre-Phase-1 (2026-04-25T15:10) | 0.62 | 0.62 | 0 | At time of Opus initial OPS audit |
| Post-Phase-1-2-3 (2026-04-25T15:50) | 0.72 | 0.62 | +0.10 | Opus +0.04 vs prior 0.68; gap to self-est = 0.10 (within calibration band) |

**Conditional**: the +0.04 maturity gain is contingent on direction 4 landing before 5/9. If 5/9 finds A13/A18 signal noise-corrupted (raw lines >> dedup count without dedup having been deployed), maturity collapses to ≤0.65, W4 toggle MUST be NO-GO, RETRO addendum 4 captures the calibration miss.

### Reject rationale (directions 1/2/6) — 治理姿态判断

Opus's most important piece of feedback was the overall posture verdict: **"线 A 不是过早优化，但 6 个方向里只有 1 个 (方向 4) 是真实空间，其余要么违反 dogfood 静默 (方向 1)、要么与可审计性相悖 (方向 2)、要么 N=1 上过度泛化 (方向 6)、要么是 5/9 之后的事 (方向 3/5)。当前最大风险不在 '做太少'，而在 '为了显得在工作而打破静默'——治理成熟度的标志正是能在静默期保持静默。"**

This locks in the dogfood-window discipline: line A's job between 2026-04-25 and 2026-05-09 is **not** to ship more amendments — it is to wait for signal. The Phase 4 amendments (this addendum + dedup + escape rate + W4 prompt) are the sole exception, justified by their direct dependency on signal validity at 5/9.

### Phase 4 landing scope (this commit's amendments)

- `scripts/plane_guard_rollback_eval.py` — 4-tuple dedup (default ON), `--no-dedup` for diagnostics, return-tuple bumped to 4 elements (added `raw_count`)
- `tests/test_plane_guard_observability.py` — new `test_rollback_eval_dedup_collapses_repeated_4tuple` test + `_write_log` accepts `distinct_4tuples` parameter + 4-tuple return unpack migrated
- `.planning/dogfood/2026-05-09_review_template.md` — Step 1.5 escape rate sanity, Step 2 dedup default + `--no-dedup` diagnostic, Step 3 dedup-count basis, §4.1 Codex data-validity prompt
- This RETRO addendum 3 — direction-survey verdicts and posture lock-in
- (No changes to `src/_plane_guard.py` or `src/__init__.py` — writers are CORE line A SOLE and must remain frozen during dogfood window)

---

## Addendum 4 · CI health sampling finding · §5#6 query-field disconnect (2026-04-25T16:50)

### What was sampled

Per OPS-2026-04-25-001 §5#6 mandatory pre-flight rule, the canonical 7-day rolling success ratio query was executed on origin/main mid-window:

```bash
gh run list --workflow=ci.yml --branch=main --limit 35 \
  --json conclusion,createdAt --jq '...'
```

### Result

| Granularity | Success ratio | OPS §5#6 verdict |
|---|---|---|
| **Workflow-level** (current §5#6 query) | 0/35 = **0%** | **RED HARD BLOCK** |
| Backend pytest job (all 35) | 8/35 = 23% | (RED if used) |
| Backend pytest job (post-`0229af9` anchor, completed runs only) | **8/8 = 100%** | **GREEN** |
| Frontend job | 0/35 = 0% | (pre-existing pkg-lock cache-path issue, addendum 2 documented) |

### Root cause: spec/query disconnect in §5#6

The OPS frontmatter encodes:

```yaml
expected_signal_source:
  workflow_path: .github/workflows/ci.yml
  job_or_step: backend-tests / "Plane-guard WARN-mode dogfood"  # <-- this field exists
pre_flight_ci_health_check_command: |
  gh run list --workflow=ci.yml --branch=main --limit 35 \
    --json conclusion,createdAt ...                              # <-- but query reads workflow-level only
```

The `job_or_step` field is informational; the actual query reads **workflow-level** `conclusion`. When any unrelated job in the workflow (e.g., the Frontend `tsc + vite build` job, which has a pre-existing cache-path bug) fails, workflow `conclusion=failure` even though the backend dogfood signal step passes cleanly. Result: false-positive RED that would HARD-BLOCK any future OPS authoring during this window.

### Why this is NOT being fixed in static period

1. **5/9 dogfood review unaffected**: review template Step 1 uses Gap #6 sanity (per-step `ci_warn_pytest.log <N> passed` check), not workflow-level conclusion. The §2.4 trigger pipeline is independent of this query.
2. **Current OPS unaffected**: OPS-2026-04-25-001 is already ACTIVE; pre-flight check fires only at DRAFT → ACTIVE flip, not on existing OPS. The frontmatter `signal_health_status_at_first_genuine_signal: GREEN` was set manually based on backend-job inspection, correctly.
3. **No future OPS authoring scheduled**: Opus 4.7 §3 v2 ACCEPT_WITH_COMMENTS direction 6 explicitly REJECTED OPS protocol v2 / OPS-002 authoring during this window (N=1, premature generalization).
4. **Static period discipline**: per RETRO Addendum 3 posture lock-in, line A is in static mode through 5/9. Fixing this jq pipeline = Phase 5 commit, breaks "sole exception" status of Phase 4. Methodology bugs that don't affect signal validity are NOT cause to break static period.

### How this gets fixed (deferred to 5/19 W5 default flip + OPS retire PR)

The §5#6 query needs to switch from workflow-level to job-level conclusion. The fix path uses GitHub's per-run jobs API (already validated in this addendum):

```bash
# replace the §5#6 jq pipeline with a per-job query
gh run list --workflow=ci.yml --branch=main --limit 35 \
  --json databaseId,createdAt --jq '.[]|"\(.databaseId)\t\(.createdAt)"' \
  | while IFS=$'\t' read -r rid created; do
      conc=$(gh api "repos/{owner}/{repo}/actions/runs/$rid/jobs" \
        --jq '.jobs[] | select(.name == "Backend · pytest (py3.12)") | .conclusion')
      echo "$created $conc"
    done \
  | <7-day-rolling-aggregation>
```

This will be landed in the same 5/19 PR as the OPS retirement, alongside `ops_note_protocol.md` §5#6 spec text update (clarify that `job_or_step` is REQUIRED to be matched in the query, not informational). Per Opus direction-survey verdict 3 (P1, execute 5/19 same PR).

### Methodology pattern proposal: MP-H (deferred candidate)

The bug class is "spec field exists in frontmatter but query doesn't read it" — this is generalizable. Candidate MP-H rule: **any structured frontmatter field that the spec mandates SHOULD be exercised by every reader/checker that consumes that part of the spec; otherwise the field is decoration, and decoration drifts**. NOT promoted now (over-generalization risk, want to see if it recurs in OPS-002 / non-OPS contexts before crystallizing). Logged here to seed the next retro's pattern review.

### Sample-only summary

This addendum captures an observation. NO code change, NO test change, NO behavioral change. RETRO-V61-006 status remains: closed-with-three-addenda (1 = Codex R2 closeout, 2 = 40-CI-failure post-mortem + first GREEN signal, 3 = Opus direction-survey, 4 = this CI health sample finding).

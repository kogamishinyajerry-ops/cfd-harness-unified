---
type: roadmap
id: ROADMAP-line-A-post-W5
title: Line A · Post-W5 Signal-Driven Roadmap (5 stages)
status: ACTIVE
created: 2026-04-25
authority: |
  Notion Opus 4.7 ACCEPT_WITH_COMMENTS 2026-04-25T17:30 (任务 B
  post-W5 signal-driven roadmap response · maturity 0.72 → 0.76
  conditional). Companion to OPS-2026-04-25-001 §7 9-gates
  refactor and RETRO-V61-006 Addendum 5.
related:
  - .planning/ops/2026-04-25_dual_track_plan.md
  - .planning/retrospectives/2026-04-25_retro_w4_prep_r1_incident.md
  - docs/adr/ADR-002-four-plane-runtime-enforcement.md
no_calendar_in_triggers: true  # Per Opus 9-gates refactor: every trigger here is event/signal-based.
---

# Line A · Post-W5 Signal-Driven Roadmap

> **Calendar dates appear ONLY in audit/trace fields (`created`, amendment timestamps).** Every stage trigger is an event or signal count. If a trigger never fires, the stage never starts — that is the correct behavior, not a failure mode.

## Posture statement (Opus authoritative)

> "W5 之后线 A 应该是 'post-W5-1 一次主动收尾 + 后续 maintenance-only with event-triggered stages'. 主依据: four-plane runtime enforcement 的本征复杂度在 W5 后已基本释放, post-W5-1 的 hard-fail 是收口动作而非新功能; 继续主动发起 stage 会落入 '为存在感而工作' 反模式, 与用户 '按阶段、功能快速推进' 导向相违 (线 A 的 '阶段' 已基本走完)."

Translated: line A is in **active development through post-W5-1** (the hard-fail promotion). After that, **maintenance-only** mode — stages 2-5 fire only when their trigger conditions naturally arise.

## Stage post-W5-1 · Plane-guard hard-fail promotion ('warn' → 'on' default)

- **Trigger** — ALL of:
  - W5 default flip merged ∧ Gate #4 fires (OPS-2026-04-25-001 retired)
  - ≥30 backend pytest CI runs all green post-W5-flip
  - A13/A18 dedup'd incidents = 0 throughout those 30 runs
  - line A SOLE escape-tag commits = 0 throughout those 30 runs
- **Scope** — `src/__init__.py` default value `'warn'` → `'on'`; same PR updates ADR-002 §default-state; deprecates the `'warn'` compatibility branch left over from OPS retirement
- **Predecessor** — Gate #4 fires (W5 + OPS retire same PR)
- **Risk** — `'on'` will hard-fail any cross-track work whose plane-crossing imports are not covered by an escape tag. MUST verify escape-rate **history** = 0 (not just current <20%) before this fires; otherwise legitimate cross-track flows break in production.
- **Codex audit class** — REQUIRED (instrumentation default-state change · ADR amendment)
- **Self-est cap** — 0.75
- **Active development**: yes — this is the line A milestone closeout

## Stage post-W5-2 · Cross-track absorption hooks 处置决议

- **Trigger** — post-W5-1 landed ∧ ≥20 CI runs in `'on'` state all green
- **Scope** — three-way decision (Opus direction-survey verdict 3): (a) delete hook registration + retain scripts in git history; (b) rename hooks to `commit-discipline` for general-track use; (c) leave registration in place. **Recommended: (a)**. The decision lands as ADR amendment or DEC; only (a) entails code (deleting `.pre-commit-config.yaml` entries).
- **Predecessor** — post-W5-1
- **Risk** — (b) is N=1 over-generalization; (c) accumulates cognitive debt. The recommendation toward (a) is provisional — finalize when the trigger fires.
- **Codex audit class** — REQUIRED (governance-tool retirement / rescope)
- **Self-est cap** — 0.65
- **Maintenance-mode**: stage fires automatically when its trigger conditions are satisfied; no proactive scheduling.

## Stage post-W5-3 · Codex review scriptification

- **Trigger** — cumulative manual `/codex-gpt54` invocations ≥ 10 ∧ ≥3 RETRO cycles have settled prompt templates (signaling stable patterns worth automating)
- **Scope** — `bin/codex-review` wrapper script; input `(PR-url, audit-class)`; output a standard prompt envelope. **Only template instantiation**, NOT auto-invoke Codex. Human-in-the-loop preserved. The wrapper's value is reducing prompt-drafting overhead, not removing the human review step.
- **Predecessor** — independent of post-W5-1/2; can run in parallel
- **Risk** — over-automation hides intentional friction (each manual prompt write is a quality calibration point). Mitigation: the script generates without sending; the operator still presses send. If usage shows operators mechanically rubber-stamp generated prompts, deprecate the script.
- **Codex audit class** — verbatim-eligible (non-runtime tooling)
- **Self-est cap** — 0.80
- **Maintenance-mode**: trigger may fire fast (10 invocations is achievable in normal use) or slow.

## Stage post-W5-4 · ADR-003 Plane Assignment v2 (conditional · event-triggered)

- **Trigger** — ≥3 distinct edge cases reported showing `src/__init__.py` auto-install plane assignment ambiguity **OR** ≥1 production-grade incident traceable to plane misassignment
- **Scope** — ADR-003 spec drafting + migration of existing plane decorators. Targets the `src/__init__.py` auto-install boundary which is the most ambiguous corner of ADR-002.
- **Predecessor** — post-W5-1 (`'on'` state must exist for ambiguity to surface in production traces)
- **Risk** — trigger may never fire; that is acceptable. Do NOT preemptively redesign for hypothetical edge cases ("不为重设计而重设计" per Opus posture). If the trigger never fires, ADR-002 stands as written indefinitely.
- **Codex audit class** — REQUIRED (ADR-class change)
- **Self-est cap** — 0.70
- **Maintenance-mode**: explicitly conditional — may never start.

## Stage post-W5-5 · `_path_utils.py` extraction (conditional · event-triggered)

- **Trigger** — cwd-vs-repo-root path resolution bug recurs for the **4th time**. Prior 3 occurrences: V61-053 / V61-049 / W4 prep F3.
- **Scope** — extract dedicated `src/_path_utils.py` module + migrate ≥3 known callsites
- **Predecessor** — independent
- **Risk** — 4th recurrence may never come, in which case the rule-of-three "wait" posture wins at zero cost. If it does come, the refactor is local and well-scoped.
- **Codex audit class** — REQUIRED (cross-cutting refactor)
- **Self-est cap** — 0.85
- **Maintenance-mode**: explicitly conditional — may never start.

## NOT-IN-ROADMAP (event-triggered, but no stage allocated until trigger fires)

These items are **logged** here so future-Claude knows they exist, but are NOT proactive stages:

- **MP-H crystallization** — the "frontmatter field MUST be exercised by every reader" rule, candidate from RETRO Addendum 4. Wait for OPS-002 recurrence before crystallizing into ops_note_protocol.md.
- **OPS-002 authoring** — wait for trigger scenario (e.g., new freeze window, new multi-session coordination need).
- **Notion sync automation** — wait for manual sync overhead to accumulate (e.g., ≥10 missed syncs or operator complaint).

## Maintenance-mode default behavior

After post-W5-1 fires, line A enters **maintenance-only** mode. Default behavior:

1. **No proactive stage starts**. Stages 2-5 are pure trigger-driven.
2. **No proactive `gsd-execute-phase` invocations**. If user asks for a feature in line A scope, evaluate: does it match an existing stage's trigger? If yes, escalate to that stage. If no, push back: "this would create a new line A thread; is that warranted?"
3. **External triggers welcomed**: line B failure that surfaces line A weakness, Codex audit finding, user feedback — all legitimate trigger sources. Calendar ticking is NOT a legitimate trigger source.
4. **Codex audits continue per Gate #7** (every risky-PR + every 10 merged PRs sample). This is the only ongoing cadence.

## Calendar legacy (audit traceability only)

The original Opus G-9 binding 2 had calendar form: W4 toggle PR ≤ 2026-05-11, W5 default flip ≤ 2026-05-19. These dates are **deprecated** as gates. Retained in OPS frontmatter `expires_calendar_legacy` and amendment_log only as audit traceability. The signal-count form **always supersedes** the calendar form in any conflict.

## Maturity coupling

| Event | Maturity impact |
|---|---|
| This roadmap landed (today) | Opus +0.04 conditional → **0.76** |
| post-W5-1 trigger fires + lands clean | +0.03 → 0.79 |
| Stage 2 decision lands ((a) recommendation followed) | +0.01 → 0.80 |
| Maintenance-mode honored for ≥3 months without proactive line A stage | +0.02 → 0.82 |
| Calendar form silently re-introduced anywhere in line A | -0.04 → 0.72 (regression) |

---

**Status**: ACTIVE 2026-04-25T17:30. Calendar dates above are timestamps for audit, NOT gate parameters.

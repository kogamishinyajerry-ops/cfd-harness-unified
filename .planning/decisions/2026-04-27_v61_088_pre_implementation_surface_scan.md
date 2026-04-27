---
decision_id: DEC-V61-088
title: Pre-implementation surface scan · 动手前 ROADMAP + 已有实现 grep 作为 routine gate
status: Proposed (2026-04-27 · awaits Kogami review per DEC-V61-087 §4 autonomous_governance rule-change trigger)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-27
authored_under: post-session 2026-04-27 Notion-Opus advisory review (P1 finding §3)
parent_dec:
  - DEC-V61-087 (v6.2 governance · this DEC adds a startup-checklist clause that complements but does not modify Kogami contract)
  - RETRO-V61-001 (counter rules · self-pass-rate honesty)
parent_review:
  source: Notion-Opus 4.7 post-hoc strategic sanity review
  date: 2026-04-27
  reference: Session page 34fc68942bed81e4a691f4df136c48fe
  finding: |
    P1 §3: "run-compare API '再发现' event"
    > Claude Code 在动手写 server API 之前没有 grep RunComparePage、没有看
    > ROADMAP §60-day 已勾选项,这是 ROADMAP 状态读取失败,不是"两条独立线"。
    > 如果接受"server hardening 与 client UI 平行演化"作为通用借口,下一次会
    > 变成"在已有 X 旁边重写 X′"的合理化。
notion_sync_status: pending (sync after Kogami review)
autonomous_governance: true  # this DEC modifies Claude Code's own startup discipline; does NOT modify Kogami contract or files (P-1..P-5), so §4 skip rule does NOT fire — Kogami review IS required per §4 first item (autonomous_governance rule-change DEC)
---

# DEC-V61-088 · Pre-implementation surface scan as routine gate

## Why

Session 2026-04-27 Notion-Opus advisory review surfaced a P1: I (Claude Code)
wrote a 200-LOC server-side run-compare API + 17 tests + ran a 2-round
Codex review arc, **before discovering** that `ui/frontend/src/pages/workbench/RunComparePage.tsx`
already existed (349 LOC, built 2026-04-26) implementing the same functional
goal client-side. The work landed as commit `96e9f46` — not wasted (it
genuinely hardens NaN/traversal/type-mismatch edge cases the client-side
path silently mishandles), but the *act of starting it* was a ROADMAP-state
read failure.

I framed the outcome as "API hardening parallel to UI feature, not redundant
work". That framing is technically defensible but Notion-Opus correctly flags
it as a **rationalization risk** if accepted as routine excuse:

> 如果接受"server hardening 与 client UI 平行演化"作为通用借口,下一次会变成
> "在已有 X 旁边重写 X′"的合理化。

The session's pattern (write feature → discover prior implementation late →
spin into "complementary hardening") is a regression from the methodology
discipline already in place for case_profile / DEC numbering / counter
audit, all of which I check upfront. ROADMAP state and existing code don't
get the same upfront-check treatment.

## Decision

**Adopt as Claude Code routine startup discipline (autonomous_governance
rule, NOT a Kogami contract change):**

Before starting any non-trivial implementation work (≥ ~30 LOC OR new
top-level page / route / service file), run a **2-step pre-implementation
surface scan** and write findings to the session's working memory:

### Step 1 · ROADMAP scan
- Read the relevant ROADMAP section (§30-day / §60-day / §90-day per scope)
- Identify whether the proposed feature maps to a known item
- If yes: note its current status (planned / in-progress / done) and link
  to the planning artifact (DEC / case_profile / dogfood doc)

### Step 2 · Existing-implementation grep
- Run the equivalent of:
  ```bash
  grep -rin "<feature_keyword>" \
    src/ ui/backend/ ui/frontend/src/ scripts/ \
    --include="*.py" --include="*.ts" --include="*.tsx" \
    -l | head -30
  ```
- Read any matched files at top-of-file level (first 60 lines + grep within
  for the feature pattern)
- If a substantial pre-existing implementation is found:
  - **STOP** before writing new code
  - Surface to user: "found existing X at <path> doing <Y>; proposed work
    is <new-or-overlap>; choose: (a) extend existing / (b) parallel new
    / (c) refactor existing"

### Skip clause

Surface scan can be skipped only when:
- (a) Routine bugfix matching an existing, located file (already-grepped)
- (b) Documentation-only changes (CLASS-1 per Pivot Charter §4.7)
- (c) Scope explicitly given by user as "rewrite X" (user has already
  done the surface scan mentally)
- (d) Trivial single-file edit ≤ ~10 LOC

For any other scope, surface scan is **mandatory** — running a `grep` and
reading 2-3 file headers takes <60 seconds and prevents the failure mode.

## Impact

### Positive
- Closes the P1 framing risk Notion-Opus flagged
- Cheap (≤1 minute per pre-implementation event)
- Generalizes the discipline already applied to case_profile / DEC numbering
- Produces an audit trail (the surface-scan findings can be quoted in the
  commit message or session page)

### Negative
- Adds a startup tax to every non-trivial work item
- Risk of "ritual compliance" if the scan becomes mechanical and doesn't
  actually inform the work — mitigated by requiring the findings to be
  *quoted* in the commit message when relevant, not just "ran the grep"

### Counter handling
- Counter v6.1 += 1 if Status flips to Accepted (autonomous_governance: true)
- Kogami review is **required** per DEC-V61-087 §4 (autonomous_governance
  rule-change DEC trigger): ANY DEC that modifies how the autonomous arm
  governs itself qualifies. This DEC modifies Claude Code's own startup
  discipline, which is exactly that surface.

## Acceptance Criteria

1. Before this DEC flips to Accepted:
   - Kogami subprocess invoked with this DEC as artifact (per DEC-V61-087
     §4 autonomous_governance rule-change trigger)
   - Codex GPT-5.4 review of THIS DEC's design (not for code review — for
     methodology soundness)
   - User explicit ratification

2. Once Accepted:
   - Update `~/CLAUDE.md` (user-level, outside repo) **Subagent 优先原则**
     section to add: "any non-trivial work (>30 LOC OR new top-level
     file): pre-implementation surface scan via grep + ROADMAP read".
     User confirms before edit.
   - Update `CLAUDE.md` (project-level, in repo) to reference this DEC
     under a new "Pre-implementation discipline" section.
   - First test: in next session, when starting any new feature work,
     log the surface-scan findings to the session conversation.

## Out of Scope

- Does NOT modify Kogami contract (P-1..P-5, DEC-V61-087 itself).
- Does NOT change Codex review triggers (RETRO-V61-001).
- Does NOT change counter rules (P-5 / DEC-V61-087 §5).
- Does NOT change user's manual workflow — only Claude Code's discipline.

## Alternatives Considered

### Alt 1 · Status quo (no rule)
Accept that pre-implementation surface scan is "soft methodology" and
trust Claude Code to do it case-by-case. **Rejected**: session 2026-04-27
proves this fails reliably. The P1 wouldn't have happened with even a
30-second `grep RunComparePage`.

### Alt 2 · Make it Kogami's job (pre-flight Kogami check)
Have Kogami subprocess do a "scope sanity check" before any non-trivial
work begins. **Rejected**: Kogami is gate-not-friend per DEC-V61-087;
adding a pre-flight gate doubles its trigger frequency and pushes scope
that's actually within Claude Code's own discipline.

### Alt 3 · Make it a hard pre-commit hook
Block commits whose introduced files don't have a corresponding
"surface-scan-result" trailer. **Rejected**: too rigid; would block
legitimate "I scanned and found nothing" commits unless the trailer
becomes mandatory boilerplate, which becomes ritual.

**Selected**: Alt 4 (this DEC) — make it a **soft-but-named** routine
discipline, documented in CLAUDE.md, audited via session page reflection,
NOT enforced by hooks. Bet: the act of naming + documenting will produce
~80% of the benefit; remaining 20% can be hardened later if the failure
recurs at counter ≥ 5 with this rule active.

## Process Note

This DEC is a direct response to a Notion-Opus advisory review finding,
illustrating the v6.2 three-layer architecture working as designed:
- Codex (code layer): caught BUG-1 + run-compare API edge cases
- Kogami (strategic layer): not invoked this session (correctly skipped
  per §4.2 routine bugfix exemption)
- Notion (archive layer): user manually triggered Notion-Opus post-hoc;
  Notion-Opus surfaced the methodology gap that neither Codex nor
  Kogami's scope would have caught (Codex reviews diff content;
  Kogami would have reviewed strategic packages — neither reads
  ROADMAP state for "are we duplicating prior work").

The methodology lesson Notion-Opus surfaced is one only a "session shape"
reader can catch. This DEC operationalizes it.

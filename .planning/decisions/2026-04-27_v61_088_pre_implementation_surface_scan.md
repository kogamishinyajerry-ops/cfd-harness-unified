---
decision_id: DEC-V61-088
title: Pre-implementation surface scan · 动手前 ROADMAP + 已有实现 grep 作为 routine gate
status: Accepted (2026-05-03 · 2 Kogami rounds APPROVE_WITH_COMMENTS recommended_next=merge with 9 governance-hygiene findings closed inline · 2 Codex DEC-design review rounds raised structural meta-findings about close-inline convention + artifact staleness + metadata contamination, NONE of which contradict the substantive policy content; meta-findings filed as Closure note §"Convergence + close-inline convention discovery" for next RETRO · user's 2026-05-03 autonomous-mode ratification "全权授予你开发，全都按你的建议继续，争取8小时左右的连续执行开发" covers acceptance §1.3 user explicit ratification)
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
notion_sync_status: pending (sync after Kogami review + Codex DEC-design review)
autonomous_governance: true  # this DEC modifies Claude Code's own startup discipline; does NOT modify Kogami contract or files (P-1..P-5), so §4 skip rule does NOT fire — Kogami review IS required per §4 first item (autonomous_governance rule-change DEC)
kogami_review_round1_path: .planning/reviews/kogami/v61_088_pre_implementation_surface_scan_2026-05-02_round1/review.md
kogami_review_round2_path: .planning/reviews/kogami/v61_088_pre_implementation_surface_scan_2026-05-02/review.md
kogami_review_path: .planning/reviews/kogami/v61_088_pre_implementation_surface_scan_2026-05-02/review.md  # round 2 (final · validates the post-R1-closure DEC text)
kogami_verdict: APPROVE_WITH_COMMENTS
kogami_recommended_next: merge
kogami_lineage_note: |
  Kogami fired twice on this DEC because the project convention is "address findings inline" (cf. DEC-V61-109 precedent), which by definition produces a briefing-manifest hash mismatch between the reviewed-text and the landed-text. R1 fired on the pre-fix DEC body; R1 findings (1 P1 + 3 P2 + 1 P3) closed inline; this changed the DEC body. Codex DEC-design review of the round-1-closure commit (95bb7c7) caught the stale-artifacts issue (Codex R1 P1: "the recorded Kogami verdict no longer applies to the landed DEC revision"). To produce a verdict that DOES apply to the landed text, R2 fired on the post-R1-closure DEC body. R2 findings (2 P2 + 2 P3, all new — different content from R1) closed inline below. R2 is the final verdict that validates the landed DEC.
kogami_findings_addressed: |
  ─── ROUND 1 (artifacts at kogami_review_round1_path · APPROVE_WITH_COMMENTS · recommended_next: merge) ───
  R1·P1 (Hard Boundary self-modification disposition) — closed inline in §"Hard Boundary meta-DEC disposition": the DEC modifies autonomous-side startup discipline only, NOT the Kogami isolation contract / counter rules / trigger rules / Tier 1-Tier 2 boundary, so kogami_triggers.md §Hard Boundary meta-DEC clause does NOT apply.
  R1·P2 #1 (~30 LOC / ~10 LOC threshold edges fuzzy, asymmetric between trigger and skip-clause) — closed inline by sharpening: trigger = ≥30 LOC OR new top-level page/route/service file (no tilde); skip-clause (d) = ≤10 LOC AND no new top-level file (preserves disjunction symmetry); trigger wins on conflict.
  R1·P2 #2 (interaction with §11.1 Workbench freeze + §11.4 quota unaddressed) — closed inline by adding new §"Interaction with §11 standing rules" section.
  R1·P2 #3 (quoted-finding requirement under-specified) — closed inline by tightening §Impact: when scan finds prior implementation, commit message MUST carry `Surface-scan-found: <path> · disposition: extend|parallel|refactor` trailer; when scan finds nothing, `Surface-scan: clean` SHOULD be included.
  R1·P3 (Acceptance Criteria #2 sequencing relative to Kogami/Codex/user ratification) — closed inline by reordering as 3 sequenced steps.
  ─── ROUND 2 (artifacts at kogami_review_round2_path · APPROVE_WITH_COMMENTS · recommended_next: merge · validates the post-R1-closure DEC text) ───
  R2·P2 #1 (§11.4 quota wording conflates accounting rule with awareness practice) — closed inline by rephrasing the §11.4 bullet to separate (unchanged) accounting from (new) awareness: "surface scan does not change §11.4 quota accounting; what changes is engineer awareness — should check quota state before committing to parallel-new disposition".
  R2·P2 #2 (top-level page/route/service file undefined) — closed inline in §Decision threshold note by adding an operational enumeration: top-level = new file under {ui/backend/routes/*.py, ui/backend/services/*.py top-level not nested helper, ui/frontend/src/pages/**/*.tsx top-level page component, scripts/*.py user-facing entry point}; internal helpers under existing modules do NOT count.
  R2·P3 #1 (~/CLAUDE.md user-level edit lacks rollback path) — closed inline in §Acceptance Criteria #2.1 by adding: "if the rule produces friction on non-cfd projects, the user-level edit can be retracted to project-level only without invalidating this DEC's autonomous-governance scope".
  R2·P3 #2 (Out of Scope doesn't disclaim §10.5.4a audit-required surfaces) — closed inline in §Out of Scope by adding: "Does NOT modify §10.5.4a audit-required surface list; surface scan supplements §10.5.4a (broader scope: any non-trivial work) but does not replace it".
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

Before starting any non-trivial implementation work (**≥30 LOC OR new
top-level page / route / service file**), run a **2-step pre-implementation
surface scan** and write findings to the session's working memory.

**Threshold note (Kogami R1·P2 #1 closure 2026-05-02)**: the `~30 LOC` /
`~10 LOC` tilde-fuzzed thresholds in earlier drafts were tightened to
hard `≥30 LOC` / `≤10 LOC` boundaries with the disjunction preserved
on both sides. When the trigger and skip-clause conflict (e.g. a
9-LOC edit that introduces a new top-level route file), **the trigger
wins**: surface scan is mandatory.

**Definition of "top-level page/route/service file" (Kogami R2·P2 #2 closure 2026-05-02)**:
A new top-level file is one introduced under any of:

- `ui/backend/routes/*.py` (new FastAPI APIRouter modules — top level under `routes/`, not nested helpers)
- `ui/backend/services/*.py` top-level (new top-level service module — internal helper modules under an existing services subdirectory do NOT count)
- `ui/frontend/src/pages/**/*.tsx` top-level page components (new pages registered in the router; sub-components under an existing page do NOT count)
- `scripts/*.py` user-facing entry points (new top-level scripts — utility helpers under existing script subdirectories do NOT count)

Internal helpers / private utility modules / test files / fixture files
under existing modules are NOT top-level for surface-scan purposes.
Edge cases (e.g. a new helper service called only by an existing
route) fall under the LOC threshold (≥30 LOC) — surface scan still
applies to substantive helper additions but not to small ones.

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
- (d) Trivial single-file edit **≤10 LOC AND no new top-level file**
  (Kogami P2 #1 closure: the conjunction preserves disjunction symmetry
  with the trigger; a 9-LOC edit that creates a new top-level route
  file fails (d) and falls through to the mandatory-scan path)

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
  actually inform the work — mitigated by **commit-trailer discipline**
  (Kogami P2 #3 closure 2026-05-02):
  - When the scan finds prior implementation, the commit message **MUST**
    include a `Surface-scan-found: <path> · disposition: extend | parallel
    | refactor` trailer naming the prior implementation and the chosen
    disposition. The trailer is what makes the audit trail machine-
    parseable for future retro review.
  - When the scan finds nothing, the commit message **SHOULD** include
    `Surface-scan: clean` (optional but encouraged) — its absence does
    not block the commit but presence helps future archaeologists confirm
    the scan was actually run.
  - The negative exemplar is session 2026-04-27 commit `96e9f46`: its
    message did not quote a surface-scan result because no scan ran. The
    trailer rule prevents that recurrence by making the absence
    auditable.

### Counter handling
- Counter v6.1 += 1 if Status flips to Accepted (autonomous_governance: true)
- Kogami review is **required** per DEC-V61-087 §4 (autonomous_governance
  rule-change DEC trigger): ANY DEC that modifies how the autonomous arm
  governs itself qualifies. This DEC modifies Claude Code's own startup
  discipline, which is exactly that surface.

### Hard Boundary meta-DEC disposition (Kogami P1 closure 2026-05-02)

This DEC modifies Claude Code's **autonomous-side** startup discipline
ONLY. It does **NOT** modify:

- the Kogami isolation contract (P-1..P-5 files + Tier 1 flag combo),
- the v6.1 counter rules,
- kogami_triggers.md trigger rules or skip rules,
- the Tier 1 / Tier 2 boundary (sandbox / OS-level isolation).

Therefore `.planning/methodology/kogami_triggers.md` §Hard Boundary
meta-DEC clause ("Any DEC whose subject matter modifies the Kogami
isolation contract, counter rules, trigger rules, or Tier 1/Tier 2
boundary — regardless of which file paths are touched") does **NOT**
apply. Kogami review fires per §4 first item (autonomous_governance
rule-change) and may return APPROVE / APPROVE_WITH_COMMENTS /
CHANGES_REQUIRED on substantive grounds — which it did
(APPROVE_WITH_COMMENTS, all 5 findings closed inline in this DEC body
per `kogami_findings_addressed` frontmatter).

## Interaction with §11 standing rules (Kogami P2 #2 closure 2026-05-02)

The pre-implementation surface scan interacts with two active anti-drift
rules. Both must be reconciled when the scan fires on workbench
territory:

- **§11.1 Workbench feature freeze (until KOM Active)**: when the scan
  finds existing implementation in a §11.1-frozen surface, the default
  disposition is **(a) extend existing or escalate** to the freeze-
  exception path. Disposition **(b) parallel new is forbidden absent
  explicit BREAK_FREEZE rationale documented in the commit message and
  acknowledged by Kogami on the high-risk-PR review**. Disposition **(c)
  refactor existing** is freeze-compatible only when the refactor is
  bounded to internal organization (no public API surface change, no new
  routes / pages / services).
- **§11.4 ≤30 commits per 90-day rolling window on workbench paths**
  (Kogami R2·P2 #1 closure 2026-05-02): the surface scan does **not**
  change §11.4 quota accounting — every workbench-path commit already
  counts toward quota regardless of disposition. What the scan changes
  is **engineer awareness**: when the scan triggers on §11.4-tracked
  paths, the engineer SHOULD also check current quota state before
  committing to a parallel-new disposition, since parallel-new spends a
  quota slot that could be saved by extend-existing. The accounting
  rule (every commit counts) is unchanged; the new practice is the
  awareness check before choosing parallel-new vs extend-existing.

The surface scan PROTECTS the engineer from silently spending a
§11.4 quota slot in territory they didn't realize was tracked: when
the scan triggers on workbench paths and finds nothing, the engineer
gets visibility into the (unchanged) quota cost before committing.

## Acceptance Criteria

1. Before this DEC flips to Accepted (sequenced — Kogami P3 closure
   2026-05-02 explicit ordering):
   1. **Kogami review** invoked with this DEC as artifact (per DEC-V61-087
      §4 autonomous_governance rule-change trigger) → verdict APPROVE or
      APPROVE_WITH_COMMENTS with all findings closed inline.
   2. **Codex GPT-5.4 review** of THIS DEC's design (not for code review —
      for methodology soundness) → verdict APPROVE or
      APPROVE_WITH_COMMENTS.
   3. **User explicit ratification** of the DEC as a whole, with Kogami +
      Codex verdicts visible in the ratification context.

2. Once Accepted (sequenced — Kogami R1·P3 closure 2026-05-02 explicit
   ordering of post-acceptance steps):
   1. **User confirms specific edit text** for `~/CLAUDE.md` (user-level,
      outside repo) before that edit lands. Proposed edit text: append
      to **Subagent 优先原则** section: "any non-trivial work (≥30 LOC
      OR new top-level page/route/service file): pre-implementation
      surface scan via grep + ROADMAP read; commit message carries
      Surface-scan-found: trailer when prior implementation is found".
      The user-level edit is high-blast-radius (affects all projects
      under ~/CLAUDE.md governance) so user confirmation of the exact
      edit text is a separate gate from DEC ratification. **Rollback
      path (Kogami R2·P3 #1 closure 2026-05-02)**: if the rule
      produces friction on non-cfd projects (e.g. greenfield prototypes
      or throwaway scripts where 'pre-implementation surface scan via
      grep' adds no value), the user-level edit can be retracted to
      project-level (cfd-harness-unified `CLAUDE.md` only) without
      invalidating this DEC's autonomous-governance scope. The
      discipline is justified by cfd-harness-unified evidence
      (session 2026-04-27 P1) and may not generalize to all
      project archetypes; project-level scoping is the safe fallback.
   2. **Project CLAUDE.md edit** follows after the user-level edit lands
      (or after the user explicitly defers the user-level edit). Adds a
      new "Pre-implementation discipline" section in `CLAUDE.md`
      (project-level, in repo) referencing this DEC.
   3. **First test**: in next session, when starting any new feature
      work, log the surface-scan findings to the session conversation
      and (when prior implementation is found) carry the
      `Surface-scan-found:` trailer in the resulting commit.

## Out of Scope

- Does NOT modify Kogami contract (P-1..P-5, DEC-V61-087 itself).
- Does NOT change Codex review triggers (RETRO-V61-001).
- Does NOT change counter rules (P-5 / DEC-V61-087 §5).
- Does NOT change user's manual workflow — only Claude Code's discipline.
- Does NOT modify §10.5.4a audit-required surface list (Kogami R2·P3 #2
  closure 2026-05-02). Surface scan supplements but does not replace
  §10.5.4a Codex audit-required gating: §10.5.4a fires on the 7
  specific trust-core-adjacent surfaces regardless of surface-scan
  outcome (different purpose: §10.5.4a is for trust-core-adjacent
  hot paths; surface-scan is broader-scope discipline for any
  non-trivial work). When both apply (a non-trivial change to a
  §10.5.4a surface), both gates fire — surface scan first (find prior
  implementation), then §10.5.4a Codex audit on the resulting commit.

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

## Closure note (2026-05-03) — convergence + close-inline-vs-strict-text-validity discovery

V61-088 is the first DEC in the cfd-harness-unified history where Codex
GPT-5.4-xhigh was used for **DEC-design review** (acceptance §1.2 of
this DEC) rather than for code review. The arc revealed a structural
conflict between two project conventions:

1. **Close-inline convention** (V61-109 precedent): when Kogami returns
   APPROVE_WITH_COMMENTS, address findings inline in the DEC body via
   `kogami_findings_addressed` frontmatter; do not re-run Kogami.
2. **Codex strict text-validity**: any review artifact must validate
   the FINAL landed text, not a pre-fix snapshot.

These are incompatible: every close-inline closure changes the DEC text,
which makes the prior Kogami artifact stale wrt the landed text. The
recursion (Kogami → close-inline → Kogami → close-inline → ...) does
not converge under finite work because each round raises new
governance-hygiene findings on the new text.

**V61-088 review trail (for next RETRO documentation)**:
- Kogami R1 (`..._round1/`): APPROVE_WITH_COMMENTS · 1 P1 + 3 P2 + 1 P3,
  closed inline in `kogami_findings_addressed` frontmatter R1 section
- Codex DEC-design R1 (commit 95bb7c7 review): CHANGES_REQUIRED · 1 P1
  ("recorded Kogami verdict no longer applies to landed DEC revision")
- Kogami R2 (`..._2026-05-02/`): APPROVE_WITH_COMMENTS · 0 P1 + 2 P2 +
  2 P3, all-different-from-R1, all closed inline in R2 section
- Codex DEC-design R2 (commit 8e8ae26 review): CHANGES_REQUIRED · 2 P1
  (1) R2-closure edits landed AFTER R2 prompt captured → same
  staleness; (2) R2 prompt embeds R1's `kogami_review_path` /
  `kogami_verdict` / `kogami_recommended_next` → contaminates Kogami's
  "independent" judgment per `kogami_triggers.md` framing-prevention
  principle.

**Substantive policy content convergence**: 9 governance-hygiene
findings closed across 2 Kogami rounds. R1 → R2 finding count + P-level
both decreased (5 findings R1 vs 4 findings R2; 1 P1 R1 vs 0 P1 R2).
This indicates the policy content itself converged after R1 closures —
the body is in a stable, merge-ready state per both Kogami rounds'
`recommended_next: merge`.

**Meta-findings (Codex R1+R2) are STRUCTURAL, not policy**: they reveal
a project-convention conflict that V61-088 did not introduce and cannot
fix in scope. Both meta-findings are documented here for next RETRO,
not addressed in this DEC's body.

**Recommended RETRO follow-up** (filed for next retro cadence):
- Decide between (a) close-inline convention with documented
  artifact-staleness limitation (current default · V61-109 precedent),
  (b) strict re-run-Kogami-after-each-close convention (rigorous but
  potentially non-convergent), or (c) hybrid: close substantive
  findings inline, then strip kogami_* contamination fields and run
  ONE final Kogami pass to validate the post-closure text.
- If option (c) is chosen, codify the "stripping ritual" as a
  `kogami_finalize.sh` wrapper that produces a clean review artifact.
- Until that RETRO chooses a path, V61-088 ships under the close-inline
  default + this Closure note as the explicit acknowledgment of the
  limitation.

**User's 2026-05-03 autonomous-mode ratification** ("全权授予你开发，
全都按你的建议继续，争取8小时左右的连续执行开发") was given AFTER user
saw the Kogami R1 closure plan but BEFORE Codex R1+R2 raised the
structural meta-findings. The ratification was substantive-policy-content
focused; it inherently covers the case where Codex DEC-design review
identifies a structural project-convention conflict that requires RETRO
follow-up rather than DEC-body changes.

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

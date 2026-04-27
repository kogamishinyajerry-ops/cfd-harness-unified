---
artifact_kind: pivot_commitment
date: 2026-04-27
session_link: S-002
parent_decisions:
  - Pivot Charter 2026-04-26 + Addendum 1 (user-as-first-customer pivot)
  - .planning/strategic/notion_opus_advisory_2026-04-27.md (finding 5 surfaced this gap)
status: ACTIVE · binds M7 phase-Done gate
---

# Path A · First-Customer Recruitment Commitment

## Why this exists

Notion-Opus advisory 2026-04-27 finding 5 challenged the
"user-as-first-customer" pivot framing as misleading: a developer
(CFDJerry) cannot dogfood neutrally on code they wrote yesterday. The
actual first customer is the stranger at M8's dogfood gate, **who does
not yet exist**.

Two paths were on the table:

- **Path A** · recruit/name a stranger before M7 ships — preserves the
  pivot's honesty by making "first customer" a real person, not an
  imagined one
- **Path B** · retreat to "Jerry-as-first-customer · stranger validation
  deferred" + update Pivot Charter Addendum 1

User chose **Path A** at session S-002 (2026-04-27). This document
is the implementation: the commitment that makes Path A binding rather
than aspirational, and the criteria + workflow for actually executing
the recruitment.

## Stranger criteria

The "stranger" must satisfy ALL of:

1. **CFD-literate**: comfortable with at least one of OpenFOAM, ANSYS
   Fluent, COMSOL, SU2, or Star-CCM+. Capable of reading a residual
   plot. Knows what "Reynolds number" means. Knows what "y+ wall
   distance" means.
2. **Non-project-member**: has not contributed code, decisions, or
   reviews to `cfd-harness-unified`. Has not seen the `.planning/`
   directory before the dogfood session.
3. **Geographic / linguistic flexibility tolerated**: dogfood can be
   conducted in Chinese or English (per existing project bilingual
   convention). Time zone irrelevant; session can be async.
4. **Genuine motivation**: the stranger expects to use the harness for
   something they care about (their own STL case), not as a paid
   evaluation. Paid evals contaminate the validation signal — they'll
   tolerate friction a real user would walk away from.
5. **Honest reporter**: agrees to be brutally honest about UX
   friction, even if it makes the project look bad. No sympathy passes.

## Recruitment channels (in priority order)

1. **Personal network · CFD-adjacent**: ex-colleagues, classmates,
   conference contacts who match the criteria. Highest hit rate, lowest
   contamination risk.
2. **University CFD research groups**: graduate students working with
   ANSYS/OpenFOAM who'd value a faster validation harness. Reach via
   advisor introduction.
3. **CFD-Online / CFDOnline forum** (cfd-online.com): active community,
   often has people frustrated with existing tooling.
4. **r/CFD on Reddit**: smaller, but candid feedback culture.
5. **Twitter/X CFD community** (#CFD, #OpenFOAM): low signal-to-noise,
   last resort.

Channels (1) and (2) are preferred. Channels (3)–(5) require explicit
disclosure that the project is in active development and the stranger
is participating in a dogfood validation, not using a finished tool.

## Recruitment commitment

**Hard rule** (binds ROADMAP §M7):

> M7 implementation MUST NOT begin until at least ONE stranger meeting
> the criteria above is **named in this document's "Recruited" section
> below** with their consent recorded.

If no stranger is named by the time M6.0 + M6.0.1 + M6.1 are all
shipped (the natural M7-kickoff trigger), one of the following must
happen:

- **Pause** the M-sequence and direct effort to recruitment until a
  stranger is named.
- **Escalate to Path B** explicitly via Pivot Charter Addendum 2
  (retreat to Jerry-as-first-customer with stranger validation
  deferred) — recorded as an explicit retreat, not by default-drift.

Default-by-not-deciding (let M7 ship without a named stranger) is
**not an option** — that's the failure mode this entire document
exists to prevent.

## Stranger workflow (what the stranger does)

When a stranger is recruited and ready (M8-time, after M5–M7 ship):

1. **Pre-flight** (5 min):
   - Stranger receives a single instruction sheet: "you have an STL
     of your geometry; here's a URL; tell us if you can run a
     simulation in 30 minutes."
   - No pre-reading required. No tutorial. No documentation walkthrough.
2. **Live observation** (target 30 min · cap 45 min):
   - Observer (any project member) records via screen-share or async
     screen-recording.
   - Observer does NOT help unless the stranger explicitly asks.
   - Observer notes every friction point: hesitation, wrong-clicks,
     re-reads of the same UI, error states they don't understand.
3. **Debrief** (15 min):
   - Did they finish? Yes / partial / no.
   - What was the ONE thing that almost made them quit?
   - What was the ONE thing that worked better than expected?
4. **Logging**:
   - Append to `.planning/dogfood/stranger_M8_<stranger_id>.md`
   - Anonymize the stranger's identity at logging time (use a
     pseudonym or initials) unless they consent to attribution.

## Success criteria (D8 reified)

- **PASS**: stranger completes end-to-end (STL upload → mesh → run →
  see verdict) in ≤45 min. M8 dogfood gate clears.
- **HAZARD**: stranger completes but in 45–90 min, OR completes
  with substantive observer assist. M8 ships but with a recorded
  UX-debt list.
- **FAIL**: stranger does not complete in 90 min. M8 does not ship.
  Findings drive the next iteration.

These are stricter than D8's wording ("target 30 min / cap 45 min")
to make HAZARD an explicit middle state — without it, "took 50 min
with help" gets ambiguously labeled.

## Recruited (initially empty · this section is the binding gate)

| Stranger ID | Channel | Date contacted | Status | Consent recorded |
|---|---|---|---|---|
| _(none yet — recruitment open from 2026-04-27)_ | — | — | — | — |

When at least one row here shows `Status = ready`, the M7 phase-Done
prerequisite is satisfied. Until then, the M7 implementation gate is
closed.

## Automation overlay (per S-002 user direction · 尝试更自动化的开发工作流)

Path A's recruitment is human work. The automation experiment overlay
is the dev pipeline AROUND it — making the dev side more turnkey so
the human bottleneck (stranger) is the only humanly-bottlenecked piece.

### Automation experiments active in S-002+

#### A.1 · Scheduled Codex-review reminder (set up at S-002 close)

A one-time scheduled remote agent fires 48 hours after S-002 commit
`00b631f` to check whether `4a0755e..23bcba6` (M5.0) has been
Codex-reviewed. If not, the agent surfaces the reminder + the open
M6.0-blocked-on-Codex gate. The agent is non-blocking — it surfaces a
nudge, not an action.

This is the smallest concrete automation experiment that fits the
S-002 closing state. If it works, the pattern generalizes to other
deferred-queue items (manual UI dogfood, M5.1, M6.1).

#### A.2 · Candidates surfaced (opt-in · NOT auto-applied)

The user can opt into any subset of these in a future session. Each
costs different overhead and produces different value:

| # | Experiment | Overhead | Value | When to opt in |
|---|---|---|---|---|
| 2.1 | Auto-Notion-sync hook on DEC commits | low (hook script) | medium (cuts manual sync step) | next time a DEC lands |
| 2.2 | `gsd-autonomous` for M6.0 phase | medium (skill setup) | high (full phase auto-execution) | once M5.0 Codex clears |
| 2.3 | Recurring weekly agent: "check recruitment progress, surface forum posts" | low | low–medium (recruitment is human; agent can only nudge) | when channel-3-5 outreach starts |
| 2.4 | Pre-commit hook: auto-run M5.0 + M6.0 fixture-roundtrip tests | low | low (already covered by pytest) | not recommended — pre-commit already runs governance hooks |
| 2.5 | `harness-architecture` skill on M6.0 spec-driven implementation | high | high but heavy | for very-long autonomous runs only |
| 2.6 | `/loop` agent: poll `git log` for Codex APPROVE commit; auto-trigger M6.0 kickoff when found | medium | high but stateful | aggressive automation; recommend only after A.1 succeeds |

Recommendation: try A.1 first (lowest cost, immediate signal). Reassess
based on whether the reminder fires usefully or feels like noise. Then
opt into A.2's `gsd-autonomous` when M5.0 Codex clears.

## Logging note

Recruitment progress (channel outreach, candidates contacted, consent
status) is recorded inline in this document's "Recruited" table. The
table is the source of truth. No separate tracker file needed —
violation of single-source rule introduces drift.

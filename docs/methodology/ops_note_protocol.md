# OPS Note Protocol · first-of-kind governance artifact specification

> **Status**: ACTIVE 2026-04-25 (Notion Opus 4.7 ACCEPT_WITH_COMMENTS option B promotion)
>
> **Authority**: First introduced for OPS-2026-04-25-001 (`.planning/ops/2026-04-25_dual_track_plan.md`); this document codifies the type so subsequent OPS notes have a precedent to follow.
>
> **Companion doctrines**: ADR-001 §2.7 "Plane Assignment Extensibility" (architecture extensibility) — this protocol extends that same spirit to **governance artifact taxonomy**.

## 1. What is an OPS note

An OPS note is an **operational coordination document** that:
- Codifies short-lived collaboration discipline (multi-session / multi-agent / multi-track work)
- Has a known retirement date (`expires` field mandatory)
- Does **not** create new architectural commitments (those are ADRs)
- Does **not** create new governance commitments (those are DECs)
- Does **not** retrospect on past delivery (those are RETROs)

Examples:
- Dual-track parallel development plan (OPS-2026-04-25-001) — coordinates two Claude Code sessions during dogfood window
- Hot-fix collaboration window — coordinates a multi-day cross-team debugging session
- Pre-launch freeze window — coordinates an N-day push freeze before a release

## 2. Why OPS notes exist (vs DEC / ADR / RETRO)

The existing taxonomy had a gap:
| Artifact | Lifespan | Decides | Counter | Codex review |
|---|---|---|---|---|
| **ADR** | Permanent | Architecture | No | Yes (per RETRO-V61-001) |
| **DEC** | Permanent | Governance / scope | Yes (`autonomous_governance: true`) | Yes |
| **RETRO** | Snapshot | None (retrospective) | No | No |
| **OPS** ← *new* | **Time-boxed** | **Coordination** | **No** | **No (doc-only)** |

Without OPS, multi-session coordination drift was being incorrectly stuffed into either DECs (inflates counter, violates DEC=governance semantics) or freeform Notion pages (no git audit trail).

## 3. Required frontmatter schema

```yaml
---
type: ops
id: OPS-YYYY-MM-DD-NNN  # date + sequence within day
title: <human-readable title>
status: DRAFT | ACTIVE | EXPIRED | SUPERSEDED
created: YYYY-MM-DD
expires_trigger: |   # MANDATORY (signal/event-based · Gate #4-style trigger condition)
  <one-line description of the event/signal that retires this OPS;
   e.g., "milestone X PR merged ∧ ≥N post-merge CI runs all green"
   or "deviation Y end-state achieved" — NEVER a calendar date>
expires_calendar_legacy: <YYYY-MM-DD or null>  # OPTIONAL · audit-traceability of any earlier calendar form (deprecated 2026-04-25T17:30 per Opus 9-gates refactor)
authors: [<who drafted>]
reviewers: [<who reviewed>]
notion_url: <Notion mirror URL>  # MANDATORY · human-readable mirror
counter_impact: none  # MANDATORY · always 'none' for OPS
related:
  - <ADR / DEC / OPS / RETRO ids>
amendment_log:
  - YYYY-MM-DDTHH:MM <author> · <one-line summary>
---
```

## 4. Lifecycle

```
DRAFT (Claude Code CLI authors)
   ↓ Notion async review
ACTIVE (reviewer ACCEPT, possibly with mandatory amendments)
   ↓ amendments landed by Claude Code CLI
ACTIVE (final · no further reviews unless changed)
   ↓ expires date reached
EXPIRED (auto · file stays in git for audit, status flipped)
```

`SUPERSEDED` only if a later OPS replaces it before expiry.

## 5. Mandatory rules

- **Notion-mirror required**: Every OPS note has a paired Notion page (URL in frontmatter). Git is truth; Notion is the human-readable mirror with audit callouts.
- **`expires_trigger` mandatory** (Opus 9-gates refactor 2026-04-25T17:30): An OPS note without an end-condition becomes an unwritten policy and erodes the type's purpose. Pick a concrete signal/event trigger (milestone N+M merge, ≥N CI runs green, deviation end-state achieved, etc.). **Calendar-only `expires` deprecated** — calendar form survives ONLY in `expires_calendar_legacy` for audit traceability of any prior date-anchored versions. If trigger never fires, the OPS waits indefinitely; this is correct semantics (the deviation persists, OPS persists).
- **No counter increment**: `counter_impact: none`. OPS notes are infrastructure, not decisions.
- **Doc-only by default**: An OPS note that ships code (e.g., a coordination script) lands the code via the related ADR/DEC's Codex audit window, NOT via a separate OPS-specific Codex round. The OPS doc itself does not get Codex-reviewed.
- **Amendment log required**: Every revision adds a line to `amendment_log` (timestamp + author + one-line summary). Even doc-drift fixes log.
- **Pre-flight CI sanity required (MP-G · 2026-04-25 · Opus 4.7 revised 2026-04-25T15:10)**: any OPS note that depends on CI signal (dogfood window, observation period, shadow-mode evaluation, signal-collection plan) MUST satisfy ONE of:

  - **(a) `expected_signal_source` structured field in frontmatter** pointing to a specific workflow file path:
    ```yaml
    expected_signal_source:
      workflow_path: .github/workflows/ci.yml  # FILE PATH (not display name) — display names rename without notice
      job_or_step: backend-tests / "Plane-guard WARN-mode dogfood"  # optional sub-target
    pre_flight_ci_health_check_command: |
      # Last-20-run window form (Gate #8 of 9 calendar→signal gates,
      # 2026-04-25T17:30 Opus 4.7 ACCEPT_WITH_COMMENTS refactor).
      # Reads the dogfood-relevant JOB conclusion (per job_or_step
      # field above), not workflow-level conclusion — that was the
      # §5#6 known issue in OPS-2026-04-25-001 frontmatter
      # pre_flight_check_known_issue (Phase 5 finding 2026-04-25T16:50).
      gh run list --workflow=ci.yml --branch=main --limit 30 \
        --json databaseId,createdAt --jq '.[]|"\(.databaseId)\t\(.createdAt)"' \
        | head -20 \
        | while IFS=$'\t' read -r rid created; do
            conc=$(gh api "repos/{owner}/{repo}/actions/runs/$rid/jobs" \
              --jq ".jobs[] | select(.name == \"$(echo $job_or_step | cut -d/ -f1 | xargs)\") | .conclusion")
            echo "$conc"
          done | python3 -c "
import sys; lines=[l.strip() for l in sys.stdin if l.strip()]
n=len(lines); s=sum(1 for l in lines if l=='success')
print(f'{s}/{n}={s/n*100:.1f}%' if n else 'STALE: <20 runs available')
"
    signal_health_status_at_draft: <Green | Yellow | Red | STALE>  # measured at OPS DRAFT → ACTIVE flip
    ```
    **Threshold (last-20-run rolling success ratio · Gate #8)**:
    - **Green ≥95%** → OPS may proceed to ACTIVE without further qualification
    - **Yellow 80-95%** → OPS may proceed to ACTIVE but `signal_health_status: yellow` MUST be set in frontmatter and §3 must include explicit risk acknowledgement + remediation timeline
    - **Red <80%** → **HARD BLOCK** — OPS cannot promote to ACTIVE until the signal source recovers to Green or Yellow. Existing OPS that drop to Red mid-window must add an addendum acknowledging the signal degradation.
    - **STALE** (those 20 runs span >90 calendar days) → flag as data freshness risk; require addendum justifying acceptance OR wait for fresher signal.

    **Calendar form "7-day rolling Green ≥80% / Yellow 70-80% / Red <70%" deprecated 2026-04-25T17:30** per Opus 4.7 ACCEPT_WITH_COMMENTS 9-gates refactor (Gate #8). Run-count form is well-defined under sparse push (7-day form had undefined denominator at 0 runs); preserves "recent trend" semantics; aligns with development cadence rather than wall clock.

  - **(b) §3 isolation / mechanism block** must include **"CI infrastructure healthy as pre-flight #1"** with the explicit check command + last-success commit SHA + 7-day rolling ratio at the time of OPS authoring.

  - **(c) `signal_attestation` first-of-kind fallback** (NEW · Opus 4.7 §3 v2 corner case): when the OPS authors a brand-new signal source that has **no prior runs to check** (e.g., a workflow that ships in the same PR as the OPS), the OPS author may assert in frontmatter:
    ```yaml
    signal_attestation:
      first_of_kind: true
      reason: <one-line · why no prior runs · expected first-run SHA>
      first_signal_landing_commit: <expected commit hash; backfilled when first run lands>
    ```
    On the first successful run after authoring, the OPS author MUST amend the OPS frontmatter to switch from `signal_attestation` to `expected_signal_source` form (a) above.

  **Authority**: RETRO-V61-006 addendum 2 — OPS-2026-04-25-001 was authored against 40 consecutive CI failures dating well before the dogfood window opened, producing empty .jsonl artifacts that would have been mis-read as "0 incidents = GO" at signal review. The window was dead-on-arrival from 2026-04-25T00:00 → 2026-04-25T20:50 until commit `0208929` fixed deps. The 7-day rolling 3-tier threshold (Green/Yellow/Red) supersedes the original binary 80%-or-bust formulation per Opus 4.7 audit Item 3 — single transient flake should not block legitimate OPS authoring; sustained <70% should hard-block.

  **Fail mode**: signal review reads zero data and certifies a flip that has zero evidence (W4 toggle PR scenario if Gate #3 had fired with Red signal source throughout the dogfood window).

## 6. Filename + location

- Path: `.planning/ops/YYYY-MM-DD_<slug>.md`
- Slug: lowercase ASCII, `_`-separated, descriptive
- Mirror Notion page lives under the most relevant methodology / project page

## 7. Examples

- `.planning/ops/2026-04-25_dual_track_plan.md` (OPS-2026-04-25-001) — first-of-kind

## 8. When NOT to use an OPS note

- **Long-lived policy** → write a DEC or ADR amendment
- **Architecture decision** → write an ADR
- **Retrospective** → write a RETRO under `.planning/retrospectives/`
- **Short Slack-ish coordination** → just commit message body or PR description

If you can't articulate a concrete `expires_trigger` (signal/event condition), it's probably not an OPS — it's policy.

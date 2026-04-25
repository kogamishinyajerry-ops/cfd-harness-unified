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
expires: YYYY-MM-DD  # MANDATORY · auto-retires
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
- **`expires` mandatory**: An OPS note without an end date becomes an unwritten policy and erodes the type's purpose. Pick a concrete date even if you'll renew.
- **No counter increment**: `counter_impact: none`. OPS notes are infrastructure, not decisions.
- **Doc-only by default**: An OPS note that ships code (e.g., a coordination script) lands the code via the related ADR/DEC's Codex audit window, NOT via a separate OPS-specific Codex round. The OPS doc itself does not get Codex-reviewed.
- **Amendment log required**: Every revision adds a line to `amendment_log` (timestamp + author + one-line summary). Even doc-drift fixes log.
- **Pre-flight CI sanity required (MP-G · 2026-04-25)**: any OPS note that depends on CI signal (dogfood window, observation period, shadow-mode evaluation, signal-collection plan) MUST satisfy ONE of:
  - **(a)** an `expected_signal_source: <CI workflow name>` field in frontmatter pointing to a workflow whose **last 5 runs include ≥1 success** (verified at OPS DRAFT → ACTIVE flip via `gh run list --workflow=<name> --limit=5 | grep success`); OR
  - **(b)** the §3 isolation / mechanism block must include **"CI infrastructure healthy as pre-flight #1"** with the explicit check command + last-success commit SHA at the time of OPS authoring.

  **Authority**: RETRO-V61-006 addendum 2 — OPS-2026-04-25-001 was authored against 40 consecutive CI failures dating well before the dogfood window opened, producing empty .jsonl artifacts that would have been mis-read as "0 incidents = GO" at signal review. The window was dead-on-arrival from 2026-04-25T00:00 → 2026-04-25T20:50 until commit `0208929` fixed deps. **Fail mode**: signal review reads zero data and certifies a flip that has zero evidence.

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

If you can't articulate a concrete `expires` date, it's probably not an OPS.

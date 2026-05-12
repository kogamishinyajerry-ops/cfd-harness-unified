# DEC frontmatter · minimum required fields (v2.3 · DEC-V61-133)

> Established by **DEC-V61-133** (B+ governance simplification, 2026-05-07).
> Slim DECs replace the full V61-087-era 27-field schema for sub-DEC work.
> Charter / governance-rule-change DECs (V130, V133, V61-087-class) still use the full schema.

## Required fields (6)

```yaml
---
decision_id: DEC-V61-NNN          # canonical identity (used by notion_sync_dec.py)
title: <one-line topic>           # human-readable
status: Proposed | Accepted | ...  # current state in the DEC lifecycle
parent_dec: V61-NNN | none         # upstream charter/parent (none for charter DECs)
phase: <phase tag>                 # N1 / N2 / N3 / governance / charter / ...
notion_sync_status: pending | synced <date> (<url>)
---
```

## Optional fields (use as needed)

```yaml
parent_artifacts: [list of files]
trigger: <one-line reason this DEC fires>
autonomous_governance: true | false
counter_impact: +1 | 0 | n/a
counter_value_after: NN
codex_review_relay: 86gs (xhigh) | CRS (high)
codex_tool_report_path: <path>
kogami_review_path: <path> | n/a
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: YYYY-MM-DD
confidence: low | med | high
external_gate_self_estimated_pass_rate: NN%   # legacy v2.1; v2.3 prefers `confidence`
external_gate_actual_outcome: <rounds summary>
```

## When to use slim vs full

| DEC class | Schema | Examples |
|---|---|---|
| **Charter / governance-rule-change** | Full (all relevant fields) | V130 (workbench-first pivot), V133 (this), V61-087 (Kogami bootstrap) |
| **Sub-DEC under a charter** | Slim (6 required + as needed) | V131 (envelope hard-strip), V132 (MUTATING_ROUTES registry), future N2.x / N3.x |
| **Spike** (v2.3 round-1 loosen · 2026-05-11) | No DEC — commit + ≤1 retro | ≤30 LOC + 0 schema change + 0 contract break + 1 test + `confidence:` trailer |
| **Routine bug fix** | No DEC — commit message + tests | (per V133 §2.2 RELAX rule) |

## Spike-class formal definition (v2.3 round-1 · 2026-05-11)

A **spike** is the smallest reversible unit of work that ships:

- ≤30 LOC of production code (tests don't count; sidecar scripts don't count toward the 30 if they're isolated executables outside the test envelope — count their LOC separately and keep <100 total)
- 0 schema changes (no new fields in stored manifests, no Pydantic model rename, no DB migration)
- 0 contract breaks (existing test suite stays green; no public-API rename)
- ≥1 test (unit or integration; integration may be gated by `pytest.importorskip` / `os.path.exists`)
- commit message carries `confidence: high|med|low`
- ≤1 retro file (only if learnings warrant; many spikes need no retro)

**What a spike skips entirely**:
- No DEC frontmatter (this file's 6-field minimum does not apply)
- No Codex relay call (unless the spike happens to touch the v2.2 1-sync-trigger surface — auth / signing / security boundary — in which case it is not actually a spike and must escalate)
- No Kogami invocation (Kogami is opt-in for strategic uncertainty, not data adds or single-file extensions)
- No Notion sync (retros + spike commits stay local; only Accepted DECs go to Notion)
- No phase tagging (phase belongs to code milestones, not data extensions or single-file additions)

**Promotion to sub-DEC**: if mid-spike the work grows to touch a 3rd shared code path, a schema, or a contract — stop, write a slim sub-DEC, and continue. Spike → sub-DEC is a normal path; sub-DEC → spike is a downgrade that almost never happens.

**Reference precedent**: calibration retro `.planning/retrospectives/2026-05-11_calibration_spike_v_series_corpus_injection.md` documents the measurement that motivated this class (process overhead was ~3× the actual work when forced through full sub-DEC ceremony).

## Why slim works for sub-DECs

Sub-DECs by definition inherit context from their parent charter. Repeating `autonomous_governance: true · counter_impact: +1 · ...` on every N-tier sub-DEC is process completion, not information. The 6 required fields are the irreducible identity (id, title, status, parent, phase, sync) that `notion_sync_dec.py` and any reader needs to find and contextualize the DEC. Other fields, when included, must add information not derivable from the parent.

## Counter as pure telemetry (V133 §2.2)

`counter_impact` and `counter_value_after` are now optional for sub-DECs. The retrospective queue can re-derive counter state from git history if needed. Live increment-and-record is no longer load-bearing.

## Migration

Existing DECs keep their existing frontmatter — no rewrite needed. New DECs MAY use slim. The Notion sync script `notion_sync_dec.py` already reads `decision_id` (the id field); the other required fields are also in current scripts/notion-side schema.

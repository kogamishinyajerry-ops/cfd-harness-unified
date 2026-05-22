---
decision_id: DEC-V61-202-SUB-M30-CYCLE6-PROVENANCE-AUDIT-V2
title: M3.0 cycle 6 — decide() provenance audit_v2 log
status: Proposed
proposed_date: 2026-05-23
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.0 cycle 6 (provenance audit · post-integration)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M30-CYCLE1-DECIDE-STATE
  - DEC-V61-202-SUB-M30-CYCLE2-MUTATION-TOPBAR
  - DEC-V61-202-SUB-M30-CYCLE3-FOCUS-DRIVER
  - DEC-V61-202-SUB-M30-CYCLE4-MULTIPHYSICS-DOGFOOD
  - DEC-V61-202-SUB-M30-CYCLE5-E2E-DEFAULT-ON
  - DEC-V61-202-SUB-M30-INTEGRATION-V4-SHELL
---

## Why

Cycles 1-5 + integration wired decide() into the live UI. Engineers
now see the dynamic frame on `/workbench/case/<id>`. But decide() is
still a black box: when an engineer reports "the workbench told me
to fix p_rgh at 14:32 but I think it was wrong", there's no log to
verify what the system actually showed.

Cycle 6 lands a provenance log: every decide() call appends one JSON
line to `.planning/audit_v2/<case_id>/decisions.jsonl` capturing the
input state + the rail/topbar/card choices made. This unlocks:

- Post-hoc retro of "why did the workbench surface X to engineer Y"
- A/B testing decide() rule changes against historical input states
- Cycle 7 beginner test analysis (which rails did the engineer follow
  / ignore, in what order)
- Compliance: each PATCH'd manifest field has an auditable trail of
  what the engineer saw before they changed it

## What

### In scope

**Backend log writer** (`ui/backend/services/workbench_decide_provenance.py`):
- `log_decision(state: CaseStateSnapshot, frame: WorkbenchFrame) -> None`
- Appends one JSON line to
  `ui/backend/user_drafts/audit_v2/<case_id>/decisions.jsonl`
- Fields: timestamp (ISO 8601 UTC), case_id, step, focus_patch,
  state_sha, manifest_state_sha,
  rail_primary.{kind, title, field_path, severity},
  topbar_cta.kind, bottom_card_count, bottom_card_severities[]
- Best-effort: fsync the directory after write so concurrent reads
  see the latest line; never raises (logging failure ≠ frame failure)

**decide() integration** (`ui/backend/services/workbench_decide.py`):
- After building the frame, call `log_decision(state, frame)` in a
  try/except (logging is fire-and-forget; if it fails decide() still
  returns the frame)
- Add an env-var or kwarg gate (`WORKBENCH_PROVENANCE_DISABLED=1`)
  for tests that don't want sidecar files written

**Tests** (`ui/backend/tests/test_workbench_decide_provenance.py`):
- Write produces a parseable JSONL line with all expected fields
- Multiple decide() calls append (don't overwrite)
- focus_patch is captured when set, absent when null
- Failing log write doesn't break the frame return
- Lines are valid JSON each (no trailing comma / encoding bug)
- Logging gate env var works

**Audit reader skill** (script `scripts/audit_v2/replay_decisions.py`):
- Reads decisions.jsonl for a case and prints a chronological table
- Optional `--field rail_primary.title` to filter columns
- For the cycle 7 beginner test, this is how we'll inspect what the
  engineer saw step-by-step

**Dogfood**:
- `scripts/dogfood/case_007_cycle6_provenance.py` stages a case, runs
  several GET workbench_frame calls (with varying step + focus_patch),
  then asserts:
  - Log file exists
  - Each call produced exactly one JSONL line
  - Lines parse as valid JSON with the documented schema
  - Lines reflect the input state (e.g., focus_patch=inlet shows up
    in the inlet row)

### Out of scope (cycle 7+)

- Cross-case query / aggregation (cycle 7+; cycle 6 is single-case provenance)
- Log retention / rotation (operational concern, M3.1)
- Front-end "show me the why" tooltip reading the log (M3.1 advisor UI)
- Signing / tamper-evidence (V130 advisor work)

## Closure criteria

- [ ] `workbench_decide_provenance.py` log writer + 6+ unit tests
- [ ] `workbench_decide.py` integration with try/except + env gate
- [ ] `replay_decisions.py` reader skill
- [ ] case_007 dogfood: 4+ checks PASS proving the log captures real decisions
- [ ] Codex R0 APPROVED or CHANGES_REQUIRED closed ≤ 3 rounds
- [ ] DEC Proposed → Accepted
- [ ] Notion sync (session-end)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Provenance log writes break decide() under disk-full / permission errors | try/except around the log call; failure is logged to backend logger but never propagates to the frame |
| Log file grows unbounded on long-running dev sessions | Rotation is M3.1 scope; cycle 6 acceptable bound = "one JSONL line per decide() call" |
| JSONL parse fragility in the reader if a line is truncated mid-write | Each line is written atomically via single `fp.write(json.dumps(...) + "\n")` call + explicit flush. fsync on the directory ensures the line is durable before next read |
| Test suite produces sidecar files that pollute git | Use a tmpdir IMPORTED_DIR override pattern (same as cycle 2/3 dogfoods) and respect `WORKBENCH_PROVENANCE_DISABLED=1` |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Predecessors: cycles 1-5 + integration (UI now visible; ready for audit)
- User authorization 2026-05-23: "我批准你的多agent团队持续工作，奔着里程碑继续"

Surface-scan-found: ui/backend/services/workbench_decide.py · disposition: extend (add fire-and-forget log_decision call after frame construction; no behavior change to existing return path)

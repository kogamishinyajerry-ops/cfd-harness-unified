# Codex Tool Invocation Audit Trail

This directory holds per-invocation TASK EXECUTION REPORT records produced
when `claude-opus47-app` (Sole Primary Driver under Model Routing v6.1)
invokes `codex-gpt54-xhigh` (Heterogeneous Code Tool) to produce diffs
inside the three-禁区 perimeter: `src/**`, `tests/**`, and
`knowledge/gold_standards/**` (non-tolerance fields only — tolerance
edits remain hard floor #1, Notion-Gate-gated).

## Directory contract

- **Filename convention**: `{YYYYMMDDTHHMM}_{short_task_slug}.md`
  (e.g. `20260420T1545_ex1_011_bfs_grading_wiring.md`).
- **One file per Codex invocation**, even if the same Fix Plan requires
  multiple tool calls (e.g. cycle 2 after cycle 1 REJECT). Cycle number
  goes in the slug: `..._ex1_011_cycle2.md`.
- **Do not edit or delete** historical entries once landed — append-only
  audit trail. If a report needs correction, add a new dated addendum
  file referencing the original by filename hash.

## File body structure (v6.1 spec)

Every report must cover, at minimum:

1. **Header block**
   - `timestamp_utc`, `timestamp_local`
   - `task_name`, `task_contract_notion_url` (or local fallback path)
   - `spec_url` (optional)
   - `cycle_number`
   - `allowed_files`, `forbidden_files` (verbatim from the instruction)
   - `acceptance_checks` (CHK-1 .. CHK-N)
   - `reject_conditions` (REJ-1 .. REJ-N)
   - `pre_dispatch_sha256` for any touched gold_standard YAMLs
     (hard floor #1 binding)
2. **Instruction body**
   - Full text of the `[CLAUDE → CODEX TOOL INVOCATION]` block as
     handed to Codex.
3. **Codex `TASK EXECUTION REPORT` reply**
   - Full text of Codex's reply. Do **not** summarize — preserve the
     raw text for root-cause retracing.
4. **Claude-side審阅 record**
   - (a) diff-合理性 verdict
   - (b) local test / Docker E2E regression command log
   - (c) CHK status (PASS/REJECT per check)
   - (d) final commit SHA (this becomes the `Codex-tool-diff: <hash>`
     trailer value)
   - (e) any REJECT → cycle 2 dispatch pointer, or final close-out

## Relationship to `.planning/decisions/` + Notion Decisions DB

- Each Codex invocation landing a禁区 commit MUST be linked from the
  governing `.planning/decisions/<date>_<decision_id>.md` entry via a
  `codex_tool_report_path:` field, per v6.1 留痕 item #1.
- When Notion MCP is restored, Decisions DB entries mirror the local
  file and additionally carry `codex_tool_invoked: true` +
  `codex_diff_hash: <sha>` + `codex_tool_report_path: <path>`.

## Operational notes

- Failure-mode escalation: after 2 failed Codex invocations for the
  same Fix Plan, a third failure self-triggers hard floor #4 (主导-
  工具链路失调 → Notion Gate recall). Each of the 3 failure reports
  stays in this directory as evidence.
- First-use note: this directory was bootstrapped empty during the
  v6.1 cutover session (S-003p, 2026-04-20). The `.gitkeep` stub is
  safe to remove the moment the first real report lands.

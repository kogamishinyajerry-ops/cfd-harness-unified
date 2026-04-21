2026-04-21T09:38:05.271280Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-21T09:38:05.271297Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
Reading additional input from stdin...
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-harness-unified
model: gpt-5.4
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: xhigh
reasoning summaries: none
session id: 019daf67-75e6-7791-ad64-68e5aa8679da
--------
user
Phase 7b+7c+7f round 2 verification after CHANGES_REQUIRED round 1.

Round 1 findings (3):
- HIGH: Manifest-derived paths (timestamp + renders outputs + PDF output) trusted without containment.
- MEDIUM: /learn embed silently swallows ALL errors, not just 404.
- LOW: Route tests skip on missing artifacts; no service-level unit tests.

Round 2 fixes (all uncommitted):

1. HIGH closure — three lines of defense added:
   (a) ui/backend/services/comparison_report.py: `_TIMESTAMP_RE = r"^\d{8}T\d{6}Z$"` shape gate + `_validated_timestamp()` helper. build_report_context raises ReportError if timestamp fails shape gate. Containment check via `.resolve().relative_to(_FIELDS_ROOT/case_id)` after composing artifact_dir. Non-object JSON run_manifest also rejected.
   (b) Renders manifest output paths now pass through `_safe_rel_under(candidate, _RENDERS_ROOT)` which rejects: non-string, empty, absolute paths, backslashes, `..` segments, and paths that fail `resolve().relative_to(renders_root)`. Fallback path discovery uses same validator.
   (c) render_report_pdf: `reports_root = _REPO_ROOT/"reports"/"phase5_reports"` resolved at top; output_path (caller-supplied or default) must `.resolve().relative_to(reports_root)` or ReportError. scripts/render_case_report.py mirrors the shape gate + containment check.

2. MEDIUM closure — ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx ScientificComparisonReportSection now distinguishes error cases:
   - status 404 or 400 → silent hide (case not opted-in / malformed run_id)
   - any other status OR network error → visible `ErrorCallout` banner with HTTP status + truncated error message
   This preserves "case not supported = clean hide" UX while exposing real regressions.

3. LOW closure — new test_comparison_report_service.py with 7 CI-safe unit tests:
   - synthetic_tree fixture builds minimal Phase 7a+7b artifact tree in tmp_path and monkeypatches module-level root constants
   - test_build_context_happy_path: full success path exercised without real solver artifacts
   - test_render_html_contains_8_sections: all §2-§8 markers assert
   - test_rejects_tampered_manifest_timestamp: `../../../tmp/evil` → ReportError
   - test_rejects_non_matching_timestamp_shape: `2026-04-21` (wrong format) → ReportError
   - test_rejects_tampered_renders_manifest_output_path: `../../../etc/passwd` scrubbed to empty or non-matching
   - test_rejects_non_object_run_manifest: JSON array → ReportError match "not an object"
   - test_pdf_output_path_contained: caller-supplied output_path outside reports_root → ReportError match "escapes reports_root"

Regression gate: PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q → 110/110 passed (was 103/103; +7 service tests). Live smoke on restarted backend: HTML 200, PDF 200 (622KB valid PDF), traversal ..__pwn → 400.

Please verify all 3 round-1 findings are closed. Flag any missed edge cases.
codex
Reviewing the Phase 7b/7c/7f round-2 fixes as a correctness pass, not new development. I’m starting with the relevant repo/memory context, then I’ll inspect the changed files and run the targeted verification that matters for the three round-1 findings.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/b1986b3d3da5bb8a04d3cb1e69af5a29bb5c2c04/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

Superpowers skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
2. **Superpowers skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If CLAUDE.md, GEMINI.md, or AGENTS.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.

## How to Access Skills

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you—follow it directly. Never use the Read tool on skill files.

**In Copilot CLI:** Use the `skill` tool. Skills are auto-discovered from installed plugins. The `skill` tool works the same as Claude Code's `Skill` tool.

**In Gemini CLI:** Skills activate via the `activate_skill` tool. Gemini loads skill metadata at session start and activates the full content on demand.

**In other environments:** Check your platform's documentation for how skills are loaded.

## Platform Adaptation

Skills use Claude Code tool names. Non-CC platforms: see `references/copilot-tools.md` (Copilot CLI), `references/codex-tools.md` (Codex) for tool equivalents. Gemini CLI users get the tool mapping loaded automatically via GEMINI.md.

# Using Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke brainstorming skill" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Skill Priority

When multiple skills could apply, use this order:

1. **Process skills first** (brainstorming, debugging) - these determine HOW to approach the task
2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → debugging first, then domain-specific skills.

## Skill Types

**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.

**Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.

exec
/bin/zsh -lc 'pwd && rg -n "cfd-harness-unified|Phase 8|Phase 9|phase 7b|comparison_report|phase5_reports" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
/Users/Zhuanz/Desktop/cfd-harness-unified
115:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
135:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
356:# Task Group: cfd-harness-unified governance closeout and planning gates
358:scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
359:applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
361:## Task 1: Close Phase 8 and reconcile stale governance evidence
365:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
369:- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
371:## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
375:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
379:- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
385:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
400:- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]
406:- Symptom: planning work accidentally looks like activation -> cause: Phase 9 docs/task text are not explicit enough about `Planned` vs `Active` -> fix: state planning-only mode in phase page, tasks, dashboard summary, and review packet [Task 2]
439:- rollout_summaries/2026-04-12T15-33-54-ByPi-jerry_ai_cfd_notion_sync_and_cfd_harness_unified_context_mis.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/12/rollout-2026-04-12T23-33-54-019d8253-fa8b-7f40-9775-46e6e03db8ac.jsonl, updated_at=2026-04-16T17:03:18+00:00, thread_id=019d8253-fa8b-7f40-9775-46e6e03db8ac, later cfd-harness-unified instruction block correctly treated as mismatch)
691:- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]

 succeeded in 0ms:
---
name: gsd-code-review
description: "Review source files changed during a phase for bugs, security issues, and code quality problems"
argument-hint: "<phase-number> [--depth=quick|standard|deep] [--files file1,file2,...]"
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - Write
  - Task
---

<objective>
Review source files changed during a phase for bugs, security vulnerabilities, and code quality problems.

Spawns the gsd-code-reviewer agent to analyze code at the specified depth level. Produces REVIEW.md artifact in the phase directory with severity-classified findings.

Arguments:
- Phase number (required) — which phase's changes to review (e.g., "2" or "02")
- `--depth=quick|standard|deep` (optional) — review depth level, overrides workflow.code_review_depth config
  - quick: Pattern-matching only (~2 min)
  - standard: Per-file analysis with language-specific checks (~5-15 min, default)
  - deep: Cross-file analysis including import graphs and call chains (~15-30 min)
- `--files file1,file2,...` (optional) — explicit comma-separated file list, skips SUMMARY/git scoping (highest precedence for scoping)

Output: {padded_phase}-REVIEW.md in phase directory + inline summary of findings
</objective>

<execution_context>
@$HOME/.Codex/get-shit-done/workflows/code-review.md
</execution_context>

<context>
Phase: $ARGUMENTS (first positional argument is phase number)

Optional flags parsed from $ARGUMENTS:
- `--depth=VALUE` — Depth override (quick|standard|deep). If provided, overrides workflow.code_review_depth config.
- `--files=file1,file2,...` — Explicit file list override. Has highest precedence for file scoping per D-08. When provided, workflow skips SUMMARY.md extraction and git diff fallback entirely.

Context files (AGENTS.md, SUMMARY.md, phase state) are resolved inside the workflow via `gsd-tools init phase-op` and delegated to agent via `<files_to_read>` blocks.
</context>

<process>
This command is a thin dispatch layer. It parses arguments and delegates to the workflow.

Execute the code-review workflow from @$HOME/.Codex/get-shit-done/workflows/code-review.md end-to-end.

The workflow (not this command) enforces these gates:
- Phase validation (before config gate)
- Config gate check (workflow.code_review)
- File scoping (--files override > SUMMARY.md > git diff fallback)
- Empty scope check (skip if no files)
- Agent spawning (gsd-code-reviewer)
- Result presentation (inline summary + next steps)
</process>

exec
/bin/zsh -lc 'git status --short' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 M reports/cylinder_crossflow/report.md
 M reports/deep_acceptance/visual_acceptance_report.html
 M reports/deep_acceptance/visual_acceptance_report_manifest.json
 M reports/differential_heated_cavity/report.md
 M reports/rayleigh_benard_convection/report.md
 M reports/turbulent_flat_plate/report.md
 M ui/backend/main.py
 M ui/frontend/public/flow-fields/circular_cylinder_wake/strouhal_curve.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/centerline_profiles.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/stream_function.png
 M ui/frontend/public/flow-fields/plane_channel_flow/wall_profile.png
 M ui/frontend/public/flow-fields/rayleigh_benard_convection/nu_ra_scaling.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/blasius_profile.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/cf_comparison.png
 M ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
?? .claude/
?? .gitignore.patch.stale.1776663560182166739
?? knowledge/corrections/
?? reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md
?? reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md
?? reports/deep_acceptance/20260421_000138_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000139_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000231_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000232_visual_acceptance_package.md
?? reports/deep_acceptance/visual_acceptance_report_20260421_000138.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000139.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000231.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000232.html
?? reports/phase5_audit/20260421T081929Z_lid_driven_cavity_raw.json
?? reports/phase5_audit/20260421T082305Z_lid_driven_cavity_raw.json
?? reports/phase5_audit/20260421T082408Z_lid_driven_cavity_raw.json
?? reports/phase5_fields/
?? reports/phase5_renders/
?? reports/phase5_reports/
?? scripts/render_case_report.py
?? ui/backend/routes/comparison_report.py
?? ui/backend/services/comparison_report.py
?? ui/backend/templates/
?? ui/backend/tests/test_comparison_report_route.py
?? ui/backend/tests/test_comparison_report_service.py
?? ui/frontend/vite.config.sandbox.ts.stale.1776667726
?? ui/frontend/vite.config.sandbox.ts.timestamp-1776667276256-33cd5f0862292.mjs

codex
Using `using-superpowers` for skill gating and `gsd-code-review` as the review mode for this pass. Next I’m reading the touched service, route, frontend, script, and new tests to verify whether the three round-1 findings are actually closed or just covered by happy-path assertions.
  → Load review context from repo memory and inspect changed files for the three claimed closures
  • Run targeted backend/frontend tests and adversarial checks relevant to the original findings
  • Summarize findings with severity, file/line references, and closure status for each round-1 item
exec
/bin/zsh -lc "sed -n '1,260p' ui/backend/services/comparison_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' ui/backend/routes/comparison_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
"""Phase 7c — CFD vs Gold comparison report route.

GET  /api/cases/{case_id}/runs/{run_label}/comparison-report         → HTML
GET  /api/cases/{case_id}/runs/{run_label}/comparison-report.pdf     → PDF
POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build   → rebuild PDF + return manifest

Uses FileResponse pattern per Phase 7a user ratification #1 (no StaticFiles).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ui.backend.services.comparison_report import (
    ReportError,
    build_report_context,
    render_report_html,
    render_report_pdf,
)
from ui.backend.services.run_ids import _validate_segment

router = APIRouter()


def _validate_ids(case_id: str, run_label: str) -> None:
    """Reuse Phase 7a traversal defense on case_id + run_label segments."""
    _validate_segment(case_id, "case_id")
    _validate_segment(run_label, "run_label")


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report",
    response_class=HTMLResponse,
    tags=["comparison-report"],
)
def get_comparison_report_html(case_id: str, run_label: str) -> HTMLResponse:
    """Return rendered HTML report (suitable for iframe embedding)."""
    _validate_ids(case_id, run_label)
    try:
        html = render_report_html(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return HTMLResponse(html)


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report/context",
    tags=["comparison-report"],
)
def get_comparison_report_context(case_id: str, run_label: str) -> JSONResponse:
    """Return the raw template context as JSON (for frontend custom rendering
    if it wants to skip the server-rendered HTML and compose its own)."""
    _validate_ids(case_id, run_label)
    try:
        ctx = build_report_context(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # Strip non-JSON-serializable entries (e.g., numpy arrays).
    # per_point_dev_pct is already list(); metrics keys are all primitives.
    return JSONResponse(ctx)


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report.pdf",
    tags=["comparison-report"],
)
def get_comparison_report_pdf(case_id: str, run_label: str) -> FileResponse:
    """Render (or re-render) PDF and stream it back."""
    _validate_ids(case_id, run_label)
    try:
        path = render_report_pdf(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="WeasyPrint unavailable on this server; set DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib",
        )
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{case_id}__{run_label}__comparison_report.pdf",
    )


@router.post(
    "/cases/{case_id}/runs/{run_label}/comparison-report/build",
    tags=["comparison-report"],
)
def build_comparison_report(case_id: str, run_label: str) -> JSONResponse:
    """Force-rebuild HTML + PDF, return manifest."""
    _validate_ids(case_id, run_label)
    try:
        html = render_report_html(case_id, run_label)
        pdf_path = render_report_pdf(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError:
        raise HTTPException(status_code=503, detail="WeasyPrint unavailable")
    return JSONResponse({
        "case_id": case_id,
        "run_label": run_label,
        "pdf_path": str(pdf_path),
        "html_bytes": len(html),
    })

 succeeded in 0ms:
"""Phase 7c — CFD vs Gold comparison report service.

Renders an 8-section HTML report for a given (case_id, run_label), using:
- Phase 7a field artifacts at reports/phase5_fields/{case}/{ts}/
- Phase 7b rendered figures at reports/phase5_renders/{case}/{ts}/
- knowledge/gold_standards/{case}.yaml gold reference
- ui/backend/tests/fixtures/runs/{case}/mesh_{20,40,80,160}_measurement.yaml for grid convergence

Backend route: ui/backend/routes/comparison_report.py calls `render_report_html`
and `render_report_pdf` from this module. No DOM / no JS — static HTML + PNG
inlined assets referenced by file:// for WeasyPrint PDF, served via FileResponse
or embedded iframe on frontend.

Design: report_html is a self-contained string (no asset URLs pointing to
/api/... — uses file:// for PDF rendering and relative paths for HTML serving).
"""
from __future__ import annotations

import datetime
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Codex round 1 HIGH (2026-04-21): strict shape gate on manifest-supplied
# timestamp and artifact paths. Mirrors ui/backend/services/field_artifacts.py
# defense-in-depth pattern so tampered runs/{label}.json cannot steer reads
# outside reports/phase5_fields/ or writes outside reports/phase5_reports/.
_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")

_MODULE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _MODULE_DIR.parents[2]
_TEMPLATES = _MODULE_DIR.parent / "templates"
_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"
_RENDERS_ROOT = _REPO_ROOT / "reports" / "phase5_renders"
_GOLD_ROOT = _REPO_ROOT / "knowledge" / "gold_standards"
_FIXTURE_ROOT = _REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"

_REPORT_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html", "htm"]),
)


class ReportError(Exception):
    """Recoverable — caller should 404 or return partial payload."""


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------


def _run_manifest_path(case_id: str, run_label: str) -> Path:
    return _FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"


def _renders_manifest_path(case_id: str, run_label: str) -> Path:
    return _RENDERS_ROOT / case_id / "runs" / f"{run_label}.json"


def _load_run_manifest(case_id: str, run_label: str) -> dict:
    p = _run_manifest_path(case_id, run_label)
    if not p.is_file():
        raise ReportError(f"no run manifest for {case_id}/{run_label}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ReportError(f"run manifest not an object: {p}")
    return data


def _load_renders_manifest(case_id: str, run_label: str) -> Optional[dict]:
    p = _renders_manifest_path(case_id, run_label)
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return data


def _validated_timestamp(ts: Any) -> Optional[str]:
    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
    match the exact YYYYMMDDTHHMMSSZ shape. Blocks '../../outside' etc."""
    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
        return None
    return ts


def _safe_rel_under(candidate: str, root: Path) -> Optional[str]:
    """Return `candidate` if it resolves under `root`, else None.

    Used to validate manifest-supplied output file paths before they flow
    into template `img src`. Prevents a tampered renders manifest from
    pointing WeasyPrint base_url resolution at arbitrary local files
    (which would then be embedded into PDFs as image data URLs).
    """
    if not isinstance(candidate, str) or not candidate:
        return None
    if candidate.startswith("/") or "\\" in candidate or ".." in candidate.split("/"):
        return None
    try:
        resolved = (_REPO_ROOT / candidate).resolve(strict=False)
        resolved.relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    return candidate


def _load_ldc_gold() -> tuple[list[float], list[float], dict]:
    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
    if not gold_path.is_file():
        raise ReportError(f"gold file missing: {gold_path}")
    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    u_doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
        None,
    )
    if u_doc is None:
        raise ReportError("no u_centerline doc in LDC gold")
    ys: list[float] = []
    us: list[float] = []
    for entry in u_doc.get("reference_values", []):
        if isinstance(entry, dict):
            y = entry.get("y")
            u = entry.get("value") or entry.get("u")
            if y is not None and u is not None:
                ys.append(float(y))
                us.append(float(u))
    return ys, us, u_doc


def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        try:
            rows.append([float(parts[0]), float(parts[1])])
        except (ValueError, IndexError):
            continue
    if not rows:
        raise ReportError(f"empty sample: {path}")
    arr = np.array(rows)
    return arr[:, 0], arr[:, 1]


def _latest_sample_iter(artifact_dir: Path) -> Path:
    sample_root = artifact_dir / "sample"
    if not sample_root.is_dir():
        raise ReportError(f"sample/ missing under {artifact_dir}")
    iters = sorted(
        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
        key=lambda d: int(d.name),
    )
    if not iters:
        raise ReportError(f"no sample iter dirs under {sample_root}")
    return iters[-1]


def _compute_metrics(
    y_sim: np.ndarray, u_sim: np.ndarray,
    y_gold: list[float], u_gold: list[float],
    tolerance_pct: float,
) -> dict[str, Any]:
    """Compute L2/Linf/RMS + per-point |dev|% + pass count."""
    y_sim_norm = y_sim / max(float(y_sim.max()), 1e-12)
    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
    u_gold_arr = np.array(u_gold)
    diff = u_sim_interp - u_gold_arr

    denom = np.where(np.abs(u_gold_arr) < 1e-9, 1e-9, np.abs(u_gold_arr))
    dev_pct = 100.0 * np.abs(diff) / denom
    n_total = len(u_gold_arr)
    n_pass = int((dev_pct < tolerance_pct).sum())

    return {
        "l2": float(np.sqrt(np.mean(diff ** 2))),
        "linf": float(np.max(np.abs(diff))),
        "rms": float(np.sqrt(np.mean(diff ** 2))),  # alias
        "max_dev_pct": float(dev_pct.max()) if n_total else 0.0,
        "n_pass": n_pass,
        "n_total": n_total,
        "per_point_dev_pct": dev_pct.tolist(),
    }


def _parse_residuals_csv(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"total_iter": 0, "final_ux": None, "note": None}
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        return {"total_iter": 0, "final_ux": None, "note": None}
    header = [c.strip() for c in lines[0].split(",")]
    last = None
    count = 0
    for ln in lines[1:]:
        parts = [c.strip() for c in ln.split(",")]
        if len(parts) != len(header):
            continue
        last = parts
        count += 1
    final_ux = None
    if last is not None and len(last) > 1 and last[1].upper() != "N/A":
        try:
            final_ux = float(last[1])
        except ValueError:
            pass
    note = None
    if final_ux is not None and final_ux > 1e-3:
        note = (f"注意：Ux 终值 {final_ux:.2e} 大于 1e-3 — "
                f"收敛可能未达稳态。建议增加 endTime 或降低 residualControl。")
    return {"total_iter": count, "final_ux": final_ux, "note": note}


def _load_grid_convergence(case_id: str, gold_y: list[float], gold_u: list[float]) -> tuple[list[dict], str]:
    """Read mesh_20/40/80/160_measurement.yaml fixtures, build table rows."""
    rows: list[dict] = []
    # LDC fixtures compare at y≈0.0625 (first gold point >0).
    sample_y = 0.0625
    try:
        sample_gold = next(u for y, u in zip(gold_y, gold_u) if abs(y - sample_y) < 1e-3)
    except StopIteration:
        sample_gold = gold_u[1] if len(gold_u) > 1 else 0.0

    case_dir = _FIXTURE_ROOT / case_id
    meshes = [("mesh_20", 20), ("mesh_40", 40), ("mesh_80", 80), ("mesh_160", 160)]
    for name, _n in meshes:
        path = case_dir / f"{name}_measurement.yaml"
        if not path.is_file():
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        meas = doc.get("measurement", {}) if isinstance(doc, dict) else {}
        val = meas.get("value")
        if val is None:
            continue
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            continue
        denom = abs(sample_gold) if abs(sample_gold) > 1e-9 else 1e-9
        dev_pct = 100.0 * abs(val_f - sample_gold) / denom
        if dev_pct < 5.0:
            verdict, cls = "PASS", "pass"
        elif dev_pct < 10.0:
            verdict, cls = "WARN", "warn"
        else:
            verdict, cls = "FAIL", "fail"
        rows.append({
            "mesh": name,

exec
/bin/zsh -lc "sed -n '1,220p' scripts/render_case_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,260p' ui/backend/tests/test_comparison_report_route.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
#!/usr/bin/env python3
"""Phase 7b — render_case_report.py

Convert Phase 7a-captured field artifacts (reports/phase5_fields/{case}/{ts}/)
into visual renders (reports/phase5_renders/{case}/{ts}/):

- profile_u_centerline.png   — matplotlib static profile (sim vs gold)
- profile_u_centerline.html  — Plotly JSON (for frontend interactive)
- residuals.png              — log-y residual convergence history
- contour_u_magnitude.png    — 2D U-magnitude contour from final sample iter
- pointwise_deviation.png    — color heatmap of |dev|% per gold point

LDC MVP: works today for case_id=lid_driven_cavity. Other 9 cases will be
unlocked in Phase 7c Sprint-2 as their adapters emit Phase 7a function objects.

Usage:
    python scripts/render_case_report.py lid_driven_cavity
    python scripts/render_case_report.py lid_driven_cavity --run audit_real_run

Dependencies: matplotlib (2D plots), plotly (interactive JSON), numpy, PyYAML.
No PyVista / no VTK parser needed for MVP — uses the sample CSV directly.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

# Codex round 1 HIGH (2026-04-21): enforce exact timestamp shape before
# composing filesystem paths, mirror ui/backend/services/comparison_report.py.
_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")

import matplotlib

matplotlib.use("Agg")  # headless — CI-safe
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FIELDS_ROOT = REPO_ROOT / "reports" / "phase5_fields"
RENDERS_ROOT = REPO_ROOT / "reports" / "phase5_renders"
GOLD_ROOT = REPO_ROOT / "knowledge" / "gold_standards"

# Deterministic matplotlib style — locked for byte-reproducibility.
plt.rcParams.update({
    "figure.figsize": (8, 5),
    "figure.dpi": 110,
    "savefig.dpi": 110,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.8,
})

# Phase 7a opt-in mirror — matches scripts/phase5_audit_run.py::_PHASE7A_OPTED_IN.
RENDER_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})


class RenderError(Exception):
    """Non-fatal render failure — caller decides whether to abort the batch."""


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _resolve_run_timestamp(case_id: str, run_label: str) -> str:
    """Read the per-run manifest written by phase5_audit_run.py and return its timestamp.

    Codex round 1 HIGH: enforce _TIMESTAMP_RE shape on the manifest value so a
    tampered manifest cannot steer downstream path composition outside
    reports/phase5_fields/.
    """
    manifest_path = FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    if not manifest_path.is_file():
        raise RenderError(f"no run manifest: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RenderError(f"manifest not an object: {manifest_path}")
    ts = data.get("timestamp")
    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
        raise RenderError(f"invalid timestamp shape in manifest: {ts!r}")
    return ts


def _artifact_dir(case_id: str, timestamp: str) -> Path:
    d = FIELDS_ROOT / case_id / timestamp
    # Containment check even though timestamp is already shape-gated upstream.
    try:
        d.resolve(strict=True).relative_to((FIELDS_ROOT / case_id).resolve())
    except (ValueError, OSError, FileNotFoundError):
        raise RenderError(f"artifact dir escapes fields root: {d}")
    if not d.is_dir():
        raise RenderError(f"artifact dir missing: {d}")
    return d


def _renders_dir(case_id: str, timestamp: str) -> Path:
    d = RENDERS_ROOT / case_id / timestamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load OpenFOAM `sample` output (.xy file, whitespace-separated).

    Column layout for uCenterline: y  U_x  U_y  U_z  p.
    Returns (y, U_x). Skips header lines starting with '#'.
    """
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        # Accept either 5 (y Ux Uy Uz p) or 2 (y Ux) column variants.
        try:
            y = float(parts[0])
            ux = float(parts[1])
        except (ValueError, IndexError):
            continue
        rows.append([y, ux])
    if not rows:
        raise RenderError(f"empty sample file: {path}")
    arr = np.array(rows)
    return arr[:, 0], arr[:, 1]


def _load_residuals_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Load residuals.csv written by _capture_field_artifacts.

    Format: Time,Ux,Uy,p  — first data row may be "N/A" for iter 0.
    Returns (iterations, {field_name: array}).
    """
    raw = path.read_text(encoding="utf-8").splitlines()
    if not raw:
        raise RenderError(f"empty residuals: {path}")
    header = [c.strip() for c in raw[0].split(",")]
    if header[0].lower() not in ("time", "iter", "iteration"):
        raise RenderError(f"unexpected residuals header: {header}")
    fields = header[1:]
    iters: list[int] = []
    data: dict[str, list[float]] = {f: [] for f in fields}
    for line in raw[1:]:
        parts = [c.strip() for c in line.split(",")]
        if len(parts) != len(header):
            continue
        try:
            iters.append(int(float(parts[0])))
        except ValueError:
            continue
        for f, v in zip(fields, parts[1:]):
            if v.upper() == "N/A" or v == "":
                data[f].append(float("nan"))
            else:
                try:
                    data[f].append(float(v))
                except ValueError:
                    data[f].append(float("nan"))
    return np.array(iters), {k: np.array(v) for k, v in data.items()}


def _load_gold_ldc() -> tuple[list[float], list[float], str]:
    """Return (y_points, u_values, citation) from knowledge/gold_standards/lid_driven_cavity.yaml.

    File is multi-document YAML (u_centerline, v_centerline, primary_vortex_location).
    Iterate safe_load_all and pick the u_centerline document.
    """
    gold = GOLD_ROOT / "lid_driven_cavity.yaml"
    if not gold.is_file():
        raise RenderError(f"gold file missing: {gold}")
    docs = list(yaml.safe_load_all(gold.read_text(encoding="utf-8")))
    u_doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
        None,
    )
    if u_doc is None:
        raise RenderError("no quantity: u_centerline doc in LDC gold YAML")
    refs = u_doc.get("reference_values", [])
    ys: list[float] = []
    us: list[float] = []
    for entry in refs:
        if isinstance(entry, dict):
            y = entry.get("y")
            u = entry.get("value") or entry.get("u")
            if y is not None and u is not None:
                ys.append(float(y))
                us.append(float(u))
    citation = u_doc.get("source") or u_doc.get("citation") or \
        "Ghia, Ghia & Shin 1982 J. Comput. Phys. 47, 387-411 — Table I Re=100"
    return ys, us, citation


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _latest_sample_iter(artifact_dir: Path) -> Path:
    """Return the highest-iteration sample directory (e.g. .../sample/1000/)."""
    sample_root = artifact_dir / "sample"
    if not sample_root.is_dir():
        raise RenderError(f"sample/ missing under {artifact_dir}")
    iters = sorted(
        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
        key=lambda d: int(d.name),
    )
    if not iters:
        raise RenderError(f"no numeric iter subdirs under {sample_root}")
    return iters[-1]

 succeeded in 0ms:
"""Phase 7c — comparison report route tests.

Guards route-level behavior: 200 on valid case/run, 404 on missing, 400 on
traversal attempts. Actual HTML content is covered by unit tests of the
service module.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from ui.backend.main import app

client = TestClient(app)

# These tests run against the real reports/phase5_fields/lid_driven_cavity/
# artifact set which is .gitignored. In CI (no artifacts), they should 404 —
# which is fine, they'll be re-collected on developer machines.


def _has_ldc_artifacts() -> bool:
    from pathlib import Path
    manifest = Path("reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json")
    return manifest.is_file()


def test_html_200_when_artifacts_present() -> None:
    if not _has_ldc_artifacts():
        return  # skip silently on CI-style clean checkout
    r = client.get("/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report")
    assert r.status_code == 200, r.text
    body = r.text
    # 8 section markers from the Jinja template.
    for marker in [
        "参考文献",           # §2
        "中心线 profile",      # §3
        "逐点偏差分布",        # §4
        "流场 contour",        # §5
        "残差收敛历史",        # §6
        "网格收敛",            # §7
        "求解器元数据",        # §8
    ]:
        assert marker in body, f"missing section marker: {marker}"
    # Verdict card must be present.
    assert "verdict-card" in body


def test_context_200_when_artifacts_present() -> None:
    if not _has_ldc_artifacts():
        return
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["case_id"] == "lid_driven_cavity"
    assert d["run_label"] == "audit_real_run"
    assert "metrics" in d
    assert d["metrics"]["n_total"] > 0
    assert d["verdict"] in ("PASS", "PARTIAL", "FAIL")


def test_html_404_unknown_case() -> None:
    r = client.get("/api/cases/nonexistent_case/runs/audit_real_run/comparison-report")
    assert r.status_code == 404


def test_html_400_traversal_case_id() -> None:
    r = client.get("/api/cases/..__pwn/runs/audit_real_run/comparison-report")
    assert r.status_code == 400


def test_html_400_traversal_run_label() -> None:
    r = client.get("/api/cases/lid_driven_cavity/runs/..__pwn/comparison-report")
    assert r.status_code == 400


def test_context_400_urlencoded_traversal() -> None:
    r = client.get(
        "/api/cases/%2e%2e__pwn/runs/audit_real_run/comparison-report/context",
    )
    assert r.status_code == 400

exec
/bin/zsh -lc "sed -n '1,260p' ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,260p' ui/backend/tests/test_comparison_report_service.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
import { useQueries, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { CaseIllustration } from "@/components/learn/CaseIllustration";
import { getFlowFields } from "@/data/flowFields";
import { getLearnCase } from "@/data/learnCases";
import type {
  ContractStatus,
  RunCategory,
  RunDescriptor,
  ValidationReport,
} from "@/types/validation";

// Student-facing case detail. Four tabs:
//   Story    — default. physics, canonical reference, why validation matters
//   Compare  — gold vs measurement, tolerance band. Framed as a learning moment
//   Run      — residuals chart placeholder (real streaming lives in Pro Workbench)
//   Advanced — decision trail + link to audit package (the pro-evidence surface)
//
// The backend ValidationReport fetch is shared; sub-tabs derive their views
// from that single record so the student can flip between them without
// re-fetching.

type TabId = "story" | "compare" | "mesh" | "run" | "advanced";

const TABS: { id: TabId; label_zh: string; label_en: string }[] = [
  { id: "story", label_zh: "故事", label_en: "Story" },
  { id: "compare", label_zh: "对比", label_en: "Compare" },
  { id: "mesh", label_zh: "网格", label_en: "Mesh" },
  { id: "run", label_zh: "运行", label_en: "Run" },
  { id: "advanced", label_zh: "进阶", label_en: "Advanced" },
];

// Cases with a curated grid-convergence sweep (4 meshes each). Every
// case in the /learn catalog now has one. If a new case is added,
// author 4 mesh_N fixtures and register its density labels here.
const GRID_CONVERGENCE_CASES: Record<
  string,
  { meshLabel: string; densities: { id: string; label: string; n: number }[] }
> = {
  lid_driven_cavity: {
    meshLabel: "uniform grid N×N",
    densities: [
      { id: "mesh_20", label: "20²", n: 400 },
      { id: "mesh_40", label: "40²", n: 1600 },
      { id: "mesh_80", label: "80²", n: 6400 },
      { id: "mesh_160", label: "160²", n: 25600 },
    ],
  },
  turbulent_flat_plate: {
    meshLabel: "wall-normal cells",
    densities: [
      { id: "mesh_20", label: "20 y-cells", n: 20 },
      { id: "mesh_40", label: "40 y-cells", n: 40 },
      { id: "mesh_80", label: "80 y-cells + 4:1", n: 80 },
      { id: "mesh_160", label: "160 y-cells", n: 160 },
    ],
  },
  backward_facing_step: {
    meshLabel: "recirculation cells",
    densities: [
      { id: "mesh_20", label: "20 cells", n: 20 },
      { id: "mesh_40", label: "40 cells", n: 40 },
      { id: "mesh_80", label: "80 cells", n: 80 },
      { id: "mesh_160", label: "160 cells", n: 160 },
    ],
  },
  circular_cylinder_wake: {
    meshLabel: "azimuthal cells around cylinder",
    densities: [
      { id: "mesh_20", label: "20 azim", n: 20 },
      { id: "mesh_40", label: "40 azim", n: 40 },
      { id: "mesh_80", label: "80 azim", n: 80 },
      { id: "mesh_160", label: "160 azim", n: 160 },
    ],
  },
  duct_flow: {
    meshLabel: "cross-section cells",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160²", n: 25600 },
    ],
  },
  differential_heated_cavity: {
    meshLabel: "square cavity N×N + wall grading",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 1.5:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
    ],
  },
  plane_channel_flow: {
    meshLabel: "isotropic cubed cells",
    densities: [
      { id: "mesh_20", label: "20³ RANS", n: 8000 },
      { id: "mesh_40", label: "40³ hybrid", n: 64000 },
      { id: "mesh_80", label: "80³ WR-LES", n: 512000 },
      { id: "mesh_160", label: "160³ DNS", n: 4096000 },
    ],
  },
  impinging_jet: {
    meshLabel: "radial cells in stagnation region",
    densities: [
      { id: "mesh_20", label: "20 rad", n: 20 },
      { id: "mesh_40", label: "40 rad + 2:1", n: 40 },
      { id: "mesh_80", label: "80 rad + 4:1", n: 80 },
      { id: "mesh_160", label: "160 rad", n: 160 },
    ],
  },
  naca0012_airfoil: {
    meshLabel: "surface cells per side",
    densities: [
      { id: "mesh_20", label: "20 surf + 8-chord", n: 20 },
      { id: "mesh_40", label: "40 surf + 15-chord", n: 40 },
      { id: "mesh_80", label: "80 surf + 40-chord", n: 80 },
      { id: "mesh_160", label: "160 surf", n: 160 },
    ],
  },
  rayleigh_benard_convection: {
    meshLabel: "square cavity + wall packing",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
    ],
  },
};

const STATUS_TEXT: Record<ContractStatus, string> = {
  PASS: "对齐黄金标准",
  HAZARD: "落入带内，但可能是 silent-pass",
  FAIL: "偏离了 tolerance band",
  UNKNOWN: "尚无可对比的测量值",
};

const STATUS_CLASS: Record<ContractStatus, string> = {
  PASS: "text-contract-pass",
  HAZARD: "text-contract-hazard",
  FAIL: "text-contract-fail",
  UNKNOWN: "text-surface-400",
};

const isTabId = (v: string | null): v is TabId =>
  v === "story" ||
  v === "compare" ||
  v === "mesh" ||
  v === "run" ||
  v === "advanced";

export function LearnCaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab");
  const tab: TabId = isTabId(rawTab) ? rawTab : "story";
  const setTab = (next: TabId) => {
    const params = new URLSearchParams(searchParams);
    if (next === "story") params.delete("tab");
    else params.set("tab", next);
    setSearchParams(params, { replace: true });
  };

  const learnCase = caseId ? getLearnCase(caseId) : undefined;
  const runId = searchParams.get("run") || undefined;

  const { data: report, error } = useQuery<ValidationReport, ApiError>({
    queryKey: ["validation-report", caseId, runId ?? "default"],
    queryFn: () => api.getValidationReport(caseId!, runId),
    enabled: !!caseId,
    retry: false,
  });

  const { data: runs } = useQuery<RunDescriptor[], ApiError>({
    queryKey: ["case-runs", caseId],
    queryFn: () => api.listCaseRuns(caseId!),
    enabled: !!caseId,
    retry: false,
  });

  const setRunId = (nextRun: string | null) => {
    const params = new URLSearchParams(searchParams);
    if (nextRun) params.set("run", nextRun);
    else params.delete("run");
    setSearchParams(params, { replace: true });
  };

  if (!caseId || !learnCase) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16 text-center text-surface-400">
        <p>找不到这个案例。</p>
        <Link to="/learn" className="mt-4 inline-block text-sky-400 hover:text-sky-300">
          ← 回到目录
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 pt-8 pb-16">
      {/* Breadcrumb + case-export + Pro Workbench switch */}
      <nav className="mb-6 flex items-center justify-between gap-3 text-[12px] text-surface-500">
        <div>
          <Link to="/learn" className="hover:text-surface-300">
            目录
          </Link>
          <span className="mx-2 text-surface-700">/</span>
          <span className="mono text-surface-400">{caseId}</span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={`/api/cases/${caseId}/export`}
            download={`${caseId}_reference.zip`}
            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-emerald-700/60 hover:bg-surface-900 hover:text-emerald-300"
            title="Download a reference bundle: gold standard YAML, validation contract, reproduction README"
          >
            <span>下载参考包</span>
            <span className="mono text-surface-600 group-hover:text-emerald-400">
              .zip ↓
            </span>
          </a>
          <Link
            to={`/audit-package?case=${encodeURIComponent(caseId ?? "")}&run=audit_real_run`}
            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-amber-700/60 hover:bg-surface-900 hover:text-amber-300"
            title="Build a signed audit package from the real-solver audit_real_run fixture (HMAC-signed zip + manifest + html + pdf + sig)"
          >
            <span>签名审计包</span>
            <span className="mono text-surface-600 group-hover:text-amber-400">
              HMAC ↓
            </span>
          </Link>
          <Link
            to={`/cases/${caseId}/report`}
            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-sky-700/60 hover:bg-surface-900 hover:text-sky-300"
            title="Switch to the evidence-heavy audit surface (Validation Report, Decisions Queue, Audit Package)"
          >
            <span>进入专业工作台</span>
            <span className="mono text-surface-600 group-hover:text-sky-400">
              Pro Workbench →
            </span>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <header className="mb-8 grid gap-6 md:grid-cols-[1fr_240px]">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-surface-500">
            {learnCase.canonical_ref}
          </p>
          <h1 className="mt-1.5 text-3xl font-semibold leading-tight text-surface-100">
            {learnCase.headline_zh}
          </h1>
          <p className="mt-1 text-[13px] text-surface-400">
            {learnCase.displayName} · {learnCase.headline_en}
          </p>

 succeeded in 0ms:
"""Phase 7c — comparison_report service unit tests (CI-safe, no real artifacts).

Builds a synthetic artifact tree in tmp_path, monkeypatches the module's root
constants, exercises render_report_html + build_report_context + the Codex
round-1 HIGH containment guards.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def synthetic_tree(tmp_path: pytest.TempPathFactory, monkeypatch):
    """Build a minimal Phase-7a-and-7b-compatible artifact tree in tmp_path."""
    root = tmp_path
    case = "lid_driven_cavity"
    ts = "20260421T000000Z"

    fields_root = root / "reports" / "phase5_fields"
    renders_root = root / "reports" / "phase5_renders"
    case_fields = fields_root / case / ts
    (case_fields / "sample" / "1000").mkdir(parents=True)
    (case_fields / "sample" / "1000" / "uCenterline.xy").write_text(
        "#   y   U_x   U_y   U_z   p\n"
        "0     0      0     0    0.5\n"
        "0.5  -0.2    0     0    0.5\n"
        "1.0   1.0    0     0    0.5\n",
        encoding="utf-8",
    )
    (case_fields / "residuals.csv").write_text(
        "Time,Ux,Uy,p\n0,N/A,N/A,N/A\n1,1.0,1.0,1.0\n2,0.1,0.1,0.1\n",
        encoding="utf-8",
    )
    (fields_root / case / "runs").mkdir(parents=True)
    (fields_root / case / "runs" / "audit_real_run.json").write_text(
        json.dumps({"timestamp": ts, "case_id": case, "run_label": "audit_real_run"}),
        encoding="utf-8",
    )

    # Minimal render outputs (empty PNGs are fine for containment checks).
    renders_case = renders_root / case / ts
    renders_case.mkdir(parents=True)
    for name in ["profile_u_centerline.png", "pointwise_deviation.png",
                 "contour_u_magnitude.png", "residuals.png"]:
        (renders_case / name).write_bytes(b"\x89PNG\r\n\x1a\n")  # 8-byte stub
    (renders_root / case / "runs").mkdir(parents=True)
    (renders_root / case / "runs" / "audit_real_run.json").write_text(
        json.dumps({
            "case_id": case, "run_label": "audit_real_run", "timestamp": ts,
            "outputs": {
                "profile_png": f"reports/phase5_renders/{case}/{ts}/profile_u_centerline.png",
                "pointwise_deviation_png": f"reports/phase5_renders/{case}/{ts}/pointwise_deviation.png",
                "contour_u_magnitude_png": f"reports/phase5_renders/{case}/{ts}/contour_u_magnitude.png",
                "residuals_png": f"reports/phase5_renders/{case}/{ts}/residuals.png",
            },
        }),
        encoding="utf-8",
    )

    # Minimal LDC gold YAML in tmp_path/knowledge/gold_standards/.
    gold_dir = root / "knowledge" / "gold_standards"
    gold_dir.mkdir(parents=True)
    (gold_dir / "lid_driven_cavity.yaml").write_text(
        "quantity: u_centerline\n"
        "reference_values:\n"
        "  - y: 0.0\n    u: 0.0\n"
        "  - y: 0.5\n    u: -0.20581\n"
        "  - y: 1.0\n    u: 1.0\n"
        "tolerance: 0.05\n"
        "source: Ghia Ghia Shin 1982 Table I Re=100\n"
        "literature_doi: 10.1016/0021-9991(82)90058-4\n",
        encoding="utf-8",
    )

    # Minimal mesh_{20,40,80,160} fixtures for grid-convergence table.
    fixture_case = root / "ui" / "backend" / "tests" / "fixtures" / "runs" / case
    fixture_case.mkdir(parents=True)
    for mesh, val in (("mesh_20", -0.055), ("mesh_40", -0.048),
                      ("mesh_80", -0.044), ("mesh_160", -0.042)):
        (fixture_case / f"{mesh}_measurement.yaml").write_text(
            f"measurement:\n  value: {val}\n", encoding="utf-8",
        )

    from ui.backend.services import comparison_report as svc
    monkeypatch.setattr(svc, "_REPO_ROOT", root)
    monkeypatch.setattr(svc, "_FIELDS_ROOT", fields_root)
    monkeypatch.setattr(svc, "_RENDERS_ROOT", renders_root)
    monkeypatch.setattr(svc, "_GOLD_ROOT", gold_dir)
    monkeypatch.setattr(svc, "_FIXTURE_ROOT", root / "ui" / "backend" / "tests" / "fixtures" / "runs")

    return {"root": root, "case": case, "ts": ts, "svc": svc}


def test_build_context_happy_path(synthetic_tree) -> None:
    svc = synthetic_tree["svc"]
    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
    assert ctx["case_id"] == "lid_driven_cavity"
    assert ctx["timestamp"] == "20260421T000000Z"
    assert ctx["metrics"]["n_total"] == 3
    assert ctx["verdict"] in ("PASS", "PARTIAL", "FAIL")


def test_render_html_contains_8_sections(synthetic_tree) -> None:
    svc = synthetic_tree["svc"]
    html = svc.render_report_html("lid_driven_cavity", "audit_real_run")
    for marker in ["参考文献", "中心线 profile", "逐点偏差分布",
                   "流场 contour", "残差收敛历史", "网格收敛",
                   "求解器元数据"]:
        assert marker in html, f"missing §: {marker}"


def test_rejects_tampered_manifest_timestamp(synthetic_tree) -> None:
    """Codex round 1 HIGH: manifest with timestamp='../../outside' must be rejected."""
    svc = synthetic_tree["svc"]
    root = synthetic_tree["root"]
    # Overwrite manifest with malicious timestamp.
    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    m.write_text(json.dumps({"timestamp": "../../../../tmp/evil"}), encoding="utf-8")
    with pytest.raises(svc.ReportError, match="invalid timestamp"):
        svc.build_report_context("lid_driven_cavity", "audit_real_run")


def test_rejects_non_matching_timestamp_shape(synthetic_tree) -> None:
    """Timestamp must match exact YYYYMMDDTHHMMSSZ regex."""
    svc = synthetic_tree["svc"]
    root = synthetic_tree["root"]
    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    m.write_text(json.dumps({"timestamp": "2026-04-21"}), encoding="utf-8")
    with pytest.raises(svc.ReportError):
        svc.build_report_context("lid_driven_cavity", "audit_real_run")


def test_rejects_tampered_renders_manifest_output_path(synthetic_tree) -> None:
    """Codex round 1 HIGH: img src in renders manifest must be inside renders root."""
    svc = synthetic_tree["svc"]
    root = synthetic_tree["root"]
    # Overwrite renders manifest with escape path.
    rm = root / "reports" / "phase5_renders" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    rm.write_text(
        json.dumps({
            "case_id": "lid_driven_cavity", "run_label": "audit_real_run",
            "timestamp": "20260421T000000Z",
            "outputs": {
                "profile_png": "../../../../etc/passwd",
                "pointwise_deviation_png": "/etc/passwd",
                "contour_u_magnitude_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/contour_u_magnitude.png",
                "residuals_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/residuals.png",
            },
        }),
        encoding="utf-8",
    )
    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
    # Escaped paths must be scrubbed to empty; the template will skip empty src.
    assert ctx["renders"]["profile_png_rel"] in ("", None) \
        or "etc/passwd" not in ctx["renders"]["profile_png_rel"]
    assert "etc/passwd" not in ctx["renders"]["pointwise_png_rel"]
    # Safe entries retained.
    assert "reports/phase5_renders" in ctx["renders"]["contour_png_rel"]


def test_rejects_non_object_run_manifest(synthetic_tree) -> None:
    """Codex round 2 (7a precedent): non-object JSON must fail closed."""
    svc = synthetic_tree["svc"]
    root = synthetic_tree["root"]
    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    m.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    with pytest.raises(svc.ReportError, match="not an object"):
        svc.build_report_context("lid_driven_cavity", "audit_real_run")


def test_pdf_output_path_contained(synthetic_tree, tmp_path: Path) -> None:
    """Codex round 1 HIGH: caller-supplied output_path must stay under reports/phase5_reports/."""
    svc = synthetic_tree["svc"]
    # Attempt to write PDF outside the reports tree.
    evil = tmp_path / "outside" / "evil.pdf"
    with pytest.raises(svc.ReportError, match="escapes reports_root"):
        svc.render_report_pdf("lid_driven_cavity", "audit_real_run", output_path=evil)

codex
The service and tests are in scope now. I’ve confirmed the core containment code exists; next I’m drilling into the exact branches around route behavior and the frontend error-handling change, because those are the likely places a “looks fixed” patch can still leak the original issue.
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparison_report_service.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/routes/comparison_report.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'rg -n "ScientificComparisonReportSection|ErrorCallout|comparison-report|404|400|network error|truncated" ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7c — CFD vs Gold comparison report route.
     2	
     3	GET  /api/cases/{case_id}/runs/{run_label}/comparison-report         → HTML
     4	GET  /api/cases/{case_id}/runs/{run_label}/comparison-report.pdf     → PDF
     5	POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build   → rebuild PDF + return manifest
     6	
     7	Uses FileResponse pattern per Phase 7a user ratification #1 (no StaticFiles).
     8	"""
     9	from __future__ import annotations
    10	
    11	from pathlib import Path
    12	
    13	from fastapi import APIRouter, HTTPException
    14	from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
    15	
    16	from ui.backend.services.comparison_report import (
    17	    ReportError,
    18	    build_report_context,
    19	    render_report_html,
    20	    render_report_pdf,
    21	)
    22	from ui.backend.services.run_ids import _validate_segment
    23	
    24	router = APIRouter()
    25	
    26	
    27	def _validate_ids(case_id: str, run_label: str) -> None:
    28	    """Reuse Phase 7a traversal defense on case_id + run_label segments."""
    29	    _validate_segment(case_id, "case_id")
    30	    _validate_segment(run_label, "run_label")
    31	
    32	
    33	@router.get(
    34	    "/cases/{case_id}/runs/{run_label}/comparison-report",
    35	    response_class=HTMLResponse,
    36	    tags=["comparison-report"],
    37	)
    38	def get_comparison_report_html(case_id: str, run_label: str) -> HTMLResponse:
    39	    """Return rendered HTML report (suitable for iframe embedding)."""
    40	    _validate_ids(case_id, run_label)
    41	    try:
    42	        html = render_report_html(case_id, run_label)
    43	    except ReportError as e:
    44	        raise HTTPException(status_code=404, detail=str(e))
    45	    return HTMLResponse(html)
    46	
    47	
    48	@router.get(
    49	    "/cases/{case_id}/runs/{run_label}/comparison-report/context",
    50	    tags=["comparison-report"],
    51	)
    52	def get_comparison_report_context(case_id: str, run_label: str) -> JSONResponse:
    53	    """Return the raw template context as JSON (for frontend custom rendering
    54	    if it wants to skip the server-rendered HTML and compose its own)."""
    55	    _validate_ids(case_id, run_label)
    56	    try:
    57	        ctx = build_report_context(case_id, run_label)
    58	    except ReportError as e:
    59	        raise HTTPException(status_code=404, detail=str(e))
    60	    # Strip non-JSON-serializable entries (e.g., numpy arrays).
    61	    # per_point_dev_pct is already list(); metrics keys are all primitives.
    62	    return JSONResponse(ctx)
    63	
    64	
    65	@router.get(
    66	    "/cases/{case_id}/runs/{run_label}/comparison-report.pdf",
    67	    tags=["comparison-report"],
    68	)
    69	def get_comparison_report_pdf(case_id: str, run_label: str) -> FileResponse:
    70	    """Render (or re-render) PDF and stream it back."""
    71	    _validate_ids(case_id, run_label)
    72	    try:
    73	        path = render_report_pdf(case_id, run_label)
    74	    except ReportError as e:
    75	        raise HTTPException(status_code=404, detail=str(e))
    76	    except ImportError:
    77	        raise HTTPException(
    78	            status_code=503,
    79	            detail="WeasyPrint unavailable on this server; set DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib",
    80	        )
    81	    return FileResponse(
    82	        path,
    83	        media_type="application/pdf",
    84	        filename=f"{case_id}__{run_label}__comparison_report.pdf",
    85	    )
    86	
    87	
    88	@router.post(
    89	    "/cases/{case_id}/runs/{run_label}/comparison-report/build",
    90	    tags=["comparison-report"],
    91	)
    92	def build_comparison_report(case_id: str, run_label: str) -> JSONResponse:
    93	    """Force-rebuild HTML + PDF, return manifest."""
    94	    _validate_ids(case_id, run_label)
    95	    try:
    96	        html = render_report_html(case_id, run_label)
    97	        pdf_path = render_report_pdf(case_id, run_label)
    98	    except ReportError as e:
    99	        raise HTTPException(status_code=404, detail=str(e))
   100	    except ImportError:
   101	        raise HTTPException(status_code=503, detail="WeasyPrint unavailable")
   102	    return JSONResponse({
   103	        "case_id": case_id,
   104	        "run_label": run_label,
   105	        "pdf_path": str(pdf_path),
   106	        "html_bytes": len(html),
   107	    })

 succeeded in 0ms:
46:      { id: "mesh_20", label: "20²", n: 400 },
48:      { id: "mesh_80", label: "80²", n: 6400 },
82:      { id: "mesh_20", label: "20² uniform", n: 400 },
84:      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
91:      { id: "mesh_20", label: "20² uniform", n: 400 },
93:      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
101:      { id: "mesh_40", label: "40³ hybrid", n: 64000 },
127:      { id: "mesh_20", label: "20² uniform", n: 400 },
129:      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
146:  UNKNOWN: "text-surface-400",
194:      <div className="mx-auto max-w-3xl px-6 py-16 text-center text-surface-400">
196:        <Link to="/learn" className="mt-4 inline-block text-sky-400 hover:text-sky-300">
212:          <span className="mono text-surface-400">{caseId}</span>
218:            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-emerald-700/60 hover:bg-surface-900 hover:text-emerald-300"
222:            <span className="mono text-surface-600 group-hover:text-emerald-400">
228:            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-amber-700/60 hover:bg-surface-900 hover:text-amber-300"
232:            <span className="mono text-surface-600 group-hover:text-amber-400">
238:            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-sky-700/60 hover:bg-surface-900 hover:text-sky-300"
242:            <span className="mono text-surface-600 group-hover:text-sky-400">
258:          <p className="mt-1 text-[13px] text-surface-400">
280:                  : "text-surface-400 hover:bg-surface-900 hover:text-surface-200"
323:              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-sky-400" aria-hidden />
365:      <ScientificComparisonReportSection caseId={caseId} />
438:      <ErrorCallout
500:            <p className="mt-3 text-[12px] leading-relaxed text-surface-400">
598:      <div className="mt-3 flex items-baseline justify-between text-[12px] text-surface-400">
658:        className="absolute top-5 -translate-x-1/2 mono text-[10px] text-surface-400"
721:        <p className="text-[13px] leading-relaxed text-surface-400">
821:                : "text-surface-400"
837:        <div className="mt-4 text-[12px] leading-relaxed text-surface-400">
846:      <section className="rounded-md border border-surface-800/60 bg-surface-900/20 p-5 text-[12px] leading-relaxed text-surface-400">
1027:        <p className="mt-4 text-[12px] leading-relaxed text-surface-400">
1210:          <p className="mt-1 text-[11px] text-surface-400">
1228:function ErrorCallout({ message }: { message: string }) {
1238:    <div className="rounded-md border border-surface-800 bg-surface-900/30 p-4 text-[13px] text-surface-400">
1281:function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
1284:    queryKey: ["comparison-report-ctx", caseId, runLabel],
1289:        )}/comparison-report/context`,
1300:  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
1301:  // → silent hide) from 5xx / malformed JSON / network errors (show banner
1305:    if (status === 404 || status === 400) return null; // case not opted-in
1312:        <ErrorCallout
1329:  )}/comparison-report`;
1332:  )}/comparison-report.pdf`;
1361:              <div className="text-surface-400">max |dev|</div>
1367:              <div className="text-surface-400">n_pass</div>
1373:              <div className="text-surface-400">L²</div>
1379:              <div className="text-surface-400">L∞</div>
1410:          className="h-[1400px] w-full border-0"

 succeeded in 0ms:
     1	"""Phase 7c — comparison_report service unit tests (CI-safe, no real artifacts).
     2	
     3	Builds a synthetic artifact tree in tmp_path, monkeypatches the module's root
     4	constants, exercises render_report_html + build_report_context + the Codex
     5	round-1 HIGH containment guards.
     6	"""
     7	from __future__ import annotations
     8	
     9	import json
    10	from pathlib import Path
    11	
    12	import pytest
    13	
    14	
    15	@pytest.fixture
    16	def synthetic_tree(tmp_path: pytest.TempPathFactory, monkeypatch):
    17	    """Build a minimal Phase-7a-and-7b-compatible artifact tree in tmp_path."""
    18	    root = tmp_path
    19	    case = "lid_driven_cavity"
    20	    ts = "20260421T000000Z"
    21	
    22	    fields_root = root / "reports" / "phase5_fields"
    23	    renders_root = root / "reports" / "phase5_renders"
    24	    case_fields = fields_root / case / ts
    25	    (case_fields / "sample" / "1000").mkdir(parents=True)
    26	    (case_fields / "sample" / "1000" / "uCenterline.xy").write_text(
    27	        "#   y   U_x   U_y   U_z   p\n"
    28	        "0     0      0     0    0.5\n"
    29	        "0.5  -0.2    0     0    0.5\n"
    30	        "1.0   1.0    0     0    0.5\n",
    31	        encoding="utf-8",
    32	    )
    33	    (case_fields / "residuals.csv").write_text(
    34	        "Time,Ux,Uy,p\n0,N/A,N/A,N/A\n1,1.0,1.0,1.0\n2,0.1,0.1,0.1\n",
    35	        encoding="utf-8",
    36	    )
    37	    (fields_root / case / "runs").mkdir(parents=True)
    38	    (fields_root / case / "runs" / "audit_real_run.json").write_text(
    39	        json.dumps({"timestamp": ts, "case_id": case, "run_label": "audit_real_run"}),
    40	        encoding="utf-8",
    41	    )
    42	
    43	    # Minimal render outputs (empty PNGs are fine for containment checks).
    44	    renders_case = renders_root / case / ts
    45	    renders_case.mkdir(parents=True)
    46	    for name in ["profile_u_centerline.png", "pointwise_deviation.png",
    47	                 "contour_u_magnitude.png", "residuals.png"]:
    48	        (renders_case / name).write_bytes(b"\x89PNG\r\n\x1a\n")  # 8-byte stub
    49	    (renders_root / case / "runs").mkdir(parents=True)
    50	    (renders_root / case / "runs" / "audit_real_run.json").write_text(
    51	        json.dumps({
    52	            "case_id": case, "run_label": "audit_real_run", "timestamp": ts,
    53	            "outputs": {
    54	                "profile_png": f"reports/phase5_renders/{case}/{ts}/profile_u_centerline.png",
    55	                "pointwise_deviation_png": f"reports/phase5_renders/{case}/{ts}/pointwise_deviation.png",
    56	                "contour_u_magnitude_png": f"reports/phase5_renders/{case}/{ts}/contour_u_magnitude.png",
    57	                "residuals_png": f"reports/phase5_renders/{case}/{ts}/residuals.png",
    58	            },
    59	        }),
    60	        encoding="utf-8",
    61	    )
    62	
    63	    # Minimal LDC gold YAML in tmp_path/knowledge/gold_standards/.
    64	    gold_dir = root / "knowledge" / "gold_standards"
    65	    gold_dir.mkdir(parents=True)
    66	    (gold_dir / "lid_driven_cavity.yaml").write_text(
    67	        "quantity: u_centerline\n"
    68	        "reference_values:\n"
    69	        "  - y: 0.0\n    u: 0.0\n"
    70	        "  - y: 0.5\n    u: -0.20581\n"
    71	        "  - y: 1.0\n    u: 1.0\n"
    72	        "tolerance: 0.05\n"
    73	        "source: Ghia Ghia Shin 1982 Table I Re=100\n"
    74	        "literature_doi: 10.1016/0021-9991(82)90058-4\n",
    75	        encoding="utf-8",
    76	    )
    77	
    78	    # Minimal mesh_{20,40,80,160} fixtures for grid-convergence table.
    79	    fixture_case = root / "ui" / "backend" / "tests" / "fixtures" / "runs" / case
    80	    fixture_case.mkdir(parents=True)
    81	    for mesh, val in (("mesh_20", -0.055), ("mesh_40", -0.048),
    82	                      ("mesh_80", -0.044), ("mesh_160", -0.042)):
    83	        (fixture_case / f"{mesh}_measurement.yaml").write_text(
    84	            f"measurement:\n  value: {val}\n", encoding="utf-8",
    85	        )
    86	
    87	    from ui.backend.services import comparison_report as svc
    88	    monkeypatch.setattr(svc, "_REPO_ROOT", root)
    89	    monkeypatch.setattr(svc, "_FIELDS_ROOT", fields_root)
    90	    monkeypatch.setattr(svc, "_RENDERS_ROOT", renders_root)
    91	    monkeypatch.setattr(svc, "_GOLD_ROOT", gold_dir)
    92	    monkeypatch.setattr(svc, "_FIXTURE_ROOT", root / "ui" / "backend" / "tests" / "fixtures" / "runs")
    93	
    94	    return {"root": root, "case": case, "ts": ts, "svc": svc}
    95	
    96	
    97	def test_build_context_happy_path(synthetic_tree) -> None:
    98	    svc = synthetic_tree["svc"]
    99	    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
   100	    assert ctx["case_id"] == "lid_driven_cavity"
   101	    assert ctx["timestamp"] == "20260421T000000Z"
   102	    assert ctx["metrics"]["n_total"] == 3
   103	    assert ctx["verdict"] in ("PASS", "PARTIAL", "FAIL")
   104	
   105	
   106	def test_render_html_contains_8_sections(synthetic_tree) -> None:
   107	    svc = synthetic_tree["svc"]
   108	    html = svc.render_report_html("lid_driven_cavity", "audit_real_run")
   109	    for marker in ["参考文献", "中心线 profile", "逐点偏差分布",
   110	                   "流场 contour", "残差收敛历史", "网格收敛",
   111	                   "求解器元数据"]:
   112	        assert marker in html, f"missing §: {marker}"
   113	
   114	
   115	def test_rejects_tampered_manifest_timestamp(synthetic_tree) -> None:
   116	    """Codex round 1 HIGH: manifest with timestamp='../../outside' must be rejected."""
   117	    svc = synthetic_tree["svc"]
   118	    root = synthetic_tree["root"]
   119	    # Overwrite manifest with malicious timestamp.
   120	    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   121	    m.write_text(json.dumps({"timestamp": "../../../../tmp/evil"}), encoding="utf-8")
   122	    with pytest.raises(svc.ReportError, match="invalid timestamp"):
   123	        svc.build_report_context("lid_driven_cavity", "audit_real_run")
   124	
   125	
   126	def test_rejects_non_matching_timestamp_shape(synthetic_tree) -> None:
   127	    """Timestamp must match exact YYYYMMDDTHHMMSSZ regex."""
   128	    svc = synthetic_tree["svc"]
   129	    root = synthetic_tree["root"]
   130	    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   131	    m.write_text(json.dumps({"timestamp": "2026-04-21"}), encoding="utf-8")
   132	    with pytest.raises(svc.ReportError):
   133	        svc.build_report_context("lid_driven_cavity", "audit_real_run")
   134	
   135	
   136	def test_rejects_tampered_renders_manifest_output_path(synthetic_tree) -> None:
   137	    """Codex round 1 HIGH: img src in renders manifest must be inside renders root."""
   138	    svc = synthetic_tree["svc"]
   139	    root = synthetic_tree["root"]
   140	    # Overwrite renders manifest with escape path.
   141	    rm = root / "reports" / "phase5_renders" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   142	    rm.write_text(
   143	        json.dumps({
   144	            "case_id": "lid_driven_cavity", "run_label": "audit_real_run",
   145	            "timestamp": "20260421T000000Z",
   146	            "outputs": {
   147	                "profile_png": "../../../../etc/passwd",
   148	                "pointwise_deviation_png": "/etc/passwd",
   149	                "contour_u_magnitude_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/contour_u_magnitude.png",
   150	                "residuals_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/residuals.png",
   151	            },
   152	        }),
   153	        encoding="utf-8",
   154	    )
   155	    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
   156	    # Escaped paths must be scrubbed to empty; the template will skip empty src.
   157	    assert ctx["renders"]["profile_png_rel"] in ("", None) \
   158	        or "etc/passwd" not in ctx["renders"]["profile_png_rel"]
   159	    assert "etc/passwd" not in ctx["renders"]["pointwise_png_rel"]
   160	    # Safe entries retained.
   161	    assert "reports/phase5_renders" in ctx["renders"]["contour_png_rel"]
   162	
   163	
   164	def test_rejects_non_object_run_manifest(synthetic_tree) -> None:
   165	    """Codex round 2 (7a precedent): non-object JSON must fail closed."""
   166	    svc = synthetic_tree["svc"]
   167	    root = synthetic_tree["root"]
   168	    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   169	    m.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
   170	    with pytest.raises(svc.ReportError, match="not an object"):
   171	        svc.build_report_context("lid_driven_cavity", "audit_real_run")
   172	
   173	
   174	def test_pdf_output_path_contained(synthetic_tree, tmp_path: Path) -> None:
   175	    """Codex round 1 HIGH: caller-supplied output_path must stay under reports/phase5_reports/."""
   176	    svc = synthetic_tree["svc"]
   177	    # Attempt to write PDF outside the reports tree.
   178	    evil = tmp_path / "outside" / "evil.pdf"
   179	    with pytest.raises(svc.ReportError, match="escapes reports_root"):
   180	        svc.render_report_pdf("lid_driven_cavity", "audit_real_run", output_path=evil)

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '1,340p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7c — CFD vs Gold comparison report service.
     2	
     3	Renders an 8-section HTML report for a given (case_id, run_label), using:
     4	- Phase 7a field artifacts at reports/phase5_fields/{case}/{ts}/
     5	- Phase 7b rendered figures at reports/phase5_renders/{case}/{ts}/
     6	- knowledge/gold_standards/{case}.yaml gold reference
     7	- ui/backend/tests/fixtures/runs/{case}/mesh_{20,40,80,160}_measurement.yaml for grid convergence
     8	
     9	Backend route: ui/backend/routes/comparison_report.py calls `render_report_html`
    10	and `render_report_pdf` from this module. No DOM / no JS — static HTML + PNG
    11	inlined assets referenced by file:// for WeasyPrint PDF, served via FileResponse
    12	or embedded iframe on frontend.
    13	
    14	Design: report_html is a self-contained string (no asset URLs pointing to
    15	/api/... — uses file:// for PDF rendering and relative paths for HTML serving).
    16	"""
    17	from __future__ import annotations
    18	
    19	import datetime
    20	import json
    21	import math
    22	import re
    23	import subprocess
    24	from pathlib import Path
    25	from typing import Any, Optional
    26	
    27	import numpy as np
    28	import yaml
    29	from jinja2 import Environment, FileSystemLoader, select_autoescape
    30	
    31	# Codex round 1 HIGH (2026-04-21): strict shape gate on manifest-supplied
    32	# timestamp and artifact paths. Mirrors ui/backend/services/field_artifacts.py
    33	# defense-in-depth pattern so tampered runs/{label}.json cannot steer reads
    34	# outside reports/phase5_fields/ or writes outside reports/phase5_reports/.
    35	_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")
    36	
    37	_MODULE_DIR = Path(__file__).resolve().parent
    38	_REPO_ROOT = _MODULE_DIR.parents[2]
    39	_TEMPLATES = _MODULE_DIR.parent / "templates"
    40	_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"
    41	_RENDERS_ROOT = _REPO_ROOT / "reports" / "phase5_renders"
    42	_GOLD_ROOT = _REPO_ROOT / "knowledge" / "gold_standards"
    43	_FIXTURE_ROOT = _REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"
    44	
    45	_REPORT_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})
    46	
    47	_env = Environment(
    48	    loader=FileSystemLoader(str(_TEMPLATES)),
    49	    autoescape=select_autoescape(["html", "htm"]),
    50	)
    51	
    52	
    53	class ReportError(Exception):
    54	    """Recoverable — caller should 404 or return partial payload."""
    55	
    56	
    57	# ---------------------------------------------------------------------------
    58	# Data assembly
    59	# ---------------------------------------------------------------------------
    60	
    61	
    62	def _run_manifest_path(case_id: str, run_label: str) -> Path:
    63	    return _FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    64	
    65	
    66	def _renders_manifest_path(case_id: str, run_label: str) -> Path:
    67	    return _RENDERS_ROOT / case_id / "runs" / f"{run_label}.json"
    68	
    69	
    70	def _load_run_manifest(case_id: str, run_label: str) -> dict:
    71	    p = _run_manifest_path(case_id, run_label)
    72	    if not p.is_file():
    73	        raise ReportError(f"no run manifest for {case_id}/{run_label}")
    74	    data = json.loads(p.read_text(encoding="utf-8"))
    75	    if not isinstance(data, dict):
    76	        raise ReportError(f"run manifest not an object: {p}")
    77	    return data
    78	
    79	
    80	def _load_renders_manifest(case_id: str, run_label: str) -> Optional[dict]:
    81	    p = _renders_manifest_path(case_id, run_label)
    82	    if not p.is_file():
    83	        return None
    84	    data = json.loads(p.read_text(encoding="utf-8"))
    85	    if not isinstance(data, dict):
    86	        return None
    87	    return data
    88	
    89	
    90	def _validated_timestamp(ts: Any) -> Optional[str]:
    91	    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
    92	    match the exact YYYYMMDDTHHMMSSZ shape. Blocks '../../outside' etc."""
    93	    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
    94	        return None
    95	    return ts
    96	
    97	
    98	def _safe_rel_under(candidate: str, root: Path) -> Optional[str]:
    99	    """Return `candidate` if it resolves under `root`, else None.
   100	
   101	    Used to validate manifest-supplied output file paths before they flow
   102	    into template `img src`. Prevents a tampered renders manifest from
   103	    pointing WeasyPrint base_url resolution at arbitrary local files
   104	    (which would then be embedded into PDFs as image data URLs).
   105	    """
   106	    if not isinstance(candidate, str) or not candidate:
   107	        return None
   108	    if candidate.startswith("/") or "\\" in candidate or ".." in candidate.split("/"):
   109	        return None
   110	    try:
   111	        resolved = (_REPO_ROOT / candidate).resolve(strict=False)
   112	        resolved.relative_to(root.resolve())
   113	    except (ValueError, OSError):
   114	        return None
   115	    return candidate
   116	
   117	
   118	def _load_ldc_gold() -> tuple[list[float], list[float], dict]:
   119	    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
   120	    if not gold_path.is_file():
   121	        raise ReportError(f"gold file missing: {gold_path}")
   122	    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
   123	    u_doc = next(
   124	        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
   125	        None,
   126	    )
   127	    if u_doc is None:
   128	        raise ReportError("no u_centerline doc in LDC gold")
   129	    ys: list[float] = []
   130	    us: list[float] = []
   131	    for entry in u_doc.get("reference_values", []):
   132	        if isinstance(entry, dict):
   133	            y = entry.get("y")
   134	            u = entry.get("value") or entry.get("u")
   135	            if y is not None and u is not None:
   136	                ys.append(float(y))
   137	                us.append(float(u))
   138	    return ys, us, u_doc
   139	
   140	
   141	def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
   142	    rows = []
   143	    for line in path.read_text(encoding="utf-8").splitlines():
   144	        s = line.strip()
   145	        if not s or s.startswith("#"):
   146	            continue
   147	        parts = s.split()
   148	        try:
   149	            rows.append([float(parts[0]), float(parts[1])])
   150	        except (ValueError, IndexError):
   151	            continue
   152	    if not rows:
   153	        raise ReportError(f"empty sample: {path}")
   154	    arr = np.array(rows)
   155	    return arr[:, 0], arr[:, 1]
   156	
   157	
   158	def _latest_sample_iter(artifact_dir: Path) -> Path:
   159	    sample_root = artifact_dir / "sample"
   160	    if not sample_root.is_dir():
   161	        raise ReportError(f"sample/ missing under {artifact_dir}")
   162	    iters = sorted(
   163	        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
   164	        key=lambda d: int(d.name),
   165	    )
   166	    if not iters:
   167	        raise ReportError(f"no sample iter dirs under {sample_root}")
   168	    return iters[-1]
   169	
   170	
   171	def _compute_metrics(
   172	    y_sim: np.ndarray, u_sim: np.ndarray,
   173	    y_gold: list[float], u_gold: list[float],
   174	    tolerance_pct: float,
   175	) -> dict[str, Any]:
   176	    """Compute L2/Linf/RMS + per-point |dev|% + pass count."""
   177	    y_sim_norm = y_sim / max(float(y_sim.max()), 1e-12)
   178	    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
   179	    u_gold_arr = np.array(u_gold)
   180	    diff = u_sim_interp - u_gold_arr
   181	
   182	    denom = np.where(np.abs(u_gold_arr) < 1e-9, 1e-9, np.abs(u_gold_arr))
   183	    dev_pct = 100.0 * np.abs(diff) / denom
   184	    n_total = len(u_gold_arr)
   185	    n_pass = int((dev_pct < tolerance_pct).sum())
   186	
   187	    return {
   188	        "l2": float(np.sqrt(np.mean(diff ** 2))),
   189	        "linf": float(np.max(np.abs(diff))),
   190	        "rms": float(np.sqrt(np.mean(diff ** 2))),  # alias
   191	        "max_dev_pct": float(dev_pct.max()) if n_total else 0.0,
   192	        "n_pass": n_pass,
   193	        "n_total": n_total,
   194	        "per_point_dev_pct": dev_pct.tolist(),
   195	    }
   196	
   197	
   198	def _parse_residuals_csv(path: Path) -> dict[str, Any]:
   199	    if not path.is_file():
   200	        return {"total_iter": 0, "final_ux": None, "note": None}
   201	    lines = path.read_text(encoding="utf-8").splitlines()
   202	    if len(lines) < 2:
   203	        return {"total_iter": 0, "final_ux": None, "note": None}
   204	    header = [c.strip() for c in lines[0].split(",")]
   205	    last = None
   206	    count = 0
   207	    for ln in lines[1:]:
   208	        parts = [c.strip() for c in ln.split(",")]
   209	        if len(parts) != len(header):
   210	            continue
   211	        last = parts
   212	        count += 1
   213	    final_ux = None
   214	    if last is not None and len(last) > 1 and last[1].upper() != "N/A":
   215	        try:
   216	            final_ux = float(last[1])
   217	        except ValueError:
   218	            pass
   219	    note = None
   220	    if final_ux is not None and final_ux > 1e-3:
   221	        note = (f"注意：Ux 终值 {final_ux:.2e} 大于 1e-3 — "
   222	                f"收敛可能未达稳态。建议增加 endTime 或降低 residualControl。")
   223	    return {"total_iter": count, "final_ux": final_ux, "note": note}
   224	
   225	
   226	def _load_grid_convergence(case_id: str, gold_y: list[float], gold_u: list[float]) -> tuple[list[dict], str]:
   227	    """Read mesh_20/40/80/160_measurement.yaml fixtures, build table rows."""
   228	    rows: list[dict] = []
   229	    # LDC fixtures compare at y≈0.0625 (first gold point >0).
   230	    sample_y = 0.0625
   231	    try:
   232	        sample_gold = next(u for y, u in zip(gold_y, gold_u) if abs(y - sample_y) < 1e-3)
   233	    except StopIteration:
   234	        sample_gold = gold_u[1] if len(gold_u) > 1 else 0.0
   235	
   236	    case_dir = _FIXTURE_ROOT / case_id
   237	    meshes = [("mesh_20", 20), ("mesh_40", 40), ("mesh_80", 80), ("mesh_160", 160)]
   238	    for name, _n in meshes:
   239	        path = case_dir / f"{name}_measurement.yaml"
   240	        if not path.is_file():
   241	            continue
   242	        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
   243	        meas = doc.get("measurement", {}) if isinstance(doc, dict) else {}
   244	        val = meas.get("value")
   245	        if val is None:
   246	            continue
   247	        try:
   248	            val_f = float(val)
   249	        except (ValueError, TypeError):
   250	            continue
   251	        denom = abs(sample_gold) if abs(sample_gold) > 1e-9 else 1e-9
   252	        dev_pct = 100.0 * abs(val_f - sample_gold) / denom
   253	        if dev_pct < 5.0:
   254	            verdict, cls = "PASS", "pass"
   255	        elif dev_pct < 10.0:
   256	            verdict, cls = "WARN", "warn"
   257	        else:
   258	            verdict, cls = "FAIL", "fail"
   259	        rows.append({
   260	            "mesh": name,
   261	            "value": val_f,
   262	            "dev_pct": dev_pct,
   263	            "verdict": verdict,
   264	            "verdict_class": cls,
   265	        })
   266	    if len(rows) < 2:
   267	        return rows, "insufficient mesh data"
   268	    devs = [r["dev_pct"] for r in rows]
   269	    monotone = all(devs[i] >= devs[i + 1] for i in range(len(devs) - 1))
   270	    note = "单调递减 ✓" if monotone else "非严格单调 — 检查 fixture"
   271	    return rows, note
   272	
   273	
   274	def _get_commit_sha() -> str:
   275	    try:
   276	        r = subprocess.run(
   277	            ["git", "rev-parse", "--short", "HEAD"],
   278	            capture_output=True, text=True, cwd=_REPO_ROOT, timeout=5,
   279	        )
   280	        return r.stdout.strip() or "unknown"
   281	    except (subprocess.SubprocessError, OSError):
   282	        return "unknown"
   283	
   284	
   285	# ---------------------------------------------------------------------------
   286	# Public API
   287	# ---------------------------------------------------------------------------
   288	
   289	
   290	def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
   291	    """Assemble all template variables. Raises ReportError on missing data."""
   292	    if case_id not in _REPORT_SUPPORTED_CASES:
   293	        raise ReportError(
   294	            f"case_id={case_id!r} not in Phase 7c MVP scope. "
   295	            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."
   296	        )
   297	
   298	    run_manifest = _load_run_manifest(case_id, run_label)
   299	    timestamp = _validated_timestamp(run_manifest.get("timestamp"))
   300	    if timestamp is None:
   301	        raise ReportError(
   302	            f"invalid timestamp in run manifest for {case_id}/{run_label}"
   303	        )
   304	    artifact_dir = _FIELDS_ROOT / case_id / timestamp
   305	    # Containment: must be inside _FIELDS_ROOT/case_id/ even after .resolve().
   306	    try:
   307	        artifact_dir.resolve(strict=True).relative_to(
   308	            (_FIELDS_ROOT / case_id).resolve()
   309	        )
   310	    except (ValueError, OSError, FileNotFoundError):
   311	        raise ReportError(f"artifact dir escapes fields root: {artifact_dir}")
   312	    if not artifact_dir.is_dir():
   313	        raise ReportError(f"artifact dir missing: {artifact_dir}")
   314	
   315	    # Load + compute
   316	    gold_y, gold_u, gold_doc = _load_ldc_gold()
   317	    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
   318	    latest_sample = _latest_sample_iter(artifact_dir)
   319	    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
   320	    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)
   321	
   322	    residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
   323	    grid_conv_rows, grid_note = _load_grid_convergence(case_id, gold_y, gold_u)
   324	
   325	    # Verdict logic: all-pass OR tolerance met.
   326	    is_all_pass = metrics["n_pass"] == metrics["n_total"] and metrics["n_total"] > 0
   327	    majority_pass = metrics["n_pass"] >= math.ceil(metrics["n_total"] * 0.6)
   328	    if is_all_pass:
   329	        verdict, verdict_gradient, subtitle = "PASS", "#059669 0%, #10b981 100%", (
   330	            f"全部 {metrics['n_total']} 个 gold 点在 ±{tolerance:.1f}% 容差内。"
   331	        )
   332	    elif majority_pass:
   333	        verdict, verdict_gradient, subtitle = "PARTIAL", "#d97706 0%, #f59e0b 100%", (
   334	            f"{metrics['n_pass']}/{metrics['n_total']} 点通过；"
   335	            f"{metrics['n_total'] - metrics['n_pass']} 点残差为已记录物理项 "
   336	            f"(见 DEC-V61-030 关于 Ghia 非均匀网格 vs 均匀网格的插值误差)。"
   337	        )
   338	    else:
   339	        verdict, verdict_gradient, subtitle = "FAIL", "#dc2626 0%, #ef4444 100%", (
   340	            f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparison_report_route.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7c — comparison report route tests.
     2	
     3	Guards route-level behavior: 200 on valid case/run, 404 on missing, 400 on
     4	traversal attempts. Actual HTML content is covered by unit tests of the
     5	service module.
     6	"""
     7	from __future__ import annotations
     8	
     9	from fastapi.testclient import TestClient
    10	
    11	from ui.backend.main import app
    12	
    13	client = TestClient(app)
    14	
    15	# These tests run against the real reports/phase5_fields/lid_driven_cavity/
    16	# artifact set which is .gitignored. In CI (no artifacts), they should 404 —
    17	# which is fine, they'll be re-collected on developer machines.
    18	
    19	
    20	def _has_ldc_artifacts() -> bool:
    21	    from pathlib import Path
    22	    manifest = Path("reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json")
    23	    return manifest.is_file()
    24	
    25	
    26	def test_html_200_when_artifacts_present() -> None:
    27	    if not _has_ldc_artifacts():
    28	        return  # skip silently on CI-style clean checkout
    29	    r = client.get("/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report")
    30	    assert r.status_code == 200, r.text
    31	    body = r.text
    32	    # 8 section markers from the Jinja template.
    33	    for marker in [
    34	        "参考文献",           # §2
    35	        "中心线 profile",      # §3
    36	        "逐点偏差分布",        # §4
    37	        "流场 contour",        # §5
    38	        "残差收敛历史",        # §6
    39	        "网格收敛",            # §7
    40	        "求解器元数据",        # §8
    41	    ]:
    42	        assert marker in body, f"missing section marker: {marker}"
    43	    # Verdict card must be present.
    44	    assert "verdict-card" in body
    45	
    46	
    47	def test_context_200_when_artifacts_present() -> None:
    48	    if not _has_ldc_artifacts():
    49	        return
    50	    r = client.get(
    51	        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
    52	    )
    53	    assert r.status_code == 200, r.text
    54	    d = r.json()
    55	    assert d["case_id"] == "lid_driven_cavity"
    56	    assert d["run_label"] == "audit_real_run"
    57	    assert "metrics" in d
    58	    assert d["metrics"]["n_total"] > 0
    59	    assert d["verdict"] in ("PASS", "PARTIAL", "FAIL")
    60	
    61	
    62	def test_html_404_unknown_case() -> None:
    63	    r = client.get("/api/cases/nonexistent_case/runs/audit_real_run/comparison-report")
    64	    assert r.status_code == 404
    65	
    66	
    67	def test_html_400_traversal_case_id() -> None:
    68	    r = client.get("/api/cases/..__pwn/runs/audit_real_run/comparison-report")
    69	    assert r.status_code == 400
    70	
    71	
    72	def test_html_400_traversal_run_label() -> None:
    73	    r = client.get("/api/cases/lid_driven_cavity/runs/..__pwn/comparison-report")
    74	    assert r.status_code == 400
    75	
    76	
    77	def test_context_400_urlencoded_traversal() -> None:
    78	    r = client.get(
    79	        "/api/cases/%2e%2e__pwn/runs/audit_real_run/comparison-report/context",
    80	    )
    81	    assert r.status_code == 400

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '340,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   340	            f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "
   341	            f"需要诊断 (solver, mesh, 或 gold 本身)。"
   342	        )
   343	
   344	    # Renders — use Phase 7b manifest if available; else None placeholders.
   345	    # Codex round 1 HIGH: every manifest-supplied output path is validated to
   346	    # resolve inside reports/phase5_renders/ before being emitted into HTML.
   347	    renders_manifest = _load_renders_manifest(case_id, run_label)
   348	    renders_dir = _RENDERS_ROOT / case_id / timestamp
   349	
   350	    def _rel(key: str, default: str = "") -> str:
   351	        candidate: Optional[str] = None
   352	        if renders_manifest:
   353	            raw = renders_manifest.get("outputs", {}).get(key)
   354	            if isinstance(raw, str):
   355	                validated = _safe_rel_under(raw, _RENDERS_ROOT)
   356	                if validated:
   357	                    candidate = validated
   358	        if candidate is None:
   359	            guess = renders_dir / default
   360	            if guess.is_file():
   361	                try:
   362	                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
   363	                    if _safe_rel_under(rel, _RENDERS_ROOT):
   364	                        candidate = rel
   365	                except ValueError:
   366	                    pass
   367	        return candidate or ""
   368	
   369	    renders = {
   370	        "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
   371	        "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
   372	        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
   373	        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
   374	    }
   375	
   376	    paper = {
   377	        "title": gold_doc.get("source", "Ghia, Ghia & Shin 1982 — Lid-Driven Cavity benchmark"),
   378	        "source": "J. Comput. Phys. 47, 387-411 (1982), Table I Re=100 column",
   379	        "doi": gold_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
   380	        "short": "Ghia 1982",
   381	        "gold_count": metrics["n_total"],
   382	        "tolerance_pct": tolerance,
   383	    }
   384	
   385	    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
   386	
   387	    return {
   388	        "case_id": case_id,
   389	        "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
   390	        "run_label": run_label,
   391	        "timestamp": timestamp,
   392	        "verdict": verdict,
   393	        "verdict_gradient": verdict_gradient,
   394	        "verdict_subtitle": subtitle,
   395	        "metrics": metrics,
   396	        "paper": paper,
   397	        "renders": renders,
   398	        "contour_caption": (
   399	            "Phase 7b MVP — 沿 x=0.5 中心线的 U_x 条带切片，后续 7b-polish 会用 VTK 体数据生成完整 2D contour。"
   400	        ),
   401	        "residual_info": residual_info,
   402	        "grid_conv": grid_conv_rows,
   403	        "grid_conv_note": grid_note,
   404	        "meta": {
   405	            "openfoam_version": "v10",
   406	            "solver": "simpleFoam (SIMPLE, laminar)",
   407	            "docker_image": "cfd-openfoam (local arm64 OpenFOAM v10)",
   408	            "commit_sha": _get_commit_sha(),
   409	            "mesh": "129×129 uniform",
   410	            "tolerance": f"±{tolerance:.1f}%",
   411	            "schemes": "steadyState + linearUpwind + Gauss linear corrected",
   412	            "report_generated_at": now,
   413	        },
   414	    }
   415	
   416	
   417	def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
   418	    """Return the full HTML string for the comparison report."""
   419	    ctx = build_report_context(case_id, run_label)
   420	    tmpl = _env.get_template("comparison_report.html.j2")
   421	    return tmpl.render(**ctx)
   422	
   423	
   424	def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
   425	                      output_path: Optional[Path] = None) -> Path:
   426	    """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.
   427	
   428	    Asset resolution: WeasyPrint converts the HTML's relative img src paths.
   429	    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.
   430	    """
   431	    # Import weasyprint lazily — heavy import, only when PDF actually needed.
   432	    import weasyprint  # type: ignore
   433	
   434	    html = render_report_html(case_id, run_label)
   435	    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/
   436	    # even when caller supplies output_path (containment against symlink tricks).
   437	    reports_root = (_REPO_ROOT / "reports" / "phase5_reports").resolve()
   438	    if output_path is None:
   439	        ctx = build_report_context(case_id, run_label)
   440	        ts = ctx["timestamp"]  # already validated by build_report_context
   441	        out_dir = reports_root / case_id / ts
   442	        out_dir.mkdir(parents=True, exist_ok=True)
   443	        output_path = out_dir / f"{run_label}_comparison_report.pdf"
   444	    try:
   445	        resolved_out = output_path.resolve(strict=False)
   446	        # Must stay inside reports/phase5_reports/
   447	        resolved_out.relative_to(reports_root)
   448	    except (ValueError, OSError):
   449	        raise ReportError(f"PDF output path escapes reports_root: {output_path}")
   450	
   451	    doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
   452	    doc.write_pdf(str(resolved_out))
   453	    return resolved_out

exec
/bin/zsh -lc "nl -ba ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | sed -n '1220,1415p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
  1220	        </Link>
  1221	      </div>
  1222	    </div>
  1223	  );
  1224	}
  1225	
  1226	// --- Shared callouts ----------------------------------------------------------
  1227	
  1228	function ErrorCallout({ message }: { message: string }) {
  1229	  return (
  1230	    <div className="rounded-md border border-contract-fail/40 bg-contract-fail/10 p-4 text-[13px] text-contract-fail">
  1231	      {message}
  1232	    </div>
  1233	  );
  1234	}
  1235	
  1236	function SkeletonCallout({ message }: { message: string }) {
  1237	  return (
  1238	    <div className="rounded-md border border-surface-800 bg-surface-900/30 p-4 text-[13px] text-surface-400">
  1239	      {message}
  1240	    </div>
  1241	  );
  1242	}
  1243	
  1244	// --- Phase 7f: Scientific CFD-vs-Gold comparison report section -----------
  1245	
  1246	type ComparisonReportContext = {
  1247	  case_id: string;
  1248	  case_display_name: string;
  1249	  run_label: string;
  1250	  timestamp: string;
  1251	  verdict: "PASS" | "PARTIAL" | "FAIL" | string;
  1252	  verdict_subtitle: string;
  1253	  metrics: {
  1254	    max_dev_pct: number;
  1255	    l2: number;
  1256	    linf: number;
  1257	    rms: number;
  1258	    n_pass: number;
  1259	    n_total: number;
  1260	  };
  1261	  paper: {
  1262	    title: string;
  1263	    source: string;
  1264	    doi?: string;
  1265	    short: string;
  1266	    gold_count: number;
  1267	    tolerance_pct: number;
  1268	  };
  1269	  renders: {
  1270	    profile_png_rel: string;
  1271	    pointwise_png_rel: string;
  1272	    contour_png_rel: string;
  1273	    residuals_png_rel: string;
  1274	  };
  1275	  meta: {
  1276	    commit_sha: string;
  1277	    report_generated_at: string;
  1278	  };
  1279	};
  1280	
  1281	function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
  1282	  const runLabel = "audit_real_run";
  1283	  const { data, isLoading, error } = useQuery<ComparisonReportContext, ApiError>({
  1284	    queryKey: ["comparison-report-ctx", caseId, runLabel],
  1285	    queryFn: async () => {
  1286	      const resp = await fetch(
  1287	        `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1288	          runLabel,
  1289	        )}/comparison-report/context`,
  1290	        { credentials: "same-origin" },
  1291	      );
  1292	      if (!resp.ok) throw new ApiError(resp.status, await resp.text());
  1293	      return (await resp.json()) as ComparisonReportContext;
  1294	    },
  1295	    retry: false,
  1296	    staleTime: 60_000,
  1297	  });
  1298	
  1299	  if (isLoading) return null; // quiet during fetch
  1300	  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
  1301	  // → silent hide) from 5xx / malformed JSON / network errors (show banner
  1302	  // so regressions are visible, not silently swallowed).
  1303	  if (error) {
  1304	    const status = error instanceof ApiError ? error.status : 0;
  1305	    if (status === 404 || status === 400) return null; // case not opted-in
  1306	    return (
  1307	      <section>
  1308	        <div className="mb-3 flex items-baseline justify-between">
  1309	          <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
  1310	          <p className="text-[11px] text-surface-500">报告服务暂不可用</p>
  1311	        </div>
  1312	        <ErrorCallout
  1313	          message={`无法加载对比报告 (HTTP ${status || "network"}): ${error.message.slice(0, 200)}`}
  1314	        />
  1315	      </section>
  1316	    );
  1317	  }
  1318	  if (!data) return null;
  1319	
  1320	  const verdictColor =
  1321	    data.verdict === "PASS"
  1322	      ? "bg-contract-pass/15 border-contract-pass/40 text-contract-pass"
  1323	      : data.verdict === "PARTIAL"
  1324	      ? "bg-yellow-500/10 border-yellow-500/40 text-yellow-300"
  1325	      : "bg-contract-fail/15 border-contract-fail/40 text-contract-fail";
  1326	
  1327	  const reportHtmlUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1328	    runLabel,
  1329	  )}/comparison-report`;
  1330	  const reportPdfUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1331	    runLabel,
  1332	  )}/comparison-report.pdf`;
  1333	
  1334	  return (
  1335	    <section>
  1336	      <div className="mb-3 flex items-baseline justify-between">
  1337	        <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
  1338	        <p className="text-[11px] text-surface-500">
  1339	          实际 OpenFOAM 真跑 · 8 sections · {data.meta.commit_sha}
  1340	        </p>
  1341	      </div>
  1342	
  1343	      <div
  1344	        className={`mb-4 rounded-md border p-4 ${verdictColor}`}
  1345	        role="status"
  1346	      >
  1347	        <div className="flex items-center justify-between gap-4">
  1348	          <div>
  1349	            <div className="text-[11px] font-semibold uppercase tracking-wider opacity-85">
  1350	              Verdict
  1351	            </div>
  1352	            <div className="mt-1 text-[22px] font-bold leading-tight">
  1353	              {data.verdict}
  1354	            </div>
  1355	            <div className="mt-1 text-[12px] text-surface-200">
  1356	              {data.verdict_subtitle}
  1357	            </div>
  1358	          </div>
  1359	          <div className="grid grid-cols-2 gap-3 text-right text-[12px]">
  1360	            <div>
  1361	              <div className="text-surface-400">max |dev|</div>
  1362	              <div className="mono text-surface-100">
  1363	                {data.metrics.max_dev_pct.toFixed(2)}%
  1364	              </div>
  1365	            </div>
  1366	            <div>
  1367	              <div className="text-surface-400">n_pass</div>
  1368	              <div className="mono text-surface-100">
  1369	                {data.metrics.n_pass} / {data.metrics.n_total}
  1370	              </div>
  1371	            </div>
  1372	            <div>
  1373	              <div className="text-surface-400">L²</div>
  1374	              <div className="mono text-surface-100">
  1375	                {data.metrics.l2.toFixed(4)}
  1376	              </div>
  1377	            </div>
  1378	            <div>
  1379	              <div className="text-surface-400">L∞</div>
  1380	              <div className="mono text-surface-100">
  1381	                {data.metrics.linf.toFixed(4)}
  1382	              </div>
  1383	            </div>
  1384	          </div>
  1385	        </div>
  1386	      </div>
  1387	
  1388	      <div className="mb-3 flex flex-wrap gap-2 text-[12px]">
  1389	        <a
  1390	          href={reportHtmlUrl}
  1391	          target="_blank"
  1392	          rel="noopener noreferrer"
  1393	          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
  1394	        >
  1395	          ↗ 新窗口打开完整报告
  1396	        </a>
  1397	        <a
  1398	          href={reportPdfUrl}
  1399	          download
  1400	          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
  1401	        >
  1402	          ↓ 下载 PDF
  1403	        </a>
  1404	      </div>
  1405	
  1406	      <div className="overflow-hidden rounded-md border border-surface-800 bg-white">
  1407	        <iframe
  1408	          title="CFD vs Gold comparison report"
  1409	          src={reportHtmlUrl}
  1410	          className="h-[1400px] w-full border-0"
  1411	          sandbox=""
  1412	        />
  1413	      </div>
  1414	    </section>
  1415	  );

codex
One gap is already visible in the tests: the new service suite is good, but the route suite still short-circuits on missing local artifacts. I’m verifying whether that leaves the original low-severity finding partially open, and I’m running the targeted backend tests plus a couple of adversarial checks to make sure the containment code behaves the way the implementation comments claim.
exec
/bin/zsh -lc "rg -n \"_resolve_run_timestamp|_artifact_dir|timestamp|relative_to|resolve\\(|manifest not an object|invalid timestamp\" scripts/render_case_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
32:# Codex round 1 HIGH (2026-04-21): enforce exact timestamp shape before
44:REPO_ROOT = Path(__file__).resolve().parent.parent
77:def _resolve_run_timestamp(case_id: str, run_label: str) -> str:
78:    """Read the per-run manifest written by phase5_audit_run.py and return its timestamp.
89:        raise RenderError(f"manifest not an object: {manifest_path}")
90:    ts = data.get("timestamp")
92:        raise RenderError(f"invalid timestamp shape in manifest: {ts!r}")
96:def _artifact_dir(case_id: str, timestamp: str) -> Path:
97:    d = FIELDS_ROOT / case_id / timestamp
98:    # Containment check even though timestamp is already shape-gated upstream.
100:        d.resolve(strict=True).relative_to((FIELDS_ROOT / case_id).resolve())
108:def _renders_dir(case_id: str, timestamp: str) -> Path:
109:    d = RENDERS_ROOT / case_id / timestamp
418:    timestamp = _resolve_run_timestamp(case_id, run_label)
419:    artifact_dir = _artifact_dir(case_id, timestamp)
420:    renders_dir = _renders_dir(case_id, timestamp)
444:        "timestamp": timestamp,
445:        "renders_dir_rel": str(renders_dir.relative_to(REPO_ROOT)),
446:        "outputs": {k: str(p.relative_to(REPO_ROOT)) for k, p in outputs.items()},

exec
/bin/zsh -lc "PYTHONPATH=. .venv/bin/python - <<'PY'
import tempfile
from pathlib import Path
from ui.backend.services import comparison_report as svc
print('timestamp valid', svc._validated_timestamp('20260421T000000Z'))
print('timestamp invalid', svc._validated_timestamp('../../../tmp/evil'))
reports_root = (svc._REPO_ROOT / 'reports' / 'phase5_reports').resolve()
print('reports_root', reports_root)
for raw in [Path('/tmp/evil.pdf'), reports_root / 'x' / 'y.pdf']:
    try:
        print(raw, '->', raw.resolve(strict=False).relative_to(reports_root))
    except Exception as e:
        print(raw, '->', type(e).__name__, str(e))
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
from ui.backend.services import comparison_report as svc
cases = [
    ('reports/phase5_renders/lid_driven_cavity/20260421T000000Z/profile.png', True),
    ('../../../../etc/passwd', False),
    ('reports/phase5_renders/../phase5_renders/lid_driven_cavity/x.png', False),
    ('reports/phase5_renders_symlink/x.png', False),
    ('reports\\\\phase5_renders\\\\x.png', False),
    ('/etc/passwd', False),
    ('', False),
]
for candidate, expected in cases:
    got = svc._safe_rel_under(candidate, svc._RENDERS_ROOT)
    print(candidate, '=>', got is not None, 'expected', expected)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_renders/lid_driven_cavity/20260421T000000Z/profile.png => True expected True
../../../../etc/passwd => False expected False
reports/phase5_renders/../phase5_renders/lid_driven_cavity/x.png => False expected False
reports/phase5_renders_symlink/x.png => False expected False
reports\phase5_renders\x.png => False expected False
/etc/passwd => False expected False
 => False expected False

 succeeded in 0ms:
timestamp valid 20260421T000000Z
timestamp invalid None
reports_root /Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_reports
/tmp/evil.pdf -> ValueError '/private/tmp/evil.pdf' is not in the subpath of '/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_reports'
/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_reports/x/y.pdf -> x/y.pdf

exec
/bin/zsh -lc 'PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_comparison_report_service.py ui/backend/tests/test_comparison_report_route.py -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 741ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0
collected 13 items

ui/backend/tests/test_comparison_report_service.py ......F               [ 53%]
ui/backend/tests/test_comparison_report_route.py ......                  [100%]

=================================== FAILURES ===================================
________________________ test_pdf_output_path_contained ________________________
ui/backend/tests/test_comparison_report_service.py:180: in test_pdf_output_path_contained
    svc.render_report_pdf("lid_driven_cavity", "audit_real_run", output_path=evil)
ui/backend/services/comparison_report.py:432: in render_report_pdf
    import weasyprint  # type: ignore
    ^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/weasyprint/__init__.py:372: in <module>
    from .css import preprocess_stylesheet  # noqa: I001, E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/weasyprint/css/__init__.py:29: in <module>
    from ..text.fonts import FontConfiguration
.venv/lib/python3.12/site-packages/weasyprint/text/fonts.py:17: in <module>
    from .constants import (  # isort:skip
.venv/lib/python3.12/site-packages/weasyprint/text/constants.py:5: in <module>
    from .ffi import pango
.venv/lib/python3.12/site-packages/weasyprint/text/ffi.py:476: in <module>
    gobject = _dlopen(
.venv/lib/python3.12/site-packages/weasyprint/text/ffi.py:464: in _dlopen
    return ffi.dlopen(names[0], flags)  # pragma: no cover
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/cffi/api.py:150: in dlopen
    lib, function_cache = _make_ffi_library(self, name, flags)
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/cffi/api.py:834: in _make_ffi_library
    backendlib = _load_backend_lib(backend, libname, flags)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/cffi/api.py:829: in _load_backend_lib
    raise OSError(msg)
E   OSError: cannot load library 'libgobject-2.0-0': dlopen(libgobject-2.0-0, 0x0002): tried: 'libgobject-2.0-0' (no such file), '/System/Volumes/Preboot/Cryptexes/OSlibgobject-2.0-0' (no such file), '/Users/Zhuanz/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/libgobject-2.0-0' (no such file), '/usr/lib/libgobject-2.0-0' (no such file, not in dyld cache), 'libgobject-2.0-0' (no such file).  Additionally, ctypes.util.find_library() did not manage to locate a library called 'libgobject-2.0-0'
----------------------------- Captured stdout call -----------------------------

-----

WeasyPrint could not import some external libraries. Please carefully follow the installation steps before reporting an issue:
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting 

-----

=========================== short test summary info ============================
FAILED ui/backend/tests/test_comparison_report_service.py::test_pdf_output_path_contained
========================= 1 failed, 12 passed in 0.50s =========================

codex
A real defect showed up under verification, not just a missing assertion: the new `test_pdf_output_path_contained` is not actually CI-safe here because `render_report_pdf()` imports WeasyPrint before it checks path containment. I’m confirming whether that also means the PDF route can leak a 500 when native WeasyPrint libs are absent, since the route currently only catches `ImportError`.
exec
/bin/zsh -lc "sed -n '400,470p' scripts/render_case_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_all(case_id: str, run_label: str = "audit_real_run") -> dict:
    """Render all 7b MVP figures for a given case/run. Returns {name: path, ...}."""
    if case_id not in RENDER_SUPPORTED_CASES:
        raise RenderError(
            f"case_id={case_id!r} not opted-in for Phase 7b rendering. "
            f"Supported: {sorted(RENDER_SUPPORTED_CASES)}. "
            f"Other cases unlock in Phase 7c Sprint-2."
        )
    timestamp = _resolve_run_timestamp(case_id, run_label)
    artifact_dir = _artifact_dir(case_id, timestamp)
    renders_dir = _renders_dir(case_id, timestamp)

    outputs: dict[str, Path] = {}
    renderers = [
        ("profile_png", render_profile_png),
        ("profile_plotly_json", render_profile_plotly_json),
        ("residuals_png", render_residuals_png),
        ("pointwise_deviation_png", render_pointwise_deviation_png),
        ("contour_u_magnitude_png", render_contour_u_magnitude_png),
    ]
    errors: dict[str, str] = {}
    for name, fn in renderers:
        try:
            outputs[name] = fn(case_id, artifact_dir, renders_dir)
        except Exception as e:  # noqa: BLE001  — keep batch alive
            errors[name] = f"{type(e).__name__}: {e}"
            print(f"[render] [WARN] {name} failed: {e}", file=sys.stderr)

    # Write per-run renders manifest (mirrors phase5_fields/{case}/runs/{label}.json).
    manifest_dir = RENDERS_ROOT / case_id / "runs"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "case_id": case_id,
        "run_label": run_label,
        "timestamp": timestamp,
        "renders_dir_rel": str(renders_dir.relative_to(REPO_ROOT)),
        "outputs": {k: str(p.relative_to(REPO_ROOT)) for k, p in outputs.items()},
        "errors": errors,
    }
    manifest_path = manifest_dir / f"{run_label}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[render] {case_id} → {len(outputs)}/{len(renderers)} outputs; manifest={manifest_path}")
    return {"manifest": manifest_path, **outputs}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 7b render pipeline for CFD audit artifacts")
    parser.add_argument("case_id", help="e.g. lid_driven_cavity")
    parser.add_argument("--run", dest="run_label", default="audit_real_run",
                        help="run_label (default: audit_real_run)")
    args = parser.parse_args(argv)
    try:
        render_all(args.case_id, args.run_label)
        return 0
    except RenderError as e:
        print(f"[render] FATAL {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

exec
/bin/zsh -lc "rg -n \"comparison-report|ScientificComparisonReportSection|ErrorCallout|LearnCaseDetailPage\" ui/frontend/tests ui/frontend/src --glob '"'!ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx'"'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 2 in 0ms:
rg: ui/frontend/tests: No such file or directory (os error 2)
ui/frontend/src/App.tsx:10:import { LearnCaseDetailPage } from "@/pages/learn/LearnCaseDetailPage";
ui/frontend/src/App.tsx:26:        <Route path="cases/:caseId" element={<LearnCaseDetailPage />} />

exec
/bin/zsh -lc "PYTHONPATH=. .venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from ui.backend.main import app
client = TestClient(app, raise_server_exceptions=False)
for url in [
    '/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf',
    '/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build',
]:
    r = client.get(url) if url.endswith('.pdf') else client.post(url)
    print(url, r.status_code)
    print(r.text[:300])
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 396ms:

-----

WeasyPrint could not import some external libraries. Please carefully follow the installation steps before reporting an issue:
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting 

-----

/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf 500
Internal Server Error

-----

WeasyPrint could not import some external libraries. Please carefully follow the installation steps before reporting an issue:
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting 

-----

/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build 500
Internal Server Error

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '688,694p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '356,366p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   688	- the user repeatedly required isolation: "在不干涉这两个notion项目的前提下" -> keep sibling Notion projects separate unless they explicitly ask for shared databases/relations [Task 1]
   689	- the user asked to integrate GSD and make it "完全自动化的开发，除了需要暂停下来让我定期手动触发Opus 4.6审查" -> automate by default but preserve hard manual review pauses [Task 2]
   690	- for freeze-signoff governance review, the user required a strict independent review with no writes to freeze artifacts -> treat this as review-only until the user explicitly changes scope [Task 3]
   691	- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]
   692	- when the user said "如果 approval granted，只能创建一个 executable approval YAML 和一个 approval action report" and "不得运行 populate-formal" -> approval sessions should only produce the allowed artifacts and must not spill into execution [Task 4]
   693	- when the request-package input said the executor "must not write manual intake state" and "must not be valid input to any CLI command" -> default manual-review-intake packaging work to markdown-only, non-mutating deliverables [Task 5]
   694	- when the user said acceptance "must not equal freeze approval" and "cannot directly enter final freeze signoff" -> always restate that `accepted_for_review` is not `freeze-complete`, even when readiness evidence looks strong [Task 3][Task 4]

 succeeded in 0ms:
   356	# Task Group: cfd-harness-unified governance closeout and planning gates
   357	
   358	scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
   359	applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
   360	
   361	## Task 1: Close Phase 8 and reconcile stale governance evidence
   362	
   363	### rollout_summary_files
   364	
   365	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
   366	

codex
I have enough to call it. The containment fix itself looks real, and the `/learn` error-visibility change also looks real. The remaining issues are around verification rigor: one PDF-path test is not actually environment-independent, and the route success-path coverage gap still exists because those tests continue to early-return on clean checkouts.
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparison_report_service.py | sed -n '170,182p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba scripts/render_case_report.py | sed -n '72,105p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   170	    with pytest.raises(svc.ReportError, match="not an object"):
   171	        svc.build_report_context("lid_driven_cavity", "audit_real_run")
   172	
   173	
   174	def test_pdf_output_path_contained(synthetic_tree, tmp_path: Path) -> None:
   175	    """Codex round 1 HIGH: caller-supplied output_path must stay under reports/phase5_reports/."""
   176	    svc = synthetic_tree["svc"]
   177	    # Attempt to write PDF outside the reports tree.
   178	    evil = tmp_path / "outside" / "evil.pdf"
   179	    with pytest.raises(svc.ReportError, match="escapes reports_root"):
   180	        svc.render_report_pdf("lid_driven_cavity", "audit_real_run", output_path=evil)

 succeeded in 0ms:
    72	# ---------------------------------------------------------------------------
    73	# I/O helpers
    74	# ---------------------------------------------------------------------------
    75	
    76	
    77	def _resolve_run_timestamp(case_id: str, run_label: str) -> str:
    78	    """Read the per-run manifest written by phase5_audit_run.py and return its timestamp.
    79	
    80	    Codex round 1 HIGH: enforce _TIMESTAMP_RE shape on the manifest value so a
    81	    tampered manifest cannot steer downstream path composition outside
    82	    reports/phase5_fields/.
    83	    """
    84	    manifest_path = FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    85	    if not manifest_path.is_file():
    86	        raise RenderError(f"no run manifest: {manifest_path}")
    87	    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    88	    if not isinstance(data, dict):
    89	        raise RenderError(f"manifest not an object: {manifest_path}")
    90	    ts = data.get("timestamp")
    91	    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
    92	        raise RenderError(f"invalid timestamp shape in manifest: {ts!r}")
    93	    return ts
    94	
    95	
    96	def _artifact_dir(case_id: str, timestamp: str) -> Path:
    97	    d = FIELDS_ROOT / case_id / timestamp
    98	    # Containment check even though timestamp is already shape-gated upstream.
    99	    try:
   100	        d.resolve(strict=True).relative_to((FIELDS_ROOT / case_id).resolve())
   101	    except (ValueError, OSError, FileNotFoundError):
   102	        raise RenderError(f"artifact dir escapes fields root: {d}")
   103	    if not d.is_dir():
   104	        raise RenderError(f"artifact dir missing: {d}")
   105	    return d

  ✓ Load review context from repo memory and inspect changed files for the three claimed closures
  ✓ Run targeted backend/frontend tests and adversarial checks relevant to the original findings
  → Summarize findings with severity, file/line references, and closure status for each round-1 item
codex
**Findings**
1. MEDIUM: the new PDF containment path is not fully verified and the PDF endpoints still 500 when WeasyPrint native libs are unavailable. In [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:432), `import weasyprint` runs before the `reports_root` containment check that starts at [line 437](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:437). The route only catches `ImportError` in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:72) and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:95), but on this machine the failure is `OSError`, so both PDF endpoints returned 500 and the new test at [test_comparison_report_service.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_service.py:174) failed before it ever exercised the containment guard.

2. LOW: the original low-severity coverage gap is only partially closed. The new service tests are useful, but the route success-path tests still early-return when artifacts are missing, so CI still does not exercise the HTML/context 200-path route integration. See [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:26) and [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:47).

Round-1 closure status:
- HIGH: closed in code. Timestamp shape-gating, field-artifact containment, render-path validation, and PDF output containment are present in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:90), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:298), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:344), and mirrored in [render_case_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:77).
- MEDIUM: closed in code. The `/learn` surface now hides only 400/404 and shows a visible banner for other failures in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1299).
- LOW: not fully closed. Service-level unit coverage was added, but route-level success coverage still depends on local artifacts.

Verification I ran:
- `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_comparison_report_service.py ui/backend/tests/test_comparison_report_route.py -q` → `12 passed, 1 failed`; the failure was `test_pdf_output_path_contained` due `OSError: cannot load library 'libgobject-2.0-0'`.
- `TestClient(app, raise_server_exceptions=False)` against `/comparison-report.pdf` and `/comparison-report/build` returned HTTP 500 in the current shell for the same reason.

Concrete next step: move the `output_path` containment check ahead of the WeasyPrint import, and map the actual native-lib load failure (`OSError`, or a broader PDF-backend exception) to the same 503 path. Then add one CI-safe route test that monkeypatches the service roots instead of depending on real artifact files.


tokens used
76,251
**Findings**
1. MEDIUM: the new PDF containment path is not fully verified and the PDF endpoints still 500 when WeasyPrint native libs are unavailable. In [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:432), `import weasyprint` runs before the `reports_root` containment check that starts at [line 437](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:437). The route only catches `ImportError` in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:72) and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:95), but on this machine the failure is `OSError`, so both PDF endpoints returned 500 and the new test at [test_comparison_report_service.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_service.py:174) failed before it ever exercised the containment guard.

2. LOW: the original low-severity coverage gap is only partially closed. The new service tests are useful, but the route success-path tests still early-return when artifacts are missing, so CI still does not exercise the HTML/context 200-path route integration. See [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:26) and [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:47).

Round-1 closure status:
- HIGH: closed in code. Timestamp shape-gating, field-artifact containment, render-path validation, and PDF output containment are present in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:90), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:298), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:344), and mirrored in [render_case_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:77).
- MEDIUM: closed in code. The `/learn` surface now hides only 400/404 and shows a visible banner for other failures in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1299).
- LOW: not fully closed. Service-level unit coverage was added, but route-level success coverage still depends on local artifacts.

Verification I ran:
- `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_comparison_report_service.py ui/backend/tests/test_comparison_report_route.py -q` → `12 passed, 1 failed`; the failure was `test_pdf_output_path_contained` due `OSError: cannot load library 'libgobject-2.0-0'`.
- `TestClient(app, raise_server_exceptions=False)` against `/comparison-report.pdf` and `/comparison-report/build` returned HTTP 500 in the current shell for the same reason.

Concrete next step: move the `output_path` containment check ahead of the WeasyPrint import, and map the actual native-lib load failure (`OSError`, or a broader PDF-backend exception) to the same 503 path. Then add one CI-safe route test that monkeypatches the service roots instead of depending on real artifact files.



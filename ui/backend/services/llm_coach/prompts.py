"""DEC-V61-119 · governance-aware system prompt composition.

Pure function — no I/O, no LLM tool registry, no orchestration. Given
a :class:`CaseCompletenessReport` snapshot and the project rules text,
return the system message string the route handler will prepend to
the user's history before opening the LLM stream.

Design constraints (per DEC-V61-119 §risk register):
  * ``max_missing_to_inline`` caps the inlined missing-field list so
    the prompt stays bounded as completeness reports grow large
    (Risk-5).
  * ``suggested_default`` values are skipped when they look like
    secrets — operator-authored data is the source, but defensive
    heuristics protect against accidental token leakage (Risk-6).
  * The role preamble explicitly names the LLM as a *read-only
    adviser* — no autonomous actions, must point engineer at
    ``field_path`` coordinates rather than fabricate data (Risk-4).
"""
from __future__ import annotations

import re
from typing import Iterable

from ui.backend.services.case_completeness import (
    CaseCompletenessReport,
    MissingField,
)
from ui.backend.services.mesh_quality import (
    MeshQualityReport,
    MeshWarning,
)

# Role + governance preamble. Kept compact; the bulk of token budget
# goes to the inlined case state below.
#
# DEC-V61-121: the rules now permit the AI to PROPOSE actions via a
# strict delimiter format. The engineer approves/rejects each
# proposal before anything applies — the AI itself still cannot
# mutate state directly.
DEFAULT_PROJECT_RULES = """\
You are the CFD Harness AI coach. Your role is to help an engineer \
complete and validate a CFD case under the project's governance rules.

Hard constraints:
  * Adviser + proposer. You MAY propose case modifications using the \
PROPOSAL delimiter format described below; the engineer must \
explicitly approve each one. You MUST NOT claim that an action has \
been applied — only the engineer's [Accept] click does that.
  * Point the engineer at the exact ``field_path`` coordinates the \
case-completeness analyzer reported. DO NOT invent field paths or \
fabricate values you weren't told.
  * "Critical" severity blocks ``ready_for_archive``. "Warning" and \
"info" are surfaced for awareness but do NOT block.
  * If the engineer asks for a value you don't see in the snapshot, \
say so plainly and suggest where to look (the manifest schema, the \
gold-standard physics_contract, or operator override) — do not \
guess.
  * Respect the engineer's language preference. The completeness \
analyzer may have authored ``why`` strings in zh-CN; reply in the \
same language unless the engineer switches.
"""


# DEC-V61-121: PROPOSAL delimiter contract. The frontend parser is
# strict — proposals MUST appear with these exact delimiters on
# their own lines, with valid YAML in between. Malformed proposals
# render as plain text and the engineer doesn't see an Accept button.
DEFAULT_PROPOSAL_INSTRUCTIONS = """\

=== Proposal protocol (DEC-V61-121) ===

When you want to propose a case modification, emit a YAML-fenced \
block with these exact delimiters on their own lines:

<<PROPOSAL
tool: <one of the registered tools below>
args:
  <key>: <value>
  ...
reason: <one-line zh/en explanation the engineer will see>
PROPOSAL>>

Rules:
  * The opening line MUST be exactly `<<PROPOSAL` and the closing \
line MUST be exactly `PROPOSAL>>`. No surrounding ``` fences.
  * `tool` MUST be one of the registered tools (see below). \
Unregistered tool names are rejected by the dispatcher.
  * `args` MUST satisfy the tool's argument schema. Bad args are \
rejected.
  * Emit at most ONE proposal per actionable item. If multiple \
patches need the same fix, emit one proposal per patch — the UI \
shows one Accept button per proposal.
  * NEVER emit a PROPOSAL block inside a Markdown code fence \
(``` ... ```) — that is for examples only, not real actions.
"""


def format_tool_registry_for_prompt() -> str:
    """Render the V121 tool registry as a string the system prompt
    can append. Pulled at compose time so changes to the registry
    propagate without any other edits."""
    # Local import to avoid a hard dep cycle when the registry imports
    # are not yet available at module load (unusual but defensive).
    from ui.backend.services.llm_coach.tool_registry import list_tools

    tools = list_tools()
    if not tools:
        return "(no tools registered — proposals are disabled this turn)"
    lines = ["=== Registered tools ==="]
    for t in tools:
        lines.append(f"- {t.name}: {t.description}")
    return "\n".join(lines)


# Heuristic: a suggested_default value of >40 chars matching common
# token shapes is probably a secret slipped in by mistake. Skip it
# from the prompt (the missing-field entry is still surfaced; just
# without the suspect value).
_SECRET_SHAPE_RE = re.compile(
    r"^("
    r"sk-[A-Za-z0-9_-]{20,}"          # OpenAI/DeepSeek-style API keys
    r"|ey[A-Za-z0-9_-]{20,}"          # JWT
    r"|[A-Fa-f0-9]{40,}"              # sha1+/sha256 hex
    r"|[A-Za-z0-9_-]{60,}"            # generic long opaque token
    r")$"
)


def _looks_like_secret(value: object) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) <= 40:
        return False
    return bool(_SECRET_SHAPE_RE.match(value))


def _format_missing_entry(entry: MissingField) -> str:
    """Render one missing-field row for the inlined snapshot.

    ``suggested_default`` is dropped if it looks like a secret;
    otherwise it's included so the LLM can offer it in its reply.
    """
    bullet = (
        f"- [{entry.severity.upper()}] field_path={entry.field_path} · "
        f"why={entry.why}"
    )
    if entry.suggested_default is not None and not _looks_like_secret(
        entry.suggested_default
    ):
        bullet += f" · suggested_default={entry.suggested_default!r}"
    return bullet


def _select_top_missing(
    missing: Iterable[MissingField],
    limit: int,
) -> tuple[list[MissingField], int]:
    """Pick up to ``limit`` entries, prioritizing critical > warning > info.

    Returns ``(picked, remainder_count)`` where ``remainder_count``
    counts how many entries did NOT make the cut (so the prompt can
    summarize "+ N more entries — ask to expand").
    """
    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    sorted_entries = sorted(
        missing, key=lambda e: severity_rank.get(e.severity, 99)
    )
    picked = sorted_entries[:limit]
    remainder = max(0, len(sorted_entries) - limit)
    return picked, remainder


def _format_mesh_warning(w: MeshWarning) -> str:
    return f"- [{w.severity.upper()}] {w.code}: {w.message}"


def _format_mesh_quality_section(report: MeshQualityReport) -> str:
    """Render the V61-122 mesh-quality block for the system prompt.

    Pure: no I/O. Always emits a deterministic shape for a given
    report so prompt readbacks are reproducible. Capped by the
    upstream report's own structure (V122 caps patch_face_counts
    naturally because patch counts per case are typically small).
    """
    parts: list[str] = ["=== Current mesh snapshot ==="]
    bb_min = report.bounding_box_min
    bb_max = report.bounding_box_max
    summary = (
        f"cells={report.cell_count} · points={report.point_count} · "
        f"internal_faces={report.internal_face_count} · "
        f"boundary_faces={report.boundary_face_count} · "
        f"bounding_box=[({bb_min[0]:g},{bb_min[1]:g},{bb_min[2]:g}),"
        f"({bb_max[0]:g},{bb_max[1]:g},{bb_max[2]:g})] · "
        f"volume={report.bounding_box_volume:g}"
    )
    if report.cells_per_unit_volume is not None:
        summary += f" · density={report.cells_per_unit_volume:g} cells/unit_vol"
    parts.append(summary)
    if report.warnings:
        parts.append("")
        parts.append(
            f"Mesh warnings ({len(report.warnings)}):"
        )
        parts.extend(_format_mesh_warning(w) for w in report.warnings)
    if report.patch_face_counts:
        parts.append("")
        parts.append("Patch face counts:")
        # Stable order so the prompt is reproducible across runs.
        for name in sorted(report.patch_face_counts):
            parts.append(f"- {name}: {report.patch_face_counts[name]}")
    # DEC-V61-126: surface checkMesh-derived metrics when present. The
    # AI coach uses these to make Fluent/StarCCM-grade quality
    # judgments (k-omega SST convergence depends on max skewness <
    # ~0.7, non-orthogonality < 70 degrees, etc). All fields are
    # optional; absent fields silently skip the line.
    has_checkmesh = (
        report.checkmesh_max_non_orthogonality_deg is not None
        or report.checkmesh_max_skewness is not None
        or report.checkmesh_max_aspect_ratio is not None
        or report.checkmesh_mesh_ok is not None
    )
    if has_checkmesh:
        parts.append("")
        parts.append("checkMesh quality metrics (OpenFOAM):")
        if report.checkmesh_max_non_orthogonality_deg is not None:
            parts.append(
                f"- max_non_orthogonality_deg="
                f"{report.checkmesh_max_non_orthogonality_deg:g}"
            )
        if report.checkmesh_max_skewness is not None:
            parts.append(
                f"- max_skewness={report.checkmesh_max_skewness:g}"
            )
        if report.checkmesh_max_aspect_ratio is not None:
            parts.append(
                f"- max_aspect_ratio={report.checkmesh_max_aspect_ratio:g}"
            )
        if report.checkmesh_n_severe_non_ortho_faces is not None:
            parts.append(
                f"- severe_non_orthogonal_faces="
                f"{report.checkmesh_n_severe_non_ortho_faces}"
            )
        if report.checkmesh_mesh_ok is not None:
            verdict = "PASS" if report.checkmesh_mesh_ok else "FAIL"
            parts.append(f"- mesh_ok={verdict}")
        if report.checkmesh_failed_checks:
            parts.append("- failed_checks:")
            for check in report.checkmesh_failed_checks:
                parts.append(f"  · {check}")
    return "\n".join(parts)


def build_coach_system_prompt(
    report: CaseCompletenessReport,
    project_rules: str = DEFAULT_PROJECT_RULES,
    *,
    max_missing_to_inline: int = 8,
    mesh_quality_report: MeshQualityReport | None = None,
) -> str:
    """Compose the coach system prompt from a completeness snapshot.

    Layers (in order):
      1. Project rules / role preamble (governance constraints).
      2. Case state line (case_id, kind, percentage, ready_for_archive,
         blocked_by_critical).
      3. Top-N missing fields, severity-ranked.
      4. Notes from the analyzer (if any) — surfaced verbatim so the
         LLM can quote the analyzer's own reasoning.

    Pure: no provider calls, no env reads, no logging side-effects.
    """
    if max_missing_to_inline < 0:
        raise ValueError("max_missing_to_inline must be non-negative")

    parts: list[str] = [project_rules.rstrip()]
    # DEC-V61-121: PROPOSAL protocol instructions + registered tool
    # list. Append AFTER the role preamble so the action-surface
    # rules sit alongside the role rules; engineers see the same
    # composition order in the audit-trail readback.
    parts.append(DEFAULT_PROPOSAL_INSTRUCTIONS.rstrip())
    parts.append("")
    parts.append(format_tool_registry_for_prompt())

    parts.append("")  # blank separator
    parts.append("=== Current case snapshot ===")
    parts.append(
        f"case_id={report.case_id} · case_kind={report.case_kind} · "
        f"completeness={report.percentage}% "
        f"({report.present_count}/{report.total_count} fields present) · "
        f"ready_for_archive={report.ready_for_archive} · "
        f"blocked_by_critical={report.blocked_by_critical}"
    )

    if report.missing:
        picked, remainder = _select_top_missing(
            report.missing, max_missing_to_inline
        )
        parts.append("")
        parts.append("=== Missing-field snapshot (top "
                     f"{len(picked)} of {len(report.missing)}, "
                     "severity-ranked) ===")
        parts.extend(_format_missing_entry(entry) for entry in picked)
        if remainder > 0:
            parts.append(
                f"... + {remainder} more missing entries (lower severity); "
                "ask the engineer if they want the full list."
            )
    else:
        parts.append("")
        parts.append(
            "=== Missing-field snapshot ===\n"
            "(none — all expected fields are present)"
        )

    if report.notes:
        parts.append("")
        parts.append("=== Analyzer notes ===")
        parts.extend(f"- {note}" for note in report.notes)

    # DEC-V61-122: optional mesh-quality section. Appended LAST so
    # the case-completeness layer (the load-bearing context) is
    # always near the top of the prompt; mesh quality is supplementary
    # context the AI may reference but is not the primary grounding
    # for "ready_for_archive" reasoning.
    if mesh_quality_report is not None:
        parts.append("")
        parts.append(_format_mesh_quality_section(mesh_quality_report))

    return "\n".join(parts)

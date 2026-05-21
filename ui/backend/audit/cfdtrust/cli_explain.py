"""`cfdtrust explain` — template-based AI advisor (M10).

Reads `artifacts/trust_report.json` + `case_manifest.yaml` and produces a
human-readable Markdown explanation of WHY each gate passed / failed,
plus actionable recommendations.

Honesty contract (per CLAUDE.md "AI advisor rules"):
  - MUST read trust_report.json + case_manifest.yaml (only).
  - MUST NOT modify case files, manifests, or trust_report.json.
  - MUST NOT turn FAIL into PASS in the explanation.
  - MUST NOT approve its own previous changes.
  - MUST surface limitations array from trust_report.
  - MUST be pure-Python rule-based — NO LLM. (The "AI advisor" is a
    deterministic rule-based renderer, not an opaque model. This way
    the explanation is reproducible and reviewable, consistent with
    "AI is advisor over evidence, not invisible evidence".)

Output: a Markdown document on stdout (or `--out <file>`). The
structure is:

  1. Header (case_id, generated_at, overall_status badge)
  2. TL;DR (1-3 sentences from the worst-failing gate)
  3. Per-gate breakdown with WHY + recommendation
  4. Honesty disclosures (limitations array verbatim)
  5. Next best action (single highest-priority recommendation)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml  # noqa: F401


# Severity ordering for recommendation prioritization.
# `blocker` = must-fix; case can't validate without resolving.
# `quality` = real defect but downstream of a blocker.
# `info`    = informational only (gate passed or is mocked).
_SEVERITY_RANK = {"blocker": 3, "quality": 2, "info": 1}


# ---------- Per-gate explainers ----------
#
# Each returns (why_paragraph, recommendation_or_None, severity_level).
# WHY paragraphs are written in plain language WITHOUT changing the
# audit's structured truth. Recommendations are derived from gate details
# in a deterministic way — same input → same output, every time.


def _explain_geometry(gate: Dict[str, Any], manifest: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
    status = gate.get("status", "UNKNOWN")
    det = gate.get("details", {}) or {}
    if status == "PASS":
        n = det.get("realized_patch_count", "?")
        return (
            f"All {n} realized polyMesh patches match the manifest's `required_patches`, "
            f"and the manifest's declared dimensionality matches the realized mesh "
            f"(empty patches present iff 2.5D/2D).",
            None,
            "info",
        )
    if status == "MOCKED":
        return (
            "solver_backend=mocked; blockMesh was not invoked, so the realized "
            "polyMesh geometry could not be inspected.",
            "Switch to `solver_backend: openfoam` in the manifest and re-run "
            "`cfdtrust run <case>` to exercise the real geometry audit.",
            "info",
        )
    if status == "BLOCKED":
        reason = det.get("reason") or "no_geometry_evidence"
        return (
            f"Geometry evidence missing or unparseable (reason: `{reason}`). "
            f"This usually means blockMesh has not yet been invoked, or it failed "
            f"before writing `constant/polyMesh/boundary`.",
            "Run `cfdtrust run <case>` with `solver_backend: openfoam`; if blockMesh "
            "fails, inspect `artifacts/solver.log` (the harness captures the failure "
            "diagnostic verbatim).",
            "blocker",
        )
    if status == "FAIL":
        pres = det.get("presence_dimension", {})
        dim = det.get("dimensionality_dimension", {})
        if pres.get("missing"):
            missing = pres["missing"]
            return (
                f"The realized polyMesh is missing patches the manifest declares as "
                f"required: `{missing}`. The case shipped a contract it cannot fulfill.",
                f"Either (a) add the missing patches `{missing}` to "
                f"`system/blockMeshDict.boundary`, or (b) remove them from "
                f"`manifest.geometry_contract.required_patches` if they aren't actually "
                f"required for this case.",
                "blocker",
            )
        if dim.get("dimension_status") == "FAIL":
            return (
                f"Dimensionality mismatch: {dim.get('reason') or 'unknown'}.",
                "OpenFOAM 2.5D / 2D meshes need an `empty` patch (front+back wedge "
                "convention). For 3D, remove any `empty` patches. Adjust either the "
                "manifest's `geometry_contract.dimensionality` field OR the "
                "`blockMeshDict.boundary` patch types.",
                "blocker",
            )
        if dim.get("dimension_status") == "INCOMPLETE":
            return (
                f"The manifest declares an unrecognized dimensionality "
                f"({dim.get('declared')!r}).",
                "Set `geometry_contract.dimensionality` to one of: `2D`, `2.5D`, `3D`.",
                "blocker",
            )
        return (gate.get("summary", "geometry FAIL"), None, "blocker")
    return (gate.get("summary", "geometry status unknown"), None, "info")


def _explain_mesh(gate: Dict[str, Any], manifest: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
    status = gate.get("status", "UNKNOWN")
    det = gate.get("details", {}) or {}
    if status == "PASS":
        return (
            "Mesh quality (skewness, non-orthogonality, aspect ratio) is within "
            "the manifest's `quality_thresholds`, AND the wall y+ is inside the "
            "manifest's `y_plus_target` range.",
            None,
            "info",
        )
    if status == "MOCKED":
        return (
            "solver_backend=mocked; checkMesh was not invoked.",
            "Switch to `solver_backend: openfoam` to exercise the real mesh audit.",
            "info",
        )
    if status == "BLOCKED":
        return (
            f"Mesh evidence missing or checkMesh blocked: {det.get('reason') or det.get('checkmesh_overall_ok')}.",
            "Inspect `artifacts/mesh_quality.log` for checkMesh's diagnostic.",
            "blocker",
        )
    if status == "FAIL":
        qual = det.get("quality_dimension", {})
        yp = det.get("y_plus_dimension", {})
        bits: List[str] = []
        recs: List[str] = []
        if qual.get("dimension_status") == "FAIL":
            for metric in qual.get("fails", []):
                m = qual["metrics"].get(metric, {})
                bits.append(
                    f"`{metric}` is {m.get('actual')} but the manifest's threshold is "
                    f"{m.get('threshold')}"
                )
            recs.append(
                "Improve mesh quality: refine cells, use grading, or run "
                "`renumberMesh` to reduce non-orthogonality."
            )
        if yp.get("dimension_status") == "FAIL":
            patch = yp.get("patch_evaluated", "?")
            avg = yp.get("actual_avg", "?")
            tmin, tmax = yp.get("target_min"), yp.get("target_max")
            bits.append(
                f"y+ on patch `{patch}` averages {avg}, outside the manifest's "
                f"target [{tmin}, {tmax}]"
            )
            if isinstance(avg, (int, float)) and isinstance(tmax, (int, float)) and avg > tmax:
                ratio = avg / max(tmax, 1e-9)
                recs.append(
                    f"y+ is too high by ~{ratio:.1f}× the target maximum. Refine the "
                    f"first-cell thickness near the wall (roughly halving it reduces y+ "
                    f"by ~2×). For wall-function policies, consider widening the y+ "
                    f"target to [30, 300] (high-Re wall function regime)."
                )
            elif isinstance(avg, (int, float)) and isinstance(tmin, (int, float)) and avg < tmin:
                recs.append(
                    "y+ is below the minimum target — the wall mesh is too fine "
                    "(over-resolved). Coarsen the first-cell to save compute."
                )
        why = "; ".join(bits) + "." if bits else gate.get("summary", "mesh FAIL")
        rec = " ".join(recs) if recs else None
        return (why, rec, "blocker")
    return (gate.get("summary", "mesh status unknown"), None, "info")


def _explain_bc(gate: Dict[str, Any], manifest: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
    status = gate.get("status", "UNKNOWN")
    det = gate.get("details", {}) or {}
    if status == "PASS":
        n_types = det.get("type_match", {}).get("checked_count", 0)
        n_vals = det.get("value_match", {}).get("matched_count", 0)
        n_der = det.get("derived_consistency", {}).get("matched_count", 0)
        return (
            f"All {n_types} BC type declarations match the realized 0/<field> files, "
            f"and {n_vals} numeric value(s) plus {n_der} derived turbulent quantity "
            f"derivation(s) (k from I·U, omega from k·L) match within tolerance.",
            None,
            "info",
        )
    if status == "MOCKED":
        return (
            "solver_backend=mocked; the harness did not parse the 0/ directory.",
            "Switch to `solver_backend: openfoam` to exercise the real BC audit.",
            "info",
        )
    if status == "BLOCKED":
        return (
            f"BC evidence missing: {det.get('reason') or 'unknown'}.",
            "Run `cfdtrust run <case>` so the backend parses the 0/ files.",
            "blocker",
        )
    if status == "FAIL":
        fp = det.get("file_presence", {})
        pc = det.get("patch_coverage", {})
        tm = det.get("type_match", {})
        vm = det.get("value_match", {})
        dr = det.get("derived_consistency", {})
        bits: List[str] = []
        recs: List[str] = []
        if fp.get("dimension_status") == "FAIL":
            missing = fp.get("missing_files", [])
            unparse = [u["field"] for u in fp.get("unparseable_files", [])]
            if missing:
                bits.append(f"missing 0/<field> files: `{missing}`")
                recs.append(
                    f"Create the missing field files in the case's `0/` directory. "
                    f"For each field, declare a `boundaryField` block listing every "
                    f"polyMesh patch."
                )
            if unparse:
                bits.append(f"unparseable 0/<field> files: `{unparse}`")
                recs.append(
                    "Inspect the listed files for missing `boundaryField { ... }` blocks "
                    "or syntax errors."
                )
        if pc.get("dimension_status") == "FAIL":
            gaps = pc.get("gaps_by_field", {})
            bits.append(f"missing BC entries per field: `{gaps}`")
            recs.append(
                "Add the missing patch entries to each affected 0/<field> file. "
                "OpenFOAM requires every polyMesh patch to have a BC declaration in "
                "every solved field."
            )
        if tm.get("dimension_status") == "FAIL":
            mm = tm.get("type_mismatches", [])
            if mm:
                bits.append(f"{len(mm)} type mismatch(es) between manifest and realized 0/<field>")
                example = mm[0] if mm else {}
                recs.append(
                    f"Example: patch `{example.get('resolved_patch')}` in field "
                    f"`{example.get('field')}` is declared as `{example.get('declared_type')}` "
                    f"in the manifest but realized as `{example.get('realized_type')}`. "
                    f"Decide which is correct, then update the other to match."
                )
            unres = tm.get("unresolvable_keys", [])
            if unres:
                bits.append(f"manifest BC key(s) match no realized patch nor type: `{unres}`")
                recs.append(
                    "Remove unresolvable keys from `manifest.bc_contract`, or fix the "
                    "spelling to match a realized polyMesh patch name / type."
                )
        if vm.get("dimension_status") == "FAIL":
            v_mm = vm.get("value_mismatches", [])
            v_miss = vm.get("value_missing", [])
            if v_mm:
                bits.append(f"{len(v_mm)} numeric value mismatch(es)")
                ex = v_mm[0]
                recs.append(
                    f"Example: `{ex['manifest_key']}.{ex['field_class']}.{ex['numeric_field']}` "
                    f"declares {ex['declared']} but realized is {ex['actual']} "
                    f"(`{ex['field']}` patch `{ex['resolved_patch']}`). Decide which is correct, "
                    f"then update the manifest or the 0/<field> file."
                )
            if v_miss:
                bits.append(f"{len(v_miss)} manifest numeric declarations have no realized value")
                recs.append(
                    "Add the missing `value uniform <X>` or `<param> X;` lines to the "
                    "corresponding BC entry in the 0/<field> file."
                )
        if dr.get("dimension_status") == "FAIL":
            d_mm = dr.get("derived_mismatches", [])
            if d_mm:
                bits.append(f"{len(d_mm)} derived-consistency mismatch(es) — k or omega does not match the I·U·L derivation")
                ex = d_mm[0]
                recs.append(
                    f"Example: `{ex['derivation']}` expects {ex['expected']:.4g} but realized "
                    f"is {ex['actual']:.4g} on patch `{ex['resolved_patch']}`. Either fix the "
                    f"realized value in the 0/<field> file, or correct the manifest's "
                    f"`intensity`/`magnitude_m_s`/`mixingLength` inputs."
                )
        why = "; ".join(bits) + "." if bits else gate.get("summary", "bc FAIL")
        rec = " ".join(recs) if recs else None
        return (why, rec, "blocker")
    return (gate.get("summary", "bc status unknown"), None, "info")


def _explain_solver(gate: Dict[str, Any], manifest: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
    status = gate.get("status", "UNKNOWN")
    det = gate.get("details", {}) or {}
    if status == "PASS":
        n = det.get("final_iter", "?")
        return (
            f"simpleFoam converged at iteration {n} with all residual targets met.",
            None,
            "info",
        )
    if status == "MOCKED":
        return (
            "Synthetic placeholder solver — no real CFD was executed.",
            "Switch to `solver_backend: openfoam` for real solver execution.",
            "info",
        )
    if status == "BLOCKED":
        reason = det.get("reason") or "unknown"
        return (
            f"Solver did not start or could not complete (reason: `{reason}`).",
            "Inspect `artifacts/solver.log` for the diagnostic.",
            "blocker",
        )
    if status == "FAIL":
        reason = det.get("reason") or "unknown"
        if reason == "residual_targets_not_met":
            failed = det.get("failed_fields", [])
            final_iter = det.get("final_iter", "?")
            max_iter = det.get("max_iter", "?")
            bits = [
                f"simpleFoam ran {final_iter}/{max_iter} iterations but {len(failed)} "
                f"field(s) did not reach residual target"
            ]
            for f in failed[:3]:
                bits.append(
                    f"`{f.get('field')}`: final residual {f.get('final_residual'):.3e} "
                    f"vs target {f.get('target'):.3e}"
                )
            rec = (
                f"Consider one of: (a) increase `solver_contract.max_iterations` "
                f"if convergence is slow but progressing; (b) widen the residual "
                f"target if the stalled value is physically acceptable; (c) inspect "
                f"the BCs / mesh — non-convergence often indicates a physical "
                f"inconsistency upstream."
            )
            return ("; ".join(bits) + ".", rec, "blocker")
        return (gate.get("summary", "solver FAIL"), None, "blocker")
    return (gate.get("summary", "solver status unknown"), None, "info")


def _explain_qoi(gate: Dict[str, Any], manifest: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
    status = gate.get("status", "UNKNOWN")
    if status == "PASS":
        return (
            "QoI extracted from solver output (e.g. wallShearStress → Cf "
            "distribution).",
            None,
            "info",
        )
    if status == "MOCKED":
        return (
            "QoI extraction not yet performed for this case.",
            "Wire the QoI extractor for this case-family if quantitative comparison "
            "is needed.",
            "info",
        )
    if status == "BLOCKED":
        return (gate.get("summary", "qoi BLOCKED"), None, "blocker")
    if status == "FAIL":
        return (gate.get("summary", "qoi FAIL"), None, "quality")
    return (gate.get("summary", "qoi status unknown"), None, "info")


def _explain_reference(gate: Dict[str, Any], manifest: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
    status = gate.get("status", "UNKNOWN")
    det = gate.get("details", {}) or {}
    if status == "PASS":
        return (
            "Realized QoI matches the canonical reference within the manifest's "
            "tolerance.",
            None,
            "info",
        )
    if status == "MOCKED":
        return (
            "No reference comparison performed (manifest declares "
            "`reference_comparison.status: not_finalized`).",
            "Finalize reference data — see `reference_comparison.source_url` for the "
            "upstream pointer.",
            "info",
        )
    if status == "BLOCKED":
        return (gate.get("summary", "reference BLOCKED"), None, "blocker")
    if status == "FAIL":
        return (
            gate.get("summary", "reference FAIL — realized QoI differs from canonical"),
            "Investigate whether the discrepancy comes from the mesh (often y+) or "
            "from the BCs / physics setup. Only when both the mesh_contract and "
            "bc_contract gates PASS can a reference FAIL be attributed to physics "
            "modeling rather than setup error.",
            "blocker",
        )
    return (gate.get("summary", "reference status unknown"), None, "info")


# Dispatch table — order matters; this is the order the explainer renders gates.
_GATE_EXPLAINERS = [
    ("geometry_contract", _explain_geometry),
    ("mesh_contract", _explain_mesh),
    ("bc_contract", _explain_bc),
    ("solver_execution", _explain_solver),
    ("qoi_extraction", _explain_qoi),
    ("reference_comparison", _explain_reference),
]


# ---------- Markdown rendering ----------


def _status_badge(status: str) -> str:
    """Visual badge for the status. Plain text, no emoji-dependent
    rendering — emoji only when ASCII-equivalent fits."""
    return {
        "PASS":    "PASS",
        "WARN":    "WARN",
        "FAIL":    "FAIL",
        "BLOCKED": "BLOCKED",
        "MOCKED":  "MOCKED",
    }.get(status, status or "UNKNOWN")


def _render_header(report: Dict[str, Any], case_id: str) -> str:
    lines = [
        f"# Trust Report Explanation: `{case_id}`",
        "",
        f"- Generated: `{report.get('generated_at', '?')}`",
        f"- Overall status: **{_status_badge(report.get('overall_status', '?'))}**",
        f"- Solver execution: `{report.get('solver_execution', '?')}`",
        f"- Validation status: `{report.get('validation_status', '?')}`",
        "",
    ]
    return "\n".join(lines)


def _render_tldr(report: Dict[str, Any], gate_severities: Dict[str, str]) -> str:
    overall = report.get("overall_status", "?")
    solver_execution = report.get("solver_execution", "?")
    if overall == "PASS":
        body = (
            "All audit gates passed and the realized QoI matches the canonical "
            "reference within tolerance. This case is validated under its declared "
            "case contract."
        )
    elif overall == "MOCKED":
        body = (
            "This run used a mocked solver — no real CFD was executed. This is not "
            "a validation result. To produce a validated result, set "
            "`solver_backend: openfoam` in the manifest and re-run."
        )
    elif overall == "BLOCKED":
        body = (
            "The trust harness could not complete one or more required gates. "
            "Resolve the BLOCKED gates below before this case can be evaluated."
        )
    elif overall == "WARN":
        # Codex R1-P3 fix: WARN must be its own branch — previously it
        # fell through to the FAIL message, which falsely told users
        # the case "did NOT pass its declared case contract" even when
        # every gate PASSed individually. The most common cause of WARN
        # today is DEC-V61-201-SUB-INGEST's overall-status demotion for
        # ingested cases whose gates all passed.
        if solver_execution == "ingested":
            body = (
                "Every audit gate passed individually on the ingested evidence, "
                "but the trust harness did not witness the solver run, so "
                "overall_status is capped at WARN (per DEC-V61-201-SUB-INGEST). "
                "validation_status is capped at `partial` for the same reason. "
                "To upgrade to PASS / validated, re-run the case under "
                "`cfdtrust run` so the harness owns the execution evidence."
            )
        else:
            # Codex R4-P2 fix: identify WARN contributors from the
            # actual `gates[*].status` field, NOT from `gate_severities`.
            # `_render_per_gate()` only returns severities in
            # {info, blocker, quality} — `none` / `pass` are not values
            # it produces, so the pre-fix predicate `sev not in
            # ("none", "pass")` was always True and would list every
            # PASS gate as a WARN contributor on a single-gate-warning
            # report. Use the gate status field directly so the list
            # matches what users see in the per-gate breakdown.
            gates = report.get("gates", {}) or {}
            warn_gates = [
                g for g, g_data in gates.items()
                if isinstance(g_data, dict) and g_data.get("status") != "PASS"
            ]
            if warn_gates:
                body = (
                    f"The case passed its declared contract but the harness "
                    f"surfaces non-blocking concerns in: `{warn_gates}`. Review "
                    f"the per-gate breakdown below; nothing here voids the trust "
                    f"verdict, but at least one gate carries a caveat."
                )
            else:
                body = (
                    "The case landed at WARN with no per-gate blockers. Inspect "
                    "the gate-level details and limitations section to understand "
                    "what was flagged."
                )
    else:  # FAIL
        blocker_gates = [g for g, sev in gate_severities.items() if sev == "blocker"]
        if blocker_gates:
            body = (
                f"This case did NOT pass its declared case contract. The harness "
                f"surfaces issues in: `{blocker_gates}`. Per the honesty rules, the "
                f"trust report does NOT claim validation when any audit gate FAILs."
            )
        else:
            body = (
                "This case has one or more FAILed gates. Per the honesty rules, "
                "no validation claim is made until every gate passes."
            )
    return "\n".join(["## TL;DR", "", body, ""])


def _render_per_gate(report: Dict[str, Any], manifest: Dict[str, Any]) -> Tuple[str, Dict[str, str]]:
    gates = report.get("gates", {}) or {}
    blocks: List[str] = ["## Per-gate breakdown", ""]
    severities: Dict[str, str] = {}
    recommendations: List[Tuple[str, str, str]] = []  # (gate, severity, rec_text)

    for gate_name, explainer in _GATE_EXPLAINERS:
        gate = gates.get(gate_name)
        if gate is None:
            blocks.append(f"### `{gate_name}`: *not reported*\n")
            continue
        why, rec, sev = explainer(gate, manifest)
        severities[gate_name] = sev
        blocks.append(f"### `{gate_name}`: **{_status_badge(gate.get('status', '?'))}**\n")
        if gate.get("summary"):
            blocks.append(f"**Summary:** {gate['summary']}\n")
        blocks.append(f"**Why:** {why}\n")
        if rec:
            blocks.append(f"**Recommendation:** {rec}\n")
            recommendations.append((gate_name, sev, rec))
        blocks.append("")

    return ("\n".join(blocks), severities)


def _render_honesty(report: Dict[str, Any]) -> str:
    limitations = report.get("limitations") or []
    if not limitations:
        return ""
    lines = ["## Honesty disclosures", ""]
    for lim in limitations:
        lines.append(f"- {lim}")
    lines.append("")
    return "\n".join(lines)


def _render_next_action(report: Dict[str, Any], severities: Dict[str, str]) -> str:
    overall = report.get("overall_status", "?")
    gates = report.get("gates", {}) or {}
    if overall == "PASS":
        return "\n".join([
            "## Next best action",
            "",
            "This case is validated. Consider adding it to a regression suite so "
            "future code changes are checked against this canonical result.",
            "",
        ])
    # For FAIL/BLOCKED, recommend addressing the FIRST blocker gate in render order.
    for gate_name, _ in _GATE_EXPLAINERS:
        if severities.get(gate_name) == "blocker":
            gate = gates.get(gate_name) or {}
            return "\n".join([
                "## Next best action",
                "",
                f"Address the blocker on `{gate_name}` first (status: "
                f"`{gate.get('status', '?')}`). Earlier gates in the audit chain "
                f"affect downstream gates, so fixing geometry/mesh/BC issues often "
                f"resolves apparent solver / reference failures too.",
                "",
            ])
    if overall == "MOCKED":
        return "\n".join([
            "## Next best action",
            "",
            "Switch to `solver_backend: openfoam` and re-run to exercise real audits.",
            "",
        ])
    return "\n".join([
        "## Next best action",
        "",
        "No critical blockers identified; review WARN entries above for refinements.",
        "",
    ])


def explain(case_dir: Path) -> str:
    """Read trust_report.json + case_manifest.yaml, return a Markdown string.

    Pure function; does NOT write to disk. The CLI wrapper handles
    stdout / --out file routing.
    """
    case_dir = Path(case_dir)
    report_path = case_dir / "artifacts" / "trust_report.json"
    manifest_path = case_dir / "case_manifest.yaml"

    if not report_path.exists():
        raise FileNotFoundError(
            f"trust_report.json not found at {report_path}. Run `cfdtrust report <case>` first."
        )
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"case_manifest.yaml not found at {manifest_path}."
        )

    report = json.loads(report_path.read_text())
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    case_id = report.get("case_id") or manifest.get("case_id") or case_dir.name

    sections: List[str] = [
        _render_header(report, case_id),
    ]
    per_gate, severities = _render_per_gate(report, manifest)
    sections.append(_render_tldr(report, severities))
    sections.append(per_gate)
    honesty = _render_honesty(report)
    if honesty:
        sections.append(honesty)
    sections.append(_render_next_action(report, severities))

    return "\n".join(sections)


def cmd_explain(case_path: str, out: Optional[str] = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on missing artifacts."""
    try:
        markdown = explain(Path(case_path))
    except FileNotFoundError as e:
        print(f"[cfdtrust] FAIL {e}", file=sys.stderr)
        return 1
    if out:
        Path(out).write_text(markdown)
        print(f"[cfdtrust] OK   explanation written to {out}")
    else:
        sys.stdout.write(markdown)
        if not markdown.endswith("\n"):
            sys.stdout.write("\n")
    return 0

"""Case reference-bundle export — downloadable zip per case.

Scope: this is a *reference bundle*, NOT a turnkey OpenFOAM case dir.
It ships the gold-standard YAML, a plain-text validation contract,
and a README pointing at authoritative OpenFOAM tutorials + the
literature source for the gold anchor. A student who downloads this
can reproduce the validation contract locally without needing to
query the live harness; they'll still need to build their own
OpenFOAM case from official tutorials.

Why not ship a full runnable case dir?
1. `src/foam_agent_adapter.py` (which owns the generators) is inside
   the v6.1 三禁区 perimeter — no autonomous modifications.
2. Hand-curating 10 cases' blockMesh/fvSchemes/controlDict would
   drift from what the adapter actually runs — two sources of truth
   is worse than one.
3. OpenFOAM's own tutorials at $FOAM_TUTORIALS already cover each of
   these canonical cases. Pointing students there is more honest
   than shipping a stale fork.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ui.backend.services.validation_report import (
    _load_gold_standard,  # noqa: SLF001 — read-only helper, scoped reuse
    _load_whitelist,  # noqa: SLF001
)

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD_DIR = REPO_ROOT / "knowledge" / "gold_standards"


def _render_readme(case_id: str, case: dict, gold: dict | None) -> str:
    """Render the zip's top-level README.md as Markdown."""
    name = case.get("name", case_id)
    reference = case.get("reference") or (gold or {}).get("source", "")
    doi = case.get("doi") or (gold or {}).get("literature_doi", "")
    flow_type = case.get("flow_type", "UNKNOWN")
    geometry = case.get("geometry_type", "UNKNOWN")
    solver = case.get("solver", "simpleFoam")
    turbulence = case.get("turbulence_model", "laminar")
    params = case.get("parameters", {})
    gold_quantity = (case.get("gold_standard") or {}).get("quantity", "unknown")

    lines = [
        f"# {name} — reference bundle",
        "",
        f"Case ID: `{case_id}`",
        "",
        "This zip is a **reference bundle**, not a runnable OpenFOAM case.",
        "",
        "## What's inside",
        "",
        "- `gold_standard.yaml` — the canonical validation contract",
        "  (observable, tolerance, preconditions) used by the live harness.",
        "  Byte-identical to `knowledge/gold_standards/" + case_id + ".yaml`.",
        "- `validation_contract.md` — plain-text summary of the contract",
        "  (quantity, anchor value, tolerance band, why each precondition",
        "  matters).",
        "- `README.md` — this file.",
        "",
        "## Case parameters",
        "",
        f"- Reference: {reference}",
    ]
    if doi:
        lines.append(f"- DOI: [{doi}](https://doi.org/{doi})")
    lines.extend(
        [
            f"- Flow type: {flow_type}",
            f"- Geometry: {geometry}",
            f"- Solver: `{solver}` + turbulence model `{turbulence}`",
            f"- Primary observable: `{gold_quantity}`",
        ]
    )
    if params:
        lines.append("")
        lines.append("### Parameters")
        lines.append("")
        for k, v in params.items():
            lines.append(f"- `{k}` = {v}")

    lines.extend(
        [
            "",
            "## How to reproduce locally",
            "",
            "1. Install OpenFOAM (v11 or v2412 both work for these cases).",
            "2. Copy an analogous tutorial from `$FOAM_TUTORIALS` as your",
            "   starting point — e.g. `incompressible/simpleFoam/` for most",
            "   steady internal flows.",
            "3. Adjust `system/blockMeshDict`, `0/` boundary conditions, and",
            "   physical properties to match the parameters listed above.",
            "4. Post-process your solver output to extract the primary",
            f"   observable (`{gold_quantity}`), and compare against",
            "   `gold_standard.yaml`'s anchor + tolerance band.",
            "",
            "## Why not ship a runnable case dir?",
            "",
            "The validation harness owns case generators inside",
            "`src/foam_agent_adapter.py` which sit inside a governance",
            "perimeter that prevents autonomous forks. OpenFOAM's own",
            "tutorials are the canonical source; we point at those rather",
            "than drift away from them.",
            "",
            "## Upstream source of truth",
            "",
            f"- Validation harness: <https://github.com/kogamishinyajerry-ops/cfd-harness-unified>",
            f"- Live case endpoint: `/api/validation-report/{case_id}`",
            f"- Student-facing narrative: `/learn/cases/{case_id}`",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_contract_md(case_id: str, case: dict, gold: dict | None) -> str:
    """Render validation_contract.md — the student-readable contract."""
    lines = [
        f"# Validation contract — {case_id}",
        "",
        "## Anchor",
    ]
    wl_gs = case.get("gold_standard") or {}
    tol = wl_gs.get("tolerance")
    quantity = wl_gs.get("quantity", "unknown")
    lines.append("")
    lines.append(f"- Quantity: `{quantity}`")
    if tol is not None:
        lines.append(f"- Tolerance: ±{tol * 100:.1f}% (relative)")

    if gold:
        observables = gold.get("observables") or []
        for ob in observables:
            rv = ob.get("ref_value")
            if isinstance(rv, (int, float)):
                lines.append(
                    f"- Reference value: `{rv}` "
                    f"({ob.get('unit', '') or 'dimensionless'})"
                )
                break

    # Preconditions
    if gold:
        preconds = (gold.get("physics_contract") or {}).get(
            "physics_precondition"
        ) or []
        if preconds:
            lines.append("")
            lines.append("## Preconditions")
            lines.append("")
            for i, pc in enumerate(preconds, 1):
                condition = pc.get("condition", "(no condition given)")
                satisfied = pc.get("satisfied_by_current_adapter", False)
                ev = pc.get("evidence_ref", "")
                consequence = pc.get("consequence_if_unsatisfied", "")
                mark = "✓" if satisfied else "✗"
                lines.append(f"### {i}. [{mark}] {condition}")
                lines.append("")
                if ev:
                    lines.append(f"- Evidence: {ev}")
                if consequence:
                    lines.append(f"- If unsatisfied: {consequence}")
                lines.append("")

    lines.append("## Verdict rule")
    lines.append("")
    lines.append("- `PASS` — measurement within tolerance AND all preconditions satisfied.")
    lines.append("- `HAZARD` — within tolerance, but some precondition is violated OR")
    lines.append("  a silent-pass-hazard audit concern is armed.")
    lines.append("- `FAIL` — measurement outside tolerance band.")

    return "\n".join(lines) + "\n"


def build_reference_bundle(case_id: str) -> bytes:
    """Return a bytes zip archive with the case reference bundle."""
    whitelist = _load_whitelist()
    case = whitelist.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"unknown case '{case_id}'")
    gold = _load_gold_standard(case_id)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            f"{case_id}/README.md", _render_readme(case_id, case, gold)
        )
        zf.writestr(
            f"{case_id}/validation_contract.md",
            _render_contract_md(case_id, case, gold),
        )
        # Gold YAML verbatim (read-only copy — no modifications).
        gold_file = GOLD_DIR / f"{case_id}.yaml"
        if gold_file.exists():
            zf.writestr(
                f"{case_id}/gold_standard.yaml",
                gold_file.read_text(encoding="utf-8"),
            )
        else:
            # Fallback — synthesize the gold dict from in-memory data.
            zf.writestr(
                f"{case_id}/gold_standard.yaml",
                yaml.safe_dump(gold or {}, allow_unicode=True, sort_keys=False),
            )
    return buf.getvalue()


@router.get("/cases/{case_id}/export")
def export_case(case_id: str) -> Response:
    """Download a reference bundle zip for one case."""
    data = build_reference_bundle(case_id)
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{case_id}_reference.zip"'
            ),
            "Cache-Control": "no-store",
        },
    )

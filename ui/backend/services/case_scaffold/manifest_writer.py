"""Write ``case_manifest.yaml`` (M5 import manifest) and the editor-facing
``user_drafts/{case_id}.yaml`` (consumed by case_drafts / case_editor).

The manifest is the M5.0 schema-additive surface for the ``source_origin``
field. The editor YAML mirrors the same field at top level so the
existing case-editor flow can read/write/lint it without modification,
and M5.1 TrustGate hard-cap (trust-core path) can read the field from
either location.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from ui.backend.services.geometry_ingest import IngestReport

# M5.0 schema-additive marker for imported cases. The M5.1 trust-core
# hard-cap path (TrustGate verdict cap on imported cases) reads this
# field from the manifest + editor YAML to gate the verdict.
SOURCE_ORIGIN_IMPORTED_USER = "imported_user"


def _ingest_summary(report: IngestReport) -> dict:
    """Subset of the ingest report safe to embed in YAML / show in UI."""
    return {
        "is_watertight": report.is_watertight,
        "bbox_min": list(report.bbox_min),
        "bbox_max": list(report.bbox_max),
        "bbox_extent": list(report.bbox_extent),
        "unit_guess": report.unit_guess,
        "solid_count": report.solid_count,
        "face_count": report.face_count,
        "is_single_shell": report.is_single_shell,
        "patches": [{"name": p.name, "face_count": p.face_count} for p in report.patches],
        "all_default_faces": report.all_default_faces,
        "warnings": list(report.warnings),
    }


def write_case_manifest(
    *,
    case_dir: Path,
    case_id: str,
    origin_filename: str,
    report: IngestReport,
    now: datetime | None = None,
) -> Path:
    """Write ``case_manifest.yaml`` inside the imported-case directory."""
    when = (now or datetime.now(timezone.utc)).isoformat()
    manifest = {
        "source": "imported",
        "source_origin": SOURCE_ORIGIN_IMPORTED_USER,
        "case_id": case_id,
        "origin_filename": origin_filename,
        "ingest_report_summary": _ingest_summary(report),
        "created_at": when,
        "solver_version_compat": "openfoam-v2412",  # default LDC compatibility band
    }
    out = case_dir / "case_manifest.yaml"
    out.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return out


def _editor_case_yaml(
    *,
    case_id: str,
    origin_filename: str,
    imported_case_dir: Path,
    report: IngestReport,
) -> dict:
    """Construct the editor-facing case YAML (workbench_basics-shaped).

    Borrows LDC default solver + materials so the user starts from a
    sensible incompressible-laminar baseline they can edit in
    ``EditCasePage``. The actual OpenFOAM case generation happens at
    M7 run-time, not here.
    """
    # Try to express imported_case_dir relative to repo root for portability.
    try:
        from ui.backend.services.validation_report import REPO_ROOT

        rel_imported = imported_case_dir.relative_to(REPO_ROOT).as_posix()
    except Exception:  # noqa: BLE001
        rel_imported = imported_case_dir.as_posix()

    return {
        "id": case_id,
        "name": f"Imported · {origin_filename}",
        "flow_type": "imported_unspecified",
        "geometry_type": "imported_stl",
        "turbulence_model": "laminar",
        "source": "imported",
        "source_origin": SOURCE_ORIGIN_IMPORTED_USER,  # M5.0 schema-additive field
        "origin_filename": origin_filename,
        "imported_case_dir": rel_imported,
        "ingest_report_summary": _ingest_summary(report),
        "solver": {
            "name": "simpleFoam",
            "family": "incompressible",
            "steady_state": True,
            "laminar": True,
            "note": "LDC default · user can edit before running",
        },
        "materials": [
            {
                "id": "imported_fluid",
                "label_en": "Imported case fluid (LDC default)",
                "properties": [
                    {
                        "symbol": "ν",
                        "name": "kinematic_viscosity",
                        "value": 1.0e-3,
                        "unit": "m^2/s",
                        "note": "LDC default; override for your geometry",
                    },
                    {
                        "symbol": "ρ",
                        "name": "density",
                        "value": 1.0,
                        "unit": "kg/m^3",
                        "note": "incompressible — ρ does not enter the equations",
                    },
                ],
            }
        ],
    }


def write_editor_case_yaml(
    *,
    drafts_dir: Path,
    case_id: str,
    origin_filename: str,
    imported_case_dir: Path,
    report: IngestReport,
) -> Path:
    """Write the editor-facing YAML at ``drafts_dir/{case_id}.yaml``."""
    drafts_dir.mkdir(parents=True, exist_ok=True)
    out = drafts_dir / f"{case_id}.yaml"
    payload = _editor_case_yaml(
        case_id=case_id,
        origin_filename=origin_filename,
        imported_case_dir=imported_case_dir,
        report=report,
    )
    out.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return out

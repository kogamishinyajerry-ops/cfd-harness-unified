"""DEC-V61-152 (N5.1) · beginner report builder.

Walks case state from disk and assembles a :class:`BeginnerReport`.
Every section is best-effort: if the corresponding case state is
missing (engineer hasn't reached that step yet), the section's
fields stay None and the verdict picks `<step>_setup_incomplete`.

V130 / V132: read-only walk. No disk write. No AI generation.
Verdict emitted by `derive_verdict()` rule function.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from ui.backend.schemas.beginner_report import (
    BeginnerReport,
    GeometrySection,
    MeshSection,
    PhysicsSection,
    SolverSection,
)
from ui.backend.services.case_report.verdict_rules import derive_verdict


def build_beginner_report(case_dir: Path) -> BeginnerReport:
    """Build a snapshot report of the case at ``case_dir``."""
    geometry = _build_geometry(case_dir)
    mesh = _build_mesh(case_dir)
    physics = _build_physics(case_dir)
    solver = _build_solver(physics, case_dir)
    verdict = derive_verdict(
        geometry=geometry, mesh=mesh, physics=physics, solver=solver,
    )
    return BeginnerReport(
        case_id=case_dir.name,
        geometry=geometry,
        mesh=mesh,
        physics=physics,
        solver=solver,
        verdict=verdict,
        generated_at=datetime.now(tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    )


# ────────── Geometry ──────────


def _build_geometry(case_dir: Path) -> GeometrySection:
    """Walk Step 1 artifacts: imported STL filename + boundary patches."""
    section = GeometrySection()

    # STL filename — heuristic: imported case directory name carries
    # the original STL name in the manifest if present, else look for
    # any *.stl in constant/triSurface/.
    stl_dir = case_dir / "constant" / "triSurface"
    if stl_dir.is_dir():
        stl_files = sorted(stl_dir.glob("*.stl"))
        if stl_files:
            section = section.model_copy(
                update={"stl_filename": stl_files[0].name}
            )

    # Bounding box — walk polyMesh/points if available; otherwise
    # leave None (Step 2 hasn't run yet).
    points_path = case_dir / "constant" / "polyMesh" / "points"
    if points_path.is_file():
        bb_min, bb_max = _read_points_bbox(points_path)
        if bb_min is not None:
            volume = (
                (bb_max[0] - bb_min[0])
                * (bb_max[1] - bb_min[1])
                * (bb_max[2] - bb_min[2])
            )
            section = section.model_copy(
                update={
                    "bounding_box_min": bb_min,
                    "bounding_box_max": bb_max,
                    "bounding_box_volume": round(max(volume, 0.0), 6),
                }
            )

    # Named patches from polyMesh/boundary.
    boundary_path = case_dir / "constant" / "polyMesh" / "boundary"
    if boundary_path.is_file():
        names = _read_patch_names(boundary_path)
        section = section.model_copy(update={"named_patches": names})

    return section


def _read_points_bbox(
    path: Path,
) -> tuple[
    tuple[float, float, float] | None,
    tuple[float, float, float] | None,
]:
    """Best-effort bbox from polyMesh/points (ASCII format)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None
    pts: list[tuple[float, float, float]] = []
    for m in re.finditer(
        r"\(([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\)", text,
    ):
        try:
            pts.append(
                (float(m.group(1)), float(m.group(2)), float(m.group(3)))
            )
        except ValueError:
            continue
    if not pts:
        return None, None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _read_patch_names(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    pattern = re.compile(
        r"(\w+)\s*\{[^}]*nFaces\s+\d+[^}]*startFace\s+\d+[^}]*\}", re.DOTALL,
    )
    out: list[str] = []
    for m in pattern.finditer(text):
        name = m.group(1)
        if name == "FoamFile":
            continue
        out.append(name)
    return out


# ────────── Mesh ──────────


def _build_mesh(case_dir: Path) -> MeshSection:
    """Walk Step 2 artifacts. Reuses the V122 mesh-quality analyzer
    when polyMesh is present; falls back to bare cell-count read
    otherwise."""
    section = MeshSection()
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        return section
    try:
        from ui.backend.services.mesh_quality.analyzer import (
            MeshQualityNotAvailableError,
            MeshQualityParseError,
            analyze_mesh_quality,
        )

        report = analyze_mesh_quality(case_dir, run_checkmesh=False)
        section = section.model_copy(
            update={
                "cell_count": report.cell_count,
                "point_count": report.point_count,
                "internal_face_count": report.internal_face_count,
                "boundary_face_count": report.boundary_face_count,
                "cells_per_unit_volume": report.cells_per_unit_volume,
            }
        )
    except (
        MeshQualityNotAvailableError,
        MeshQualityParseError,
    ):
        # Mesh not yet generated or corrupt — leave section empty.
        return section
    except Exception:
        # Defensive: any other unexpected failure is logged at the
        # caller layer; report builder must not crash.
        return section
    return section


# ────────── Physics ──────────


def _build_physics(case_dir: Path) -> PhysicsSection:
    """Walk Step 3 artifacts: constant/physicalProperties +
    constant/momentumTransport. Reads back the structured contracts
    via simple regex parse — N3.3 writer's output is byte-stable, so
    parsing it is reliable."""
    section = PhysicsSection()

    # Physical properties — nu + (optionally) rho/Cp/kappa/Pr.
    phys_path = case_dir / "constant" / "physicalProperties"
    if phys_path.is_file():
        text = _safe_read(phys_path)
        nu = _parse_dim_value(text, "nu")
        rho = _parse_dim_value(text, "rho")
        cp = _parse_dim_value(text, "Cp")
        pr = _parse_dim_value(text, "Pr")
        # Fluid name doesn't appear in OpenFOAM dict — fall back to
        # generic "fluid" placeholder so the report shows that physics
        # WAS committed, even if name metadata isn't recoverable.
        if nu is not None:
            update: dict = {
                "fluid_name": "fluid",
                "kinematic_viscosity": nu,
            }
            if rho is not None:
                update["density"] = rho
            if pr is not None:
                update["prandtl"] = pr
            if cp is not None:
                update["has_thermal"] = True
            section = section.model_copy(update=update)

    # Momentum transport — simulationType literal.
    momentum_path = case_dir / "constant" / "momentumTransport"
    if momentum_path.is_file():
        text = _safe_read(momentum_path)
        # Map OpenFOAM simulationType → RegimeKind literal.
        sim_match = re.search(r"simulationType\s+(\w+)", text)
        ras_model_match = re.search(r"RASModel\s+(\w+)", text)
        regime: str | None = None
        if sim_match is not None:
            sim = sim_match.group(1)
            if sim == "laminar":
                regime = "laminar"
            elif sim == "RAS" and ras_model_match is not None:
                ras = ras_model_match.group(1)
                if ras == "kEpsilon":
                    regime = "RANS-RAS"
                elif ras == "kOmegaSST":
                    regime = "RANS-kOmegaSST"
                else:
                    regime = "RANS-RAS"  # fallback for unknown RAS sub-models
            elif sim == "LES":
                regime = "LES-stub"
        if regime is not None:
            section = section.model_copy(update={"regime": regime})

    return section


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _parse_dim_value(text: str, key: str) -> float | None:
    """Parse `<key> [dims] <value>;` OpenFOAM dict line. Returns
    None when the key is absent or the line is malformed."""
    pattern = re.compile(
        rf"\b{re.escape(key)}\s+\[[^\]]*\]\s+([-0-9.eE+]+)\s*;"
    )
    m = pattern.search(text)
    if m is None:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


# ────────── Solver ──────────


def _build_solver(physics: PhysicsSection, case_dir: Path) -> SolverSection:
    """Derive solver from regime + has_thermal via N3.4 derivation
    table. When regime is None (physics not yet committed), returns
    empty section."""
    section = SolverSection()
    if physics.regime is None:
        return section

    try:
        from ui.backend.schemas.material_contract import (
            FluidProperties,
            MaterialContract,
            ThermalProperties,
        )
        from ui.backend.schemas.regime_contract import (
            ApplicabilityBounds,
            RegimeContract,
        )
        from ui.backend.services.physics import (
            derive_solver,
            derive_tolerance_for_regime,
        )

        # Build a synthetic contract pair just for the derivation
        # (the derivation reads only `regime` + `material.thermal`).
        material = MaterialContract(
            kind="custom",
            fluid=FluidProperties(
                name=physics.fluid_name or "fluid",
                density=physics.density or 1000.0,
                kinematic_viscosity=physics.kinematic_viscosity or 1.0e-6,
                prandtl=physics.prandtl,
            ),
            thermal=(
                ThermalProperties(
                    specific_heat=1000.0,
                    thermal_conductivity=1.0,
                )
                if physics.has_thermal
                else None
            ),
            authored_at="1970-01-01T00:00:00Z",  # synthetic; not used downstream
        )
        regime_contract = RegimeContract(
            kind="custom",
            regime=physics.regime,  # type: ignore[arg-type]
            applicability=ApplicabilityBounds(),
            authored_at="1970-01-01T00:00:00Z",
        )
        derivation = derive_solver(regime_contract, material)
        tol = derive_tolerance_for_regime(physics.regime)  # type: ignore[arg-type]
        section = section.model_copy(
            update={
                "derived_solver": derivation.solver,
                "derivation_rationale": derivation.rationale,
                "tolerance_tier": tol.tier,
            }
        )
    except (KeyError, ImportError, ValueError):
        # Defensive: regime literal didn't resolve. Leave empty —
        # verdict picks 'has_open_issues'.
        pass

    return section

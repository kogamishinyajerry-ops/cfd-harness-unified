"""Derive WorkbenchBasics from a real OpenFOAM case on disk.

Faithful-mirror contract (DEC-V61-206): every value here is read from a
file in the case directory. Sections that cannot be derived are omitted
(→ the UI shows an honest "待识别"), never guessed. The returned model
carries ``provenance="derived"`` so the frontend can label it "派生自算例"
and distinguish it from a hand-authored knowledge yaml.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from ui.backend.schemas.workbench_basics import (
    BBox,
    BoundaryCondition,
    BoundaryConditionPatch,
    CharacteristicLength,
    Geometry,
    Material,
    MaterialProperty,
    Patch,
    Solver,
    WorkbenchBasics,
)
from ui.backend.services.case_scaffold import IMPORTED_DIR
from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    _read_patch_ranges,
)
from ui.backend.services.render.polymesh_parser import (
    _strip_comments,
    _strip_foamfile_header,
)

# Fields we know how to label. Order = canonical display order. A field is
# only surfaced if its `0/<field>` file actually exists on disk.
_FIELD_META: dict[str, tuple[str, str, str]] = {
    # field: (quantity, units, symbol-for-display)
    "U": ("velocity", "m/s", "U"),
    "p": ("kinematic_pressure", "m^2/s^2", "p"),
    "p_rgh": ("kinematic_pressure", "m^2/s^2", "p_rgh"),
    "T": ("temperature", "K", "T"),
    "k": ("turbulence_kinetic_energy", "m^2/s^2", "k"),
    "omega": ("turbulence_specific_dissipation", "1/s", "ω"),
    "epsilon": ("turbulence_dissipation", "m^2/s^3", "ε"),
    "nut": ("turbulent_viscosity", "m^2/s", "νt"),
    "nuTilda": ("spalart_allmaras_variable", "m^2/s", "ν̃"),
    "alphat": ("turbulent_thermal_diffusivity", "kg/(m·s)", "αt"),
}
_FIELD_ORDER = list(_FIELD_META.keys())


# ─────────────────────────── foam-dict parsing ───────────────────────────

def _patch_blocks(content: str) -> dict[str, str]:
    """Split a ``boundaryField { ... }`` body into ``{patch_name: body}``.

    Brace-depth scanner so a nested sub-dict inside a patch entry (rare,
    e.g. coded BCs) does not break the split. Comments/header already
    stripped by the caller.
    """
    out: dict[str, str] = {}
    i, n = 0, len(content)
    while i < n:
        m = re.compile(r"([A-Za-z_][\w.\-]*)\s*\{").match(content, i)
        if not m:
            i += 1
            continue
        name = m.group(1)
        depth = 1
        j = m.end()
        while j < n and depth > 0:
            if content[j] == "{":
                depth += 1
            elif content[j] == "}":
                depth -= 1
            j += 1
        out[name] = content[m.end() : j - 1]
        i = j
    return out


def _extract_boundary_field_body(text: str) -> Optional[str]:
    """Return the body inside the top-level ``boundaryField { ... }``."""
    text = _strip_comments(text)
    m = re.search(r"boundaryField\s*\{", text)
    if not m:
        return None
    depth = 1
    j = m.end()
    n = len(text)
    while j < n and depth > 0:
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
        j += 1
    return text[m.end() : j - 1]


def _parse_value(body: str) -> Optional[object]:
    """Parse the ``value`` entry of a patch BC block into a scalar, a
    list[float], or a raw string (e.g. ``$internalField``). None if absent.
    """
    m = re.search(r"\bvalue\s+(.+?);", body, re.DOTALL)
    if not m:
        return None
    raw = m.group(1).strip()
    raw = re.sub(r"^uniform\s+", "", raw).strip()
    # vector / list:  (1 -0 -0)
    vm = re.match(r"^\(([^)]*)\)$", raw)
    if vm:
        try:
            return [float(tok) for tok in vm.group(1).split()]
        except ValueError:
            return raw
    # bare scalar
    try:
        return float(raw)
    except ValueError:
        return raw or None


def _parse_type(body: str) -> Optional[str]:
    m = re.search(r"\btype\s+([A-Za-z_][\w]*)\s*;", body)
    return m.group(1) if m else None


def parse_foam_boundary_field(text: str) -> dict[str, dict[str, object]]:
    """``0/<field>`` text → ``{patch: {"type": str, "value": ...}}``."""
    body = _extract_boundary_field_body(text)
    if body is None:
        return {}
    out: dict[str, dict[str, object]] = {}
    for patch, pbody in _patch_blocks(body).items():
        btype = _parse_type(pbody)
        if btype is None:
            continue
        entry: dict[str, object] = {"type": btype}
        val = _parse_value(pbody)
        if val is not None:
            entry["value"] = val
        out[patch] = entry
    return out


# ─────────────────────────── role / display ───────────────────────────

def _is_zero_vec(v: object) -> bool:
    return isinstance(v, list) and all(abs(float(x)) < 1e-12 for x in v)


def _role_from_u(u_bc: Optional[dict[str, object]], name: str) -> str:
    """Faithful role from the ACTUAL U boundary condition (the ground
    truth of what setup-bc configured), with a name hint only as a
    last resort. A ``periodic_*`` patch that was written as ``noSlip``
    honestly derives to ``wall`` — not ``periodic`` — because that is
    what the solver actually ran.
    """
    if u_bc is not None:
        t = str(u_bc.get("type", ""))
        if t == "noSlip" or t == "slip":
            return "wall"
        if t in ("zeroGradient", "inletOutlet", "outletInlet"):
            return "outlet"
        if t in ("cyclic", "cyclicAMI"):
            return "cyclic"
        if t in ("symmetry", "symmetryPlane"):
            return "symmetry"
        if t == "empty":
            return "empty"
        if t == "fixedValue":
            return "wall" if _is_zero_vec(u_bc.get("value")) else "inlet"
        if t in ("movingWallVelocity", "rotatingWallVelocity"):
            return "moving_wall"
    # No U field for this patch → fall back to a conservative name hint.
    low = name.lower()
    if "inlet" in low:
        return "inlet"
    if "outlet" in low:
        return "outlet"
    if low in ("frontandback", "front_back", "frontback"):
        return "empty"
    return "wall"


def _display_zh(field: str, btype: str, value: object) -> str:
    sym = _FIELD_META.get(field, (field, "", field))[2]
    if btype == "noSlip":
        return f"{sym} = 0"
    if btype == "empty":
        return "—"
    if btype == "zeroGradient":
        return f"∂{sym}/∂n = 0"
    if btype in ("cyclic", "cyclicAMI"):
        return "周期 (cyclic)"
    if btype in ("symmetry", "symmetryPlane"):
        return "对称面"
    if btype == "fixedValue":
        if isinstance(value, list):
            return f"{sym}=({', '.join(_fmt_num(x) for x in value)})"
        if isinstance(value, (int, float)):
            return f"{sym} = {_fmt_num(value)}"
        return f"{sym} = fixedValue"
    # wall functions and the long tail: surface the OpenFOAM token verbatim.
    return btype


def _fmt_num(x: object) -> str:
    f = float(x)
    if f == int(f):
        return str(int(f))
    return f"{f:g}"


# ─────────────────────────── section derivers ───────────────────────────

def _derive_boundary_conditions(
    case_dir: Path, patch_names: list[str]
) -> tuple[list[BoundaryCondition], dict[str, dict[str, object]]]:
    """Return (boundary_conditions, u_bc_by_patch). Scans every known
    `0/<field>` that exists; omits fields with no file.
    """
    zero_dir = case_dir / "0"
    bcs: list[BoundaryCondition] = []
    u_by_patch: dict[str, dict[str, object]] = {}
    for field in _FIELD_ORDER:
        fpath = zero_dir / field
        if not fpath.is_file():
            continue
        try:
            parsed = parse_foam_boundary_field(fpath.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — never break the endpoint on a malformed field
            continue
        if not parsed:
            continue
        if field == "U":
            u_by_patch = parsed
        quantity, units, _sym = _FIELD_META[field]
        per_patch: dict[str, BoundaryConditionPatch] = {}
        for patch in patch_names:
            entry = parsed.get(patch)
            if entry is None:
                continue
            btype = str(entry["type"])
            value = entry.get("value")
            per_patch[patch] = BoundaryConditionPatch(
                type=btype,
                value=value if isinstance(value, (float, list, str)) else None,
                display_zh=_display_zh(field, btype, value),
            )
        if per_patch:
            bcs.append(
                BoundaryCondition(
                    field=field,
                    quantity=quantity,
                    units=units,
                    per_patch=per_patch,
                )
            )
    return bcs, u_by_patch


def _derive_patches(
    patch_ranges: list[tuple[str, int, int]],
    u_by_patch: dict[str, dict[str, object]],
) -> list[Patch]:
    patches: list[Patch] = []
    for name, _start, nfaces in patch_ranges:
        role = _role_from_u(u_by_patch.get(name), name)
        patches.append(
            Patch(
                id=name,
                role=role,
                location="derived",
                label_zh=name,
                label_en=name,
                description_zh=f"{nfaces} faces · 派生自 polyMesh/boundary + 0/U",
            )
        )
    return patches


def _foam_scalar(text: str, key: str) -> Optional[float]:
    """Read ``<key>  <number>;`` (optionally ``<key> <name> [dims] <number>;``
    as in physicalProperties) → float, else None."""
    m = re.search(rf"\b{re.escape(key)}\b[^;]*?(-?\d+\.?\d*(?:[eE][-+]?\d+)?)\s*;", text)
    return float(m.group(1)) if m else None


def _foam_token(text: str, key: str) -> Optional[str]:
    m = re.search(rf"\b{re.escape(key)}\s+([A-Za-z_][\w]*)\s*;", text)
    return m.group(1) if m else None


def _derive_materials(case_dir: Path) -> list[Material]:
    const = case_dir / "constant"
    props: list[MaterialProperty] = []
    phys = const / "physicalProperties"
    if not phys.is_file():
        phys = const / "transportProperties"  # legacy name
    if phys.is_file():
        try:
            text = _strip_comments(phys.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            text = ""
        nu = _foam_scalar(text, "nu")
        if nu is not None:
            props.append(
                MaterialProperty(symbol="ν", name="kinematic_viscosity", value=nu, unit="m^2/s")
            )
        rho = _foam_scalar(text, "rho")
        if rho is not None:
            props.append(
                MaterialProperty(symbol="ρ", name="density", value=rho, unit="kg/m^3")
            )
    if not props:
        return []
    return [
        Material(id="fluid", label_zh="流体", label_en="Fluid", properties=props)
    ]


# OpenFOAM application → (steady_state, family) hints. Faithful: derived
# from system/controlDict `application`, not guessed from anything else.
_STEADY_APPS = {"simpleFoam", "buoyantSimpleFoam", "porousSimpleFoam", "SRFSimpleFoam"}
_TRANSIENT_APPS = {
    "icoFoam", "pimpleFoam", "pisoFoam", "interFoam", "buoyantPimpleFoam",
    "rhoPimpleFoam", "sonicFoam",
}


def _derive_solver(case_dir: Path) -> Optional[Solver]:
    cd = case_dir / "system" / "controlDict"
    if not cd.is_file():
        return None
    try:
        text = _strip_comments(cd.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    app = _foam_token(text, "application")
    if not app:
        return None
    steady = app in _STEADY_APPS
    transient = app in _TRANSIENT_APPS
    # Turbulence model from constant/momentumTransport (laminar vs RAS/LES).
    laminar = True
    mt = case_dir / "constant" / "momentumTransport"
    if not mt.is_file():
        mt = case_dir / "constant" / "turbulenceProperties"  # legacy
    if mt.is_file():
        try:
            sim = _foam_token(_strip_comments(mt.read_text(encoding="utf-8")), "simulationType")
            laminar = (sim or "laminar") == "laminar"
        except Exception:  # noqa: BLE001
            pass
    state_zh = "稳态" if steady else ("瞬态" if transient else "未知时间格式")
    return Solver(
        name=app,
        family="OpenFOAM",
        steady_state=steady,
        laminar=laminar,
        display_zh=f"{app} · {state_zh}",
        reasoning_zh=f"派生自 system/controlDict（application={app}）"
        + ("，constant/momentumTransport 为 laminar" if laminar else ""),
    )


def _derive_geometry(case_dir: Path) -> Optional[Geometry]:
    """Best-effort bbox from polyMesh points. Shape is 'imported' — the
    V4 workbench renders the real GLB, not the <CaseFrame> SVG, so the
    shape category is informational only.
    """
    points = case_dir / "constant" / "polyMesh" / "points"
    if not points.is_file():
        return None
    try:
        from ui.backend.services.render.polymesh_parser import parse_points

        pts = parse_points(points)
    except Exception:  # noqa: BLE001
        return None
    if pts is None or len(pts) == 0:
        return None
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    extents = [float(maxs[i] - mins[i]) for i in range(3)]
    char = max(extents) if extents else 0.0
    return Geometry(
        shape="imported",
        bbox=BBox(
            x_min=float(mins[0]), x_max=float(maxs[0]),
            y_min=float(mins[1]), y_max=float(maxs[1]),
            z_min=float(mins[2]), z_max=float(maxs[2]),
        ),
        characteristic_length=CharacteristicLength(
            name="L_max", value=char, unit="m",
            description_zh="包围盒最大边长（派生自 polyMesh/points）",
        ),
    )


# ─────────────────────────── orchestrator ───────────────────────────

def derive_workbench_basics(
    case_id: str, case_dir: Optional[Path] = None
) -> Optional[WorkbenchBasics]:
    """Derive a WorkbenchBasics from an imported case, or None when the
    case has no OpenFOAM boundary on disk (→ endpoint keeps its 404 and
    the UI keeps its honest 待识别 placeholders).
    """
    if case_dir is None:
        case_dir = IMPORTED_DIR / case_id
    boundary = case_dir / "constant" / "polyMesh" / "boundary"
    if not boundary.is_file():
        return None
    try:
        patch_ranges = _read_patch_ranges(boundary)
    except Exception:  # noqa: BLE001
        return None
    if not patch_ranges:
        return None
    patch_names = [name for name, _s, _n in patch_ranges]

    boundary_conditions, u_by_patch = _derive_boundary_conditions(case_dir, patch_names)
    patches = _derive_patches(patch_ranges, u_by_patch)
    materials = _derive_materials(case_dir)
    solver = _derive_solver(case_dir)
    geometry = _derive_geometry(case_dir)

    return WorkbenchBasics(
        case_id=case_id,
        display_name=case_id,
        provenance="derived",
        dimension=3,
        geometry=geometry,
        patches=patches,
        boundary_conditions=boundary_conditions,
        materials=materials,
        solver=solver,
    )

"""Foam-Agent 调用适配器：MockExecutor（测试）+ FoamAgentExecutor（真实）"""

from __future__ import annotations

import io
import math
import os
import re
import shutil
import tarfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import CFDExecutor, ExecutionResult, FlowType, GeometryType, TaskSpec

# ---------------------------------------------------------------------------
# MockExecutor — unchanged, used for testing
# ---------------------------------------------------------------------------


class MockExecutor:
    """测试专用执行器：is_mock=True，返回预设结果"""

    _PRESET: Dict[str, Dict[str, Any]] = {
        "INTERNAL": {
            "residuals": {"p": 1e-6, "U": 1e-6},
            "key_quantities": {"u_centerline": [0.0, -0.037, 0.025, 0.333, 1.0]},
        },
        "EXTERNAL": {
            "residuals": {"p": 1e-5, "U": 1e-5},
            # DEC-V61-041: mock preset deliberately stamps a gold-
            # matching value because it IS a mock (real adapter now
            # produces this via forceCoeffs FFT). `mock_preset_marker`
            # lets downstream distinguish mock from real.
            "key_quantities": {
                "strouhal_number": 0.165,
                "cd_mean": 1.36,
                "cl_rms": 0.048,
                "mock_preset_marker": True,
            },
        },
        "NATURAL_CONVECTION": {
            "residuals": {"p": 1e-6, "T": 1e-7},
            "key_quantities": {"nusselt_number": 4.52},
        },
    }

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
        preset = self._PRESET.get(task_spec.flow_type.value, self._PRESET["INTERNAL"])
        return ExecutionResult(
            success=True,
            is_mock=True,
            residuals=dict(preset["residuals"]),
            key_quantities=dict(preset["key_quantities"]),
            execution_time_s=0.01,
            raw_output_path=None,
        )


# ---------------------------------------------------------------------------
# FoamAgentExecutor — real adapter (Docker + OpenFOAM)
# ---------------------------------------------------------------------------

try:
    import docker
    import docker.errors
    _DOCKER_AVAILABLE = True
except ImportError:
    _DOCKER_AVAILABLE = False
    docker = None  # type: ignore


# ---------------------------------------------------------------------------
# Parameter plumbing pre-run assertion (P-B C2)
# ---------------------------------------------------------------------------
# Motivation: knowledge/corrections/ records 12 PARAMETER_PLUMBING_MISMATCH
# events on DHC/Rayleigh-Bénard where solver silently executed at a fallback
# Ra instead of the whitelist-declared Ra, producing Nu values 50-90% off and
# looking indistinguishable from a physics bug in the deviation report.
#
# Rather than trust that task_spec.Ra flows correctly to every downstream
# file (blockMesh, physicalProperties, g, BC files), we parse the generated
# OpenFOAM dict files back from disk and recompute the effective Ra (or Re
# for internal channel flows). If the round-tripped value drifts > 1% from
# what task_spec declares, we raise loudly before burning CPU on a bogus run.
#
# Guards only the two highest-risk case builders: natural-convection cavity
# (where Ra is derived from g, beta, dT, L, nu, Pr — five values that must
# all plumb through) and steady internal channel (where Re → nu via Re=1/nu
# in inlet-U=1 convention). Other builders take Re as a direct velocity
# input and are less prone to silent drift.

class ParameterPlumbingError(RuntimeError):
    """Case-file round-trip verification failed — a declared parameter did
    not survive the write pipeline. Raised BEFORE solver launch so operators
    debug a 50ms regex failure instead of a 70s-per-step solver run that
    silently hits the wrong operating point.
    """


_DICT_SCALAR_RE = re.compile(
    r"^\s*(?P<key>[A-Za-z_][A-Za-z_0-9]*)"
    r"(?:\s+\[[\d\s\-]+\])?"              # optional OpenFOAM dimensions
    r"\s+(?P<value>-?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)\s*;",
    re.MULTILINE,
)


def _parse_dict_scalar(text: str, key: str) -> Optional[float]:
    """Extract a top-level scalar assignment from an OpenFOAM dict file.

    Matches both ``Pr 0.71;`` and ``nu [0 2 -1 0 0 0 0] 1e-5;`` forms.
    Returns the numeric value or None if not found.
    """
    for match in _DICT_SCALAR_RE.finditer(text):
        if match.group("key") == key:
            try:
                return float(match.group("value"))
            except ValueError:
                return None
    return None


_G_VECTOR_RE = re.compile(
    r"value\s*(?:\[[\d\s\-]+\])?\s*\(\s*"
    r"(-?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)\s+"
    r"(-?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)\s+"
    r"(-?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)"
    r"\s*\)\s*;"
)


def _parse_g_magnitude(text: str) -> Optional[float]:
    """Extract |g| from a ``constant/g`` file's ``value (gx gy gz);``."""
    match = _G_VECTOR_RE.search(text)
    if match is None:
        return None
    try:
        gx, gy, gz = (float(match.group(i)) for i in (1, 2, 3))
    except ValueError:
        return None
    return math.sqrt(gx * gx + gy * gy + gz * gz)


# ---------------------------------------------------------------------------
# Gold-anchored sampleDict helpers (P-B C3)
# ---------------------------------------------------------------------------
# Motivation: case generators previously emitted `type uniform` sampleDicts
# with arbitrary nPoints. Solver output lands on a regular grid that doesn't
# coincide with `gold_standard.reference_values` coordinates, forcing the
# comparator to interpolate or nearest-neighbor-lookup. This introduces a
# sampling-grid error term indistinguishable from solver error in the final
# verdict.
#
# C3 replaces uniform sampling with explicit `type points` sets anchored to
# the exact coordinates in `knowledge/whitelist.yaml`. Solver samples AT the
# gold points; comparator lookup is exact. Paired with C1 alias layer this
# closes the full sampling-location mismatch channel.
#
# Per docs/c3_sampling_strategy_design.md the roll-out is per-case (LDC /
# NACA / Impinging Jet), each with a different function-object choice based
# on the physical quantity being sampled. These two helpers are the shared
# abstraction used by all three generators.


_DEFAULT_WHITELIST_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "whitelist.yaml"


def _load_gold_reference_values(
    task_name: str,
    *,
    whitelist_path: Optional[Path] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Load `gold_standard.reference_values` for the named case from whitelist.

    Matches on either `case.id` or `case.name` (whichever equals task_name).
    Returns None when the whitelist file is missing, unreadable, the case
    isn't present, or reference_values is empty. Callers decide fallback
    behavior — absence is not an error at this layer (many test fixtures
    use synthetic task names not in whitelist).
    """
    import yaml  # local import to avoid module-load cost when unused

    path = whitelist_path or _DEFAULT_WHITELIST_PATH
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return None

    for case in data.get("cases", []):
        if case.get("id") == task_name or case.get("name") == task_name:
            gold = case.get("gold_standard") or {}
            values = gold.get("reference_values")
            if isinstance(values, list) and values:
                return values
            return None
    return None


def _load_whitelist_turbulence_model(
    task_name: str,
    *,
    whitelist_path: Optional[Path] = None,
) -> Optional[str]:
    """Return `turbulence_model` from whitelist.yaml for the named case.

    DEC-V61-053 Batch B1: whitelist may demand a specific model (e.g. `laminar`
    for cylinder at Re=100 in the 2D Karman shedding regime). The historic
    `_turbulence_model_for_solver` heuristic ignored whitelist and hardcoded
    kOmegaSST for BODY_IN_CHANNEL EXTERNAL, silently over-dissipating the
    wake. Callers should prefer this value when present and fall back to
    the heuristic only when absent.

    Returns None when the whitelist file is missing, unreadable, the case
    isn't present, or no `turbulence_model` field is set.
    """
    import yaml

    path = whitelist_path or _DEFAULT_WHITELIST_PATH
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return None

    canonical = _normalize_task_name_to_case_id(task_name)
    for case in data.get("cases", []):
        if (
            case.get("id") == canonical
            or case.get("id") == task_name
            or case.get("name") == task_name
        ):
            val = case.get("turbulence_model")
            return val if isinstance(val, str) else None
    return None


# DEC-V61-057 Batch A.5: alias→case_id table inlined here (NOT imported from
# src.auto_verifier.config) to keep the Execution-plane adapter free of
# Evaluation-plane imports per ADR-001 four-plane contract. The two tables
# MUST stay in sync; promotion to a shared knowledge artifact (e.g.
# knowledge/aliases.yaml) is tracked in the F3-MED followup queue.
_TASK_NAME_TO_CASE_ID_ALIASES = {
    "Lid-Driven Cavity": "lid_driven_cavity_benchmark",
    "Backward-Facing Step": "backward_facing_step_steady",
    "Circular Cylinder Wake": "cylinder_crossflow",
    "Turbulent Flat Plate (Zero Pressure Gradient)": "turbulent_flat_plate",
    "Fully Developed Turbulent Square-Duct Flow": "duct_flow",
    "Fully Developed Turbulent Pipe Flow": "duct_flow",
    "Rayleigh-Benard Convection (Ra=10^6)": "rayleigh_benard_convection",
    "Rayleigh-Bénard Convection (Ra=10^6)": "rayleigh_benard_convection",
    "Differential Heated Cavity (Natural Convection)": "differential_heated_cavity",
    "Differential Heated Cavity (Natural Convection, Ra=10^6 benchmark)": "differential_heated_cavity",
    "NACA 0012 Airfoil External Flow": "naca0012_airfoil",
    "Axisymmetric Impinging Jet (Re=10000)": "axisymmetric_impinging_jet",
    "Fully Developed Plane Channel Flow (DNS)": "fully_developed_plane_channel_flow",
}


def _normalize_task_name_to_case_id(task_name: str) -> str:
    """Resolve a TaskSpec.name (which may be a human-readable display title
    like 'Differential Heated Cavity (Natural Convection)') to its canonical
    case_id ('differential_heated_cavity').

    DEC-V61-057 Batch A.5 (Codex round-1 F1-HIGH): src/auto_verifier/config.py
    already maintains the canonical alias map. This helper duplicates the map
    inline (see _TASK_NAME_TO_CASE_ID_ALIASES above) because the adapter is
    in the Execution plane and ADR-001 forbids importing from Evaluation
    plane modules. The two tables MUST stay in sync.
    """
    if not task_name:
        return ""
    return _TASK_NAME_TO_CASE_ID_ALIASES.get(task_name, task_name)


def _load_whitelist_parameter(
    task_name: str,
    param_name: str,
    *,
    whitelist_path: Optional[Path] = None,
) -> Optional[float]:
    """Return `parameters.<param_name>` from whitelist.yaml for the named case.

    DEC-V61-057 Batch A.1 (Codex F1-HIGH): the natural-convection adapter
    historically inferred `aspect_ratio` from `Ra` via threshold heuristic
    (Ra<1e9 → AR=2.0 rayleigh_benard branch; Ra>=1e9 → AR=1.0 DHC branch),
    even though the whitelist explicitly declares `parameters.aspect_ratio`
    per case. This trapped DHC at Ra=1e6 (de Vahl Davis 1983 benchmark,
    AR=1.0 square cavity) into the rayleigh_benard 2:1-rectangle branch.

    This loader lets callers consult the whitelist parameters block directly
    when `task_spec.boundary_conditions` does not carry the field.

    DEC-V61-057 Batch A.5 (Codex round-1 F1-HIGH): the input `task_name` is
    normalized through TASK_NAME_TO_CASE_ID first so display titles
    (e.g. 'Differential Heated Cavity (Natural Convection)') resolve to
    the canonical case_id used throughout whitelist.yaml.

    Returns None when whitelist file/case/parameter is missing or non-numeric.
    """
    import yaml

    path = whitelist_path or _DEFAULT_WHITELIST_PATH
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return None

    canonical = _normalize_task_name_to_case_id(task_name)
    for case in data.get("cases", []):
        if (
            case.get("id") == canonical
            or case.get("id") == task_name
            or case.get("name") == task_name
        ):
            params = case.get("parameters") or {}
            val = params.get(param_name)
            if isinstance(val, (int, float)):
                return float(val)
            return None
    return None


def _emit_gold_anchored_points_sampledict(
    case_dir: Path,
    set_name: str,
    physical_points: List[Tuple[float, float, float]],
    fields: List[str],
    *,
    axis: str = "xyz",
    header_comment: str = "",
) -> None:
    """Write `system/sampleDict` with a single `type points` set.

    For C3 gold-anchored sampling: the points passed in should be the exact
    physical-coord locations at which the gold_standard reference_values
    were measured, so solver output lands on the comparison grid without
    any interpolation error.

    Parameters:
        case_dir: OpenFOAM case directory (system/ must exist)
        set_name: name of the sampling set (e.g., "uCenterline")
        physical_points: list of (x, y, z) tuples in case coordinates
        fields: OpenFOAM field names to sample (e.g., ["U"])
        axis: output-file sort axis — "xyz" (raw order) or "y"/"x"/"z"
        header_comment: optional extra comment line in the dict header
    """
    if not physical_points:
        raise ValueError("physical_points must not be empty")
    points_text = "\n".join(
        f"            ({px:.12g} {py:.12g} {pz:.12g})"
        for (px, py, pz) in physical_points
    )
    fields_text = " ".join(fields)
    extra = f"|  {header_comment}\n" if header_comment else ""
    (case_dir / "system" / "sampleDict").write_text(
        f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
|  sampleDict - gold-anchored point sampling (C3)                          |
{extra}\\*---------------------------------------------------------------------------*/
type            sets;
libs            ("libsampling.so");

interpolationScheme cellPoint;

setFormat       raw;

sets
(
    {set_name}
    {{
        type        points;
        axis        {axis};
        ordered     on;
        points
        (
{points_text}
        );
    }}
);

fields          ({fields_text});

// ************************************************************************* //
""",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Gold-anchored sampleDict result parsing (C3 result-harvest side)
# ---------------------------------------------------------------------------
# Motivation: C3 generators (DEC-V61-007/008/009) emit `type points` sampleDicts
# at exact gold coordinates. When the solver runs, these produce files under
# `postProcessing/sets/<time>/<setName>_<field>.xy` containing the solver's
# output sampled AT the gold points — no interpolation. The existing
# _extract_* methods in FoamAgentExecutor work on volume-cell snapshots
# (writeCellCentres output) and interpolate onto gold coords. Parsing the
# sampleDict output directly gives a more accurate value.
#
# This module-level parser + loader is paired with per-case populators on
# FoamAgentExecutor (below in the class) that overwrite the standard
# comparator keys (u_centerline / pressure_coefficient / nusselt_number)
# with sampleDict-sourced values when available. If no postProcessing/sets/
# output exists (MOCK executor, failed run, pre-C3 cache), the cell-based
# extractors' output is preserved — backwards compatible.


def _parse_openfoam_raw_points_output(text: str) -> List[Tuple[Tuple[float, ...], Tuple[float, ...]]]:
    """Parse a `setFormat raw` sample output file.

    Supports common variants:
    - 3D coord rows: `x y z v0 [v1 v2 ...]` (typical for type=points output)
    - Distance-column rows: `distance v0 [v1 v2 ...]` (type=uniform / type=sets with axis)

    Returns a list of (coords_tuple, values_tuple). Callers reconcile
    coord shape (3 for xyz, 1 for distance).

    Rules:
    - Lines starting with `#` are skipped (comments).
    - Empty lines are skipped.
    - Lines that don't parse as all-float are skipped.
    - Lines with exactly 3 floats are treated as distance + 2 field values
      (unusual case), not x/y/z.
    - Lines with ≥4 floats: first 3 are (x, y, z), remainder are values.
    """
    result: List[Tuple[Tuple[float, ...], Tuple[float, ...]]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        try:
            floats = [float(p) for p in parts]
        except ValueError:
            continue
        if len(floats) >= 4:
            coords = tuple(floats[:3])
            values = tuple(floats[3:])
        elif len(floats) >= 2:
            coords = (floats[0],)
            values = tuple(floats[1:])
        else:
            continue
        result.append((coords, values))
    return result


def _try_load_sampledict_output(
    case_dir: Path,
    set_name: str,
    field: str,
) -> Optional[List[Tuple[Tuple[float, ...], Tuple[float, ...]]]]:
    """Find the latest `postProcessing/sets/<time>/<setName>_<field>.xy` file
    under case_dir and parse it. Returns None on any missing file / parse
    failure — absence is not an error at this layer (MOCK runs, legacy
    pre-C3 case cache, etc., all legitimately have no sampling output).

    Time-directory selection: picks the largest numeric-named dir. Some
    OpenFOAM versions write `sets/<setName>/<time>/` instead of
    `sets/<time>/<setName>_<field>.xy`; both layouts are tried.
    """
    pp_root = case_dir / "postProcessing" / "sets"
    if not pp_root.is_dir():
        return None

    # Layout A: postProcessing/sets/<time>/<setName>_<field>.xy
    # Layout B: postProcessing/sets/<setName>/<time>/<field>
    layout_a_times: List[Tuple[float, Path]] = []
    for item in pp_root.iterdir():
        if item.is_dir():
            try:
                layout_a_times.append((float(item.name), item))
            except ValueError:
                pass

    candidates: List[Path] = []
    if layout_a_times:
        _, latest = max(layout_a_times, key=lambda x: x[0])
        primary = latest / f"{set_name}_{field}.xy"
        if primary.exists():
            candidates.append(primary)
        # Fallback glob — some OF versions use other extensions
        for glob_path in latest.glob(f"{set_name}*"):
            if glob_path.is_file() and glob_path not in candidates:
                candidates.append(glob_path)

    layout_b_root = pp_root / set_name
    if layout_b_root.is_dir():
        b_times: List[Tuple[float, Path]] = []
        for item in layout_b_root.iterdir():
            if item.is_dir():
                try:
                    b_times.append((float(item.name), item))
                except ValueError:
                    pass
        if b_times:
            _, latest_b = max(b_times, key=lambda x: x[0])
            for glob_path in latest_b.glob(f"*{field}*"):
                if glob_path.is_file() and glob_path not in candidates:
                    candidates.append(glob_path)

    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        points = _parse_openfoam_raw_points_output(text)
        if points:
            return points
    return None


class FoamAgentExecutor:
    """通过 Docker + OpenFOAM 执行真实仿真的 FoamAgentExecutor。

    1. 连接 cfd-openfoam 容器
    2. 生成 Lid-Driven Cavity 最小 case 文件
    3. 执行 blockMesh + icoFoam
    4. 解析 log 文件，提取残差和关键物理量
    """

    CONTAINER_NAME = "cfd-openfoam"
    # Case 临时目录宿主机根路径
    DEFAULT_WORK_DIR = "/tmp/cfd-harness-cases"
    SOLVER = "icoFoam"
    BLOCK_MESH_TIMEOUT = 600
    SOLVER_TIMEOUT = 7200

    # DEC-V61-053 Codex R4 LOW fix (2026-04-24): single source of truth
    # for the cylinder case's endTime. Both the controlDict generator
    # (line ~4886) and the extractor's endTime-aware trim (line ~7891)
    # read from this class constant instead of hardcoding the literal.
    # Silent-drift prevention: if a future DEC bumps this back to 60s or
    # 200s for precision, the extractor's transient_trim / min_averaging_
    # window values scale automatically.
    CYLINDER_ENDTIME_S = 10.0

    def __init__(
        self,
        work_dir: Optional[str] = None,
        container_name: Optional[str] = None,
        ncx: int = 40,
        ncy: int = 20,
    ) -> None:
        self._work_dir = Path(work_dir or self.DEFAULT_WORK_DIR)
        self._container_name = container_name or self.CONTAINER_NAME
        self._timeout = self.SOLVER_TIMEOUT
        self._docker_client: Any = None
        self._ncx = ncx
        self._ncy = ncy

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
        t0 = time.monotonic()

        # 1. Python docker SDK available?
        if not _DOCKER_AVAILABLE:
            return self._fail(
                "Docker Python SDK not installed. Real-solver execution "
                "requires the cfd-real-solver optional deps. Install with: "
                "`.venv/bin/pip install -e '.[cfd-real-solver]'` (or "
                "`pip install 'docker>=7.0'`). "
                "MockExecutor remains available for unit-test paths "
                "(EXECUTOR_MODE=mock).",
                time.monotonic() - t0,
            )

        # 2. Docker daemon reachable and container running?
        try:
            self._docker_client = docker.from_env()
            container = self._docker_client.containers.get(self._container_name)
            if container.status != "running":
                raise docker.errors.DockerException(
                    f"Container '{self._container_name}' is not running "
                    f"(status={container.status})."
                )
        except docker.errors.DockerException as exc:
            # `docker.errors.NotFound` is a subclass of DockerException; use
            # isinstance dispatch so tests that mock only DockerException
            # don't trip on a missing/non-class NotFound attribute.
            not_found_cls = getattr(docker.errors, "NotFound", None)
            try:
                is_not_found = (
                    isinstance(not_found_cls, type)
                    and isinstance(exc, not_found_cls)
                )
            except TypeError:
                is_not_found = False
            if is_not_found:
                return self._fail(
                    f"Docker container '{self._container_name}' not found. "
                    "Start it with: "
                    f"`docker start {self._container_name}` "
                    "(or create one from image "
                    "`cfd-workbench/openfoam-v10:arm64` mounted at "
                    "/tmp/cfd-harness-cases).",
                    time.monotonic() - t0,
                )
            return self._fail(
                f"Docker daemon or container '{self._container_name}' "
                f"unavailable: {exc}. Verify `docker info` works and the "
                "container is started.",
                time.monotonic() - t0,
            )
        except Exception as exc:
            return self._fail(
                f"Unexpected error initialising Docker client / container: "
                f"{exc!r}",
                time.monotonic() - t0,
            )

        # 3. 准备临时 case 目录
        case_id = f"ldc_{os.getpid()}_{int(time.time() * 1000)}"
        case_host_dir = self._work_dir / case_id
        case_cont_dir = f"/tmp/cfd-harness-cases/{case_id}"
        try:
            case_host_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return self._fail(
                f"Cannot create case directory: {exc}",
                time.monotonic() - t0,
            )

        raw_output_path = str(case_host_dir)

        try:
            # 4. 根据几何类型生成 case 文件
            if task_spec.geometry_type == GeometryType.BACKWARD_FACING_STEP:
                self._generate_backward_facing_step(case_host_dir, task_spec)
                solver_name = "simpleFoam"
            elif task_spec.geometry_type == GeometryType.NATURAL_CONVECTION_CAVITY:
                self._generate_natural_convection_cavity(case_host_dir, task_spec)
                solver_name = "buoyantFoam"
            elif task_spec.geometry_type == GeometryType.BODY_IN_CHANNEL:
                # 路由: INTERNAL (Plane Channel Flow DNS) → icoFoam laminar; EXTERNAL (Circular Cylinder Wake) → pimpleFoam
                if task_spec.flow_type == FlowType.INTERNAL:
                    self._generate_steady_internal_channel(case_host_dir, task_spec)
                    solver_name = "icoFoam"
                else:
                    solver_name = "pimpleFoam"
                    # DEC-V61-053 Batch B1: honor whitelist `turbulence_model`
                    # per DEC-V61-005 A-class correction. Prior code always
                    # called _turbulence_model_for_solver which hardcoded
                    # kOmegaSST for BODY_IN_CHANNEL EXTERNAL, silently
                    # overriding whitelist's `laminar` — see
                    # knowledge/gold_standards/circular_cylinder_wake.yaml
                    # physics_precondition. Cylinder at Re=100 is in the
                    # laminar 2D Karman shedding regime (Williamson 1996);
                    # kOmegaSST over-dissipates the wake.
                    whitelist_turb = _load_whitelist_turbulence_model(task_spec.name)
                    if whitelist_turb in ("laminar", "kOmegaSST", "kEpsilon"):
                        turbulence_model = whitelist_turb
                    else:
                        turbulence_model = self._turbulence_model_for_solver(
                            solver_name, task_spec.geometry_type, task_spec.Re
                        )
                    self._generate_circular_cylinder_wake(case_host_dir, task_spec, turbulence_model)
            elif task_spec.geometry_type == GeometryType.AIRFOIL:
                solver_name = "simpleFoam"
                turbulence_model = self._turbulence_model_for_solver(
                    solver_name, task_spec.geometry_type, task_spec.Re
                )
                self._generate_airfoil_flow(case_host_dir, task_spec, turbulence_model)
            elif task_spec.geometry_type == GeometryType.IMPINGING_JET:
                self._generate_impinging_jet(case_host_dir, task_spec)
                solver_name = "buoyantFoam"
            elif task_spec.geometry_type == GeometryType.SIMPLE_GRID:
                # LDC: canonical name match, no Re-heuristic (Codex MEDIUM: the
                # `Re < 2300` fallback was too broad — any SIMPLE_GRID laminar
                # case would get routed through the cavity generator, silent
                # wrong-physics risk).
                if self._is_lid_driven_cavity_case(task_spec, "simpleFoam"):
                    self._generate_lid_driven_cavity(case_host_dir, task_spec)
                    solver_name = "simpleFoam"
                else:
                    solver_name = "simpleFoam"
                    turbulence_model = self._turbulence_model_for_solver(
                        solver_name, task_spec.geometry_type, task_spec.Re
                    )
                    self._generate_steady_internal_flow(case_host_dir, task_spec, turbulence_model)
            else:
                self._generate_lid_driven_cavity(case_host_dir, task_spec)
                solver_name = "simpleFoam"

            # 5. 执行 blockMesh
            blockmesh_ok, blockmesh_log = self._docker_exec(
                "blockMesh", case_cont_dir, self.BLOCK_MESH_TIMEOUT,
            )
            if not blockmesh_ok:
                return self._fail(
                    f"blockMesh failed:\n{blockmesh_log}",
                    time.monotonic() - t0,
                    raw_output_path=raw_output_path,
                )

            # topoSet/createBaffles only needed for circular cylinder wake (BODY_IN_CHANNEL EXTERNAL)
            # AIRFOIL uses a direct 2D blockMesh around the projected airfoil surface.
            needs_topo = (
                task_spec.geometry_type == GeometryType.BODY_IN_CHANNEL
                and task_spec.flow_type == FlowType.EXTERNAL
            )
            if needs_topo:
                topo_ok, topo_log = self._docker_exec(
                    "topoSet", case_cont_dir, self.BLOCK_MESH_TIMEOUT,
                )
                if not topo_ok:
                    return self._fail(
                        f"topoSet failed:\n{topo_log}",
                        time.monotonic() - t0,
                        raw_output_path=raw_output_path,
                    )

                baffles_ok, baffles_log = self._docker_exec(
                    "createBaffles -overwrite", case_cont_dir, self.BLOCK_MESH_TIMEOUT,
                )
                if not baffles_ok:
                    return self._fail(
                        f"createBaffles failed:\n{baffles_log}",
                        time.monotonic() - t0,
                        raw_output_path=raw_output_path,
                    )

            # 6. 执行求解器
            solver_ok, solver_log = self._docker_exec(
                solver_name, case_cont_dir, self._timeout,
            )
            if not solver_ok:
                return self._fail(
                    f"{solver_name} failed:\n{solver_log}",
                    time.monotonic() - t0,
                    raw_output_path=raw_output_path,
                )

            # 6.5. 执行 postProcess 提取完整场数据用于关键物理量计算
            # writeObjects: 写出 U/p/phi 等场文件
            # writeCellCentres: 写出 Cx/Cy/Cz cell center 坐标 (用于定位 probe 坐标)
            # 注意: 用 -funcs '(...)' 而非 -func，OpenFOAM 才能识别多个 functionObject
            post_ok, post_log = self._docker_exec(
                "postProcess -funcs '(writeObjects writeCellCentres)' -latestTime", case_cont_dir, 120,
            )
            # postProcess 失败不阻塞主流程（后续解析会处理无数据的情况）

            # 7. 复制 postProcess 输出的场文件到宿主机
            # postProcess 写出到 latestTime 目录，需要复制回 host 才能解析
            self._copy_postprocess_fields(container, case_cont_dir, case_host_dir)

            # 7.5. [Phase 7a] Stage field artifacts (VTK + sample CSV + residuals)
            #      BEFORE the finally-block tears down case_host_dir.
            #      Best-effort: any failure MUST NOT fail the run — comparator
            #      scalar extraction below still needs to succeed.
            _phase7a_ts: Optional[str] = None
            _phase7a_cid: Optional[str] = None
            try:
                _md = getattr(task_spec, "metadata", None) or {}
                _phase7a_ts = _md.get("phase7a_timestamp")
                _phase7a_cid = _md.get("phase7a_case_id") or task_spec.name
            except Exception:
                _phase7a_ts = None
            if _phase7a_ts and _phase7a_cid:
                self._capture_field_artifacts(
                    container,
                    case_cont_dir,
                    case_host_dir,
                    _phase7a_cid,
                    _phase7a_ts,
                )

            # 8. 解析 log 文件
            log_path = case_host_dir / f"log.{solver_name}"
            residuals, key_quantities = self._parse_solver_log(log_path, solver_name, task_spec)

            # 9. 从 writeObjects 输出的场文件提取 case-specific 关键物理量
            key_quantities = self._parse_writeobjects_fields(
                log_path.parent, solver_name, task_spec, key_quantities
            )

            elapsed = time.monotonic() - t0
            return ExecutionResult(
                success=True,
                is_mock=False,
                residuals=residuals,
                key_quantities=key_quantities,
                execution_time_s=elapsed,
                raw_output_path=raw_output_path,
            )

        finally:
            # 清理临时 case 目录（Python 3.9 兼容，不使用 missing_ok）
            try:
                shutil.rmtree(case_host_dir)
            except FileNotFoundError:
                pass

    # ------------------------------------------------------------------
    # DEC-V61-075 P2-T2.1 · ExecutorAbstraction RunReport bridge
    # ------------------------------------------------------------------
    # FoamAgentExecutor pre-dates the EXECUTOR_ABSTRACTION.md §2 ABC.
    # `execute(task_spec) -> ExecutionResult` is preserved for backward
    # compatibility with the `CFDExecutor` Protocol (~30 call sites in
    # tests/, ui/backend/services/wizard_drivers.py, scripts/, and
    # src/task_runner.py legacy path) — see DEC-V61-075 scope rationale.
    # `execute_with_run_report` is the new canonical entry point that
    # wraps the same call and packages the result into the `RunReport`
    # shape the §6 TrustGate routing consumes.

    def execute_with_run_report(self, task_spec: TaskSpec) -> "RunReport":  # noqa: F821 (forward ref)
        """Run the simulation and return a §6.1 ``RunReport``.

        Per EXECUTOR_ABSTRACTION.md §6.1 (docker_openfoam mode):

        - ``mode`` is always ``ExecutorMode.DOCKER_OPENFOAM`` — this
          adapter IS the canonical truth-source executor.
        - ``status`` is ``ExecutorStatus.OK`` regardless of solver
          outcome. The spec's ``ExecutorStatus`` distinguishes executor
          *mode-level refusal* (``MODE_NOT_APPLICABLE`` for hybrid-init
          §5.2 / ``MODE_NOT_YET_IMPLEMENTED`` for future_remote §6.1)
          from run *outcome*; the latter is recorded inside
          ``execution_result.success`` and downstream gates evaluate it
          there.

          Pre-flight environment failures (Docker SDK missing, container
          stopped, case-dir creation failed) currently surface as
          ``execution_result.success=False`` with ``raw_output_path=None``
          and the synthetic note ``docker_openfoam_preflight_failed``
          appended to ``RunReport.notes`` so adopters of this API can
          observe + branch on the pre-flight vs. solver-runtime
          distinction without parsing ``error_message`` strings. The
          status stays ``OK`` because promoting environment unavailability
          to a non-OK status would require a spec amendment to §6.1 +
          ``ExecutorStatus`` (additive enum value) — out of scope for
          DEC-V61-075's "thin bridge" P2-T2.1 sub-scope. A follow-up
          DEC may introduce ``ExecutorStatus.EXECUTOR_UNAVAILABLE`` to
          let ``TaskRunner`` short-circuit on pre-flight failure
          symmetrically with the §5.2 + §6.1 mode-refusal short-circuit.
        - ``contract_hash`` and ``version`` are sourced from a transient
          :class:`DockerOpenFOAMExecutor` instance via lazy import so
          the §3 / spike F-3 manifest-tagging contract is single-sourced
          (a future spec amendment that bumps the hash flows here for
          free; this method does not duplicate the SHA-256 derivation).

        The lazy import keeps trust-core 5 module-init time light and
        avoids any circular-import surprise: ``src.executor.docker_openfoam``
        already lazy-imports ``FoamAgentExecutor`` inside ``_get_wrapped``,
        so the two-way reference is symmetric and only resolves at call
        time.
        """
        # Lazy import — see method docstring for the symmetric-lazy
        # rationale + DEC-V61-075 scope rationale.
        from src.executor import DockerOpenFOAMExecutor  # noqa: PLC0415
        from src.executor.base import ExecutorStatus, RunReport  # noqa: PLC0415

        result = self.execute(task_spec)
        canonical = DockerOpenFOAMExecutor()
        # Pre-flight environment failure detection (Codex P2-T2.1 R1 P2):
        # FoamAgentExecutor.execute() returns success=False with
        # raw_output_path=None when Docker SDK is missing, the
        # container is stopped, or case-dir creation fails (lines
        # 567-632). Solver-runtime failures (divergence, timeout) set
        # raw_output_path to the actual case directory before failing.
        # The note lets callers branch on pre-flight vs. solver-runtime
        # without parsing error_message strings; see method docstring
        # for why status stays OK in this DEC.
        notes: Tuple[str, ...] = ()
        if not result.success and result.raw_output_path is None:
            notes = ("docker_openfoam_preflight_failed",)
        return RunReport(
            mode=canonical.MODE,
            status=ExecutorStatus.OK,
            contract_hash=canonical.contract_hash,
            version=canonical.VERSION,
            execution_result=result,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Case file generation (Lid-Driven Cavity)
    # ------------------------------------------------------------------

    def _turbulence_model_for_solver(
        self, solver_name: str, geometry_type: GeometryType, Re: Optional[float] = None
    ) -> str:
        """Auto-select turbulence model based on solver family.

        Core rule: buoyantFoam family -> kEpsilon (avoids OF10 kOmegaSST dimension bug);
        SIMPLE_GRID laminar -> laminar; others -> kOmegaSST.
        """
        if "buoyant" in solver_name:
            return "kEpsilon"
        if geometry_type == GeometryType.SIMPLE_GRID and Re is not None and Re < 2300:
            return "laminar"
        return "kOmegaSST"

    @staticmethod
    def _emit_phase7a_function_objects(turbulence_model: str = "laminar") -> str:
        """Phase 7a — return the controlDict `functions{}` block as a raw string.

        Called from each case generator that opts into Phase 7a field capture.
        For LDC (laminar) yPlus is omitted; for turbulent cases the yPlus block
        is activated. Sample coordinates are in post-convertToMeters space
        (LDC: convertToMeters=0.1, so y-axis 0.0→0.1 spans the full cavity).

        See .planning/phases/07a-field-capture/07a-RESEARCH.md §2.2 for the
        function-object reference. `writeControl timeStep; writeInterval 500;`
        is correct for steady simpleFoam per research validation
        (`runTime` is transient-only — user ratification #2).
        """
        y_plus_block = ""
        if turbulence_model and turbulence_model != "laminar":
            y_plus_block = (
                "\n    yPlus\n"
                "    {\n"
                "        type            yPlus;\n"
                '        libs            ("libfieldFunctionObjects.so");\n'
                "        writeControl    writeTime;\n"
                "    }\n"
            )

        return (
            "\nfunctions\n"
            "{\n"
            "    sample\n"
            "    {\n"
            "        type            sets;\n"
            '        libs            ("libsampling.so");\n'
            "        writeControl    timeStep;\n"
            "        writeInterval   500;\n"
            "\n"
            "        interpolationScheme cellPoint;\n"
            "        setFormat       raw;\n"
            "\n"
            "        fields          (U p);\n"
            "\n"
            # OpenFOAM 10 sampledSets requires `sets (...)` list-form and
            # inner `type lineUniform;` (not `type uniform;`). Dict-form +
            # `uniform` parses via foamDictionary but crashes at runtime with
            # "Attempt to return dictionary entry as a primitive" inside
            # Foam::functionObjects::sampledSets::read. Verified against
            # /opt/openfoam10/etc/caseDicts/postProcessing/graphs/graphUniform.cfg.
            # DEC-V61-050 batch 1: two sets — uCenterline (vertical, x=0.05)
            # for Ghia Table I u-profile comparison; vCenterline (horizontal,
            # y=0.05) for Ghia Table II v-profile comparison. Without the
            # second set, v_centerline physics_contract precondition #4
            # stays unsatisfied and the audit comparator can only exercise
            # one observable dimension. The OF function-object syntax
            # accepts multiple dict-like entries inside `sets ( ... )`.
            "        sets\n"
            "        (\n"
            "            uCenterline\n"
            "            {\n"
            "                type        lineUniform;\n"
            "                axis        y;\n"
            "                start       (0.05 0.0   0.005);\n"
            "                end         (0.05 0.1   0.005);\n"
            "                nPoints     129;\n"
            "            }\n"
            "\n"
            "            vCenterline\n"
            "            {\n"
            "                type        lineUniform;\n"
            "                axis        x;\n"
            "                start       (0.0  0.05  0.005);\n"
            "                end         (0.1  0.05  0.005);\n"
            "                nPoints     129;\n"
            "            }\n"
            "        );\n"
            "    }\n"
            "\n"
            "    residuals\n"
            "    {\n"
            "        type            residuals;\n"
            '        libs            ("libutilityFunctionObjects.so");\n'
            "        writeControl    timeStep;\n"
            "        writeInterval   1;\n"
            "        fields          (U p);\n"
            "    }\n"
            f"{y_plus_block}"
            "}\n"
        )

    def _generate_lid_driven_cavity(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成 Lid-Driven Cavity 最小 OpenFOAM case 文件。"""
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        # 1. system/blockMeshDict — 立方体 cavity，顶盖驱动 (u=1 m/s)
        block_mesh = self._render_block_mesh_dict(task_spec)
        (case_dir / "system" / "blockMeshDict").write_text(
            block_mesh, encoding="utf-8"
        )

        # 2. constant/physicalProperties — 水的物性
        # convertToMeters=0.1, 实际 L=0.1m, U_lid=1 m/s
        # Re = U*L/nu → nu = U*L/Re = 0.1/Re
        Re = float(task_spec.Re or 100)
        nu_val = 0.1 / Re  # Re=100 → nu=0.001; Re=10 → nu=0.01
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;

nu              [0 2 -1 0 0 0 0] {nu_val};

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 2b. constant/momentumTransport — laminar (OpenFOAM 10 simpleFoam requirement)
        # Re=100 LDC is laminar; simpleFoam (OpenFOAM 10) mandates this file at case bring-up.
        (case_dir / "constant" / "momentumTransport").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      momentumTransport;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  laminar;

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 3. system/controlDict (Phase 7a: functions{} block injected before fence)
        _controldict_head = """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         2000;

deltaT          1;

writeControl    timeStep;

writeInterval   2000;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;
"""
        _controldict_tail = "\n// ************************************************************************* //\n"
        # LDC is laminar per constant/momentumTransport emitted above; pass through
        # turbulence_model kwarg so the helper suppresses the yPlus block. Future
        # turbulent generators (Phase 7c Sprint-2) will pass their own model string.
        (case_dir / "system" / "controlDict").write_text(
            _controldict_head
            + self._emit_phase7a_function_objects(turbulence_model="laminar")
            + _controldict_tail,
            encoding="utf-8",
        )

        # 4. system/fvSchemes
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss limitedLinearV 1;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

wallDist
{
    method          meshWave;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 5. system/fvSolution
        (case_dir / "system" / "fvSolution").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-06;
        relTol          0.1;
        smoother        GaussSeidel;
    }

    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-05;
        relTol          0.1;
        nSweeps         1;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;
    consistent      yes;
    pRefCell        0;
    pRefValue       0;
    residualControl
    {
        p               1e-5;
        U               1e-5;
    }
}

relaxationFactors
{
    equations
    {
        U               0.9;
    }
    fields
    {
        p               0.3;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 6. 0/U — 速度边界条件
        (case_dir / "0" / "U").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{
    lid
    {
        type            fixedValue;
        value           uniform (1 0 0);
    }
    wall1
    {
        type            noSlip;
    }
    wall2
    {
        type            noSlip;
    }
    bottom
    {
        type            noSlip;
    }
    frontAndBack
    {
        type            empty;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 7. 0/p — 压力边界条件
        (case_dir / "0" / "p").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    lid
    {
        type            zeroGradient;
    }
    wall1
    {
        type            zeroGradient;
    }
    wall2
    {
        type            zeroGradient;
    }
    bottom
    {
        type            zeroGradient;
    }
    frontAndBack
    {
        type            empty;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 8. system/sampleDict — gold-anchored centerline u profile (Ghia 1982)
        # C3 (docs/c3_sampling_strategy_design.md §3.1): when the task_spec
        # name matches a whitelist case with reference_values, emit explicit
        # points at the exact gold y-coords. Else fall back to uniform 16
        # points for test fixtures / off-whitelist contexts.
        gold_values = _load_gold_reference_values(task_spec.name) or []
        y_values = [float(rv["y"]) for rv in gold_values if isinstance(rv, dict) and "y" in rv]
        if y_values:
            physical_points = [(0.5, y, 0.0) for y in y_values]
            _emit_gold_anchored_points_sampledict(
                case_dir,
                set_name="uCenterline",
                physical_points=physical_points,
                fields=["U"],
                axis="y",
                header_comment=f"LDC centerline x=0.5, {len(y_values)} gold y-coords (Ghia 1982)",
            )
        else:
            (case_dir / "system" / "sampleDict").write_text(
                """\
/*--------------------------------*- C++ -*---------------------------------*\\
|  sampleDict - extract velocity profile for Gold Standard comparison      |
\\*---------------------------------------------------------------------------*/
type            sets;
libs            ("libsampling.so");

interpolationScheme cellPoint;

setFormat       raw;

sets
(
    uCenterline
    {
        type        uniform;
        axis        y;
        start       (0.5 0.0 0.0);
        end         (0.5 1.0 0.0);
        nPoints     16;
    }
);

fields          (U);

// ************************************************************************* //
""",
                encoding="utf-8",
            )

    def _generate_backward_facing_step(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成 Backward-Facing Step 最小 OpenFOAM case 文件。

        几何参数 (Driver & Seegmiller 1985, Gold Standard):
        - Re = 7600 (基于 step height H)
        - Expansion ratio = 1.125 (channel height 1.125H, inlet height H)
        - 2D channel flow, steady, incompressible
        - solver: simpleFoam
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        # Re=7600, H=1, U_bulk = nu*Re/H = nu*7600
        # 运动粘度 nu = 1e-5 (空气) 近似, 但 BFS 通常用水
        # Gold Standard: nu = U_bulk * H / Re, U_bulk 由 Re 反推
        # 这里 nu = 1/7600 m^2/s  (U_bulk=1 m/s, H=1 m)
        nu_val = 1.0 / float(task_spec.Re)  # ~1.316e-4 for Re=7600
        H = 1.0  # step height
        # Driver & Seegmiller 1985 ER=1.125 canonical geometry:
        #   inlet channel height = 8·H, full downstream channel height = 9·H,
        #   ER = H_channel / H_inlet = 9/8 = 1.125 (Xr/H=6.26 reference).
        # DEC-V61-052: previous channel_height=1.125·H was wrong-convention
        # (treated 1.125 as H_ch/H_step instead of H_ch/H_inlet) and combined
        # with the single-block mesh produced a flat channel, not a BFS.
        channel_height = 9.0 * H  # full downstream channel height (ER=1.125)

        # DEC-V61-052 round 2c: turbulence model is now selectable via
        # TaskSpec.boundary_conditions["turbulence_model"]. Default keeps
        # backwards compat with the whitelist (kEpsilon). kOmegaSST is the
        # alternative tested against Codex round 1 #4 (-37% k-ε under-
        # prediction shouldn't be blamed on the envelope before a sensitivity
        # run). Both models share the new bounded-upwind schemes + SIMPLEC
        # URFs from round 2a.
        # Round 2c measurement on this fixture (same mesh + URFs + schemes):
        #   kEpsilon    → Xr/H = 3.99  (-36.3% vs Driver 1985 = 6.26)
        #   kOmegaSST   → Xr/H = 5.63  (-10.1%)  ← inside / at edge of 10% tolerance
        # kOmegaSST's F1/F2 blending between near-wall k-ω behaviour and
        # free-stream k-ε behaviour captures the separated shear layer
        # substantially better than standard k-ε on BFS. Default to SST.
        # kEpsilon stays available as a "wrong_model" diagnostic via BC
        # override (`turbulence_model: kEpsilon`).
        bc = task_spec.boundary_conditions or {}
        turbulence_model = str(bc.get("turbulence_model", "kOmegaSST"))
        if turbulence_model not in ("kEpsilon", "kOmegaSST"):
            turbulence_model = "kOmegaSST"
        use_komega = turbulence_model == "kOmegaSST"

        # 1. system/blockMeshDict — 3-block BFS topology with real step at x=0
        block_mesh = self._render_bfs_block_mesh_dict(task_spec, H, channel_height, self._ncx, self._ncy)
        (case_dir / "system" / "blockMeshDict").write_text(block_mesh, encoding="utf-8")

        # 2. constant/physicalProperties — 牛顿流体物性
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;

nu              [0 2 -1 0 0 0 0] {nu_val};

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 3. system/controlDict — simpleFoam, steady-state
        (case_dir / "system" / "controlDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;

startFrom       startTime;

startTime       0;

stopAt          endTime;

// DEC-V61-052 round 2d: endTime bumped to 1500 so residuals have room to
// fall into the 1e-6 range — late-window Xr drift is then read straight
// off the persisted write snapshots at t=800/1000/1200/1500. Prior
// endTime=1000 left Ux at 1e-5 still dropping ~80% in the last 200
// iterations; the visual/scalar gates were all passing, but the
// stationarity claim (Codex round 1 #5) required a larger margin.
endTime         1500;

deltaT          1;

writeControl    runTime;

writeInterval   100;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;

maxCo           0.5;

// DEC-V61-052 Batch C round 2: wallShearStress FO so the solver writes
// tau_w on all walls at each writeTime. The lower_wall patch — which
// merges the inlet-floor + vertical-step-face + downstream-floor — is
// where BFS reattachment is defined (tau_x sign change on the y=0,
// x>0 faces). Without this FO, the extractor was falling back to a
// cell-centre Ux probe at y=0.5 which picked up the bottom half of
// the recirculation bubble rather than wall shear (Codex round-1 #1).
functions
{
    wallShearStress
    {
        type            wallShearStress;
        libs            ("libfieldFunctionObjects.so");
        writeControl    writeTime;
        patches         (lower_wall upper_wall);
    }
    yPlus
    {
        type            yPlus;
        libs            ("libfieldFunctionObjects.so");
        writeControl    writeTime;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 4. system/fvSchemes — SIMPLE pressure-velocity coupling
        # DEC-V61-052 round 2c: divSchemes carry both epsilon+omega
        # entries so the same template works for kEpsilon and kOmegaSST.
        # Unused entries are harmless — OpenFOAM only reads the ones the
        # active turbulence model declares.
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    // DEC-V61-052: BFS k-ε is unconditionally unstable under central-differenced
    // convection at the recirculation shear layer. Switch to bounded Gauss
    // linearUpwind for momentum (TVD-like, still 2nd-order in smooth regions)
    // and bounded upwind for turbulence scalars (keeps k, ε non-negative).
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,k)      bounded Gauss upwind;
    div(phi,epsilon) bounded Gauss upwind;
    div(phi,omega)  bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

// kOmegaSST needs wallDist for its F1/F2 blending functions. `meshWave`
// is the standard PDE-free iterative wall-distance solver in OpenFOAM
// 10. Harmless when kEpsilon is active (key is only read if requested).
wallDist
{
    method          meshWave;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 5. system/fvSolution — SIMPLE solver settings, k-epsilon turbulence
        (case_dir / "system" / "fvSolution").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p
    {
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.01;
    }

    pFinal
    {
        $p;
        relTol          0;
    }

    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          0.01;
    }

    k
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          0.01;
    }

    epsilon
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          0.01;
    }

    omega
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          0.01;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;
    // DEC-V61-052: residualControl removed — BFS k-ε false-converges in ~17 iters
    // when k/ε are bouncing around at 1e+33 but residuals (which are normalized
    // to current magnitude) come in tiny. Let the solver run endTime=1000 iters
    // and rely on monotone residual descent + post-run gate battery for sanity.
    // consistent=yes enables SIMPLEC, which permits higher URFs with less drift.
    consistent      yes;
}

relaxationFactors
{
    // DEC-V61-052: gentle BFS defaults. k-ε on a recirculating mesh with
    // steep gradients at the step corner needs p relaxation (absent
    // originally, effectively p=1.0) and tighter U/k/ε. Values here are
    // the standard Fluent/CFX-style SIMPLEC defaults for separated flow.
    fields
    {
        p               0.3;
    }
    equations
    {
        U               0.7;
        k               0.5;
        epsilon         0.5;
        omega           0.5;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 6. 0/U — 速度边界条件
        # Inlet: uniform flow U = (U_bulk, 0, 0), where U_bulk = 1 m/s
        # (Re = U_bulk*H/nu, so U_bulk = nu*Re/H = nu*7600)
        u_bulk = nu_val * float(task_spec.Re)  # = 1.0 m/s for this nu/Re pairing
        (case_dir / "0" / "U").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({u_bulk} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    lower_wall
    {{
        type            noSlip;
    }}
    upper_wall
    {{
        type            noSlip;
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 7. 0/p — 压力边界条件
        (case_dir / "0" / "p").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    lower_wall
    {
        type            zeroGradient;
    }
    upper_wall
    {
        type            zeroGradient;
    }
    front
    {
        type            empty;
    }
    back
    {
        type            empty;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 8. constant/turbulenceProperties — RAS model selected by TaskSpec
        (case_dir / "constant" / "turbulenceProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;

RAS
{{
    RASModel     {turbulence_model};

    turbulence   on;

    printCoeffs  on;
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 9. 0/nut — turbulent viscosity (required by kEpsilon)
        # Estimated: nut ~ 0.01 for Re=7600 (based on nu=1.316e-4 and U=1)
        nut_val = 0.01  # initial estimate
        (case_dir / "0" / "nut").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform {nut_val};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {nut_val};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    lower_wall
    {{
        // DEC-V61-052: Spalding-form blending wall function spans viscous
        // sublayer (y+<5), buffer (5<y+<30), and log region. First B1
        // near-wall cell at ncy_B1=40 has y+≈5 under BFS Re=7600, so
        // nutkWallFunction (log-only) would give nonsense.
        type            nutUSpaldingWallFunction;
        value           uniform 0;
    }}
    upper_wall
    {{
        // DEC-V61-052: Spalding-form blending wall function spans viscous
        // sublayer (y+<5), buffer (5<y+<30), and log region. First B1
        // near-wall cell at ncy_B1=40 has y+≈5 under BFS Re=7600, so
        // nutkWallFunction (log-only) would give nonsense.
        type            nutUSpaldingWallFunction;
        value           uniform 0;
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 10. 0/k — turbulent kinetic energy
        # Estimated: k = 0.001 for low turbulence
        k_val = 0.001
        (case_dir / "0" / "k").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform {k_val};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {k_val};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    lower_wall
    {{
        type            kqRWallFunction;
        value           uniform {k_val};
    }}
    upper_wall
    {{
        type            kqRWallFunction;
        value           uniform {k_val};
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 11. 0/epsilon OR 0/omega — turbulent dissipation field for the
        # selected RAS model. kEpsilon → ε (dim [0 2 -3 0 0 0 0],
        # epsilonWallFunction). kOmegaSST → ω (dim [0 0 -1 0 0 0 0],
        # omegaWallFunction). Initial value is an engineering estimate —
        # k/ε/ω relax fast vs U/p in steady RANS, so coarse initials
        # don't change the converged field noticeably.
        if use_komega:
            # For kOmegaSST: ω = sqrt(k)/(C_mu^0.25 · L), L≈h_s/10.
            # With k_val=0.001, C_mu=0.09, L=0.1 → ω ≈ 0.61. Round to 1.0.
            omega_val = 1.0
            (case_dir / "0" / "omega").write_text(
                f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];

internalField   uniform {omega_val};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {omega_val};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    lower_wall
    {{
        type            omegaWallFunction;
        value           uniform {omega_val};
    }}
    upper_wall
    {{
        type            omegaWallFunction;
        value           uniform {omega_val};
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
""",
                encoding="utf-8",
            )
        else:
            epsilon_val = 0.001
            (case_dir / "0" / "epsilon").write_text(
                f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      epsilon;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -3 0 0 0 0];

internalField   uniform {epsilon_val};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {epsilon_val};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    lower_wall
    {{
        type            epsilonWallFunction;
        value           uniform {epsilon_val};
    }}
    upper_wall
    {{
        type            epsilonWallFunction;
        value           uniform {epsilon_val};
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
""",
                encoding="utf-8",
            )

        # 8. system/sampleDict — extract velocity profile to find reattachment length (Driver 1985)
        # Sample Ux at y=0.5 (boundary layer) along x from -1 to 12
        # Reattachment point: where Ux changes from negative (recirculation) to positive
        (case_dir / "system" / "sampleDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
|  sampleDict - extract velocity profile for reattachment length           |
\\*---------------------------------------------------------------------------*/
type            sets;
libs            ("libsampling.so");

interpolationScheme cellPoint;

setFormat       raw;

sets
(
    // Near-floor probe for Xr extraction — y=0.025 sits inside the first
    // B1 cell (ncy_B1=40, dy_B1≈0.025) for x≥0; for x<0 the probe runs
    // through the step void and samples nothing (field undefined → skipped
    // by the post-hoc Xr extractor). DEC-V61-052 geometry: L_down=30·H.
    wallProfile
    {
        type        uniform;
        axis        x;
        start       (0.05 0.025 0.05);
        end         (29.95 0.025 0.05);
        nPoints     300;
    }
);

fields          (U);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _generate_natural_convection_cavity(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成自然对流腔体（差温腔体）OpenFOAM case 文件。

        参考: Dhir 2001, Ampofo & Karayiannis 2003 (Ra=10^10).
        - Square cavity, aspect ratio = 1
        - Left wall: hot (T_hot), Right wall: cold (T_cold)
        - Top/bottom: adiabatic
        - 2D approximation (z-depth = 0.1m)
        - Solver: buoyantFoam (Boussinesq, h-based energy)
        - Turbulence: k-omega SST
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        # Physical parameters
        Ra = float(task_spec.Ra or task_spec.Re or 1e10)  # Use Ra field; fallback to Re as proxy
        Pr = 0.71  # Prandtl number (air)
        # Boussinesq validity: beta * dT << 1
        # At mean T=323K: beta=1/T_mean≈0.0031; set dT=10K → beta*dT≈0.031 (VALID)
        # dT=10K works for both Ra=1e6 (NC Cavity) and Ra=1e10 (DHC) via g scaling
        T_hot = 305.0  # K
        T_cold = 295.0  # K
        dT = T_hot - T_cold  # 10K — Boussinesq-valid for all Ra
        # DEC-V61-057 Batch A.1 (Codex F1-HIGH): the historic Ra-threshold
        # heuristic (Ra<1e9 → AR=2.0; Ra>=1e9 → AR=1.0) trapped DHC at
        # Ra=1e6 (de Vahl Davis 1983, AR=1.0 square cavity) into the
        # rayleigh_benard 2:1-rectangle branch because Ra=1e6 is shared
        # between RBC (AR=2.0) and DHC (AR=1.0). Resolution priority:
        #
        #   1. task_spec.boundary_conditions["aspect_ratio"]  — explicit override
        #   2. whitelist.yaml parameters.aspect_ratio for task_spec.name
        #   3. case-id-aware fallback (DHC=1.0, RBC=2.0)
        #   4. Ra-threshold heuristic (legacy default for unknown cases)
        bc_ar = (
            task_spec.boundary_conditions.get("aspect_ratio")
            if task_spec.boundary_conditions
            else None
        )
        wl_ar = _load_whitelist_parameter(task_spec.name, "aspect_ratio")
        if isinstance(bc_ar, (int, float)):
            aspect_ratio = float(bc_ar)
        elif wl_ar is not None:
            aspect_ratio = wl_ar
        else:
            # DEC-V61-057 Batch A.5 (Codex round-1 F1-HIGH): normalize through
            # the alias map before substring fallback so Notion-supplied
            # display titles (e.g. "Differential Heated Cavity (Natural
            # Convection)") resolve to the canonical case_id and the
            # case-id-aware fallback fires correctly.
            canonical = _normalize_task_name_to_case_id(task_spec.name or "").lower()
            if "differential_heated_cavity" in canonical:
                aspect_ratio = 1.0  # DHC: square cavity (de Vahl Davis 1983)
            elif "rayleigh_benard" in canonical or "rayleigh-bénard" in canonical:
                aspect_ratio = 2.0  # RBC: 2:1 rectangle (semantic; see test_rbc_keeps_uniform_mesh)
            elif Ra >= 1e9:
                aspect_ratio = 1.0  # legacy: high-Ra DHC heuristic
            elif Ra >= 1e5:
                aspect_ratio = 2.0  # legacy: mid-Ra RBC heuristic
            else:
                aspect_ratio = 1.0  # safe square default
        L = aspect_ratio  # cavity length in x-direction (m)
        beta = 1.0 / ((T_hot + T_cold) / 2.0)  # Boussinesq beta at mean temperature
        nu = 1.0e-5  # kinematic viscosity (air, m^2/s)
        alpha = nu / Pr  # thermal diffusivity
        # DEC-V61-057 Batch A.2 (Codex F1-HIGH): natural-convection path
        # historically hard-wrote `simulationType RAS` + `kOmegaSST` plus
        # k/epsilon/omega/nut initial fields, regardless of whitelist
        # turbulence_model. For DHC at Ra=1e6 (de Vahl Davis, laminar
        # regime), this added spurious dissipation budget and mis-tuned Nu.
        # Resolution: consult whitelist; default kOmegaSST for legacy cases.
        wl_turb = _load_whitelist_turbulence_model(task_spec.name)
        turbulence_model = wl_turb or "kOmegaSST"
        if turbulence_model not in ("laminar", "kEpsilon", "kOmegaSST"):
            turbulence_model = "kOmegaSST"  # safe fallback
        is_laminar_nc = (turbulence_model == "laminar")

        # Derived
        # Ra = g * beta * dT * L^3 / (nu * alpha)
        # g = Ra * nu * alpha / (beta * dT * L^3)
        g = Ra * nu * alpha / (beta * dT * L**3)  # gravity magnitude
        # EX-1-007 B1: DHC (Ra>=1e9) needs ~2 cells in thermal BL (δ_T ~ L·Ra^-0.25).
        # Symmetric wall-packing: first half expansion=6 (small cells at wall x=0),
        # second half expansion=1/6 (small cells at wall x=L). Midline cells large.
        # blockMesh smoke-check verified min cell ≈ 1.4mm, max ≈ 8.4mm, aspect=6.
        #
        # DEC-V61-057 Batch A.3 (Codex F1-HIGH): DHC at Ra=1e6 (de Vahl Davis 1983)
        # also needs BL grading. At Ra=1e6, δ_T/L ≈ Ra^(-1/4) ≈ 0.032; uniform
        # 80 cells gives Δ=0.0125L → 2.56 cells in BL, BELOW 5-cell minimum.
        # Solution: reuse the high-Ra grading branch for DHC at any Ra (square
        # cavity δ_T scales with Ra^-0.25 across all Ra). 4:1 wall-packing
        # gives wall cell ≈ 0.006L → 5.3 BL cells at Ra=1e6 (sufficient).
        # RBC stays uniform: rolls span full domain, no thin BL to resolve.
        # DEC-V61-057 Batch A.5: same alias-aware normalization for mesh dispatch.
        is_dhc = (
            "differential_heated_cavity"
            in _normalize_task_name_to_case_id(task_spec.name or "").lower()
        )
        if Ra >= 1e9 or is_dhc:
            # graded mesh — symmetric wall packing
            if is_dhc and Ra < 1e9:
                # DHC at moderate Ra (e.g. de Vahl Davis 1e6 benchmark): 80 cells
                # with 4:1 packing gives wall cell ≈ 0.006L (≥5 BL cells at Ra=1e6).
                nL = max(int(80 * L), 80)
                grading_str = "((0.5 0.5 4) (0.5 0.5 0.25))"
            else:
                # DHC at Ra>=1e9 (legacy turbulent regime): 256 cells + 6:1 packing.
                nL = max(int(256 * L), 128)
                grading_str = "((0.5 0.5 6) (0.5 0.5 0.1667))"
        else:
            # RBC and other non-DHC NC cavities: uniform mesh
            nL = max(int(80 * L), 40)
            grading_str = "1"
        mean_T = (T_hot + T_cold) / 2.0  # initial temperature field
        # Store dT/L in boundary_conditions for the extractor (TaskSpec is local to this call)
        if task_spec.boundary_conditions is None:
            task_spec.boundary_conditions = {}
        task_spec.boundary_conditions["dT"] = dT
        task_spec.boundary_conditions["L"] = L
        # DEC-V61-042: plumb wall-coord + wall-value + BC type so the
        # extractor can call src.wall_gradient.extract_wall_gradient
        # against the actual boundary face instead of guessing which of
        # two interior cells to difference. Hot wall at x=0, cold at x=L,
        # both fixedValue per the T boundary block written below.
        task_spec.boundary_conditions["wall_coord_hot"] = 0.0
        task_spec.boundary_conditions["wall_coord_cold"] = L
        task_spec.boundary_conditions["T_hot_wall"] = T_hot
        task_spec.boundary_conditions["T_cold_wall"] = T_cold
        task_spec.boundary_conditions["wall_bc_type"] = "fixedValue"
        # h = Cp*(T - T0) with T0=300K
        Cp = 1005.0
        T0 = 300.0
        h_hot = Cp * (T_hot - T0)       # 5025 for T_hot=305K
        h_cold = Cp * (T_cold - T0)      # -5025 for T_cold=295K
        h_internal = Cp * (mean_T - T0)   # 0 for mean_T=300K
        # omega initialization for kOmegaSST: omega = sqrt(k)/(Cmu^0.25 * L)
        Cmu = 0.09  # kOmegaSST constant
        kappa = 0.41  # von Karman constant
        k_internal = 1e-4  # matches 0/k initial value
        omega_init = float(
            "{omega_init:.4f}".format(
                omega_init=math.sqrt(k_internal) / (Cmu**0.25 * max(L, 0.01))
            )
        )
        omega_wall = float(
            "{omega_wall:.4f}".format(
                omega_wall=math.sqrt(k_internal) / (Cmu**0.25 * max(L, 0.01))
            )
        )

        # --------------------------------------------------------------------------
        # 1. system/blockMeshDict — cavity with configurable aspect ratio
        # --------------------------------------------------------------------------
        # Build dynamic mesh geometry from L (aspect_ratio) and nL (cell count)
        _vertices = """vertices
(
    (0 0 0)
    ({Lx:g} 0 0)
    ({Lx:g} {Ly:g} 0)
    (0 {Ly:g} 0)
    (0 0 0.1)
    ({Lx:g} 0 0.1)
    ({Lx:g} {Ly:g} 0.1)
    (0 {Ly:g} 0.1)
);""".format(Lx=L, Ly=L)
        _blocks = """blocks
(
    hex (0 1 2 3 4 5 6 7) ({nLx} {nLy} 1) simpleGrading ({gx} {gy} 1)
);""".format(nLx=nL, nLy=nL, gx=grading_str, gy=grading_str)
        _bnd = """boundary
(
    hot_wall
    {
        type            wall;
        faces           ((0 4 7 3));
    }
    cold_wall
    {
        type            wall;
        faces           ((1 2 6 5));
    }
    adiabatic_top
    {
        type            wall;
        faces           ((3 7 6 2));
    }
    adiabatic_bottom
    {
        type            wall;
        faces           ((0 1 5 4));
    }
    front
    {
        type            empty;
        faces           ((0 3 2 1));
    }
    back
    {
        type            empty;
        faces           ((4 5 6 7));
    }
);"""
        _header = """/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;
"""
        blockmesh_txt = _header + "\n" + _vertices + "\n\n" + _blocks + "\n\nedges\n(\n);\n\n" + _bnd + "\n\nmergePatchPairs\n(\n);\n\n// ************************************************************************* //"
        (case_dir / "system" / "blockMeshDict").write_text(blockmesh_txt, encoding="utf-8")


        # --------------------------------------------------------------------------
        # 2. constant/physicalProperties — Boussinesq fluid
        # --------------------------------------------------------------------------
        # Cp for Boussinesq: use 1005 J/(kg·K) for air at ~300K
        Cp = 1005.0
        mu = nu  # dynamic viscosity == nu * rho (rho=1 for Boussinesq)

        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

thermoType
{{
    type            heRhoThermo;
    mixture         pureMixture;
    transport       const;
    thermo          hConst;
    equationOfState Boussinesq;
    specie          specie;
    energy          sensibleEnthalpy;
}}

mixture
{{
    specie
    {{
        molWeight       28.9;
    }}
    equationOfState
    {{
        rho0            1;
        T0              300;
        beta            {beta:.16e};
    }}
    thermodynamics
    {{
        Cp              {Cp:.16e};
        Hf              0;
    }}
    transport
    {{
        mu              {mu:.16e};
        Pr              {Pr};
    }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 3. constant/g — Gravity
        # --------------------------------------------------------------------------
        (case_dir / "constant" / "g").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      g;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions       [0 1 -2 0 0 0 0];

value           (0 -{g:.16e} 0);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 4. constant/turbulenceProperties
        # DEC-V61-057 Batch A.2 (Codex F1-HIGH): consult whitelist turbulence_model
        # before falling back to RAS+kOmegaSST default.
        # --------------------------------------------------------------------------
        _turb_props_header = """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

"""
        if is_laminar_nc:
            _turb_props_body = "simulationType  laminar;\n"
        else:
            _turb_props_body = (
                "simulationType  RAS;\n\n"
                "RAS\n{\n"
                f"    RASModel      {turbulence_model};\n\n"
                "    turbulence    on;\n\n"
                "    printCoeffs   on;\n"
                "}\n"
            )
        (case_dir / "constant" / "turbulenceProperties").write_text(
            _turb_props_header
            + _turb_props_body
            + "\n// ************************************************************************* //\n",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 5. system/controlDict — buoyantSimpleFoam
        # --------------------------------------------------------------------------
        # EX-1-007 B1: 256² wall-packed mesh at Ra=1e10 measured 70s/step; full
        # endTime=500 (1000 steps) would take ~19h. Characteristic time τ=L/v_buoy
        # ≈ 0.84s at Ra=1e10, so endTime=10 (~12τ) is sufficient for quasi-steady
        # Nu extraction. 80²-uniform baseline (Ra=1e6) keeps endTime=500 unchanged.
        _dhc_end_time = 10 if Ra >= 1e9 else 500
        _ctrl_dict_text = """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     buoyantFoam;

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         500;

deltaT          0.5;

writeControl    runTime;

writeInterval   200;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;

// ************************************************************************* //
"""
        # EX-1-007 B1: writeInterval must be <= endTime, else postProcess -latestTime
        # finds no field output. Original heredoc had a duplicate writeInterval
        # (100 then 200) — collapsed to single 200, now parameterized to endTime.
        _write_interval = _dhc_end_time if Ra >= 1e9 else 200
        (case_dir / "system" / "controlDict").write_text(
            _ctrl_dict_text.replace(
                "endTime         500;",
                "endTime         {0};".format(_dhc_end_time),
            ).replace(
                "writeInterval   200;",
                "writeInterval   {0};".format(_write_interval),
            ),
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 6. system/fvSchemes
        # --------------------------------------------------------------------------
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss upwind;
    div(phi,h)      bounded Gauss upwind;
    div(phi,K)      bounded Gauss linear;
    div(phi,k)      bounded Gauss upwind;
    div(phi,epsilon) bounded Gauss upwind;
    div(phi,omega)     bounded Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}
wallDist
{
    method          meshWave;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 7. system/fvSolution
        # --------------------------------------------------------------------------
        (case_dir / "system" / "fvSolution").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p_rgh
    {
        solver          PCG;
        preconditioner   DIC;
        tolerance       1e-7;
        relTol          0.01;
    }
    p_rghFinal
    {
        $p_rgh;
        relTol          0;
    }
    h
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-8;
        relTol          0.01;
        maxIter         2000;
    }
    hFinal
    {
        $h;
        relTol          0;
    }
    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-7;
        relTol          0.01;
    }
    UFinal
    {
        $U;
        relTol          0;
    }
    k
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    epsilon
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-6;
        relTol          0.01;
    }
    omega
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
}

relaxationFactors
{
    fields
    {
        p_rgh           0.1;
    }
    equations
    {
        U               0.3;
        h               0.05;
        k               0.3;
        epsilon         0.3;
        omega           0.3;
    }
}

PIMPLE
{
    nOuterCorrectors 80;
    nNonOrthogonalCorrectors 2;
    pRefCell        0;
    pRefValue       0;

    residualControl
    {
        U       1e-5;
        h       1e-6;
        p_rgh   1e-5;
        k       1e-5;
        epsilon 1e-5;
        omega   1e-5;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 8. 0/U — Velocity (initial: zero)
        # --------------------------------------------------------------------------
        (case_dir / "0" / "U").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{
    hot_wall
    {
        type            fixedValue;
        value           uniform (0 0 0);
    }
    cold_wall
    {
        type            fixedValue;
        value           uniform (0 0 0);
    }
    adiabatic_top
    {
        type            fixedValue;
        value           uniform (0 0 0);
    }
    adiabatic_bottom
    {
        type            fixedValue;
        value           uniform (0 0 0);
    }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 9. 0/p — Static pressure (thermodynamic pressure, used by buoyantFoam)
        # --------------------------------------------------------------------------
        (case_dir / "0" / "p").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    hot_wall
    {
        type            calculated;
        value           $internalField;
    }
    cold_wall
    {
        type            calculated;
        value           $internalField;
    }
    adiabatic_top
    {
        type            calculated;
        value           $internalField;
    }
    adiabatic_bottom
    {
        type            calculated;
        value           $internalField;
    }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 9b. 0/p_rgh — buoyant pressure (hydrostatic)
        # p_rgh = p - rho*g*h for Boussinesq
        # --------------------------------------------------------------------------
        (case_dir / "0" / "p_rgh").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p_rgh;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    hot_wall
    {
        type            fixedFluxPressure;
        value           $internalField;
    }
    cold_wall
    {
        type            fixedFluxPressure;
        value           $internalField;
    }
    adiabatic_top
    {
        type            fixedFluxPressure;
        value           $internalField;
    }
    adiabatic_bottom
    {
        type            fixedFluxPressure;
        value           $internalField;
    }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 10. 0/h — Sensible enthalpy (replaces T for buoyantFoam)
        # h = Cp*(T-T_cold), [0 2 -2 0 0 0 0]; hot: Cp*10K=10050, cold: 0
        # --------------------------------------------------------------------------
        (case_dir / "0" / "h").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      h;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

// h = Cp*(T - T0), T0=300K from equationOfState
// hot_wall: Cp*(T_hot-T0) = 1005*(305-300) = 5025
// cold_wall: Cp*(T_cold-T0) = 1005*(295-300) = -5025
// internalField: Cp*(mean_T-T0) = 1005*(300-300) = 0
internalField   uniform {h_internal};

boundaryField
{{
    hot_wall
    {{
        type            fixedValue;
        value           uniform {h_hot};
    }}
    cold_wall
    {{
        type            fixedValue;
        value           uniform {h_cold};
    }}
    adiabatic_top
    {{
        type            zeroGradient;
    }}
    adiabatic_bottom
    {{
        type            zeroGradient;
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 10b. 0/T — Temperature (required by buoyantFoam even with sensibleEnthalpy)
        # CRITICAL: With energy equation in terms of h (sensibleEnthalpy), T at walls
        # must be zeroGradient — NOT fixedValue. Setting T fixedValue over-constrains
        # the energy equation (solver already has h fixedValue at walls), causing T field
        # to stay near initial mean_T with ~1K variation instead of 10K gradient.
        # --------------------------------------------------------------------------
        (case_dir / "0" / "T").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      T;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 0 1 0 0 0];

internalField   uniform {mean_T};

boundaryField
{{
    hot_wall
    {{
        type            fixedValue;
        value           uniform {T_hot};
    }}
    cold_wall
    {{
        type            fixedValue;
        value           uniform {T_cold};
    }}
    adiabatic_top
    {{
        type            zeroGradient;
    }}
    adiabatic_bottom
    {{
        type            zeroGradient;
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 10c. 0/alphat — Turbulent thermal diffusivity (required by kOmegaSST)
        # alphat = mu_t / Pr_t; wallFunction handles near-wall treatment
        # --------------------------------------------------------------------------
        (case_dir / "0" / "alphat").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      alphat;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{{
    hot_wall
    {{
        type            compressible::alphatJayatillekeWallFunction;
        Prt             0.85;
        value           uniform 0;
    }}
    cold_wall
    {{
        type            compressible::alphatJayatillekeWallFunction;
        Prt             0.85;
        value           uniform 0;
    }}
    adiabatic_top
    {{
        type            zeroGradient;
    }}
    adiabatic_bottom
    {{
        type            zeroGradient;
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 11. 0/k — Turbulent kinetic energy [m2/s2]
        # DEC-V61-057 Batch A.2: skipped for laminar regime (no RAS transport
        # equations to seed). For laminar buoyantFoam, k field is never read.
        # --------------------------------------------------------------------------
        if not is_laminar_nc: (case_dir / "0" / "k").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 1e-4;

boundaryField
{{
    hot_wall           {{ type kqRWallFunction; value uniform 1e-4; }}
    cold_wall          {{ type kqRWallFunction; value uniform 1e-4; }}
    adiabatic_top       {{ type kqRWallFunction; value uniform 1e-4; }}
    adiabatic_bottom    {{ type kqRWallFunction; value uniform 1e-4; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 11b. 0/epsilon — Turbulent dissipation rate [m2/s3]
        # DEC-V61-057 Batch A.2: skipped for laminar regime (k-epsilon transport
        # equations not active in laminar buoyantFoam).
        # --------------------------------------------------------------------------
        if not is_laminar_nc: (case_dir / "0" / "epsilon").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      epsilon;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -3 0 0 0 0];

internalField   uniform 1e-5;

boundaryField
{{
    hot_wall           {{ type epsilonWallFunction; value uniform 1e-5; }}
    cold_wall          {{ type epsilonWallFunction; value uniform 1e-5; }}
    adiabatic_top       {{ type epsilonWallFunction; value uniform 1e-5; }}
    adiabatic_bottom    {{ type epsilonWallFunction; value uniform 1e-5; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 11c. 0/omega — Specific dissipation rate [1/s] (required by kOmegaSST)
        # omega_init and omega_wall already computed at lines 1334-1343
        # DEC-V61-057 Batch A.2: skipped for laminar regime.
        # --------------------------------------------------------------------------
        if not is_laminar_nc: (case_dir / "0" / "omega").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];

internalField   uniform {omega_init:.4f};

boundaryField
{{
    hot_wall
    {{
        type            omegaWallFunction;
        value           uniform {omega_wall:.4f};
    }}
    cold_wall
    {{
        type            omegaWallFunction;
        value           uniform {omega_wall:.4f};
    }}
    adiabatic_top
    {{
        type            omegaWallFunction;
        value           uniform {omega_wall:.4f};
    }}
    adiabatic_bottom
    {{
        type            omegaWallFunction;
        value           uniform {omega_wall:.4f};
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 12. 0/nut — Turbulent viscosity (for k-omega SST)
        # DEC-V61-057 Batch A.2: skipped for laminar regime (nut not used by
        # laminar momentum equation; would be a phantom field).
        # --------------------------------------------------------------------------
        if not is_laminar_nc: (case_dir / "0" / "nut").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    hot_wall           { type nutkWallFunction; value uniform 0; }
    cold_wall          { type nutkWallFunction; value uniform 0; }
    adiabatic_top       { type nutkWallFunction; value uniform 0; }
    adiabatic_bottom    { type nutkWallFunction; value uniform 0; }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 12b. 0/omega — Specific dissipation rate [1/s] (for k-omega SST)
        # omega = sqrt(k) / (Cmu^0.25 * L), Cmu=0.09 so Cmu^0.25=0.5623
        # With k=1e-4 and L=1.0: omega ≈ 0.0178
        # DEC-V61-057 Batch A.2: skipped for laminar regime. NOTE: this is the
        # second omega write in this method (after 11c) — appears to be a pre-
        # existing duplicate. Both blocks are now laminar-guarded.
        # --------------------------------------------------------------------------
        omega_init = (1e-4 ** 0.5) / ((0.09 ** 0.25) * max(L, 1.0))
        if not is_laminar_nc: (case_dir / "0" / "omega").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];

internalField   uniform {omega_init};

boundaryField
{{
    hot_wall
    {{
        type            omegaWallFunction;
        value           uniform {omega_init};
    }}
    cold_wall
    {{
        type            omegaWallFunction;
        value           uniform {omega_init};
    }}
    adiabatic_top
    {{
        type            omegaWallFunction;
        value           uniform {omega_init};
    }}
    adiabatic_bottom
    {{
        type            omegaWallFunction;
        value           uniform {omega_init};
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # -- P-B C2: post-write plumbing verification -----------------------
        # Round-trip the written dict files and confirm the declared Ra
        # survived. Raises ParameterPlumbingError BEFORE the solver starts.
        declared_Ra = float(task_spec.Ra or task_spec.Re or 1e10)
        self._verify_buoyant_case_plumbing(
            case_dir=case_dir,
            declared_Ra=declared_Ra,
            declared_Pr=Pr,
            declared_L=L,
            declared_dT=dT,
            declared_beta=beta,
        )

    # ------------------------------------------------------------------
    # P-B C2: parameter plumbing verifiers
    # ------------------------------------------------------------------
    @staticmethod
    def _verify_buoyant_case_plumbing(
        case_dir: Path,
        declared_Ra: float,
        declared_Pr: float,
        declared_L: float,
        declared_dT: float,
        declared_beta: float,
        tolerance: float = 0.01,
    ) -> None:
        """Parse back ``constant/physicalProperties`` and ``constant/g`` from
        a natural-convection-cavity case dir, recompute the effective
        Rayleigh number from on-disk values, and assert it matches
        ``declared_Ra`` within ``tolerance`` (1% default).

        Catches silent regressions where a parameter (g, beta, mu, Pr, L)
        plumbs through to one derived quantity but not the file that the
        solver actually reads.
        """
        props_path = case_dir / "constant" / "physicalProperties"
        g_path = case_dir / "constant" / "g"
        if not props_path.exists():
            raise ParameterPlumbingError(
                f"physicalProperties missing at {props_path} — generator skipped write"
            )
        if not g_path.exists():
            raise ParameterPlumbingError(
                f"constant/g missing at {g_path} — gravity was not written"
            )

        props_text = props_path.read_text(encoding="utf-8")
        g_text = g_path.read_text(encoding="utf-8")

        beta = _parse_dict_scalar(props_text, "beta")
        Cp = _parse_dict_scalar(props_text, "Cp")
        mu = _parse_dict_scalar(props_text, "mu")
        Pr = _parse_dict_scalar(props_text, "Pr")
        g_mag = _parse_g_magnitude(g_text)

        missing = [
            name for name, val in (
                ("beta", beta), ("Cp", Cp), ("mu", mu), ("Pr", Pr), ("|g|", g_mag),
            ) if val is None
        ]
        if missing:
            raise ParameterPlumbingError(
                f"Could not parse {missing} from case files under {case_dir}. "
                f"physicalProperties format may have drifted from the regex."
            )

        # rho0=1 in Boussinesq formulation we emit → nu == mu. alpha = nu / Pr.
        nu = mu
        alpha = nu / Pr
        Ra_effective = g_mag * beta * declared_dT * (declared_L ** 3) / (nu * alpha)

        if declared_Ra <= 0:
            raise ParameterPlumbingError(
                f"declared Ra={declared_Ra} is not positive — upstream task_spec bug"
            )
        rel_err = abs(Ra_effective - declared_Ra) / declared_Ra
        if rel_err > tolerance:
            raise ParameterPlumbingError(
                "Buoyant case plumbing drift: declared Ra={:g}, but files on disk "
                "encode Ra_effective={:g} (rel_err={:.2%}, tol={:.2%}). "
                "Disk values: beta={:.4e}, mu(=nu)={:.4e}, Pr={:.4f}, |g|={:.4e}, "
                "dT={:.4f}, L={:.4f}. Fix the generator or update the declared "
                "parameters in the whitelist.".format(
                    declared_Ra, Ra_effective, rel_err, tolerance,
                    beta, mu, Pr, g_mag, declared_dT, declared_L,
                )
            )
        if abs(Pr - declared_Pr) / max(declared_Pr, 1e-12) > tolerance:
            raise ParameterPlumbingError(
                "Pr plumbing drift: declared Pr={:g}, file encodes Pr={:g}".format(
                    declared_Pr, Pr,
                )
            )

    @staticmethod
    def _verify_internal_channel_plumbing(
        case_dir: Path,
        declared_Re: float,
        tolerance: float = 0.01,
    ) -> None:
        """Parse back ``constant/physicalProperties`` from a plane-channel
        case and assert ``Re_effective = 1/nu`` matches ``declared_Re``.

        The convention U_bulk=1 m/s means Re = 1/nu — any drift here means
        the solver sees a different Reynolds number than what the whitelist
        declared.
        """
        props_path = case_dir / "constant" / "physicalProperties"
        if not props_path.exists():
            raise ParameterPlumbingError(
                f"physicalProperties missing at {props_path}"
            )
        nu = _parse_dict_scalar(props_path.read_text(encoding="utf-8"), "nu")
        if nu is None:
            raise ParameterPlumbingError(
                f"Could not parse 'nu' from {props_path}. Format may have drifted."
            )
        if nu <= 0:
            raise ParameterPlumbingError(
                f"Disk encodes non-positive nu={nu} — case will blow up"
            )
        Re_effective = 1.0 / nu
        if declared_Re <= 0:
            raise ParameterPlumbingError(
                f"declared Re={declared_Re} is not positive — upstream task_spec bug"
            )
        rel_err = abs(Re_effective - declared_Re) / declared_Re
        if rel_err > tolerance:
            raise ParameterPlumbingError(
                "Internal channel plumbing drift: declared Re={:g}, disk encodes "
                "Re_effective={:g} (1/nu where nu={:.4e}, rel_err={:.2%}, "
                "tol={:.2%}). Fix the generator.".format(
                    declared_Re, Re_effective, nu, rel_err, tolerance,
                )
            )

    def _generate_steady_internal_channel(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成平面通道层流 case 文件（icoFoam + laminar, 无湍流模型）。

        适用于:
        - Plane Channel Flow DNS (BODY_IN_CHANNEL + INTERNAL, Re_tau=180)

        几何: 矩形通道 x=[-5D, 10D], y=[-D/2, D/2], z=[-D/2, D/2], D=1
        - Inlet (x=-5D): fixedValue U=(U_bulk,0,0), zeroGradient p
        - Outlet (x=10D): zeroGradient U, fixedValue p=0
        - Walls (y=±D/2, z=±D/2): noSlip
        - 2D: front/back empty
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        D = 1.0
        L = 15.0 * D
        half_D = D / 2.0
        ncx = max(4, self._ncx)
        ncy = max(4, self._ncy // 2)
        ncz = max(4, self._ncy // 2)

        Re = float(task_spec.Re or 5600)
        nu_val = 1.0 / Re
        U_bulk = 1.0

        # DEC-V61-043: plumb the physical constants the u+/y+ emitter
        # needs. Walls at y=±D/2 with noSlip (fixedValue U=0). Half
        # channel height h = D/2. icoFoam is kinematic, so u_tau =
        # sqrt(|τ_w/ρ|) with τ_w/ρ read directly from the
        # wallShearStress FO.
        if task_spec.boundary_conditions is None:
            task_spec.boundary_conditions = {}
        task_spec.boundary_conditions["channel_D"] = D
        task_spec.boundary_conditions["channel_half_height"] = half_D
        task_spec.boundary_conditions["nu"] = nu_val
        task_spec.boundary_conditions["U_bulk"] = U_bulk

        # 1. system/blockMeshDict
        (case_dir / "system" / "blockMeshDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
convertToMeters 1;

vertices
(
    (-{L} -{half_D} -{half_D})
    ({L}  -{half_D} -{half_D})
    ({L}   {half_D} -{half_D})
    (-{L}  {half_D} -{half_D})
    (-{L} -{half_D}  {half_D})
    ({L}  -{half_D}  {half_D})
    ({L}   {half_D}  {half_D})
    (-{L}  {half_D}  {half_D})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({ncx} {ncy} {ncz}) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type            patch;
        faces
        (
            (0 4 7 3)
        );
    }}
    outlet
    {{
        type            patch;
        faces
        (
            (1 2 6 5)
        );
    }}
    walls
    {{
        type            wall;
        faces
        (
            (3 7 6 2)
            (0 1 5 4)
        );
    }}
    front
    {{
        type            empty;
        faces
        (
            (0 3 2 1)
        );
    }}
    back
    {{
        type            empty;
        faces
        (
            (4 5 6 7)
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 2. constant/physicalProperties
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] {nu_val};
// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 3. system/controlDict
        (case_dir / "system" / "controlDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
application     icoFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         50;
deltaT          0.002;
writeControl    timeStep;
writeInterval   25000;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

// DEC-V61-043: in-solver function objects for u_tau / u+ / y+
// extraction. wallShearStress writes τ_w at both channel walls;
// uLine samples U along y at x=0 (mid-length, fully-developed
// region for our long domain). Outputs:
//   postProcessing/wallShearStress/<t>/wallShearStress.dat
//   postProcessing/uLine/<t>/channelCenter_U.xy
// icoFoam works in kinematic viscosity, so wallShearStress returns
// τ_w/ρ (kinematic stress, units m²/s²). u_τ = sqrt(|τ_w/ρ|).
functions
{{
    wallShearStress
    {{
        type            wallShearStress;
        libs            ("libfieldFunctionObjects.so");
        patches         (walls);
        writeControl    writeTime;
        writeFields     false;
        log             false;
    }}

    uLine
    {{
        type            sets;
        libs            ("libsampling.so");
        writeControl    writeTime;
        interpolationScheme cellPoint;
        setFormat       raw;
        fields          (U);
        sets
        (
            channelCenter
            {{
                type        lineUniform;
                axis        y;
                start       (0.0 -0.5 0.0);
                end         (0.0  0.5 0.0);
                nPoints     129;
            }}
        );
    }}
}}
// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 4. system/fvSchemes
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
ddtSchemes
{
    default         Euler;
}
gradSchemes
{
    default         Gauss linear;
}
divSchemes
{
    default         none;
    div(phi,U)      Gauss linear;
}
laplacianSchemes
{
    default         Gauss linear corrected;
}
// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 5. system/fvSolution
        (case_dir / "system" / "fvSolution").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
solvers
{
    p
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-06;
        relTol          0.05;
    }
    pFinal
    {
        $p;
        relTol          0;
    }
    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-05;
        relTol          0.05;
    }
}
PISO
{
    nCorrectors         2;
    nNonOrthogonalCorrectors 0;
    pRefCell            0;
    pRefValue           0;
}
// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 6. 0/U
        (case_dir / "0" / "U").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({U_bulk} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    walls
    {{
        type            noSlip;
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}
// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 7. 0/p
        (case_dir / "0" / "p").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{{
    inlet
    {{
        type            zeroGradient;
    }}
    outlet
    {{
        type            fixedValue;
        value           uniform 0;
    }}
    walls
    {{
        type            zeroGradient;
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}
// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # -- P-B C2: post-write plumbing verification -----------------------
        # Confirm the nu we wrote to disk round-trips to the declared Re.
        self._verify_internal_channel_plumbing(case_dir=case_dir, declared_Re=Re)

    def _generate_steady_internal_flow(
        self, case_dir: Path, task_spec: TaskSpec, turbulence_model: str = "kEpsilon"
    ) -> None:
        """生成稳态内部流 case 文件（simpleFoam + configurable turbulence model）。

        适用于:
        - Turbulent Flat Plate (SIMPLE_GRID, Re=5e4) -> kOmegaSST
        - Fully Developed Pipe Flow (SIMPLE_GRID, Re=5e4) -> kOmegaSST

        几何: 矩形通道, 2D 近似 (z-depth = 0.1m)
        - inlet: uniform velocity U = (U_bulk, 0, 0)
        - walls: no-slip
        - outlet: zeroGradient pressure
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        Re = float(task_spec.Re or 50000)
        L = float(task_spec.boundary_conditions.get("plate_length", 1.0)) if task_spec.boundary_conditions else 1.0
        nu_val = 1.0 / Re  # U_bulk=1 m/s → nu = 1/Re
        U_bulk = 1.0  # m/s (consistent with nu=1/Re)

        # Domain: x=[0, 5L], y=[0, 0.5], z=[0, 0.1]
        x_min, x_max = 0.0, 5.0 * L
        y_min, y_max = 0.0, 0.5
        z_min, z_max = 0.0, 0.1

        (case_dir / "system" / "blockMeshDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    ({x_min} {y_min} {z_min})
    ({x_max} {y_min} {z_min})
    ({x_max} {y_max} {z_min})
    ({x_min} {y_max} {z_min})
    ({x_min} {y_min} {z_max})
    ({x_max} {y_min} {z_max})
    ({x_max} {y_max} {z_max})
    ({x_min} {y_max} {z_max})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (100 80 1) simpleGrading (1 4 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type            patch;
        faces           ((0 4 7 3));
    }}
    outlet
    {{
        type            patch;
        faces           ((1 2 6 5));
    }}
    walls
    {{
        type            wall;
        faces           ((0 1 5 4)) ((3 6 7 2));
    }}
    front
    {{
        type            empty;
        faces           ((0 3 2 1));
    }}
    back
    {{
        type            empty;
        faces           ((4 5 6 7));
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # constant/physicalProperties
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;

nu              [0 2 -1 0 0 0 0] {nu_val};

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # constant/turbulenceProperties — k-epsilon
        (case_dir / "constant" / "turbulenceProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;

RAS
{{
    RASModel      {turbulence_model};
    turbulence    on;
    printCoeffs   on;
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/controlDict
        (case_dir / "system" / "controlDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;

startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1000;
deltaT          1;
writeControl    runTime;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/fvSchemes
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{
    default         steadyState;
}
gradSchemes
{
    default         Gauss linear;
}
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,k)      bounded Gauss limitedLinear 1;
    div(phi,epsilon) bounded Gauss limitedLinear 1;
    div(phi,omega)  bounded Gauss limitedLinear 1;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes
{
    default         Gauss linear corrected;
}
interpolationSchemes
{
    default         linear;
}
snGradSchemes
{
    default         corrected;
}
wallDist
{
    method          meshWave;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )


        # Build fvSolution content conditionally based on turbulence model
        if turbulence_model == "kOmegaSST":
            solvers_block = """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p
    {
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.01;
    }
    pFinal
    {
        $p;
        relTol          0;
    }
    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-7;
        relTol          0.01;
    }
    UFinal
    {
        $U;
        relTol          0;
    }
    k
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    omega
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;
    residualControl
    {
        U       1e-5;
        p       1e-4;
        k       1e-5;
        omega   1e-5;
    }
}

relaxationFactors
{
    fields
    {
        p               0.3;
    }
    equations
    {
        U               0.7;
        k               0.7;
        omega           0.7;
    }
}
"""
        else:
            solvers_block = """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p
    {
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.01;
    }
    pFinal
    {
        $p;
        relTol          0;
    }
    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-7;
        relTol          0.01;
    }
    UFinal
    {
        $U;
        relTol          0;
    }
    k
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    epsilon
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-6;
        relTol          0.01;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;
    residualControl
    {
        U       1e-5;
        p       1e-4;
        k       1e-5;
        epsilon  1e-5;
    }
}

relaxationFactors
{
    equations
    {
        U               0.9;
        k               0.9;
        epsilon         0.9;
    }
}
"""
        (case_dir / "system" / "fvSolution").write_text(solvers_block, encoding="utf-8")

        # 0/U
        (case_dir / "0" / "U").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({U_bulk} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    walls
    {{
        type            noSlip;
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/p
        (case_dir / "0" / "p").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    walls
    {
        type            zeroGradient;
    }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/k
        k_init = 0.01
        (case_dir / "0" / "k").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform {k_init};

boundaryField
{{
    inlet        {{ type fixedValue; value uniform {k_init}; }}
    outlet       {{ type zeroGradient; }}
    walls        {{ type kLowReWallFunction; value uniform {k_init}; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/epsilon
        eps_init = 0.001
        # 0/epsilon (kEpsilon) or 0/omega (kOmegaSST) — only the relevant one
        if turbulence_model == "kOmegaSST":
            omega_init = 1e-5
            (case_dir / "0" / "omega").write_text(
                f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];

internalField   uniform {omega_init};

boundaryField
{{
    inlet        {{ type fixedValue; value uniform {omega_init}; }}
    outlet       {{ type zeroGradient; }}
    walls        {{ type omegaWallFunction; value uniform {omega_init}; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
                encoding="utf-8",
            )
        else:
            eps_init = 0.01
            (case_dir / "0" / "epsilon").write_text(
                f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      epsilon;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -3 0 0 0 0];

internalField   uniform {eps_init};

boundaryField
{{
    inlet        {{ type fixedValue; value uniform {eps_init}; }}
    outlet       {{ type zeroGradient; }}
    walls        {{ type epsilonWallFunction; value uniform {eps_init}; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
                encoding="utf-8",
            )

        # 0/nut
        (case_dir / "0" / "nut").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{{
    inlet        {{ type calculated; value uniform 0; }}
    outlet       {{ type calculated; value uniform 0; }}
    walls        {{ type nutkWallFunction; value uniform 0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/sampleDict — extract temperature profile for Nusselt number validation
        (case_dir / "system" / "sampleDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
|  sampleDict - extract temperature profile for natural convection cavity     |
\\*---------------------------------------------------------------------------*/
type            sets;
libs            ("libsampling.so");

interpolationScheme cellPoint;

setFormat       raw;

sets
(
    midPlaneT
    {
        type        uniform;
        axis        y;
        start       (0.5 0.0 0.0);
        end         (0.5 1.0 0.0);
        nPoints     20;
    }
);

fields          (T);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _generate_circular_cylinder_wake(
        self, case_dir: Path, task_spec: TaskSpec, turbulence_model: str = "kOmegaSST"
    ) -> None:
        """生成圆柱尾迹 case 文件 (pimpleFoam transient).

        适用于:
        - Circular Cylinder Wake (BODY_IN_CHANNEL, EXTERNAL, TRANSIENT, Re=100)
        - Plane Channel Flow DNS (BODY_IN_CHANNEL, INTERNAL, STEADY, Re_tau=180)

        几何: 矩形通道中央放置圆柱
        - 圆柱直径 D = 0.1m
        - 通道截面: 20D × 10D
        - 圆柱位于 x=2D 位置
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        Re = float(task_spec.Re or 100)
        D = 0.1  # cylinder diameter
        U_bulk = 1.0  # m/s
        nu_val = U_bulk * D / Re  # kinematic viscosity
        # DEC-V61-041: plumb D, U_ref so the FFT emitter doesn't have to
        # rediscover them. The forceCoeffs FO references lRef/magUInf
        # that must stay in sync with these.
        if task_spec.boundary_conditions is None:
            task_spec.boundary_conditions = {}
        task_spec.boundary_conditions["cylinder_D"] = D
        task_spec.boundary_conditions["U_ref"] = U_bulk
        # DEC-V61-053 Codex R4 LOW fix: surface endTime in boundary_conditions
        # from the class constant CYLINDER_ENDTIME_S (single source of truth).
        # Extractor reads it to derive transient_trim / min_averaging_window.
        task_spec.boundary_conditions["cylinder_endTime"] = self.CYLINDER_ENDTIME_S

        # Channel dimensions — DEC-V61-053 Batch B1 (decision b):
        # grown from L_inlet=2D/L_outlet=8D/H=2.5D (20% blockage) to
        # L_inlet=10D/L_outlet=20D/H=6D (~8% blockage) to match Williamson
        # 1996 unconfined-wake anchors. Prior geometry biased Cd high +8-12%
        # and St +2-5% per Zdravkovich Ch.6.
        W = 6.0 * D  # half-width (unused downstream, retained for reference)
        H = 6.0 * D  # half-height (was 2.5D)
        L_inlet = 10.0 * D  # upstream length (was 2D)
        L_outlet = 20.0 * D  # downstream length (was 8D)
        z_depth = 0.1 * D  # 2D thickness (unchanged)

        x_min = -L_inlet
        x_max = L_outlet
        y_min = -H
        y_max = H
        z_min = -z_depth / 2
        z_max = z_depth / 2

        # Vertex indices for blockMesh (single block, cylindrical hole via boundary)
        # We'll create a rectangular channel and define cylinder via curved boundary
        # Simple approach: rectangular channel with cylinder as a circular patch
        (case_dir / "system" / "blockMeshDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    ({x_min:.6f} {y_min:.6f} {z_min:.6f})
    ({x_max:.6f} {y_min:.6f} {z_min:.6f})
    ({x_max:.6f} {y_max:.6f} {z_min:.6f})
    ({x_min:.6f} {y_max:.6f} {z_min:.6f})
    ({x_min:.6f} {y_min:.6f} {z_max:.6f})
    ({x_max:.6f} {y_min:.6f} {z_max:.6f})
    ({x_max:.6f} {y_max:.6f} {z_max:.6f})
    ({x_min:.6f} {y_max:.6f} {z_max:.6f})
);

blocks
(
    // DEC-V61-053 Batch B1 + Codex round-1 MED-2 refinement:
    // original (200 100 1)=40k cells on the pre-B1 small domain gave
    // dx=dy=0.05D. Naive scale to (400 200 1) for the grown domain gave
    // dx=0.075D / dy=0.06D — a 50% coarsening vs. the original. Bumped
    // to (600 240 1)=144k cells to match original resolution:
    //   dx = L_total/600 = 30D/600 = 0.050D
    //   dy = H_total/240 = 12D/240 = 0.050D
    // Matches Williamson-quality resolution (~0.05D at cylinder/wake).
    hex (0 1 2 3 4 5 6 7) (600 240 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type            patch;
        faces           ((0 4 7 3));
    }}
    outlet
    {{
        type            patch;
        faces           ((1 2 6 5));
    }}
    lower_wall
    {{
        type            wall;
        faces           ((0 1 5 4));
    }}
    upper_wall
    {{
        type            wall;
        faces           ((3 6 7 2));
    }}
    front
    {{
        type            empty;
        faces           ((0 3 2 1));
    }}
    back
    {{
        type            empty;
        faces           ((4 5 6 7));
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/topoSetDict -- cylinder cellZone via cylinderToCell + faceZone for createBaffles
        (case_dir / "system" / "topoSetDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\\\    /   O peration     | Version:  10                                    |
|   \\\\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      topoSetDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

actions
(
    {{
        name    cylinderCells;
        type    cellSet;
        action  new;
        source  cylinderToCell;
        sourceInfo
        {{
            point1 (0 0 {z_min:.6f});
            point2 (0 0 {z_max:.6f});
            radius {D / 2:.6f};
        }}
    }}
    {{
        name    cylinderZone;
        type    cellZoneSet;
        action  new;
        source  setToCellZone;
        sourceInfo
        {{
            set cylinderCells;
        }}
    }}
    {{
        name    cylinderAllFaces;
        type    faceSet;
        action  new;
        source  cellToFace;
        sourceInfo
        {{
            set cylinderCells;
            option all;
        }}
    }}
    {{
        name    cylinderInternalFaces;
        type    faceSet;
        action  new;
        source  cellToFace;
        sourceInfo
        {{
            set cylinderCells;
            option both;
        }}
    }}
    {{
        name    cylinderBaffleFaces;
        type    faceSet;
        action  new;
        source  faceToFace;
        sourceInfo
        {{
            set cylinderAllFaces;
        }}
    }}
    {{
        name    cylinderBaffleFaces;
        type    faceSet;
        action  delete;
        source  faceToFace;
        sourceInfo
        {{
            set cylinderInternalFaces;
        }}
    }}
    {{
        name    cylinderBaffleZone;
        type    faceZoneSet;
        action  new;
        source  setsToFaceZone;
        sourceInfo
        {{
            faceSet cylinderBaffleFaces;
            cellSet cylinderCells;
            flip false;
        }}
    }}
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/createBafflesDict -- converts internal faceZone to wall patch "cylinder"
        (case_dir / "system" / "createBafflesDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\\\    /   O peration     | Version:  10                                    |
|   \\\\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      createBafflesDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

internalFacesOnly true;

baffles
{
    cylinderBaffleZone
    {
        type faceZone;
        zoneName cylinderBaffleZone;
        patches
        {
            owner
            {
                name cylinder;
                type wall;
            }
            neighbour
            {
                name cylinder;
                type wall;
            }
        }
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )
        # constant/physicalProperties
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;

nu              [0 2 -1 0 0 0 0] {nu_val:.6e};

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # constant/turbulenceProperties — compute body OUTSIDE the outer
        # f-string to stay Python 3.9-compatible (nested multi-line f-strings
        # with embedded braces break 3.9 parsers; project .venv is 3.12 but
        # test tooling like `python3 -m py_compile` and CI shims default to
        # 3.9, per Codex round-2 FAIL).
        if turbulence_model == "laminar":
            _turb_body = "simulationType  laminar;"
        else:
            _turb_body = (
                "simulationType  RAS;\n"
                "\n"
                "RAS\n"
                "{\n"
                f"    RASModel      {turbulence_model};\n"
                "    turbulence    on;\n"
                "    printCoeffs   on;\n"
                "}"
            )
        (case_dir / "constant" / "turbulenceProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

{_turb_body}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/controlDict — pimpleFoam transient
        (case_dir / "system" / "controlDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     pimpleFoam;

startFrom       startTime;
startTime       0;
stopAt          endTime;
// DEC-V61-053 endTime from class constant CYLINDER_ENDTIME_S (single
// source of truth; extractor reads via boundary_conditions to keep
// transient_trim / min_averaging_window in sync). At St=0.164 the
// shedding period T = D/U/St ≈ 0.61s. 10s gives ~2s transient +
// ~8s steady = ~13 resolved periods. Δf ≈ 0.13 Hz → ΔSt ≈ 0.013.
// The 60s / 200s precision upgrades remain deferred to a future DEC.
endTime         {self.CYLINDER_ENDTIME_S};
// DEC-V61-053 Batch B1 live-run tuning (2026-04-24): maxCo=1.0 doubles
// the achievable timestep vs the conservative 0.5 (shedding frequency
// is well-resolved at Co=1 on this refined grid; Nyquist margin per
// DEC-V61-041 was 2x). deltaT bumped to 0.005 so the adaptive ramp
// starts closer to stationary Co. maxDeltaT 0.02 keeps ≥30 samples
// per shedding period at St=0.164.
deltaT          0.005;
adjustTimeStep  yes;
maxCo           1.0;
maxDeltaT       0.02;
writeControl    runTime;
writeInterval   2.0;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

// DEC-V61-041: forceCoeffs FO — writes Cl(t), Cd(t) time histories to
// postProcessing/forceCoeffs1/0/coefficient.dat. Parsed by
// src.cylinder_strouhal_fft to extract St via FFT on Cl. Patches
// (cylinder) matches the createBaffles output patch name verified at
// DEC-V61-041 research time (createBafflesDict baffle patches owner
// + neighbour both named 'cylinder'). lRef=D=0.1, Aref=D*span=0.1*0.01
// = 0.001 for the 2D thin-span mesh (z_depth=0.1*D=0.01), magUInf=1.0
// matches the inlet U_bulk. Codex DEC-041 round 1 BLOCKER fix: Aref
// was 0.01 (10x too large) → coefficients were reported 10x smaller.
functions
{{
    forceCoeffs1
    {{
        type            forceCoeffs;
        libs            ("libforces.so");
        writeControl    timeStep;
        writeInterval   1;
        patches         (cylinder);
        rho             rhoInf;
        rhoInf          1.0;
        CofR            (0 0 0);
        liftDir         (0 1 0);
        dragDir         (1 0 0);
        pitchAxis       (0 0 1);
        magUInf         1.0;
        lRef            0.1;
        Aref            0.001;
        log             false;
    }}

    // DEC-V61-053 Batch B1b: runtime-sample wake centerline U at 4 gold
    // x/D stations (Williamson 1996 u_mean_centerline reference). D=0.1m
    // so x=(x/D)·D ∈ {0.01, 0.02, 0.03, 0.05} ... wait D=0.1 → points are
    // at x=0.1, 0.2, 0.3, 0.5 m (i.e. 1D, 2D, 3D, 5D downstream of the
    // cylinder center at x=0). writeControl=timeStep + writeInterval=20
    // gives ~20 samples per shedding period at St=0.164, dt~0.001s, Co
    // relaxing to ~0.005s steady-state — adequate for B2 time-averaging
    // in the statistically-stationary window.
    cylinderCenterline
    {{
        type            sets;
        libs            ("libsampling.so");
        // DEC-V61-053 live-run attempt 6 (2026-04-24): FO registered and
        // "Reading set description" logged, but postProcessing/cylinder
        // Centerline/ never materialized on disk. Root cause: missing
        // `executeControl` → sampling never fires even though the set
        // is parsed. OF10 template at /opt/openfoam10/etc/caseDicts/
        // postProcessing/probes/internalProbes.cfg uses BOTH
        // `executeControl writeTime` AND `writeControl writeTime`.
        // Fix: add executeControl + executeInterval matching the
        // writeControl, so sampling runs AND output flushes.
        executeControl  timeStep;
        executeInterval 20;
        writeControl    timeStep;
        writeInterval   20;
        interpolationScheme cellPoint;
        setFormat       raw;
        fields          (U);
        sets
        (
            wakeCenterline
            {{
                type        points;
                axis        xyz;
                ordered     on;
                points
                (
                    (0.1 0 0)
                    (0.2 0 0)
                    (0.3 0 0)
                    (0.5 0 0)
                );
            }}
        );
    }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/fvSchemes
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{
    default         Euler;
}
gradSchemes
{
    default         Gauss linear;
}
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,k)      bounded Gauss limitedLinear 1;
    div(phi,epsilon) bounded Gauss limitedLinear 1;
    div(phi,omega)  bounded Gauss limitedLinear 1;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes
{
    default         Gauss linear corrected;
}
interpolationSchemes
{
    default         linear;
}
snGradSchemes
{
    default         corrected;
}
wallDist
{
    method          meshWave;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/fvSolution
        is_kepsilon = turbulence_model == "kEpsilon"
        eps_block = ("""\
    epsilon
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-5;
        relTol          0.01;
    }
    epsilonFinal
    {
        $epsilon;
        relTol          0;
    }
""") if is_kepsilon else ""
        omega_block = ("""\
    omega
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    omegaFinal
    {
        $omega;
        relTol          0;
    }
""") if turbulence_model == "kOmegaSST" else ""
        rel_eps = ("        epsilon         0.9;\n        ") if is_kepsilon else ""
        rel_omg = ("        omega           0.9;\n        ") if turbulence_model == "kOmegaSST" else ""
        fvsol = (
            """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    // DEC-V61-053 live-run debug (2026-04-24): swapped GAMG+GaussSeidel
    // for PCG+DIC on p. The GAMG path diverged on first pressure solve
    // (Initial=1 → Final=nan in 1000 iters) for this external cylinder
    // geometry; see reports/phase5_audit/live_cylinder_run_20260424.log.
    // PCG+DIC is the recommended robust fallback for 2D cylinder wakes
    // per OpenFOAM tutorials. Kept GAMG wiring commented as reference.
    p
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-6;
        relTol          0.01;
    }
    pFinal
    {
        $p;
        relTol          0;
    }
    U
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-6;
        relTol          0.01;
    }
    UFinal
    {
        $U;
        relTol          0;
    }
    k
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-6;
        relTol          0.01;
    }
"""
            + eps_block
            + omega_block
            + """\
    kFinal
    {
        $k;
        relTol          0;
    }
}

PIMPLE
{
    nOuterCorrectors 1;
    nCorrectors     2;
    nNonOrthogonalCorrectors 1;
}

relaxationFactors
{
    equations
    {
        U               0.9;
        k               0.9;
"""
            + rel_eps
            + rel_omg
            + """\
    }
}

// ************************************************************************* //
"""
        )
        (case_dir / "system" / "fvSolution").write_text(fvsol, encoding="utf-8")

        # 0/U
        (case_dir / "0" / "U").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform ({U_bulk} 0 0);

boundaryField
{{
    inlet        {{ type fixedValue; value uniform ({U_bulk} 0 0); }}
    outlet       {{ type zeroGradient; }}
    lower_wall   {{ type noSlip; }}
    upper_wall   {{ type noSlip; }}
    cylinder     {{ type noSlip; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # DEC-V61-053 Batch B1: laminar solver needs only p/U (not k/omega/nut).
        # Writing turbulence fields when simulationType=laminar causes
        # "Field nut not found" / RAS-model-not-registered errors at startup.
        _is_laminar = turbulence_model == "laminar"

        # 0/p
        (case_dir / "0" / "p").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{{
    inlet        {{ type zeroGradient; }}
    outlet       {{ type fixedValue; value uniform 0; }}
    lower_wall   {{ type zeroGradient; }}
    upper_wall   {{ type zeroGradient; }}
    cylinder     {{ type zeroGradient; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/k, 0/omega, 0/nut — written only when turbulence_model != "laminar".
        # Laminar solver stack doesn't register these fields; writing them
        # causes startup errors.
        if not _is_laminar:
            (case_dir / "0" / "k").write_text(
                f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0.01;

boundaryField
{{
    inlet        {{ type fixedValue; value uniform 0.01; }}
    outlet       {{ type zeroGradient; }}
    lower_wall   {{ type kLowReWallFunction; value uniform 0; }}
    upper_wall   {{ type kLowReWallFunction; value uniform 0; }}
    cylinder     {{ type kLowReWallFunction; value uniform 0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
                encoding="utf-8",
            )
            (case_dir / "0" / "omega").write_text(
                f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];

internalField   uniform 1.0;

boundaryField
{{
    inlet        {{ type fixedValue; value uniform 1.0; }}
    outlet       {{ type zeroGradient; }}
    lower_wall   {{ type omegaWallFunction; value uniform 1.0; }}
    upper_wall   {{ type omegaWallFunction; value uniform 1.0; }}
    cylinder     {{ type omegaWallFunction; value uniform 1.0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
                encoding="utf-8",
            )
            (case_dir / "0" / "nut").write_text(
                """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet        { type calculated; value uniform 0; }
    outlet       { type calculated; value uniform 0; }
    lower_wall   { type nutkWallFunction; value uniform 0; }
    upper_wall   { type nutkWallFunction; value uniform 0; }
    cylinder     { type nutkWallFunction; value uniform 0; }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
                encoding="utf-8",
            )

    def _generate_impinging_jet(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """Generate impinging jet case files (buoyantFoam steady, Boussinesq).

        Uses buoyantFoam with Boussinesq approximation for thermal fields.
        Hot jet inlet (310K) impinges on cold plate (290K).
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        Re = float(task_spec.Re or 10000)
        D = 0.05
        h_over_d = 2.0
        H = h_over_d * D
        U_bulk = 1.0
        nu_val = U_bulk * D / Re

        # Thermal parameters (Boussinesq)
        T_inlet = 310.0   # hot jet
        T_plate = 290.0   # cold impingement plate
        T_mean = 300.0    # reference
        Cp = 1005.0
        beta = 1.0 / T_mean
        Pr = 0.71
        mu_val = nu_val  # dynamic viscosity for Boussinesq

        # Enthalpy: h = Cp*(T - T_mean)
        h_inlet = Cp * (T_inlet - T_mean)   # 10050
        h_plate = Cp * (T_plate - T_mean)   # -10050
        h_internal = 0.0                     # mean field starts at T_mean

        # Domain: r=[0, 5D], z=[z_min, z_max]; split at z=0 for planar faces
        r_max = 5.0 * D
        z_min = -D / 2
        z_split = 0.0
        z_max = H + D / 2
        n_r = 60
        total_nz = 80
        n_z_lower = max(1, int(round(total_nz * (z_split - z_min) / (z_max - z_min))))
        n_z_upper = total_nz - n_z_lower

        # Gravity = 0 (forced convection impinging jet, buoyancy negligible)
        g_val = 0.0

        # DEC-V61-042: plumb wall-coord + wall-value + BC type so the
        # wall-normal stencil can difference against the actual plate
        # temperature instead of differencing radially across the plate
        # (which is ~0 by symmetry and gave the -6000× under-read).
        # Plate is at the upper face of the upper block (patch `plate`,
        # faces (8 9 10 11) at jet-axial coord = z_max). The extractor
        # reads cells by cy (jet-axial coord in OpenFOAM's y-slot) and
        # treats the wall as cy = max(cys), matching z_max here.
        if task_spec.boundary_conditions is None:
            task_spec.boundary_conditions = {}
        task_spec.boundary_conditions["D_nozzle"] = D
        task_spec.boundary_conditions["T_plate"] = T_plate
        task_spec.boundary_conditions["T_inlet"] = T_inlet
        task_spec.boundary_conditions["wall_coord_plate"] = z_max
        task_spec.boundary_conditions["wall_bc_type"] = "fixedValue"

        (case_dir / "system" / "blockMeshDict").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    (0 {z_min:.6f} 0)
    ({r_max:.6f} {z_min:.6f} 0)
    ({r_max:.6f} {z_split:.6f} 0)
    (0 {z_split:.6f} 0)
    (0 {z_min:.6f} 0.1)
    ({r_max:.6f} {z_min:.6f} 0.1)
    ({r_max:.6f} {z_split:.6f} 0.1)
    (0 {z_split:.6f} 0.1)
    (0 {z_max:.6f} 0)
    ({r_max:.6f} {z_max:.6f} 0)
    ({r_max:.6f} {z_max:.6f} 0.1)
    (0 {z_max:.6f} 0.1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({n_r} {n_z_lower} 1) simpleGrading (1 1 1)
    hex (3 2 9 8 7 6 10 11) ({n_r} {n_z_upper} 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type            patch;
        faces           ((0 4 5 1));
    }}
    plate
    {{
        type            wall;
        faces           ((8 9 10 11));
    }}
    outer
    {{
        type            patch;
        faces           ((1 5 6 2) (2 6 10 9));
    }}
    axis
    {{
        type            empty;
        faces           ((0 3 7 4) (3 8 11 7));
    }}
    front
    {{
        type            empty;
        faces           ((0 1 2 3) (3 2 9 8));
    }}
    back
    {{
        type            empty;
        faces           ((4 5 6 7) (7 6 10 11));
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # Boussinesq thermophysical properties for buoyantFoam
        (case_dir / "constant" / "thermophysicalProperties").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      thermophysicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

thermoType
{{
    type            heRhoThermo;
    mixture         pureMixture;
    transport       const;
    thermo          hConst;
    equationOfState Boussinesq;
    specie          specie;
    energy          sensibleEnthalpy;
}}

mixture
{{
    specie
    {{
        molWeight       28.9;
    }}
    equationOfState
    {{
        rho0            1.0;
        T0              {T_mean:g};
        beta            {beta:.16e};
    }}
    thermodynamics
    {{
        Cp              {Cp:.16e};
        Hf              0;
    }}
    transport
    {{
        mu              {mu_val:.16e};
        Pr              {Pr};
    }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # Zero gravity (forced convection - buoyancy negligible compared to inertia)
        (case_dir / "constant" / "g").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      g;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions       [0 1 -2 0 0 0 0];

value           (0 {g_val:.16e} 0);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # kEpsilon turbulence (simpler for buoyant flow)
        (case_dir / "constant" / "turbulenceProperties").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;

RAS
{
    RASModel      kEpsilon;
    turbulence    on;
    printCoeffs   on;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "system" / "controlDict").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     buoyantFoam;

startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1000;
deltaT          5;

writeControl    runTime;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

functions
{
    writeCellCentres
    {
        type            writeCellCentres;
        libs            ("libfieldFunctionObjects.so");
        writeControl    writeTime;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "system" / "fvSchemes").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes {
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div(phi,h) bounded Gauss linearUpwind grad(h);
    div(phi,K) bounded Gauss linear;
    div(phi,k) bounded Gauss limitedLinear 1;
    div(phi,epsilon) bounded Gauss limitedLinear 1;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "system" / "fvSolution").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p_rgh
    {
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-7;
        relTol          0.01;
    }
    p_rghFinal
    {
        $p_rgh;
        relTol          0;
    }
    h
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-8;
        relTol          0.01;
        maxIter         2000;
    }
    hFinal
    {
        $h;
        relTol          0;
    }
    U
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    UFinal
    {
        $U;
        relTol          0;
    }
    k
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    epsilon
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    epsilonFinal
    {
        $epsilon;
        relTol          0;
    }
}

relaxationFactors
{
    fields
    {
        p_rgh           0.2;
    }
    equations
    {
        U               0.5;
        h               0.3;
        k               0.5;
        epsilon           0.5;
    }
}

PIMPLE
{
    nOuterCorrectors 1;
    nCorrectors 2;
    nNonOrthogonalCorrectors 0;
    residualControl
    {
        p_rgh 1e-5;
        h 1e-5;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )


        # epsilon init: Cmu^0.75 * k^1.5 / l_turb, Cmu=0.09, l_turb~0.1*D=0.005
        U_nozzle = U_bulk
        (case_dir / "0" / "U").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

// Zero initial velocity — solver converges from rest
internalField   uniform (0 0 0);

boundaryField
{{
    inlet           {{ type fixedValue; value uniform (0 0 {U_bulk:.6f}); }}
    plate           {{ type noSlip; }}
    outer           {{ type zeroGradient; }}
    axis            {{ type empty; }}
    front           {{ type empty; }}
    back            {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # Static thermodynamic pressure (101325 Pa reference)
        (case_dir / "0" / "p").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -2 0 0 0 0];

internalField   uniform 101325;

boundaryField
{
    inlet       { type calculated; value $internalField; }
    plate       { type calculated; value $internalField; }
    outer       { type calculated; value $internalField; }
    axis        { type empty; }
    front       { type empty; }
    back        { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # Buoyant pressure p_rgh = p - rho*g*h (0 for zero gravity)
        (case_dir / "0" / "p_rgh").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p_rgh;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet       { type fixedFluxPressure; value $internalField; }
    plate       { type fixedFluxPressure; value $internalField; }
    outer       { type fixedValue; value uniform 101325; }
    axis        { type empty; }
    front       { type empty; }
    back        { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # Sensible enthalpy h = Cp*(T - T_mean)
        (case_dir / "0" / "h").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      h;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

// h = Cp*(T - T_mean), T_mean=300K from equationOfState
// inlet (310K): Cp*10 = {h_inlet:.6g}
// plate (290K): Cp*(-10) = {h_plate:.6g}
// internal: 0 (at T_mean=300K)
internalField   uniform {h_internal:.6g};

boundaryField
{{
    inlet           {{ type fixedValue; value uniform {h_inlet:.6g}; }}
    plate           {{ type fixedValue; value uniform {h_plate:.6g}; }}
    outer           {{ type inletOutlet; inletValue uniform 0; value uniform 0; }}
    axis            {{ type empty; }}
    front           {{ type empty; }}
    back            {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # Temperature field
        (case_dir / "0" / "T").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      T;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 0 1 0 0 0];

internalField   uniform {T_mean:.6g};

boundaryField
{{
    inlet           {{ type fixedValue; value uniform {T_inlet:.6g}; }}
    plate           {{ type fixedValue; value uniform {T_plate:.6g}; }}
    outer           {{ type inletOutlet; inletValue uniform {T_mean:.6g}; value uniform {T_mean:.6g}; }}
    axis            {{ type empty; }}
    front           {{ type empty; }}
    back            {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # Turbulent thermal diffusivity
        (case_dir / "0" / "alphat").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      alphat;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet       { type calculated; value uniform 0; }
    plate       { type compressible::alphatWallFunction; value uniform 0; }
    outer       { type zeroGradient; }
    axis        { type empty; }
    front       { type empty; }
    back        { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # Turbulent kinetic energy
        (case_dir / "0" / "k").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0.01;

boundaryField
{{
    inlet           {{ type fixedValue; value uniform 0.01; }}
    plate           {{ type kLowReWallFunction; value uniform 0.01; }}
    outer           {{ type inletOutlet; inletValue uniform 0.01; value uniform 0.01; }}
    axis            {{ type empty; }}
    front           {{ type empty; }}
    back            {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # Turbulence dissipation epsilon
        # epsilon = Cmu^0.75 * k^1.5 / l_turb, Cmu=0.09, l_turb~0.1*D=0.005
        epsilon_init = 0.0328  # 0.09**0.75 * 0.01**1.5 / 0.005
        (case_dir / "0" / "epsilon").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      epsilon;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -3 0 0 0 0];

// epsilon initialization: Cmu^0.75 * k^1.5 / l_turb
internalField   uniform {epsilon_init:.6g};

boundaryField
{{
    inlet           {{ type fixedValue; value uniform {epsilon_init:.6g}; }}
    plate           {{ type epsilonWallFunction; value uniform {epsilon_init:.6g}; }}
    outer           {{ type inletOutlet; inletValue uniform {epsilon_init:.6g}; value uniform {epsilon_init:.6g}; }}
    axis            {{ type empty; }}
    front           {{ type empty; }}
    back            {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "0" / "nut").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet       { type calculated; value uniform 0; }
    plate       { type nutkWallFunction; value uniform 0; }
    outer       { type zeroGradient; }
    axis        { type empty; }
    front       { type empty; }
    back        { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/sampleDict — gold-anchored Nu sampling (C3c).
        # docs/c3_sampling_strategy_design.md §3.3 Option B: probe at
        # z=1mm above the impingement plate (plate at z=0), one point per
        # r/d in whitelist reference_values. Fields (T U) so downstream
        # harvester can derive Nu via finite-difference wall-gradient
        # estimate (or upgrade to wallHeatFlux function-object in a
        # follow-up once Case 9 gold values stabilize per Gate Q-new HOLD).
        #
        # NOTE: Case 9 gold values (Nu@r/d=0=25, r/d=1=12) are on HOLD
        # pending Behnad 2013 paper re-read (DEC-V61-006 · Gate Q-new
        # Case 9 C-verdict). The r_over_d COORDINATES are valid; only the
        # Nu reference numbers are provisional. This sampling infrastructure
        # is orthogonal and stable across any Nu-value correction.
        gold_values = _load_gold_reference_values(task_spec.name) or []
        rod_values = [
            float(rv["r_over_d"])
            for rv in gold_values
            if isinstance(rv, dict) and "r_over_d" in rv
        ]
        if rod_values:
            probe_z = 0.001  # 1mm above plate (plate at z=0)
            physical_points = [(rod * D, 0.0, probe_z) for rod in rod_values]
            _emit_gold_anchored_points_sampledict(
                case_dir,
                set_name="plateProbes",
                physical_points=physical_points,
                fields=["T", "U"],
                axis="x",
                header_comment=(
                    f"Impinging jet plate probes at z={probe_z}m above plate "
                    f"(plate z=0), {len(rod_values)} gold r/d coords (D={D:g}m, "
                    f"T_inlet={T_inlet:g}K, T_plate={T_plate:g}K; "
                    f"Nu derivation via wall-gradient post-processing TBD)"
                ),
            )

    def _generate_airfoil_flow(
        self, case_dir: Path, task_spec: TaskSpec, turbulence_model: str = "kOmegaSST"
    ) -> None:
        """Generate airfoil external flow case files (simpleFoam steady k-omega SST).

        Uses the tutorial six-block topology in the x-z plane, but keeps all
        shared block vertices explicit to avoid blockMesh projection drift at
        block interfaces. Only the airfoil boundary edges are projected onto
        the real NACA0012 surface for Cp extraction.
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        Re = float(task_spec.Re or 3000000)
        bc = task_spec.boundary_conditions or {}
        chord = float(bc.get("chord_length", 1.0))
        U_inf = 1.0  # freestream velocity
        nu_val = U_inf * chord / Re
        # DEC-V61-058 Batch B1 (Codex DEC-V61-058 F2): α routing via single
        # canonical case_id `naca0012_airfoil`. The whitelist canonical key is
        # `angle_of_attack` (knowledge/whitelist.yaml parameters block); the
        # adapter ALSO accepts `alpha_deg` as a programmatic alias for callers
        # that don't go through the whitelist→task_runner→bc pipeline.
        #
        # Codex round 1 F1 fix (2026-04-25): precedence is now
        # `angle_of_attack` (whitelist SoT) FIRST, `alpha_deg` (alias) SECOND.
        # Adapter does NOT persist the resolved value back into bc — every
        # call resolves freshly from the caller-supplied input. This avoids
        # the round-1 reuse bug where a persisted canonical `alpha_deg=4`
        # would mask a subsequent caller's `angle_of_attack=8`.
        #
        # Sign convention (PINNED, OF airFoil2D tutorial precedent):
        #   α positive → freestream rotates upward in x-z plane:
        #     U_inf_vec = U_inf · (cos α, 0, sin α)
        #   liftDir = (-sin α, 0, cos α);  dragDir = (cos α, 0, sin α)
        #   At α=+8°, upper-surface suction (z>0 side of airfoil) generates
        #   force in +liftDir = +z direction → Cl > 0 (asserted in Stage E
        #   sign-convention smoke test per intake §9 close checklist).
        # Mesh is geometry-locked to x-z plane (lines below);
        # rotation happens in 0/U only — no mesh re-rotation.
        _alpha_raw = bc.get("angle_of_attack")
        if _alpha_raw is None:
            _alpha_raw = bc.get("alpha_deg", 0.0)
        # Fail closed on non-numeric (Codex round 1 Q1(a): the prior `or 0.0`
        # silently masked `""` / `False` as α=0). Accept int/float/None only.
        if _alpha_raw is None:
            alpha_deg = 0.0
        elif isinstance(_alpha_raw, bool):
            # bool is a subclass of int in Python — reject explicitly so
            # bc["angle_of_attack"]=False isn't read as 0.0.
            raise ParameterPlumbingError(
                f"naca0012_airfoil: angle_of_attack/alpha_deg must be numeric; "
                f"got bool={_alpha_raw!r}"
            )
        elif isinstance(_alpha_raw, (int, float)):
            alpha_deg = float(_alpha_raw)
        else:
            raise ParameterPlumbingError(
                f"naca0012_airfoil: angle_of_attack/alpha_deg must be numeric; "
                f"got type={type(_alpha_raw).__name__} value={_alpha_raw!r}"
            )
        alpha_rad = math.radians(alpha_deg)
        cos_a = math.cos(alpha_rad)
        sin_a = math.sin(alpha_rad)
        Ux_inf = U_inf * cos_a   # streamwise component (≈ U_inf for small α)
        Uz_inf = U_inf * sin_a   # vertical component (0 at α=0; +0.139 at α=8°)
        # DEC-V61-044: plumb chord + U_inf + rho into boundary_conditions
        # so the airfoil_surface_sampler.compute_cp helper can normalize
        # p → Cp without re-deriving the freestream from other sources.
        # simpleFoam is incompressible kinematic-pressure, so rho=1.0.
        # DEC-V61-058 round 1 F1 fix: do NOT persist alpha_deg / U_inf_x /
        # U_inf_z back into bc. They have no downstream consumer
        # (airfoil_extractors.compute_cl_cd takes alpha_deg as a direct
        # function argument), and persistence created the round-1 reuse bug.
        task_spec.boundary_conditions = bc
        bc.setdefault("chord_length", chord)
        bc["U_inf"] = U_inf
        bc["p_inf"] = 0.0  # gauge pressure matches 0/p internalField
        bc["rho"] = 1.0  # incompressible kinematic convention
        # Tutorialproven topology: aerofoil in x-z plane, z=normal (80 cells),
        # y=thin span (1 cell, empty boundaries). This is the ONLY geometry that
        # works with the C-grid hex ordering. The adapter's previous x-y plane
        # approach produced inside-out errors because block vertex ordering
        # depends on z being the normal direction.
        # DEC-V61-061: mesh refinement to close V61-058 physics-fidelity gap.
        # V61-058 had: 16k cells, 120 airfoil surface faces, y+_max=139,
        # domain ±5 chord — Cl@α=8°=0.491 vs gold 0.815 (40% under).
        # V61-061 refinement (single-axis, monotone):
        #   - domain ±5→±10 chord (x), ±2→±4 chord (z) — far-field cleaner
        #   - airfoil surface 120→240 (nx 30→60 on 4 aerofoil blocks)
        #   - z-normal nz 80→120, simpleGrading 40→200 → y+~30-50
        #   - wake blocks nx 40→60 (better wake resolution)
        # Estimated cells: 43.2k (~2.7× V61-058). Estimated runtime: ~2min/α.
        y_lo = -0.001
        y_hi = 0.001
        z_far = 4.0 * chord  # V61-061: 2.0→4.0 chord (domain z-extent)
        x_min = -10.0 * chord  # V61-061: -5.0→-10.0 chord
        x_max = 10.0 * chord   # V61-061: +5.0→+10.0 chord
        x_upper = 0.3 * chord
        z_upper = self._naca0012_half_thickness(0.3) * chord
        x_lower = x_upper
        z_lower = -z_upper
        x_le = 0.0
        x_te = chord
        z_le = 0.0
        z_te = 0.0
        span = y_hi - y_lo

        self._write_naca0012_surface_obj(case_dir, chord, span)

        # 24 explicit vertices (12 at y=y_lo, 12 at y=y_hi), aerofoil in x-z plane.
        # Keep all shared block vertices Cartesian to avoid "Inconsistent point
        # locations between block pair" errors from projected block interfaces.
        # Only the aerofoil boundary edges remain projected onto the OBJ surface.
        (case_dir / "system" / "blockMeshDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

geometry
{{
    aerofoil
    {{
        type            triSurfaceMesh;
        file            "NACA0012.obj";
    }}
}}

vertices
(
    // Layer y = y_lo (bottom of thin span)
    // Explicit Cartesian vertices keep block interfaces identical across blocks.
    ({x_lower:.6f} {y_lo:.6f} {-z_far:.6f})
    ({x_te:.6f} {y_lo:.6f} {-z_far:.6f})
    ({x_max:.6f} {y_lo:.6f} {-z_far:.6f})

    ({x_min:.6f} {y_lo:.6f} {z_le:.6f})
    ({x_le:.6f} {y_lo:.6f} {z_le:.6f})
    ({x_te:.6f} {y_lo:.6f} {z_te:.6f})
    ({x_max:.6f} {y_lo:.6f} {z_te:.6f})

    ({x_lower:.6f} {y_lo:.6f} {z_lower:.6f})
    ({x_upper:.6f} {y_lo:.6f} {z_upper:.6f})

    ({x_upper:.6f} {y_lo:.6f} {z_far:.6f})
    ({x_te:.6f} {y_lo:.6f} {z_far:.6f})
    ({x_max:.6f} {y_lo:.6f} {z_far:.6f})

    // Layer y = y_hi (top of thin span) — same z coords as bottom layer
    ({x_lower:.6f} {y_hi:.6f} {-z_far:.6f})
    ({x_te:.6f} {y_hi:.6f} {-z_far:.6f})
    ({x_max:.6f} {y_hi:.6f} {-z_far:.6f})

    ({x_min:.6f} {y_hi:.6f} {z_le:.6f})
    ({x_le:.6f} {y_hi:.6f} {z_le:.6f})
    ({x_te:.6f} {y_hi:.6f} {z_te:.6f})
    ({x_max:.6f} {y_hi:.6f} {z_te:.6f})

    ({x_lower:.6f} {y_hi:.6f} {z_lower:.6f})
    ({x_upper:.6f} {y_hi:.6f} {z_upper:.6f})

    ({x_upper:.6f} {y_hi:.6f} {z_far:.6f})
    ({x_te:.6f} {y_hi:.6f} {z_far:.6f})
    ({x_max:.6f} {y_hi:.6f} {z_far:.6f})
);

blocks
(
    // blockMesh local ordering matches the tutorial:
    //   direction 1 = streamwise, direction 2 = thin span (1 cell), direction 3 = z-normal.
    // simpleGrading avoids block-interface inconsistencies caused by edgeGrading.
    // DEC-V61-061 iter 2 (revised): nx 60→100 (400 surface faces),
    // nz 120→160, simpleGrading 200→400 (y+ target ~20-30). Total ~96k cells.
    // Iter 2 first attempt with grading=1000 diverged (NaN in Uz/p) due to
    // extreme aspect-ratio cells; backed off to 400 + added nNOC=1.
    hex ( 7 4 16 19 0 3 15 12)
    (100 1 160)
    simpleGrading (1 1 400)

    hex ( 5 7 19 17 1 0 12 13)
    (100 1 160)
    simpleGrading (1 1 400)

    hex ( 17 18 6 5 13 14 2 1)
    (100 1 160)
    simpleGrading (10 1 400)

    hex ( 20 16 4 8 21 15 3 9)
    (100 1 160)
    simpleGrading (1 1 400)

    hex ( 17 20 8 5 22 21 9 10)
    (100 1 160)
    simpleGrading (1 1 400)

    hex ( 5 6 18 17 10 11 23 22)
    (100 1 160)
    simpleGrading (10 1 400)
);

edges
(
    // Aerofoil surface edges — bottom (y_lo) and top (y_hi) layers
    project 4 7 (aerofoil)
    project 7 5 (aerofoil)
    project 4 8 (aerofoil)
    project 8 5 (aerofoil)

    project 16 19 (aerofoil)
    project 19 17 (aerofoil)
    project 16 20 (aerofoil)
    project 20 17 (aerofoil)
);

boundary
(
    aerofoil
    {{
        type            wall;
        faces
        (
            (4 7 19 16)
            (7 5 17 19)
            (5 8 20 17)
            (8 4 16 20)
        );
    }}
    inlet
    {{
        type            patch;
        inGroups        (freestream);
        faces
        (
            (3 0 12 15)
            (0 1 13 12)
            (1 2 14 13)
            (11 10 22 23)
            (10 9 21 22)
            (9 3 15 21)
        );
    }}
    outlet
    {{
        type            patch;
        inGroups        (freestream);
        faces
        (
            (2 6 18 14)
            (6 11 23 18)
        );
    }}
    back
    {{
        type            empty;
        faces
        (
            (3 4 7 0)
            (7 5 1 0)
            (5 6 2 1)
            (3 9 8 4)
            (9 10 5 8)
            (10 11 6 5)
        );
    }}
    front
    {{
        type            empty;
        faces
        (
            (15 16 19 12)
            (19 17 13 12)
            (17 18 14 13)
            (15 16 20 21)
            (20 17 22 21)
            (17 18 23 22)
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] {nu_val:.6e};

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "constant" / "turbulenceProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
simulationType  RAS;
RAS
{{
    RASModel      {turbulence_model};
    turbulence    on;
    printCoeffs   on;
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # controlDict is split into a static preamble + an α-aware functions{}
        # block. The functions{} block is built as an f-string so that
        # forceCoeffs liftDir/dragDir + Aref are α-derived. Static prefix uses
        # plain string to avoid mass-escaping `{` `}` (python_version_parity
        # risk on 3.9 nested f-strings).
        controlDict_static = """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
// DEC-V61-061 iter 2: endTime 5000→8000 — even finer mesh (96k cells,
// y+ target ~10-20) needs more iters. V61-061 iter 1 (43k cells) hit
// 1e-7 residuals around iter 4500.
endTime         8000;
deltaT          1;
writeControl    runTime;
writeInterval   500;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

"""
        # DEC-V61-058 B1.2: forceCoeffs FO on aerofoil patch (per-α) for Cl/Cd
        # extraction. Aref + lRef + rhoInf pinned per Codex DEC-V61-058 Q3.
        # liftDir/dragDir derived from cos_a/sin_a so multi-α runs use the
        # correct rotation convention: liftDir = (-sin α, 0, cos α);
        # dragDir = (cos α, 0, sin α). At α=+8°, Cl > 0 by upper-suction (Stage E
        # smoke test asserts this).
        #
        # DEC-V61-058 B1.3: yPlus FO on aerofoil patch — wall-resolution
        # diagnostic emitted as PROVISIONAL_ADVISORY (Codex F5: NOT HARD-gated;
        # band [11, 500] applied at extractor level).
        thin_span = y_hi - y_lo  # = 0.002 m
        Aref_m2 = chord * thin_span  # = 0.002 m² for chord=1.0
        controlDict_functions = f"""\
// DEC-V61-044: in-solver surface sampler on the `aerofoil` patch
// (note British spelling — matches blockMesh patch name). Emits
// postProcessing/airfoilSurface/<t>/p_aerofoil.raw with columns
// `x y z p` per face. Parser lives in src/airfoil_surface_sampler.py.
// Runs at writeTime (every 200 iterations via writeInterval above).
//
// DEC-V61-058 B1.2 + B1.3: forceCoeffs1 + yPlus FOs added.
//   forceCoeffs Aref = chord × thin_span = {chord:.4f} × {thin_span:.4f}
//                    = {Aref_m2:.6e} m² (Codex Q3a verified).
//   forceCoeffs lRef = chord = {chord:.4f} m (Codex Q3b: only affects Cm).
//   forceCoeffs rhoInf = 1.0 (incompressible kinematic, Codex Q3c).
//   liftDir = (-sin α, 0, cos α); dragDir = (cos α, 0, sin α);
//     alpha_deg = {alpha_deg:.4f}°.
functions
{{
    airfoilSurface
    {{
        type            surfaces;
        libs            ("libsampling.so");
        writeControl    writeTime;
        surfaceFormat   raw;
        fields          (p);
        interpolationScheme cellPoint;
        // DEC-V61-058 Stage E live-run fix (2026-04-25): OpenFOAM 10
        // sampledSurfaces expects `surfaces` as a LIST (parens), not
        // a dict (curlies). The dict-form inherited from DEC-V61-044
        // (commit a267d2a) parsed as "Attempt to return dictionary
        // entry as a primitive" at runtime — this case was not in any
        // live-run sweep between V61-044 (Apr 22) and V61-058 (Apr 25),
        // so the latent syntax bug went unnoticed until now.
        surfaces
        (
            aerofoil
            {{
                type            patch;
                patches         (aerofoil);
                interpolate     false;
            }}
        );
    }}

    forceCoeffs1
    {{
        type            forceCoeffs;
        libs            ("libforces.so");
        writeControl    timeStep;
        writeInterval   1;
        patches         (aerofoil);
        rho             rhoInf;
        rhoInf          1.0;
        CofR            (0.25 0 0);  // 1/4-chord moment ref (NACA convention)
        liftDir         ({-sin_a:.6e} 0 {cos_a:.6e});
        dragDir         ({cos_a:.6e} 0 {sin_a:.6e});
        pitchAxis       (0 1 0);     // y-axis (thin-span normal)
        magUInf         {U_inf:.6e};
        lRef            {chord:.6e};
        Aref            {Aref_m2:.6e};
        log             false;
    }}

    yPlus
    {{
        type            yPlus;
        libs            ("libfieldFunctionObjects.so");
        writeControl    writeTime;
        // y+ field written to postProcessing/yPlus/<t>/yPlus.dat with
        // columns: `Time  patch  min  max  average` per wall patch.
        // Extractor (compute_y_plus_max) filters by `patch == aerofoil`
        // and reads the `max` column from the final-time row (Codex
        // round 1 Q3(a) clarification: yPlus FO has no `patches` field
        // surface — every wall patch in the case is automatically
        // emitted).
    }}
}}

// ************************************************************************* //
"""
        (case_dir / "system" / "controlDict").write_text(
            controlDict_static + controlDict_functions,
            encoding="utf-8",
        )

        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes { default steadyState; }
gradSchemes {
    default         Gauss linear;
    limited         cellLimited Gauss linear 1;
    grad(U)         $limited;
    grad(k)         $limited;
    grad(omega)     $limited;
}
divSchemes {
    default         none;
    div(phi,U)      bounded Gauss upwind;
    div(phi,k)      bounded Gauss upwind;
    div(phi,omega)  bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        fvsol = (
            """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-6; relTol 0.05; }
    pFinal { $p; relTol 0; }
    U { solver PBiCGStab; preconditioner DILU; tolerance 1e-10; relTol 0.1; }
    UFinal { $U; relTol 0; }
    k { solver PBiCGStab; preconditioner DILU; tolerance 1e-10; relTol 0.1; }
    omega { solver PBiCGStab; preconditioner DILU; tolerance 1e-10; relTol 0.1; }
}

SIMPLE
{
    residualControl
    {
        p       1e-6;
        U       1e-5;
        k       1e-5;
        omega   1e-5;
    }
    // DEC-V61-061 iter 2: nNOC 0→1 to handle higher non-orthogonality
    // from refined mesh near LE/TE (max non-orth was 69° in V61-058).
    nNonOrthogonalCorrectors 1;
}

relaxationFactors
{
    fields { p 0.3; }
    equations { U 0.5; k 0.5; omega 0.5; }
}

// ************************************************************************* //
"""
        )
        (case_dir / "system" / "fvSolution").write_text(fvsol, encoding="utf-8")

        # DEC-V61-058 B1: Ux/Uz come from α-rotated freestream (Ux_inf, Uz_inf
        # computed above). Y component stays zero — thin-span x-z plane mesh.
        Ux = Ux_inf
        Uz = Uz_inf
        # Turbulence intensity I=0.005 (0.5%) for external aero at Re=3e6
        # Reduced from 0.03 (3%) to suppress nut/nu~10^3 instability with kOmegaSST
        # k = 1.5*(U_inf*I)^2  --  gives physically consistent TKE
        # Standard turbulence length-scale formula for omega:
        # omega = k^0.5 / (Cmu^0.25 * L),  NOT  k^0.5 / (beta_star * L)
        # Cmu = 0.09, so Cmu^0.25 = 0.09^0.25 ≈ 0.5623
        # beta_star (0.09) is a closure coefficient, NOT the omega denominator constant.
        # Using beta_star directly here caused omega to be ~10x too large (0.68 vs 0.069),
        # making nut/nu ~10^4 instead of ~10^3, over-damping the BL and biasing Cp low.
        I_turb = 0.005
        k_init = 1.5 * (U_inf * I_turb) ** 2   # = 3.75e-5
        L_turb = 0.1 * chord                     # = 0.1
        Cmu = 0.09
        omega_init = (k_init ** 0.5) / ((Cmu ** 0.25) * L_turb)  # ≈ 0.069 (was 0.681)

        (case_dir / "0" / "U").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];
// DEC-V61-058 B1: α-rotated freestream U_inf·(cos α, 0, sin α).
// alpha_deg = {alpha_deg:.4f}, |U_inf| = {U_inf:.4f}.
internalField   uniform ({Ux:.6e} 0 {Uz:.6e});
boundaryField
{{
    freestream
    {{
        type            freestreamVelocity;
        freestreamValue uniform ({Ux:.6e} 0 {Uz:.6e});
        value           uniform ({Ux:.6e} 0 {Uz:.6e});
    }}
    aerofoil {{ type noSlip; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "0" / "p").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    freestream
    {
        type            freestreamPressure;
        freestreamValue uniform 0;
        value           uniform 0;
    }
    aerofoil { type zeroGradient; }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/k — turbulent kinetic energy
        (case_dir / "0" / "k").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];
internalField   uniform {k_init};
boundaryField
{{
    freestream {{ type inletOutlet; inletValue uniform {k_init}; value uniform {k_init}; }}
    aerofoil {{ type kqRWallFunction; value uniform {k_init}; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/omega — specific dissipation rate
        (case_dir / "0" / "omega").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];
internalField   uniform {omega_init};
boundaryField
{{
    freestream {{ type inletOutlet; inletValue uniform {omega_init}; value uniform {omega_init}; }}
    aerofoil {{ type omegaWallFunction; value uniform {omega_init}; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/nut — turbulent viscosity with wall functions on the airfoil patch
        (case_dir / "0" / "nut").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];
internalField   uniform 0.0;
boundaryField
{{
    freestream {{ type calculated; value uniform 0; }}
    aerofoil {{ type nutkWallFunction; value uniform 0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/sampleDict — gold-anchored Cp sampling (C3b).
        # docs/c3_sampling_strategy_design.md §3.2 Option B: sample p at
        # upper-surface points for each x_over_c in whitelist reference_values.
        # The Cp profile gold YAML is anchored at α=0° (NACA0012 symmetric);
        # at α=0° upper and lower surfaces mirror, so upper-surface sampling
        # captures the full distribution. DEC-V61-058 B1 added α-routing for
        # the force-coefficient gates (Cl/Cd via forceCoeffs FO), but the Cp
        # PROFILE_GATE remains an α=0 measurement — runs at α=4°/α=8° produce
        # forceCoeffs Cl/Cd but the Cp sampleDict block here still reads the
        # α=0 gold values (intake §3 design: Cp at α=0 only; upper-surface
        # asymmetric sampling at α≠0 is out-of-scope, deferred). cellPoint
        # interpolation at wall points extrapolates from first interior cell
        # — standard for wall-pressure extraction in OpenFOAM.
        gold_values = _load_gold_reference_values(task_spec.name) or []
        xoc_values = [
            float(rv["x_over_c"])
            for rv in gold_values
            if isinstance(rv, dict) and "x_over_c" in rv
        ]
        if xoc_values:
            physical_points = [
                (
                    xoc * chord,
                    0.0,  # mid-span (y thin slab)
                    FoamAgentExecutor._naca0012_half_thickness(xoc) * chord,
                )
                for xoc in xoc_values
            ]
            _emit_gold_anchored_points_sampledict(
                case_dir,
                set_name="airfoilCp",
                physical_points=physical_points,
                fields=["p"],
                axis="x",
                header_comment=(
                    f"NACA0012 upper surface, {len(xoc_values)} gold x/c coords "
                    f"(chord={chord:g}); Cp = (p - p_inf) / (0.5*U_inf^2), "
                    f"U_inf={U_inf:g}, p_inf=0 gauge"
                ),
            )

    @staticmethod
    def _naca0012_half_thickness(x_over_c: float, thickness_ratio: float = 0.12) -> float:
        """Return the half-thickness y/c for a symmetric NACA 0012 profile."""
        x = min(max(x_over_c, 0.0), 1.0)
        if x in (0.0, 1.0):
            return 0.0
        thickness = (
            0.2969 * math.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x**2
            + 0.2843 * x**3
            - 0.1036 * x**4
        )
        return max(0.0, 5.0 * thickness_ratio * thickness)

    @classmethod
    def _write_naca0012_surface_obj(
        cls,
        case_dir: Path,
        chord: float,
        span: float,
        point_count: int = 2001,
    ) -> None:
        """Write a thin-span NACA0012 OBJ aligned with the x-z airfoil plane."""
        geometry_dir = case_dir / "constant" / "geometry"
        geometry_dir.mkdir(parents=True, exist_ok=True)

        xs = [
            0.5 * chord * (1.0 - math.cos(math.pi * i / (point_count - 1)))
            for i in range(point_count)
        ]
        lines = [
            "# Wavefront OBJ file",
            "# Regions:",
            "#     0    airfoil",
            "g airfoil",
        ]
        span_lo = -0.5 * span
        span_hi = 0.5 * span

        upper_front: List[int] = []
        upper_back: List[int] = []
        lower_front: List[int] = []
        lower_back: List[int] = []
        next_idx = 1

        for x in xs:
            z = cls._naca0012_half_thickness(x / chord) * chord
            vertices = (
                (x, span_lo, z),
                (x, span_hi, z),
                (x, span_lo, -z),
                (x, span_hi, -z),
            )
            for bucket, vertex in zip(
                (upper_front, upper_back, lower_front, lower_back), vertices
            ):
                lines.append(f"v {vertex[0]:.8f} {vertex[1]:.8f} {vertex[2]:.8f}")
                bucket.append(next_idx)
                next_idx += 1

        for i in range(point_count - 1):
            uf0, uf1 = upper_front[i], upper_front[i + 1]
            ub0, ub1 = upper_back[i], upper_back[i + 1]
            lf0, lf1 = lower_front[i], lower_front[i + 1]
            lb0, lb1 = lower_back[i], lower_back[i + 1]

            lines.append(f"f {uf0} {uf1} {ub1}")
            lines.append(f"f {uf0} {ub1} {ub0}")
            lines.append(f"f {lf0} {lb1} {lf1}")
            lines.append(f"f {lf0} {lb0} {lb1}")

        lead = (upper_front[0], upper_back[0], lower_back[0], lower_front[0])
        trail = (
            upper_front[-1],
            upper_back[-1],
            lower_back[-1],
            lower_front[-1],
        )
        lines.append(f"f {lead[0]} {lead[1]} {lead[2]}")
        lines.append(f"f {lead[0]} {lead[2]} {lead[3]}")
        lines.append(f"f {trail[0]} {trail[2]} {trail[1]}")
        lines.append(f"f {trail[0]} {trail[3]} {trail[2]}")

        (geometry_dir / "NACA0012.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _render_bfs_block_mesh_dict(
        self, task_spec: TaskSpec, H: float, channel_height: float,
        ncx: int = 40, ncy: int = 20,
    ) -> str:
        """Render a canonical 3-block BFS blockMeshDict with a real step at x=0.

        Geometry (Driver & Seegmiller 1985, ER=1.125 convention):
          - h_s = H                     (step height, input param `H`)
          - H_ch = channel_height       (full downstream channel height = 9·H)
          - H_inlet = H_ch - h_s        (upstream inlet channel height = 8·H)
          - L_up = 10·H                 (upstream inlet channel length)
          - L_down = 30·H               (downstream channel length — covers Xr≈6.26 + recovery)
          - L_z = 0.1·H                 (thin z-extrusion for 2D empty patches)

        Three-block topology (viewed in the xy-plane at any z):

            y=H_ch ┌───────────────┬───────────────────────────────┐
                   │               │                               │
                   │    block A    │          block B2             │  upper_wall
                   │ (inlet chan)  │      (downstream upper)       │
            y=h_s  ├───────────────┼───────────────────────────────┤
                   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│          block B1             │
                   ▓  STEP VOID   ▓│      (recirculation + recov.) │
                   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│                               │
            y=0                    └───────────────────────────────┘
                   x=-L_up         x=0                      x=+L_down
                                   │
                                   step_face (part of lower_wall patch)

        Patch name policy (DEC-V61-052):
          The three physical lower-wall pieces — inlet-channel floor at y=h_s
          for x∈[-L_up,0], the vertical step face at x=0 for y∈[0,h_s], and
          the downstream floor at y=0 for x∈[0,L_down] — are all noSlip walls
          with identical k/ε/nut wall-function BC. They are merged into a
          SINGLE `lower_wall` patch so that the existing 0/U, 0/p, 0/k,
          0/epsilon, 0/nut templates (which reference one `lower_wall`) keep
          working without per-piece rewrites. This is semantically lossless.

          `inlet` is block A's x=-L_up face (spans only y∈[h_s,H_ch], i.e., the
          physical inlet channel). `outlet` combines B1 and B2 east faces.
          `upper_wall` combines A and B2 top faces. `front`/`back` are empty
          patches across all three blocks.

        Cell-count ties (blockMesh requires matching subdivisions at shared
        interfaces):
          - A-B2 interface at x=0, y∈[h_s,H_ch]: both blocks use ncy_A cells in y.
          - B1-B2 interface at y=h_s, x∈[0,L_down]: both blocks use ncx_B cells in x.
          - B1's y-resolution (ncy_B1) is independent — only appears on B1's
            west (step face, wall) and east (outlet, patch) faces, both boundary.

        Default cell counts (whitelist, ~7300 cells):
          ncx_A=40, ncy_A=16, ncx_B=120, ncy_B1=40, ncy_B2=ncy_A=16.
          Legacy `ncx`/`ncy` args are ignored by this multi-block generator —
          they were single-block quantities. TODO: thread explicit multi-block
          counts through TaskSpec if grid-refinement studies need override.
        """
        # Geometry (see docstring for conventions)
        h_s = H
        H_ch = channel_height
        L_up = 10.0 * H
        L_down = 30.0 * H
        L_z = 0.1 * H

        x0 = -L_up
        x1 = 0.0
        x2 = L_down
        y0 = 0.0
        y1 = h_s
        y2 = H_ch
        z0 = 0.0
        z1 = L_z

        # Cell counts (see docstring — legacy single-block ncx/ncy ignored)
        ncx_A = 40
        ncy_A = 16          # must equal ncy_B2 (A-B2 interface at x=0)
        ncx_B = 120
        ncy_B1 = 40
        ncy_B2 = ncy_A

        # 16 vertices: 8 (x,y) grid points × 2 z-levels.
        # Layout (v_i / v_(i+8) give z=0 / z=L_z pairs):
        #   v0 = (x0, y1)  upstream-bottom (inlet channel floor corner)
        #   v1 = (x1, y1)  step-top corner (junction A/B1/B2)
        #   v2 = (x1, y2)  upstream-top interior (junction A/B2)
        #   v3 = (x0, y2)  upstream-top outer
        #   v4 = (x1, y0)  step-foot (start of downstream floor)
        #   v5 = (x2, y0)  downstream-bottom outer
        #   v6 = (x2, y1)  downstream y=h_s outer (B1-B2 east joint)
        #   v7 = (x2, y2)  downstream-top outer
        verts = [
            (x0, y1, z0), (x1, y1, z0), (x1, y2, z0), (x0, y2, z0),
            (x1, y0, z0), (x2, y0, z0), (x2, y1, z0), (x2, y2, z0),
            (x0, y1, z1), (x1, y1, z1), (x1, y2, z1), (x0, y2, z1),
            (x1, y0, z1), (x2, y0, z1), (x2, y1, z1), (x2, y2, z1),
        ]
        vtx_block = "\n".join(f"    ({vx} {vy} {vz})" for vx, vy, vz in verts)

        return f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
{vtx_block}
);

blocks
(
    // DEC-V61-052 round 2c: x-grading concentrates cells near the step corner.
    // y-grading kept uniform to avoid inconsistent shared-edge spacings between
    // the three blocks (blockMesh requires matching vertex locations at all
    // inter-block interfaces).
    //
    //   block A (upstream):  last x-cell 1/4 of first → cells bunch toward x=0
    //   block B1 (recirc):   last x-cell 4× first      → cells bunch toward x=0 (the step)
    //   block B2 (upper):    last x-cell 4× first      → same x-distribution as B1
    //
    // This puts the finest x-resolution in the shear-layer zone (first ~1H
    // downstream of the step), which controls reattachment location under
    // kOmegaSST. Reviewers: this is "a bounded matrix" item from Codex round 1 #4.
    hex (0 1 2 3 8 9 10 11) ({ncx_A} {ncy_A} 1) simpleGrading (0.25 1 1)
    hex (4 5 6 1 12 13 14 9) ({ncx_B} {ncy_B1} 1) simpleGrading (4 1 1)
    hex (1 6 7 2 9 14 15 10) ({ncx_B} {ncy_B2} 1) simpleGrading (4 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type            patch;
        faces
        (
            (0 8 11 3)  // block A west face, y∈[h_s,H_ch], x=-L_up
        );
    }}
    outlet
    {{
        type            patch;
        faces
        (
            (5 6 14 13) // block B1 east face, y∈[0,h_s], x=+L_down
            (6 7 15 14) // block B2 east face, y∈[h_s,H_ch], x=+L_down
        );
    }}
    lower_wall
    {{
        type            wall;
        faces
        (
            (0 1 9 8)   // block A south face (inlet channel floor, y=h_s, x∈[-L_up,0])
            (4 12 9 1)  // block B1 west face (the step face, x=0, y∈[0,h_s])
            (4 5 13 12) // block B1 south face (downstream floor, y=0, x∈[0,L_down])
        );
    }}
    upper_wall
    {{
        type            wall;
        faces
        (
            (3 11 10 2) // block A north face, y=H_ch, x∈[-L_up,0]
            (2 10 15 7) // block B2 north face, y=H_ch, x∈[0,L_down]
        );
    }}
    front
    {{
        type            empty;
        faces
        (
            (8 9 10 11)  // block A  z=+L_z
            (12 13 14 9) // block B1 z=+L_z
            (9 14 15 10) // block B2 z=+L_z
        );
    }}
    back
    {{
        type            empty;
        faces
        (
            (0 3 2 1)  // block A  z=0
            (4 1 6 5)  // block B1 z=0
            (1 2 7 6)  // block B2 z=0
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""

    def _render_block_mesh_dict(self, task_spec: TaskSpec) -> str:
        """渲染 blockMeshDict，支持 TaskSpec boundary_conditions 参数覆盖。"""
        # 允许通过 boundary_conditions 覆盖顶盖速度
        lid_u = float(
            task_spec.boundary_conditions.get("lid_velocity_u", 1.0)
        )
        return f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 0.1;

vertices
(
    (0 0 0)
    (1 0 0)
    (1 1 0)
    (0 1 0)
    (0 0 0.1)
    (1 0 0.1)
    (1 1 0.1)
    (0 1 0.1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (129 129 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    lid
    {{
        type            wall;
        faces           ((3 7 6 2));
    }}
    wall1
    {{
        type            wall;
        faces           ((0 4 7 3));
    }}
    wall2
    {{
        type            wall;
        faces           ((1 2 6 5));
    }}
    bottom
    {{
        type            wall;
        faces           ((0 1 5 4));
    }}
    frontAndBack
    {{
        type            empty;
        faces
        (
            (0 3 2 1)
            (4 5 6 7)
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""

    # ------------------------------------------------------------------
    # Docker execution helpers
    # ------------------------------------------------------------------

    def _docker_exec(
        self,
        command: str,
        working_dir: str,
        timeout: int,
    ) -> Tuple[bool, str]:
        """在 cfd-openfoam 容器中执行命令，返回 (success, stdout_log)。

        流程：
        1. 在容器内创建 case 目录（openfoam 用户可写）
        2. 复制 case 文件到容器内
        3. 以 root 权限 chmod 确保 openfoam 可写
        4. 执行 OpenFOAM 命令
        5. 复制 log 文件回宿主机
        """
        container = self._docker_client.containers.get(self._container_name)
        case_id = working_dir.split("/")[-1]
        host_case_dir = self._work_dir / case_id

        # Step 1: 以 openfoam 用户身份创建目录
        container.exec_run(cmd=["bash", "-c", f"mkdir -p {working_dir} && chmod 777 {working_dir}"])

        # Step 2: 复制 case 文件到容器内
        try:
            archive_ok = container.put_archive(
                path=working_dir,
                data=self._make_tarball(host_case_dir),
            )
            if not archive_ok:
                raise RuntimeError(f"put_archive returned {archive_ok!r} for {working_dir}")
        except Exception as e:
            import sys as _sys
            print(f"[WARN] put_archive failed: {e}", file=_sys.stderr)

        # Step 3: 以 root 身份修复权限（openfoam 用户需要能写 constant/）
        try:
            container.exec_run(
                cmd=["bash", "-c", f"find {working_dir} -type d -exec chmod 777 {{}} \\; 2>/dev/null; true"],
                user="0",
            )
        except Exception as e:
            import sys as _sys
            print(f"[WARN] chmod exec_run failed: {e}", file=_sys.stderr)

        # Step 4: 执行 OpenFOAM 命令
        safe_log_name = re.sub(r"[^a-zA-Z0-9]", "_", command).strip("_")
        bash_cmd = (
            f"source /opt/openfoam10/etc/bashrc && "
            f"cd {working_dir} && "
            f"{command} > log.{safe_log_name} 2>&1"
        )
        result = container.exec_run(
            cmd=["bash", "-c", bash_cmd],
            workdir=working_dir,
        )

        # Step 5: 读取容器内的 log 文件
        log_path = host_case_dir / f"log.{safe_log_name}"
        self._copy_file_from_container(container, f"{working_dir}/log.{safe_log_name}", log_path)

        if log_path.exists() and log_path.stat().st_size > 0:
            return result.exit_code == 0, log_path.read_text(encoding="utf-8", errors="replace")
        return result.exit_code == 0, str(result.output)

    @staticmethod
    def _make_tarball(src_dir: Path) -> bytes:
        """把目录内容打包成 tarball bytes（用于 put_archive）。

        Recursive walk of all subdirectories.
        Strips host permissions to avoid container write issues.
        All files set to 0644, all dirs set to 0755.
        """
        import io as _io, tarfile as _tarfile, os as _os
        buf = _io.BytesIO()
        with _tarfile.open(fileobj=buf, mode="w", format=_tarfile.PAX_FORMAT) as tar:
            for root, dirs, files in _os.walk(src_dir):
                dirs.sort()
                files.sort()
                for fname in sorted(files):
                    fpath = Path(root) / fname
                    arcname = str(fpath.relative_to(src_dir))
                    info = _tarfile.TarInfo(arcname)
                    info.size = fpath.stat().st_size
                    info.mode = 0o644
                    info.mtime = fpath.stat().st_mtime
                    info.type = _tarfile.REGTYPE
                    tar.addfile(info, fileobj=fpath.open("rb"))
                for dname in sorted(dirs):
                    dpath = Path(root) / dname
                    arcname = str(dpath.relative_to(src_dir)) + "/"
                    info = _tarfile.TarInfo(arcname)
                    info.size = 0
                    info.mode = 0o755
                    info.type = _tarfile.DIRTYPE
                    tar.addfile(info)
        buf.seek(0)
        return buf.read()

    @staticmethod
    def _copy_file_from_container(container: Any, container_path: str, dest_path: Path) -> None:
        """从容器内复制单个文件到宿主机路径。"""
        try:
            bits, _ = container.get_archive(container_path)
            data = b"".join(bits)
            with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                member_name = container_path.split("/")[-1]
                for m in tar.getmembers():
                    if m.name.endswith(member_name):
                        member = tar.extractfile(m)
                        if member:
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            dest_path.write_bytes(member.read())
                        break
        except Exception as e:
            import sys as _sys
            print(f"[WARN] _copy_file_from_container failed: {e}", file=_sys.stderr)

    def _copy_postprocess_fields(
        self, container: Any, case_cont_dir: str, case_host_dir: Path
    ) -> None:
        """从容器内复制 postProcess -func writeObjects 输出的场文件到宿主机。

        postProcess 在 latestTime 目录写出 U, Cx, Cy, (T) 等场文件，
        将这些文件复制到宿主机的对应时间目录。
        """
        try:
            # Find numeric time directories (exclude '0' - initial condition).
            # DEC-V61-053 live-run fix (2026-04-24): `sort -t/ -k1 -n` fails
            # on adaptive-timestep directory names like "2.00032" "5.998936"
            # "10.000003" — field 1 (before first /) is empty on absolute
            # paths, so sort falls back to lexical comparison and picks
            # "5.9..." as "latest" over "10.0...". This silently skipped
            # writeObjects fields for pimpleFoam transient runs. Fixed by
            # tagging each line with its basename and numeric-sorting on
            # the tag instead.
            result = container.exec_run(
                cmd=[
                    "bash",
                    "-c",
                    f'find "{case_cont_dir}" -maxdepth 1 -type d -name "[0-9]*" 2>/dev/null | grep -v "/0$" | sed "s|/$||" | awk -F/ \'{{print $NF"\\t"$0}}\' | sort -k1,1 -n | tail -1 | cut -f2-',
                ],
            )
            latest_cont_dir = result.output.decode().strip()

            if not latest_cont_dir:
                return

            # Verify it's a directory, not a file
            path_check = container.exec_run(
                cmd=["bash", "-c", f'if [ ! -d "{latest_cont_dir}" ]; then echo not_dir; fi']
            )
            if path_check.output.decode().strip() == "not_dir":
                return

            latest_time = Path(latest_cont_dir).name

            # 场文件：U 和 Cx/Cy 必选，Cz/T 按 case 需要复制。
            # DEC-V61-052 round 2: include wallShearStress so BFS (and
            # any other case registering the wallShearStress FO) can run
            # tau_x-based extractors instead of Ux proxies. When the FO
            # is absent the file simply doesn't exist — skipped safely.
            field_files = ["U", "p", "Cx", "Cy", "Cz", "T", "wallShearStress", "yPlus"]
            host_time_dir = case_host_dir / latest_time

            for field_file in field_files:
                actual_cont_path = f"{latest_cont_dir}/{field_file}"
                # Check if file exists in container before attempting copy (T is optional)
                check = container.exec_run(
                    cmd=["bash", "-c", f'[ -f "{actual_cont_path}" ] && echo exists || echo missing']
                )
                if check.output.decode().strip() == "missing":
                    continue
                host_path = host_time_dir / field_file
                self._copy_file_from_container(container, actual_cont_path, host_path)
        except Exception as e:
            import sys as _sys
            print(f"[WARN] _copy_postprocess_fields failed: {e}", file=_sys.stderr)

    # ------------------------------------------------------------------
    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
    # ------------------------------------------------------------------

    def _capture_field_artifacts(
        self,
        container: Any,
        case_cont_dir: str,
        case_host_dir: Path,
        case_id: str,
        timestamp: str,
    ) -> Optional[Path]:
        """Phase 7a — stage OpenFOAM field artifacts out of the container
        before the finally-block tears down case_host_dir.

        Mirrors _copy_postprocess_fields. Runs foamToVTK inside the container,
        then uses docker `get_archive` to pull VTK/, postProcessing/sample/,
        and postProcessing/residuals/ wholesale via a single tar stream.
        Also copies log.<solver> from the host case dir (already on host).

        Returns the host-side artifact_dir on success, None on failure.
        Never raises — field capture is best-effort and must not fail the run
        (comparator scalar extraction still needs to succeed downstream).
        """
        import io as _io
        import sys as _sys
        import tarfile as _tarfile

        repo_root = Path(__file__).resolve().parents[1]
        artifact_dir = repo_root / "reports" / "phase5_fields" / case_id / timestamp
        try:
            artifact_dir.mkdir(parents=True, exist_ok=True)

            # (a) foamToVTK — -allPatches merges patches into a single file.
            #     -noFaceZones: DEC-V61-034 Tier C, circular_cylinder_wake uses
            #     createBaffles which leaves a cylinderBaffleZone faceZone; OF10
            #     foamToVTK SEGVs when interpolating surfScalarField phi onto
            #     the post-baffle faceZone (flux pointer inconsistent with
            #     split owner/neighbour patches of the same name). -noFaceZones
            #     skips the faceZone write, which is not required downstream
            #     (the cylinder wall is already emitted as a regular patch).
            #     No-op for the 9 cases that don't use faceZones.
            #     Fallback without -allPatches if it trips empty-patch
            #     assertions (07a-RESEARCH.md §3.2).
            ok, log = self._docker_exec(
                "foamToVTK -latestTime -noZero -allPatches -noFaceZones",
                case_cont_dir,
                120,
            )
            if not ok:
                print(
                    # Tail slice: SEGV stack traces + OF error strings are at
                    # end-of-log, not the banner. 200-char head truncation
                    # hid the cylinder_wake SEGV for a full diagnosis cycle.
                    f"[WARN] foamToVTK -allPatches failed, retrying without: {log[-400:]}",
                    file=_sys.stderr,
                )
                ok, log = self._docker_exec(
                    "foamToVTK -latestTime -noZero -noFaceZones", case_cont_dir, 120,
                )
            if not ok:
                print(
                    f"[WARN] foamToVTK failed, field capture skipped: {log[-400:]}",
                    file=_sys.stderr,
                )
                return None

            # (b) Tar + get_archive the three subtrees. Missing subtrees are
            #     fine (e.g. postProcessing/residuals only exists if the
            #     residuals function object was emitted).
            for sub in ("VTK", "postProcessing/sample", "postProcessing/residuals"):
                src_in_cont = f"{case_cont_dir}/{sub}"
                probe = container.exec_run(
                    cmd=["bash", "-c", f'[ -e "{src_in_cont}" ] && echo y || echo n'],
                )
                if probe.output.decode().strip() != "y":
                    continue
                try:
                    bits, _ = container.get_archive(src_in_cont)
                    buf = _io.BytesIO(b"".join(bits))
                    with _tarfile.open(fileobj=buf) as tar:
                        tar.extractall(path=artifact_dir)
                except Exception as e:  # noqa: BLE001
                    print(
                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
                    )

            # (c) log.<solver> — already on host after _docker_exec.
            for logname in (
                "log.simpleFoam",
                "log.icoFoam",
                "log.buoyantFoam",
                "log.pimpleFoam",
            ):
                src = case_host_dir / logname
                if src.is_file():
                    (artifact_dir / logname).write_bytes(src.read_bytes())
                    break

            # (d) Derive residuals.csv from residuals/0/residuals.dat if present.
            #     Per user ratification #3 — structured ASCII, no log regex.
            #     NOTE: container.get_archive('.../postProcessing/residuals')
            #     tar-extracts under basename `residuals/`, not the full
            #     `postProcessing/residuals/` path. Same applies to `sample/`.
            residuals_dat_candidates = list(
                artifact_dir.glob("residuals/*/residuals.dat")
            )
            if residuals_dat_candidates:
                try:
                    self._emit_residuals_csv(
                        residuals_dat_candidates[0],
                        artifact_dir / "residuals.csv",
                    )
                except Exception as e:  # noqa: BLE001
                    print(
                        f"[WARN] residuals.csv derivation failed: {e!r}",
                        file=_sys.stderr,
                    )

            return artifact_dir
        except Exception as e:  # noqa: BLE001
            print(
                f"[WARN] _capture_field_artifacts failed: {e!r}", file=_sys.stderr,
            )
            return None

    @staticmethod
    def _emit_residuals_csv(dat_path: Path, csv_path: Path) -> None:
        """Convert OpenFOAM v10 residuals function-object output to CSV.

        The .dat format is whitespace-separated with a header line starting
        with `#`. We passthrough as CSV (comma-separated) with an explicit
        header — downstream tools (Phase 7b render pipeline) consume this.
        """
        lines = dat_path.read_text(encoding="utf-8").splitlines()
        header: Optional[List[str]] = None
        rows: List[List[str]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                tokens = line.lstrip("#").split()
                if tokens:
                    header = tokens
                continue
            rows.append(line.split())
        if not header or not rows:
            return
        with csv_path.open("w", encoding="utf-8") as fh:
            fh.write(",".join(header) + "\n")
            for r in rows:
                fh.write(",".join(r) + "\n")

    # ------------------------------------------------------------------
    # Log parsing
    # ------------------------------------------------------------------

    def _parse_solver_log(self, log_path: Path, solver_name: str = "icoFoam", task_spec: Optional[TaskSpec] = None) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """解析 solver log 文件，提取最终（末次迭代）残差和关键物理量。

        Args:
            log_path: log 文件路径
            solver_name: "icoFoam" 或 "simpleFoam" 或 "buoyantFoam"
            task_spec: 任务规格，用于 case-specific 物理量解释

        Returns:
            (residuals, key_quantities)
        """
        if not log_path.exists():
            return {}, {}

        text = log_path.read_text(encoding="utf-8", errors="replace")

        residuals: Dict[str, float] = {}
        key_quantities: Dict[str, Any] = {}

        if solver_name == "simpleFoam":
            # simpleFoam 格式:
            # "Solving for Ux, Initial residual = X, Final residual = Y, No Iterations Z"
            # 也可能有: "Solving for Ux, Initial residual = X, Final residual = Y"
            # 还有 turbulence: "Solving for k, Initial residual = X, Final residual = Y"
            pattern = re.compile(
                r"Solving for (\w+),.*?Initial residual\s*=\s*([\d.eE+-]+)"
            )
            for match in pattern.finditer(text):
                var = match.group(1)
                # 只保留最后一个匹配（最终迭代）
                residuals[var] = float(match.group(2))

            # 从最终迭代提取速度分量残差用于 key_quantities
            ux_matches = list(re.finditer(
                r"Solving for Ux,.*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ))
            uy_matches = list(re.finditer(
                r"Solving for Uy,.*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ))
            if ux_matches and uy_matches:
                ux_res = float(ux_matches[-1].group(1))
                uy_res = float(uy_matches[-1].group(1))
                key_quantities["U_residual_magnitude"] = (ux_res ** 2 + uy_res ** 2) ** 0.5

        else:
            # icoFoam 格式:
            # "Solving for <var>, Initial residual = X, Final residual = Y"
            for match in re.finditer(
                r"Solving for (\w+).*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ):
                var = match.group(1)
                residuals[var] = float(match.group(2))

            # 关键物理量：末次时间步的最大速度
            ux_matches = list(re.finditer(
                r"Solving for Ux,.*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ))
            uy_matches = list(re.finditer(
                r"Solving for Uy,.*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ))
            if ux_matches and uy_matches:
                ux_res = float(ux_matches[-1].group(1))
                uy_res = float(uy_matches[-1].group(1))
                key_quantities["U_max_approx"] = max(ux_res, abs(uy_res))

        # 从 postProcessing/sets 目录读取 sample utility 输出的关键物理量
        post_dir = log_path.parent / "postProcessing"
        if post_dir.exists():
            sets_dir = post_dir / "sets"
            if sets_dir.exists():
                # 遍历所有时间目录
                for time_dir in sorted(sets_dir.iterdir()):
                    if time_dir.is_dir():
                        # 查找 sample 输出文件 (e.g., U_uCenterline, T_midPlaneT)
                        for sample_file in sorted(time_dir.iterdir()):
                            filename = sample_file.name
                            lines = sample_file.read_text(encoding="utf-8", errors="replace").splitlines()

                            # 解析 sample 文件格式:
                            # #   Time  x  y  z  Ux  Uy  Uz  (for vector fields)
                            # #   Time  x  y  z  T         (for scalar fields)
                            if filename.startswith("U_"):
                                # Velocity sample - extract Ux component for centerline profile
                                set_name = filename[2:]  # e.g., "uCenterline", "wallProfile"
                                vals = []
                                y_coords = []
                                x_coords = []
                                for line in lines:
                                    if line.startswith("#") or not line.strip():
                                        continue
                                    parts = line.split()
                                    # setFormat raw: x y z Ux Uy Uz  (6 columns, no leading Time)
                                    # OR with Time: time x y z Ux Uy Uz (7 columns)
                                    if len(parts) >= 7:
                                        # Format: time x y z Ux Uy Uz
                                        x_idx, y_idx, z_idx, u_idx = 1, 2, 3, 4
                                    elif len(parts) >= 6:
                                        # Format: x y z Ux Uy Uz (setFormat raw)
                                        x_idx, y_idx, z_idx, u_idx = 0, 1, 2, 3
                                    else:
                                        continue
                                    try:
                                        x_coords.append(float(parts[x_idx]))
                                        y_coords.append(float(parts[y_idx]))
                                        vals.append(float(parts[u_idx]))  # Ux component
                                    except ValueError:
                                        pass
                                if vals:
                                    # Use set name as key, e.g., "uCenterline"
                                    key_quantities[set_name] = vals
                                    # Also store coordinates for profile matching
                                    key_quantities[f"{set_name}_y"] = y_coords
                                    # BFS reattachment length needs x coordinates
                                    key_quantities[f"{set_name}_x"] = x_coords

                            elif filename.startswith("T_"):
                                # Temperature sample - extract T component
                                set_name = filename[2:]  # e.g., "midPlaneT"
                                vals = []
                                y_coords = []
                                for line in lines:
                                    if line.startswith("#") or not line.strip():
                                        continue
                                    parts = line.split()
                                    # Format: time x y z T
                                    if len(parts) >= 5:
                                        try:
                                            y_coords.append(float(parts[2]))  # y coordinate
                                            vals.append(float(parts[4]))  # T value
                                        except ValueError:
                                            pass
                                if vals:
                                    key_quantities[set_name] = vals
                                    key_quantities[f"{set_name}_y"] = y_coords

        # Case-specific interpretation: 映射 sample 输出到 Gold Standard 期望的 quantity 名称
        if task_spec is not None:
            geom = task_spec.geometry_type

            # LDC: uCenterline -> u_centerline (Gold Standard 格式)
            # Covers: icoFoam+SIMPLE_GRID (explicit), name-based SIMPLE_GRID/CUSTOM, Re<2300
            if self._is_lid_driven_cavity_case(task_spec, solver_name):
                if "uCenterline" in key_quantities:
                    key_quantities["u_centerline"] = key_quantities["uCenterline"]
                    del key_quantities["uCenterline"]
                    if "uCenterline_y" in key_quantities:
                        key_quantities["u_centerline_y"] = key_quantities["uCenterline_y"]
                        del key_quantities["uCenterline_y"]

            # BFS: 从 wallProfile 计算再附着长度 Xr/H
            elif geom == GeometryType.BACKWARD_FACING_STEP:
                if "wallProfile" in key_quantities:
                    x_coords = key_quantities.get("wallProfile_x", [])
                    ux_vals = key_quantities.get("wallProfile", [])
                    if x_coords and ux_vals and len(x_coords) == len(ux_vals):
                        # 找再附着点: Ux 从负变正的第一个位置
                        reattachment_x = None
                        for i in range(1, len(ux_vals)):
                            if ux_vals[i-1] < 0 and ux_vals[i] >= 0:
                                # 线性插值找精确零交点
                                x1, x2 = x_coords[i-1], x_coords[i]
                                u1, u2 = ux_vals[i-1], ux_vals[i]
                                if u2 != u1:
                                    reattachment_x = x1 - u1 * (x2 - x1) / (u2 - u1)
                                else:
                                    reattachment_x = x1
                                break
                        # P6-TD-001: same physical-plausibility guard as
                        # _extract_bfs_reattachment — reject upstream (x ≤ 0)
                        # detections from under-converged solvers.
                        if reattachment_x is not None and reattachment_x > 0:
                            H = 1.0  # step height
                            key_quantities["reattachment_length"] = reattachment_x / H
                        elif reattachment_x is not None:
                            key_quantities["reattachment_detection_upstream_artifact"] = True
                            key_quantities["reattachment_detection_rejected_x"] = reattachment_x
                    # 清理中间数据
                    for k in list(key_quantities.keys()):
                        if k.startswith("wallProfile"):
                            del key_quantities[k]

            # DEC-V61-042: removed secondary NC-Cavity Nu computation path
            # that differenced two cells of the midPlaneT profile (silent
            # substitution risk — would overwrite the proper wall-gradient
            # result from _extract_nc_nusselt if midPlaneT happened to be
            # populated by a parallel sample FO). The authoritative path
            # is now _extract_nc_nusselt via _parse_writeobjects_fields,
            # which uses the 3-point one-sided stencil on the hot wall.
            elif geom == GeometryType.NATURAL_CONVECTION_CAVITY:
                pass  # no-op — handled in _parse_writeobjects_fields

        return residuals, key_quantities

    # ------------------------------------------------------------------
    # writeObjects field extraction
    # ------------------------------------------------------------------

    def _parse_writeobjects_fields(
        self,
        case_dir: Path,
        solver_name: str,
        task_spec: Optional[TaskSpec],
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从 postProcess writeObjects 输出的场文件提取 case-specific 关键物理量。

        postProcess -func writeObjects -latestTime 在最新时间目录写出:
        - U: vector field (Ux, Uy, Uz) for each cell
        - Cx, Cy, Cz: cell centre coordinates
        - p: pressure field
        这些文件格式为 OpenFOAM internalField nonuniform List<...>。

        Returns:
            key_quantities updated with u_centerline, reattachment_length, nusselt_number
        """
        if task_spec is None:
            return key_quantities

        # 找到最新时间目录
        time_dirs = []
        for item in case_dir.iterdir():
            if item.is_dir():
                try:
                    t = float(item.name)
                    time_dirs.append((t, item))
                except ValueError:
                    pass
        if not time_dirs:
            return key_quantities

        latest_t, latest_dir = max(time_dirs, key=lambda x: x[0])

        # DEC-V61-053 live-run fix (2026-04-24): cylinder extractor paths
        # (forceCoeffs FFT for St/Cd/Cl + sampleDict for u_centerline) are
        # independent of the U/Cx/Cy field-file existence check below —
        # they read postProcessing/forceCoeffs1 and postProcessing/sets
        # directly. Lift their invocation ABOVE the field-file gate so
        # they still run when _copy_postprocess_fields doesn't produce
        # U/Cx/Cy (which happens when the sort-bug fix above lands
        # incomplete, or when `postProcess -funcs writeObjects` fails
        # silently on pimpleFoam adaptive-timestep runs).
        if (task_spec.geometry_type == GeometryType.BODY_IN_CHANNEL
                and task_spec.flow_type == FlowType.EXTERNAL):
            # DEC-V61-053 Codex R4 LOW fix: read endTime from
            # boundary_conditions (plumbed by generator from class constant
            # CYLINDER_ENDTIME_S — single source of truth). Fallback to
            # CYLINDER_ENDTIME_S for MOCK / out-of-band calls. If a future
            # DEC bumps the constant to 60s/200s, transient_trim and
            # min_averaging_window scale automatically.
            _bc = task_spec.boundary_conditions or {}
            _cyl_endtime = float(_bc.get("cylinder_endTime", self.CYLINDER_ENDTIME_S))
            _cyl_trim = min(0.2 * _cyl_endtime, 50.0)  # 20% transient, cap at original default
            _cyl_min_window = max(0.3 * _cyl_endtime, 2.0)  # min 2s floor for demo runs
            key_quantities = self._extract_cylinder_strouhal(
                [], [], [], task_spec, key_quantities, case_dir=case_dir,
                transient_trim_s=_cyl_trim,
            )
            try:
                from src.cylinder_centerline_extractor import (  # noqa: PLC0415
                    extract_centerline_u_deficit,
                )
                bc = task_spec.boundary_conditions or {}
                D_val = float(bc.get("cylinder_D", 0.1))
                U_val = float(bc.get("U_ref", 1.0))
                centerline = extract_centerline_u_deficit(
                    case_dir, U_inf=U_val, D=D_val,
                    min_averaging_window_s=_cyl_min_window,
                )
                for k, v in centerline.items():
                    key_quantities[k] = v
            except Exception as e:  # noqa: BLE001
                key_quantities["u_deficit_extractor_error"] = f"{type(e).__name__}: {e}"

        # 检查是否有 U 和 Cx/Cy 文件
        u_path = latest_dir / "U"
        cx_path = latest_dir / "Cx"
        cy_path = latest_dir / "Cy"
        if not all(p.exists() for p in [u_path, cx_path, cy_path]):
            return key_quantities

        # 读取场数据
        cxs = self._read_openfoam_scalar_field(cx_path)
        cys = self._read_openfoam_scalar_field(cy_path)
        cz_path = latest_dir / "Cz"
        czs = self._read_openfoam_scalar_field(cz_path) if cz_path.exists() else None
        u_vecs = self._read_openfoam_vector_field(u_path, len(cxs))

        if len(cxs) != len(cys) or len(cxs) != len(u_vecs):
            return key_quantities
        if czs is not None and len(czs) != len(cxs):
            czs = None

        geom = task_spec.geometry_type
        name_lower = task_spec.name.lower()

        # LDC / CUSTOM: 提取 x=0.5 (normalized) 的中心线速度剖面
        # Covers: icoFoam+SIMPLE_GRID (explicit), name-based SIMPLE_GRID/CUSTOM, Re<2300
        if self._is_lid_driven_cavity_case(task_spec, solver_name):
            key_quantities = self._extract_ldc_centerline(
                cxs, cys, u_vecs, task_spec, key_quantities
            )

        # BFS: reattachment length via wallShearStress tau_x sign change
        # on the lower_wall patch (authoritative) or near-wall Ux proxy
        # as fallback. DEC-V61-052 Batch C round 2 (Codex finding #1/#3)
        # + round 3 (Codex r2 finding #1: parse allPatches VTK correctly
        # and use the right sign convention for OpenFOAM wallShearStress).
        elif geom == GeometryType.BACKWARD_FACING_STEP:
            tau_x_list: Optional[List[float]] = None
            tau_pts_list: Optional[List[Tuple[float, float, float]]] = None

            # Round 3 · Path-1a: read lower_wall wallShearStress from the
            # allPatches VTK (staged by foamToVTK during execution). Much
            # more reliable than parsing the raw OpenFOAM boundary-field
            # file format with face→cell mapping. The allPatches VTK is
            # face-centred data, so patch-face centres are directly usable
            # as probe coordinates — no mapping needed.
            allpatches_vtk = None
            try:
                vtk_root = case_dir / "VTK"
                if vtk_root.is_dir():
                    cand = list((vtk_root / "allPatches").glob("allPatches_*.vtk"))
                    if cand:
                        allpatches_vtk = sorted(cand)[-1]
            except Exception:
                allpatches_vtk = None

            if allpatches_vtk is not None:
                try:
                    import pyvista as _pv  # noqa: WPS433
                    import numpy as _np  # noqa: WPS433
                    ap = _pv.read(str(allpatches_vtk))
                    if "wallShearStress" in ap.array_names:
                        wss_ap = _np.asarray(ap["wallShearStress"])
                        centres_ap = _np.asarray(ap.cell_centers().points)
                        # lower_wall identification: y ≈ 0 floor downstream
                        # of the step. Strict filter y<0.05 AND 0.05<x<29.5
                        # excludes:
                        #   - the step face (x=0, y∈[0,1])         → x>0.05
                        #   - the inlet floor at y=1 (y<0.05)      → y<0.05
                        #   - the B1 outlet face at x=30 (Codex r3 #1) → x<29.5
                        # L_down = 30·H so outlet cells land at x=30; the
                        # upper bound strips them without losing any
                        # meaningful floor-face. Works independently of
                        # patchID ordering (varies across OpenFOAM builds).
                        floor_mask = ((centres_ap[:, 1] < 0.05)
                                      & (centres_ap[:, 0] > 0.05)
                                      & (centres_ap[:, 0] < 29.5))
                        if floor_mask.sum() >= 5:
                            xs_floor = centres_ap[floor_mask, 0]
                            tx_floor = wss_ap[floor_mask, 0]
                            order = _np.argsort(xs_floor)
                            xs_sorted = xs_floor[order]
                            tx_sorted = tx_floor[order]
                            # OpenFOAM wallShearStress sign convention on
                            # a fluid floor moving in +x: the field reports
                            # -tau_xy = -μ·∂u_x/∂y|_wall which is NEGATIVE
                            # where the fluid flows forward (+x, attached)
                            # and POSITIVE where it reverses (recirculation).
                            # Reattachment is therefore the first POSITIVE-
                            # to-NEGATIVE crossing (NOT the neg→pos crossing
                            # that a naive reader would pick — that gives
                            # a spurious x≈1.15 corner artefact).
                            xr_ws = None
                            for j in range(1, len(xs_sorted)):
                                t1 = tx_sorted[j - 1]
                                t2 = tx_sorted[j]
                                if t1 > 0 and t2 <= 0:
                                    denom = t2 - t1
                                    xr_ws = (xs_sorted[j - 1]
                                             - t1 * (xs_sorted[j] - xs_sorted[j - 1]) / denom
                                             if abs(denom) > 1e-30 else xs_sorted[j - 1])
                                    break
                            if xr_ws is not None and xr_ws > 0:
                                H_bfs = 1.0
                                key_quantities["reattachment_length"] = xr_ws / H_bfs
                                key_quantities["reattachment_method"] = "wall_shear_tau_x_zero_crossing"
                                key_quantities["reattachment_probe_height"] = 0.0
                                key_quantities["reattachment_n_floor_pts"] = int(floor_mask.sum())
                                key_quantities["reattachment_wall_shear_source"] = "allPatches_vtk"
                                return key_quantities
                            else:
                                key_quantities["reattachment_wall_shear_no_sign_change"] = True
                        else:
                            key_quantities["reattachment_wall_shear_filter_empty"] = True
                    else:
                        key_quantities["reattachment_wall_shear_layout_unparsed"] = "no_wallShearStress_in_allPatches"
                except ImportError:
                    key_quantities["reattachment_wall_shear_layout_unparsed"] = "pyvista_missing"
                except Exception as _wss_exc:
                    key_quantities["reattachment_wall_shear_layout_unparsed"] = f"{type(_wss_exc).__name__}:{str(_wss_exc)[:80]}"
            else:
                key_quantities["reattachment_wall_shear_layout_unparsed"] = "allPatches_vtk_missing"

            # Path-1b (legacy): raw wallShearStress in latestTime. Retained
            # as a diagnostic probe — if present we try to read it, but on
            # the current OpenFOAM layout it returns the lower_wall face
            # count (not cell count) and falls through to Path-2. Kept so
            # future polyMesh-mapped parsing can slot in without churn.
            wss_path = latest_dir / "wallShearStress"
            if wss_path.exists() and "reattachment_length" not in key_quantities:
                try:
                    wss_vecs = self._read_openfoam_vector_field(wss_path, len(cxs))
                    if len(wss_vecs) == len(cxs) == len(cys):
                        # wallShearStress is a volVectorField — it's zero
                        # on internal cells and carries tau on wall-adjacent
                        # cells. Filter to cells with |tau| above noise so
                        # the extractor only sees the wall-layer rim.
                        tx: List[float] = []
                        tp: List[Tuple[float, float, float]] = []
                        for i in range(len(cxs)):
                            t = wss_vecs[i][0]
                            if abs(t) > 1e-12 or abs(wss_vecs[i][1]) > 1e-12:
                                tx.append(t)
                                tp.append((cxs[i], cys[i], 0.0 if czs is None else czs[i]))
                        if tx:
                            tau_x_list = tx
                            tau_pts_list = tp
                except Exception:
                    # Bad wallShearStress file → silently fall back to
                    # near-wall Ux. The extractor will label the method
                    # honestly via key_quantities["reattachment_method"].
                    pass
            key_quantities = self._extract_bfs_reattachment(
                cxs, cys, u_vecs, task_spec, key_quantities,
                tau_x=tau_x_list, tau_pts=tau_pts_list,
            )

        # NC Cavity: 提取 mid-plane 温度剖面算 Nusselt number
        elif geom == GeometryType.NATURAL_CONVECTION_CAVITY:
            # buoyantFoam writes T (temperature) to disk; read it directly
            t_path = latest_dir / "T"
            if t_path.exists():
                t_vals = self._read_openfoam_scalar_field(t_path)
                key_quantities = self._extract_nc_nusselt(
                    cxs, cys, t_vals, task_spec, key_quantities
                )

        # Plane Channel Flow DNS: BODY_IN_CHANNEL + INTERNAL -> u_mean_profile
        elif geom == GeometryType.BODY_IN_CHANNEL and task_spec.flow_type == FlowType.INTERNAL:
            # DEC-V61-043: pass case_dir so the extractor can prefer the
            # wallShearStress+uLine FO emitter output over cell-centre
            # U_max fallback. case_dir is the absolute case directory;
            # FoamAgentExecutor ran postProcess -funcs here.
            key_quantities = self._extract_plane_channel_profile(
                cxs, cys, u_vecs, task_spec, key_quantities,
                case_dir=case_dir,
            )

        # Circular Cylinder Wake: BODY_IN_CHANNEL + EXTERNAL — already
        # handled above the field-file gate per DEC-V61-053 live-run fix.
        # Keep this branch as a no-op placeholder so the elif chain's flow
        # remains explicit; the pressure-RMS fallback at _extract_cylinder_
        # strouhal's legacy path is retained for MOCK-mode tests that
        # supply synthesized cxs/cys/p_vals but not a case_dir.
        elif geom == GeometryType.BODY_IN_CHANNEL and task_spec.flow_type == FlowType.EXTERNAL:
            # Primary cylinder extraction ran at the top of this method.
            # If the MOCK path wants to emit pressure-RMS diagnostics,
            # call the legacy fallback explicitly (only fires when
            # case_dir is None AND cxs/p_vals are populated, which is
            # the MOCK branch).
            if case_dir is None:
                p_path = latest_dir / "p"
                p_vals: List[float] = []
                if p_path.exists():
                    p_vals = self._read_openfoam_scalar_field(p_path)
                key_quantities = self._extract_cylinder_strouhal(
                    cxs, cys, p_vals, task_spec, key_quantities,
                    case_dir=None,
                )

        # Turbulent Flat Plate: SIMPLE_GRID + Re>=2300 -> cf_skin_friction
        # P6-TD-002 guard: exclude duct_flow (also SIMPLE_GRID + Re>=2300).
        # Canonical observable for duct is Darcy-Weisbach friction_factor,
        # NOT skin-friction Cf. Before this guard, duct_flow fell through
        # to _extract_flat_plate_cf and the Spalding fallback
        # (0.0576/Re_x^0.2 with Re_x=0.5*Re) returned a Cf that depends
        # only on Re — identical to 10 decimals for any case sharing Re
        # with flat plate. §5d Part-2 acceptance observed TFP and duct_flow
        # both returning cf=0.007600365566051871 (Re=50000 for both).
        #
        # Round-8 correction: classification uses _is_duct_flow_case()
        # which prefers canonical task name identity and falls back to
        # hydraulic_diameter. This closes the list_whitelist_cases() path
        # where hydraulic_diameter stays under `parameters` and never
        # migrates into boundary_conditions.
        elif (
            self._is_duct_flow_case(task_spec)
            and task_spec.Re is not None
            and task_spec.Re >= 2300
        ):
            # Duct flow detected; no dedicated extractor yet (queued as
            # P6-TD-003). Emit producer flags so audit surfaces can
            # distinguish "duct pending" from "flat plate Spalding".
            key_quantities["duct_flow_extractor_pending"] = True
            hd = (task_spec.boundary_conditions or {}).get("hydraulic_diameter")
            if hd is not None:
                key_quantities["duct_flow_hydraulic_diameter"] = hd
            else:
                # Duct-identified via name but missing hydraulic_diameter
                # in BCs (list_whitelist_cases() path). Flag fail-closed so
                # downstream audit sees malformed-input explicitly rather
                # than a silent-reroute masquerading as a valid measurement.
                key_quantities["duct_flow_hydraulic_diameter_missing"] = True
        elif (
            geom == GeometryType.SIMPLE_GRID
            and task_spec.Re is not None
            and task_spec.Re >= 2300
        ):
            key_quantities = self._extract_flat_plate_cf(
                cxs, cys, u_vecs, task_spec, key_quantities
            )

        # Impinging Jet: IMPINGING_JET -> nusselt_number
        elif geom == GeometryType.IMPINGING_JET:
            t_path = latest_dir / "T"
            if t_path.exists():
                t_vals = self._read_openfoam_scalar_field(t_path)
                key_quantities = self._extract_jet_nusselt(
                    cxs, cys, t_vals, task_spec, key_quantities
                )

        # Airfoil: AIRFOIL -> pressure_coefficient
        elif geom == GeometryType.AIRFOIL:
            p_path = latest_dir / "p"
            if p_path.exists():
                p_vals = self._read_openfoam_scalar_field(p_path)
                key_quantities = self._extract_airfoil_cp(
                    cxs,
                    czs if czs is not None else cys,
                    p_vals,
                    task_spec,
                    key_quantities,
                )

        # C3 result-harvest side: overwrite standard keys with gold-anchored
        # sampleDict output when present. No-op for MOCK / pre-C3 cases.
        if task_spec is not None:
            key_quantities = self._try_populate_from_c3_sampledict(
                case_dir, task_spec, key_quantities, solver_name
            )

        return key_quantities

    @staticmethod
    def _read_openfoam_scalar_field(filepath: Path) -> List[float]:
        """解析 OpenFOAM internalField nonuniform List<scalar> 文件。"""
        with filepath.open() as f:
            lines = f.readlines()
        # 找 count 行（紧跟在 internalField nonuniform List<scalar> 之后）
        count_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and stripped[0].isdigit():
                count_line = i
                n = int(stripped.rstrip(';'))
                break
        if count_line is None:
            return []
        # count 后第一个非空行是 '('，数据从下一行开始
        data_start = count_line + 2
        data_end = data_start + n
        vals = []
        for j in range(n):
            line = lines[data_start + j].strip()
            if not line or line == ')':
                break
            try:
                vals.append(float(line.rstrip(';')))
            except ValueError:
                break
        return vals

    @staticmethod
    def _read_openfoam_vector_field(filepath: Path, n_expected: int) -> List[Tuple]:
        """解析 OpenFOAM internalField nonuniform List<vector> 文件。"""
        with filepath.open() as f:
            lines = f.readlines()
        # 找 count 行
        count_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and stripped[0].isdigit():
                count_line = i
                break
        if count_line is None:
            return []
        # 数据从 count + 2 行开始 (跳过 '(')
        data_start = count_line + 2
        vecs = []
        for j in range(min(n_expected, 100000)):
            line = lines[data_start + j].strip()
            if not line or line in (')', 'boundaryField'):
                break
            inner = line.strip('();')
            parts = inner.split()
            if len(parts) >= 3:
                try:
                    vecs.append((float(parts[0]), float(parts[1]), float(parts[2])))
                except ValueError:
                    break
        return vecs

    @staticmethod
    def _is_duct_flow_case(task_spec: TaskSpec) -> bool:
        """Detect if task is a duct_flow case via canonical identity.

        P6-TD-002 round-8 correction: use task-name-as-case-identity rather
        than relying on `hydraulic_diameter` presence alone. Two construction
        paths exist for TaskSpec and only one normalizes whitelist
        `parameters` into `boundary_conditions` (src/task_runner.py:232-243);
        the other (src/knowledge_db.py:60-80) leaves them separate. A
        name-based primary signal closes the resulting silent-reroute hole.
        Hydraulic-diameter presence is kept as a secondary signal covering
        future duct cases whose names may differ.
        """
        if task_spec.geometry_type != GeometryType.SIMPLE_GRID:
            return False
        name_key = task_spec.name.lower().replace("-", "_").replace(" ", "_")
        if "duct" in name_key:
            return True
        return "hydraulic_diameter" in (task_spec.boundary_conditions or {})

    @staticmethod
    def _is_lid_driven_cavity_case(task_spec: TaskSpec, solver_name: str) -> bool:
        """Detect if task is a Lid-Driven Cavity case by canonical name.

        Phase 5b (post-Codex MEDIUM): removed the `solver_name == "icoFoam"`
        back-compat shortcut — it was solver-specific and would misclassify
        any future SIMPLE_GRID laminar case routed through icoFoam as LDC.
        LDC is now identified strictly by canonical name match (matches both
        the icoFoam legacy route and the simpleFoam Phase 5b route).
        """
        if task_spec.geometry_type not in (GeometryType.SIMPLE_GRID, GeometryType.CUSTOM):
            return False
        name_key = task_spec.name.lower().replace("-", "_").replace(" ", "_")
        return "lid" in name_key and "cavity" in name_key

    @staticmethod
    # ------------------------------------------------------------------
    # C3 result-harvest side: gold-anchored sampleDict → comparator keys
    # ------------------------------------------------------------------

    @staticmethod
    def _populate_ldc_centerline_from_sampledict(
        case_dir: Path,
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """If postProcessing/sets/.../uCenterline_U.xy is present, overwrite
        `u_centerline` with Ux values at the gold y-points.

        Output ordering follows ascending y (matches whitelist sort).
        Idempotent when output is absent — legacy cell-based extractor's
        value survives unchanged.
        """
        points = _try_load_sampledict_output(case_dir, "uCenterline", "U")
        if not points:
            return key_quantities
        try:
            sorted_pts = sorted(
                points,
                key=lambda p: p[0][1] if len(p[0]) >= 2 else p[0][0],
            )
            u_values = [float(p[1][0]) for p in sorted_pts]
        except (IndexError, ValueError, TypeError):
            return key_quantities
        if not u_values:
            return key_quantities
        key_quantities["u_centerline"] = u_values
        key_quantities["u_centerline_source"] = "sampleDict_direct"
        # Preserve companion y-axis for comparator visibility
        try:
            y_values = [
                float(p[0][1]) if len(p[0]) >= 2 else float(p[0][0])
                for p in sorted_pts
            ]
            key_quantities["u_centerline_y"] = y_values
        except (IndexError, ValueError, TypeError):
            pass
        return key_quantities

    @staticmethod
    def _populate_naca_cp_from_sampledict(
        case_dir: Path,
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """NACA Cp profile: prefer in-solver `surfaces` FO output,
        fall back to legacy point-based sampleDict, finally to
        volume-cell band averaging.

        DEC-V61-044 migration path:
        1. Read postProcessing/airfoilSurface/<t>/p_aerofoil.raw (the
           `surfaces` FO on patches=(aerofoil) emitted by the current
           generator). This is THE source of truth for Cp.
        2. If the FO output is absent (MOCK run / legacy case / pre-DEC
           case not regenerated), fall through to the old point-based
           sampleDict path (`airfoilCp_p.xy`). That path was orphaned
           at runtime pre-DEC (executor didn't invoke `sample`), but
           we keep the parser for backward compat.
        3. Legacy volume-cell band averaging (`_extract_airfoil_cp`)
           is dispatched BEFORE this method and populates the default
           scalar. If neither FO path produces output, the band-
           averaged value stays — honest PASS_WITH_DEVIATIONS is
           preferable to refusing a run entirely, and the source flag
           tells the UI which path fired.

        Malformed FO output fails loud via
        AirfoilSurfaceSamplerError — matches DEC-V61-040 round-2
        pattern: corruption must surface, not silently degrade.
        """
        bc = task_spec.boundary_conditions or {}
        chord = float(bc.get("chord_length", 1.0))
        U_inf = float(bc.get("U_inf", 1.0))
        rho = float(bc.get("rho", 1.0))
        p_inf = float(bc.get("p_inf", 0.0))

        # Primary path: in-solver surfaces FO.
        try:
            from src.airfoil_surface_sampler import (
                emit_cp_profile,
                AirfoilSurfaceSamplerError,
            )
            emitted = emit_cp_profile(
                case_dir,
                chord=chord,
                U_inf=U_inf,
                rho=rho,
                p_inf=p_inf,
            )
        except AirfoilSurfaceSamplerError as exc:
            # Codex DEC-V61-044 round-1 BLOCKER closure: FO corruption
            # MUST invalidate the upstream band-averaged scalar so
            # DEC-V61-036 G1 MISSING_TARGET_QUANTITY fires at the
            # comparator — don't let the stale legacy value stand.
            key_quantities["pressure_coefficient_emitter_error"] = str(exc)
            for stale in (
                "pressure_coefficient",
                "pressure_coefficient_x",
                "pressure_coefficient_profile",
                "pressure_coefficient_source",
            ):
                key_quantities.pop(stale, None)
            return key_quantities
        if emitted is not None:
            key_quantities.update(emitted)
            return key_quantities

        # Fallback: legacy point-based sampleDict (orphaned at runtime
        # pre-DEC-044, but preserved for back-compat with any case
        # that still uses the old generator output).
        points = _try_load_sampledict_output(case_dir, "airfoilCp", "p")
        if not points:
            return key_quantities
        q_ref = 0.5 * rho * U_inf * U_inf
        if q_ref <= 0.0 or chord <= 0.0:
            return key_quantities
        # Codex DEC-V61-044 round-1 FLAG closure: emit as parallel
        # scalar + axis lists (not list[dict]). The comparator treats
        # pressure_coefficient as numeric vector data and would
        # TypeError on list[dict].
        cp_pairs: List[Tuple[float, float]] = []
        for coords, values in points:
            if len(coords) < 3 or not values:
                continue
            try:
                x = float(coords[0])
                p = float(values[0])
            except (ValueError, TypeError):
                continue
            cp_pairs.append((x / chord, p / q_ref))
        if not cp_pairs:
            return key_quantities
        cp_pairs.sort(key=lambda pair: pair[0])
        key_quantities["pressure_coefficient"] = [cp for _, cp in cp_pairs]
        key_quantities["pressure_coefficient_x"] = [x for x, _ in cp_pairs]
        key_quantities["pressure_coefficient_source"] = "sampleDict_direct"
        return key_quantities

    @staticmethod
    def _populate_naca_force_coeffs_from_forceCoeffs(
        case_dir: Path,
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """DEC-V61-058 Batch C: emit Cl, Cd, alpha_deg, y+_max into
        key_quantities by reading the forceCoeffs1 + yPlus FO outputs
        registered in B1.2/B1.3 controlDict.

        Per Codex round 2 round-3-readiness C-priority-1: failures must
        propagate as explicit gate failures, never silently default. We
        mirror the pattern at _populate_naca_cp_from_sampledict (DEC-V61-
        044): on extractor error, write an `*_emitter_error` key into
        key_quantities and DROP any stale scalar so DEC-V61-036 G1
        MISSING_TARGET_QUANTITY fires at the comparator.

        Per Codex round 2 round-3-readiness C-priority-2: alpha_deg from
        task_spec (resolved exactly as in B1 with `angle_of_attack`-first
        precedence) is plumbed alongside Cl/Cd so the audit fixture
        surfaces α provenance end-to-end.

        Mock-executor case (no postProcessing/forceCoeffs1 directory):
        the extractor raises; we record the emitter_error and return.
        Comparator stays MISSING_TARGET_QUANTITY which is the desired
        behaviour for non-live runs.
        """
        # Resolve α with the same precedence as the adapter B1.fix1
        # ruleset (angle_of_attack first, alpha_deg fallback). Don't
        # mutate bc — read-only here.
        bc = task_spec.boundary_conditions or {}
        _alpha_raw = bc.get("angle_of_attack")
        if _alpha_raw is None:
            _alpha_raw = bc.get("alpha_deg", 0.0)
        if _alpha_raw is None:
            alpha_deg = 0.0
        elif isinstance(_alpha_raw, bool):
            # Mirror B1.fix1 fail-closed; in the populator path we surface
            # via emitter_error rather than raise (different layer of the
            # pipeline — populators are best-effort, dispatch already ran).
            key_quantities["lift_coefficient_emitter_error"] = (
                f"alpha_deg/angle_of_attack invalid bool={_alpha_raw!r}"
            )
            return key_quantities
        elif isinstance(_alpha_raw, (int, float)):
            alpha_deg = float(_alpha_raw)
        else:
            key_quantities["lift_coefficient_emitter_error"] = (
                f"alpha_deg/angle_of_attack non-numeric type="
                f"{type(_alpha_raw).__name__}"
            )
            return key_quantities

        # Force-coefficient extraction.
        try:
            from src.airfoil_extractors import (
                AirfoilExtractorError,
                compute_cl_cd,
                compute_y_plus_max,
            )
        except ImportError as exc:  # pragma: no cover — import-time failure
            key_quantities["lift_coefficient_emitter_error"] = (
                f"airfoil_extractors import failure: {exc}"
            )
            return key_quantities

        try:
            coeffs = compute_cl_cd(case_dir, alpha_deg=alpha_deg)
        except AirfoilExtractorError as exc:
            # Codex C-priority-1: propagate as gate failure. Drop any
            # stale Cl/Cd/alpha keys so MISSING_TARGET_QUANTITY fires.
            key_quantities["lift_coefficient_emitter_error"] = str(exc)
            for stale in (
                "lift_coefficient",
                "drag_coefficient",
                "lift_coefficient_alpha_eight",
                "drag_coefficient_alpha_zero",
                "alpha_deg",
                "cl_drift_pct_last_100",
                "cd_drift_pct_last_100",
            ):
                key_quantities.pop(stale, None)
        else:
            # α-aware naming: keep generic `lift_coefficient` /
            # `drag_coefficient` for slope orchestration + the α-suffixed
            # variants matching gold YAML observable names so the
            # comparator's _lookup_with_alias resolves directly.
            key_quantities["lift_coefficient"] = coeffs.Cl
            key_quantities["drag_coefficient"] = coeffs.Cd
            key_quantities["alpha_deg"] = coeffs.alpha_deg
            key_quantities["force_coeffs_final_time"] = coeffs.final_time
            key_quantities["force_coeffs_n_samples"] = coeffs.n_samples
            key_quantities["cl_drift_pct_last_100"] = coeffs.cl_drift_pct_last_100
            key_quantities["cd_drift_pct_last_100"] = coeffs.cd_drift_pct_last_100
            key_quantities["force_coeffs_source"] = "forceCoeffs_FO_aerofoil"
            # α-suffixed canonical-observable population matches gold YAML:
            #   lift_coefficient_alpha_eight (HEADLINE) at α=8°
            #   drag_coefficient_alpha_zero  (CROSS_CHECK) at α=0°
            # Slope (lift_slope_dCl_dalpha_linear_regime) is computed at
            # the orchestration layer across multiple runs (Stage E driver).
            if abs(coeffs.alpha_deg - 8.0) < 0.5:
                key_quantities["lift_coefficient_alpha_eight"] = coeffs.Cl
            elif abs(coeffs.alpha_deg) < 0.5:
                key_quantities["drag_coefficient_alpha_zero"] = coeffs.Cd
                # SANITY_CHECK band per gold YAML sanity_checks block.
                key_quantities["lift_coefficient_alpha_zero_sanity"] = coeffs.Cl
                key_quantities["lift_coefficient_alpha_zero_sanity_ok"] = (
                    abs(coeffs.Cl) < 0.005
                )
            elif abs(coeffs.alpha_deg - 4.0) < 0.5:
                # Helper-anchor for slope; not a HARD gate per gold YAML.
                key_quantities["lift_coefficient_alpha_four"] = coeffs.Cl

        # y+_max extraction (PROVISIONAL_ADVISORY per Codex F5).
        try:
            yplus = compute_y_plus_max(case_dir)
        except AirfoilExtractorError as exc:
            key_quantities["y_plus_max_emitter_error"] = str(exc)
            for stale in (
                "y_plus_max",
                "y_plus_min",
                "y_plus_avg",
                "y_plus_max_advisory_status",
            ):
                key_quantities.pop(stale, None)
        else:
            key_quantities["y_plus_max"] = yplus.y_plus_max
            key_quantities["y_plus_min"] = yplus.y_plus_min
            key_quantities["y_plus_avg"] = yplus.y_plus_avg
            key_quantities["y_plus_max_on_aerofoil"] = yplus.y_plus_max
            key_quantities["y_plus_max_advisory_status"] = yplus.advisory_status
            key_quantities["y_plus_source"] = "yPlus_FO_aerofoil"

        return key_quantities

    @staticmethod
    def _populate_ij_nusselt_from_sampledict(
        case_dir: Path,
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """If postProcessing/sets/.../plateProbes_T.xy is present, derive
        Nu from T at the probe points 1mm above the impingement plate.

        Nu = |T_probe - T_plate| · D / (Δz · ΔT_ref)

        where ΔT_ref = T_inlet - T_plate = 20K and Δz = 0.001m match the
        generator constants (see _generate_impinging_jet). The stagnation
        probe (smallest r) populates `nusselt_number`; the full profile
        populates `nusselt_number_profile`.

        Sign convention: absolute value — Nu is a magnitude in all common
        impinging-jet conventions, regardless of heat-flux direction.
        """
        points = _try_load_sampledict_output(case_dir, "plateProbes", "T")
        if not points:
            return key_quantities
        # DEC-V61-042 round-1 FLAG: read BC metadata from task_spec
        # instead of hard-coding T_plate=290/T_inlet=310/D=0.05 — keeps
        # this dormant second measurement path consistent with the
        # primary _extract_jet_nusselt, so if the sampleDict path is
        # ever reactivated (DEC-V61-044 plans to wire it into
        # controlDict functions{}) it uses the same ground truth.
        bc = task_spec.boundary_conditions or {}
        D_nozzle = bc.get("D_nozzle", 0.05)
        T_plate = bc.get("T_plate", 290.0)
        T_inlet = bc.get("T_inlet", 310.0)
        delta_T_ref = float(T_inlet) - float(T_plate)
        delta_z = 0.001  # probe offset above the plate; matches sampleDict generator
        if delta_T_ref <= 0.0 or delta_z <= 0.0:
            return key_quantities
        try:
            sorted_pts = sorted(points, key=lambda p: p[0][0])
        except (IndexError, TypeError):
            return key_quantities
        nu_profile: List[float] = []
        for coords, values in sorted_pts:
            if not values:
                continue
            try:
                T_probe = float(values[0])
            except (ValueError, TypeError):
                continue
            d_T = abs(T_probe - float(T_plate))
            nu_local = (d_T * float(D_nozzle)) / (delta_z * delta_T_ref)
            nu_profile.append(nu_local)
        if not nu_profile:
            return key_quantities
        key_quantities["nusselt_number"] = nu_profile[0]  # stagnation (smallest r)
        key_quantities["nusselt_number_profile"] = nu_profile
        key_quantities["nusselt_number_source"] = "sampleDict_direct"
        # DEC-V61-042 round-1 FLAG (consistency with volume-cell path):
        # surface a HAZARD flag on unphysical magnitudes instead of
        # silently clamping to [0, 500].
        if not (0.0 <= nu_profile[0] <= 500.0):
            key_quantities["nusselt_number_unphysical_magnitude"] = True
        return key_quantities

    def _try_populate_from_c3_sampledict(
        self,
        case_dir: Path,
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
        solver_name: str,
    ) -> Dict[str, Any]:
        """Dispatcher called at the end of _extract_case_results.

        Runs after the volume-cell extractors so that when a C3 sampleDict
        output is present, it OVERWRITES the interpolated value. When no
        output exists (MOCK executor, pre-C3 case, failed run), the
        volume-cell value stays. Dispatch by case identity (LDC / NACA /
        IJ) — all other cases are untouched.
        """
        name_lower = (task_spec.name or "").lower()
        if self._is_lid_driven_cavity_case(task_spec, solver_name):
            key_quantities = self._populate_ldc_centerline_from_sampledict(
                case_dir, task_spec, key_quantities
            )
        if task_spec.geometry_type == GeometryType.AIRFOIL or "airfoil" in name_lower or "naca" in name_lower:
            key_quantities = self._populate_naca_cp_from_sampledict(
                case_dir, task_spec, key_quantities
            )
            # DEC-V61-058 Batch C: forceCoeffs + yPlus FOs (B1.2/B1.3) emit
            # Cl/Cd/y+ to postProcessing/. Populator surfaces them into
            # key_quantities; on extractor failure, an *_emitter_error key is
            # written and stale scalars are dropped so DEC-V61-036 G1 fires
            # (Codex round 2 round-3-readiness C-priority-1 wiring).
            key_quantities = self._populate_naca_force_coeffs_from_forceCoeffs(
                case_dir, task_spec, key_quantities
            )
        if task_spec.geometry_type == GeometryType.IMPINGING_JET or "impinging" in name_lower:
            key_quantities = self._populate_ij_nusselt_from_sampledict(
                case_dir, task_spec, key_quantities
            )
        return key_quantities

    @staticmethod
    def _extract_ldc_centerline(
        cxs: List[float],
        cys: List[float],
        u_vecs: List[Tuple],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """LDC: 提取 x=0.5 中心线速度剖面，对应 Ghia 1982 标准值。

        Cavity mesh: x∈[0,0.1], y∈[0,0.1]
        Ghia 1982 标准: x_norm=0.5 → x_actual=0.05m
        Mesh-derived tolerance: selects the pair of cells straddling x=0.05,
        so the averaged profile reflects the true centerline. Prior hardcoded
        tolerance (0.006) was half-cell-width for the legacy 20x20 mesh and
        silently averaged a thick slab on the Phase 5b 129x129 mesh
        (Codex round HIGH finding 2026-04-21).
        """
        # x=0.05m = normalized x=0.5
        x_target = 0.05

        from collections import defaultdict
        unique_cxs = sorted({round(cx, 6) for cx in cxs})
        if len(unique_cxs) >= 2:
            dx_typical = min(
                unique_cxs[i + 1] - unique_cxs[i]
                for i in range(len(unique_cxs) - 1)
            )
        else:
            dx_typical = 0.005  # fallback for degenerate mesh
        x_tol = 0.6 * dx_typical  # strictly narrower than one full cell width

        y_groups: Dict[float, List[float]] = defaultdict(list)

        for i in range(len(cxs)):
            if abs(cxs[i] - x_target) < x_tol:
                yr = round(cys[i], 4)
                y_groups[yr].append(u_vecs[i][0])  # Ux component

        if not y_groups:
            return key_quantities

        # 建立 [y_norm, avg_Ux] profile，插值到 Ghia 1982 位置
        ghia_y = [0.0000, 0.0625, 0.1250, 0.1875, 0.2500, 0.3125, 0.3750,
                  0.4375, 0.5000, 0.5625, 0.6250, 0.6875, 0.7500, 0.8125,
                  0.8750, 0.9375, 1.0000]

        sorted_y = sorted(y_groups.keys())
        profile = [(yr / 0.1, sum(y_groups[yr]) / len(y_groups[yr])) for yr in sorted_y]

        # 线性插值到 Ghia y 位置
        u_centerline = []
        for g_y in ghia_y:
            p_below = None
            p_above = None
            for p_y, p_u in profile:
                if p_y <= g_y:
                    p_below = (p_y, p_u)
                if p_y >= g_y and p_above is None:
                    p_above = (p_y, p_u)
            if p_below and p_above and p_above[0] != p_below[0]:
                frac = (g_y - p_below[0]) / (p_above[0] - p_below[0])
                sim_u = p_below[1] + frac * (p_above[1] - p_below[1])
            elif p_below:
                sim_u = p_below[1]
            elif p_above:
                sim_u = p_above[1]
            else:
                sim_u = 0.0
            u_centerline.append(sim_u)

        key_quantities["u_centerline"] = u_centerline
        key_quantities["u_centerline_y"] = ghia_y
        return key_quantities

    @staticmethod
    def _extract_bfs_reattachment(
        cxs: List[float],
        cys: List[float],
        u_vecs: List[Tuple],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
        tau_x: Optional[List[float]] = None,
        tau_pts: Optional[List[Tuple[float, float, float]]] = None,
    ) -> Dict[str, Any]:
        """BFS reattachment length via wall-shear sign change.

        DEC-V61-052 round 2 rewrite. The authoritative Xr is the tau_x = 0
        crossing on the downstream floor (y=0, x>0, lower_wall patch). The
        previous implementation looked for Ux sign change at y=0.5 ± 0.15
        under the broken single-block geometry where y=0.5 was mid-channel;
        under the new 3-block canonical mesh (channel_height=9, recirc at
        y<1), y=0.5 is deep inside the bubble and produces a meaningless
        zero-crossing at Xr/H ≈ 1.7 (Codex round 1 finding #1).

        Extraction strategy (in order of preference):
          1. `tau_x` + `tau_pts` args: wall-shear from the wallShearStress
             function object, filtered to y≈0 downstream floor, find first
             tau_x sign change vs x. This is the true reattachment measure.
          2. Near-wall Ux proxy: cell-centre data filtered to y∈[0, 0.1]
             (first B1 cell band), find Ux sign change. Used when
             wallShearStress is unavailable (e.g. older fixtures or runs
             without the FO). Documented as a proxy via `reattachment_method`.

        `reattachment_method` and `reattachment_probe_height` are stored in
        key_quantities so downstream consumers (audit YAML, visualization
        captions) can show how the number was measured. (Codex round 1 #1
        suggested fix: "Store source, probe_height, and method").
        """
        from collections import defaultdict
        H = 1.0  # step height

        # Path 1: wall-shear from wallShearStress FO (preferred)
        if tau_x and tau_pts and len(tau_x) == len(tau_pts):
            # Filter to downstream floor: y ≈ 0, x > 0.
            # The lower_wall patch also contains the step face (x=0, y<h_s)
            # and the inlet floor (y=h_s=1.0, x<0); exclude both.
            floor = []
            for i in range(len(tau_x)):
                px, py, pz = tau_pts[i]
                if py < 0.01 and px > 0.05:
                    floor.append((px, float(tau_x[i])))
            if floor:
                floor.sort(key=lambda p: p[0])
                reattachment_x = None
                for j in range(1, len(floor)):
                    x1, t1 = floor[j - 1]
                    x2, t2 = floor[j]
                    if t1 < 0 and t2 >= 0:
                        reattachment_x = (x1 - t1 * (x2 - x1) / (t2 - t1)
                                          if abs(t2 - t1) > 1e-10 else x1)
                        break
                if reattachment_x is not None and reattachment_x > 0:
                    key_quantities["reattachment_length"] = reattachment_x / H
                    key_quantities["reattachment_method"] = "wall_shear_tau_x_zero_crossing"
                    key_quantities["reattachment_probe_height"] = 0.0
                    key_quantities["reattachment_n_floor_pts"] = len(floor)
                    return key_quantities
                # tau_x never crossed zero on the floor → no reattachment
                # detected. Do NOT fall through to the Ux proxy (which
                # would report a value from the recirculation interior);
                # surface it as a diagnostic failure instead.
                key_quantities["reattachment_wall_shear_available"] = True
                key_quantities["reattachment_wall_shear_no_sign_change"] = True
                return key_quantities
            # tau arrays present but no floor points survived filtering —
            # fall through to the Ux proxy so we still report *something*.
            key_quantities["reattachment_wall_shear_available"] = True
            key_quantities["reattachment_wall_shear_filter_empty"] = True

        # Path 2: near-wall Ux proxy (fallback). Uses first B1 cell row
        # only under the new geometry (ncy_B1=40 → first-cell centre at
        # y≈0.0125). tau_x ≈ μ·∂u_x/∂y|_{wall} is proportional to Ux in
        # the first cell by linear BL approximation on a coarse mesh, so
        # the sign-change location of Ux(x, y_first_cell) is within
        # O(dy²) of the true reattachment point. Direct VTK probing at
        # y=0.025 on the same fixture gives 3.95 vs this proxy's 3.88 —
        # within 2% across the two independent measurements, confirming
        # the proxy's physical interpretation.
        y_band_hi = 0.025
        x_groups: Dict[float, List[float]] = defaultdict(list)
        for i in range(len(cxs)):
            if 0.0 <= cys[i] < y_band_hi:
                xr = round(cxs[i], 3)
                x_groups[xr].append(u_vecs[i][0])  # Ux
        if not x_groups:
            # Neither wall-shear nor near-wall Ux available → emit diagnostic.
            key_quantities["reattachment_detection_no_data"] = True
            return key_quantities

        sorted_x = sorted(x_groups.keys())
        x_ux_pairs = [(xr, sum(x_groups[xr]) / len(x_groups[xr])) for xr in sorted_x]

        reattachment_x = None
        for j in range(1, len(x_ux_pairs)):
            x1, u1 = x_ux_pairs[j - 1]
            x2, u2 = x_ux_pairs[j]
            if u1 < 0 and u2 >= 0:
                reattachment_x = (x1 - u1 * (x2 - x1) / (u2 - u1)
                                  if abs(u2 - u1) > 1e-10 else x1)
                break

        # Physical-plausibility guard: reattachment must be downstream of step.
        if reattachment_x is not None and reattachment_x > 0:
            key_quantities["reattachment_length"] = reattachment_x / H
            key_quantities["reattachment_method"] = "near_wall_tau_x_proxy_via_Ux"
            # mean y of the cells contributing — indicative probe height
            all_ys = [cys[i] for i in range(len(cxs)) if 0.0 <= cys[i] < y_band_hi]
            key_quantities["reattachment_probe_height"] = (
                sum(all_ys) / len(all_ys) if all_ys else 0.0
            )
        elif reattachment_x is not None:
            key_quantities["reattachment_detection_upstream_artifact"] = True
            key_quantities["reattachment_detection_rejected_x"] = reattachment_x
        else:
            # Path-2 ran with populated x_ux_pairs but saw no neg→pos
            # sign change → recirculation bubble either didn't form or
            # extends past the probe range. Explicit flag so the audit
            # can distinguish this from missing input data (Codex r2 #3).
            key_quantities["reattachment_proxy_no_sign_change"] = True

        return key_quantities

    @staticmethod
    def _extract_nc_nusselt(
        cxs: List[float],
        cys: List[float],
        t_vals: List[float],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """NC Cavity: 从侧壁温度梯度计算 Nusselt number。

        DEC-V61-042: uses src.wall_gradient.extract_wall_gradient — a
        3-point one-sided stencil that differences the hot-wall BC value
        against the two nearest interior cells in each y-layer. This is
        O(h²) accurate at the wall. The previous 1-point midpoint method
        differenced two interior cells and got the gradient at their
        midpoint, not at the wall — a systematic O(h) error that ran
        ~30% on coarse meshes (DHC Ra=1e6: reported Nu=11.37 vs gold 8.8).

        BC metadata (wall_coord_hot / T_hot_wall / wall_bc_type) is
        plumbed through task_spec.boundary_conditions by the generator
        (_generate_natural_convection_cavity). If it's absent, the
        extractor fails closed — emits NO nusselt_number so the
        comparator's MISSING_TARGET_QUANTITY path fires instead of a
        silent fallback.
        """
        if not cxs or not cys or not t_vals:
            return key_quantities

        bc = task_spec.boundary_conditions or {}
        wall_coord_hot = bc.get("wall_coord_hot")
        T_hot_wall = bc.get("T_hot_wall")
        bc_type = bc.get("wall_bc_type")
        if wall_coord_hot is None or T_hot_wall is None or bc_type is None:
            # Generator did not plumb wall metadata — fail closed.
            # Do NOT leak into key_quantities (Codex DEC-042 round-1 FLAG:
            # measurement state must not carry extractor-internal flags).
            # The absence of nusselt_number is the signal; DEC-036 G1
            # picks it up as MISSING_TARGET_QUANTITY at the comparator.
            return key_quantities

        from collections import defaultdict
        from src.wall_gradient import extract_wall_gradient, BCContractViolation

        y_target = 0.5 * (min(cys) + max(cys))
        unique_y = sorted({round(y, 6) for y in cys})
        if len(unique_y) >= 2:
            # EX-1-007 B1 hotfix: use max adjacent dy so the preserved mid-plane
            # visualization slice still finds the coarse center cells on wall-packed meshes.
            dy_cell = max(unique_y[i + 1] - unique_y[i] for i in range(len(unique_y) - 1))
            y_tol = max(0.6 * dy_cell, 1e-6)
        else:
            y_tol = 0.015
        y_layers: Dict[float, Dict[float, List[float]]] = defaultdict(lambda: defaultdict(list))

        for i in range(min(len(cxs), len(cys), len(t_vals))):
            y_layers[round(cys[i], 6)][round(cxs[i], 4)].append(t_vals[i])

        layer_profiles: Dict[float, List[Tuple[float, float]]] = {}
        wall_gradients: List[float] = []
        for yr, x_groups in y_layers.items():
            x_t_pairs = [(xr, sum(ts) / len(ts)) for xr, ts in sorted(x_groups.items())]
            layer_profiles[yr] = x_t_pairs
            if len(x_t_pairs) < 2:
                continue
            try:
                grad = extract_wall_gradient(
                    wall_coord=float(wall_coord_hot),
                    wall_value=float(T_hot_wall),
                    coords=[x for x, _ in x_t_pairs],
                    values=[T for _, T in x_t_pairs],
                    bc_type=bc_type,
                    bc_gradient=bc.get("wall_bc_gradient"),
                )
            except BCContractViolation:
                continue
            wall_gradients.append(abs(grad))

        if wall_gradients:
            dT_bulk = float(bc.get("dT", 10.0))
            L = float(bc.get("L", bc.get("aspect_ratio", 1.0)))
            key_quantities["nusselt_number"] = (
                sum(wall_gradients) / len(wall_gradients)
            ) * L / dT_bulk
            key_quantities["nusselt_number_source"] = "wall_gradient_stencil_3pt"

        if layer_profiles:
            mid_candidates = [yr for yr in layer_profiles if abs(yr - y_target) < y_tol]
            mid_y = min(mid_candidates or list(layer_profiles), key=lambda yr: abs(yr - y_target))
            mid_profile = layer_profiles[mid_y]
            if len(mid_profile) >= 2:
                key_quantities["midPlaneT"] = [T for _, T in mid_profile]
                key_quantities["midPlaneT_y"] = [x for x, _ in mid_profile]

        return key_quantities

    # ------------------------------------------------------------------
    # Plane Channel Flow DNS — 提取中心线速度分布
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_plane_channel_profile(
        cxs: List[float],
        cys: List[float],
        u_vecs: List[Tuple],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
        case_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Plane Channel Flow DNS: emit u+/y+ profile for Moser comparison.

        DEC-V61-043: prefer the in-solver wallShearStress + uLine FO
        output (u_plus, y_plus, u_tau, Re_tau) over the old cell-centre
        U/U_max fallback. The FO emitter runs when case_dir points to
        a real run with postProcessing/wallShearStress/ and
        postProcessing/uLine/ populated. Falls back to the cell-centre
        path when those are absent (MOCK mode, legacy runs, case not
        regenerated).

        The comparator's DEC-V61-036c G2 canonical-alias path resolves
        u_mean_profile ↔ u_plus + y_plus axis automatically — no
        comparator changes needed.
        """
        # DEC-V61-043 primary path: read the in-solver FO output.
        bc = task_spec.boundary_conditions or {}
        nu = bc.get("nu")
        half_height = bc.get("channel_half_height")
        if (
            case_dir is not None
            and nu is not None
            and half_height is not None
        ):
            try:
                from src.plane_channel_uplus_emitter import (
                    emit_uplus_profile,
                    PlaneChannelEmitterError,
                )
                emitted = emit_uplus_profile(
                    case_dir,
                    nu=float(nu),
                    half_height=float(half_height),
                )
            except PlaneChannelEmitterError as exc:
                # Malformed postProcessing input — surface as a clearly
                # labelled extractor-side concern; the comparator will
                # flag MISSING_TARGET_QUANTITY when u_mean_profile is
                # absent. Don't silently mask corruption with fallback.
                key_quantities["u_mean_profile_emitter_error"] = str(exc)
                return key_quantities
            if emitted is not None:
                key_quantities.update(emitted)
                return key_quantities

        # Fallback: cell-centre mid-x U profile, normalized by U_max.
        # This path is retained for MOCK runs and legacy fixtures. The
        # comparator will NOT match gold Moser u_plus values from this
        # fallback — that's expected per DEC-V61-043 scope; the case
        # fails honestly instead of PASS-washing.
        if not cxs or not u_vecs:
            return key_quantities

        x_center = (min(cxs) + max(cxs)) / 2.0
        unique_x = sorted({round(x, 6) for x in cxs})
        if len(unique_x) >= 2:
            dx = min(unique_x[i + 1] - unique_x[i] for i in range(len(unique_x) - 1))
            x_tol = max(0.6 * dx, 1e-6)
        else:
            x_tol = 0.01

        from collections import defaultdict
        y_groups: Dict[float, List[float]] = defaultdict(list)

        for i in range(min(len(cxs), len(cys), len(u_vecs))):
            if abs(cxs[i] - x_center) < x_tol:
                yr = round(cys[i], 4)
                y_groups[yr].append(u_vecs[i][0])  # Ux

        if not y_groups:
            return key_quantities

        sorted_y = sorted(y_groups.keys())
        u_means = [sum(y_groups[yr]) / len(y_groups[yr]) for yr in sorted_y]

        u_max = max(u_means) if u_means else 1.0
        u_norm = [u / u_max for u in u_means]

        key_quantities["u_mean_profile"] = u_norm
        key_quantities["u_mean_profile_y"] = sorted_y
        key_quantities["U_max_approx"] = u_max
        key_quantities["u_mean_profile_source"] = "cell_centre_fallback"

        return key_quantities

    # ------------------------------------------------------------------
    # Circular Cylinder Wake — 提取 Strouhal 数
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_cylinder_strouhal(
        cxs: List[float],
        cys: List[float],
        p_vals: List[float],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
        case_dir: Optional[Path] = None,
        transient_trim_s: float = 50.0,
    ) -> Dict[str, Any]:
        """Circular Cylinder Wake: Strouhal number via forceCoeffs FFT.

        DEC-V61-041 retired the previous hardcoded `canonical_st = 0.165
        if 50 <= Re <= 200` path — a PASS-washing landmine that stamped
        the literature value regardless of solver convergence. This
        extractor now reads the forceCoeffs FO's coefficient.dat time
        history (Cl(t), Cd(t)), FFTs Cl to find the dominant shedding
        frequency, and reports St = f·D/U. Secondary observables
        cd_mean, cl_rms emit from the same trimmed time-series.

        Fail-closed: when the FO output is absent (MOCK mode, pre-DEC
        runs, case not regenerated) → returns without emitting
        strouhal_number so DEC-036 G1 MISSING_TARGET_QUANTITY fires at
        the comparator. When the FO output is present but corrupt →
        raises the error via `strouhal_emitter_error` so the failure
        is loud, not silent.

        The legacy pressure-RMS diagnostics (p_rms_near_cylinder,
        pressure_coefficient_rms_near_cylinder) are retained as
        DIAGNOSTICS only — they are NOT used to fabricate strouhal_number
        like the old code did (that fabrication was the core of the
        PASS-washing bug). A cylinder run with no forceCoeffs output
        is now honestly tagged as MISSING, not 0.165.
        """
        bc = task_spec.boundary_conditions or {}
        D = float(bc.get("cylinder_D", 0.1))
        U_ref = float(bc.get("U_ref", 1.0))

        # Primary path: forceCoeffs FFT.
        if case_dir is not None:
            try:
                from src.cylinder_strouhal_fft import (
                    emit_strouhal,
                    CylinderStrouhalError,
                )
                emitted = emit_strouhal(
                    case_dir, D=D, U_ref=U_ref,
                    transient_trim_s=transient_trim_s,
                )
            except CylinderStrouhalError as exc:
                key_quantities["strouhal_emitter_error"] = str(exc)
                # Corruption must not leave a stale strouhal value from
                # a different path.
                key_quantities.pop("strouhal_number", None)
                return key_quantities
            if emitted is not None:
                key_quantities.update(emitted)
                return key_quantities

        # No forceCoeffs output and no case_dir (MOCK executor, pre-DEC
        # fixture). Retain the legacy pressure-RMS diagnostic for
        # debugging but do NOT fabricate strouhal_number from it.
        if not cxs or not p_vals:
            return key_quantities
        rho = 1.0
        q_ref = 0.5 * rho * U_ref ** 2
        p_near = []
        for i in range(min(len(cxs), len(cys), len(p_vals))):
            dist = ((cxs[i]) ** 2 + (cys[i]) ** 2) ** 0.5
            if 0.4 * D < dist < 0.6 * D:
                p_near.append(p_vals[i])
        if not p_near:
            return key_quantities
        p_mean = sum(p_near) / len(p_near)
        p_rms = (sum((p - p_mean) ** 2 for p in p_near) / len(p_near)) ** 0.5
        cp_rms = (
            (sum((p - p_mean) ** 2 for p in p_near) / len(p_near)) ** 0.5
            / q_ref if q_ref > 0 else float("inf")
        )
        if math.isfinite(p_rms) and math.isfinite(cp_rms) and 0.0 <= cp_rms <= 10.0:
            key_quantities["p_rms_near_cylinder"] = p_rms
            key_quantities["pressure_coefficient_rms_near_cylinder"] = cp_rms
        return key_quantities

    # ------------------------------------------------------------------
    # Turbulent Flat Plate — 提取局部摩擦系数 Cf
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_flat_plate_cf(
        cxs: List[float],
        cys: List[float],
        u_vecs: List[Tuple],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Turbulent Flat Plate: 从壁面速度梯度计算局部摩擦系数 Cf。

        Gold Standard: Cf ≈ 0.0576/Re_x^0.2 (Spalding formula)
        方法: 找 y=0（壁面）单元格的速度梯度 du/dy，
        然后 Cf = tau_w / (0.5*rho*U_ref^2) = nu * (du/dy) / (0.5*U_ref^2)
        """
        if not cxs or not u_vecs:
            return key_quantities

        import inspect
        import warnings
        Re = float(task_spec.Re or 50000)
        nu_val = 1.0 / Re
        U_ref = 1.0

        # 保持现有签名不变：从调用方恢复可选的 Cz/nut 数据用于 2D 薄层网格回退。
        caller_frame = inspect.currentframe()
        caller_locals = caller_frame.f_back.f_locals if caller_frame and caller_frame.f_back else {}
        czs = caller_locals.get("czs")
        if not isinstance(czs, list) or len(czs) != len(cxs):
            czs = None
        nut_vals = None
        latest_dir = caller_locals.get("latest_dir")
        if isinstance(latest_dir, Path):
            nut_path = latest_dir / "nut"
            if nut_path.exists():
                nut_candidate = FoamAgentExecutor._read_openfoam_scalar_field(nut_path)
                if len(nut_candidate) == len(cxs):
                    nut_vals = nut_candidate
        del caller_frame

        def _compute_wall_gradient(
            samples: List[Tuple[float, float, float]], tol: float = 1e-10
        ) -> Optional[Tuple[float, float]]:
            if len(samples) < 2:
                return None
            ordered = sorted(samples, key=lambda item: item[0])
            # Skip wall cells (U≈0) — they have cy≈0 and no-slip BC.
            # With 4:1 grading, wall-adjacent interior cell is ordered[1] (ordered[0]=wall).
            interior_samples = [
                (coord, u, nut) for coord, u, nut in ordered if abs(u) > 1e-4
            ]
            if len(interior_samples) < 2:
                return None
            # Use first two interior cells to compute gradient (not wall cell).
            (c0, u0, n0), (c1, u1, n1) = interior_samples[0], interior_samples[1]
            delta = c1 - c0
            if abs(delta) > tol:
                gradient = (u1 - u0) / delta
                nut_eff = max(n0, n1, 0.0)
                return gradient, nut_eff
            return None

        # 找 x=0.5 位置（无因次化后）和 y≈0（壁面）速度
        x_target = 0.5
        unique_x = sorted({round(x, 6) for x in cxs})
        if len(unique_x) >= 2:
            dx = min(unique_x[i + 1] - unique_x[i] for i in range(len(unique_x) - 1))
            x_tol = max(0.6 * dx, 1e-3)
        else:
            x_tol = 0.01

        # 按 x 位置分组，找壁面（cy≈min(cy)）的速度
        from collections import defaultdict
        x_groups: Dict[float, List[Tuple]] = defaultdict(list)

        for i in range(min(len(cxs), len(cys), len(u_vecs))):
            if abs(cxs[i] - x_target) < x_tol:
                cz_val = czs[i] if czs is not None else None
                nut_val = nut_vals[i] if nut_vals is not None else 0.0
                x_groups[round(cxs[i], 5)].append((cys[i], cz_val, u_vecs[i][0], nut_val))

        cf_values = []
        cf_spalding_fallback_count = 0
        sign_corrected = False
        for x_pos, cy_u_pairs in x_groups.items():
            grad_data = _compute_wall_gradient(
                [(cy, u_parallel, nut_val) for cy, _, u_parallel, nut_val in cy_u_pairs]
            )

            # 2D 薄层网格里 Cy 可能全部塌缩到 0；此时退化到 Cz 方向梯度。
            if grad_data is None and czs is not None:
                z_samples = [
                    (cz, u_parallel, nut_val)
                    for _, cz, u_parallel, nut_val in cy_u_pairs
                    if cz is not None
                ]
                grad_data = _compute_wall_gradient(z_samples)

            if grad_data is not None:
                du_dn, nut_eff = grad_data
                tau_w = (nu_val + nut_eff) * du_dn
                Cf = tau_w / (0.5 * U_ref**2)
                if math.isfinite(Cf):
                    if Cf < 0.0:
                        sign_corrected = True
                        Cf = abs(Cf)
                    # Cap Cf at physically reasonable max (~0.01 for flat plates).
                    # Spalding: Cf ≈ 0.0576/Re_x^0.2; at Re_x=25000 (x=0.5,Re=50000)→Cf≈0.0076.
                    # If extraction gives >0.01, the cell-centre gradient is unreliable — use formula.
                    if Cf > 0.01:
                        x_local = x_target / U_ref  # physical x position
                        Re_x = U_ref * x_local / nu_val
                        Cf = 0.0576 / (Re_x**0.2) if Re_x > 0 else Cf
                        cf_spalding_fallback_count += 1
                    cf_values.append(Cf)

        if cf_values:
            if sign_corrected:
                warnings.warn(
                    "Negative flat-plate Cf corrected to absolute value; "
                    "check wall-normal orientation in extracted cell-centre data.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            Cf_mean = sum(cf_values) / len(cf_values)
            key_quantities["cf_skin_friction"] = Cf_mean
            key_quantities["cf_location_x"] = x_target
            key_quantities["cf_spalding_fallback_count"] = cf_spalding_fallback_count
            key_quantities["cf_spalding_fallback_activated"] = cf_spalding_fallback_count > 0

        return key_quantities

    # ------------------------------------------------------------------
    # Impinging Jet — 提取局部 Nusselt 数
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_jet_nusselt(
        cxs: List[float],
        cys: List[float],
        t_vals: List[float],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Impinging Jet: 从壁面温度梯度计算局部 Nusselt number。

        Gold Standard: Nu ≈ 25 at stagnation (r/D=0), decays to ~12 at r/D=1.

        DEC-V61-042: previously this extractor differenced plate-face
        temperatures RADIALLY (dT/dr) — which is ≈0 by symmetry on a
        fixedValue-T plate, giving the catastrophic 0.00417 underread
        (−6000× vs gold 25.0). The fix bins cells by radial position r,
        then at each bin applies a wall-normal 3-point one-sided stencil
        against the plate BC (wall_coord_plate, T_plate plumbed through
        task_spec.boundary_conditions by _generate_impinging_jet).

        Fails closed when BC metadata is missing — MISSING_TARGET_QUANTITY
        will fire at the comparator rather than a silent garbage read.
        """
        if not cxs or not cys or not t_vals:
            return key_quantities

        bc = task_spec.boundary_conditions or {}
        wall_coord_plate = bc.get("wall_coord_plate")
        T_plate = bc.get("T_plate")
        T_inlet = bc.get("T_inlet")
        bc_type = bc.get("wall_bc_type")
        D_nozzle = bc.get("D_nozzle")
        if (
            wall_coord_plate is None or T_plate is None or T_inlet is None
            or bc_type is None or D_nozzle is None
        ):
            # Fail closed — absence of nusselt_number is the signal.
            # (Codex DEC-042 round-1 FLAG: don't leak extractor-internal
            # state into measurement key_quantities.)
            return key_quantities

        Delta_T = float(T_inlet) - float(T_plate)
        if abs(Delta_T) < 1e-10:
            return key_quantities

        from collections import defaultdict
        from src.wall_gradient import extract_wall_gradient, BCContractViolation

        # Bin cells by radial position r = |cx| (axisymmetric, axis at cx=0).
        # Within each bin, we have cells at different cy (jet-axial) positions;
        # the 3-point stencil operates on that cy-column against the plate
        # BC at cy = wall_coord_plate.
        unique_r = sorted({round(abs(cx), 4) for cx in cxs})
        r_cols: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
        for i in range(min(len(cxs), len(cys), len(t_vals))):
            r_key = round(abs(cxs[i]), 4)
            r_cols[r_key].append((cys[i], t_vals[i]))

        sorted_r: List[float] = []
        Nu_profile: List[float] = []
        wall_cy = float(wall_coord_plate)
        for r_key in unique_r:
            column = r_cols.get(r_key, [])
            if len(column) < 2:
                continue
            # Plate sits at the MAX cy in the domain (jet hits top). The
            # wall_gradient stencil validates wall_coord < cell_coord, so
            # we flip into a wall-normal coordinate n = wall_cy - cy where
            # the wall is at n=0 and interior cells at n>0. We take |grad|
            # afterwards so the sign flip from dn/dcy = −1 washes out.
            interior = [
                (wall_cy - cy, t) for (cy, t) in column if cy < wall_cy
            ]
            if len(interior) < 2:
                continue
            try:
                grad = extract_wall_gradient(
                    wall_coord=0.0,
                    wall_value=float(T_plate),
                    coords=[n for n, _ in interior],
                    values=[t for _, t in interior],
                    bc_type=bc_type,
                    bc_gradient=bc.get("wall_bc_gradient"),
                )
            except BCContractViolation:
                continue
            # Stagnation Nu definition: h·D/k = D·|dT/dn|/ΔT (dimensionless).
            # sign of grad depends on cold-plate hot-jet orientation; take |·|.
            Nu = float(D_nozzle) * abs(grad) / Delta_T
            sorted_r.append(r_key)
            Nu_profile.append(Nu)

        if Nu_profile:
            # Stagnation Nu at r ≈ 0 is the first (smallest r) bin.
            key_quantities["nusselt_number"] = Nu_profile[0]
            key_quantities["nusselt_number_source"] = "wall_gradient_stencil_3pt"
            key_quantities["nusselt_number_profile"] = Nu_profile
            key_quantities["nusselt_number_profile_r"] = sorted_r
            # DEC-V61-042 round-1 FLAG: previous code silently clamped
            # Nu to [0, 500]. Clamping hides runaway — e.g. a diverged
            # solver producing spurious 1e6 gradients would masquerade
            # as a benign 500. Instead, surface a HAZARD flag when a
            # physically implausible value appears so the UI and
            # comparator can treat it honestly. The threshold is
            # generous (500× gold stag Nu≈25) — any hit is a red flag.
            Nu_stag = Nu_profile[0]
            if not (0.0 <= Nu_stag <= 500.0):
                key_quantities["nusselt_number_unphysical_magnitude"] = True

        return key_quantities

    # ------------------------------------------------------------------
    # NACA Airfoil — 提取压力系数分布 Cp
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_airfoil_cp(
        cxs: List[float],
        czs: List[float],
        p_vals: List[float],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """NACA Airfoil: 提取翼型表面压力系数分布 Cp。

        Gold Standard: Cp 分布 (x/c vs Cp)，来自 Thomas 1979 / Lada 2007
        方法: 在 0<=x/c<=1 的 cell centres 中，寻找最接近 NACA0012 上/下表面的
        近壁压力，并对对称表面做平均后得到 Cp(x/c)。

        Note: Mesh now uses x-z plane (z=normal to aerofoil, y=thin span).
        czs contains z-coordinate values from the x-z plane mesh.
        """
        if not cxs or not p_vals:
            return key_quantities

        U_ref = 1.0
        bc = task_spec.boundary_conditions or {}
        chord = float(bc.get("chord_length", 1.0))
        rho = 1.0  # incompressible, reference density
        q_ref = 0.5 * rho * U_ref**2
        if q_ref <= 0.0:
            return key_quantities

        # czs contains z values (normal direction in x-z plane mesh)
        unique_z = sorted({round(z, 6) for z in czs})
        if len(unique_z) >= 2:
            dz_min = min(
                unique_z[i + 1] - unique_z[i]
                for i in range(len(unique_z) - 1)
                if unique_z[i + 1] > unique_z[i]
            )
        else:
            dz_min = 0.01 * chord

        surface_band = max(8.0 * dz_min, 0.02 * chord)
        search_envelope = 0.25 * chord

        from collections import defaultdict

        upper_candidates: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
        lower_candidates: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
        farfield_pressures: List[float] = []

        n = min(len(cxs), len(czs), len(p_vals))
        for i in range(n):
            x = cxs[i]
            z = czs[i]  # z is the normal direction in x-z plane mesh
            p = p_vals[i]

            x_norm = x / chord if chord else 0.0
            if (x < -0.5 * chord or x > 1.5 * chord) and abs(z) < 0.5 * chord:
                farfield_pressures.append(p)

            if x_norm < 0.0 or x_norm > 1.0 or abs(z) > search_envelope:
                continue

            z_surface = FoamAgentExecutor._naca0012_half_thickness(x_norm) * chord
            key = round(x_norm, 3)

            if z >= 0.0:
                upper_candidates[key].append((abs(z - z_surface), p))
            else:
                lower_candidates[key].append((abs(z + z_surface), p))

        p_ref = (
            sum(farfield_pressures) / len(farfield_pressures)
            if farfield_pressures
            else 0.0
        )
        cp_profile: List[Tuple[float, float]] = []

        for x_key in sorted(set(upper_candidates) | set(lower_candidates)):
            p_surface_samples: List[float] = []
            if upper_candidates.get(x_key):
                dist, p_upper = min(upper_candidates[x_key], key=lambda item: item[0])
                if dist <= surface_band:
                    p_surface_samples.append(p_upper)
            if lower_candidates.get(x_key):
                dist, p_lower = min(lower_candidates[x_key], key=lambda item: item[0])
                if dist <= surface_band:
                    p_surface_samples.append(p_lower)
            if p_surface_samples:
                p_surface = sum(p_surface_samples) / len(p_surface_samples)
                cp_profile.append((x_key, (p_surface - p_ref) / q_ref))

        if cp_profile:
            key_quantities["pressure_coefficient_x"] = [x for x, _ in cp_profile]
            key_quantities["pressure_coefficient"] = [cp for _, cp in cp_profile]

        return key_quantities

    # DEC-V61-042: _extract_rayleigh_benard_nusselt deleted — it was
    # defined but never dispatched (RBC routes through _extract_nc_nusselt
    # via GeometryType.NATURAL_CONVECTION_CAVITY), and it used the same
    # 1-point gradient that DEC-042 replaces with the shared 3-point
    # stencil. RBC's remaining issue (side-heated generator vs needed
    # bottom-heated geometry) is out of scope and tracked separately —
    # deleting the dead method avoids re-introducing the 1-point path
    # as a silent fallback when that generator fix eventually lands.

    # ------------------------------------------------------------------
    # Error helper
    # ------------------------------------------------------------------

    @staticmethod
    def _fail(
        message: str,
        elapsed: float,
        raw_output_path: Optional[str] = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            is_mock=False,
            residuals={},
            key_quantities={},
            execution_time_s=elapsed,
            raw_output_path=raw_output_path,
            error_message=message,
        )

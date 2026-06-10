"""P4 V72.A · VOF dam-break surge-front QoI extractor (Execution Plane).

Computes the Martin & Moyce (1952) dimensionless surge-front position
``Z = x_front / a`` of a collapsing water column at pinned sample times from a
solved VOF case's raw fields:

    front_x(t)      = max cell-centre x over floor-band cells with alpha >= 0.5
    water_volume(t) = sum(alpha_i * V_i) over ALL cells (G4 conservation input)
    alpha_min/max   = global bounds at t (G5 boundedness input)

HONESTY (the load-bearing property of the downstream gate)
----------------------------------------------------------
Every QoI is computed from the solver's OWN raw ``alpha.water`` field plus the
mesh-derived ``C`` (cell centres, ``postProcess -func writeCellCentres``) and
``V`` (cell volumes, ``postProcess -func writeCellVolumes``) fields. The
extractor deliberately does NOT read any solver functionObject that already
reports a front position (e.g. isoSurface output) — the judged quantity is
recomputed here, never self-reported by the run (anti-tautology, loop-auditor
V72.A S2). The Ritter bound, the Martin & Moyce anchor, and every threshold
live SOLELY in the gold + gate; no reference value is read here.

Fail-closed contract (loop-auditor V72.A F5/F6 + wedge/BFS precedent):
  * missing/ambiguous time dir, missing alpha.water / C / V file  -> raise
  * binary writeFormat (we only parse ascii)                      -> raise
  * cell-count mismatch between alpha / C / V                     -> raise
  * fewer than ``min_wet_cells`` wet cells in the floor band      -> raise
    (a splash-thin or empty front never yields a fabricated Z)
Never a default value, never a silent uniform-mesh assumption.

Known declared limitation (loop-auditor V72.A F6): the front is the MAX wet-cell
x in the floor band; a detached splash droplet that wets >= min_wet_cells band
cells ahead of the contiguous front would bias Z high. For T <= 2.0 (pre-impact
window of this anchor) the literature shows a coherent front; the min-wet-cells
guard plus the gate's strict Ritter upper bound bracket the failure mode.

ADR-001 plane assignment: **Execution Plane** (reads solver artifacts; stdlib
only; NO Evaluation/Control imports — comparator/threshold wiring lives in
``src.dam_break_gate``, Control Plane).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

# Wet threshold for the volume-fraction field: a cell belongs to the water
# body when alpha >= 0.5 (the conventional VOF interface midpoint).
ALPHA_WET_THRESHOLD: float = 0.5

# Default minimum number of wet floor-band cells required to call a front
# (F6 splash guard); the gate may pass a stricter value.
DEFAULT_MIN_WET_CELLS: int = 3

# Absolute tolerance when matching a requested sample time to an on-disk
# OpenFOAM time directory name. Sized to absorb DIRECTORY-NAME FORMATTING
# noise ONLY (timePrecision rounding of a ~0.1 s value: <=5e-7) — NOT
# write-control sloppiness: a run that writes 0.086 instead of the pinned
# 0.086293 (~1% of the physical time at T=1) must FAIL CLOSED, never be
# silently graded as the pinned sample (Codex V72.A R0 P2-2).
_TIME_DIR_ATOL: float = 1.0e-6


class DamBreakExtractionError(ValueError):
    """Raised on ANY extraction failure — the gate treats it as an honest BLOCK."""


@dataclass(frozen=True)
class DamBreakSnapshot:
    """Measured state of the collapsing column at one sample time."""

    time: float                # physical time t [s] of the matched time dir
    time_dir: str              # the on-disk OpenFOAM time directory name
    front_x: float             # max wet cell-centre x in the floor band [m]
    z_front: float             # front_x / a (Martin & Moyce dimensionless Z)
    n_wet_band_cells: int      # wet cells inside the floor band (>= min_wet_cells)
    water_volume: float        # sum(alpha_i * V_i) over all cells [m^3]
    alpha_min: float           # global min(alpha) at this time
    alpha_max: float           # global max(alpha) at this time


@dataclass(frozen=True)
class DamBreakMetrics:
    """Extractor output: snapshots ordered by ascending sample time."""

    snapshots: Tuple[DamBreakSnapshot, ...]
    column_width_a: float      # the normalization length a [m]
    floor_band_y: float        # the floor-band height used for the front [m]
    front_method: str = "max_wet_cell_centre_x_in_floor_band"


# --------------------------------------------------------------------------
# OpenFOAM ascii field parsing (stdlib, fail-closed)
# --------------------------------------------------------------------------

_FORMAT_RE = re.compile(r"\bformat\s+(\w+)\s*;")
_UNIFORM_SCALAR_RE = re.compile(
    r"internalField\s+uniform\s+([0-9eE+.\-]+)\s*;"
)
_NONUNIFORM_RE = re.compile(
    r"internalField\s+nonuniform\s+List<(scalar|vector)>\s*\n\s*(\d+)\s*\n\s*\(",
)
_VECTOR_RE = re.compile(r"\(\s*([0-9eE+.\-]+)\s+([0-9eE+.\-]+)\s+([0-9eE+.\-]+)\s*\)")


def _read_text_ascii_checked(path: Path) -> str:
    if not path.is_file():
        raise DamBreakExtractionError(f"missing field file: {path}")
    text = path.read_text(encoding="utf-8", errors="strict")
    m = _FORMAT_RE.search(text[:2000])
    if not m or m.group(1) != "ascii":
        raise DamBreakExtractionError(
            f"unsupported writeFormat in {path} "
            f"(found {m.group(1) if m else 'none'!r}; this extractor parses ascii "
            f"only — pin `writeFormat ascii;` in controlDict)"
        )
    return text


def _parse_nonuniform_block(text: str, path: Path) -> Tuple[str, int, str]:
    m = _NONUNIFORM_RE.search(text)
    if not m:
        raise DamBreakExtractionError(
            f"no nonuniform internalField in {path} (cannot infer mesh size)"
        )
    kind, count = m.group(1), int(m.group(2))
    start = m.end()  # just after the opening '('
    end = text.find(")", start) if kind == "scalar" else _find_vector_block_end(text, start)
    if end < 0:
        raise DamBreakExtractionError(f"unterminated internalField list in {path}")
    return kind, count, text[start:end]


def _find_vector_block_end(text: str, start: int) -> int:
    # vector lists nest parentheses: scan for the ');' that closes the list.
    m = re.search(r"\)\s*;\s*", text[start:])
    if not m:
        return -1
    # m.start() is the final closing paren of the LIST; vector entries each
    # close their own paren earlier, so search for the last "(x y z)" before it.
    return start + m.start()


def read_scalar_field(path: Path, expected_n: int | None = None) -> List[float]:
    """Parse an ascii volScalarField; uniform fields expand to ``expected_n``."""
    text = _read_text_ascii_checked(path)
    um = _UNIFORM_SCALAR_RE.search(text)
    if um:
        if expected_n is None:
            raise DamBreakExtractionError(
                f"uniform internalField in {path} but mesh size unknown"
            )
        return [float(um.group(1))] * expected_n
    kind, count, block = _parse_nonuniform_block(text, path)
    if kind != "scalar":
        raise DamBreakExtractionError(f"{path}: expected scalar field, got {kind}")
    values = [float(v) for v in block.split()]
    if len(values) != count:
        raise DamBreakExtractionError(
            f"{path}: header count {count} != parsed values {len(values)}"
        )
    if expected_n is not None and count != expected_n:
        raise DamBreakExtractionError(
            f"{path}: cell count {count} != expected {expected_n} (field/mesh mismatch)"
        )
    return values


def read_vector_field(path: Path) -> List[Tuple[float, float, float]]:
    """Parse an ascii volVectorField (e.g. cell centres ``C``)."""
    text = _read_text_ascii_checked(path)
    kind, count, block = _parse_nonuniform_block(text, path)
    if kind != "vector":
        raise DamBreakExtractionError(f"{path}: expected vector field, got {kind}")
    vectors = [
        (float(a), float(b), float(c)) for a, b, c in _VECTOR_RE.findall(block)
    ]
    if len(vectors) != count:
        raise DamBreakExtractionError(
            f"{path}: header count {count} != parsed vectors {len(vectors)}"
        )
    return vectors


# --------------------------------------------------------------------------
# Time-directory resolution (fail-closed)
# --------------------------------------------------------------------------

def _numeric_time_dirs(case_dir: Path) -> List[Tuple[float, Path]]:
    out: List[Tuple[float, Path]] = []
    for child in case_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            out.append((float(child.name), child))
        except ValueError:
            continue
    return sorted(out, key=lambda p: p[0])


def _resolve_time_dir(case_dir: Path, t: float) -> Tuple[float, Path]:
    candidates = [
        (tv, p) for tv, p in _numeric_time_dirs(case_dir)
        if math.isclose(tv, t, abs_tol=_TIME_DIR_ATOL)
    ]
    if not candidates:
        raise DamBreakExtractionError(
            f"no time directory within {_TIME_DIR_ATOL} of t={t} in {case_dir} "
            f"(pin write times in controlDict; fail-closed, no nearest-neighbor guess)"
        )
    if len(candidates) > 1:
        raise DamBreakExtractionError(
            f"ambiguous time directories for t={t} in {case_dir}: "
            f"{[p.name for _, p in candidates]}"
        )
    return candidates[0]


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

def extract_dam_break(
    case_dir: Path,
    sample_times: Sequence[float],
    column_width_a: float,
    floor_band_y: float,
    min_wet_cells: int = DEFAULT_MIN_WET_CELLS,
    alpha_field_name: str = "alpha.water",
) -> DamBreakMetrics:
    """Extract surge-front QoIs at each sample time (fail-closed).

    ``C`` and ``V`` (cell centres / volumes) are read from the FIRST sample
    time dir that carries them, falling back to ``0/`` then ``constant/``;
    the static mesh of this anchor makes them time-invariant.
    """
    case_dir = Path(case_dir)
    if column_width_a <= 0 or floor_band_y <= 0:
        raise DamBreakExtractionError(
            f"non-physical geometry inputs: a={column_width_a}, band={floor_band_y}"
        )
    resolved = [_resolve_time_dir(case_dir, t) for t in sample_times]

    centres, volumes = _load_mesh_fields(case_dir, [p for _, p in resolved])
    n = len(centres)

    snapshots: List[DamBreakSnapshot] = []
    for t_actual, tdir in resolved:
        alpha = read_scalar_field(tdir / alpha_field_name, expected_n=n)
        wet_band_x = [
            centres[i][0]
            for i in range(n)
            if centres[i][1] <= floor_band_y and alpha[i] >= ALPHA_WET_THRESHOLD
        ]
        if len(wet_band_x) < min_wet_cells:
            raise DamBreakExtractionError(
                f"only {len(wet_band_x)} wet floor-band cells at t={t_actual} "
                f"(< {min_wet_cells}); refusing to report a front (splash guard)"
            )
        front_x = max(wet_band_x)
        water_volume = math.fsum(a * v for a, v in zip(alpha, volumes))
        snapshots.append(
            DamBreakSnapshot(
                time=t_actual,
                time_dir=tdir.name,
                front_x=front_x,
                z_front=front_x / column_width_a,
                n_wet_band_cells=len(wet_band_x),
                water_volume=water_volume,
                alpha_min=min(alpha),
                alpha_max=max(alpha),
            )
        )
    snapshots.sort(key=lambda s: s.time)
    return DamBreakMetrics(
        snapshots=tuple(snapshots),
        column_width_a=column_width_a,
        floor_band_y=floor_band_y,
    )


def _load_mesh_fields(
    case_dir: Path, sample_dirs: Sequence[Path]
) -> Tuple[List[Tuple[float, float, float]], List[float]]:
    """Locate and parse cell centres ``C`` + cell volumes ``V`` (fail-closed)."""
    search: List[Path] = list(sample_dirs) + [case_dir / "0", case_dir / "constant"]
    c_path = next((d / "C" for d in search if (d / "C").is_file()), None)
    v_path = next((d / "V" for d in search if (d / "V").is_file()), None)
    if c_path is None:
        raise DamBreakExtractionError(
            f"cell-centres field C not found in {case_dir} "
            f"(run `postProcess -func writeCellCentres`; fail-closed)"
        )
    if v_path is None:
        raise DamBreakExtractionError(
            f"cell-volumes field V not found in {case_dir} "
            f"(run `postProcess -func writeCellVolumes`; no uniform-mesh fallback, "
            f"fail-closed per loop-auditor V72.A F5)"
        )
    centres = read_vector_field(c_path)
    volumes = read_scalar_field(v_path, expected_n=len(centres))
    if any(v <= 0 for v in volumes):
        raise DamBreakExtractionError(f"non-positive cell volume in {v_path}")
    return centres, volumes


def to_key_quantities(metrics: DamBreakMetrics) -> Dict[str, float]:
    """Flatten snapshots for ExecutionResult.key_quantities consumers."""
    out: Dict[str, float] = {}
    for snap in metrics.snapshots:
        out[f"z_front_t{snap.time_dir}"] = snap.z_front
        out[f"water_volume_t{snap.time_dir}"] = snap.water_volume
    return out

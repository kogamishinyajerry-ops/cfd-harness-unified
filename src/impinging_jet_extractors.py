"""Impinging-jet multi-dimensional extractors · DEC-V61-071 Stage B.

Pure-helper extractors operating on pre-loaded cell-center field arrays from
an axisymmetric impinging-jet simulation snapshot. Designed for the
Baughn-Shimizu 1989 benchmark (Re=23000, H/D=2, free jet, plate at uniform
heat flux in the literature; adapter currently emits constant-T Dirichlet —
mismatch documented in `knowledge/gold_standards/axisymmetric_impinging_jet.yaml`
§physics_contract.note).

Geometry convention (matches `FoamAgentAdapter._generate_impinging_jet`):
  - cxs: radial coordinate r (m). Axis at r=0.
  - cys: jet-axial coordinate z (m). Plate at cy = max(cys) = z_max.
  - czs: slab depth (m), unused — adapter emits a pseudo-2D Cartesian r-z slab
    with `empty` patches on the lateral faces. NOT a true axisymmetric `wedge`.

Each extractor:
  - takes an ``ImpingingJetFieldSlice`` + ``ImpingingJetBoundary`` pair,
  - returns ``{value, ...diagnostics}`` so the comparator/UI can decide
    whether to FAIL/PASS/ADVISORY based on classification + diagnostics
    per RETRO-V61-050 + DEC-V61-057 Stage B precedent,
  - fails closed (returns ``{}``) on input shape errors instead of raising,
    so an invalid input degrades to MISSING_TARGET_QUANTITY at the gate
    rather than crashing the audit pipeline.

Module is Execution-plane (registered in ``src._plane_assignment``) — it
must not import from ``src.auto_verifier``, ``src.metrics``,
``src.report_engine``, or any other Evaluation-plane module per ADR-001.

This module deliberately re-implements the radial-binning logic from
``foam_agent_adapter._extract_jet_nusselt`` rather than calling into the
adapter, mirroring the DHC Stage B (DEC-V61-057) precedent: the adapter
method is private to the FoamAgentAdapter class and intake §6 froze
adapter modifications outside `_generate_impinging_jet` for V61-071.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.wall_gradient import BCContractViolation, extract_wall_gradient


# ---------------------------------------------------------------------------
# Input dataclasses (frozen; pure value objects)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImpingingJetFieldSlice:
    """Cell-center field arrays from an impinging-jet simulation snapshot.

    All sequences MUST have identical length (one entry per cell). Empty
    sequences are tolerated — extractors return ``{}`` ("missing" signal).

    Attributes:
        cxs: cell-center radial coordinate r (m). Axis at cxs=0.
        cys: cell-center jet-axial coordinate z (m). Plate at cys=max(cys).
        t_vals: temperature scalar field (K). Required for Nu extractors.
        u_vecs: velocity vector field as list of (ux, uy, uz) tuples (m/s).
            Required only for y+ extractor; optional for Nu-only extraction.
            ux is the radial component, uy is the axial component.
    """
    cxs: Sequence[float]
    cys: Sequence[float]
    t_vals: Sequence[float] = field(default_factory=tuple)
    u_vecs: Optional[Sequence[Tuple[float, float, float]]] = None


@dataclass(frozen=True)
class ImpingingJetBoundary:
    """Boundary-condition + reference-scale metadata for non-dim conversion.

    Attributes:
        D_nozzle: jet nozzle diameter D (m). Adapter default 0.05.
        T_plate: plate temperature (K). Adapter default 290.0 (cold).
        T_inlet: jet inlet temperature (K). Adapter default 310.0 (hot).
        wall_coord_plate: cy (jet-axial) coordinate of the plate face (m).
            Conventionally cy=z_max in adapter convention.
        bc_type: ``'fixedValue'`` or ``'fixedGradient'``. Selects stencil
            mode in ``src.wall_gradient.extract_wall_gradient``. Adapter
            currently emits ``'fixedValue'`` (Dirichlet/constant-T) — see
            §physics_contract.note for the literature uniform-q mismatch.
        bc_gradient: required iff ``bc_type='fixedGradient'`` (uniform-q
            variant); ignored otherwise.
        nu: kinematic viscosity ν (m²/s). Required only for y+ extractor.
            Adapter default 1.0 * 0.05 / Re; for Re=23000 this is ~2.17e-6.
    """
    D_nozzle: float
    T_plate: float
    T_inlet: float
    wall_coord_plate: float
    bc_type: str
    bc_gradient: Optional[float] = None
    nu: Optional[float] = None


# Default radial stations used by the profile gate (Behnia 1997 Fig 3 ●
# symbols at Re=23000 H/D=2). The headline gate at r/D=0 lives in
# ``extract_nusselt_at_stagnation`` and is intentionally excluded from
# the profile gate, which is graded as a single shape family per
# Codex F2 (one PROFILE_QUALITATIVE_GATE, not 6 independent gates).
DEFAULT_PROFILE_STATIONS_R_OVER_D: Tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 3.0, 5.0)

# Search band for the secondary Nu peak in the wall-jet (intake §1 gate iv).
# At Re ≥ 20000 expected status is PRESENT; at Re < 10000 expected ABSENT.
# Re=23000 sits above the threshold so the Baughn-Shimizu row should pass
# with PRESENT.
SECONDARY_PEAK_SEARCH_BAND_R_OVER_D: Tuple[float, float] = (1.5, 2.5)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _input_lengths_consistent(*arrays: Optional[Sequence[Any]]) -> bool:
    """Return True iff all non-None inputs have identical length.

    DEC-V61-057 Codex round-2 F1-HIGH precedent: extractors MUST early-
    return ``{}`` on length mismatch so the comparator's MISSING_TARGET_QUANTITY
    path fires instead of silently clipping to the shortest input.
    """
    lens = [len(a) for a in arrays if a is not None]
    return not lens or all(n == lens[0] for n in lens)


def _radial_columns(
    slice_: ImpingingJetFieldSlice,
) -> Dict[float, List[Tuple[float, float]]]:
    """Bin cells by radial position r=|cx|; each bin is a column of (cy, T).

    Mirrors the binning in ``FoamAgentAdapter._extract_jet_nusselt`` so the
    pseudo-2D r-z slab is collapsed into a 1-D radial profile. The 4-decimal
    round on r matches the adapter's ``round(abs(cx), 4)`` precision (about
    0.1 mm at the adapter's 0.05 m nozzle scale).
    """
    cxs, cys, t_vals = slice_.cxs, slice_.cys, slice_.t_vals
    if not cxs or not cys or not t_vals:
        return {}
    if not _input_lengths_consistent(cxs, cys, t_vals):
        return {}
    cols: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
    for i in range(len(cxs)):
        cols[round(abs(cxs[i]), 4)].append((cys[i], t_vals[i]))
    return cols


def _nu_at_radial_column(
    column: List[Tuple[float, float]],
    bc: ImpingingJetBoundary,
    delta_T: float,
) -> Optional[float]:
    """Return Nu_local at one r-bin via 3-point wall-normal stencil.

    Returns ``None`` when the column has fewer than 2 interior cells below
    the plate (wall sits at cy=wall_coord_plate, plate at TOP of domain).
    """
    wall_cy = float(bc.wall_coord_plate)
    interior = [(wall_cy - cy, t) for (cy, t) in column if cy < wall_cy]
    if len(interior) < 2:
        return None
    interior.sort(key=lambda p: p[0])
    try:
        grad = extract_wall_gradient(
            wall_coord=0.0,
            wall_value=float(bc.T_plate),
            coords=[n for n, _ in interior],
            values=[t for _, t in interior],
            bc_type=bc.bc_type,  # type: ignore[arg-type]
            bc_gradient=bc.bc_gradient,
        )
    except BCContractViolation:
        return None
    return float(bc.D_nozzle) * abs(grad) / abs(delta_T)


def _full_nu_profile(
    slice_: ImpingingJetFieldSlice,
    bc: ImpingingJetBoundary,
) -> List[Tuple[float, float]]:
    """Return [(r_over_d, Nu_local)] over all r-bins with ≥2 wall-normal cells.

    Returns [] on missing/inconsistent inputs or zero ΔT.
    """
    delta_T = float(bc.T_inlet) - float(bc.T_plate)
    if abs(delta_T) < 1e-10 or bc.D_nozzle == 0.0:
        return []
    cols = _radial_columns(slice_)
    if not cols:
        return []
    out: List[Tuple[float, float]] = []
    for r_key in sorted(cols.keys()):
        nu = _nu_at_radial_column(cols[r_key], bc, delta_T)
        if nu is not None:
            out.append((r_key / float(bc.D_nozzle), nu))
    return out


# ---------------------------------------------------------------------------
# B.1 · Stagnation Nu extractor (HARD_GATED · headline)
# ---------------------------------------------------------------------------

# Hazard threshold for nusselt_number_unphysical_magnitude per the existing
# adapter convention (3.3× Baughn 1989 stag Nu=145 plus a 100 hard-floor).
# A divergent solver producing spurious gradients gets flagged rather than
# clamped — comparator can then treat the value honestly per RETRO-V61-050.
NU_STAG_UNPHYSICAL_CEILING = 500.0


def extract_nusselt_at_stagnation(
    slice_: ImpingingJetFieldSlice,
    bc: ImpingingJetBoundary,
) -> Dict[str, Any]:
    """Stagnation Nusselt number Nu(r=0) on the plate.

    Bins cells by r=|cx|, picks the smallest-r column, and applies a 3-point
    wall-normal stencil at the plate (cy=wall_coord_plate). Per the standard
    impinging-jet definition Nu = h·D/k = D·|dT/dn|_wall / (T_inlet - T_plate).

    Gold value at Re=23000 H/D=2 is Nu_stag=145 (Behnia 1997 Fig 3 ● symbol;
    Baughn-Shimizu 1989 dataset). HARD_GATED with ±30% tolerance per intake §2.

    Returns
    -------
    dict
        Empty when inputs are missing/inconsistent or no r-bin has ≥2 wall-
        normal cells (callers should treat as MISSING_TARGET_QUANTITY). On
        success::

            {
              "value": float,                  # Nu_stag (dimensionless)
              "r_at_stagnation": float,        # smallest r used (m)
              "r_at_stagnation_over_D": float, # normalized r/D (≈ 0)
              "num_cells_in_stagnation_column": int,
              "num_radial_bins_total": int,
              "unphysical_magnitude": bool,    # True if Nu < 0 or > 500
              "source": "wall_gradient_stencil_3pt_stagnation",
            }
    """
    delta_T = float(bc.T_inlet) - float(bc.T_plate)
    if abs(delta_T) < 1e-10 or bc.D_nozzle == 0.0:
        return {}
    cols = _radial_columns(slice_)
    if not cols:
        return {}
    sorted_r = sorted(cols.keys())
    # Walk outward until we find an r-bin with enough cells; some adapters
    # leave the axis-cell sparse on graded meshes.
    for r_key in sorted_r:
        column = cols[r_key]
        nu = _nu_at_radial_column(column, bc, delta_T)
        if nu is None:
            continue
        unphysical = not (0.0 <= nu <= NU_STAG_UNPHYSICAL_CEILING)
        return {
            "value": float(nu),
            "r_at_stagnation": float(r_key),
            "r_at_stagnation_over_D": float(r_key) / float(bc.D_nozzle),
            "num_cells_in_stagnation_column": len(column),
            "num_radial_bins_total": len(sorted_r),
            "unphysical_magnitude": bool(unphysical),
            "source": "wall_gradient_stencil_3pt_stagnation",
        }
    return {}


# ---------------------------------------------------------------------------
# B.2 · Profile-at-stations extractor (PROFILE_QUALITATIVE_GATE)
# ---------------------------------------------------------------------------

def extract_profile_at_stations(
    slice_: ImpingingJetFieldSlice,
    bc: ImpingingJetBoundary,
    target_r_over_d: Sequence[float] = DEFAULT_PROFILE_STATIONS_R_OVER_D,
) -> Dict[str, Any]:
    """Nu(r/D) at a set of radial stations from Behnia 1997 Fig 3.

    For each target r/D station, picks the r-bin closest in r/D and applies
    the wall-normal stencil. PROFILE_QUALITATIVE_GATE classification per
    intake §1 v2 — graded as one profile family (shape: monotonic decay,
    local minimum, secondary peak, post-secondary decay), not 6 independent
    per-station gates.

    Returns
    -------
    dict
        Empty on missing/inconsistent inputs. On success::

            {
              "stations": [
                {
                  "target_r_over_D": float,
                  "matched_r_over_D": float,
                  "matched_r": float,
                  "Nu_local": float,
                  "abs_residual_r_over_D": float,
                },
                ...
              ],
              "num_stations_resolved": int,
              "num_stations_requested": int,
              "shape_diagnostics": {
                "is_monotonic_decay_first_segment": bool,  # r/D ∈ [0, 1.5]
                "has_local_minimum_in_band": bool,         # r/D ∈ [1.0, 2.0]
              },
              "source": "wall_gradient_stencil_3pt_profile",
            }
    """
    profile = _full_nu_profile(slice_, bc)
    # DEC-V61-071 Stage B Codex R1 F1-HIGH: a sparse mesh that only resolves
    # one radial bin would previously map every target onto that single bin
    # and report ``num_stations_resolved == len(targets)`` with bogus shape
    # diagnostics computed on duplicated data. Require at least one usable
    # bin per target AND consume each bin at most once so a sparse/diverged
    # run degrades to MISSING_TARGET_QUANTITY at the gate instead.
    if not profile or len(profile) < len(target_r_over_d):
        return {}
    stations: List[Dict[str, Any]] = []
    used_indices: set[int] = set()
    for target in target_r_over_d:
        remaining = [
            (idx, pair) for idx, pair in enumerate(profile)
            if idx not in used_indices
        ]
        if not remaining:
            return {}
        best_idx, best = min(
            remaining,
            key=lambda item: abs(item[1][0] - float(target)),
        )
        used_indices.add(best_idx)
        stations.append({
            "target_r_over_D": float(target),
            "matched_r_over_D": float(best[0]),
            "matched_r": float(best[0]) * float(bc.D_nozzle),
            "Nu_local": float(best[1]),
            "abs_residual_r_over_D": float(abs(best[0] - float(target))),
        })

    # Shape diagnostics over the resolved stations.
    by_target: List[Tuple[float, float]] = sorted(
        [(s["target_r_over_D"], s["Nu_local"]) for s in stations],
        key=lambda p: p[0],
    )
    first_segment = [(t, n) for (t, n) in by_target if t <= 1.5]
    is_monotonic_decay_first_segment = (
        len(first_segment) >= 2
        and all(
            first_segment[i + 1][1] <= first_segment[i][1]
            for i in range(len(first_segment) - 1)
        )
    )
    # DEC-V61-071 Stage B Codex R1 F3-MED: previously sorted the entire
    # band by Nu and picked the lowest target as the candidate minimum,
    # which misfired when the lowest sample sat at the band edge (e.g.
    # ``r/D ∈ {0.5:12, 1.0:10, 1.5:11, 2.0:12}`` falsely reported
    # ``has_local_minimum_in_band=True``). Scan the band for any strict-
    # interior local minimum directly so a band-edge minimum doesn't
    # masquerade as a valley.
    band = [(t, n) for (t, n) in by_target if 1.0 <= t <= 2.0]
    has_local_minimum_in_band = (
        len(band) >= 3
        and any(
            band[i][1] <= band[i - 1][1] and band[i][1] <= band[i + 1][1]
            for i in range(1, len(band) - 1)
        )
    )

    return {
        "stations": stations,
        "num_stations_resolved": len(stations),
        "num_stations_requested": len(target_r_over_d),
        "shape_diagnostics": {
            "is_monotonic_decay_first_segment": bool(is_monotonic_decay_first_segment),
            "has_local_minimum_in_band": bool(has_local_minimum_in_band),
        },
        "source": "wall_gradient_stencil_3pt_profile",
    }


# ---------------------------------------------------------------------------
# B.3 · Secondary-peak presence extractor (PROFILE_QUALITATIVE_GATE · boolean)
# ---------------------------------------------------------------------------

def extract_secondary_peak_status(
    slice_: ImpingingJetFieldSlice,
    bc: ImpingingJetBoundary,
    search_band_r_over_d: Tuple[float, float] = SECONDARY_PEAK_SEARCH_BAND_R_OVER_D,
) -> Dict[str, Any]:
    """Detect a secondary Nu peak in the wall-jet at r/D ∈ [1.5, 2.5].

    Computes the full Nu(r/D) profile and looks for a local maximum strictly
    inside the search band. PROFILE_QUALITATIVE_GATE per intake §1.iv:
      - Re ≥ 20000 → expected = PRESENT (Re=23000 satisfies this)
      - Re <  10000 → expected = ABSENT
      - 10000 ≤ Re < 20000 → indeterminate (intake notes a transition zone)

    Returns
    -------
    dict
        Empty on missing inputs / sparse profile. On success::

            {
              "value": "PRESENT" | "ABSENT",
              "peak_r_over_D": float | None,    # r/D of the max in band
              "peak_Nu_local": float | None,
              "search_band_r_over_D": [float, float],
              "num_bins_in_band": int,
              "monotonic_in_band": bool,        # True → no peak (ABSENT)
              "source": "radial_local_max_search",
            }
    """
    profile = _full_nu_profile(slice_, bc)
    if not profile:
        return {}
    lo, hi = float(search_band_r_over_d[0]), float(search_band_r_over_d[1])
    # DEC-V61-071 Stage B Codex R1 F2-HIGH: previously rejected band-edge
    # peaks (e.g. r/D=2.5 with neighbours only inside the band) and broad
    # plateaus, even though gold §physics_contract notes the Re=23000
    # peak need only be "detectable as a local maximum ... not a sharp
    # double-peak". Carry the global profile index alongside each in-band
    # sample and consult the FULL profile (including post-band r/D=3, 5)
    # for the right neighbour, and accept ≥ comparisons for plateau-tops
    # provided at least one neighbour is strictly lower.
    in_band = [
        (global_idx, r_val, nu_val)
        for global_idx, (r_val, nu_val) in enumerate(profile)
        if lo <= r_val <= hi
    ]
    if len(in_band) < 3:
        return {
            "value": "ABSENT",
            "peak_r_over_D": None,
            "peak_Nu_local": None,
            "search_band_r_over_D": [lo, hi],
            "num_bins_in_band": len(in_band),
            "monotonic_in_band": True,
            "source": "radial_local_max_search",
        }

    monotonic = all(in_band[i + 1][2] <= in_band[i][2] for i in range(len(in_band) - 1))
    peak_idx: Optional[int] = None
    for global_idx, _, nu_val in in_band:
        if global_idx == 0 or global_idx == len(profile) - 1:
            continue
        left = profile[global_idx - 1][1]
        right = profile[global_idx + 1][1]
        if nu_val >= left and nu_val >= right and (nu_val > left or nu_val > right):
            if peak_idx is None or nu_val > profile[peak_idx][1]:
                peak_idx = global_idx

    if peak_idx is None:
        return {
            "value": "ABSENT",
            "peak_r_over_D": None,
            "peak_Nu_local": None,
            "search_band_r_over_D": [lo, hi],
            "num_bins_in_band": len(in_band),
            "monotonic_in_band": monotonic,
            "source": "radial_local_max_search",
        }

    return {
        "value": "PRESENT",
        "peak_r_over_D": float(profile[peak_idx][0]),
        "peak_Nu_local": float(profile[peak_idx][1]),
        "search_band_r_over_D": [lo, hi],
        "num_bins_in_band": len(in_band),
        "monotonic_in_band": monotonic,
        "source": "radial_local_max_search",
    }


# ---------------------------------------------------------------------------
# B.4 · y+ first-cell at plate (PROVISIONAL_ADVISORY)
# ---------------------------------------------------------------------------

def extract_y_plus_first_cell(
    slice_: ImpingingJetFieldSlice,
    bc: ImpingingJetBoundary,
) -> Dict[str, Any]:
    """First-cell y+ at the plate per radial bin · max reported as advisory.

    Computes the wall-shear-velocity at each r-bin from the radial-velocity
    gradient at the plate:

        u_τ = sqrt(ν · |du_r/dn|_wall),   y+ = n_first · u_τ / ν

    where ``n_first`` is the wall-normal distance of the cell-center closest
    to the plate. The ADVISORY status reports ``max(y+)`` across r-bins so
    the worst wall-resolution point surfaces; per-bin breakdown also returned.

    Target for k-ω SST + automatic wall treatment: y+ < 5 (intake §1 R6).
    PROVISIONAL_ADVISORY classification — comparator does not gate on this.

    Returns
    -------
    dict
        Empty when ``u_vecs`` is missing or no r-bin has ≥2 wall-normal cells.
        Empty also when ``bc.nu`` is missing/zero. On success::

            {
              "value": float,            # max y+ across r-bins
              "y_plus_max_at_r_over_D": float,
              "y_plus_min": float,
              "y_plus_mean": float,
              "num_radial_bins_used": int,
              "target_max": 5.0,
              "advisory_status": "PROVISIONAL_ADVISORY",
              "source": "wall_shear_first_cell",
            }
    """
    if slice_.u_vecs is None or not slice_.cxs or not slice_.cys:
        return {}
    if not _input_lengths_consistent(slice_.cxs, slice_.cys, slice_.u_vecs):
        return {}
    if bc.nu is None or bc.nu <= 0.0 or bc.D_nozzle == 0.0:
        return {}

    wall_cy = float(bc.wall_coord_plate)
    cols: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
    for i in range(len(slice_.cxs)):
        # u_x is the radial component (tangent to the plate).
        cols[round(abs(slice_.cxs[i]), 4)].append((slice_.cys[i], slice_.u_vecs[i][0]))

    y_plus_per_bin: List[Tuple[float, float]] = []
    for r_key, col in cols.items():
        interior = [(wall_cy - cy, ur) for (cy, ur) in col if cy < wall_cy]
        if len(interior) < 2:
            continue
        interior.sort(key=lambda p: p[0])
        try:
            grad = extract_wall_gradient(
                wall_coord=0.0,
                wall_value=0.0,  # no-slip at the plate
                coords=[n for n, _ in interior],
                values=[ur for _, ur in interior],
                bc_type="fixedValue",
                bc_gradient=None,
            )
        except BCContractViolation:
            continue
        u_tau_sq = float(bc.nu) * abs(grad)
        if u_tau_sq < 0.0:
            continue
        u_tau = u_tau_sq ** 0.5
        n_first = interior[0][0]
        y_plus = n_first * u_tau / float(bc.nu)
        y_plus_per_bin.append((r_key / float(bc.D_nozzle), y_plus))

    if not y_plus_per_bin:
        return {}
    r_at_max, y_plus_max = max(y_plus_per_bin, key=lambda p: p[1])
    y_plus_values = [yp for (_, yp) in y_plus_per_bin]
    return {
        "value": float(y_plus_max),
        "y_plus_max_at_r_over_D": float(r_at_max),
        "y_plus_min": float(min(y_plus_values)),
        "y_plus_mean": float(sum(y_plus_values) / len(y_plus_values)),
        "num_radial_bins_used": len(y_plus_per_bin),
        "target_max": 5.0,
        "advisory_status": "PROVISIONAL_ADVISORY",
        "source": "wall_shear_first_cell",
    }

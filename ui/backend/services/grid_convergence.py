"""Phase 7d — Richardson extrapolation + Grid Convergence Index (GCI).

Per Roache 1994 (J. Fluids Eng. 116, 405-413) and Celik et al. 2008
(ASME V&V 20 standard). Given three successively-refined mesh solutions
f_1 (coarse), f_2 (medium), f_3 (fine) with refinement ratios r_21 = h_2/h_1,
r_32 = h_3/h_2:

    p_obs = |ln(|(f_3 - f_2)/(f_2 - f_1)|)| / ln(r)    (uniform r)

    ε_21 = |f_2 - f_1|/|f_1|
    GCI_21 = Fs * ε_21 / (r_21^p - 1)       (coarse-to-medium uncertainty)
    GCI_32 = Fs * ε_32 / (r_32^p - 1)       (medium-to-fine uncertainty)

Fs = safety factor (1.25 for 3-grid, 3.0 for 2-grid).

We consume the mesh_20/40/80/160 fixtures already at
`ui/backend/tests/fixtures/runs/{case}/mesh_{N}_measurement.yaml`.
These are 4 meshes; we compute GCI over the finest three (40/80/160)
which is standard practice, and return auxiliary info for the coarsest.

This is pure numerical code — no Docker, no src/ touch, no 三禁区.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE_ROOT = _REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"


@dataclass(frozen=True)
class MeshSolution:
    label: str          # e.g. "mesh_40"
    n_cells_1d: int     # e.g. 40 (for an N×N×1 LDC mesh)
    value: float        # the scalar comparator quantity


@dataclass(frozen=True)
class RichardsonGCI:
    """Output of Richardson + GCI computation on three successive meshes.

    Follows Celik et al. 2008 nomenclature: subscripts 1/2/3 go
    coarse-to-fine, so r_21 = h_2/h_1 with r > 1 means refined.
    """
    coarse: MeshSolution        # f_1
    medium: MeshSolution        # f_2
    fine: MeshSolution          # f_3
    r_21: float                 # refinement ratio coarse → medium
    r_32: float                 # medium → fine
    p_obs: Optional[float]      # observed order of accuracy
    f_extrapolated: Optional[float]   # Richardson extrapolation to h→0
    e_21: float                 # relative change coarse→medium
    e_32: float                 # relative change medium→fine
    gci_21: Optional[float]     # coarse-mesh uncertainty band
    gci_32: Optional[float]     # fine-mesh uncertainty band
    asymptotic_range_ok: Optional[bool]  # True if GCI_32 * r^p ≈ GCI_21 within 1.25x
    note: str                   # human-readable diagnostic


_FS_THREE_GRID = 1.25


def compute_richardson_gci(
    coarse: MeshSolution,
    medium: MeshSolution,
    fine: MeshSolution,
) -> RichardsonGCI:
    """Compute Richardson extrapolation + GCI for three solutions.

    Handles degenerate cases:
    - (f_2 - f_1) ≈ 0 → no refinement signal, p_obs undefined
    - oscillating signs (f_3 - f_2) and (f_2 - f_1) opposite → p_obs flagged note
    - non-uniform refinement ratio — uses average per Celik §2.3
    """
    # Celik 2008 convention: r = h_coarse / h_fine > 1 with h ∝ 1/N for uniform meshes.
    # So r_21 = h_1/h_2 = N_2/N_1 (medium cells / coarse cells) must be > 1.
    r_21 = medium.n_cells_1d / coarse.n_cells_1d
    r_32 = fine.n_cells_1d / medium.n_cells_1d
    if r_21 <= 1 or r_32 <= 1:
        raise ValueError(
            f"meshes not monotonically refined: "
            f"n_1d = {coarse.n_cells_1d}, {medium.n_cells_1d}, {fine.n_cells_1d}"
        )

    eps_21 = medium.value - coarse.value
    eps_32 = fine.value - medium.value

    # Celik 2008 Eq. 4: approximate relative error uses the REFINED solution
    # (downstream value) as denominator, not the upstream.
    e_21 = abs(eps_21 / medium.value) if abs(medium.value) > 1e-12 else float("inf")
    e_32 = abs(eps_32 / fine.value) if abs(fine.value) > 1e-12 else float("inf")

    p_obs: Optional[float] = None
    f_ext: Optional[float] = None
    gci_21: Optional[float] = None
    gci_32: Optional[float] = None
    asymptotic_ok: Optional[bool] = None
    note = "ok"

    # Observed order requires non-trivial refinement signal on both stages.
    if abs(eps_21) < 1e-14 or abs(eps_32) < 1e-14:
        note = "solution converged to within numerical precision on coarse triple; p_obs undefined"
    elif eps_21 * eps_32 < 0:
        note = (
            "oscillating convergence (sign flip between refinement stages) "
            "— Richardson formula does not directly apply; p_obs omitted"
        )
    else:
        # Uniform refinement ratio case (r_21 = r_32): simple log-ratio.
        # Non-uniform: use Celik §2.3 fixed-point iteration. We'll pick the
        # simple form when ratios agree within 5%; else iterate.
        diverged = False
        ratio_diff = abs(r_21 - r_32) / r_21
        if ratio_diff < 0.05:
            r = 0.5 * (r_21 + r_32)
            ratio = eps_32 / eps_21
            if abs(ratio) > 1e-300:
                p_obs = abs(math.log(abs(ratio))) / math.log(r)
        else:
            # Celik iterative method: p from ln(|eps_32 - sign*r_32^p|/|r_21^p * eps_21 - sign|)
            # Simplified iteration (Celik Eq. 2 + 3).
            # OverflowError guards: r**p_guess blows up for large p_guess on
            # asymmetric refinement triples — escape cleanly to p_obs=None
            # instead of raising into the report-generation layer.
            sign = 1.0 if eps_32 * eps_21 > 0 else -1.0
            p_guess: Optional[float] = 2.0
            for _ in range(50):
                try:
                    q = math.log(
                        (r_21 ** p_guess - sign) / (r_32 ** p_guess - sign)
                    )
                    new_p = (1.0 / math.log(r_21)) * abs(
                        math.log(abs(eps_32 / eps_21)) + q
                    )
                except (ValueError, ZeroDivisionError, OverflowError):
                    p_guess = None
                    diverged = True
                    break
                if abs(new_p - p_guess) < 1e-6:
                    p_guess = new_p
                    break
                p_guess = new_p
            if p_guess is not None and p_guess > 0:
                p_obs = p_guess
            elif diverged:
                note = (
                    "non-uniform refinement iteration diverged (numerical "
                    "overflow on asymmetric mesh triple); p_obs omitted"
                )

        if p_obs is not None and p_obs > 0:
            # Richardson extrapolation to h → 0. Guard every power against
            # OverflowError — large p_obs on non-uniform r still possible.
            try:
                r_fine = r_32
                denom = r_fine ** p_obs - 1.0
                if abs(denom) > 1e-12:
                    f_ext = fine.value + (fine.value - medium.value) / denom
                # GCI (Roache 1994 / Celik 2008 Eq. 5).
                gci_21 = _FS_THREE_GRID * e_21 / (r_21 ** p_obs - 1.0)
                gci_32 = _FS_THREE_GRID * e_32 / (r_32 ** p_obs - 1.0)
                # Asymptotic range check: GCI_21 / (r^p * GCI_32) ≈ 1 (±25% typical).
                if gci_32 and gci_32 > 0:
                    ratio = gci_21 / (r_21 ** p_obs * gci_32)
                    asymptotic_ok = 0.8 <= ratio <= 1.25
                    if not asymptotic_ok:
                        note = (
                            f"not in asymptotic range (GCI ratio = {ratio:.3f}; "
                            f"target ≈ 1.0 ±25%)"
                        )
            except OverflowError:
                f_ext = None
                gci_21 = None
                gci_32 = None
                asymptotic_ok = None
                note = (
                    f"GCI computation overflowed at p_obs={p_obs:.3f}; "
                    "Richardson extrapolation and GCI omitted"
                )
        elif p_obs == 0.0 or (p_obs is None and not diverged and note == "ok"):
            # Zero observed order: data does not monotonically reduce with
            # refinement (flat / inverse / pathological). Don't dress this as
            # a successful GCI; flag it so the reader stops reading GCI as
            # "uncertainty band" — there is no convergence to extrapolate.
            note = (
                "zero observed order of accuracy — refinement signal does "
                "not decay; Richardson extrapolation does not apply and GCI "
                "is not meaningful"
            )
            p_obs = None

    return RichardsonGCI(
        coarse=coarse, medium=medium, fine=fine,
        r_21=r_21, r_32=r_32,
        p_obs=p_obs, f_extrapolated=f_ext,
        e_21=e_21, e_32=e_32,
        gci_21=gci_21, gci_32=gci_32,
        asymptotic_range_ok=asymptotic_ok,
        note=note,
    )


def load_mesh_solutions_from_fixtures(
    case_id: str,
    mesh_labels: tuple[str, ...] = ("mesh_20", "mesh_40", "mesh_80", "mesh_160"),
    fixture_root: Optional[Path] = None,
) -> list[MeshSolution]:
    """Read mesh_N_measurement.yaml fixtures into MeshSolution records."""
    base = fixture_root or _FIXTURE_ROOT
    case_dir = base / case_id
    out: list[MeshSolution] = []
    for lbl in mesh_labels:
        p = case_dir / f"{lbl}_measurement.yaml"
        if not p.is_file():
            continue
        doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        meas = doc.get("measurement", {})
        val = meas.get("value")
        if val is None:
            continue
        try:
            v = float(val)
        except (ValueError, TypeError):
            continue
        # Derive 1D cell count from label (e.g. "mesh_40" → 40).
        try:
            n = int(lbl.split("_")[-1])
        except ValueError:
            continue
        out.append(MeshSolution(label=lbl, n_cells_1d=n, value=v))
    return out


def compute_gci_from_fixtures(
    case_id: str,
    fixture_root: Optional[Path] = None,
) -> Optional[RichardsonGCI]:
    """Convenience wrapper: load fixtures + compute GCI over finest 3 meshes.

    Returns None if fewer than 3 solutions available.
    Raises ValueError if the finest 3 aren't monotonically refined.
    """
    sols = load_mesh_solutions_from_fixtures(case_id, fixture_root=fixture_root)
    if len(sols) < 3:
        return None
    # Sort coarse → fine by n_cells_1d ascending, pick last 3.
    sols = sorted(sols, key=lambda s: s.n_cells_1d)
    coarse, medium, fine = sols[-3], sols[-2], sols[-1]
    return compute_richardson_gci(coarse, medium, fine)

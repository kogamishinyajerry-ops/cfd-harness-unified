"""P4 V71.B · coverage + anti-cheat test for the low-Re BFS resolved-wall gate.

Drives the FROZEN LIVE probe (``reports/showcase_aero/_v71b_bfs_lowre_probe/`` — a
REAL OF11 ``foamRun`` solve of the adapter-generated wall-RESOLVED case, NOT
authored; see its REPRODUCE.md) through the QoI extractor and the
``backward_facing_step_lowre`` gate, and asserts the gate PASSES on genuine solver
output — then proves every hard gate fails-closed by doctoring copies of the frozen
``proof/floor_faces.csv``.

The tests run OFFLINE against the frozen stdlib CSV (no Docker, no pyvista needed)
yet validate REAL physics: the measured Xr/H + floor y+ come from the solver field,
not from the gold. A separate fidelity test (``pytest.importorskip('pyvista')``)
proves the frozen CSV is a faithful serialization of the allPatches VTK — the live
production path reads the VTK; the offline gate reads the CSV; both feed the SAME
``_metrics_from_floor_faces`` core.

Honesty locks exercised here:
  - the gate PASSES on a real solve: Xr/H within 10% of the 6.26 blended anchor, all
    FOUR hard gates hold (reattachment-in-tol + resolved-near-wall + single
    reattachment + non-degenerate floor mask);
  - the gate is REAL: a field whose reattachment lands out of band → FAIL
    (reattachment_within_tol);
  - the resolved-wall claim is MACHINE-ENFORCED: a single floor face doctored to
    y+≈5 (a coarsened / wall-functioned mesh) → FAIL (resolved_near_wall), the gate
    arm the high-Re sibling would (correctly) trip;
  - single clean reattachment is a HARD gate: an injected extra wall-shear pos→neg
    crossing → FAIL (single_reattachment) even though the FIRST crossing is still in
    tolerance;
  - the floor mask must be non-degenerate: a truncated handful of faces → FAIL
    (floor_mask_nondegenerate) even with a valid crossing in tolerance;
  - missing artifacts raise rather than fabricate a default (fail-closed);
  - the extractor MEASURES (does not echo the gold): the measured Xr/H differs from
    the committed 6.26 reference yet lands inside the band;
  - VTK↔CSV fidelity: the pyvista read of the frozen VTK matches the stdlib read of
    the frozen CSV face-for-face.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Tuple

import pytest

from src.bfs_lowre_extractor import (
    extract_bfs_lowre,
    read_floor_faces_from_csv,
    to_key_quantities,
)
from src.bfs_lowre_gate import gate_bfs_lowre_against_gold

_REPO = Path(__file__).resolve().parents[2]
_PROBE = _REPO / "reports" / "showcase_aero" / "_v71b_bfs_lowre_probe"
_FROZEN_CSV = _PROBE / "proof" / "floor_faces.csv"
_FROZEN_VTK = _PROBE / "VTK" / "allPatches" / "allPatches_3000.vtk"
_GOLD_ANCHOR = 6.26  # the committed blended reference the extractor must NOT echo

Row = Tuple[float, float, float, float]  # (x, y, yplus, tau_x)


def _read_frozen_rows() -> List[Row]:
    """Parse the committed ``floor_faces.csv`` data rows (already x-sorted)."""
    rows: List[Row] = []
    for line in _FROZEN_CSV.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("x,"):
            continue
        p = s.split(",")
        rows.append((float(p[0]), float(p[1]), float(p[2]), float(p[3])))
    return rows


def _write_case(tmp_path: Path, rows: List[Row]) -> Path:
    """Materialize a doctored ``<case>/proof/floor_faces.csv`` and return the case dir."""
    case = tmp_path / "case"
    (case / "proof").mkdir(parents=True)
    body = ["# doctored fixture (test)", "x,y,yplus,tau_x"]
    body += [f"{x:.6e},{y:.6e},{yp:.6e},{tx:.6e}" for (x, y, yp, tx) in rows]
    (case / "proof" / "floor_faces.csv").write_text("\n".join(body) + "\n", encoding="utf-8")
    return case


def _doctor(tmp_path: Path, fn: Callable[[List[Row]], List[Row]]) -> Path:
    """Apply ``fn`` to the frozen rows and write a doctored case."""
    return _write_case(tmp_path, fn(_read_frozen_rows()))


# ---------------------------------------------------------------------------
# 1. genuine solve → PASS
# ---------------------------------------------------------------------------


def test_gate_passes_on_frozen_live_probe():
    """The real OF11 solve clears all four arms of the gate."""
    g = gate_bfs_lowre_against_gold(_PROBE)
    assert g.passed, g.summary
    assert g.reattachment_within_tol
    assert g.resolved_near_wall_ok
    assert g.single_reattachment_ok
    assert g.floor_mask_nondegenerate_ok
    # the DEFINING resolved-wall property, measured (not attested)
    assert g.metrics.floor_yplus_max < 1.0
    assert g.metrics.n_pos_neg_crossings == 1
    assert g.metrics.n_floor_faces >= 50


def test_extractor_measures_does_not_echo_gold():
    """The measured Xr/H is the solver's, distinct from the 6.26 reference yet in band."""
    m = extract_bfs_lowre(_PROBE)
    assert m.reattachment_xr_h != _GOLD_ANCHOR
    assert abs(m.reattachment_xr_h / _GOLD_ANCHOR - 1.0) <= 0.10
    # frozen physics check (the documented 5.881, −6.05% vs 6.26)
    assert m.reattachment_xr_h == pytest.approx(5.8812, abs=1e-3)
    assert m.reattachment_method == "wall_shear_tau_x_zero_crossing"
    kq = to_key_quantities(m)
    assert kq["reattachment_length"] == pytest.approx(m.reattachment_xr_h)


# ---------------------------------------------------------------------------
# 2. anti-cheat: each hard gate fails-closed
# ---------------------------------------------------------------------------


def test_reattachment_out_of_band_fails(tmp_path):
    """A field whose reattachment lands out of the 10% band → FAIL.

    Shrinking every x toward the step pulls the wall-shear pos→neg crossing in to
    Xr/H≈5.29 (−15% vs 6.26), outside [5.634, 6.886] — the sign pattern (single
    crossing) and the floor y+ are untouched, so ONLY the tolerance arm trips.
    """
    case = _doctor(tmp_path, lambda rows: [(x * 0.9, y, yp, tx) for (x, y, yp, tx) in rows])
    g = gate_bfs_lowre_against_gold(case)
    assert not g.passed
    assert not g.reattachment_within_tol
    # the resolved-wall regime + clean single reattachment are intact
    assert g.resolved_near_wall_ok
    assert g.single_reattachment_ok
    assert g.floor_mask_nondegenerate_ok


def test_coarsened_floor_yplus_fails_resolved_gate(tmp_path):
    """One floor face doctored to y+≈5 (wall-functioned / coarse) → FAIL.

    This is the arm that distinguishes the slice: the high-Re sibling measures
    ~4.2 here and must NOT keep a 'resolved' badge. ``max(yPlus)`` over the floor
    rises above 1 while reattachment stays in tolerance.
    """
    def coarsen(rows: List[Row]) -> List[Row]:
        out = list(rows)
        x, y, _yp, tx = out[60]
        out[60] = (x, y, 5.0, tx)  # a single first-cell y+≈5 face
        return out

    case = _doctor(tmp_path, coarsen)
    g = gate_bfs_lowre_against_gold(case)
    assert not g.passed
    assert not g.resolved_near_wall_ok
    assert g.metrics.floor_yplus_max >= 1.0
    # reattachment unchanged → only the resolved-wall precondition trips
    assert g.reattachment_within_tol
    assert g.single_reattachment_ok


def test_injected_extra_crossing_fails_single_reattachment(tmp_path):
    """An extra wall-shear pos→neg crossing downstream → FAIL.

    Flip ONE attached (tau_x<0) downstream face positive: its left neighbour stays
    negative (neg→pos, not counted) and its right neighbour stays negative
    (pos→neg, COUNTED), so the crossing count goes 1→2. The FIRST crossing (the
    real reattachment at x≈5.88) is unchanged and still in tolerance — only the
    single-reattachment arm catches the spurious feature.
    """
    def inject(rows: List[Row]) -> List[Row]:
        out = list(rows)
        # pick a downstream attached face (x≈12), well past reattachment
        idx = next(i for i, (x, _y, _yp, tx) in enumerate(out) if x > 11.0 and tx < 0)
        x, y, yp, _tx = out[idx]
        out[idx] = (x, y, yp, +1.0e-3)  # a positive spike between two negatives
        return out

    case = _doctor(tmp_path, inject)
    g = gate_bfs_lowre_against_gold(case)
    assert not g.passed
    assert not g.single_reattachment_ok
    assert g.metrics.n_pos_neg_crossings == 2
    # first crossing (real reattachment) still in band, floor still resolved
    assert g.reattachment_within_tol
    assert g.resolved_near_wall_ok


def test_degenerate_floor_mask_fails(tmp_path):
    """A handful of faces (< _MIN_FLOOR_FACES) → FAIL even with a valid crossing.

    Keep a contiguous 38-face span straddling the reattachment so the extractor
    still finds exactly one pos→neg crossing in tolerance — but 38 < 50, so the
    verdict must not rest on a malformed/under-resolved mesh.
    """
    case = _doctor(tmp_path, lambda rows: rows[20:58])
    g = gate_bfs_lowre_against_gold(case)
    assert not g.passed
    assert not g.floor_mask_nondegenerate_ok
    assert g.metrics.n_floor_faces < 50
    # the slice still has a single in-band reattachment + resolved floor
    assert g.single_reattachment_ok
    assert g.reattachment_within_tol
    assert g.resolved_near_wall_ok


def test_missing_artifacts_raise_not_fabricate(tmp_path):
    """No floor-face source under the case dir → raise (never a fabricated pass)."""
    empty = tmp_path / "empty_case"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        gate_bfs_lowre_against_gold(empty)


def test_no_reattachment_field_raises(tmp_path):
    """A floor with no wall-shear pos→neg crossing (never reattaches) → raise."""
    # force every face attached (tau_x<0): no recirculation bubble ever closes
    case = _doctor(tmp_path, lambda rows: [(x, y, yp, -abs(tx) - 1e-6) for (x, y, yp, tx) in rows])
    with pytest.raises(ValueError):
        gate_bfs_lowre_against_gold(case)


def test_vtk_fallback_picks_latest_by_numeric_timestep(tmp_path, monkeypatch):
    """Codex R1 P2: the VTK fallback selects the latest snapshot by NUMERIC timestep.

    Lexicographically ``allPatches_900.vtk`` sorts AFTER ``allPatches_3000.vtk`` ('9'
    > '3'), which would feed the gate an early, unconverged field. With no frozen CSV
    present, ``extract_bfs_lowre`` must take the VTK branch and pick ``_3000``.
    ``read_floor_faces_from_vtk`` is stubbed (no pyvista / real VTK needed) to record
    which file was chosen.
    """
    import src.bfs_lowre_extractor as ext

    vtk_dir = tmp_path / "VTK" / "allPatches"
    vtk_dir.mkdir(parents=True)
    for name in ("allPatches_100.vtk", "allPatches_900.vtk", "allPatches_3000.vtk"):
        (vtk_dir / name).write_bytes(b"")  # contents irrelevant — reader is stubbed

    picked: dict[str, str] = {}

    def _fake_reader(path):
        picked["name"] = path.name
        # a minimal floor with exactly one pos→neg crossing so _metrics doesn't raise
        return [1.0, 2.0, 3.0], [0.1, 0.1, 0.1], [1.0, -1.0, -1.0]

    monkeypatch.setattr(ext, "read_floor_faces_from_vtk", _fake_reader)
    m = ext.extract_bfs_lowre(tmp_path)
    assert picked["name"] == "allPatches_3000.vtk"
    assert m.n_floor_faces == 3


# ---------------------------------------------------------------------------
# 3. VTK ↔ CSV fidelity (the frozen CSV faithfully serializes the VTK)
# ---------------------------------------------------------------------------


def test_frozen_csv_matches_vtk():
    """The stdlib CSV read matches the pyvista VTK read face-for-face (shared mask).

    This equivalence is what LICENSES the offline CSV replay to stand in for the
    production VTK path: a live workbench case has NO frozen ``proof/floor_faces.csv``,
    so ``extract_bfs_lowre`` takes the VTK branch (``src.bfs_lowre_extractor`` resolution
    order); the frozen probe ships the CSV so the stdlib gate runs without pyvista. The
    two are NOT independently trusted — this test proves the CSV is a faithful, shared-
    mask serialization of the VTK, so a hand-edited CSV that diverged from the solver
    field would fail here. ``importorskip`` keeps the stdlib gate green on a pyvista-less
    box, but the canonical interpreter (``.venv``) HAS pyvista, so this guard runs in CI.
    """
    pytest.importorskip("pyvista")
    from src.bfs_lowre_extractor import read_floor_faces_from_vtk

    xs_c, yp_c, tx_c = read_floor_faces_from_csv(_FROZEN_CSV)
    xs_v, yp_v, tx_v = read_floor_faces_from_vtk(_FROZEN_VTK)
    assert len(xs_c) == len(xs_v)

    # both masked by the SAME bfs_floor_mask → identical face set; compare sorted-by-x
    def _sort(xs, yp, tx):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        return ([xs[i] for i in order], [yp[i] for i in order], [tx[i] for i in order])

    xs_c, yp_c, tx_c = _sort(xs_c, yp_c, tx_c)
    xs_v, yp_v, tx_v = _sort(xs_v, yp_v, tx_v)
    for a, b in zip(xs_c, xs_v):
        assert a == pytest.approx(b, abs=1e-5)
    for a, b in zip(yp_c, yp_v):
        assert a == pytest.approx(b, rel=1e-4, abs=1e-6)
    for a, b in zip(tx_c, tx_v):
        assert a == pytest.approx(b, rel=1e-4, abs=1e-9)

"""Phase 7d — Richardson GCI unit tests."""
from __future__ import annotations

import math

import pytest

from ui.backend.services.grid_convergence import (
    MeshSolution,
    RichardsonGCI,
    compute_richardson_gci,
    compute_gci_from_fixtures,
)


def test_second_order_synthetic() -> None:
    """Synthetic data: f_h = f_exact + C * h^2 (formal 2nd-order).
    With finer meshes (errors << 1), we land in asymptotic range.
    f_exact = 1.0, C = 0.001 (small correction).
    """
    import math as _m
    def fh(h):
        return 1.0 + 0.001 * h ** 2
    coarse = MeshSolution("mesh_40", 40, fh(1 / 40))
    medium = MeshSolution("mesh_80", 80, fh(1 / 80))
    fine = MeshSolution("mesh_160", 160, fh(1 / 160))
    gci = compute_richardson_gci(coarse, medium, fine)
    assert gci.r_21 == pytest.approx(2.0)
    assert gci.r_32 == pytest.approx(2.0)
    assert gci.p_obs is not None
    assert gci.p_obs == pytest.approx(2.0, abs=1e-4)
    assert gci.f_extrapolated is not None
    assert gci.f_extrapolated == pytest.approx(1.0, abs=1e-9)
    assert gci.asymptotic_range_ok is True  # small errors → asymptotic


def test_first_order_synthetic() -> None:
    """f_h = 1.0 + 0.5 * h with h = 0.1, 0.05, 0.025 → p_obs = 1.0."""
    coarse = MeshSolution("m10", 10, 1.0 + 0.5 * 0.1)
    medium = MeshSolution("m20", 20, 1.0 + 0.5 * 0.05)
    fine = MeshSolution("m40", 40, 1.0 + 0.5 * 0.025)
    gci = compute_richardson_gci(coarse, medium, fine)
    assert gci.p_obs == pytest.approx(1.0, abs=1e-6)


def test_rejects_non_monotone_refinement() -> None:
    coarse = MeshSolution("big", 40, 1.0)
    medium = MeshSolution("small", 20, 1.1)
    fine = MeshSolution("mid", 30, 1.05)
    with pytest.raises(ValueError, match="not monotonically refined"):
        compute_richardson_gci(coarse, medium, fine)


def test_oscillating_convergence_note() -> None:
    """When eps_21 and eps_32 have opposite signs, p_obs is undefined."""
    coarse = MeshSolution("c", 10, 1.0)
    medium = MeshSolution("m", 20, 1.5)  # +0.5
    fine = MeshSolution("f", 40, 1.2)    # -0.3 (opposite direction)
    gci = compute_richardson_gci(coarse, medium, fine)
    assert gci.p_obs is None
    assert "oscillating" in gci.note


def test_converged_to_precision_note() -> None:
    """When eps is below numerical precision, p_obs is undefined."""
    coarse = MeshSolution("c", 10, 1.0)
    medium = MeshSolution("m", 20, 1.0)
    fine = MeshSolution("f", 40, 1.0)
    gci = compute_richardson_gci(coarse, medium, fine)
    assert gci.p_obs is None
    assert "precision" in gci.note.lower() or "converged" in gci.note.lower()


def test_ldc_fixtures_end_to_end() -> None:
    """Against the real LDC mesh_N fixtures (40/80/160): expect sensible p_obs + GCI."""
    gci = compute_gci_from_fixtures("lid_driven_cavity")
    assert gci is not None
    assert gci.p_obs is not None
    assert 0.5 < gci.p_obs < 2.5, f"p_obs out of expected range: {gci.p_obs}"
    assert gci.gci_32 is not None
    # GCI should be in percent-range (not absurd).
    assert 0 < gci.gci_32 < 1.0


def test_nonuniform_overflow_recovers_cleanly() -> None:
    """Codex round 1 finding #2 (DEC-V61-033): asymmetric refinement triples
    like (10, 16, 50) with f_h = 1 + 0.3*h^1.7 push r_21**p_guess past
    float64 and raised an uncaught OverflowError before the fix. After
    the fix, the iteration must escape to p_obs=None with a diagnostic
    note, not propagate the exception into the report-generation layer.
    """
    def fh(n):
        return 1.0 + 0.3 * (1.0 / n) ** 1.7
    coarse = MeshSolution("c", 10, fh(10))
    medium = MeshSolution("m", 16, fh(16))
    fine = MeshSolution("f", 50, fh(50))
    # Must not raise.
    gci = compute_richardson_gci(coarse, medium, fine)
    # p_obs either bounded and finite, OR None with a diagnostic. Either
    # outcome is acceptable; what is NOT acceptable is an unbounded raise.
    if gci.p_obs is None:
        assert "overflow" in gci.note.lower() or "iteration" in gci.note.lower() or "diverged" in gci.note.lower()
    else:
        assert math.isfinite(gci.p_obs)


def test_zero_observed_order_flagged_not_silent() -> None:
    """Codex round 1 finding #3 (DEC-V61-033): p_obs=0 falling through
    with note='ok' is misleading. Reader should see an explicit
    zero-order diagnostic instead.

    Reproducer: (1.0, 0.5, 0.0) → eps_21 = eps_32 = -0.5 → ratio=1 →
    p_obs raw = 0. GCI not meaningful here.
    """
    coarse = MeshSolution("c", 10, 1.0)
    medium = MeshSolution("m", 20, 0.5)
    fine = MeshSolution("f", 40, 0.0)
    gci = compute_richardson_gci(coarse, medium, fine)
    # Either p_obs stays 0.0 AND note explicitly flags it, OR p_obs is
    # normalized to None AND note flags it. Silent "ok" is the bug.
    assert gci.note != "ok", f"zero-order case must be flagged, got note={gci.note!r}"
    assert gci.gci_21 is None
    assert gci.gci_32 is None


def test_returns_none_on_insufficient_fixtures(tmp_path) -> None:
    """Graceful: if <3 mesh fixtures exist, returns None not raises."""
    case_dir = tmp_path / "nonexistent_case"
    case_dir.mkdir()
    (case_dir / "mesh_40_measurement.yaml").write_text(
        "measurement:\n  value: 1.0\n", encoding="utf-8",
    )
    result = compute_gci_from_fixtures("nonexistent_case", fixture_root=tmp_path)
    assert result is None

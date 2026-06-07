#!/usr/bin/env python3
"""Generate the SYNTHETIC offline fixture for the P4 wedge-oblique-shock gate tests.

================================  HONESTY  ================================
This is NOT a solver run. There is NO rhoCentralFoam, NO mesh, NO OpenFOAM
involved. This script hand-constructs a postProcessing/ tree whose values
correspond to an analytical M1=2.0, theta=15deg oblique shock, SOLELY so the
gate's PARSING + FAIL-CLOSED logic can be exercised in CI without a live solver
(which is blocked on an ESI image, DEC-V61-224 fork wall, deferred).

  * It does NOT validate any physics — the physics reference is locked by the
    self-verifying gold test (tests/p4/test_wedge_oblique_shock_gold.py).
  * It does NOT flip runnable-coverage 2->3 — the gold's contract_status stays
    ANALYTICAL_REFERENCE_AUTHORED · LIVE_RUN_PENDING.
  * The real FROZEN probe (a genuine converged rhoCentralFoam tail) REPLACES this
    fixture when the deferred live-flip slice lands.

The values are deliberately constructed so that (a) the post-shock state is
ideal-gas consistent (p2 = rho2 R T2, so the gate's thermodynamic-consistency hard
gate passes), and (b) beta (45.0deg) and M2 (1.44) sit slightly OFF the exact gold
references (45.34deg / 1.4457) yet inside the 3% band — proving the gate MEASURES
rather than echoes the gold.
==========================================================================

Run:  python3 reports/showcase_aero/_w71a_wedge_probe_SYNTHETIC/_build_synthetic_fixture.py
"""
from __future__ import annotations

import math
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_POST = _HERE / "postProcessing"
_TIME = "0.001"  # arbitrary converged-tail time dir

# --- analytical M1=2.0, theta=15deg oblique-shock state (see gold header) ---
GAMMA = 1.4
R = 287.058
P1 = 1.0e5
T1 = 300.0
RHO1 = P1 / (R * T1)            # 1.161078...
M1 = 2.0

# exact ratios for theta=15 (the gold references); we apply them to the freestream
# state and recompute rho2 from the ideal-gas law so p2/rho2/T2 are self-consistent.
P2_P1 = 2.1947
T2_T1 = 1.2694
P2 = P2_P1 * P1
T2 = T2_T1 * T1
RHO2 = P2 / (R * T2)           # -> rho2/rho1 ~= 1.7292 (within 3% of gold 1.7289)

# DELIBERATELY slightly off the exact gold (measures, not echoes):
M2_MEASURED = 1.44             # gold ref 1.4457 (0.4% low)
BETA_DEG_MEASURED = 45.0       # gold ref 45.3436 (0.76% low)
X_STATION = 0.5                # must equal wedge_inputs.x_shock_station in the gold


def _write_surface_field(probe: str, value: float) -> None:
    d = _POST / probe / _TIME
    d.mkdir(parents=True, exist_ok=True)
    (d / "surfaceFieldValue.dat").write_text(
        "# SYNTHETIC fixture (NOT a solver run) — see _build_synthetic_fixture.py\n"
        "# Region type : patch\n"
        "# Time        areaAverage\n"
        f"0.0009\t{value:.10g}\n"
        f"0.001\t{value:.10g}\n",
        encoding="utf-8",
    )


def _write_shock_line() -> None:
    """A vertical rho(y) sample at x=X_STATION: rho2 below the shock, rho1 above.

    The shock crossing is the steepest density step; its midpoint is y_shock, and
    beta = atan2(y_shock, x_station). We place sample points straddling y_shock so
    the midpoint lands exactly there.
    """
    y_shock = X_STATION * math.tan(math.radians(BETA_DEG_MEASURED))  # 0.5 for beta=45
    d = _POST / "shockLine" / _TIME
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# SYNTHETIC fixture (NOT a solver run) — distance rho", "# x = %.4f m" % X_STATION]
    # sample y = 0.01, 0.03, ... 0.99 (offset so 0.49 / 0.51 straddle y_shock=0.50)
    y = 0.01
    while y < 1.0:
        rho = RHO2 if y < y_shock else RHO1
        lines.append(f"{y:.4f}\t{rho:.10g}")
        y += 0.02
    (d / "line_rho.xy").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    _write_surface_field("freestream_p", P1)
    _write_surface_field("freestream_rho", RHO1)
    _write_surface_field("freestream_T", T1)
    _write_surface_field("freestream_Ma", M1)
    _write_surface_field("postShock_p", P2)
    _write_surface_field("postShock_rho", RHO2)
    _write_surface_field("postShock_T", T2)
    _write_surface_field("postShock_Ma", M2_MEASURED)
    _write_shock_line()
    print(f"wrote SYNTHETIC fixture under {_POST}")
    print(f"  rho1={RHO1:.6f} rho2={RHO2:.6f} rho2/rho1={RHO2/RHO1:.5f}")
    print(f"  p2/p1={P2/P1:.5f} T2/T1={T2/T1:.5f} M2={M2_MEASURED} beta~={BETA_DEG_MEASURED}")


if __name__ == "__main__":
    main()

"""P4 V73.B · offline replay of the frozen RAE 2822 Case 9 live probe.

The bundle ``reports/showcase_aero/_v73b_rae2822_probe/`` is REAL solver
output (rhoSimpleFoam + kOmegaSST, ESI v2312, converged at iter 2627 on
residualControl 5e-5) frozen with a SHA256 tamper manifest. These tests
replay the V73.A extractor + two-tier gate on it and PIN the verdict:

    tier-1 SANITY-PASS (all 9 gates)  ·  tier-2 ENFORCED **FAIL**

The ENFORCED FAIL is the deliverable, not a defect: vanilla
rhoSimpleFoam+SST reproducibly sits aft-shock/high-lift on this case
(RESULT.md §3) and the gate says so. A future change that silently turns
this CONFLICT into a PASS without a physics-level fix should trip these
pins.

The live solve itself is exercised by the opt-in test at the bottom
(CFDTRUST_LIVE_TRANSONIC_E2E=1), mirroring the V71.A/B convention.
"""
from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

import pytest

from src.transonic_airfoil_extractor import extract_transonic_airfoil
from src.transonic_airfoil_gate import gate_transonic_airfoil_against_gold

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO / "reports" / "showcase_aero" / "_v73b_rae2822_probe"
T_SNAP = 2627

pytestmark = pytest.mark.skipif(
    not PROBE.is_dir(), reason="frozen V73.B probe bundle absent"
)


@pytest.fixture(scope="module")
def metrics():
    return extract_transonic_airfoil(PROBE, chord=1.0, gamma=1.4, r_specific=287.058)


@pytest.fixture(scope="module")
def gate():
    return gate_transonic_airfoil_against_gold(PROBE)


class TestTamperManifest:
    def test_sha256sums_verifies(self):
        proc = subprocess.run(
            ["shasum", "-a", "256", "-c", "SHA256SUMS", "--quiet"],
            cwd=PROBE, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"tamper manifest failed:\n{proc.stdout}{proc.stderr}"

    def test_manifest_covers_every_file(self):
        listed = {
            line.split("  ", 1)[1].strip()
            for line in (PROBE / "SHA256SUMS").read_text().splitlines() if line
        }
        actual = {
            f"./{p.relative_to(PROBE)}"
            for p in PROBE.rglob("*")
            if p.is_file() and p.name != "SHA256SUMS"
        }
        assert listed == actual, (
            f"manifest drift: missing={sorted(actual - listed)} "
            f"stale={sorted(listed - actual)}"
        )


class TestFrozenExtraction:
    """Pin the extracted numbers (first live exercise of the V73.A
    face-centre extraction path — these values double as its regression
    baseline)."""

    def test_forces(self, metrics):
        assert metrics.cl_fc == pytest.approx(0.8777, abs=2e-4)
        assert metrics.cd_fc == pytest.approx(0.03037, abs=5e-5)
        assert metrics.cl_p == pytest.approx(0.8691, abs=2e-4)

    def test_shock_position(self, metrics):
        assert metrics.shock_xc == pytest.approx(0.6005, abs=1e-3)
        assert metrics.shock_decline_reason is None

    def test_freestream_measured_vs_declared(self, metrics):
        assert metrics.measured.mach == pytest.approx(0.7340, abs=5e-4)
        assert metrics.measured.alpha_deg == pytest.approx(2.676, abs=5e-3)
        assert metrics.declared.mach == pytest.approx(0.7341, abs=5e-4)
        assert metrics.declared.alpha_deg == pytest.approx(2.790, abs=1e-3)
        assert metrics.reynolds_declared == pytest.approx(6.5e6, rel=1e-3)

    def test_contour_split_population(self, metrics):
        # 320 wrap cells -> both branches well-populated, no starvation
        assert metrics.n_upper > 200 and metrics.n_lower > 200

    def test_cp_physics_bounds(self, metrics):
        assert metrics.max_cp == pytest.approx(1.1366, abs=1e-3)
        assert metrics.min_cp_upper == pytest.approx(-1.3414, abs=2e-3)


class TestFrozenVerdict:
    def test_tier1_sanity_pass(self, gate):
        assert gate.sanity_passed is True
        for leg in ("freestream_mach_ok", "alpha_ok", "reynolds_ok",
                    "stagnation_ok", "supersonic_pocket_ok", "shock_ok",
                    "ranges_ok", "cl_crosscheck_ok"):
            assert getattr(gate, leg) is True, leg

    def test_tier2_enforced_and_failed(self, gate):
        # anchors numerized + provenance accepted -> ENFORCED (not
        # PROVISIONAL); the run honestly misses both ENFORCED anchors
        assert gate.tier2_mode == "ENFORCED"
        assert gate.tier2_passed is False

    def test_summary_carries_both_misses(self, gate):
        assert "SANITY-PASS" in gate.summary
        assert "ENFORCED FAIL" in gate.summary
        # the breadth-anchor invariant (V73 cannot move coverage)
        assert "runnable-coverage stays 3" in gate.summary

    def test_yplus_resolved_wall_claim(self):
        rows = [
            l.split() for l in
            (PROBE / "postProcessing/yPlus1/0/yPlus.dat").read_text().splitlines()
            if l and not l.startswith("#")
        ]
        t, _patch, _mn, mx, avg = rows[-1][:5]
        assert int(t) == T_SNAP
        assert float(mx) <= 1.0, "B109 resolved-wall claim: y+ max <= 1"


class TestSnapshotAlignment:
    """The three planes (surface write, forceCoeffs row, probe row) must all
    exist AT t_snap — the property whose absence fail-closes the extractor."""

    def test_surface_write_at_t_snap(self):
        assert (PROBE / f"postProcessing/airfoilSurface/{T_SNAP}/p_aerofoil.raw").is_file()

    def test_force_and_probe_rows_at_t_snap(self):
        for rel in ("postProcessing/forceCoeffs1/0/coefficient.dat",
                    "postProcessing/freestreamProbe/0/surfaceFieldValue.dat"):
            times = [
                int(l.split()[0]) for l in (PROBE / rel).read_text().splitlines()
                if l and not l.startswith("#")
            ]
            assert T_SNAP in times, f"{rel} missing row at t_snap"

    def test_convergence_statement_frozen(self):
        log = (PROBE / "logs/log.rhoSimpleFoam.headtail").read_text()
        assert f"SIMPLE solution converged in {T_SNAP} iterations" in log, (
            "t_snap must be the SELF-STOPPED convergence iteration "
            "(pre-registered protocol, not a hand-picked time)"
        )


_LIVE = os.environ.get("CFDTRUST_LIVE_TRANSONIC_E2E") == "1"


@pytest.mark.skipif(
    not _LIVE,
    reason="opt-in live e2e: set CFDTRUST_LIVE_TRANSONIC_E2E=1 (needs docker + ESI image; ~30 min)",
)
class TestLiveTransonicE2E:
    def test_generate_solve_gate(self, tmp_path):
        case = tmp_path / "rae2822_live"
        subprocess.run(
            ["python3", str(REPO / "scripts/p4/generate_rae2822_case9.py"), str(case)],
            check=True,
        )
        script = (
            "source /openfoam/profile.rc >/dev/null 2>&1; cd /work && "
            "blockMesh > log.blockMesh 2>&1 && checkMesh > log.checkMesh 2>&1 && "
            "decomposePar -force > log.decomposePar 2>&1 && "
            "mpirun --allow-run-as-root -np 8 rhoSimpleFoam -parallel > log.rhoSimpleFoam 2>&1 && "
            "reconstructPar -latestTime > log.reconstructPar 2>&1"
        )
        subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "bash",
             "-v", f"{case}:/work", "opencfd/openfoam-default:2312", "-c", script],
            check=True, timeout=3600 * 2,
        )
        res = gate_transonic_airfoil_against_gold(case)
        assert res.sanity_passed is True
        assert res.tier2_mode == "ENFORCED"
        # the frozen-probe CONFLICT is reproducible, not a one-off
        assert res.tier2_passed is False

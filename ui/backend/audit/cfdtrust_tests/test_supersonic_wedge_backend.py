"""P4 V71.A · DEC-V61-234 — cfdtrust openfoam backend reconciliation tests.

Proves the ``cfdtrust run`` V&V backend DISPATCHES the manifest-declared solver
(rhoCentralFoam) on the ESI image with the ESI profile — NOT a hardcoded
``simpleFoam`` under the Foundation OF11 bashrc — so it is reconciled with (not
divergent from) the ``foam_agent_adapter`` execution backend, per the
DEC-V61-224(b) image-reconciliation provision. Also pins the injection fence on
the now-manifest-driven solver verb (the existing image fence never covered it).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cfdtrust.backends import openfoam as ofa


# --------------------------------------------------------------------------
# helper unit tests — env-fork + solver sanitiser
# --------------------------------------------------------------------------

def test_env_setup_for_image_routes_esi_vs_foundation():
    assert ofa._env_setup_for_image("opencfd/openfoam-default:2312") == "/openfoam/profile.rc"
    assert ofa._env_setup_for_image("openfoam/openfoam11-paraview510:latest") == "/opt/openfoam11/etc/bashrc"
    # unknown image → Foundation default (historical behaviour preserved).
    assert ofa._env_setup_for_image("some/other:tag") == "/opt/openfoam11/etc/bashrc"


def test_resolve_solver_name_manifest_driven_with_fallback():
    assert ofa._resolve_solver_name({"solver": "rhoCentralFoam"}) == "rhoCentralFoam"
    assert ofa._resolve_solver_name({}) == "simpleFoam"            # omit → simpleFoam
    assert ofa._resolve_solver_name({"solver": "   "}) == "simpleFoam"


def test_resolve_solver_name_rejects_injection():
    for bad in ("rm -rf /", "simpleFoam; cat /etc/passwd", "foo$(id)", "a|b", "../x", "-rf"):
        with pytest.raises(ValueError):
            ofa._resolve_solver_name({"solver": bad})


# --------------------------------------------------------------------------
# run() integration — manifest-driven dispatch on the ESI image
# --------------------------------------------------------------------------

def _make_case(case_dir: Path) -> None:
    for sub in ("system", "constant", "0"):
        (case_dir / sub).mkdir(parents=True, exist_ok=True)


def _patch_capturing_docker(monkeypatch):
    """Fake docker subprocess recording every ``docker run ... -c <cmd>``."""
    monkeypatch.setattr(ofa.shutil, "which", lambda cmd: "/usr/local/bin/docker")
    runs: list[dict] = []

    def fake_run(args, **kwargs):
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        if "version" in args:
            R.stdout = "26.0.0\n"
            return R()
        if "inspect" in args:
            return R()
        cmd_str = args[-1] if args else ""
        runs.append({"argv": list(args), "shell": cmd_str})
        if "rhoCentralFoam" in cmd_str:
            R.stdout = (
                "Time = 1e-06\n"
                "diagonal:  Solving for rho, Initial residual = 0.1, "
                "Final residual = 0.01, No Iterations 1\n"
            )
        return R()

    monkeypatch.setattr(ofa.subprocess, "run", fake_run)
    return runs


def test_run_dispatches_rhocentralfoam_on_esi_image(monkeypatch, tmp_path: Path):
    """A compressible manifest must dispatch rhoCentralFoam (NOT simpleFoam) and
    source the ESI profile (NOT the OF11 bashrc) on the ESI image — the
    DEC-V61-224(b) reconciliation."""
    _make_case(tmp_path)
    runs = _patch_capturing_docker(monkeypatch)

    ofa.run(
        tmp_path,
        {
            "solver": "rhoCentralFoam",
            "solver_docker_image": "opencfd/openfoam-default:2312",
        },
    )

    solver_runs = [r for r in runs if "rhoCentralFoam" in r["shell"]]
    assert solver_runs, "the solver step must dispatch rhoCentralFoam"
    sr = solver_runs[0]
    assert "simpleFoam" not in sr["shell"]                  # NOT the old hardcode
    assert "source /openfoam/profile.rc" in sr["shell"]     # ESI profile
    assert "/opt/openfoam11/etc/bashrc" not in sr["shell"]  # NOT the OF11 bashrc
    assert "opencfd/openfoam-default:2312" in sr["argv"]    # ESI image in the argv


def test_run_defaults_to_simplefoam_on_foundation_image(monkeypatch, tmp_path: Path):
    """An incompressible manifest that omits ``solver`` stays simpleFoam under the
    Foundation OF11 bashrc — the existing path must be byte-stable."""
    _make_case(tmp_path)
    runs = _patch_capturing_docker(monkeypatch)

    ofa.run(tmp_path, {})  # no solver, no image → simpleFoam + default OF11 image

    solver_runs = [
        r for r in runs
        if "simpleFoam" in r["shell"]
        and "blockMesh" not in r["shell"]
        and "checkMesh" not in r["shell"]
    ]
    assert solver_runs, "default dispatch must be simpleFoam"
    assert "source /opt/openfoam11/etc/bashrc" in solver_runs[0]["shell"]


def test_run_blocks_on_injection_solver_name(monkeypatch, tmp_path: Path):
    """A metachar-laden manifest solver must BLOCK before any container call —
    the new manifest→argv path must not become an injection surface."""
    _make_case(tmp_path)
    runs = _patch_capturing_docker(monkeypatch)

    result = ofa.run(tmp_path, {"solver": "simpleFoam; rm -rf /"})

    assert result["status"] == "BLOCKED"
    assert result["details"]["reason"] == "manifest_invalid_solver_name"
    assert all("rm -rf" not in r["shell"] for r in runs)  # never reached a container

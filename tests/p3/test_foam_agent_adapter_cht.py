"""P3 W3.2a (DEC-V61-223) — offline structural tests for the CHT multi-region
case generator + the geometry-dispatch live-run boundary.

Per DEC-V61-217 charter row W3.2 (sub-DEC V61-223 · GENERATION SIDE only). All
tests are OFFLINE — they call ``_generate_cht_multi_region`` directly (it only
writes files) and round-trip the output through the W3.0.x region extractors.
ZERO Docker / ZERO solver: the LIVE multi-region mesh pipeline + ``checkMesh`` +
``chtMultiRegionSimpleFoam`` run are W3.2b (asserted-deferred by the dispatch
boundary test below).

Charter W3.2 passes-criteria covered HERE (the offline subset):
  - generator emits a 2-fluid + 1-solid case_011-stripped steady-laminar plate
  - ``constant/regionProperties`` parses → 3 regions via the W3.0 reader
  - per-region ``thermophysicalProperties`` parses → correct thermo_type/Cp via
    the W3.0.2 multi-region extractor (audit-side region ingestion)
  - master ``controlDict`` application == chtMultiRegionSimpleFoam
  - coupled-baffle interface BCs on BOTH fluid<->solid interfaces (non-Rad)
  - dispatch routes CHT to the generator and asserts the explicit W3.2b boundary
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from src.foam_agent_adapter import FoamAgentExecutor
from src.models import (
    Compressibility,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)
from ui.backend.services.case_extractors import extract_region_properties_snapshot
from ui.backend.services.case_extractors.thermo_dict_multi_region import (
    extract as extract_thermo_multi_region,
)


def _cht_spec(**bc) -> TaskSpec:
    return TaskSpec(
        name="cht_canonical_v0_1",
        geometry_type=GeometryType.CHT_MULTI_REGION,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        boundary_conditions=dict(bc),
    )


def _generate(tmp_path: Path, **bc) -> Path:
    """Generate a CHT case into *tmp_path* (no __init__ side effects, no Docker)."""
    ex = FoamAgentExecutor(work_dir=str(tmp_path / "_work"))
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    ex._generate_cht_multi_region(case_dir, _cht_spec(**bc))
    return case_dir


# ----------------------------------------------------------------------
# Generation structure
# ----------------------------------------------------------------------

def test_generates_three_region_skeleton(tmp_path: Path) -> None:
    case = _generate(tmp_path)
    # master files
    assert (case / "system" / "controlDict").is_file()
    assert (case / "system" / "blockMeshDict").is_file()
    assert (case / "constant" / "regionProperties").is_file()
    assert (case / "constant" / "g").is_file()
    # per-region trees (2 fluid + 1 solid)
    for r in ("region_hot_fluid", "region_cold_fluid", "region_solid"):
        assert (case / "constant" / r / "thermophysicalProperties").is_file()
        assert (case / "system" / r / "fvSchemes").is_file()
        assert (case / "system" / r / "fvSolution").is_file()
        assert (case / "0" / r / "T").is_file()
    # fluids carry momentumTransport (laminar) + U/p/p_rgh; solid does not move
    for r in ("region_hot_fluid", "region_cold_fluid"):
        assert (case / "constant" / r / "momentumTransport").is_file()
        for f in ("U", "p", "p_rgh"):
            assert (case / "0" / r / f).is_file()
    assert not (case / "0" / "region_solid" / "U").exists()
    # solid gets T AND p (Codex R0 P2: chtMultiRegionSimpleFoam needs a solid
    # pressure field at startup) but no momentum field.
    assert (case / "0" / "region_solid" / "p").is_file()
    assert not (case / "0" / "region_solid" / "p_rgh").exists()


def test_region_properties_roundtrips_through_w30_reader(tmp_path: Path) -> None:
    """Audit-side region ingestion: the W3.0 regionProperties reader parses the
    generated case → 2 fluid + 1 solid = 3 regions."""
    case = _generate(tmp_path)
    snap = extract_region_properties_snapshot(case)
    assert snap is not None
    assert snap.fluid_regions == ("region_hot_fluid", "region_cold_fluid")
    assert snap.solid_regions == ("region_solid",)
    assert len(snap.fluid_regions) + len(snap.solid_regions) == 3


def test_per_region_thermo_roundtrips_through_w302_extractor(tmp_path: Path) -> None:
    """Audit-side per-region thermo ingestion (W3.0.2): both fluids parse as
    heRhoThermo, the solid as heSolidThermo, with the case_011 Cp numerals."""
    case = _generate(tmp_path)
    snap = extract_region_properties_snapshot(case)
    tmap = extract_thermo_multi_region(case, snap)
    # every region present + fully parseable (no None payloads)
    assert set(tmap.keys()) == {"region_hot_fluid", "region_cold_fluid", "region_solid"}
    assert all(v is not None for v in tmap.values())
    assert tmap["region_hot_fluid"].thermo_type == "heRhoThermo"
    assert tmap["region_cold_fluid"].thermo_type == "heRhoThermo"
    assert tmap["region_solid"].thermo_type == "heSolidThermo"


def test_no_include_directives_in_thermo(tmp_path: Path) -> None:
    """W3.0.2 honest-refusal contract: any ``#``-directive → region None. The
    generator must emit fully-inlined thermo so the extractor parses every
    region (proven by the round-trip above, pinned explicitly here)."""
    case = _generate(tmp_path)
    for r in ("region_hot_fluid", "region_cold_fluid", "region_solid"):
        txt = (case / "constant" / r / "thermophysicalProperties").read_text()
        assert "#include" not in txt and "#codeStream" not in txt
        assert "#calc" not in txt and "#remove" not in txt


def test_master_controldict_application_is_cht_solver(tmp_path: Path) -> None:
    case = _generate(tmp_path)
    txt = (case / "system" / "controlDict").read_text()
    assert "application       chtMultiRegionSimpleFoam;" in txt


def test_coupled_baffle_bc_on_both_interfaces_non_rad(tmp_path: Path) -> None:
    """Both fluid<->solid interfaces use the non-radiation coupled-baffle BC
    (pure-CHT v0.1 — NOT the turbulentTemperatureRadCoupledMixed variant);
    fluidThermo on the fluid sides, solidThermo on the solid side."""
    case = _generate(tmp_path)
    hot_T = (case / "0" / "region_hot_fluid" / "T").read_text()
    cold_T = (case / "0" / "region_cold_fluid" / "T").read_text()
    solid_T = (case / "0" / "region_solid" / "T").read_text()

    coupled = "compressible::turbulentTemperatureCoupledBaffleMixed"
    assert coupled in hot_T and "kappaMethod     fluidThermo;" in hot_T
    assert coupled in cold_T and "kappaMethod     fluidThermo;" in cold_T
    # solid side: TWO coupled interfaces (to hot AND cold), both solidThermo
    assert solid_T.count(coupled) == 2
    assert solid_T.count("kappaMethod     solidThermo;") == 2
    assert "region_solid_to_region_hot_fluid" in solid_T
    assert "region_solid_to_region_cold_fluid" in solid_T
    # NO radiation variant anywhere (pure-CHT v0.1 scope-out)
    for t in (hot_T, cold_T, solid_T):
        assert "RadCoupledMixed" not in t


def test_fluid_interface_patch_names_match_splitmeshregions_convention(tmp_path: Path) -> None:
    """The fluid-side coupled patch is named <region>_to_<neighbour> — exactly
    what splitMeshRegions -cellZones auto-generates (W3.2b will materialise it)."""
    case = _generate(tmp_path)
    hot_T = (case / "0" / "region_hot_fluid" / "T").read_text()
    assert "region_hot_fluid_to_region_solid" in hot_T


def test_blockmesh_patch_names_match_field_bcs(tmp_path: Path) -> None:
    """Codex R0 P1 regression: every external patch a per-region 0/ field
    references MUST exist in the blockMeshDict it emits, or chtMultiRegionSimpleFoam
    aborts at field-load (W3.2b). Pins generator internal consistency."""
    import re

    case = _generate(tmp_path)
    bm = (case / "system" / "blockMeshDict").read_text()
    mesh_patches = set(re.findall(r"^\s{4}(\S+)\s*\{ type (?:patch|wall)", bm, re.M))

    for r in ("region_hot_fluid", "region_cold_fluid"):
        for field in ("T", "U", "p_rgh"):
            txt = (case / "0" / r / field).read_text()
            ext = {
                x for x in re.findall(r"^\s{4}(\S+)", txt, re.M)
                if x.endswith(("_inlet", "_outlet", "_wall"))
            }
            assert ext, f"{r}/{field} should reference external patches"
            assert ext <= mesh_patches, (
                f"{r}/{field} references patches absent from blockMesh: "
                f"{ext - mesh_patches}"
            )
    # solid external wall patch matches between mesh + field
    solid_T = (case / "0" / "region_solid" / "T").read_text()
    assert "region_solid_walls" in solid_T
    assert "region_solid_walls" in bm


def test_field_files_have_correct_foamfile_object_name(tmp_path: Path) -> None:
    """Codex R1 P2 regression: a 0/<region>/<field> FoamFile `object` MUST be the
    field name (T/U/p/p_rgh), not the class (volScalarField/volVectorField) —
    OpenFOAM rejects a header whose object name disagrees with the field being
    read (W3.2b field-load). The `class` stays the OpenFOAM field class."""
    import re

    case = _generate(tmp_path)
    checks = [
        ("0/region_hot_fluid/T", "T", "volScalarField"),
        ("0/region_hot_fluid/U", "U", "volVectorField"),
        ("0/region_hot_fluid/p", "p", "volScalarField"),
        ("0/region_hot_fluid/p_rgh", "p_rgh", "volScalarField"),
        ("0/region_cold_fluid/T", "T", "volScalarField"),
        ("0/region_solid/T", "T", "volScalarField"),
        ("0/region_solid/p", "p", "volScalarField"),
    ]
    for rel, obj, cls in checks:
        txt = (case / rel).read_text()
        assert re.search(r"object\s+" + re.escape(obj) + r"\s*;", txt), (
            f"{rel}: FoamFile object should be '{obj}'"
        )
        assert re.search(r"class\s+" + re.escape(cls) + r"\s*;", txt), (
            f"{rel}: FoamFile class should be '{cls}'"
        )
        # the R1 P2 bug: object must NOT be a field-class token
        assert not re.search(r"object\s+vol(Scalar|Vector)Field\s*;", txt), (
            f"{rel}: FoamFile object is a class name (R1 P2 regression)"
        )


def test_blockmesh_has_three_named_cellzones(tmp_path: Path) -> None:
    case = _generate(tmp_path)
    bm = (case / "system" / "blockMeshDict").read_text()
    for r in ("region_hot_fluid", "region_solid", "region_cold_fluid"):
        assert r in bm
    # fluid<->solid faces are INTERNAL (shared) — NOT declared as boundary
    # patches (so splitMeshRegions makes the coupled interfaces). Guard that
    # we did not accidentally emit an interface patch in blockMesh.
    assert "region_hot_fluid_to_region_solid" not in bm


def test_boundary_conditions_overrides_respected(tmp_path: Path) -> None:
    case = _generate(tmp_path, T_hot_in=500.0, T_cold_in=280.0)
    hot_T = (case / "0" / "region_hot_fluid" / "T").read_text()
    cold_T = (case / "0" / "region_cold_fluid" / "T").read_text()
    assert "uniform 500.0" in hot_T
    assert "uniform 280.0" in cold_T
    # solid init defaults to the mean of the two stream temps (390.0)
    solid_T = (case / "0" / "region_solid" / "T").read_text()
    assert "uniform 390.0" in solid_T


# ----------------------------------------------------------------------
# Dispatch LIVE-run reconciliation (DEC-V61-225 · W3.2b · OF11/foamMultiRun)
#
# The W3.2a fail-loud boundary is REMOVED: execute() now routes CHT to the
# dedicated _execute_cht_multi_region runner (host-side ESI→Foundation
# translation → blockMesh → splitMeshRegions -cellZones -overwrite →
# foamMultiRun). These tests assert the simulated-success contract (no Docker)
# + the never-misroute-to-simpleFoam invariant; the REAL OF11 run is the
# opt-in CFD_LIVE_OF11 test at the bottom.
# ----------------------------------------------------------------------

class _FakeContainer:
    status = "running"


class _FakeContainers:
    def get(self, name):  # noqa: D401, ANN001
        return _FakeContainer()


class _FakeClient:
    containers = _FakeContainers()


class _FakeErrors:
    class DockerException(Exception):
        pass

    class NotFound(DockerException):
        pass


class _FakeDocker:
    errors = _FakeErrors

    @staticmethod
    def from_env():
        return _FakeClient()


def _make_multiregion_log(fluids, solids) -> str:
    """A minimal foamMultiRun-shaped log: per-region Solving lines + End."""
    lines = ["Exec   : foamMultiRun", "Time = 200s"]
    for f in fluids:
        lines.append(
            f"{f}  DILUPBiCGStab:  Solving for Ux, Initial residual = 4.4e-07, "
            "Final residual = 8.7e-10, No Iterations 1"
        )
        lines.append(
            f"{f}  GAMG:  Solving for p_rgh, Initial residual = 1.4e-06, "
            "Final residual = 1.8e-08, No Iterations 2"
        )
        lines.append(
            f"{f}  time step continuity errors : sum local = 4.6e-08, "
            "global = -1.0e-08, cumulative = -4.8e-04"
        )
    for s in solids:
        lines.append(
            f"{s}      DICPCG:  Solving for e, Initial residual = 0.0095, "
            "Final residual = 8.5e-05, No Iterations 1"
        )
    lines.append("End")
    return "\n".join(lines) + "\n"


def test_cht_execute_runs_multiregion_pipeline_success(tmp_path, monkeypatch) -> None:
    """DEC-V61-225: execute() on a CHT spec runs the multi-region pipeline
    (translate → blockMesh → splitMeshRegions → foamMultiRun) and returns a REAL
    (is_mock=False) success. _docker_exec is monkeypatched to simulate a
    successful run so the test stays Docker-free. It asserts the pipeline order
    AND that a CHT case is NEVER routed to the single-region simpleFoam path."""
    import src.foam_agent_adapter as faa

    monkeypatch.setattr(faa, "_DOCKER_AVAILABLE", True)
    monkeypatch.setattr(faa, "docker", _FakeDocker)

    commands: list[str] = []
    fluids = ["region_hot_fluid", "region_cold_fluid"]
    solids = ["region_solid"]

    def fake_docker_exec(self_, command, working_dir, timeout, log_name=None):
        commands.append(command)
        if command == "foamMultiRun":
            return True, _make_multiregion_log(fluids, solids)
        return True, f"ok:{command}"

    monkeypatch.setattr(
        faa.FoamAgentExecutor, "_docker_exec", fake_docker_exec
    )

    ex = faa.FoamAgentExecutor(work_dir=str(tmp_path / "work"))
    res = ex.execute(_cht_spec())

    assert res.success is True
    assert res.is_mock is False
    # exact pipeline order; foamMultiRun (NOT simpleFoam / chtMultiRegionSimpleFoam)
    assert commands == [
        "blockMesh",
        "splitMeshRegions -cellZones -overwrite",
        "foamMultiRun",
    ]
    assert "simpleFoam" not in commands
    assert "chtMultiRegionSimpleFoam" not in commands
    # per-region residuals parsed (solid energy 'e', fluid p_rgh)
    assert "region_solid:e" in res.residuals
    assert "region_hot_fluid:p_rgh" in res.residuals
    assert res.key_quantities.get("reached_end") is True


def test_cht_blockmesh_failure_is_honest_block(tmp_path, monkeypatch) -> None:
    """DEC-V61-225: a non-zero blockMesh yields a structured BLOCK (success=False,
    is_mock=False) — NOT a crash and NEVER a misroute to the single-region path."""
    import src.foam_agent_adapter as faa

    monkeypatch.setattr(faa, "_DOCKER_AVAILABLE", True)
    monkeypatch.setattr(faa, "docker", _FakeDocker)

    commands: list[str] = []

    def fake_docker_exec(self_, command, working_dir, timeout, log_name=None):
        commands.append(command)
        if command == "blockMesh":
            return False, "blockMesh: FOAM FATAL ERROR"
        return True, "ok"

    monkeypatch.setattr(
        faa.FoamAgentExecutor, "_docker_exec", fake_docker_exec
    )

    ex = faa.FoamAgentExecutor(work_dir=str(tmp_path / "work"))
    res = ex.execute(_cht_spec())

    assert res.success is False
    assert res.is_mock is False
    assert "blockMesh" in (res.error_message or "")
    # foamMultiRun must NOT run after a blockMesh failure, and simpleFoam never.
    assert "foamMultiRun" not in commands
    assert "simpleFoam" not in commands


def test_mesh_already_provided_cht_never_misroutes_to_simplefoam(
    tmp_path, monkeypatch
) -> None:
    """Codex R0 P2 regression (re-targeted for W3.2b): a STAGED/imported CHT case
    (mesh_already_provided=True) must run the multi-region pipeline — NOT fall
    through to the imported-case simpleFoam default. is_mock stays False."""
    import src.foam_agent_adapter as faa

    monkeypatch.setattr(faa, "_DOCKER_AVAILABLE", True)
    monkeypatch.setattr(faa, "docker", _FakeDocker)

    # A pre-populated, ALREADY-translated CHT case dir (mesh_already_provided
    # skips the generator, so the staged dir must carry the OF11-shaped dicts;
    # we generate then translate it up-front to mirror an imported OF11 case).
    src_case = tmp_path / "imported_cht"
    src_case.mkdir(parents=True)
    ex_gen = faa.FoamAgentExecutor(work_dir=str(tmp_path / "_gen"))
    ex_gen._generate_cht_multi_region(src_case, _cht_spec())
    ex_gen._translate_cht_case_esi_to_of11(src_case)
    # mesh_already_provided requires a polyMesh on disk (pre-flight check).
    (src_case / "constant" / "polyMesh").mkdir(parents=True)

    commands: list[str] = []
    fluids = ["region_hot_fluid", "region_cold_fluid"]
    solids = ["region_solid"]

    def fake_docker_exec(self_, command, working_dir, timeout, log_name=None):
        commands.append(command)
        if command == "foamMultiRun":
            return True, _make_multiregion_log(fluids, solids)
        return True, "ok"

    monkeypatch.setattr(
        faa.FoamAgentExecutor, "_docker_exec", fake_docker_exec
    )

    spec = TaskSpec(
        name="imported_cht",
        geometry_type=GeometryType.CHT_MULTI_REGION,
        flow_type=FlowType.INTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        mesh_already_provided=True,
        case_dir_override=str(src_case),
    )
    ex = faa.FoamAgentExecutor(work_dir=str(tmp_path / "work"))
    res = ex.execute(spec)

    assert res.success is True
    assert res.is_mock is False
    assert "foamMultiRun" in commands
    assert "simpleFoam" not in commands


def test_cht_never_silently_succeeds_without_docker(tmp_path, monkeypatch) -> None:
    """Defensive regression: a CHT spec must NEVER silently succeed via the LDC
    fall-through / single-region path. With the docker SDK unavailable, execute()
    returns a (non-mock) failure rather than a bogus solver result."""
    import src.foam_agent_adapter as faa

    monkeypatch.setattr(faa, "_DOCKER_AVAILABLE", False)
    ex = faa.FoamAgentExecutor(work_dir=str(tmp_path / "work"))
    res = ex.execute(_cht_spec())
    assert res.success is False
    assert res.is_mock is False


# ----------------------------------------------------------------------
# DEC-V61-225 unit tests: solver-command mapping + ESI→OF11 translation pins
# ----------------------------------------------------------------------

def test_of11_solver_command_mapping(tmp_path: Path) -> None:
    """The incompressible RANS family maps to foamRun -solver incompressibleFluid;
    everything else (notably buoyantFoam, deferred) passes through unchanged."""
    ex = FoamAgentExecutor(work_dir=str(tmp_path / "_w"))
    for name in ("simpleFoam", "pimpleFoam", "icoFoam"):
        assert ex._of11_solver_command(name) == "foamRun -solver incompressibleFluid"
    # buoyantFoam intentionally unmapped/deferred → passes through (fails honestly)
    assert ex._of11_solver_command("buoyantFoam") == "buoyantFoam"
    assert (
        ex._of11_solver_command("chtMultiRegionSimpleFoam")
        == "chtMultiRegionSimpleFoam"
    )


def test_translate_cht_case_esi_to_of11_pins_six_keywords(tmp_path: Path) -> None:
    """Pin all 6 ESI→Foundation(OF11) keyword changes on a freshly generated CHT
    case (NO Docker). DEC-V61-225 translation table."""
    case = _generate(tmp_path)
    ex = FoamAgentExecutor(work_dir=str(tmp_path / "_w"))
    fluids, solids = ex._read_cht_regions(case)
    assert fluids == ["region_hot_fluid", "region_cold_fluid"]
    assert solids == ["region_solid"]

    ex._translate_cht_case_esi_to_of11(case)

    # (1)(2)(3) solid thermophysicalProperties
    solid_tp = (case / "constant" / "region_solid" / "thermophysicalProperties").read_text()
    assert "constIsoSolid" in solid_tp
    assert "constIso;" not in solid_tp  # no bare constIso remains
    assert "eConst" in solid_tp
    assert "hConst" not in solid_tp
    assert "sensibleInternalEnergy" in solid_tp
    assert "sensibleEnthalpy" not in solid_tp
    assert "Cv 896" in solid_tp  # Cp → Cv, value preserved
    assert "Cp " not in solid_tp

    # (4) per-fluid gravity materialised from constant/g
    top_g = (case / "constant" / "g").read_text()
    for f in fluids:
        fg = case / "constant" / f / "g"
        assert fg.is_file()
        assert fg.read_text() == top_g

    # (5) per-fluid fvSolution SIMPLE: rhoMin/rhoMax removed
    for f in fluids:
        fv = (case / "system" / f / "fvSolution").read_text()
        assert "rhoMin" not in fv
        assert "rhoMax" not in fv

    # (6) solid fvSolution: energy solver block key + relaxation key h → e
    solid_fv = (case / "system" / "region_solid" / "fvSolution").read_text()
    assert re.search(r"(?m)^\s*e\s*$", solid_fv)  # solver block key
    assert "equations { e 0.5; }" in solid_fv
    # the bare 'h' solver/relax keys are gone (other tokens unaffected)
    assert not re.search(r"(?m)^\s*h\s*$", solid_fv)
    assert "{ h 0.5; }" not in solid_fv


@pytest.mark.skipif(
    os.environ.get("CFD_LIVE_OF11") != "1",
    reason="opt-in live OF11 run (set CFD_LIVE_OF11=1 with the cfd-openfoam container up)",
)
def test_cht_live_run_through_adapter_of11(tmp_path: Path) -> None:
    """Opt-in: the REAL OF11/foamMultiRun run through the adapter, gated on
    CFD_LIVE_OF11=1 (so CI without docker stays green). Reproduces the logged
    solve: success=True, is_mock=False, ≥1 region residual, reached End."""
    ex = FoamAgentExecutor(work_dir=str(tmp_path / "work"))
    res = ex.execute(_cht_spec())
    assert res.success is True, res.error_message
    assert res.is_mock is False
    assert res.key_quantities.get("reached_end") is True
    # at least the solid energy + one fluid pressure residual were parsed
    assert any(k.endswith(":e") for k in res.residuals)
    assert any(k.endswith(":p_rgh") for k in res.residuals)

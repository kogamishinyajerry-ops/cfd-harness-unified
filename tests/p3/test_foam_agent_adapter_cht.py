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
# Dispatch live-run boundary (W3.2a wires the route; LIVE run is W3.2b)
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


def test_cht_execute_hits_explicit_live_run_boundary(tmp_path, monkeypatch) -> None:
    """With a (faked) running container, execute() routes CHT to the generator
    then returns an EXPLICIT W3.2b live-run boundary failure — it never runs the
    single-region blockMesh->solver pipeline on a multi-region case. (The temp
    case dir generated en route is torn down by execute()'s finally-block; the
    generator's on-disk output is covered by the direct generator tests above.)
    """
    import src.foam_agent_adapter as faa

    monkeypatch.setattr(faa, "_DOCKER_AVAILABLE", True)
    monkeypatch.setattr(faa, "docker", _FakeDocker)

    ex = faa.FoamAgentExecutor(work_dir=str(tmp_path / "work"))
    res = ex.execute(_cht_spec())

    assert res.success is False
    assert res.is_mock is False
    msg = res.error_message or ""
    # explicit, labelled boundary — NOT the generic docker-unavailable failure
    assert "W3.2b" in msg
    assert "chtMultiRegionSimpleFoam" in msg
    assert "splitMeshRegions" in msg


def test_mesh_already_provided_cht_also_hits_boundary(tmp_path, monkeypatch) -> None:
    """Codex R0 P2 regression: a STAGED/imported CHT case
    (mesh_already_provided=True) must ALSO hit the W3.2b boundary — not fall
    through to the imported-case simpleFoam default (the single-region misroute
    the guard exists to prevent)."""
    import src.foam_agent_adapter as faa

    monkeypatch.setattr(faa, "_DOCKER_AVAILABLE", True)
    monkeypatch.setattr(faa, "docker", _FakeDocker)

    # minimal pre-populated case dir (the executor only checks polyMesh/ exists)
    src_case = tmp_path / "imported_cht"
    (src_case / "constant" / "polyMesh").mkdir(parents=True)

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

    assert res.success is False
    msg = res.error_message or ""
    assert "W3.2b" in msg
    # the boundary explicitly warns against the simpleFoam misroute
    assert "simpleFoam" in msg


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

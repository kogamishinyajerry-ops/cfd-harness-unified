"""Tests for `ui.backend.services.case_extractors.region_properties_reader`.

Per DEC-V61-217 W3.0. All fixtures are synthetic (``tmp_path``); no real
OpenFOAM case directories are required. Mirrors the DEC-V61-213 test
pattern from ``tests/test_thermo_dict_extractor.py``.

Structure:

  (B) **Edge-case units** — synthetic ``tmp_path`` fixtures that pin each
      extractor contract:

      - Happy path: case_002b-shaped 7-region fixture (1 fluid + 6 solid)
        and case_011-shaped 3-region fixture (2 fluid + 1 solid).
      - Missing-key (group absent → ``None``) — both axes.
      - Present-but-empty-payload (``fluid ()`` → ``()``) — the DEC-V61-213
        key-presence-vs-payload-completeness distinction.
      - Whitespace / multi-line / comment variants.
      - Stdlib-only architectural pin (subprocess trimesh-stub).
      - Duplicate-group refusal.
"""
from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ui.backend.services.case_extractors import extract_region_properties_snapshot
from ui.backend.services.case_extractors.region_properties_reader import (
    RegionPropertiesSnapshot,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------------
# Helper: write a ``constant/regionProperties`` file.
# ----------------------------------------------------------------------

def _write_region_properties(case_dir: Path, content: str) -> None:
    """Write *content* to ``<case_dir>/constant/regionProperties``."""
    (case_dir / "constant").mkdir(exist_ok=True)
    (case_dir / "constant" / "regionProperties").write_text(
        content, encoding="utf-8"
    )


def _make_region_props(fluid_names: str, solid_names: str) -> str:
    """Build a minimal canonical ``regionProperties`` file string."""
    return (
        "/*--------------------------------*- C++ -*----------------------------------*\\\n"
        "\\*---------------------------------------------------------------------------*/\n"
        "FoamFile\n"
        "{\n"
        "    version     2.0;\n"
        "    format      ascii;\n"
        "    class       dictionary;\n"
        '    location    "constant";\n'
        "    object      regionProperties;\n"
        "}\n"
        "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n"
        "\n"
        "regions\n"
        "(\n"
        f"    fluid       ({fluid_names})\n"
        f"    solid       ({solid_names})\n"
        ");\n"
        "\n"
        "// ************************************************************************* //\n"
    )


# ----------------------------------------------------------------------
# Happy-path fixtures
# ----------------------------------------------------------------------

def test_case_002b_shaped_fixture_yields_7_regions(tmp_path: Path) -> None:
    """case_002b shape: 1 fluid region + 6 Ti solid extrusions = 7 regions.

    Pin DEC-V61-217 W3.0 charter passes-criteria: fixture A yields correct
    fluid_regions / solid_regions tuples.
    """
    _write_region_properties(
        tmp_path,
        _make_region_props(
            fluid_names="region_bay_air",
            solid_names=(
                "Inner_Surf Outer_Surf Plane_Outer_Surf "
                "firewall_front_solid firewall_behind_solid Frame_solid"
            ),
        ),
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("region_bay_air",)
    assert snap.solid_regions == (
        "Inner_Surf",
        "Outer_Surf",
        "Plane_Outer_Surf",
        "firewall_front_solid",
        "firewall_behind_solid",
        "Frame_solid",
    )
    assert len(snap.fluid_regions) + len(snap.solid_regions) == 7


def test_case_011_shaped_fixture_yields_3_regions(tmp_path: Path) -> None:
    """case_011 shape: 2 fluid air streams + 1 Al-6061 solid = 3 regions.

    Pin DEC-V61-217 W3.0 charter passes-criteria: fixture B yields correct
    fluid_regions / solid_regions tuples.
    """
    _write_region_properties(
        tmp_path,
        _make_region_props(
            fluid_names="region_hot_fluid region_cold_fluid",
            solid_names="region_solid",
        ),
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("region_hot_fluid", "region_cold_fluid")
    assert snap.solid_regions == ("region_solid",)
    assert len(snap.fluid_regions) + len(snap.solid_regions) == 3


# ----------------------------------------------------------------------
# Missing-key (group absent → None) — charter's first mandated regression
# ----------------------------------------------------------------------

def test_missing_constant_dir_returns_none(tmp_path: Path) -> None:
    """No ``constant/`` dir at all → ``None``.

    Pin: file-open guard mirrors solver_block_extractor.py:184-192.
    """
    assert extract_region_properties_snapshot(tmp_path) is None


def test_missing_regionproperties_file_returns_none(tmp_path: Path) -> None:
    """``constant/`` exists but no ``regionProperties`` file → ``None``."""
    (tmp_path / "constant").mkdir()
    assert extract_region_properties_snapshot(tmp_path) is None


def test_nonexistent_case_dir_returns_none(tmp_path: Path) -> None:
    """A path that does not exist at all → ``None``, no exception.

    Pin: mirrors ``test_nonexistent_case_dir_returns_none`` in
    test_thermo_dict_extractor.py:255.
    """
    assert extract_region_properties_snapshot(tmp_path / "nonexistent") is None


def test_missing_regions_key_returns_none(tmp_path: Path) -> None:
    """File exists with FoamFile header but NO ``regions ( ... )`` block → ``None``.

    Pin DEC-V61-213 honest-omission contract: when the structurally-required
    ``regions`` key is absent, ``extract()`` returns ``None`` (not a
    ``Snapshot(None, None)``). Mirrors ``test_no_thermotype_block_returns_none``
    (thermo:260).
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; class dictionary; object regionProperties; }\n",
    )
    assert extract_region_properties_snapshot(tmp_path) is None


def test_missing_fluid_group_yields_none_fluid_present_solid(tmp_path: Path) -> None:
    """``regions`` present with only ``solid (...)`` group, no ``fluid`` key.

    DEC-V61-213 key-presence-vs-payload-completeness: fluid key absent →
    ``fluid_regions = None``; solid key present → ``solid_regions = (...)``.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    solid       (region_solid)\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions is None
    assert snap.solid_regions == ("region_solid",)


def test_missing_solid_group_yields_fluid_present_none_solid(tmp_path: Path) -> None:
    """``regions`` present with only ``fluid (...)`` group, no ``solid`` key.

    DEC-V61-213: solid key absent → ``solid_regions = None``.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid       (air)\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("air",)
    assert snap.solid_regions is None


def test_empty_regions_outer_yields_both_none(tmp_path: Path) -> None:
    """``regions ();`` — outer list present, no group keys at all.

    Returns a valid ``Snapshot(None, None)`` — not ``None``. The ``regions``
    key was parseable; neither group was declared. Distinct from "no
    ``regions`` key at all" (which returns ``None``).
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions ();\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions is None
    assert snap.solid_regions is None


# ----------------------------------------------------------------------
# Present-but-empty-payload — charter's second mandated regression
# DEC-V61-213 separation: group-present-empty ≠ group-absent
# ----------------------------------------------------------------------

def test_empty_fluid_payload_distinct_from_missing(tmp_path: Path) -> None:
    """``fluid ()`` present-but-empty → ``fluid_regions == ()`` (empty tuple, NOT None).

    Pin DEC-V61-213 key-presence-vs-payload-completeness (the "present-but-empty"
    leg): ``()`` signals "I have information, and it is empty" — ``None`` signals
    "no information at all". These are semantically different.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid   ()\n"
        "    solid   (region_solid)\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ()          # present-but-empty
    assert snap.fluid_regions is not None    # NOT the missing-key sentinel
    assert snap.solid_regions == ("region_solid",)


def test_empty_solid_payload_distinct_from_missing(tmp_path: Path) -> None:
    """``solid ()`` present-but-empty → ``solid_regions == ()`` (empty tuple, NOT None).

    Mirror of test above, solid axis. Real heatExchanger-shape files have
    ``solid ()`` when all thermal load is in the fluid regions.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid   (air porous)\n"
        "    solid   ()\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.solid_regions == ()
    assert snap.solid_regions is not None
    assert snap.fluid_regions == ("air", "porous")


def test_both_groups_empty_payload(tmp_path: Path) -> None:
    """``fluid () solid ()`` → both ``()`` — snapshot non-None (both groups present, both empty).

    Pin the independent-optionality property: the snapshot is valid even
    when both groups are declared but empty. ``Snapshot((), ())`` is a
    legitimate state.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid   ()\n"
        "    solid   ()\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ()
    assert snap.solid_regions == ()


# ----------------------------------------------------------------------
# Whitespace / multi-line / comment variants
# ----------------------------------------------------------------------

def test_multiline_region_list_parses(tmp_path: Path) -> None:
    """Region names spread across multiple lines inside ``( ... )`` → correct tuple.

    OpenFOAM whitespace is fully free; each name on its own indented line
    is legal and equivalent to the one-line form.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid\n"
        "    (\n"
        "        region_hot_fluid\n"
        "        region_cold_fluid\n"
        "    )\n"
        "    solid\n"
        "    (\n"
        "        metal\n"
        "    )\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("region_hot_fluid", "region_cold_fluid")
    assert snap.solid_regions == ("metal",)


def test_extra_whitespace_and_tabs_parse(tmp_path: Path) -> None:
    """Tabs + multiple spaces between ``fluid`` and ``(`` + between names.

    Whitespace freedom: ``fluid\t  (\tregion_a\t\tregion_b\t)`` must parse
    identically to ``fluid (region_a region_b)``.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid\t  (\tregion_a\t\tregion_b\t)\n"
        "    solid  ( metal )\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("region_a", "region_b")
    assert snap.solid_regions == ("metal",)


def test_line_commented_region_does_not_false_match(tmp_path: Path) -> None:
    """A ``// solid (ghost_region);`` comment must NOT inject ``ghost_region``.

    Pin ``_strip_comments`` correctness: the real ``solid (metal)`` group
    wins; the ``//``-commented fake group must be invisible after stripping.
    Mirrors ``test_commented_molweight_does_not_false_match`` (thermo:360).
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid   (air)\n"
        "    // solid (ghost_region);  // old experimental config\n"
        "    solid   (metal)\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.solid_regions == ("metal",)
    assert "ghost_region" not in (snap.solid_regions or ())


def test_block_commented_region_does_not_false_match(tmp_path: Path) -> None:
    """A ``/* ... fluid (fake); ... */`` block comment must be stripped before parse.

    Pin ``_strip_comments`` multi-line block stripping (mirrors
    ``test_block_commented_molweight_does_not_false_match``, thermo:394).
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "/*\n"
        "   Old config: fluid (fake_region);\n"
        "   Do not use.\n"
        "*/\n"
        "regions\n"
        "(\n"
        "    fluid   (air)\n"
        "    solid   (metal)\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("air",)
    assert "fake_region" not in (snap.fluid_regions or ())


def test_foamfile_oneline_header_survives(tmp_path: Path) -> None:
    """One-line ``FoamFile { ... object regionProperties; }`` headers must not
    confuse the paired-paren scan that locates ``regions ( ... )``.

    Pin DEC-V61-213 §Truth-chain R3 equivalent: the scanner correctly
    finds ``regions`` and NOT the inner FoamFile braces. Mirrors
    ``test_foamfile_oneline_header_survives`` (thermo:427).
    """
    _write_region_properties(
        tmp_path,
        'FoamFile { version 2.0; format ascii; class dictionary; location "constant"; object regionProperties; }\n'
        "regions\n"
        "(\n"
        "    fluid   (air_hot air_cold)\n"
        "    solid   (metal)\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("air_hot", "air_cold")
    assert snap.solid_regions == ("metal",)


def test_oneline_regions_entry_parses(tmp_path: Path) -> None:
    """One-line ``regions ( fluid (a) solid (b) );`` — must not fail.

    OpenFOAM whitespace-free grammar: the one-line form is legal and the
    parser must not require ``regions`` to be at column 0 on its own line.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions ( fluid (region_a) solid (region_b) );\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("region_a",)
    assert snap.solid_regions == ("region_b",)


def test_region_names_with_digits_and_underscores(tmp_path: Path) -> None:
    """Region names containing digits + underscores (project naming convention).

    Project profiles use names like ``region_hot_fluid``, ``Frame_solid``,
    ``Outer_Surf_solid`` — all must parse correctly.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid   (region_hot_fluid region_cold_fluid2)\n"
        "    solid   (Frame_solid Outer_Surf_solid APU_door3)\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("region_hot_fluid", "region_cold_fluid2")
    assert snap.solid_regions == ("Frame_solid", "Outer_Surf_solid", "APU_door3")


# ----------------------------------------------------------------------
# Stdlib-only / contract pins
# ----------------------------------------------------------------------

def test_extractor_module_loads_without_trimesh() -> None:
    """Mirror DEC-V61-211 R0 P1 fix: the extractor module imports cleanly
    when ``trimesh`` is absent (``.[ui]`` env without ``[workbench]``).

    Pin via subprocess so the test environment's trimesh availability
    does not mask a real regression — the subprocess stubs ``trimesh``
    to ``None`` in ``sys.modules``, then imports the extractor and checks
    ``RegionPropertiesSnapshot`` is reachable with the expected field set.
    Mirrors ``test_extractor_module_loads_without_trimesh`` in
    test_thermo_dict_extractor.py:805.
    """
    code = (
        "import sys\n"
        "sys.modules['trimesh'] = None\n"
        "from ui.backend.services.case_extractors import (\n"
        "    extract_region_properties_snapshot,\n"
        ")\n"
        "from ui.backend.services.case_extractors.region_properties_reader "
        "import RegionPropertiesSnapshot\n"
        "import dataclasses\n"
        "names = sorted(f.name for f in dataclasses.fields(RegionPropertiesSnapshot))\n"
        "assert names == ['fluid_regions', 'solid_regions'], names\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        timeout=30,
    )
    assert result.returncode == 0 and result.stdout.strip() == "OK", (
        f"extractor failed to import without trimesh.\n"
        f"  stdout: {result.stdout!r}\n"
        f"  stderr: {result.stderr!r}"
    )


def test_snapshot_is_frozen_dataclass_with_expected_fields() -> None:
    """``RegionPropertiesSnapshot`` is a frozen dataclass with exactly the two fields.

    Pin immutability contract (mirrors ``test_thermo_model_tags_is_frozen_dataclass``
    thermo:695) and field-name contract (mirrors the stdlib-only subprocess test).
    """
    snap = RegionPropertiesSnapshot(
        fluid_regions=("air",),
        solid_regions=("metal",),
    )
    assert dataclasses.is_dataclass(snap)
    field_names = sorted(f.name for f in dataclasses.fields(snap))
    assert field_names == ["fluid_regions", "solid_regions"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.fluid_regions = ("new",)  # type: ignore[misc]


def test_unreadable_file_returns_none(tmp_path: Path) -> None:
    """A directory at the expected file path → ``read_text`` raises
    ``IsADirectoryError`` (an ``OSError`` subclass) → ``None``.

    Mirrors ``test_unreadable_file_returns_none`` (thermo:865).
    """
    (tmp_path / "constant").mkdir()
    # Create a DIRECTORY where the file should be — read_text raises IsADirectoryError.
    (tmp_path / "constant" / "regionProperties").mkdir()
    assert extract_region_properties_snapshot(tmp_path) is None


# ----------------------------------------------------------------------
# Duplicate-group refusal (DEC-V61-213 invariant #4)
# ----------------------------------------------------------------------

def test_duplicate_fluid_group_returns_none(tmp_path: Path) -> None:
    """Two ``fluid (...)`` groups inside ``regions`` → ambiguous source → ``None``.

    Pin DEC-V61-213 honest-refusal discipline: silently picking the first
    match when the source is ambiguous would violate the truth-chain
    contract. Mirrors ``test_duplicate_thermotype_returns_none`` (thermo:477).
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid   (air)\n"
        "    fluid   (water)\n"
        "    solid   (metal)\n"
        ");\n",
    )
    assert extract_region_properties_snapshot(tmp_path) is None


def test_duplicate_regions_key_returns_none(tmp_path: Path) -> None:
    """Two top-level ``regions ( ... )`` entries → ambiguous source → ``None``.

    OpenFOAM itself errors on duplicate top-level keys; the extractor
    mirrors that spirit by refusing. Pin duplicate-key refusal via
    ``_locate_regions_body`` len-check.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { version 2.0; object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    fluid   (air)\n"
        "    solid   (metal)\n"
        ");\n"
        "regions\n"
        "(\n"
        "    fluid   (water)\n"
        ");\n",
    )
    assert extract_region_properties_snapshot(tmp_path) is None


# ----------------------------------------------------------------------
# RED-TEAM additions (LENS B pattern-fidelity audit, 2026-05-30).
# These pin behaviors the implementer's suite left unexercised:
#   1. A tight single-test contrast of missing-key vs empty-payload on the
#      SAME axis — hardens DEC-V61-213 separation against a future refactor
#      that collapses ``None`` and ``()`` into one path. (The implementer
#      pins these distinctly but across two separate tests.)
#   2. The double-paren OpenFOAM ``regions ( (fluid (..)) (solid (..)) )``
#      shape named verbatim in the module docstring (lines 4-5) and the
#      W3.0 charter spec, which NO existing fixture exercises (all use the
#      single-paren ``regions ( fluid (..) solid (..) )`` form).
#   3. The digit-prefixed-name silent-mangling behavior (``123air`` →
#      ``air``) — currently UNDOCUMENTED. Pins it as a known scope-out so a
#      future regression toward whole-token refusal is a deliberate, tested
#      change rather than a silent one. See suggested_fix in the red-team
#      report: add a docstring scope-out OR refuse on out-of-grammar tokens.
# ----------------------------------------------------------------------

def test_missing_vs_empty_same_axis_are_distinct(tmp_path: Path) -> None:
    """RED-TEAM: missing ``fluid`` key (→ ``None``) and ``fluid ()`` (→ ``()``)
    must be DISTINCT on the same axis — the DEC-V61-213 separation, pinned in
    a single contrast test.

    A refactor that conflated absent-group with empty-payload (returning
    ``None`` for both, or ``()`` for both) would still pass each leg's
    individual existing test only if BOTH were edited; this single test makes
    the *distinction itself* the assertion so a one-sided collapse cannot
    sneak through.
    """
    missing_dir = tmp_path / "missing"
    missing_dir.mkdir()
    _write_region_properties(
        missing_dir,
        "FoamFile { object regionProperties; }\n"
        "regions ( solid (metal) );\n",
    )
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    _write_region_properties(
        empty_dir,
        "FoamFile { object regionProperties; }\n"
        "regions ( fluid () solid (metal) );\n",
    )

    missing_snap = extract_region_properties_snapshot(missing_dir)
    empty_snap = extract_region_properties_snapshot(empty_dir)
    assert missing_snap is not None and empty_snap is not None

    # The contract: these two encodings are NOT equal.
    assert missing_snap.fluid_regions is None       # absent group
    assert empty_snap.fluid_regions == ()           # present-but-empty
    assert missing_snap.fluid_regions != empty_snap.fluid_regions, (
        "DEC-V61-213 separation collapsed: missing-key and empty-payload "
        "encoded identically on the fluid axis"
    )


def test_double_paren_openfoam_shape_parses(tmp_path: Path) -> None:
    """RED-TEAM: the double-paren ``regions ( (fluid (..)) (solid (..)) )`` form.

    The module docstring (lines 4-5) and the W3.0 charter spec both document
    the shape as ``regions ((fluid (r1 r2)) (solid (r3)));`` — yet every
    implementer fixture uses the single-paren ``regions ( fluid (..) solid
    (..) )`` form. This pins that the documented double-paren form actually
    yields the correct tuples (it currently does, via the paired-paren
    scanner's depth handling).
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { object regionProperties; }\n"
        "regions\n"
        "(\n"
        "    (fluid (region_bay_air))\n"
        "    (solid (Inner_Surf Outer_Surf))\n"
        ");\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("region_bay_air",)
    assert snap.solid_regions == ("Inner_Surf", "Outer_Surf")


def test_digit_prefixed_name_is_not_silently_corrupted(tmp_path: Path) -> None:
    """RED-TEAM P2 (fixed 2026-05-30): a digit-prefixed token (out-of-grammar
    for OpenFOAM ``word`` tokens) must NOT be silently rewritten into a
    *different valid-looking* region name.

    The original implementer parser used ``re.findall(r"[A-Za-z_]\\w*",
    sub_body)`` which SILENTLY truncated ``123air`` to ``air`` — fabricating
    a region name that was never declared. The fix replaces the regex harvest
    with a strict whole-token tokenizer (``_parse_names``): an out-of-grammar
    token makes the name-list unparseable, so the extractor REFUSES the whole
    snapshot (``None``) rather than fabricating ``air``. This is the
    truth-chain discipline of the sibling extractors — honest refusal, never
    silent corruption.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { object regionProperties; }\n"
        "regions ( fluid (123air clean_air) solid (metal) );\n",
    )
    # Post-fix contract: out-of-grammar token → honest refusal, NOT a
    # fabricated 'air'. The whole snapshot is None.
    assert extract_region_properties_snapshot(tmp_path) is None


# ----------------------------------------------------------------------
# RED-TEAM additions (LENS A parser-correctness audit, 2026-05-30).
# These pin the P1 depth-confusion fix: a group word nested inside another
# group's name-list must NEVER false-match and fabricate a region list.
# Each test FAILED on the original global-regex implementation (which
# returned actively WRONG tuples) and PASSES on the top-level-anchored
# parser (which returns an honest None).
# ----------------------------------------------------------------------

def test_nested_fluid_inside_solid_does_not_fabricate(tmp_path: Path) -> None:
    """RED-TEAM P1: ``regions ( solid ( metal fluid (deep) ) )`` has NO
    top-level ``fluid`` group — the ``fluid (deep)`` lives inside the
    ``solid`` group's name-list.

    The original parser's global ``\\bfluid\\s*\\(`` scan false-matched it and
    returned ``fluid_regions=('deep',)`` + ``solid_regions=('metal','fluid',
    'deep')`` — both fabricated. The fixed parser sees a nested group inside
    the ``solid`` name-list, which is out-of-grammar for a name-list, so it
    REFUSES the whole snapshot.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { object regionProperties; }\n"
        "regions ( solid ( metal fluid (deep) ) );\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    # Must NOT fabricate a fluid group from the nested token.
    assert snap is None


def test_region_name_with_paren_suffix_does_not_conjure_group(tmp_path: Path) -> None:
    """RED-TEAM P1: ``fluid (air solid(metal))`` — ``solid(metal)`` is a
    fluid region name written with no space, NOT a real ``solid`` group.

    The original parser conjured ``solid_regions=('metal',)`` from it. The
    fixed parser sees a nested group inside the ``fluid`` name-list and
    refuses (``None``).
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { object regionProperties; }\n"
        "regions ( fluid (air solid(metal)) );\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is None


def test_three_level_nested_name_list_refuses(tmp_path: Path) -> None:
    """RED-TEAM P1: a third nesting level ``fluid ( (subA subB) )`` is beyond
    the two-level ``(groupWord (name ...))`` schema.

    The original parser silently flattened it to ``('subA','subB')``. The
    fixed parser refuses (``None``) — nested groups are not valid inside a
    name-list.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { object regionProperties; }\n"
        "regions ( fluid ( (subA subB) ) solid (metal) );\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is None


# ----------------------------------------------------------------------
# CODEX R0 additions (governance review, 2026-05-30).
#   P2: trailing tokens after the regions(...) list → honest refusal.
#   P3: a `regions (` inside a quoted metadata string must NOT trigger the
#       duplicate-key refusal on an otherwise valid file.
# ----------------------------------------------------------------------

def test_trailing_tokens_after_regions_list_refuses(tmp_path: Path) -> None:
    """CODEX R0 P2: ``regions ( fluid (air) ) solid (metal);`` — a misplaced
    paren leaves ``solid (metal)`` stranded AFTER the first balanced
    ``regions (...)`` close.

    The pre-fix parser silently truncated the suffix and returned a partial
    snapshot (``fluid=('air',), solid=None``) — making a broken multi-region
    topology look like a valid single-fluid case. The fixed parser refuses
    (``None``): non-trivial tokens after the list close are a malformation.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { object regionProperties; }\n"
        "regions ( fluid (air) ) solid (metal);\n",
    )
    assert extract_region_properties_snapshot(tmp_path) is None


def test_quoted_regions_in_metadata_does_not_false_duplicate(tmp_path: Path) -> None:
    """CODEX R0 P3: a ``regions (`` substring inside a quoted metadata value
    must NOT be counted as a second ``regions`` entry.

    The pre-fix token scan saw two ``regions (`` occurrences (one inside the
    quoted ``note`` string, one real) and rejected the file via the
    duplicate-key path. The fixed scan ignores ``regions (`` inside quoted
    strings, so this otherwise-valid file parses correctly.
    """
    _write_region_properties(
        tmp_path,
        'FoamFile { version 2.0; note "generated from regions (fluid solid) '
        'template"; object regionProperties; }\n'
        "regions ( fluid (air_hot) solid (metal) );\n",
    )
    snap = extract_region_properties_snapshot(tmp_path)
    assert snap is not None
    assert snap.fluid_regions == ("air_hot",)
    assert snap.solid_regions == ("metal",)


# ----------------------------------------------------------------------
# CODEX R1 addition (governance review round 1, 2026-05-30).
#   P2: a stray ``;`` INSIDE the regions list is malformed (a statement
#       terminator only belongs after the list close) → honest refusal.
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "regions_entry",
    [
        "regions ( fluid; (air) solid (metal) );",  # stray ; after a group word
        "regions (;);",                             # lone ; as the whole body
        "regions ( fluid (air); solid (metal) );",  # ; between groups
    ],
)
def test_stray_semicolon_in_regions_body_refuses(
    tmp_path: Path, regions_entry: str
) -> None:
    """CODEX R1 P2: a ``;`` inside the ``regions ( ... )`` body is malformed.

    The pre-fix tokenizer skipped ``;`` as whitespace and still returned a
    seemingly-valid snapshot, hiding a corrupted topology from the later P3
    readers. The fixed tokenizer treats an in-body ``;`` as out-of-grammar
    and refuses (``None``). A legitimate trailing ``;`` (after the list
    close) is still accepted — see ``test_oneline_regions_entry_parses``.
    """
    _write_region_properties(
        tmp_path,
        "FoamFile { object regionProperties; }\n" + regions_entry + "\n",
    )
    assert extract_region_properties_snapshot(tmp_path) is None

"""Tests for ``ui.backend.services.case_extractors.step_extractor``.

Per DEC-V61-214. Two layers (mirror DEC-V61-211 / -212 / -213 pattern):

  (A) **Cross-case drift-parity canary** — parametrize over all 27
      ``*_dicts/`` profiles under ``.planning/case_profiles/``, assert
      ``extract(profile).step_path == _autodiscover_step(profile)``
      (both ``None`` today; lights up if either silently drifts).

  (B) **Edge-case units** — root-vs-cad priority, sort determinism on
      case-insensitive filesystems, no-recursion-into-vendored,
      bbox/extents per-field honest omission, manifest fallback,
      duplicate-key R1 carry-forward, stdlib-only import, live
      assemble_stack dispatch discrimination.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ui.backend.services.case_extractors import extract_step_path_snapshot
from ui.backend.services.case_extractors.step_extractor import StepArtifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = REPO_ROOT / ".planning" / "case_profiles"


# ---- (A) drift-parity canary ----------------------------------------


def _list_case_profiles() -> list[Path]:
    """Return every ``*_dicts`` profile dir under case_profiles/.

    Used for the cross-case drift-parity canary. Today (verified
    2026-05-30) ZERO profiles ship STEP / bbox.json / manifest.json /
    cad/, so every entry produces ``step_path=None`` and the canary
    asserts agreement with ``_autodiscover_step``.
    """
    if not PROFILES_DIR.is_dir():
        return []
    return sorted(p for p in PROFILES_DIR.iterdir() if p.is_dir() and p.name.endswith("_dicts"))


@pytest.mark.parametrize(
    "profile",
    [p.name for p in _list_case_profiles()],
)
def test_drift_parity_canary_against_autodiscover_step(profile: str) -> None:
    """Cross-case canary: extractor.step_path matches HTTP path's _autodiscover_step.

    Lifts ``_autodiscover_step`` from ``ai_review.py`` under
    ``importorskip('trimesh')`` (the FastAPI route module transitively
    pulls ``trimesh`` via ``geometry_ingest``). All 27 profiles produce
    ``None`` today; the canary lights up the instant either
    implementation silently drifts — direct V20-reclassification analog.
    """
    pytest.importorskip("trimesh")
    from ui.backend.routes.ai_review import _autodiscover_step

    case_dir = PROFILES_DIR / profile
    if not case_dir.is_dir():
        pytest.skip(f"profile dir missing: {profile}")

    extractor_step = extract_step_path_snapshot(case_dir)
    http_step = _autodiscover_step(case_dir)

    extracted_path = (
        extractor_step.step_path if extractor_step is not None else None
    )
    # Compare equality — both arms agree today (None on every profile).
    # Note: extractor returns absolute resolved str; HTTP path returns
    # whatever str(p) yields. Normalize both via resolve() for the
    # canary check to tolerate symlinks / relative-input differences.
    if extracted_path is None or http_step is None:
        assert extracted_path == http_step, (
            f"{profile}: drift between extractor (step_path={extracted_path!r}) "
            f"and _autodiscover_step ({http_step!r}) — at least one moved"
        )
    else:
        assert (
            Path(extracted_path).resolve() == Path(http_step).resolve()
        ), (
            f"{profile}: drift — extractor {extracted_path!r} vs "
            f"_autodiscover_step {http_step!r}"
        )


def test_all_case_profiles_return_none_today() -> None:
    """Pin DEC-V61-214 §Case-differentiation: today every profile → None.

    The 27 in-repo ``*_dicts/`` profiles ship ZERO STEP / bbox.json /
    manifest.json / cad/ artifacts (verified 2026-05-30). This is the
    honest "discrimination = 1 output" baseline DEC-V61-214 commits to.
    The instant a future case sediments a STEP into its profile, this
    test breaks — that's the intended signal that the eval discrimination
    set grew.
    """
    profiles = _list_case_profiles()
    if not profiles:
        pytest.skip("no _dicts profiles found")
    non_none = []
    for p in profiles:
        result = extract_step_path_snapshot(p)
        if result is not None:
            non_none.append((p.name, result))
    assert not non_none, (
        "case_profiles unexpectedly produced StepArtifacts — a profile "
        "gained CAD artifacts: "
        f"{[(name, art.step_path) for name, art in non_none]}. "
        "Update DEC-V61-214 §Case-differentiation table and grow the "
        "eval discrimination set."
    )


# ---- (B) STEP path discovery edge cases -----------------------------


def test_no_step_no_bbox_returns_None(tmp_path: Path) -> None:
    """Empty tmp_path → None (no STEP, no cad/, no manifest)."""
    assert extract_step_path_snapshot(tmp_path) is None


def test_nonexistent_case_dir_returns_none(tmp_path: Path) -> None:
    """A path that doesn't exist at all → None (no exception)."""
    assert extract_step_path_snapshot(tmp_path / "nonexistent") is None


def test_step_root_wins_over_cad_subdir(tmp_path: Path) -> None:
    """When both ``<case>/foo.step`` AND ``<case>/cad/bar.step`` exist,
    the root-level file wins.

    Pin DRAFT §v0.1 In line 49: "root first, then <case_dir>/cad/".
    """
    root_step = tmp_path / "foo.step"
    root_step.write_text("ISO-10303-21;\nHEADER;\n", encoding="utf-8")
    (tmp_path / "cad").mkdir()
    cad_step = tmp_path / "cad" / "bar.step"
    cad_step.write_text("ISO-10303-21;\nHEADER;\n", encoding="utf-8")

    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(root_step.resolve())


def test_cad_subdir_when_root_empty(tmp_path: Path) -> None:
    """Only ``<case>/cad/foo.step`` exists → that path wins."""
    (tmp_path / "cad").mkdir()
    cad_step = tmp_path / "cad" / "foo.step"
    cad_step.write_text("ISO-10303-21;\nHEADER;\n", encoding="utf-8")

    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(cad_step.resolve())


def test_uppercase_suffix_recognized(tmp_path: Path) -> None:
    """``MODEL.STEP`` (uppercase) is recognized — all 4 globs honored."""
    upper = tmp_path / "MODEL.STEP"
    upper.write_text("ISO-10303-21;\n", encoding="utf-8")

    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(upper.resolve())


def test_stp_suffix_recognized(tmp_path: Path) -> None:
    """``model.stp`` (alternate suffix) is recognized."""
    stp = tmp_path / "model.stp"
    stp.write_text("ISO-10303-21;\n", encoding="utf-8")

    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(stp.resolve())


def test_sort_determinism_case_insensitive_filesystem(tmp_path: Path) -> None:
    """Per-suffix sorted() iteration cannot double-yield on case-insensitive FS.

    DRAFT §Codex review line 128-131 pre-empt. On HFS+/APFS default, a
    naive concatenated glob over (``*.step``, ``*.STEP``) could match
    the same physical file twice; the per-suffix iteration in
    ``_discover_step_path`` yields independent buckets and first-hit
    wins per outer (root vs cad).

    We can't create both ``a.step`` and ``A.STEP`` on case-insensitive
    APFS (would collide as one inode), so we instead pin determinism
    by creating two files with the same suffix differing only in case
    of the BASENAME — sorted() must yield a deterministic first.
    """
    (tmp_path / "b.step").write_text("", encoding="utf-8")
    (tmp_path / "a.step").write_text("", encoding="utf-8")

    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    # sorted() is lexicographic — 'a' < 'b'
    assert result.step_path.endswith("a.step"), (
        f"sorted() drift on case-insensitive FS: got {result.step_path!r}"
    )


def test_no_recursion_into_vendored_dirs(tmp_path: Path) -> None:
    """STEPs buried in ``<case>/.venv/share/doc/gmsh/tutorials/`` must NOT be found.

    Pin DRAFT §Truth-chain risks line 148-151. The ONLY in-repo STEPs
    are gmsh tutorials in ``.venv/share/doc/gmsh/``; if the extractor
    silently recursed, it would leak tutorial STEPs into eval
    discovery. This is the canary.
    """
    nested = tmp_path / ".venv" / "share" / "doc" / "gmsh" / "tutorials"
    nested.mkdir(parents=True)
    (nested / "t20_data.step").write_text("ISO-10303-21;\n", encoding="utf-8")

    # Also bury one in node_modules for good measure.
    nm = tmp_path / "node_modules" / "some-pkg"
    nm.mkdir(parents=True)
    (nm / "model.step").write_text("ISO-10303-21;\n", encoding="utf-8")

    # And one in a random nested subdir.
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "deep.step").write_text("ISO-10303-21;\n", encoding="utf-8")

    result = extract_step_path_snapshot(tmp_path)
    assert result is None, (
        f"extractor recursed into vendored/nested dir: {result!r}"
    )


def test_absolute_path_returned_for_json_safety(tmp_path: Path) -> None:
    """step_path is str AND absolute (DRAFT §v0.1 In line 50)."""
    (tmp_path / "model.step").write_text("", encoding="utf-8")
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert isinstance(result.step_path, str)
    assert Path(result.step_path).is_absolute()


# ---- (B) bbox / extents edge cases ----------------------------------


def _write_step(tmp_path: Path, name: str = "model.step") -> Path:
    """Helper: write a minimal placeholder STEP file."""
    p = tmp_path / name
    p.write_text("ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n", encoding="utf-8")
    return p


def test_bbox_well_formed_yields_max_extent(tmp_path: Path) -> None:
    """cad/bbox.json with valid 6-tuple bbox → max(dx,dy,dz) computed.

    Pin lift parity with ``ai_review.py:_bbox_max_extent``.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 10, 5, 2]}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw == pytest.approx(10.0)
    assert result.body_extents_raw is None  # extents key absent


def test_bbox_key_absent_returns_none_extent(tmp_path: Path) -> None:
    """bbox.json with ONLY ``extents`` (no ``bbox`` key) → bbox_max_extent_raw=None.

    Pairs with ``test_bbox_key_present_malformed_returns_none_extent_per_R1``
    — both yield None but for traceably different reasons.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"extents": [3.0]}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None  # absent — honest
    assert result.body_extents_raw == [3.0]


def test_bbox_key_present_malformed_returns_none_extent_per_R1(tmp_path: Path) -> None:
    """DEC-V61-213 R1 carry-forward: bbox key present but arity ≠ 6 → None.

    The key is structurally present in the JSON but unparseable as the
    expected 6-tuple shape. Must refuse the field deliberately — NOT
    collapse with "key absent" silently. The TEST captures the
    intent; the runtime collapses honestly. Pairs with
    ``test_bbox_key_absent_returns_none_extent``.

    step_path is preserved (per-field, not whole-snapshot refusal —
    DRAFT §Truth-chain R2).
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0]}),  # arity 3, not 6
        encoding="utf-8",
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None  # malformed — honest refuse
    assert result.body_extents_raw is None


def test_bbox_non_numeric_per_field_none(tmp_path: Path) -> None:
    """bbox tuple with non-numeric element → bbox_max_extent_raw=None."""
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0, "oops", 5, 2]}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None


def test_bbox_non_list_per_field_none(tmp_path: Path) -> None:
    """bbox key whose value is a non-list (string) → bbox_max_extent_raw=None."""
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": "not a list"}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None


def test_extents_malformed_per_field_none(tmp_path: Path) -> None:
    """extents key with non-coercible element → body_extents_raw=None.

    bbox / step_path are independently preserved.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 1, 1, 1], "extents": [1, 2, "oops"]}),
        encoding="utf-8",
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw == pytest.approx(1.0)
    assert result.body_extents_raw is None


def test_extents_non_list_per_field_none(tmp_path: Path) -> None:
    """extents key whose value is a non-list (dict) → body_extents_raw=None."""
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"extents": {"unexpected": "shape"}}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.body_extents_raw is None


def test_nan_in_bbox_collapses_to_none(tmp_path: Path) -> None:
    """DEC-V61-214 R1 adversarial guard: NaN in bbox → bbox_max_extent_raw=None.

    Rationale: Python's ``json.loads`` is permissive by default and
    accepts JS-style ``NaN`` literals (decoded as ``float('nan')``).
    ``max(nan, ...)`` returns ``nan``, which is a contagious silent-
    failure value: downstream
    ``unit_detector.detect_unit(bbox_max_extent_raw=nan, ...)`` would
    silently mis-bucket because every numeric-threshold comparison
    against nan is False. The honest-omission contract requires
    non-finite floats in numeric-required JSON fields to collapse to
    ``None`` rather than pass through. Pinned per the workflow's
    adversarial finding.

    step_path is preserved (per-field, not whole-snapshot, omission).
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    # Hand-craft JSON with bare NaN literal (json.loads accepts this by
    # default — it's the silent-passthrough path we want to block).
    (tmp_path / "cad" / "bbox.json").write_text(
        '{"bbox": [0, 0, 0, NaN, 1, 1]}', encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None


def test_inf_in_bbox_collapses_to_none(tmp_path: Path) -> None:
    """Parity with NaN guard: +Infinity in bbox → bbox_max_extent_raw=None.

    ``json.loads`` also accepts JS-style ``Infinity`` / ``-Infinity``
    literals. ``max(inf, ...)`` returns ``inf``, which would propagate
    just as silently into ``unit_detector`` thresholds (every finite
    threshold compares False against inf, mis-bucketing the case).
    Same honest-omission contract per R1 carry-forward.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        '{"bbox": [0, 0, 0, Infinity, 1, 1]}', encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None


def test_neg_inf_in_bbox_collapses_to_none(tmp_path: Path) -> None:
    """Parity with NaN/+Inf: -Infinity in bbox → bbox_max_extent_raw=None."""
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        '{"bbox": [-Infinity, 0, 0, 1, 1, 1]}', encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None


def test_nan_in_extents_collapses_to_none(tmp_path: Path) -> None:
    """Parity guard for extents: NaN in extents → body_extents_raw=None.

    Same R1 adversarial finding applied to the ``extents`` field. A
    list containing ``nan`` would propagate into the downstream
    ``unit_detector`` body-class filter (unit_detector.py:191-200)
    where threshold comparisons against nan silently fail. Honest
    omission of the whole extents field is the cleanest contract;
    bbox / step_path are independently preserved.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        '{"bbox": [0, 0, 0, 1, 1, 1], "extents": [1.0, NaN, 3.0]}',
        encoding="utf-8",
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    # bbox is finite + well-formed, so it survives.
    assert result.bbox_max_extent_raw == pytest.approx(1.0)
    # extents carries nan → whole field collapses to None.
    assert result.body_extents_raw is None


def test_inf_in_extents_collapses_to_none(tmp_path: Path) -> None:
    """Parity with NaN in extents: +Infinity → body_extents_raw=None."""
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        '{"extents": [Infinity, 2.0]}', encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.body_extents_raw is None


def test_manifest_fallback_when_cad_bbox_absent(tmp_path: Path) -> None:
    """manifest.json supplies bbox/extents when cad/bbox.json absent.

    Pin lift parity with ``ai_review.py:_autodiscover_geometry_metadata``
    fallback chain (cad/bbox.json → manifest.json).
    """
    step = _write_step(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 3, 3, 3], "extents": [3]}),
        encoding="utf-8",
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw == pytest.approx(3.0)
    assert result.body_extents_raw == [3.0]


def test_manifest_does_not_override_cad_bbox(tmp_path: Path) -> None:
    """When both cad/bbox.json and manifest.json carry ``bbox``, cad wins.

    DRAFT §Codex review line 132-133 pre-empt: precedence must NOT
    invert. cad/bbox.json values come first; manifest.json is fallback
    only.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 1, 1, 1]}), encoding="utf-8"
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 99, 99, 99]}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    # cad/bbox.json wins → 1.0, not 99.0
    assert result.bbox_max_extent_raw == pytest.approx(1.0)


def test_manifest_only_supplies_field_absent_from_cad_bbox(tmp_path: Path) -> None:
    """Per-field fallback: cad/bbox.json has bbox; manifest has extents.

    Result: bbox from cad/bbox.json; extents from manifest.json.
    """
    _ = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 1, 2, 4]}), encoding="utf-8"
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"extents": [7.0]}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.bbox_max_extent_raw == pytest.approx(4.0)
    assert result.body_extents_raw == [7.0]


def test_malformed_json_per_field_none(tmp_path: Path) -> None:
    """cad/bbox.json with invalid JSON → bbox/extents both None.

    step_path is preserved if STEP present.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        "{not valid json", encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None
    assert result.body_extents_raw is None


def test_bbox_json_non_dict_top_level_per_field_none(tmp_path: Path) -> None:
    """cad/bbox.json whose top-level is a list (not dict) → bbox/extents None."""
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps([1, 2, 3]), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None
    assert result.body_extents_raw is None


# ---- (B) collapse-to-None contract ----------------------------------


def test_no_step_but_bbox_collapses_to_None(tmp_path: Path) -> None:
    """bbox.json populated but no STEP file → extract() returns None.

    Design-phase decision PINNED: bbox/extents without step_path are
    useless because assemble_stack gates ``unit_detector`` dispatch on
    ``step_path is not None``. The cleanest contract is to collapse
    the whole result to None rather than emit a StepArtifacts with
    populated bbox but absent step_path.

    Prevents accidental partial-StepArtifacts emission.
    """
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 10, 10, 10], "extents": [10]}),
        encoding="utf-8",
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 5, 5, 5]}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is None


# ---- (B) corrupt-vs-absent integration pin --------------------------


def test_corrupt_bbox_value_is_not_silently_swallowed_into_key_absent(tmp_path: Path) -> None:
    """DEC-213 R1 carry-forward integration test.

    bbox.json with malformed ``bbox`` key emits the SAME
    ``bbox_max_extent_raw=None`` as bbox.json with key absent — BUT
    each path is hit by a SEPARATE test (the previous two tests) so
    silent drift between the two arms (e.g., a future refactor making
    one raise but the other silently return) is caught. This test
    pins them in the same fixture for a direct compare.
    """
    # Case A: key absent (only extents).
    case_a = tmp_path / "absent"
    case_a.mkdir()
    _write_step(case_a)
    (case_a / "cad").mkdir()
    (case_a / "cad" / "bbox.json").write_text(
        json.dumps({"extents": [3.0]}), encoding="utf-8"
    )
    result_a = extract_step_path_snapshot(case_a)
    assert result_a is not None
    assert result_a.bbox_max_extent_raw is None

    # Case B: key present but malformed (arity 3).
    case_b = tmp_path / "malformed"
    case_b.mkdir()
    _write_step(case_b)
    (case_b / "cad").mkdir()
    (case_b / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0]}), encoding="utf-8"
    )
    result_b = extract_step_path_snapshot(case_b)
    assert result_b is not None
    assert result_b.bbox_max_extent_raw is None

    # Both arms yield None for bbox_max_extent_raw — that's the
    # honest collapse. The DISTINGUISHED state is captured by the
    # extents field: case_a preserves [3.0]; case_b is None.
    assert result_a.body_extents_raw == [3.0]
    assert result_b.body_extents_raw is None


# ---- (B) public contract / dataclass shape --------------------------


def test_return_type_is_step_artifacts_dataclass(tmp_path: Path) -> None:
    """When non-None, return is StepArtifacts instance — defensive
    against future field-add silently leaking into eval layer.
    """
    _write_step(tmp_path)
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert isinstance(result, StepArtifacts)
    import dataclasses
    assert dataclasses.is_dataclass(result)
    names = sorted(f.name for f in dataclasses.fields(StepArtifacts))
    assert names == ["bbox_max_extent_raw", "body_extents_raw", "step_path"]


def test_step_artifacts_is_frozen(tmp_path: Path) -> None:
    """StepArtifacts is frozen — immutability pin (mirror DEC-V61-211 / -213)."""
    import dataclasses

    artifacts = StepArtifacts(step_path="/tmp/x.step")
    with pytest.raises(dataclasses.FrozenInstanceError):
        artifacts.step_path = "/tmp/y.step"  # type: ignore[misc]


# ---- (B) stdlib-only architectural promise --------------------------


def test_extractor_module_loads_without_trimesh() -> None:
    """Mirror DEC-V61-211 R0 P1 fix: the extractor module imports cleanly
    when trimesh is absent (``.[ui]`` env without ``[workbench]``).

    Pin via subprocess so the test environment's trimesh availability
    doesn't mask a real regression — the subprocess stubs ``trimesh``
    to None in ``sys.modules``, then imports the extractor and checks
    ``StepArtifacts`` is reachable with the expected field set.
    """
    import os
    import subprocess
    import sys

    code = (
        "import sys\n"
        "sys.modules['trimesh'] = None\n"
        "from ui.backend.services.case_extractors import (\n"
        "    extract_step_path_snapshot,\n"
        ")\n"
        "from ui.backend.services.case_extractors.step_extractor "
        "import StepArtifacts\n"
        "import dataclasses\n"
        "names = sorted(f.name for f in dataclasses.fields(StepArtifacts))\n"
        "assert names == [\n"
        "    'bbox_max_extent_raw', 'body_extents_raw', 'step_path',\n"
        "], names\n"
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


# ---- (B) live assemble_stack dispatch discrimination ----------------


def test_assemble_stack_dispatches_unit_detector_when_step_path_present(
    tmp_path: Path,
) -> None:
    """DEC-V61-214 acceptance — live case-discrimination proof.

    Positive: tmp_path with STEP + bbox.json → extract returns
    StepArtifacts → assemble_stack with step_path=... dispatches
    ``unit_detector``.

    Negative twin: empty tmp_path → extract returns None →
    assemble_stack with step_path=None → ``unit_detector`` NOT in
    dispatched set.

    Skip if trimesh missing (advisor's transitive import chain).
    """
    pytest.importorskip("trimesh")
    from ui.backend.services.advisor_stack import assemble_stack

    # Positive case — STEP file + bbox.
    pos_case = tmp_path / "pos"
    pos_case.mkdir()
    _write_step(pos_case)
    (pos_case / "cad").mkdir()
    (pos_case / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 1, 1, 1], "extents": [1.0]}),
        encoding="utf-8",
    )
    pos_result = extract_step_path_snapshot(pos_case)
    assert pos_result is not None
    report_pos = assemble_stack(
        step_path=pos_result.step_path,
        step_bbox_max_extent_raw=pos_result.bbox_max_extent_raw,
        step_body_extents_raw=pos_result.body_extents_raw,
    )
    pos_dispatched = {c.advisor_name for c in report_pos.advisor_calls}
    assert "unit_detector" in pos_dispatched, (
        f"positive case: unit_detector not in dispatched set = "
        f"{sorted(pos_dispatched)}"
    )

    # Negative twin — empty case dir.
    neg_case = tmp_path / "neg"
    neg_case.mkdir()
    neg_result = extract_step_path_snapshot(neg_case)
    assert neg_result is None
    report_neg = assemble_stack(step_path=None)
    neg_dispatched = {c.advisor_name for c in report_neg.advisor_calls}
    assert "unit_detector" not in neg_dispatched, (
        f"negative case: unit_detector unexpectedly dispatched = "
        f"{sorted(neg_dispatched)}"
    )


# ---- (B) misc robustness --------------------------------------------


def test_unreadable_cad_bbox_returns_per_field_none(tmp_path: Path) -> None:
    """OSError on bbox.json read → per-field None (mirror sibling pattern).

    Simulate via a DIRECTORY at the file path — read_text raises
    IsADirectoryError (a subclass of OSError) which is caught.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").mkdir()  # directory at file path
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None
    assert result.body_extents_raw is None


def test_empty_extents_list_yields_empty_list(tmp_path: Path) -> None:
    """Empty extents list is valid (advisor handles empty list fine)."""
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"extents": []}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.body_extents_raw == []


def test_cad_dir_with_only_bbox_no_step_in_cad(tmp_path: Path) -> None:
    """STEP at root + bbox.json in cad/ — both resolve cleanly."""
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 2, 2, 2], "extents": [2]}),
        encoding="utf-8",
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw == pytest.approx(2.0)
    assert result.body_extents_raw == [2.0]


def test_cad_subdir_step_with_root_bbox(tmp_path: Path) -> None:
    """STEP only in cad/, bbox.json at root cad/ — still resolves."""
    (tmp_path / "cad").mkdir()
    cad_step = tmp_path / "cad" / "model.step"
    cad_step.write_text("", encoding="utf-8")
    (tmp_path / "cad" / "bbox.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 5, 5, 5]}), encoding="utf-8"
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(cad_step.resolve())
    assert result.bbox_max_extent_raw == pytest.approx(5.0)


def test_step_suffix_precedence_within_root(tmp_path: Path) -> None:
    """Within a single dir, ``.step`` (first suffix in _STEP_SUFFIX_PATTERNS)
    is tried before ``.stp`` / ``.STEP`` / ``.STP``.

    Pin the suffix order — if a single dir has both ``a.step`` and
    ``b.stp``, ``a.step`` should win (first suffix bucket).
    """
    (tmp_path / "b.stp").write_text("", encoding="utf-8")
    (tmp_path / "a.step").write_text("", encoding="utf-8")

    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path.endswith("a.step"), (
        f"suffix order drift: expected a.step, got {result.step_path!r}"
    )


# ---- (B) Codex CRS R0 R1 fixes --------------------------------------
# P2 finding: when cad/bbox.json has a key that is structurally PRESENT
# but the value is malformed (collapses to None via the per-field
# coercer), the manifest.json fallback MUST NOT overwrite that None
# with a stale manifest value. Conflating "key absent" with "key
# present but malformed" would let stale manifest data silently mask
# a real bug in a freshly written cad/bbox.json. Two distinct tests
# pin the bbox arm and the extents arm so silent drift between the
# two is caught (DEC-V61-213 R1 two-test pattern carry-forward).
# P3 finding: _load_json_dict's read_text(encoding="utf-8") raises
# UnicodeDecodeError on non-UTF-8 bytes; that MUST collapse to silent
# omission per the contract.


def test_bbox_key_present_but_malformed_does_not_fallback_to_manifest_per_R1(
    tmp_path: Path,
) -> None:
    """Codex CRS R0 P2 R1 pin (bbox arm).

    cad/bbox.json has a structurally-present ``bbox`` key but the value
    is malformed (wrong arity). manifest.json carries a valid bbox.
    Outcome: bbox_max_extent_raw stays ``None`` (cad/bbox.json "wins"
    by virtue of key-presence, even when its value is honest-None) and
    does NOT silently inherit the stale manifest value (99.0).
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        # Arity != 6 → _compute_bbox_max_extent returns None
        json.dumps({"bbox": [0, 0, 0, 1]}),
        encoding="utf-8",
    )
    (tmp_path / "manifest.json").write_text(
        # Valid bbox, but must NOT shadow the present-but-malformed
        # cad/bbox.json bbox.
        json.dumps({"bbox": [0, 0, 0, 99, 99, 99]}),
        encoding="utf-8",
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None, (
        "Manifest stale-data leak: present-but-malformed cad/bbox.json "
        f"bbox was overridden by manifest value {result.bbox_max_extent_raw!r}; "
        "expected honest None (Codex CRS R0 P2)"
    )


def test_extents_key_present_but_malformed_does_not_fallback_to_manifest_per_R1(
    tmp_path: Path,
) -> None:
    """Codex CRS R0 P2 R1 pin (extents arm).

    cad/bbox.json has a structurally-present ``extents`` key but the
    value is malformed (non-list). manifest.json carries valid extents.
    Outcome: body_extents_raw stays ``None`` and does NOT inherit the
    stale manifest value [99.0, 99.0, 99.0]. Parity with the bbox arm
    above so silent drift between the two arms is caught.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        # Non-list → _coerce_extents returns None
        json.dumps({"extents": "not-a-list"}),
        encoding="utf-8",
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"extents": [99.0, 99.0, 99.0]}),
        encoding="utf-8",
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.body_extents_raw is None, (
        "Manifest stale-data leak: present-but-malformed cad/bbox.json "
        f"extents was overridden by manifest value {result.body_extents_raw!r}; "
        "expected honest None (Codex CRS R0 P2)"
    )


def test_bbox_key_absent_does_fallback_to_manifest_per_R1(tmp_path: Path) -> None:
    """Codex CRS R0 P2 R1 pin (key-absent arm — fallback DOES fire).

    Parity with the present-but-malformed test above: when the cad/
    bbox.json key is genuinely ABSENT (cad/bbox.json present but
    without the ``bbox`` key), the manifest.json fallback DOES supply
    the value. This pins the "key-absent vs key-present-malformed"
    distinction so the two arms cannot silently collapse together.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    (tmp_path / "cad" / "bbox.json").write_text(
        # bbox key absent; only extents present
        json.dumps({"extents": [1.0, 2.0, 3.0]}),
        encoding="utf-8",
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 42, 42, 42]}),
        encoding="utf-8",
    )
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    # bbox key absent in cad/bbox.json → manifest fallback supplies 42.0
    assert result.bbox_max_extent_raw == pytest.approx(42.0)
    # extents present in cad/bbox.json → cad wins
    assert result.body_extents_raw == [1.0, 2.0, 3.0]


def test_non_utf8_cad_bbox_json_returns_none_silently_per_R1(tmp_path: Path) -> None:
    """Codex CRS R0 P3 R1 pin.

    cad/bbox.json contains non-UTF-8 bytes — read_text(encoding='utf-8')
    raises UnicodeDecodeError, which MUST be caught and collapsed to
    silent omission, NOT propagated out of extract(). manifest.json
    fallback still supplies the bbox.
    """
    step = _write_step(tmp_path)
    (tmp_path / "cad").mkdir()
    # Latin-1 byte 0xff is invalid in UTF-8 sequence headers
    (tmp_path / "cad" / "bbox.json").write_bytes(b'{"bbox": [\xff]}')
    (tmp_path / "manifest.json").write_text(
        json.dumps({"bbox": [0, 0, 0, 7, 7, 7]}),
        encoding="utf-8",
    )
    # MUST NOT RAISE — silent omission per the contract
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    # cad/bbox.json unreadable → key-absent semantics → manifest fallback
    # legitimately supplies the value. This is correct: unreadable file
    # IS structurally absent (no dict could be loaded).
    assert result.bbox_max_extent_raw == pytest.approx(7.0)


def test_non_utf8_manifest_returns_none_silently_per_R1(tmp_path: Path) -> None:
    """Codex CRS R0 P3 R1 pin (manifest arm).

    manifest.json contains non-UTF-8 bytes — UnicodeDecodeError MUST be
    caught and collapsed to silent omission. No cad/bbox.json present,
    so both bbox and extents collapse to None per the honest contract.
    """
    step = _write_step(tmp_path)
    (tmp_path / "manifest.json").write_bytes(b'{"bbox": [\xff]}')
    # MUST NOT RAISE
    result = extract_step_path_snapshot(tmp_path)
    assert result is not None
    assert result.step_path == str(step.resolve())
    assert result.bbox_max_extent_raw is None
    assert result.body_extents_raw is None

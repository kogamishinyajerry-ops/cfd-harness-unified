"""Tests for ``geometry_ingest.stl_face_label_validator`` (D11).

Coverage (mirrors D6 ``test_extra_body_advisor`` + D10
``test_bc_type_name_validity_advisor`` patterns · ≥ 8 tests):

  1. ``test_orphan_face_label_in_manifest_warns`` — V94 classic path (a)
  2. ``test_duplicate_face_label_in_stl_warns`` — path (b) detection
     fires when a face label is declared by ≥2 parts (the duplicate is
     latent in the manifest and would manifest in the emitted STL)
  3. ``test_missing_reference_from_shm_to_manifest_warns`` — path (c)
  4. ``test_consistent_face_labels_silent`` — happy path is clean
  5. ``test_empty_inputs_silent`` — all-None / all-empty stays clean
  6. ``test_4q_gate_no_llm_imports`` — V130 Q1
  7. ``test_4q_gate_no_case_dir_writes`` — V132 Q4
  8. ``test_evidence_v_rows_references_canonical_V94`` — TrustGate
     surface — every D11 finding must cite V94
  9. ``test_orphan_only_fires_when_stl_inventory_provided`` — V130
     silent-skip guard when stl_face_normals is absent
 10. ``test_shm_patches_top_level_reference_also_detected`` — alternative
     shm idiom (patches[] block, not refinementSurfaces.regions)
 11. ``test_case_011_v94_regression`` — full V94 ground-truth replay
"""
from __future__ import annotations

import inspect
import sys

import pytest

from ui.backend.services.geometry_ingest import stl_face_label_validator as mod
from ui.backend.services.geometry_ingest.stl_face_label_validator import (
    FaceLabelFinding,
    FaceLabelReport,
    validate_face_label_consistency,
)


# ---- 1. orphan_declared_label warns -------------------------------------


def test_orphan_face_label_in_manifest_warns() -> None:
    """Manifest claims face labels not present as STL solid keys → V94 path (a)."""
    parts_manifest = {
        "parts": [
            {
                "name": "region_hot_fluid",
                "role": "region_fluid",
                "face_labels": ["hot_inlet", "hot_outlet", "hot_walls"],
            }
        ]
    }
    # The V94 canonical sighting: cq.exporters emitted ONLY the parent
    # body label, no sub-face labels.
    stl_face_normals = {
        "region_hot_fluid": [(0.0, 1.0, 0.0)],
    }
    report = validate_face_label_consistency(
        stl_face_normals=stl_face_normals,
        parts_manifest=parts_manifest,
        shm_dict=None,
    )
    assert isinstance(report, FaceLabelReport)
    assert not report.is_clean
    assert report.warning_count == 3   # all three declared labels are orphan
    assert report.critical_count == 0
    codes = {f.code for f in report.findings}
    assert codes == {"orphan_declared_label"}
    orphan_labels = {f.face_label for f in report.findings}
    assert orphan_labels == {"hot_inlet", "hot_outlet", "hot_walls"}
    for f in report.findings:
        assert f.severity == "warning"
        assert "V94" in f.evidence_v_rows
        assert f.suggested_fix is not None
        assert "cq.Assembly" in f.suggested_fix or "createPatch" in f.suggested_fix


# ---- 2. duplicate_face_label_in_manifest warns --------------------------


def test_duplicate_face_label_in_stl_warns() -> None:
    """Same face label declared by ≥2 parts → V94 path (b).

    The advisor detects the duplicate at the manifest layer where it is
    recoverable; the conflict would otherwise propagate into the emitted
    STL ("STL face_label 重复 — 配 BC 不知选哪个" per V63-A brief).
    """
    parts_manifest = {
        "parts": [
            {
                "name": "region_hot_fluid",
                "face_labels": ["inlet", "outlet"],
            },
            {
                "name": "region_cold_fluid",
                # 'inlet' collides with region_hot_fluid's 'inlet'
                "face_labels": ["inlet", "cold_outlet"],
            },
        ]
    }
    stl_face_normals = {
        "region_hot_fluid": [(0.0, 1.0, 0.0)],
        "region_cold_fluid": [(0.0, -1.0, 0.0)],
        "inlet": [(1.0, 0.0, 0.0)],   # present in STL, but duplicate-declared
        "outlet": [(-1.0, 0.0, 0.0)],
        "cold_outlet": [(-1.0, 0.0, 0.0)],
    }
    report = validate_face_label_consistency(
        stl_face_normals=stl_face_normals,
        parts_manifest=parts_manifest,
        shm_dict=None,
    )
    dup = [f for f in report.findings if f.code == "duplicate_face_label_in_manifest"]
    assert len(dup) == 1
    finding = dup[0]
    assert finding.face_label == "inlet"
    assert finding.severity == "warning"
    assert "V94" in finding.evidence_v_rows
    assert "region_hot_fluid" in finding.detail
    assert "region_cold_fluid" in finding.detail
    assert finding.suggested_fix is not None
    # No orphan findings (every declared label IS in STL inventory)
    assert all(f.code != "orphan_declared_label" for f in report.findings)


# ---- 3. shm_reference_undeclared_in_manifest warns ----------------------


def test_missing_reference_from_shm_to_manifest_warns() -> None:
    """shm_dict references face label NOT in any parts_manifest.face_labels → V94 path (c)."""
    parts_manifest = {
        "parts": [
            {
                "name": "region_hot_fluid",
                "face_labels": ["hot_inlet", "hot_outlet"],
            }
        ]
    }
    shm_dict = {
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "region_hot_fluid": {
                    "level": [2, 2],
                    "regions": {
                        "hot_inlet": {"level": [3, 3]},
                        "phantom_patch": {"level": [3, 3]},   # ← undeclared
                    },
                }
            }
        }
    }
    # STL inventory contains every declared label so orphan(a) does not fire.
    stl_face_normals = {
        "region_hot_fluid": [(0.0, 1.0, 0.0)],
        "hot_inlet": [(1.0, 0.0, 0.0)],
        "hot_outlet": [(-1.0, 0.0, 0.0)],
    }
    report = validate_face_label_consistency(
        stl_face_normals=stl_face_normals,
        parts_manifest=parts_manifest,
        shm_dict=shm_dict,
    )
    miss = [
        f for f in report.findings
        if f.code == "shm_reference_undeclared_in_manifest"
    ]
    assert len(miss) == 1
    f = miss[0]
    assert f.face_label == "phantom_patch"
    assert f.severity == "warning"
    assert "V94" in f.evidence_v_rows
    assert "refinementSurfaces.region_hot_fluid.regions.phantom_patch" in f.location


# ---- 4. clean case stays clean ------------------------------------------


def test_consistent_face_labels_silent() -> None:
    """Everything declared in manifest, present in STL, referenced consistently in shm → clean."""
    parts_manifest = {
        "parts": [
            {
                "name": "region_hot_fluid",
                "face_labels": ["hot_inlet", "hot_outlet"],
            }
        ]
    }
    stl_face_normals = {
        "region_hot_fluid": [(0.0, 1.0, 0.0)],
        "hot_inlet": [(1.0, 0.0, 0.0)],
        "hot_outlet": [(-1.0, 0.0, 0.0)],
    }
    shm_dict = {
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "region_hot_fluid": {
                    "level": [2, 2],
                    "regions": {
                        "hot_inlet": {"level": [3, 3]},
                        "hot_outlet": {"level": [3, 3]},
                    },
                }
            }
        }
    }
    report = validate_face_label_consistency(
        stl_face_normals=stl_face_normals,
        parts_manifest=parts_manifest,
        shm_dict=shm_dict,
    )
    assert report.is_clean
    assert report.findings == ()
    assert set(report.declared_labels) == {"hot_inlet", "hot_outlet"}
    assert "hot_inlet" in report.stl_labels
    assert "hot_inlet" in report.shm_referenced_labels


# ---- 5. empty / missing inputs degrade silently -------------------------


def test_empty_inputs_silent() -> None:
    """All-None and all-empty inputs both produce empty findings without raising."""
    r_none = validate_face_label_consistency(
        stl_face_normals=None, parts_manifest=None, shm_dict=None
    )
    assert isinstance(r_none, FaceLabelReport)
    assert r_none.is_clean
    assert r_none.declared_labels == ()
    assert r_none.stl_labels == ()
    assert r_none.shm_referenced_labels == ()

    r_empty = validate_face_label_consistency(
        stl_face_normals={},
        parts_manifest={"parts": []},
        shm_dict={"castellatedMeshControls": {}},
    )
    assert r_empty.is_clean
    assert r_empty.findings == ()

    # Malformed shapes: non-dict parts entry, non-list face_labels, etc.
    # — all silently skipped per V130.
    r_malformed = validate_face_label_consistency(
        stl_face_normals={"valid_key": [(0.0, 0.0, 1.0)], 42: ["bad_key"]},  # type: ignore[dict-item]
        parts_manifest={
            "parts": [
                "string entry",   # not a dict
                {"name": 5, "face_labels": ["x"]},   # name not str
                {"name": "ok", "face_labels": "not a list"},   # face_labels not list
                {"name": "good", "face_labels": ["", "  ", "real"]},   # empties stripped
            ]
        },
        shm_dict={"castellatedMeshControls": {"refinementSurfaces": "not a dict"}},
    )
    # Only 'real' is declared (orphan vs 'valid_key' → fires)
    assert "real" in r_malformed.declared_labels
    assert len(r_malformed.declared_labels) == 1


# ---- 6. 4Q gate · no LLM imports ----------------------------------------


def test_4q_gate_no_llm_imports() -> None:
    """V130 advisor-not-driver — Q1: LLM offline OK.

    Scan the advisor module's source for any LLM provider SDK import.
    A future maintainer who adds ``import openai`` by mistake trips this
    immediately.
    """
    src = inspect.getsource(mod)
    for forbidden in (
        "import openai",
        "import anthropic",
        "import google.generativeai",
        "from openai",
        "from anthropic",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
    ):
        assert forbidden not in src, f"D11 advisor contains forbidden token: {forbidden}"


# ---- 7. 4Q gate · no filesystem writes ----------------------------------


def test_4q_gate_no_case_dir_writes(tmp_path, monkeypatch) -> None:
    """V132 advisory-only — Q4: AI advisory only.

    Stub builtins.open to detect any write-mode call. D11 should perform
    exactly zero filesystem writes regardless of input shape.
    """
    write_attempts: list[str] = []
    real_open = open

    def watcher(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            write_attempts.append(f"open({file!r}, {mode!r})")
        return real_open(file, mode, *args, **kwargs)

    import builtins
    monkeypatch.setattr(builtins, "open", watcher)

    # Exercise all three detection paths.
    validate_face_label_consistency(
        stl_face_normals={"region_hot_fluid": [(0.0, 1.0, 0.0)]},
        parts_manifest={
            "parts": [
                {"name": "region_hot_fluid", "face_labels": ["hot_inlet"]},
                {"name": "region_cold_fluid", "face_labels": ["hot_inlet", "cold_outlet"]},
            ]
        },
        shm_dict={
            "castellatedMeshControls": {
                "refinementSurfaces": {
                    "region_hot_fluid": {
                        "regions": {"phantom": {"level": [3, 3]}}
                    }
                }
            }
        },
    )
    assert write_attempts == [], f"D11 attempted writes: {write_attempts}"


# ---- 8. TrustGate · every finding cites canonical V94 -------------------


def test_evidence_v_rows_references_canonical_V94() -> None:
    """Every D11 finding must carry V94 in evidence_v_rows for drift_guard.

    V94 is the canonical face-label-loss class in
    ``docs/openfoam_corpus/industrial_solver_findings_v_series.md``.
    drift_guard at the route boundary (DEC-V62-A-sub-M-DRIFT-V2) rejects
    findings whose evidence_v_rows reference a V-row absent from the
    runtime corpus, so V94 must appear in every D11 finding.
    """
    parts_manifest = {
        "parts": [
            {"name": "region_hot_fluid", "face_labels": ["hot_inlet", "hot_outlet"]},
            {"name": "region_cold_fluid", "face_labels": ["hot_inlet"]},   # dup
        ]
    }
    shm_dict = {
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "region_hot_fluid": {
                    "regions": {"hot_inlet": {}, "ghost": {}}   # 'ghost' undeclared
                }
            }
        }
    }
    stl_face_normals: dict[str, list[tuple[float, float, float]]] = {
        # 'hot_outlet' missing from STL → orphan fires for that one
        "region_hot_fluid": [(0.0, 1.0, 0.0)],
        "region_cold_fluid": [(0.0, -1.0, 0.0)],
        "hot_inlet": [(1.0, 0.0, 0.0)],
    }
    report = validate_face_label_consistency(
        stl_face_normals=stl_face_normals,
        parts_manifest=parts_manifest,
        shm_dict=shm_dict,
    )
    assert len(report.findings) >= 3   # one per detection path
    codes = {f.code for f in report.findings}
    assert codes == {
        "orphan_declared_label",
        "duplicate_face_label_in_manifest",
        "shm_reference_undeclared_in_manifest",
    }
    for f in report.findings:
        assert f.advisor_name == "stl_face_label_validator"
        assert "V94" in f.evidence_v_rows, f"finding missing V94: {f}"


# ---- 9. V130 silent-skip when stl inventory absent ----------------------


def test_orphan_only_fires_when_stl_inventory_provided() -> None:
    """V130 silent-skip: orphan detection requires the STL inventory to
    contrast against; if ``stl_face_normals`` is None, the orphan path
    cannot fire (we cannot prove a label is missing from an inventory
    we never saw). Duplicate (b) + shm-reference (c) still fire.
    """
    parts_manifest = {
        "parts": [
            {"name": "region_hot_fluid", "face_labels": ["hot_inlet", "hot_outlet"]},
            {"name": "region_cold_fluid", "face_labels": ["hot_inlet"]},   # dup with above
        ]
    }
    shm_dict = {
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "region_hot_fluid": {
                    "regions": {"ghost_patch": {}}   # undeclared
                }
            }
        }
    }
    report = validate_face_label_consistency(
        stl_face_normals=None,
        parts_manifest=parts_manifest,
        shm_dict=shm_dict,
    )
    codes = {f.code for f in report.findings}
    assert "orphan_declared_label" not in codes
    assert "duplicate_face_label_in_manifest" in codes
    assert "shm_reference_undeclared_in_manifest" in codes


# ---- 10. shm_dict patches[] top-level idiom -----------------------------


def test_shm_patches_top_level_reference_also_detected() -> None:
    """Alternative shm idiom — ``castellatedMeshControls.patches[].name`` —
    is also walked for the (c) detection.
    """
    parts_manifest = {
        "parts": [
            {"name": "region_hot_fluid", "face_labels": ["hot_inlet"]},
        ]
    }
    shm_dict = {
        "castellatedMeshControls": {
            "patches": [
                {"name": "hot_inlet", "patchInfo": {"type": "patch"}},
                {"name": "rogue_top_level_patch", "patchInfo": {"type": "patch"}},
            ]
        }
    }
    report = validate_face_label_consistency(
        stl_face_normals=None,
        parts_manifest=parts_manifest,
        shm_dict=shm_dict,
    )
    miss = [
        f for f in report.findings
        if f.code == "shm_reference_undeclared_in_manifest"
    ]
    assert len(miss) == 1
    assert miss[0].face_label == "rogue_top_level_patch"
    assert "patches[1].name" in miss[0].location


# ---- 11. case_011 V94 ground-truth replay --------------------------------


def test_case_011_v94_regression() -> None:
    """V94 canonical ground truth — cq.exporters single-shell STL loses
    every named face label declared in the case profile (case_011 v1
    sediment, surfaced 2026-05-14 by v3 sub-session).

    Manifest claims 6 face labels across hot + cold fluid regions;
    STL inventory only carries the two parent-body labels. All 6 face
    labels must orphan-fire. The third-region (solid) entry has no
    face_labels declaration → contributes no findings.
    """
    parts_manifest = {
        "parts": [
            {
                "name": "region_hot_fluid",
                "role": "region_fluid",
                "face_labels": ["hot_inlet", "hot_outlet", "hot_walls"],
            },
            {
                "name": "region_cold_fluid",
                "role": "region_fluid",
                "face_labels": ["cold_inlet", "cold_outlet", "cold_walls"],
            },
            # Solid region with no face_labels (the boundary of the conduction
            # box — V94 doesn't fire here because the engineer authored no
            # face-label expectations).
            {
                "name": "region_solid",
                "role": "solid",
            },
        ]
    }
    # cq.exporters single-watertight-shell behaviour: only the parent
    # region body labels appear in the emitted STL.
    stl_face_normals = {
        "region_hot_fluid": [(0.0, 1.0, 0.0)],
        "region_cold_fluid": [(0.0, -1.0, 0.0)],
        "region_solid": [(0.0, 0.0, 1.0)],
    }
    report = validate_face_label_consistency(
        stl_face_normals=stl_face_normals,
        parts_manifest=parts_manifest,
        shm_dict=None,
    )
    orphans = [f for f in report.findings if f.code == "orphan_declared_label"]
    assert len(orphans) == 6
    orphan_labels = {f.face_label for f in orphans}
    assert orphan_labels == {
        "hot_inlet", "hot_outlet", "hot_walls",
        "cold_inlet", "cold_outlet", "cold_walls",
    }
    # Each orphan finding cites V94
    for f in orphans:
        assert "V94" in f.evidence_v_rows
        assert f.suggested_fix is not None
    # No duplicate, no shm-orphan in this baseline replay
    assert all(f.code == "orphan_declared_label" for f in report.findings)

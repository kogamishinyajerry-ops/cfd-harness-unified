"""Unit tests for the pre-meshing thin-wall advisor.

Pillar 2 falsification: V10 (sHM ate Frame patches) repeated across
case_002a + case_002b CHT. Advisor warns BEFORE meshing instead of
the engineer discovering missing patches mid-debug.
"""
from __future__ import annotations

import math

import pytest

from ui.backend.services.geometry_ingest.thin_wall_advisor import (
    PatchGeometry,
    ThinWallWarning,
    detect_thin_wall_patches_at_risk,
)


# Reproducing case_002a / case_002b refinement scheme:
# background_cell_size = 0.08 m; level [1, 2] → level_max=2 →
# effective cell = 0.08 / 4 = 0.02 m = 20 mm.
# A 50 mm beam (Frame_1, beam_3) has thickness 0.05 m → 2.5 cells
# per thickness — borderline (sHM merges in practice when the
# thinnest dimension is < ~3× the cell size).

_BG = 0.08  # m, matches APU bay
_FRAME = PatchGeometry(name="Frame_1", bbox_dimensions=(2.0, 0.5, 0.05))  # 50 mm thick


def test_apu_bay_v10_pattern_emits_warning_at_default_threshold():
    warnings = detect_thin_wall_patches_at_risk(
        patches=[_FRAME],
        refinement_levels={"Frame_1": (1, 2)},
        background_cell_size=_BG,
    )
    assert len(warnings) == 1
    w = warnings[0]
    assert w.patch_name == "Frame_1"
    assert w.estimated_thickness == pytest.approx(0.05)
    assert w.effective_cell_size == pytest.approx(0.02)
    assert w.cells_per_thickness == pytest.approx(2.5)
    assert w.assigned_level == (1, 2)
    assert w.severity == "info"
    assert "AT RISK" in w.message or "marginal" in w.message
    assert "level " in w.message


def test_5mm_thin_wall_at_level_2_is_critical():
    skin = PatchGeometry(name="Inner_Surf", bbox_dimensions=(2.0, 1.0, 0.005))
    warnings = detect_thin_wall_patches_at_risk(
        patches=[skin],
        refinement_levels={"Inner_Surf": (1, 2)},
        background_cell_size=_BG,
    )
    assert len(warnings) == 1
    w = warnings[0]
    assert w.severity == "critical"
    assert w.cells_per_thickness < 1.0
    assert "WILL be merged" in w.message
    assert w.recommended_level_max >= 5


def test_recommended_level_makes_cells_per_thickness_meet_target():
    skin = PatchGeometry(name="Inner_Surf", bbox_dimensions=(2.0, 1.0, 0.005))
    warnings = detect_thin_wall_patches_at_risk(
        patches=[skin],
        refinement_levels={"Inner_Surf": (1, 2)},
        background_cell_size=_BG,
        min_cells_per_thickness=2,
    )
    w = warnings[0]
    recomputed_cell = _BG / (2 ** w.recommended_level_max)
    recomputed_cells_per_thickness = 0.005 / recomputed_cell
    assert recomputed_cells_per_thickness >= 2.0


def test_thick_solid_body_does_not_warn():
    body = PatchGeometry(name="body_2", bbox_dimensions=(0.4, 0.3, 0.25))
    warnings = detect_thin_wall_patches_at_risk(
        patches=[body],
        refinement_levels={"body_2": (1, 2)},
        background_cell_size=_BG,
    )
    assert warnings == []


def test_patch_without_refinement_assignment_is_skipped_silently():
    warnings = detect_thin_wall_patches_at_risk(
        patches=[_FRAME],
        refinement_levels={},
        background_cell_size=_BG,
    )
    assert warnings == []


def test_warnings_sorted_by_cells_per_thickness_ascending():
    skin_5mm = PatchGeometry(name="skin", bbox_dimensions=(2.0, 1.0, 0.005))
    frame_50mm = PatchGeometry(name="frame", bbox_dimensions=(2.0, 0.5, 0.05))
    plate_20mm = PatchGeometry(name="plate", bbox_dimensions=(1.0, 1.0, 0.02))
    warnings = detect_thin_wall_patches_at_risk(
        patches=[frame_50mm, skin_5mm, plate_20mm],
        refinement_levels={"skin": (1, 2), "frame": (1, 2), "plate": (1, 2)},
        background_cell_size=_BG,
        min_cells_per_thickness=3,
    )
    assert [w.patch_name for w in warnings] == ["skin", "plate", "frame"]
    assert warnings[0].cells_per_thickness < warnings[1].cells_per_thickness
    assert warnings[1].cells_per_thickness < warnings[2].cells_per_thickness


def test_min_cells_per_thickness_3_escalates_severity():
    plate = PatchGeometry(name="plate", bbox_dimensions=(1.0, 1.0, 0.05))
    [w_two] = detect_thin_wall_patches_at_risk(
        patches=[plate],
        refinement_levels={"plate": (1, 2)},
        background_cell_size=_BG,
        min_cells_per_thickness=2,
    )
    [w_three] = detect_thin_wall_patches_at_risk(
        patches=[plate],
        refinement_levels={"plate": (1, 2)},
        background_cell_size=_BG,
        min_cells_per_thickness=3,
    )
    assert w_two.severity == "info"
    assert w_three.severity == "warning"
    assert w_three.recommended_level_max >= w_two.recommended_level_max


def test_thick_plate_above_info_threshold_emits_no_warning():
    plate = PatchGeometry(name="thick_plate", bbox_dimensions=(1.0, 1.0, 0.10))
    warnings = detect_thin_wall_patches_at_risk(
        patches=[plate],
        refinement_levels={"thick_plate": (1, 2)},
        background_cell_size=_BG,
        min_cells_per_thickness=2,
    )
    assert warnings == []


def test_negative_or_zero_thickness_skipped():
    bad = PatchGeometry(name="bad", bbox_dimensions=(1.0, 1.0, 0.0))
    warnings = detect_thin_wall_patches_at_risk(
        patches=[bad],
        refinement_levels={"bad": (1, 2)},
        background_cell_size=_BG,
    )
    assert warnings == []


def test_negative_level_max_skipped():
    p = PatchGeometry(name="x", bbox_dimensions=(0.1, 0.1, 0.005))
    warnings = detect_thin_wall_patches_at_risk(
        patches=[p],
        refinement_levels={"x": (-1, -1)},
        background_cell_size=_BG,
    )
    assert warnings == []


def test_invalid_background_cell_size_raises():
    with pytest.raises(ValueError, match="background_cell_size"):
        detect_thin_wall_patches_at_risk(
            patches=[_FRAME],
            refinement_levels={"Frame_1": (1, 2)},
            background_cell_size=0.0,
        )
    with pytest.raises(ValueError, match="background_cell_size"):
        detect_thin_wall_patches_at_risk(
            patches=[_FRAME],
            refinement_levels={"Frame_1": (1, 2)},
            background_cell_size=-1.0,
        )
    with pytest.raises(ValueError, match="background_cell_size"):
        detect_thin_wall_patches_at_risk(
            patches=[_FRAME],
            refinement_levels={"Frame_1": (1, 2)},
            background_cell_size=math.inf,
        )


def test_invalid_min_cells_per_thickness_raises():
    with pytest.raises(ValueError, match="min_cells_per_thickness"):
        detect_thin_wall_patches_at_risk(
            patches=[_FRAME],
            refinement_levels={"Frame_1": (1, 2)},
            background_cell_size=_BG,
            min_cells_per_thickness=0,
        )


def test_thinwallwarning_is_immutable_dataclass():
    p = PatchGeometry(name="x", bbox_dimensions=(1.0, 1.0, 0.005))
    [w] = detect_thin_wall_patches_at_risk(
        patches=[p],
        refinement_levels={"x": (1, 2)},
        background_cell_size=_BG,
    )
    with pytest.raises((AttributeError, TypeError)):
        w.severity = "info"

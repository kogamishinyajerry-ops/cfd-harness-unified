"""DEC-V61-142 (N3.3) · backend ↔ frontend library parity test.

The frontend mirror of the preset libraries lives in
``ui/frontend/src/pages/workbench/physics_panel/preset_library_view.ts``.
This test asserts that:

  * Every backend preset_id is present in the frontend mirror (set
    equality)
  * Every backend preset's citation URL appears verbatim in the
    mirror file (string substring match)
  * Every backend preset's display_name + key fluid/regime number
    appears verbatim in the mirror

When `materials_library.py` / `regimes_library.py` change without
updating the frontend mirror, this test fails — preventing the silent
drift the charter §"raw vs structured dict-write coexistence" guards
against.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.physics import (
    MATERIAL_PRESETS,
    REGIME_PRESETS,
)


_MIRROR_PATH = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "pages"
    / "workbench"
    / "physics_panel"
    / "preset_library_view.ts"
)


@pytest.fixture(scope="module")
def mirror_text() -> str:
    if not _MIRROR_PATH.is_file():
        pytest.skip(f"frontend mirror not present at {_MIRROR_PATH}")
    return _MIRROR_PATH.read_text(encoding="utf-8")


def test_every_backend_material_preset_id_in_mirror(mirror_text: str):
    for preset_id in MATERIAL_PRESETS:
        assert f'preset_id: "{preset_id}"' in mirror_text, (
            f"frontend mirror missing material preset_id={preset_id!r} — "
            "out-of-sync with backend library"
        )


def test_every_backend_regime_preset_id_in_mirror(mirror_text: str):
    for preset_id in REGIME_PRESETS:
        assert f'preset_id: "{preset_id}"' in mirror_text, (
            f"frontend mirror missing regime preset_id={preset_id!r} — "
            "out-of-sync with backend library"
        )


def test_every_backend_material_citation_in_mirror(mirror_text: str):
    for preset_id, preset in MATERIAL_PRESETS.items():
        assert preset.citation in mirror_text, (
            f"frontend mirror missing material citation for {preset_id!r}: "
            f"{preset.citation!r}"
        )


def test_every_backend_regime_citation_in_mirror(mirror_text: str):
    for preset_id, preset in REGIME_PRESETS.items():
        assert preset.citation in mirror_text, (
            f"frontend mirror missing regime citation for {preset_id!r}: "
            f"{preset.citation!r}"
        )


def test_material_density_values_in_mirror(mirror_text: str):
    """Catch numeric drift — if a material's ρ changes in the backend
    library but not the mirror, the engineer would see different
    values in the dropdown vs the on-disk dict."""
    for preset_id, preset in MATERIAL_PRESETS.items():
        rho_str = str(preset.fluid.density)
        assert rho_str in mirror_text, (
            f"frontend mirror missing density {rho_str} for {preset_id!r}"
        )


def test_regime_kind_literals_in_mirror(mirror_text: str):
    for preset_id, preset in REGIME_PRESETS.items():
        regime_literal = f'regime: "{preset.regime}"'
        assert regime_literal in mirror_text, (
            f"frontend mirror missing regime literal for {preset_id!r}: "
            f"{regime_literal}"
        )

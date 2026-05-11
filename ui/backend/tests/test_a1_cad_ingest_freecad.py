"""Tests for V198 A1 · cad_ingest_freecad.

Covers the pure filter logic in :func:`collect_named_solids` using
duck-typed mocks (no FreeCAD install needed). The FreeCAD-bound integration
path is gated by `pytest.importorskip` so CI/test-runners without FreeCAD
still go green.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from ui.backend.services.geometry_ingest.cad_ingest_freecad import (
    CADIngestBackendUnavailable,
    NamedSolid,
    collect_named_solids,
    load_step_preserving_names,
)


def _fake_shape(*, has_solids: bool = True, is_null: bool = False):
    return SimpleNamespace(
        Solids=[object()] if has_solids else [],
        isNull=lambda: is_null,
    )


def _fake_obj(*, type_id: str, label: str, name: str, shape):
    return SimpleNamespace(TypeId=type_id, Label=label, Name=name, Shape=shape)


def _fake_doc(objects):
    return SimpleNamespace(Objects=objects)


def test_collect_named_solids_skips_container_typeids():
    doc = _fake_doc(
        [
            _fake_obj(
                type_id="App::Part", label="root", name="part", shape=_fake_shape()
            ),
            _fake_obj(
                type_id="Part::Feature",
                label="combustor_outlet",
                name="body_3",
                shape=_fake_shape(),
            ),
            _fake_obj(
                type_id="App::Origin",
                label="origin",
                name="o1",
                shape=_fake_shape(),
            ),
        ]
    )
    result = collect_named_solids(doc)
    assert [r.label for r in result] == ["combustor_outlet"]
    assert result[0].name == "body_3"


def test_collect_named_solids_skips_null_and_no_solid_shapes():
    doc = _fake_doc(
        [
            _fake_obj(
                type_id="Part::Feature",
                label="empty_shape",
                name="e1",
                shape=None,
            ),
            _fake_obj(
                type_id="Part::Feature",
                label="null_shape",
                name="n1",
                shape=_fake_shape(is_null=True),
            ),
            _fake_obj(
                type_id="Part::Feature",
                label="wire_only",
                name="w1",
                shape=_fake_shape(has_solids=False),
            ),
            _fake_obj(
                type_id="Part::Feature",
                label="apu_intake",
                name="b2",
                shape=_fake_shape(),
            ),
        ]
    )
    result = collect_named_solids(doc)
    assert [r.label for r in result] == ["apu_intake"]


def test_collect_named_solids_preserves_document_order():
    doc = _fake_doc(
        [
            _fake_obj(
                type_id="Part::Feature",
                label=lbl,
                name=lbl,
                shape=_fake_shape(),
            )
            for lbl in ["b_first", "b_second", "b_third"]
        ]
    )
    result = collect_named_solids(doc)
    assert [r.label for r in result] == ["b_first", "b_second", "b_third"]


def test_collect_named_solids_falls_back_to_name_when_label_empty():
    doc = _fake_doc(
        [
            _fake_obj(
                type_id="Part::Feature",
                label="",
                name="fallback_name",
                shape=_fake_shape(),
            ),
        ]
    )
    result = collect_named_solids(doc)
    assert result[0].label == "fallback_name"
    assert isinstance(result[0], NamedSolid)


def test_load_step_raises_when_freecad_unavailable():
    pytest.importorskip("pytest")  # always succeeds
    try:
        import FreeCAD  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        with pytest.raises(CADIngestBackendUnavailable, match="FreeCAD is required"):
            load_step_preserving_names("/nonexistent/file.step")
    else:
        pytest.skip("FreeCAD is installed — unavailability error path not testable here")


def test_collect_named_solids_module_not_in_mutation_registry():
    """V130 advisor philosophy: a pure CAD-ingest helper is read-only.
    The module must not register itself in KNOWN_MUTATION_FUNCTIONS.
    """
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    for fn in KNOWN_MUTATION_FUNCTIONS:
        module = getattr(fn, "__module__", "")
        assert "cad_ingest_freecad" not in module

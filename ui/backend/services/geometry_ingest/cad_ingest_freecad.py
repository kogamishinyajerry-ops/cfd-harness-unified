"""STEP CAD ingest preserving named-body labels (V198 artifact A1).

Codifies the APU bay V1 finding: FreeCAD's documented `Part.insert()` STEP
loader drops the named-body hierarchy — every imported body comes back as
auto-generated `Part`, `Part001`, ... regardless of the CATIA/NX/SolidWorks
labels in the STEP file. The undocumented `Import.insert()` (from the
`Import` module) preserves them.

Source: `apu-bay-ventilation/scripts/01_cad_clean.py:73-85` +
`scripts/02_domain_subtract.py:80-102`.

V-series: V1 (industrial_case_solver_findings.md).

Design choice: FreeCAD is imported lazily inside `load_step_preserving_names`
because FreeCAD is a system app (not pip-installable). Callers that only need
the pure logic of :func:`collect_named_solids` (filter leaf solids from a
document object) can use it without FreeCAD installed — pass any object with
``.Objects`` returning items having ``.TypeId``, ``.Shape``, ``.Label``,
``.Name`` attributes. Mirrors the optional-backend pattern from
`geometry_surgery.py` (A3) and `virtual_interface_detector.py` (A2).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


# FreeCAD container / scaffolding types that hold no geometry of their own.
# Mirrors APU bay `02_domain_subtract.py:106-108` SKIP_TYPES.
_CONTAINER_TYPES: frozenset[str] = frozenset(
    {
        "App::Part",
        "Part::Compound",
        "Part::Compound2",
        "App::DocumentObjectGroup",
        "App::Origin",
        "App::Plane",
        "App::Line",
        "App::Point",
    }
)


class CADIngestBackendUnavailable(RuntimeError):
    """FreeCAD is not importable in this environment.

    A1 requires a system FreeCAD install (not pip). Typical install paths:
    macOS Homebrew `brew install freecad` → use `freecad.cmd` or
    `python3 -c "import FreeCAD"` via FreeCAD's bundled Python; Linux
    `apt install freecad`; or use the official AppImage with `FREECAD_USER_MOD`
    pointing at a Python with FreeCAD's `lib/` on `sys.path`.
    """


@dataclass(frozen=True)
class NamedSolid:
    """One leaf-solid CAD body indexed by its STEP-preserved Label."""

    label: str
    name: str
    obj: Any  # the FreeCAD DocumentObject (opaque to callers without FreeCAD)


def load_step_preserving_names(
    step_path: Path | str,
    doc_name: str = "cad_ingest",
) -> Any:
    """Load a STEP file into a FreeCAD document **preserving body labels**.

    Uses the undocumented `Import` module (not the documented `Part.insert`)
    because the latter drops CATIA/NX/SolidWorks named-body labels — see V1.

    Returns the loaded FreeCAD Document (caller owns lifecycle and must call
    `FreeCAD.closeDocument(doc.Name)` when done).
    """
    try:
        import FreeCAD  # type: ignore[import-not-found]
        import Import as _Importer  # type: ignore[import-not-found]
    except ImportError as exc:
        raise CADIngestBackendUnavailable(
            "FreeCAD is required for STEP ingest with name preservation. "
            "See cad_ingest_freecad.CADIngestBackendUnavailable docstring "
            "for install hints."
        ) from exc

    path_str = str(Path(step_path))
    doc = FreeCAD.newDocument(doc_name)
    _Importer.insert(path_str, doc.Name)
    doc.recompute()
    return doc


def collect_named_solids(doc: Any) -> list[NamedSolid]:
    """Return leaf solids from `doc` indexed by Label, in document order.

    A leaf solid is any DocumentObject that:
      1. Has `TypeId` not in :data:`_CONTAINER_TYPES`
      2. Has a non-null `Shape` attribute
      3. Has `Shape.Solids` non-empty

    Label preservation depends on the loader having used `Import.insert()`
    (see :func:`load_step_preserving_names`). With `Part.insert()` upstream,
    every Label becomes `Part`, `Part001`, ... and downstream mapping breaks.

    Pure on the duck-typed `doc.Objects` iterable — does not require FreeCAD
    to be importable, so the filter logic is unit-testable in isolation.
    """
    solids: list[NamedSolid] = []
    for obj in doc.Objects:
        if obj.TypeId in _CONTAINER_TYPES:
            continue
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull():
            continue
        if not shape.Solids:
            continue
        label = obj.Label or obj.Name
        solids.append(NamedSolid(label=label, name=obj.Name, obj=obj))
    return solids

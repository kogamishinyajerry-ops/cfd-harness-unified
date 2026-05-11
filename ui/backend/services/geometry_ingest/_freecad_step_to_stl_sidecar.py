"""FreeCAD subprocess sidecar for STEP→STL conversion (V198 4a).

Runs *inside* ``freecadcmd``, never in the main venv. Reads sidecar args
file specified by ``STEP_TO_STL_ARGS`` env var; opens STEP via A1 pattern
(``Import.insert`` preserves named-body labels); meshes each named leaf
solid via ``MeshPart.meshFromShape`` at the supplied deflections; writes
one ASCII STL per body + a ``manifest.json`` to ``out_dir``.

Underscore-prefixed module name keeps pytest collection out (FreeCAD
imports would fail in normal test runs).
"""
import json
import os
import re

import FreeCAD  # type: ignore[import-not-found]
import Import as _Importer  # type: ignore[import-not-found]
import MeshPart  # type: ignore[import-not-found]

_SKIP_TYPES = {
    "App::Part",
    "Part::Compound",
    "Part::Compound2",
    "App::DocumentObjectGroup",
    "App::Origin",
    "App::Plane",
    "App::Line",
    "App::Point",
}
_SANITIZE = re.compile(r"[^a-z0-9]+")


def _sanitize(label):
    cleaned = _SANITIZE.sub("_", label.strip().lower()).strip("_")
    return cleaned or "body"


with open(os.environ["STEP_TO_STL_ARGS"]) as fh:
    _lines = [ln.strip() for ln in fh.readlines() if ln.strip()]
_step_path, _out_dir = _lines[0], _lines[1]
_lin_def, _ang_def = float(_lines[2]), float(_lines[3])

_doc = FreeCAD.newDocument("step_to_stl")
_Importer.insert(_step_path, _doc.Name)
_doc.recompute()

_bodies = []
_used = {}
for _obj in _doc.Objects:
    if _obj.TypeId in _SKIP_TYPES:
        continue
    _shape = getattr(_obj, "Shape", None)
    if _shape is None or _shape.isNull() or not _shape.Solids:
        continue
    _label = _obj.Label or _obj.Name
    _stem = _sanitize(_label)
    _n = _used.get(_stem, 0) + 1
    _used[_stem] = _n
    _final = _stem if _n == 1 else f"{_stem}_{_n}"
    _out = os.path.join(_out_dir, f"{_final}.stl")
    _mesh = MeshPart.meshFromShape(
        Shape=_shape, LinearDeflection=_lin_def, AngularDeflection=_ang_def
    )
    _mesh.write(Filename=_out, Format="AST")
    _bodies.append(
        {
            "label": _label,
            "name": _obj.Name,
            "stem": _final,
            "path": _out,
            "n_facets": _mesh.CountFacets,
        }
    )

with open(os.path.join(_out_dir, "manifest.json"), "w") as _fh:
    json.dump(
        {"step_path": _step_path, "n_bodies": len(_bodies), "bodies": _bodies},
        _fh,
        indent=2,
    )

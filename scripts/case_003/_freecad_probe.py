"""FreeCAD subprocess probe — runs inside freecadcmd, NOT in main venv.

Loads STEP via Import.insert() (V198 A1 pattern), collects named-leaf-solid
metadata + bbox, writes JSON to stdout. Read by scripts/case_003/ramp_session_1.py
in the main venv to feed into A1/P0 logic.

Usage (inside freecadcmd):
    freecadcmd -c "exec(open('scripts/case_003/_freecad_probe.py').read())" \\
        --pass <step_path> <json_out_path>

Or via subprocess from main venv (see ramp_session_1.py).
"""
import os
import json

import FreeCAD  # type: ignore
import Import as _Importer  # type: ignore

# Read paths from sidecar args file (freecadcmd's positional-arg handling
# auto-opens any non-script path it sees, which fails for our JSON output.
# Sidecar file avoids the issue.)
_ARGS_FILE = os.path.join(
    "ui", "backend", "user_drafts", "imported", "case_003_crm_hls", "_probe_args.txt"
)
with open(_ARGS_FILE) as fh:
    lines = [ln.strip() for ln in fh.readlines() if ln.strip()]
step_path, out_path = lines[0], lines[1]

_CONTAINER_TYPES = {
    "App::Part",
    "Part::Compound",
    "Part::Compound2",
    "App::DocumentObjectGroup",
    "App::Origin",
    "App::Plane",
    "App::Line",
    "App::Point",
}

doc = FreeCAD.newDocument("case_003")
_Importer.insert(step_path, doc.Name)
doc.recompute()

solids = []
bbox_max_extent = 0.0
for obj in doc.Objects:
    if obj.TypeId in _CONTAINER_TYPES:
        continue
    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        continue
    if not shape.Solids:
        continue
    label = obj.Label or obj.Name
    bb = shape.BoundBox
    solids.append(
        {
            "label": label,
            "name": obj.Name,
            "type_id": obj.TypeId,
            "n_solids": len(shape.Solids),
            "n_faces": len(shape.Faces),
            "bbox": {
                "x_min": bb.XMin,
                "y_min": bb.YMin,
                "z_min": bb.ZMin,
                "x_max": bb.XMax,
                "y_max": bb.YMax,
                "z_max": bb.ZMax,
                "x_length": bb.XLength,
                "y_length": bb.YLength,
                "z_length": bb.ZLength,
            },
        }
    )
    bbox_max_extent = max(
        bbox_max_extent, bb.XLength, bb.YLength, bb.ZLength
    )

with open(out_path, "w") as fh:
    json.dump(
        {
            "step_path": step_path,
            "n_solids": len(solids),
            "bbox_max_extent_raw": bbox_max_extent,
            "solids": solids,
        },
        fh,
        indent=2,
    )

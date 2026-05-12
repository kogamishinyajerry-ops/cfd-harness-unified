"""Session 8 probe1: try FreeCAD compound tessellation for shared-edge
vertex stitching.

Three variants in one run:
  C1: status quo (per-body MeshPart.meshFromShape) — baseline reference
  C2: Part.makeCompound([body.Shape ...]) + one meshFromShape call
  C3: Part.Compound with explicit removeSplitter + sewing

Output: per-variant combined STL → feed to gmsh, count facets +
degenerates at Tolerance=1e-12 (the clean-substrate measurement). If
C2 produces a STL that gmsh accepts without HXT PLC error → compound
alone is sufficient. If only C3 succeeds → need explicit sewing in
sidecar.

This script runs INSIDE freecadcmd. Driver below launches it.
"""
import json
import os
import re
import sys

import FreeCAD  # type: ignore
import Import as _Importer  # type: ignore
import MeshPart  # type: ignore
import Part  # type: ignore

_SANITIZE = re.compile(r"[^a-z0-9]+")


def sanitize(label):
    cleaned = _SANITIZE.sub("_", label.strip().lower()).strip("_")
    return cleaned or "body"


STEP = os.environ["STEP_PATH"]
OUT_DIR = os.environ["OUT_DIR"]
LIN_DEF = 0.05
ANG_DEF = 0.1


def load_bodies():
    doc = FreeCAD.newDocument("probe")
    _Importer.insert(STEP, doc.Name)
    doc.recompute()
    bodies = []
    skip = {"App::Part", "Part::Compound", "Part::Compound2",
            "App::DocumentObjectGroup", "App::Origin",
            "App::Plane", "App::Line", "App::Point"}
    for obj in doc.Objects:
        if obj.TypeId in skip:
            continue
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull() or not shape.Solids:
            continue
        label = obj.Label or obj.Name
        bodies.append((sanitize(label), shape))
    return doc, bodies


def emit_solid(name, mesh, fh):
    """Write one ``solid <name>`` block from a FreeCAD Mesh object."""
    fh.write(f"solid {name}\n")
    for facet in mesh.Facets:
        nx, ny, nz = facet.Normal
        fh.write(f"  facet normal {nx:.6e} {ny:.6e} {nz:.6e}\n")
        fh.write("    outer loop\n")
        for pt in facet.Points:
            fh.write(f"      vertex {pt[0]:.6e} {pt[1]:.6e} {pt[2]:.6e}\n")
        fh.write("    endloop\n")
        fh.write("  endfacet\n")
    fh.write(f"endsolid {name}\n")


def v_c1_per_body(bodies):
    """Per-body MeshPart.meshFromShape — status quo."""
    out = os.path.join(OUT_DIR, "c1_per_body.stl")
    n_facets = 0
    with open(out, "w") as fh:
        for name, shape in bodies:
            m = MeshPart.meshFromShape(
                Shape=shape, LinearDeflection=LIN_DEF, AngularDeflection=ANG_DEF
            )
            emit_solid(name, m, fh)
            n_facets += m.CountFacets
    return out, n_facets


def v_c2_compound(bodies):
    """Single Compound + one meshFromShape — relies on OCC BRep
    tessellation to share vertices at shared edges."""
    out = os.path.join(OUT_DIR, "c2_compound.stl")
    compound = Part.makeCompound([s for _, s in bodies])
    m = MeshPart.meshFromShape(
        Shape=compound, LinearDeflection=LIN_DEF, AngularDeflection=ANG_DEF
    )
    # Single solid block — no per-body split (we just want to see if
    # tessellation is watertight). Later impl will split by face groups.
    with open(out, "w") as fh:
        emit_solid("combined", m, fh)
    return out, m.CountFacets


def v_c3_sewing(bodies):
    """Use Part.Shape.fuse to weld shared edges, then mesh the fused
    shape. This is OCC's BRepAlgoAPI_Fuse + the resulting solid has
    proper shared-edge topology."""
    out = os.path.join(OUT_DIR, "c3_fused.stl")
    fused = bodies[0][1]
    for _, s in bodies[1:]:
        fused = fused.fuse(s)
    # Remove redundant interior splitters (sliver edges)
    fused = fused.removeSplitter()
    m = MeshPart.meshFromShape(
        Shape=fused, LinearDeflection=LIN_DEF, AngularDeflection=ANG_DEF
    )
    with open(out, "w") as fh:
        emit_solid("fused", m, fh)
    return out, m.CountFacets


doc, bodies = load_bodies()
print(f"loaded {len(bodies)} bodies: {[b[0] for b in bodies]}", flush=True)

results = {}
for name, fn in [("c1_per_body", v_c1_per_body),
                 ("c2_compound", v_c2_compound),
                 ("c3_fused", v_c3_sewing)]:
    try:
        path, n = fn(bodies)
        results[name] = {"ok": True, "path": path, "facets": n}
        print(f"{name}: OK {path} facets={n}", flush=True)
    except Exception as exc:
        results[name] = {"ok": False, "error": str(exc)}
        print(f"{name}: FAILED {exc!r}", flush=True)

with open(os.path.join(OUT_DIR, "probe1_results.json"), "w") as fh:
    json.dump(results, fh, indent=2)
print("probe1 done", flush=True)

"""Session 9 probe1: count gmsh entities at each pipeline stage for
the large fixture, to diagnose why F2 path's named-solid voting only
emits 1 of 3 expected PhysicalGroups.

Compare against the 12-facet seamed fixture (session 7 test passes) at
each stage:
  (a) post merge — should see N=3 discrete surface entities (one per
      STL solid block, default Mesh.StlOneSolidPerSurface=1)
  (b) post classifySurfaces(angle=180°, boundary=False, fr=False) —
      may merge to 1 entity OR keep 3

If (b) shows 1 entity on the large fixture but 3 on the small fixture,
classifySurfaces is the culprit and we need to either:
  - keep the original discrete entities (skip classify entirely on F2)
  - tune classifier params to preserve solid boundaries
  - construct PhysicalGroups from the pre-classify entities
"""
import math, sys, time
from pathlib import Path

# Build large fixture in-process
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.tests.conftest import (
    seamed_multi_solid_box_stl,
    large_seamed_multi_solid_box_stl,
)

OUT = Path("/tmp/case_session9_probe1")
OUT.mkdir(exist_ok=True)
SMALL = OUT / "small.stl"
LARGE = OUT / "large.stl"
SMALL.write_bytes(seamed_multi_solid_box_stl())
LARGE.write_bytes(large_seamed_multi_solid_box_stl())
print(f"small: {SMALL.stat().st_size:,} bytes", flush=True)
print(f"large: {LARGE.stat().st_size:,} bytes", flush=True)


def probe(stl_path, label):
    print(f"\n=== {label}: {stl_path} ===", flush=True)
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.Verbosity", 1)
    gmsh.option.setNumber("Geometry.Tolerance", 1e-12)

    gmsh.merge(str(stl_path))
    ents = gmsh.model.getEntities(2)
    print(f"  post-merge dim=2 entities: {len(ents)}", flush=True)
    for d, t in ents:
        _, tags_list, _ = gmsh.model.mesh.getElements(dim=2, tag=t)
        ntris = sum(len(tt) for tt in tags_list)
        print(f"    entity tag={t}  type={gmsh.model.getType(d,t)}  ntris={ntris}", flush=True)

    gmsh.model.mesh.classifySurfaces(
        angle=180.0*math.pi/180.0, boundary=False, forReparametrization=False,
        curveAngle=180.0*math.pi/180.0,
    )
    ents = gmsh.model.getEntities(2)
    print(f"  post-classify(angle=180°, boundary=False, fr=False) dim=2 entities: {len(ents)}", flush=True)
    for d, t in ents:
        _, tags_list, _ = gmsh.model.mesh.getElements(dim=2, tag=t)
        ntris = sum(len(tt) for tt in tags_list)
        print(f"    entity tag={t}  type={gmsh.model.getType(d,t)}  ntris={ntris}", flush=True)

    gmsh.finalize()


probe(SMALL, "SMALL (12 facets seamed)")
probe(LARGE, "LARGE (12288 facets subdivided)")

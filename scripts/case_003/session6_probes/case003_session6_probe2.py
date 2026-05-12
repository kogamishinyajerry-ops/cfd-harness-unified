"""Session 6 segment 1 probe2: can we generate(3) on a discrete-entity
volume bounded by gmsh.merge's STL solids — WITHOUT classifySurfaces?

If yes: F-NEW-22 has a clean architectural bypass.
If hangs: gmsh's 3D mesher internally triggers classify-equivalent work
         and discrete-surface path is not the silver bullet.

Hard wall-clock cutoff = 120 s (signal-based; F-NEW-23 noted gmsh C++
ignores SIGALRM during classify, but generate(3) is a separate stage
that may yield more often; if it doesn't, the parent wrapper kills).
"""
import sys
import time

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"

t0 = time.monotonic()
def t(): return f"[{time.monotonic()-t0:7.2f}s]"

print(f"{t()} probe2 start", flush=True)
import gmsh
print(f"{t()} gmsh import", flush=True)

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.option.setNumber("General.Verbosity", 1)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Algorithm3D", 1)  # Delaunay 3D, same as M6
print(f"{t()} gmsh init", flush=True)

gmsh.merge(STL)
print(f"{t()} gmsh.merge done", flush=True)

ent_2d = gmsh.model.getEntities(dim=2)
print(f"{t()} dim=2 entities: {len(ent_2d)}", flush=True)

# Create discrete volume bounded by all surfaces (passthrough mode)
vol_tag = gmsh.model.addDiscreteEntity(dim=3, tag=-1, boundary=[t_ for _, t_ in ent_2d])
print(f"{t()} addDiscreteEntity(dim=3) returned tag={vol_tag}", flush=True)

# Synchronize
gmsh.model.geo.synchronize()
print(f"{t()} synchronize done", flush=True)

# Try generate(3) — the moment of truth
print(f"{t()} calling generate(3) — this is the critical experiment", flush=True)
try:
    gmsh.model.mesh.generate(3)
    print(f"{t()} generate(3) RETURNED", flush=True)

    # Count generated cells
    _, _, elem_tags_3d = gmsh.model.mesh.getElements(dim=3)
    n_cells = sum(len(tags) for tags in elem_tags_3d)
    print(f"{t()} GENERATED {n_cells:,} 3D cells", flush=True)
except Exception as exc:
    print(f"{t()} generate(3) RAISED: {exc!r}", flush=True)

gmsh.finalize()
print(f"{t()} probe2 done", flush=True)

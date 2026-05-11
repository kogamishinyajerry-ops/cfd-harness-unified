"""Session 6 probe8: F2 path + HXT (Algorithm3D=10) — last shot at
producing case_003 cells in session 6. HXT typically handles degenerate
input triangles more gracefully than Delaunay 3D.
"""
import time, sys, math

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"

t0 = time.monotonic()
def t(): return f"[{time.monotonic()-t0:7.2f}s]"

print(f"{t()} probe8 start (F2 + HXT, coarse lc)", flush=True)
import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setNumber("General.Verbosity", 3)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Algorithm3D", 10)  # HXT
print(f"{t()} gmsh init", flush=True)

gmsh.merge(STL)
print(f"{t()} merge done", flush=True)

lc = 200_000.0
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc * 0.5)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc * 2.0)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)

gmsh.model.mesh.classifySurfaces(
    angle=180.0 * math.pi / 180.0,
    boundary=False,
    forReparametrization=False,
    curveAngle=180.0 * math.pi / 180.0,
)
print(f"{t()} fast-classify done", flush=True)

ent_2d = gmsh.model.getEntities(2)
loop = gmsh.model.geo.addSurfaceLoop([tt for _, tt in ent_2d])
vol = gmsh.model.geo.addVolume([loop])
print(f"{t()} addSurfaceLoop={loop} addVolume={vol}", flush=True)
gmsh.model.geo.synchronize()
print(f"{t()} synchronize done", flush=True)

print(f"{t()} calling generate(3) with HXT", flush=True)
try:
    gmsh.model.mesh.generate(3)
    print(f"{t()} generate(3) RETURNED", flush=True)
    _, _, e3 = gmsh.model.mesh.getElements(dim=3)
    n_cells = sum(len(tags) for tags in e3)
    print(f"{t()} HXT MESHED — {n_cells:,} 3D cells", flush=True)
except Exception as exc:
    print(f"{t()} generate(3) FAILED: {exc!r}", flush=True)

gmsh.finalize()
print(f"{t()} probe8 done", flush=True)

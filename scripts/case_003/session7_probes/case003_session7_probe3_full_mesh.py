"""Session 7 probe3: definitive case_003 e2e mesh test.

Combine: F2 path (fast-classify + skip createGeometry + addSurfaceLoop +
addVolume) + Geometry.Tolerance=1e-12 + coarse 200m lc.

If generate(3) produces non-zero cells → F-NEW-22 + F-NEW-24 + F-NEW-25
all solved by tolerance + F2 path. case_003 substrate is clean; we can
go straight to F2 implementation in gmsh_runner.py.

If still fails → at least one of F-NEW-25 (genuine self-intersection)
or another wall is real.
"""
import time, math, sys
from pathlib import Path

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"

t0 = time.monotonic()
def t(): return f"[{time.monotonic()-t0:7.2f}s]"

print(f"{t()} probe3 start (F2 + Tolerance=1e-12 + coarse lc)", flush=True)
import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setNumber("General.Verbosity", 3)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Algorithm3D", 1)
gmsh.option.setNumber("Geometry.Tolerance", 1e-12)  # <-- the critical option
print(f"{t()} gmsh init (Geometry.Tolerance=1e-12)", flush=True)

gmsh.merge(STL)
print(f"{t()} merge done — dim=2 ents: {len(gmsh.model.getEntities(2))}", flush=True)

# Coarse uniform lc, no F-NEW-19 filter
lc = 200_000.0
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc * 0.5)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc * 2.0)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)

# F2 path
gmsh.model.mesh.classifySurfaces(
    angle=180.0 * math.pi / 180.0,
    boundary=False,
    forReparametrization=False,
    curveAngle=180.0 * math.pi / 180.0,
)
print(f"{t()} fast-classify done — dim=2 ents: {len(gmsh.model.getEntities(2))}", flush=True)

ent_2d = gmsh.model.getEntities(2)
loop = gmsh.model.geo.addSurfaceLoop([tag for _, tag in ent_2d])
vol = gmsh.model.geo.addVolume([loop])
print(f"{t()} addSurfaceLoop={loop} addVolume={vol}", flush=True)
gmsh.model.geo.synchronize()
print(f"{t()} synchronize done", flush=True)

print(f"{t()} calling generate(3) — the moment of truth", flush=True)
try:
    gmsh.model.mesh.generate(3)
    print(f"{t()} generate(3) RETURNED", flush=True)
    _, _, e3 = gmsh.model.mesh.getElements(dim=3)
    n_cells = sum(len(tags) for tags in e3)
    print(f"{t()} CASE_003 MESHED — {n_cells:,} 3D cells", flush=True)

    # Also try writing the mesh
    msh_out = "/tmp/case003_session7_probe3.msh"
    gmsh.write(msh_out)
    sz = Path(msh_out).stat().st_size
    print(f"{t()} Wrote MSH file: {msh_out} ({sz:,} bytes)", flush=True)
except Exception as exc:
    print(f"{t()} generate(3) FAILED: {exc!r}", flush=True)

gmsh.finalize()
print(f"{t()} probe3 done", flush=True)

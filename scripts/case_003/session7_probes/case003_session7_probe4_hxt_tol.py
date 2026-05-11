"""Session 7 probe4: F2 + Tolerance=1e-12 + HXT (Algorithm3D=10).

Session 6 probe8 was HXT + default Tolerance=1e-8 — fast-failed with
PLC error at (-838124,838200,838124). Hypothesis: that PLC error was
also a dedup artifact, just like the 9356 degenerates. With proper
Tolerance, HXT should run clean.
"""
import time, math, sys
from pathlib import Path

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"

t0 = time.monotonic()
def t(): return f"[{time.monotonic()-t0:7.2f}s]"

print(f"{t()} probe4 start (F2 + HXT + Tolerance=1e-12)", flush=True)
import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setNumber("General.Verbosity", 5)  # max verbose
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Algorithm3D", 10)  # HXT
gmsh.option.setNumber("Geometry.Tolerance", 1e-12)

gmsh.merge(STL)
print(f"{t()} merge done", flush=True)

lc = 200_000.0
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc * 0.5)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc * 2.0)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)

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

print(f"{t()} calling generate(3) with HXT + Tolerance=1e-12", flush=True)
try:
    gmsh.model.mesh.generate(3)
    print(f"{t()} generate(3) RETURNED", flush=True)
    _, _, e3 = gmsh.model.mesh.getElements(dim=3)
    n_cells = sum(len(tags) for tags in e3)
    print(f"{t()} CASE_003 MESHED — {n_cells:,} 3D cells", flush=True)
    msh_out = "/tmp/case003_session7_probe4.msh"
    gmsh.write(msh_out)
    sz = Path(msh_out).stat().st_size
    print(f"{t()} Wrote MSH: {msh_out} ({sz:,} bytes)", flush=True)
except Exception as exc:
    print(f"{t()} generate(3) FAILED: {exc!r}", flush=True)

gmsh.finalize()
print(f"{t()} probe4 done", flush=True)

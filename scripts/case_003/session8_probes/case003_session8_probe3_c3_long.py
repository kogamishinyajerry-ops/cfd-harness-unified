"""Session 8 probe3: extend C3 verification with longer timeout
and Delaunay 3D alternative.
"""
import math, time, sys, subprocess, os, signal

STL = "/tmp/case003_session8_probe1_out/c3_fused.stl"

def run_with_algo(algo3d, timeout_s):
    label = f"C3_algo{algo3d}"
    code = f"""
import math, time, gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setNumber("General.Verbosity", 5)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Algorithm3D", {algo3d})
gmsh.option.setNumber("Geometry.Tolerance", 1e-12)
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 200_000)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 500_000)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

t0 = time.monotonic()
def t(): return f"[{{time.monotonic()-t0:7.2f}}s]"

print(f"{{t()}} merge", flush=True)
gmsh.merge({STL!r})
print(f"{{t()}} merge done — dim=2 ents pre: {{len(gmsh.model.getEntities(2))}}", flush=True)

gmsh.model.mesh.classifySurfaces(
    angle=180.0*math.pi/180.0, boundary=False, forReparametrization=False,
    curveAngle=180.0*math.pi/180.0,
)
print(f"{{t()}} fast-classify done — ents: {{len(gmsh.model.getEntities(2))}}", flush=True)

ent_2d = gmsh.model.getEntities(2)
loop = gmsh.model.geo.addSurfaceLoop([tag for _, tag in ent_2d])
vol = gmsh.model.geo.addVolume([loop])
gmsh.model.geo.synchronize()
print(f"{{t()}} synchronize done", flush=True)

try:
    gmsh.model.mesh.generate(3)
    _, _, e3 = gmsh.model.mesh.getElements(dim=3)
    n = sum(len(tags) for tags in e3)
    print(f"{{t()}} {label} OK — {{n:,}} 3D cells", flush=True)
    print(f"VERDICT_{label}=WATERTIGHT_CELLS={{n}}", flush=True)
except Exception as exc:
    print(f"{{t()}} {label} FAILED: {{exc!r}}", flush=True)
    print(f"VERDICT_{label}=FAIL", flush=True)

gmsh.finalize()
"""
    print(f"\n>>> launching {label} timeout={timeout_s}s", flush=True)
    proc = subprocess.Popen(
        ["/Users/Zhuanz/Desktop/cfd-harness-unified/.venv/bin/python", "-c", code],
        stdout=sys.stdout, stderr=sys.stderr, start_new_session=True,
    )
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        print(f">>> {label} HARD TIMEOUT {timeout_s}s — killing", flush=True)
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        print(f"VERDICT_{label}=HANG", flush=True)


# HXT first (faster on success, faster fast-fail on PLC). 5 min cap.
run_with_algo(10, 300)
# Delaunay 3D second — known slower but more robust. 5 min cap.
run_with_algo(1, 300)

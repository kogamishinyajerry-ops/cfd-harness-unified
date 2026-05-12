"""Session 8 probe2: feed each probe1 variant through gmsh + HXT to
detect remaining self-intersections.

For each STL, run F2 path equivalent:
  1. Tolerance=1e-12 + merge
  2. fast-classify
  3. addSurfaceLoop + addVolume
  4. generate(3) with HXT (Algorithm3D=10) — fast-fails on PLC error,
     succeeds on watertight stitched STL

Hard 60s timeout per variant; output: which variants survive HXT.
"""
import math
import os
import subprocess
import sys


def run_variant(stl_path, label, timeout_s=60):
    """Spawn isolated gmsh subprocess for clean state."""
    code = f"""
import math, time, sys
import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setNumber("General.Verbosity", 3)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Algorithm3D", 10)  # HXT
gmsh.option.setNumber("Geometry.Tolerance", 1e-12)

t0 = time.monotonic()
def t(): return f"[{{time.monotonic()-t0:6.2f}}s]"

print(f"{{t()}} {label!r}: merge {stl_path!r}", flush=True)
gmsh.merge({stl_path!r})
ent_2d_pre = gmsh.model.getEntities(2)
print(f"{{t()}} merge done — dim=2 ents pre-classify: {{len(ent_2d_pre)}}", flush=True)

gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 100_000)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 400_000)

gmsh.model.mesh.classifySurfaces(
    angle=180.0 * math.pi / 180.0,
    boundary=False,
    forReparametrization=False,
    curveAngle=180.0 * math.pi / 180.0,
)
print(f"{{t()}} fast-classify done — dim=2 ents: {{len(gmsh.model.getEntities(2))}}", flush=True)

ent_2d = gmsh.model.getEntities(2)
loop = gmsh.model.geo.addSurfaceLoop([tag for _, tag in ent_2d])
vol = gmsh.model.geo.addVolume([loop])
gmsh.model.geo.synchronize()
print(f"{{t()}} synchronize done", flush=True)

try:
    gmsh.model.mesh.generate(3)
    _, _, e3 = gmsh.model.mesh.getElements(dim=3)
    n = sum(len(tags) for tags in e3)
    print(f"{{t()}} HXT OK — {{n:,}} 3D cells", flush=True)
    print(f"{label!r}: VERDICT = WATERTIGHT", flush=True)
except Exception as exc:
    print(f"{{t()}} HXT FAILED: {{exc!r}}", flush=True)
    print(f"{label!r}: VERDICT = SELF_INTERSECTION", flush=True)

gmsh.finalize()
"""
    proc = subprocess.Popen(
        ["/Users/Zhuanz/Desktop/cfd-harness-unified/.venv/bin/python", "-c", code],
        stdout=sys.stdout, stderr=sys.stderr, start_new_session=True,
    )
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        print(f"{label}: HARD TIMEOUT {timeout_s}s — killing", flush=True)
        os.killpg(proc.pid, 9)
        proc.wait()
        print(f"{label}: VERDICT = HANG", flush=True)


PROBE_DIR = "/tmp/case003_session8_probe1_out"
for label, fname in [("C1_per_body", "c1_per_body.stl"),
                     ("C2_compound", "c2_compound.stl"),
                     ("C3_fused", "c3_fused.stl")]:
    path = os.path.join(PROBE_DIR, fname)
    sz = os.path.getsize(path)
    print(f"\n>>> {label} ({sz:,} bytes)\n", flush=True)
    run_variant(path, label)

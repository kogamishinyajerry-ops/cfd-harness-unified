"""Session 8 probe5: bisect which body pair is responsible for the
self-intersection at (1.6e6, 838200, -702488).

Hypothesis: the medium-farfield pair (tags 5,6 from session 6 probe7 =
root_mount_cover, thin_access_plate — extent ~1.6km) may overlap in the
source STEP.

Actually wait — looking at session 7 probe1 per-body listing:
  airframe_reference (393k tris)
  root_mount_pad (12), root_mount_cover (12), thin_access_plate (12)
  inlet (12), outlet (12), symmetry_plane (12)
  farfield_top (12), farfield_bottom (12), farfield_outer (12)

And session 6 probe7 bbox listing:
  tag=1 152,400  → airframe (big)
  tags 2,3,4 18,288-27,432  → small mounts
  tags 5,6 1,600,200  → ???
  tags 7-10 2,438,400  → farfield outer-class

The 12-tri bodies are 6-face boxes. Of these, the extent-1.6M bodies
must be the 2 farfields with that scale. The PLC error coord
(1.6e6, 838200, -702488) is on one of those 1.6M-extent box boundaries.

Strategy: drop bodies one-by-one and find which exclusion clears the
PLC. If excluding {root_mount_*, thin_access_plate} clears it →
internal mount geometry penetrates farfield. If excluding farfield_*
clears it → farfield geometry self-intersects.
"""
import re, sys, math, subprocess, signal, os
from pathlib import Path
import numpy as np

STL_DIR = Path("/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2")

_SOLID_BLOCK_RE = re.compile(
    rb"^\s*solid\s+(\S+)[^\n]*$\n([\s\S]*?)^\s*endsolid\b[^\n]*$\n?", re.MULTILINE)


def gmsh_verify(stl_path, label, timeout_s=60):
    code = f"""
import math, gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.option.setNumber("General.Verbosity", 2)
gmsh.option.setNumber("Mesh.Algorithm3D", 10)
gmsh.option.setNumber("Geometry.Tolerance", 1e-12)
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 100_000)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 500_000)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
gmsh.merge({stl_path!r})
gmsh.model.mesh.classifySurfaces(
    angle=180.0*math.pi/180.0, boundary=False, forReparametrization=False,
    curveAngle=180.0*math.pi/180.0)
ent_2d = gmsh.model.getEntities(2)
loop = gmsh.model.geo.addSurfaceLoop([tag for _, tag in ent_2d])
gmsh.model.geo.addVolume([loop])
gmsh.model.geo.synchronize()
try:
    gmsh.model.mesh.generate(3)
    _, _, e3 = gmsh.model.mesh.getElements(dim=3)
    n = sum(len(tags) for tags in e3)
    print(f"VERDICT_{label}=CELLS_{{n}}", flush=True)
except Exception as exc:
    print(f"VERDICT_{label}=FAIL {{exc!r}}", flush=True)
gmsh.finalize()
"""
    proc = subprocess.Popen(
        ["/Users/Zhuanz/Desktop/cfd-harness-unified/.venv/bin/python", "-c", code],
        stdout=sys.stdout, stderr=sys.stderr, start_new_session=True)
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        print(f"VERDICT_{label}=HANG", flush=True)


def build_combined(include_names, out_path):
    """Concatenate per-body STLs for names in include_names."""
    import json
    manifest = json.loads((STL_DIR / "manifest.json").read_text())
    pieces = []
    for body in manifest["bodies"]:
        if body["stem"] not in include_names:
            continue
        raw = Path(body["path"]).read_bytes()
        # Rewrite solid name to stem
        rewritten = re.sub(rb"^\s*solid\b[^\n]*",
                           f"solid {body['stem']}".encode(), raw,
                           count=1, flags=re.MULTILINE)
        rewritten = re.sub(rb"^\s*endsolid\b[^\n]*",
                           f"endsolid {body['stem']}".encode(), rewritten,
                           count=1, flags=re.MULTILINE)
        if not rewritten.endswith(b"\n"):
            rewritten += b"\n"
        pieces.append(rewritten)
    Path(out_path).write_bytes(b"".join(pieces))


# All bodies
ALL = ["airframe_reference", "root_mount_pad", "root_mount_cover",
       "thin_access_plate", "inlet", "outlet", "symmetry_plane",
       "farfield_top", "farfield_bottom", "farfield_outer"]

# Exclusion variants
variants = [
    ("all_bodies", ALL),
    ("no_mounts", [b for b in ALL if b not in
                   ("root_mount_pad", "root_mount_cover", "thin_access_plate")]),
    ("no_farfield", [b for b in ALL if not b.startswith("farfield_")]),
    ("no_airframe", [b for b in ALL if b != "airframe_reference"]),
    ("farfield_only", [b for b in ALL if b.startswith("farfield_")]),
]

for label, includes in variants:
    out = f"/tmp/case003_session8_bisect_{label}.stl"
    build_combined(set(includes), out)
    sz = Path(out).stat().st_size
    print(f"\n=== {label} ({len(includes)} bodies, {sz:,} bytes) ===", flush=True)
    gmsh_verify(out, label, timeout_s=90)

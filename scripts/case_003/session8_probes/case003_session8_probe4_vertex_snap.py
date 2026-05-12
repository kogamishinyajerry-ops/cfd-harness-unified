"""Session 8 probe4: post-tessellation vertex snap in combine layer.

Strategy:
  1. Read all per-body ASCII STLs from stl_session_2/
  2. Parse triangles → numpy array of (n_tri, 3, 3)
  3. Build hash of vertex coords (rounded to snap tolerance)
  4. Snap each vertex to the canonical position of its hash bucket
  5. Re-emit combined STL with snapped triangles
  6. Feed to gmsh HXT, see if PLC error disappears

Tolerance: Q3 = 0.05 mm linear deflection. Vertex snap should use
something on the order of 1e-3 to 1e-1 mm — small enough to preserve
real features, large enough to catch independently-tessellated
shared-edge vertices.

This probe tests several snap tolerances to find the right value.
"""
import re
import sys
import math
import time
import subprocess
import signal
import os
from pathlib import Path

import numpy as np

STL_DIR = Path("/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2")

_SOLID_BLOCK_RE = re.compile(
    rb"^\s*solid\s+(\S+)[^\n]*$\n([\s\S]*?)^\s*endsolid\b[^\n]*$\n?",
    re.MULTILINE,
)
_FACET_RE = re.compile(rb"facet\s+normal\s+(\S+)\s+(\S+)\s+(\S+)[\s\S]*?endfacet",
                        re.MULTILINE)
_VERTEX_RE = re.compile(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)")


def parse_stl_triangles(stl_bytes):
    """Return list of (name, tri_array (n,3,3), normals (n,3))."""
    out = []
    for m in _SOLID_BLOCK_RE.finditer(stl_bytes):
        name = m.group(1).decode("ascii", errors="replace")
        body = m.group(2)
        tris = []
        normals = []
        for fm in _FACET_RE.finditer(body):
            nx, ny, nz = float(fm.group(1)), float(fm.group(2)), float(fm.group(3))
            verts = _VERTEX_RE.findall(fm.group(0))
            if len(verts) != 3:
                continue
            try:
                pts = [[float(v[0]), float(v[1]), float(v[2])] for v in verts]
            except ValueError:
                continue
            tris.append(pts)
            normals.append([nx, ny, nz])
        out.append((name, np.array(tris), np.array(normals)))
    return out


def snap_vertices(per_body, tol):
    """For each unique vertex (rounded to tol), pick canonical
    position (mean of all coincident copies) and replace."""
    # Concat all vertices
    all_verts = np.concatenate([b[1].reshape(-1, 3) for b in per_body], axis=0)
    n = len(all_verts)
    print(f"  total vertices: {n:,}", flush=True)

    # Round each coord to nearest tol-multiple → hashable bucket
    if tol <= 0:
        return per_body  # no-op
    rounded = np.round(all_verts / tol).astype(np.int64)
    # Build bucket→canonical_position map
    # Use lex sort + groupby
    bucket_keys = np.empty(n, dtype=object)
    for i in range(n):
        bucket_keys[i] = (int(rounded[i, 0]), int(rounded[i, 1]), int(rounded[i, 2]))

    canonical = {}
    for i in range(n):
        k = bucket_keys[i]
        if k not in canonical:
            canonical[k] = all_verts[i]
        # Else: leave canonical = first-seen position

    print(f"  unique buckets at tol={tol}: {len(canonical):,}  ({n/len(canonical):.2f}× compression)", flush=True)

    # Replace each vertex with canonical
    snapped_per_body = []
    cursor = 0
    for name, tris, normals in per_body:
        n_tri = tris.shape[0]
        snapped = np.empty_like(tris)
        for j in range(n_tri):
            for k in range(3):
                vi = cursor + j * 3 + k
                snapped[j, k] = canonical[bucket_keys[vi]]
        cursor += n_tri * 3
        snapped_per_body.append((name, snapped, normals))
    return snapped_per_body


def emit_combined(per_body, out_path):
    """Emit one multi-solid ASCII STL block per body."""
    lines = []
    for name, tris, normals in per_body:
        lines.append(f"solid {name}")
        for j in range(tris.shape[0]):
            nx, ny, nz = normals[j]
            lines.append(f"  facet normal {nx:.6e} {ny:.6e} {nz:.6e}")
            lines.append("    outer loop")
            for k in range(3):
                x, y, z = tris[j, k]
                lines.append(f"      vertex {x:.6e} {y:.6e} {z:.6e}")
            lines.append("    endloop")
            lines.append("  endfacet")
        lines.append(f"endsolid {name}")
    Path(out_path).write_text("\n".join(lines) + "\n")


def gmsh_verify(stl_path, label, timeout_s=90):
    """Feed STL through gmsh HXT, capture PLC error or success."""
    code = f"""
import math, time, gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setNumber("General.Verbosity", 2)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Algorithm3D", 10)
gmsh.option.setNumber("Geometry.Tolerance", 1e-12)
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 200_000)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 500_000)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

t0 = time.monotonic()
def t(): return f"[{{time.monotonic()-t0:6.2f}}s]"

gmsh.merge({stl_path!r})
print(f"{{t()}} merge done", flush=True)
gmsh.model.mesh.classifySurfaces(
    angle=180.0*math.pi/180.0, boundary=False, forReparametrization=False,
    curveAngle=180.0*math.pi/180.0,
)
print(f"{{t()}} classify done — ents: {{len(gmsh.model.getEntities(2))}}", flush=True)
ent_2d = gmsh.model.getEntities(2)
loop = gmsh.model.geo.addSurfaceLoop([tag for _, tag in ent_2d])
gmsh.model.geo.addVolume([loop])
gmsh.model.geo.synchronize()
try:
    gmsh.model.mesh.generate(3)
    _, _, e3 = gmsh.model.mesh.getElements(dim=3)
    n = sum(len(tags) for tags in e3)
    print(f"{{t()}} HXT OK — {{n:,}} cells", flush=True)
    print(f"VERDICT_{label}=CELLS_{{n}}", flush=True)
except Exception as exc:
    print(f"{{t()}} HXT FAILED: {{exc!r}}", flush=True)
    print(f"VERDICT_{label}=FAIL", flush=True)
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


# Load per-body STLs from session 2 output dir
import json
manifest = json.loads((STL_DIR / "manifest.json").read_text())
per_body = []
for body in manifest["bodies"]:
    raw = Path(body["path"]).read_bytes()
    parsed = parse_stl_triangles(raw)
    if parsed:
        # rewrite solid name to stem (matching combine_per_body_stls behavior)
        _, tris, normals = parsed[0]
        per_body.append((body["stem"], tris, normals))
print(f"loaded {len(per_body)} bodies", flush=True)

# Try several snap tolerances
for tol in [0.0, 1e-3, 1e-1, 1.0, 10.0]:
    print(f"\n=== snap_tol={tol} ===", flush=True)
    snapped = snap_vertices(per_body, tol)
    out = f"/tmp/case003_session8_snap_tol_{tol}.stl"
    emit_combined(snapped, out)
    sz = Path(out).stat().st_size
    print(f"  emitted {out} ({sz:,} bytes)", flush=True)
    gmsh_verify(out, f"tol_{tol}", timeout_s=90)

"""Session 7 probe1: count degenerate triangles in each per-body STL.

If per-body STLs already carry degenerates → filter belongs in
step_to_per_body_stl (sidecar) or as a post-emit cleanup loop.
If per-body are clean but combined is not → filter belongs in
combine_per_body_stls (would be surprising given combine doesn't
modify triangles).
"""
import time, sys, json
from pathlib import Path

STL_DIR = Path("/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2")

t0 = time.monotonic()
def t(): return f"[{time.monotonic()-t0:6.2f}s]"

import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.option.setNumber("General.Verbosity", 2)  # show Warning lines

manifest = json.loads((STL_DIR / "manifest.json").read_text())
print(f"{t()} manifest bodies: {len(manifest['bodies'])}", flush=True)

# Per-body probe: merge each one separately, capture gmsh log to see degenerates
total_degen = 0
for body in manifest["bodies"]:
    path = Path(body["path"])
    stem = body["stem"]
    # Fresh model for each body
    gmsh.model.add(stem)
    gmsh.model.setCurrent(stem)
    # Capture gmsh log for this merge
    gmsh.logger.start()
    gmsh.merge(str(path))
    log = gmsh.logger.get()
    gmsh.logger.stop()

    # Triangle count
    ent_2d = gmsh.model.getEntities(2)
    tri_count = 0
    for d, tag in ent_2d:
        _, tags_list, _ = gmsh.model.mesh.getElements(dim=2, tag=tag)
        tri_count += sum(len(tags) for tags in tags_list)

    # Parse "N degenerate" from log
    degen = 0
    for line in log:
        if "degenerate" in line.lower():
            # format: "Warning: 0 duplicate/N degenerate triangles in STL file"
            parts = line.split("/")
            if len(parts) >= 2:
                try:
                    degen = int(parts[1].split()[0])
                except (ValueError, IndexError):
                    pass
    total_degen += degen
    print(f"{t()} {stem:30s} tris={tri_count:7d}  degen={degen}", flush=True)

print(f"{t()} TOTAL degen across per-body STLs: {total_degen}", flush=True)
print(f"{t()} combined STL reported: 9356 — accounting:", flush=True)
print(f"{t()}   if per-body sum == combined → degenerates are FreeCAD-emit-time", flush=True)
print(f"{t()}   if per-body sum < combined  → combine step introduces them (unlikely)", flush=True)

gmsh.finalize()
print(f"{t()} probe1 done", flush=True)

"""Session 7 probe2: test the "degenerates emerge from vertex dedup"
hypothesis.

If true: disabling gmsh's STL vertex dedup should drop degenerate
count from 9356 to ~8 (matching per-body sum).

Options to test:
  Geometry.Tolerance — geometric tolerance for snapping (default 1e-8)
  Mesh.StlRemoveDuplicateTriangles — dedupe exact-duplicate triangles
  Mesh.StlOneSolidPerSurface — one solid → one entity (default 1)

We can't directly disable cross-solid vertex dedup, but we can:
  (a) read combined STL, examine raw vertex coords at shared edges
  (b) set Geometry.Tolerance to a smaller value and see if degenerate
      count changes
"""
import time, sys, math
from pathlib import Path

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"

t0 = time.monotonic()
def t(): return f"[{time.monotonic()-t0:6.2f}s]"


def merge_with_tolerance(tolerance):
    """Merge combined STL with a given Geometry.Tolerance; capture
    gmsh's degenerate count."""
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.Verbosity", 2)
    gmsh.option.setNumber("Geometry.Tolerance", tolerance)
    gmsh.logger.start()
    gmsh.merge(STL)
    log = gmsh.logger.get()
    gmsh.logger.stop()
    degen = 0
    for line in log:
        if "degenerate" in line.lower():
            parts = line.split("/")
            if len(parts) >= 2:
                try:
                    degen = int(parts[1].split()[0])
                except (ValueError, IndexError):
                    pass
    ent_2d = gmsh.model.getEntities(2)
    total_tri = 0
    for d, tag in ent_2d:
        _, tags_list, _ = gmsh.model.mesh.getElements(dim=2, tag=tag)
        total_tri += sum(len(tags) for tags in tags_list)
    gmsh.finalize()
    return total_tri, degen


print(f"{t()} probe2 start — testing Geometry.Tolerance sensitivity", flush=True)
for tol in [1e-8, 1e-12, 1e-3, 1.0, 1e3]:
    tri, degen = merge_with_tolerance(tol)
    print(f"{t()} Geometry.Tolerance={tol:8.0e}  tris={tri:7d}  degen={degen}", flush=True)

print(f"{t()} probe2 done", flush=True)

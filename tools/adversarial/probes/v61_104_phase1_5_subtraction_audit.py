"""Probe — DEC-V61-104 Phase 1.5 obstacle-subtraction audit.

Empirically tests whether gmsh's geo-kernel ``addVolume`` actually
subtracts an interior obstacle from the fluid domain on the iter01
thin-blade-in-plenum STL across mesh densities ``lc ∈ {0.0085, 0.005,
0.003, 0.002, 0.001}`` (production beginner-mode through fine).

Counts BOTH total tetrahedra AND tetrahedra whose centroid falls inside
the blade body's bounding box. If gmsh subtracts correctly, the
inside-blade-bbox count is 0 across all densities.

Result (2026-05-01): inside_blade_bbox=0 for both single-loop and
multi-loop addVolume across all densities. **gmsh single-loop
addVolume already correctly treats internal shells as obstacles** —
contradicts the previous Phase 1 partial-findings doc claim.

Run: ``python tools/adversarial/probes/v61_104_phase1_5_subtraction_audit.py``
"""

from __future__ import annotations
import math, sys
from pathlib import Path
import gmsh

ITER01_STL = Path("/Users/Zhuanz/Desktop/cfd-harness-unified/tools/adversarial/cases/iter01/geometry.stl")


def run(label, lc, multi_body):
    sys.path.insert(0, str(Path("/Users/Zhuanz/Desktop/cfd-harness-unified")))
    from ui.backend.services.meshing_gmsh.topology import partition_surfaces_by_body, _body_bbox

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        if lc > 0:
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc / 100.0)
        gmsh.merge(str(ITER01_STL))
        gmsh.model.mesh.classifySurfaces(
            angle=40.0 * math.pi / 180.0,
            boundary=True,
            forReparametrization=True,
            curveAngle=180.0 * math.pi / 180.0,
        )
        gmsh.model.mesh.createGeometry()
        surfaces = gmsh.model.getEntities(dim=2)
        bodies = partition_surfaces_by_body(gmsh, surfaces)

        if multi_body and len(bodies) > 1:
            outer_loop = gmsh.model.geo.addSurfaceLoop(bodies[0])
            inner_loops = [gmsh.model.geo.addSurfaceLoop(b) for b in bodies[1:]]
            gmsh.model.geo.addVolume([outer_loop] + [-l for l in inner_loops])
        else:
            loop = gmsh.model.geo.addSurfaceLoop([s[1] for s in surfaces])
            gmsh.model.geo.addVolume([loop])
        gmsh.model.geo.synchronize()
        gmsh.model.mesh.generate(3)

        elem_types, elem_tags, node_tags = gmsh.model.mesh.getElements(dim=3)
        total = sum(len(elem_tags[i]) for i, et in enumerate(elem_types) if et == 4)

        # Use blade bbox from smaller body
        from ui.backend.services.meshing_gmsh.topology import _bbox_volume
        bboxes = [_body_bbox(gmsh, b) for b in bodies]
        sizes = [(_bbox_volume(b), idx) for idx, b in enumerate(bboxes)]
        sizes.sort()
        blade_idx = sizes[0][1]
        xmin, ymin, zmin, xmax, ymax, zmax = bboxes[blade_idx]
        inside = 0
        for et_idx, et in enumerate(elem_types):
            if et != 4:
                continue
            nt = node_tags[et_idx]
            for tet_i in range(len(nt) // 4):
                cx = cy = cz = 0.0
                for nid in nt[tet_i * 4 : tet_i * 4 + 4]:
                    c, _, _, _ = gmsh.model.mesh.getNode(int(nid))
                    cx += c[0]; cy += c[1]; cz += c[2]
                cx /= 4.0; cy /= 4.0; cz /= 4.0
                if xmin < cx < xmax and ymin < cy < ymax and zmin < cz < zmax:
                    inside += 1
        print(f"{label:<60s} total={total:>6d} inside_blade_bbox={inside:>4d}")
    finally:
        gmsh.finalize()


def main():
    # iter01 bbox diagonal ≈ sqrt(0.24^2 + 0.08^2 + 0.04^2) ≈ 0.256
    # Production beginner mode: lc = diag/30 ≈ 0.0085
    # Production power mode: lc = diag/60 ≈ 0.0043
    # iter01 produces ~7159 cells in prod, so let's match
    for lc in [0.0085, 0.005, 0.003, 0.002, 0.001]:
        run(f"single-loop lc={lc}", lc, multi_body=False)
        run(f"multi-loop  lc={lc}", lc, multi_body=True)


if __name__ == "__main__":
    main()

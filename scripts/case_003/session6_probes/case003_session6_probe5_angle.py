"""Session 6 segment 1 probe5: classifySurfaces angle parameter tuning.

If angle=180° (no actual splitting — all triangles "smooth" relative to
threshold) completes fast on 384k facets, F-NEW-22 has a minimum-LOC fix
that doesn't break byte-identity (we'd select angle conditionally).

Variants:
  A180: classifySurfaces(angle=180°) — no splitting
  A90 : classifySurfaces(angle=90°)  — coarse splitting
  A40 : classifySurfaces(angle=40°)  — baseline (M6's current value), confirms hang
  A180-fast: A180 + Mesh.MeshSizeFromCurvature=0 + boundary=False
"""
import time, sys, math

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"

def run_variant(name, angle_deg, extra_opts=None, boundary=True, fr=True):
    t0 = time.monotonic()
    def t(): return f"[{time.monotonic()-t0:7.2f}s]"
    print(f"\n=== {name}  angle={angle_deg}°  boundary={boundary}  forReparametrization={fr} ===", flush=True)
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.Verbosity", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)
    if extra_opts:
        for k, v in extra_opts.items():
            gmsh.option.setNumber(k, v)
    gmsh.merge(STL)
    print(f"{t()} merge done", flush=True)
    try:
        gmsh.model.mesh.classifySurfaces(
            angle=angle_deg * math.pi / 180.0,
            boundary=boundary,
            forReparametrization=fr,
            curveAngle=180.0 * math.pi / 180.0,
        )
        print(f"{t()} classifySurfaces DONE — ents dim=2: {len(gmsh.model.getEntities(2))}", flush=True)
        try:
            gmsh.model.mesh.createGeometry()
            print(f"{t()} createGeometry DONE — parametric dim=2 ents: {len(gmsh.model.getEntities(2))}", flush=True)
        except Exception as exc:
            print(f"{t()} createGeometry FAILED: {exc!r}", flush=True)
    except Exception as exc:
        print(f"{t()} classifySurfaces FAILED: {exc!r}", flush=True)
    gmsh.finalize()
    print(f"{t()} {name} done", flush=True)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "A180"
    if arg == "A180":
        run_variant("A180", 180.0)
    elif arg == "A90":
        run_variant("A90", 90.0)
    elif arg == "A40":
        run_variant("A40", 40.0)
    elif arg == "A180-fast":
        run_variant("A180-fast", 180.0,
                    extra_opts={"Mesh.MeshSizeFromCurvature": 0,
                                "Mesh.AngleSmoothNormals": 30},
                    boundary=False, fr=False)
    else:
        print(f"unknown variant {arg}")

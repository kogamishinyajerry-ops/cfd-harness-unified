"""Session 6 segment 1 probe6: classifySurfaces fast-mode +
skip createGeometry + try various volume-creation paths.

Variants:
  F1: fast-classify + addDiscreteEntity(3, boundary=ents) + generate(3)
  F2: fast-classify + addSurfaceLoop + addVolume + generate(3)
       (M6 path minus createGeometry)
  F3: fast-classify + HXT (Algorithm3D=10) + addDiscreteEntity(3)
  F4: fast-classify + HXT direct (no addDiscreteEntity)
"""
import time, sys, math

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"


def fast_classify(gmsh, t):
    gmsh.model.mesh.classifySurfaces(
        angle=180.0 * math.pi / 180.0,
        boundary=False,
        forReparametrization=False,
        curveAngle=180.0 * math.pi / 180.0,
    )
    print(f"{t()} fast-classify done — dim=2 ents: {len(gmsh.model.getEntities(2))}", flush=True)


def run_variant(name, algo3d, do_after_classify):
    t0 = time.monotonic()
    def t(): return f"[{time.monotonic()-t0:7.2f}s]"
    print(f"\n=== {name}  Algorithm3D={algo3d} ===", flush=True)
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.Verbosity", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.Algorithm3D", algo3d)
    gmsh.merge(STL)
    print(f"{t()} merge done", flush=True)
    try:
        fast_classify(gmsh, t)
        do_after_classify(gmsh, t)
        gmsh.model.geo.synchronize()
        print(f"{t()} synchronize done", flush=True)
        print(f"{t()} calling generate(3)", flush=True)
        gmsh.model.mesh.generate(3)
        _, _, e3 = gmsh.model.mesh.getElements(dim=3)
        n = sum(len(tags) for tags in e3)
        print(f"{t()} generate(3) OK — {n:,} 3D cells", flush=True)
    except Exception as exc:
        print(f"{t()} VARIANT {name} FAILED: {exc!r}", flush=True)
    gmsh.finalize()
    print(f"{t()} {name} done", flush=True)


def f1_addde(gmsh, t):
    ent_2d = gmsh.model.getEntities(2)
    vol = gmsh.model.addDiscreteEntity(3, -1, [tt for _, tt in ent_2d])
    print(f"{t()} addDiscreteEntity(3) = {vol}", flush=True)


def f2_loop_vol(gmsh, t):
    ent_2d = gmsh.model.getEntities(2)
    try:
        loop = gmsh.model.geo.addSurfaceLoop([tt for _, tt in ent_2d])
        print(f"{t()} addSurfaceLoop = {loop}", flush=True)
        vol = gmsh.model.geo.addVolume([loop])
        print(f"{t()} addVolume = {vol}", flush=True)
    except Exception as exc:
        print(f"{t()} geo path failed: {exc!r}", flush=True)


def f4_nothing(gmsh, t):
    print(f"{t()} F4: no addDiscreteEntity, just HXT direct on classified ents", flush=True)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "F1"
    if arg == "F1":
        run_variant("F1", 1, f1_addde)
    elif arg == "F2":
        run_variant("F2", 1, f2_loop_vol)
    elif arg == "F3":
        run_variant("F3", 10, f1_addde)
    elif arg == "F4":
        run_variant("F4", 10, f4_nothing)

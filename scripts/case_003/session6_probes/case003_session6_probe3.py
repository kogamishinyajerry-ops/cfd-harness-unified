"""Session 6 segment 1 probe3: try sequences to make the
discrete-surface mesh "bind" to the discrete volume so generate(3)
sees the triangles as the volume's boundary.

Tries 4 variants in sequence (separate gmsh sessions per variant):
  V1: gmsh.model.mesh.createTopology() before addDiscreteEntity(3)
  V2: gmsh.model.mesh.createTopology() AFTER addDiscreteEntity(3)
  V3: removeDuplicateNodes + addDiscreteEntity(3) + generate(3)
  V4: addDiscreteEntity(3) + reclassifyNodes + generate(3)
"""
import time, sys

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"

def run_variant(name, do):
    t0 = time.monotonic()
    def t(): return f"[{time.monotonic()-t0:7.2f}s]"
    print(f"\n=== {name} ===", flush=True)
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.Verbosity", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)
    gmsh.merge(STL)
    print(f"{t()} merge done", flush=True)
    try:
        do(gmsh, t)
        # final attempt at generate(3)
        print(f"{t()} calling generate(3)", flush=True)
        gmsh.model.mesh.generate(3)
        _, _, e3 = gmsh.model.mesh.getElements(dim=3)
        n = sum(len(tags) for tags in e3)
        print(f"{t()} generate(3) OK — {n:,} 3D cells", flush=True)
    except Exception as exc:
        print(f"{t()} VARIANT {name} FAILED: {exc!r}", flush=True)
    gmsh.finalize()
    print(f"{t()} {name} done\n", flush=True)


def v1(gmsh, t):
    print(f"{t()} createTopology() before addDiscreteEntity(3)", flush=True)
    gmsh.model.mesh.createTopology()
    print(f"{t()} createTopology done — dim=2:{len(gmsh.model.getEntities(2))} dim=3:{len(gmsh.model.getEntities(3))}", flush=True)
    ent_2d = gmsh.model.getEntities(2)
    vol = gmsh.model.addDiscreteEntity(3, -1, [tt for _, tt in ent_2d])
    print(f"{t()} addDiscreteEntity(3) returned {vol}", flush=True)
    gmsh.model.geo.synchronize()


def v2(gmsh, t):
    print(f"{t()} addDiscreteEntity(3) before createTopology()", flush=True)
    ent_2d = gmsh.model.getEntities(2)
    vol = gmsh.model.addDiscreteEntity(3, -1, [tt for _, tt in ent_2d])
    print(f"{t()} addDiscreteEntity(3) returned {vol}", flush=True)
    gmsh.model.mesh.createTopology()
    print(f"{t()} createTopology done", flush=True)
    gmsh.model.geo.synchronize()


def v3(gmsh, t):
    print(f"{t()} removeDuplicateNodes + addDiscreteEntity(3)", flush=True)
    gmsh.model.mesh.removeDuplicateNodes()
    print(f"{t()} removeDuplicateNodes done", flush=True)
    ent_2d = gmsh.model.getEntities(2)
    vol = gmsh.model.addDiscreteEntity(3, -1, [tt for _, tt in ent_2d])
    print(f"{t()} addDiscreteEntity(3) returned {vol}", flush=True)
    gmsh.model.geo.synchronize()


def v4(gmsh, t):
    print(f"{t()} addDiscreteEntity(3) + reclassifyNodes", flush=True)
    ent_2d = gmsh.model.getEntities(2)
    vol = gmsh.model.addDiscreteEntity(3, -1, [tt for _, tt in ent_2d])
    print(f"{t()} addDiscreteEntity(3) returned {vol}", flush=True)
    try:
        gmsh.model.mesh.reclassifyNodes()
        print(f"{t()} reclassifyNodes done", flush=True)
    except Exception as exc:
        print(f"{t()} reclassifyNodes failed: {exc!r}", flush=True)
    gmsh.model.geo.synchronize()


# Run each variant in a separate Python subprocess to isolate gmsh state.
# Actually keep simple — gmsh.finalize between variants should be enough.

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    funcs = {"v1": v1, "v2": v2, "v3": v3, "v4": v4}
    if arg in funcs:
        run_variant(arg, funcs[arg])
    else:
        for name, fn in funcs.items():
            run_variant(name, fn)

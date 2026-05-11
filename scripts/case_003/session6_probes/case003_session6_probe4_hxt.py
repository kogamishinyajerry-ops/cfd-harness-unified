"""Session 6 segment 1 probe4: HXT algorithm — gmsh's modern
"mesh-the-inside-of-an-STL" 3D mesher. Algorithm3D = 10 (HXT).

Tries 3 variants in separate subprocesses for clean state:
  H1: gmsh.merge + HXT + generate(3) — no addDiscreteEntity, no
      classifySurfaces. Pure "give me cells inside this surface mesh."
  H2: gmsh.merge + addDiscreteEntity(3) + HXT + generate(3)
  H3: gmsh.merge + createTopology + addDiscreteEntity(3) + HXT +
      generate(3)
"""
import time, sys

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"

def run_variant(name, do):
    t0 = time.monotonic()
    def t(): return f"[{time.monotonic()-t0:7.2f}s]"
    print(f"\n=== {name} (HXT, Algorithm3D=10) ===", flush=True)
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.Verbosity", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)  # HXT
    gmsh.merge(STL)
    print(f"{t()} merge done — dim=2 ents: {len(gmsh.model.getEntities(2))}", flush=True)
    try:
        do(gmsh, t)
        print(f"{t()} calling generate(3) with HXT", flush=True)
        gmsh.model.mesh.generate(3)
        _, _, e3 = gmsh.model.mesh.getElements(dim=3)
        n = sum(len(tags) for tags in e3)
        print(f"{t()} generate(3) OK — {n:,} 3D cells", flush=True)
    except Exception as exc:
        print(f"{t()} VARIANT {name} FAILED: {exc!r}", flush=True)
    gmsh.finalize()
    print(f"{t()} {name} done\n", flush=True)


def h1(gmsh, t):
    print(f"{t()} H1: HXT direct — no addDiscreteEntity, no createTopology", flush=True)
    gmsh.model.geo.synchronize()


def h2(gmsh, t):
    print(f"{t()} H2: addDiscreteEntity(3) + HXT", flush=True)
    ent_2d = gmsh.model.getEntities(2)
    vol = gmsh.model.addDiscreteEntity(3, -1, [tt for _, tt in ent_2d])
    print(f"{t()} addDiscreteEntity(3) returned {vol}", flush=True)
    gmsh.model.geo.synchronize()


def h3(gmsh, t):
    print(f"{t()} H3: createTopology + addDiscreteEntity(3) + HXT", flush=True)
    gmsh.model.mesh.createTopology()
    print(f"{t()} createTopology done — dim=2:{len(gmsh.model.getEntities(2))} dim=3:{len(gmsh.model.getEntities(3))}", flush=True)
    ent_2d = gmsh.model.getEntities(2)
    vol = gmsh.model.addDiscreteEntity(3, -1, [tt for _, tt in ent_2d])
    print(f"{t()} addDiscreteEntity(3) returned {vol}", flush=True)
    gmsh.model.geo.synchronize()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    funcs = {"h1": h1, "h2": h2, "h3": h3}
    if arg in funcs:
        run_variant(arg, funcs[arg])
    else:
        for name, fn in funcs.items():
            run_variant(name, fn)

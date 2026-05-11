"""Session 6 segment 1 probe: what does gmsh see AFTER merge but
BEFORE classifySurfaces?

Goal — answer 3 questions:
  Q1: how many dim=2 discrete entities does merge create on a 10-named-
      solid STL? Are they pre-partitioned by solid block?
  Q2: do any physical groups exist automatically? Any dim=3?
  Q3: per-entity triangle counts — confirm the 10-solid hypothesis.

NO classifySurfaces call. NO createGeometry. NO generate(3). Pure
introspection — should complete in seconds.
"""
import sys
import time

STL = "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/combined_session_4.stl"

t0 = time.monotonic()
def t(): return f"[{time.monotonic()-t0:6.2f}s]"

print(f"{t()} probe1 start")
import gmsh
print(f"{t()} gmsh import done — version {gmsh.__version__ if hasattr(gmsh, '__version__') else 'n/a'}")

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.option.setNumber("General.Verbosity", 1)
print(f"{t()} gmsh init done")

gmsh.merge(STL)
print(f"{t()} gmsh.merge done")

# === Q1: entities after merge ===
ent_0d = gmsh.model.getEntities(dim=0)
ent_1d = gmsh.model.getEntities(dim=1)
ent_2d = gmsh.model.getEntities(dim=2)
ent_3d = gmsh.model.getEntities(dim=3)
print(f"{t()} entities — dim=0:{len(ent_0d)}  dim=1:{len(ent_1d)}  dim=2:{len(ent_2d)}  dim=3:{len(ent_3d)}")

# === Q2: physical groups + entity types ===
pg = gmsh.model.getPhysicalGroups()
print(f"{t()} physical groups (all dims): {len(pg)} — {pg[:10]}")

# Check entity type — discrete vs parametric
for d, tag in ent_2d[:5]:
    typ = gmsh.model.getType(d, tag)
    print(f"{t()}   dim=2 tag={tag}  type={typ}")

# === Q3: per-entity triangle counts ===
total_tri = 0
print(f"{t()} per dim=2 entity triangle counts:")
for d, tag in ent_2d:
    try:
        elem_types, elem_tags_list, _ = gmsh.model.mesh.getElements(dim=2, tag=tag)
    except Exception as exc:
        print(f"{t()}   tag={tag}  ERROR {exc!r}")
        continue
    n = sum(len(tags) for tags in elem_tags_list)
    total_tri += n
    print(f"{t()}   tag={tag:4d}  n_tris={n:7d}  elem_types={list(elem_types)}")
print(f"{t()} TOTAL triangles across dim=2 entities: {total_tri:,}")

# === Q4: nodes ===
node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
print(f"{t()} total nodes: {len(node_tags):,}")

# === Q5: try addDiscreteEntity for volume ===
print(f"{t()} attempting addDiscreteEntity(dim=3, ...) experiment...")
try:
    # Get the boundary of all surfaces (just gather tags, don't try to
    # synthesize a topologically valid surface loop)
    vol_tag = gmsh.model.addDiscreteEntity(dim=3, tag=-1, boundary=[t for _, t in ent_2d])
    print(f"{t()}   addDiscreteEntity(dim=3) returned tag={vol_tag}")
    ent_3d_after = gmsh.model.getEntities(dim=3)
    print(f"{t()}   dim=3 entities after: {len(ent_3d_after)} — {ent_3d_after}")
except Exception as exc:
    print(f"{t()}   addDiscreteEntity FAILED: {exc!r}")

gmsh.finalize()
print(f"{t()} probe1 done")

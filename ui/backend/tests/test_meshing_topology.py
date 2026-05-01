"""Unit tests for ``ui.backend.services.meshing_gmsh.topology`` (DEC-V61-104).

Two layers:
  - Pure-logic tests on the partitioner with a fake gmsh stub (no
    real gmsh load). Cheap and deterministic. Covers union-find,
    bbox-volume sorting, single-body fall-through, and the
    TopologyPartitionError disconnected-exterior-shells guard.
  - Real-gmsh integration tests on the cube-in-cube STL fixture:
    (a) classifySurfaces + partitioner returns 2 bodies with outer
    first, and (b) the gmsh_runner multi-loop addVolume call site
    accepts the negated inner loop and runs generate(3) without
    error. Note: Phase 1 ships the scaffolding; gmsh's geo-kernel
    addVolume hole subtraction is empirically a no-op on STL-imported
    surfaces, so cell counts are NOT asserted to drop here. Phase 1.5
    will add OCC-kernel cut or surface-orientation reversal to
    actually subtract the obstacle volume; cell-count regression
    assertions belong in that follow-up.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
import trimesh

from ui.backend.services.meshing_gmsh.topology import (
    TopologyPartitionError,
    _bbox_contains,
    _bbox_volume,
    _body_bbox,
    partition_surfaces_by_body,
)


# ===== Fake gmsh stub for pure-logic tests ==============================


class _FakeGmsh:
    """Minimal gmsh interface for partitioner unit tests. Surfaces and
    edges are configured at construction time; the partitioner only
    needs ``getBoundary`` (for connectivity) and ``mesh.getElements`` /
    ``mesh.getNode`` (for bbox computation)."""

    def __init__(
        self,
        surface_to_edges: dict[int, list[int]],
        surface_to_nodes: dict[int, list[tuple[float, float, float]]],
    ):
        self._surface_to_edges = surface_to_edges
        self._surface_to_nodes = surface_to_nodes
        # Build a node-id index so ``getNode`` returns a position. Each
        # (surface, vertex) pair gets a unique node id.
        self._node_coords: dict[int, tuple[float, float, float]] = {}
        self._surface_node_ids: dict[int, list[int]] = {}
        next_id = 1
        for s_tag, coords_list in surface_to_nodes.items():
            ids: list[int] = []
            for coord in coords_list:
                self._node_coords[next_id] = coord
                ids.append(next_id)
                next_id += 1
            self._surface_node_ids[s_tag] = ids

        # Compose the namespace so callers can do gmsh.model.<...>.
        outer = self

        class _Mesh:
            def getElements(_self, dim: int, tag: int):
                ids = outer._surface_node_ids.get(int(tag), [])
                if not ids:
                    return ([], [], [])
                # Triangle elements: flat node array of length 3 * n_tri.
                # For test purposes we treat each consecutive triple as
                # one triangle.
                return ([2], [list(range(len(ids) // 3))], [ids])

            def getNode(_self, nid: int):
                c = outer._node_coords.get(int(nid))
                if c is None:
                    raise ValueError(f"unknown node {nid}")
                return (list(c), [], 0, 0)

        class _Model:
            def __init__(_self):
                _self.mesh = _Mesh()

            def getBoundary(_self, entities, oriented=False):
                out = []
                for _dim, tag in entities:
                    for e in outer._surface_to_edges.get(int(tag), []):
                        out.append((1, int(e)))
                return out

        self.model = _Model()


# ===== Pure-logic tests =====================================================


def test_partition_empty_returns_empty():
    fake = _FakeGmsh({}, {})
    assert partition_surfaces_by_body(fake, []) == []


def test_partition_single_surface_returns_self():
    fake = _FakeGmsh({1: [10]}, {1: [(0, 0, 0), (1, 0, 0), (0, 1, 0)]})
    result = partition_surfaces_by_body(fake, [(2, 1)])
    assert result == [[1]]


def test_partition_single_body_via_shared_edges():
    """Three surfaces all sharing edges form one body — outputs [[1,2,3]]."""
    fake = _FakeGmsh(
        surface_to_edges={1: [10, 11], 2: [10, 12], 3: [11, 12]},
        surface_to_nodes={
            1: [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
            2: [(1, 0, 0), (1, 1, 0), (0, 1, 0)],
            3: [(0, 0, 1), (1, 0, 1), (0, 1, 1)],
        },
    )
    result = partition_surfaces_by_body(fake, [(2, 1), (2, 2), (2, 3)])
    assert len(result) == 1
    assert sorted(result[0]) == [1, 2, 3]


def test_partition_two_disjoint_bodies_orders_outer_first():
    """Outer body has bbox covering [0,10]^3, inner body is [4,5]^3 —
    outer wins by bbox volume and is returned first."""
    fake = _FakeGmsh(
        surface_to_edges={
            # Outer body surfaces share edges 100, 101.
            1: [100], 2: [100, 101], 3: [101],
            # Inner body surfaces share edges 200, 201.
            4: [200], 5: [200, 201], 6: [201],
        },
        surface_to_nodes={
            1: [(0, 0, 0), (10, 0, 0), (0, 10, 0)],
            2: [(10, 0, 0), (10, 10, 0), (0, 10, 0)],
            3: [(0, 0, 10), (10, 0, 10), (0, 10, 10)],
            4: [(4, 4, 4), (5, 4, 4), (4, 5, 4)],
            5: [(5, 4, 4), (5, 5, 4), (4, 5, 4)],
            6: [(4, 4, 5), (5, 4, 5), (4, 5, 5)],
        },
    )
    result = partition_surfaces_by_body(
        fake, [(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6)]
    )
    assert len(result) == 2
    outer, inner = result
    # Outer body should contain surfaces 1, 2, 3 (the bigger bbox).
    assert sorted(outer) == [1, 2, 3]
    assert sorted(inner) == [4, 5, 6]


def test_partition_three_bodies_inner_order_arbitrary_but_outer_first():
    """Outer + 2 disjoint inner obstacles. Outer is identified by bbox
    volume; inner ordering is implementation-defined. All surfaces
    contribute non-degenerate bboxes (extent > 0 in every axis) so the
    bbox-volume comparison is meaningful."""
    fake = _FakeGmsh(
        surface_to_edges={
            1: [100], 2: [100],   # outer body
            3: [200], 4: [200],   # inner body 1
            5: [300], 6: [300],   # inner body 2
        },
        surface_to_nodes={
            # Outer body: bbox spans (0,0,0) to (20,20,20), volume=8000.
            1: [(0, 0, 0), (20, 0, 0), (0, 20, 0), (0, 0, 20)],
            2: [(20, 20, 20), (0, 20, 20), (20, 0, 20), (20, 20, 0)],
            # Inner body 1: bbox (2,2,2) to (3,3,3), volume=1.
            3: [(2, 2, 2), (3, 2, 2), (2, 3, 2), (2, 2, 3)],
            4: [(3, 3, 3), (2, 3, 3), (3, 2, 3), (3, 3, 2)],
            # Inner body 2: bbox (15,15,15) to (16,16,16), volume=1.
            5: [(15, 15, 15), (16, 15, 15), (15, 16, 15), (15, 15, 16)],
            6: [(16, 16, 16), (15, 16, 16), (16, 15, 16), (16, 16, 15)],
        },
    )
    result = partition_surfaces_by_body(
        fake, [(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6)]
    )
    assert len(result) == 3
    assert sorted(result[0]) == [1, 2]  # outer (8000 >> 1)
    inner_groups = sorted(sorted(g) for g in result[1:])
    assert inner_groups == [[3, 4], [5, 6]]


def test_bbox_volume_degenerate_returns_zero():
    assert _bbox_volume((0, 0, 0, 0, 0, 0)) == 0.0
    assert _bbox_volume((1, 1, 1, 0, 0, 0)) == 0.0  # max < min clamped


def test_bbox_volume_normal_case():
    assert _bbox_volume((0, 0, 0, 2, 3, 4)) == pytest.approx(24.0)


def test_partition_raises_when_inner_bbox_not_contained_in_outer():
    """Two disconnected exterior shells (e.g. two separate cubes that
    do NOT enclose one another) must raise TopologyPartitionError —
    the multi-loop addVolume path would silently corrupt the geometry
    by treating the smaller shell as a hole. Codex post-merge MED
    guard for DEC-V61-104 Phase 1."""
    fake = _FakeGmsh(
        surface_to_edges={
            # Body A (larger): bbox (0,0,0)-(10,10,10), volume=1000.
            1: [100], 2: [100],
            # Body B (smaller): bbox (20,20,20)-(25,25,25), volume=125.
            # Sits OUTSIDE body A entirely — the disconnected-shells case.
            3: [200], 4: [200],
        },
        surface_to_nodes={
            1: [(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)],
            2: [(10, 10, 10), (0, 10, 10), (10, 0, 10), (10, 10, 0)],
            3: [(20, 20, 20), (25, 20, 20), (20, 25, 20), (20, 20, 25)],
            4: [(25, 25, 25), (20, 25, 25), (25, 20, 25), (25, 25, 20)],
        },
    )
    with pytest.raises(TopologyPartitionError) as exc_info:
        partition_surfaces_by_body(
            fake, [(2, 1), (2, 2), (2, 3), (2, 4)]
        )
    assert exc_info.value.failing_check == "topology_disconnected_exterior_shells"


def test_partition_accepts_valid_interior_obstacle_topology():
    """Outer body fully contains inner body — partitioner returns
    [outer, inner] without raising. Sanity-checks the containment
    guard does NOT false-positive on the legitimate topology."""
    fake = _FakeGmsh(
        surface_to_edges={
            1: [100], 2: [100],   # outer
            3: [200], 4: [200],   # inner, sits inside outer
        },
        surface_to_nodes={
            1: [(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)],
            2: [(10, 10, 10), (0, 10, 10), (10, 0, 10), (10, 10, 0)],
            3: [(4, 4, 4), (5, 4, 4), (4, 5, 4), (4, 4, 5)],
            4: [(5, 5, 5), (4, 5, 5), (5, 4, 5), (5, 5, 4)],
        },
    )
    result = partition_surfaces_by_body(
        fake, [(2, 1), (2, 2), (2, 3), (2, 4)]
    )
    assert len(result) == 2
    assert sorted(result[0]) == [1, 2]


def test_bbox_contains_basic_cases():
    outer = (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert _bbox_contains(outer, (1.0, 1.0, 1.0, 9.0, 9.0, 9.0)) is True
    assert _bbox_contains(outer, (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)) is True
    # Inner protrudes past outer max — not contained.
    assert _bbox_contains(outer, (1.0, 1.0, 1.0, 11.0, 9.0, 9.0)) is False
    # Inner sits entirely outside.
    assert _bbox_contains(outer, (20.0, 20.0, 20.0, 25.0, 25.0, 25.0)) is False


def test_bbox_contains_tolerates_floating_point_noise():
    outer = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    # Inner exceeds outer by less than tolerance — should still be True.
    assert _bbox_contains(
        outer, (-1.0e-12, -1.0e-12, -1.0e-12, 1.0 + 1.0e-12, 1.0, 1.0)
    ) is True


def test_body_bbox_handles_no_elements_gracefully():
    """A surface with no mesh elements returns the degenerate (0,0,0,0,0,0)
    bbox so partition doesn't crash."""
    fake = _FakeGmsh({1: []}, {})
    assert _body_bbox(fake, [1]) == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


# ===== Real-gmsh integration test ===========================================
# Skipped if gmsh not importable (e.g. in a pure-stdlib env).


def _skip_if_no_gmsh():
    try:
        import gmsh  # noqa: F401
    except ImportError:
        pytest.skip("gmsh not installed in this env")


def test_cube_in_cube_partitions_into_outer_plus_inner_via_real_gmsh(tmp_path: Path):
    """Real-gmsh partition coverage: load a cube-in-cube STL through
    classifySurfaces + the topology partitioner, assert two bodies are
    returned with the outer (large cube) first.

    Scope: this test ONLY exercises the partitioner against real gmsh
    output — it does NOT call ``addVolume([outer, -inner])`` or
    ``generate(3)``. The addVolume + mesh-generation path is covered
    by ``test_cube_in_cube_multi_loop_addvolume_runs_via_real_gmsh``
    below. DEC-V61-104 Phase 1 happy-path validation; iter01
    thin-blade plenum is a follow-up adversarial validation.
    """
    _skip_if_no_gmsh()
    import gmsh

    # Build the cube-in-cube STL.
    outer = trimesh.creation.box([1.0, 1.0, 1.0])
    inner = trimesh.creation.box([0.2, 0.2, 0.2])
    combined = trimesh.util.concatenate([outer, inner])
    stl_path = tmp_path / "cube_in_cube.stl"
    buf = io.BytesIO()
    combined.export(buf, file_type="stl")
    stl_path.write_bytes(buf.getvalue())

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.merge(str(stl_path))
        gmsh.model.mesh.classifySurfaces(
            angle=40.0 * 3.141592653589793 / 180.0,
            boundary=True,
            forReparametrization=True,
            curveAngle=180.0 * 3.141592653589793 / 180.0,
        )
        gmsh.model.mesh.createGeometry()
        surfaces = gmsh.model.getEntities(dim=2)
        bodies = partition_surfaces_by_body(gmsh, surfaces)
        # Compute bbox volumes against the real gmsh instance to verify
        # the partitioner identified the bigger cube as the outer body.
        outer_volume = _bbox_volume(_body_bbox(gmsh, bodies[0]))
        inner_volume = (
            _bbox_volume(_body_bbox(gmsh, bodies[1]))
            if len(bodies) > 1 else 0.0
        )
    finally:
        gmsh.finalize()

    assert len(bodies) == 2, (
        f"expected 2 bodies for cube-in-cube STL, got {len(bodies)}: {bodies}"
    )
    # Outer should be the size-1.0 cube (bbox ~1.0^3 = 1.0); inner is
    # size-0.2 (bbox ~0.008). Tolerate gmsh's classifySurfaces splitting
    # a cube face into multiple parametric surfaces (so each body may
    # have 1-12 surfaces depending on the angle threshold).
    assert outer_volume > inner_volume * 10.0, (
        f"outer bbox {outer_volume} should dominate inner {inner_volume}"
    )
    assert outer_volume >= 0.5, f"outer body bbox volume {outer_volume} too small"
    assert inner_volume <= 0.05, f"inner body bbox volume {inner_volume} too big"


def test_cube_in_cube_multi_loop_addvolume_runs_via_real_gmsh(tmp_path: Path):
    """Real-gmsh end-to-end coverage for the gmsh_runner multi-loop
    branch added by DEC-V61-104 Phase 1: load a cube-in-cube STL,
    partition, build ``addVolume([outer_loop, -inner_loop])``,
    synchronize, and run ``generate(3)`` without raising. Asserts a
    non-zero tetrahedral cell count.

    Honest scope: Phase 1 documented (see
    ``tools/adversarial/results/iter01_v61_104_phase1_partial_findings.md``)
    that gmsh's geo-kernel does NOT actually subtract the inner volume
    for STL-imported surfaces — cell counts are roughly equivalent to
    the single-loop path. This test guards against the
    ``addVolume([outer, -inner])`` call regressing into a hard error
    (which WOULD silently break the production pipeline), not against
    the no-op subtraction. Phase 1.5 will add OCC-kernel cut and a
    cell-count drop assertion.
    """
    _skip_if_no_gmsh()
    import gmsh

    outer = trimesh.creation.box([1.0, 1.0, 1.0])
    inner = trimesh.creation.box([0.2, 0.2, 0.2])
    combined = trimesh.util.concatenate([outer, inner])
    stl_path = tmp_path / "cube_in_cube.stl"
    buf = io.BytesIO()
    combined.export(buf, file_type="stl")
    stl_path.write_bytes(buf.getvalue())

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.merge(str(stl_path))
        gmsh.model.mesh.classifySurfaces(
            angle=40.0 * 3.141592653589793 / 180.0,
            boundary=True,
            forReparametrization=True,
            curveAngle=180.0 * 3.141592653589793 / 180.0,
        )
        gmsh.model.mesh.createGeometry()
        surfaces = gmsh.model.getEntities(dim=2)
        bodies = partition_surfaces_by_body(gmsh, surfaces)
        assert len(bodies) >= 2, (
            f"cube-in-cube must partition into >=2 bodies, got {bodies}"
        )

        outer_loop = gmsh.model.geo.addSurfaceLoop(bodies[0])
        inner_loops = [
            gmsh.model.geo.addSurfaceLoop(body) for body in bodies[1:]
        ]
        gmsh.model.geo.addVolume([outer_loop] + [-loop for loop in inner_loops])
        gmsh.model.geo.synchronize()
        gmsh.model.mesh.generate(3)

        elem_types, _elem_tags, _node_tags = gmsh.model.mesh.getElements(dim=3)
        total_cells = 0
        for et_idx, et in enumerate(elem_types):
            if et == 4:  # 4-node tetrahedron
                total_cells += len(_elem_tags[et_idx])
    finally:
        gmsh.finalize()

    assert total_cells > 0, (
        "multi-loop addVolume + generate(3) produced zero tetrahedral cells"
    )

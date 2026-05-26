"""
make_turbine_cascade.py
Generate a 2.5D turbine-blade cascade FLUID-DOMAIN ASCII STL for OpenFOAM.
Requires only numpy + scipy (in .venv).

Watertightness strategy:
- All six solids share the SAME 2D vertex coordinates.
- Blade walls and z-face triangulation both use blade polygon vertices verbatim.
- Blade polygon boundary edges must appear exactly once in good_simplices (fluid side).
  We ensure this by: after Delaunay + drop inside-blade triangles, check for any blade
  boundary edge that has count=0, and recover the missing fluid-side triangle by choosing
  the correct neighbor triangle from the full Delaunay.
"""
import numpy as np
from scipy.spatial import Delaunay
from collections import defaultdict, Counter

# Rounds of 1->4 midpoint subdivision applied before writing the STL. Default 1
# (x4 facets) crosses the backend F2-path facet gate (_F2_PATH_FACET_THRESHOLD
# = 10_000). Override with `--subdivide N` (0 = native ~3.7k facets, which takes
# the classifySurfaces path that FAILS on the curved blade).
SUBDIVIDE_ROUNDS = 1


# ── 1. BLADE PROFILE ─────────────────────────────────────────────────────────

def build_blade_polygon(n_half=80, tmax=0.10, phi_LE_deg=15.0, phi_TE_deg=-25.0):
    t = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n_half)))
    phi_LE = np.radians(phi_LE_deg)
    phi_TE = np.radians(phi_TE_deg)
    ds = 1.0 / (n_half - 1)
    xc = np.zeros(n_half); yc = np.zeros(n_half)
    for i in range(1, n_half):
        phi_i    = phi_LE + (phi_TE - phi_LE) * t[i]
        phi_prev = phi_LE + (phi_TE - phi_LE) * t[i - 1]
        phi_mid  = 0.5 * (phi_i + phi_prev)
        xc[i] = xc[i-1] + np.cos(phi_mid) * ds
        yc[i] = yc[i-1] + np.sin(phi_mid) * ds
    xc = (xc - xc[0]) / (xc[-1] - xc[0])
    dxc = np.gradient(xc, t); dyc = np.gradient(yc, t)
    lengths = np.hypot(dxc, dyc)
    nx = -dyc / lengths; ny = dxc / lengths
    def T(x):
        return 5 * tmax * (0.2969*np.sqrt(np.maximum(x, 0)) - 0.1260*x
                           - 0.3516*x**2 + 0.2843*x**3 - 0.1015*x**4)
    half_t = T(xc) / 2.0
    upper = np.column_stack([xc + nx*half_t, yc + ny*half_t])
    lower = np.column_stack([xc - nx*half_t, yc - ny*half_t])
    return np.vstack([upper, lower[-2:0:-1]])


def place_blade(poly, chord_scale=1.0, x_le=0.15, y_center=0.5):
    p = poly * chord_scale
    p[:, 0] += x_le - p[:, 0].min()
    y_mid = 0.5 * (p[:, 1].max() + p[:, 1].min())
    p[:, 1] += y_center - y_mid
    return p


# ── 2. HELPERS ────────────────────────────────────────────────────────────────

def point_in_polygon(pts, poly):
    n = len(poly)
    px = pts[:, 0]; py = pts[:, 1]
    inside = np.zeros(len(pts), dtype=bool)
    xp = poly[:, 0]; yp = poly[:, 1]
    j = n - 1
    for i in range(n):
        xi, yi = xp[i], yp[i]
        xj, yj = xp[j], yp[j]
        cond = ((yi > py) != (yj > py)) & \
               (px < (xj - xi) * (py - yi) / (yj - yi + 1e-300) + xi)
        inside ^= cond
        j = i
    return inside


def tri_normal(v0, v1, v2):
    a = v1 - v0; b = v2 - v0
    n = np.cross(a, b)
    L = np.linalg.norm(n)
    return n / L if L > 1e-14 else np.array([0.0, 0.0, 1.0])


def subdivide_4(triangles, rounds=1):
    """1->4 midpoint subdivision of each triangle, per round.

    WHY THIS EXISTS (genuine engine finding, dogfood 2026-05-26):
    The baseline gmsh path runs ``classifySurfaces(40deg) + createGeometry`` which
    REPARAMETRIZES the surface -- and that fails on a curved blade wall with
    "Invalid boundary mesh / overlapping facets" (PLC segment-facet intersect).
    The backend's F2 path (``gmsh_runner._should_use_f2_path``) skips
    classifySurfaces and uses the discrete entities directly (preserving the
    named-solid->patch mapping 1:1), but it is gated on
    ``_F2_PATH_FACET_THRESHOLD = 10_000`` facets. The native cascade is only
    ~3.7k facets, so we subdivide once (x4 -> ~14.7k) to cross that gate.

    This is a WORKAROUND, not the fix: the real fix is that the F2 path should
    also trigger on surface CURVATURE, not only facet count (see dogfood retro).
    Midpoint subdivision preserves watertightness because a shared edge's
    midpoint is order-independent (0.5*(va+vb) with consistent rounding), so
    neighbouring triangles split their common edge identically.
    """
    for _ in range(rounds):
        out = []
        for v0, v1, v2 in triangles:
            m01 = 0.5 * (v0 + v1)
            m12 = 0.5 * (v1 + v2)
            m20 = 0.5 * (v2 + v0)
            out.extend([
                (v0, m01, m20),
                (m01, v1, m12),
                (m20, m12, v2),
                (m01, m12, m20),
            ])
        triangles = out
    return triangles


def write_solid(f, name, triangles):
    f.write(f"solid {name}\n")
    for v0, v1, v2 in triangles:
        n = tri_normal(v0, v1, v2)
        f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
        f.write("    outer loop\n")
        for v in (v0, v1, v2):
            f.write(f"      vertex {v[0]:.8f} {v[1]:.8f} {v[2]:.8f}\n")
        f.write("    endloop\n")
        f.write("  endfacet\n")
    f.write(f"endsolid {name}\n")


def rect_boundary_pts(xmin, xmax, ymin, ymax, nx=35, ny=15):
    pts = []
    for i in range(nx): pts.append((xmin + i*(xmax-xmin)/nx, ymin))
    for j in range(ny): pts.append((xmax, ymin + j*(ymax-ymin)/ny))
    for i in range(nx): pts.append((xmax - i*(xmax-xmin)/nx, ymax))
    for j in range(ny): pts.append((xmin, ymax - j*(ymax-ymin)/ny))
    return np.array(pts)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    OUT = "/Users/Zhuanz/Desktop/cfd-audit-merge/scripts/dogfood/cases/geometry/turbine_cascade.stl"
    xmin, xmax = -1.0, 2.5
    ymin, ymax =  0.0, 1.0
    zmin, zmax =  0.0, 0.1

    blade_raw = build_blade_polygon(n_half=80)
    final_chord = None; blade_poly = None
    for chord_scale in [1.0, 0.90, 0.80, 0.70, 0.60]:
        bp = place_blade(blade_raw, chord_scale=chord_scale)
        clr_lo = bp[:, 1].min() - ymin
        clr_hi = ymax - bp[:, 1].max()
        if min(clr_lo, clr_hi) >= 0.12:
            final_chord = chord_scale; blade_poly = bp; break

    if blade_poly is None:
        raise RuntimeError("Clearance >= 0.12 not achievable")

    bp = blade_poly
    N_blade = len(bp)
    clr_lo = bp[:, 1].min() - ymin
    clr_hi = ymax - bp[:, 1].max()
    blade_xmin, blade_xmax = bp[:, 0].min(), bp[:, 0].max()
    blade_ymin, blade_ymax = bp[:, 1].min(), bp[:, 1].max()

    print(f"Final chord scale: {final_chord}")
    print(f"Blade x: [{blade_xmin:.4f}, {blade_xmax:.4f}]  y: [{blade_ymin:.4f}, {blade_ymax:.4f}]")
    print(f"Clearance: lower={clr_lo:.4f}, upper={clr_hi:.4f}  (min={min(clr_lo,clr_hi):.4f})")

    # ── Build 2D point pool ───────────────────────────────────────────────────
    rect_pts = rect_boundary_pts(xmin, xmax, ymin, ymax, nx=35, ny=15)
    N_rect = len(rect_pts)

    gx = np.linspace(xmin, xmax, 40)[1:-1]
    gy = np.linspace(ymin, ymax, 20)[1:-1]
    gxx, gyy = np.meshgrid(gx, gy)
    interior_cand = np.column_stack([gxx.ravel(), gyy.ravel()])
    # Exclude interior grid points that are either inside the blade OR within a
    # minimum distance threshold from any blade polygon edge (catches near-boundary cases
    # that fool the ray-casting PIP due to numerical precision at the thin TE).
    inside_mask = point_in_polygon(interior_cand, bp)

    def min_dist_to_poly_edges(pts, poly):
        """Return minimum distance from each point to any edge of the polygon."""
        n = len(poly)
        min_d = np.full(len(pts), np.inf)
        for i in range(n):
            j = (i + 1) % n
            a = poly[i]; b = poly[j]
            ab = b - a; ab_len2 = np.dot(ab, ab)
            if ab_len2 < 1e-14:
                d = np.linalg.norm(pts - a, axis=1)
            else:
                t_proj = np.clip(((pts - a) @ ab) / ab_len2, 0.0, 1.0)
                proj = a + t_proj[:, None] * ab
                d = np.linalg.norm(pts - proj, axis=1)
            min_d = np.minimum(min_d, d)
        return min_d

    min_dist = min_dist_to_poly_edges(interior_cand, bp)
    near_blade = min_dist < 0.025  # exclude points within 0.025 of blade surface
    interior_pts = interior_cand[~inside_mask & ~near_blade]

    all_pts_2d = np.vstack([rect_pts, bp, interior_pts])
    blade_start = N_rect  # blade polygon indices: blade_start .. blade_start+N_blade-1

    # ── Delaunay ──────────────────────────────────────────────────────────────
    tri_obj = Delaunay(all_pts_2d)
    simplices = tri_obj.simplices  # (K,3)

    # Build vertex→triangles map
    vertex_to_tris = defaultdict(set)
    for ti, s in enumerate(simplices):
        for v in s:
            vertex_to_tris[v].add(ti)

    # Build edge→triangles map for full Delaunay
    edge_to_tris_full = defaultdict(list)
    for ti, s in enumerate(simplices):
        for a, b in [(s[0],s[1]), (s[1],s[2]), (s[2],s[0])]:
            edge_to_tris_full[(min(a,b), max(a,b))].append(ti)

    # Classify each triangle: inside blade or outside rect or good
    centroids = all_pts_2d[simplices].mean(axis=1)
    inside_tri_mask = point_in_polygon(centroids, bp)
    out_of_rect_mask = ((centroids[:,0] < xmin) | (centroids[:,0] > xmax) |
                        (centroids[:,1] < ymin) | (centroids[:,1] > ymax))
    drop_mask = inside_tri_mask | out_of_rect_mask  # True = drop

    # Start with good simplices
    good_indices = set(np.where(~drop_mask)[0])

    # ── Extra pass: remove good_indices triangles that have non-blade interior
    #    vertices that actually land inside or ON the blade (PIP numerical edge case).
    #    We scale the blade polygon slightly outward (epsilon expand) to catch near-boundary pts.
    def point_in_polygon_expanded(pts, poly, expand=1e-4):
        """Test inside an epsilon-expanded version of poly (for near-boundary points)."""
        cx = poly[:, 0].mean(); cy = poly[:, 1].mean()
        poly_exp = cx + (1 + expand) * (poly[:, 0] - cx), cy + (1 + expand) * (poly[:, 1] - cy)
        poly_expanded = np.column_stack(poly_exp)
        return point_in_polygon(pts, poly_expanded)

    to_remove = set()
    for ti in list(good_indices):
        s = simplices[ti]
        for v in s:
            if blade_start <= v < blade_start + N_blade:
                continue  # blade boundary vertex — OK
            if v < N_rect:
                continue  # rect boundary vertex — OK
            # Interior vertex: check if it's inside blade (with small expansion)
            pt = all_pts_2d[v].reshape(1, 2)
            if point_in_polygon_expanded(pt, bp)[0]:
                to_remove.add(ti)
                break

    good_indices -= to_remove
    if to_remove:
        print(f"  Removed {len(to_remove)} good_indices tri(s) with blade-interior vertices")

    # ── Recover missing blade boundary edges ─────────────────────────────────
    # For each blade polygon edge, count how many GOOD triangles share it.
    # It must be exactly 1.  If 0, the correct fluid-side triangle was dropped → restore it.
    # If 2, something is wrong but we handle it.
    recovered = 0
    for i in range(N_blade):
        j = (i + 1) % N_blade
        bi = blade_start + i; bj = blade_start + j
        e = (min(bi, bj), max(bi, bj))
        sharing_tris = edge_to_tris_full.get(e, [])
        good_sharing = [ti for ti in sharing_tris if ti in good_indices]
        if len(good_sharing) == 0:
            # Both triangles sharing this edge were dropped; one of them is actually
            # outside the blade (fluid side) — we need to restore it.
            for ti in sharing_tris:
                c = all_pts_2d[simplices[ti]].mean(axis=0)
                # Pick the one whose centroid is NOT inside the blade
                if not point_in_polygon(c.reshape(1,2), bp)[0]:
                    good_indices.add(ti)
                    recovered += 1

    if recovered > 0:
        print(f"  Recovered {recovered} fluid-side triangles at blade boundary")

    good_simplices = simplices[sorted(good_indices)]

    # ── Helper: 3D vertex ─────────────────────────────────────────────────────
    def v3(idx, z):
        return np.array([all_pts_2d[idx, 0], all_pts_2d[idx, 1], z])

    def vp(x, y, z):
        return np.array([x, y, z])

    # ── frontAndBack z-faces ──────────────────────────────────────────────────
    front_back_tris = []
    for s in good_simplices:
        p0, p1, p2 = all_pts_2d[s[0]], all_pts_2d[s[1]], all_pts_2d[s[2]]
        # z=zmin, outward normal = -z
        v0f = vp(p0[0], p0[1], zmin)
        v1f = vp(p1[0], p1[1], zmin)
        v2f = vp(p2[0], p2[1], zmin)
        n_f = tri_normal(v0f, v1f, v2f)
        if n_f[2] > 0:
            front_back_tris.append((v0f, v2f, v1f))
        else:
            front_back_tris.append((v0f, v1f, v2f))
        # z=zmax, outward normal = +z
        v0b = vp(p0[0], p0[1], zmax)
        v1b = vp(p1[0], p1[1], zmax)
        v2b = vp(p2[0], p2[1], zmax)
        n_b = tri_normal(v0b, v1b, v2b)
        if n_b[2] < 0:
            front_back_tris.append((v0b, v2b, v1b))
        else:
            front_back_tris.append((v0b, v1b, v2b))

    # ── Blade vertical walls ──────────────────────────────────────────────────
    cx_blade = bp[:, 0].mean(); cy_blade = bp[:, 1].mean()
    blade_tris = []
    for i in range(N_blade):
        j = (i + 1) % N_blade
        bi = blade_start + i; bj = blade_start + j
        v00 = v3(bi, zmin); v10 = v3(bj, zmin)
        v11 = v3(bj, zmax); v01 = v3(bi, zmax)
        tris = [(v00, v10, v11), (v00, v11, v01)]
        n_t = tri_normal(*tris[0])
        mid = 0.5 * (all_pts_2d[bi] + all_pts_2d[bj])
        to_c = np.array([cx_blade - mid[0], cy_blade - mid[1], 0.0])
        if np.dot(n_t[:2], to_c[:2]) < 0:
            tris = [(v2, v1, v0) for v0, v1, v2 in tris]
        blade_tris.extend(tris)

    # ── Outer box vertical walls (from rect_pts boundary) ────────────────────
    INLET_tris = []; OUTLET_tris = []; PLOWER_tris = []; PUPPER_tris = []
    eps = 1e-6
    for i in range(N_rect):
        j = (i + 1) % N_rect
        ri = rect_pts[i]; rj = rect_pts[j]
        mid_x = 0.5*(ri[0]+rj[0]); mid_y = 0.5*(ri[1]+rj[1])
        v00 = np.array([ri[0], ri[1], zmin])
        v10 = np.array([rj[0], rj[1], zmin])
        v11 = np.array([rj[0], rj[1], zmax])
        v01 = np.array([ri[0], ri[1], zmax])
        if abs(mid_x - xmin) < eps:
            patch = "inlet";  target = np.array([-1.0, 0.0, 0.0])
        elif abs(mid_x - xmax) < eps:
            patch = "outlet"; target = np.array([1.0, 0.0, 0.0])
        elif abs(mid_y - ymin) < eps:
            patch = "lower";  target = np.array([0.0, -1.0, 0.0])
        elif abs(mid_y - ymax) < eps:
            patch = "upper";  target = np.array([0.0, 1.0, 0.0])
        else:
            continue
        tris = [(v00, v10, v11), (v00, v11, v01)]
        n_t = tri_normal(*tris[0])
        if np.dot(n_t, target) < 0:
            tris = [(v2, v1, v0) for v0, v1, v2 in tris]
        if patch == "inlet":   INLET_tris.extend(tris)
        elif patch == "outlet": OUTLET_tris.extend(tris)
        elif patch == "lower": PLOWER_tris.extend(tris)
        else:                  PUPPER_tris.extend(tris)

    # ── Write STL ─────────────────────────────────────────────────────────────
    all_solids = {
        "inlet":          INLET_tris,
        "outlet":         OUTLET_tris,
        "periodic_lower": PLOWER_tris,
        "periodic_upper": PUPPER_tris,
        "blade":          blade_tris,
        "frontAndBack":   front_back_tris,
    }

    # Cross the backend F2-path facet gate (default 1 round x4 -> ~14.7k facets)
    # so gmsh skips classifySurfaces (which fails on the curved blade). See
    # subdivide_4 docstring + dogfood retro for the genuine finding behind this.
    if SUBDIVIDE_ROUNDS > 0:
        all_solids = {
            name: subdivide_4(tris, rounds=SUBDIVIDE_ROUNDS)
            for name, tris in all_solids.items()
        }

    with open(OUT, "w") as f:
        for name, tris in all_solids.items():
            write_solid(f, name, tris)

    # ── VALIDATION ────────────────────────────────────────────────────────────
    print("\n=== VALIDATION ===")
    total = 0
    for name, tris in all_solids.items():
        print(f"  {name}: {len(tris)} facets")
        total += len(tris)
    print(f"  TOTAL: {total} facets")

    all_verts = []
    for tris in all_solids.values():
        for v0, v1, v2 in tris:
            all_verts.extend([v0, v1, v2])
    all_verts = np.array(all_verts)
    print(f"\nOverall bbox:")
    print(f"  x: [{all_verts[:,0].min():.4f}, {all_verts[:,0].max():.4f}]")
    print(f"  y: [{all_verts[:,1].min():.4f}, {all_verts[:,1].max():.4f}]")
    print(f"  z: [{all_verts[:,2].min():.4f}, {all_verts[:,2].max():.4f}]")
    print(f"\nBlade bbox: x=[{blade_xmin:.4f},{blade_xmax:.4f}] y=[{blade_ymin:.4f},{blade_ymax:.4f}]")
    print(f"Clearance: lower={clr_lo:.4f}, upper={clr_hi:.4f}  "
          f"(min={min(clr_lo,clr_hi):.4f}, need >=0.12)")
    print(f"Final chord scale: {final_chord}")

    # Watertightness: every edge appears exactly 2 times
    edge_count = defaultdict(int)
    def edge_key(va, vb):
        a = tuple(np.round(va, 7)); b = tuple(np.round(vb, 7))
        return (min(a, b), max(a, b))
    for tris in all_solids.values():
        for v0, v1, v2 in tris:
            edge_count[edge_key(v0, v1)] += 1
            edge_count[edge_key(v1, v2)] += 1
            edge_count[edge_key(v2, v0)] += 1
    non_manifold = [(e, c) for e, c in edge_count.items() if c != 2]
    watertight = len(non_manifold) == 0
    print(f"\nWATERTIGHT: {watertight}")
    if not watertight:
        print(f"  Non-manifold edges: {len(non_manifold)}")
        cnt = Counter(c for _, c in non_manifold)
        print(f"  Edge-count distribution: {dict(cnt)}")
        for e, c in non_manifold[:5]:
            print(f"    count={c}  {e[0]} → {e[1]}")
    print(f"\nSTL written to: {OUT}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--subdivide", type=int, default=SUBDIVIDE_ROUNDS,
        help="rounds of 1->4 midpoint subdivision (default 1 -> ~14.7k facets, "
             "crosses the backend F2-path facet gate; 0 = native ~3.7k)",
    )
    args = ap.parse_args()
    SUBDIVIDE_ROUNDS = args.subdivide
    main()

"""Generate NACA 4-digit airfoil STL — pseudo-2D slab for OpenFOAM simpleFoam.

Defaults: NACA 0012, chord=1.0m, span=0.1m (slab), 200 chordwise points cosine-clustered.
Span is intentionally short — pseudo-2D handled by symmetryPlane on the two spanwise faces.

Run:
    python3 generate_naca_stl.py [naca=0012] [chord=1.0] [span=0.1] [n=200] > airfoil.stl
"""
import math
import sys

NACA = "0012"
CHORD = 1.0
SPAN = 0.1
N = 200


def naca4(code: str, x_over_c: float) -> tuple[float, float]:
    """NACA 4-digit thickness distribution. Returns (yt_upper, yt_lower) at x/c.

    For symmetric airfoils (00xx) camber line is at y=0.
    """
    m = int(code[0]) / 100.0
    p = int(code[1]) / 10.0 if int(code[1]) > 0 else 1.0
    t = int(code[2:4]) / 100.0

    x = x_over_c
    yt = 5 * t * (
        0.2969 * math.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x * x
        + 0.2843 * x ** 3
        - 0.1015 * x ** 4
    )

    if m == 0:
        yc = 0.0
        dyc_dx = 0.0
    elif x < p:
        yc = m / p ** 2 * (2 * p * x - x * x)
        dyc_dx = 2 * m / p ** 2 * (p - x)
    else:
        yc = m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x * x)
        dyc_dx = 2 * m / (1 - p) ** 2 * (p - x)

    theta = math.atan(dyc_dx)
    xu = x - yt * math.sin(theta)
    yu = yc + yt * math.cos(theta)
    xl = x + yt * math.sin(theta)
    yl = yc - yt * math.cos(theta)
    return (xu, yu), (xl, yl)


def cosine_x(n: int) -> list[float]:
    """Cosine-clustered x/c samples from 0 to 1 (n+1 points)."""
    return [0.5 * (1 - math.cos(math.pi * i / n)) for i in range(n + 1)]


def airfoil_points(code: str, n: int, chord: float) -> list[tuple[float, float]]:
    """Return closed polygon: trailing edge → upper → leading edge → lower → trailing edge.

    Output is (n+1)*2 - 2 points (LE/TE shared between upper/lower at sharp closure).
    """
    xs = cosine_x(n)
    upper = []
    lower = []
    for x in xs:
        (xu, yu), (xl, yl) = naca4(code, x)
        upper.append((xu * chord, yu * chord))
        lower.append((xl * chord, yl * chord))

    pts = list(reversed(upper)) + lower[1:]
    return pts


def emit_stl_ascii(pts2d: list[tuple[float, float]], span: float, name: str = "airfoil") -> str:
    """Emit ASCII STL by extruding 2D polygon along z by ±span/2.

    Generates:
      - upper face (z=+span/2) triangles
      - lower face (z=-span/2) triangles
      - side wall triangles (closed prism)
    """
    z_pos = span / 2.0
    z_neg = -span / 2.0
    lines = [f"solid {name}"]

    def tri(p1, p2, p3, normal=None):
        if normal is None:
            ux, uy, uz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
            vx, vy, vz = p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            mag = math.sqrt(nx * nx + ny * ny + nz * nz)
            if mag == 0:
                return []
            nx, ny, nz = nx / mag, ny / mag, nz / mag
        else:
            nx, ny, nz = normal
        return [
            f"  facet normal {nx:.6e} {ny:.6e} {nz:.6e}",
            "    outer loop",
            f"      vertex {p1[0]:.6e} {p1[1]:.6e} {p1[2]:.6e}",
            f"      vertex {p2[0]:.6e} {p2[1]:.6e} {p2[2]:.6e}",
            f"      vertex {p3[0]:.6e} {p3[1]:.6e} {p3[2]:.6e}",
            "    endloop",
            "  endfacet",
        ]

    centroid_x = sum(p[0] for p in pts2d) / len(pts2d)
    centroid_y = sum(p[1] for p in pts2d) / len(pts2d)
    c_pos = (centroid_x, centroid_y, z_pos)
    c_neg = (centroid_x, centroid_y, z_neg)

    n_pts = len(pts2d)
    for i in range(n_pts):
        j = (i + 1) % n_pts
        a2 = pts2d[i]
        b2 = pts2d[j]
        a_pos = (a2[0], a2[1], z_pos)
        b_pos = (b2[0], b2[1], z_pos)
        a_neg = (a2[0], a2[1], z_neg)
        b_neg = (b2[0], b2[1], z_neg)

        lines.extend(tri(a_pos, b_pos, c_pos, normal=(0, 0, 1)))
        lines.extend(tri(b_neg, a_neg, c_neg, normal=(0, 0, -1)))
        lines.extend(tri(a_pos, a_neg, b_neg))
        lines.extend(tri(a_pos, b_neg, b_pos))

    lines.append(f"endsolid {name}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    code = NACA
    chord = CHORD
    span = SPAN
    n = N
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            if k == "naca":
                code = v
            elif k == "chord":
                chord = float(v)
            elif k == "span":
                span = float(v)
            elif k == "n":
                n = int(v)

    pts = airfoil_points(code, n, chord)
    out = emit_stl_ascii(pts, span, name=f"NACA{code}")
    sys.stdout.write(out)
    sys.stderr.write(
        f"NACA {code} · chord={chord} · span={span} · "
        f"chordwise n={n} · polygon points={len(pts)} · "
        f"facets={len(pts) * 4}\n"
    )

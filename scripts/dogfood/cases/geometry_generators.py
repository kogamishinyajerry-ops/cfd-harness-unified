"""Programmatic ASCII STL writers for the B-arc dogfood case pool.

Three generators, all pure-stdlib, deterministic. Output is small
(~1-5 KB per file) ASCII STL suitable for OpenFOAM import. Geometry
is representative — not high-fidelity — because the dogfood tests
workbench UX + advisor signal-to-noise, not solver accuracy.

Re-running each generator must produce byte-identical output;
test_cases.py asserts this by comparison against the committed
fixtures under `geometry/`.
"""
from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Iterable

Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]

GEOM_DIR = Path(__file__).parent / "geometry"


# ---------------------------------------------------------------------------
# Common ASCII STL writer
# ---------------------------------------------------------------------------


def _normal(a: Vec3, b: Vec3, c: Vec3) -> Vec3:
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    norm = math.sqrt(nx * nx + ny * ny + nz * nz)
    if norm == 0.0:
        return (0.0, 0.0, 0.0)
    return (nx / norm, ny / norm, nz / norm)


def _fmt(x: float) -> str:
    """Stable 6-decimal formatting; strips negative-zero artefacts."""
    s = f"{x:.6f}"
    if s == "-0.000000":
        return "0.000000"
    return s


def write_stl(name: str, triangles: Iterable[Triangle], buf: io.StringIO) -> int:
    """Write triangles as ASCII STL into buf; return facet count."""
    buf.write(f"solid {name}\n")
    count = 0
    for a, b, c in triangles:
        n = _normal(a, b, c)
        buf.write(
            "  facet normal " + " ".join(_fmt(v) for v in n) + "\n"
        )
        buf.write("    outer loop\n")
        for v in (a, b, c):
            buf.write("      vertex " + " ".join(_fmt(x) for x in v) + "\n")
        buf.write("    endloop\n")
        buf.write("  endfacet\n")
        count += 1
    buf.write(f"endsolid {name}\n")
    return count


def parse_stl_facet_count(text: str) -> int:
    """Count facets in an ASCII STL by counting `endfacet` lines."""
    return sum(1 for line in text.splitlines() if line.strip() == "endfacet")


# ---------------------------------------------------------------------------
# NACA0012 — extruded thin-wing slice
# ---------------------------------------------------------------------------


def _naca0012_y(x: float) -> float:
    """NACA0012 half-thickness profile; x in [0, 1]."""
    return 0.6 * (
        0.2969 * math.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x * x
        + 0.2843 * x * x * x
        - 0.1015 * x * x * x * x
    )


def _airfoil_profile(n_segments: int = 30) -> list[tuple[float, float]]:
    """Closed airfoil contour: lower surface (TE→LE) + upper surface (LE→TE)."""
    upper: list[tuple[float, float]] = []
    lower: list[tuple[float, float]] = []
    for i in range(n_segments + 1):
        t = i / n_segments
        # cosine clustering for finer resolution near LE/TE
        x = 0.5 * (1.0 - math.cos(math.pi * t))
        y = _naca0012_y(x)
        upper.append((x, y))
        lower.append((x, -y))
    # Build closed contour: lower from TE to LE, then upper from LE to TE
    return list(reversed(lower)) + upper[1:]


def generate_naca0012(thickness: float = 0.1) -> tuple[str, int]:
    """Generate NACA0012 STL: extruded profile from z=0 to z=thickness."""
    profile = _airfoil_profile(n_segments=30)
    triangles: list[Triangle] = []
    z0 = 0.0
    z1 = thickness

    n = len(profile)
    # Side walls (extruded surface) — two triangles per profile segment
    for i in range(n):
        x0, y0 = profile[i]
        x1, y1 = profile[(i + 1) % n]
        v00: Vec3 = (x0, y0, z0)
        v01: Vec3 = (x0, y0, z1)
        v10: Vec3 = (x1, y1, z0)
        v11: Vec3 = (x1, y1, z1)
        triangles.append((v00, v10, v11))
        triangles.append((v00, v11, v01))

    # Caps — fan triangulation from leading-edge vertex (index 0 == TE here;
    # use first profile point as fan center for both caps)
    fan_center_low: Vec3 = (profile[0][0], profile[0][1], z0)
    fan_center_high: Vec3 = (profile[0][0], profile[0][1], z1)
    for i in range(1, n - 1):
        a_lo: Vec3 = (profile[i][0], profile[i][1], z0)
        b_lo: Vec3 = (profile[i + 1][0], profile[i + 1][1], z0)
        triangles.append((fan_center_low, b_lo, a_lo))  # bottom cap (winding flipped)
        a_hi: Vec3 = (profile[i][0], profile[i][1], z1)
        b_hi: Vec3 = (profile[i + 1][0], profile[i + 1][1], z1)
        triangles.append((fan_center_high, a_hi, b_hi))

    buf = io.StringIO()
    count = write_stl("naca0012", triangles, buf)
    return buf.getvalue(), count


# ---------------------------------------------------------------------------
# Backward-facing step — 12-facet box-with-step
# ---------------------------------------------------------------------------


def generate_backward_step() -> tuple[str, int]:
    """Channel with sudden expansion. Streamwise: x in [0, 10]; cross: y in
    [0, 2] post-step or [1, 2] pre-step; spanwise: z in [0, 1].

    Pre-step region: x in [0, 2], y in [1, 2] (height = 1).
    Post-step region: x in [2, 10], y in [0, 2] (height = 2).
    L-shaped 2D footprint extruded in z.
    """
    # 12 vertices defining the L-shaped prism
    # Pre-step (smaller channel) corners:
    a = (0.0, 1.0, 0.0)  # bot-front-pre
    b = (2.0, 1.0, 0.0)  # bot-front-step
    # step face goes from (2, 1, *) down to (2, 0, *)
    c = (2.0, 0.0, 0.0)  # bot-front-post
    d = (10.0, 0.0, 0.0)  # bot-back-post
    e = (10.0, 2.0, 0.0)  # top-back-post
    f = (0.0, 2.0, 0.0)  # top-back-pre
    a2 = (0.0, 1.0, 1.0)
    b2 = (2.0, 1.0, 1.0)
    c2 = (2.0, 0.0, 1.0)
    d2 = (10.0, 0.0, 1.0)
    e2 = (10.0, 2.0, 1.0)
    f2 = (0.0, 2.0, 1.0)

    triangles: list[Triangle] = [
        # z=0 cap (L-shape) — fan from f
        (f, a, b),
        (f, b, e),
        (b, c, d),
        (b, d, e),
        # z=1 cap (mirrored winding)
        (f2, b2, a2),
        (f2, e2, b2),
        (b2, d2, c2),
        (b2, e2, d2),
        # walls — pre-step inlet (x=0, from y=1 to y=2)
        (a, f, f2),
        (a, f2, a2),
        # walls — step face (x=2, from y=0 to y=1)
        (c, b, b2),
        (c, b2, c2),
        # walls — outlet (x=10)
        (d, d2, e2),
        (d, e2, e),
        # walls — bottom inner (y=1, x in [0,2])
        (a, b, b2),
        (a, b2, a2),
        # walls — bottom outer (y=0, x in [2,10])
        (c, c2, d2),
        (c, d2, d),
        # walls — top (y=2)
        (e, e2, f2),
        (e, f2, f),
    ]
    buf = io.StringIO()
    count = write_stl("backward_step", triangles, buf)
    return buf.getvalue(), count


# ---------------------------------------------------------------------------
# Pipe expansion — two coaxial cylinders sharing the expansion plane
# ---------------------------------------------------------------------------


def generate_pipe_expansion(n_sides: int = 16) -> tuple[str, int]:
    """Two coaxial cylinders along x-axis. Upstream r=0.5 from x=0 to x=4;
    downstream r=1.0 from x=4 to x=12. Joint plane (annular) at x=4.
    """
    triangles: list[Triangle] = []
    r1 = 0.5
    r2 = 1.0
    x0 = 0.0
    x_join = 4.0
    x_end = 12.0

    # Generate ring vertices
    def ring(x: float, r: float) -> list[Vec3]:
        return [
            (x, r * math.cos(2 * math.pi * i / n_sides), r * math.sin(2 * math.pi * i / n_sides))
            for i in range(n_sides)
        ]

    up_inlet = ring(x0, r1)
    up_join = ring(x_join, r1)
    down_join = ring(x_join, r2)
    down_outlet = ring(x_end, r2)

    # Upstream side wall
    for i in range(n_sides):
        a = up_inlet[i]
        b = up_inlet[(i + 1) % n_sides]
        c = up_join[(i + 1) % n_sides]
        d = up_join[i]
        triangles.append((a, b, c))
        triangles.append((a, c, d))
    # Downstream side wall
    for i in range(n_sides):
        a = down_join[i]
        b = down_join[(i + 1) % n_sides]
        c = down_outlet[(i + 1) % n_sides]
        d = down_outlet[i]
        triangles.append((a, b, c))
        triangles.append((a, c, d))
    # Annular expansion face (between r1 and r2 at x=x_join)
    for i in range(n_sides):
        a = up_join[i]
        b = up_join[(i + 1) % n_sides]
        c = down_join[(i + 1) % n_sides]
        d = down_join[i]
        triangles.append((a, b, c))
        triangles.append((a, c, d))
    # Inlet cap (disk at x=x0)
    center_in: Vec3 = (x0, 0.0, 0.0)
    for i in range(n_sides):
        a = up_inlet[i]
        b = up_inlet[(i + 1) % n_sides]
        triangles.append((center_in, b, a))
    # Outlet cap (disk at x=x_end)
    center_out: Vec3 = (x_end, 0.0, 0.0)
    for i in range(n_sides):
        a = down_outlet[i]
        b = down_outlet[(i + 1) % n_sides]
        triangles.append((center_out, a, b))

    buf = io.StringIO()
    count = write_stl("pipe_expansion", triangles, buf)
    return buf.getvalue(), count


# ---------------------------------------------------------------------------
# Driver — used by tests + initial commit
# ---------------------------------------------------------------------------


GENERATORS = {
    "naca0012": generate_naca0012,
    "backward_step": generate_backward_step,
    "pipe_expansion": generate_pipe_expansion,
}


def regenerate_all(target_dir: Path | None = None) -> dict[str, int]:
    """Regenerate all 3 STL fixtures into `target_dir`; return facet counts."""
    target = target_dir or GEOM_DIR
    target.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for case_id, gen in GENERATORS.items():
        text, count = gen()
        (target / f"{case_id}.stl").write_text(text, encoding="utf-8")
        counts[case_id] = count
    return counts


__all__ = [
    "GENERATORS",
    "GEOM_DIR",
    "generate_backward_step",
    "generate_naca0012",
    "generate_pipe_expansion",
    "parse_stl_facet_count",
    "regenerate_all",
    "write_stl",
]


if __name__ == "__main__":  # pragma: no cover
    counts = regenerate_all()
    for name, n in counts.items():
        print(f"{name}: {n} facets")

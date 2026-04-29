"""Render the LDC cube with lid faces in red, walls in gray.

Reads the polyMesh boundary file (post-setup-bc) and the polyMesh
points + faces, projects each boundary face to the screen via a fixed
isometric camera, and rasterizes filled triangles via Pillow.

Camera: looking down +y axis, slightly tilted, with the lid at the
top of the screen — gives the user the most intuitive "this is the
lid moving rightward" perspective.
"""
from __future__ import annotations

import io
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


class BcOverlayError(RuntimeError):
    """Raised when the polyMesh isn't post-setup-bc shaped, or
    rendering fails for I/O reasons."""


# ---- cabinet (oblique) projection -------------------------------------------
#
# CFD convention: world +z is "up" → must end up at the TOP of the
# rendered image. Cabinet projection: world +x maps to screen +x (to
# the right), world +z maps to screen +y (up), world +y maps to a
# diagonal offset (depth into the page) at 45° with half-scale.
#
# This puts the LDC lid (top of the cube at z=+0.05) visibly on top
# of the rendering, with the moving-lid arrow tangent to it — matches
# the canonical cavity diagram.
_CABINET_DEPTH_SCALE = 0.5
_CABINET_ANGLE_RAD = math.radians(30.0)
_DEPTH_DX = _CABINET_DEPTH_SCALE * math.cos(_CABINET_ANGLE_RAD)
_DEPTH_DY = _CABINET_DEPTH_SCALE * math.sin(_CABINET_ANGLE_RAD)


def _world_to_screen_axes(p: np.ndarray) -> np.ndarray:
    """Cabinet projection: returns (Nx2) (screen_x, screen_y_up).
    Screen-y here points UP (world convention); the caller flips to
    image coordinates where y grows down.
    """
    sx = p[:, 0] + p[:, 1] * _DEPTH_DX
    sy = p[:, 2] + p[:, 1] * _DEPTH_DY
    return np.column_stack([sx, sy])

_IMAGE_SIZE = (520, 520)
_PADDING = 60  # pixels reserved for axis labels + lid arrow


def _split_foam_block(path: Path) -> tuple[str, int, str, str]:
    text = path.read_text()
    m = re.search(r"^\s*(\d+)\s*\n\(\s*\n", text, flags=re.MULTILINE)
    if not m:
        raise BcOverlayError(f"can't parse FOAM block in {path}")
    count = int(m.group(1))
    body_start = m.end()
    body_end = text.index("\n)", body_start)
    return text[:body_start], count, text[body_start:body_end], text[body_end:]


def _parse_points(body: str) -> np.ndarray:
    coords: list[tuple[float, float, float]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(
            r"\(([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\)", line
        )
        if m:
            coords.append(
                (float(m.group(1)), float(m.group(2)), float(m.group(3)))
            )
    return np.array(coords, dtype=np.float64)


def _parse_faces(body: str) -> list[list[int]]:
    faces: list[list[int]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+)\(([\d\s]+)\)$", line)
        if m:
            faces.append([int(x) for x in m.group(2).split()])
    return faces


def _read_boundary_patches(
    polymesh: Path,
) -> dict[str, tuple[int, int]]:
    """Return ``{patch_name: (startFace, nFaces)}`` keyed in declaration order."""
    text = (polymesh / "boundary").read_text()
    # Find the patch list: "<count>\n(\n<patches>\n)"
    patches: dict[str, tuple[int, int]] = {}
    pattern = re.compile(
        r"(\w+)\s*\{[^}]*nFaces\s+(\d+)[^}]*startFace\s+(\d+)[^}]*\}",
        re.DOTALL,
    )
    for m in pattern.finditer(text):
        name = m.group(1)
        if name == "FoamFile":
            continue
        n_faces = int(m.group(2))
        start_face = int(m.group(3))
        patches[name] = (start_face, n_faces)
    return patches


def _project(points: np.ndarray, bbox_min: np.ndarray, bbox_max: np.ndarray) -> np.ndarray:
    """Project Nx3 world coords to Nx2 screen coords (pixel space).

    Uses cabinet projection (see :func:`_world_to_screen_axes`) so
    that world +z lands at the TOP of the rendered image — the LDC
    lid is visibly on top.
    """
    screen = _world_to_screen_axes(points)
    # Compute the projected bbox so we can scale to fit the canvas.
    corners = np.array(
        [
            [x, y, z]
            for x in (bbox_min[0], bbox_max[0])
            for y in (bbox_min[1], bbox_max[1])
            for z in (bbox_min[2], bbox_max[2])
        ]
    )
    proj_corners = _world_to_screen_axes(corners)
    rmin = proj_corners.min(axis=0)
    rmax = proj_corners.max(axis=0)
    extent = rmax - rmin
    canvas_extent = np.array(_IMAGE_SIZE) - 2 * _PADDING
    scale = min(canvas_extent / extent)
    centered = (screen - rmin) * scale
    # Center within the canvas; image y grows down so flip the
    # vertical (screen-y-up → image-y-down).
    margin_x = (_IMAGE_SIZE[0] - extent[0] * scale) / 2
    margin_y = (_IMAGE_SIZE[1] - extent[1] * scale) / 2
    centered[:, 0] += margin_x
    centered[:, 1] = _IMAGE_SIZE[1] - centered[:, 1] - margin_y
    return centered


def render_bc_overlay_png(
    case_dir: Path,
    *,
    lid_velocity: tuple[float, float, float] = (1.0, 0.0, 0.0),
) -> bytes:
    """Render the post-setup-bc cube with lid red, walls gray. Return
    PNG bytes.

    Raises :class:`BcOverlayError` if the polyMesh isn't post-split or
    no ``lid`` patch exists.
    """
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        raise BcOverlayError(f"no polyMesh at {polymesh}")

    patches = _read_boundary_patches(polymesh)
    if "lid" not in patches or "fixedWalls" not in patches:
        raise BcOverlayError(
            f"polyMesh boundary has no 'lid' + 'fixedWalls' patches "
            f"(got {sorted(patches.keys())}). Run setup-bc first."
        )

    _, _, pts_body, _ = _split_foam_block(polymesh / "points")
    points = _parse_points(pts_body)

    _, _, faces_body, _ = _split_foam_block(polymesh / "faces")
    faces = _parse_faces(faces_body)

    bbox_min = points.min(axis=0)
    bbox_max = points.max(axis=0)
    screen_pts = _project(points, bbox_min, bbox_max)

    img = Image.new("RGB", _IMAGE_SIZE, (12, 14, 22))  # surface-950ish
    draw = ImageDraw.Draw(img, "RGBA")

    # Color all wall faces first (gray), then lid faces on top (red).
    # This ordering is important because lid + wall faces share the
    # top edges — drawing lid last keeps its outline crisp.
    wall_start, wall_n = patches["fixedWalls"]
    lid_start, lid_n = patches["lid"]

    wall_color = (140, 145, 160, 220)  # surface-300 with mild alpha
    wall_outline = (90, 96, 110, 200)
    lid_color = (244, 100, 100, 230)  # rose-400ish
    lid_outline = (220, 60, 60, 255)

    for i in range(wall_start, wall_start + wall_n):
        if i >= len(faces):
            continue
        face = faces[i]
        coords = [tuple(screen_pts[v]) for v in face]
        if len(coords) >= 3:
            draw.polygon(coords, fill=wall_color, outline=wall_outline)

    for i in range(lid_start, lid_start + lid_n):
        if i >= len(faces):
            continue
        face = faces[i]
        coords = [tuple(screen_pts[v]) for v in face]
        if len(coords) >= 3:
            draw.polygon(coords, fill=lid_color, outline=lid_outline)

    # Lid velocity arrow: project the (lid speed, 0, 0) vector and
    # draw it tangent to the lid in screen space.
    arrow_origin_world = np.array(
        [
            (bbox_min[0] + bbox_max[0]) / 2,
            (bbox_min[1] + bbox_max[1]) / 2,
            bbox_max[2],
        ]
    )
    speed = math.sqrt(sum(c * c for c in lid_velocity))
    if speed > 0:
        # Draw the arrow as a long vector along the lid plane
        unit = np.array(lid_velocity) / speed
        arrow_extent = max(bbox_max - bbox_min) * 0.5
        arrow_tip_world = arrow_origin_world + unit * arrow_extent
        a0, a1 = _project(
            np.stack([arrow_origin_world, arrow_tip_world]),
            bbox_min,
            bbox_max,
        )
        draw.line([tuple(a0), tuple(a1)], fill=(244, 220, 100, 255), width=3)
        # arrow head: two short backward-angled segments
        dx = a1[0] - a0[0]
        dy = a1[1] - a0[1]
        length = math.hypot(dx, dy) or 1.0
        nx = dx / length
        ny = dy / length
        head = 14
        for sign in (+1, -1):
            # rotate (-nx,-ny) by ±25°
            theta = math.radians(25) * sign
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            bx = (-nx) * cos_t - (-ny) * sin_t
            by = (-nx) * sin_t + (-ny) * cos_t
            draw.line(
                [tuple(a1), (a1[0] + bx * head, a1[1] + by * head)],
                fill=(244, 220, 100, 255),
                width=3,
            )

    # Legend + labels.
    try:
        font = ImageFont.load_default()
    except Exception:  # noqa: BLE001
        font = None
    draw.rectangle((10, 10, 22, 22), fill=lid_color, outline=lid_outline)
    draw.text((28, 10), f"lid · U = ({lid_velocity[0]:g} {lid_velocity[1]:g} {lid_velocity[2]:g}) m/s",
              fill=(244, 220, 220), font=font)
    draw.rectangle((10, 28, 22, 40), fill=wall_color, outline=wall_outline)
    draw.text((28, 28), "fixedWalls · no-slip", fill=(200, 205, 220), font=font)
    draw.text(
        (10, _IMAGE_SIZE[1] - 22),
        f"lid faces: {lid_n}  ·  wall faces: {wall_n}",
        fill=(160, 165, 180),
        font=font,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

"""Server-rendered PNG visualizations for Steps 3-5 (DEC-V61-097).

Each step in the M-PANELS panel needs a distinct viewport so the user
can SEE what just happened, instead of staring at the same Step-2
mesh wireframe through the back half of the demo. The three modules
here render Pillow-only PNGs (no matplotlib dependency) for:

* ``bc_overlay``        — Step 3: meshed cube with lid faces in red
                          and wall faces in gray, plus a lid-velocity
                          arrow.
* ``residual_chart``    — Step 4: log-scale line plot of p / Ux / Uy
                          / Uz initial residuals across iterations,
                          parsed from log.icoFoam.
* ``velocity_slice``    — Step 5: |U| heatmap on the z=0 midplane,
                          viridis colormap, drawn at 400×400.

All three are deterministic functions of files already on disk
(polyMesh + log.icoFoam + final time directory) — no caching needed
beyond what FastAPI's ``StreamingResponse`` already provides.
"""
from .bc_overlay import (
    BcOverlayError,
    render_bc_overlay_png,
)
from .residual_chart import (
    ResidualChartError,
    render_residual_chart_png,
)
from .velocity_slice import (
    VelocitySliceError,
    render_velocity_slice_png,
)
from .report_bundle import (
    ARTIFACT_NAMES,
    ReportBundle,
    ReportBundleError,
    build_report_bundle,
    read_report_artifact,
)

__all__ = [
    "ARTIFACT_NAMES",
    "BcOverlayError",
    "ReportBundle",
    "ReportBundleError",
    "ResidualChartError",
    "VelocitySliceError",
    "build_report_bundle",
    "read_report_artifact",
    "render_bc_overlay_png",
    "render_residual_chart_png",
    "render_velocity_slice_png",
]

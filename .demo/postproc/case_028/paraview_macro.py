"""ParaView pvpython macro: case_028 APU bay ventilation slice screenshot.

Run via:  pvpython paraview_macro.py  — produces paraview_view.png in current dir.
Tested-paths-only-not-executed-in-session.

Opens the OpenFOAM case via an auto-created .foam handle, loads the
latest time directory (474), slices at the geometric mid-z, colors by
velocity magnitude (U), and saves an 1280x720 screenshot.

If the .foam handle is missing the script creates an empty one (the
standard ParaView OpenFOAM ingest convention).
"""
from __future__ import annotations
import os
from pathlib import Path

from paraview.simple import (  # type: ignore[import-not-found]
    OpenFOAMReader, Slice, GetActiveViewOrCreate, Show, Hide, Render,
    SaveScreenshot, GetAnimationScene, ColorBy, GetColorTransferFunction,
)

CASE_DIR = Path(
    "/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/"
    "case_028_apu_bay_ventilation/case"
)
FOAM_HANDLE = CASE_DIR / "case.foam"
OUT = Path(__file__).parent / "paraview_view.png"


def ensure_foam_handle() -> Path:
    if not FOAM_HANDLE.exists():
        FOAM_HANDLE.touch()
    return FOAM_HANDLE


def main() -> None:
    handle = ensure_foam_handle()
    reader = OpenFOAMReader(FileName=str(handle))
    reader.MeshRegions = ["internalMesh"]
    reader.CellArrays = ["U", "p", "k", "omega", "nut"]

    scene = GetAnimationScene()
    scene.UpdateAnimationUsingDataTimeSteps()
    scene.GoToLast()  # last time = 474

    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [1280, 720]
    view.OrientationAxesVisibility = 1
    view.Background = [0.12, 0.13, 0.14]

    # Geometric mid-z slice (origin auto from bounds)
    reader.UpdatePipeline()
    bounds = reader.GetDataInformation().GetBounds()
    zmid = 0.5 * (bounds[4] + bounds[5])
    slc = Slice(Input=reader)
    slc.SliceType = "Plane"
    slc.SliceType.Origin = [
        0.5 * (bounds[0] + bounds[1]),
        0.5 * (bounds[2] + bounds[3]),
        zmid,
    ]
    slc.SliceType.Normal = [0.0, 0.0, 1.0]

    Hide(reader, view)
    disp = Show(slc, view)
    ColorBy(disp, ("CELLS", "U", "Magnitude"))
    lut = GetColorTransferFunction("U")
    disp.SetScalarBarVisibility(view, True)
    view.ResetCamera()
    Render(view)
    SaveScreenshot(str(OUT), view, ImageResolution=[1280, 720])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

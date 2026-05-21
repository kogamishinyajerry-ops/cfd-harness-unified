"""ParaView pvpython macro: case_021 NASA TMR flat plate wall y+ visualization.

Run via:  pvpython paraview_macro.py  — produces paraview_view.png in current dir.
Tested-paths-only-not-executed-in-session.

Visualizes wallShearStress magnitude on the `plate` patch at the final
converged time (2500). y+ itself is a derived FV functionObject field
that would require a yPlus utility run; this macro shows wallShearStress
which is what the converged solution actually emits.

The TMR (NASA Turbulence Modeling Resource) flat plate is the canonical
RANS k-ω SST verification case (Re_L = 5e6).
"""
from __future__ import annotations
from pathlib import Path

from paraview.simple import (  # type: ignore[import-not-found]
    OpenFOAMReader, ExtractBlock, GetActiveViewOrCreate, Show, Hide, Render,
    SaveScreenshot, GetAnimationScene, ColorBy, GetColorTransferFunction,
)

CASE_DIR = Path(
    "/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/"
    "case_021_nasa_tmr_flat_plate/case_v65"
)
FOAM_HANDLE = CASE_DIR / "case.foam"
OUT = Path(__file__).parent / "paraview_view.png"

# Patch name from constant/polyMesh/boundary; flat plate is wall side.
PLATE_PATCH = "plate"


def ensure_foam_handle() -> Path:
    if not FOAM_HANDLE.exists():
        FOAM_HANDLE.touch()
    return FOAM_HANDLE


def main() -> None:
    handle = ensure_foam_handle()
    reader = OpenFOAMReader(FileName=str(handle))
    reader.MeshRegions = ["internalMesh", f"patch/{PLATE_PATCH}"]
    reader.CellArrays = ["U", "p", "k", "omega", "nut", "wallShearStress"]

    scene = GetAnimationScene()
    scene.UpdateAnimationUsingDataTimeSteps()
    scene.GoToLast()  # 2500

    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [1280, 720]
    view.OrientationAxesVisibility = 1
    view.Background = [0.10, 0.12, 0.14]

    # Extract just the plate patch
    extract = ExtractBlock(Input=reader)
    extract.Selectors = [f"/Root/patch/{PLATE_PATCH}"]

    Hide(reader, view)
    disp = Show(extract, view)
    ColorBy(disp, ("CELLS", "wallShearStress", "Magnitude"))
    GetColorTransferFunction("wallShearStress")
    disp.SetScalarBarVisibility(view, True)
    view.ResetCamera()
    Render(view)
    SaveScreenshot(str(OUT), view, ImageResolution=[1280, 720])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

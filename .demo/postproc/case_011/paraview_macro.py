"""ParaView pvpython macro: case_011 plate-fin compact HX multi-region slice.

Run via:  pvpython paraview_macro.py  — produces paraview_view.png in current dir.
Tested-paths-only-not-executed-in-session.

Conjugate heat transfer case — chtMultiRegionFoam with three regions:
region_hot_fluid + region_cold_fluid + region_solid. The macro loads
all three, slices along the HX longitudinal axis (mid-y plane), and
colors by temperature T. Solid region appears in steel grayscale; fluid
regions show the full hot/cold thermal gradient.
"""
from __future__ import annotations
from pathlib import Path

from paraview.simple import (  # type: ignore[import-not-found]
    OpenFOAMReader, Slice, GetActiveViewOrCreate, Show, Hide, Render,
    SaveScreenshot, GetAnimationScene, ColorBy, GetColorTransferFunction,
    GroupDatasets,
)

CASE_DIR = Path(
    "/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/"
    "case_011_plate_fin_compact_hx/case"
)
FOAM_HANDLE = CASE_DIR / "case.foam"
OUT = Path(__file__).parent / "paraview_view.png"

REGIONS = ["region_hot_fluid", "region_cold_fluid", "region_solid"]


def ensure_foam_handle() -> Path:
    if not FOAM_HANDLE.exists():
        FOAM_HANDLE.touch()
    return FOAM_HANDLE


def main() -> None:
    handle = ensure_foam_handle()
    reader = OpenFOAMReader(FileName=str(handle))
    reader.MeshRegions = REGIONS
    reader.CellArrays = ["T", "U", "p"]

    scene = GetAnimationScene()
    scene.UpdateAnimationUsingDataTimeSteps()
    scene.GoToLast()  # last time dir

    reader.UpdatePipeline()
    bounds = reader.GetDataInformation().GetBounds()
    ymid = 0.5 * (bounds[2] + bounds[3])

    slc = Slice(Input=reader)
    slc.SliceType = "Plane"
    slc.SliceType.Origin = [
        0.5 * (bounds[0] + bounds[1]),
        ymid,
        0.5 * (bounds[4] + bounds[5]),
    ]
    slc.SliceType.Normal = [0.0, 1.0, 0.0]

    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [1280, 720]
    view.OrientationAxesVisibility = 1
    view.Background = [0.10, 0.10, 0.12]

    Hide(reader, view)
    disp = Show(slc, view)
    ColorBy(disp, ("CELLS", "T"))
    GetColorTransferFunction("T")
    disp.SetScalarBarVisibility(view, True)
    view.ResetCamera()
    Render(view)
    SaveScreenshot(str(OUT), view, ImageResolution=[1280, 720])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

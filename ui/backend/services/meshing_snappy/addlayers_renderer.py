"""Render a minimal addLayers-only ``snappyHexMeshDict``.

We deliberately set ``castellatedMesh false; snap false; addLayers
true;`` so snappyHexMesh operates only on the already-existing
polyMesh produced by the gmsh stage. This keeps the wall-treatment
contract narrow:

  Input  : constant/polyMesh/  (from gmsh + gmshToFoam)
  Output : constant/polyMesh/  (refreshed with layer cells)

The dict is intentionally small. Engineers who need the full
castellated + snap workflow can author their own dict via the M-PANELS
RawDict editor (V096). N2.3-extend can layer multi-patch + per-patch
quality knobs onto this template.
"""
from __future__ import annotations

from typing import Iterable

from ui.backend.schemas.mesh_prism_layers import PatchPrismConfig


def render_snappy_dict(patches: Iterable[PatchPrismConfig]) -> str:
    """Return the full ``system/snappyHexMeshDict`` text content for
    the given patch configs.

    The header is verbatim OpenFOAM 10 convention (FoamFile block).
    Numerical defaults (minThickness, expansionRatio, etc.) are
    OpenFOAM-tutorial typical values that produce stable layer
    addition for the wall-bounded cases this project targets.
    Engineers needing custom controls per patch override via the
    RawDict editor.
    """
    patch_blocks = []
    for cfg in patches:
        patch_blocks.append(_layers_block_for_patch(cfg))

    layers_section = "\n".join(patch_blocks)

    return _DICT_TEMPLATE.format(layers_section=layers_section)


def _layers_block_for_patch(cfg: PatchPrismConfig) -> str:
    """Render a single ``layers { <patch> { ... } }`` entry.

    minThickness defaults to first_cell_height * 0.5 (snappyHexMesh
    will discard layers thinner than this — half of requested
    first-layer height is a conservative floor that lets the layer
    addition succeed on typical wall meshes without falling below
    physical relevance).
    """
    min_thickness = cfg.first_cell_height * 0.5
    return _PATCH_LAYERS_BLOCK.format(
        patch=cfg.patch,
        num_layers=cfg.num_layers,
        first_cell_height=_render_float(cfg.first_cell_height),
        expansion_ratio=_render_float(cfg.expansion_ratio),
        min_thickness=_render_float(min_thickness),
    )


def _render_float(value: float) -> str:
    """Render a float with enough precision that snappyHexMesh's
    internal parsing reproduces the engineer's intent. ``%g`` would
    round 1e-6 to "1e-06" which OpenFOAM accepts, but small
    first-layer heights (~1e-5) deserve fixed-point if they fit, for
    legibility in the dict (audit trail).
    """
    if 1e-3 <= abs(value) < 1e6:
        return f"{value:.10g}"
    return f"{value:.6e}"


# These constants are the snappyHexMesh stub the engineer's prism
# config writes into. ``layers`` is the only block per-patch knobs
# expand into; everything else is a fixed-template default suitable
# for addLayers-only operation on a pre-existing polyMesh.
_PATCH_LAYERS_BLOCK = """    "{patch}"
    {{
        nSurfaceLayers {num_layers};
        firstLayerThickness {first_cell_height};
        expansionRatio {expansion_ratio};
        minThickness {min_thickness};
    }}"""


_DICT_TEMPLATE = """\
/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.openfoam.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      snappyHexMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
// DEC-V61-137 (N2.3) · addLayers-only configuration. castellatedMesh
// and snap stages are intentionally false: the input polyMesh comes
// from gmsh + gmshToFoam (V61-095 / V61-119) and we only need
// snappyHexMesh's addLayers stage on top. Multi-patch shipped in
// N2.3-extend; v0 emits one patch.

castellatedMesh false;
snap            false;
addLayers       true;

geometry {{ }};

castellatedMeshControls
{{
    maxLocalCells 1000000;
    maxGlobalCells 50000000;
    minRefinementCells 0;
    nCellsBetweenLevels 1;
    features ( );
    refinementSurfaces {{ }};
    refinementRegions {{ }};
    locationInMesh (0 0 0);
    allowFreeStandingZoneFaces true;
    resolveFeatureAngle 30;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
}}

addLayersControls
{{
    relativeSizes false;
    layers
    {{
{layers_section}
    }}
    expansionRatio 1.2;
    finalLayerThickness 0.5;
    minThickness 1e-6;
    nGrow 0;
    featureAngle 60;
    slipFeatureAngle 30;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedianAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}

meshQualityControls
{{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minVol 1e-13;
    minTetQuality 1e-15;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist -1;
    nSmoothScale 4;
    errorReduction 0.75;
}}

writeFlags ( );
mergeTolerance 1e-6;

// ************************************************************************* //
"""

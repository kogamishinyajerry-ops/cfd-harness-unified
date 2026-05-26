"""Derive a WorkbenchBasics view from a real imported OpenFOAM case.

The hand-authored `knowledge/workbench_basics/<case_id>.yaml` files only
exist for the ~10 canonical cases. Every imported case (the turbine
full-pipeline dogfood, APU bay, …) therefore 404s on
`/api/cases/{id}/workbench-basics` and the V4 workbench falls back to
"待识别" placeholders — even when the case has been through setup-bc and
carries real boundary fields on disk.

This package derives the same WorkbenchBasics shape directly from the
OpenFOAM case files (`constant/polyMesh/boundary`, `0/<field>`,
`constant/physicalProperties`, `system/controlDict`, …). It is a faithful
mirror of what is on disk — every section it cannot derive is omitted, so
the UI keeps showing an honest "待识别" for that section rather than a
guess (DEC-V61-206 truth-chain: real data or an honest empty state, never
a fabricated one).
"""
from __future__ import annotations

from ui.backend.services.workbench_basics_deriver.deriver import (
    derive_workbench_basics,
)

__all__ = ["derive_workbench_basics"]

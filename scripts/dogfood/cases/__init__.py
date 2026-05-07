"""B-arc dogfood case pool (DEC-V61-165)."""
from pathlib import Path

from scripts.dogfood.cases.geometry_generators import (
    GEOM_DIR,
    GENERATORS,
    parse_stl_facet_count,
    regenerate_all,
)

CASES_DIR = Path(__file__).parent
BRIEFS_DIR = CASES_DIR / "briefs"

CASE_IDS = ("naca0012", "backward_step", "pipe_expansion")


def brief_path(case_id: str) -> Path:
    return BRIEFS_DIR / f"{case_id}.json"


def stl_path(case_id: str) -> Path:
    return GEOM_DIR / f"{case_id}.stl"


__all__ = [
    "BRIEFS_DIR",
    "CASES_DIR",
    "CASE_IDS",
    "GENERATORS",
    "GEOM_DIR",
    "brief_path",
    "parse_stl_facet_count",
    "regenerate_all",
    "stl_path",
]

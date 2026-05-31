"""V9 advisor backend package · V91.2 Python matcher port.

Public API:
    - V9_ADVISOR_RULES · readonly tuple of AdvisorRule loaded from JSON SSOT
    - V9_RULESET_VERSION · str ruleset version
    - match_advisor_patterns · pure-function matcher · (slice, rules) → matches
    - RunArtifactSlice / ForcesEntry / ConvergenceStats / GoldDelta · input shapes
    - MatchedCommentary · output shape
    - CoupledPatch / RegionSlice · W3.0.6 multi-region CHT extension shapes

V130 invariant honored BY CONSTRUCTION (V91 RS#35): module imports
restricted to stdlib + typing + intra-package.
"""

from .manifest_adapter import (
    commentary_section_for_manifest,
    derive_slice_from_manifest,
    matches_for_manifest,
)
from .pattern_matcher import (
    AdvisorRule,
    ConvergenceStats,
    CoupledPatch,
    DevelopedRegionGoldDelta,
    ForcesEntry,
    GoldDelta,
    IntegratedDragPct,
    MatchedCommentary,
    MatchSite,
    ReferenceBandSummary,
    RegionSlice,
    RunArtifactSlice,
    match_advisor_patterns,
)
from .rules import V9_ADVISOR_RULES, V9_RULESET_VERSION

__all__ = [
    "AdvisorRule",
    "ConvergenceStats",
    "CoupledPatch",
    "DevelopedRegionGoldDelta",
    "ForcesEntry",
    "GoldDelta",
    "IntegratedDragPct",
    "MatchedCommentary",
    "MatchSite",
    "ReferenceBandSummary",
    "RegionSlice",
    "RunArtifactSlice",
    "V9_ADVISOR_RULES",
    "V9_RULESET_VERSION",
    "commentary_section_for_manifest",
    "derive_slice_from_manifest",
    "match_advisor_patterns",
    "matches_for_manifest",
]

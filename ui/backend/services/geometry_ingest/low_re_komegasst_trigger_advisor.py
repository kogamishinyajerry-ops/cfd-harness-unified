"""Low-Reynolds wall-resolved kOmegaSST model-bias advisory.

Flags the documented kOmegaSST reattachment / Cf under-prediction that
appears whenever kOmegaSST is run in wall-RESOLVED (integrate-to-wall,
y+<1) mode. This is a TURBULENCE-MODELING bias, not a low Reynolds
number bias — the term "low-Re kOmegaSST" refers to the solver mode
that integrates to the wall without a wall function, NOT a low bulk
Reynolds number regime.

Documented failure modes (V104 corpus witnesses):

  BFS (backward-facing step) — reattachment length x_R/h under-predicted
  by ~13% vs DNS / experiment when kOmegaSST is run wall-resolved
  (integrate-to-wall) at Re=5000. Slice V71.B canonical case observes
  ~6% under-prediction vs the 6.26 anchor, consistent with the class-
  limit bias.

  NACA0012 stall — Cl_max under-predicted by ~28–31% near stall; the
  bias is intrinsic to kOmegaSST's over-production in adverse-pressure-
  gradient regions and cannot be corrected by mesh or time-step refinement.

The advisor fires a single INFO finding (never blocking) to ensure the
engineer is aware that the under-prediction is a known model-class limit
for wall-resolved kOmegaSST, not a setup error.

Canonicalization note:
  The planning-doc spelling is ``low_re_kOmegaSST_trigger``; this module
  is named ``low_re_komegasst_trigger`` (all lowercase) so the canonical-
  eval harness regex ``_RULE_LINE_RE`` (``[a-z_][a-z0-9_]*``) can parse
  and enforce the firings-table row. The two spellings are the same
  advisor; no duplicate module exists.

Anti-scope (V130 advisory-only contract):
  - Does NOT mutate any case directory; returns frozen findings only.
  - Does NOT call any LLM, HTTP endpoint, or external process.
  - Does NOT block the mesh or solve step; severity is always "info".

References:
  - ``docs/openfoam_corpus/industrial_solver_findings_v_series.md`` V104
    (BFS x_R/h −13%, NACA0012 stall Cl_max −28..31% — "the class-limit
    is the model, not the dicts")
  - DEC-V61-235 (low_re_komegasst_trigger advisor · V71.B slice)
  - ``low_re_kOmegaSST_trigger`` planning-doc canonical name →
    canonicalized to ``low_re_komegasst_trigger`` for regex-parse
    compatibility

LANDED 2026-06-08 under DEC-V61-235.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# Normalized kOmegaSST variant tokens. Canonical name is "kOmegaSST";
# common alternate spellings (hyphenated, spaced, all-lowercase) are
# also accepted. Normalization: strip whitespace/hyphens, casefold.
_KOMEGASST_NORMALIZED_TOKEN: str = "komegasst"

# y+ threshold below which the near-wall is considered "resolved"
# (integrate-to-wall mode). OpenFOAM / ERCOFTAC consensus: y+ < 1.0
# is the wall-resolved criterion.
_YPLUS_RESOLVED_THRESHOLD: float = 1.0

# V104 detail text explaining the documented model bias.
_V104_DETAIL: str = (
    "kOmegaSST in wall-resolved (integrate-to-wall, y+<1) mode has a "
    "documented model-class bias: reattachment length under-predicted "
    "~13% on backward-facing step (V104 BFS witness, Re=5000) and "
    "Cl_max under-predicted ~28-31% near stall on NACA0012 (V104 stall "
    "witness). The V71.B canonical case observes ~6% reattachment under-"
    "prediction vs the 6.26 anchor — consistent with the V104 class-"
    "limit. This is an intrinsic turbulence-model bias for integrate-to-"
    "wall kOmegaSST; it cannot be resolved by mesh or time-step "
    "refinement. Advisory only (INFO) — the finding documents the known "
    "floor, not a configuration error. Cite V104 in your validation "
    "report and consider model uncertainty in post-processing. "
    "(DEC-V61-235)"
)


def _normalize_turbulence_model(name: str) -> str:
    """Return a canonical lowercase token for turbulence model name lookup.

    Strips whitespace, hyphens, and case so that ``kOmegaSST``,
    ``k-omega SST``, ``K_OMEGA_SST``, and ``komegasst`` all map to the
    same token.
    """
    return re.sub(r"[\s\-_]", "", name).casefold()


@dataclass(frozen=True)
class LowReKOmegaSSTSnapshot:
    """Normalized snapshot of turbulence-model configuration.

    Fields:

      ``turbulence_model`` — RASModel name from
      ``constant/turbulenceProperties`` (e.g., ``"kOmegaSST"``).

      ``wall_treatment`` — coarse enum: ``"resolved"`` means integrate-
      to-wall (no wall function, y+ target < 1); ``"wall_function"``
      means standard wall function approach (y+ 30–300); ``None`` when
      not specified / unknown.

      ``first_cell_yplus`` — estimated first-cell y+ from mesh
      pre-analysis or user-supplied value; ``None`` when unavailable.
      Takes priority over ``wall_treatment`` for predicate evaluation
      when both are present.
    """

    turbulence_model: str
    wall_treatment: str | None = None
    first_cell_yplus: float | None = None


@dataclass(frozen=True)
class LowReKOmegaSSTFinding:
    """One advisory finding from the low-Re kOmegaSST advisor.

    Always severity="info" (never blocking per V130 anti-scope).
    """

    severity: str     # always "info" for this advisor
    code: str         # "v104_low_re_komegasst_underprediction"
    location: str     # "turbulenceProperties.RAS.RASModel"
    detail: str       # engineer-readable model-bias summary


@dataclass(frozen=True)
class LowReKOmegaSSTReport:
    """Aggregate output from :func:`check_low_re_komegasst`.

    ``findings`` is an empty tuple when the predicate does not apply
    (non-kOmegaSST model, or wall-function / unresolved near-wall).
    Contains exactly one INFO finding when both conditions are met.
    """

    findings: tuple[LowReKOmegaSSTFinding, ...]


def check_low_re_komegasst(snapshot: LowReKOmegaSSTSnapshot) -> LowReKOmegaSSTReport:
    """Inspect ``snapshot`` for the V104 wall-resolved kOmegaSST bias pattern.

    Returns a :class:`LowReKOmegaSSTReport` with zero or one finding.

    Predicate fires EXACTLY ONE finding iff BOTH conditions hold:

      (a) ``turbulence_model`` is a kOmegaSST variant (accepts
          ``"kOmegaSST"`` / ``"k-omega SST"`` / ``"komegasst"``
          and any case / spacing / hyphen variation thereof).

      (b) The near-wall is RESOLVED — either:
          ``wall_treatment == "resolved"``, OR
          ``first_cell_yplus is not None and first_cell_yplus < 1.0``.

    Pure function: 0 LLM, 0 I/O, 0 mutation.
    """
    # (a) kOmegaSST variant check
    normalized = _normalize_turbulence_model(snapshot.turbulence_model)
    if normalized != _KOMEGASST_NORMALIZED_TOKEN:
        return LowReKOmegaSSTReport(findings=())

    # (b) Wall-resolved check. MEASURED first-cell y+ is AUTHORITATIVE when present
    # (the documented LowReKOmegaSSTSnapshot contract + Codex R1 P2): it disambiguates
    # the regime even when wall_treatment claims otherwise — e.g. a config asserting
    # wall_treatment='resolved' but with a measured y+=5 is NOT resolved, so the V104
    # advisory must NOT fire. Only when y+ is unavailable do we fall back to the coarse
    # wall_treatment enum.
    if snapshot.first_cell_yplus is not None:
        is_resolved = snapshot.first_cell_yplus < _YPLUS_RESOLVED_THRESHOLD
    else:
        is_resolved = snapshot.wall_treatment == "resolved"
    if not is_resolved:
        return LowReKOmegaSSTReport(findings=())

    return LowReKOmegaSSTReport(
        findings=(
            LowReKOmegaSSTFinding(
                severity="info",
                code="v104_low_re_komegasst_underprediction",
                location="turbulenceProperties.RAS.RASModel",
                detail=_V104_DETAIL,
            ),
        )
    )

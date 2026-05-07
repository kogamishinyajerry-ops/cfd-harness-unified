"""Case brief loader + machine-checked verdict comparison for the B-arc dogfood.

Briefs are JSON files describing a case, its physics, the engineer's
question, and a structured reference value with tolerance. Personas
verbalize their reasoning, but the harness only trusts the machine
comparison of `observed_value` vs `reference ± tolerance`.

B.3 will populate `cases/` with NACA0012 / backward-step / pipe-expansion;
B.1 ships only the loader + verdict checker.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ToleranceKind = Literal["abs", "rel"]


@dataclass(frozen=True)
class Reference:
    """Structured reference value for a case."""

    metric: str
    value: float
    tolerance: float
    tolerance_kind: ToleranceKind
    source: str

    def passes(self, observed: float) -> bool:
        if self.tolerance_kind == "abs":
            return abs(observed - self.value) <= self.tolerance
        # relative: tolerance is a fraction (e.g., 0.05 for ±5%)
        if self.value == 0.0:
            return abs(observed) <= self.tolerance
        return abs(observed - self.value) / abs(self.value) <= self.tolerance


@dataclass(frozen=True)
class CaseBrief:
    """One case description consumed by a persona."""

    case_id: str
    title: str
    geometry: str
    physics: dict[str, Any]
    question: str
    reference: Reference
    notes: str = ""

    def to_persona_text(self) -> str:
        """Natural-language brief for the persona prompt."""
        ref = self.reference
        return (
            f"# Case: {self.title}\n\n"
            f"**Case ID**: {self.case_id}\n"
            f"**Geometry**: {self.geometry}\n"
            f"**Physics**: {json.dumps(self.physics, ensure_ascii=False)}\n\n"
            f"## Question\n{self.question}\n\n"
            f"## Reference target (machine-checked)\n"
            f"- Metric: `{ref.metric}`\n"
            f"- Reference value: {ref.value} ± "
            f"{ref.tolerance}{'%' if ref.tolerance_kind == 'rel' else ''} "
            f"({ref.tolerance_kind})\n"
            f"- Source: {ref.source}\n\n"
            f"{self.notes}".strip()
        )


@dataclass(frozen=True)
class VerdictResult:
    """Outcome of comparing the persona's observed value to the reference."""

    passed: bool
    metric: str
    observed: float | None
    reference: float
    tolerance: float
    tolerance_kind: ToleranceKind
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "metric": self.metric,
            "observed": self.observed,
            "reference": self.reference,
            "tolerance": self.tolerance,
            "tolerance_kind": self.tolerance_kind,
            "detail": self.detail,
        }


def load_brief(path: Path) -> CaseBrief:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    ref_raw = raw["reference"]
    reference = Reference(
        metric=str(ref_raw["metric"]),
        value=float(ref_raw["value"]),
        tolerance=float(ref_raw["tolerance"]),
        tolerance_kind=ref_raw.get("tolerance_kind", "rel"),
        source=str(ref_raw.get("source", "unspecified")),
    )
    return CaseBrief(
        case_id=str(raw["case_id"]),
        title=str(raw["title"]),
        geometry=str(raw["geometry"]),
        physics=dict(raw.get("physics", {}) or {}),
        question=str(raw["question"]),
        reference=reference,
        notes=str(raw.get("notes", "") or ""),
    )


def check_verdict(brief: CaseBrief, observed: float | None) -> VerdictResult:
    """Compare observed value to brief reference; tolerate `None` (drop)."""
    ref = brief.reference
    if observed is None:
        return VerdictResult(
            passed=False,
            metric=ref.metric,
            observed=None,
            reference=ref.value,
            tolerance=ref.tolerance,
            tolerance_kind=ref.tolerance_kind,
            detail="persona did not produce an observed value (drop or error)",
        )
    passed = ref.passes(observed)
    if ref.tolerance_kind == "rel":
        if ref.value == 0.0:
            err = abs(observed)
            err_pct = err  # tolerance interpreted as absolute fallback
        else:
            err_pct = abs(observed - ref.value) / abs(ref.value)
        detail = (
            f"observed={observed:g}, reference={ref.value:g}, "
            f"err={err_pct:.4f} (tol={ref.tolerance:.4f} relative)"
        )
    else:
        err = abs(observed - ref.value)
        detail = (
            f"observed={observed:g}, reference={ref.value:g}, "
            f"err={err:g} (tol={ref.tolerance:g} absolute)"
        )
    return VerdictResult(
        passed=passed,
        metric=ref.metric,
        observed=observed,
        reference=ref.value,
        tolerance=ref.tolerance,
        tolerance_kind=ref.tolerance_kind,
        detail=detail,
    )


__all__ = [
    "CaseBrief",
    "Reference",
    "VerdictResult",
    "check_verdict",
    "load_brief",
]

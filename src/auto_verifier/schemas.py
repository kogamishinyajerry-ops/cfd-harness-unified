"""Serializable schemas for AutoVerifier reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConvergenceReport:
    status: str
    final_residual: Optional[float]
    target_residual: float
    residual_ratio: Optional[float]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "final_residual": self.final_residual,
            "target_residual": self.target_residual,
            "residual_ratio": self.residual_ratio,
            "warnings": list(self.warnings),
        }


@dataclass
class ObservableCheck:
    name: str
    ref_value: Any
    sim_value: Any
    rel_error: Optional[float]
    abs_error: Optional[float]
    tolerance: Any
    within_tolerance: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ref_value": self.ref_value,
            "sim_value": self.sim_value,
            "rel_error": self.rel_error,
            "abs_error": self.abs_error,
            "tolerance": self.tolerance,
            "within_tolerance": self.within_tolerance,
        }


@dataclass
class GoldStandardComparison:
    overall: str
    observables: List[ObservableCheck] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "observables": [observable.to_dict() for observable in self.observables],
            "warnings": list(self.warnings),
        }


@dataclass
class PhysicsCheck:
    status: str
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "warnings": list(self.warnings),
        }


@dataclass
class CorrectionSuggestion:
    primary_cause: str
    confidence: str
    suggested_correction: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_cause": self.primary_cause,
            "confidence": self.confidence,
            "suggested_correction": self.suggested_correction,
        }


@dataclass
class AutoVerifyReport:
    case_id: str
    timestamp: str
    convergence: ConvergenceReport
    gold_standard_comparison: GoldStandardComparison
    physics_check: PhysicsCheck
    verdict: str
    correction_spec_needed: bool
    correction_spec: Optional[CorrectionSuggestion]
    out_of_scope_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "case_id": self.case_id,
            "timestamp": self.timestamp,
            "convergence": self.convergence.to_dict(),
            "gold_standard_comparison": self.gold_standard_comparison.to_dict(),
            "physics_check": self.physics_check.to_dict(),
            "verdict": self.verdict,
            "correction_spec_needed": self.correction_spec_needed,
            "correction_spec": None if self.correction_spec is None else self.correction_spec.to_dict(),
        }
        if self.out_of_scope_reason is not None:
            data["out_of_scope_reason"] = self.out_of_scope_reason
        return data


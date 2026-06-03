"""P3 W3.3a · CHT straight-fin analytical gate (``cht_analytical``, Control Plane).

Comparator wiring for the straight-fin coverage benchmark: extract the fin QoIs
from a solved case (Execution Plane, ``src.cht_fin_extractor``) and gate them
against the closed-form reference in
``knowledge/gold_standards/cht_straight_fin.yaml`` via the canonical
``ResultComparator`` (Evaluation Plane). This is the ``cht_analytical`` gate
mode: it reuses the existing scalar-tolerance comparison path (no bespoke
comparator) — the only fin-specific code is the extractor and this thin
orchestration.

ADR-001 plane assignment: **Control Plane**. Control is the only plane permitted
to import BOTH Execution (the extractor) and Evaluation (the comparator) — the
same posture as ``src.task_runner``, which builds an ``ExecutionResult`` and
hands it to ``ResultComparator``. The fin geometry / BC inputs are sourced from
the gold's ``case_info.fin_inputs`` (the SAME contract the self-verifying
derivation test locks), so the gate carries no independent magic numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from .cht_fin_extractor import (
    FinConductionQoIs,
    extract_fin_qois,
    to_key_quantities,
)
from .models import ComparisonResult, ExecutionResult
from .result_comparator import ResultComparator

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_GOLD = _REPO_ROOT / "knowledge" / "gold_standards" / "cht_straight_fin.yaml"


@dataclass(frozen=True)
class FinGateResult:
    """Outcome of gating the extracted QoIs against the analytical gold."""

    passed: bool
    qois: FinConductionQoIs
    comparisons: List[Tuple[str, ComparisonResult]]
    summary: str


def _load_fin_gold_docs(gold_path: Path) -> List[Dict[str, Any]]:
    docs = [d for d in yaml.safe_load_all(gold_path.read_text(encoding="utf-8")) if d]
    if not docs:
        raise ValueError(f"empty / unparseable gold standard: {gold_path}")
    return docs


def gate_fin_against_gold(
    case_dir: Path,
    gold_path: Path = _DEFAULT_GOLD,
) -> FinGateResult:
    """Run the ``cht_analytical`` gate: extract QoIs, compare vs the gold.

    Each gold doc (one per ``quantity``) is compared via the canonical
    scalar-tolerance path in :class:`ResultComparator`; the gate PASSES only if
    every observable is within its tolerance.
    """
    docs = _load_fin_gold_docs(gold_path)
    fin_inputs = docs[0]["case_info"]["fin_inputs"]
    qois = extract_fin_qois(
        case_dir,
        h_conv=float(fin_inputs["h_conv"]),
        w=float(fin_inputs["w"]),
        t=float(fin_inputs["t"]),
        L=float(fin_inputs["L"]),
        T_inf=float(fin_inputs["T_inf"]),
    )
    result = ExecutionResult(
        success=True,
        is_mock=False,
        key_quantities=to_key_quantities(qois),
    )

    comparator = ResultComparator()
    comparisons: List[Tuple[str, ComparisonResult]] = []
    for doc in docs:
        gold = {
            "quantity": doc["quantity"],
            "reference_values": doc["reference_values"],
            "tolerance": doc.get("tolerance", 0.05),
            "id": doc.get("case_info", {}).get("id"),
        }
        comparisons.append((doc["quantity"], comparator.compare(result, gold)))

    passed = all(cmp.passed for _, cmp in comparisons)
    parts = [f"{name}={'PASS' if cmp.passed else 'FAIL'}" for name, cmp in comparisons]
    summary = (
        f"cht_analytical gate {'PASS' if passed else 'FAIL'} "
        f"(eta={qois.fin_efficiency:.5f}, tip={qois.fin_tip_temperature_ratio:.5f}, "
        f"energy_residual={qois.energy_residual_w:.3e} W) | " + ", ".join(parts)
    )
    return FinGateResult(passed=passed, qois=qois, comparisons=comparisons, summary=summary)

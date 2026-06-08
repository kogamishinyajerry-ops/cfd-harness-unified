"""P4 V71.B · low-Re k-omega-SST backward-facing-step gate (``backward_facing_step_lowre``, Control Plane).

Comparator wiring for the wall-RESOLVED (y+<1) backward-facing-step reattachment
anchor: extract the reattachment QoI + the floor y+ from a solved case (Execution
Plane, ``src.bfs_lowre_extractor``) and gate them against the blended engineering
anchor (Xr/H=6.26, 10% tolerance) in
``knowledge/gold_standards/backward_facing_step_lowre.yaml`` via the canonical
``ResultComparator`` (Evaluation Plane), backstopped by independent hard gates.

Why a SPECIALIZED gate (not the generic residual comparator)
------------------------------------------------------------
The high-Re ``backward_facing_step`` anchor rides the generic comparator on its
inline reattachment gold — and that alone is correct THERE. The low-Re sibling's
distinguishing claim is the *resolved near-wall regime* (y+<1, integrate-to-wall),
which is the whole reason the case exists; the reattachment-within-tolerance check
is shared verbatim with the high-Re case and proves nothing new about resolution.
Per the V&V review (DEC-V61-235), a "validated low-Re resolved" verdict therefore
MUST machine-ENFORCE the y+<1 precondition, fail-closed — attesting it in prose
would let a future regression to a coarse / wall-functioned mesh keep the
"resolved" badge while still passing the reattachment check. Three independent
hard gates backstop the comparator tolerance:

  1. **Resolved near-wall** — ``floor_yplus_max < 1`` over the reattachment-floor
     faces (the SAME faces the reattachment QoI is measured on, shared mask). This
     is the DEFINING property of the slice; the high-Re mesh measures ~4.2 here
     and would (correctly) FAIL. The step-corner singularity (y+~3.4) and the
     attached upper wall (y+~200) are NOT read by this gate — they are outside the
     floor mask and disclosed in the gold's physics_contract.
  2. **Single clean reattachment** — exactly one wall-shear tau_x pos→neg crossing
     on the floor. A doctored / multi-bubble field that conjures extra crossings
     (or an extractor that picked the wrong feature) is caught here, independent
     of whether the first crossing happened to land in tolerance.
  3. **Floor mask non-degenerate** — at least ``_MIN_FLOOR_FACES`` faces survived
     the mask, so the verdict rests on a resolved reattachment region, not a
     handful of faces from a malformed mesh.

ADR-001 plane assignment: **Control Plane** — the only plane permitted to import
BOTH Execution (the extractor) and Evaluation (the comparator), same posture as
``src.task_runner`` / ``src.wedge_oblique_shock_gate`` / ``src.cht_conjugate_gate``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .bfs_lowre_extractor import BfsLowReMetrics, extract_bfs_lowre, to_key_quantities
from .models import ComparisonResult, ExecutionResult
from .result_comparator import ResultComparator

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_GOLD = (
    _REPO_ROOT / "knowledge" / "gold_standards" / "backward_facing_step_lowre.yaml"
)

# The DEFINING resolved-wall precondition: first-cell y+ over the reattachment
# floor must be below 1 (integrate-to-wall, no log-layer reliance). The high-Re
# wall-function mesh measures ~4.2 here and FAILS this gate by design.
_RESOLVED_YPLUS_MAX: float = 1.0

# A resolved BFS floor (ncx_B=120 downstream cells) yields ~119 masked floor
# faces; require a generous floor so a malformed / under-resolved mesh cannot
# pass on a handful of faces.
_MIN_FLOOR_FACES: int = 50


@dataclass(frozen=True)
class BfsLowReGateResult:
    """Outcome of gating the resolved low-Re BFS QoIs against the gold."""

    passed: bool
    metrics: BfsLowReMetrics
    comparison: ComparisonResult
    reattachment_within_tol: bool    # generic comparator vs Xr/H=6.26 ± 10%
    resolved_near_wall_ok: bool      # floor y+ max < 1 (the resolved precondition)
    single_reattachment_ok: bool     # exactly one wall-shear pos→neg crossing
    floor_mask_nondegenerate_ok: bool  # enough floor faces survived the mask
    summary: str


def _load_bfs_lowre_gold(gold_path: Path) -> Dict[str, Any]:
    docs = [d for d in yaml.safe_load_all(gold_path.read_text(encoding="utf-8")) if d]
    if not docs:
        raise ValueError(f"empty / unparseable gold standard: {gold_path}")
    # the reattachment_length doc is authoritative (there is one observable here)
    for doc in docs:
        if doc.get("quantity") == "reattachment_length":
            return doc
    return docs[0]


def gate_bfs_lowre_against_gold(
    case_dir: Path,
    gold_path: Path = _DEFAULT_GOLD,
) -> BfsLowReGateResult:
    """Run the ``backward_facing_step_lowre`` gate.

    PASSES only if (a) reattachment is within the gold tolerance via the canonical
    comparator, AND (b) all three independent hard gates hold. Any extraction
    failure propagates as an exception (an honest FAIL upstream) — never a
    fabricated pass.
    """
    doc = _load_bfs_lowre_gold(gold_path)
    metrics = extract_bfs_lowre(Path(case_dir))

    result = ExecutionResult(
        success=True,
        is_mock=False,
        key_quantities=to_key_quantities(metrics),
    )
    gold = {
        "quantity": doc["quantity"],
        "reference_values": doc["reference_values"],
        "tolerance": doc.get("tolerance", 0.10),
        "id": doc.get("case_info", {}).get("id"),
    }
    comparator = ResultComparator()
    comparison = comparator.compare(result, gold)
    reattachment_within_tol = comparison.passed

    resolved_near_wall_ok = metrics.floor_yplus_max < _RESOLVED_YPLUS_MAX
    single_reattachment_ok = metrics.n_pos_neg_crossings == 1
    floor_mask_nondegenerate_ok = metrics.n_floor_faces >= _MIN_FLOOR_FACES

    passed = (
        reattachment_within_tol
        and resolved_near_wall_ok
        and single_reattachment_ok
        and floor_mask_nondegenerate_ok
    )

    ref = float(doc["reference_values"][0]["value"])
    pct = 100.0 * (metrics.reattachment_xr_h / ref - 1.0) if ref else float("nan")
    parts: List[str] = [
        f"reattachment_within_tol={'PASS' if reattachment_within_tol else 'FAIL'}",
        f"resolved_near_wall={'PASS' if resolved_near_wall_ok else 'FAIL'}",
        f"single_reattachment={'PASS' if single_reattachment_ok else 'FAIL'}",
        f"floor_mask_nondegenerate={'PASS' if floor_mask_nondegenerate_ok else 'FAIL'}",
    ]
    summary = (
        f"backward_facing_step_lowre gate {'PASS' if passed else 'FAIL'} "
        f"(Xr/H={metrics.reattachment_xr_h:.4f} = {pct:+.2f}% vs {ref:g}, "
        f"floor y+ max={metrics.floor_yplus_max:.4f} (<{_RESOLVED_YPLUS_MAX:g} resolved), "
        f"crossings={metrics.n_pos_neg_crossings}, floor_faces={metrics.n_floor_faces}, "
        f"method={metrics.reattachment_method}) | " + ", ".join(parts)
    )
    return BfsLowReGateResult(
        passed=passed,
        metrics=metrics,
        comparison=comparison,
        reattachment_within_tol=reattachment_within_tol,
        resolved_near_wall_ok=resolved_near_wall_ok,
        single_reattachment_ok=single_reattachment_ok,
        floor_mask_nondegenerate_ok=floor_mask_nondegenerate_ok,
        summary=summary,
    )

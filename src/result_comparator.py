"""结果 vs Gold Standard 对比器"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .models import ComparisonResult, DeviationDetail, ExecutionResult

logger = logging.getLogger(__name__)


# Canonical → aliases map for the ACTUAL side of comparison.
#
# Problem: gold_standards declare quantities by canonical name (e.g. "friction_factor"),
# but the solver / postProcessing layer writes under various historical names
# ("f", "fDarcy", etc.). Without this table, ResultComparator returned
# "Quantity 'friction_factor' not found in execution result" and flagged the
# correction as COMPARATOR_SCHEMA_MISMATCH (see knowledge/corrections/ —
# 4× pipe friction_factor, 6× u_mean_profile, etc.).
#
# Governance: this is *naming-layer* infrastructure (src/ turf, autonomous per
# DEC-V61-003). Does NOT modify knowledge/gold_standards/ or knowledge/whitelist.yaml.
# Each alias set should be defensible from published solver/postProcessing
# conventions — do not paper over real physics mismatches here.
CANONICAL_ALIASES: Dict[str, Tuple[str, ...]] = {
    # Darcy friction factor: solver may emit "f" (single letter),
    # "fDarcy" (OpenFOAM turbulence function object), or "fFanning" (4× smaller).
    # Do NOT include fFanning here — unit conversion is not an alias.
    "friction_factor":    ("f", "fDarcy", "darcy_f", "darcyFrictionFactor"),
    # Skin friction: OpenFOAM wallShearStress function object typically yields "Cf".
    "cf_skin_friction":   ("Cf", "cf", "skin_friction", "skinFriction"),
    # Pressure coefficient: Cp / cp / p_coeff all seen in the wild.
    "pressure_coefficient": ("Cp", "cp", "p_coeff", "pressureCoefficient"),
    # Nusselt: averaged over a patch is often "Nu_avg" / "averageNu".
    "nusselt_number":     ("Nu", "Nu_avg", "Nu_mean", "averageNu", "nu_avg"),
    # Strouhal: sometimes derived post-run and named "St" or "strouhal".
    "strouhal_number":    ("St", "strouhal", "shedding_St"),
    # Reattachment length in BFS: case-specific shorthand.
    "reattachment_length": ("Xr_over_H", "reattachment_x", "xr_H"),
    # Lid-driven cavity u-profile: legacy sampleDict set name "uCenterline".
    # (adapter already does this rename for LDC specifically — redundancy is safe
    # and covers solvers that bypass the adapter's case-specific branch.)
    "u_centerline":       ("uCenterline", "U_centerline", "u_profile_centerline"),
    # DNS channel u+ profile.
    "u_mean_profile":     ("u_plus", "u_plus_profile", "u_plus_mean", "uPlusProfile"),
}


def _lookup_with_alias(
    key_quantities: Dict[str, Any],
    canonical: str,
) -> Tuple[Optional[Any], Optional[str]]:
    """Return (value, key_used). Canonical name wins; fall through aliases.

    Returns (None, None) when no match — caller should report the *canonical*
    name in error messages so users see what gold expected, not what adapter emitted.
    """
    direct = key_quantities.get(canonical)
    if direct is not None:
        return direct, canonical
    for alias in CANONICAL_ALIASES.get(canonical, ()):
        if alias in key_quantities:
            value = key_quantities[alias]
            if value is not None:
                logger.debug(
                    "ResultComparator: resolved %r via alias %r", canonical, alias
                )
                return value, alias
    return None, None


class ResultComparator:
    """对比 ExecutionResult 与 Gold Standard

    支持标量比较（单个数值）和向量比较（列表，取最大偏差）。
    """

    def __init__(self, threshold: float = 0.10) -> None:
        """
        Args:
            threshold: 默认相对误差阈值（0.10 = 10%），
                       whitelist 中有显式 tolerance 时以 whitelist 为准。
        """
        self._default_threshold = threshold

    def compare(
        self,
        result: ExecutionResult,
        gold: Dict[str, Any],
    ) -> ComparisonResult:
        """执行对比，返回 ComparisonResult"""
        quantity_key = gold.get("quantity")
        if quantity_key is None:
            logger.warning("Gold standard missing 'quantity' key, skipping comparison")
            return ComparisonResult(passed=True, summary="No gold standard quantity defined")

        # Alias-aware lookup: canonical name → fallback aliases (see CANONICAL_ALIASES).
        # resolved_key is the *actual* key under which the value was stored; we use
        # it for axis resolution below (so "Cp" as alias still finds "Cp_x" companion).
        actual_value, resolved_key = _lookup_with_alias(result.key_quantities, quantity_key)
        if actual_value is None:
            deviation = DeviationDetail(
                quantity=quantity_key,
                expected=gold.get("reference_values"),
                actual=None,
            )
            # Include available keys in the summary to help debug adapter-vs-gold
            # naming drift without grepping logs.
            available = sorted(k for k in result.key_quantities.keys() if not k.endswith(("_x", "_y", "_z")))
            return ComparisonResult(
                passed=False,
                deviations=[deviation],
                summary=(
                    f"Quantity '{quantity_key}' not found in execution result "
                    f"(tried aliases: {CANONICAL_ALIASES.get(quantity_key, ())}; "
                    f"available scalar keys: {available})"
                ),
            )

        tolerance = gold.get("tolerance", self._default_threshold)
        reference_values = gold.get("reference_values", [])
        deviations: List[DeviationDetail] = []

        if isinstance(actual_value, list) and reference_values:
            # Axis resolution uses the *resolved* key name so a canonical-vs-alias
            # mismatch on the value side doesn't then break companion coord lookup.
            # E.g. canonical="pressure_coefficient" resolved via alias="Cp" still
            # looks up "Cp_x" correctly here.
            actual_coords, reference_coords, coord_label = self._resolve_profile_axis(
                resolved_key or quantity_key, result.key_quantities, reference_values
            )
            deviations = self._compare_vector(
                quantity_key,
                actual_value,
                reference_values,
                tolerance,
                actual_coords=actual_coords,
                reference_coords=reference_coords,
                coord_label=coord_label,
            )
        elif isinstance(actual_value, (int, float)) and reference_values:
            deviations = self._compare_scalar(quantity_key, actual_value, reference_values, tolerance)
        else:
            logger.debug("Cannot compare quantity '%s': type mismatch or missing reference", quantity_key)

        passed = len(deviations) == 0
        summary_parts = [f"Quantity: {quantity_key}", f"Tolerance: {tolerance:.1%}"]
        if not passed:
            summary_parts.append(f"Failed: {len(deviations)} deviation(s)")
        else:
            summary_parts.append("PASS")

        return ComparisonResult(
            passed=passed,
            deviations=deviations,
            summary=" | ".join(summary_parts),
            gold_standard_id=gold.get("id"),
        )

    # ------------------------------------------------------------------
    # 内部比较方法
    # ------------------------------------------------------------------

    def _compare_scalar(
        self,
        quantity: str,
        actual: float,
        reference_values: List[Dict[str, Any]],
        tolerance: float,
    ) -> List[DeviationDetail]:
        """标量比较：从 reference_values 取第一个 value"""
        deviations = []
        for ref in reference_values:
            _v = ref.get("value")
            if _v is None: _v = ref.get("Nu")
            if _v is None: _v = ref.get("Cp")
            if _v is None: _v = ref.get("Cf")
            if _v is None: _v = ref.get("u_plus")
            if _v is None: _v = ref.get("f")
            expected = _v
            if expected is None:
                continue
            abs_err = abs(actual - expected)
            # Near-zero reference: use absolute error instead of relative.
            # When ref ≈ 0, |actual-ref|/|ref| → ∞ even for small |actual|.
            # Fallback: |error| <= tolerance * max(|ref|, 1.0) treats near-zero like regular.
            if abs(expected) < 1e-6:
                err = abs_err
            else:
                err = abs_err / (abs(expected) + 1e-12)
            if err > tolerance:
                deviations.append(DeviationDetail(
                    quantity=quantity,
                    expected=expected,
                    actual=actual,
                    relative_error=err,
                    tolerance=tolerance,
                ))
            break  # 标量只比较第一个参考值
        return deviations

    def _compare_vector(
        self,
        quantity: str,
        actual_list: List[float],
        reference_values: List[Dict[str, Any]],
        tolerance: float,
        actual_coords: Optional[List[float]] = None,
        reference_coords: Optional[List[float]] = None,
        coord_label: Optional[str] = None,
    ) -> List[DeviationDetail]:
        """向量比较：支持按 profile 坐标插值比较。

        如果 actual_coords 提供（与 actual_list 等长），则在 Gold Standard 的 profile 坐标位置
        对 actual_list 进行线性插值后再比较。
        否则退化为 index-based positional matching。
        """
        deviations = []
        # DEC-V61-036c G2: extended ref-scalar key lookup to close the
        # last schema-level PASS-washing path. plane_channel_flow gold
        # has `{y_plus: ..., u_plus: ...}` tuples — the prior key set
        # {u, value, Nu, Cp, Cf, f} all returned None for every tuple,
        # so comparator silently produced zero deviations and PASSed.
        # Added u_plus (DNS profile) + other known gold-dict scalar keys
        # per Codex DEC-036 round-1 B2 finding.
        _REF_SCALAR_KEYS = ("u", "u_plus", "value", "Nu", "Cp", "Cf", "f", "St")

        def _pick_ref_scalar(r: Dict[str, Any]) -> Optional[float]:
            for k in _REF_SCALAR_KEYS:
                v = r.get(k)
                if v is not None:
                    return v
            return None

        ref_scalars = [_pick_ref_scalar(r) for r in reference_values]
        ref_axis = reference_coords or [None for _ in reference_values]

        # 坐标感知插值比较：只有当 actual_coords 可用且 reference 有同轴坐标时才启用
        use_interp = (
            actual_coords is not None
            and len(actual_coords) == len(actual_list)
            and all(coord is not None for coord in ref_axis)
        )

        if use_interp:
            # 构建 actual profile 并在 Gold Standard 坐标位置插值
            actual_pairs = sorted(zip(actual_coords, actual_list))
            act_axis_sorted = [p[0] for p in actual_pairs]
            act_value_sorted = [p[1] for p in actual_pairs]

            for ref_coord, ref_u in zip(ref_axis, ref_scalars):
                if ref_u is None:
                    continue
                # 线性插值
                sim_u = self._interp1d(act_axis_sorted, act_value_sorted, ref_coord)
                abs_err = abs(sim_u - ref_u)
                if abs(ref_u) < 1e-6:
                    err = abs_err
                else:
                    err = abs_err / (abs(ref_u) + 1e-12)
                if err > tolerance:
                    axis_name = coord_label or "coord"
                    coord_text = (
                        f"{ref_coord:.4f}" if isinstance(ref_coord, (int, float)) else str(ref_coord)
                    )
                    deviations.append(DeviationDetail(
                        quantity=f"{quantity}[{axis_name}={coord_text}]",
                        expected=ref_u,
                        actual=sim_u,
                        relative_error=err,
                        tolerance=tolerance,
                    ))
        else:
            # Fallback: positional matching
            for i, (act, ref) in enumerate(zip(actual_list, ref_scalars)):
                if ref is None:
                    continue
                abs_err = abs(act - ref)
                if abs(ref) < 1e-6:
                    err = abs_err
                else:
                    err = abs_err / (abs(ref) + 1e-12)
                if err > tolerance:
                    deviations.append(DeviationDetail(
                        quantity=f"{quantity}[{i}]",
                        expected=ref,
                        actual=act,
                        relative_error=err,
                        tolerance=tolerance,
                    ))
        return deviations

    @staticmethod
    def _resolve_profile_axis(
        quantity: str,
        key_quantities: Dict[str, Any],
        reference_values: List[Dict[str, Any]],
    ) -> Tuple[Optional[List[float]], Optional[List[float]], Optional[str]]:
        """Resolve a shared coordinate axis for profile comparison.

        Supports the current y-aware centerline case plus x-based profiles such as
        `pressure_coefficient_x` vs `x_over_c`.
        """
        axis_candidates = [
            (f"{quantity}_y", "y"),
            # DEC-V61-036c G2: plane_channel u+/y+ DNS profile. Gold has
            # `y_plus` as the reference axis; the adapter emits
            # `u_mean_profile_y_plus` (or its alias `y_plus`) as the
            # actual axis. Without this candidate, axis resolution fell
            # through to positional matching and the comparator silently
            # did not honestly compare u+ against y+.
            (f"{quantity}_y_plus", "y_plus"),
            ("y_plus", "y_plus"),
            (f"{quantity}_x", "x"),
            (f"{quantity}_x", "x_over_c"),
            (f"{quantity}_x", "x_D"),
            (f"{quantity}_x", "x_H"),
            # Codex DEC-036c review pointed out: impinging_jet gold emits
            # `r_over_d`, not `r_D` — axis resolver missed the live key.
            # Pre-existing gap (not introduced by G2), fixed here.
            (f"{quantity}_x", "r_over_d"),
            (f"{quantity}_x", "r_D"),
            (f"{quantity}_x", "r"),
        ]

        for actual_key, reference_key in axis_candidates:
            actual_coords = key_quantities.get(actual_key)
            reference_coords = [ref.get(reference_key) for ref in reference_values]
            if (
                actual_coords is not None
                and isinstance(actual_coords, list)
                and all(coord is not None for coord in reference_coords)
            ):
                return actual_coords, reference_coords, reference_key

        return None, None, None

    @staticmethod
    def _interp1d(xs: List[float], ys: List[float], x_target: float) -> float:
        """线性插值。xs 必须单调递增。"""
        if x_target <= xs[0]:
            return ys[0]
        if x_target >= xs[-1]:
            return ys[-1]
        for k in range(len(xs) - 1):
            if xs[k] <= x_target <= xs[k + 1]:
                if xs[k + 1] == xs[k]:
                    return ys[k]
                frac = (x_target - xs[k]) / (xs[k + 1] - xs[k])
                return ys[k] + frac * (ys[k + 1] - ys[k])
        return ys[-1]

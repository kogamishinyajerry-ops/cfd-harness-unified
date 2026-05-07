"""DEC-V61-150 (N4.5) · controlDict timing schema + advisor tests.

Coverage:
  * Schema field validators (positivity, max_co bounds, write_interval
    sanity cap)
  * Empty timing → empty hints
  * Steady solver + transient-only fields → info hints
  * Transient solver: max_co with adjust=False → info; adjust=True
    without max_co → warning
  * write_interval > end_time → info hint (regime-agnostic)
  * Hint sort: warning first, then info; alpha by target
  * V130 advisory-only: timing_advisor module is NOT in
    KNOWN_MUTATION_FUNCTIONS
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ui.backend.schemas.control_dict_timing import ControlDictTiming
from ui.backend.services.case_solve.timing_advisor import (
    TimingHint,
    derive_timing_hints,
)


def _empty_timing() -> ControlDictTiming:
    return ControlDictTiming(authored_at="2026-05-07T12:00:00Z")


# ────────── Schema validators ──────────


def test_end_time_must_be_strictly_positive():
    ControlDictTiming(end_time=10.0, authored_at="2026-05-07T12:00:00Z")
    with pytest.raises(ValidationError):
        ControlDictTiming(end_time=0.0, authored_at="2026-05-07T12:00:00Z")
    with pytest.raises(ValidationError):
        ControlDictTiming(end_time=-1.0, authored_at="2026-05-07T12:00:00Z")


def test_write_interval_strictly_positive():
    ControlDictTiming(write_interval=0.5, authored_at="2026-05-07T12:00:00Z")
    with pytest.raises(ValidationError):
        ControlDictTiming(
            write_interval=0.0, authored_at="2026-05-07T12:00:00Z",
        )


def test_write_interval_huge_value_rejected():
    """Defensive: huge write_interval suggests unit mistake."""
    with pytest.raises(ValidationError):
        ControlDictTiming(
            write_interval=1.0e7,  # > 1e6 cap
            authored_at="2026-05-07T12:00:00Z",
        )


def test_max_co_bounded_zero_to_ten():
    ControlDictTiming(max_co=1.0, authored_at="2026-05-07T12:00:00Z")
    ControlDictTiming(max_co=10.0, authored_at="2026-05-07T12:00:00Z")
    with pytest.raises(ValidationError):
        ControlDictTiming(max_co=0.0, authored_at="2026-05-07T12:00:00Z")
    with pytest.raises(ValidationError):
        ControlDictTiming(max_co=10.1, authored_at="2026-05-07T12:00:00Z")


def test_delta_t_strictly_positive():
    ControlDictTiming(delta_t=0.001, authored_at="2026-05-07T12:00:00Z")
    with pytest.raises(ValidationError):
        ControlDictTiming(delta_t=0.0, authored_at="2026-05-07T12:00:00Z")


def test_adjust_time_step_optional_bool():
    ControlDictTiming(adjust_time_step=True, authored_at="2026-05-07T12:00:00Z")
    ControlDictTiming(adjust_time_step=False, authored_at="2026-05-07T12:00:00Z")
    ControlDictTiming(adjust_time_step=None, authored_at="2026-05-07T12:00:00Z")


def test_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        ControlDictTiming(
            authored_at="2026-05-07T12:00:00Z", mystery="oops",
        )


# ────────── Advisor: empty / coherent ──────────


def test_advisor_empty_timing_yields_no_hints():
    hints = derive_timing_hints(timing=_empty_timing(), solver="simpleFoam")
    assert hints == []


def test_advisor_coherent_transient_yields_no_hints():
    timing = ControlDictTiming(
        end_time=10.0,
        write_interval=0.5,
        adjust_time_step=True,
        max_co=1.0,
        authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="pimpleFoam")
    assert hints == []


def test_advisor_coherent_steady_yields_no_hints():
    timing = ControlDictTiming(
        end_time=2000.0,
        write_interval=100.0,
        authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="simpleFoam")
    assert hints == []


# ────────── Advisor: steady solver + transient-only fields ──────────


def test_steady_solver_with_max_co_set_emits_info():
    timing = ControlDictTiming(
        max_co=1.0, authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="simpleFoam")
    assert len(hints) == 1
    assert hints[0].target == "max_co"
    assert hints[0].severity == "info"
    assert "steady" in hints[0].message


def test_steady_solver_with_adjust_time_step_set_emits_info():
    timing = ControlDictTiming(
        adjust_time_step=True, authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="buoyantSimpleFoam")
    info_hints = [h for h in hints if h.target == "adjust_time_step"]
    assert len(info_hints) == 1
    assert info_hints[0].severity == "info"


def test_steady_solver_with_delta_t_set_emits_info():
    timing = ControlDictTiming(
        delta_t=0.001, authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="simpleFoam")
    info_hints = [h for h in hints if h.target == "delta_t"]
    assert len(info_hints) == 1


# ────────── Advisor: transient solver coherence ──────────


def test_transient_max_co_with_adjust_false_emits_info():
    timing = ControlDictTiming(
        adjust_time_step=False,
        max_co=1.0,
        authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="pimpleFoam")
    info_hints = [h for h in hints if h.target == "max_co"]
    assert len(info_hints) == 1
    assert info_hints[0].severity == "info"


def test_transient_adjust_true_without_max_co_emits_warning():
    timing = ControlDictTiming(
        adjust_time_step=True, authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="pimpleFoam")
    warning_hints = [h for h in hints if h.severity == "warning"]
    assert len(warning_hints) == 1
    assert warning_hints[0].target == "max_co"


# ────────── Advisor: write_interval vs end_time ──────────


def test_write_interval_above_end_time_emits_info():
    timing = ControlDictTiming(
        end_time=10.0,
        write_interval=20.0,  # > end_time
        authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="pimpleFoam")
    info_hints = [
        h for h in hints if h.target == "write_interval" and h.severity == "info"
    ]
    assert len(info_hints) == 1


# ────────── Advisor: sort order ──────────


def test_warnings_sort_before_info():
    timing = ControlDictTiming(
        end_time=10.0,
        write_interval=20.0,    # info: write_interval > end_time
        adjust_time_step=True,  # warning: adjust=True but max_co unset
        authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="pimpleFoam")
    severities = [h.severity for h in hints]
    rank = {"warning": 0, "info": 1}
    for i in range(len(severities) - 1):
        assert rank[severities[i]] <= rank[severities[i + 1]]


def test_within_severity_alpha_by_target():
    """Steady solver with all three transient-only fields set emits
    three info hints — they should appear sorted alphabetically by
    target."""
    timing = ControlDictTiming(
        adjust_time_step=True,
        max_co=1.0,
        delta_t=0.001,
        authored_at="2026-05-07T12:00:00Z",
    )
    hints = derive_timing_hints(timing=timing, solver="simpleFoam")
    targets = [h.target for h in hints]
    assert targets == sorted(targets)


# ────────── V130 advisory-only contract ──────────


def test_timing_advisor_not_in_known_mutation_functions():
    """V130 Principle B: advisor is read-only. derive_timing_hints
    MUST NOT appear in KNOWN_MUTATION_FUNCTIONS."""
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    for module, symbol in KNOWN_MUTATION_FUNCTIONS:
        assert symbol != "derive_timing_hints"
        assert "timing_advisor" not in module

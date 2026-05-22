"""DEC-V61-202-SUB-M30-CYCLE3 · focus_patch driver tests.

Coverage:
    1. focus_patch unset → no focus bias (existing behavior preserved)
    2. focus_patch="inlet" + multi-patch FAIL findings → rail picks inlet
    3. focus_patch="inlet" + bottom_cards reordered so inlet cards bubble up
    4. focus_patch="inlet" + bc_audit gaps_by_field mentions inlet → matched
    5. focus_patch=non-existent patch → graceful fallback (no errors, items[0])
    6. focus_matches uses field_path substring (vof_contract.inlet.* matches)
    7. focus_matches uses body_text substring
"""
from __future__ import annotations

from ui.backend.schemas.workbench_frame import CaseStateSnapshot
from ui.backend.services.workbench_decide import decide


def _state(**kwargs) -> CaseStateSnapshot:
    base = {
        "case_id": "x",
        "step": 4,
        "manifest": {},
        "artifacts": {},
        "completeness": None,
    }
    base.update(kwargs)
    return CaseStateSnapshot(**base)


def _make_findings(patches_by_severity):
    """Build a `findings` list with one entry per (patch, severity)."""
    out = []
    for patch, severity in patches_by_severity:
        out.append({
            "severity": severity,
            "title": f"BC missing on {patch}",
            "message": f"Expected fields not declared on patch={patch}",
            "field_path": f"bc_contract.{patch}.velocity",
        })
    return out


def test_no_focus_no_bias():
    """focus_patch unset → rail picks first severity-sorted item."""
    state = _state(
        artifacts={
            "bc_quality.json": {
                "findings": _make_findings([
                    ("inlet", "fail"),
                    ("outlet", "fail"),
                ]),
            }
        },
    )
    frame = decide(state)
    # No focus_patch → existing severity-sort order; first FAIL wins.
    assert frame.rail_primary.kind == "problem_fix"
    # The order is whatever severity-sort gives — should be one of them.
    assert frame.rail_primary.title in (
        "BC missing on inlet",
        "BC missing on outlet",
    )


def test_focus_inlet_promotes_inlet_problem_in_rail():
    """focus_patch='inlet' + same-severity items → inlet wins."""
    state = _state(
        focus_patch="inlet",
        artifacts={
            "bc_quality.json": {
                "findings": _make_findings([
                    ("outlet", "fail"),
                    ("inlet", "fail"),
                    ("wall", "fail"),
                ]),
            }
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "problem_fix"
    assert "inlet" in frame.rail_primary.title


def test_focus_inlet_bubbles_inlet_card_to_top():
    """focus_patch='inlet' → bottom_cards' inlet entry comes before
    non-inlet entries (within same severity bucket)."""
    state = _state(
        focus_patch="inlet",
        artifacts={
            "bc_quality.json": {
                "findings": _make_findings([
                    ("outlet", "warn"),
                    ("wall", "warn"),
                    ("inlet", "warn"),
                ]),
            }
        },
    )
    frame = decide(state)
    cards = frame.bottom_cards
    # First card in the bucket should mention inlet.
    assert "inlet" in cards[0].title


def test_focus_inlet_respects_severity_bucket():
    """focus_patch='inlet' must NOT promote inlet-WARN above outlet-FAIL.
    Focus bias operates WITHIN a severity bucket, not across buckets."""
    state = _state(
        focus_patch="inlet",
        artifacts={
            "bc_quality.json": {
                "findings": [
                    {"severity": "fail", "title": "outlet fail",
                     "message": "outlet failed", "field_path": "bc_contract.outlet"},
                    {"severity": "warn", "title": "inlet warn",
                     "message": "inlet warn", "field_path": "bc_contract.inlet"},
                ],
            }
        },
    )
    frame = decide(state)
    # Rail.primary is a FAIL: outlet. Inlet warn should NOT win.
    assert frame.rail_primary.kind == "problem_fix"
    assert "outlet" in frame.rail_primary.title


def test_focus_nonexistent_patch_falls_through():
    """focus_patch='ghost_patch' with no matches → first item (existing
    behavior, no errors)."""
    state = _state(
        focus_patch="ghost_patch",
        artifacts={
            "bc_quality.json": {
                "findings": [
                    {"severity": "fail", "title": "real fail",
                     "message": "real failure", "field_path": "bc_contract.inlet"},
                ],
            }
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "problem_fix"
    assert frame.rail_primary.title == "real fail"


def test_focus_matches_via_gaps_by_field():
    """Real bc_audit.json `patch_coverage_dimension.gaps_by_field`
    shape: {fieldname: [missing_patch1, ...]}. focus_patch='inlet'
    should match when 'inlet' appears in any field's missing list."""
    state = _state(
        focus_patch="inlet",
        artifacts={
            "bc_audit.json": {
                "gate_status": "FAIL",
                "patch_coverage_dimension": {
                    "dimension_status": "FAIL",
                    "gaps_by_field": {
                        "U": ["inlet", "outlet"],
                        "p": ["wall"],
                    },
                },
                "value_match_dimension": {
                    "dimension_status": "FAIL",
                    "gaps_by_field": {"k": ["outlet"]},
                },
            }
        },
    )
    frame = decide(state)
    # The patch_coverage_dimension card (mentions inlet via gaps_by_field)
    # should be the rail.primary FAIL because it focus-matches.
    assert frame.rail_primary.kind == "problem_fix"
    assert "patch_coverage" in frame.rail_primary.title


def test_focus_matches_field_path_substring():
    """field_path 'vof_contract.inlet.boundary' should match focus_patch='inlet'."""
    state = _state(
        focus_patch="inlet",
        completeness={
            "missing": [
                {"field_path": "bc.outlet.pressure", "severity": "critical",
                 "why": "outlet pressure missing"},
                {"field_path": "bc.inlet.velocity", "severity": "critical",
                 "why": "inlet velocity missing"},
            ]
        },
    )
    frame = decide(state)
    # inlet wins same-severity tie
    assert "inlet" in frame.rail_primary.title


def test_focus_matches_body_text():
    """body_text 'velocity at the inlet patch' should match focus='inlet'."""
    state = _state(
        focus_patch="inlet",
        artifacts={
            "bc_quality.json": {
                "findings": [
                    {"severity": "fail", "title": "Generic FAIL A",
                     "message": "generic failure A",
                     "field_path": "bc_contract.x"},
                    {"severity": "fail", "title": "Generic FAIL B",
                     "message": "velocity at the inlet patch is wrong",
                     "field_path": "bc_contract.y"},
                ],
            }
        },
    )
    frame = decide(state)
    # B's body mentions inlet → wins tie
    assert frame.rail_primary.title == "Generic FAIL B"


def test_focus_does_not_promote_critical_gap_above_audit_fail():
    """Codex R0 P2-A regression: focus bias must operate WITHIN a
    (severity, kind) sub-bucket — a focus-matching missing_field (critical)
    must NOT be reordered ahead of an unrelated audit_finding FAIL at
    the same severity rank."""
    state = _state(
        focus_patch="inlet",
        artifacts={
            "bc_quality.json": {
                "findings": [
                    {"severity": "fail", "title": "non-focused FAIL",
                     "message": "unrelated failure",
                     "field_path": "bc_contract.outlet"},
                ],
            }
        },
        completeness={
            "missing": [
                {"field_path": "bc.inlet.velocity", "severity": "critical",
                 "why": "inlet velocity missing"},
            ]
        },
    )
    frame = decide(state)
    # First card must be the audit FAIL, not the focus-matching critical gap.
    assert frame.bottom_cards[0].kind == "audit_finding"
    assert "non-focused FAIL" in frame.bottom_cards[0].title


def test_focus_matches_resolved_patch_in_nested_arrays():
    """Codex R0 P2-B regression: bc_audit's value_mismatches /
    type_mismatches arrays carry concrete patch names via
    resolved_patch. focus_patch must match these so a viewport pick on
    a concrete patch (e.g. topWall) surfaces the related FAIL even
    when the manifest key is just `wall`."""
    state = _state(
        focus_patch="topWall",
        artifacts={
            "bc_audit.json": {
                "gate_status": "FAIL",
                "value_match_dimension": {
                    "dimension_status": "FAIL",
                    "value_mismatches": [
                        {"field": "U", "resolved_patch": "inlet"},
                    ],
                    "type_mismatches": [
                        {"field": "U", "resolved_patch": "topWall"},
                        {"field": "p", "resolved_patch": "bottomWall"},
                    ],
                },
                "patch_coverage_dimension": {
                    "dimension_status": "FAIL",
                    "gaps_by_field": {"k": ["inlet"]},
                },
            }
        },
    )
    frame = decide(state)
    # value_match dimension surfaces topWall via type_mismatches; it
    # should win rail.primary over patch_coverage (which only mentions
    # inlet/bottomWall, not topWall).
    assert frame.rail_primary.kind == "problem_fix"
    assert "value_match" in frame.rail_primary.title


def test_focus_matches_value_missing_and_derived_failure_sublists():
    """Codex R2 P2 regression: bc_audit emits FAIL records not only via
    value_mismatches / type_mismatches but also via value_missing,
    derived_mismatches, and derived_missing. focus_patch must match
    resolved_patch from all of these so a viewport pick on a concrete
    patch surfaces the relevant failure regardless of which sub-list
    the auditor chose."""
    from ui.backend.services.workbench_decide import (
        _focus_matches,
        _iter_problems_from_artifact,
    )

    for sublist_key in ("value_missing", "derived_mismatches", "derived_missing"):
        artifact = {
            "gate_status": "FAIL",
            "value_match_dimension": {
                "dimension_status": "FAIL",
                # Successful records that must NOT contribute.
                "matched": [
                    {"field": "U", "resolved_patch": "passing_patch"},
                ],
                # FAIL records under the sub-list being tested.
                sublist_key: [
                    {"field": "alpha", "resolved_patch": "inlet"},
                ],
            },
        }
        state = _state(focus_patch="inlet", artifacts={"bc_audit.json": artifact})
        problems = list(
            _iter_problems_from_artifact(artifact, "bc_audit.json")
        )
        dim_problem = next(
            (p for p in problems if p.get("rule") == "value_match_dimension"),
            None,
        )
        assert dim_problem is not None, (
            f"value_match dim should be emitted for sublist {sublist_key}"
        )
        assert _focus_matches(state, dim_problem) is True, (
            f"focus_patch=inlet must match the FAIL in sublist {sublist_key}"
        )

        # Conversely, focusing the passing_patch (only in `matched`)
        # must still NOT match.
        state_pass = _state(
            focus_patch="passing_patch", artifacts={"bc_audit.json": artifact}
        )
        assert _focus_matches(state_pass, dim_problem) is False, (
            f"focus on passing-only patch must not match FAIL via {sublist_key}"
        )


def test_focus_does_not_match_resolved_patch_in_successful_sublists():
    """Codex R1 P2 regression: bc_audit dimensions can include both
    successful `matched`/`checked` records AND failing
    `value_mismatches`/`type_mismatches` records. Focusing a patch that
    ONLY appears in the successful records must NOT cause _focus_matches
    to treat the whole FAIL dimension as patch-relevant."""
    state = _state(
        focus_patch="passing_patch",  # only in successful list
        artifacts={
            "bc_audit.json": {
                "gate_status": "FAIL",
                "value_match_dimension": {
                    "dimension_status": "FAIL",
                    # Successful entries — must NOT be scanned for focus.
                    "matched": [
                        {"field": "U", "resolved_patch": "passing_patch"},
                    ],
                    "checked": [
                        {"field": "p", "resolved_patch": "passing_patch"},
                    ],
                    # FAIL entries — these ARE scanned.
                    "value_mismatches": [
                        {"field": "alpha", "resolved_patch": "failing_patch"},
                    ],
                },
            }
        },
    )
    frame = decide(state)
    # The FAIL dimension surfaces in bottom_cards, but focusing
    # "passing_patch" must not promote it via successful-record matching.
    # With no real match, the rail.primary falls through to severity sort.
    # The load-bearing assertion: _focus_matches() on the value_match card
    # must return False (no false-positive).
    from ui.backend.services.workbench_decide import (
        _focus_matches,
        _iter_problems_from_artifact,
    )
    problems = list(
        _iter_problems_from_artifact(
            state.artifacts["bc_audit.json"],
            "bc_audit.json",
        )
    )
    value_match_problem = next(
        (p for p in problems if p.get("rule") == "value_match_dimension"),
        None,
    )
    assert value_match_problem is not None, "value_match dim should be emitted"
    assert _focus_matches(state, value_match_problem) is False, (
        "Successful-only patch must not match a failing dim"
    )

    # Conversely, focusing the failing_patch DOES match.
    state2 = _state(
        focus_patch="failing_patch",
        artifacts=state.artifacts,
    )
    assert _focus_matches(state2, value_match_problem) is True


def test_focus_unset_does_not_reorder_cards():
    """When focus_patch is None, bottom_cards keep their severity-sort
    order (no focus reorder fires)."""
    findings = [
        {"severity": "warn", "title": "wA", "message": "a", "field_path": "bc_contract.inlet"},
        {"severity": "warn", "title": "wB", "message": "b", "field_path": "bc_contract.outlet"},
        {"severity": "warn", "title": "wC", "message": "c", "field_path": "bc_contract.wall"},
    ]
    state_no_focus = _state(artifacts={"bc_quality.json": {"findings": findings}})
    state_w_focus = _state(focus_patch="outlet",
                           artifacts={"bc_quality.json": {"findings": findings}})

    f1 = decide(state_no_focus)
    f2 = decide(state_w_focus)

    # With focus_patch='outlet', the outlet card (wB · field_path=bc_contract.outlet)
    # bubbles to the top within the WARN severity bucket.
    assert f2.bottom_cards[0].field_path == "bc_contract.outlet"
    # Without focus, order is stable severity-sort over the input.
    # The first card's field_path should NOT be the focused 'outlet'
    # (because input order had inlet first).
    assert f1.bottom_cards[0].field_path != "bc_contract.outlet"

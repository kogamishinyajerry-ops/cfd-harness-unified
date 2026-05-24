"""DEC-V61-202-SUB-M31-CYCLE7 · corrupted-manifest visibility tests.

BUG-CYCLE5-3: when the manifest is schema-invalid (e.g. corruption
arriving via legacy data, manual YAML edit, or any future PATCH-
bypass), the workbench rail must surface a critical info_gap on
every step + disable the topbar CTA — not silently fall through to
step_default ("ready to proceed").

Cycle 6 prevented corruption via PATCH; cycle 7 ensures the rail
still surfaces corruption that arrives via other ingress paths.
"""
from __future__ import annotations

from ui.backend.schemas.workbench_frame import CaseStateSnapshot
from ui.backend.services.workbench_decide import decide


def _state_with_corruption(step: int) -> CaseStateSnapshot:
    """Build a state where completeness has a critical at the meta-path
    that the analyzer surfaces for schema-invalid manifests.
    """
    return CaseStateSnapshot(
        case_id="case_corrupted",
        step=step,
        manifest={"case_id": "case_corrupted"},  # frame doesn't validate; raw read
        artifacts={},
        completeness={
            "missing": [
                {
                    "field_path": "case_manifest.yaml",
                    "severity": "critical",
                    "why": (
                        "Imported case_manifest.yaml is parseable YAML but "
                        "fails schema validation: bc.patches.inlet must be "
                        "a dict, got str. Every backend route that reads "
                        "the manifest will reject it; fix the schema "
                        "before continuing."
                    ),
                }
            ]
        },
        focus_patch=None,
        focus_region=None,
        focus_panel=None,
    )


def _state_with_off_step_missing(step: int) -> CaseStateSnapshot:
    """Sanity baseline: a NON-meta gap with `field_path` outside the
    current step's prefixes should still be filtered (no over-promotion).
    """
    return CaseStateSnapshot(
        case_id="case_misc",
        step=step,
        manifest={"case_id": "case_misc"},
        artifacts={},
        completeness={
            "missing": [
                {
                    "field_path": "qoi_contract.tolerance",  # step-5 territory
                    "severity": "critical",
                    "why": "QoI tolerance is required for trust evaluation.",
                }
            ]
        },
        focus_patch=None,
        focus_region=None,
        focus_panel=None,
    )


# ─── BUG-3 closure: corruption visible on every step ───


def test_corrupted_manifest_surfaces_on_step_1():
    frame = decide(_state_with_corruption(1))
    assert frame.rail_primary.kind == "info_gap"
    assert frame.rail_primary.field_path == "case_manifest.yaml"
    assert frame.topbar_cta.enabled is False


def test_corrupted_manifest_surfaces_on_step_2():
    frame = decide(_state_with_corruption(2))
    assert frame.rail_primary.kind == "info_gap"
    assert frame.rail_primary.field_path == "case_manifest.yaml"
    assert frame.topbar_cta.enabled is False


def test_corrupted_manifest_surfaces_on_step_3():
    frame = decide(_state_with_corruption(3))
    assert frame.rail_primary.kind == "info_gap"
    assert frame.rail_primary.field_path == "case_manifest.yaml"
    assert frame.topbar_cta.enabled is False


def test_corrupted_manifest_surfaces_on_step_4():
    frame = decide(_state_with_corruption(4))
    assert frame.rail_primary.kind == "info_gap"
    assert frame.rail_primary.field_path == "case_manifest.yaml"
    assert frame.topbar_cta.enabled is False


def test_corrupted_manifest_surfaces_on_step_5():
    frame = decide(_state_with_corruption(5))
    assert frame.rail_primary.kind == "info_gap"
    assert frame.rail_primary.field_path == "case_manifest.yaml"
    assert frame.topbar_cta.enabled is False


def test_corrupted_manifest_why_explains_corruption():
    """Engineer must be able to read what's wrong from the rail."""
    frame = decide(_state_with_corruption(4))
    title = (frame.rail_primary.title or "").lower()
    body = (frame.rail_primary.body_text or "").lower()
    text = title + " " + body
    # The analyzer's "why" message must reach the rail surface — engineer
    # needs to see "schema validation failed" or similar, not a stub.
    assert "schema" in text or "manifest" in text or "case_manifest" in text


# ─── Sanity: off-step non-meta gaps are still filtered ───


def test_off_step_non_meta_critical_does_NOT_promote_to_step_1():
    """A critical for step 5 (qoi_contract.tolerance) must NOT bubble
    up to step 1's rail just because corruption-class items do.
    The allow-list is narrow on purpose.
    """
    frame = decide(_state_with_off_step_missing(1))
    # Step 1 rail should fall through to step_default since the only
    # missing field is step-5 territory.
    assert frame.rail_primary.kind == "step_default"


def test_corrupted_manifest_priority_outranks_default():
    """A corrupted-manifest critical must outrank step_default even
    when there are no other findings.
    """
    frame = decide(_state_with_corruption(1))
    assert frame.rail_primary.kind != "step_default"


# ─── Regression: cycle-7 fix doesn't break the happy path ───


def test_no_completeness_returns_step_default():
    """No analyzer output → no critical surfaced; rail falls through
    to step_default. The fix must not generate phantom criticals.
    """
    state = CaseStateSnapshot(
        case_id="case_clean",
        step=4,
        manifest={"case_id": "case_clean"},
        artifacts={},
        completeness=None,
        focus_patch=None,
        focus_region=None,
        focus_panel=None,
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "step_default"

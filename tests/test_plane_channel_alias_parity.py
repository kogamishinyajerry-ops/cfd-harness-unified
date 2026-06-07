"""DEC-V61-059 Stage A.6 — alias normalization sanity check.

The plane-channel work touches two alias tables that ADR-001 four-plane
contract keeps in deliberate duplication (Evaluation plane cannot import
from Execution plane and vice versa):

  - Execution plane: src.foam_agent_adapter._TASK_NAME_TO_CASE_ID_ALIASES
  - Evaluation plane: src.auto_verifier.config.TASK_NAME_TO_CASE_ID

Both must agree on the plane-channel mapping at minimum:
  "Fully Developed Plane Channel Flow (DNS)" → "fully_developed_plane_channel_flow"

This test pins the two-table round-trip so a future refactor that
touches only one side surfaces immediately. It also documents the
plane-channel canonical id (DEC-V61-036c referenced legacy id
"plane_channel_flow"; the canonical id has been
"fully_developed_plane_channel_flow" since the Q-2 rename).
"""

from __future__ import annotations

from src.auto_verifier.config import TASK_NAME_TO_CASE_ID
from src.foam_agent_adapter import (
    _TASK_NAME_TO_CASE_ID_ALIASES,
    _normalize_task_name_to_case_id,
)


PLANE_CHANNEL_DISPLAY_TITLE = "Fully Developed Plane Channel Flow (DNS)"
PLANE_CHANNEL_CANONICAL_ID = "fully_developed_plane_channel_flow"


def test_adapter_alias_table_resolves_plane_channel_display_title():
    """Adapter (Execution plane) must resolve the human-readable title
    used by the whitelist + Notion integrations to the canonical id.
    """
    assert (
        _TASK_NAME_TO_CASE_ID_ALIASES[PLANE_CHANNEL_DISPLAY_TITLE]
        == PLANE_CHANNEL_CANONICAL_ID
    )


def test_auto_verifier_alias_table_resolves_plane_channel_display_title():
    """Auto-verifier (Evaluation plane) must agree with the adapter
    on the plane-channel mapping. ADR-001 forbids cross-plane imports
    of the table itself; this test enforces the contract by value
    rather than by symbol-sharing.
    """
    assert (
        TASK_NAME_TO_CASE_ID[PLANE_CHANNEL_DISPLAY_TITLE]
        == PLANE_CHANNEL_CANONICAL_ID
    )


def test_alias_tables_agree_on_plane_channel_mapping():
    """Direct comparison: both tables must produce the same canonical
    id for the plane-channel display title.
    """
    assert (
        _TASK_NAME_TO_CASE_ID_ALIASES[PLANE_CHANNEL_DISPLAY_TITLE]
        == TASK_NAME_TO_CASE_ID[PLANE_CHANNEL_DISPLAY_TITLE]
    )


def test_normalize_helper_returns_canonical_id():
    """Adapter dispatch path uses _normalize_task_name_to_case_id to
    convert TaskSpec.name → case_id; verify it agrees with the
    table-level mapping for the plane-channel display title.
    """
    assert (
        _normalize_task_name_to_case_id(PLANE_CHANNEL_DISPLAY_TITLE)
        == PLANE_CHANNEL_CANONICAL_ID
    )


def test_alias_tables_agree_for_all_whitelist_titles():
    """Stronger contract: every entry in the auto-verifier table must
    match the adapter table. ADR-001 keeps them as deliberate dupes;
    this test catches drift where one side gains/loses a mapping
    without the other.

    Some entries appear only on one side (e.g. legacy-only aliases);
    we require AGREEMENT WHEN BOTH HAVE THE KEY rather than full
    set equality.
    """
    shared_keys = (
        set(TASK_NAME_TO_CASE_ID.keys())
        & set(_TASK_NAME_TO_CASE_ID_ALIASES.keys())
    )
    assert shared_keys, "expected at least one shared entry across tables"
    for title in shared_keys:
        assert (
            TASK_NAME_TO_CASE_ID[title]
            == _TASK_NAME_TO_CASE_ID_ALIASES[title]
        ), (
            f"alias drift: auto_verifier maps {title!r} → "
            f"{TASK_NAME_TO_CASE_ID[title]!r}, "
            f"adapter maps to {_TASK_NAME_TO_CASE_ID_ALIASES[title]!r}"
        )


def test_normalize_helper_passes_through_unknown_titles():
    """Unknown titles return verbatim (caller decides what to do)."""
    assert (
        _normalize_task_name_to_case_id("frobnozzle-case")
        == "frobnozzle-case"
    )
    assert _normalize_task_name_to_case_id("") == ""

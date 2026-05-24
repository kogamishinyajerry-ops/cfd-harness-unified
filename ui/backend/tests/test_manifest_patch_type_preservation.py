"""DEC-V61-202-SUB-M31-CYCLE6 · type-preservation unit tests.

Covers `_check_type_preservation` directly (cheap, no I/O) so the rule
table is locked in regardless of route plumbing.
"""
from __future__ import annotations

from ui.backend.services.manifest_patch import _check_type_preservation


# ─────────────────────── happy paths (return None) ───────────────────────


def test_path_not_present_allows_any_type():
    manifest = {"a": {"b": 1}}
    assert _check_type_preservation(manifest, ["x", "y"], "anything") is None
    assert _check_type_preservation(manifest, ["a", "z"], {"k": 1}) is None
    assert _check_type_preservation(manifest, ["a", "z"], [1, 2, 3]) is None


def test_dict_replaced_by_dict_is_ok():
    manifest = {"bc": {"patches": {"inlet": {"patch_type": "fixedValue"}}}}
    err = _check_type_preservation(
        manifest, ["bc", "patches", "inlet"], {"patch_type": "noSlip"}
    )
    assert err is None


def test_list_replaced_by_list_is_ok():
    manifest = {"required_artifacts": ["a", "b"]}
    err = _check_type_preservation(
        manifest, ["required_artifacts"], ["c", "d", "e"]
    )
    assert err is None


def test_scalar_replaced_by_scalar_is_ok():
    manifest = {"bc": {"patches": {"inlet": {"patch_type": "fixedValue"}}}}
    # str → str (the typo case from the dogfood — accepted at PATCH layer,
    # analyzer's job to flag enum membership)
    err = _check_type_preservation(
        manifest, ["bc", "patches", "inlet", "patch_type"], "fixedValue_typo"
    )
    assert err is None


def test_scalar_replaced_by_different_scalar_kind_is_ok():
    manifest = {"physics": {"compressible": False}}
    # bool → str (still scalar; engineer might be replacing a flag with
    # a descriptive code). Scalar→scalar is intentionally permissive.
    err = _check_type_preservation(
        manifest, ["physics", "compressible"], "auto-detect"
    )
    assert err is None


def test_none_value_treated_as_scalar():
    manifest = {"physics": {"steady": None}}
    err = _check_type_preservation(manifest, ["physics", "steady"], True)
    assert err is None


def test_empty_segments_returns_none():
    assert _check_type_preservation({"a": 1}, [], "x") is None


def test_parent_not_dict_returns_none_for_write_at_path_to_handle():
    # Pre-existing corruption: bc.patches.inlet is somehow a string.
    # We don't pre-empt — `_write_at_path` will raise PatchPathError
    # with a clear "intermediate is not a dict" message.
    manifest = {"bc": {"patches": {"inlet": "already_corrupted"}}}
    err = _check_type_preservation(
        manifest, ["bc", "patches", "inlet", "patch_type"], "fixedValue"
    )
    assert err is None


# ─────────────────────── rejected paths (return msg) ───────────────────────


def test_dict_replaced_by_scalar_is_rejected():
    """BUG-CYCLE5-1: the load-bearing regression."""
    manifest = {"bc": {"patches": {"inlet": {"patch_type": "fixedValue"}}}}
    err = _check_type_preservation(
        manifest, ["bc", "patches", "inlet"], "not_a_dict"
    )
    assert err is not None
    assert "bc.patches.inlet" in err
    # Reason-keyword vocabulary the cycle-5 dogfood looks for:
    assert "type" in err.lower()
    assert "dict" in err.lower()
    assert "str" in err  # the type name of the offending value


def test_dict_replaced_by_list_is_rejected():
    manifest = {"bc": {"patches": {"inlet": {"patch_type": "fixedValue"}}}}
    err = _check_type_preservation(
        manifest, ["bc", "patches", "inlet"], ["a", "b"]
    )
    assert err is not None
    assert "dict" in err.lower()
    assert "list" in err


def test_list_replaced_by_scalar_is_rejected():
    manifest = {"required_artifacts": ["a", "b"]}
    err = _check_type_preservation(
        manifest, ["required_artifacts"], "broken"
    )
    assert err is not None
    assert "list" in err.lower()


def test_list_replaced_by_dict_is_rejected():
    manifest = {"required_artifacts": ["a", "b"]}
    err = _check_type_preservation(
        manifest, ["required_artifacts"], {"k": "v"}
    )
    assert err is not None
    assert "list" in err.lower()
    assert "dict" in err


def test_scalar_replaced_by_dict_is_rejected():
    manifest = {"physics": {"compressible": False}}
    err = _check_type_preservation(
        manifest, ["physics", "compressible"], {"nested": True}
    )
    assert err is not None
    assert "scalar" in err.lower()


def test_scalar_replaced_by_list_is_rejected():
    manifest = {"physics": {"compressible": False}}
    err = _check_type_preservation(
        manifest, ["physics", "compressible"], [1, 2, 3]
    )
    assert err is not None
    assert "scalar" in err.lower()


def test_none_replaced_by_dict_is_rejected():
    manifest = {"physics": {"steady": None}}
    err = _check_type_preservation(
        manifest, ["physics", "steady"], {"value": True}
    )
    assert err is not None
    assert "scalar" in err.lower() or "none" in err.lower()


# ─────────────────────── error message contract ───────────────────────


def test_error_message_includes_engineer_recovery_hint():
    """Engineer should see the escape hatch in the error itself."""
    manifest = {"bc": {"patches": {"inlet": {"patch_type": "fixedValue"}}}}
    err = _check_type_preservation(
        manifest, ["bc", "patches", "inlet"], "not_a_dict"
    )
    assert err is not None
    assert "unset" in err.lower()  # mentions the unset → set workaround


def test_dogfood_reason_keyword_match():
    """The cycle-5 dogfood's `_is_rejection_with_named_reason()` predicate
    scans for ('type', 'value', 'dict', 'schema', 'expected', 'patch_type').
    Our error message must hit at least one of these so the dogfood's
    PASS predicate flips when this fix lands.
    """
    cycle5_keywords = ("type", "value", "dict", "schema", "expected", "patch_type")
    manifest = {"bc": {"patches": {"inlet": {"patch_type": "fixedValue"}}}}
    err = _check_type_preservation(
        manifest, ["bc", "patches", "inlet"], "not_a_dict"
    )
    assert err is not None
    hits = [k for k in cycle5_keywords if k in err.lower()]
    assert hits, f"error message missing all cycle-5 dogfood keywords: {err}"

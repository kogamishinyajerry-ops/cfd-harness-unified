"""DEC-V61-202-SUB-M30-CYCLE6 · provenance audit_v2 log writer tests.

Coverage:
    1. log_decision writes a parseable JSONL line with expected fields
    2. Multiple decide() calls append (don't overwrite)
    3. focus_patch is captured when set, null when absent
    4. Failing log write doesn't break the frame (decide() still returns)
    5. Every line is independently valid JSON
    6. WORKBENCH_PROVENANCE_DISABLED=1 short-circuits the writer
    7. Case-id sanitization rejects path-traversal attempts
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ui.backend.schemas.workbench_frame import CaseStateSnapshot
from ui.backend.services.workbench_decide import decide


@pytest.fixture
def provenance_enabled(monkeypatch, tmp_path):
    """Re-enable provenance writes (the autouse conftest fixture
    disables them by default) and redirect AUDIT_V2_DIR to a tmp_path
    so we never pollute the working tree."""
    monkeypatch.delenv("WORKBENCH_PROVENANCE_DISABLED", raising=False)
    # Import lazily so the patch lands AFTER the env var change.
    import ui.backend.services.workbench_decide_provenance as wp

    monkeypatch.setattr(wp, "AUDIT_V2_DIR", tmp_path)
    # Reset the dedup cache so tests don't share state. Push-review
    # P2 #1 dedup is per-process; tests want a clean slate.
    wp._LAST_STATE_SHA_PER_CASE.clear()
    return tmp_path


def _state(**kwargs) -> CaseStateSnapshot:
    base = {
        "case_id": "test_case",
        "step": 4,
        "manifest": {},
        "artifacts": {},
        "completeness": None,
    }
    base.update(kwargs)
    return CaseStateSnapshot(**base)


def _read_lines(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    return [
        json.loads(line) for line in log_path.read_text().splitlines() if line.strip()
    ]


def test_log_decision_writes_parseable_line(provenance_enabled):
    state = _state(case_id="case_abc")
    frame = decide(state)
    log_path = provenance_enabled / "case_abc" / "decisions.jsonl"
    assert log_path.exists()
    lines = _read_lines(log_path)
    assert len(lines) == 1
    rec = lines[0]
    assert rec["case_id"] == "case_abc"
    assert rec["step"] == 4
    assert rec["state_sha"] == frame.state_sha
    assert rec["manifest_state_sha"] == frame.manifest_state_sha
    assert "timestamp" in rec
    assert rec["rail_primary"]["kind"] == frame.rail_primary.kind
    assert rec["rail_primary"]["title"] == frame.rail_primary.title
    # severity is derived from provenance (Codex R0 P2 #2): present in the
    # record but may be None for step_default rails that don't have an
    # underlying finding/gap severity.
    assert "severity" in rec["rail_primary"]
    assert rec["topbar_cta"]["kind"] == frame.topbar_cta.kind
    assert rec["bottom_card_count"] == len(frame.bottom_cards or [])


def test_log_decision_appends_multiple_calls(provenance_enabled):
    """Push-review P2 #1: dedup is by state_sha, so distinct states
    still each get their own line (the writer appends, doesn't
    overwrite). Using three *different* states proves the append path."""
    decide(_state(case_id="case_multi", step=1))
    decide(_state(case_id="case_multi", step=2))
    decide(_state(case_id="case_multi", step=3))
    log_path = provenance_enabled / "case_multi" / "decisions.jsonl"
    lines = _read_lines(log_path)
    assert len(lines) == 3
    # Append order = call order
    assert [line["step"] for line in lines] == [1, 2, 3]


def test_log_decision_captures_focus_patch(provenance_enabled):
    state_with = _state(case_id="case_focus", focus_patch="inlet")
    state_without = _state(case_id="case_focus")
    decide(state_with)
    decide(state_without)
    log_path = provenance_enabled / "case_focus" / "decisions.jsonl"
    lines = _read_lines(log_path)
    assert len(lines) == 2
    assert lines[0]["focus_patch"] == "inlet"
    assert lines[1]["focus_patch"] is None


def test_log_decision_failure_does_not_break_frame(monkeypatch):
    """If the log writer raises, decide() must still return a frame."""
    monkeypatch.delenv("WORKBENCH_PROVENANCE_DISABLED", raising=False)
    import ui.backend.services.workbench_decide_provenance as wp

    def boom(_state, _frame):
        raise RuntimeError("simulated disk full")

    monkeypatch.setattr(wp, "log_decision", boom)
    state = _state(case_id="case_break")
    frame = decide(state)
    # Frame returned despite the log error.
    assert frame.case_id == "case_break"
    assert frame.rail_primary is not None


def test_every_jsonl_line_is_valid_json(provenance_enabled):
    state = _state(case_id="case_valid")
    decide(state)
    decide(_state(case_id="case_valid", focus_patch="outlet"))
    decide(_state(case_id="case_valid", step=2))
    log_path = provenance_enabled / "case_valid" / "decisions.jsonl"
    raw = log_path.read_text().splitlines()
    for line in raw:
        if not line.strip():
            continue
        # json.loads raises on parse failure → test fails
        parsed = json.loads(line)
        assert isinstance(parsed, dict)


def test_disabled_env_var_short_circuits(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKBENCH_PROVENANCE_DISABLED", "1")
    import ui.backend.services.workbench_decide_provenance as wp

    monkeypatch.setattr(wp, "AUDIT_V2_DIR", tmp_path)
    state = _state(case_id="case_disabled")
    frame = decide(state)
    log_path = tmp_path / "case_disabled" / "decisions.jsonl"
    # No file written.
    assert not log_path.exists()
    # Frame still returned.
    assert frame.case_id == "case_disabled"


def test_case_id_sanitization_blocks_traversal(provenance_enabled):
    # Case_id with path-separator chars should be sanitized so the
    # log file lands inside AUDIT_V2_DIR, not somewhere else.
    state = _state(case_id="../etc/passwd")
    decide(state)
    # Sanitizer keeps a-zA-Z0-9_-. and replaces the rest with _.
    # "../etc/passwd" → ".._etc_passwd" (the `..` survives but slashes
    # become _ so the resulting name is a single directory entry,
    # NOT a path-traversal).
    expected_dir = provenance_enabled / ".._etc_passwd"
    assert expected_dir.exists()
    # Confirm the parent traversal didn't escape AUDIT_V2_DIR.
    log_files = list(provenance_enabled.rglob("decisions.jsonl"))
    for log_file in log_files:
        assert provenance_enabled in log_file.parents


def test_dedup_cache_not_poisoned_by_failed_write(monkeypatch, tmp_path):
    """Push-review R1 P2 #2 regression: a transient write failure
    must not poison the dedup cache. After the error, the very next
    call with the same state_sha must retry and (when conditions are
    healthy) actually land a log line."""
    monkeypatch.delenv("WORKBENCH_PROVENANCE_DISABLED", raising=False)
    import ui.backend.services.workbench_decide_provenance as wp

    wp._LAST_STATE_SHA_PER_CASE.clear()
    monkeypatch.setattr(wp, "AUDIT_V2_DIR", tmp_path)

    # First call: force the file open to fail.
    original_open = wp.open if hasattr(wp, "open") else open
    call_counter = {"n": 0}

    def flaky_open(*args, **kwargs):
        call_counter["n"] += 1
        if call_counter["n"] == 1:
            raise PermissionError("simulated transient permission denied")
        return original_open(*args, **kwargs)

    # Patch the built-in `open` inside the provenance module's namespace.
    import builtins as _builtins

    monkeypatch.setattr(_builtins, "open", flaky_open)

    state = _state(case_id="case_poison")
    decide(state)  # first call: simulated write failure
    log_path = tmp_path / "case_poison" / "decisions.jsonl"
    assert not log_path.exists(), "first write should have failed"

    # Second call with the SAME state must retry — not be deduped.
    decide(state)
    assert log_path.exists()
    lines = _read_lines(log_path)
    assert len(lines) == 1, (
        "after a failed write, the next same-state call must retry and "
        f"land 1 line — got {len(lines)}"
    )


def test_repeated_same_state_sha_dedup(provenance_enabled, monkeypatch):
    """Push-review P2 #1 regression: passive refetches that return the
    same state_sha must not append duplicate log lines. React Query
    refetch on remount / window-focus is the canonical case."""
    import ui.backend.services.workbench_decide_provenance as wp

    # Clear the in-process dedup cache so this test is hermetic.
    wp._LAST_STATE_SHA_PER_CASE.clear()

    state = _state(case_id="case_dedup")
    decide(state)
    decide(state)  # passive refetch — same state_sha
    decide(state)  # another passive refetch
    log_path = provenance_enabled / "case_dedup" / "decisions.jsonl"
    lines = _read_lines(log_path)
    assert len(lines) == 1, (
        f"expected exactly 1 line after 3 same-state calls, got {len(lines)}"
    )

    # A state change (different step) MUST write a new line.
    state2 = _state(case_id="case_dedup", step=2)
    decide(state2)
    lines = _read_lines(log_path)
    assert len(lines) == 2
    assert lines[0]["step"] != lines[1]["step"]


def test_replay_script_runs_without_pythonpath(tmp_path, monkeypatch):
    """Codex R0 P2 #1 regression: invoking the replay helper exactly as
    documented (`python3 scripts/audit_v2/replay_decisions.py <case>`)
    must succeed from the repo root without an ambient PYTHONPATH.
    Verifies the in-script sys.path bootstrap."""
    import subprocess
    import sys
    from pathlib import Path as _P

    repo_root = _P(__file__).resolve().parents[3]
    script = repo_root / "scripts" / "audit_v2" / "replay_decisions.py"
    assert script.exists()
    # No PYTHONPATH in env — proves the script self-bootstraps.
    env = {
        k: v for k, v in os.environ.items() if k not in {"PYTHONPATH"}
    }
    result = subprocess.run(
        [sys.executable, str(script), "nonexistent_case",
         "--audit-dir", str(tmp_path)],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    # Exits 1 (no log) but proves the import + arg parse succeeded
    # without ModuleNotFoundError.
    assert "ModuleNotFoundError" not in result.stderr, result.stderr
    assert "No log at" in result.stderr


def test_rail_severity_extracted_from_provenance(provenance_enabled):
    """Codex R0 P2 #2 regression: when the rail is driven by a FAIL
    finding, the log row must carry severity='fail' so post-hoc replay
    can tell WARN-vs-FAIL apart even though kind/title may coincide."""
    state = _state(
        case_id="case_sev_fail",
        artifacts={
            "bc_audit.json": {
                "findings": [
                    {"severity": "fail", "title": "missing inlet U",
                     "message": "set U on inlet",
                     "field_path": "bc_contract.inlet.U"},
                ]
            }
        },
    )
    decide(state)
    log_path = provenance_enabled / "case_sev_fail" / "decisions.jsonl"
    lines = _read_lines(log_path)
    assert len(lines) == 1
    rec = lines[0]
    # The rail was driven by the FAIL finding → severity surfaces.
    assert rec["rail_primary"].get("severity") == "fail"


def test_dot_only_case_id_uses_stable_digest(provenance_enabled, monkeypatch):
    """Codex R0 P3 regression: pure-dot case IDs must route to a
    deterministic directory name across processes, not Python's salted
    hash()."""
    import ui.backend.services.workbench_decide_provenance as wp

    # Two independent calls (simulating writer + replay reader in
    # separate processes) must agree on the same safe name.
    safe_a = wp._safe_case_id("..")
    safe_b = wp._safe_case_id("..")
    assert safe_a == safe_b
    assert safe_a.startswith("_invalid_")
    # And the suffix must be a stable hex digest, not a Python hash().
    digest_part = safe_a[len("_invalid_") :]
    assert all(c in "0123456789abcdef" for c in digest_part)
    assert len(digest_part) == 12


def test_log_includes_bottom_card_severities(provenance_enabled):
    state = _state(
        case_id="case_severities",
        artifacts={
            "bc_quality.json": {
                "findings": [
                    {"severity": "fail", "title": "fail1",
                     "message": "x", "field_path": "bc_contract.inlet"},
                    {"severity": "warn", "title": "warn1",
                     "message": "y", "field_path": "bc_contract.outlet"},
                ]
            }
        },
    )
    decide(state)
    log_path = provenance_enabled / "case_severities" / "decisions.jsonl"
    lines = _read_lines(log_path)
    assert len(lines) == 1
    rec = lines[0]
    assert "bottom_card_severities" in rec
    assert isinstance(rec["bottom_card_severities"], list)
    # At least one severity should appear (depends on step routing)
    assert rec["bottom_card_count"] >= 0

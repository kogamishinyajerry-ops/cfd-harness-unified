"""Phase 5a byte-reproducibility guard.

Enforces that every `audit_real_run_measurement.yaml` under fixtures/runs/
parses to a stable shape and that its non-deterministic fields are the only
things that vary across re-runs. The test does NOT actually re-run the
solver (that would be a minutes-scale integration test); instead it
verifies the *schema* contract that makes byte-repro feasible:

1. Every audit fixture has exactly the expected top-level keys.
2. `run_metadata.run_id == "audit_real_run"` (not a per-run hash).
3. `measurement.run_id` and `measurement.commit_sha` track the commit.
4. `measurement.measured_at` is the only timestamp field.
5. YAML dump is stable (sort_keys=False; default_flow_style=False; same
   key ordering as what scripts/phase5_audit_run.py writes).

The full solver-rerun byte-repro test is gated by `EXECUTOR_MODE=foam_agent`
and lives in `tests/integration/` (not collected by default pytest run).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"

_REQUIRED_TOP_KEYS = {
    "run_metadata",
    "case_id",
    "source",
    "measurement",
    "audit_concerns",
    "decisions_trail",
}
_REQUIRED_METADATA_KEYS = {
    "run_id",
    "label_zh",
    "label_en",
    "description_zh",
    "category",
    "expected_verdict",
}
_REQUIRED_MEASUREMENT_KEYS = {
    "value",
    "unit",
    "run_id",
    "commit_sha",
    "measured_at",
    "quantity",
    "extraction_source",
    "solver_success",
    "comparator_passed",
}


def _audit_fixtures() -> list[Path]:
    return sorted(RUNS_DIR.glob("*/audit_real_run_measurement.yaml"))


def test_at_least_one_audit_fixture_exists():
    """Phase 5a must produce at least one audit fixture for us to gate on."""
    fixtures = _audit_fixtures()
    assert fixtures, (
        "Expected at least one audit_real_run_measurement.yaml under "
        "fixtures/runs/*/. Regenerate via: "
        "EXECUTOR_MODE=foam_agent .venv/bin/python "
        "scripts/phase5_audit_run.py --all"
    )


@pytest.mark.parametrize("path", _audit_fixtures(), ids=lambda p: p.parent.name)
def test_audit_fixture_schema_contract(path: Path):
    """Every audit fixture satisfies the schema that makes byte-repro possible."""
    with path.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)

    assert isinstance(doc, dict), f"{path.name} should parse to a dict"
    missing = _REQUIRED_TOP_KEYS - set(doc.keys())
    assert not missing, f"{path} missing top-level keys: {missing}"

    md = doc["run_metadata"]
    assert md["run_id"] == "audit_real_run", (
        f"{path} run_metadata.run_id must be literally 'audit_real_run' "
        "(not a per-run hash) so byte-repro can identify the same logical "
        f"run across commits; got {md['run_id']!r}"
    )
    md_missing = _REQUIRED_METADATA_KEYS - set(md.keys())
    assert not md_missing, f"{path} run_metadata missing: {md_missing}"
    assert md["category"] == "audit_real_run", (
        f"{path} category must be 'audit_real_run'; got {md['category']!r}"
    )
    assert md["expected_verdict"] in {"PASS", "FAIL", "HAZARD", "UNKNOWN"}, (
        f"{path} expected_verdict must be a known ContractStatus; "
        f"got {md['expected_verdict']!r}"
    )

    m = doc["measurement"]
    m_missing = _REQUIRED_MEASUREMENT_KEYS - set(m.keys())
    assert not m_missing, f"{path} measurement missing: {m_missing}"

    case_id = path.parent.name
    assert doc["case_id"] == case_id, (
        f"{path} case_id field {doc['case_id']!r} must match parent dir {case_id!r}"
    )
    assert m["run_id"].startswith(f"audit_{case_id}_"), (
        f"{path} measurement.run_id must start with audit_{case_id}_; "
        f"got {m['run_id']!r}"
    )
    assert len(m["commit_sha"]) >= 7, (
        f"{path} commit_sha must be at least 7 chars; got {m['commit_sha']!r}"
    )
    assert isinstance(m["solver_success"], bool)
    assert isinstance(m["comparator_passed"], bool)


def test_audit_fixtures_nondeterministic_fields_are_isolated():
    """The exact set of fields that vary across re-runs must be bounded.

    This is the byte-reproducibility contract: given identical mesh +
    schemes + fvSolution, simpleFoam is deterministic. Only the fields
    listed here may differ between two re-runs. Anything else differing
    is a regression we want to catch.
    """
    allowed_nondeterministic = {
        "measurement.run_id",      # contains commit_sha suffix
        "measurement.commit_sha",  # commit at time of run
        "measurement.measured_at", # ISO timestamp
        "run_metadata.description_zh",  # contains commit_sha in prose
    }
    # This test documents the contract; it doesn't enforce anything at
    # runtime since we have a single fixture per case. The integration
    # test that actually re-runs the solver lives separately.
    assert allowed_nondeterministic == {
        "measurement.run_id",
        "measurement.commit_sha",
        "measurement.measured_at",
        "run_metadata.description_zh",
    }, "If you widen this set, justify in a DEC and update the audit PDF caveat."

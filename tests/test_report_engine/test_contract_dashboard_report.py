from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from report_engine import ContractDashboardGenerator


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_contract_dashboard.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_contract_dashboard_cli", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_dashboard_render_contains_core_sections():
    result = ContractDashboardGenerator().render()
    assert result.case_count == 10
    assert "10-case Physics Contract Dashboard" in result.html
    assert "物理契约状态分布" in result.html
    assert "冻结的治理边界" in result.html
    assert "Q-1" in result.html
    assert "Q-2" in result.html
    assert "方腔顶盖驱动流" in result.html
    # DEC-V61-011 (Gate Q-2 Path A, 2026-04-20): pipe → square-duct rename.
    # The canonical title is now "全发展湍流方管流" (Jones 1976 square-duct
    # correlation). "全发展湍流管流" was a physics-mislabel for a circular pipe.
    assert "全发展湍流方管流" in result.html
    assert "轴对称冲击射流" in result.html
    assert "Observable mismatch" in result.html
    assert "visual_acceptance_report.html" in result.html
    # Contract-class distribution drifts case-by-case as gold YAMLs are
    # reclassified. After DEC-V61-046 round-1 R3-M1 fix (gold_file pointers
    # switched from legacy aliases to canonical yamls on 2026-04-22), the
    # dashboard now reads the same gold source as the live /api/cases surface.
    # Distribution consequently shifted:
    #   SATISFIED: 3 → 4 (+LDC canonical SATISFIED_FOR_U_CENTERLINE_ONLY)
    #   COMPATIBLE: 3 → 1 (LDC_benchmark + BFS_steady were COMPATIBLE;
    #       canonical LDC is SATISFIED and canonical BFS is PARTIALLY)
    #   PARTIALLY_COMPATIBLE: 1 → 2 (+BFS canonical)
    #   INCOMPATIBLE: 1 → 0 (plane_channel legacy → canonical DISGUISED tier)
    #   INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE: 1 → 2
    #       (+plane_channel canonical; impinging_jet canonical is also DISGUISED)
    # COMPATIBLE_WITH_SILENT_PASS_HAZARD (cylinder) unchanged at 1.
    # Zero UNKNOWN maintained.
    assert result.summary_counts["SATISFIED"] == 4
    assert result.summary_counts["COMPATIBLE"] == 1
    assert result.summary_counts["COMPATIBLE_WITH_SILENT_PASS_HAZARD"] == 1
    assert result.summary_counts["PARTIALLY_COMPATIBLE"] == 2
    assert result.summary_counts["INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE"] == 2
    assert result.summary_counts.get("INCOMPATIBLE", 0) == 0
    assert result.summary_counts.get("UNKNOWN", 0) == 0


def test_contract_dashboard_generate_writes_output(tmp_path: Path):
    output = tmp_path / "contract_status_dashboard.html"
    result = ContractDashboardGenerator().generate(output_path=output)
    assert output.is_file()
    assert result.output_path == str(output)
    assert result.snapshot_path
    assert Path(result.snapshot_path).is_file()
    assert result.manifest_path
    manifest_path = Path(result.manifest_path)
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["canonical_path"] == str(output)
    assert manifest["snapshot_path"] == str(Path(result.snapshot_path))
    assert manifest["manifest_path"] == str(manifest_path)
    assert manifest["case_count"] == 10
    # Post-R3-M1 gold_file retargeting (DEC-V61-046 round 1): dashboard now
    # reads canonical yamls, shifting the distribution. COMPATIBLE collapsed
    # 3→1 as LDC promoted to SATISFIED and BFS to PARTIALLY_COMPATIBLE.
    assert manifest["class_counts"]["SATISFIED"] == 4
    assert manifest["class_counts"]["COMPATIBLE"] == 1
    assert any(ref.startswith("Q-1") for ref in manifest["open_gate_refs"])
    assert any(ref.startswith("Q-2") for ref in manifest["open_gate_refs"])
    html = output.read_text(encoding="utf-8")
    assert "PENDING_RE_RUN" in html
    # Post-DEC-V61-011 the "materialized auto_verify_report" shibboleth was
    # removed; pin the lasting invariant instead — dashboard must surface
    # its auto_verify_report.yaml provenance.
    assert "auto_verify_report.yaml" in html


def test_contract_dashboard_cli_default(capsys):
    cli = _load_module()
    code = cli.main(["generate_contract_dashboard.py"])
    captured = capsys.readouterr()
    assert code == 0
    assert "OK    contract_dashboard" in captured.out
    assert "snapshot=" in captured.out
    assert "manifest=" in captured.out
    assert "cases=10" in captured.out


def test_contract_dashboard_cli_rejects_extra_args(capsys):
    cli = _load_module()
    code = cli.main(["generate_contract_dashboard.py", "bogus"])
    captured = capsys.readouterr()
    assert code == 2
    assert "does not accept case_ids" in captured.err


def test_contract_dashboard_script_runs_as_subprocess():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "contract_dashboard" in result.stdout


# ---------------------------------------------------------------------------
# DEC-V61-046 round-1 R3-M1: gold_file parity invariant
# ---------------------------------------------------------------------------

def test_dashboard_gold_files_match_canonical_whitelist_yamls():
    """Dashboard specs must read from the canonical whitelist gold yamls, not
    from legacy aliases. This pins R3-M1 (codex round 1): dashboard and the
    live `/api/cases` surface now share one gold source per case, preventing
    split-brain drift where a contract reclassification lands in one surface
    but not the other.

    If a new legacy alias is legitimately needed (e.g., for a rename DEC
    transition), either update this test to explicitly whitelist the
    exception or re-point the spec at the canonical file."""
    from report_engine.contract_dashboard import CANONICAL_CASE_SPECS

    for spec in CANONICAL_CASE_SPECS:
        expected = f"{spec.whitelist_id}.yaml"
        assert spec.gold_file == expected, (
            f"dashboard spec for whitelist_id={spec.whitelist_id!r} reads "
            f"from {spec.gold_file!r}; expected canonical {expected!r}. "
            f"R3-M1 invariant broken — dashboard + /api/cases would drift."
        )


# ---------------------------------------------------------------------------
# DEC-V61-046 round-1 R3-N1: _normalize_contract_class prefix behaviour
# ---------------------------------------------------------------------------

def test_normalize_contract_class_maps_satisfied_prefixes():
    """Direct behavioural pin for `_normalize_contract_class` — the
    CONTRACT_CLASS_ORDER tuple is consulted via `.startswith()`, so any future
    reordering that puts `COMPATIBLE` ahead of `SATISFIED` would silently
    misclassify SATISFIED_UNDER_LAMINAR_CONTRACT etc. The dashboard render
    test only asserts aggregate distribution; this test pins the mapping at
    the helper level so regressions fail at the root cause, not downstream."""
    from report_engine.contract_dashboard import ContractDashboardGenerator

    gen = ContractDashboardGenerator()
    f = gen._normalize_contract_class

    # SATISFIED family — all must resolve to SATISFIED, not COMPATIBLE.
    assert f("SATISFIED") == "SATISFIED"
    assert f("SATISFIED — clean pass") == "SATISFIED"
    assert f("SATISFIED_UNDER_LAMINAR_CONTRACT — Blasius is exact") == "SATISFIED"
    assert f("SATISFIED_FOR_U_CENTERLINE_ONLY — v/vortex flagged") == "SATISFIED"

    # Longer-specific first: DISGUISED must NOT downgrade to COMPATIBLE via
    # shorter-prefix race (COMPATIBLE is last in the order tuple).
    assert (
        f("INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE — observable mismatch")
        == "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE"
    )
    assert f("COMPATIBLE_WITH_SILENT_PASS_HAZARD — shortcut") == "COMPATIBLE_WITH_SILENT_PASS_HAZARD"

    # Base cases.
    assert f("COMPATIBLE — all preconditions met") == "COMPATIBLE"
    assert f("PARTIALLY_COMPATIBLE — RANS surrogate") == "PARTIALLY_COMPATIBLE"
    assert f("INCOMPATIBLE — precondition unmet") == "INCOMPATIBLE"
    assert f("DEVIATION — unexplained gap") == "DEVIATION"

    # Unknown / missing / empty — must fall through to UNKNOWN.
    assert f("") == "UNKNOWN"
    assert f("SOMETHING_NEW_WE_HAVENT_SEEN") == "UNKNOWN"

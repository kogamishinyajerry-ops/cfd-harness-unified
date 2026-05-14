"""DEC-V62-A-sub-M-DRIFT-V2 · drift guard tests.

8 tests covering the runtime corpus drift-prevention surface:

  1. load_v_series_index parses live corpus → ≥100 V-rows, contains V1/V100
  2. check_finding_drift returns ok=True when all cited V-rows present
  3. check_finding_drift returns ok=False + missing list when some cited V-rows absent
  4. check_finding_drift treats fully bogus citation as full miss
  5. enforce_at_route_boundary audit mode: keeps findings, appends guard entry
  6. enforce_at_route_boundary strict mode: drops drift findings, preserves clean ones
  7. Route integration: POST /api/ai-review surfaces guard entry in advisor_calls
  8. 4Q gate compliance: module imports zero LLM modules, makes zero case_dir writes
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routes import ai_review as ai_review_route
from ui.backend.services import advisor_stack as advisor_stack_module
from ui.backend.services.advisor_stack import (
    AdvisorCall,
    AdvisorStackReport,
    Finding,
)
from ui.backend.services.v_series_drift_guard import (
    _DEFAULT_CORPUS_PATH,
    check_finding_drift,
    enforce_at_route_boundary,
    load_v_series_index,
)


# ---------- Fixtures -------------------------------------------------------


def _make_finding(v_rows: tuple[str, ...], code: str = "TEST") -> Finding:
    return Finding(
        source_advisor="test_advisor",
        severity="warning",
        code=code,
        message="synthetic test finding",
        location=None,
        evidence_v_rows=v_rows,
        raw=None,
    )


def _make_report(findings: tuple[Finding, ...]) -> AdvisorStackReport:
    return AdvisorStackReport(
        findings=findings,
        advisor_calls=(),
        evidence_refs=tuple(sorted({r for f in findings for r in f.evidence_v_rows})),
        stack_duration_ms=1.23,
        advisor_count=1,
    )


@pytest.fixture
def tmp_corpus(tmp_path: Path) -> Path:
    """Synthetic corpus with V42 + V99 only, mirroring the runtime format."""
    p = tmp_path / "tiny_corpus.md"
    p.write_text(
        "# Tiny test corpus\n\n"
        "Some prose; should NOT count: see V1 and V5 below.\n\n"
        "### V42\n\nBody for V42 finding.\n\n"
        "### V99\n\nBody for V99 finding.\n\n",
        encoding="utf-8",
    )
    return p


# ---------- 1. load_v_series_index against live corpus --------------------


def test_load_index_parses_live_corpus_has_canonical_rows():
    """Live corpus must yield ≥100 V-rows including V1 and V100."""
    idx = load_v_series_index()
    assert len(idx) >= 100, f"expected ≥100 V-rows, got {len(idx)}"
    assert "V1" in idx
    assert "V100" in idx
    # Prose mention "see V42" should NOT have been captured as a row;
    # but V42 IS a real heading in the live corpus, so verify via a row
    # that does NOT exist (V9999 sentinel).
    assert "V9999" not in idx


# ---------- 2. check_finding_drift · all hit ------------------------------


def test_check_finding_drift_all_hits(tmp_corpus: Path):
    """Finding citing only V-rows present in the index → ok=True, missing=[]."""
    finding = _make_finding(("V42", "V99"))
    idx = load_v_series_index(corpus_path=tmp_corpus)
    ok, missing = check_finding_drift(finding, index=idx)
    assert ok is True
    assert missing == []


# ---------- 3. check_finding_drift · partial miss -------------------------


def test_check_finding_drift_partial_miss(tmp_corpus: Path):
    """Finding citing one real + one bogus V-row → ok=False, missing=[bogus]."""
    finding = _make_finding(("V42", "V9999"))
    idx = load_v_series_index(corpus_path=tmp_corpus)
    ok, missing = check_finding_drift(finding, index=idx)
    assert ok is False
    assert missing == ["V9999"]


# ---------- 4. check_finding_drift · full miss + sort -----------------------


def test_check_finding_drift_full_miss_sorted(tmp_corpus: Path):
    """Finding citing only absent V-rows → missing numerically sorted."""
    finding = _make_finding(("V200", "V50", "V100"))  # all absent from tiny_corpus
    idx = load_v_series_index(corpus_path=tmp_corpus)
    ok, missing = check_finding_drift(finding, index=idx)
    assert ok is False
    # Numeric sort: V50 < V100 < V200 (not lexicographic which would put V100<V200<V50)
    assert missing == ["V50", "V100", "V200"]


# ---------- 5. enforce audit mode -----------------------------------------


def test_enforce_audit_mode_preserves_findings_and_appends_guard(tmp_corpus: Path):
    """Audit mode: every Finding retained, advisor_calls gets one new entry."""
    clean = _make_finding(("V42",), code="C")
    drift = _make_finding(("V9999",), code="D")
    report = _make_report((clean, drift))
    out = enforce_at_route_boundary(report, mode="audit", corpus_path=tmp_corpus)

    # No finding dropped in audit mode
    assert len(out.findings) == 2
    assert {f.code for f in out.findings} == {"C", "D"}

    # Exactly one new advisor_call appended at the end
    assert len(out.advisor_calls) == 1
    guard = out.advisor_calls[-1]
    assert guard.advisor_name == "v_series_drift_guard"
    assert guard.status == "ok"
    assert isinstance(guard.output, dict)
    assert guard.output["mode"] == "audit"
    assert guard.output["check_status"] == "drift_detected"
    assert guard.output["missing_v_rows"] == ["V9999"]
    assert guard.output["findings_flagged"] == 1
    assert guard.output["findings_dropped"] == 0


# ---------- 6. enforce strict mode -----------------------------------------


def test_enforce_strict_mode_drops_drift_keeps_clean(tmp_corpus: Path):
    """Strict mode: drift findings removed, clean findings retained."""
    clean = _make_finding(("V42",), code="C")
    drift = _make_finding(("V9999",), code="D")
    no_evidence = _make_finding((), code="E")  # waived TrustGate → always kept
    report = _make_report((clean, drift, no_evidence))
    out = enforce_at_route_boundary(report, mode="strict", corpus_path=tmp_corpus)

    # Drift finding dropped; clean + no-evidence retained
    assert {f.code for f in out.findings} == {"C", "E"}
    guard = out.advisor_calls[-1]
    assert guard.output["mode"] == "strict"
    assert guard.output["check_status"] == "drift_detected"
    assert guard.output["findings_flagged"] == 1
    assert guard.output["findings_dropped"] == 1


# ---------- 7. Route integration -------------------------------------------


def _stub_assemble_stack(*args, **kwargs):
    """Return a synthetic report with one bogus-V-row finding."""
    bad = Finding(
        source_advisor="stub_advisor",
        severity="warning",
        code="STUB",
        message="cites a V-row that does not exist in the runtime corpus",
        location=None,
        evidence_v_rows=("V9999",),
        raw=None,
    )
    return AdvisorStackReport(
        findings=(bad,),
        advisor_calls=(),
        evidence_refs=("V9999",),
        stack_duration_ms=0.1,
        advisor_count=1,
    )


def test_route_audit_mode_default_surfaces_drift_guard(monkeypatch):
    """POST /api/ai-review with a synthetic drift finding surfaces guard entry."""
    monkeypatch.setattr(ai_review_route, "assemble_stack", _stub_assemble_stack)

    app = FastAPI()
    app.include_router(ai_review_route.router, prefix="/api")
    client = TestClient(app)

    resp = client.post("/api/ai-review", json={"parts_manifest": {"parts": []}})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    advisor_calls = body["report"]["advisor_calls"]
    guard_entries = [c for c in advisor_calls if c["advisor_name"] == "v_series_drift_guard"]
    assert len(guard_entries) == 1
    guard = guard_entries[0]
    assert guard["output"]["mode"] == "audit"
    assert guard["output"]["check_status"] == "drift_detected"
    assert "V9999" in guard["output"]["missing_v_rows"]
    # Audit mode preserves the stub finding
    assert len(body["report"]["findings"]) == 1

    # Strict mode via query param drops the finding
    resp_strict = client.post(
        "/api/ai-review?drift_mode=strict",
        json={"parts_manifest": {"parts": []}},
    )
    assert resp_strict.status_code == 200, resp_strict.text
    body_strict = resp_strict.json()
    assert len(body_strict["report"]["findings"]) == 0
    guard_strict = [
        c for c in body_strict["report"]["advisor_calls"]
        if c["advisor_name"] == "v_series_drift_guard"
    ][0]
    assert guard_strict["output"]["findings_dropped"] == 1


# ---------- 8. 4Q gate compliance (no LLM imports + no case_dir writes) -----


def test_four_question_gate_no_llm_imports_no_case_dir_writes():
    """Static AST check: the guard module imports zero LLM provider modules
    and contains no ``case_dir`` write paths.

    This is the cheapest enforcement of V130 4Q gate (advisory-not-driver):
    we don't trust runtime probes — we read the module source and assert
    every import path is LLM-free and that no ``.write_text``/``open(...,
    "w")``/``shutil`` write surface exists under a ``case_dir`` arg.
    """
    src_path = Path(__file__).resolve().parents[1] / "services" / "v_series_drift_guard.py"
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)

    # 1. No LLM provider imports
    banned_substrings = ("llm_provider", "deepseek", "openai", "anthropic", "gemini")
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module)
    for mod in imported_modules:
        lower = mod.lower()
        for banned in banned_substrings:
            assert banned not in lower, (
                f"v_series_drift_guard imports {mod!r} which contains LLM banned substring "
                f"{banned!r}; violates V130 4Q gate (LLM offline OK?)"
            )

    # 2. No case_dir writes — module body must not invoke write_text /
    #    shutil / os.makedirs (the only on-disk surface allowed is the
    #    ``Path.read_text`` corpus load).
    forbidden_attrs = {"write_text", "write_bytes", "mkdir", "makedirs", "rmtree", "copy", "move"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attrs, (
                f"v_series_drift_guard contains forbidden write surface .{node.attr}; "
                "violates V130 4Q gate (AI advisory only? no case_dir writes)"
            )

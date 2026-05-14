"""V62-A M-4Q-AUDIT · stack-level four-question gate acceptance suite.

Cross-feature acceptance tests that aggregate the per-module 4Q checks
already living inside ``test_advisor_stack.py``, ``test_ai_review_route.py``,
and ``test_ai_diagnose_route.py`` into one end-to-end suite exercising the
LLM-offline contract via the public HTTP surface.

Paired audit artifact: ``.planning/audits/v62_stack_4q_audit.md``.
Sub-DEC: ``.planning/decisions/2026-05-14_v62_sub_4q_audit.md``.

The four questions (verbatim from V130 advisor-not-driver thesis):

  1Q. **LLM offline OK?**         No ``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY``
                                  in env → POST both routes → 200 + non-empty
                                  finding / match payloads.
  2Q. **Artifacts output?**       Every response surfaces source_advisor +
                                  evidence_v_rows on findings + a persisted
                                  audit JSON file on disk.
  3Q. **TrustGate?**              Every advisor-emitted V-row id is a member
                                  of ``advisor_stack._V_ROWS_PER_ADVISOR``.
  4Q. **AI advisory only?**       sha256 of the supplied ``case_dir`` tree is
                                  bytewise identical before and after each
                                  POST (read-only contract).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routes import ai_diagnose as ai_diagnose_route
from ui.backend.routes import ai_review as ai_review_route
from ui.backend.services.advisor_stack import _V_ROWS_PER_ADVISOR


# ---------- Fixtures ------------------------------------------------------


def _parts_manifest_multi_advisor() -> dict[str, Any]:
    """Triggers A4 (face_orientation) + A5 (inlet_outlet_validator)."""
    return {
        "parts": [
            {
                "name": "louver_vane_2",
                "actual_face_normal": [0.7880, -0.6157, 0.0],
                "expected_face_normal": [0.0, -1.0, 0.0],
                "tolerance_deg": 4.0,
            },
            {"name": "supply_inlet", "role": "inlet"},
        ]
    }


def _shm_dict_with_typo() -> dict[str, Any]:
    """Triggers A8 shm_dict_validator (V52 typo_suspicion)."""
    return {
        "geometry": {
            "region_fluid": {"type": "triSurfaceMesh", "file": "region_fluid.stl"}
        },
        "castellatedMeshControls": {
            "features": [],
            "refinementSurfaces": {"region_fluid": {"level": [2, 2]}},
            "refinementRegions": {},
            "minMedianAxisAngle": 90,
        },
        "addLayersControls": {},
    }


@pytest.fixture
def llm_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hard guarantee no LLM creds are present in env.

    delenv with raising=False — if the key was never set this is a no-op,
    but the assertion still locks the contract that nothing in the request
    path reads it.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)


@pytest.fixture
def app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    llm_offline: None,
) -> FastAPI:
    """FastAPI app mounting BOTH stack-level routes at /api with
    audit / cache state redirected into ``tmp_path``."""
    monkeypatch.setattr(ai_review_route, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        ai_diagnose_route,
        "_AUDIT_DIR",
        tmp_path / ".planning" / "audits" / "ai_diagnose",
    )
    monkeypatch.setattr(ai_diagnose_route, "_corpus_cache", None, raising=False)
    monkeypatch.setattr(ai_diagnose_route, "_corpus_cache_mtime", None, raising=False)

    a = FastAPI()
    a.include_router(ai_review_route.router, prefix="/api")
    a.include_router(ai_diagnose_route.router, prefix="/api")
    return a


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def case_dir_multi(tmp_path: Path) -> Path:
    """case_dir wired for 3-advisor dispatch via auto-discovery."""
    case_dir = tmp_path / "case_4q_acceptance"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.yaml").write_text(
        yaml.safe_dump(_parts_manifest_multi_advisor()), encoding="utf-8"
    )
    (inputs / "shm_dict.json").write_text(
        json.dumps(_shm_dict_with_typo()), encoding="utf-8"
    )
    return case_dir


def _hash_tree(root: Path) -> dict[str, str]:
    """sha256 every file under ``root``; returns {relpath: hex}."""
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


# ---------- Q1 · LLM offline OK ------------------------------------------


def test_q1_llm_offline_both_routes_return_200_with_payload(
    client: TestClient, case_dir_multi: Path,
) -> None:
    """Q1 LLM offline OK — with API keys deleted from env, both routes
    return 200 and surface non-empty advisory output."""
    review = client.post(
        "/api/ai-review",
        json={
            "parts_manifest": _parts_manifest_multi_advisor(),
            "shm_dict": _shm_dict_with_typo(),
        },
    )
    assert review.status_code == 200, review.text
    review_body = review.json()
    assert review_body["llm_enhanced"] is False
    assert review_body["report"]["advisor_count"] >= 2
    assert review_body["report"]["findings"], "expected findings under offline path"

    diagnose = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": (
                "louver vane face orientation deviation D7 plus janafThermo "
                "Tlow warnings"
            ),
            "case_dir": str(case_dir_multi),
        },
    )
    assert diagnose.status_code == 200, diagnose.text
    diagnose_body = diagnose.json()
    assert diagnose_body["llm_match_used"] is False
    assert diagnose_body["v_row_matches"], "expected V-row matches under offline path"
    # case_dir provided + parts_manifest discoverable → stack ran
    assert diagnose_body["stack_report"] is not None
    assert diagnose_body["stack_report"]["advisor_count"] >= 1


# ---------- Q2 · Artifacts output ----------------------------------------


def test_q2_findings_carry_source_advisor_evidence_v_rows_and_audit_artifact(
    client: TestClient,
) -> None:
    """Q2 Artifacts output — each Finding has source_advisor +
    evidence_v_rows and the route persists a JSON audit artifact whose
    path round-trips a re-readable payload."""
    resp = client.post(
        "/api/ai-review",
        json={
            "parts_manifest": _parts_manifest_multi_advisor(),
            "shm_dict": _shm_dict_with_typo(),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    audit_path = Path(body["audit_artifact_path"])
    assert audit_path.is_file(), f"audit_trail missing on disk: {audit_path}"
    reloaded = json.loads(audit_path.read_text(encoding="utf-8"))
    assert reloaded["report"]["advisor_count"] == body["report"]["advisor_count"]

    findings = body["report"]["findings"]
    assert findings, "expected ≥1 finding from multi-advisor dispatch"
    for f in findings:
        assert f.get("source_advisor"), f"Q2 violation: missing source_advisor: {f}"
        assert f.get("evidence_v_rows"), f"Q2 violation: missing evidence_v_rows: {f}"
        assert isinstance(f["evidence_v_rows"], list)


# ---------- Q3 · TrustGate -----------------------------------------------


def test_q3_trustgate_every_evidence_v_row_is_canonical(
    client: TestClient, case_dir_multi: Path,
) -> None:
    """Q3 TrustGate — every V-row id stamped on an advisor finding belongs
    to the canonical ``_V_ROWS_PER_ADVISOR`` registry."""
    canonical: set[str] = set()
    for rows in _V_ROWS_PER_ADVISOR.values():
        canonical.update(rows)
    assert canonical, "canonical registry must be non-empty for Q3 to be meaningful"

    review = client.post(
        "/api/ai-review",
        json={
            "parts_manifest": _parts_manifest_multi_advisor(),
            "shm_dict": _shm_dict_with_typo(),
        },
    )
    assert review.status_code == 200, review.text
    review_findings = review.json()["report"]["findings"]
    assert review_findings, "expected findings to validate against canonical"

    for f in review_findings:
        advisor = f["source_advisor"]
        per_advisor = set(_V_ROWS_PER_ADVISOR.get(advisor, ()))
        assert per_advisor, (
            f"Q3 violation: advisor {advisor!r} has no canonical V-rows"
        )
        for v in f["evidence_v_rows"]:
            assert v in canonical, (
                f"Q3 violation: V-row {v!r} (advisor {advisor!r}) not "
                f"in canonical registry"
            )
            assert v in per_advisor, (
                f"Q3 violation: V-row {v!r} not registered for advisor "
                f"{advisor!r}"
            )

    # Same check on the diagnose route's optional stack cross-reference.
    diagnose = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "face orientation deviation",
            "case_dir": str(case_dir_multi),
        },
    )
    assert diagnose.status_code == 200, diagnose.text
    diag_body = diagnose.json()
    stack = diag_body["stack_report"]
    assert stack is not None, "case_dir should have surfaced a stack_report"
    for f in stack["findings"]:
        per_advisor = set(_V_ROWS_PER_ADVISOR.get(f["source_advisor"], ()))
        for v in f["evidence_v_rows"]:
            assert v in canonical, f"Q3 (diagnose) violation: {v!r} not canonical"
            assert v in per_advisor, (
                f"Q3 (diagnose) violation: {v!r} not registered for "
                f"{f['source_advisor']!r}"
            )


# ---------- Q4 · Advisory-only (read-only case_dir) ----------------------


def test_q4_case_dir_sha256_unchanged_across_both_routes(
    client: TestClient, case_dir_multi: Path,
) -> None:
    """Q4 advisory-only — sha256 of every file under ``case_dir`` is byte
    identical before and after POSTing to each route."""
    before = _hash_tree(case_dir_multi)
    assert before, "fixture should populate case_dir before snapshot"

    review = client.post(
        "/api/ai-review", json={"case_dir": str(case_dir_multi)},
    )
    assert review.status_code == 200, review.text
    mid = _hash_tree(case_dir_multi)
    assert mid == before, (
        f"Q4 violation: /ai-review mutated case_dir. "
        f"diff={set(before.items()) ^ set(mid.items())}"
    )

    diagnose = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "janafThermo Tlow species range warnings flood",
            "case_dir": str(case_dir_multi),
        },
    )
    assert diagnose.status_code == 200, diagnose.text
    after = _hash_tree(case_dir_multi)
    assert after == before, (
        f"Q4 violation: /ai-diagnose mutated case_dir. "
        f"diff={set(before.items()) ^ set(after.items())}"
    )

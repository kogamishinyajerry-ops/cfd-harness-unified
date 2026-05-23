"""DEC-V61-202-SUB-M30-CYCLE1 · workbench_frame route + decide() tests.

Coverage matrix:
    1. decide() determinism — same state → same frame
    2. decide() V130 LLM-offline invariant — no network imports
    3. Priority tree: FAIL > critical gap > WARN > soft gap > default
    4. Step-relevance routing: a Step 4 problem doesn't surface on Step 1
    5. Step-default frames for all 5 steps
    6. Focus → viewport_overlays (patch_highlight)
    7. case_007 VOF shape: Gap #48 (p_rgh) surfaces as bottom_card on Step 4
    8. case_007 VOF shape: Gap #49 (phases derivation) surfaces too
    9. Route smoke: 404 on missing case
    10. Route smoke: live load of a fixture-shaped case
    11. State SHA stability across re-render of same state
    12. Bottom-card cap at 8 entries
"""
from __future__ import annotations

import json
import secrets
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from ui.backend.schemas.workbench_frame import CaseStateSnapshot
from ui.backend.services.workbench_decide import decide


# ─────────────────── unit tests on decide() (no I/O) ───────────────────


def _base_state(step: int = 1, **overrides) -> CaseStateSnapshot:
    base = {
        "case_id": "test_case",
        "step": step,
        "manifest": {},
        "artifacts": {},
        "completeness": None,
    }
    base.update(overrides)
    return CaseStateSnapshot(**base)


def test_decide_returns_step_default_when_no_signals():
    state = _base_state(step=3)
    frame = decide(state)
    assert frame.rail_primary.kind == "step_default"
    assert frame.step == 3
    assert frame.case_id == "test_case"
    # Step hint should be the only bottom card on a clean case.
    assert len(frame.bottom_cards) == 1
    assert frame.bottom_cards[0].kind == "step_hint"


def test_decide_is_deterministic_same_state_same_frame():
    state = _base_state(step=4)
    f1 = decide(state)
    f2 = decide(state)
    assert f1.state_sha == f2.state_sha
    assert f1.rail_primary == f2.rail_primary
    assert f1.bottom_cards == f2.bottom_cards


def test_decide_state_sha_changes_on_step_change():
    s1 = _base_state(step=1)
    s2 = _base_state(step=2)
    assert decide(s1).state_sha != decide(s2).state_sha


def test_decide_state_sha_changes_on_focus_change():
    s1 = _base_state(step=4, focus_patch=None)
    s2 = _base_state(step=4, focus_patch="inlet")
    assert decide(s1).state_sha != decide(s2).state_sha


def test_decide_renders_all_5_step_defaults():
    for step in (1, 2, 3, 4, 5):
        frame = decide(_base_state(step=step))
        assert frame.rail_primary.kind == "step_default"
        # Each step has a recognizable Chinese label.
        assert f"Step {step}" in frame.rail_primary.title


def test_decide_fail_problem_beats_critical_gap():
    """Priority 1 (FAIL audit finding) outranks Priority 2 (critical
    missing field). Both on step 4."""
    state = _base_state(
        step=4,
        artifacts={
            "bc_quality.json": {
                "verdict": "fail",
                "reason": "missing 0/U file",
                "findings": [
                    {
                        "severity": "fail",
                        "title": "BC fields missing",
                        "message": "expected 0/U not on disk",
                        "field_path": "bc_contract.inlet.velocity",
                    }
                ],
            }
        },
        completeness={
            "missing": [
                {
                    "field_path": "bc_contract.outlet.pressure",
                    "severity": "critical",
                    "why": "outlet pressure type not set",
                }
            ]
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "problem_fix"
    assert "BC fields missing" in frame.rail_primary.title


def test_decide_critical_gap_when_no_fail():
    """Priority 2 (critical missing field) wins when no FAIL."""
    state = _base_state(
        step=4,
        completeness={
            "missing": [
                {
                    "field_path": "bc_contract.outlet.pressure",
                    "severity": "critical",
                    "why": "outlet pressure type not set",
                }
            ]
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "info_gap"
    assert "bc_contract.outlet.pressure" in frame.rail_primary.title


def test_decide_attaches_ship_vof_bc_patches_skeleton_on_step4():
    """DEC-V61-202-SUB-M31-CYCLE1: when (field_path=bc.patches,
    case_family=ship_vof) hits a step-4 gap, the rail must carry the
    canonical 3-patch skeleton + the 'Apply skeleton' CTA label."""
    state = _base_state(
        step=4,
        manifest={"case_family": "ship_vof"},
        completeness={
            "missing": [
                {
                    "field_path": "bc.patches",
                    "severity": "critical",
                    "why": "at least one boundary patch required",
                }
            ]
        },
    )
    frame = decide(state)
    rail = frame.rail_primary
    assert rail.kind == "info_gap"
    assert rail.field_path == "bc.patches"
    assert rail.suggested_skeleton is not None
    assert set(rail.suggested_skeleton.keys()) == {"inlet", "outlet", "wall"}
    assert rail.suggested_skeleton["inlet"]["patch_type"] == "fixedValue"
    assert rail.suggested_skeleton["outlet"]["patch_type"] == "zeroGradient"
    assert rail.suggested_skeleton["wall"]["patch_type"] == "noSlip"
    assert rail.cta_label == "应用骨架 / Apply skeleton"
    # Provenance must record the skeleton presence so audit trail can
    # tell skeleton-driven from scalar-default-driven rails apart.
    prov_joined = " · ".join(rail.provenance)
    assert "skeleton_keys=" in prov_joined


def test_decide_no_skeleton_when_case_family_unknown():
    """Cycle 1 fail-soft: unknown case_family → no skeleton attached;
    rail falls back to the "Edit" CTA. Cycles 2-5 add more families."""
    state = _base_state(
        step=4,
        manifest={"case_family": "unknown_family_xyz"},
        completeness={
            "missing": [
                {
                    "field_path": "bc.patches",
                    "severity": "critical",
                    "why": "at least one boundary patch required",
                }
            ]
        },
    )
    frame = decide(state)
    assert frame.rail_primary.suggested_skeleton is None
    assert frame.rail_primary.cta_label == "编辑 / Edit"


def test_decide_skeleton_does_not_clobber_existing_suggested_default():
    """If a gap somehow already carries BOTH a scalar suggested_default
    AND we'd attach a skeleton, the scalar wins on cta_label (UI shows
    the scalar Apply primary; the skeleton CTA renders alongside as a
    secondary affordance). Both fields are forwarded so the frontend
    sees the full picture."""
    state = _base_state(
        step=4,
        manifest={"case_family": "ship_vof"},
        completeness={
            "missing": [
                {
                    "field_path": "bc.patches",
                    "severity": "critical",
                    "why": "...",
                    "suggested_default": {"inlet": {"patch_type": "fixedValue"}},
                }
            ]
        },
    )
    frame = decide(state)
    rail = frame.rail_primary
    assert rail.suggested_default is not None
    assert rail.suggested_skeleton is not None
    assert rail.cta_label == "填入 / Apply"  # scalar wins primary CTA


def test_decide_step_relevance_routes_step4_problem_to_step4():
    """A bc_quality.json problem should NOT surface on Step 1."""
    artifacts = {
        "bc_quality.json": {
            "findings": [
                {"severity": "fail", "title": "BC fail", "message": "..."}
            ],
        }
    }
    f_step4 = decide(_base_state(step=4, artifacts=artifacts))
    f_step1 = decide(_base_state(step=1, artifacts=artifacts))
    assert f_step4.rail_primary.kind == "problem_fix"
    assert f_step1.rail_primary.kind == "step_default"


def test_decide_focus_patch_emits_viewport_overlay():
    state = _base_state(step=4, focus_patch="inlet")
    frame = decide(state)
    overlays = [o for o in frame.viewport_overlays if o.kind == "patch_highlight"]
    assert len(overlays) == 1
    assert overlays[0].target == "inlet"


def test_decide_step2_cell_count_badge():
    state = _base_state(
        step=2,
        artifacts={
            "mesh_report.json": {"n_cells": 1_240_000, "max_non_orthogonality": 65},
        },
    )
    frame = decide(state)
    badges = [
        o for o in frame.viewport_overlays if o.kind == "cell_count_badge"
    ]
    assert len(badges) == 1
    assert "1.2M" in (badges[0].label or "")


def test_decide_step2_high_non_orthogonality_warns():
    state = _base_state(
        step=2,
        artifacts={
            "mesh_report.json": {"n_cells": 50_000, "max_non_orthogonality": 78},
        },
    )
    frame = decide(state)
    warns = [
        o for o in frame.viewport_overlays if o.kind == "checkmesh_warn"
    ]
    assert len(warns) == 1
    assert warns[0].severity == "warn"


def test_decide_step2_severe_non_orthogonality_fails():
    state = _base_state(
        step=2,
        artifacts={
            "mesh_report.json": {"n_cells": 50_000, "max_non_orthogonality": 88},
        },
    )
    frame = decide(state)
    warns = [
        o for o in frame.viewport_overlays if o.kind == "checkmesh_warn"
    ]
    assert warns[0].severity == "fail"


def test_decide_gap48_p_rgh_surfaces_on_step4_for_vof_case():
    """case_007 VOF shape: when bc_quality.json reports missing p_rgh,
    rail_primary should be problem_fix with that signal."""
    state = _base_state(
        step=4,
        artifacts={
            "bc_quality.json": {
                "findings": [
                    {
                        "severity": "fail",
                        "title": "missing field p_rgh",
                        "message": "interFoam expects 0/p_rgh; not found",
                        "field_path": "bc_contract.pressure",
                    }
                ]
            }
        },
        manifest={"vof_contract": {"phases": ["water", "air"]}},
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "problem_fix"
    titles = [c.title for c in frame.bottom_cards]
    assert any("p_rgh" in t for t in titles)


def test_decide_gap49_phases_surfaces_on_step3():
    """Step 3 (physics) gaps for missing vof_contract surface as rail
    info_gap when manifest lacks phases declaration."""
    state = _base_state(
        step=3,
        completeness={
            "missing": [
                {
                    "field_path": "vof_contract.phases",
                    "severity": "critical",
                    "why": "interFoam case requires vof_contract.phases",
                }
            ]
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "info_gap"
    assert "vof_contract.phases" in frame.rail_primary.title


def test_decide_bottom_cards_capped_at_8():
    findings = [
        {
            "severity": "warn",
            "title": f"finding {i}",
            "message": f"msg {i}",
        }
        for i in range(20)
    ]
    state = _base_state(
        step=4, artifacts={"bc_quality.json": {"findings": findings}}
    )
    frame = decide(state)
    assert len(frame.bottom_cards) == 8


def test_decide_no_llm_imports_in_module():
    """V130 invariant: workbench_decide.py must not import any LLM client."""
    import ui.backend.services.workbench_decide as mod
    import ast
    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    forbidden = {"openai", "anthropic", "httpx", "requests", "aiohttp"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in (node.names if hasattr(node, "names") else [])]
            module = getattr(node, "module", None)
            for n in names + ([module] if module else []):
                if n is None:
                    continue
                top = n.split(".")[0]
                assert top not in forbidden, (
                    f"V130 violation: {mod.__file__} imports {n}"
                )


# ─────────────────── route smoke tests ───────────────────


def _client() -> TestClient:
    from ui.backend.main import app
    return TestClient(app)


def _safe_id() -> str:
    return f"imported_2026-05-22T00-00-00Z_{secrets.token_hex(4)}"


def _stage_imported_case(monkeypatch, tmp_path: Path, manifest: dict) -> str:
    """Stage an imported_user case_dir with a manifest + empty artifacts dir.

    Returns the case_id used.
    """
    case_id = _safe_id()
    imported_root = tmp_path / "imported"
    imported_root.mkdir()
    case_dir = imported_root / case_id
    case_dir.mkdir()
    (case_dir / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))
    (case_dir / "artifacts").mkdir()

    # Patch both the resolver in workbench_frame and the resolver
    # case_completeness uses.
    monkeypatch.setattr(
        "ui.backend.routes.workbench_frame.IMPORTED_DIR", imported_root
    )
    monkeypatch.setattr(
        "ui.backend.services.case_completeness.analyzer.IMPORTED_DIR",
        imported_root,
    )
    return case_id


def test_route_returns_404_on_missing_case(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "ui.backend.routes.workbench_frame.IMPORTED_DIR", tmp_path / "imported"
    )
    monkeypatch.setattr(
        "ui.backend.routes.workbench_frame.DRAFTS_DIR", tmp_path / "drafts"
    )
    r = _client().get("/api/cases/no_such_case/workbench_frame?step=1")
    assert r.status_code == 404


def test_route_returns_step_default_for_minimal_case(monkeypatch, tmp_path):
    case_id = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {
            "case_id": "x",
            "case_family": "test",
            "solver_backend": "openfoam",
            "physics": {"regime": "steady_incompressible_laminar"},
        },
    )
    r = _client().get(f"/api/cases/{case_id}/workbench_frame?step=1")
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["case_id"] == case_id
    assert payload["step"] == 1
    assert payload["rail_primary"]["kind"] in ("step_default", "info_gap")


def test_route_surfaces_bc_audit_findings(monkeypatch, tmp_path):
    case_id = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {"case_id": "x", "case_family": "test", "solver_backend": "openfoam"},
    )
    # Drop a bc_quality.json into the case dir.
    case_dir = (tmp_path / "imported" / case_id)
    (case_dir / "artifacts" / "bc_quality.json").write_text(
        json.dumps(
            {
                "verdict": "fail",
                "reason": "synthetic test failure",
                "findings": [
                    {
                        "severity": "fail",
                        "title": "synthetic",
                        "message": "for-test",
                        "field_path": "bc_contract.inlet",
                    }
                ],
            }
        )
    )
    r = _client().get(f"/api/cases/{case_id}/workbench_frame?step=4")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rail_primary"]["kind"] == "problem_fix"
    titles = [c["title"] for c in body["bottom_cards"]]
    assert any("synthetic" in t for t in titles)


def test_route_step_query_validates_1_through_5(monkeypatch, tmp_path):
    case_id = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {"case_id": "x", "case_family": "test", "solver_backend": "openfoam"},
    )
    r0 = _client().get(f"/api/cases/{case_id}/workbench_frame?step=0")
    assert r0.status_code == 422
    r6 = _client().get(f"/api/cases/{case_id}/workbench_frame?step=6")
    assert r6.status_code == 422
    r3 = _client().get(f"/api/cases/{case_id}/workbench_frame?step=3")
    assert r3.status_code == 200


# ─────────────────── Codex R0 R1 regression tests ───────────────────


def test_r1_whitelist_case_resolves_to_200_not_404(monkeypatch, tmp_path):
    """Codex R0 P1-1: whitelist cases (knowledge/whitelist.yaml) must
    resolve via the workbench_frame endpoint. Pre-fix: 404. Fix:
    _load_manifest checks _load_whitelist() as third branch."""
    # Use lid_driven_cavity — confirmed in whitelist.yaml head.
    monkeypatch.setattr(
        "ui.backend.routes.workbench_frame.IMPORTED_DIR", tmp_path / "x"
    )
    monkeypatch.setattr(
        "ui.backend.routes.workbench_frame.DRAFTS_DIR", tmp_path / "y"
    )
    r = _client().get("/api/cases/lid_driven_cavity/workbench_frame?step=1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_id"] == "lid_driven_cavity"


def test_r1_bc_patches_gap_surfaces_on_step4():
    """Codex R0 P1-2: imported-user BC gaps are reported as `bc.patches`
    (not `bc_contract.patches`) by analyze_case_completeness. Step 4
    must include the `bc.` prefix to route them correctly."""
    state = CaseStateSnapshot(
        case_id="x",
        step=4,
        manifest={},
        artifacts={},
        completeness={
            "missing": [
                {
                    "field_path": "bc.patches",
                    "severity": "critical",
                    "why": "no BC setup yet",
                }
            ]
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "info_gap"
    assert "bc.patches" in frame.rail_primary.title


def test_r1_real_mesh_report_gate_status_fail_surfaces_problem():
    """Codex R0 P1-3: real cfdtrust mesh_report.json uses gate_status
    (top-level) + quality_dimension.dimension_status — not
    findings/issues/problems lists."""
    state = CaseStateSnapshot(
        case_id="x",
        step=2,
        manifest={},
        artifacts={
            "mesh_report.json": {
                "gate_status": "FAIL",
                "quality_dimension": {
                    "dimension_status": "FAIL",
                    "fails": ["max_non_orthogonality"],
                    "metrics": {
                        "max_non_orthogonality": {
                            "actual": 78.5,
                            "threshold": 65.0,
                            "ok": False,
                        }
                    },
                },
                "stats": {"cells": 1_240_000},
                "notes": ["non-ortho exceeds threshold"],
            }
        },
    )
    frame = decide(state)
    # Should surface as problem_fix (not step_default)
    assert frame.rail_primary.kind == "problem_fix"
    # bottom_cards should include at least one audit_finding
    findings = [c for c in frame.bottom_cards if c.kind == "audit_finding"]
    assert len(findings) >= 1


def test_r1_real_mesh_report_stats_cells_overlay():
    """Codex R0 P2: cell count is at stats.cells, not n_cells."""
    state = CaseStateSnapshot(
        case_id="x",
        step=2,
        manifest={},
        artifacts={
            "mesh_report.json": {
                "gate_status": "PASS",
                "stats": {"cells": 2_500_000, "points": 2_700_000},
                "quality_dimension": {
                    "dimension_status": "PASS",
                    "metrics": {
                        "max_non_orthogonality": {
                            "actual": 45.0,
                            "threshold": 65.0,
                            "ok": True,
                        }
                    },
                },
            }
        },
    )
    frame = decide(state)
    badges = [
        o for o in frame.viewport_overlays if o.kind == "cell_count_badge"
    ]
    assert len(badges) == 1
    assert "2.5M" in (badges[0].label or "")


def test_r1_real_mesh_report_high_non_ortho_overlay():
    """Codex R0 P2: max_non_orthogonality is at
    quality_dimension.metrics.max_non_orthogonality.actual."""
    state = CaseStateSnapshot(
        case_id="x",
        step=2,
        manifest={},
        artifacts={
            "mesh_report.json": {
                "stats": {"cells": 100_000},
                "quality_dimension": {
                    "dimension_status": "FAIL",
                    "metrics": {
                        "max_non_orthogonality": {
                            "actual": 82.3,
                            "threshold": 70.0,
                            "ok": False,
                        }
                    },
                },
            }
        },
    )
    frame = decide(state)
    warns = [
        o for o in frame.viewport_overlays if o.kind == "checkmesh_warn"
    ]
    assert len(warns) == 1
    assert "82" in (warns[0].label or "")
    assert warns[0].severity == "warn"


def test_r1_real_bc_audit_gate_status_surfaces_on_step4():
    """Codex R0 P1-3: real bc_audit.json uses gate_status +
    file_presence_dimension etc., not findings list."""
    state = CaseStateSnapshot(
        case_id="x",
        step=4,
        manifest={},
        artifacts={
            "bc_audit.json": {
                "gate_status": "FAIL",
                "file_presence_dimension": {
                    "dimension_status": "FAIL",
                    "fails": ["U", "p"],
                },
                "patch_coverage_dimension": {
                    "dimension_status": "PASS",
                },
            }
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "problem_fix"
    # Should produce ≥2 audit_finding cards (gate + dimension)
    findings = [c for c in frame.bottom_cards if c.kind == "audit_finding"]
    assert len(findings) >= 2


def test_r1_real_trust_report_gates_dict_surfaces_on_step5():
    """Codex R0 P1-3: real trust_report.json uses gates.<name>.status,
    not top-level findings."""
    state = CaseStateSnapshot(
        case_id="x",
        step=5,
        manifest={},
        artifacts={
            "trust_report.json": {
                "case_id": "x",
                "overall_status": "MOCKED",
                "gates": {
                    "solver_execution": {
                        "status": "MOCKED",
                        "summary": "Synthetic solver log; no real CFD",
                    },
                    "geometry_contract": {
                        "status": "FAIL",
                        "summary": "Missing required patches: inlet, outlet",
                    },
                },
            }
        },
    )
    frame = decide(state)
    # FAIL beats MOCKED severity — rail should be problem_fix
    assert frame.rail_primary.kind == "problem_fix"
    # Both gates should show as audit_findings
    findings = [c for c in frame.bottom_cards if c.kind == "audit_finding"]
    titles = " ".join(f.title for f in findings)
    assert "geometry_contract" in titles
    assert "solver_execution" in titles


def test_r1_mocked_gate_status_normalizes_to_warn():
    """Codex R0 P1-3: gate_status=MOCKED should surface as warn (not
    silently swallowed and not fail)."""
    state = CaseStateSnapshot(
        case_id="x",
        step=2,
        manifest={},
        artifacts={
            "mesh_report.json": {
                "gate_status": "MOCKED",
                "checkmesh_invoked": False,
                "notes": ["solver_backend=mocked; checkMesh was not invoked"],
            }
        },
    )
    frame = decide(state)
    # No critical gap + only WARN gate → soft path
    findings = [c for c in frame.bottom_cards if c.kind == "audit_finding"]
    assert len(findings) >= 1
    assert findings[0].severity == "warn"


def test_r1_pass_gate_status_emits_no_problem():
    """Codex R0 P1-3: gate_status=PASS must NOT surface as a problem."""
    state = CaseStateSnapshot(
        case_id="x",
        step=2,
        manifest={},
        artifacts={
            "mesh_report.json": {
                "gate_status": "PASS",
                "stats": {"cells": 100_000},
                "quality_dimension": {"dimension_status": "PASS"},
            }
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "step_default"
    # No audit_findings (PASS shouldn't emit)
    findings = [c for c in frame.bottom_cards if c.kind == "audit_finding"]
    assert len(findings) == 0

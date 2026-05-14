"""Tests for ``ui.backend.services.advisor_stack`` (M-STACK-ASSEMBLY).

V62-A first sub-DEC. Coverage:

1. Empty kwargs → empty report (advisor_count=0, no findings)
2. parts_manifest only → A4 + A5 dispatched, both run
3. shm_dict only → A8 dispatched
4. thermo_dict only → A10 dispatched
5. step_path only → unit_detector dispatched (uses STEP fixture)
6. interface_bodies + interface_specs → A2-v2 dispatched
7. thin_wall_inputs → thin_wall dispatched
8. multi-artifact (parts_manifest + shm_dict + thermo_dict + thin_wall + step
   + interfaces) → ≥6 advisors dispatched, findings merged across them
9. Crash isolation: one advisor raising does not stop the others
10. evidence_refs union across multiple advisors (V79+V81+V52+...)
11. AdvisorCall audit fields populated (name, duration_ms ≥ 0, version)
12. 4Q gate verification: stack module imports include 0 LLM dep
13. 4Q gate verification: stack performs 0 file writes during a typical
    multi-artifact dispatch
14. forward-compat: unknown kwargs do NOT raise
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from ui.backend.services.advisor_stack import (
    AdvisorCall,
    AdvisorStackReport,
    Finding,
    assemble_stack,
)
from ui.backend.services.geometry_ingest import virtual_interface_detector
from ui.backend.services.geometry_ingest.thin_wall_advisor import PatchGeometry


# ---------- Fixtures -------------------------------------------------------


def _parts_manifest_with_d7_violation() -> dict:
    """A4 V79 D7 case: 38° XY-plane rotation on louver_vane_2."""
    return {
        "parts": [
            {
                "name": "louver_vane_2",
                "actual_face_normal": [0.7880, -0.6157, 0.0],
                "expected_face_normal": [0.0, -1.0, 0.0],
                "tolerance_deg": 4.0,
            },
            # A5 V81 violation: through-flow body missing boundary_emission
            {"name": "supply_inlet", "role": "inlet"},
        ]
    }


def _shm_dict_with_typo() -> dict:
    """A8 V52 typo: minMedianAxisAngle (should be minMedialAxisAngle)."""
    return {
        "geometry": {
            "region_fluid": {"type": "triSurfaceMesh", "file": "region_fluid.stl"}
        },
        "castellatedMeshControls": {
            "features": [],
            "refinementSurfaces": {
                "region_fluid": {"level": [2, 2]},
            },
            "refinementRegions": {},
            "minMedianAxisAngle": 90,  # V52 typo
        },
        "addLayersControls": {},
    }


def _thermo_dict_above_canonical_floor() -> dict:
    """A10 V41/V93: Tlow above 200 K canonical floor → tlow_above_canonical."""
    return {
        "N2": {
            "specie": {"molWeight": 28.0134},
            "thermodynamics": {
                "Tlow": 350.0,  # > 200 K canonical → tlow_above_canonical
                "Thigh": 5000.0,
                "Tcommon": 1000.0,
                "highCpCoeffs": [3.0, 0, 0, 0, 0, 0, 0],
                "lowCpCoeffs": [3.0, 0, 0, 0, 0, 0, 0],
            },
            "transport": {"As": 1.4584e-06, "Ts": 110.4},
            "equationOfState": {},
        },
    }


def _interface_bodies_with_d1_gap():
    """A2-v2 D1: two bodies that should have shared but have 0.3 mm gap."""
    Face = virtual_interface_detector.FaceGeometry
    Body = virtual_interface_detector.BodyGeometry
    Spec = virtual_interface_detector.InterfaceSpec
    # body_a face at x=10, normal +x
    fa = Face(
        area=100.0, bbox_min=(10.0, 0, 0), bbox_max=(10.0, 10, 10),
        normal=(1.0, 0, 0), centroid=(10.0, 5.0, 5.0),
    )
    # body_b face at x=10.3, normal -x (0.3 mm gap)
    fb = Face(
        area=100.0, bbox_min=(10.3, 0, 0), bbox_max=(10.3, 10, 10),
        normal=(-1.0, 0, 0), centroid=(10.3, 5.0, 5.0),
    )
    bodies = {
        "body_a": Body(name="body_a", faces=(fa,), centroid=(5.0, 5.0, 5.0)),
        "body_b": Body(name="body_b", faces=(fb,), centroid=(15.0, 5.0, 5.0)),
    }
    specs = [Spec(patch_name="iface_d1", mode="shared", body_a="body_a", body_b="body_b")]
    return bodies, specs


def _thin_wall_inputs_with_at_risk_patch() -> dict:
    """thin_wall: a 0.5 mm patch with 1.0 mm cell size — under 2 cells."""
    return {
        "patches": [PatchGeometry(name="thin_plate", bbox_dimensions=(100.0, 50.0, 0.5))],
        "refinement_levels": {"thin_plate": (0, 0)},
        "background_cell_size": 1.0,
    }


# ---------- Tests ----------------------------------------------------------


def test_empty_kwargs_yields_empty_report() -> None:
    r = assemble_stack()
    assert isinstance(r, AdvisorStackReport)
    assert r.advisor_count == 0
    assert r.findings == ()
    assert r.advisor_calls == ()
    assert r.evidence_refs == ()
    assert r.failed_advisor_count == 0
    assert r.stack_duration_ms >= 0.0


def test_parts_manifest_dispatches_a4_and_a5() -> None:
    r = assemble_stack(parts_manifest=_parts_manifest_with_d7_violation())
    names = {c.advisor_name for c in r.advisor_calls}
    assert names == {"face_orientation_advisor", "inlet_outlet_validator"}
    assert r.advisor_count == 2
    # A4 should produce a critical finding (38° > 2·4° = 8°)
    a4_findings = [f for f in r.findings if f.source_advisor == "face_orientation_advisor"]
    assert len(a4_findings) == 1
    assert a4_findings[0].severity == "critical"
    # A5 should produce a fail finding for missing boundary_emission
    a5_findings = [f for f in r.findings if f.source_advisor == "inlet_outlet_validator"]
    assert len(a5_findings) == 1
    assert a5_findings[0].severity == "fail"


def test_shm_dict_only_dispatches_a8() -> None:
    r = assemble_stack(shm_dict=_shm_dict_with_typo())
    assert r.advisor_count == 1
    assert r.advisor_calls[0].advisor_name == "shm_dict_validator"
    typo_findings = [f for f in r.findings if f.code == "typo_suspicion"]
    assert len(typo_findings) >= 1
    assert "V52" in typo_findings[0].evidence_v_rows
    assert "V86" in typo_findings[0].evidence_v_rows


def test_thermo_dict_only_dispatches_a10() -> None:
    r = assemble_stack(thermo_dict=_thermo_dict_above_canonical_floor())
    assert r.advisor_count == 1
    assert r.advisor_calls[0].advisor_name == "thermo_polynomial_range_advisor"
    breach = [f for f in r.findings if f.code == "tlow_above_canonical"]
    assert len(breach) == 1
    assert breach[0].severity == "warning"
    assert "V41" in breach[0].evidence_v_rows


def test_step_path_dispatches_unit_detector(tmp_path: Path) -> None:
    # Synthesize a minimal STEP header with explicit MM declaration
    step_text = (
        "ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION (('test'),'2;1');\n"
        "FILE_NAME ('t','2026-01-01T00:00:00',(''),(''),'',('',''),'');\n"
        "FILE_SCHEMA (('AUTOMOTIVE_DESIGN'));\nENDSEC;\nDATA;\n"
        "#1 = SI_UNIT(.MILLI., .METRE.);\n"
        "ENDSEC;\nEND-ISO-10303-21;\n"
    )
    step_file = tmp_path / "ut.step"
    step_file.write_text(step_text)
    r = assemble_stack(step_path=step_file, step_bbox_max_extent_raw=500.0)
    assert r.advisor_count == 1
    assert r.advisor_calls[0].advisor_name == "unit_detector"
    # High-confidence MM result → no Finding (recoverable from .raw)
    assert all(f.source_advisor != "unit_detector" for f in r.findings)


def test_interface_bodies_dispatches_a2v2_and_flags_d1() -> None:
    bodies, specs = _interface_bodies_with_d1_gap()
    r = assemble_stack(
        interface_bodies=bodies,
        interface_specs=specs,
        interface_gap_threshold_mm=1.0,
    )
    assert r.advisor_count == 1
    assert r.advisor_calls[0].advisor_name == "virtual_interface_detector"
    d1 = [f for f in r.findings if f.code == "d1_unintended_gap"]
    assert len(d1) == 1
    assert d1[0].severity == "critical"
    assert "V25" in d1[0].evidence_v_rows


def test_thin_wall_inputs_dispatches() -> None:
    r = assemble_stack(thin_wall_inputs=_thin_wall_inputs_with_at_risk_patch())
    assert r.advisor_count == 1
    assert r.advisor_calls[0].advisor_name == "thin_wall_advisor"
    findings = [f for f in r.findings if f.code == "thin_wall_at_risk"]
    assert len(findings) == 1


def test_multi_artifact_dispatches_six_advisors(tmp_path: Path) -> None:
    """Done dim #1: ≥3 advisor calls per route. We exceed with 6."""
    bodies, specs = _interface_bodies_with_d1_gap()
    step_text = (
        "ISO-10303-21;\nHEADER;\nFILE_NAME('t','2026-01-01T00:00:00',(''),"
        "(''),'',('',''),'');\nENDSEC;\nDATA;\n"
        "#1 = SI_UNIT(.MILLI., .METRE.);\nENDSEC;\nEND-ISO-10303-21;\n"
    )
    step_file = tmp_path / "multi.step"
    step_file.write_text(step_text)

    r = assemble_stack(
        parts_manifest=_parts_manifest_with_d7_violation(),
        shm_dict=_shm_dict_with_typo(),
        thermo_dict=_thermo_dict_above_canonical_floor(),
        thin_wall_inputs=_thin_wall_inputs_with_at_risk_patch(),
        step_path=step_file,
        interface_bodies=bodies,
        interface_specs=specs,
    )
    names = {c.advisor_name for c in r.advisor_calls}
    assert names == {
        "face_orientation_advisor",
        "inlet_outlet_validator",
        "shm_dict_validator",
        "thermo_polynomial_range_advisor",
        "thin_wall_advisor",
        "unit_detector",
        "virtual_interface_detector",
    }
    assert r.advisor_count == 7
    assert r.failed_advisor_count == 0
    # Findings span multiple advisors
    sources = {f.source_advisor for f in r.findings}
    assert len(sources) >= 4
    # V-row union is non-empty
    assert "V79" in r.evidence_refs
    assert "V81" in r.evidence_refs
    assert "V52" in r.evidence_refs
    assert "V41" in r.evidence_refs


def test_advisor_crash_is_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    """If A4 raises, A5 still runs and the stack returns.

    Codex R0 P2 (2026-05-14): the error payload on AdvisorCall.output is
    a JSON-serializable dict, not the raw Exception object — see
    ``test_report_is_json_serializable_on_error_path`` for the round-trip
    regression.
    """
    from ui.backend.services.advisor_stack import face_orientation_advisor as fa_mod

    def boom(_manifest, **_kwargs):  # pragma: no cover - simulated crash
        raise RuntimeError("simulated A4 crash")

    monkeypatch.setattr(fa_mod, "check_face_orientation", boom)

    r = assemble_stack(parts_manifest=_parts_manifest_with_d7_violation())
    # A4 is in calls with status=error; A5 is in calls with status=ok.
    by_name = {c.advisor_name: c for c in r.advisor_calls}
    assert by_name["face_orientation_advisor"].status == "error"
    assert by_name["face_orientation_advisor"].output == {
        "exception_type": "RuntimeError",
        "message": "simulated A4 crash",
    }
    assert by_name["inlet_outlet_validator"].status == "ok"
    assert r.failed_advisor_count == 1
    # A4 contributes no findings; A5 still surfaces its V81 fail.
    assert all(f.source_advisor != "face_orientation_advisor" for f in r.findings)
    assert any(f.source_advisor == "inlet_outlet_validator" for f in r.findings)


def test_report_is_json_serializable_on_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Codex R0 P2 regression: ``json.dumps(asdict(report))`` must succeed
    even when an advisor raised. Prior code stored the raw Exception
    object on AdvisorCall.output, which broke audit-trail persistence on
    exactly the partial-failure path crash isolation is meant to
    preserve."""
    import json
    from dataclasses import asdict

    from ui.backend.services.advisor_stack import face_orientation_advisor as fa_mod

    def boom(_manifest, **_kwargs):  # pragma: no cover - simulated
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(fa_mod, "check_face_orientation", boom)
    r = assemble_stack(parts_manifest=_parts_manifest_with_d7_violation())
    # Round-trip — must not raise:
    payload = json.dumps(asdict(r))
    assert "RuntimeError" in payload
    assert "simulated crash" in payload


def test_critical_count_includes_fail_severity() -> None:
    """Codex R0 P2 regression: A5 ``fail`` findings (V81 protocol
    violations) must count as blocking in stack-level summaries.
    Previously ``critical_count`` only counted ``severity='critical'`` so
    a route gate consuming this helper would silently ignore V81
    blocking findings from A5."""
    r = assemble_stack(
        parts_manifest={
            "parts": [
                # A5 fail: through-flow body missing boundary_emission
                {"name": "supply_inlet", "role": "inlet"},
            ]
        }
    )
    assert r.advisor_count == 2  # A4 + A5
    fail_findings = [f for f in r.findings if f.severity == "fail"]
    assert len(fail_findings) == 1
    assert r.critical_count == 1  # A5's fail counts as blocking
    assert r.warning_count == 0


def test_workbench_env_real_package_exports_preserved(tmp_path: Path) -> None:
    """Codex R2 P1 regression (2026-05-14): in workbench env (trimesh
    installed), importing ``advisor_stack`` first must NOT shadow the
    real ``geometry_ingest`` package. The R2 unconditional placeholder
    broke this — `from ui.backend.services.geometry_ingest import
    IngestReport` would ImportError because the placeholder lacked the
    re-exported names.

    Subprocess is the only honest test of import order — in-process
    pytest already has both packages cached at collection time.
    """
    import subprocess
    import textwrap

    repo_root = Path(__file__).resolve().parents[3]
    script = textwrap.dedent(
        """
        # Workbench env: trimesh IS available. Import advisor_stack FIRST,
        # then verify the real package's re-exports still resolve.
        from ui.backend.services.advisor_stack import assemble_stack
        from ui.backend.services.geometry_ingest import (
            IngestReport,
            canonical_stl_bytes,
        )
        # Smoke: real exports must be callable / class objects, not None.
        assert IngestReport is not None
        assert callable(canonical_stl_bytes)
        # Stack still works alongside.
        r = assemble_stack(parts_manifest={"parts": []})
        assert r.advisor_count == 2  # A4 + A5 dispatched on empty parts list
        print("WORKBENCH_OK")
        """
    ).strip()
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        timeout=30,
    )
    assert result.returncode == 0, (
        "workbench-env import-order regression.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "WORKBENCH_OK" in result.stdout, (
        f"missing success marker.\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_stack_importable_without_trimesh(tmp_path: Path) -> None:
    """Codex R0 P1 + R1 P3 regression: a *cold-start* `import
    advisor_stack` must succeed in base UI environments where the
    ``[workbench]`` extra (and therefore ``trimesh``) is not installed.

    R0 P1 (2026-05-14): the prior ``from ui.backend.services.geometry_ingest
    import ...`` triggered ``geometry_ingest/__init__.py`` and its eager
    ``health_check.py`` → ``import trimesh`` chain.

    R1 P3 (2026-05-14): in-process tracer test could not exercise cold-
    start because ``advisor_stack`` and all 7 leaf advisor modules were
    already cached at the time the test ran. This subprocess-based test
    spawns a fresh Python with ``trimesh`` blocked at the ``sys.meta_path``
    layer *before* any user import, so the cold-start path is actually
    exercised. The subprocess also verifies the parent-package placeholder
    fix (R1 P2): a *second* normal import via the package path must
    resolve to the cached leaf without triggering the real ``__init__.py``.
    """
    import subprocess
    import textwrap

    # Repo root = ui/backend/services/advisor_stack.py → up 4 levels
    repo_root = Path(__file__).resolve().parents[3]
    script = textwrap.dedent(
        """
        import sys

        # Python 3.12+ uses the modern MetaPathFinder.find_spec API; the
        # legacy find_module path is bypassed silently. We implement
        # find_spec to actually intercept trimesh imports.
        class _BlockTrimesh:
            def find_spec(self, name, path=None, target=None):
                if name == "trimesh" or name.startswith("trimesh."):
                    raise ModuleNotFoundError(
                        f"simulated [ui]-only env: no module named {name}"
                    )
                return None

        sys.meta_path.insert(0, _BlockTrimesh())

        # Cold start 1: importing advisor_stack must succeed without trimesh.
        from ui.backend.services.advisor_stack import assemble_stack

        # Cold start 2 (R1 P2 regression): a subsequent *normal* package-
        # path import of an advisor leaf must also work without triggering
        # the real geometry_ingest/__init__.py.
        from ui.backend.services.geometry_ingest import (
            face_orientation_advisor,
        )
        from ui.backend.services.geometry_ingest.shm_dict_validator import (
            validate_shm_dict,
        )

        # Smoke dispatch: emit V81 fail finding without any trimesh involvement.
        r = assemble_stack(
            parts_manifest={
                "parts": [{"name": "supply_inlet", "role": "inlet"}]
            }
        )
        assert r.advisor_count == 2
        assert r.critical_count == 1, "A5 fail should count as blocking"
        # Note: we do NOT assert ``"trimesh" not in sys.modules``. Python's
        # import machinery may insert a ``None`` sentinel as a negative
        # cache when a finder rejects an import, which is not a leak. The
        # behavioral checks above (advisor_count, critical_count) prove
        # the stack functions without trimesh actually loaded.
        cached = sys.modules.get("trimesh")
        assert cached is None or cached.__class__.__name__ == "NoneType", (
            f"trimesh leaked as a real module: {cached!r}"
        )
        print("COLD_START_OK")
        """
    ).strip()
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        timeout=30,
    )
    assert result.returncode == 0, (
        "cold-start subprocess failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "COLD_START_OK" in result.stdout, (
        f"missing success marker.\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_audit_call_fields_populated() -> None:
    r = assemble_stack(shm_dict=_shm_dict_with_typo())
    call = r.advisor_calls[0]
    assert call.advisor_name == "shm_dict_validator"
    assert call.status == "ok"
    assert call.duration_ms >= 0.0
    assert call.version.endswith(".py")
    assert "shm_dict_validator" in call.version
    assert call.input_summary  # non-empty


def test_evidence_refs_only_include_dispatched_advisors() -> None:
    r = assemble_stack(thermo_dict=_thermo_dict_above_canonical_floor())
    # Only A10's V-rows should appear; not e.g. V79 (A4) since A4 didn't run.
    assert "V41" in r.evidence_refs
    assert "V93" in r.evidence_refs
    assert "V79" not in r.evidence_refs
    assert "V52" not in r.evidence_refs


def test_4q_gate_no_llm_imports() -> None:
    """4Q gate (1) — LLM offline OK: stack module imports zero LLM deps."""
    import ui.backend.services.advisor_stack as stack_mod

    src = Path(stack_mod.__file__).read_text()
    forbidden = ("anthropic", "openai", "ai_advisor", "corpus_loader", "llm_provider")
    for token in forbidden:
        assert f"import {token}" not in src
        assert f"from {token}" not in src
        # Also check no submodule import (e.g., `from x.anthropic import ...`)
        assert f".{token}" not in src or token == "openai"  # openai not present
    # Sanity: even when imported, none of the advisor modules pulled an LLM
    # client into sys.modules.
    for mod_name in list(sys.modules):
        assert mod_name not in {"anthropic", "openai"}


def test_4q_gate_no_case_dir_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """4Q gate (4) — AI advisory only: dispatch performs 0 file writes."""
    write_count = {"n": 0}
    real_write_text = Path.write_text
    real_write_bytes = Path.write_bytes

    def counting_write_text(self, *a, **k):  # pragma: no cover - assertion path
        write_count["n"] += 1
        return real_write_text(self, *a, **k)

    def counting_write_bytes(self, *a, **k):  # pragma: no cover
        write_count["n"] += 1
        return real_write_bytes(self, *a, **k)

    monkeypatch.setattr(Path, "write_text", counting_write_text)
    monkeypatch.setattr(Path, "write_bytes", counting_write_bytes)

    bodies, specs = _interface_bodies_with_d1_gap()
    assemble_stack(
        parts_manifest=_parts_manifest_with_d7_violation(),
        shm_dict=_shm_dict_with_typo(),
        thermo_dict=_thermo_dict_above_canonical_floor(),
        thin_wall_inputs=_thin_wall_inputs_with_at_risk_patch(),
        interface_bodies=bodies,
        interface_specs=specs,
    )
    assert write_count["n"] == 0


def test_forward_compat_unknown_kwargs_do_not_raise() -> None:
    r = assemble_stack(
        parts_manifest=_parts_manifest_with_d7_violation(),
        future_artifact_v63="something the next charter adds",
        another_unknown=42,
    )
    # The unknown kwargs are silently ignored; A4 + A5 still ran.
    assert r.advisor_count == 2

"""Tests for the advisory Reynolds-coherence pre-check (DEC-V61-209 follow-up).

P2 W1.0′ (Blueprint v4). The advisory is NON-circular: it compares the case's
ACTUAL nu (constant/transportProperties) against an independently-sourced
canonical Re/length in the manifest. It is ADVISORY-ONLY by construction — the
caller stashes the verdict in gate details and never lets it change a status.
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from cfdtrust.qoi import flow_coherence


# ---------- nu parsing ----------

def test_parse_nu_simple_form():
    text = dedent("""
        transportModel  Newtonian;
        nu              6e-06;
    """)
    assert flow_coherence.parse_nu_from_transport_text(text) == 6e-06


def test_parse_nu_dimensioned_form():
    # OpenFOAM also writes the dimensioned form; nu is the last token before ';'.
    text = "transportModel Newtonian;\nnu  nu [0 2 -1 0 0 0 0] 1.5e-05;\n"
    assert flow_coherence.parse_nu_from_transport_text(text) == 1.5e-05


def test_parse_nu_ignores_numbers_in_comments():
    # Regression: a comment mentioning "U/nu" and other numbers (e.g. "x>=0.2;")
    # must NOT be parsed as nu. This is the exact real-flat-plate structure that
    # an integration check caught (old regex grabbed 0.2 from a comment).
    text = dedent("""
        FoamFile { version 2.0; object transportProperties; }
        transportModel  Newtonian;

        // Kinematic viscosity set so Re/L = U/nu = 30 / 6e-6 = 5e6 (NASA).
        // matches reference within 1.4% across the developed plate (x>=0.2;
        // leading edge excluded). Was 1.5e-5 (Re/L=2e6): gave 15-17% error.
        nu              6e-06;
    """)
    assert flow_coherence.parse_nu_from_transport_text(text) == 6e-06


def test_parse_nu_missing_returns_none():
    assert flow_coherence.parse_nu_from_transport_text("transportModel Newtonian;\n") is None


def test_parse_nu_nonpositive_returns_none():
    # A zero/negative viscosity is not usable — refuse rather than divide later.
    assert flow_coherence.parse_nu_from_transport_text("nu 0;\n") is None
    assert flow_coherence.parse_nu_from_transport_text("nu -1e-5;\n") is None


def test_read_kinematic_viscosity_from_case_dir(tmp_path: Path):
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "transportProperties").write_text(
        "transportModel  Newtonian;\nnu              6e-06;\n", encoding="utf-8"
    )
    assert flow_coherence.read_kinematic_viscosity(tmp_path) == 6e-06


def test_read_kinematic_viscosity_missing_file_returns_none(tmp_path: Path):
    assert flow_coherence.read_kinematic_viscosity(tmp_path) is None


# ---------- coherence verdict ----------

def test_coherent_when_re_matches_canonical():
    # Flat plate: U=30, nu=6e-6 -> Re/L = 5e6 == NASA canonical.
    g = flow_coherence.evaluate_reynolds_coherence(30.0, 6e-06, 5.0e6)
    assert g["status"] == "coherent"
    assert g["re_per_length_computed"] == 5.0e6
    assert abs(g["ratio"] - 1.0) < 1e-9
    assert "message" not in g  # coherent rows carry no advisory message


def test_advisory_on_dec209_drift():
    # The exact DEC-V61-209 cycle-2 failure: nu=1.5e-5 -> Re/L=2e6 vs canonical 5e6.
    g = flow_coherence.evaluate_reynolds_coherence(30.0, 1.5e-05, 5.0e6)
    assert g["status"] == "advisory"
    assert abs(g["ratio"] - 0.4) < 1e-9  # 2e6 / 5e6
    assert "message" in g
    assert "Advisory only" in g["message"]


def test_advisory_band_boundaries():
    # ratio exactly 2.0 (and 0.5) is still "coherent" (inclusive band); beyond -> advisory.
    assert flow_coherence.evaluate_reynolds_coherence(2.0, 1.0, 1.0)["status"] == "coherent"  # ratio 2.0
    assert flow_coherence.evaluate_reynolds_coherence(0.5, 1.0, 1.0)["status"] == "coherent"  # ratio 0.5
    assert flow_coherence.evaluate_reynolds_coherence(2.01, 1.0, 1.0)["status"] == "advisory"
    assert flow_coherence.evaluate_reynolds_coherence(0.49, 1.0, 1.0)["status"] == "advisory"


def test_skip_when_inputs_unavailable():
    # Cannot-compute is a SKIP (not a false flag), for each missing input.
    assert flow_coherence.evaluate_reynolds_coherence(None, 6e-6, 5e6)["status"] == "skip"
    assert flow_coherence.evaluate_reynolds_coherence(30.0, None, 5e6)["status"] == "skip"
    assert flow_coherence.evaluate_reynolds_coherence(30.0, 6e-6, None)["status"] == "skip"
    assert flow_coherence.evaluate_reynolds_coherence(0.0, 6e-6, 5e6)["status"] == "skip"
    assert flow_coherence.evaluate_reynolds_coherence(30.0, 0.0, 5e6)["status"] == "skip"


def test_advisory_only_shape_carries_no_gate_status_key():
    # Guard the advisory-only contract: the verdict dict must NOT carry a
    # top-level gate "PASS"/"FAIL" status that _overall_status could read.
    g = flow_coherence.evaluate_reynolds_coherence(30.0, 1.5e-05, 5.0e6)
    assert g["status"] in {"coherent", "advisory", "skip"}
    assert g["status"] not in {"PASS", "FAIL", "BLOCKED"}

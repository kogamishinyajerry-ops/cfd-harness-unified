"""Spike (2026-05-11) · V-series industrial findings retrieval validation.

Validates that synced V-series + solver_convergence_playbook from
.planning/methodology/ are reachable through the existing N6.1 corpus
loader and surface for an engineer-realistic failure-mode query.

No corpus_loader code change in this spike — relies entirely on the
auto-discovery of docs/openfoam_corpus/*.md and the existing
keyword + section-anchor scoring.

Acceptance: a query phrased like an engineer hitting the kOmegaSST +
zero-IC + wall-function-NaN failure (APU bay V3 / playbook S1) must
return at least one of those two chunks in the top-5 hits.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.ai_advisor import get_default_corpus, reset_default_corpus


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _reset_corpus():
    reset_default_corpus()
    yield
    reset_default_corpus()


def test_v_series_kOmegaSST_zero_ic_query_surfaces_v3_or_s1() -> None:
    corpus = get_default_corpus(REPO_ROOT)
    query = "kOmegaSST zero initial condition wall function NaN omega blowup"
    hits = corpus.find_relevant(query, top_k=5)

    anchors = [h.section_anchor or "" for h in hits]
    paths = [h.path for h in hits]

    v3_or_s1_hit = any(
        ("V3" in a and "kOmegaSST" in a) or ("S1" in a and "kOmegaSST" in a)
        for a in anchors
    )
    assert v3_or_s1_hit, (
        f"Expected V3 or S1 (kOmegaSST + zero IC failure) in top-5 for "
        f"engineer-realistic query. Got anchors: {anchors}\nPaths: {paths}"
    )

    v_series_or_playbook = any(
        "industrial_solver_findings_v_series" in p
        or "solver_convergence_playbook" in p
        for p in paths
    )
    assert v_series_or_playbook, (
        f"V-series or playbook file not in top-5 results. Paths: {paths}"
    )

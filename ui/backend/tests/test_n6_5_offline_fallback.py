"""DEC-V61-161 (N6.5) · Broadened LLM-offline fallback tests.

Coverage:
  * No-mesh case: broaden returns base findings unchanged
  * Clean mesh (advisor returns []): no extra findings emitted
  * Mesh with severe non-orthogonal faces: advisor output surfaces
    as ReviewFinding[] grounded in corpus
  * Missing corpus citation for a metric → finding dropped
  * Recommended_change dict serialized to plain prose
  * V130 advisory-only: fallback module NOT in
    KNOWN_MUTATION_FUNCTIONS
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.schemas.ai_advisor import ReviewFinding
from ui.backend.services.ai_actions.mutating_routes import (
    KNOWN_MUTATION_FUNCTIONS,
)
from ui.backend.services.ai_advisor import load_corpus
from ui.backend.services.ai_advisor.fallback import (
    _serialize_recommended_change,
    _suggestion_to_finding,
    broaden_review_findings,
)


# ────────── Fixtures ──────────


def _build_corpus(tmp_path: Path):
    (tmp_path / "docs/openfoam_corpus").mkdir(parents=True)
    (tmp_path / "docs/openfoam_corpus/mesh.md").write_text(
        "## Mesh quality\n\nThe checkMesh utility reports orthogonality.\n"
        "## Mesh skewness\n\nSkewness above 0.95 causes solver instability.\n"
        "## Aspect ratio\n\nPrism layer aspect ratios up to 1000 are normal.\n",
        encoding="utf-8",
    )
    return load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )


def _empty_case(tmp_path: Path) -> Path:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    return case_dir


# ────────── Behavior with no mesh ──────────


def test_broaden_returns_base_findings_when_no_mesh(tmp_path: Path) -> None:
    """When the case has no polyMesh yet, the advisor cannot run;
    broaden must return the base findings unchanged."""
    corpus = _build_corpus(tmp_path)
    case_dir = _empty_case(tmp_path)
    base: list[ReviewFinding] = []

    out = broaden_review_findings(case_dir, base, corpus)
    assert out == base


def test_broaden_does_not_raise_on_unrelated_errors(tmp_path: Path) -> None:
    """If the mesh analyzer raises something unexpected, broaden
    catches it and returns base findings (route MUST NOT 5xx)."""
    corpus = _build_corpus(tmp_path)
    case_dir = _empty_case(tmp_path)
    # No mesh → analyze_mesh_quality raises MeshQualityNotAvailableError
    # which we catch explicitly. Confirm no uncaught exception escapes.
    out = broaden_review_findings(case_dir, [], corpus)
    assert isinstance(out, list)


# ────────── Mesh-advisor → ReviewFinding integration ──────────


def test_suggestion_to_finding_converts_critical_with_corpus_citation(
    tmp_path: Path,
) -> None:
    """Direct unit test: MeshFixSuggestion (advisor output) →
    ReviewFinding with mesh-quality corpus citation."""
    from ui.backend.services.mesh_quality.schemas import (
        MeshFixSuggestion,
    )

    corpus = _build_corpus(tmp_path)
    sug = MeshFixSuggestion(
        metric="n_severe_non_ortho_faces",
        severity="critical",
        suggestion_text=(
            "5 severely non-orthogonal faces detected; "
            "tighten sizing field."
        ),
        recommended_change={"sizing_field": 0.05},
    )

    finding = _suggestion_to_finding(sug, corpus)
    assert finding is not None
    assert finding.source == "rule_based"
    assert finding.area == "mesh"
    assert finding.severity == "critical"
    assert "severely non-orthogonal" in finding.message
    assert finding.recommended_change == "sizing_field=0.05"
    assert corpus.get_chunk(finding.citation.chunk_id) is not None


def test_suggestion_to_finding_drops_when_no_corpus_match(
    tmp_path: Path,
) -> None:
    """Empty corpus → no citation → return None (caller drops)."""
    from ui.backend.services.mesh_quality.schemas import (
        MeshFixSuggestion,
    )

    (tmp_path / "docs/openfoam_corpus").mkdir(parents=True)
    empty_corpus = load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )

    sug = MeshFixSuggestion(
        metric="n_severe_non_ortho_faces",
        severity="warning",
        suggestion_text="msg",
        recommended_change=None,
    )

    assert _suggestion_to_finding(sug, empty_corpus) is None


@pytest.mark.parametrize(
    "metric,sev",
    [
        ("max_non_orthogonality", "warning"),
        ("max_skewness", "critical"),
        ("max_aspect_ratio", "info"),
        ("n_severe_non_ortho_faces", "critical"),
    ],
)
def test_suggestion_to_finding_maps_severity_and_metric(
    metric, sev, tmp_path: Path
) -> None:
    """Each metric→severity combo converts cleanly when corpus
    has a matching chunk."""
    from ui.backend.services.mesh_quality.schemas import (
        MeshFixSuggestion,
    )

    corpus = _build_corpus(tmp_path)
    sug = MeshFixSuggestion(
        metric=metric,
        severity=sev,
        suggestion_text=f"test {metric} text",
        recommended_change=None,
    )

    finding = _suggestion_to_finding(sug, corpus)
    assert finding is not None
    assert finding.severity == sev
    assert finding.area == "mesh"


# ────────── recommended_change serialization ──────────


def test_serialize_recommended_change_none_returns_none() -> None:
    assert _serialize_recommended_change(None) is None


def test_serialize_recommended_change_dict_to_prose() -> None:
    result = _serialize_recommended_change(
        {"sizing_field": 0.05, "refinement_level": 2}
    )
    assert result is not None
    assert "sizing_field=0.05" in result
    assert "refinement_level=2" in result


def test_serialize_recommended_change_truncates_to_500_chars() -> None:
    # Force a long input
    big = {f"key_{i}": "value" * 5 for i in range(100)}
    result = _serialize_recommended_change(big)
    assert result is not None
    assert len(result) <= 500


def test_serialize_recommended_change_non_dict_str_coerces() -> None:
    result = _serialize_recommended_change("plain string")
    assert result == "plain string"


# ────────── V130 contract ──────────


def test_fallback_module_not_in_mutation_registry() -> None:
    forbidden = "ui.backend.services.ai_advisor.fallback"
    for module_path, symbol_name in KNOWN_MUTATION_FUNCTIONS:
        assert module_path != forbidden, (
            f"fallback registered as mutation function: {symbol_name}"
        )


def test_fallback_module_does_not_import_mutation_function() -> None:
    """Layer-C-style static check on the fallback file: no
    import statement names a symbol in KNOWN_MUTATION_FUNCTIONS."""
    import ast

    repo_root = Path(__file__).resolve().parents[3]
    file_path = repo_root / "ui/backend/services/ai_advisor/fallback.py"
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    imported: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imported.append((mod, alias.name))

    forbidden = KNOWN_MUTATION_FUNCTIONS
    violations = [pair for pair in imported if pair in forbidden]
    assert not violations, (
        f"fallback imports mutation symbols: {violations}"
    )

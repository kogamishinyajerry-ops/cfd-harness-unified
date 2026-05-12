"""DEC-V61-157 (N6.1) · RAG corpus loader tests.

Coverage:
  * Schema validators (CitedChunk / CorpusStats extra=forbid + bounds)
  * Loader walks markdown sections; correct chunk_id + sha
  * Loader honors allowlist (case directories under workspace/projects/
    are NOT ingested)
  * Lookup keyword matching + section-anchor 2x weight
  * Lookup top_k cap, empty query, no-match query
  * Singleton lazy load + reset
  * V130 advisory-only: corpus_loader NOT in KNOWN_MUTATION_FUNCTIONS
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from ui.backend.schemas.ai_advisor import CitedChunk, CorpusStats
from ui.backend.services.ai_advisor import (
    Corpus,
    LoadedChunk,
    get_default_corpus,
    load_corpus,
    reset_default_corpus,
)
from ui.backend.services.ai_actions.mutating_routes import (
    KNOWN_MUTATION_FUNCTIONS,
)


# ────────── Schema validators ──────────


def test_cited_chunk_extra_forbidden() -> None:
    valid_kwargs = dict(
        chunk_id="x",
        source="openfoam_corpus",
        path="docs/x.md",
        sha="0" * 64,
        section_anchor=None,
        byte_offset=0,
        text="hello",
    )
    CitedChunk(**valid_kwargs)
    with pytest.raises(ValidationError):
        CitedChunk(**valid_kwargs, extra_field="oops")


def test_cited_chunk_sha_must_be_64_hex() -> None:
    with pytest.raises(ValidationError):
        CitedChunk(
            chunk_id="x",
            source="openfoam_corpus",
            path="docs/x.md",
            sha="too-short",
            byte_offset=0,
            text="hello",
        )


def test_corpus_stats_corpus_sha_required() -> None:
    with pytest.raises(ValidationError):
        CorpusStats(total_chunks=0, total_files=0, sources={})


# ────────── Loader behavior ──────────


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_corpus_picks_up_markdown_sections(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs/openfoam_corpus/foo.md",
        "## Mesh quality\n\nFirst section body.\n\n"
        "## Solver selection\n\nSecond section body.\n",
    )

    corpus = load_corpus(
        tmp_path,
        roots=[("docs/openfoam_corpus", "openfoam_corpus")],
    )

    assert corpus.stats.total_files == 1
    assert corpus.stats.total_chunks == 2
    anchors = {c.section_anchor for c in corpus.chunks}
    assert anchors == {"Mesh quality", "Solver selection"}
    for chunk in corpus.chunks:
        assert chunk.source == "openfoam_corpus"
        assert chunk.path == "docs/openfoam_corpus/foo.md"
        assert len(chunk.sha) == 64
        assert hashlib.sha256(chunk.text.encode("utf-8")).hexdigest() == chunk.sha


def test_load_corpus_handles_preamble_before_first_section(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs/openfoam_corpus/preface.md",
        "Preamble line one.\n\n"
        "Preamble line two.\n\n"
        "## Section A\n\nBody A.\n",
    )
    corpus = load_corpus(
        tmp_path,
        roots=[("docs/openfoam_corpus", "openfoam_corpus")],
    )
    anchors = sorted(
        (c.section_anchor or "<preamble>") for c in corpus.chunks
    )
    assert anchors == ["<preamble>", "Section A"]


def test_load_corpus_skips_empty_sections(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs/openfoam_corpus/empty.md",
        "## Empty header (no body)\n\n## Real header\n\nBody.\n",
    )
    corpus = load_corpus(
        tmp_path,
        roots=[("docs/openfoam_corpus", "openfoam_corpus")],
    )
    anchors = {c.section_anchor for c in corpus.chunks}
    assert anchors == {"Real header"}


def test_load_corpus_chunk_id_stable_across_runs(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs/openfoam_corpus/stable.md",
        "## A\n\nbody one\n\n## B\n\nbody two\n",
    )
    c1 = load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )
    c2 = load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )
    assert c1.stats.corpus_sha == c2.stats.corpus_sha
    ids1 = sorted(c.chunk_id for c in c1.chunks)
    ids2 = sorted(c.chunk_id for c in c2.chunks)
    assert ids1 == ids2


def test_load_corpus_does_not_ingest_workspace_projects(tmp_path: Path) -> None:
    """Charter §threat model row 5: case directories MUST NOT reach
    the loader. The default allowlist excludes workspace/projects/;
    we verify a leaked file there is not picked up."""
    _write(
        tmp_path / "workspace/projects/case_x/0/U",
        "type fixedValue;\nvalue uniform (0 0 0);\n",
    )
    _write(
        tmp_path / "docs/openfoam_corpus/legit.md",
        "## Topic\n\nlegit content\n",
    )
    corpus = load_corpus(tmp_path)
    paths = {c.path for c in corpus.chunks}
    for p in paths:
        assert "workspace/projects" not in p, (
            f"Leaked case path into corpus: {p}"
        )
    assert "docs/openfoam_corpus/legit.md" in paths


def test_load_corpus_only_md_files(tmp_path: Path) -> None:
    _write(tmp_path / "docs/openfoam_corpus/keep.md", "## A\n\nbody\n")
    _write(
        tmp_path / "docs/openfoam_corpus/skip.txt",
        "Should not be ingested.",
    )
    _write(
        tmp_path / "docs/openfoam_corpus/skip.yaml",
        "key: value\n",
    )
    corpus = load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )
    paths = {c.path for c in corpus.chunks}
    assert paths == {"docs/openfoam_corpus/keep.md"}


def test_load_corpus_missing_root_yields_empty(tmp_path: Path) -> None:
    corpus = load_corpus(
        tmp_path,
        roots=[("docs/nonexistent", "openfoam_corpus")],
    )
    assert corpus.stats.total_chunks == 0
    assert corpus.stats.total_files == 0
    # Empty corpus still has a stable sha (sha256 of empty input)
    assert (
        corpus.stats.corpus_sha
        == hashlib.sha256(b"").hexdigest()
    )


def test_load_corpus_two_sources_counted_separately(tmp_path: Path) -> None:
    _write(tmp_path / "docs/openfoam_corpus/a.md", "## X\n\nbody x\n")
    _write(
        tmp_path / ".planning/decisions/y.md",
        "## Decision\n\nrationale\n",
    )
    corpus = load_corpus(tmp_path)
    assert corpus.stats.sources["openfoam_corpus"] == 1
    assert corpus.stats.sources["project_decisions"] == 1


# ────────── Lookup behavior ──────────


def _build_two_section_corpus(tmp_path: Path) -> Corpus:
    _write(
        tmp_path / "docs/openfoam_corpus/topic.md",
        "## Mesh quality\n\nThe checkMesh utility reports orthogonality.\n\n"
        "## Solver selection\n\nPick simpleFoam for steady RANS.\n",
    )
    return load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )


def test_find_relevant_keyword_match(tmp_path: Path) -> None:
    corpus = _build_two_section_corpus(tmp_path)
    hits = corpus.find_relevant("simpleFoam steady", top_k=5)
    assert len(hits) == 1
    assert hits[0].section_anchor == "Solver selection"


def test_find_relevant_anchor_weighted_higher(tmp_path: Path) -> None:
    """Anchor matches outweigh body matches: a query of
    "Mesh quality" must surface the Mesh-quality section first even
    if the other section also contains the word "quality" in body."""
    _write(
        tmp_path / "docs/openfoam_corpus/anchor_test.md",
        "## Mesh quality\n\nbody about orthogonality\n\n"
        "## Other\n\nThe word quality appears here too in body text.\n",
    )
    corpus = load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )
    hits = corpus.find_relevant("mesh quality", top_k=5)
    assert hits[0].section_anchor == "Mesh quality"


def test_find_relevant_top_k_cap(tmp_path: Path) -> None:
    parts = []
    for i in range(10):
        parts.append(f"## Section {i}\n\nfoobar token at section {i}\n")
    _write(tmp_path / "docs/openfoam_corpus/many.md", "\n".join(parts))
    corpus = load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )
    hits = corpus.find_relevant("foobar", top_k=3)
    assert len(hits) == 3


def test_find_relevant_empty_query_returns_empty(tmp_path: Path) -> None:
    corpus = _build_two_section_corpus(tmp_path)
    assert corpus.find_relevant("", top_k=5) == []
    assert corpus.find_relevant("   ", top_k=5) == []


def test_find_relevant_no_match_returns_empty(tmp_path: Path) -> None:
    corpus = _build_two_section_corpus(tmp_path)
    assert corpus.find_relevant("zzz_no_token_matches_xyzzy", top_k=5) == []


def test_find_relevant_source_filter(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs/openfoam_corpus/of.md",
        "## Mesh quality\n\northogonality body\n",
    )
    _write(
        tmp_path / ".planning/decisions/dec.md",
        "## Mesh quality\n\nproject-internal mesh quality decision\n",
    )
    corpus = load_corpus(tmp_path)
    hits = corpus.find_relevant(
        "mesh quality", top_k=5, sources=["openfoam_corpus"]
    )
    assert len(hits) == 1
    assert hits[0].path == "docs/openfoam_corpus/of.md"


def test_find_relevant_top_k_zero_or_negative_returns_empty(
    tmp_path: Path,
) -> None:
    corpus = _build_two_section_corpus(tmp_path)
    assert corpus.find_relevant("anything", top_k=0) == []
    assert corpus.find_relevant("anything", top_k=-1) == []


# ────────── get_chunk by id ──────────


def test_get_chunk_resolves_known_id(tmp_path: Path) -> None:
    corpus = _build_two_section_corpus(tmp_path)
    sample = corpus.chunks[0]
    resolved = corpus.get_chunk(sample.chunk_id)
    assert resolved is not None
    assert resolved.chunk_id == sample.chunk_id


def test_get_chunk_unknown_id_returns_none(tmp_path: Path) -> None:
    corpus = _build_two_section_corpus(tmp_path)
    assert corpus.get_chunk("does-not-exist:0:0000000000000000") is None


# ────────── Singleton ──────────


def test_get_default_corpus_caches(tmp_path: Path) -> None:
    _write(tmp_path / "docs/openfoam_corpus/x.md", "## A\n\nbody\n")
    reset_default_corpus()
    c1 = get_default_corpus(tmp_path)
    c2 = get_default_corpus(tmp_path)
    assert c1 is c2
    reset_default_corpus()


def test_reset_default_corpus_forces_reload(tmp_path: Path) -> None:
    _write(tmp_path / "docs/openfoam_corpus/x.md", "## A\n\nbody\n")
    reset_default_corpus()
    c1 = get_default_corpus(tmp_path)
    reset_default_corpus()
    c2 = get_default_corpus(tmp_path)
    assert c1 is not c2
    reset_default_corpus()


# ────────── Wire schema round-trip ──────────


def test_loaded_chunk_to_cited_round_trip(tmp_path: Path) -> None:
    corpus = _build_two_section_corpus(tmp_path)
    for chunk in corpus.chunks:
        cited = chunk.to_cited()
        assert isinstance(cited, CitedChunk)
        assert cited.chunk_id == chunk.chunk_id
        assert cited.sha == chunk.sha
        assert cited.path == chunk.path


# ────────── V130 advisory-only contract ──────────


def test_corpus_loader_module_not_in_mutation_registry() -> None:
    """The corpus loader module + its symbols MUST NOT appear in
    KNOWN_MUTATION_FUNCTIONS. The module is read-only by construction;
    this guards against regression where a future commit adds a
    case-state writer to ai_advisor and forgets to register it."""
    forbidden_module = "ui.backend.services.ai_advisor.corpus_loader"
    forbidden_package = "ui.backend.services.ai_advisor"
    for module_path, _symbol in KNOWN_MUTATION_FUNCTIONS:
        assert module_path != forbidden_module, (
            f"corpus_loader registered as mutation function: {_symbol}"
        )
        assert module_path != forbidden_package, (
            f"ai_advisor package registered as mutation function: {_symbol}"
        )


def test_corpus_loader_does_not_import_mutation_function() -> None:
    """Layer-C-style static check on the corpus_loader file: no
    import statement names a symbol in KNOWN_MUTATION_FUNCTIONS."""
    import ast

    repo_root = Path(__file__).resolve().parents[3]
    loader_file = (
        repo_root
        / "ui/backend/services/ai_advisor/corpus_loader.py"
    )
    tree = ast.parse(loader_file.read_text(encoding="utf-8"))
    imported: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imported.append((mod, alias.name))

    forbidden = KNOWN_MUTATION_FUNCTIONS
    violations = [pair for pair in imported if pair in forbidden]
    assert not violations, (
        f"corpus_loader imports mutation symbols: {violations}"
    )

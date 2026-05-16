"""DEC-V61-157 (N6.1) · RAG corpus loader.

V1 design (per charter §"Why local in-memory corpus"):
  * Local on-disk only — no service dependency, no embedding model,
    no network. Q1 (LLM-offline reachability) requires it.
  * Two allowlisted roots: ``docs/openfoam_corpus/`` (curated
    OpenFOAM topics) + ``.planning/decisions/`` (project DEC trail).
  * Chunk strategy: split markdown by ``##``-or-deeper headers; one
    chunk per section, truncated at 4096 chars (wire-cap from schema).
    Plain-text/yaml files are chunked at 4096-char paragraph
    boundaries.
  * Each chunk records ``chunk_id``, ``path``, ``sha``,
    ``section_anchor``, ``byte_offset``, ``text``.
  * Lookup: keyword token-overlap scoring; section anchors weighted
    higher than body text. Returns top-k ``CitedChunk`` for
    server-side citation grounding.

Out of scope (deferred to N6-extend if recall regresses):
  * Embedding-based retrieval
  * Cross-language retrieval
  * Auto-reindex on file change
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from ui.backend.schemas.ai_advisor import CitedChunk, CorpusSource, CorpusStats

logger = logging.getLogger(__name__)


_CHUNK_TEXT_CAP = 4096
_DEFAULT_CORPUS_ROOTS: tuple[tuple[str, CorpusSource], ...] = (
    ("docs/openfoam_corpus", "openfoam_corpus"),
    (".planning/decisions", "project_decisions"),
)


# ────────── Internal data structures ──────────


@dataclass(frozen=True)
class LoadedChunk:
    """In-memory representation of one corpus chunk.

    Distinct from :class:`CitedChunk` (wire schema) only in that it
    carries the full text without truncation enforcement at type level
    — the loader enforces the 4096-char cap at chunk creation.
    """

    chunk_id: str
    source: CorpusSource
    path: str
    sha: str
    section_anchor: Optional[str]
    byte_offset: int
    text: str
    # Cached lowercase tokens for keyword scoring; computed once at
    # load time so query-time lookup is O(corpus * |query_tokens|).
    _tokens: frozenset[str] = field(default_factory=frozenset)

    def to_cited(self) -> CitedChunk:
        # V69.3 (2026-05-16): some long-form V-row corpus anchors exceed
        # the CitedChunk.section_anchor 256-char Pydantic constraint
        # (e.g. V94 "STL files emitted..." carrying full body description).
        # Truncate to 253 + "..." so the wire contract stays honest about
        # truncation while keeping construction safe under Pydantic.
        anchor = self.section_anchor
        if anchor is not None and len(anchor) > 256:
            anchor = anchor[:253] + "..."
        return CitedChunk(
            chunk_id=self.chunk_id,
            source=self.source,
            path=self.path,
            sha=self.sha,
            section_anchor=anchor,
            byte_offset=self.byte_offset,
            text=self.text,
        )


@dataclass
class Corpus:
    """Loaded in-memory corpus + lookup primitives.

    Immutable after construction. Lookup is read-only and thread-safe.
    """

    chunks: tuple[LoadedChunk, ...]
    _by_id: dict[str, LoadedChunk]
    stats: CorpusStats

    def get_chunk(self, chunk_id: str) -> Optional[LoadedChunk]:
        """Resolve ``chunk_id`` to a loaded chunk, or None.

        Used by N6.2 / N6.3 server-side citation grounding: when the
        advisor returns a finding, the route handler calls this to
        verify the chunk_id resolves; missing chunk → finding is
        dropped before returning to the engineer.
        """
        return self._by_id.get(chunk_id)

    def find_relevant(
        self,
        query: str,
        *,
        top_k: int = 5,
        sources: Optional[Iterable[CorpusSource]] = None,
    ) -> list[LoadedChunk]:
        """Keyword-overlap lookup. Returns up to ``top_k`` chunks
        ranked by score; section-anchor matches are weighted 2x body
        matches.

        ``sources`` filter is honored if provided; missing → all
        sources searched. Empty query returns []. Ties broken by
        ``chunk_id`` for determinism.
        """
        if not query.strip():
            return []
        if top_k <= 0:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        allowed: Optional[frozenset[CorpusSource]] = (
            frozenset(sources) if sources is not None else None
        )

        scored: list[tuple[float, str, LoadedChunk]] = []
        for chunk in self.chunks:
            if allowed is not None and chunk.source not in allowed:
                continue
            body_overlap = len(query_tokens & chunk._tokens)
            if body_overlap == 0 and chunk.section_anchor is None:
                continue
            score = float(body_overlap)
            if chunk.section_anchor:
                anchor_tokens = _tokenize(chunk.section_anchor)
                anchor_overlap = len(query_tokens & anchor_tokens)
                # Anchor matches weighted 2x — section-targeted hits
                # are higher-precision than body-substring hits.
                score += 2.0 * float(anchor_overlap)
            if score > 0:
                # Tuple ordering: higher score first; tiebreak by
                # chunk_id ascending for determinism.
                scored.append((score, chunk.chunk_id, chunk))

        scored.sort(key=lambda t: (-t[0], t[1]))
        return [c for _, _, c in scored[:top_k]]


# ────────── Tokenization ──────────


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{1,}")


def _tokenize(text: str) -> frozenset[str]:
    """Split ``text`` into lowercase alphanumeric tokens (length ≥ 2).

    Tokens shorter than 2 chars are dropped because single letters
    overlap noisily with every chunk. Underscores are kept as part
    of identifiers (e.g. ``snappyHexMesh`` → ``snappyhexmesh``;
    ``check_mesh`` → ``check_mesh``).
    """
    return frozenset(m.group(0).lower() for m in _TOKEN_RE.finditer(text))


# ────────── Loader ──────────


_HEADER_RE = re.compile(r"^(#{2,})\s+(.+?)\s*$", re.MULTILINE)


def _split_markdown_sections(
    text: str,
) -> list[tuple[Optional[str], int, str]]:
    """Split markdown ``text`` into ``(anchor, byte_offset, body)``
    sections. Anchor is the header text (e.g. "Mesh quality"); None
    for the pre-first-header preamble. ``byte_offset`` is the start
    offset in the original text bytes.

    A "section" is the body from one ``##``-or-deeper header up to
    (but not including) the next ``##``-or-deeper header.
    """
    matches = list(_HEADER_RE.finditer(text))
    sections: list[tuple[Optional[str], int, str]] = []

    # Preamble (text before first ##-header) — only emit if non-empty
    # after stripping.
    if not matches:
        preamble = text.strip()
        if preamble:
            sections.append((None, 0, preamble))
        return sections

    first_start = matches[0].start()
    if first_start > 0:
        preamble = text[:first_start].strip()
        if preamble:
            sections.append((None, 0, preamble))

    for i, m in enumerate(matches):
        anchor = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        # Skip empty sections (header with no content)
        if not body:
            continue
        sections.append((anchor, m.start(), body))

    return sections


def _split_plain_paragraphs(text: str) -> list[tuple[Optional[str], int, str]]:
    """Plain-text fallback: split on blank lines, cap at chunk size.

    Returns ``(None, byte_offset, paragraph)`` tuples — no anchor for
    plain-text sources.
    """
    sections: list[tuple[Optional[str], int, str]] = []
    offset = 0
    for paragraph in re.split(r"\n\s*\n", text):
        stripped = paragraph.strip()
        if stripped:
            byte_off = text.find(paragraph, offset)
            if byte_off < 0:
                byte_off = offset
            sections.append((None, byte_off, stripped))
        offset += len(paragraph) + 2  # +2 for the split separator
    return sections


def _make_chunk(
    *,
    source: CorpusSource,
    relative_path: str,
    section_anchor: Optional[str],
    byte_offset: int,
    text: str,
) -> LoadedChunk:
    """Build a :class:`LoadedChunk` with truncated text + computed
    SHA + chunk_id. SHA is computed over the truncated text so the
    response SHA matches what the engineer sees on the wire."""
    truncated = text[:_CHUNK_TEXT_CAP]
    sha = hashlib.sha256(truncated.encode("utf-8")).hexdigest()
    chunk_id = f"{relative_path}:{byte_offset}:{sha[:16]}"
    return LoadedChunk(
        chunk_id=chunk_id,
        source=source,
        path=relative_path,
        sha=sha,
        section_anchor=section_anchor,
        byte_offset=byte_offset,
        text=truncated,
        _tokens=_tokenize(truncated),
    )


def _iter_corpus_files(root: Path) -> Iterable[Path]:
    """Yield candidate text files under ``root``. Currently:
    ``.md`` (markdown) only. Other extensions are skipped silently.

    The allowlist keeps the corpus surface narrow — engineers
    extending the corpus for V1 must use markdown.
    """
    if not root.exists() or not root.is_dir():
        return ()
    return sorted(
        p
        for p in root.rglob("*.md")
        if p.is_file() and not p.name.startswith(".")
    )


def load_corpus(
    repo_root: Path,
    *,
    roots: Optional[Iterable[tuple[str, CorpusSource]]] = None,
) -> Corpus:
    """Walk allowlisted roots under ``repo_root`` and build an
    in-memory :class:`Corpus`.

    Default roots (from charter):
        * ``docs/openfoam_corpus/`` → ``openfoam_corpus``
        * ``.planning/decisions/`` → ``project_decisions``

    Files outside the allowlisted roots are NEVER ingested. Notably:
    case directories under ``workspace/projects/`` are not in the
    allowlist (charter §threat model row 5).

    Parameters
    ----------
    repo_root
        Repo root directory; allowlisted roots are resolved relative
        to it.
    roots
        Optional override of the allowlist (used by tests for
        deterministic small fixtures). Production callers should
        omit this and use the defaults.
    """
    effective_roots = tuple(roots) if roots is not None else _DEFAULT_CORPUS_ROOTS

    chunks: list[LoadedChunk] = []
    file_count = 0
    source_counts: dict[CorpusSource, int] = {}

    for relative_root, source in effective_roots:
        root_path = (repo_root / relative_root).resolve()
        # Defense-in-depth: ensure the resolved path is still under
        # repo_root (prevents symlink escapes).
        try:
            root_path.relative_to(repo_root.resolve())
        except ValueError:
            logger.warning(
                "Corpus root %r resolved outside repo_root; skipping.",
                relative_root,
            )
            continue

        for file_path in _iter_corpus_files(root_path):
            try:
                rel_path = file_path.relative_to(repo_root.resolve()).as_posix()
            except ValueError:
                logger.warning(
                    "Corpus file %s not under repo_root; skipping.", file_path
                )
                continue

            try:
                text = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("Skipping %s: %s", rel_path, exc)
                continue

            sections = _split_markdown_sections(text)
            if not sections:
                sections = _split_plain_paragraphs(text)

            file_added = False
            for anchor, byte_offset, body in sections:
                chunk = _make_chunk(
                    source=source,
                    relative_path=rel_path,
                    section_anchor=anchor,
                    byte_offset=byte_offset,
                    text=body,
                )
                chunks.append(chunk)
                file_added = True
                source_counts[source] = source_counts.get(source, 0) + 1

            if file_added:
                file_count += 1

    by_id: dict[str, LoadedChunk] = {}
    for chunk in chunks:
        # Collisions are vanishingly unlikely (path + offset + sha16)
        # but if one occurs, the second is dropped — first wins, log.
        if chunk.chunk_id in by_id:
            logger.warning(
                "Duplicate chunk_id %s; dropping second occurrence.",
                chunk.chunk_id,
            )
            continue
        by_id[chunk.chunk_id] = chunk

    # Stable corpus fingerprint: sorted chunk_id||sha digest.
    fingerprint_input = "\n".join(
        f"{c.chunk_id}:{c.sha}" for c in sorted(by_id.values(), key=lambda c: c.chunk_id)
    ).encode("utf-8")
    corpus_sha = hashlib.sha256(fingerprint_input).hexdigest()

    stats = CorpusStats(
        total_chunks=len(by_id),
        total_files=file_count,
        sources=source_counts,
        corpus_sha=corpus_sha,
    )

    return Corpus(
        chunks=tuple(by_id.values()),
        _by_id=by_id,
        stats=stats,
    )


# ────────── Process-level singleton ──────────


_lock = threading.Lock()
_cached_corpus: Optional[Corpus] = None
_cached_repo_root: Optional[Path] = None


def get_default_corpus(repo_root: Optional[Path] = None) -> Corpus:
    """Return the process-singleton corpus. Lazy on first call.

    ``repo_root`` is required on the first call; subsequent calls
    ignore it (cached). Tests that flip the corpus must call
    :func:`reset_default_corpus` first.
    """
    global _cached_corpus, _cached_repo_root

    with _lock:
        if _cached_corpus is not None:
            return _cached_corpus
        if repo_root is None:
            # Fallback: derive repo root from this file's location.
            # ui/backend/services/ai_advisor/corpus_loader.py → repo
            # root is parents[4].
            repo_root = Path(__file__).resolve().parents[4]
        _cached_corpus = load_corpus(repo_root)
        _cached_repo_root = repo_root
        logger.info(
            "Loaded AI advisor corpus: %d chunks across %d files (sha=%s).",
            _cached_corpus.stats.total_chunks,
            _cached_corpus.stats.total_files,
            _cached_corpus.stats.corpus_sha[:12],
        )
        return _cached_corpus


def reset_default_corpus() -> None:
    """Clear the singleton cache. Used by tests + (rare) corpus
    refresh after curated edits during development."""
    global _cached_corpus, _cached_repo_root
    with _lock:
        _cached_corpus = None
        _cached_repo_root = None

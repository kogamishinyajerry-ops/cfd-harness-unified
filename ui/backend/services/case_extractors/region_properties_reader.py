"""region_properties_reader · case_dir → RegionPropertiesSnapshot | None (v0.1).

Per DEC-V61-217 W3.0. Reads ``<case_dir>/constant/regionProperties`` and
returns a frozen dataclass carrying the ``fluid`` and ``solid`` region name
lists declared in the CHT multi-region ``regions`` entry.

Extracted shape::

    RegionPropertiesSnapshot(
        fluid_regions: tuple[str, ...] | None,   # None iff group key absent
        solid_regions: tuple[str, ...] | None,   # None iff group key absent
    )

Each field is **independently optional** per DEC-V61-213's
key-presence-vs-payload-completeness rule:

  - Group key **absent**     → field = ``None``         (missing-key leg)
  - Group key **present but sub-list empty** → field = ``()``  (empty tuple)
  - Group key **present**    → field = populated ``tuple[str, ...]``

This means ``Snapshot(None, None)`` (both groups declared absent in the source
``regions ()`` entry) is a valid non-None snapshot — the file was readable
and the outer ``regions`` key was present; it simply declared neither a
``fluid`` nor a ``solid`` group. ``extract()`` returning ``None`` signals
"cannot construct any snapshot at all" (file missing, unreadable, or no
parseable ``regions`` entry).

## Scope-locked NON-features (extractor returns ``None`` rather than guess)

  - ``#include`` directives: a ``regionProperties`` that pulls the region
    list from an included file is not followed; returns ``None``.
  - Macro substitution (``$regionList``): a ``$``-led token is out of the
    bare-word grammar, so the name-list refuses (``None``) rather than
    capturing the macro literal as a region name. No real case in
    ``.planning/case_profiles/`` uses this pattern today (verified
    2026-05-30).
  - **String-literal-unaware comment stripping** (mirrors
    ``solver_block_extractor`` finding #6): ``//`` and ``/* */`` inside
    quoted string values would be stripped. Safe for v0.1's purely-word-
    token region names (no quoted-string values).
  - **Group detection is top-level-anchored** (red-team 2026-05-30 P1 fix):
    a ``fluid``/``solid`` token nested inside another group's name-list does
    NOT false-match. Such a nested shape makes the enclosing name-list
    out-of-grammar, so the parser REFUSES the whole snapshot (``None``)
    instead of fabricating a region list. The earlier global-regex scan
    (which could conjure ``solid_regions=('metal',)`` from a fluid region
    name written ``solid(metal)``, or read ``fluid_regions=('deep',)`` out
    of a ``fluid (deep)`` nested inside the ``solid`` group) is gone.
  - **Names must be bare OpenFOAM ``word`` tokens** (letter/underscore
    start). An out-of-grammar token — digit-led (``123air``), punctuation,
    or a nested ``( ... )`` inside a name-list — triggers honest refusal
    (``None``), never a silent truncation (``123air`` → ``air``) or a
    silent flatten of nested content. v0.1 parses exactly one level of
    ``(groupWord (name ...))`` pairs; deeper nesting refuses.
  - Region group keys other than ``fluid`` and ``solid`` (e.g. ``porous``)
    are parsed but ignored — they appear on neither field. Only the two CHT
    groups W3.0's consumers need are surfaced.
  - Duplicate-group refusal: two ``fluid (...)`` groups inside the same
    ``regions`` block → snapshot ``None`` (DEC-V61-213 honest-refusal
    discipline; see ``_extract_group_pairs``).

## Architectural placement

Mirrors DEC-V61-211 ``solver_block_extractor`` exactly: stdlib-only
(``pathlib`` + ``re`` + ``dataclasses``), pure function, read-only (one
``Path.read_text``), no route, no mutation, no import from
``geometry_ingest`` (would pull ``trimesh`` transitively via
``__init__.py → health_check``).

``RegionPropertiesSnapshot`` is a NEW dataclass — no upstream equivalent
exists today, so no mirror-parity canary is needed (would be added when a
future advisor consumes region lists directly, mirroring DEC-V61-211 R0 P1
pattern). Drift risk: NONE today.

## Why line-anchored regex + paired-paren scan (not a generic OF-dict parser)

A general OpenFOAM-dict parser is multi-hour, edge-case-heavy infrastructure
(regex keys, includes, macros, embedded code). The ``regions`` entry in
``regionProperties`` has a well-defined two-level ``( (key (names...)) ... )``
structure that does not appear elsewhere in the file (after stripping the
FoamFile header via comment-stripping). A line-anchored token match for
``regions`` + a paired-paren scan is correct and bounded for the in-repo
case profiles (verified by ``tests/p3/test_region_properties_reader.py``).

## Why fluid/solid tuples are independently optional

Per DEC-V61-213 §key-presence-vs-payload-completeness: ``fluid`` absent is
"I have no information about fluid regions" (``None``); ``fluid ()`` is
"I have information — the fluid region list is empty" (``()``). These are
semantically distinct. An CHT case with only-solid regions would legitimately
have no ``fluid`` group; ``None`` is the correct encoding, not ``()``. The
parser decides each field on its own independent path so that one-fluid /
no-solid and no-fluid / one-solid cases are both valid and unambiguous.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = ["extract", "RegionPropertiesSnapshot"]


# ----------------------------------------------------------------------
# RegionPropertiesSnapshot dataclass — NEW, no upstream equivalent.
# ----------------------------------------------------------------------
# Per DEC-V61-213 + DEC-V61-217 W3.0. Both fields carry `= None` because
# BOTH are independently optional; there is no required field. frozen=True
# mirrors the sibling extractors' immutability contract.
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class RegionPropertiesSnapshot:
    """CHT region lists — fluid/solid group names from ``constant/regionProperties``.

    NEW dataclass (no upstream equivalent) per DEC-V61-217 W3.0.
    Drift risk: NONE today (no upstream class to drift against). If a future
    advisor consumes ``RegionPropertiesSnapshot``, a
    ``test_region_properties_snapshot_mirror_parity`` canary would be added
    at that point (mirror DEC-211 R0 P1 pattern).

    Key-presence-vs-payload-completeness (DEC-V61-213):
      - ``None``           ← group key absent from source
      - ``()``             ← group key present, sub-list empty
      - ``(name, ...)``    ← group key present, sub-list populated
    """

    fluid_regions: tuple[str, ...] | None = None
    solid_regions: tuple[str, ...] | None = None


# ----------------------------------------------------------------------
# Comment stripping (identical to all three sibling extractors).
# ----------------------------------------------------------------------
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _strip_comments(text: str) -> str:
    """Remove ``/* ... */`` blocks and ``// ...`` line tails before key matching."""
    text = _BLOCK_COMMENT_RE.sub("", text)
    text = _LINE_COMMENT_RE.sub("", text)
    return text


# ----------------------------------------------------------------------
# Paired-paren scanner — mirrors thermo_dict_extractor._find_matching_close
# but for ``(``/``)`` instead of ``{``/``}``. String-literal-aware so
# quoted ``(``/``)`` characters cannot mismatch the paren depth count.
# ----------------------------------------------------------------------
def _find_matching_close_paren(text: str, start: int) -> int | None:
    """Return index of the ``)`` that closes the ``(`` whose body starts at *start*.

    *start* is the index of the first character AFTER the opening ``(``.
    Returns the index of the matching ``)``, or ``None`` if unmatched.
    """
    depth = 1
    i = start
    n = len(text)
    in_string = False
    while i < n:
        c = text[i]
        if in_string:
            if c == "\\" and i + 1 < n:
                i += 2
                continue
            if c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return None


# Locates `regions` at token level (not strictly column-0 anchored) so that
# one-line ``regions ( ... );`` works as well as the multi-line form.
# Uses ``(?ms)`` for DOTALL+MULTILINE so ``.`` spans newlines later.
# ``\b`` word-boundary prevents ``myregions`` from matching.
_REGIONS_TOKEN_RE = re.compile(r"(?ms)\bregions\s*\(")

# After the ``regions ( ... )`` list closes, only a single optional ``;`` plus
# whitespace may remain (standard ``regionProperties`` has no other top-level
# entry). Anything else means the file is malformed → honest refusal.
_TRAILING_OK_RE = re.compile(r"\s*;?\s*\Z")


def _index_in_string(text: str, idx: int) -> bool:
    """Return ``True`` if *idx* falls inside a double-quoted string in *text*.

    A single forward scan tracking quote state (with ``\\`` escapes), mirroring
    ``_find_matching_close_paren``'s string handling. Used so that a ``regions
    (`` token appearing inside a quoted metadata value (e.g.
    ``note "generated from regions (fluid solid) template";``) is NOT counted
    as a real ``regions`` entry (Codex R0 P3).
    """
    in_string = False
    i = 0
    n = len(text)
    while i < idx and i < n:
        c = text[i]
        if in_string:
            if c == "\\" and i + 1 < n:
                i += 2
                continue
            if c == '"':
                in_string = False
        elif c == '"':
            in_string = True
        i += 1
    return in_string


def _locate_regions_body(text: str) -> str | None:
    """Find ``regions ( ... )`` in *text* and return the inner body string.

    Uses ``finditer`` to detect duplicates (ambiguous source → ``None``).
    Returns the raw inner body (between the outer ``(`` and its matching
    ``)``), or ``None`` if:
      - no ``regions`` token found,
      - more than one ``regions (`` occurrence OUTSIDE a quoted string
        (duplicate-key refusal — a ``regions (`` inside a quoted metadata
        value does NOT count; Codex R0 P3),
      - the opening ``(`` has no matching ``)``,
      - non-trivial tokens remain after the ``regions (...)`` list closes
        (e.g. ``regions ( fluid (air) ) solid (metal);`` — a misplaced paren
        that would otherwise yield a silently-truncated partial snapshot;
        Codex R0 P2 honest-refusal).
    """
    matches = [
        m for m in _REGIONS_TOKEN_RE.finditer(text)
        if not _index_in_string(text, m.start())
    ]
    if len(matches) != 1:
        # 0 → regions key missing; >1 → ambiguous source.
        return None
    m = matches[0]
    body_start = m.end()  # one past the opening ``(``
    close = _find_matching_close_paren(text, body_start)
    if close is None:
        return None
    # Honest-refusal: reject trailing top-level tokens after the list closes.
    if _TRAILING_OK_RE.fullmatch(text[close + 1 :]) is None:
        return None
    return text[body_start:close]


# ----------------------------------------------------------------------
# Top-level structural parser.
#
# The ``regions`` body is parsed into a flat list of TOP-LEVEL items, each
# either a bare ``word`` token or a balanced ``( ... )`` group. Group
# detection is anchored to this top level so that a ``fluid``/``solid``
# token appearing INSIDE another group's name-list can never false-match
# and fabricate a region list (red-team 2026-05-30 P1). Any out-of-grammar
# character (digit-led token, stray ``)``, quote) makes the parse refuse
# (returns ``None``) rather than silently harvesting a partial result.
# ----------------------------------------------------------------------
_WORD_RE = re.compile(r"[A-Za-z_]\w*")


def _parse_top_level_items(body: str) -> list[tuple[str, str]] | None:
    """Tokenize *body* into top-level items, or ``None`` if malformed.

    Each item is ``("word", token)`` or ``("group", inner_body)`` where
    *inner_body* is the text between a balanced ``(`` and its matching
    ``)``. Only whitespace separates items. Any other character — a
    digit-led token, an embedded quote, a stray ``)``, or a ``;`` (Codex R1
    P2: a statement terminator is malformed INSIDE the ``regions`` list; a
    legitimate trailing ``;`` lives after the list close, handled by
    ``_locate_regions_body``) — means the body is out of the bare-word/paren
    grammar this extractor accepts, so the function returns ``None`` (honest
    refusal, never a partial harvest).
    """
    items: list[tuple[str, str]] = []
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c.isspace():
            i += 1
            continue
        if c == "(":
            close = _find_matching_close_paren(body, i + 1)
            if close is None:
                return None  # unmatched open paren
            items.append(("group", body[i + 1 : close]))
            i = close + 1
            continue
        if c == ")":
            return None  # stray close paren → malformed
        m = _WORD_RE.match(body, i)
        if m is None:
            return None  # out-of-grammar token (digit-led, quote, punctuation)
        items.append(("word", m.group(0)))
        i = m.end()
    return items


def _parse_names(sub_body: str) -> tuple[str, ...] | None:
    """A region name-list must contain ONLY bare word tokens.

    Returns the tuple of names (possibly empty ``()``), or ``None`` if the
    sub-list contains a nested group or any out-of-grammar token — an honest
    refusal rather than a silently-flattened or silently-truncated result
    (red-team 2026-05-30 P2: ``(air solid(metal))`` must NOT conjure a
    ``solid`` group; ``(123air)`` must NOT become ``air``).
    """
    items = _parse_top_level_items(sub_body)
    if items is None:
        return None
    names: list[str] = []
    for kind, value in items:
        if kind != "word":
            return None  # a nested group inside a name-list → refuse
        names.append(value)
    return tuple(names)


def _extract_group_pairs(regions_body: str) -> dict[str, tuple[str, ...]] | None:
    """Map each top-level group word → its region-name tuple.

    Handles both accepted shapes:
      - single-paren  ``fluid (a b) solid (c)``        (canonical OpenFOAM)
      - double-paren  ``(fluid (a b)) (solid (c))``    (W3.0 charter form)

    Returns ``None`` (refuse the whole snapshot) on any malformation or on a
    duplicate group word (DEC-V61-213 honest-refusal). An empty body yields
    an empty mapping (no groups declared → both fields end up ``None``).
    """
    items = _parse_top_level_items(regions_body)
    if items is None:
        return None

    pairs: dict[str, tuple[str, ...]] = {}

    def _record(word: str, names: tuple[str, ...]) -> bool:
        if word in pairs:
            return False  # duplicate group → caller refuses
        pairs[word] = names
        return True

    idx = 0
    while idx < len(items):
        kind, value = items[idx]
        if kind == "word":
            # single-paren form: a group word must be followed by its ( ... ).
            if idx + 1 >= len(items) or items[idx + 1][0] != "group":
                return None  # group word with no following name-list → malformed
            names = _parse_names(items[idx + 1][1])
            if names is None or not _record(value, names):
                return None
            idx += 2
            continue
        # kind == "group": double-paren form — inner must be exactly word + list.
        inner = _parse_top_level_items(value)
        if (
            inner is None
            or len(inner) != 2
            or inner[0][0] != "word"
            or inner[1][0] != "group"
        ):
            return None
        names = _parse_names(inner[1][1])
        if names is None or not _record(inner[0][1], names):
            return None
        idx += 1
    return pairs


def extract(case_dir: Path) -> RegionPropertiesSnapshot | None:
    """Read ``<case_dir>/constant/regionProperties`` → ``RegionPropertiesSnapshot``.

    Returns ``None`` (the honest "cannot construct a valid snapshot" signal)
    when:
      - ``constant/regionProperties`` is missing or unreadable (OSError),
      - no parseable single ``regions ( ... )`` entry exists (key absent,
        unmatched paren, or duplicate ``regions`` key — an ambiguous-source
        refusal per DEC-V61-213 invariant #4),
      - the ``regions`` body is malformed: a duplicate ``fluid``/``solid``
        group, a name-list containing a nested group, or any out-of-grammar
        token (digit-led name, stray paren). In every such case the parser
        REFUSES rather than fabricating a partial region list.

    When ``regions ( ... )`` is present and well-formed, ``fluid_regions``
    and ``solid_regions`` are populated independently (DEC-V61-213):
      - group key absent             → field ``None``   (missing-key leg)
      - group key present, empty list → field ``()``
      - group key present, populated → field ``tuple[str, ...]``

    ``regions ()`` (outer list present, no groups) yields
    ``RegionPropertiesSnapshot(None, None)`` — a valid non-``None`` snapshot.

    Per DEC-V61-130/132, this function is **read-only** — ``Path.read_text``
    is the only I/O; no writes, no route, no mutation.
    """
    region_props_path = case_dir / "constant" / "regionProperties"
    if not region_props_path.is_file():
        return None
    try:
        raw = region_props_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    regions_body = _locate_regions_body(_strip_comments(raw))
    if regions_body is None:
        # No parseable ``regions ( ... )`` entry (key absent, duplicate,
        # or unmatched paren) → cannot construct a snapshot.
        return None

    pairs = _extract_group_pairs(regions_body)
    if pairs is None:
        # Malformed body / duplicate group / out-of-grammar token → refuse.
        return None

    # ``dict.get`` yields ``None`` for an absent group and the (possibly
    # empty) tuple for a present one — the DEC-V61-213 key-presence-vs-
    # payload-completeness distinction falls out for free, no sentinel needed.
    return RegionPropertiesSnapshot(
        fluid_regions=pairs.get("fluid"),
        solid_regions=pairs.get("solid"),
    )

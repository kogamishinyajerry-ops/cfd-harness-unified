"""shm_dict extractor · case_dir → Mapping[str, Any] | None (v0.1).

Per DEC-V61-212. Reads ``<case_dir>/system/snappyHexMeshDict`` and returns
the minimum-subset parsed dict that lets
``geometry_ingest.shm_dict_validator.validate_shm_dict`` produce
case-specific findings.

Extracted shape (each top-level key independently OPTIONAL — missing in
source ⇒ absent from output, NOT key=None)::

    {
        "geometry": {
            "<entry_key>": {"type": "<token>", "name": "<alias>", "file": "<path>"},
            ...   # name/file present only if source declared them
        },
        "castellatedMeshControls": {
            "features": [{"file": "<name>.eMesh"}, ...] | [],
            "refinementSurfaces": {
                "<surf>": {"patchInfo": {"type": "<wall|patch|symmetryPlane|...>"}},
                # OR {"<surf>": {"patchInfo": {}}}     if type unparseable,
                # OR {"<surf>": {}}                    if patchInfo block absent
            },
            "refinementRegions": {"<reg>": {}, ...},
        },
        "addLayersControls": {"<key>": None, ...},   # flat top-level keys only
    }

The four detection paths in `validate_shm_dict` read exactly these
fields (per DEC-V61-212 §Decision table). Numeric values
(``level``/``levels``/``nSurfaceLayers``/``maxLocalCells``/...) are
**NOT extracted** — they widen extractor surface for zero finding-gain.

## Scope-locked NON-features (extractor will NOT parse correctly)

  - Numeric/quantitative values (sizing-field audit · separate sub-DEC).
  - ``snapControls`` / ``meshQualityControls`` blocks (typo-widening ·
    separate sub-DEC). Typo at ``snapControls.tolerace`` invisible to v0.1.
  - ``#include`` directives (e.g. case_006's
    ``meshQualityControls { #include "meshQualityDict" }``) — included
    file contents are NOT followed; the include line is silently ignored
    (no extracted key). Typos inside an included file are invisible.
  - **Same-line block-form `#`-directives**
    (``#codeStream { ... }`` with ``{`` on the SAME line as the
    directive name, or any ``#<directive> {`` opening on the directive's
    header line). The ``addLayersControls`` walker handles next-line form
    (``#codeStream\\n{ ... }``) cleanly via R2's brace-peek after the
    header line, but the same-line form leaks the block body's inner
    tokens into the extracted key set. **v0.1 scope-locks this OUT**:
    zero in-repo SHM files use this pattern today (verified
    ``find .planning ui/backend -name snappyHexMeshDict*``, 2026-05-28
    audit in `.planning/retrospectives/2026-05-28_dec212_codex_round3_overflow.md`).
    A follow-on v0.2 / sub-DEC can add the ~10 LOC peek-for-same-line-``{``
    fix when a real case lands the pattern. Codex R2 P2 finding archived
    per the retro; v2.3 round cap=3 honored.
  - OpenFOAM regex-pattern keys (e.g. ``"(U|k|omega)"``) — captured as a
    literal string key, not expanded. `validate_shm_dict`'s typo
    fuzzy-match has edit-distance > 2 vs every CANONICAL key for these.
  - STL face-normals for path (e) — `validate_shm_dict` consumes
    ``stl_face_normals`` as a SEPARATE kwarg from a geometric source,
    NOT from the shm_dict. v0.1 extractor does NOT supply normals; path
    (e) of the advisor never runs against v0.1-extracted dicts. A
    separate ``shm_stl_normals_extractor`` sub-DEC will own normals.
  - Multi-mesh-dir convention (case_004_v64_mesh_conv_study ships
    ``h2/snappyHexMeshDict`` + ``h4/`` instead of
    ``system/snappyHexMeshDict``) — v0.1 returns None for that case
    (honest omission). Follow-on sub-DEC can add multi-dir handling.
  - Macros / variable substitution (``$macroName``) — captured as the
    literal ``$macroName`` token. `validate_shm_dict` reads keys not
    values for paths (a)-(d); path (e) only fires on a string value in
    `_CONSTRAINED_PATCH_TYPES`, which ``$macro`` is not, so no
    false-positive risk.
  - Quotes / outer parens — ``type "wall";`` and ``name (region);`` are
    stripped to the bare token (mirrors `_strip_geometry_alias` advisor
    convention).
  - Brace-depth-unawareness of top-level block locator: the four
    top-level block names (``geometry`` / ``castellatedMeshControls`` /
    ``refinementSurfaces`` / ``refinementRegions`` / ``addLayersControls``)
    are located by line-anchored regex matched against the
    comment-stripped buffer. A malformed concatenated SHM with a
    ``geometry {`` line inside a nested block would false-match. The
    DEC-211 R0/P3 sibling caveat applies here too — well-formed source
    is assumed (verified across all 10 in-repo SHM dicts 2026-05-28).
  - String-literal-unaware comment stripping: ``//`` / ``/* */`` inside
    quoted values are stripped, mangling the quoted text. Safe for v0.1
    because none of the extracted token classes use those characters.

## Architectural placement

Mirrors DEC-V61-211 ``solver_block_extractor`` exactly: stdlib-only
(``pathlib`` + ``re``), pure function, read-only (one ``Path.read_text``),
no route, no mutation, no import from ``geometry_ingest`` (no
trimesh transitive — though v0.1 has no dataclass mirror since the
return type IS ``Mapping[str, Any]``).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

__all__ = ["extract"]


# ----------------------------------------------------------------------
# Comment stripping (same approach as DEC-V61-211 solver_block_extractor).
# ----------------------------------------------------------------------
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _strip_comments(text: str) -> str:
    text = _BLOCK_COMMENT_RE.sub("", text)
    text = _LINE_COMMENT_RE.sub("", text)
    return text


# ----------------------------------------------------------------------
# Brace / paren matching helpers (string-literal aware).
# ----------------------------------------------------------------------
def _find_matching_close(text: str, start: int, open_ch: str, close_ch: str) -> int | None:
    """Return index of `close_ch` matching the opener at index `start-1`.

    `start` points to the first character AFTER the opener. String literals
    (``"..."`` with simple backslash escaping) are skipped when counting
    depth. Returns None if unmatched.
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
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return None


def _find_top_level_block(text: str, key: str) -> tuple[int, int] | None:
    """Find top-level ``<key> { ... }`` block in `text`; return inner (start, end).

    `start` is the index of the first char of the inner body (one past the
    opening ``{``). `end` is the index of the matching closing ``}``
    (exclusive of the brace itself, so ``text[start:end]`` is the inner body
    excluding both braces).

    Returns None when the key doesn't appear at column 0 of any line in
    the (comment-stripped) buffer OR when the brace is unmatched.
    """
    # `<key>` at column 0 (after optional indentation), optionally
    # followed by whitespace/newlines, then `{`. Handles same-line and
    # next-line opening brace forms.
    pattern = re.compile(
        rf"(?ms)^\s*{re.escape(key)}\s*\{{",
    )
    m = pattern.search(text)
    if m is None:
        return None
    body_start = m.end()
    close = _find_matching_close(text, body_start, "{", "}")
    if close is None:
        return None
    return body_start, close


def _find_nested_block(text: str, key: str) -> tuple[int, int] | None:
    """Find ``<key> { ... }`` ANYWHERE in `text` (not column-anchored).

    Used inside an already-extracted parent block, where the nested key
    may appear indented at column > 0. The parent's outer braces have
    already been stripped before calling this.
    """
    pattern = re.compile(rf"(?ms)(?:^|\s){re.escape(key)}\s*\{{")
    m = pattern.search(text)
    if m is None:
        return None
    # m.end() is just past the `{`
    body_start = m.end()
    close = _find_matching_close(text, body_start, "{", "}")
    if close is None:
        return None
    return body_start, close


def _find_paren_list(text: str, key: str) -> str | None:
    """Find ``<key> ( ... )`` ANYWHERE in `text`; return inner contents.

    Returns None if key absent OR parens unmatched. Returns empty string
    if the source literally said ``<key> ();``.
    """
    pattern = re.compile(rf"(?ms)(?:^|\s){re.escape(key)}\s*\(")
    m = pattern.search(text)
    if m is None:
        return None
    body_start = m.end()
    close = _find_matching_close(text, body_start, "(", ")")
    if close is None:
        return None
    return text[body_start:close]


# ----------------------------------------------------------------------
# Geometry block parsing.
# ----------------------------------------------------------------------
# Within a geometry entry body, simple `key value;` extraction. The
# entry body is depth-0 inside its own braces; nested constructs like
# `min (a b c)` are non-brace and don't interfere with these regexes.
_TYPE_KV_RE = re.compile(r"\btype\s+([^\s;]+)\s*;")
_NAME_KV_RE = re.compile(r"\bname\s+([^\s;]+)\s*;")
_FILE_QUOTED_RE = re.compile(r'\bfile\s+"([^"]+)"\s*;')
_FILE_BARE_RE = re.compile(r'\bfile\s+([^\s;"]+)\s*;')


def _strip_quotes_and_parens(token: str) -> str:
    """Strip ONE outer ``"..."`` OR ONE outer ``(...)`` from a captured token.

    Source forms the extractor must normalize before emitting (Codex R0 P1
    finding 2026-05-28, DEC-V61-212 R1):
      - ``name wing``        → ``wing``  (no-op)
      - ``name "wing"``      → ``wing``  (outer double-quotes stripped)
      - ``name (region)``    → ``region`` (V100-WIDEN parens, mirrors
                                           ``shm_dict_validator._strip_geometry_alias``)
      - ``type "symmetryPlane"`` → ``symmetryPlane`` (else V99 path (e)
        would silently skip — ``"symmetryPlane"`` ≠ ``symmetryPlane`` so
        advisor's ``_CONSTRAINED_PATCH_TYPES`` membership check fails and
        a real multi-normal constrained patch goes undetected)

    Quotes and parens are NEVER stripped from a token that begins with one
    but does not end with the matching delimiter (would corrupt the
    truth-chain promise — better leave a malformed token visible than
    silently produce something plausible). Empty-after-strip returns
    ``""`` so the caller can drop the attribute.
    """
    s = token.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1].strip()
    elif len(s) >= 2 and s[0] == "(" and s[-1] == ")":
        s = s[1:-1].strip()
    return s


def _parse_geometry_entry(entry_body: str) -> dict[str, Any]:
    """Pull `type` / `name` / `file` from one geometry entry body."""
    entry: dict[str, Any] = {}
    m_type = _TYPE_KV_RE.search(entry_body)
    if m_type:
        entry["type"] = _strip_quotes_and_parens(m_type.group(1))
    m_name = _NAME_KV_RE.search(entry_body)
    if m_name:
        entry["name"] = _strip_quotes_and_parens(m_name.group(1))
    m_file = _FILE_QUOTED_RE.search(entry_body)
    if m_file is None:
        m_file = _FILE_BARE_RE.search(entry_body)
    if m_file:
        entry["file"] = m_file.group(1)
    return entry


def _parse_geometry_block(inner: str) -> dict[str, dict[str, Any]]:
    """Walk a geometry-block body and pull each entry.

    Each entry has the form ``<key> { <kvs> }`` (key may contain dots /
    underscores; ``{`` may be on same or next line). Entries with
    unmatched braces are silently skipped (parse failure on that entry
    only, not whole block).
    """
    entries: dict[str, dict[str, Any]] = {}
    i = 0
    n = len(inner)
    while i < n:
        # Skip whitespace.
        while i < n and inner[i].isspace():
            i += 1
        if i >= n:
            break
        # Read key token until whitespace or `{` (handles `<word>.stl`).
        j = i
        while j < n and not inner[j].isspace() and inner[j] != "{":
            j += 1
        if j == i:
            # No progress — character is something unexpected (e.g. `}`,
            # stray punctuation). Skip it.
            i += 1
            continue
        key = inner[i:j]
        i = j
        # Skip whitespace to the opening `{`.
        while i < n and inner[i].isspace():
            i += 1
        if i >= n or inner[i] != "{":
            # Key with no body — skip to next whitespace/EOL and continue.
            continue
        # Consume the `{` and find its matching `}`.
        i += 1
        close = _find_matching_close(inner, i, "{", "}")
        if close is None:
            # Unmatched brace — drop this entry, stop scanning rest of
            # block (further entries are unparseable past unmatched).
            break
        entry_body = inner[i:close]
        entries[key] = _parse_geometry_entry(entry_body)
        i = close + 1
    return entries


# ----------------------------------------------------------------------
# castellatedMeshControls block parsing.
# ----------------------------------------------------------------------
_PATCH_INFO_TYPE_RE = re.compile(r"\btype\s+([^\s;]+)\s*;")


def _parse_features_list(cmc_inner: str) -> list[dict[str, str]] | None:
    """Extract ``features ( ... )`` list of ``{file "X.eMesh"; ...}`` entries.

    Returns:
      - None  if `features` key absent OR paren-balanced parse failed OR
              parsed-entries count < expected entries (truth-chain R1:
              omit on parse failure rather than emit partial `[]` that
              would fabricate V86 ``orphaned_emesh_feature`` from a
              `.eMesh`-on-disk caller).
      - []    if source literally said ``features ()`` (empty).
      - [{"file": "X.eMesh"}, ...]  for parsed entries.
    """
    raw = _find_paren_list(cmc_inner, "features")
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return []
    # Count expected brace-delimited entries vs successfully parsed.
    expected = stripped.count("{")
    if expected == 0:
        # No entries declared inside non-empty parens — anomaly, refuse.
        return None
    entries: list[dict[str, str]] = []
    i = 0
    n = len(stripped)
    while i < n:
        # Skip up to next `{`.
        while i < n and stripped[i] != "{":
            i += 1
        if i >= n:
            break
        i += 1
        close = _find_matching_close(stripped, i, "{", "}")
        if close is None:
            break
        entry_body = stripped[i:close]
        m = _FILE_QUOTED_RE.search(entry_body)
        if m is None:
            m = _FILE_BARE_RE.search(entry_body)
        if m:
            entries.append({"file": m.group(1)})
        i = close + 1
    if len(entries) != expected:
        # Parse-failure on at least one entry (e.g. no `file` key,
        # unmatched braces, ...). Truth-chain R1: omit key.
        return None
    return entries


def _parse_refinement_surfaces(cmc_inner: str) -> dict[str, dict[str, Any]] | None:
    """Extract ``refinementSurfaces { <surf> { ... } ... }``.

    Per DEC-212 R2 (refined): ALWAYS emit the surface key. patchInfo
    sub-cases:
      - patchInfo block absent     → emit ``{<surf>: {}}``
      - patchInfo block, type      → emit ``{<surf>: {"patchInfo": {"type": "<tok>"}}}``
      - patchInfo block, no type   → emit ``{<surf>: {"patchInfo": {}}}``

    Returns None only when the ``refinementSurfaces`` key itself is
    absent. An empty ``refinementSurfaces { }`` source emits ``{}``.
    """
    span = _find_nested_block(cmc_inner, "refinementSurfaces")
    if span is None:
        return None
    inner = cmc_inner[span[0]:span[1]]
    surfaces: dict[str, dict[str, Any]] = {}
    i = 0
    n = len(inner)
    while i < n:
        while i < n and inner[i].isspace():
            i += 1
        if i >= n:
            break
        j = i
        while j < n and not inner[j].isspace() and inner[j] != "{":
            j += 1
        if j == i:
            i += 1
            continue
        surf_name = inner[i:j]
        i = j
        while i < n and inner[i].isspace():
            i += 1
        if i >= n or inner[i] != "{":
            continue
        i += 1
        close = _find_matching_close(inner, i, "{", "}")
        if close is None:
            break
        surf_body = inner[i:close]
        i = close + 1
        # Look for nested `patchInfo { type <tok>; }`.
        pi_span = _find_nested_block(surf_body, "patchInfo")
        if pi_span is None:
            # No patchInfo block in source — emit surface, no patchInfo key.
            surfaces[surf_name] = {}
            continue
        pi_inner = surf_body[pi_span[0]:pi_span[1]]
        m = _PATCH_INFO_TYPE_RE.search(pi_inner)
        if m is None:
            # patchInfo block exists but no parseable type — emit empty
            # patchInfo so path (b)/(c) still works on this surface (R2).
            surfaces[surf_name] = {"patchInfo": {}}
        else:
            surfaces[surf_name] = {
                "patchInfo": {"type": _strip_quotes_and_parens(m.group(1))}
            }
    return surfaces


def _parse_refinement_regions(cmc_inner: str) -> dict[str, dict[str, Any]] | None:
    """Extract ``refinementRegions { <reg> { ... } ... }``.

    Only the region KEYS matter to advisor path (c); values are emitted
    as empty dicts. Empty source block emits ``{}``. Returns None when
    the key itself is absent.
    """
    span = _find_nested_block(cmc_inner, "refinementRegions")
    if span is None:
        return None
    inner = cmc_inner[span[0]:span[1]]
    regions: dict[str, dict[str, Any]] = {}
    i = 0
    n = len(inner)
    while i < n:
        while i < n and inner[i].isspace():
            i += 1
        if i >= n:
            break
        j = i
        while j < n and not inner[j].isspace() and inner[j] != "{":
            j += 1
        if j == i:
            i += 1
            continue
        reg_name = inner[i:j]
        i = j
        while i < n and inner[i].isspace():
            i += 1
        if i >= n or inner[i] != "{":
            continue
        i += 1
        close = _find_matching_close(inner, i, "{", "}")
        if close is None:
            break
        regions[reg_name] = {}
        i = close + 1
    return regions


# ----------------------------------------------------------------------
# addLayersControls block — flat top-level keys only.
# ----------------------------------------------------------------------
# Matches `<key>` at start of a line within the block body. Captures
# both scalar `key value;` and nested `key { ... }` and `key ( ... );`
# forms — we only need the KEYS for typo fuzzy-match, values discarded.
# Note: this regex is INTENTIONALLY non-greedy on values; we only use
# the captured key. Scalar form `key value;` is the dominant case.
_ALC_KEY_RE = re.compile(r"(?m)^\s*([A-Za-z][A-Za-z0-9_]*)\s+(?=[\S])")


def _parse_addlayerscontrols_keys(body: str) -> dict[str, None] | None:
    """Pull top-level KEYS from addLayersControls block; values are None.

    Path (d) typo-detection walks dict KEYS only — so emitting a
    ``{key: None}`` map is the smallest faithful representation. Nested
    sub-blocks (``layers { surface { ... } }``) are NOT recursed: their
    surface-name children are case-specific patch names and could
    fuzzy-match a CANONICAL key by accident.

    Returns ``{}`` for an empty block body; None only if the
    ``addLayersControls`` key was absent from the whole SHM.
    """
    keys: dict[str, None] = {}
    # Walk top-level only — skip past any nested `{...}` and `(...)`.
    i = 0
    n = len(body)
    while i < n:
        # Skip leading whitespace.
        while i < n and body[i].isspace():
            i += 1
        if i >= n:
            break
        # Codex R0 P2 fix (DEC-V61-212 R1) + Codex R1 P2 follow-up (R2):
        # an OpenFOAM directive line starts with `#`. Three forms exist:
        #
        #   (a) single-line (no body): `#include "..."` / `#includeIfPresent`
        #       / `#remove key` / `#inputMode merge` / `#calc "..."`.
        #   (b) block-form: `#codeStream { code #{ ... #}; ... }` —
        #       directive name on one line, BODY in following `{...}` block.
        #   (c) conditional: `#if 0 ... #endif` / `#ifdef` / `#ifndef` /
        #       `#ifeq` — directive on one line, BODY of arbitrary lines
        #       terminated by `#endif`. Conditional content may be active
        #       (`#if 1`) or inactive (`#if 0`); honest extractor cannot
        #       evaluate the condition without a preprocessor.
        #
        # Pre-R1 behavior was buggy for (a) — `include` was emitted as a
        # fake key AND the next setting was eaten. R1 fixed (a) by skipping
        # the directive's whole line, but inadvertently REGRESSED (b)/(c):
        # the line-only skip resumes scanning inside the directive body,
        # leaking inactive/generated tokens into the key set. Codex R1 P2
        # caught this. R2 fix:
        #
        #   - (a) single-line: skip the header line (R1 behavior, kept).
        #   - (b) block-form: header skip THEN skip the following `{...}`
        #     block (matched-brace, string-literal-aware via
        #     `_find_matching_close`). For `#codeStream`, the inner
        #     `#{ ... #}` markers still balance brace-counted (each `#{`
        #     adds 1 to depth, each `#};` subtracts 1).
        #   - (c) conditional: scan for matching `#endif` with depth
        #     tracking so nested `#if ... #endif` doesn't terminate early.
        #     ALL content between `#if*` and `#endif` is honestly omitted
        #     (we don't know which branch is active — better to silently
        #     drop active settings than fabricate inactive ones).
        #
        # Honest scope-out: `#else` and `#elif` branches are skipped as
        # part of the `#if/#endif` body (we never include them). A real
        # case relying on `#else` would lose those keys; v0.2 sub-DEC
        # can add condition evaluation if real evidence emerges.
        if body[i] == "#":
            # Capture directive name BEFORE skipping (need it for #if/#endif
            # detection and for not leaking it as a key).
            dn_start = i + 1
            dn_end = dn_start
            while dn_end < n and (body[dn_end].isalnum() or body[dn_end] == "_"):
                dn_end += 1
            directive = body[dn_start:dn_end].lower()
            # Skip directive header to EOL.
            nl = body.find("\n", i)
            if nl == -1:
                break  # directive runs to EOF; nothing more to scan
            i = nl + 1
            # Form (c): conditional → scan to matching `#endif` (depth-aware).
            if directive in ("if", "ifdef", "ifndef", "ifeq"):
                depth = 1
                cond_re = re.compile(r"(?m)^\s*#(\w+)")
                while depth > 0 and i < n:
                    m = cond_re.search(body, i)
                    if m is None:
                        i = n  # unmatched #if → consume to EOF (honest)
                        break
                    inner = m.group(1).lower()
                    line_end = body.find("\n", m.end())
                    if line_end == -1:
                        line_end = n
                    if inner in ("if", "ifdef", "ifndef", "ifeq"):
                        depth += 1
                    elif inner == "endif":
                        depth -= 1
                    i = line_end + 1
                continue
            # Form (b): block-form → if next non-ws is `{`, skip block.
            # (Form (a) falls through: nothing to do after the header line.)
            k = i
            while k < n and body[k].isspace():
                k += 1
            if k < n and body[k] == "{":
                close = _find_matching_close(body, k + 1, "{", "}")
                if close is None:
                    break  # unmatched block → stop scanning (honest)
                i = close + 1
            continue
        # Read potential key token (alphanumeric / underscore only;
        # OpenFOAM key idiom).
        j = i
        while j < n and (body[j].isalnum() or body[j] == "_"):
            j += 1
        if j == i:
            # Not a key character — advance.
            i += 1
            continue
        key = body[i:j]
        i = j
        # Skip whitespace.
        while i < n and body[i].isspace():
            i += 1
        if i >= n:
            break
        # Now decide value form: scalar `value;`, list `( ... );`, or
        # block `{ ... }`. Advance past whichever; record the key.
        c = body[i]
        if c == "{":
            # Nested block — skip past matching `}`.
            i += 1
            close = _find_matching_close(body, i, "{", "}")
            if close is None:
                break
            keys[key] = None
            i = close + 1
        elif c == "(":
            # Paren list — skip past matching `)`, then optional `;`.
            i += 1
            close = _find_matching_close(body, i, "(", ")")
            if close is None:
                break
            keys[key] = None
            i = close + 1
            # Optional trailing `;`.
            while i < n and body[i].isspace():
                i += 1
            if i < n and body[i] == ";":
                i += 1
        else:
            # Scalar value terminated by `;`. Skip to next `;`.
            sc = body.find(";", i)
            if sc == -1:
                break
            keys[key] = None
            i = sc + 1
    return keys


# ----------------------------------------------------------------------
# Public extract entry-point.
# ----------------------------------------------------------------------
def extract(case_dir: Path) -> Mapping[str, Any] | None:
    """Read ``<case_dir>/system/snappyHexMeshDict`` → parsed dict subset.

    Returns ``None`` when:
      - ``system/snappyHexMeshDict`` is missing,
      - the file is unreadable (OSError),
      - none of the five extractable top-level blocks
        (``geometry`` / ``castellatedMeshControls`` /
        ``addLayersControls`` — plus the two nested under cmc) is
        present (an SHM with NO recognizable block is meaningless for
        the case-behavioral eval).

    Per DEC-V61-132 truth-chain: missing source field ⇒ absent output
    key (NOT key=None). Parse failure on a specific sub-block ⇒ omit
    that sub-block (R1 for ``features`` list; R2 for individual
    refinementSurface ``patchInfo`` when block-present-but-type-missing
    emits ``{"patchInfo": {}}``, sub-case of "emit surface always").

    This function is **read-only** — ``Path.read_text`` is the sole I/O.
    Per DEC-V61-130/132: no writes, no route, no mutation, advisory only.
    """
    path = case_dir / "system" / "snappyHexMeshDict"
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    body = _strip_comments(raw)
    out: dict[str, Any] = {}

    # --- geometry block ---
    geom_span = _find_top_level_block(body, "geometry")
    if geom_span is not None:
        geom_inner = body[geom_span[0]:geom_span[1]]
        out["geometry"] = _parse_geometry_block(geom_inner)

    # --- castellatedMeshControls block (with nested rs/rr/features) ---
    cmc_span = _find_top_level_block(body, "castellatedMeshControls")
    if cmc_span is not None:
        cmc_inner = body[cmc_span[0]:cmc_span[1]]
        cmc_out: dict[str, Any] = {}
        feat = _parse_features_list(cmc_inner)
        if feat is not None:
            cmc_out["features"] = feat
        rs = _parse_refinement_surfaces(cmc_inner)
        if rs is not None:
            cmc_out["refinementSurfaces"] = rs
        rr = _parse_refinement_regions(cmc_inner)
        if rr is not None:
            cmc_out["refinementRegions"] = rr
        if cmc_out:
            out["castellatedMeshControls"] = cmc_out

    # --- addLayersControls (flat keys only) ---
    alc_span = _find_top_level_block(body, "addLayersControls")
    if alc_span is not None:
        alc_inner = body[alc_span[0]:alc_span[1]]
        alc_keys = _parse_addlayerscontrols_keys(alc_inner)
        if alc_keys is not None:
            out["addLayersControls"] = alc_keys

    if not out:
        # NO recognizable block — meaningless for the eval pipeline.
        return None
    return out

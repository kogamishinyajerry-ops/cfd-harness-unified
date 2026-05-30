"""thermo_dict extractor · case_dir → (Mapping[str, Any], ThermoModelTags) | None (v0.1).

Per DEC-V61-213. Reads ``<case_dir>/constant/thermophysicalProperties`` and
returns the minimum-subset parsed dict that lets
``geometry_ingest.thermo_polynomial_range_advisor.check_thermo_polynomial_range``
dispatch over a synthesized single-species mixture, plus a companion
``ThermoModelTags`` dataclass exposing the ``thermoType`` block tokens
the eval layer reads to differentiate cases.

Extracted shape (single synthetic species under the sentinel key
``"_mixture"`` — see §"Truth-chain R1" below for sentinel choice
rationale)::

    {
        "_mixture": {
            "specie": {"molWeight": <float>},
            "thermodynamics": {
                "Cp": <float>,             # when thermoType.thermo == hConst
                "Hf": <float>,             # when present in source
                # NOTE: Tlow/Thigh INTENTIONALLY absent — hConst has no
                # polynomial range; synthesizing a default would
                # fabricate fictional advisor input (DEC-213 §Truth-chain
                # R2). Honest omission is the truth.
            },
            "transport": {
                # Either As/Ts (when transport == sutherland) OR
                # mu/Pr (when transport == const). Partial sutherland
                # (As without Ts, or vice-versa) ⇒ snapshot None.
                "As": <float>, "Ts": <float>,
                # OR
                "mu": <float>, "Pr": <float>,
            },
        }
    }

The companion ``ThermoModelTags`` (frozen dataclass) carries the six
``thermoType`` tokens — ``type`` / ``mixture`` / ``transport`` /
``thermo`` / ``equation_of_state`` / ``energy`` — used by the eval to
differentiate cases. ``check_thermo_polynomial_range`` itself does NOT
read these tags (DEC-V61-213 §Decision), but the eval depends on them
to assert the 4 distinct ``(transport, energy)`` tuples across the 5
in-repo hConst profiles.

## Scope-locked v0.1 — extractor will NOT parse correctly

  - ``thermo == eConst`` profiles (e.g.
    ``case_006_v64_val_full_2_dicts/_v24_rhocentralfoam_fallback``,
    which uses ``Cv 717.5;`` instead of ``Cp``). v0.1 returns ``None``
    for eConst sources — scope-locked hConst-only per the same v0.1-narrow
    rationale that ``solver_block_extractor`` uses for preconditioners
    (DEC-V61-211). Documented as a NON-feature; carry-forward sub-DEC
    adds eConst→Cv reading when a real run needs it.
  - **janaf-polynomial / multi-species mechanism shape**
    (``constant/thermo.compressibleGas`` with ``highCpCoeffs``/``lowCpCoeffs``
    + per-species ``Tlow``/``Thigh`` records). Zero in-repo profiles ship
    this format today (verified 2026-05-28: only ``case_009_sandia_flame_d.md``
    discusses it; no ``*_dicts/`` directory contains it). v0.2 sub-DEC when
    case_009 sediments a ``_dicts/`` artifact.
  - **Synthesizing a default Tlow under hConst/eConst** — extractor MUST
    NOT (DEC-V61-213 §Truth-chain R2). Absence IS the truth. The
    advisor's ``_extract_species_tlows`` correctly drops species with
    no coercible Tlow, leaving the census empty and paths (a)/(b)/(c)
    vacuous ⇒ ``is_clean=True``.
  - ``#include`` directives (e.g. ``#include "thermoMixture.foam"``) —
    silently ignored at line level. Pre-flight audit of all 6 in-repo
    thermo files confirms ZERO ``#``-directives, so the extractor never
    needs to handle them in v0.1 (DEC-V61-212 retro lesson #2:
    enumerate ALL forms BEFORE writing; the form set is empty here).
    Follow-on sub-DEC if a real case lands ``#include`` inside the
    ``mixture`` or ``thermoType`` blocks.
  - **Macro substitution** (``$molWeight``, ``$Cp``) and ``#calc``
    expressions — captured as literal token by the value regex, which
    won't parse as a float ⇒ snapshot None (honest refusal, not
    fabrication). Mirrors ``solver_block_extractor`` macro-substitution
    scope-out language.
  - **Multi-species top-level shape** (e.g. ``mixture { species (CH4 O2 N2); … }``
    or species-keyed dict where the top-level keys ARE species names) —
    v0.1 emits only the single ``_mixture`` synthetic key. Separate
    sub-DEC when real multi-species ships.
  - **0/T boundary conditions** (the ``thermo_boundary_conditions``
    kwarg of ``check_thermo_polynomial_range``) — separate extractor
    under separate sub-DEC; different directory (``0/T`` not
    ``constant/…``), different failure modes.
  - **Brace-depth-unawareness inside the mixture/thermoType slices** —
    once the paired-brace scan locates the outer block, inner regexes
    are line-anchored at column 0 within the slice. A malformed
    nested-block-with-same-key would false-match. Mirror
    ``solver_block_extractor`` §brace-depth scope-out. All 6 in-repo
    files verified well-formed.
  - **String-literal-unaware comment stripping** — mirror
    ``solver_block_extractor`` + ``shm_dict_extractor``. Safe for v0.1's
    numeric-value-only keys (``molWeight``/``Cp``/``Hf``/``As``/``Ts``/
    ``mu``/``Pr``).
  - **One-line ``FoamFile { … object thermophysicalProperties; }``
    headers** (e.g. ``case_006_v64_thermo_fpe_fix:11``,
    ``case_006_v64_val_full_2:6``, ``_v24_rhocentralfoam_fallback:4``)
    are handled CORRECTLY because the line-anchored regexes for the
    in-scope keys (``molWeight``/``Cp``/``Hf``/``As``/``Ts``/``mu``/
    ``Pr``) fire INSIDE the ``mixture { … }`` / ``thermoType { … }``
    paired-brace slice, not at module top level. Verified by tests.

## Architectural placement

Mirrors DEC-V61-211 ``solver_block_extractor`` + DEC-V61-212
``shm_dict_extractor`` exactly: stdlib-only (``pathlib`` + ``re`` +
``dataclasses`` + ``typing``), pure function, read-only (one
``Path.read_text``), no route, no mutation, no import from
``geometry_ingest`` (would pull ``trimesh`` transitively via
``__init__.py → health_check``). ``ThermoModelTags`` is a NEW
dataclass — no upstream class exists today so no mirror parity
canary is needed (would be added when a future advisor consumes the
tags directly).

## Why thermo_dict v0.1 has real discrimination

Per DEC-V61-213 §"Why thermo_dict v0.1 has real discrimination", the 5
hConst in-repo profiles split into **4 distinct ``(transport, energy)``
tuples**:

  - sutherland + sensibleEnthalpy + hConst        — case_006_v64_thermo_fpe_fix
  - const + sensibleEnthalpy + hConst             — case_006_v64_val_full_2
  - sutherland + sensibleInternalEnergy + hConst  — case_016, case_031
  - const + sensibleInternalEnergy + hConst       — case_030

The 6th profile (case_006_v64_val_full_2/_v24_rhocentralfoam_fallback)
uses eConst — out of scope for v0.1 (returns None).

The advisor's path (a)/(b)/(c) logic returns ``is_clean=True`` on all 5
hConst profiles (the species_tlows census is empty — hConst has no
janaf polynomial range), so the EXTRACTOR's value in v0.1 is feeding
``assemble_stack`` so the dispatcher records "A10 advisor dispatched →
0 findings" rather than "A10 advisor skipped (no thermo_dict)" — a
truth-chain distinction the eval depends on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

__all__ = ["extract", "ThermoModelTags"]


# ----------------------------------------------------------------------
# ThermoModelTags companion dataclass — eval discriminator.
# ----------------------------------------------------------------------
# NEW dataclass (no upstream equivalent). Carries the six thermoType
# block tokens that differentiate cases at the eval layer.
# `check_thermo_polynomial_range` itself does NOT consume these tags —
# they are emitted alongside the snapshot so the eval / test layer can
# assert that 4 distinct (transport, energy) tuples exist across the 5
# in-repo hConst profiles (DEC-V61-213 §"Why thermo_dict v0.1 has real
# discrimination").
#
# Drift risk: NONE today (no upstream class to drift against). If a
# future advisor consumes `ThermoModelTags`, a `test_thermo_model_tags_mirror_parity`
# canary would be added at that point (mirror DEC-211 R0 P1 pattern).
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class ThermoModelTags:
    """``thermoType`` block tokens — eval-layer discriminator only.

    Field naming mirrors OpenFOAM's ``thermoType`` block keys verbatim,
    except ``equation_of_state`` is Python-snake-case'd from OF's
    ``equationOfState`` (the OF dict key) for Pythonic field access.
    """

    type: str                # e.g. "hePsiThermo" / "heRhoThermo"
    mixture: str             # "pureMixture" (only form in v0.1)
    transport: str           # "sutherland" | "const"
    thermo: str              # "hConst" | "eConst" (eConst ⇒ snapshot None in v0.1)
    equation_of_state: str   # "perfectGas"
    energy: str              # "sensibleEnthalpy" | "sensibleInternalEnergy"


# ----------------------------------------------------------------------
# Comment stripping (same approach as DEC-V61-211 / -212).
# ----------------------------------------------------------------------
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _strip_comments(text: str) -> str:
    text = _BLOCK_COMMENT_RE.sub("", text)
    text = _LINE_COMMENT_RE.sub("", text)
    return text


# ----------------------------------------------------------------------
# Paired-brace scanner — mirrors shm_dict_extractor._find_matching_close.
# String-literal aware so quoted ``{`` / ``}`` characters in values
# (e.g. ``location "constant";``) cannot mismatch the brace count.
# ----------------------------------------------------------------------
def _find_matching_close(text: str, start: int, open_ch: str, close_ch: str) -> int | None:
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
    """Find top-level ``<key> { ... }`` block; return inner (start, end).

    ``start`` indexes the first char of the inner body (one past the
    opening ``{``); ``end`` indexes the matching closing ``}`` (exclusive
    of the brace itself, so ``text[start:end]`` is the inner body
    excluding both braces). Duplicate top-level occurrences are
    detected by the caller via a second ``finditer`` pass — invariant #4
    duplicate-key refusal (mirrors solver_block_extractor.py:200-228).
    """
    pattern = re.compile(rf"(?ms)^\s*{re.escape(key)}\s*\{{")
    m = pattern.search(text)
    if m is None:
        return None
    body_start = m.end()
    close = _find_matching_close(text, body_start, "{", "}")
    if close is None:
        return None
    return body_start, close


def _count_top_level_blocks(text: str, key: str) -> int:
    """Return the number of top-level ``<key> {`` occurrences in `text`.

    Used to refuse snapshots when the source duplicates a structurally
    required top-level block (e.g. two ``thermoType { … }`` blocks —
    OpenFOAM errors on this, and silently picking the first would
    violate the truth-chain promise the same way that solver_block
    duplicate-application refuses).
    """
    pattern = re.compile(rf"(?ms)^\s*{re.escape(key)}\s*\{{")
    return len(pattern.findall(text))


def _find_nested_block(text: str, key: str) -> tuple[int, int] | None:
    """Find ``<key> { ... }`` ANYWHERE in `text` (not column-anchored)."""
    pattern = re.compile(rf"(?ms)(?:^|\s){re.escape(key)}\s*\{{")
    m = pattern.search(text)
    if m is None:
        return None
    body_start = m.end()
    close = _find_matching_close(text, body_start, "{", "}")
    if close is None:
        return None
    return body_start, close


def _count_nested_blocks(text: str, key: str) -> int:
    """Count ``<key> {`` occurrences ANYWHERE in `text`."""
    pattern = re.compile(rf"(?ms)(?:^|\s){re.escape(key)}\s*\{{")
    return len(pattern.findall(text))


# ----------------------------------------------------------------------
# Inner-key matchers — used INSIDE pre-located leaf sub-blocks (`specie`,
# `thermodynamics`, `transport` under `mixture`; the `thermoType` body
# itself). At this depth the body is small and structurally constrained
# (each block holds 1-3 key=value pairs), so we use a permissive
# "word-boundary + key + value + ;" pattern that matches anywhere in the
# slice rather than only at column 0. This handles BOTH the canonical
# multi-line form (one key per line — all 6 in-repo profiles) AND the
# compressed single-line form (`{ As 1.458e-06; Ts 110.4; }`) which is
# legal OpenFOAM syntax. Top-level FoamFile collision is impossible
# here because these regexes only fire INSIDE a paired-brace slice we
# already located via `_find_top_level_block` / `_find_nested_block`.
#
# Key boundary: `(?:^|[\s;{])` requires the key to follow a separator
# (start-of-string, whitespace, `;`, or `{`) so substring matches like
# `xCp` cannot fire (`Cp` would otherwise match anywhere in
# `someXCp 1.0;` — a fabrication risk). The terminator `;` after the
# value bounds the right side; duplicate-key refusal (above) catches
# multi-match ambiguity.
# ----------------------------------------------------------------------
# Numeric value pattern: signed scientific or decimal float, captured as
# the bare token. `_parse_float` gates parseability; macros (`$molWeight`)
# don't match this pattern and return None ⇒ snapshot None (honest refusal).
_NUMERIC_VALUE = r"[0-9eE+\-.]+"
_KEY_LEFT_BOUNDARY = r"(?:^|[\s;{])"  # start-of-string OR whitespace/;/{ separator

_MOL_WEIGHT_RE = re.compile(
    rf"{_KEY_LEFT_BOUNDARY}molWeight\s+({_NUMERIC_VALUE})\s*;"
)
_CP_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}Cp\s+({_NUMERIC_VALUE})\s*;")
_HF_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}Hf\s+({_NUMERIC_VALUE})\s*;")
# Cadence Codex R1 (2026-05-30 · CRS P3): Hf KEY-PRESENCE detector,
# independent of numeric parseability. Required to distinguish "Hf
# absent → optional omission" from "Hf present but ambiguous
# (duplicate / $macro / #calc) → honest snapshot refusal". The
# value-capturing `_HF_RE` above only matches numeric Hf entries;
# without this, duplicate or macro Hf entries cause `_HF_RE.findall()`
# to return 0 matches, collapsing into the "absent" case and hiding
# source ambiguity — violating the v0.1 truth-chain/refusal contract.
_HF_KEY_PRESENCE_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}Hf\s")
_AS_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}As\s+({_NUMERIC_VALUE})\s*;")
_TS_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}Ts\s+({_NUMERIC_VALUE})\s*;")
_MU_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}mu\s+({_NUMERIC_VALUE})\s*;")
_PR_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}Pr\s+({_NUMERIC_VALUE})\s*;")

# thermoType inner token matchers. \w+ matches the bare model name
# (e.g. `hePsiThermo`, `pureMixture`, `sutherland`, `hConst`,
# `perfectGas`, `specie`, `sensibleEnthalpy`). Same boundary discipline
# as the numeric matchers above (handles same-line packed thermoType
# blocks like `{ type hePsiThermo; mixture pureMixture; … }`).
_THERMOTYPE_TYPE_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}type\s+(\w+)\s*;")
_THERMOTYPE_MIXTURE_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}mixture\s+(\w+)\s*;")
_THERMOTYPE_TRANSPORT_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}transport\s+(\w+)\s*;")
_THERMOTYPE_THERMO_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}thermo\s+(\w+)\s*;")
_THERMOTYPE_EOS_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}equationOfState\s+(\w+)\s*;")
_THERMOTYPE_SPECIE_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}specie\s+(\w+)\s*;")
_THERMOTYPE_ENERGY_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}energy\s+(\w+)\s*;")


def _parse_float(token: str) -> float | None:
    try:
        return float(token)
    except (TypeError, ValueError):
        return None


def _single_match_or_none(regex: re.Pattern[str], body: str) -> str | None:
    """Return the single capture from `regex` over `body`, or None.

    Returns None when:
      - zero matches (key absent — caller decides what that means),
      - more than one match (duplicate key — ambiguous source, honest
        refusal per architecture invariant #4 / DEC-V61-211 pattern).
    """
    matches = regex.findall(body)
    if len(matches) != 1:
        return None
    return matches[0]


def _strip_nested_blocks(body: str) -> str:
    """Return *body* with every balanced ``{ ... }`` sub-block removed.

    Only depth-0 characters survive (those NOT enclosed in any ``{`` / ``}``
    pair). Applied before scanning a located leaf block (thermoType / specie /
    transport / thermodynamics) for scalar ``key value;`` pairs, so that a token
    declared inside a NESTED sub-block — adversarial / malformed input; valid OF
    leaf blocks contain no sub-dicts — cannot leak into the parent-block scan
    and be accepted as the parent value. Closes the recurring
    "line-anchored vs brace-depth" fabrication class (W3.0.2 red-team 2026-05-30;
    single-region shared the latent leak, hardened here for both paths).
    """
    out: list[str] = []
    depth = 0
    for ch in body:
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _extract_thermo_model_tags(thermotype_inner: str) -> ThermoModelTags | None:
    """Pull the six ``thermoType`` block tokens; None if any missing/ambiguous.

    Depth-0 scan only: a token declared inside a nested sub-block of thermoType
    (not valid OF; adversarial input) must NOT satisfy a REQUIRED token —
    notably the load-bearing ``type`` discriminator (W3.0.2 red-team P1).
    """
    thermotype_inner = _strip_nested_blocks(thermotype_inner)
    type_tok = _single_match_or_none(_THERMOTYPE_TYPE_RE, thermotype_inner)
    mixture_tok = _single_match_or_none(_THERMOTYPE_MIXTURE_RE, thermotype_inner)
    transport_tok = _single_match_or_none(_THERMOTYPE_TRANSPORT_RE, thermotype_inner)
    thermo_tok = _single_match_or_none(_THERMOTYPE_THERMO_RE, thermotype_inner)
    eos_tok = _single_match_or_none(_THERMOTYPE_EOS_RE, thermotype_inner)
    energy_tok = _single_match_or_none(_THERMOTYPE_ENERGY_RE, thermotype_inner)
    # `specie` token is the OF "specie type" (always literal `specie` in
    # the 6 in-repo profiles); we don't carry it on ThermoModelTags
    # because it's invariant across all observed cases. Verify it exists
    # (and is parseable) but don't store. If a future profile uses a
    # non-`specie` specie type, that's a meaningful divergence and a
    # carry-forward sub-DEC adds the field.
    specie_tok = _single_match_or_none(_THERMOTYPE_SPECIE_RE, thermotype_inner)
    if any(
        t is None
        for t in (type_tok, mixture_tok, transport_tok, thermo_tok,
                  eos_tok, energy_tok, specie_tok)
    ):
        return None
    # Cast for mypy: we just checked None above.
    assert type_tok is not None
    assert mixture_tok is not None
    assert transport_tok is not None
    assert thermo_tok is not None
    assert eos_tok is not None
    assert energy_tok is not None
    return ThermoModelTags(
        type=type_tok,
        mixture=mixture_tok,
        transport=transport_tok,
        thermo=thermo_tok,
        equation_of_state=eos_tok,
        energy=energy_tok,
    )


def _extract_specie_block(mixture_inner: str) -> dict[str, Any] | None:
    """Pull ``specie { molWeight … }`` sub-block from mixture body.

    Returns None when:
      - ``specie`` sub-block is absent or duplicate (ambiguous source),
      - the brace is unmatched,
      - ``molWeight`` is absent / duplicate / unparseable
        (REQUIRED key per DEC-V61-213 §Honest-omission).
    """
    if _count_nested_blocks(mixture_inner, "specie") != 1:
        return None
    span = _find_nested_block(mixture_inner, "specie")
    if span is None:
        return None
    body = _strip_nested_blocks(mixture_inner[span[0]:span[1]])
    mw_token = _single_match_or_none(_MOL_WEIGHT_RE, body)
    if mw_token is None:
        return None
    mw = _parse_float(mw_token)
    if mw is None:
        return None
    return {"molWeight": mw}


def _extract_thermodynamics_block(
    mixture_inner: str,
    thermo_kind: str,
) -> dict[str, Any] | None:
    """Pull ``thermodynamics { Cp … Hf … }`` sub-block from mixture body.

    Gated on ``thermo_kind == "hConst"`` (v0.1 scope-out for eConst).
    Returns None when:
      - ``thermodynamics`` block is absent or duplicate,
      - ``Cp`` is absent / duplicate / unparseable under hConst
        (REQUIRED key for hConst per advisor docstring shape).

    ``Hf`` is OPTIONAL — absent ⇒ omitted from output (not key=None).
    ``Tlow`` is INTENTIONALLY NOT extracted under hConst per
    DEC-V61-213 §Truth-chain R2 (hConst has no polynomial range —
    synthesizing a default would fabricate fictional advisor input).
    """
    if thermo_kind != "hConst":
        # v0.1 scope-out: eConst (uses Cv not Cp) and janaf (uses
        # highCpCoeffs/lowCpCoeffs) are documented NON-features.
        return None
    if _count_nested_blocks(mixture_inner, "thermodynamics") != 1:
        return None
    span = _find_nested_block(mixture_inner, "thermodynamics")
    if span is None:
        return None
    body = _strip_nested_blocks(mixture_inner[span[0]:span[1]])
    cp_token = _single_match_or_none(_CP_RE, body)
    if cp_token is None:
        return None
    cp = _parse_float(cp_token)
    if cp is None:
        return None
    out: dict[str, Any] = {"Cp": cp}
    # Cadence Codex R1 (2026-05-30 · CRS P3): distinguish "Hf absent
    # → optional omission" from "Hf present but ambiguous → honest
    # snapshot refusal". The value-capturing _HF_RE only matches
    # numeric Hf entries, so without the key-presence guard below,
    # duplicate (`Hf 0; Hf 1;`) or macro (`Hf $macro;`) entries fall
    # into the "absent" case and hide source ambiguity, violating the
    # v0.1 truth-chain/refusal contract. With it: key present in any
    # form ⇒ must single-match-numeric or snapshot refuses.
    hf_key_present = bool(_HF_KEY_PRESENCE_RE.search(body))
    if hf_key_present:
        hf_token = _single_match_or_none(_HF_RE, body)
        if hf_token is None:
            # Hf key is in the source but doesn't single-match a
            # numeric value: duplicate, $macro, #calc, or other
            # unparseable form. Honest refusal beats fabrication
            # (DEC-V61-211 R0 P2#2 pattern).
            return None
        hf = _parse_float(hf_token)
        if hf is None:
            # Defensive: regex matched a token but float() failed
            # (should be unreachable given _NUMERIC_VALUE pattern, but
            # belt-and-braces per DEC-V61-211 R0 P2#2).
            return None
        out["Hf"] = hf
    return out


def _extract_transport_block(
    mixture_inner: str,
    transport_kind: str,
) -> dict[str, Any] | None:
    """Pull ``transport { … }`` sub-block from mixture body.

    Branches on ``transport_kind``:
      - ``"sutherland"`` → ``{As: float, Ts: float}``; both REQUIRED.
        Either absent/unparseable ⇒ snapshot None (partial sutherland
        is a fabrication risk).
      - ``"const"``      → ``{mu: float, Pr: float}``; both REQUIRED.
        Same partial-refusal contract.
      - any other kind   → None (v0.1 scope-out).
    """
    if _count_nested_blocks(mixture_inner, "transport") != 1:
        return None
    span = _find_nested_block(mixture_inner, "transport")
    if span is None:
        return None
    body = _strip_nested_blocks(mixture_inner[span[0]:span[1]])

    if transport_kind == "sutherland":
        as_token = _single_match_or_none(_AS_RE, body)
        ts_token = _single_match_or_none(_TS_RE, body)
        if as_token is None or ts_token is None:
            return None
        as_val = _parse_float(as_token)
        ts_val = _parse_float(ts_token)
        if as_val is None or ts_val is None:
            return None
        return {"As": as_val, "Ts": ts_val}

    if transport_kind == "const":
        mu_token = _single_match_or_none(_MU_RE, body)
        pr_token = _single_match_or_none(_PR_RE, body)
        if mu_token is None or pr_token is None:
            return None
        mu_val = _parse_float(mu_token)
        pr_val = _parse_float(pr_token)
        if mu_val is None or pr_val is None:
            return None
        return {"mu": mu_val, "Pr": pr_val}

    # Other transport kinds (polynomial / logPolynomial / icoTabulated /
    # …) are documented v0.1 NON-features — return None.
    return None


def extract(case_dir: Path) -> tuple[Mapping[str, Any], ThermoModelTags] | None:
    """Read ``<case_dir>/constant/thermophysicalProperties`` → (snapshot, tags).

    Returns the 2-tuple ``(Mapping[str, Any], ThermoModelTags)`` on
    success, or ``None`` (honest "cannot construct a valid snapshot")
    when ANY of:
      - ``constant/thermophysicalProperties`` is missing,
      - the file is unreadable (``OSError``),
      - the ``thermoType { … }`` block is absent / duplicate / unparseable,
      - the ``mixture { … }`` block is absent / duplicate,
      - ``thermoType.thermo == eConst`` (v0.1 scope-out),
      - ``thermoType.transport`` is neither ``sutherland`` nor ``const``
        (v0.1 scope-out — polynomial/etc. NON-feature),
      - ``mixture.specie.molWeight`` is absent / duplicate / unparseable,
      - ``mixture.thermodynamics.Cp`` is absent / duplicate / unparseable
        under hConst (the REQUIRED key for the shape the advisor expects),
      - ``mixture.transport.{As, Ts}`` (sutherland) or
        ``mixture.transport.{mu, Pr}`` (const) is incomplete or
        unparseable (partial extracts are fabrication risk).

    Per DEC-V61-130/132, this function is **read-only** —
    ``Path.read_text`` is the only I/O; no writes, no route, no mutation.

    The returned snapshot is a single-species shape keyed by the
    sentinel ``"_mixture"`` (DEC-V61-213 §Truth-chain R1 — distinct
    from any real chemical species name). The advisor's
    ``_extract_species_tlows`` iterates ``dict.items()`` over the
    top-level keys; the sentinel produces an empty Tlow census on
    hConst input (Tlow absent — DEC-V61-213 §R2), which yields the
    correct ``is_clean=True`` advisor verdict.
    """
    path = case_dir / "constant" / "thermophysicalProperties"
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    body = _strip_comments(raw)

    # --- thermoType block ---
    if _count_top_level_blocks(body, "thermoType") != 1:
        return None
    tt_span = _find_top_level_block(body, "thermoType")
    if tt_span is None:
        return None
    tt_inner = body[tt_span[0]:tt_span[1]]
    tags = _extract_thermo_model_tags(tt_inner)
    if tags is None:
        return None

    # v0.1 scope-out: eConst (Cv not Cp), and non-pureMixture forms.
    if tags.thermo != "hConst":
        return None
    if tags.mixture != "pureMixture":
        # Multi-species mechanism shapes are out of v0.1 scope.
        return None

    # --- mixture block ---
    if _count_top_level_blocks(body, "mixture") != 1:
        return None
    mx_span = _find_top_level_block(body, "mixture")
    if mx_span is None:
        return None
    mx_inner = body[mx_span[0]:mx_span[1]]

    specie = _extract_specie_block(mx_inner)
    if specie is None:
        return None

    thermo = _extract_thermodynamics_block(mx_inner, tags.thermo)
    if thermo is None:
        return None

    transport = _extract_transport_block(mx_inner, tags.transport)
    if transport is None:
        return None

    snapshot: dict[str, Any] = {
        "_mixture": {
            "specie": specie,
            "thermodynamics": thermo,
            "transport": transport,
        }
    }
    return snapshot, tags

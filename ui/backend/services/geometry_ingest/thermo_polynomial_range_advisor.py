"""Reacting low-Mach pre-ignition T-floor advisor (A10).

Closes V41 (channel-(b) per-species Tlow patch incomplete — global-header
patch alone leaves 13/53 GRI-3.0 species at Tlow=300, igniting the v1
case_009 8.86M-warning flood) and V93 (the pre-ignition T-floor rule
``min(boundary fixedValue T) - safety_margin >= max(per-species Tlow)``).
Two distinct chemkinToFoam conversion-state failure modes on the same
case_009 substrate (v1 = failing / v1.5 = passing) satisfy the session-5
retro §9 promotion-gate consolidation: v1 + v1.5 dual-evidence is an
admissible substitute for the V25→A2-v2 "2 independent cases" convention
when the failure family is one converter's two-channel vulnerability.

Design choice — pure dict consumer (mirrors A4
:mod:`face_orientation_advisor`, A5 :mod:`inlet_outlet_validator`, and
A8 :mod:`shm_dict_validator`):

The advisor consumes a caller-parsed ``constant/thermo.compressibleGas``
dict and a caller-parsed ``0/T`` boundaryField dict. File parsing is
the caller's responsibility — typically via a thin ``foamDictionary``
adapter on the case directory. Keeping the file-IO boundary outside the
advisor:

* matches the A4 / A5 / A7 / A8 sibling pattern (pure dict in →
  dataclass report out, no runtime OpenFOAM dependency)
* makes the advisor unit-testable without OpenFOAM installed in CI
* lets the caller decide which on-disk form to authoritatively parse
  (case-local ``constant/thermo.compressibleGas`` vs in-memory template)

References:

- V41 in ``docs/openfoam_corpus/industrial_solver_findings_v_series.md``
  (case_009 v1 sediment · channel-(a) global-header patch)
- V91 in same corpus (case_009 v1 retroactive blind-verification ·
  Track C session 4 · flagged V41 as `[QUESTIONABLE 2026-05-14]`)
- V93 in same corpus (case_009 v1.5 cleanup · channel-(b) rule + canonical
  remediation tool ``patch_janaf_tlow.py``)
- Retro: ``.planning/retrospectives/2026-05-14_track_c_session_5_case_009_v1_5_reacting.md``
  §4 (A10 promotion-gate evaluation), §9 (paired before/after evidence)
- Parent sub-DEC: V61-198-sub-A10 (2026-05-14)
- Algorithm reference: ``~/Desktop/case_009_sandia_flame_d/v1_5/scripts/patch_janaf_tlow.py``
- Sibling validator pattern: ``face_orientation_advisor.py`` (A4),
  ``inlet_outlet_validator.py`` (A5), ``shm_dict_validator.py`` (A8)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CANONICAL_TLOW_FLOOR_K: float = 200.0
"""CHEMKIN / NIST-JANAF canonical low-end of NASA-7 polynomial validity.

The 13 GRI-3.0 species that bit case_009 v1 (N2, AR, CH3O, HCCO, HCCOH,
HCNN, HCNO, HNCO, HOCN, CH2CHO, H2CN, C3H7, C3H8) carry per-species
``G 300.000 ... 1000.000`` records inherited from older NIST polynomials,
overriding the patched global header. CHEMKIN's published canonical
floor is 200 K — most modern mech repositories ship with this baseline.
A species observed above this floor is a candidate for the V93
post-conversion sweep."""

DEFAULT_SAFETY_MARGIN_K: float = 5.0
"""V93 codified safety margin for the pre-ignition T-floor rule.

Rule: ``min(boundary fixedValue T) - safety_margin >= max(per-species
Tlow)``. The 5 K margin guards against PIMPLE inner-iteration numerical
noise — buoyancy-driven flow plus a finite-volume discretization can
drop a fraction of coflow cells fractionally below the boundary value,
firing the limiter at every chemistry source-term evaluation."""

CANONICAL_THERMO_KEYS: tuple[tuple[str, str], ...] = (
    # (canonical, parent_block). Parent block "<species>" means the key
    # sits directly under a species name (top-level of the thermo dict);
    # other blocks are nested under that.
    ("specie", "<species>"),
    ("thermodynamics", "<species>"),
    ("transport", "<species>"),
    ("equationOfState", "<species>"),
    ("elements", "<species>"),
    ("molWeight", "specie"),
    ("nMoles", "specie"),
    ("Tlow", "thermodynamics"),
    ("Thigh", "thermodynamics"),
    ("Tcommon", "thermodynamics"),
    ("highCpCoeffs", "thermodynamics"),
    ("lowCpCoeffs", "thermodynamics"),
    ("As", "transport"),
    ("Ts", "transport"),
    ("mu", "transport"),
    ("Pr", "transport"),
)
"""Canonical vocabulary worth fuzzy-matching for typo suspicion.

Drawn from OpenFOAM-ESI 2312 ``janafThermo<EquationOfState>`` dict
schema. Each entry is (canonical_key, parent_block_name) so a typo's
suggestion carries both the correct spelling AND the dict path it
belongs in (same disambiguation as ``shm_dict_validator.CANONICAL_KEYS``).
"""

_LEVENSHTEIN_MAX: int = 2
"""Fuzzy-match ceiling for typo suggestion (matches A8 default)."""

_MIN_KEY_LEN_FOR_FUZZY: int = 4
"""Skip fuzzy-match for keys shorter than this.

Without this guard, a 1-2 char user key (e.g. element symbol ``N`` inside
``elements: {N: 2, H: 4}``) sits within edit distance 2 of every 2-3 char
canonical (``As``, ``Ts``, ``mu``, ``Pr``), producing false-positive typo
findings on every species block. 4 chars is the shortest canonical worth
defending (``Tlow`` / ``Thigh``) — typos with len < 4 are too ambiguous
to surface a single confident suggestion."""


@dataclass(frozen=True)
class ThermoFinding:
    """One audit result for one thermo-range issue."""

    code: str          # "tlow_above_canonical" | "t_floor_breach" |
    #                    "internal_t_below_tlow" | "typo_suspicion"
    severity: str      # "warning" | "critical"
    location: str      # dict path, e.g. "N2.thermodynamics.Tlow"
    message: str
    species: str | None = None
    suggestion: str | None = None


@dataclass(frozen=True)
class SpeciesCoverage:
    """Distribution of per-species Tlow across the active mechanism.

    The three buckets cover the V41 / V93 diagnostic decomposition:

    * ``at_canonical_floor`` — Tlow == 200 K (CHEMKIN baseline)
    * ``above_canonical_to_300`` — 200 K < Tlow <= 300 K (the band V41
      claimed was empty but V91 measured 13/53 species in)
    * ``above_300`` — Tlow > 300 K (truly cold-fuel-incompatible — rare
      but possible for e.g. some F77 NASA-7 polynomials)
    """

    at_canonical_floor: int
    above_canonical_to_300: int
    above_300: int
    total_species_with_tlow: int


@dataclass(frozen=True)
class ThermoPolynomialRangeReport:
    """Outcome of :func:`check_thermo_polynomial_range`."""

    findings: tuple[ThermoFinding, ...]
    species_coverage: SpeciesCoverage
    max_species_tlow: float
    min_boundary_t: float

    @property
    def is_clean(self) -> bool:
        """True iff no critical or warning finding was produced."""
        return len(self.findings) == 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


def _levenshtein(a: str, b: str) -> int:
    """Standard iterative Levenshtein distance (no external dep)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]


def _suggest_for_unknown_key(key: str) -> str | None:
    """Return canonical suggestion if a known key is within edit distance.

    Short keys (< 4 chars) are skipped — too ambiguous against the
    2-3 char canonical short list. See ``_MIN_KEY_LEN_FOR_FUZZY``.
    """
    if len(key) < _MIN_KEY_LEN_FOR_FUZZY:
        return None
    best: tuple[int, str] | None = None
    for canonical, _block in CANONICAL_THERMO_KEYS:
        if canonical == key:
            return None
        if len(canonical) < _MIN_KEY_LEN_FOR_FUZZY:
            continue
        d = _levenshtein(key, canonical)
        if d <= _LEVENSHTEIN_MAX and (best is None or d < best[0]):
            best = (d, canonical)
    return best[1] if best is not None else None


def _walk_dict_keys(node: Any, path: str, out: list[tuple[str, str]]) -> None:
    """Recursively collect (key, full_path) pairs from a nested dict."""
    if not isinstance(node, dict):
        return
    for k, v in node.items():
        full_path = f"{path}.{k}" if path else str(k)
        out.append((str(k), full_path))
        _walk_dict_keys(v, full_path, out)


def _coerce_temperature(value: Any) -> float | None:
    """Coerce a janaf-dict numeric (Tlow, BC value) to float, or None.

    Accepts float, int, and bare strings like ``"294"`` or ``"uniform 294"``
    (the OpenFOAM ``boundaryField.<patch>.value uniform N`` convention).
    Anything non-coercible returns None so the caller can decide to skip.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("uniform"):
            s = s[len("uniform"):].strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _extract_species_tlows(
    janaf_thermo_dict: dict[str, Any],
) -> dict[str, float]:
    """Pull each top-level species' ``thermodynamics.Tlow`` out of the dict.

    Species without a coercible Tlow are silently dropped from the
    coverage census (matches A4's "missing actual_face_normal → skip"
    convention; the validator should not invent data).
    """
    tlows: dict[str, float] = {}
    for sp_name, sp_body in janaf_thermo_dict.items():
        if not isinstance(sp_body, dict):
            continue
        thermo = sp_body.get("thermodynamics")
        if not isinstance(thermo, dict):
            continue
        tlow = _coerce_temperature(thermo.get("Tlow"))
        if tlow is None:
            continue
        tlows[str(sp_name)] = tlow
    return tlows


def _extract_boundary_temperatures(
    boundary_conditions: dict[str, Any] | None,
) -> tuple[list[tuple[str, float]], float | None]:
    """Pull (patch_name, T_value) tuples for every fixedValue T patch.

    Also returns the internalField T (if present). Patches without
    ``type == fixedValue`` (e.g. ``zeroGradient``, ``inletOutlet``) are
    silently dropped — only fixedValue patches drive the V93 rule.

    The advisor accepts the canonical OpenFOAM ``0/T`` shape::

        internalField: uniform 300.0
        boundaryField:
          fuel_jet:
            type: fixedValue
            value: 294.0
          coflow_air:
            type: fixedValue
            value: uniform 291.0
          wall:
            type: zeroGradient   # ignored — not fixedValue

    A flat shape (no ``boundaryField`` wrapper, just patch_name →
    {type, value}) is also tolerated so callers can pass a sliced dict.
    """
    if not isinstance(boundary_conditions, dict):
        return [], None

    internal_t = _coerce_temperature(boundary_conditions.get("internalField"))

    bf = boundary_conditions.get("boundaryField")
    if not isinstance(bf, dict):
        # Fallback: treat the whole dict as patch_name → {type, value}
        # (excluding the internalField key we already consumed).
        bf = {
            k: v
            for k, v in boundary_conditions.items()
            if k != "internalField" and isinstance(v, dict)
        }

    patches: list[tuple[str, float]] = []
    for patch_name, patch_body in bf.items():
        if not isinstance(patch_body, dict):
            continue
        if patch_body.get("type") != "fixedValue":
            continue
        t_val = _coerce_temperature(patch_body.get("value"))
        if t_val is None:
            continue
        patches.append((str(patch_name), t_val))
    return patches, internal_t


def check_thermo_polynomial_range(
    janaf_thermo_dict: dict[str, Any],
    boundary_conditions: dict[str, Any] | None = None,
    *,
    safety_margin_k: float = DEFAULT_SAFETY_MARGIN_K,
    canonical_tlow_floor_k: float = CANONICAL_TLOW_FLOOR_K,
) -> ThermoPolynomialRangeReport:
    """Audit a parsed ``constant/thermo.compressibleGas`` against V41 + V93.

    Expected ``janaf_thermo_dict`` shape (subset; only fields read here
    are documented):

    .. code-block:: yaml

       N2:
         specie:
           molWeight: 28.0134
         thermodynamics:
           Tlow: 300         # V41 / V93 target field
           Thigh: 5000
           Tcommon: 1000
           highCpCoeffs: [...]
           lowCpCoeffs: [...]
         transport:
           As: 1.4584e-06
           Ts: 110.4
         equationOfState: {}
       AR:
         ...

    Expected ``boundary_conditions`` shape (subset): canonical OpenFOAM
    ``0/T`` dict with optional ``internalField`` and ``boundaryField``.
    ``None`` disables path (b) / internalField check (paths (a), (c),
    (d) still run on the thermo dict alone).

    Detection logic:

    (a) **Tlow above canonical floor** — for each species with
        ``Tlow > canonical_tlow_floor_k``, emit ``tlow_above_canonical``
        warning. This catches the V41 channel-(b) state independent of
        what the boundary conditions look like (e.g. an LES case where
        BCs happen to be ≥ 300 still surfaces the partial-patch flag).

    (b) **Pre-ignition T-floor breach** — V93 codified rule. If
        ``max(species Tlow) > min(fixedValue T) - safety_margin_k``,
        emit a single ``t_floor_breach`` critical naming the offending
        species + patch + numeric gap. Skip silently if no fixedValue
        patches are present (caller can't supply a check).

    (c) **internalField T below max(species Tlow)** — companion check
        for (b). If ``internalField`` is set and falls below
        ``max(species Tlow) - safety_margin_k``, emit
        ``internal_t_below_tlow`` critical. Catches the case where
        boundary conditions are well-conditioned but the cold-start
        internal field would still trip the limiter at t=0.

    (d) **Typo suspicion** — fuzzy match every key under any species
        block against ``CANONICAL_THERMO_KEYS``; edit distance ≤ 2 with
        a non-canonical key emits ``typo_suspicion`` warning. Mirrors
        the A8 pattern.

    Missing / sliced inputs (no species blocks, no boundary_conditions,
    empty thermodynamics) are silently skipped — the dict may be partial
    in a pre-flight UI snapshot.
    """
    findings: list[ThermoFinding] = []

    # --- Extract species Tlow census --------------------------------------
    species_tlows = _extract_species_tlows(janaf_thermo_dict)
    max_species_tlow = max(species_tlows.values(), default=0.0)

    # --- Extract boundary fixedValue T list -------------------------------
    bc_patches, internal_t = _extract_boundary_temperatures(boundary_conditions)
    bc_values = [t for _name, t in bc_patches]
    if internal_t is not None:
        bc_values.append(internal_t)
    min_boundary_t = min(bc_values) if bc_values else 0.0

    # --- Path (a): per-species Tlow > canonical floor ---------------------
    species_above_floor: list[str] = []
    for sp_name, tlow in species_tlows.items():
        if tlow > canonical_tlow_floor_k:
            species_above_floor.append(sp_name)
            findings.append(
                ThermoFinding(
                    code="tlow_above_canonical",
                    severity="warning",
                    location=f"{sp_name}.thermodynamics.Tlow",
                    message=(
                        f"species '{sp_name}' carries Tlow={tlow:g} K, above "
                        f"canonical {canonical_tlow_floor_k:g} K floor — "
                        "post-conversion sweep (V93 patch_janaf_tlow.py) is "
                        "the canonical remediation"
                    ),
                    species=sp_name,
                    suggestion=(
                        f"lower Tlow to {canonical_tlow_floor_k:g}; the "
                        "underlying NASA-7 polynomial is typically fitted "
                        "from 200 K and extrapolation cost is <1% cp(T) "
                        "error for diatomics, exact for monatomics"
                    ),
                )
            )

    # --- Path (b): V93 pre-ignition T-floor breach ------------------------
    if bc_patches and species_tlows:
        # Find the offending (species, patch) pair with the worst gap.
        # Single critical finding suffices — the engineer's first action
        # is to run patch_janaf_tlow.py, not to triage per-pair.
        offender_patch, offender_t = min(bc_patches, key=lambda x: x[1])
        # Worst-case species = species with max Tlow
        offender_species = max(species_tlows, key=lambda s: species_tlows[s])
        offender_tlow = species_tlows[offender_species]
        gap = offender_t - safety_margin_k - offender_tlow
        if gap < 0.0:
            findings.append(
                ThermoFinding(
                    code="t_floor_breach",
                    severity="critical",
                    location=f"boundaryField.{offender_patch}.value",
                    message=(
                        f"V93 pre-ignition T-floor rule violated: "
                        f"min(BC T) = {offender_t:g} K on patch "
                        f"'{offender_patch}' minus safety_margin "
                        f"{safety_margin_k:g} K = "
                        f"{offender_t - safety_margin_k:g} K, but "
                        f"max(per-species Tlow) = {offender_tlow:g} K on "
                        f"species '{offender_species}' (gap {gap:g} K). "
                        f"janafThermo limit warnings will flood the log "
                        "at every chemistry source-term evaluation; "
                        "ignite-stage wall-clock dominated by stderr I/O"
                    ),
                    species=offender_species,
                    suggestion=(
                        "run patch_janaf_tlow.py on constant/thermo."
                        f"compressibleGas to lower Tlow → "
                        f"{canonical_tlow_floor_k:g} K; alternatively "
                        f"raise '{offender_patch}' fixedValue above "
                        f"{offender_tlow + safety_margin_k:g} K (band-aid)"
                    ),
                )
            )

    # --- Path (c): internalField T below max(species Tlow) ----------------
    if internal_t is not None and species_tlows:
        if internal_t < max_species_tlow - safety_margin_k:
            findings.append(
                ThermoFinding(
                    code="internal_t_below_tlow",
                    severity="critical",
                    location="internalField",
                    message=(
                        f"internalField T = {internal_t:g} K is below "
                        f"max(per-species Tlow) {max_species_tlow:g} K minus "
                        f"safety_margin {safety_margin_k:g} K = "
                        f"{max_species_tlow - safety_margin_k:g} K. The "
                        "cold-start field will trip janafThermo limit "
                        "at t=0 across the whole domain"
                    ),
                    species=None,
                    suggestion=(
                        f"either raise internalField above "
                        f"{max_species_tlow + safety_margin_k:g} K or run "
                        "patch_janaf_tlow.py to lower per-species Tlow"
                    ),
                )
            )

    # --- Path (d): typo suspicion fuzzy match -----------------------------
    canonical_set = {k for k, _ in CANONICAL_THERMO_KEYS}
    seen_typo_paths: set[str] = set()
    for sp_name, sp_body in janaf_thermo_dict.items():
        if not isinstance(sp_body, dict):
            continue
        walked: list[tuple[str, str]] = []
        _walk_dict_keys(sp_body, str(sp_name), walked)
        for key, full_path in walked:
            if key in canonical_set:
                continue
            suggestion = _suggest_for_unknown_key(key)
            if suggestion is None:
                continue
            if full_path in seen_typo_paths:
                continue
            seen_typo_paths.add(full_path)
            findings.append(
                ThermoFinding(
                    code="typo_suspicion",
                    severity="warning",
                    location=full_path,
                    message=(
                        f"key '{key}' resembles canonical '{suggestion}' "
                        f"(edit distance ≤ {_LEVENSHTEIN_MAX}) — likely typo"
                    ),
                    species=str(sp_name),
                    suggestion=suggestion,
                )
            )

    # --- Path (d'): species coverage census -------------------------------
    at_floor = 0
    above_floor_to_300 = 0
    above_300 = 0
    for tlow in species_tlows.values():
        if tlow <= canonical_tlow_floor_k:
            at_floor += 1
        elif tlow <= 300.0:
            above_floor_to_300 += 1
        else:
            above_300 += 1
    coverage = SpeciesCoverage(
        at_canonical_floor=at_floor,
        above_canonical_to_300=above_floor_to_300,
        above_300=above_300,
        total_species_with_tlow=len(species_tlows),
    )

    return ThermoPolynomialRangeReport(
        findings=tuple(findings),
        species_coverage=coverage,
        max_species_tlow=max_species_tlow,
        min_boundary_t=min_boundary_t,
    )

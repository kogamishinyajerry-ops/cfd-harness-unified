"""BC-type-name validity advisor (D10).

Detects ``boundaryField`` BC type names that are absent from the active
OpenFOAM fork's BC registry — the foam-extend-vs-ESI mismatch class
surfaced by V29 (M-STACK-TRACK-3 §gap2, case_006 ONERA M6 transonic,
sedimented 2026-05-14). The case_006 ``parts_manifest`` declares
``characteristicPressureInletOutletPressure`` and
``characteristicVelocityInletOutletVelocity`` on its three far-field
parts; both names are valid in foam-extend but **do not exist** in the
project's default Docker image (``opencfd/openfoam-default:2312``,
OpenFOAM-ESI). The solver would crash at boundary-field construction
time with ``not found in valid types``, but the LANDED A5
``inlet_outlet_validator`` short-circuits on ``role`` and never inspects
the ``bc:`` block — so the stack was silent on six BC-name declarations
that would force a runtime crash.

D10 closes that gap with a fork-aware catalog lookup: each declared BC
type name is classified as ``valid_standard`` (present in the active
fork), ``valid_foam_extend_only`` (present in foam-extend, absent in
ESI mainline), ``valid_sentinel`` (project-internal placeholder, never
emitted by OpenFOAM), or ``unknown`` (likely typo or unsupported user-
custom BC). The verdict + active fork together pick the severity.

Design choice — pure dict consumer (mirrors A5
``inlet_outlet_validator`` / A8 ``shm_dict_validator`` / A10
``thermo_polynomial_range_advisor`` / D6 ``extra_body_advisor``):

The advisor consumes a ``bc_specs`` list whose entries already carry
the per-part BC type names extracted from a ``parts_manifest``,
``boundary`` dict, or other upstream source. Catalog lookup is pure
string set membership — no FreeCAD, no OpenFOAM, no LLM dependency.

Three classification tiers + four severity rules:

(1) ``valid_standard`` — BC name is in ``STANDARD_OPENFOAM_BCS`` (the
    OpenFOAM ESI mainline registry subset this advisor covers).
    Severity: ``pass`` — no finding emitted.

(2) ``valid_foam_extend_only`` — BC name is in
    ``FOAM_EXTEND_ONLY_BCS`` and NOT in ``STANDARD_OPENFOAM_BCS``.
    Severity:
      * ``fork='main'`` (default) → **critical** — solver will crash.
      * ``fork='foam-extend'`` → **info** (tolerant) — expected on
        foam-extend; emit a passing note only when an explicit advisory
        is requested via caller, otherwise silent.
      * ``fork='unknown'`` → **warning** — caller should disambiguate.

(3) ``valid_sentinel`` — BC name is in ``SENTINEL_BC_NAMES``
    (project-internal placeholders such as ``none_volume_reference``,
    meaning "this body is a volume reference / no BC applies").
    Severity: ``info`` (silently passed; no finding).

(4) ``unknown`` — BC name is in NONE of the catalogs. Severity:
    ``warning`` (under any fork). Most-likely cause is a typo
    (``fixedValue`` → ``fixedValeu``) or a user-coded BC that the
    advisor's catalog hasn't been taught about. The caller surfaces
    the suggestion to extend the catalog rather than silently passing.

Anti-scope (per M-STACK-TRACK-3 §gap2 + V62-A-charter):

- does NOT check BC *value* numeric validity (e.g., negative
  ``totalPressure``, or ``flowRateInletVelocity volumetricFlowRate``
  out-of-range). Value-range validation is a separate advisor class
  (A10-thermo-range is the only such advisor currently LANDED).
- does NOT check BC *consistency* across coupled fields (e.g., did
  the user declare ``fixedValue`` on ``U`` but ``zeroGradient`` on ``p``
  in a way that violates the SIMPLE / PIMPLE algorithm contract). That
  is V19 / V11 territory and properly belongs to a per-field-pair
  checker advisor, not this catalog-based name validator.
- does NOT check ``patch type`` (``boundary`` file ``type wall;`` /
  ``patch;`` / ``symmetryPlane;``). That is sHM dict territory (A8).
- does NOT detect patch-geometry / inlet-outlet topology mistakes —
  A5 ``inlet_outlet_validator`` is the SSOT for that. **D10 supplements
  A5; it does not replace A5.** A5 reads ``role:`` and inspects topology;
  D10 reads ``bc:`` and inspects the literal type name.
- does NOT mutate any case directory. V130 advisor-not-driver: the
  advisor only ever returns a frozen report; the caller decides what
  to do.

References:

- V29 in ``docs/openfoam_corpus/industrial_solver_findings_v_series.md``
  (case_006 ONERA M6 transonic · 2026-05-14 · canonical evidence row:
  ESI v2312 lacks ``characteristicPressureInletOutletPressure`` /
  ``characteristicVelocityInletOutletVelocity`` BC types)
- M-STACK-TRACK-3 retro
  ``.planning/retrospectives/2026-05-14_stack_track_c_session_3_case_006.md``
  §5 row V29 (D-class candidate `bc_type_name_validity_advisor`) +
  §7 item 2 (D-class promotion path) + §9 item 3 (~120 LOC advisor +
  catalog + 6-8 tests · sub-DEC scope)
- Parent sub-DEC: ``DEC-V62-A-sub-D10-bc-type-validity`` (this advisor)
- Sibling validator pattern: D6 ``extra_body_advisor.py``
  (single-case land precedent · [QUESTIONABLE] marker pending ≥2-case
  cross-validation)
- A2 v1 single-case-land precedent (advisor LANDED on one case;
  promoted to [VALIDATED] only after a 2nd-case sediment confirms)

Catalog provenance:

- ``STANDARD_OPENFOAM_BCS`` — derived from OpenFOAM-ESI v2412
  documentation (https://www.openfoam.com/documentation/guides/v2412/doc/)
  Boundary Conditions section + cross-checked against
  ``openfoam-default:2312`` Docker image (case_006 substrate's default).
  Covers the patchField subclasses an industrial CFD case will most
  likely encounter; intentionally NOT exhaustive — OpenFOAM has 200+
  registered BCs and the advisor's value is catching foam-extend
  mismatches and typos, not enforcing a closed registry.
- ``FOAM_EXTEND_ONLY_BCS`` — derived from foam-extend-5.0 release
  (https://sourceforge.net/p/foam-extend/foam-extend-5.0/) +
  case_006 retro V29 enumeration. Covers the ``characteristic*`` BC
  family that ESI deprecated in favor of ``freestream`` /
  ``waveTransmissive``.
- ``SENTINEL_BC_NAMES`` — project-internal placeholders observed in
  ``case_006/inputs/parts_manifest.yaml`` and sibling case profiles.

Catalog policy: additions are append-only. Removing an entry from
``STANDARD_OPENFOAM_BCS`` would silently flip a passing case to
``unknown`` → ``warning``; removals therefore require a sub-DEC.
Adding a foam-extend-only name to ``STANDARD_OPENFOAM_BCS`` (i.e.,
asserting it's been backported to ESI) requires citing the ESI release
notes in the commit message that flips it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


# ---- Catalogs --------------------------------------------------------------

STANDARD_OPENFOAM_BCS: frozenset[str] = frozenset({
    # --- Core patchField subclasses (value/gradient/mixed) ---
    "calculated",                                       # case_011 v5b · case_016 m219 · ESI v2412 mainline
    "empty",                                            # ESI v2412 mainline · fvPatchField/basic
    "fixedGradient",                                    # ESI v2412 mainline · fvPatchField/basic
    "fixedValue",                                       # case_011 v5b · ESI v2412 mainline
    "mixed",                                            # ESI v2412 mainline · fvPatchField/basic
    "uniformFixedValue",                                # ESI v2412 mainline · derivedFvPatchFields
    "uniformFixedGradient",                             # ESI v2412 mainline · derivedFvPatchFields
    "uniformMixed",                                     # ESI v2412 mainline · derivedFvPatchFields
    "uniformInletOutlet",                               # ESI v2412 mainline · derivedFvPatchFields
    "zeroGradient",                                     # case_006 · case_011 · case_016 · ESI v2412 mainline
    "fixedMean",                                        # ESI v2412 mainline · derivedFvPatchFields
    "fixedMeanOutletInlet",                             # ESI v2412 mainline · derivedFvPatchFields
    # --- Geometric constraints ---
    "cyclic",                                           # ESI v2412 mainline · constraint
    "cyclicAMI",                                        # ESI v2412 mainline · constraint
    "cyclicACMI",                                       # ESI v2412 mainline · constraint
    "cyclicSlip",                                       # ESI v2412 mainline · constraint
    "cyclicPeriodicAMI",                                # ESI v2412 mainline · constraint
    "nonuniformTransformCyclic",                        # ESI v2412 mainline · constraint
    "jumpCyclic",                                       # ESI v2412 mainline · derived · jump-discontinuity cyclic
    "jumpCyclicAMI",                                    # ESI v2412 mainline · derived · jump-discontinuity AMI
    "processor",                                        # ESI v2412 mainline · constraint
    "processorCyclic",                                  # ESI v2412 mainline · constraint
    "slip",                                             # case_011 v5b · ESI v2412 mainline · constraint
    "noSlip",                                           # case_006 · ESI v2412 mainline · derived
    "partialSlip",                                      # ESI v2412 mainline · derivedFvPatchFields/partialSlip
    "fixedNormalSlip",                                  # ESI v2412 mainline · derivedFvPatchFields
    "symmetry",                                         # case_006 · ESI v2412 mainline · constraint
    "symmetryPlane",                                    # ESI v2412 mainline · constraint
    "wedge",                                            # ESI v2412 mainline · constraint
    "wall",                                             # ESI v2412 mainline · base patchType
    # --- Inlet / outlet families ---
    "inletOutlet",                                      # case_011 · case_016 · ESI v2412 mainline
    "outletInlet",                                      # ESI v2412 mainline · derived
    "advective",                                        # ESI v2412 mainline · derived
    "fanPressure",                                      # ESI v2412 mainline · derived
    "fixedFluxPressure",                                # case_011 v5b · ESI v2412 mainline · derived
    "fixedProfile",                                     # ESI v2412 mainline · derived
    "flowRateInletVelocity",                            # case_011 v5b · ESI v2412 mainline · derived
    "flowRateOutletVelocity",                           # ESI v2412 mainline · derived
    "mappedFixed",                                      # ESI v2412 mainline · derived
    "mappedFixedValue",                                 # ESI v2412 mainline · derived
    "mappedField",                                      # ESI v2412 mainline · derived
    "mappedFlowRate",                                   # ESI v2412 mainline · derived
    "mappedMixed",                                      # ESI v2412 mainline · derived
    "mappedVelocityFlux",                               # ESI v2412 mainline · derived
    "pressureDirectedInletOutletVelocity",              # ESI v2412 mainline · derived
    "pressureDirectedInletVelocity",                    # ESI v2412 mainline · derived
    "pressureInletOutletVelocity",                      # case_011 v5b · ESI v2412 mainline · derived
    "pressureInletOutletParSlipVelocity",               # ESI v2412 mainline · derived (parallel-slip variant)
    "pressureInletUniformVelocity",                     # ESI v2412 mainline · derived
    "pressureInletVelocity",                            # ESI v2412 mainline · derived
    "pressureNormalInletOutletVelocity",                # ESI v2412 mainline · derived
    "pressureOutlet",                                   # ESI v2412 mainline · derived
    "fixedNormalInletOutletVelocity",                   # ESI v2412 mainline · derived
    "entrainmentPressure",                              # ESI v2412 mainline · derived
    "syringePressure",                                  # ESI v2412 mainline · derived
    "inletOutletTotalTemperature",                      # ESI v2412 mainline · compressible derived
    "surfaceNormalFixedValue",                          # ESI v2412 mainline · derived
    "swirlFlowRateInletVelocity",                       # ESI v2412 mainline · derived
    "swirlInletVelocity",                               # ESI v2412 mainline · derived
    "timeVaryingMappedFixedValue",                      # ESI v2412 mainline · derived
    "turbulentInlet",                                   # ESI v2412 mainline · derived
    "turbulentDFSEMInlet",                              # ESI v2412 mainline · LES synthetic-eddy inlet
    "turbulentDigitalFilterInlet",                      # ESI v2412 mainline · LES digital-filter inlet
    "turbulentMixingLengthDissipationRateInlet",        # ESI v2412 mainline · turbulence-inlet helper
    "turbulentMixingLengthFrequencyInlet",              # ESI v2412 mainline · turbulence-inlet helper
    "totalPressure",                                    # ESI v2412 mainline · derived
    "totalTemperature",                                 # ESI v2412 mainline · derived
    "prghPressure",                                     # ESI v2412 mainline · multiphase derived
    "prghTotalPressure",                                # ESI v2412 mainline · multiphase derived
    "prghTotalHydrostaticPressure",                     # ESI v2412 mainline · multiphase derived
    "variableHeightFlowRate",                           # ESI v2412 mainline · multiphase derived
    "variableHeightFlowRateInletVelocity",              # ESI v2412 mainline · multiphase derived
    # --- Compressible / far-field (ESI replacements for foam-extend characteristic*) ---
    "freestream",                                       # case_006 · case_016 · ESI v2412 mainline · compressible
    "freestreamPressure",                               # case_016 m219 · ESI v2412 mainline · compressible
    "freestreamVelocity",                               # ESI v2412 mainline · compressible
    "supersonicFreestream",                             # ESI v2412 mainline · compressible/derived
    "waveTransmissive",                                 # case_016 m219 · ESI v2412 mainline · compressible
    # --- ABL / atmospheric ---
    "atmBoundaryLayerInletVelocity",                    # ESI v2412 mainline · atmosphericModels
    "atmBoundaryLayerInletK",                           # ESI v2412 mainline · atmosphericModels
    "atmBoundaryLayerInletEpsilon",                     # ESI v2412 mainline · atmosphericModels
    "atmBoundaryLayerInletOmega",                       # ESI v2412 mainline · atmosphericModels
    "atmTurbulentHeatFluxTemperature",                  # ESI v2412 mainline · atmosphericModels
    "atmAlphatkWallFunction",                           # ESI v2412 mainline · atmosphericModels
    "atmEpsilonWallFunction",                           # ESI v2412 mainline · atmosphericModels
    "atmNutkWallFunction",                              # ESI v2412 mainline · atmosphericModels
    "atmNutUWallFunction",                              # ESI v2412 mainline · atmosphericModels
    "atmNutWallFunction",                               # ESI v2412 mainline · atmosphericModels
    "atmOmegaWallFunction",                             # ESI v2412 mainline · atmosphericModels
    # --- Turbulence wall functions ---
    "epsilonWallFunction",                              # ESI v2412 mainline · RAS wallFunctions
    "fWallFunction",                                    # ESI v2412 mainline · v2-f model
    "kLowReWallFunction",                               # ESI v2412 mainline · RAS wallFunctions
    "kqRWallFunction",                                  # case_006 · case_016 · ESI v2412 mainline
    "nutLowReWallFunction",                             # ESI v2412 mainline · RAS wallFunctions
    "nutUSpaldingWallFunction",                         # case_006 · case_016 · ESI v2412 mainline
    "nutUTabulatedWallFunction",                        # ESI v2412 mainline · RAS wallFunctions
    "nutUWallFunction",                                 # ESI v2412 mainline · RAS wallFunctions
    "nutUBlendedWallFunction",                          # ESI v2412 mainline · RAS wallFunctions
    "nutkAtmRoughWallFunction",                         # ESI v2412 mainline · RAS wallFunctions
    "nutkRoughWallFunction",                            # ESI v2412 mainline · RAS wallFunctions
    "nutkWallFunction",                                 # ESI v2412 mainline · RAS wallFunctions
    "omegaWallFunction",                                # case_006 · case_016 · ESI v2412 mainline
    "v2WallFunction",                                   # ESI v2412 mainline · v2-f model
    # --- Wall velocities (moving / rotating / translating) ---
    "movingWallVelocity",                               # ESI v2412 mainline · derived (dynamic mesh)
    "rotatingWallVelocity",                             # ESI v2412 mainline · derived
    "translatingWallVelocity",                          # ESI v2412 mainline · derived
    # --- Thermal / CHT (heatTransfer + compressible namespaces) ---
    "alphatJayatillekeWallFunction",                    # ESI v2412 mainline · CHT thermal wallFunction
    "alphatWallFunction",                               # ESI v2412 mainline · CHT thermal wallFunction
    "compressible::alphatJayatillekeWallFunction",      # ESI v2412 mainline · compressible::ns mirror
    "compressible::alphatWallFunction",                 # case_016 m219 · ESI v2412 mainline · compressible::ns
    "compressible::epsilonWallFunction",                # ESI v2412 mainline · compressible::ns mirror
    "compressible::kqRWallFunction",                    # ESI v2412 mainline · compressible::ns mirror
    "compressible::omegaWallFunction",                  # ESI v2412 mainline · compressible::ns mirror
    "compressible::nutkWallFunction",                   # ESI v2412 mainline · compressible::ns mirror
    "compressible::nutkRoughWallFunction",              # ESI v2412 mainline · compressible::ns mirror
    "compressible::nutUSpaldingWallFunction",           # ESI v2412 mainline · compressible::ns mirror
    "compressible::nutUWallFunction",                   # ESI v2412 mainline · compressible::ns mirror
    "compressible::nutLowReWallFunction",               # ESI v2412 mainline · compressible::ns mirror
    "compressible::turbulentTemperatureCoupledBaffleMixed",  # case_011 v5b · ESI v2412 mainline · CHT region-coupling
    "compressible::turbulentTemperatureRadCoupledMixed",     # ESI v2412 mainline · CHT + radiation coupling
    "externalWallHeatFluxTemperature",                  # ESI v2412 mainline · derived CHT
    "humidityTemperatureCoupledMixed",                  # ESI v2412 mainline · humidity-coupled CHT
    "turbulentHeatFluxTemperature",                     # ESI v2412 mainline · derived
    # --- Radiation BCs (CHT extensions) ---
    "MarshakRadiation",                                 # ESI v2412 mainline · radiationModels
    "MarshakRadiationFixedTemperature",                 # ESI v2412 mainline · radiationModels
    "greyDiffusiveRadiation",                           # ESI v2412 mainline · radiationModels
    "greyDiffusiveRadiationViewFactor",                 # ESI v2412 mainline · radiationModels viewFactor solver
    "wideBandDiffusiveRadiation",                       # ESI v2412 mainline · fvDOM/wideBand
    "fixedIncidentRadiation",                           # ESI v2412 mainline · radiationModels
    # --- Multiphase / VOF / contact-angle ---
    "alphaContactAngle",                                # ESI v2412 mainline · multiphase contact-angle base
    "constantAlphaContactAngle",                        # ESI v2412 mainline · multiphase
    "dynamicAlphaContactAngle",                         # ESI v2412 mainline · multiphase
    "temperatureDependentContactAngle",                 # ESI v2412 mainline · multiphase
    "timeVaryingAlphaContactAngle",                     # ESI v2412 mainline · multiphase
    "waveSurfacePressure",                              # ESI v2412 mainline · waveModels
    "waveVelocity",                                     # ESI v2412 mainline · waveModels
    "waveDisplacement",                                 # ESI v2412 mainline · dynamicMesh
    # --- Coded / programmable ---
    "codedFixedValue",                                  # ESI v2412 mainline · coded BCs
    "codedMixed",                                       # ESI v2412 mainline · coded BCs
})
"""OpenFOAM-ESI mainline patchField type names (subset · v2412 baseline).

Intentionally non-exhaustive (OpenFOAM ships 200+ BCs); the advisor's
value is catching the foam-extend-vs-ESI mismatch surfaced by V29 plus
common typos, not enforcing closure over a moving registry.

V63-A Tier 1 catalog audit (sub-DEC DEC-V63-A-sub-M-D10-CATALOG-AUDIT ·
2026-05-14) expanded this set from 80 → 138 entries (case-evidence from
case_006 / case_011 v5b / case_016 m219 BC names + ESI v2412 mainline
documented BCs · wall-velocity / radiation / multiphase / atmospheric
wall functions / LES inlets / compressible::ns mirrors). Catalog policy
remains append-only; no entries removed.
"""


FOAM_EXTEND_ONLY_BCS: frozenset[str] = frozenset({
    # The case_006 V29 evidence row · foam-extend-5.0 characteristic* family.
    # ESI mainline replaced these with freestream / waveTransmissive
    # circa OpenFOAM-3.x.
    "characteristicPressureInletOutletPressure",
    "characteristicVelocityInletOutletVelocity",
    "characteristicTemperatureInletOutletTemperature",
    "characteristicScalarInletOutlet",
    "characteristicWaveTransmissivePressure",
    "characteristicWaveTransmissiveVelocity",
})
"""BC type names that exist in foam-extend but NOT in OpenFOAM-ESI.

A solver compiled against ``opencfd/openfoam-default:*`` will fail
boundary-field construction with ``not found in valid types`` when
any of these is declared in a ``boundaryField`` block.
"""


SENTINEL_BC_NAMES: frozenset[str] = frozenset({
    # Project-internal placeholders meaning "no BC applies to this body".
    # Observed in case_006 parts_manifest farfield_reference body.
    "none",
    "none_volume_reference",
    "n/a",
    "na",
    "placeholder",
})
"""Project-internal sentinel strings used where a real BC would normally
go. The advisor must NOT flag these as ``unknown`` — they are valid
intent markers (the case author declaring "this body is a volume
reference body, no actual patch BC is emitted")."""


# ---- Dataclasses -----------------------------------------------------------

Fork = Literal["main", "foam-extend", "unknown"]


@dataclass(frozen=True)
class ValidityVerdict:
    """Outcome of one ``check_bc_type_name_validity`` call.

    ``verdict`` is the catalog tier; ``severity`` is what the caller
    should report given the active fork; ``suggested_fix`` is a best-
    effort hint when the BC is foam-extend-only or an obvious typo.
    """

    bc_type_name: str
    verdict: str                # "valid_standard" | "valid_foam_extend_only" | "valid_sentinel" | "unknown"
    severity: str               # "pass" | "info" | "warning" | "critical"
    fork: Fork
    suggested_fix: str | None


@dataclass(frozen=True)
class BcTypeNameFinding:
    """One BC-name finding for one (part, field) pair."""

    part_name: str
    field_name: str             # "U" / "p" / "T" / "nut" / "k" / "omega" / ...
    bc_type_name: str           # the BC name as declared
    verdict: str                # same vocabulary as ValidityVerdict
    severity: str               # "warning" | "critical"  (pass/info findings are NOT emitted)
    fork: Fork
    suggested_fix: str | None
    detail: str


@dataclass(frozen=True)
class BcTypeNameReport:
    """Outcome of :func:`detect_invalid_bc_types`."""

    findings: tuple[BcTypeNameFinding, ...]
    checked_count: int          # number of (part, field) BC declarations evaluated
    parts_examined: int         # number of bc_specs entries iterated
    fork: Fork

    @property
    def is_clean(self) -> bool:
        """True iff no warning/critical finding was emitted."""
        return len(self.findings) == 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


# ---- Suggested-fix table --------------------------------------------------

_FOAM_EXTEND_TO_ESI_HINT: dict[str, str] = {
    "characteristicPressureInletOutletPressure":
        "Substitute 'freestreamPressure' (ESI canonical far-field "
        "pressure) or 'waveTransmissive' (ESI canonical upwind/downwind "
        "transmissive). See V29 evidence row.",
    "characteristicVelocityInletOutletVelocity":
        "Substitute 'freestream' (auto-direction-detecting flow per "
        "ESI canonical far-field velocity). See V29 evidence row.",
    "characteristicTemperatureInletOutletTemperature":
        "Substitute 'freestream' with 'freestreamValue uniform T_inf' "
        "(ESI canonical far-field temperature). See V29 evidence row.",
    "characteristicScalarInletOutlet":
        "Substitute 'inletOutlet' (ESI canonical scalar reversal-aware "
        "BC) or a field-specific freestream variant.",
    "characteristicWaveTransmissivePressure":
        "Substitute 'waveTransmissive' (ESI direct equivalent).",
    "characteristicWaveTransmissiveVelocity":
        "Substitute 'waveTransmissive' (ESI direct equivalent).",
}


# ---- Public API ------------------------------------------------------------


def check_bc_type_name_validity(
    bc_type_name: str,
    fork: Fork = "main",
) -> ValidityVerdict:
    """Look up a single BC type name in the fork-aware catalog.

    Args:
        bc_type_name: the BC name as declared in a ``boundaryField``
            block. Whitespace is stripped; non-string inputs raise.
        fork: which OpenFOAM fork the case targets. ``'main'`` is the
            project's default (ESI v2312 Docker image); ``'foam-extend'``
            relaxes the ``characteristic*`` family to ``valid_standard``-
            severity-equivalent; ``'unknown'`` treats foam-extend-only
            names as ``warning`` instead of ``critical``.

    Returns:
        :class:`ValidityVerdict` whose severity reflects the fork.

    Raises:
        TypeError: if ``bc_type_name`` is not a string.
    """
    if not isinstance(bc_type_name, str):
        raise TypeError(
            f"bc_type_name must be str, got {type(bc_type_name).__name__}"
        )
    name = bc_type_name.strip()

    if name in STANDARD_OPENFOAM_BCS:
        return ValidityVerdict(
            bc_type_name=name,
            verdict="valid_standard",
            severity="pass",
            fork=fork,
            suggested_fix=None,
        )

    if name in SENTINEL_BC_NAMES or name.lower() in SENTINEL_BC_NAMES:
        return ValidityVerdict(
            bc_type_name=name,
            verdict="valid_sentinel",
            severity="info",
            fork=fork,
            suggested_fix=None,
        )

    if name in FOAM_EXTEND_ONLY_BCS:
        if fork == "main":
            severity = "critical"
        elif fork == "foam-extend":
            severity = "info"
        else:
            severity = "warning"
        return ValidityVerdict(
            bc_type_name=name,
            verdict="valid_foam_extend_only",
            severity=severity,
            fork=fork,
            suggested_fix=_FOAM_EXTEND_TO_ESI_HINT.get(name),
        )

    # Not in any catalog — likely typo or unsupported user BC.
    return ValidityVerdict(
        bc_type_name=name,
        verdict="unknown",
        severity="warning",
        fork=fork,
        suggested_fix=(
            f"BC type '{name}' is not in the advisor's catalog "
            f"(STANDARD_OPENFOAM_BCS + FOAM_EXTEND_ONLY_BCS + "
            f"SENTINEL_BC_NAMES). Check spelling, or extend the catalog "
            f"via sub-DEC if this is a legitimate ESI BC not yet covered."
        ),
    )


def detect_invalid_bc_types(
    bc_specs: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    fork: Fork = "main",
) -> BcTypeNameReport:
    """Audit a list of ``bc_specs`` for foam-extend mismatches and typos.

    Expected schema for each entry::

        {
          "part_name": "<patch / body name>",          # str (required)
          "fields": {"U": "noSlip", "p": "zeroGradient", ...}  # str -> str (required)
        }

    Backward-compat: entries that omit ``part_name`` or ``fields`` are
    silently skipped (the absence becomes visible via
    ``checked_count`` vs ``parts_examined``).

    Args:
        bc_specs: list of per-part BC declarations. Order is preserved
            in the report findings.
        fork: which OpenFOAM fork to validate against. See
            :func:`check_bc_type_name_validity` for severity semantics.

    Returns:
        :class:`BcTypeNameReport` whose ``findings`` carry only the
        ``warning`` and ``critical`` results (passes / infos are
        suppressed to keep stack output focused on actionable items).
    """
    findings: list[BcTypeNameFinding] = []
    checked_count = 0
    parts_examined = 0

    if bc_specs is None:
        return BcTypeNameReport(
            findings=(),
            checked_count=0,
            parts_examined=0,
            fork=fork,
        )

    for entry in bc_specs:
        if not isinstance(entry, dict):
            continue
        parts_examined += 1
        part_name = entry.get("part_name") or entry.get("name")
        fields = entry.get("fields") or entry.get("bc")
        if not isinstance(part_name, str) or not isinstance(fields, dict):
            continue
        for field_name, bc_type_name in fields.items():
            if not isinstance(field_name, str) or not isinstance(bc_type_name, str):
                continue
            checked_count += 1
            verdict = check_bc_type_name_validity(bc_type_name, fork=fork)
            if verdict.severity in ("pass", "info"):
                continue
            findings.append(
                BcTypeNameFinding(
                    part_name=part_name,
                    field_name=field_name,
                    bc_type_name=verdict.bc_type_name,
                    verdict=verdict.verdict,
                    severity=verdict.severity,
                    fork=verdict.fork,
                    suggested_fix=verdict.suggested_fix,
                    detail=_build_detail(
                        part_name=part_name,
                        field_name=field_name,
                        verdict=verdict,
                    ),
                )
            )

    return BcTypeNameReport(
        findings=tuple(findings),
        checked_count=checked_count,
        parts_examined=parts_examined,
        fork=fork,
    )


def extract_bc_specs_from_parts_manifest(
    parts_manifest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Adapter: extract D10-shaped ``bc_specs`` from a ``parts_manifest``.

    Each ``parts_manifest['parts'][i]`` entry with a ``bc:`` block is
    converted into ``{"part_name": <name>, "fields": <bc-block>}``.
    Parts without a ``bc:`` block are skipped silently — they have
    nothing for D10 to validate.

    Returns an empty list (never ``None``) if the manifest is malformed
    or absent. Per V130, missing inputs degrade silently.
    """
    if not isinstance(parts_manifest, dict):
        return []
    parts = parts_manifest.get("parts") or []
    out: list[dict[str, Any]] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        name = part.get("name")
        bc_block = part.get("bc")
        if not isinstance(name, str) or not isinstance(bc_block, dict):
            continue
        out.append({"part_name": name, "fields": dict(bc_block)})
    return out


# ---- Helpers ---------------------------------------------------------------


def _build_detail(
    *, part_name: str, field_name: str, verdict: ValidityVerdict
) -> str:
    """Compose the human-readable detail for one finding."""
    base = (
        f"part '{part_name}' field '{field_name}' declares "
        f"BC type '{verdict.bc_type_name}' — verdict {verdict.verdict} "
        f"under fork '{verdict.fork}'"
    )
    if verdict.verdict == "valid_foam_extend_only":
        base += (
            "; this BC exists in foam-extend but is absent from "
            "OpenFOAM-ESI mainline (the project's default Docker image "
            "opencfd/openfoam-default:2312). Solver will crash at "
            "boundary-field construction time with 'not found in valid "
            "types'"
        )
    elif verdict.verdict == "unknown":
        base += (
            "; BC name does not match any entry in the advisor's "
            "catalog (STANDARD_OPENFOAM_BCS + FOAM_EXTEND_ONLY_BCS + "
            "SENTINEL_BC_NAMES) — likely typo or user-coded BC not yet "
            "catalogued"
        )
    if verdict.suggested_fix:
        base += f". Suggested fix: {verdict.suggested_fix}"
    return base


__all__ = [
    "BcTypeNameFinding",
    "BcTypeNameReport",
    "FOAM_EXTEND_ONLY_BCS",
    "Fork",
    "SENTINEL_BC_NAMES",
    "STANDARD_OPENFOAM_BCS",
    "ValidityVerdict",
    "check_bc_type_name_validity",
    "detect_invalid_bc_types",
    "extract_bc_specs_from_parts_manifest",
]

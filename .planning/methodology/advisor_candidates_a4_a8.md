# Defect-class advisor candidates · D6/D7/D9/D10 · consolidation + harvest-003 prep

> Living document. Updated when a case sub-session sediments new evidence
> on D6/D7/D9/D10. Promotes a candidate from "drafted" → "ready-to-land"
> when ≥ 2 cross-topology cases exercise it (per V25 pattern, same gate as
> A1-A3 went through).
>
> **Parent**: harvest cycle 003 (triggered after case_020 sediment per
> `case_proposal_queue.md`). This doc is the rallying point.
>
> **A-number reconciliation note** (added 2026-05-12 post-publish): the
> initial draft of this doc claimed A5/A6/A7 slots for D6/D9/D10 advisor
> candidates. That was incorrect — `.planning/cross_cuts/advisor_coverage_2026-05-09.md`
> is SSOT for A-number allocation and had **already** assigned A6 =
> `hvac_adpi.py`, A7 = `step_canonicalizer.py`, A8 = `shm_dict_validator.py`
> (A5 unallocated). Only **A4 = face_orientation advisor** is shared
> between both docs (no conflict). The defect-class advisor candidates
> below are therefore referenced by their **defect-letter** (`D6_advisor`,
> `D9_advisor`, `D10_advisor`) — they will receive A-numbers only when
> harvest-003 promotes them past `drafted`. File name `advisor_candidates_a4_a8.md`
> preserved for git-history continuity.

## Why this exists

Three advisor-stack-scope-audit cases (case_012, case_016, plus pending
case_020) intentionally inject defect classes that **no LANDED advisor
detects**. The point of those injections is **not** to test existing
advisors — it is to surface the gaps so the gaps become advisor
candidates. The candidates then need:

1. A defect-class signature (what the advisor must detect)
2. Pre-drafted advisor spec (signature / inputs / outputs)
3. ≥ 2 cross-topology cases of evidence (the gate that promoted A1/A2/A3
   from "proposed" to "landed in `ui/backend/services/geometry_ingest/`")

This doc tracks all of that in one place so harvest-003 doesn't have to
re-derive the state.

## Promotion gate (same as A1/A2/A3)

A candidate promotes from `drafted` → `ready-to-land` when **all** are true:

- Defect-class signature documented (this file's "Signature" subsection)
- Advisor API surface drafted (this file's "Pre-drafted spec")
- ≥ 2 cross-topology cases have **injected** the defect with main-session
  manual verification (per Hard Guardrail #3) — this is the
  cross-topology evidence
- ≥ 1 case has a written V-row with `[QUESTIONABLE <date>]` marker (per
  knowledge-status convention)

Then promotion to `landed` follows the A1-A3 trajectory: implementation
in `ui/backend/services/geometry_ingest/<advisor_name>.py`, unit tests in
`ui/backend/tests/test_<advisor_name>.py`, status flip to `[VALIDATED]`
in this doc + the V-row, INDEX.md cross-link.

## Candidate slate

### A4 · `face_orientation_advisor`

| field | value |
|---|---|
| Defect class | D7 — "wrong-normal-direction face" (`component_bank.md` L128); generalized to "component rotated from intended orientation" |
| Signature | A face or body whose dominant face normal deviates from a declared/sibling-consensus orientation by more than a per-group tolerance (default 5°) |
| Engineering symptom | Silent flow-pattern asymmetry (rotated diffuser vane → asymmetric jet throw), or sHM `locationInMesh` ambiguity if normal is fully reversed |
| Current evidence | **1 / 2** (V79 case_012 first injection · case_013 dispatched · deferred) |
| Status | `drafted` — pending case_013 sediment |
| V-row(s) | V79 (case_012 first injection · backfilled 2026-05-12) |
| Sibling | Parallel to V55 (D6_advisor) and V56 (D9_advisor) advisor-gap surfacers |

**Pre-drafted spec**:

```python
def detect_face_orientation_anomalies(
    parts_manifest: PartsManifest,
    cad_shapes: Dict[str, Shape],
    *,
    tolerance_deg: float = 5.0,
) -> List[FaceOrientationAnomaly]:
    """For each body declaring `expected_face_normal` or `sibling_group`
    in parts_manifest, compute dominant face normal and compare against
    declared or sibling-consensus direction.

    Returns one anomaly per body whose deviation exceeds tolerance.
    Anomaly carries: body_name, measured_normal, expected_normal,
    deviation_deg, severity (warn @ 5-15°, error @ >15°).
    """
```

Downstream classifier: `body_has_rotation_defect(anomaly, sibling_consensus_deg) -> bool`.

### D6_advisor · `extra_body_in_fluid_advisor` (A-number pending)

| field | value |
|---|---|
| Defect class | D6 — "floating tiny body" (`component_bank.md` L127); generalized to "any disjoint solid fully enclosed by fluid region whose role is not declared" |
| Signature | A solid body that (a) is fully enclosed by the bounding surfaces of a fluid region and (b) is not declared in parts_manifest with `bc_role: internal_wall` or equivalent role |
| Engineering symptom | sHM meshes around the extra body as a no-slip wall; engineer sees no warning; flow correctness depends on whether the body's location matters (FOD inspection class problem) |
| Current evidence | **1 / 2** (V55 case_016 first injection · case_018 dispatched · deferred) |
| Status | `drafted` — pending case_018 sediment |
| V-row(s) | V55 (case_016 first injection 2026-05-11) |
| Sibling | Parallel to V79 (A4 face_orientation / D7) and V56 (D9_advisor) |

**Pre-drafted spec**:

```python
def detect_extra_bodies_in_fluid(
    parts_manifest: PartsManifest,
    cad_shapes: Dict[str, Shape],
    fluid_region_name: str,
) -> List[ExtraBodyAnomaly]:
    """List any solid in cad_shapes whose AABB is fully contained inside
    the bounding surface of fluid_region AND that is not declared in
    parts_manifest as `bc_role: internal_wall` (or `wall_role: structural`).

    Returns body_name, AABB, containing_region, declared_role (or None),
    clearance_to_nearest_wall_mm, severity (warn @ V > 1e-9 m^3, error
    when role is None).
    """
```

Anti-scope: does **not** detect bodies that are partially inside / partially
outside (that's a different topology check — leave to import-time AABB
overlap classifier V59).

### D9_advisor · `curved_surface_tessellation_accuracy_advisor` (A-number pending)

| field | value |
|---|---|
| Defect class | D9 — "over-aggressive simplification" (`component_bank.md` L130); a curved surface approximated by too few facets to resolve the relevant physics scale |
| Signature | A curved patch in parts_manifest whose tessellation `max_chord_deviation` exceeds a fraction (default 1/4) of the target physics resolution length |
| Engineering symptom | Acoustic-source representation degrades silently; engineer sees lower SPL than expected at the FW-H observer but cannot trace it to CAD |
| Current evidence | **1 / 2** (V56 case_016 first injection · case_017 + case_020 dispatched · deferred) |
| Status | `drafted` — pending case_017 OR case_020 sediment |
| V-row(s) | V56 (case_016 first injection 2026-05-11) |
| Sibling | Parallel to V79 (A4 face_orientation / D7) and V55 (D6_advisor) |

**Pre-drafted spec**:

```python
def detect_curved_surface_tessellation_gap(
    parts_manifest: PartsManifest,
    cad_shapes: Dict[str, Shape],
    *,
    target_resolution_mm: float,
    chord_deviation_ratio: float = 0.25,
) -> List[TessellationAnomaly]:
    """For each patch flagged `curvature: curved` in parts_manifest,
    compute max chord deviation from the smooth arc (per-facet) and
    return anomaly if max_chord_deviation_mm > chord_deviation_ratio
    * target_resolution_mm.

    target_resolution_mm is typically the local cell size at sHM level
    assigned to that patch.
    """
```

Anti-scope: does **not** flag UNDER-tessellation that the physics doesn't
care about (e.g., a curved exterior wall far from any acoustic source).
Engineer must declare `curvature_physics_role: acoustic | aerodynamic | none`
in parts_manifest; advisor only fires when role is `acoustic` or
`aerodynamic`.

### D10_advisor · `non_watertight_shell_advisor` (A-number pending)

| field | value |
|---|---|
| Defect class | D10 — "open shell (non-watertight)" (`component_bank.md` L131); a body missing one or more faces |
| Signature | A solid body whose BRep representation reports `is_watertight=False` (counterpart already exists at M5.0 import-time check; advisor extension classifies severity by **hole-size class**) |
| Engineering symptom | STL ingest health_check flags non-watertight; sHM behavior is patch-by-patch undefined (may close the hole with neighbor cells, may leak fluid into helper-solid void); behavior is geometry-and-mesher-dependent |
| Current evidence | **0 / 2** (case_020 dispatched · deferred · will be first injection) |
| Status | `pending-first-injection` — needs case_020 sediment to advance |
| V-row(s) | (none yet — will be V79+ when case_020 sediments) |
| Sibling | Closes the D6/D7/D9/D10 advisor-gap quartet |

**Pre-drafted spec**:

```python
def classify_non_watertight_holes(
    parts_manifest: PartsManifest,
    cad_shapes: Dict[str, Shape],
    *,
    hole_size_warn_mm: float = 1.0,
    hole_size_error_mm: float = 10.0,
) -> List[NonWatertightHole]:
    """For each body flagged is_watertight=False by health_check,
    enumerate open edges (free edges in the BRep), cluster into holes,
    return per-hole: body_name, hole_centroid, hole_perimeter_mm,
    severity (warn @ small / error @ large / silent @ < tolerance).

    Extends the existing M5.0 import-time watertightness check with
    quantitative hole-size classification, not just boolean."""
```

Anti-scope: does **not** repair the hole. Pure detection + classification.
Repair belongs to either CAD round-trip or sHM `locationInMesh` strategy
choice — out of advisor scope.

### Other unallocated defect-class candidates (V-series cross-cuts)

Two additional advisor candidates surface in V-series but are NOT
defect-class first-injection rows — they are setup-pattern advisors
that would prevent silent-fail (not detect injected defects):

- `multi_region_cad_topology_check` (V51 — detects fluid-volume
  intersection in chtMR cases before sHM short-circuits a 21-min
  meshing iteration)
- `wall_function_compat_advisor` (V49 — checks alphat/nut/k triplet
  consistency at conjugate baffles)

Neither has cross-topology defect-class evidence; both are S22/S24
playbook-promoted (see `solver_convergence_playbook.md` for the
checklist). Whether they merit advisor implementation vs.
playbook-only depends on harvest-003 retrospective — playbook-only
is the lighter-touch option.

A5 slot in the A-numbering is currently **unallocated** per harvest-003
SSOT (`advisor_coverage_2026-05-09.md`). Allocation policy: harvest
process assigns A-numbers when an advisor is promoted from `drafted`
to a deeper implementation plan (sub-DEC + LOC estimate).

## Cross-cutting observations

1. **D6 + D7 + D9 + D10 are all "out-of-stack scope" defects.** The
   landed A1-A3 advisor stack was designed around assembled-product
   defects (welds, gaps, sliver fillets, fuselage-frame thinness). The
   advisor-stack-scope-audit cases (case_012 / case_016 / case_018 /
   case_020) are deliberately picking defects that sit outside this
   design envelope. The four candidates close the envelope's four
   gaps: orientation / FOD / curvature-fidelity / open-shell.

2. **V25 placeholder semantic generalizes.** Future defect-class advisor
   implementations (A4 face_orientation + D6/D9/D10) should learn from
   V25: do **not** return PASS based on a single
   boolean. Each advisor should return a structured measurement
   (`deviation_deg`, `body_volume_mm3`, `chord_deviation_mm`,
   `hole_perimeter_mm`) so the engineer can sort severity, and the
   downstream classifier converts measurement → PASS/WARN/ERROR — not
   the advisor itself.

3. **Hard Guardrail #3 is the immediate gate.** Until the four defect-class
   advisors (A4 face_orientation + D6/D9/D10) land, all four defect
   classes are caught only by **manual verification** in
   the sub-session (`scripts/check_<defect>.py` env-var-driven).
   Sub-sessions must explicitly run the manual check; skipping it
   silently passes the defect downstream. This is the operational gate
   keeping the gap from causing production damage during the
   pre-advisor period.

4. **Harvest-003 trigger.** This doc moves from "drafted" status into
   active land-implementation when **case_020 sediments**. That sediment
   produces (a) the first D10 injection (= first D10_advisor evidence
   row), (b) second D9 injection (= second D9_advisor evidence row,
   D9_advisor → `ready-to-land`), and likely confirms the case-018 D6
   prediction (D6_advisor → `ready-to-land`). A4 promotion still waits
   on case_013 sediment independently.

## Next-action checklist (when harvest-003 fires)

- [ ] Case_020 sub-session writes V-rows for D10 first injection + D9
      second injection
- [ ] Verify D9_advisor has ≥ 2 V-rows (V56 + case_020 D9) → flip status
      `drafted` → `ready-to-land`
- [ ] If case_013 sediment landed: verify A4 face_orientation has ≥ 2
      V-rows (V79 + case_013 D7) → flip A4 status
- [ ] If case_018 sediment landed: verify D6_advisor has ≥ 2 V-rows
      (V55 + case_018 D6) → flip D6_advisor status
- [ ] For each `ready-to-land` candidate: spawn implementation sub-DEC
      (sub-DEC scope per v2.3 §3 — one advisor module, one test file,
      one INDEX.md row update; not a full charter DEC unless cross ≥3
      shared code paths). At sub-DEC land time, the candidate receives
      its A-number from harvest snapshot SSOT (next free slot).
- [ ] D10_advisor promotion path: needs second D10 case after case_020 —
      defer decision to next harvest retrospective (case_020 sediment +
      one additional D10 injection from next batch)

## References

- `methodology/industrial_case_solver_findings.md` V55 / V56 / V79
- `methodology/component_bank.md` Defect Catalog (D6 / D7 / D9 / D10)
- `case_profiles/case_012_hvac_supply_diffuser.md` §"Defects"
- `case_index.md` rows for case_012 / case_013 / case_016 / case_017 /
  case_018 / case_020
- DEC-V61-198 §"5-artifact extraction" (A1-A3 trajectory template)

# DEC-V61-071 Stage A.0a · Pre-pivot Context Resolution

Decision document for the four entangled context questions per intake §6 A_0a:
citation, confinement, Re/H/D, wall-BC family.

**Date**: 2026-04-26
**Author**: Claude Code (Opus 4.7, 1M context · Track B sixth-apply continued from Stage 0 v2)
**Source PDF**: Behnia, Parneix & Durbin, "Accurate modeling of impinging jet heat transfer"
                 (CTR Annual Research Briefs 1997, Stanford, pp. 149-160)
**URL**: https://web.stanford.edu/group/ctr/ResBriefs97/behnia.pdf
**Cross-reference dataset**: ERCOFTAC Classic Collection Case025 + KBwiki UFR_3-09
                              (Baughn-Shimizu 1989 + Baughn et al. 1991 hydrodynamic companion)

---

## Q1 · Citation

**STATUS**: RESOLVED — primary thermal anchor confirmed.

**Anchor selected**: Baughn, J.W. & Shimizu, S. (1989) "Heat Transfer Measurements From a
Surface With Uniform Heat Flux and an Impinging Jet", *J. Heat Transfer* **111**(4), 1096-1098.
DOI: `10.1115/1.3250776`

**Verification trail**:
- DOI resolves to ASME Digital Collection (paywalled; Cloudflare-protected page).
- Authoritative dataset summary verified via:
  - **Behnia/Parneix/Durbin 1997** CTR Annual Research Briefs (publicly archived PDF)
    — explicitly references Baughn & Shimizu 1989 as the primary experimental
    Nu(r/D) dataset, plots their data on Fig 2(a), Fig 3, Fig 4.
  - **ERCOFTAC Classic Collection Case025** (UFR_3-09 KBwiki) — hosts the ij2lr-nuss.dat
    raw Nu(r/D) profile + ij2lr-??-sw-mu.dat / ij2lr-??-cw-vv.dat hydrodynamic data.
  - Cross-referenced via WebSearch: "Baughn Shimizu 1989 ERCOFTAC dataset" surfaces
    cfd.mace.manchester.ac.uk/ercoftac/ Case025 first-result.

**Whitelist DOI status**: `10.1016/j.ijheatfluidflow.2013.03.003` (current whitelist value)
VERIFIED to resolve to a **turbine LES paper, NOT impinging jet** per Codex Crossref query
during R1 review (2026-04-26). This is the V61-060 pattern repeated and MUST be replaced
at Stage A.0b.

**Demoted**: Cooper et al. 1993 (`10.1016/S0017-9310(05)80204-2`) is HYDRODYNAMIC PART I
(mean velocity + Reynolds stresses), NOT heat transfer. v1 listing it as interchangeable
with Baughn was wrong; v2 demoted to "hydrodynamic support only" per Codex F1-HIGH.

**Excluded**: Behnia 1998 (`10.1016/S0017-9310(97)00254-8`) and Behnia 1999
(`10.1016/S0142-727X(98)10040-1`) are RANS-validation papers (V2F model), NOT primary
experimental datasets. They CITE Baughn 1989 as their experimental reference. Use them
only as cross-check for "what good RANS agreement looks like", not as headline anchor.

---

## Q2 · Confinement

**STATUS**: RESOLVED — free jet (unconfined).

**Verification**:
- Behnia 1997 §2.1.1 Fig 1 (configuration diagram) shows the computational domain as
  open boundary at the upper edge — explicitly UNCONFINED.
- Behnia 1997 §2.4 ("Effect of confinement") explicitly contrasts the unconfined case
  (sections 2.1-2.3) against a confined variant introduced for comparison only —
  i.e. the primary dataset is unconfined.
- ERCOFTAC Case025 setup mirrors: "free jet impinging on flat plate (not confined)"
  per WebFetch of UFR_3-09.

**Whitelist alignment**: whitelist `geometry_type: IMPINGING_JET` + `parameters.h_over_d=2.0`
implies free jet by default. ✓ MATCHES.

---

## Q3 · Re / H / D match

**STATUS**: MISMATCH — whitelist Re=10000 is OFF-EXPERIMENTAL-BAND.

**Baughn-Shimizu 1989 measured at Re ∈ {2.3×10⁴, 7×10⁴}** = Re ∈ {23000, 70000}.
The two specific values appear in:
- ERCOFTAC Case025 description (verified via WebFetch)
- Behnia 1997 Fig 3 caption: "symbols: experiments (● : Re = 23,000, □ : Re = 50,000,
  × : Re = 70,000)" (Re=50,000 is from Yan 1993 not Baughn)
- Behnia 1997 Fig 2(b) text: "the widely-used test-case of an unconfined impinging jet
  on a flat plat at Re = 23,000"

**Whitelist Re=10,000**: NO direct experimental data exists at this Re. Two paths
considered:

| Path | Action | Pro | Con |
|---|---|---|---|
| (A) Bump whitelist Re | 10000 → 23000 in `knowledge/whitelist.yaml` | Anchored to actual measured row; honest; matches Behnia 1997 single-Re comparisons | Architectural change to whitelist; downstream may have cached fixtures at Re=10k |
| (B) Re^0.5 scaling | Use Nu_stag(10k) ≈ Nu_stag(23k) × √(10k/23k) ≈ 92 | Preserves whitelist Re | Derived correlation guesswork; V61-060 lesson explicitly avoids this. No measurement to anchor |

**Decision: PATH (A) — bump whitelist Re=10000 → 23000.**

Rationale: V61-060 (RBC) explicitly demonstrated that pivoting to a publicly-archived
benchmark with explicit Table/Figure locator is preferable to derived/correlated values
even when it means changing the case parameters. The whitelist Re=10000 has no source
attribution — it appears to be an arbitrary low-Re probe added at the original
DEC-V61-009 work. Re=23000 is the canonical literature benchmark.

**H/D=2 match**: ✓ Whitelist `h_over_d=2.0` matches Baughn 1989 H/D=2 row exactly.

---

## Q4 · Wall-BC family

**STATUS**: MISMATCH — adapter constant-T vs literature uniform-q.

**Literature BC**: Baughn 1989 used a "very thin vacuum-deposited gold coating on a
plastic substrate" with surface temperature measured via thermochromic liquid crystals.
This setup electrically heats the gold film at constant power → **uniform heat flux**
(q = const, Neumann ∂T/∂n = q/k) on the plate surface. Verified via ERCOFTAC Case025
description.

**Adapter BC**: `src/foam_agent_adapter.py:6204` emits the plate as
`type fixedValue; value uniform {T_plate};` → **constant temperature** (T = const,
Dirichlet). This is the §4 R7-HIGH risk realized.

**Quantitative impact** (per literature):
- Behnia 1997 mentions (paraphrased): "constant temperature or constant heat flux
  assumption would not be accurate any more, which may explain the discrepancy"
  — both BC families produce slightly different Nu(r/D) profiles, with uniform-q
  typically 5-15% higher than constant-T at the stagnation point for the same
  effective ΔT.
- Order-of-magnitude estimate: BC mismatch alone could account for 10-20% deviation
  in Nu_stag, independent of mesh + turbulence-model effects.

**Decision**: KEEP adapter at constant-T for this DEC. Document mismatch in
`physics_contract.note` per intake §7 acceptance criterion vii. Tolerance widening to
±30% (already in intake §2) absorbs this gap.

**Optional follow-up DEC**: add fixedGradient T plate BC variant to `_generate_impinging_jet`
(~30 LOC). Out of scope for V61-071 itself.

---

## Stage A.0a Acceptance summary

| Question | Status | Action at Stage A.0b |
|---|---|---|
| Q1 Citation | RESOLVED | Replace whitelist DOI; gold YAML §source = Baughn & Shimizu 1989; literature_doi = 10.1115/1.3250776 |
| Q2 Confinement | RESOLVED — free jet | Document free-jet assumption in physics_contract.note |
| Q3 Re/H/D | MISMATCH | Bump whitelist Re=10000 → 23000 atomic with alias-map updates per RETRO-V61-060 |
| Q4 Wall BC | MISMATCH | Document constant-T vs uniform-q gap in physics_contract.note; widen tolerance to ±30% |

**Overall verdict**: **PROCEED** with documented mismatches. This is NOT a BLOCK because:
- The chosen anchor (Baughn 1989) is publicly archived and cross-referenced.
- The Re mismatch is closeable via single-line whitelist edit.
- The BC mismatch is acknowledged and absorbed by the widened tolerance band.
- Stage E may still produce an honest-FAIL closeout (V61-060/V61-063/V61-066 pattern)
  if the BC mismatch + steady-state-RANS + k-omega-SST stack cannot match Baughn's
  uniform-q transient measurement; that is acceptable per acceptance criterion ii.

---

## Reference values for Stage A.0b gold YAML rewrite

From Behnia 1997 Fig 3 (digitized from PDF, ● symbols at Re=23,000 H/D=2):

| r/D | Nu | Notes |
|---|---:|---|
| 0.0 | 145 | Stagnation peak (HEADLINE) |
| 0.5 | 130 | First decay step |
| 1.0 | 105 | Past potential-core boundary |
| 1.5 | 95 | Local minimum (pre-secondary) |
| 2.0 | 130 | Secondary peak (transition-to-turbulence in wall jet) |
| 3.0 | 95 | Post-secondary decay |
| 5.0 | 60 | Wall-jet decay region |

Tolerance: ±30% relative per intake §2 / §7.iii.

**Secondary peak at r/D=2**: visible at Re=23,000 but not pronounced (vs sharp double-peak
at Re=70,000). Per intake §1 gate iv: at Re=23,000 (≥20,000), gate #3
`secondary_peak_presence_or_absence` should be PRESENT — peak at r/D ∈ [1.5, 2.5] is
acceptable per the boolean gate.

---

## Open items for Stage A.0b commit

1. Replace `knowledge/whitelist.yaml` axisymmetric_impinging_jet entry:
   - `name`: rename to include "Baughn-Shimizu 1989 benchmark" suffix
     (e.g. "Axisymmetric Impinging Jet (Baughn-Shimizu 1989, Re=23000)")
   - `reference`: "Baughn & Shimizu 1989 — Heat Transfer Measurements From a Surface
     With Uniform Heat Flux and an Impinging Jet"
   - `doi`: "10.1115/1.3250776"
   - `parameters.Re`: 10000 → 23000

2. Update BOTH `_TASK_NAME_TO_CASE_ID_ALIASES` maps atomically:
   - `src/foam_agent_adapter.py:247` — add new task_name → case_id mapping
   - `src/auto_verifier/config.py:30` — same

3. Rewrite `knowledge/gold_standards/axisymmetric_impinging_jet.yaml`:
   - Schema_v2 with 4 observables matching intake §1 v2 taxonomy
   - `nusselt_stagnation_at_r_d_zero`: HARD_GATED, ref=145, tol=0.30
   - `nusselt_profile_r_over_d_*`: 4 stations × QUALITATIVE_GATE (R2 dropped to 1
     gate per Codex F2 — these stations form ONE profile family, not 4 independent)
   - `secondary_peak_presence_or_absence`: QUALITATIVE_GATE, expected=PRESENT (Re=23k)
   - `y_plus_first_cell_at_plate`: PROVISIONAL_ADVISORY
   - `physics_contract.note`: document Q3 (Re bump rationale) + Q4 (BC mismatch)
     + slab-geometry approximation per R8

All three changes MUST be in ONE commit per RETRO-V61-060 addendum (alias-map staleness
defect). Pre-commit verification: run `_normalize_task_name_to_case_id` smoke test before
push.

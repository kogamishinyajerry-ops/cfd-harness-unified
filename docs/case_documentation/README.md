# Case documentation index

> GOV-1 v0.5 enrichment landing under DEC-V61-080 · 2026-04-26 · Option B (docs-only)
> See [`_p4_schema_input.md`](_p4_schema_input.md) for failure-pattern synthesis feeding P4 KNOWLEDGE_OBJECT_MODEL design.

This tree distils each whitelist Gold Standard case into three artifacts:
- **`README.md`** — physics description, BC compatibility, expected behavior, tolerance → citation map, geometry sketch, known good results
- **`citations.bib`** — BibTeX library for primary literature, cross-check correlations, engineering V&V band references
- **`failure_notes.md`** — observed failure modes (resolved + active), pattern themes for P4 schema input

`knowledge/**` is **not modified** — these docs are derived material that keeps `knowledge/case_profiles/` empty until P4 KOM schema ratification.

## Status board (2026-04-26)

| # | Case | Contract status | Citation coverage | Active hazards |
|---|---|---|---|---|
| 1 | [`lid_driven_cavity`](lid_driven_cavity/README.md) | SATISFIED for 3 of 4 Ghia observables (secondaries noise-floor-bounded) | 5/6 = 83% | Stream-function noise floor blocks BL/BR validation; Poisson solve ψ deferred |
| 2 | [`backward_facing_step`](backward_facing_step/README.md) | SATISFIED (post-DEC-V61-052) | 4/4 = 100% | Mesh independence study deferred; 7360-cell quick-run is undersampled-but-stable |
| 3 | [`circular_cylinder_wake`](circular_cylinder_wake/README.md) | COMPATIBLE_WITH_SILENT_PASS_HAZARD (DEC-V61-053 in flight) | 4/4 = 100% | Silent kOmegaSST override; 8.3% blockage residual; St falls back to U_max_approx |
| 4 | [`turbulent_flat_plate`](turbulent_flat_plate/README.md) | SATISFIED_UNDER_LAMINAR_CONTRACT (post-DEC-V61-006) | 1/1 = 100% | Spalding fallback retained; assertion that fallback didn't fire under laminar contract is missing |
| 5 | [`duct_flow`](duct_flow/README.md) | SATISFIED (post-DEC-V61-011 rename) | 1/1 = 100% | None — verdict-stable after pipe→duct rename |
| 6 | [`differential_heated_cavity`](differential_heated_cavity/README.md) | SATISFIED (post-DEC-V61-006 P-2 Ra=10⁶ downgrade) | 5/5 = 100% | ψ_max demotes to PROVISIONAL_ADVISORY when closure residual ≥ 1% |
| 7 | [`plane_channel_flow`](plane_channel_flow/README.md) | **INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE** | 1/1 = 100% | Laminar icoFoam vs turbulent DNS reference — solver pivot or gold pivot needed; y+=100 gold value (22.8) anomalous |
| 8 | [`impinging_jet`](impinging_jet/README.md) | INCOMPATIBLE + reference values **PROVISIONAL** | 0/1 = 0% (`TBD-GOV1`) | Axis empty vs wedge (planar slice); A4 p_rgh iter cap; Behnad 2013 paper re-read pending |
| 9 | [`naca0012_airfoil`](naca0012_airfoil/README.md) | PARTIALLY_COMPATIBLE → SATISFIED at V61-058 Stage E closeout | 5/5 = 100% | Cp magnitude 30-50% attenuated (qualitative gate); Stage E live-run verification pending |
| 10 | [`rayleigh_benard_convection`](rayleigh_benard_convection/README.md) | COMPATIBLE (gold value PROVISIONAL) | 1/1 = 100% | Chaivat correlation variant ambiguity (recompute 9.4 vs stored 10.5) |

**Overall**: 27/29 = 93% tolerance citations covered; 2 honest `TBD-GOV1`.

### Citation tier breakdown (post-audit A2 transparency split, 2026-04-26 · GOV-1 v0.7 update under DEC-V61-086, 2026-04-26)

The "27 cited" tally above conflates three distinct anchor tiers. Per the
independent audit verdict (RATIFY_WITH_AMENDMENTS, A2), these are surfaced
explicitly so consumers can apply their own rigor bar:

| Tier | Anchor type | Count | Pct of 29 | Notes |
|---|---|---|---|---|
| (a) | Case-specific literature (primary paper for the gold value) | 11 | 38% | Ghia 1982, Williamson 1996, de Vahl Davis 1983, Kim/Moser 1987-1999, Ladson 1988, Jones 1976, Chaivat 2006 — direct paper anchors. **GOV-1 v0.7 delta**: NACA `lift_slope_dCl_dalpha` upgraded from tier-(c) to tier-(a) via dual-citation (Ladson §3.4 ±1.2% tunnel repeatability primary + dec_v61_058_intake secondary), per `_research_notes/_trace_methodology.md` §3 + §5 borderline pattern. Note: per the DOI integrity audit, several tier-(a) DOIs have integrity issues separate from tier classification (CCW typo, DCT wrong journal, IJ + RBC mismatch) — see [`_research_notes/gov1_paper_reread_2026-04-26.md`](_research_notes/gov1_paper_reread_2026-04-26.md) |
| (b) | Standards-anchored (ASME V&V 20-2009 engineering V&V band) | 9 | 31% | Methodologically defensible per Pivot Charter §5 (no per-paper anchoring mandate), but NOT the same rigor class as (a). Engineering tolerance band absorbing mesh + scheme uncertainty. |
| (c) | Internal-decision anchor (`dec_v61_057_intake`, `dec_v61_058_intake`) | 7 | 24% | Per-observable tolerance values set by internal DEC §B intake decisions. **GOV-1 v0.7**: trace attempted for all 8 tier-(c) entries; 1 succeeded (NACA lift_slope, see tier-(a) row), 7 honest-fallback retained. Retained: DHC `nusselt_max` / `u_max_v` / `v_max_h` / `psi_max_center` (de Vahl Davis 1983 has no per-grid scatter or measurement-noise §X — gold-value-by-association upgrade explicitly forbidden by `_research_notes/_trace_methodology.md` §2); NACA `pressure_coefficient` profile (harness 30-50% attenuation, no published anchor); NACA `drag_coefficient_alpha_zero` (wall-function discretization noise, solver-specific); NACA `y_plus_max` (Codex F5 advisory, not literature). |
| TBD | `TBD-GOV1` | 2 | 7% | LDC secondary-vortex ψ relaxation (no published reference); IJ Behnia HOLD (gold value itself PROVISIONAL pending paper re-read) |
| **Total** | — | **29** | **100%** | — |

**Literature-coverage metric (tier a only)**: **11/29 = 38%** (GOV-1 v0.7, +1 from v0.6 baseline 10/29 = 34%). The 93% figure remains
valid as the all-tier total but should not be read as 93% literature-anchored.

**GOV-1 v0.7 honesty note**: the v0.7 tier-(c)→tier-(a) trace pass produced 1
upgrade out of 8 attempted, NOT the ≥5 implied by the "≥15/29 expected"
target framed at v0.6 close. This reflects the reality that DHC's primary
paper (de Vahl Davis 1983) is a converged-numerical-benchmark publication
without per-grid scatter or measurement-noise sections, and most NACA
cross-check tolerances are harness-internal numerical/extractor decisions
with no published anchor. The methodology's no-circular-citation rule
(`_research_notes/_trace_methodology.md` §2 — "gold-value-by-association"
anti-pattern) prevented inflating the count via reclassification. This is
not a documentation gap; it is a real distinction in rigor between
gold-value anchoring (where the paper IS the source) and tolerance
anchoring (where engineering judgment about extractor / numerical noise
floors is the source).

## Open HOLDs requiring external paper re-read (input to GOV-1 v1.0)

These three cases are blocked from full citation closure until a primary-source verification:

1. **IJ — Behnad 2013** (DOI [10.1016/j.ijheatfluidflow.2013.03.003](https://doi.org/10.1016/j.ijheatfluidflow.2013.03.003)). Audit recomputed Nu(r/d=0) ~110-130 vs stored gold 25 — 4-5× discrepancy. Need to confirm Re=10000, h/d=2 configuration matches Behnad's reported peak. → see [`_research_notes/`](_research_notes/) when produced.

2. **RBC — Chaivat 2006** (DOI [10.1016/j.ijheatmasstransfer.2005.07.039](https://doi.org/10.1016/j.ijheatmasstransfer.2005.07.039)). Recompute 0.229·(10⁶)^0.269 = 9.4 vs stored 10.5 = 11.5% off (within 15% tol but suspicious). Need to identify which correlation variant Chaivat reports as the primary equation.

3. **LDC — secondary-vortex ψ relaxation** (`tolerance: 0.10` vs primary `0.05`). No published reference quantifies the corner-eddy-vs-primary ψ relaxation factor. Either find a literature precedent (e.g., Ghia 1982 corner-eddy mesh-sensitivity discussion) or formally accept as engineering choice. **GOV-1 v0.7 trace attempted** (DEC-V61-086 follow-up, 2026-04-26): Ghia 1982 Table III provides gold values but no §X mesh-sensitivity discussion; trace fails methodology §1.1. Retained as `TBD-GOV1` pending CFDJerry direction on which path (literature re-read for hidden §X anchor, or formal engineering-choice DEC mint) to pursue. Promotion to tier-(c) via engineering-choice DEC is **not autonomous** — requires CFDJerry signal per Pivot Charter §4.7 framework (DEC-V61-085 CLASS-1/2/3 boundary).

## Citation key index (cross-case)

The following BibTeX keys appear across multiple cases:

- `asme_vv20_2009` — engineering V&V tolerance band practice (8 cases)
- `ghia1982` — LDC primary anchor (1 case, comprehensive)
- `williamson1996` — CCW primary anchor (1 case)
- `de_vahl_davis_1983` — DHC primary anchor (1 case)
- `kim_moin_moser_1987` + `moser1999` — PCF primary anchors (1 case)
- `ladson1988` + `abbott1959` + `gregory_oreilly_1970` — NACA multi-source anchors (1 case)
- `dec_v61_057_intake`, `dec_v61_058_intake` — internal-decision citations (DHC, NACA)

A future GOV-1 v1.0 doc may consolidate these into a top-level
`docs/case_documentation/_citations.bib` to dedupe — for now, per-case
files preserve self-contained traceability.

## How to extend

When P4 KOM schema is ratified:
1. Reconcile each `<case_id>/README.md` content into `knowledge/case_profiles/<case_id>/profile.yaml` per the new schema fields
2. Reconcile each `<case_id>/failure_notes.md` content into `knowledge/case_profiles/<case_id>/failure_patterns.yaml` per the new `FailurePattern` schema
3. Keep `<case_id>/citations.bib` as-is — BibTeX is not a KOM concern; it lives in docs/

A follow-up DEC should specify the exact mapping rules.

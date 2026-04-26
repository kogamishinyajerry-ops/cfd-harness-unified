# CCW Research Notes

Evidence packages and per-issue investigations for `circular_cylinder_wake`.

## Naming

`YYYY-MM-DD_<topic-slug>.md`

## Likely future notes

- **silent kOmegaSST override resolution** — whitelist declares
  `turbulence_model: laminar` but adapter overrides for BODY_IN_CHANNEL
  geometry. DEC-V61-053 Batch B1 partially mitigated; full closure of
  the silent-pass hazard merits a dedicated note.
- **blockage residual sensitivity (8.3% → ≤5%)** — domain growth study
  H ∈ {6D, 8D, 10D, 12D} at fixed Re=100, comparing Cd/St/Cl_rms drift
  vs Williamson 1996 anchors.
- **U_max_approx fallback retirement** — once laminar-solver path lands,
  audit fixture should surface St as primary (not fall back); empirical
  trace of when the fallback fires.

## Cross-references

- Primary citations: `../citations.bib`
- Failure modes: `../failure_notes.md`
- Tolerance map: `../README.md`
- DOI integrity: `../../docs/case_documentation/_research_notes/gov1_paper_reread_2026-04-26.md` (CCW DOI typo flagged)

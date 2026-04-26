# TFP Research Notes

Evidence packages and per-issue investigations for `turbulent_flat_plate`.

## Naming

`YYYY-MM-DD_<topic-slug>.md`

## Likely future notes

- **Spalding fallback assertion gap** — README §"Active hazards" notes
  the assertion that the Spalding fallback didn't fire under the laminar
  contract is missing. A note documenting empirical fallback-trigger
  conditions + a regression test would close the observability gap.
- **Cf @ x=0.5 derivation chain** — gold value 0.0076 is from Spalding
  for plate_length=1.0m at Re_x=5×10⁵; an evidence note tracing the
  exact Spalding correlation form (Schlichting Boundary Layer Theory
  Ch. 21 or White Viscous Fluid Flow Ch. 7) would upgrade the citation
  from internal-decision to literature-anchored.

## Cross-references

- Primary citations: `../citations.bib`
- Failure modes: `../failure_notes.md`
- Tolerance map: `../README.md`

# BFS Research Notes

Evidence packages and per-issue investigations for `backward_facing_step`.

## Naming

`YYYY-MM-DD_<topic-slug>.md`

## Likely future notes

- **mesh independence study** — README §"Active hazards" notes the
  7360-cell quick-run is undersampled-but-stable; a refinement sweep
  (≥3 mesh levels) would close mesh sensitivity.
- **reattachment length sensitivity to inlet profile** — Driver 1985 vs
  Le-Moin-Kim 1997 differ on whether step inlet should be fully
  developed; impacts `xR/h` reattachment-length tolerance.

## Cross-references

- Primary citations: `../citations.bib`
- Failure modes: `../failure_notes.md`
- Tolerance map: `../README.md`

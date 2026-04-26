# LDC Research Notes

Evidence packages and per-issue investigations for `lid_driven_cavity`.
Each note is a dated markdown file with a clear topic.

## Naming

`YYYY-MM-DD_<topic-slug>.md` — date is when the note is authored, topic
slug describes what the note investigates (anchor evidence, observability
gap, extractor calibration, etc.).

## Likely future notes

- **secondary-vortex ψ relaxation literature trace** — the `0.10` tolerance
  for BL/BR secondary-vortex stream-function values (vs `0.05` primary)
  is currently `TBD-GOV1` per `../README.md` Open HOLDs. A literature
  trace would verify whether Ghia 1982 §3.4 or a later cross-validation
  study reports a justified relaxation factor.
- **stream-function extractor noise floor** — empirical measurement of
  ψ noise floor on adapter mesh as function of refinement; informs whether
  Poisson-solve ψ is needed or whether trapezoidal stays sufficient.

## Cross-references

- Primary citations: `../citations.bib`
- Failure modes: `../failure_notes.md`
- Tolerance map: `../README.md` §"Tolerance → citation map"

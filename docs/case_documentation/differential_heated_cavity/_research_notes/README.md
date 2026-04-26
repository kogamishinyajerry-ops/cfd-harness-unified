# DHC Research Notes

Evidence packages and per-issue investigations for `differential_heated_cavity`.

## Naming

`YYYY-MM-DD_<topic-slug>.md`

## Likely future notes

- **DEC-V61-057 §B intake → de Vahl Davis 1983 Tables I-IV trace** —
  4 of 5 DHC observables (`nusselt_max`, `u_max_centerline_v`,
  `v_max_centerline_h`, `psi_max_center`) are tier-(c) cited to
  internal DEC §B. The tolerance VALUES are internal-decision but the
  reference VALUES come from de Vahl Davis 1983 Tables I-IV. A trace
  note clarifying which-comes-from-where would tighten the citation
  audit — see `../../README.md` §"Citation tier breakdown" for the
  underlying methodology question.
- **ψ_max closure-residual demotion calibration** — the 1% threshold
  for demoting ψ_max from HARD_GATED to PROVISIONAL_ADVISORY is
  internal-decision; an empirical study of closure residual vs mesh
  refinement at Ra=10⁶ would justify the threshold from data.
- **Ra=10¹⁰ turbulent regime infeasibility** — README §"Active hazards"
  notes ~1000 wall-normal cells needed; a note documenting why Ra=10⁶
  was the chosen anchor (vs Ra=10⁸ or higher) would close the case-pivot
  question if it ever resurfaces.

## Cross-references

- Primary citations: `../citations.bib`
- Failure modes: `../failure_notes.md`
- Tolerance map: `../README.md`
- DEC-V61-057 intake: `../../../.planning/intake/DEC-V61-057_differential_heated_cavity.yaml`

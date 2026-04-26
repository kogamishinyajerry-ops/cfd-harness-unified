# PCF Research Notes

Evidence packages and per-issue investigations for `plane_channel_flow`.

## Naming

`YYYY-MM-DD_<topic-slug>.md`

## Likely future notes

- **INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE resolution** —
  README flags `laminar icoFoam` solver vs `Kim/Moin/Moser 1987` /
  `Moser/Kim/Mansour 1999` turbulent DNS reference as a contract
  mismatch. Solver pivot (laminar → DNS or RANS) OR gold pivot
  (turbulent DNS → laminar Poiseuille) needed. An evidence note framing
  the trade-off + cost estimate for each path would unblock the
  decision.
- **y+=100 anomaly** — the y+=100 gold value (22.8) is anomalous
  vs Kim/Moser DNS interior-region log-law u+ behavior. A note
  diagnosing whether the anomaly is in the gold value, the y+ definition
  used by the harness, or the solver-side velocity profile sampling.

## Cross-references

- Primary citations: `../citations.bib`
- Failure modes: `../failure_notes.md`
- Tolerance map: `../README.md`

# NACA0012 Research Notes

Evidence packages and per-issue investigations for `naca0012_airfoil`.

## Naming

`YYYY-MM-DD_<topic-slug>.md`

## Likely future notes

- **Cp magnitude 30-50% attenuation root-cause** — README §"Active hazards"
  notes Cp surface values are systematically attenuated vs Ladson 1988
  (qualitative-gate-only). Suspected causes: (a) surface sampler grid
  spacing; (b) surface vs near-surface velocity reconstruction; (c) BC
  attenuation in adapter inlet profile. A diagnostic note isolating which
  is dominant would unblock magnitude-gate elevation.
- **DEC-V61-058 §3 PROFILE/QUALITATIVE/SAME_RUN gate → Ladson 1988 §3.4
  trace** — internal DEC §3 chose specific PROFILE (5%) /
  QUALITATIVE (sign-only) / SAME_RUN gate cadence; the underlying
  rationale references Ladson 1988 §3.4 mesh-sensitivity discussion.
  A trace note re-citing each gate to its Ladson §3.4 paragraph would
  upgrade tier-(c) citations to tier-(a).
- **Stage E live-run verification readout** — once Stage E live-run lands,
  a note documenting which gates passed vs flagged + per-gate magnitude
  attenuation residual.

## Cross-references

- Primary citations: `../citations.bib`
- Failure modes: `../failure_notes.md`
- Tolerance map: `../README.md`
- DEC-V61-058 (NACA Ladson anchor pivot, CLASS-2 precedent): see project decision history

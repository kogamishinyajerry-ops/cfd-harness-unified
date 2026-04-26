# DCT Research Notes

Evidence packages and per-issue investigations for `duct_flow`.

## Naming

`YYYY-MM-DD_<topic-slug>.md`

## Likely future notes

- **Re* modified-Reynolds verification** — DEC-V61-082 rewrote
  `reference_correlation_context` from a fictitious `f_duct ≈ 0.88·f_pipe`
  to Jones 1976's actual Re* approach. Once V61-082 Codex APPROVE lands,
  a note tracing the exact formula derivation from Jones 1976 §3 (with
  ASME archive page-image evidence) would future-proof against re-litigation.
- **smooth-pipe vs smooth-duct delta at Re=50000** — Colebrook 1939
  smooth-pipe gives f≈0.0206; gold is 0.0185 (~10% lower) consistent
  with Jones 1976 ~5% scatter band. A note quantifying the actual band
  for AR=1 ducts would replace the current rule-of-thumb description.

## Cross-references

- Primary citations: `../citations.bib`
- Failure modes: `../failure_notes.md`
- Tolerance map: `../README.md`
- DEC-V61-082 (CLASS-2 pending Codex): `../../../.planning/decisions/2026-04-26_v61_082_dct_journal_swap.md`

# OpenFOAM Corpus (N6 RAG seed)

Curated topic notes consumed by the N6 AI advisor stack. Each file is
markdown; sections are split on `##`-or-deeper headers by the corpus
loader (`ui/backend/services/ai_advisor/corpus_loader.py`).

## Allowlist scope

This directory is one of two corpus roots (the other is
`.planning/decisions/`). Case directories under `workspace/projects/`
are **not** ingested — see DEC-V61-156 §threat model.

## Adding new topics

Add a `.md` file with `##`-headed sections. The loader will pick it up
on next process restart. There is no auto-reindex in V1.

## V1 seed content

- `mesh_quality_checkmesh.md` — checkMesh interpretation reference
- `solver_selection.md` — when to pick simpleFoam / icoFoam / pimpleFoam
- `boundary_conditions_basics.md` — common BC types + when each applies
- `under_relaxation_factors.md` — URF guidance for SIMPLE / PISO loops
- `residual_diagnostics.md` — interpreting solver residuals

## V-series industrial findings (synced 2026-05-11, spike scope)

Synced copies of methodology SSOT files. Originals at `.planning/methodology/` remain authoritative; corpus copies enable AI advisor retrieval. Re-sync manually when SSOT changes (no auto-watcher in spike scope).

- `solver_convergence_playbook.md` — S1-S10 decision tree from APU bay V3→V13 industrial case
- `industrial_solver_findings_v_series.md` — V1-V14+ per-finding index (engineer-facing solver/mesh internals)

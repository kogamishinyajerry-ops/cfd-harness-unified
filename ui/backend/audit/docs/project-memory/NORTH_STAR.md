# North Star

## Long-term ambition

Build a **STAR-CCM+-class, AI-native CFD workbench** with an embedded AI advisor.

Capabilities the long-term system must eventually own:

- integrated CFD workbench (case lifecycle, projects, runs, comparisons)
- CAD / geometry handling (import, repair, simplification)
- meshing (structured, unstructured, snapping, boundary layers)
- boundary condition setup (typed, validated, physics-aware)
- solver orchestration (multi-solver, multi-physics, queueable)
- post-processing (fields, surfaces, sections, integrals, line plots)
- verification & validation (mesh independence, reference comparison, uncertainty)
- design exploration (DOE, surrogates, optimization)
- AI advisor embedded in the workflow (case review, failure triage, next experiment)

## Why this is the North Star, not the v0 target

A complete CFD workbench is the destination, not the first step. Every prior attempt
that started by building everything at once stalled because no single subsystem was
ever known to be correct.

The North Star sets direction. The wedge (`CURRENT_SCOPE.md`) sets the next
implementation target.

## Owner constraint

The owner is one human with multiple AI agents (Claude, Codex, others). The
North Star must remain achievable within that constraint:

- agents may parallelize, but the owner must be able to inspect state in under one minute
- agents must record evidence in the repo, not in chat context
- no agent may declare the North Star "reached" or "almost reached" without
  artifacts proving the underlying capability is real

## How we will know we are getting there

The North Star moves closer when:

1. A new CFD case can move from `case_manifest.yaml` to `trust_report.json` without
   silent assumptions, with the AI advisor explaining each gate.
2. Negative tests fail loudly and Red Team review catches false PASSes.
3. The cockpit reflects current state without requiring chat context.
4. The number of cases with `solver_execution: real` and
   `validation_status: validated` grows monotonically and is provable from the repo.

Anything else — slick UI, AI demos, marketing-grade dashboards — is theatre until
those four conditions are true.

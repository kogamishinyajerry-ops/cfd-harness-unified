# Open Questions

Append questions; resolve them via DECISION_LOG.md.

## OQ-0001 — Which canonical reference dataset for `flat_plate_rans_sst`?
**Raised by:** benchmark-director, 2026-05-20
**Status:** RESOLVED 2026-05-20 — see DEC-0006 (NASA TMR flat plate)
**Context:** `case_manifest.yaml > reference_comparison.status = placeholder`. Phase 1
cannot end without a finalized reference. Candidates: NASA TMR flat plate, Wieghardt,
or other published SST reference. Licensing must permit redistribution under the project.
**Required for:** Phase 1 go.

## OQ-0002 — Real OpenFOAM adapter strategy: docker, native, or both?
**Raised by:** openfoam-adapter-engineer, 2026-05-20
**Status:** RESOLVED 2026-05-20 — see DEC-0005 (Docker only)
**Context:** Phase 1 needs a real solver invocation. Decision affects reproducibility,
CI integration, and the system-architect's `MODULE_BOUNDARIES.md`.
**Required for:** Phase 1 go.

## OQ-0003 — Should Phase 2 (negative tests) precede or follow Phase 1 (real solver)?
**Raised by:** project-governor, 2026-05-20
**Status:** open
**Context:** Roadmap currently lists Phase 1 then 2, but negative-test fixtures may be
easier to land first and harden the harness before the solver moves.
**Required for:** roadmap finalization.

## OQ-0004 — What is the absolute floor for "validation_status: validated"?
**Raised by:** cfd-vv-director, 2026-05-20
**Status:** open
**Context:** We must define the minimum evidence required before any trust_report may
move from `not_validated` to `validated`. Suggested floor: real solver run + cited
reference dataset + QoI within tolerance + mesh independence study.
**Required for:** Phase 1 acceptance criteria.

## OQ-0005 — How should the AI advisor surface its uncertainty?
**Raised by:** product-ui-director, 2026-05-20
**Status:** open
**Context:** Advisor output must distinguish "evidence-backed claim" from "speculation."
Possible formats: cite-and-quote artifact paths, confidence tags, "I don't know."
**Required for:** Phase 4 design.

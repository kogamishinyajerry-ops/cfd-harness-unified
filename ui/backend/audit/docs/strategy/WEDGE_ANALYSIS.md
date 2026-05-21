# Wedge Analysis

## What is a wedge here

A wedge is the smallest piece of the North Star that:

1. is independently useful,
2. produces evidence rather than promises,
3. forces every later phase to inherit its discipline.

## v0 wedge restated

**"Take one CFD case, produce a machine-auditable trust contract, and refuse
to mark it PASS without artifacts."**

## Why this is the right wedge

- **Independently useful:** even with a mocked solver, the manifest + audit
  artifacts are non-trivial deliverables — they enforce structure the OpenFOAM
  community currently lacks.
- **Produces evidence:** every gate writes a JSON/CSV/log artifact; the
  trust_report points to each one.
- **Discipline propagates:** Phase 1's real solver inherits the same gate
  structure; Phase 2's negative tests inherit the same schema; Phase 4's AI
  advisor reads the same artifacts. Nothing later in the roadmap can skip the
  trust layer.

## Why competing wedges were rejected

| Rejected wedge | Why we did not pick it |
|---|---|
| "Build a CFD UI first" | UI without trust is decoration. Repeats prior failure. |
| "Build the OpenFOAM adapter first" | Solver fidelity without case contract gives green runs we can't justify. |
| "Build the AI advisor first" | Advisor without evidence becomes confident hallucinations. |
| "Build a turbulence-model selector" | Premature automation of a decision that operators must own. |
| "Build design exploration first" | Optimizing over unverified cases is amplified error. |

## What the wedge must NOT become

If the wedge starts including UI editing, automatic BC patching, AI rewriting case
files, or "validated"-without-reference reports, it has been broken. Roll back.

## Wedge expansion plan

Wedge stays narrow through Phase 2. Phase 3 (static UI) and Phase 4 (AI advisor)
extend the wedge along the same trust spine. Phase 5 (design exploration) only
becomes legitimate once the trust spine is end-to-end real.

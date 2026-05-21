# Competitive Map

This document positions AI-CFD-V2 against existing CFD tooling. It is descriptive,
not aspirational — claims here must remain defensible.

## Reference category leaders

| Tool | What it is | Where it is strong | What it is weak at (relative to our wedge) |
|---|---|---|---|
| STAR-CCM+ | Commercial all-in-one CFD workbench | Geometry → mesh → solve → post integrated; industry trust | Closed; expensive; no machine-readable trust contract per case |
| Ansys Fluent | Commercial CFD solver + workbench | Solver fidelity; turbulence model breadth | Same closed/expensive constraints; opaque audit trail |
| OpenFOAM | Open-source CFD toolkit | Source-available solver; widely cited | Steep learning curve; correctness is a function of operator skill; no first-party trust contract |
| SimScale | Cloud CFD workbench | Convenience; collaboration | Convenience can hide errors; limited reproducibility outside platform |
| AI-assisted CAE startups (various) | LLM advisor wrappers | Quick demos | Often produce confident outputs without artifacts; the failure mode we are explicitly avoiding |

## Where AI-CFD-V2 v0 wedges in

The wedge is **not** "another CFD GUI." The wedge is the layer the above tools
all lack: **a machine-checkable trust contract per case, with auditable artifacts
and an AI advisor that explains evidence rather than fabricates it.**

Concretely: AI-CFD-V2 stands next to OpenFOAM, not in place of it. OpenFOAM
remains the solver of record; AI-CFD-V2 makes its outputs trustworthy.

## Where AI-CFD-V2 is NOT trying to win in v0

- not trying to beat STAR-CCM+ on UI polish
- not trying to beat Fluent on turbulence-model coverage
- not trying to beat SimScale on convenience
- not trying to beat AI-assisted startups on demo flash

The differentiator is **evidence per claim**, not feature surface area.

## When the competitive map should be revisited

After Phase 2 (negative tests). At that point, the trust harness either does or
does not catch seeded bad cases. If it does, the differentiator is real. If it
doesn't, no amount of competitive analysis matters.

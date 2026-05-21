# Scope Firewall (v0)

The following are **out of scope** for v0. Do not implement, design UI for,
sketch APIs for, or write speculative docs about them in this phase.

## Explicitly out of scope

- full STAR-CCM+ clone
- arbitrary CAD repair
- general mesh optimization
- full 3D interactive editor
- automatic turbulence model selector
- multi-physics (combustion, multiphase, FSI, MHD, etc.)
- LES / DES / hybrid models beyond what `flat_plate_rans_sst` declares
- production-grade OpenFOAM orchestration (queues, clusters, autoscaling)
- design exploration (DOE, gradient-based optimization, surrogate modeling)
- claiming validation without reference data
- "AI runs the whole case" autonomy
- shipping anything UI heavier than the cockpit + a static trust-report page

## What "out of scope" means operationally

If an agent thinks one of the above is needed:

1. Stop the in-flight work.
2. Append a CWOS event with `status: NEEDS_DECISION`.
3. Add an entry to `OPEN_QUESTIONS.md` describing the proposed extension.
4. Wait for the project-governor agent + the owner to decide.

A scope extension committed without going through this loop is a defect, even
if the code is otherwise good.

## What is gray-zone (allowed only as scaffold)

- mocked OpenFOAM solver execution (allowed if clearly labeled)
- placeholder reference datasets (allowed if `reference_comparison.status` ≠ `finalized`)
- scaffolded negative-test directories (allowed if README says so)
- empty audit module stubs (allowed if they still emit honest artifacts)

The scaffold rule: anything declared scaffold must be visible in the cockpit and
in the trust_report. Never let scaffold accidentally graduate to "done" by going
unnoticed.

## What is forbidden even as scaffold

- a trust_report claiming `validation_status: "validated"` without reference data
- a UI screen that hides the mocked-solver banner
- a doc that implies real CFD validation is solved
- an agent that approves its own work
- a cockpit value not backed by an artifact

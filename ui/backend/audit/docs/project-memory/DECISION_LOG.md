# Decision Log

Append-only. Newest at the top. Mirrors `.cwos/decisions.yaml`.

## DEC-0006 — 2026-05-20 — Canonical reference dataset for flat_plate_rans_sst = NASA TMR flat plate
**Status:** ACCEPTED
**Decided by:** project-owner (resolves OQ-0001)
**Rationale:** NASA Turbulence Modeling Resource flat plate is the de-facto SST verification
target. Pros: publicly hosted at https://turbmodels.larc.nasa.gov/flatplate.html, redistributable
under open terms, contains both Cf distribution and skin-friction reference, and matches the
geometry/BC contract already declared in `case_manifest.yaml`. Wieghardt 1944 was the considered
alternative but licensing is murky and the data is older.
**Implication:** Phase 1 must download/cache NASA TMR data under `cases/flat_plate_rans_sst/reference/`
with citation + license file. R-11 (reference shopping) is mitigated because the choice is
recorded BEFORE any real run is attempted.

## DEC-0005 — 2026-05-20 — OpenFOAM adapter strategy = Docker only
**Status:** ACCEPTED
**Decided by:** project-owner (resolves OQ-0002)
**Rationale:** macOS has no native OpenFOAM. Docker Desktop runs the official `openfoam/openfoam11`
images cleanly, gives byte-reproducible builds, and matches what CI will use. "Both" would double
the maintenance surface for zero current benefit. The adapter is a thin `docker run` wrapper that
mounts the case dir and shells through to `simpleFoam`. If a future Linux-native CI worker arises,
a second backend can be added then — the contract is `run(case_dir, manifest) -> dict` and is
strategy-agnostic.
**Implication:** Phase 1 `src/cfdtrust/backends/openfoam.py` detects Docker availability + image
presence and BLOCKs with a structured reason if either is missing. No silent fallback to mocked.

## DEC-0004 — 2026-05-20 — First UI is cockpit + trust report, not a full CFD workbench
**Status:** ACCEPTED
**Decided by:** product-ui-director
**Rationale:** A 1-minute cockpit + a per-case trust report is enough UI for Phase 0.
Anything else slides into "STAR-CCM+ clone" scope.

## DEC-0003 — 2026-05-20 — Phase 0 may use mocked solver execution; must be clearly labeled
**Status:** ACCEPTED
**Decided by:** cfd-vv-director + project-governor
**Rationale:** Real OpenFOAM integration is not the wedge; a mocked solver gate lets us
exercise the rest of the trust loop while making the mock impossible to hide. Every mocked
trust_report must include `solver_execution: mocked` and `validation_status: not_validated`.

## DEC-0002 — 2026-05-20 — flat_plate_rans_sst is the first sample case
**Status:** ACCEPTED
**Decided by:** cfd-vv-director + benchmark-director
**Rationale:** Flat plate steady-RANS with k-omega SST is the most-studied verification case;
reference data is well-known, geometry is trivial, and the case forces us to define every
contract section (mesh / BC / QoI / reference).

## DEC-0001 — 2026-05-20 — v0 wedge is OpenFOAM-based CFD Trust Workbench
**Status:** ACCEPTED
**Decided by:** project-governor + project-owner
**Rationale:** Building a full CFD workbench in one shot reliably fails. The first credible
thing to build is a machine-auditable trust contract around a single canonical benchmark,
with the solver layer mockable so the rest of the loop is exercised.

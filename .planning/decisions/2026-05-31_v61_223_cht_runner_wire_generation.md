---
decision_id: V61-223
title: CHT runner-wire — generation side (GeometryType + generator + case_family) — P3 W3.2a sub-DEC
status: Accepted
accepted_date: 2026-06-03
parent_dec: V61-217
phase: P3 (Blueprint v4 · CHT)
autonomous_governance: true
confidence: high
kogami_opt_in: false
round_cap: 3
codex_review_relay: 86gs gpt-5.4 xhigh (governance-primary; recovered this session after last session's 5-for-5 outage — CRS fallback on standby)
codex_verdict: APPROVE-equivalent (clean close at R1 — R0 86gs xhigh 1×P1+2×P2 fixed; R1 CRS high 1×P2 fixed + 1×P2 disproven via blockMesh ground-truth in ESI opencfd/openfoam-default:2312; round cap=3 NOT reached)
codex_tool_report_path: reports/codex_tool_reports/v61_223_w32a_report.md
notion_sync_status: pending_accepted
touches_shared_dec: V61-217 (W3.2 charter row — generation half) · V61-202-SUB-M31-CYCLE4 (case_family_registry chtMultiRegion deferred-target — CLOSED here) · V61-211 (solver_block region-agnostic controlDict — relied on) · V61-220 (thermo multi-region extractor — generator output parses through it)
sibling_dec_contract_for: V61-217 W3.2b (live multi-region run — splitMeshRegions pipeline + OF10/ESI solver-image reconciliation) · W3.2c (producer-side region emission) · W3.2d (R15/R16 reground)
---

# DEC-V61-223 · CHT runner-wire — generation side (P3 W3.2a)

## Context

DEC-V61-217 charter row **W3.2** (runner-wire) is the biggest P3 phase. A W3.2
understand-phase (6 parallel read-only subsystem maps) found it decomposes into
four sub-units, each offline-testable or runtime-gated:

| sub-unit | offline-testable here? | gating surprise found |
|---|---|---|
| **W3.2a generation** | ✅ | post-dispatch flow is single-region — needs `splitMeshRegions` |
| **W3.2b live-run** | ❌ (needs Docker + solver/image) | OF10 image lacks `chtMultiRegionSimpleFoam` (ESI-only); adapter hardwired to OF10 bashrc |
| **W3.2c producer-side** | ✅ | no producer for `coupled_patches.neighbour_region` |
| **W3.2d R15/R16 reground** | ✅ (rules) | no in-repo per-region produced-mesh-presence extractor |

**User decision (2026-05-31): scope this slice to the GENERATION SIDE only**
(W3.2a). The environment has the `docker` *CLI* + OpenFOAM images but NOT the
`docker` *Python SDK* (so live execution short-circuits) and the charter's
literal `chtMultiRegionSimpleFoam` is unrunnable without OF10-vs-ESI
reconciliation — both W3.2b. The other four understand-phase minor decisions
took charter-consistent defaults (all reversible).

> **[CORRECTED 2026-06-03 · DEC-V61-224 takeover audit]** The "NOT the `docker`
> Python SDK (so live execution short-circuits)" claim above is **FALSE** as
> stated: under the project runtime `uv run python -c "import docker"` → 7.1.0
> (importable); only the bare-system `python3` lacks it, which is irrelevant
> since the adapter runs under `.venv`/uv. The **real** W3.2b blocker is a
> runner/image fork: `src/foam_agent_adapter.py` is hardwired to a Foundation
> **OF10** image `cfd-workbench/openfoam-v10:arm64` + container `cfd-openfoam` +
> `/opt/openfoam10/etc/bashrc` — **none present on disk** — and to the ESI-only
> solver name `chtMultiRegionSimpleFoam`, while the only runnable backend
> (`ui/backend/audit/cfdtrust/backends/openfoam.py`) uses Foundation **OF11**
> `openfoam/openfoam11-paraview510` driven by `foamRun -solver <module>` (OF11
> does CHT via `foamRun -solver multiRegion`, never the ESI name). The W3.2a R1
> verification DID run `blockMesh` on the generated case in the ESI
> `opencfd/openfoam-default:2312` image (3 cellZones materialised). See
> DEC-V61-224 §Re-diagnosis. The generation slice itself is unaffected.

Surface scan (V61-088): the generation surface is **extend** — `GeometryType`
enum (`src/models.py`), the geometry dispatch + `_generate_*` family
(`src/foam_agent_adapter.py`), and the `case_family_registry`
(`ui/backend/services/`). R1–prior geometries untouched.

## Decision

Ship the CHT generation side: a new `GeometryType.CHT_MULTI_REGION`, a
`_generate_cht_multi_region()` generator, a geometry-dispatch route with an
**explicit live-run boundary**, and a `cht_steady_laminar_multi_region`
case-family registration. All offline-testable; ZERO Docker / ZERO solver.

### What ships

1. **`GeometryType.CHT_MULTI_REGION`** (`src/models.py`) — geometry-agnostic
   name (chosen over the charter's alternative `PLATE_FIN_HX`, which over-fits
   to one HX instance; the name is reusable for case_002b-class single-stream
   CHT later).
2. **`_generate_cht_multi_region()`** — a **case_011-stripped** canonical CHT
   case: 2 laminar air channels (hot 420 K / cold 300 K) separated by an
   Al-6061 solid plate. Emits `constant/regionProperties` (2 fluid + 1 solid) +
   per-region `thermophysicalProperties` (`heRhoThermo`/const fluid +
   `heSolidThermo`/constIso solid — EXACTLY the shape the W3.0.2 multi-region
   thermo extractor parses) + per-region `0/<region>/{U,p,p_rgh,T}` with
   `compressible::turbulentTemperatureCoupledBaffleMixed` interface BCs
   (NON-radiation — pure-CHT v0.1, charter Q1) + per-region
   `system/<region>/{fvSchemes,fvSolution}` + master `controlDict`
   (`application chtMultiRegionSimpleFoam`).
3. **blockMesh BOX topology, 3 conformal named cellZones** — the fluid↔solid
   interfaces are INTERNAL (shared) faces, so `splitMeshRegions -cellZones`
   (W3.2b) materialises the coupled `<region>_to_<neighbour>` patches the
   `0/<region>/T` BCs reference. This deliberately **sidesteps the
   V90/V92/V94 STL/snappyHexMesh death-chains** case_011 v5b hit — the honest
   v0.1 path (charter W3.0.1 requires only the *extractor* survive those sHM
   forms, not the generator produce them).
4. **Dispatch route + explicit live-run boundary** — `execute()` routes
   `CHT_MULTI_REGION` to the generator + sets `solver_name`, then returns a
   **labelled W3.2b failure** rather than running the single-region
   blockMesh→solver pipeline on a multi-region case (which would emit nonsense /
   V94-class errors). This is the project's mocked-execution-boundary + explicit-
   label discipline: honest, not silent.
5. **`case_family_registry`** — `cht_steady_laminar_multi_region` family +
   skeleton (coupled-baffle wall placeholder) + a CHT gate in
   `helper_candidate_applies` that **MIRRORS simpleFoam** (laminar IS the target
   regime per charter Q4; turbulent CHT deferred). **Steady-only** — transient
   `chtMultiRegionFoam` stays unregistered (charter Q4). Closes the
   **DEC-V61-202-SUB-M31-CYCLE4** deferred-target commitment; flips the W3.0.3
   seam tripwire.

## Load-bearing choices

1. **Generation side ≠ live-run** — drawing W3.2's boundary at generation keeps
   the slice fully offline-testable and avoids shipping untestable execution
   code (the rules-ahead-of-data anti-pattern the W3.1 retro flagged). The
   live-run boundary is explicit + labelled, never silent.
2. **blockMesh box, not sHM-multi-STL** — the honest v0.1 mesh path; sidesteps
   the case_011 death-chains. The generator produces a clean canonical case, not
   an industrial-fidelity replica (that is W3.4 dogfood).
3. **Non-radiation coupled baffle** — `turbulentTemperatureCoupledBaffleMixed`
   (NOT the `Rad` variant case_002b used) — correct for pure-CHT v0.1 (charter
   Q1 radiation scope-out).
4. **Steady-only family registration** — transient `chtMultiRegionFoam` stays
   out (charter Q4); the seam tripwire's transient assertion stays False as the
   intentional cross-workstream marker for a future transient sub-DEC.
5. **Generator output is contract-bound to the W3.0.x extractors** — proven by
   round-tripping the generated case through the REAL `region_properties_reader`
   + `thermo_dict_multi_region` extractors (audit-side region ingestion), not a
   synthetic shortcut.

## Passes-criteria

1. `pytest -q tests/p3/ tests/test_foam_agent_adapter*` → **519 passed** (full
   unscoped, per the W3.1 byte-repro lesson); 19 new CHT tests (14 generation
   in `tests/p3/test_foam_agent_adapter_cht.py` + 5 registry). *(Original draft
   said "516 passed; 17 new" — stale undercount from before the R0/R1 fix
   commits each added a regression test; corrected 2026-06-03 to match HEAD
   `8391973`, whose own commit body records "519 passed".)*
2. Generated case round-trips through the W3.0 regionProperties reader (3
   regions) + W3.0.2 thermo extractor (hot/cold heRhoThermo, solid
   heSolidThermo) — no None payloads.
3. Coupled-baffle BC on BOTH fluid↔solid interfaces; non-rad; fluidThermo /
   solidThermo sides; no `#include` directives (extractor parses every region).
4. Dispatch boundary fires: `execute()` on a CHT spec returns a labelled W3.2b
   failure (success False, non-mock) — never a silent single-region run.
5. `case_family_registry`: family registered, helper applies for laminar /
   rejects turbulent / transient unregistered; pre-commit four-plane contract +
   corpus-drift hooks pass.
6. Codex review chain (round cap 3); residual tracked.

## Governance (DEC-level meta)

- `autonomous_governance: true` (counter +1 on Accept).
- Kogami opt-in: false (sub-DEC; additive generation layer + reversible).
- Codex round cap = 3. Surface-scan-found: `src/foam_agent_adapter.py` +
  `src/models.py` + `ui/backend/services/case_family_registry.py` · extend.
- Four-question gate (generation-side framing): LLM offline ✓ (pure
  deterministic templating) · artifacts canonical ✓ (byte-deterministic file
  generation) · TrustGate-explainable ✓ (no verdict mutation) · advisory-only ✓
  (case_family helper is advisory; no gate change).

## W3.2 follow-up (sibling-DEC contracts defined here)

- **W3.2b** live run — wire `splitMeshRegions -cellZones` into the post-dispatch
  flow + reconcile OF10-vs-ESI (`chtMultiRegionSimpleFoam` is ESI-only; the
  adapter sources `/opt/openfoam10/etc/bashrc`); run ≥1 iteration without
  ±1e+300 (V14). Remove the W3.2a live-run boundary.
- **W3.2c** producer-side — `build_manifest()` emits `manifest["regions"]`;
  run-detail API + TS parity; the `coupled_patches.neighbour_region` extractor.
- **W3.2d** R15/R16 reground — `mesh_present`/`face_zone_present` on RegionSlice
  + a `mesh_summary`→regions parser.

## Ratification

**Accepted 2026-06-03.** Codex chain closed **APPROVE-equivalent at R1** (clean,
round cap=3 not reached) — see `reports/codex_tool_reports/v61_223_w32a_report.md`
(R2/Outcome finalized 2026-06-03). 519 tests green at HEAD `8391973`. Notion sync:
`pending_accepted` → session-end batch. The W3.2b live-run blocker was re-diagnosed
in the 2026-06-03 takeover (see DEC-V61-224): the docker-Python-SDK framing was
incorrect; the true blocker is the OF10/ESI ↔ OF11/foamRun runner fork.

— cfd-chief-engineer, 2026-05-31 · finalized in 2026-06-03 takeover audit

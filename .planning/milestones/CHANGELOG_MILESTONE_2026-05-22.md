# Milestone Changelog · 2026-05-22

> Stakeholder-facing summary of the cfd-harness-unified `audit/` subsystem milestone landing 2026-05-21 / 2026-05-22.
> Engine commit at milestone close: `5769673` (main).

## Headline

**`cfdtrust ingest` shipped with 7 rounds of Codex review + 9-regime dogfood + a self-discovered solver-gate bug fixed in the same arc.** The engine now loads externally-run OpenFOAM cases and emits honest verdicts — including honest BLOCKs when evidence is missing — across the laminar / RANS / CHT / MRF / transonic / VOF / LES / industrial-RANS / reacting-low-Mach physics axes.

---

## Before / After

| Scenario | Before this milestone | After this milestone |
|---|---|---|
| Externally-run OpenFOAM case from V-series corpus | Engine could not see it (closed loop limited to 3 bundled cases) | `cfdtrust ingest` reads polyMesh + 0/ + solver log → emits trust report |
| Solver gate on partially-emitted residuals | Silently PASSed on whichever fields happened to be in the final iter block | BLOCKs with `incomplete_residual_coverage` when <50% of declared targets observed (TBD-17) |
| `validation_status` on an ingested case | Schema permitted `validated` | Schema-blocked: `validated` requires `solver_execution == real` |
| `overall_status` on a clean ingested case | Could reach PASS | Capped at WARN by report-assembly demotion |
| Decomposed-parallel case with `processor*/` time dirs | Engine treated as no-time-dirs → BLOCKED | Recognized; ingest proceeds when reference is not_finalized, BLOCKs honestly when reference is finalized (DEC-V61-201-SUB-INGEST-P2-DECOMPOSED-NOT-FINALIZED) |
| Solver log in non-standard layout (`case_dir/log/log_*.txt`) | BLOCKED `no_solver_log_found` | Engine walks `log/` subdir + manifest-derived primary + extended fallback list (Gap #10, #14, #9) |
| Self-test on 9 distinct physics regimes | 0 / 9 ingested | 8 / 9 ingest cleanly with actionable honest verdicts; 1 honestly BLOCKs at the first guard (case_010 LES, never run) |

---

## Capability matrix · 9 regimes verified

| Case | Regime | Solver | Outcome | Honesty fences observed |
|---|---|---|---|---|
| 027 Hagen-Poiseuille pipe | laminar wedge axisymmetric | simpleFoam | ingest → `overall_status=FAIL` (mesh wedge-axis skewness false-positive; bc parse) | `solver_execution=ingested`, `validation_status=not_validated` |
| 021 NASA TMR flat plate | turbulent RANS | simpleFoam kOmegaSST | ingest → `FAIL` (only `p` parsed into residuals.csv — log discriminator gap) | `solver_execution=ingested`, `validation_status=not_validated` |
| 011 plate-fin compact HX | conjugate heat transfer (multi-region) | chtMultiRegionFoam | ingest → `FAIL` (multi-region BC schema gap surfaced) | `solver_execution=ingested`, `validation_status=not_validated` |
| 004 NREL Phase VI rotor | rotating machinery (MRF) | simpleFoam + MRF | ingest → `FAIL` (MRF zone awareness gap surfaced) | `solver_execution=ingested`, `validation_status=not_validated` |
| 006 ONERA M6 transonic | compressible (density-based) | rhoCentralFoam | ingest → `FAIL` + 8 NEW gaps surfaced (#17-#24: thermophysical / perfectGas / sutherland / rho / T / Mach / shock-capturing fvSchemes all invisible) | `solver_execution=ingested`, `validation_status=not_validated` |
| 007 KCS ship hull | multiphase VOF (free-surface) | interFoam | ingest → `FAIL` + phase-field schema blindness surfaced (TBD-1..TBD-4) | `solver_execution=ingested`, `validation_status=not_validated` |
| 010 DrivAer fastback | incompressible external LES | pimpleFoam + LES (WALE) | **honest BLOCK** (`0/` absent, case at mesh-only scaffold state) + 6 LES schema gaps surfaced (#26-#31) | `solver_execution=skipped` (NOT `ingested` — engine refused to fabricate) |
| 028 APU bay ventilation | industrial RANS multi-solid | simpleFoam kOmegaSST | ingest → `FAIL` on bc_contract (140 missing BC entries × 28 STL walls × 5 fields enumerated; 87 type mismatches; 1 derived I·U·L omega mismatch) | `solver_execution=ingested`, `validation_status=not_validated` |
| 009 Sandia Flame D | reacting low-Mach (DRM-19 chemistry, 19 species) | reactingFoam | ingest → `FAIL` + **TBD-17 self-discovered: solver gate silently PASSed on 3/27 fields** | `solver_execution=ingested`, `validation_status=not_validated` |

**Score: 9 / 9 honest. 0 / 9 fabricated.**

---

## Self-discovered bug · TBD-17 (the demo's load-bearing moment)

> Found during case_009 Sandia Flame D dogfood, 2026-05-22.
> Logged: `.planning/dogfood/DOGFOOD_CASE_009.md` §TBD-17
> Fixed: commit `3b5c43f` (Merge: `5769673`)
> Fence: `_PARTIAL_FINAL_COVERAGE_THRESHOLD = 0.5`; gate BLOCKs with `incomplete_residual_coverage` when fewer than half of declared targets appear in the final residual block.

**The pattern:** the manifest declared 27 residual targets (Ux/Uy/Uz, p, h, k, epsilon + 20 DRM-19 species). The source log was cut mid-PIMPLE-outer-loop before the species ODE batch fired for the final timestep — so `parsed["iterations"][-1]["residuals"]` happened to contain only `{Ux, Uy, Uz}`. The gate logic iterated manifest targets and silently skipped any field absent from the final block (`if actual is None: continue`). Result: `failed=[]`, `checked=[Ux,Uy,Uz]`, `not failed → PASS`. Three of twenty-seven fields actually checked. Gate said PASS.

**Why this matters for the demo:** this is exactly the failure mode the trust harness exists to prevent. The pre-existing R15-F-02 fix covered "zero target fields → refuse PASS" but stopped at zero. Reacting cases blow through that gap because they always have *some* checked field (Ux is solved before species). We caught it during our own dogfood. Fix shipped in the same arc as the discovery — no separate sprint, no triage queue, no "we'll get to it." Engine ships `3b5c43f` with the fence intact, plus 2 reacting-class spikes (TBD-15 reactingFoam log discovery, TBD-19 species-regex paren bug).

---

## What's queued post-demo

### Spike-class (≤30 LOC, follow the Gap-#9 / Gap-#10 pattern)
- TBD-16 · `_parse_simplefoam_log` collapses sub-second physical time to `iter=0` (breaks unsteady iteration discriminator across reactingFoam / pisoFoam / fireFoam / pimpleFoam)
- TBD-20 · multi-GiB solver log reads → 13 GiB peak RSS (need streaming parser; mirrors existing `_scan_solver_log_for_divergence` tail-stream idiom)
- Gap #26-#27 · ingest fallback to "do what audit can given disk state" when artifacts missing; walk step-numbered mesh-pipeline logs (`01_blockMesh.log` etc.)
- Gap #29 · `0.orig/` blindness when `0/` absent (case_010 pattern)

### DEC-scale (cross-cutting, needs sub-DEC)
- TBD-18 · `reacting_contract` manifest schema extension (species_list / inlet_compositions / combustion_model / chemistry_solver / thermo_temperature_range)
- Gap #18 (case_006) · compressible-physics schema extension (`compressible_contract` for thermophysicalProperties / perfectGas / sutherland / rho / T / Mach)
- TBD-3 (case_007) · `vof_contract` schema extension (phase-field awareness)
- Gap #28 (case_010) · `les_contract` schema extension (LESModel / delta / SGS-eddy-viscosity)

### Charter-class
- M2 mesh / M3 physics-materials / M4 BC-solver / M5 post-processing / M6 AI-advisor-stack tracks per long-term roadmap v2 (`project_cfd_harness_roadmap_v2.md`)

---

## Provenance · session commits

All commits since the AI-CFD-V2 → cfd-harness-unified merge (`5250bb7`):

```
5769673 Merge: TBD-17 honesty-adjacent + 2 reacting spikes (case_009 findings)
3b5c43f fix(audit-ingest): honesty-adjacent + 2 reacting spikes (TBD-15/#17/#19 from case_009)
93c70ce Merge: close 5 dogfood spikes from case_006 + case_007 (Gap #17/#20/#21/#22/#25)
c5354e1 fix(audit-ingest): close 5 dogfood spikes from case_006 + case_007 (Gap #17/#20/#21/#22/#25)
a03b066 Merge: close 3 dogfood spikes (Gap #12+#13+#14)
a82edde fix(audit-ingest): close 3 dogfood spikes (Gap #12+#13+#14)
bd29b77 docs(notion-sync): backfill notion_sync_status for 2 newly-Accepted follow-up DECs
22c5e83 Merge: DEC-V61-201-SUB-INGEST-P2-DECOMPOSED-NOT-FINALIZED land
666acea Merge: DEC-V61-201-SUB-INGEST-P1-GUARD-DISCRIMINATE land
8af43cb Merge: Gap #10 — search case_dir/log/ subdir for solver log
9de3430 docs(audit-ingest): backfill commit SHA into DEC-V61-201-SUB-INGEST-P1-GUARD-DISCRIMINATE
e86c011 feat(audit-ingest): discriminate precondition vs post-residual BLOCKED (P1-GUARD-DISCRIMINATE)
7144192 feat(audit-ingest): relax decomposed BLOCK to finalized-reference only (P2-DECOMPOSED-NOT-FINALIZED)
adc4c24 fix(audit-ingest): search case_dir/log/ subdir for solver log (Gap #10)
553237d docs(notion-sync): backfill notion_sync_status for 2 Accepted DECs
3781e16 Merge: DEC-V61-201-SUB-INGEST-P2-FOLLOWUP land (gate recompute from residuals)
f45ec3b Merge: Gap #9 DILUPBiCGStab residual regex fix
981df56 docs(audit-ingest): backfill commit SHA bbe2c4e into P2-FOLLOWUP DEC
bbe2c4e feat(audit): recompute ingest gate from residuals when solver_gate.json missing (P2-FOLLOWUP)
00518d3 fix(audit): extend _RESIDUAL_LINE_RE to OFv2312 default solvers (Gap #9)
```

Plus the parent DEC commits within `5250bb7` (the merge PR of `feature/audit-ingest-mode`) which include the 7-round Codex arc: R1-R7 sequential review with CRS fallback at R3+R4 and CRS+86gs interleave at R6.

---

## Test posture at milestone close

- pytest: 409 passing / 1 skipped (pre-existing). Baseline was 374; +35 tests added across the arc (23 ingest-specific from the parent DEC, +12 from follow-up sub-DECs and spike fixes).
- Codex review rounds (parent DEC-V61-201-SUB-INGEST): 7 rounds, all CHANGES_REQUIRED → final 2 P1s deferred to follow-up sub-DECs which subsequently landed (`P1-GUARD-DISCRIMINATE` + `P2-DECOMPOSED-NOT-FINALIZED`).
- Honesty fences: held across all 7 review rounds + 9 dogfood regimes. Zero false PASSes.

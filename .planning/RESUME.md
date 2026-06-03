# RESUME.md · cfd-harness-unified next-session pickup

> ## ⏩ MOST RECENT — P3 W3.3b CONJUGATE BENCHMARK LIVE PASS → runnable-coverage 1→2 FLIPPED (read first)
>
> **Status**: `P3_IN_PROGRESS`. **HEAD = the W3.3b coverage-flip commit this session
> (DEC-V61-228); run `git log -1`.** **runnable-coverage 1→2 FLIPPED** — the full
> two-region conjugate Gnielinski benchmark passes its 10% tolerance gate
> end-to-end. CHT is now the 2nd runnable+validated compute type (Blueprint v4 Law 1).
>
> **W3.3b (DEC-V61-228) LANDED.** A FULL two-region conjugate solve where the FLUID
> flow PRODUCES h (vs W3.3a, which validated only the solid side + an IMPOSED Robin
> h). foamMultiRun (OF11 **Foundation** fork — `regionSolvers {fluid; solid}`,
> `coupledTemperature` interface from `splitMeshRegions -cellZones`; reconciled per
> DEC-V61-224, not the ESI `chtMultiRegionSimpleFoam` the charter first named).
> - **LIVE RESULT (Re=50000, resolved y+~0.8 mesh, mapFields restart):**
>   `Nu_solve = 113.21` vs `Nu_Gnielinski = 104.7987` → **+8.0% (INSIDE 10% band)**;
>   energy balance `|Q_iface − ṁcp·ΔT| = 0.977 W = 2.12%` of Q_iface (<5% hard gate);
>   Re=50000 in band; h_produced=59.55 W/m²K. The +8% is the REAL, honestly-reported
>   kOmegaSST+const-Prt internal-HT bias — within band at Re=50000.
> - `src/cht_conjugate_extractor.py` (**Execution** plane, PURE): parse
>   `postProcessing/*/surfaceFieldValue.dat` → `h = q_wall/(T_wall − T_bulk_window)`,
>   `Nu = h·D_h/k`, T_bulk from a cumulative wall-heat energy balance + cup-mixing
>   outlet T. Nu from raw solver output + inputs only (NEVER the Gnielinski form →
>   anti-tautology), fail-closed on missing/NaN/non-physical dT.
> - `src/cht_conjugate_gate.py` (**Control** plane): `gate_conjugate_against_gold()`
>   extract → `ResultComparator.compare()` vs Gnielinski gold + **2 HARD gates**:
>   energy-balance closure (≤5% of Q_iface) AND Re-in-validity-band (3e3–5e6).
> - gold `cht_pipe_gnielinski.yaml`: re-anchored Re 10000→50000, `contract_status →
>   LIVE_RUN_PASS_W3.3b_B`; self-verifying `test_cht_pipe_gnielinski_gold.py`
>   re-derives 104.7987 from Re/Pr (fails on drift). `_plane_assignment`+`.importlinter`
>   already carried both modules (lint-imports **5/5 KEPT**).
> - `tests/p3/test_cht_conjugate_gate.py` (**9 green**): offline replay of
>   `_w33b_pipe_probe` → gate PASS; anti-cheat (doctored qWindowAvg → Nu out of band
>   → FAIL; doctored TbulkOut → energy hard-gate FAIL; out-of-band Re → FAIL);
>   extracted Nu ≠ gold ref yet within 10%; missing input → raise. **362 p3 + 1 skip.**
> - Frozen converged-tail artifacts: `reports/showcase_aero/_w33b_pipe_probe/` — a
>   proper case dir (postProcessing = gate replay source; constant/fluid/physicalProperties
>   = the case fluid the gate reads; system; 0; REPRODUCE.md).
> - **Codex CRS chain (effort=high, 86gs hung)**: R0 2 findings [P2 Re read from gold
>   YAML; P3 no Pr gate] → fix `2969ede` (derive Re from solved mdot+area; add Pr
>   hard gate). R1 2 findings [P1 mu read from gold; P2 Pr read from gold] → fix
>   reads ALL fluid transport props (mu/cp/k/Pr) from the CASE `physicalProperties`
>   + adds a fluid-matches-gold hard gate. Gate now has 4 hard components; still
>   PASSES (6/6 checks green). **R2 APPROVE — chain CLOSED within cap=3 (0 findings).**
>   Report: `reports/codex_tool_reports/v61_228_w33b_conjugate_report.md`.
>
> **RE-ANCHOR rationale (DEC-V61-228, user decision "Re-anchor at higher Re"):** a
> baseline Re=10000 conjugate solve over-predicted Gnielinski **+17%** —
> energy-consistent, fully-developed, NOT a bug — a known low-Re RANS+const-Prt
> internal-HT bias at the turbulent edge → documented **NO-GO**. Re=50000 is
> mid-turbulent where both the closure and the correlation are robust. Principled
> fix to a weak validation point: 10% tolerance NOT loosened, reference re-derived
> not transcribed, result NOT engineered to pass.
>
> **NEXT (Notion + follow-ons)**:
> - **Codex review chain DONE** — CRS cap=3, R0→R1→R2 APPROVE (commits 40420ab →
>   2969ede → 5e026cb). Gate hardened to read fluid props from the replayed case.
> - **Session-end TODO**: Notion batch-sync Accepted DEC-V61-224/225/226/227/228.
>   Commits are LOCAL on `main` (not pushed — push is a user call).
> - Follow-ons: live-through-adapter dispatch for the conjugate case (currently
>   gated offline from frozen artifacts); buoyantFoam→OF11 deferred guard; P4
>   (rhoCentralFoam / ONERA M6) is the next compute type per the risk-first path.
>
> ---
>
> ## ✅ PRIOR — P3 W3.2b LANDED + Codex CLOSED + Workflow Monitor SHIPPED + W3.3a live-validated
>
> **Status**: `P3_IN_PROGRESS`. **HEAD = `7bb84b4`**. **runnable-coverage STILL 1**
> (W3.2b proves CHT+RANS RUN through the adapter; formal 1→2 needs the **W3.3** V&V
> benchmark tolerance gate).
>
> **W3.2b (DEC-V61-225) LANDED + Accepted.** The whole `foam_agent_adapter` exec
> path is reconciled to OF11 (RANS + CHT). Commits: feat `2aa0297` → `8bdea61`
> (CRS R0: regionProperties comment-anchor + buoyantFoam honest-BLOCK) → `462128f`
> (86gs R0 P2: honor `mesh_already_provided`, M6.1 parity) → `6617098` (CRS R1 P1:
> CHT mesh+solve in a **single `_docker_exec`** under `set -e` — removes the
> implicit cross-call put_archive merge dependency). **LIVE OF11 CHT gate PASS
> 9.17s** (`CFD_LIVE_OF11=1`); 334 p3 + 200 adapter green. Codex CRS R0→R2 (86gs
> hung → CRS); **R2 P1 "buoyantFoam regression" ADJUDICATED false-premise**
> (pre-W3.2b adapter sourced a nonexistent `/opt/openfoam10/etc/bashrc` → every
> adapter solve was already dead per DEC-V61-224; `buoyantFoam` absent in OF11;
> guard = honest BLOCK, tested intended; reverting = re-introduce R0 cryptic-fail)
> + **USER-RATIFIED 维持现状**. `buoyantFoam`→OF11 = logged deferred follow-up.
>
> **Workflow Monitor (DEC-V61-226) SHIPPED.** User pivot: "visible/resumable/
> traceable CFD workflow runtime". Chief-eng **REJECTED Trigger.dev** (north-star
> conflict [local-first/offline/auditable] + Python↔TS seam + the 6 stages already
> exist as backend routes + the proposal's "mock that pretends to solve" honesty
> risk); built **in-house** on FastAPI+SSE+React. MVP-1 frontend mock-first
> (`cef6ccd`, `ui/frontend/src/pages/workflow_monitor/` — OUTSIDE §11.1 freeze,
> indelible isMock banner) → **real backend** (`3e63372`: `schemas/workflow.py`
> camelCase Pydantic · `services/workflow_monitor.py` assembles a `WorkflowRun`
> from REAL `reports/showcase_aero/naca0012_showcase_a*/run_record.json`,
> `is_mock=False`, honest report gate keys on the recorded `converged` flag NOT a
> cl%-drift [7747% artifact at α=0] · `routes/workflow_runs.py` GET list/run + SSE
> events, run_key resolved vs the discovered set = no traversal · frontend
> `WorkflowMonitorRoute` react-query + honest mock-fallback). Backend 5/5 +
> frontend 8/8 + `tsc -b` pass; real-data page rendered headless (no mock banner).
> Showcase fixtures committed `7bb84b4` (run_record.json; 21MB raw logs gitignored).
>
> **W3.3 ARC OPENED** (the V&V gate that flips coverage 1→2): research+plan
> `12224f6` (`.planning/p3_w33_cht_benchmark_research.md`) → **user ratified W3.3a**
> (analytical solid-side first) → W3.3a benchmark CONTRACT landed `d2ffbc7`
> (`knowledge/gold_standards/cht_straight_fin.yaml` — analytical straight-fin
> η=0.77402 / tip-ratio=0.66604, Incropera-cited; **self-verifying** test
> `tests/p3/test_cht_straight_fin_gold.py` re-derives from inputs, 4/4, so the
> reference can't drift or be fabricated). `contract_status =
> ANALYTICAL_REFERENCE_AUTHORED · LIVE_RUN_PENDING` — does NOT yet flip coverage.
>
> **W3.3a LIVE-VALIDATED** `84ce01d` (ultracode): a 4-agent design workflow
> (`wuep5hxdl` — 3 doc-grounded OF11 designers + judge; caught the ESI→OF11 BC
> rename `externalWallHeatFluxTemperature`→`externalTemperature`) produced the
> case; I ran it in `cfd-openfoam`; an adversarial-verify workflow (`wi98g7czg` —
> 3 skeptics + judge) returned **CONFIRMED_WITH_CAVEATS · trustworthy**. Live
> `foamRun -solver solid` (constSolidThermo kappa=180, 100×2×2 hex, Robin fin BC,
> adiabatic tip, e-resid 7.83e-9): **fin_efficiency 0.77354 vs 0.77402 = 0.063%
> PASS · tip_ratio 0.66622 vs 0.66604 = 0.028% PASS**, energy-conserving. Not
> circular/fabricated (self-verify test is the honesty lock; dual-channel
> flux+temp consistency; Bi=8.3e-4). `contract_status →
> SOLID_SIDE_LIVE_VALIDATED · CONJUGATE_FLIP_PENDING_W3.3b`. Evidence:
> `.planning/intel/p3_w33a/fin_probe_evidence.md` +
> `reports/showcase_aero/_w33a_fin_probe/` (dicts + logs + postProcessing .dat).
> **runnable-coverage STILL 1** (solid-side validated; the formal 1→2 flip needs
> W3.3b, fluid-produced h).
>
> **NEXT (W3.3a gate-wiring — production code, its OWN feat→Codex chain)**:
> (a) CHT QoI extractor (parse Q_base/T_tip → fin_efficiency/tip-ratio) mirroring
> `ui/backend/audit/cfdtrust/audit/qoi.py`; (b) register `gate_mode:
> cht_analytical` in `src/auto_verifier/gold_standard_comparator.py` (reuse
> `compare()` + G-gates); (c) coverage test asserting the live PASS (mirror
> `tests/test_e2e_mock.py:75`). Then **W3.3b** (full conjugate vs Gnielinski)
> flips coverage 1→2. **Other tracks**: Workflow Monitor live-NEW-run runner ·
> buoyantFoam→OF11. **Session-end TODO**: Notion batch-sync Accepted DECs
> V61-224/225/226.
>
> **Infra note**: the OF11 `cfd-openfoam` container is left running (intentional).
> Pre-existing dev servers :8000 (backend, STALE — predates the workflow-runs
> route) + :5188 (vite) are running; a fresh restart picks up the new route.
>
> ---
>
> ## Earlier — P3 W3.2a LANDED + 2026-06-03 TAKEOVER RE-ASSESSMENT
>
> **Status**: `P3_IN_PROGRESS`. **HEAD = `8391973`**. **runnable-coverage STILL 1.**
>
> **W3.2a (DEC-V61-223, CHT runner-wire GENERATION side) is LANDED + finalized.**
> Shipped: `GeometryType.CHT_MULTI_REGION` (`src/models.py`) +
> `_generate_cht_multi_region()` (`src/foam_agent_adapter.py` — case_011-stripped
> canonical CHT: 2 laminar air channels + Al solid plate, `regionProperties` +
> per-region `heRhoThermo`/`heSolidThermo` thermo + non-rad coupled-baffle BCs +
> master `controlDict`) + `cht_steady_laminar_multi_region` case-family + an
> **honest fail-loud live-run boundary** (`success=False, is_mock=False`, labelled
> `W3.2b`, fires for fresh AND imported mesh). **519 tests green**; the generator
> round-trips through the REAL W3.0.x extractors (not mock). Codex **APPROVE-
> equivalent, clean close at R1** (R0 86gs xhigh 1×P1+2×P2 → R1 CRS high 1×P2
> fixed + 1×P2 **disproven** by running `blockMesh` in ESI
> `opencfd/openfoam-default:2312` → "Writing polyMesh with 3 cellZones"); cap NOT
> reached. **DEC-V61-223 → Accepted** (finalized in 2026-06-03 takeover; report
> R2/Outcome filled; STATE ANCHOR-32 added).
>
> **🔴 THE BLOCKER (re-diagnosed in the 2026-06-03 takeover · DEC-V61-224)**: P3's
> exit gate (run CHT end-to-end → coverage 2) is **environmentally/architecturally
> unreachable as wired**. DEC-223's "missing docker Python SDK" claim is **FALSE**
> (`uv run python -c "import docker"` → 7.1.0). The REAL root is a **two-backend
> runner fork**: `foam_agent_adapter` (the charter's chosen path) is hardwired to a
> **nonexistent Foundation OF10** image (`cfd-workbench/openfoam-v10:arm64` +
> `/opt/openfoam10/etc/bashrc`) + the **ESI-only** solver name
> `chtMultiRegionSimpleFoam`; meanwhile the ONLY backend that actually runs
> (`ui/backend/audit/cfdtrust/backends/openfoam.py`, which produced
> runnable-coverage=1) uses **Foundation OF11** `openfoam/openfoam11-paraview510`
> via `foamRun -solver <module>` (OF11 does CHT via `foamRun -solver multiRegion`,
> never the ESI name). The charter wired its exit gate to the rotten path.
>
> **NEXT = USER DECISION (forward W3.2 PAUSED)**: **A** = reconcile
> `foam_agent_adapter` → OF11 + `foamRun -solver multiRegion` (image already on
> disk; cfdtrust already drives it) → run W3.2a's generated case end-to-end →
> legitimately flip coverage 1→2 + dissolve the fork. **B** = keep building offline
> (W3.2c producer-side / W3.2d R15-R16 reground), freeze coverage=1, add a
> remote/CI runner to the blueprint. **Latent-risk check before either**: confirm
> whether coverage=1 (RANS) even executes through `foam_agent_adapter` in THIS env
> — it was validated via `cfdtrust`, NOT the adapter, whose wired image is absent.
> Blueprint v4 §4 amended with a solver-environment/image-reconciliation provision
> (P4 rhoCentralFoam + P4+ VOF/LES hit the same wall). See DEC-V61-224.
>
> **Pending session-end**: Notion sync of Accepted DEC **`V61-223`** (and the new
> `V61-224` once it lands) — `notion_sync_status: pending_accepted`.
>
> ---
>
> ## Earlier — P3 W3.1 CHT v9 RULES LANDED (DEC-V61-222) (2026-05-31)
>
> **Status**: `P3_IN_PROGRESS`. HEAD = `97b2ca6`. W3.1 (CHT v9 rule distillation,
> `DEC-V61-217` W3.1) LANDED via a 4-commit Codex chain (`6adce39` rules → `e1d2f13`
> deriver adapter → `27913a5` defer R15/R16 → `97b2ca6` revert UI wiring).
>
> **What shipped (14 rules total, v9.4.0)**:
> - **R13 `COUPLED_INTERFACE_DANGLING_REF`** ← `coupled_patches[].neighbour_region`
>   vs region inventory. Catches **V94** (dangling coupled ref → "Cannot find
>   patchField entry"). *Regrounded* from the charter's unsound "wall-coupling-type-
>   mismatch" (red-team killed: false-fired on healthy mixed-physics + dead code).
> - **R14 `PER_REGION_THERMO_MISSING`** ← `thermo_type`+`thermo_snapshot_ref` both
>   None. Catches **V14/V92** (region declared, no per-region thermo payload).
> - **Deriver-path reachability**: `derive_slice_from_manifest()` reads
>   `manifest["regions"]` via bulletproof-graceful `_regions_from_manifest()`
>   (106-case crash-safe; production-path proven through real `matches_for_manifest`).
>   This DEFINES the `manifest["regions"]` contract W3.2 emits.
>
> **DEFERRED → W3.2** (Codex R1 cross-artifact finding — the frozen schema carries
> DECLARED topology, not produced-mesh presence): **R15 CONDUCTION_DOMINANCE** (kind
> from regionProperties ≠ mesh-loss) + **R16 FACE_ZONE_LOSS** (shm_snapshot_ref=None
> = "extruded", not "lost" — false-fires on healthy case_002b). Both need a per-region
> mesh-presence field. UI live-card path REVERTED (Codex R2 — run-detail API doesn't
> emit regions); the full UI/producer flow is one coherent W3.2 unit.
>
> **Codex chain**: R0→R1→R2 all CHANGES_REQUIRED on converging producer-side layers
> (one root: production reachability needs W3.2). Round cap=3 reached. 2 user
> adjudications (charter-trigger R1 + round-cap R2). R2 P1 ratified W3.2-deferred →
> `codex_round3_overflow_w31.md`. ALL rounds on CRS (86gs **5-for-5 unavailable** this
> session — recommend CRS-primary routing DEC). 448 p3+v9 tests green · tsc clean.
>
> **NEXT = W3.2** (runner-wire · `DEC-V61-217` W3.2 · gated on W3.0.6, now also needs
> W3.1's deriver contract): `foam_agent_adapter` CHT dispatch + new `GeometryType` +
> `case_family_registry` chtMultiRegion family + generator producing `regionProperties`
> + per-region `0/<region>` + per-region thermo + master `controlDict`. **PLUS the
> W3.1 follow-up the chain deferred**: (a) `build_manifest()` emits `manifest["regions"]`
> from the W3.0.x extractors; (b) run-detail API (`run_history.py` + `get_run_detail()`)
> emits regions + re-add the UI adapter carry-through; (c) add a `RegionSlice`
> produced-mesh-presence field → reground + re-ship R15/R16; (d) integration test:
> a real multi-region bundle fires ≥1 CHT rule end-to-end. See DEC-V61-222 §W3.2-followup.
>
> **Pending session-end**: Notion sync of Accepted DECs `V61-219`/`V61-220`/`V61-221`/
> **`V61-222`** (verify `V61-218` synced) — all `notion_sync_status: pending_accepted`.
>
> ---
>
> ## Earlier — P3-PREP ARC COMPLETE (W3.0/.0.1/.0.2/.0.3/.0.6) (2026-05-30)
>
> **Status**: `P3_IN_PROGRESS`. HEAD = `32e5397`. P3 CHT charter `DEC-V61-217`
> Accepted. **The ENTIRE P3-prep arc is COMPLETE** — the readers + the frozen
> slice contract W3.1 consumes, all landed this session:
> - **W3.0** `regionProperties` reader (DEC-V61-218, `7cdb870`) — the PIVOT snapshot.
> - **W3.0.1** `shm_dict` multi-region (DEC-V61-219, `781c335`) — cellZone-TOKEN-keyed.
> - **W3.0.2** `thermo_dict` multi-region (DEC-V61-220, `e733fae`) — fluid+solid;
>   Contract A required-field refusal.
> - **W3.0.3** `solver_block` CHT regression (SPIKE, `a03e4ec`) — zero extractor change.
> - **W3.0.6** multi-region `RunArtifactSlice` (DEC-V61-221, `32e5397`) — RegionSlice
>   + CoupledPatch nested dataclasses + `regions` field; Python↔TS parity restored;
>   **clean Codex APPROVE at R2**. The frozen contract W3.1 R13–R16 consume.
>
> **NEXT (the actual rules phase · bigger · surfaced for user greenlight)**: **W3.1**
> — CHT v9 rule distillation. Distill **3–4 advisor rules R13–R16** from V-series CHT
> death-chains (V14 sentinel ±1e+300 · V15 limitTemperature clamp · V63-A/V93/V94
> face-zone loss · V90 locationsInMesh · V92 cellZoneInside · case_011 v5b conduction-
> dominance). Candidates: R13 wall-coupling-type-mismatch ← `coupled_patches[].coupling_type`
> · R14 per-region-thermo-missing ← `thermo_type`/`thermo_snapshot_ref` · R15
> conduction-dominance ← `kind` · R16 face-zone-loss ← `shm_snapshot_ref`. Each rule:
> offline-runnable (Law 3) · names ≥1 V-row it would have caught · fires on synthetic
> CHT fixtures · silent on healthy cases · four-question gate per rule · Codex APPROVE.
> Mirrors the W2.1 distillation pattern (DEC-V61-216). Bigger than the W3.0.x schema
> work (it's rule LOGIC + V-series evidence) — worth a target/plan checkpoint.
>
> **Pending session-end**: Notion sync of Accepted DECs `V61-219` + `V61-220` +
> `V61-221` (verify `V61-218` already synced) — `notion_sync_status: pending_accepted`.
>
> ---
>
> ### Earlier this session — W3.0.2 detail
>
> **What shipped (W3.0.2)**: `ui/backend/services/case_extractors/thermo_dict_multi_region.py`
> (`extract(case_dir, region_snapshot) -> Mapping[str, RegionThermoSnapshot | None] | None`,
> keyed by every UNIQUE region) + 3 p3 test files + 1 single-region regression pin +
> `__init__` re-export (SIX→SEVEN). **EXTENDED for solid thermo** (heSolidThermo/
> constIso kappa/rhoConst rho), not a fluid-only wrapper. Two invariants: kind from
> snapshot membership ONLY (never name inference) + **Contract A** (required-field-
> absent → region None, symmetric with single-region; required = molWeight+Cp+complete
> fluid transport; solid kappa/rho optional). The reused single-region leaf scanners
> were **hardened at root** (`_strip_nested_blocks` — fixes a latent nested-
> `thermoType.type`-leak fabrication that affected single-region too;
> `tests/test_thermo_dict_extractor.py` +2 regression pins).
>
> **Governance (W3.0.2)**: 2-lens `test-red-team` caught **P1×3** (solid-kappa
> gating + nesting-depth discriminator leak ×2) fixed pre-Codex. Codex chain
> **R0(2×P2)→R1(2×P1)→R2(1×P1) cap=3** on 86gs xhigh(R0) then **CRS gpt-5.4 high**
> (86gs stream-failed mid-R1, effort xhigh→high logged) — all findings fixed+pinned;
> R2 fixed at cap (consult tool errored twice; W3.0.1 precedent). Chain report
> `reports/codex_tool_reports/v61_220_chain_report.md`; overflow
> `.planning/retrospectives/codex_round3_overflow_w302.md`. confidence:med. 153
> p3+single-region green; 308 case-extractor surface pass — no regression.
>
> **Prior (W3.0 + W3.0.1)**: `region_properties_reader.py` (DEC-V61-218, the PIVOT
> snapshot) + `shm_dict_multi_region.py` (DEC-V61-219, master-sHM cellZone-derived,
> region found by cellZone TOKEN not surface entry name — anti-circularity). Both
> Accepted, stdlib-only, honest-refusal. See ANCHOR-26/27 in STATE.md.
>
> **NEXT P3 work items** (charter dependency order):
> - **W3.0.3** — `solver_block_extractor` CHT regression (SPIKE · zero code change ·
>   ≤30 LOC test-only): confirm `chtMultiRegionSimpleFoam` is reported from
>   case_002b/case_011-shaped controlDicts. **NEXT.** Likely spike-class (/goal
>   Pattern C): if truly test-only ≤30 LOC, skip DEC/Codex/Kogami/Notion (echo
>   "skipped: spike-class") — but if it surfaces a real `solver_block_extractor`
>   gap (a missing CHT solver token), it escalates to a sub-DEC + Codex.
> - then **W3.0.6** — multi-region `RunArtifactSlice` (3+ nested dataclasses;
>   `regions: list[RegionSlice]`) — **MUST precede W3.1 CHT rule distillation**.
> Same workflow→Codex→commit loop. **Carry-forward checklist** (compress the
> ~3-round Codex floor — every W3.0/W3.0.1/W3.0.2 round hit one of these): enumerate
> UP FRONT (a) malformed-input, (b) ambiguous/duplicate-source, (c) nesting-depth
> (line-anchored vs brace-depth), (d) **NEW from W3.0.2** — *wrapper refusal-bar
> parity* (does the wrapper's required-field bar match the wrapped extractor's?
> pin a region-None test per required field) + *map-key uniqueness* (dedup names
> drawn from ≥2 source lists). For association parsers, ≥1 fixture where the join
> key ≠ the entry key, else the test is circular.
>
> **Notion**: DEC-V61-218 + V61-219 + V61-220 all `pending_accepted` — session-end batch.
>
> ---
>
> **Generated**: 2026-05-24T20:30 local (session-end checkpoint)
> **Last DEC commit**: `1ccb4b3` (M32 cycle 3 DEC close)
> **Updated**: 2026-05-25T11:10 — **M3.2 → M3.8 SEVEN MILESTONES CLOSED** in one continuous run.
> **Updated**: 2026-05-25 (continuation) — **M3.9 → M3.14 SIX MORE MILESTONES CLOSED**, then **PUSHED to origin/main** (`f8c895d` → `5b3978d`; local == origin).
> The push tripped the `codex-cadence` pre-push floor (84 commits since last Codex trailer). Cleared it the honest way: ran `codex-review-relay --base 2648adf` (86gs gpt-5.4 xhigh) on **this session's** delta → **R0 found 3 REAL bugs** (vtk partial-window leak · M3.13 gate missed tsconfig·json · spot-check `localhost` IPv6 trap) → **R1 verbatim fixes** (`5b3978d`, carries `Codex-verified: RESOLVED` trailer) → push passed. Prior-session 70817a0..2648adf not re-reviewed (its spike-class call).
> **CI GREEN on origin/main** (run 26386645089): Frontend tsc+vite build ✓ · Backend pytest py3.12 ✓ (3m33s). Whole arc validated end-to-end on remote. (Unrelated: the "§11.2 Sampling Audit Reminder" workflow fails-by-design when an audit is due — pre-existing governance cron, not this arc.)

---

## ⏩ CONTINUATION SESSION 2026-05-25 (M3.9 → M3.12) — read this first

**Worktree note (cost the session some discovery time — pinned so you don't repeat it):**
`main` is checked out in the **`/Users/Zhuanz/Desktop/cfd-audit-merge`** worktree,
NOT `~/Desktop/cfd-harness-unified` (that path had branch `codex/v4-import-blueprint-fidelity`).
Work M3.x here.

**4 milestones, all single-cycle, all spike/sub-DEC (0 DEC files · 0 Codex · 0 Kogami):**

| M | What | Commits |
|---|---|---|
| M3.9 | B4 left-rail dead-space closed **WON'T-FIX (BY-DESIGN)** via industrial-ui-comparator (8/10, top-anchored-tree = industry norm) + hardened `workbench_visual_spot_check.mjs` with `--base-url`/`--port` (was hardcoded :5173, now defaults :5180 per vite.config) | `f8c895d` `27ba80e` |
| M3.10 | **vtk.js proxy bug root-fix** — `detectWebGL()` + typed `WebGLUnavailableError` in new `webgl_support.ts`; guard at `createKernel` chokepoint; ViewportV4 catches → graceful badge. Real-browser before/after PROVEN (4 Proxy crashes → 0). Removes hard dep on `--use-gl=swiftshader`. | `89ebd82` `dc96286` |
| M3.11 | **Unblocked `tsc -b` build** — pre-existing error at `TopBarV4.tsx:67` (left by the 7-milestone session; no frontend tsc gate caught it). Widened `useEffectiveCaseId` activeStep to `\| undefined`. | `06448b1` `47db1b6` |
| M3.12 | Completed M3.10 root-fix to legacy `Viewport.tsx` (defensive — that component is currently unrouted per App.tsx; honest disposition in retro). | `b4564f7` + retro |
| M3.13 | **Frontend `tsc -b` pre-commit gate** (`DEC-V61-203`, **Accepted · user-ratified "A"** · synced to Notion). Blocks red-build commits; closes the gap that caused M3.11. Verified clean→Pass / type-error→Fail / live commit self-skips on non-frontend. | `f6e06c4` + retro |

**Visual-audit backlog now FULLY DRAINED** (B1/B2/B3/B5/B6 closed M3.4; B4 closed M3.9).

**Live services this session** (reuse if still up): backend `uvicorn :8001` (run from repo
root: `uv run uvicorn ui.backend.main:app --port 8001`); vite `:5188` (`CFD_FRONTEND_PORT=5188
CFD_BACKEND_PORT=8001 npm run dev`). ⚠️ A **stale StructureOptimizer `vite preview` squats
IPv6 `[::1]:5180`** — do NOT kill it; use explicit `127.0.0.1:<port>` + a fresh port.

**CI mirror — DONE/MOOT (M3.14 verified):** CI already has a `frontend-build` job
(`ci.yml:155-178`) running `npm run typecheck` + `npm run build` (both run tsc) on push-to-main
+ PRs. No CI change needed. The M3.11 slip's real cause was the branch being ~87 commits
unpushed (CI never ran), which the M3.13 local gate now covers pre-commit.

**Branch protection — DONE (2026-05-25, user-authorized).** `main` now has required CI checks
(`Backend · pytest (py3.12)` + `Frontend · tsc + vite build`, strict) + require-PR (0 reviews,
solo self-merge). **`enforce_admins: false`** on purpose → **you keep direct-push to `main`**
(workflow unchanged); the PR path is CI-gated. To force PRs for everything (airtight vs
`--no-verify`): `gh api --method PUT .../branches/main/protection/enforce_admins`. To revert:
`gh api --method DELETE .../branches/main/protection`. See DEC-V61-203 §Follow-up.

**DRY VtkCanvasV3 — DONE (M3.15, `b25a4d7`):** `detectWebGL` now defined once in `webgl_support`,
imported by viewport_kernel + VtkCanvasV3. WebGL arc fully closed (M3.10→M3.12→M3.15).

**TOP NEXT CANDIDATE:** **M4 charter scoping** — post-Step-7 solver_run / results / report /
Notion sync. Multi-day; needs **Kogami opt-in** (user must召唤) per v2.3 — NOT autonomous.
Optional governance knob: flip `enforce_admins: true` to fully PR-gate main (DEC-V61-203 §Follow-up).

**Pre-existing uncommitted dirt (NOT touched this session — triage):** 12 deleted
`test-results/v4-*-2026-05-19.png` + 4 modified `ui/backend/audit/cases/flat_plate_rans_sst/
artifacts/*.json`. Present before this session started (prior session leftover). Left
untouched per "don't change unrelated files."
>
> **Session-end accumulator (2026-05-25)**:
> - 7 milestones closed (M3.2 / M3.3 / M3.4 / M3.5 / M3.6 / M3.7 / M3.8)
> - 20 cycles total
> - 25 new commits (`72e6acb` → `0f3358b`)
> - 0 post-R3 defects
> - 0 Codex relay invocations (all spike-class single-functionality sub-DECs)
> - 0 Kogami invocations (v2.3 opt-in only)
> - Multi-agent crew validated (Sonnet 4.6 narration · Explore survey · 6+ subagents across milestones)
> - Visual spot-check methodology hardened (added DOMContentLoaded overlay-init guard · added `--use-gl=swiftshader` for headless WebGL)
> - 4 demo .webm deliverables on user Desktop (progressive arc: empty seed → real CAD pre-B7 → real CAD post-B7)
>
> **Closing commit lineage**:
> - M3.2: `092a710` retro + multiple cycle commits
> - M3.3: M3.3 close retro
> - M3.4: `093e5b9` retro
> - M3.5: `f3f055b` retro (demo recording infrastructure)
> - M3.6: `6de6504` retro (real-CAD demo on circular_cylinder_wake fixture)
> - M3.7: `6ea1725` retro (workbench chrome de-hardcoding · closed B7)
> - M3.8: `0f3358b` retro (DRY useEffectiveCaseId hook)

---

## Where we are

**Milestone M3.1 (workbench dynamic guided UX, engine-side) = CLOSEABLE.**
**Milestone M3.2 (workbench frontend severity + actionability) = IN PROGRESS, 3 cycles landed.**

Parent charter: `DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED`.

## What landed this session (11 sub-DECs)

| Cycle | DEC ID | Final commit | Notion |
|---|---|---|---|
| M3.1 C1 | DEC-V61-202-SUB-M31-CYCLE1-FORM-HELPER-SHIPVOF | `4b701ea` + `a116981` | [36ac6894...474657](https://www.notion.so/36ac68942bed819d9ea7e7833f474657) |
| M3.1 C2 | DEC-V61-202-SUB-M31-CYCLE2-UI-LABELER-SCALAR-INPUT | `aaade23` | [36ac6894...64ac8f](https://www.notion.so/36ac68942bed819395b9d018fbc4ac8f) |
| M3.1 C3 | DEC-V61-202-SUB-M31-CYCLE3-RANS-FAMILY-SKELETON | `436d4b8` | [36ac6894...4ac8f](https://www.notion.so/36ac68942bed819395b9d018fbc4ac8f) |
| M3.1 C4 | DEC-V61-202-SUB-M31-CYCLE4-LES-EXTENSION-REGISTRY-EXTRACT | `a7d300b` | [36ac6894...10f2](https://www.notion.so/36ac68942bed81af8e3ee0d3882510f2) |
| M3.1 C5 | DEC-V61-202-SUB-M31-CYCLE5-FAILURE-PATH-DOGFOOD | `46880cc` | [36ac6894...d547](https://www.notion.so/36ac68942bed8187ba36f2b3134dd547) |
| M3.1 C6 | DEC-V61-202-SUB-M31-CYCLE6-PATCH-TYPE-PRESERVATION | `d64551c` | [36ac6894...0daf](https://www.notion.so/36ac68942bed81679d0af4274afb0daf) |
| M3.1 C7 | DEC-V61-202-SUB-M31-CYCLE7-CORRUPTED-MANIFEST-RAIL | `0e912b0` | [36ac6894...c755](https://www.notion.so/36ac68942bed8156854dfee0533bc755) |
| M3.1 C8 | DEC-V61-202-SUB-M31-CYCLE8-PATCH-TYPE-ENUM-WARNING | `cf1541b` | [36ac6894...7aa](https://www.notion.so/36ac68942bed81c0b401d3fd6016e7aa) |
| M3.2 C1 | DEC-V61-202-SUB-M32-CYCLE1-RAIL-SEVERITY-SURFACING | `c91ae09` | [36ac6894...5ba8](https://www.notion.so/36ac68942bed8162a7eee92e87d95ba8) |
| M3.2 C2 | DEC-V61-202-SUB-M32-CYCLE2-TOPBAR-SEVERITY-DISABLED | `7a6737e` | [36ac6894...4f50](https://www.notion.so/36ac68942bed81f4883adf9ffcc64f50) |
| M3.2 C3 | DEC-V61-202-SUB-M32-CYCLE3-COPY-FIELD-PATH | `28951f1` | [36ac6894...9fe7](https://www.notion.so/36ac68942bed812c9a97ed017c259fe7) |

**Retro**: `.planning/retrospectives/2026-05-24_m31_milestone_close.md` (commit `9fed473`, 290 lines, NOT synced to Notion per SSOT rule).

## Cycle-5 failure-path bug closure matrix (all FIXED)

| Bug | Severity | Fixed in cycle | Regression test |
|---|---|---|---|
| BUG-CYCLE5-1 (PATCH no type validation) | P1 | 6 | `test_manifest_patch_type_preservation` (23 unit tests) + dogfood step 5 |
| BUG-CYCLE5-2 (cascade blocks revert) | P1 | 6 (bundled) | dogfood step 6 |
| BUG-CYCLE5-3 (analyzer misses corruption) | P2 | 7 | `test_workbench_decide_corrupted_manifest` (9 unit tests) + dogfood step 8 |
| BUG-CYCLE5-4 (typo'd patch_type silently OK) | P3 | 8 | `test_case_completeness_patch_type_warning` (16 unit tests) |

Total new test coverage: **48 unit tests + 4 dogfood steps**.

## M3.9+ entry candidates (M3.2-M3.8 closed 2026-05-25)

### Open backlog (cosmetic / janitorial)
- **B4** (P3 · left sidebar dead vertical space) — only open finding from M3.2 visual audit · ~5-15 LOC
- **M3.4 B1 partial-fix caveat** — opened by M3.6 retro · M3.4 cycle 2 fix only covered empty-CAD cases · authored cases hit proxy bug in headless until M3.6's swiftshader workaround applied · root-fix in vtk.js wrapper deferred

### Carry-overs from earlier retros
- **Open in IDE via `vscode://`** — workbench → editor jump (M3.2 retro)
- **Raw YAML viewer modal** — backend YAML route + modal (M3.2 retro)
- **"Replace whole node" UI recovery** — M3.1 cycle 6 deferred
- **Backend `gap.why` enrichment** across all gap families (M3.3 retro)
- **Workbench-basics + manifest cross-validation** — M3.6 retro · basics says 7 patches but cylinder.stl has all_default_faces=true

### Demo deliverables (Desktop, 2026-05-25)
- `cfd_workbench_demo_2026-05-25.webm` (M3.5 · empty seed · 73s) — baseline
- `cfd_workbench_demo_realcad_2026-05-25.webm` (M3.6 · real CAD pre-B7 · 72s) — APU chrome bleed-through visible
- `cfd_workbench_demo_post_b7_2026-05-25.webm` (M3.7 post-B7 · 72s) — **canonical: case-authentic chrome + 3D cylinder**
- 9 PNG keyframes mapped per demo
- Companion: `scripts/dogfood/m35_workbench_demo_narration.md`

### Suggested M3.9 theme(s)
- **M3.9 = B4 cosmetic** — close last visual-audit finding · smallest cycle · ~10 LOC
- **M3.9 = M4 charter scoping** — what comes after Step 7 Post · solver_run / results / report / Notion sync · multi-day · likely Kogami opt-in
- **M3.9 = vtk.js proxy bug root-fix** — guard `new Proxy(null,...)` in ViewportV4's vtk.js bootstrap layer · removes need for swiftshader workaround · P2 followup

### Reusable infrastructure (NEW this session)
- `scripts/dogfood/m35_workbench_demo.mjs` — Playwright demo recorder with caption + cursor overlay (217 LOC)
- `scripts/dogfood/stage_m36_realcad_demo.py` — idempotent canonical-fixture case staging (98 LOC)
- `ui/frontend/src/pages/workbench/v4/hooks/useEffectiveCaseId.ts` — DRY blueprint-vs-case gate (48 LOC · M3.8 cycle 1)
- `.planning/methodology/screenshot_spot_check.md` (hardened with DOMContentLoaded + swiftshader notes from M3.5/M3.6)

### Notion sync debt (carried)
- `DEC-V61-201` (Status: Accepted 2026-05-21 · `notion_sync_status: pending`) — 4-day-old debt from session-end batch · attempted in this session-end

---

## M3.4 charter (CLOSED 2026-05-25)

### Theme
**Geometry step graceful empty-state** — close the B1-B5 step=geometry empty-state cluster surfaced by M3.3 cycle 3 cross-step audit. When a case has no CAD upload, step=1 currently cascades into broken widgets (MainCanvas proxy error + stat number collision + duplicate banner + sidebar dead-space + step rail overlap). Replace this with a clean empty-state UX so a fresh engineer landing on the workbench sees a usable, on-ramp-friendly screen instead of error popups.

### In scope
- `MainCanvas` / `VtkCanvasV3` empty-state fallback when no geometry artifact present (B1)
- Bottom-center stat area: render placeholder OR collapse layout when stats are 0 (B2)
- `DynamicBottomCards` rendering policy at step=geometry when only one rail-equivalent gap exists (B3 — investigate M3.0 charter intent first)
- Step rail z-index / positioning to not overlap bottom banner (B5)
- Optional: left sidebar fill (e.g., recently-viewed cases, minimap) at step=geometry only (B4 — lowest priority)
- **CTA**: an "Upload CAD here" prominent action in the empty viewport (high-value engineer on-ramp)

### Out of scope
- V4 shell layout broad refactor (defer to dedicated V4 milestone)
- Audit-engine changes (v2.3 charter freeze in DEC-V61-202 still holds)
- M-VIZ / vtk.js pipeline rework (only the empty-state guard, not the renderer itself)
- B1-B5 fixes for OTHER steps (cycle 3 audit proved they only manifest at geometry)

### Expected cycles
3-5, depending on root-cause investigation depth. Provisional:
- Cycle 1: charter + investigate each B finding's actual root cause (read VtkCanvas / DynamicBottomCards / step rail / sidebar source · grep for absolute-positioning bleed)
- Cycle 2: empty-state component for viewport (B1 + B2)
- Cycle 3: bottom banner rendering policy + step rail (B3 + B5)
- Cycle 4 (optional): sidebar fill (B4) OR defer to M3.5
- Cycle N: phase-close retro

### Close criterion
Stage `m33_ux_demo_seed` (no CAD) → navigate to `?step=geometry` → page renders cleanly with empty-state placeholder + "Upload CAD" CTA · no error popup · no number collision · no duplicate banner · no step rail overlap. Visual spot-check screenshot saved as part of phase-close retro.

### Open questions before cycle 1
1. Is `DynamicBottomCards` duplicating the same rail at step=geometry **by design** (per M3.0 charter)? Need to read `.planning/decisions/2026-05-22_v61_202_sub_m30_cycle1_decide_state.md` before changing rendering policy.
2. Does `MainCanvas` have an existing empty-state code path, or is the proxy error from an unguarded null-target call?
3. Is the "Upload CAD here" CTA already implemented elsewhere (some other onboarding flow)? Grep before building.

### Process integration
Per M3.3 cycle 2 methodology doc: every M3.4 cycle touching workbench frontend MUST reference at least one screenshot from `workbench_visual_spot_check.mjs` in its closing commit. Phase-close retro must include side-by-side before/after PNGs.

---

## M3.2 closed · M3.3 closed · M3.4 entry candidates

### M3.2 close outcome (2026-05-25)

7 cycles · 0 post-R3 defects · 0 cycles at Codex cap=3 · 0% user-ratification (cycles 1-3 only; 4-7 N/A per process-class). Retro at `.planning/retrospectives/2026-05-25_m32_milestone_close.md` (full counter telemetry · Codex round economy · four-question gate audit · backlog F-M32-1/F-M32-2 disposition · M3.3 charter recommendations).

**Process-class diversification empirically validated** on a 4-cycle stretch (4-5 spike-class · 6-7 single-functionality sub-DEC) with zero process-pollution and zero defects.

### Backlog findings carried over (not blocking M3.2 close)

- **F-M32-1** · rapid-double-click timer no-extend (P3 · UX research-gated). Fix only if engineer confusion surfaces; sketch in retro.
- **F-M32-2** · step=boundary navigation 404/422 console noise (P2 · backend triage). Out of M3.2 scope; assign to backend track.

### M3.3 charter — propose a 1-paragraph scope at cycle 1

Per retro §Recommendations #1: open M3.3 with theme + in-scope + out-of-scope + expected cycle count + close criterion. Candidate themes (user picks):

1. **Backend `gap.why` enrichment** — verify analyzer emits rich why across ALL gap families (not just case_family). Adjacent to F-M32-2 backend triage but distinct.
2. **Open in IDE via `vscode://`** — workbench → editor jump. Cross-cutting; sub-DEC with backend surface-area for case_dir absolute path + manifest line numbers.
3. **Raw YAML viewer modal** — fetch + render manifest YAML inside workbench panel. Backend YAML route + modal component.
4. **"Replace whole node" UI recovery** — for legacy-corrupted manifests (M3.1 cycle 6 deferred). Tied to specific corruption patterns from M3.1 cycle 7.
5. **Real-user UX validation arc** — close the "no real engineer used the toast" gap from M3.2 retro §What went poorly #4. Lighter than other candidates; could be the bridge milestone.

### Notion sync queue (session-end)

Cycles 4-7 are NOT synced to Notion (spike-class + single-functionality sub-DEC = Notion bypassed per v2.3). Cycles 1-3 already synced (per prior session). No action needed.

### M3.2 charter open questions (from retro §"Open questions for M3.2 charter")

1. Should "replace whole node" UI recovery be in M3.2 scope?
2. Cockpit `project_status.json` SHA-lag → graduate to dedicated cockpit-pipeline DEC?
3. V63-A catalog drift canary — add to base `[ui]` test suite or runtime-only is fine?
4. Pre-cap-3 guard: "if Codex precedence/source-of-truth finding twice, declare charter-class"?

## Methodology lessons captured (load-bearing for M3.2+)

1. **Failure-path dogfood pattern works** — 100% bug closure within milestone arc. Apply to focus-pick + multi-physics flag-mismatch dogfoods next.
2. **Precedence/source-of-truth Codex findings ≥2 = charter-class signal** — Cycle 1 8-round arc would have been 2-round with this guard.
3. **Cross-module import surface-scan pre-flight** — Verify `head -50 package/__init__.py | grep -i import` for heavy deps before any `from package.module import X`. Cycle 8 R1 trimesh leak postmortem.
4. **Catalog-reuse checklist**: (a) import-tree clean, (b) intentional exclusions match use case, (c) overloaded semantics reconcile. Cycle 8 3-round arc → 1 round with this.
5. **Static drift-detection > importlib.reload** for SSOT-mirror invariants. Cycle 8 R2's `test_v63a_catalog_is_subset_of_known_types` is the pattern.
6. **Manifest-only contract (cycle 1 R7) is load-bearing** — Cycles 3 and 6 inherited it. Any future architectural ratification should be documented as a contract this strongly.

## V130 four-question gate audit (8/8 M3.1 cycles)

All cycles answer Y/Y/Y/Y:
- LLM offline — does it run? ✓
- Artifacts canonical (manifest/json/yaml)? ✓
- TrustGate-explainable (provenance on every decision)? ✓
- AI advisory-only (no auto-writes by AI)? ✓

Advisor-not-driver contract held across all 8 cycles including programmatic dogfood.

## Counter telemetry

- M3.0 counter delta: +8
- M3.1 counter delta: +8
- M3.2 counter so far: +3 (cycles 1-3)
- Cumulative M3 counter: +19 (from 73 → 84+? exact transition depends on M2 closure baseline)
- post-R3 defects M3.1: 0
- user-ratifications M3.1: 4 / 8 = 50% (healthy band 30-60%)
- Codex APPROVE-at-R0: 1 / 8 (12.5% — cycle 7 ideal cycle)

## Codex round economy (this session)

| Cycle | Rounds | Closure |
|---|---|---|
| M3.1 C1 | 8 (R0-R8) | user-ratified R7 (manifest-only contract) |
| M3.1 C2 | 4 (R0-R3) | clean APPROVE R3 |
| M3.1 C3 | 3 (R0-R2) | clean APPROVE R2 |
| M3.1 C4 | 4 (R0-R3) | user-ratified R3 (same-day rename non-issue) |
| M3.1 C5 | 4 (R0-R3) | user-ratified R3 (msg-only scan fix) |
| M3.1 C6 | 2 (R0-R1) | user-ratified R1 (cockpit SHA structural) |
| M3.1 C7 | 1 (R0) | clean APPROVE R0 (ideal cycle) |
| M3.1 C8 | 3 (R0-R2) | clean APPROVE R2 (inline fix at cap=3) |
| M3.2 C1 | 2 (R0-R1) | clean APPROVE R1 |
| M3.2 C2 | 2 (R0-R1) | clean APPROVE R1 |
| M3.2 C3 | 2 (R0-R1) | clean APPROVE R1 |

Total ~35 rounds across 11 sub-DECs (avg 3.2 rounds/cycle, dragged up by cycle 1 outlier). Without C1: 27 / 10 = 2.7 avg.

## File map (most-touched paths this session)

### Backend (engine)
- `ui/backend/services/workbench_decide.py` — `_FORM_HELPER_SKELETONS`, `_STRUCTURAL_META_PATHS`, `_rail_from_problem`/`_rail_from_gap` severity passthrough
- `ui/backend/services/manifest_patch.py` — `_check_type_preservation`, `_compare_subtree_types`
- `ui/backend/services/case_completeness/analyzer.py` — `_KNOWN_OPENFOAM_PATCH_TYPES`, `_FIELD_LEVEL_BC_TYPES` (inline-copied STANDARD_OPENFOAM_BCS), `_SOLVER_TO_CASE_FAMILY_CANDIDATES`
- `ui/backend/services/case_family_registry.py` — **new SSOT module** (cycle 4 extraction)
- `ui/backend/services/workbench_decide_provenance.py` — reads `frame.rail_primary.severity` directly (no string scraping)
- `ui/backend/schemas/workbench_frame.py` — `RailPrimary.severity: Severity = "info"`

### Frontend (workbench)
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicFramePanel.tsx` — inline-edit affordance, `toneFor(rail)` 4-tone helper, `CopyFieldPathButton`
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicTopbarCta.tsx` — `railSeverity` prop + `DISABLED_CLASS_BY_SEVERITY`
- `ui/frontend/src/pages/workbench/StepPanelShell.tsx` + `v4/WorkbenchShellV4.tsx` — both threaded `railSeverity={dynamicFrame.rail_primary.severity}`
- `ui/frontend/src/types/workbench_frame.ts` — mirrors backend severity field

### Tests
- `ui/backend/tests/test_manifest_patch_type_preservation.py` (NEW, 23 tests)
- `ui/backend/tests/test_workbench_decide_corrupted_manifest.py` (NEW, 9 tests)
- `ui/backend/tests/test_case_completeness_patch_type_warning.py` (NEW, 16 tests)
- `ui/backend/tests/test_workbench_decide_rail_severity.py` (NEW, 11 tests)
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/__tests__/DynamicFramePanel.test.tsx` (32 tests total)
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/__tests__/DynamicTopbarCta.test.tsx` (11 tests)
- `scripts/dogfood/case_007_cycle5_failure_path.py` (10/10 PASS)

## Standing constraints (still in force)

- **Manifest-only contract** for solver field (cycle 1 R7 ratified; load-bearing)
- **Codex round cap = 3** per v2.3 DEC-V61-133 (R0 + 2 fix iterations; ratification can extend or close)
- **Kogami opt-in only** (auto-triggers废止 per v2.3); user explicitly invokes
- **DEC scope-driven**: charter / ≥3 shared paths / governance-rule-change → full DEC; sub-DEC for narrower
- **Notion sync**: Accepted-only, session-end batch (retros stay local)
- **Four-question gate** (V130): LLM offline / artifacts canonical / TrustGate / advisor-only — all 4 must be Y
- **No port squatting / no schedule-date gating / no CFDJerry visual smoke gating**
- **`codex-relay` skill** is Claude Code's own responsibility; do not push commands to user

## Next-session entry checklist

1. **Read this RESUME.md first** (you're here)
2. Skim `.planning/STATE.md` ANCHOR-23 (top of file) for full session narrative
3. Decide M3.2 cycle 4 direction (see "Open M3.2 work" above) — user mandate is continuous milestone progress
4. If picking cycle 4 from the candidate list, do pre-implementation surface scan per V61-088:
   - ROADMAP scan
   - existing-implementation grep
   - file new sub-DEC with predecessors pointing to M3.2 cycles 1-3
5. Spike-class (≤30 LOC + 1 test) is fine for the toast/copy-body_text variants — those won't need DEC

## Bottom line

M3.1 closes with a fully-drained cycle-5 backlog, no post-merge defects, 50% user-ratification rate matching v2.3 design intent, zero V131 spirals. M3.2 is bootstrapped through the severity-visibility foundation (cycles 1-2) and the first actionability affordance (cycle 3). Engine-side is closeable; the frontend actionability thread is open and ready for cycle 4+ expansion.

**Recommendation for next session**: pick a cycle 4 direction from the open-list above; spike-class if applicable; otherwise sub-DEC + Codex round cap=3 + session-end Notion sync.

# Workbench Onboarding Guide

> **Audience**: First-time engineers approaching the cfd-harness-unified workbench.
> **Read time**: ~12 minutes.
> **Time to first successful run**: ~30 seconds (lid_driven_cavity) once you've read § 2.
> **Authored**: V70.3 (B163 · 2026-05-16) per V70 charter §3 V70-DONE-3.

## 1 · What the workbench is, and what it is not

The cfd-harness-unified workbench is a **CFD simulation cockpit** built around OpenFOAM. It manages the 5-step pipeline (Import → Mesh → Setup BC → Solve → Results), surfaces gold-standard reference comparisons via a TrustGate, and provides an AI advisor that suggests next moves — without ever writing case files for you.

**Three product principles you should internalize before clicking anything:**

1. **AI is an advisor, never a driver** (V130 / V132 invariant). The AI looks at your case state and emits suggestions ("your y+ is in the wall-function dead zone — consider switching turbulence model to k-omega-SST"). The AI does NOT modify files, run solvers, or commit changes. You drive; AI advises. If you see AI doing anything beyond `GET`-and-comment, file a bug.
2. **Everything must work LLM-offline.** Disconnect the LLM provider and every step still runs. The AI advisor degrades gracefully to "advisor offline — your work is preserved". The workbench is a CFD tool, not an LLM wrapper.
3. **TrustGate is your friend, not your enemy.** Every case has a "gold standard" reference (from published literature). After a run, TrustGate compares your solution to the reference. PASS means within published error bands; FAIL means investigate, do not commit. The badge prevents silent regressions.

What the workbench is **not**:
- It is not a CAD tool. Geometries come in as STL or via a small set of intrinsic blockMesh templates.
- It is not a results database. Each run lives in `workspace/projects/<case>/` and is yours to keep or delete.
- It is not a benchmark farm. It runs on one machine; large parallel jobs need explicit `decomposePar` setup.

## 2 · The 2-minute first run · lid_driven_cavity

The fastest path from "I just opened this" to "I have a converged CFD solution with gold-standard verification" is the lid-driven cavity:

1. From the workbench index (`/workbench`), click the **First-time banner** link → `lid_driven_cavity starter case`.
2. The case opens at Step 1 (Import). The geometry is intrinsic — a 1×1 unit square with a moving top wall — so there's nothing to import. Click **Next → Step 2 (Mesh)**.
3. Step 2 (Mesh): a 17×17 uniform blockMesh is generated in <1s. The Engineer Control Rail at top-right shows the wireframe. Click **Next → Step 3 (Setup BC)**.
4. Step 3 (BC): The MaterialCard shows ν=0.01 m²/s, Re=100. The 4 walls are noSlip; the top wall sets U=(1, 0, 0). Click **Next → Step 4 (Solve)**.
5. Step 4 (Solve): Click the green **Run** button. icoFoam iterates ~25 seconds. Residuals chart (Engineer Control Rail → **Residuals** mode) shows log10 convergence dropping cleanly to ~1e-6 for U and p.
6. Step 5 (Results): TrustGate badge turns PASS — your u-centerline solution matches Ghia 1982 within 5% across the 17-point reference grid. Engineer Control Rail → **Report** mode shows the side-by-side error plot.

You are done. You just reproduced a published CFD benchmark.

## 3 · The 5 steps · what each one actually does

| Step | Default viewport mode | What you decide | What the workbench does | What the AI advisor sees |
|---|---|---|---|---|
| 1 · Import | Geometry | Pick a case (new / from catalog / import STL) | Loads or generates geometry; emits Step 1 artifacts | "Is the geometry watertight? Is the domain extent reasonable?" |
| 2 · Mesh | Mesh | Pick meshing strategy + grid params | Runs blockMesh / snappyHexMesh / gmsh; emits Step 2 artifacts | "Is mesh quality (skewness / aspect ratio) within acceptable bounds? Is y+ in the right regime for your turbulence model?" |
| 3 · Setup BC | BC | Specify BCs + materials + turbulence model | Writes `0/`, `constant/transportProperties`, `constant/turbulenceProperties`; emits Step 3 artifacts | "Are BC types consistent with patch types? Are material properties physical? Is turbulence model compatible with mesh y+?" |
| 4 · Solve | Residuals | Pick solver + run parameters | Invokes OpenFOAM solver; streams logs | "Are residuals dropping monotonically? Has the case stagnated? Are forces converging?" |
| 5 · Results | Report | Inspect verdict + force/error plots | Runs TrustGate comparison vs gold reference; emits Step 5 artifacts | "Is the verdict trustworthy? Are there mesh / model / convergence concerns to flag?" |

The **Engineer Control Rail** (top-right of the viewport area) lets you switch viewport modes at any time — e.g., switch to **Field** during a Step 4 run to preview velocity slice while the solver iterates.

## 4 · The case catalog · what's in each one

The workbench ships with 11 cases:

| Case | Regime | Reference | Why it's there |
|---|---|---|---|
| lid_driven_cavity | Laminar incompressible steady | Ghia 1982 | Starter case · fastest TrustGate PASS path |
| plane_channel_flow | DNS turbulent transient | Moser-Kim-Mansour 1999 | Resolved-scale anchor |
| backward_facing_step | k-epsilon RANS steady | Driver-Seegmiller 1985 | Industrial RANS anchor |
| naca0012_airfoil | k-omega-SST steady | NASA TMR | External aero anchor |
| circular_cylinder_wake | k-omega-SST transient | Norberg 1987 | Vortex shedding anchor |
| rayleigh_benard_convection | buoyantFoam Ra=1e6 | Bénard 1900 | Natural convection anchor |
| naca0012_transonic | rhoSimpleFoam M=0.8 | AGARD AR-138 | Compressible aero anchor |
| apu_bay_ventilation (case_002a · gold_pending) | chtMultiRegionFoam | Industry vendor data | First imported_user case · ⏳ gold pending |
| (3 more documented in catalog) |

Hover any case card on `/workbench` for a one-line summary. Click for the case-detail page (case_id-routed) where you can edit parameters and re-run.

## 5 · Where the truth lives

Three SSOTs you should know:

- **`knowledge/whitelist.yaml`** — the 10 anchor cases + their gold references. Any case here has a TrustGate verdict guarantee.
- **`.planning/evals/canonical/E01..E30*.md`** — 30 canonical advisor eval cases (V69 + V70.2). Each tests that the AI advisor produces the expected rule firings for a known physics regime. Run `uv run pytest ui/backend/tests/test_canonical_advisor_eval.py` to verify the advisor surface hasn't regressed.
- **`.planning/cfd_capability_matrix.md`** (V70.1) — honest enumeration of which CFD regimes the workbench can run end-to-end (33/59 cells PR; 26/59 GAP-TRACKED; 0 empty).

If you find something the workbench claims to support but doesn't actually run, that's a structural fraud signal — file a reverse-stop entry per V70 charter §6.

## 6 · Common first-time pitfalls (the AI advisor will warn you about most)

1. **y+ regime mismatch**: k-epsilon at y+~1 over-predicts skin friction by 60-70%. The `yplus_regime_match_advisor` (V66-B) catches this — if it fires ERROR severity, switch turbulence model or remesh.
2. **Turbulent BC + laminar solver**: `icoFoam` has no turbulence model. Setting `kQR` on inlet patches will be silently ignored. Always check that solver + BC + turbulence model agree (`solver_block_advisor` flags inconsistencies).
3. **Forgetting to converge before TrustGate**: TrustGate trusts your solution. Run residuals to ≤1e-5 before checking verdict. If TrustGate shows FAIL on a converged solution, the issue is physics not solver state.
4. **Importing STL with mm units** when the case template assumes meters. Step 2 (Mesh) does NOT auto-scale. Check `system/snappyHexMeshDict` if mesh dimensions look off by 1000×.
5. **Running on a single processor** for a 5M-cell case. Use `decomposePar` first. The workbench will warn at Step 4 if cell count > 500k and `decomposeParDict` is missing.

## 7 · The AI advisor's actual scope (V130 invariant)

The AI advisor does **3 things** and **only these 3 things**:

1. **GET case state**: read `.foam` files, log tails, residual histories
2. **Apply advisor rules** from `.planning/methodology/advisor_rules.md`: each rule has a clear "fire condition" and "suggestion"
3. **Emit advisory commentary** via `/api/ai-review` and `/api/ai-diagnose`: structured JSON with citations to the V-row corpus

The AI advisor does **NOT**:
- Write case files
- Modify any `0/` / `constant/` / `system/` directory
- Invoke OpenFOAM solvers
- Commit git changes
- Network anywhere except the configured LLM provider

If you see the AI doing anything from the second list, that is a V132 invariant violation — file a bug immediately.

## 8 · Next steps

After your first lid_driven_cavity run:

1. **Try backward_facing_step**: same workflow, RANS turbulence, real industrial physics. ~3 minute run.
2. **Read `.planning/V_series_index.md`**: the V-row corpus is the long-form record of every meaningful workbench evolution. It tells you not just *what* the workbench does but *why* each piece exists.
3. **Run the dogfood loop**: `uv run python scripts/smoke/dogfood_loop.py --whitelist-only`. This runs all 10 whitelist cases end-to-end. If anything regresses on your machine, you'll see it here before you trust your own work.
4. **Browse the canonical eval set**: `ls .planning/evals/canonical/`. Each case is a 1-page distillation of "this regime, this expected advisor behavior". Useful for understanding the advisor's coverage envelope.
5. **Read the SCORING-FRAMEWORK.md**: 10 quality pillars + zone anchors. Understanding the scoring rubric helps you understand what the team prioritizes.

## 9 · How to ask for help

- For UI / UX bugs: file an issue with a screenshot + repro steps. The first-time banner / tutorial / Engineer Control Rail are all V70.3 artifacts; if anything visibly drifts, please flag.
- For physics / regime questions: check `.planning/cfd_capability_matrix.md` first to see if your regime is PR / GAP-TRACKED / out-of-scope. If GAP-TRACKED, the closure path is documented; if out-of-scope, propose a charter for the relevant V71+ arc.
- For AI advisor mistakes: dump the case state + advisor output, file under V130 invariant audit.

Welcome to the workbench. Build something honest.

— V70.3 onboarding guide · 2026-05-16 · B163

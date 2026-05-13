# Live Bash Commands for Segments 2, 3, 4

> Open terminal in `~/Desktop/apu-bay-ventilation-cht` with font ≥ 18pt and `PROMPT_COMMAND` simplified (e.g. only `$ ` prompt). Pre-run all of these once the day before so the filesystem cache is warm.

## Segment 2 (0:05–0:11) — CAD → mesh live

```bash
# 1. Show STL inputs (30 patches in final boundary; 20 merged OBJ files; 14 APU bodies + 16 other patches)
ls inputs/cleaned_combined_merged_*.obj | wc -l            # → 20 merged surface files
cat case_refined_v2/constant/polyMesh/boundary | grep -cE "^    [a-zA-Z]"   # → 30 patches in final mesh

# 2. Show patch naming SSOT (frozen contract — type enum: mass_flow_inlet/outlet, pressure_outlet/inlet, wall_hot, wall_adiabatic, wall_external_temp, symmetry, farfield)
head -50 inputs/naming.yaml

# 3. Show mesh decisions (refinementBox jet L3 + 3-layer prism)
sed -n '1,60p' case_refined_v2/system/snappyHexMeshDict

# 4. Show mesh quality outcome
grep -E "Mesh stats|cells:|faces:|Skipping|Refining|Layer addition" case_refined_v2/log/sHM_v2_tight.log | tail -25
```

**Narration cue**: after #2, say "this `naming.yaml` is what makes Segment 4's post-processing trustworthy — same patch name from STL through mesh through BC through `paraview_HD_v3_smooth`'s axes labels".

## Segment 3 (0:11–0:16) — Mesh quality decision

```bash
# Switch to the harness repo to show the runtime corpus
cd ~/Desktop/cfd-harness-unified

# 1. Show corpus shape (84 V-rows, runtime-loadable)
wc -l docs/openfoam_corpus/industrial_solver_findings_v_series.md       # → 1150 lines
grep -c "^### V" docs/openfoam_corpus/industrial_solver_findings_v_series.md   # → 84
grep "^### V8 \|^### V84 " docs/openfoam_corpus/industrial_solver_findings_v_series.md

# 2. Show V84 (the load-bearing finding for this segment)
awk '/^### V84/,/^### V[0-9]+|^## /' docs/openfoam_corpus/industrial_solver_findings_v_series.md | head -15

# 3. Show corpus_loader contract (it's the project's runtime advisor entry point)
sed -n '101,115p' ui/backend/services/ai_advisor/corpus_loader.py        # find_relevant signature

# 4. Ad-hoc query (proves the corpus is queryable, not just a markdown doc)
uv run python -c "
from pathlib import Path
from ui.backend.services.ai_advisor.corpus_loader import load_corpus
c = load_corpus(Path('.'), roots=[('docs/openfoam_corpus', 'openfoam_corpus')])
for h in c.find_relevant('max skewness solver', top_k=3):
    print(' ', h.path, '|', (h.section_anchor or '')[:80])
"
```

**Narration cue**: after #4, say "this is the **runtime** path — `corpus_loader.py` is what `/ai-review` and `/ai-diagnose` use; the V-series is project-owned knowledge, not web-scraped, not LLM-hallucinated".

**Caveat**: switching repos (Segment 2 → Segment 3) is a `cd` — pre-warm both directories.

## Segment 4 (0:16–0:22) — Solver run highlights

```bash
# Switch back to demo case
cd ~/Desktop/apu-bay-ventilation-cht

# 1. Parse the plateau-window log
grep -E "^Time = |continuity errors|smoothSolver|GAMG" case_refined_v2/log/pimple_v2_plateau.log | tail -30

# 2. Show residual plateau
grep "smoothSolver:  Solving for h" case_refined_v2/log/pimple_v2_plateau.log | tail -10
grep "smoothSolver:  Solving for k" case_refined_v2/log/pimple_v2_plateau.log | tail -10

# 3. Open the HD HTML report (assumes Safari/Chrome opens by default)
open reports/v6N/report_v6N_HD_v3_final.html

# 4. Or display the 8 HD PNGs one by one in Preview
open reports/v6N/paraview_HD_v3_smooth/{01,02,03,04,05,06,07,08}_*.png
```

**Narration cue order for the 8 HD images** (≈40 s each):
1. `01_T_axial_Z0_HD.png` — "axial T slice, combustor 600 K cone clearly visible"
2. `03_Umag_axial_Z0_HD.png` — "|U| field, jet impingement + recirculation"
3. `04_Inner_Surf_T_HD.png` — "inner-surface T gradients on the 14 APU bodies"
4. `05_firewall_combustor_T_HD.png` — "firewall + combustor zoom"
5. `06_streamlines_combustor_HD.png` — "streamlines from combustor outlet"
6. `07_streamlines_intake_HD.png` — "streamlines into apu_intake suction"
7. `08_combined_view_HD.png` — "composite view"
8. (`02_T_xsection_X66_HD.png` is held in reserve if Q&A needs cross-section)

**Segue line into Segment 5**:
> "Qualitatively this is right — separation, jet, suction path, all there. **But** the bay bulk temperature is 328-350 K versus theoretical 494 K — that's 30 % under. Why?"
> *cue advisor video Moment 2*

## Pre-warm checklist (run once before demo)

```bash
cd ~/Desktop/apu-bay-ventilation-cht

# Verify Segment 2 targets all exist
test -f inputs/naming.yaml && echo "naming.yaml OK"
test -f case_refined_v2/system/snappyHexMeshDict && echo "snappyHexMeshDict OK"
test -f case_refined_v2/log/sHM_v2_tight.log && echo "sHM log OK"
test -f case_refined_v2/log/pimple_v2_plateau.log && echo "plateau log OK"
test -f case_refined_v2/constant/polyMesh/boundary && echo "boundary OK"

# Cache filesystem and read-throughput
cat case_refined_v2/log/sHM_v2_tight.log > /dev/null
cat case_refined_v2/log/pimple_v2_plateau.log > /dev/null
cat reports/v6N/ENGINEERING_CAVEAT.md > /dev/null
for f in reports/v6N/paraview_HD_v3_smooth/*.png; do cat "$f" > /dev/null; done

cd ~/Desktop/cfd-harness-unified
cat docs/openfoam_corpus/industrial_solver_findings_v_series.md > /dev/null

# Verify uv venv works (Segment 3 ad-hoc query)
uv run python -c "from ui.backend.services.ai_advisor.corpus_loader import load_corpus; print('OK')"
```

If any of these takes > 1 s on the second run, something is wrong — investigate before demo.

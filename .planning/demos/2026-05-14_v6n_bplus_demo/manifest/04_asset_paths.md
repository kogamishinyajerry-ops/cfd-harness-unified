# Asset Inventory — Every File Referenced in Demo

## Case data (in `~/Desktop/apu-bay-ventilation-cht/`)

| Path | Used in | Notes |
|---|---|---|
| `inputs/cleaned_combined_merged_*.obj` | Segment 2 | 17 patches, OBJ format (post-cleanup) |
| `config/naming.yaml` | Segment 2 | Patch-name SSOT |
| `case_refined_v2/system/snappyHexMeshDict` | Segment 2 | Mesh decisions |
| `case_refined_v2/log/sHM_v2_tight.log` | Segment 2 | Mesh outcome (943k cells, max_skew 6.875, 20 skew faces) |
| `case_refined_v2/log/pimple_v2_plateau.log` | Segment 4 | Plateau-window solver log |
| `case_refined_v2/constant/polyMesh/` | (background) | The actual mesh — reachable but not displayed |
| `case_refined_v2/postProcessing/patchAverage(patch=apu_intake,T)/` | (background) | T history at intake patch |

## HD ParaView outputs (`~/Desktop/apu-bay-ventilation-cht/reports/v6N/`)

| File | Size | Used in | Notes |
|---|---|---|---|
| `paraview_HD_v3_smooth/01_T_axial_Z0_HD.png` | 3200×2000 | Segment 4 #1 | Axial T slice; combustor 600 K cone |
| `paraview_HD_v3_smooth/02_T_xsection_X66_HD.png` | 3200×2000 | Segment 4 reserve | Cross-section X=66; held for Q&A |
| `paraview_HD_v3_smooth/03_Umag_axial_Z0_HD.png` | 3200×2000 | Segment 4 #2 | \|U\| field; jet + recirc |
| `paraview_HD_v3_smooth/04_Inner_Surf_T_HD.png` | 3200×2000 | Segment 4 #3 | 14 APU body surface T gradients |
| `paraview_HD_v3_smooth/05_firewall_combustor_T_HD.png` | 3200×2000 | Segment 4 #4 | Firewall + combustor zoom |
| `paraview_HD_v3_smooth/06_streamlines_combustor_HD.png` | 3200×2000 | Segment 4 #5 | Combustor outlet streamlines |
| `paraview_HD_v3_smooth/07_streamlines_intake_HD.png` | 3200×2000 | Segment 4 #6 | Intake suction streamlines |
| `paraview_HD_v3_smooth/08_combined_view_HD.png` | 3200×2000 | Segment 4 #7 | Composite |
| `report_v6N_HD_v3_final.html` | 22 MB | Segment 4 alt | 4-tier comparison HTML (browser tab pre-loaded) |
| `ENGINEERING_CAVEAT.md` | — | Segment 5 ref | Honest 30 % deficit diagnosis (cited by advisor Moment 2) |

## Harness repo assets (in `~/Desktop/cfd-harness-unified/`)

| Path | Used in | Notes |
|---|---|---|
| `docs/openfoam_corpus/industrial_solver_findings_v_series.md` | Segment 3 | 84 V-rows · runtime corpus · 1150 lines |
| `ui/backend/services/ai_advisor/corpus_loader.py` | Segment 3 | Runtime entry point (`find_relevant`) |
| `CLAUDE.md` | Q&A | Project SSOT for v6.2 architecture + governance |

## Recordings to produce (the human records these — see `00_README.md`)

| File | Source | Duration target | When recorded |
|---|---|---|---|
| `recordings/moment_1_raw.mov` | Fresh Claude Code session, paste `advisor_transcripts/moment_1_prompt.md` engineer block | 60-90 s | Day before demo |
| `recordings/moment_2_raw.mov` | Same, paste Moment 2 engineer block | 90 s | Day before demo |
| `recordings/moment_3_raw.mov` | Same, paste Moment 3 engineer block | 90 s | Day before demo |
| `recordings/advisor_moments_final.mp4` | CapCut output assembling the 3 raws + 10s transitions | ~5 min | Day before demo |
| `recordings/full_demo_dryrun.mov` | QuickTime full-display screen recording of you doing the 30-min demo once | 30 min | Day before demo (Plan B) |
| `recordings/backup_self_recording_*.mov` | screencapture auto-started by Claude Code Opus when generating this workspace | up to 25 min | Already running (background) |

## External tools assumed present

- macOS Terminal or iTerm2 (font ≥ 18pt)
- A browser (Safari/Chrome) — for `report_v6N_HD_v3_final.html`
- macOS Preview — for the 8 HD PNGs
- QuickTime Player — for the 3 raw advisor recordings + Plan B full-demo screencast
- CapCut (Chinese: 剪映) — for assembling `advisor_moments_final.mp4`
- A second display recommended (one for live terminal, one for HD images + cheat sheet)

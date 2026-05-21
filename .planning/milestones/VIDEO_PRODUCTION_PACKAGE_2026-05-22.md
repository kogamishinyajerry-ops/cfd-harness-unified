# Video Production Package — cfd-harness-unified milestone demo

**Date**: 2026-05-22
**Operator-ready**: yes — record without rehearsal using these artifacts
**Total runtime target**: 5:30 (title 0:05 + 5 stages 5:00 + close 0:25)
**Strategic thesis**: "the engine refuses to lie" (per DEC-V61-130 advisor-not-driver pivot)

## Index

### 1. Real terminal captures · `/Users/Zhuanz/Desktop/cfd-audit-merge/.demo/captures/2026-05-22T0145Z/`

| File | Lines | What it captures |
|---|---|---|
| `INVOCATION_NOTES.md` | 47 | How cfdtrust was made invokable (editable install) + canonical commands |
| `stage_01_git_log.txt` | 21 | `git log --oneline 5250bb7..HEAD` — 21 commits since baseline |
| `stage_02a_case_027_ingest.txt` | 4 | case_027 `cfdtrust ingest` — PASS at iter 5000 with honest WARN |
| `stage_02b_case_027_report.txt` | 5 | case_027 `cfdtrust report` — overall_status=FAIL (mesh_contract), validation_status=not_validated |
| `stage_02c_case_027_explain.txt` | 71 | case_027 `cfdtrust explain` — per-gate WHY + recommendation Markdown |
| `stage_03_case_010_block.txt` | 3 | case_010 BLOCKED with `case_dir_not_openfoam_compatible` + next-step guidance |
| `stage_04a_tbd17_grep.txt` | 80 | `git log --grep=TBD-17 --format=fuller` — fix commit + ship commit |
| `stage_04b_tbd17_show.txt` | 24 | `git show 3b5c43f --stat` — 302 insertions across openfoam.py + ingest tests |
| `stage_05a_test_count.txt` | 7 | `pytest -q` — `427 passed, 1 skipped in 4.07s` |
| `stage_05b_dogfood_inventory.txt` | 7 | 7 DOGFOOD_CASE_*.md reports across 9 physics regimes |

### 2. Post-processing artifacts · `/Users/Zhuanz/Desktop/cfd-audit-merge/.demo/postproc/`

| Case | Script | PNG | Status |
|---|---|---|---|
| case_027 Hagen-Poiseuille | `case_027/residual_plot.py` | `case_027/residual_plot.png` (70 KB) | **executed** — matplotlib 3.10.9 |
| case_021 NASA TMR | `case_021/residual_plot.py` | `case_021/residual_plot.png` (71 KB) | **executed** |
| case_009 Sandia Flame D | `case_009/residual_plot.py` | `case_009/residual_plot.png` (82 KB) | **executed** — hero plot w/ TBD-17 annotation |
| case_028 APU bay ventilation | `case_028/paraview_macro.py` | `case_028/paraview_view.png` | **script only** — needs pvpython |
| case_011 plate-fin CHT | `case_011/paraview_macro.py` | `case_011/paraview_view.png` | **script only** — needs pvpython |
| case_021 NASA TMR (wall) | `case_021/paraview_macro.py` | `case_021/paraview_view.png` | **script only** — needs pvpython |

### 3. Frame-by-frame screencast script · `/Users/Zhuanz/Desktop/cfd-audit-merge/.demo/SCREENCAST_SCRIPT.md`

Five stages + title + closing card, all tied to real capture files and
real PNGs with explicit line-range highlight regions.

## Recording setup notes

### Terminal preset (for live recording or asciinema replay)

```
Application: iTerm2 or Terminal.app
Window size: 100 cols × 30 rows
Font: Menlo 14pt
Background: #16181C (dark, low-contrast)
Foreground: #e6e6e6
Cursor: solid, no blink during recording
Prompt: minimal (recommend `PS1='$ '` for recording session only)
```

### Recommended toolchain

| Tool | Purpose | Install |
|---|---|---|
| **OBS Studio** | scene mixing terminal + image + slide | brew install --cask obs |
| **asciinema** | terminal-only path; play back captures | brew install asciinema |
| **Keynote** or **Final Cut Pro** | title + closing card + highlight overlays | preinstalled |
| **ParaView 5.10+** | only needed if executing the 3 ParaView macros | brew install --cask paraview |

### Recording flow (hybrid path — recommended)

1. Create OBS scenes: `Title`, `Stage1_Term`, `Stage2_Split`, `Stage3_Term`, `Stage4_Split`, `Stage5_Term`, `Close`.
2. For terminal scenes: open iTerm2, `cat .demo/captures/2026-05-22T0145Z/stage_<N>_*.txt` to display capture verbatim (no live re-run = no flake).
3. For split scenes (stage 2 + stage 4): terminal source 60% left + Image source (PNG path from postproc) 40% right.
4. Record per-scene at 60 fps, 1920×1080, AAC 192k.
5. Edit in Final Cut: cuts per SCREENCAST_SCRIPT.md, overlay highlight boxes per line-range in the script.
6. Export H.264 MP4, 1080p, target ~50 MB for the 5:30 cut.

### Recording flow (asciinema-only path — faster but lower production value)

1. Per stage: `asciinema rec stage_<N>.cast`, then in the new shell `cat .demo/captures/2026-05-22T0145Z/stage_<N>_*.txt`, then `exit` to stop recording.
2. Stitch with `asciinema-edit cut` or render each to GIF via `agg`.
3. Cannot show PNG side panels — skip stages 2 split-view and 4 split-view, or follow them with a static PNG slide.

## Production checklist

```
[x] cfdtrust CLI invokable (editable install resolved missing PATH)
[x] All 10 capture files generated + verified non-empty (line counts above)
[x] matplotlib 3.10.9 installed (via pip --user --break-system-packages)
[x] 3 residual PNGs rendered (case_027, case_021, case_009)
[x] 3 ParaView macros written + docstring-documented (case_028, case_011, case_021)
[x] SCREENCAST_SCRIPT.md frame-by-frame written (252 lines)
[x] Pytest side-effects cleaned (git checkout -- on cases/ and docs/status/)
[ ] OBS scenes created (operator task, ≤30 min setup)
[ ] Recording session executed (operator task, ≤30 min including 2 takes)
[ ] Final Cut edit (operator task, ≤60 min)
[ ] Stakeholder review + sign-off (project-governor agent, post-recording)
[~] ParaView PNGs (queued — runs ParaView on operator machine; non-blocking for the 5:30 cut)
```

## Who needs to do what

- **Recording operator** (human or remote-pair): OBS setup + capture playback + Final Cut edit. Estimated 2h total.
- **ParaView operator** (optional, post-launch): run the 3 paraview_macro.py scripts via `pvpython` to produce paraview_view.png for stages where APU bay industrial visualization is desired in v2 of the demo. Estimated 30 min.
- **marketing-director agent** (this run): produced all artifacts above; no further action until next milestone gate.
- **project-governor agent**: review the final MP4 + this manifest, greenlight stakeholder distribution.

## Non-claims (what this demo does NOT promise)

Per `marketing-director.md` SSOT and DEC-V61-130 strategic pivot:

- No M6 charter-class work shipped (Gap #28 manifest schema redesign, Gap #23 compressible regex coverage, Gap #15 chtMultiRegion BC enumeration — all queued post-demo)
- No chatbot button / wired-up RAG surface (Claude Code session IS the advisor)
- No "AI-powered" / "revolutionary" framing
- No promise that the ingest mode constitutes solver validation (validation_status capped at `not_validated` for all ingested runs by design)
- No fabricated reference comparisons (`reference_comparison.status: not_finalized` is honest)
- No headcount / customer / business KPI claims

## Honesty as differentiator — explicit demo beats

1. **Stage 2 ingest WARN** — harness did NOT witness solver execution; validation_status capped at not_validated
2. **Stage 2 report FAIL** — case_027 mesh_contract failed on `axis` patch BC; engine reports honestly even though solver converged
3. **Stage 3 BLOCK** — case_010 cannot be ingested; engine refuses to score instead of fabricating PASS
4. **Stage 4 TBD-17** — pre-fix engine silently parsed 3 of 27 declared residuals; new TBD-17 path BLOCKS with `incomplete_residual_coverage` + `missing_target_fields` list
5. **Stage 5 dogfood inventory** — 7 reports, multiple of which are honest FAILs / BLOCKs (case_010 / case_011 multi-region / etc.) — capability matrix includes the gaps

## References (every claim sourced)

- DEC-V61-130 strategic pivot — `/Users/Zhuanz/Desktop/cfd-audit-merge/.planning/decisions/` (Notion-synced)
- DEC-V61-201 sub-audit ingest mode — `2026-05-21_v61_201_sub_audit_ingest_mode.md`
- TBD-17 fix commit — `3b5c43f311f1f9a14091ca05ceade69574c67f0a` (verified via `git show`)
- Test count — `427 passed, 1 skipped` (verified via `pytest`, capture stage_05a)
- Dogfood reports — `find ... DOGFOOD_CASE_*.md` (capture stage_05b)
- All capture files independently re-runnable via commands in `INVOCATION_NOTES.md`

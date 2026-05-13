# 30-Minute Segment Timing & Beats

| Time | Segment | Mode | Screen | What you say (one-line) |
|---|---|---|---|---|
| 0:00–0:05 | 1 · Stage setting | Slides | Single | "APU bay ventilation, MES day 55 °C, traditional 5-7 days, today 30 min" |
| 0:05–0:11 | 2 · CAD → mesh live | Live terminal | Dual: terminal + naming.yaml | "17 patches frozen by naming.yaml — same name from STL through solver to post-processing" |
| 0:11–0:16 | 3 · Mesh quality decision | Live terminal + V-series corpus | Dual: terminal + corpus | "max_skew 6.87 is sHM's reject-wall, not solver's — V84 says run a 50-iter smoke" |
| 0:16–0:22 | 4 · Solver run highlights | Log + HD images | Dual: log + image carousel | "Residual plateau is real; here's what the run looks like" — show 8 HD PNGs |
| 0:22–0:27 | 5 · AI advisor moments | Video player | Full-screen | Play the 3 pre-recorded advisor moments (no live LLM) |
| 0:27–0:30 | 6 · Positioning + Q&A | Slides + open | Single | "4 DEC pillars closed; LLM-offline; advisor-not-driver; V-series sediment" + Q&A |

## Why each segment ends where it ends

### Segment 1 (0:00–0:05) — Stage setting

Hard stop at 5:00. CFD peers need 4 minutes to calibrate "is this real?" — give them the workload (943k cells, buoyantPimpleFoam, 4-core MPI, MES day 55 °C, combustor 2.8 kg/s @ 616 K, 14 APU bodies T 343–674 K), and the painful baseline (5-7 days, multiple solver divergences). Don't sell — they smell marketing within 30 s.

### Segment 2 (0:05–0:11) — CAD → mesh live

6 min for `ls inputs/`, `cat naming.yaml`, `tail sHM.log`. Don't try to explain every patch — pick 2-3 that have non-obvious naming (combustor_outlet, apu_intake, farfield_cylinder) and explain the suction-vs-blow geometry. **Beat to land**: "naming.yaml = single source of truth from STL → mesh → BC → post" (the Sediment-as-you-go pillar).

### Segment 3 (0:11–0:16) — Mesh quality decision

5 min split into:
- 2 min · show V-series corpus file structure (84 V-rows, runtime advisor copy, ingest-able by `corpus_loader.py`)
- 2 min · search for max_skewness; surface V84
- 1 min · narrate: "this lesson came from case_002a F4b yesterday — today's v6N B+ already operates on this principle; that's V-series complexity-compounding"

**Beat to land**: corpus is project-owned, not web-scraped — V84 was sedimented yesterday by the same kind of session as this demo.

### Segment 4 (0:16–0:22) — Solver run highlights

6 min split into:
- 1 min · `grep` the `pimple_v2_plateau.log` for residuals + continuity errors; show plateau achieved
- ~40 s × 8 HD images = ~5 min for the visualization carousel
- Resist the temptation to explain each turbulence-model detail — image carousel is for **flow-structure recognition** (peers will catch "OK that's a separation bubble" / "that's the jet impingement" without you naming it)

**Beat to land**: end of carousel, segue with "qualitatively right, but bay bulk T is 150 K below energy-balance — let's hear the AI advisor on that" → cue Segment 5.

### Segment 5 (0:22–0:27) — AI advisor moments

5 min for 3 × 90-s clips with 10-s transitions:
- **Moment 1** (60 s) — "max_skew 6.87 can I proceed?" → mesh-go decision
- **Moment 2** (90 s) — "why is bay 30 % under?" → numerical-dissipation diagnosis
- **Moment 3** (90 s) — "which of 4 upgrade paths under 7-day ARM budget?" → priority ranking

**Beat to land** (post-video, 15 s): "Note what just happened — advisor cited 3 V-rows, named numerical-dissipation root causes from `ENGINEERING_CAVEAT.md`, gave a Mon–Sun week plan; the workbench is still running offline-capable, advisor was advisor not driver, every claim is corpus-cited."

### Segment 6 (0:27–0:30) — Positioning + Q&A

3 min split into:
- 60 s · positioning recap: DEC-V61-198 four pillars · LLM-offline · advisor-not-driver · V-series sediment
- 120 s · Q&A — use `05_qa_canned_responses.md` for the 5 predicted questions

**Hard stop**: 30:00. If Q&A runs long, offer "happy to go deeper after — let me share `~/Desktop/cfd-harness-unified/CLAUDE.md` and the V-series corpus link".

## Cumulative timing safety margin

| Segment | Budgeted | Tight (90 % case) | Loose (worst case) |
|---|---|---|---|
| 1 | 5:00 | 4:30 | 5:30 |
| 2 | 6:00 | 5:00 | 7:00 |
| 3 | 5:00 | 4:00 | 6:00 |
| 4 | 6:00 | 5:00 | 7:30 |
| 5 | 5:00 | 4:50 | 5:00 (videos are deterministic) |
| 6 | 3:00 | 2:30 | 5:00 (Q&A is the elastic bucket) |
| **Total** | **30:00** | **25:50** | **36:00** |

If you blow the loose case, Segment 6 absorbs first — never sacrifice Segments 4/5.

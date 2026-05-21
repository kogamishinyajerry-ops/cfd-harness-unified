# Missing artifacts queue — 2026-05-22 demo cycle

Honest list of what could NOT be produced in-session and what needs to
happen to land them.

## ParaView screenshots — 3 cases

| Artifact | Reason | Path forward |
|---|---|---|
| `.demo/postproc/case_028/paraview_view.png` | `pvpython` not invoked in-session (ParaView macro write-only per agent constraint) | Operator runs `pvpython /Users/Zhuanz/Desktop/cfd-audit-merge/.demo/postproc/case_028/paraview_macro.py` after `brew install --cask paraview` |
| `.demo/postproc/case_011/paraview_view.png` | same | Operator runs the case_011 macro |
| `.demo/postproc/case_021/paraview_view.png` | same | Operator runs the case_021 macro |

**Status**: macros are docstring-documented + tested-paths-only verified
(field names confirmed against actual time-dir contents; case_028 uses
field `U` in `474/`, case_011 uses field `T` across 3 multi-region
`region_*` dirs, case_021 uses `wallShearStress` on `plate` patch in
`2500/`). Macros should execute on a stock ParaView 5.10+ install
without modification.

**Demo impact**: stages 2/3/4/5 work fully without ParaView PNGs. The
APU bay / CHT / wall-shear visualizations would be a v2 enhancement
showing "the workbench can do industrial cases" — currently asserted in
text-only form (case_028 dogfood report exists per stage_05b inventory).

## Real screenshots (UI / browser) — not in scope this cycle

The 2026-05-22 demo is **terminal + post-processing PNG only**. No web
UI screenshots are required. If a future milestone gates on showing
the workbench UI (post-N2 sizing field overlay etc.), this section
should be expanded.

## Live solver run — explicitly out of scope

Per agent constraint: "DO NOT use `cfdtrust run` (Docker + slow + out
of scope). `ingest` only." The trust harness's solver execution path
runs OpenFOAM in Docker (image `openfoam/openfoam11-paraview510:latest`)
and would add 10-60 minutes per case to the capture window. Ingest mode
is the demo-friendly path: the case is solved offline, the harness
ingests the residuals/log/checkmesh, and the WARN-on-ingest discloses
honestly that the harness did not witness the run.

If a "live solver" stage is requested in a future cycle: budget a
separate recording session with Docker prewarmed and one quick
case (case_024 lid-driven cavity ~3 min on a 4-core box) and add a
stage between current Stage 2 and 3.

## Notion sync — out of scope this cycle

The marketing-director agent does not own Notion sync. Per project
SSOT (`notion-sync-cfd-harness` skill + `~/CLAUDE.md` "Notion 仅 sync
Status=Accepted 的 DEC" rule), Notion sync happens at session end via
the cfd-harness-unified main session. Demo materials are NOT synced to
Notion (they're build-time artifacts, not decisions).

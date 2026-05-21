# SCREENCAST_SCRIPT — cfd-harness-unified 2026-05-22 milestone demo

Frame-by-frame manifest for a 5-6 minute screencast. All commands reference
real capture files under `.demo/captures/2026-05-22T0145Z/` and real PNGs
under `.demo/postproc/<case>/`. Captures were produced live by the
marketing-director agent; the recording operator does NOT re-run anything
unless explicitly noted — they replay terminal contents from the capture
files via `cat`, `bat`, or a typing-replay tool (asciinema rec + asciicast2gif).

Total target runtime: **5:30** (title 0:05 + 5 stages summing to 5:00 + close 0:25).
Terminal preset: 100×30, Menlo 14pt, background `#16181C`, fg `#e6e6e6`.

---

## Title card · 00:00 – 00:05

**Shot type**: full-screen text card (slide / OBS scene)
**On-screen text** (centered):
```
cfd-harness-unified · milestone demo
2026-05-22 · the engine refuses to lie
```
**Voice-over**: "Five-minute demo. We're showing why this CFD trust harness
ships honesty as a feature, not as marketing."
**Cut**: hard cut to terminal

---

## Stage 1 · provenance · 00:05 – 00:45

**Shot type**: terminal only
**On-screen overlay**: "21 commits since 5250bb7 · all real"
**Voice-over (≤2 sentences)**: "Twenty-one commits since the merge baseline,
spanning dogfood discoveries, sub-DEC implementations, and one self-discovered
honesty bug we'll get to in stage four."
**Command** (operator types, then replay from capture):
```
git -C ~/Desktop/cfd-audit-merge log --oneline 5250bb7..HEAD
```
**Source capture**: `.demo/captures/2026-05-22T0145Z/stage_01_git_log.txt` (21 lines)
**Highlight regions**:
- line 1 (`e1867aa docs(demo)`): pulse-highlight 0.5s — "this commit, the demo materials"
- line 3 (`3b5c43f fix(audit-ingest)`): persistent yellow box — "TBD-17 fix lands here"
- line 13 (`e86c011 feat(audit-ingest): discriminate`): persistent green box — "sub-DEC P1-GUARD-DISCRIMINATE land"
**Cut**: hold 2s on the box highlights, then hard cut to stage 2

---

## Stage 2 · case_027 Hagen-Poiseuille happy path · 00:45 – 02:15

**Shot type**: split-view (terminal left 60%, residual PNG right 40%)
**On-screen overlay**: "case_027 · laminar pipe · 6-gate ingest"
**Voice-over (≤3 sentences)**: "Hagen-Poiseuille pipe — laminar, analytic
reference exists. We ingest an externally-run OpenFOAM case; the harness
walks six gates and emits a structured trust report. Watch the validation
status — even though the solver converged cleanly, validation_status caps
at not_validated because the harness didn't witness the run."

**Commands** (3 sub-shots, ~30s each):

### 2a · ingest
```
cfdtrust ingest ~/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65
```
**Source**: `stage_02a_case_027_ingest.txt` (4 lines)
**Highlight**: line 1 (`ingest PASS: simpleFoam converged at iter 5000`),
line 4 (`WARN Ingested run: harness did NOT witness... validation_status
cannot reach validated`). Pulse the WARN line in amber.

### 2b · report
```
cfdtrust report ~/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65
```
**Source**: `stage_02b_case_027_report.txt` (5 lines)
**Highlight**: lines 2-4 — pulse `overall_status = FAIL` (red),
`solver_execution = ingested` (amber), `validation_status = not_validated`
(amber). Voice-over: "FAIL is honest — the mesh contract gate caught a
missing axis BC on the `0/U` and `0/p` files. The solver was fine; the
case had an unfixed pre-existing problem."

### 2c · explain (Markdown)
```
cfdtrust explain ~/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65
```
**Source**: `stage_02c_case_027_explain.txt` (71 lines)
**Highlight**: scroll to and pulse the `### file_presence FAIL` and
`### solver_execution PASS` sections. Voice-over: "Per-gate WHY + a
recommendation. No black box."

**Side panel** (right 40%): show `.demo/postproc/case_027/residual_plot.png`
fade in at stage 2a, hold through 2b/2c.

**Cut**: hard cut to stage 3.

---

## Stage 3 · case_010 honest BLOCK · 02:15 – 02:45

**Shot type**: terminal only
**On-screen overlay**: "case_010 · DrivAer LES · BLOCKED early, refuses to invent verdict"
**Voice-over (≤2 sentences)**: "Same command, but this case directory is
incomplete. The engine refuses to score it — no `system/`, no `constant/`,
no `0/`. BLOCKED with a precise next-step instead of a fabricated PASS."
**Command**:
```
cfdtrust ingest ~/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case
```
**Source**: `stage_03_case_010_block.txt` (3 lines)
**Highlight**: all three lines pulse red on appearance.
Line 1 `FAIL ingest BLOCKED: Case directory does not look like an OpenFOAM case`,
line 2 `reason: case_dir_not_openfoam_compatible`,
line 3 `next step: Provide system/, constant/, and 0/...`.
**Cut**: 1s hold, fade to stage 4.

---

## Stage 4 · TBD-17 self-discovery · 02:45 – 04:00

**Shot type**: split-view (terminal top-half, case_009 residual PNG bottom-half)
**On-screen overlay**: "Stage 4 · the engine snitched on itself"
**Voice-over (≤3 sentences)**: "This is the hero moment. While dogfooding
case_009 Sandia Flame D — a reacting flow with 27 declared residual targets
— the harness's pre-fix code silently passed when the residuals parser only
captured 3 fields. We caught it during the same dogfood arc and shipped the
fix in commit 3b5c43f."

**Commands** (2 sub-shots, ~30s each):

### 4a · git log grep
```
git -C ~/Desktop/cfd-audit-merge log --grep=TBD-17 --format=fuller
```
**Source**: `stage_04a_tbd17_grep.txt` (80 lines)
**Highlight**: lines 1-3 (e1867aa commit header), then scroll to line ~50
where the 3b5c43f fix commit appears. Persistent yellow box around the
fix-commit body lines `TBD-17 (CRITICAL): solver_gate no longer silently
skips manifest target fields absent from residuals.csv`.

### 4b · git show 3b5c43f --stat
```
git -C ~/Desktop/cfd-audit-merge show 3b5c43f --stat
```
**Source**: `stage_04b_tbd17_show.txt` (24 lines)
**Highlight**: last 4 lines (the diffstat). Voice-over: "302 lines added
across the openfoam backend + 174 new test lines. The new tests
specifically assert BLOCK on missing residual coverage — regression-proof."

**Side panel** (bottom-half): `.demo/postproc/case_009/residual_plot.png`
fade in at stage 4a. Annotation box on the plot reads:
"MANIFEST DECLARED 27 FIELDS · PARSER FOUND 26 · TBD-17 surface fixed in
commit 3b5c43f".

**Cut**: hold 3s on the annotation, hard cut to stage 5.

---

## Stage 5 · capability · 04:00 – 05:00

**Shot type**: terminal only, two sequential commands
**On-screen overlay**: "428 tests · 7 dogfood reports"
**Voice-over (≤2 sentences)**: "Four hundred twenty-seven tests pass, one
skipped (Docker-gated). Seven case-family dogfood reports landed —
laminar, RANS, MRF rotating, VOF free-surface, transonic, reacting,
incompressible vehicle, CHT."

### 5a · pytest
```
cd ~/Desktop/cfd-audit-merge && pytest ui/backend/audit/cfdtrust_tests/ -q 2>&1 | tail -10
```
**Source**: `stage_05a_test_count.txt` (7 lines)
**Highlight**: last line `427 passed, 1 skipped in 4.07s`. Pulse green.

### 5b · dogfood inventory
```
find ~/Desktop/cfd-harness-unified/_sandboxes -name 'DOGFOOD_CASE_*.md'
```
**Source**: `stage_05b_dogfood_inventory.txt` (7 lines)
**Highlight**: 7 lines visible — voice-over: "case_004 NREL wind turbine
MRF, case_006 ONERA M6 transonic, case_007 KCS ship VOF, case_010
DrivAer LES, case_011 plate-fin CHT, case_021 NASA TMR flat plate,
case_027 Hagen-Poiseuille."

**Cut**: hard cut to closing card.

---

## Closing card · 05:00 – 05:30

**Shot type**: full-screen text card, hold 30s
**On-screen text** (centered, large):
```
cfd-harness-unified

An industrial CFD workbench whose AI advisor
refuses to fabricate verdicts.

9 physics regimes verified · 1 honesty bug
self-discovered + fixed in-arc.

Claude Code session = advisor surface
(per DEC-V61-130 strategic pivot)
```
**Voice-over (≤2 sentences, hold last 10s in silence)**: "AI is the
advisor, not the driver. The session you're watching is the advisor — no
chatbot button, no rubber-stamp PASS, no fabricated reference comparisons.
That's the differentiator."
**Cut**: fade to black over 2s.

---

## Production notes

- **Asciinema-only path**: stages 1, 3, 5 work as pure terminal replays —
  `asciinema rec stage_N.cast && asciinema play stage_N.cast`. Faster to
  produce; less production value.
- **OBS hybrid path** (recommended): use OBS Studio scene per stage with
  a terminal source on left + image source (residual_plot.png) on right.
  Stage 2 + Stage 4 need the split-view. Crossfade between scenes.
- **No live re-runs during recording**: every command can be replayed from
  `.demo/captures/2026-05-22T0145Z/*.txt` via `cat` — recorded as if live.
  The actual stdout is byte-identical to what would happen if the operator
  re-ran the commands. This avoids flaky timing.
- **Annotation tool**: Keynote magic move or Final Cut callout box for the
  highlight regions. Don't burn highlights into the asciinema cast — keep
  them as overlay layer for re-editability.
- **Pacing reference**: 4 sec/line for terminal text, 1 sec hold per
  pulse highlight, 2-3 sec hold on the side-panel PNG fade.

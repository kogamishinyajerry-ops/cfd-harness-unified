# Demo Screen Recording · Annotated Outline

> Companion to `DEMO.md` and `CHANGELOG_MILESTONE_2026-05-22.md`.
> Authoring only — DO NOT auto-record. Hand this to whoever drives the recording.
> Target length: **5 minutes total**.

---

## Pre-recording setup

| Item | Setting |
|---|---|
| Terminal size | 120 cols × 36 rows (fits 1080p capture without horizontal overflow on default font) |
| Terminal font | Menlo / Cascadia Mono / JetBrains Mono · 16pt |
| Shell prompt | Truncate to last 2 path segments (`audit/` not `~/Desktop/cfd-audit-merge/ui/backend/audit/`) — helps viewer focus on commands not paths |
| Color scheme | High-contrast dark (Solarized Dark / Dracula) — JSON output reads better |
| Tabs to have open | (1) terminal at repo root `~/Desktop/cfd-audit-merge`. (2) terminal at external sandbox `~/Desktop/cfd-harness-unified/_sandboxes/` for sanity. (3) editor with `.planning/dogfood/DOGFOOD_CASE_009.md` pre-scrolled to §TBD-17 line ~120 for the Stage-4 reveal. |
| Pre-run | `export PYTHONPATH=ui/backend/audit` in the recording terminal (do this BEFORE recording starts so the env var doesn't pollute the capture) |
| Pre-warm | Run each Stage 2 / 3 / 4 command once before recording to prime any Docker image pulls (`openfoam/openfoam11-paraview510:latest` for checkMesh) — viewer should not watch a Docker pull |
| Recording app | **asciinema** for terminal-only (lightest, copy-pasteable transcript). **OBS** if hybrid with slide overlays. User picks. |

---

## Per-stage callouts

> Format: `[mm:ss] · ON-SCREEN OVERLAY · voice-over`
> Voice-over is 1-2 sentences max per stage. Keep it tight.

### [00:00 – 00:30] · STAGE 1 · "Show the trail"

**On-screen overlay** (top-right corner, 4-line):
```
cfd-harness-unified · audit subsystem
Milestone 2026-05-22 · 20 session commits
Engine: 5769673
```

**Command shown**: `git log --oneline 5250bb7..HEAD`

**Voice-over** (15 sec):
> "Twenty commits since we merged AI-CFD-V2 into the workbench last week. Seven rounds of Codex review on the ingest mode, four follow-up sub-DECs, and eight dogfood spike fixes — every one of these traces back to a finding in a real CFD case. We didn't write this engine and hope it works; we ran it on nine regimes and shipped the patches in the same arc."

### [00:30 – 02:00] · STAGE 2 · "Honest ingest on a laminar case"

**On-screen overlay** (top-right, replace previous):
```
Stage 2/5 · case_027 Hagen-Poiseuille
Laminar wedge · simpleFoam · 5000 iter externally run
```

**Command shown**:
```bash
python -m cfdtrust.cli ingest \
  ~/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65
python -m cfdtrust.cli report \
  ~/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65
```

**Highlight on output** (boxed annotation in post):
```
overall_status   = FAIL
solver_execution = ingested      ←
validation_status= not_validated ←
```

**Voice-over** (45 sec total, split across the two commands):
> (after ingest) "The case actually ran 5000 iterations externally in OpenFOAM 2312. The engine reads the polyMesh, parses the log, computes the gate from residuals. So far it could just say PASS."
> (after report) "But look at the report. `solver_execution = ingested`. `validation_status = not_validated`. Even with residuals converged, the engine refuses to claim `validated` or top-level `PASS`, because the harness didn't witness the run. That cap is enforced at three layers — schema, gate, and report-assembly. This is the ingest honesty contract."

### [02:00 – 03:30] · STAGE 3 · "Honest BLOCK on a case that never ran"

**On-screen overlay** (replace):
```
Stage 3/5 · case_010 DrivAer LES
4.6M-cell mesh · pimpleFoam + WALE LES · NEVER RUN
```

**Command shown**:
```bash
python -m cfdtrust.cli ingest \
  ~/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case
```

**Highlight on output** (boxed annotation):
```
overall_status   = BLOCKED
solver_execution = skipped      ← NOT "ingested" — fence held
validation_status= not_validated
```

**Voice-over** (50 sec):
> "case_010 is the DrivAer LES case. There's a 4.6 million cell background mesh on disk, there's a `0.orig` directory with boundary templates, there are step-numbered mesh-pipeline logs. A lazy engine could pretend, run checkMesh, emit a half-credible verdict. This one refuses. `solver_execution = skipped` — not `ingested`. The engine will not claim it loaded a solver run that never happened. That's the fail-safe direction holding even when there's nothing to ingest."

### [03:30 – 04:30] · STAGE 4 · "The engine snitched on itself"

**On-screen overlay** (replace; this is the key stage):
```
Stage 4/5 · TBD-17 self-discovered bug
Found in case_009 Sandia Flame D · Fixed same session
Commit: 3b5c43f → merged 5769673
```

**Commands shown**:
```bash
git log --grep="TBD-17" --oneline
sed -n '120,155p' .planning/dogfood/DOGFOOD_CASE_009.md
```

**Highlight on output** (boxed annotation around the lines in DOGFOOD_CASE_009.md):
```
"simpleFoam converged at iter 0 (all 3 field residuals ≤ target)"
                                  ↑
                  manifest declared 27 fields. gate checked 3.
```

**Voice-over** (50 sec — this is THE pitch moment):
> "Mid-arc we dogfooded case_009, Sandia Flame D — reacting low-Mach combustion, 19 species, 27 declared residual targets. The engine's own solver gate said PASS on iteration zero, all three field residuals at target. **Three. Of twenty-seven.** The source log was cut mid-PIMPLE before species residuals were emitted, and the gate silently skipped the 24 missing fields. This is exactly the failure mode the trust harness exists to prevent — and the engine found it inside itself. We logged it as TBD-17. We shipped the fix in the same arc, commit `3b5c43f`. New fence: gate BLOCKs with `incomplete_residual_coverage` when fewer than half of declared targets are observed. That's the demo's load-bearing moment: the engine is honest enough to snitch on itself."

### [04:30 – 05:00] · STAGE 5 · "Nine regimes, zero false PASSes"

**On-screen overlay** (final, larger — capability matrix):
```
9 regimes verified · 9 honest verdicts · 0 fabricated

027 laminar    │ 021 RANS      │ 011 CHT
004 MRF        │ 006 transonic │ 007 VOF
010 LES BLOCK  │ 028 industrial│ 009 reacting + TBD-17
```

**Command shown** (optional):
```bash
cat .planning/milestones/CHANGELOG_MILESTONE_2026-05-22.md | head -50
```

**Voice-over** (25 sec):
> "Nine physics regimes this week. Laminar, RANS, CHT, MRF, transonic, multiphase, LES, industrial, reacting. Every one ingested and emitted an honest verdict — including the BLOCK on the case that never ran and the FAIL on the case where the engine caught its own bug. Zero false PASSes. That's the pitch."

---

## Final freeze frame · 5 seconds at end

**Full-screen overlay** (everything else dims):

```
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│     cfd-harness-unified                                           │
│                                                                   │
│     An industrial CFD workbench whose AI advisor                  │
│     refuses to fabricate verdicts.                                │
│                                                                   │
│     9 regimes verified · 1 self-discovered bug · same-arc fix    │
│                                                                   │
│     github.com/kogamishinyajerry-ops/cfd-harness-unified          │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

Hold 5 sec. End recording.

---

## Recording length target

- Stage 1: 30s
- Stage 2: 90s
- Stage 3: 90s
- Stage 4: 60s
- Stage 5: 30s
- Freeze frame: 5s
- **Total: 305s (5:05)** — buffer is 5s, viewer-tolerable.

If a stage runs long, the cuttable seconds are: voice-over pause in Stage 2 (-10s OK), Stage 5 narration (-10s OK). Do NOT cut Stage 4 — that's the demo's load-bearing moment.

---

## Tools recommendation

- **asciinema** — best for "terminal-only, copy-pasteable, embeddable in a README" demo. Output is `.cast` file + GitHub asciinema embed. Zero post-production. Recommended for engineer-to-engineer audience.
- **OBS Studio** — best for "presentation-ready with overlays, freeze frame, slide hybrid" demo. Output is `.mp4`. Recommended for stakeholder / leadership audience where the title cards and the overlay boxes carry weight.
- **Both**: record once with asciinema for the trail; re-author with OBS overlays for the stakeholder version. The asciinema cast file doubles as the on-disk transcript proof.

User decides based on audience. If unsure, default to asciinema first (lower production overhead, faster turnaround, fully verifiable on replay).

---

## Pre-recording sanity checklist

- [ ] `git log --oneline 5250bb7..HEAD` shows exactly 20 commits (matches the count this outline assumes)
- [ ] case_027 / case_010 / case_009 paths exist at `~/Desktop/cfd-harness-unified/_sandboxes/case_*/case*/`
- [ ] `python -m cfdtrust.cli ingest ...case_027.../case_v65` exits 0 in pre-warm
- [ ] `python -m cfdtrust.cli ingest ...case_010.../case` exits non-zero with `BLOCKED` in pre-warm
- [ ] `.planning/dogfood/DOGFOOD_CASE_009.md` line ~120 contains the TBD-17 §
- [ ] PYTHONPATH set + Docker daemon running (checkMesh image will be invoked on Stage 2)
- [ ] No background processes that will output to terminal mid-recording

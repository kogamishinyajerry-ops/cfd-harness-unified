# cfd-harness-unified · DEMO

> Stakeholder demo · 2026-05-22 milestone gate
> Engine commit: `5769673` (main, post-7-round-Codex-arc + 9-regime dogfood + TBD-17 honesty patch)

---

## Pitch

**An industrial CFD workbench whose AI advisor refuses to fabricate verdicts.**

Three-paragraph version:

cfd-harness-unified is a CFD audit engine that sits in front of OpenFOAM and refuses to lie about what it saw. It ships a 6-gate trust contract (geometry / mesh / BC / solver / QoI / reference) plus a `cfdtrust ingest` mode that loads cases run outside the harness — but every gate is wired to fail honestly rather than fabricate a verdict when evidence is missing.

We dogfooded it across 9 physics regimes this milestone — laminar pipe, RANS flat plate, CHT multi-region, MRF rotating machinery, transonic compressible, multiphase VOF, LES external aero, APU bay industrial, and Sandia Flame D reacting low-Mach. Every one of those runs surfaced honest verdicts: `overall_status = FAIL` or `BLOCKED` when evidence was thin, never a false PASS. Of the 9 cases, 1 (LES) honestly BLOCKED at the first guard because the case never ran. 8 ingested cleanly with downstream FAILs that map to real, actionable manifest under-specification.

Mid-arc the engine snitched on itself. While dogfooding case_009 (Sandia Flame D), the engine's own solver gate declared `PASS — simpleFoam converged at iter 0, all 3 field residuals ≤ target` on a reacting case where the manifest declared 27 fields. The gate silently skipped the 24 species residuals that hadn't been emitted before the run was cut. We logged this as TBD-17 and shipped the fix in the same session: a minimum-coverage threshold that BLOCKs the gate when fewer than 50% of declared targets are observed. The patch is `3b5c43f` — that's the demo's load-bearing moment.

---

## 30-second elevator (hallway version)

We built a CFD audit engine that refuses to certify what it didn't witness. Nine real cases this week — every one came out with an honest verdict, including the case where the engine caught its own silent-skip bug mid-demo and we shipped the fix the same day. The pitch isn't "we cover more physics regimes than X." The pitch is **the engine doesn't lie**, which is the only differentiator that matters when an engineer's name goes on the result.

---

## 5-minute demo script

> All commands run from the repo root: `cd ~/Desktop/cfd-audit-merge`
> External case directories live in `~/Desktop/cfd-harness-unified/_sandboxes/`.

### Stage 1 · 30 sec · "Show me the trail"

```bash
git log --oneline 5250bb7..HEAD
```

Expected: 20 commits since the AI-CFD-V2 merge (`5250bb7`). Narrate: "7 rounds of Codex review on the ingest mode, 4 follow-up sub-DECs, then 8 dogfood spikes from cases 006/007/009. Round cap is 3 per V133 governance — we extended to 7 with explicit user ratification because every round caught a real issue."

### Stage 2 · 90 sec · "Honest ingest on a laminar case"

```bash
cd ~/Desktop/cfd-audit-merge
PYTHONPATH=ui/backend/audit python -m cfdtrust.cli ingest \
  ~/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65
```

Expected (truncated):

```
[cfdtrust] OK   ingest PASS: simpleFoam converged at iter 5000 (all field residuals ≤ target).
[cfdtrust] OK     external_log_source = log_simpleFoam.txt
[cfdtrust] WARN Ingested run: harness did NOT witness the solver execution.
```

Then:

```bash
PYTHONPATH=ui/backend/audit python -m cfdtrust.cli report \
  ~/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65
```

Expected:

```
overall_status   = FAIL          ← mesh + bc FAIL on the wedge-axis substrate
solver_execution = ingested      ← honesty fence: capped below PASS
validation_status= not_validated ← honesty fence: capped below validated
```

Narrate: "The case actually ran 5000 iterations externally. The engine reads the log, computes the gate from residuals — and then caps `overall_status` at WARN because the harness didn't witness the run, no matter how clean the residuals look. That's the ingest honesty contract."

### Stage 3 · 90 sec · "Honest BLOCK on a case that never ran"

```bash
PYTHONPATH=ui/backend/audit python -m cfdtrust.cli ingest \
  ~/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case
```

Expected:

```
[cfdtrust] BLOCKED: no_solver_artifacts (case is at mesh-only scaffold state)
overall_status   = BLOCKED
solver_execution = skipped       ← NOT 'ingested'; the engine refused to claim ingestion
validation_status= not_validated
```

Narrate: "case_010 DrivAer LES has a 4.6M-cell background mesh and `0.orig/` boundary templates, but no `0/`, no time directories, no solver log — the case has never been run. A naive engine could pretend, run checkMesh, and emit something. This one refuses. `solver_execution = skipped`, not `ingested`. The fail-safe direction holds even on a case that has nothing to ingest."

### Stage 4 · 60 sec · "The engine snitched on itself"

```bash
git log --grep="TBD-17" --oneline
```

Expected:

```
5769673 Merge: TBD-17 honesty-adjacent + 2 reacting spikes (case_009 findings)
3b5c43f fix(audit-ingest): honesty-adjacent + 2 reacting spikes (TBD-15/#17/#19 from case_009)
```

Then open the dogfood report:

```bash
sed -n '120,155p' .planning/dogfood/DOGFOOD_CASE_009.md
```

Live narration: "We dogfooded case_009 Sandia Flame D — reacting low-Mach, DRM-19 chemistry, 27 declared residual fields. The gate said PASS on iter 0 because the source log was cut mid-PIMPLE-iteration before species residuals were emitted, so only Ux/Uy/Uz showed up. `failed=[]`, `checked=[Ux,Uy,Uz]`, `not failed → PASS`. **3 of 27 fields checked**, gate said PASS. This is exactly the failure mode the trust harness exists to prevent. We logged it as TBD-17, shipped the fix in the same arc as commit `3b5c43f`: introduced `_PARTIAL_FINAL_COVERAGE_THRESHOLD = 0.5` so the gate now BLOCKs with `incomplete_residual_coverage` when fewer than half of declared targets are observed."

### Stage 5 · 30 sec · "What the engine knows about"

Show the capability matrix (Stage 4 of `CHANGELOG_MILESTONE_2026-05-22.md`):

| Case | Regime | Outcome |
|---|---|---|
| 027 Hagen-Poiseuille | laminar wedge axisymmetric | ingest → honest FAIL on mesh + bc |
| 021 NASA TMR | turbulent RANS flat plate | ingest → honest FAIL |
| 011 plate-fin HX | conjugate heat transfer (multi-region) | ingest → honest FAIL |
| 004 NREL Phase VI | rotating machinery (MRF) | ingest → honest FAIL |
| 006 ONERA M6 | transonic compressible (rhoCentralFoam) | ingest → honest FAIL + 8 schema gaps surfaced |
| 007 KCS ship | multiphase VOF (interFoam) | ingest → honest FAIL + phase-field blindness surfaced |
| 010 DrivAer | incompressible external LES | honest BLOCK (case never ran) + 6 LES schema gaps surfaced |
| 028 APU bay | industrial RANS ventilation | ingest → honest FAIL on bc_contract (140 missing BC entries enumerated) |
| 009 Sandia Flame D | reacting low-Mach (DRM-19) | ingest → honest FAIL + **TBD-17 self-discovered bug** |

"Nine regimes. Zero false PASSes. Every BLOCK and every FAIL maps to a specific manifest under-specification or a documented engine gap — none are 'we couldn't figure it out so we guessed.'"

---

## The narrative arc

- The audit engine has 6 gates. Each gate is wired to BLOCK or FAIL when evidence is missing, never to invent a verdict.
- Honesty fences are layered. `solver_execution=ingested` caps `overall_status` at WARN. `validation_status=validated` is schema-blocked unless `solver_execution=real`. These aren't suggestions — they're enforced at the schema level + at gate level + at report-assembly level. Codex tried to coerce a false PASS across 7 review rounds and failed.
- The engine self-discovered TBD-17 mid-dogfood. The fix shipped in the same session. Most demos hide the bugs they found — this demo's load-bearing moment IS the bug, because the discovery + fix arc is the proof that the engine's design works as advertised.
- We dogfooded 9 regimes in one milestone. Not "we support these"; we ran each one through the engine and reported what came out, including the regimes where the engine surfaced schema gaps it doesn't know how to audit yet (compressible physics, VOF phase-fields, LES sub-grid stress, reacting species transport — all queued).
- The advisor surface is intentionally NOT a chatbot. There is no RAG button. The "AI advisor" is a Claude Code session reading the V-series corpus (`.planning/methodology/industrial_case_solver_findings.md`, 85+ V-rows) and driving the engine via CLI. See `V_SERIES_CORPUS_MAP.md`.

---

## What's NOT in the demo

These are deliberate non-features, per the strategic pivot SSOT (`feedback_cfd_harness_ai_advisor_pivot.md` + `feedback_claude_code_is_the_advisor.md`):

- **No RAG retrieval UI button.** The advisor is a Claude Code session reading V-series corpus, not a separately-deployed RAG service.
- **No autocomplete / chat panel inside the workbench.** The workbench runs CFD; the advisor sits beside it.
- **No "AI writes the case" feature.** AI is advisory-only — it GETs case state and gives diagnostic / death-mode opinions; it never writes manifest files or solver dicts.
- **No promise of LES / reacting / VOF schema coverage.** Those gaps are surfaced (gaps #18, #23, #28, TBD-18) and **queued**, not shipped.
- **No CodeBuddy / STAR-CCM+ integration in this demo.** APU bay deliveries via CodeBuddy are a separate workflow (`project_apu_bay_step_reexport.md`).

---

## Commands to copy-paste

```bash
# --- Setup (one-time, terminal A) ---
cd ~/Desktop/cfd-audit-merge
export PYTHONPATH=ui/backend/audit

# --- Stage 1: trail ---
git log --oneline 5250bb7..HEAD

# --- Stage 2: laminar ingest, honest FAIL ---
python -m cfdtrust.cli ingest \
  ~/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65
python -m cfdtrust.cli report \
  ~/Desktop/cfd-harness-unified/_sandboxes/case_027_hagen_poiseuille_pipe/case_v65

# --- Stage 3: LES, honest BLOCK ---
python -m cfdtrust.cli ingest \
  ~/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case

# --- Stage 4: self-discovered bug ---
git log --grep="TBD-17" --oneline
sed -n '120,155p' .planning/dogfood/DOGFOOD_CASE_009.md

# --- Stage 5: capability matrix ---
cat .planning/milestones/CHANGELOG_MILESTONE_2026-05-22.md
```

---

## Source links (everything in this demo is verifiable in-repo)

- 7-round Codex arc retro: `.planning/retrospectives/2026-05-21_v61_201_sub_ingest_codex_5round_arc.md`
- Parent DEC: `.planning/decisions/2026-05-21_v61_201_sub_audit_ingest_mode.md`
- TBD-17 dogfood: `.planning/dogfood/DOGFOOD_CASE_009.md` §TBD-17
- case_028 industrial: `.planning/dogfood/DOGFOOD_CASE_028.md`
- V-series corpus: `.planning/methodology/industrial_case_solver_findings.md` (85+ V-rows)
- Engine README: `ui/backend/audit/README.md`

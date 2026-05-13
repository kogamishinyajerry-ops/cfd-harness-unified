# Q&A Canned Responses — 8 Predicted Peer Questions

> Use during Segment 6 Q&A or as defensive lines mid-demo. **Always defer to honesty** — if peer asks something you genuinely don't know, say so; the project's whole credibility rests on advisor-not-driver + honest caveat.

## Q1 (high probability) — "30 % temperature deficit, isn't that just a bad CFD result?"

> "Yes, and that's exactly the point of showing it. ENGINEERING_CAVEAT.md ships **with** the result — we don't hide it. The deficit is dominated by CFL=35,000 + Euler 1st-order + limitedLinear collapsing to upwind at the strongest gradient. The qualitative flow topology — jet, recirc, suction path, wall-cooling pattern — is correct and shippable for sizing decisions. Detail thermal-load design needs a Boussinesq rerun or CHT + radiation, which is what the advisor's Moment 3 prioritized."

## Q2 (high probability) — "Why didn't you use transient solver from the start?"

> "We did try — buoyantPimpleFoam is exactly what's running here. The 'why not steady' question was answered the hard way: buoyantSimpleFoam attempted 5 times, all diverged in 4-10 iterations with ρ → 1e+10 / ω → 1e+42. That's V5/V6/V7 in our corpus. The compressible-buoyant SIMPLE chain has a known startup instability under jet + suction-outlet + k-ω SST IC. After 5 failures, we switched. The interesting question is **why** we didn't notice earlier — that's V12: mass-conservation sanity checks should be configuration-time, not verdict-time."

## Q3 (high probability) — "How is this different from ChatGPT + a CFD plugin?"

> "Three structural differences, not UX:
> (1) **LLM-offline runnable**. The workbench's full pipeline — CAD ingest → mesh → BC writer → solver → post — runs without any LLM call. Take away the AI, the engineer still ships. ChatGPT plugins fail closed when the LLM is unreachable.
> (2) **Advisor not driver**. Four-question gate: every AI suggestion must be (a) LLM-offline-bypassable, (b) producing auditable artifacts, (c) corpus-cited, (d) advisory not executable. AI is structurally forbidden from writing case files.
> (3) **Project-owned corpus**. The V-series you saw in Segment 3 is sedimented from this project's own industrial cases, not scraped from the web. corpus_loader.py runs offline; it's a `find_relevant` keyword search, not a vector-DB call to OpenAI."

## Q4 (medium probability) — "What's the AI accuracy / hallucination rate?"

> "That's the wrong question for this architecture. Accuracy isn't an AI property — it's a corpus property. The advisor cites V-rows; the engineer evaluates whether the V-row applies. If the V-row is wrong, we fix the V-row (that's the Sediment-as-you-go pillar). If the engineer doesn't trust the cite, they ignore it. There's no 'hallucinated solver scheme' because AI is structurally forbidden from writing solver schemes."

## Q5 (medium probability) — "Mesh max_skew 6.87 — your validation is one case. Is that enough?"

> "Not enough for production claim. V84's status in the corpus is `preliminary positive 2026-05-13 · empirically observed through step 213/3000 · full convergence + post-mortem pending`. We don't say 'closed' until 2 industrial cases confirm + post-mortem is written. That's the V-series Status legend convention. We do publish at preliminary tier so the methodology is shareable; we don't promote until evidence catches up."

## Q6 (medium probability) — "How long did this case actually take you?"

> "Spread across many sessions. The mesh debug arc (V73-V78) was one full day of focused work. The 4-tier HD report generation was 2-3 days of ParaView script iteration. The solver run is 10.4 h ExecutionTime wall clock per attempt. Honest total: about 2 weeks elapsed including 4-5 days of real engineer time. That's faster than our previous baseline (5-7 days for just the first mesh-debug arc), but the demo's not selling 'AI cuts CFD time by 5×' — it's selling 'the workflow is observable and reproducible'."

## Q7 (lower probability) — "Why not use commercial CFD like STAR-CCM+ / Fluent?"

> "STAR-CCM+ does live alongside this — see the `inputs_clean_starccm/` directory; the same STL geometry was prepared for STAR-CCM+ import. The harness is OpenFOAM-first because the CLI surface is automatable end-to-end without a GUI. Most commercial CAEs are GUI-mandatory for setup, which kills 'Claude Code session drives the workflow' before it starts. If a user wants to use this corpus + advisor pattern with STAR-CCM+, the AI-advisor layer is portable — only the executor binding needs swapping."

## Q8 (lower probability) — "What if I want to contribute a V-finding?"

> "Industrial case surfaces a death mode → add a row to `.planning/methodology/industrial_case_solver_findings.md` with the 7-column schema (Surface / Engineer symptom / Root cause / Fix / Status / Reference case / Lesson). After ~5 V-rows accumulate, run the corpus sync to `docs/openfoam_corpus/industrial_solver_findings_v_series.md` so the runtime `/ai-diagnose` advisor picks it up. We have a session 2 hours ago that did exactly that — 27 V-rows synced in one commit (`a0effac`). Process is documented at the file header."

---

## Hard rules during Q&A

- **Time-box answer**: 60 s for predicted Q1-Q5, 90 s for Q6-Q8.
- **Don't oversell**: if peer is skeptical, agree where they're right ("yes, mesh validation is preliminary"), then redirect to what is structurally defensible.
- **Hand off after**: "happy to share `~/Desktop/cfd-harness-unified/CLAUDE.md` + the V-series corpus file — DM me, I'll send."
- **Hard stop at 30:00**: "Time's up — let's keep going after the session."

## Questions NOT to invite

- "Show me the C++ source of corpus_loader.py" — say "happy to share offline, the file is `ui/backend/services/ai_advisor/corpus_loader.py`, 431 lines, public in the repo".
- "Can you live-run the advisor now?" — say "I pre-recorded for stability reasons today; happy to do a live one-on-one after".
- "What's your license?" — depends on context; if no answer prepared, say "internal pilot, license terms TBD".

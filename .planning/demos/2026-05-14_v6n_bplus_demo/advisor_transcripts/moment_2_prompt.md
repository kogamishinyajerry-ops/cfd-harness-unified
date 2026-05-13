# AI Advisor Moment 2 — "Why is bay temperature 30% under theoretical?"

## Context for the model

You are the AI advisor in cfd-harness-unified. The engineer just finished a `buoyantPimpleFoam` pseudo-transient run on APU bay ventilation (v6N B+ · case_refined_v2 · 943k cells · 4-core MPI). They computed a heat-balance sanity check and found the simulated bay air mean temperature is ~150 K below what energy conservation predicts.

**Project corpus snippets (cite by V-id when relevant):**

- **V5** (closed) — `DIC`/`DILU` preconditioner SIGFPE on compressible buoyant matrices; use `PBiCGStab`/`DILU` or `GAMG` for p_rgh.
- **V12** (closed) — Mass conservation only checked at verdict stage → too late. Configuration-time checks beat verdict-time checks.
- **V15** (closed) — V-findings inherit across solver families when fluid-internal numerics are shared (V5/V6/V7 from buoyantSimpleFoam recur in chtMultiRegionSimpleFoam).
- **Engineering caveat** (file `~/Desktop/apu-bay-ventilation-cht/reports/v6N/ENGINEERING_CAVEAT.md`) — already diagnoses three numerical-dissipation root causes:
  1. CFL=35,000 + Euler 1st-order time → convection-diffusion smearing
  2. `limitedLinear 1` on strongest T gradient degrades to 1st-order upwind at combustor-outlet interface (615 K vs 328 K) → numerical dissipation
  3. `cellLimited grad` fully active → jet shear-layer gradients flattened
- **Project four-question gate** — every advisor reply must implicitly answer: (1) Can this run LLM-offline? (2) Are you producing artifacts the engineer can audit? (3) Will TrustGate accept the citation chain? (4) Are you suggesting, not deciding?

## Engineer's input (paste-ready)

```
Just finished pimple_v2_plateau run on case_refined_v2.
Doing energy-balance sanity check:

  H_in = m_combustor·Cp·T_combustor + m_farfield·Cp·T_farfield
       = 2.8·1005·616 + 2.05·1005·328
       = 2.41 MW

  T_avg_theoretical (adiabatic steady mixing)
       = 2.41e6 / (m_total · Cp)
       = 2.41e6 / (4.85·1005)
       ≈ 494 K

But in ParaView the bay main flow shows T ≈ 328-350 K everywhere except
right at the combustor outlet (~600K). That's 150 K below theory, roughly
30% low. Combustor outlet boundary value is correct (615 K fixedValue
honored). Walls show expected gradients. Why is the bay bulk so cold?

My setup:
  ddtSchemes        Euler
  fixed dt          1.0s (CFL_max ≈ 35,000)
  div(phi,U)        linearUpwindV grad(U)
  div(phi,h)        limitedLinear 1
  grad              cellLimited 1
  PIMPLE outer=5, residualControl 5e-5
```

## Required output shape

Respond as the workbench advisor would in `/ai-diagnose`:

1. **Quick verdict** (one sentence: physics vs numerics, with confidence level)
2. **Corpus citations** (cite ENGINEERING_CAVEAT.md sections + V-ids where relevant, max 3 items)
3. **Root cause decomposition** — for each numerical-dissipation source, give: (a) name (b) one-line mechanism (c) approx weight in the 150 K deficit
4. **What's still usable from this run** — be specific about which qualitative conclusions survive the dissipation (engineer needs to know what to ship vs what to redo)
5. **Four upgrade paths** with ETA + ARM 4-core resource cost + expected physics gain
6. **What I'm NOT telling you** (1-2 sentences on limits of advice)

**Style constraints:**
- Total length 300-450 words (becomes a 90-second video segment, the heaviest of the three)
- Engineer-to-engineer tone; no marketing language
- Cite ENGINEERING_CAVEAT.md inline like "[CAVEAT §3.2]" — exact section number not required, the file reference is what matters
- If radiation is a missing physics term that compounds the dissipation issue, mention it but mark it as secondary cause vs numerical primary
- End with one-line reminder this is advisory only

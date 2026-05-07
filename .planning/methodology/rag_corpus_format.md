# RAG Corpus Format (M6 prerequisite)

> **Living document.** Defined ahead of M6 AI Advisor charter (per
> DEC-V61-198 Phase δ trigger condition: corpus ≥ 20 process-log
> entries). Establishes the **schema** that case threads must
> produce so M6 RAG loader can ingest without retroactive
> reformatting.
>
> **No loader code yet.** This file is a contract: case threads
> write logs in this shape from now on, M6 charter wires the
> loader when corpus crosses threshold.

## Why this exists

Per DEC-V61-198 Pillar 3, the AI advisor's leverage comes from
RAG over **our own industrial case process logs**, not papers.
For that to work, every case thread must produce artifacts in a
consistent schema so:

1. The loader can index without case-specific parsing
2. AI Review can answer "your case resembles industrial case X
   version Y" by surfacing the matched corpus entry directly
3. AI Diagnose can match "you are at V_n; recommended fix family
   is S_m" by linking V-series rows to playbook entries to your
   current symptom

If the format is defined late, every existing case-log gets
retroactively reformatted — which is exactly the kind of
mid-arc churn the project should avoid.

## Per-case corpus contribution

Each industrial case in `case_index.md` produces **5 corpus
artifacts**, all in the case's desktop sandbox + cross-referenced
from the case's reference profile in
`.planning/case_profiles/case_NNN_<name>.md`.

### Artifact 1 — Reference profile (canonical entry-point)

| Path | `.planning/case_profiles/case_NNN_<name>.md` |
|---|---|
| Format | Markdown, this repo |
| Schema | See existing examples (`case_002a` / `case_002b`); required sections: header / pointer / per-stage wall time / hand-coded vs reused / V-series sourced / coverage axis / what's missing / references |
| RAG role | Primary search index; AI Review's first-stage retriever matches against these |

### Artifact 2 — SSOT case configuration (input snapshot)

| Path | `<case-sandbox>/config/case.yaml` |
|---|---|
| Format | YAML (case-thread native) |
| Schema | Already case-thread defined; corpus consumes verbatim |
| RAG role | "What was the input config for this run?" — direct evidence for AI Review when comparing two cases at the BC / mesh / solver-config layer |
| Notes | If a case has multiple version files (`case.yaml.v1`, `case.yaml.v2`), keep all; corpus indexes per-version |

### Artifact 3 — Run log bundle (per-version)

| Path | `<case-sandbox>/case/log/` (or equivalent) |
|---|---|
| Format | Plain text, one log per stage, OpenFOAM solver output for the solver stage |
| Schema | Each version produces 4-6 logs: surfaceFeatureExtract / blockMesh / snappyHexMesh / checkMesh / solver / post-processing |
| RAG role | "What did the solver actually do?" — substrate for AI Diagnose's symptom matching (residual patterns, NaN events, clamp activity) |
| Notes | Logs are versioned by suffix (`05_solver_v13.log`, `05_solver_v14.log`) or by version-tagged subfolder; corpus indexes both layouts |

### Artifact 4 — Final report (per-version)

| Path | `<case-sandbox>/evidence/<version>/REPORT.md` |
|---|---|
| Format | Markdown, this repo's report dialect |
| Schema | Required sections: Executive summary / Physics + workload / Mesh / Solver config / Convergence / Physics results / Limitations / Next steps / File manifest |
| RAG role | Authoritative "what we learned this version" — closes the loop AI Review needs to say "...the previous case shipped at v13 with this final outcome" |
| Notes | If running multi-version (case_002a v1-v14), each version gets its own report subdir |

### Artifact 5 — Decision log (rationale capture)

| Path | `<case-sandbox>/docs/decisions_v<n>.md` (or scattered in REPORT.md "Engineering decision log" appendix) |
|---|---|
| Format | Markdown |
| Schema | Per-decision rows: decision / chosen option / alternatives / rationale / version where landed |
| RAG role | **The highest-leverage artifact for AI advisor**. Tells WHY a choice was made — captures the engineer's mental model, not just the configuration |
| Notes | Often the load-bearing source for "why did this case choose pressure-outlet instead of mass-flow at v1?" — answer comes from this artifact, not from the config |

## V-series finding cross-link

Each V-series entry in `industrial_case_solver_findings.md` carries
a `Reference case` field pointing at the case_NNN reference profile
that surfaced it. The corpus loader uses this as a back-link:
"finding V14 came from case_002b CHT; here's case_002b's reference
profile + run logs + decision log".

## Numerics-class taxonomy (for inheritance retrieval)

Per V-series Pattern 6, V-findings inherit across solver families
when fluid-internal numerics match. The corpus must tag each case
with its `numerics_class`:

| Numerics class | Solver examples | Inherits findings from |
|---|---|---|
| compressible-buoyant-RANS | buoyantSimpleFoam, chtMultiRegionSimpleFoam (fluid sub-solver) | (root) |
| incompressible-RANS | simpleFoam, pisoFoam steady | (root) |
| compressible-shock-density-based | rhoCentralFoam, sonicFoam | compressible-buoyant-RANS (partial: high-Mach extras) |
| incompressible-LES | pisoFoam-LES | incompressible-RANS (partial: turbulence-model extras) |
| multiphase-VOF | interFoam | (root) |
| reacting-low-Mach | reactingFoam, fireFoam | compressible-buoyant-RANS (partial) |

The reference profile's "Solver-class capability axis" section
should declare the case's `numerics_class` so corpus retrieval can
surface inherited findings.

## Decision rationale schema (artifact 5 detail)

For AI advisor leverage, the decision-log entries should follow:

```markdown
### 决策 N · <one-line summary>

- **Decision**: <chosen option in 1 sentence>
- **Alternatives considered**:
  - <option A>: <why rejected>
  - <option B>: <why rejected>
- **Rationale**: <why this option chosen — the load-bearing reason>
- **Lands at version**: v<n>
- **V-series link** (if applicable): V_n
- **Reversibility**: high | medium | low (can future versions
  revisit?)
```

Free-form prose between rows is fine; the structured fields are
what the corpus loader extracts.

## Artifact size guidance

Corpus loader will eventually need to chunk for embedding. Target
sizes:

- Reference profile: 2-10 KB (single file, no chunking needed)
- Solver log: 50 KB - 5 MB (chunk by `^Time = N` boundaries)
- Final report: 5-50 KB (chunk by `^## ` headings)
- Decision log: 1-20 KB (chunk by `^### 决策 N` boundaries)
- case.yaml: 1-10 KB (single file)

Logs > 10 MB should be downsampled (drop intermediate iterations,
keep first 50 + last 50 + every 100th in between) — solver log
size beyond this point is mostly redundant.

## Privacy / governance constraints

- **No PII / customer data** in corpus artifacts; industrial cases
  may use internal geometry but should be sanitized of customer
  identification before adding to corpus
- **Decision-log rationale** that contains business-sensitive
  context (e.g. "we chose Re=10^6 because the customer's flight
  envelope is X") should be redacted or generalized
- **OpenFOAM raw output** is not sensitive; logs can be ingested
  verbatim
- **AI advisor outputs** that cite corpus entries must respect the
  same redaction (no leak via citation)

## Update cadence

Update this file when:
- A new case adds an artifact type not currently listed
- M6 charter lands (cross-link to actual loader implementation)
- Numerics-class taxonomy gets a new row (with a new solver class)
- Decision-log schema needs a new field

Update the corpus *contents* (not this file) every time:
- A case version completes — append run log, update report,
  append decision rows
- A V-series finding lands — back-link to case
- A case closes — final write-back of REPORT.md + decision log

## References

- DEC-V61-198 — Phase δ trigger (corpus ≥ 20 launches M6)
- `industrial_case_solver_findings.md` — V-series (corpus-back-linked)
- `solver_convergence_playbook.md` — decision tree (corpus-back-linked)
- `case_index.md` — multi-case tracker (lists corpus contributors)
- `~/Desktop/apu-bay-ventilation/evidence/v13_post_v5_183632/REPORT.md`
  — example of artifact 4 (final report)
- `~/Desktop/apu-bay-ventilation-cht/docs/decisions_v1.md` — example
  of artifact 5 (decision log; loose schema, will be tightened with
  next version's update)

# Case Index

> **Multi-case tracker.** Established by DEC-V61-198 strategic pivot
> (2026-05-07). The project state is described by **which solver
> classes have a covered case running through it**, not by case
> count.
>
> Each row points at a `case_NNN_<name>.md` reference profile (or
> `.yaml` for gold-standard academic cases). Industrial cases live
> in dedicated desktop sandboxes; their reference profile in this
> repo is a pointer + summary, not a copy.

## Active threads

| case_id | Solver class | Case-thread location | Status | V-series source | Last touch |
|---|---|---|---|---|---|
| `case_002a_apu_bay_buoyant_simple` | Internal flow + buoyancy + forced convection | `~/Desktop/apu-bay-ventilation/` | active · v14 @ iter 813+ | V3-V13 | 2026-05-07 |
| `case_002b_apu_bay_cht` | CHT (multi-region + radiation) | `~/Desktop/apu-bay-ventilation-cht/` | active · v2 norad @ iter 67+ | V14-V15 | 2026-05-07 |

## Closed threads

(none yet)

## Pending solver-classes

Per DEC-V61-198 coverage map. Pull when concrete brief arrives — do
not pre-stage.

| Solver class | Status | Likely candidate when triggered |
|---|---|---|
| External flow + high-Re + boundary layer | pending | intake diffuser / NACA airfoil at engineering Re |
| Rotating machinery (MRF / sliding mesh) | pending | fan / pump impeller |
| Multiphase / VOF | pending | sloshing oil sump / offshore |
| Compressible high-speed | pending | nozzle / transonic |
| Combustion / reacting flow | pending | combustor / fire spread |
| Transient LES / DES | pending | bluff-body wake / aeroacoustics |

## Gold-standard academic cases (reference fleet, not industrial)

See `case_profiles/*.yaml` — 10 frozen cases from the
project's earlier methodology phase. **Not the dogfood substrate
post-DEC-V61-198**; retained as verdict-tolerance fixtures only.

## Conventions

- **Naming**: `case_NNN_<short_name>.md` for industrial reference
  profiles. NNN is monotonically allocated; sub-letters (a/b/c)
  indicate parallel threads on the same physical case (different
  solver, different physics simplification, etc.).
- **Industrial references are pointers, not copies**: the
  reference profile in `.planning/case_profiles/` documents
  per-step wall times, V-series source, what's hand-coded vs reused
  — but the case files themselves stay in the desktop sandbox.
- **Gold-standard cases stay in YAML** (legacy schema with
  `risk_flags`, `tolerance_policy`); industrial cases stay in
  Markdown (no benchmark, narrative documentation).
- **Updating this index**: any time a case-thread starts, closes,
  or sediments a new V-series finding, append/update the row +
  bump "Last touch". Append-only for the "Closed threads" section.

## How a case gets a row

A case earns a row when it satisfies all three:
1. Has at least one full pipeline run (CAD → mesh → solve at least
   to first time-step)
2. Has produced at least one V-series finding (or validated an
   existing one)
3. Has a reference profile written under `.planning/case_profiles/`

A case is **closed** (move to "Closed threads") when:
- Final report exists in the case-thread sandbox
- All V-series findings backfilled into the index
- Any reusable engineering pattern is either extracted as a
  main-project artifact or filed as a deferred-extraction note
  in the reference profile

## Cross-references

- `solver_class` taxonomy: DEC-V61-198 §"Three pillars · P1"
- V-series finding format: `industrial_case_solver_findings.md`
- Solver convergence playbook: `solver_convergence_playbook.md`
- RAG corpus format (M6 prerequisite): `rag_corpus_format.md`
- Per-case ingestion checklist: DEC-V61-198 §"Six per-case standard moves"

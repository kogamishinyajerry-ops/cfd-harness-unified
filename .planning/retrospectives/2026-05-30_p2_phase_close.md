# P2 phase-close · Blueprint v4 "close the AI loop on RANS-aero vertical" · 2026-05-30

> Parents: DEC-V61-207 (Blueprint v4 charter) · DEC-V61-209 (P1 V&V loop CLOSED, source of W2.1 distillation lessons) · DEC-V61-210 (cfdtrust canonical V&V runner).
> Arc: P2 sub-DECs **V61-211..V61-216** (6 sub-DECs, all Status=Accepted, Notion-synced). HEAD `01752c9` lands DEC-V61-216 W2.1.
> Trigger: **phase-close** (P2 deliverable COMPLETE — pre-flight extractor substrate + post-run ruleset distillation contract both shipped). Mandatory per RETRO-V61-001 cadence trigger #1.
> Codex this phase: all 6 sub-DECs went through Codex relay under v2.3 round cap=3; 1 cap=3 overflow (DEC-V61-212, separate retro `2026-05-28_dec212_codex_round3_overflow.md`); 1 86gs xhigh 429 → CRS gpt-5.4 fallback (DEC-V61-214); 1 cadence docstring-vs-code gap caught at THRESHOLD=30 (R9 fast-divergence, separate retro `2026-05-29_cadence_codex_r1_r9_fast_divergence.md`). Per `~/Desktop/cfd-audit-merge/CLAUDE.md` "Notion 深度同步规则", this retro is local-only (retros NOT synced).

## 做了什么 (what)

P2 split into two substrate workstreams, both landed:

**Pre-flight signal substrate (Stage-2 2b extractors · `ui/backend/services/case_extractors/`)** — four stdlib-only `case_dir → advisor kwargs` readers, each scope-locked, each honest-`None` on absent keys, each shipping with regression tests + truth-chain table:

- **DEC-V61-211** `solver_block_extractor.py` — reads `system/controlDict` for `solver` / `adjustTimeStep` / `deltaT`; defines a **local mirror dataclass** (`SolverBlockSnapshot`) so importing the extractor does NOT drag trimesh into the advisor surface (the canonical `SolverBlockSnapshot` lives downstream in a trimesh-touching path).
- **DEC-V61-212** `shm_dict_extractor.py` — line-anchored `snappyHexMeshDict` parser feeding `validate_shm_dict`. v2.3 cap=3 overflow honored — R0+R1+R2 chain hit P2 residual (`#codeStream {` same-line directive body); honest scope-out documented in extractor docstring. Established the **"enumerate ALL forms BEFORE writing"** discipline as a project pattern.
- **DEC-V61-213** `thermo_dict_extractor.py` — `constant/thermophysicalProperties` parser feeding A10 `thermo_polynomial_range_advisor`. R1 introduced the **key-presence detector** pattern: numeric-required regex distinguishes "key present but unparseable" from "key absent" for optional `thermoType.transport` / `mixture.specie.molWeight` fields. Pattern carried forward by 214/215/216.
- **DEC-V61-214** `step_extractor.py` — discovers `step_path` + `bbox_max_extent_raw` + `body_extents_raw` for `unit_detector.detect_unit`. Design phase **overrode the brief framing**: mojibake/STEP-header parse deferred out of v0.1 scope (no in-repo case consumes them); carried the key-presence pattern into multi-source field resolution (manifest fallback shadow risk). 86gs xhigh hit 429 mid-review → CRS gpt-5.4 high fallback completed APPROVE_WITH_COMMENTS.

**Post-run ruleset distillation substrate (W2.0.6 slice extension → W2.1 rules)** — Blueprint v4 Law-3 productization path moves forward:

- **DEC-V61-215** `RunArtifactSlice` extension (W2.0.6) — widens the slice with **three optional nested dataclasses** (`DevelopedRegionGoldDelta` / `IntegratedDragPct` / `ReferenceBandSummary`), each tracing **verbatim** to `trust_report.json:gates.reference_comparison.details.*`. R1 invariant: optional fields stay `None` when unknown — **never fabricate `0.0` sentinel**. Cross-language Python+TS dataclass parity green. Data-shape-only — zero new rules.
- **DEC-V61-216** W2.1 substantive distillation — **three new v9 advisor rules R10/R11/R12** distill the DEC-V61-209 ADDENDUM 4/5 NASA-convention near-LE / shape-mismatch / XOR-disagreement post-run lessons. Each rule fires on a different ADDENDUM lesson, cites its W2.0.6 consuming field verbatim, ships with 6 fixtures (2 reused from W2.0.6 + 4 new) and 15 parity assertions. Shared `NASA_TOL_PCT=10.0` module-level constant prevents literal drift between R10/R11/R12. CRS gpt-5.4 R0+R1 atomic APPROVE_WITH_COMMENTS. HEAD = `01752c9`.

**The v9 ruleset grew from 8 → 12 rules**, every rule data-shape-only and zero in-loop LLM — ratifying Blueprint v4 Law-3 (the offline ruleset ships and runs without AI).

## P2 sub-DEC ledger

| DEC | Status | Workstream | Delivers | Codex | confidence |
|---|---|---|---|---|---|
| **V61-211** | Accepted | W-Extractor-1 | solver_block extractor — local-mirror dataclass to break trimesh import contagion | APPROVE_WITH_COMMENTS (clean chain) | high |
| **V61-212** | Accepted | W-Extractor-2 | shm_dict extractor — cap=3 overflow honored, residual P2 → retro | APPROVE_WITH_COMMENTS @ R2 (P2 residual deferred per v2.3) | high |
| **V61-213** | Accepted | W-Extractor-3 | thermo_dict extractor — key-presence detector pattern established | APPROVE_WITH_COMMENTS (R1 closed) | high |
| **V61-214** | Accepted | W-Extractor-4 | STEP-path extractor — workflow autonomy override (mojibake deferred) | APPROVE_WITH_COMMENTS (CRS fallback after 86gs 429) | high |
| **V61-215** | Accepted | W2.0.6 (slice) | `RunArtifactSlice` × 3 nested dataclasses (data-shape only) | APPROVE_WITH_COMMENTS (cross-language parity green) | high |
| **V61-216** | Accepted | W2.1 (rules) | R10/R11/R12 v9 rules + 6 fixtures + 15 parity assertions | APPROVE_WITH_COMMENTS (R0+R1 atomic CRS) | high |

All 6 frontmatter `notion_sync_status: synced 2026-05-28..2026-05-30` against the Decisions DB.

## 关键发现 (key findings — lessons learned)

1. **Enumerate ALL forms of a class-of-bugs BEFORE writing the fix.** Reactively responding to Codex's specific repro guarantees R{N+1} finds the sub-case you missed. DEC-V61-212 R0+R1+R2 chain demonstrated this end-to-end: R1's line-only `#` skip regressed pre-R1's whole-block skip behavior for `#codeStream\n{`, then R2 missed the same-line `#codeStream {` form (retro `2026-05-28_dec212_codex_round3_overflow.md` lines 12-14, 56). Zero in-repo SHM cases triggered the residual P2 → honest scope-out documented in extractor docstring. **Carry-forward**: P3 CHT extractors (multi-region `regionProperties`, `changeDictionaryDict`, per-region nested directives) — survey all real cases' syntax forms BEFORE writing any per-region parser, especially `#include` / `#codeStream` / `#calc` shapes.

2. **Key-presence detection must be distinct from value-extraction for optional fields.** A manifest fallback can silently shadow a malformed primary source unless presence is tracked independently of value. DEC-V61-213 R1 introduced the numeric-required regex (tracks "key present but unparseable" vs "key absent"); DEC-V61-214 R1 carried it forward to multi-source field resolution (STEP manifest fallback could mask corrupted primary `bbox` block). Both shipped as separate code paths to prevent value-fabrication on partial reads. **Carry-forward**: P3 CHT `regionProperties` / per-region `thermophysicalProperties` — region-list presence vs region-payload completeness are independently optional and need the same separation.

3. **Optional fields stay `None` when unknown — never fabricate `0.0` or empty-string sentinels.** Downstream rules must short-circuit on `None` rather than match on a synthetic default that the truth-chain cannot defend. DEC-V61-215 R1 invariant: W2.0.6 nested dataclass fields stay `None` when `trust_report.json:gates.reference_comparison.details.*` keys are absent. DEC-V61-216 R10 known-gap fixture `dec209_r10_xfloor_unknown_known_gap` proves R10 silently skips when `x_floor_m is None` rather than firing on a fabricated `0.0` cutoff. Same lesson as DEC-V61-209 cycle-3g ("don't rationalize") at the data-contract layer. **Carry-forward**: P3 CHT slice extension (a "W3.0.6"-equivalent for region-temperature-delta / interface-flux) — every new optional field gets a known-gap fixture that pins the silent-skip.

4. **Shared module-level constants prevent literal drift between related rules.** DEC-V61-216 R12 hard-codes `NASA_TOL_PCT=10.0` as a module-level literal in both Python `rules.py` and TS `v9_advisor_rules.ts`, with explicit DEC-209 ADDENDUM 4 citation. The DEC §"Parity strategy" calls out the literal as byte-identical across runtimes. **Carry-forward**: P3 CHT canonical constants (e.g. `CHT_INTERFACE_FLUX_TOL_PCT`, `CHT_TEMPERATURE_GRADIENT_TOL_K_PER_M`) at module level with single DEC-citation source; never inline as literals at predicate-call sites.

5. **Cadence Codex reviews (THRESHOLD=30 gestalt pass) catch defects per-PR reviews miss by construction.** Per-PR reviews don't read docstring + implementation against each other; the cadence pass has to read both. Cadence retro `2026-05-29_cadence_codex_r1_r9_fast_divergence.md`: R9 went through its own DEC commentary, commit body, and crossed individual reviews on DEC-211/212 commits, but only the cadence pass on `origin/main..HEAD` 38-commit aggregate caught that `recentResiduals(...,4)` early-return defeated the stated "V6 first-iter fast-divergence" target. **Carry-forward**: keep cadence hook enabled; expect at least one P3 cadence pass to catch a "rule docstring claims X but predicate covers Y" contradiction in CHT-specific advisors before P3 close.

6. **Workflow autonomy is real — design phase will (correctly) override brief framing when the framing conflicts with what an honest data contract supports.** Record the deferral, do not silently widen scope. DEC-V61-214 design phase OVERRODE the brief's mojibake/STEP header-parse framing; shipped only the fields `unit_detector.detect_unit` actually consumes. Deferred items recorded in §"Out of scope" for a separate `step_brep_inspector` sub-DEC. **Carry-forward**: P3 CHT charter authoring — pre-state which P3 scope-outs are deliberate (e.g. "CHT coupling-only, NOT conjugate radiation") so the design phase doesn't need to override the brief; also pre-register CRS fallback as expected when 86gs xhigh quota tight.

7. **The scalar-rule space saturated at R9; further honest distillation required widening the data contract first (W2.0.6) before writing rules (W2.1).** This is the **same sequencing constraint** the P1-close blindspot retro finding-5 predicted. DEC-V61-215 (W2.0.6) added 3 nested dataclasses BEFORE DEC-V61-216 (W2.1) wrote R10/R11/R12. Trying to write the rules first would have manufactured theater rules with no discriminating power (same class as the W1.1 circular pre-flight finding). **Carry-forward**: P3 CHT cannot skip a `W3.0.6`-equivalent slice extension. Plan two sub-DECs per CHT distillation increment (slice + rules), not one.

## 治理 (governance)

| Gate | Status |
|---|---|
| Four-question gate (all 6 sub-DECs) | ✅ LLM-offline (pure stdlib extractors + pure-function predicates; `test_stack_zero_llm_imports` green) · artifacts (each extractor outputs deterministic dataclass; each rule emits `matched_at` string) · TrustGate (advisor-only surfacing; honest-`None` invariants) · AI advisory-only (no mutating route touched; DEC-V61-130/132 contracts intact) |
| Truth-chain | ✅ DEC-215/216 ship verbatim source-key tables (`trust_report.json:gates.reference_comparison.details.*` → consuming field path); DEC-216 R12 cites DEC-209 ADDENDUM 4 line range for `NASA_TOL_PCT=10.0`; no fabricated provenance (P1-close retro finding-2 actively defended against in W2.1 authoring) |
| Codex round cap=3 (v2.3) | ✅ All 6 chains within cap. **1 cap=3 overflow**: DEC-V61-212 R2 P2 residual deferred to retro queue per V133 (separate cap=3 overflow retro). **1 relay fallback**: DEC-V61-214 86gs xhigh 429 → CRS gpt-5.4 high reconciled cleanly. **1 cadence catch**: R9 docstring-vs-code fixed @ R1 + KNOWN-GAP documented |
| Cross-language parity | ✅ DEC-215 dataclass parity (Python + TS) + DEC-216 15 parity assertions (9 legacy + 6 new) green across runtimes; `js_to_fixed` / `toFixed` byte-identical `matched_at` strings |
| Cadence trailer pre-push hook | ✅ Each push HEAD carried canonical `Codex-verified: VERDICT` first-token trailer; THRESHOLD=30 fired once mid-P2 (R9 catch, 38-commit aggregate) and reset cleanly |
| Notion sync | ✅ All 6 sub-DEC frontmatters carry `notion_sync_status: synced YYYY-MM-DD (<url>)` against Decisions DB. This retro is local-only per rule (retros NOT synced) |
| Pollution guard | ✅ No live-solve artifacts committed; W2.0.6 fixtures are synthetic shapes of `trust_report.json:gates.reference_comparison.details.*`, not real solve output |
| confidence | high (6 Codex-reviewed sub-DECs, cross-language parity green, ruleset 8→12 rules with verbatim citations, scope-outs all documented with deferred-trigger rationale, P3 readiness == "needs a charter, not features") |

## Cadence + Codex discipline observations (P2 windows)

- **86gs xhigh primary / CRS gpt-5.4 high fallback** — the documented relay topology (per `~/CLAUDE.md`) exercised cleanly in P2. 86gs handled DEC-211/212/213/215/216; CRS picked up DEC-214 mid-review after 86gs returned **429 Too Many Requests** with no verdict. CRS verdict transcripts archived (`reports/codex_tool_reports/`, gitignored per step-1 C4 convention).
- **Trailer format `Codex-verified: VERDICT` as first token of HEAD commit body** confirmed working with cadence hook across 6 sub-DEC chains; no false positives, no missed catches.
- **All landed Codex reviews caught real bugs that would have shipped silently** — R10 station-gate, R12 boundary, x_floor fabrication risk, UnicodeDecodeError leak, manifest stale-data override, NaN/Inf contagion. Per-PR reviews handled the local defects; the cadence pass caught the cross-commit drift (R9 docstring/code mismatch).
- **v2.3 cap=3** held under DEC-212 stress (P2 residual deferred to retro queue, not iterated past R2). No V131-style 22-round spirals observed in P2. Total Codex rounds across 6 sub-DECs: ~14 rounds (averaging ~2.3/DEC including R0 + at most 2 fix iterations).
- **Notion sync discipline**: only Status=Accepted DECs synced; spike commits / retros / charter drafts excluded. P2 session-end batch sync was zero-friction (all 6 sub-DEC `notion_sync_status` already set during landing).

## RETRO-V61-001 cadence check — post-R3 live-run defects?

Searched `.planning/retrospectives/` for the **post-R3 defect class** (cadence trigger #2: Codex APPROVE'd then smoke/live-run revealed a bug). P2 retros surveyed:

| Retro | Cadence trigger | Post-R3 defect class? |
|---|---|---|
| `2026-05-28_p1_close_p2_blindspot_findings.md` | P1 phase-close + 2 blind-spot findings | **None.** Findings 1/2/3/4 were caught BEFORE Codex APPROVE (adversarial-design / pre-write audit / integration-vs-unit / 86gs reconcile). Finding 5 is methodology-meta. |
| `2026-05-28_dec212_codex_round3_overflow.md` | cap=3 overflow | **None.** R2 residual P2 deferred per v2.3 rule, not a post-APPROVE defect. |
| `2026-05-29_cadence_codex_r1_r9_fast_divergence.md` | cadence pass at THRESHOLD=30 | **No** in the strict RETRO-V61-001 sense. R9 was caught by the cadence Codex pass BEFORE post-merge / smoke run — gestalt review is a Codex layer, not a post-Codex layer. (Reasonable to log under finding 5's "claim/code drift recurrence" methodology pin.) |
| This retro | phase-close | **None.** All 6 P2 sub-DECs landed Codex APPROVE; no smoke/live-run defect attributed to any of them post-merge. |

**Verdict**: zero post-R3 live-run defects in the P2 window. The RETRO-V61-001 cadence trigger #2 was not invoked. The two methodology pins from this phase (claim/code drift recurrence + rule-of-3 for promoting a claim/code automated test) stay tracked in the cadence retro, not promoted to a hard methodology.

## Deferred items (active backlog · explicit triggers)

| Item | Why deferred | Trigger to resume |
|---|---|---|
| **W2.0.7** — production `manifest_adapter::build_manifest()` wiring (inject `trust_report` top-level from `<case_dir>/artifacts/trust_report.json`) | DEC-V61-215 R1 scope-out: fixture-only validation was sufficient for the data-shape contract; production manifest wiring is separate review surface | First real customer case lands a `trust_report.json` with `gate_mode == 'nasa_integrated'` AND a downstream consumer needs R10/R11/R12 to fire on real run output |
| **W2.2** — production wiring of R10/R11/R12 advisory surfacing through `/api/cases/{id}/ai-review` and dashboard | DEC-V61-216 §"Out of scope": fixture-only validation per W2.0.6 R1 scope-out; dependency on W2.0.7 first | After W2.0.7 lands AND first dashboard E2E test surfaces an R10/R11/R12 match on a real `trust_report.json` |
| **`step_brep_inspector` sub-DEC** — STEP header mojibake decode + B-rep topology inspection | DEC-V61-214 design phase deferred: no in-repo case consumes mojibake-decoded PRODUCT names; `unit_detector.detect_unit` only needs `step_path + bbox_max_extent_raw + body_extents_raw` | First real CAD-bearing case (e.g. P3 CHT plate-fin / blade-cooling) lands a STEP with Chinese PRODUCT names or requires per-body extraction |
| **R13 candidate** — `\|integrated_drag_pct.pct - station_pct\|` magnitude-of-disagreement rule | DEC-V61-216 §"Out of scope": R12 discriminator is PASS/FAIL boundary-crossing, not absolute delta; would need new field on `IntegratedDragPct` | First case where R12 fires on a marginal XOR (e.g. 9.99 vs 10.01) AND a user reports advisory noise because practical delta is sub-percent |
| **`_SEVERITY_RANK` reorder for strict `high` tier above `warn`** | DEC-V61-216 §"Severity rank reconciliation": would reorder every existing match list, separate sub-DEC required | UI consumer explicitly requests visual severity escalation in dashboard advisory list |
| **V6 first-iter mass-flow-zero-IC single-sample blow-up rule** | Cadence retro lines 56-62: single residual at O(1) indistinguishable from startup transient without slice-extension flag (`first_iter_residual_o1`) | Slice extension lands the discriminating field (likely P3+ V-series harvest from CHT solver init) |
| **Automated docstring-vs-code parity test for v9 rules** | Cadence retro finding 2 lines 76-86: rule-of-3 not yet hit (R9 case is first; need second occurrence before promoting methodology) | Second cadence Codex pass surfaces an analogous "covers list ≠ predicate behavior" drift on a different rule |

## Carry-forward patterns (sediment for P3 reuse)

These patterns first crystallized in P2 and are explicit reuse candidates for P3 CHT and beyond:

1. **Local-mirror dataclass to break import contagion** (first: DEC-V61-211 `SolverBlockSnapshot` local mirror). Reusable in: P3 CHT region-mapping reader for `constant/regionProperties` likely needs to mirror a CHT-coupling dataclass without pulling the full multi-region solver runtime; any P4+ extractor touching advisor kwargs but staying stdlib-only.
2. **Honest `None` for absent keys + downstream short-circuit + known-gap fixture pinning silent-skip** (first: DEC-V61-211, systematized in DEC-V61-215 R1, enforced in DEC-V61-216 R10 known-gap fixture). Reusable in: every P3 CHT slice-extension optional field; every future data-contract extension.
3. **Key-presence detector separate from value extractor for optional fields, with numeric-required regex** (first: DEC-V61-213 R1, carried by 214/215/216). Reusable in: P3 CHT `regionProperties` / `chtMultiRegionSimpleFoam` BC dicts where region-list presence vs region-payload completeness are independently optional.
4. **Shared module-level constants for cross-rule literals** (first: DEC-V61-216 R12 `NASA_TOL_PCT=10.0`, byte-identical Python+TS). Reusable in: P3 CHT canonical tolerance constants; any P4+ vertical with physical-convention thresholds shared across rules.
5. **"Enumerate ALL forms BEFORE writing the fix"** (first: DEC-V61-212 cap=3 overflow retro). Reusable in: all P3+ extractors over solver-authored files; any rule predicate that branches on syntax forms in source artifacts.
6. **Truth-chain table in DEC body** — every new field / rule lists `(source DEC §, verbatim source key, consuming code path)` so a reader can dereference every claim without opening another file (first: DEC-V61-215 §"Truth-chain", adopted in DEC-V61-216). Reusable in: P3 CHT charter + sub-DECs; makes the P1-close blindspot retro finding-2 ("fabricated provenance") class structurally diff-detectable at write time.
7. **Cross-language byte-identical parity via shared fixture file + JSON SSOT + dual predicate bindings** (extended through P2 in DEC-215/216). Reusable in: any P3+ rule that must surface identically in Python advisor and TS frontend dashboard.

## 下一步 / 风险 (next / risks)

- **P3 (CHT end-to-end)** is the next Blueprint v4 phase per `blueprint_v4_2026-05-27.md` §4. **P3 charter has NOT been written.** Charter authoring is a user-decision per `~/Desktop/cfd-audit-merge/CLAUDE.md` scope rule (governance-rule-impacting / new compute type / ≥3 shared code paths). Considerations doc landed at `.planning/p3_cht_kickoff_considerations.md` to inform the main session's charter draft — **it is NOT a charter**.
- **STATE.md ANCHOR-24** advances `last_updated` from `2026-05-24T20:30 local` (ANCHOR-23, M3.x workbench arc) to `2026-05-30T<local>` covering the DEC-V61-207..216 Blueprint v4 P1+P2 arc (10 DECs). Per Counter Interpretation B (W3 Kogami P2-2), STATE.md `last_updated` is the canonical SSOT for "current state of project".
- **No P2 outstanding code risk.** All 6 sub-DECs Accepted, Notion-synced, Codex APPROVE'd within cap=3, cross-language parity green, no post-R3 live-run defects, no smoke / dogfood failures attributed. P2 is structurally closed.
- **Counter delta** across DEC-V61-207..216 (10 DECs):
  - `autonomous_governance: true` → V61-209, V61-210 (counter +2)
  - `autonomous_governance: false` → V61-215, V61-216 (N/A · listed for completeness)
  - V61-207, V61-208, V61-211, V61-212, V61-213, V61-214 — frontmatter not surveyed in this retro (deferred to next counter-audit pass; pure telemetry per V133, no STOP threshold).
- **P3 readiness blockers**: NONE on the engine side. The blocker is purely a user decision — invoke Kogami opt-in for the charter (per V133 "charter / governance-rule-change DECs where independent second opinion is desired") or run Codex APPROVE-only.

## Local artifacts

- This retro: `.planning/retrospectives/2026-05-30_p2_phase_close.md`
- P2 sub-DECs: `.planning/decisions/2026-05-28_v61_211_solver_block_extractor.md` · `2026-05-28_v61_212_shm_dict_extractor.md` · `2026-05-28_v61_213_thermo_dict_extractor.md` · `2026-05-28_v61_214_step_extractor.md` · `2026-05-29_v61_215_slice_extension_w206.md` · `2026-05-30_v61_216_w21_substantive_distillation.md`
- Sibling P2 retros (referenced): `2026-05-28_p1_close_p2_blindspot_findings.md` · `2026-05-28_dec212_codex_round3_overflow.md` · `2026-05-29_cadence_codex_r1_r9_fast_divergence.md`
- P3 charter considerations (NOT a charter): `.planning/p3_cht_kickoff_considerations.md`
- STATE.md ANCHOR-24 advance: `.planning/STATE.md` frontmatter `last_updated` line
- HEAD commit lineage: P2 sub-DEC chain ending at `01752c9` (DEC-V61-216 W2.1 land)

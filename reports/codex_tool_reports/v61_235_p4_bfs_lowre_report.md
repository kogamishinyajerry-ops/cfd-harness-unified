# Codex Tool Report — DEC-V61-235 · P4 V71.B wall-RESOLVED low-Re kOmegaSST BFS anchor

- **Relay backend**: 86gamestore (`~/.codex-relay`), model `gpt-5.4`, reasoning `xhigh` (governance baseline, RETRO-V61-001).
- **Command**: `codex review --commit <SHA>` (each round reviewed the single squashed V71.B commit).
- **Round cap**: 3 (R0 + 2 fix iterations). **CLOSED at R2 with APPROVE · 0 P1 at close.**
- **Raw logs**: `_r0_raw.txt` / `_r1_raw.txt` / `_r2_raw.txt` are **local-only** (gitignored via `reports/codex_tool_reports/*.txt`). This tracked `.md` is the canonical, self-contained trail.
- **Adversarial pre-pass**: `test-red-team` (same-family, NOT a governance substitute) — APPROVE; 1 P1 + 2 P2 closed inline before R0 (matrix "DONE"→"LANDED·pending", E21 behavioral firing test, fidelity-test docstring).

## What this slice does

V&V-anchor slice (analogous to the wedge's DEC-V61-233): anchors `backward_facing_step_lowre`
at Re_H=5000 with k-omega-SST **integrated to the wall** (y+<1, wall-RESOLVED) — the low-Re
turbulence-MODELING regime, distinguished from the high-Re Spalding-wall-function sibling
purely by the resolved near-wall mesh. SAME incompressible-RANS compute type →
**runnable-coverage STAYS 3** (turbulence-TREATMENT breadth, NOT a new compute type).
Landed: shared floor-mask SSOT, Execution-plane extractor (wall-shear reattachment +
floor-y+), Control-plane gate (comparator + 3 hard gates), gold, frozen LIVE probe, the
`low_re_komegasst_trigger` advisor, offline gate/gold tests. Live `execute()`/TaskRunner
wiring + the selectable whitelist entry are DEFERRED to V71B-FOLLOWUP-1.

## Round-by-round

### R0 (commit 58320fe) — CHANGES_REQUIRED · 1 P1 + 2 P2 (all production-path reachability) → ADDRESSED

Codex headline: *"The newly added low-Re BFS verification path is broken for real executions
because it consumes artifacts that the executor deletes before TaskRunner sees them. In
addition, the new low-Re gate and advisor are not reachable on important production paths."*

- **[P1] `task_runner.py:1018-1026`** — `_verify_bfs_lowre` ran the gate against
  `exec_result.raw_output_path`, which for a real solve is the executor's temp dir
  (rmtree'd in `finally`, and never holding `proof/floor_faces.csv` / `VTK/allPatches`) →
  `FileNotFoundError` on every live run; only the frozen fixture passed.
- **[P2] `task_runner.py:575-576`** — the branch keyed on `boundary_conditions['wall_treatment']`,
  false on Notion-driven specs (`NotionClient._parse_task` sets `boundary_conditions={}`).
- **[P2] `advisor_stack.py:967-978`** — no production caller populates `low_re_komegasst_inputs`;
  the advisor is dead outside tests.

**Fix (R1):** removed the premature `_verify_bfs_lowre` method + the geometry-gated 4c
branch. Per the wedge precedent, the verification branch belongs in the WIRING slice
(DEC-V61-234), NOT the V&V-anchor slice (DEC-V61-233): it works there only because
`_execute_supersonic_wedge` produces a PERSISTENT `raw_output_path`. The live wiring +
advisor caller-wiring were disclosed and deferred to `V71B-FOLLOWUP-1`.

### R1 (commit c638b08) — CHANGES_REQUIRED · 1 P1 + 2 P2 (R0 findings resolved) → ADDRESSED

- **[P1] `whitelist.yaml:95-97`** — whitelisting `backward_facing_step_lowre` made it
  selectable via `KnowledgeDB.list_whitelist_cases()` / `run_batch()`, but with the R0
  branch removed there was NO verification path: `load_gold_standard()` → None →
  "No gold standard found" (exposed-but-unverifiable — the flip side of R0 P1).
- **[P2] `bfs_lowre_extractor.py:236-239`** — `sorted(vtks)[-1]` is LEXICAL:
  `allPatches_900.vtk` > `allPatches_3000.vtk` ('9'>'3') → could measure an unconverged
  early field.
- **[P2] advisor `:165-169`** — fired on `wall_treatment=='resolved'` even when measured
  y+ proved unresolved, contradicting its own documented y+-priority contract.

**Fix (R2):** un-whitelisted the case (the selectable entry lands WITH the wiring, per the
wedge precedent — `whitelist.yaml` keeps only a deferral comment); latest VTK by NUMERIC
timestep (`max(vtks, key=_vtk_timestep)`) + a monkeypatched regression guard; measured
`first_cell_yplus` made AUTHORITATIVE over `wall_treatment` + 2 new advisor tests.

### R2 (commit 668a51d) — APPROVE

Codex headline: *"I did not find a discrete, actionable regression introduced by commit
668a51d. The new low-Re BFS gate and advisor are intentionally staged behind deferred live
wiring, and the code added here appears internally consistent without breaking existing
execution paths."*

(R2's first attempt died mid-investigation with a relay error — exit 144, no verdict
produced; re-run on the identical commit returned the APPROVE above. A no-verdict relay
failure does not consume a cap=3 round.)

## Disposition

- 0 P1 at chain close. All R0/R1 findings ADDRESSED in code (not deferred-with-P1).
- Deferred live wiring (gate TaskRunner branch + adapter runner + selectable whitelist entry
  + advisor live-caller) is tracked in `.planning/followups/v71b_bfs_lowre_live_wiring_deferred.md`
  — a disclosed follow-up, not an open finding.
- No P2/P3 carried to the retro queue.

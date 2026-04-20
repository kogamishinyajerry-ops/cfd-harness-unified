# Q-2: R-A-relabel — `fully_developed_pipe` → `duct_flow` whitelist rename

**Filed**: 2026-04-20T23:05 by claude-opus47-app (Sole Primary Driver under v6.1)
**Status**: **OPEN** — awaiting Kogami gate decision
**Upstream DEC**: DEC-V61-010 (C3 result-harvest completed) · DEC-V61-006 (B-class gold remediation closed Q-1)
**Related**: `reports/ex1_first_slice/diagnostic_memo.md` §R-A-relabel · `reports/ex1_005_whitelist_coverage_and_mini_review/methodology_mini_review.md` §R-A-relabel
**Blocking class**: Hard floor #3 — `knowledge/whitelist.yaml` rename + new `knowledge/gold_standards/duct_flow.yaml`

---

## Problem statement

Whitelist entry `fully_developed_pipe` declares `geometry_type: SIMPLE_GRID`, but the adapter's `SIMPLE_GRID` geometry for steady internal channel flow is a **rectangular duct**, not a circular pipe. The gold reference is the Blasius/Moody pipe friction factor `f = 0.0791/Re^0.25`, which is valid only for circular pipe cross-sections.

Consequence:

- Solver runs a rectangular duct flow (adapter generator behavior).
- Comparator evaluates output against a circular-pipe Darcy correlation.
- The two are categorically mismatched; any PASS verdict is physically coincidental.

This is **why Case 5 (Fully Developed Pipe Flow) sits at `PASS_WITH_DEVIATIONS` in the dashboard matrix** — not because solver physics are wrong, but because the whitelist labels a duct as a pipe.

## Why this is a gate

Under DEC-V61-003 §8:
- `knowledge/whitelist.yaml` metadata fields (geometry_type / flow_type / turbulence_model / solver / parameters) can be autonomously edited.
- `knowledge/whitelist.yaml` `reference_values` are gate-protected.
- **Renaming a whitelist entry** is a structural change that crosses both categories simultaneously: it changes `id` (metadata-adjacent, but also a cross-cutting key), gold-standard file location (`knowledge/gold_standards/fully_developed_turbulent_pipe_flow.yaml` → `knowledge/gold_standards/duct_flow.yaml`), and `reference_values` (new Darcy correlation for duct). Renames are not on the autonomous allowlist.

Additionally, the rename ripples through consumer code:
- `error_attributor` has case-name-routing logic.
- `foam_agent_adapter` may have name-based case detection branches.
- Dashboard UI ranks/filters by case id.

Gate decision is required to avoid an unintended cross-module refactor.

## Two decision paths

### Path A — Rename to `duct_flow` (intrinsic honesty path)

1. Rename whitelist `id: fully_developed_pipe` → `id: duct_flow`.
2. Rename `knowledge/gold_standards/fully_developed_turbulent_pipe_flow.yaml` → `knowledge/gold_standards/duct_flow.yaml` (or create new, archive old).
3. Update `reference_values`: replace Blasius circular-pipe `f = 0.0791/Re^0.25` with the Jones-duct correlation for rectangular duct at aspect ratio 1 (square duct):
   - At Re=50000: `f ≈ 0.0212` (Jones 1976 rectangular duct correlation).
   - Tolerance: 10% (matches existing).
4. Update consumer code routing (grep for `fully_developed_pipe`, `fully_developed_turbulent_pipe_flow`, adjust to `duct_flow` or canonical new name).
5. Dashboard UI picks up new name automatically via whitelist pull.

**Pro**: Honest physics labeling. Passes become meaningful.
**Con**: Multi-file refactor. Must update consumer code across `src/error_attributor.py`, possibly `src/foam_agent_adapter.py`, tests, and any references in `docs/`.

### Path B — Change geometry_type in generator (engineering path)

1. Keep whitelist `id: fully_developed_pipe`.
2. Modify `_generate_steady_internal_channel` (or a new `_generate_steady_pipe_flow`) to emit an actual **circular pipe** geometry (axisymmetric or full-3D cylinder mesh) instead of a rectangular duct.
3. Leave gold reference (Blasius pipe) unchanged — it'd now be correct.

**Pro**: Preserves case ID history. Comparator + gold unchanged.
**Con**: Larger engineering change. Axisymmetric/cylindrical blockMeshDict is more complex than the current SIMPLE_GRID rectangular mesh. Adapter's other consumers of SIMPLE_GRID (Plane Channel DNS, Turbulent Flat Plate) must be untouched — possible branching required.

### Path C — Relax tolerance + add "regime mismatch" flag (temporizing path)

1. Keep current labeling.
2. Widen tolerance to cover the ~30% Moody-vs-Jones-duct systematic delta.
3. Add a `physics_contract.regime_mismatch: "duct_vs_pipe"` annotation flag in the gold file so reviewers see the caveat.

**Pro**: Smallest change, no consumer code touches, keeps the PASS coming.
**Con**: Dishonest. A wider tolerance to mask a physics-labeling error is exactly the pattern DEC-V61-001 (v6.1 takeover) said we'd stop doing.

---

## Audit recommendation

**Path A**. Same spirit as the B-class gold remediation (DEC-V61-006) — honest physics labeling beats preserving ID history. The multi-file refactor is real but bounded (~5 files, all under autonomous turf post-rename, so self-reviewable once the gate is approved). Path B's cylindrical mesh generator is a more ambitious change that's not justified by a whitelist labeling fix. Path C is rejected on honesty grounds.

## Requested gate decision

Kogami picks one:

| Option | Action |
|---|---|
| **A** | Rename to `duct_flow`, new Jones-correlation gold, refactor consumer code |
| **B** | Generator-side rewrite to actual circular pipe (larger engineering change) |
| **C** | Relax tolerance + add regime-mismatch annotation (temporizing; rejected by driver) |
| **D** | Hold — investigate further (audit miscategorized something; keep Q-2 open) |

---

## If Path A approved

1. Branch `feat/q2-r-a-relabel-duct-flow`.
2. Edit `knowledge/whitelist.yaml`: rename entry id + update reference_values + update description.
3. Create `knowledge/gold_standards/duct_flow.yaml` with Jones-rectangular-duct f correlation; archive old `fully_developed_turbulent_pipe_flow.yaml`.
4. Grep + update: `src/error_attributor.py`, `src/foam_agent_adapter.py`, `tests/**`, `docs/**` for case-name references.
5. Land as PR #11 + DEC-V61-011 + Notion mirror.
6. Close Q-2 in `external_gate_queue.md`.

Net effect: Phase 5 Audit Package Builder unblocked.

## Phase 5 interaction

Q-2 is the **last remaining blocker for Phase 5** (Audit Package Builder). Q-1 closed via DEC-V61-006 Path P-2. Once Q-2 closes (any path), Phase 5 critical path opens. The Phase 5 kickoff plan has been written separately at `.planning/phase5_audit_package_builder_kickoff.md` (same session).

## Reversibility

Path A is reversible via one `git revert -m 1 <merge-sha>`. The gold file rename is recoverable from git history. Consumer code touches are small and trackable.

## Ping

**Action required from Kogami**: reply with A/B/C/D decision (or alternative) at any surface (Notion comment, GitHub PR comment, direct message). Once received I'll land PR #11.

**Blocking until**: Kogami reply received OR explicit waiver.

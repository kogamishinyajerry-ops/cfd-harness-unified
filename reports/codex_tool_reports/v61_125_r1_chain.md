# DEC-V61-125 · lc_override arg · Codex pre-merge chain

**Backend**: CRS `gpt-5.4` high (default per V61-119 §L2 protocol)
**Trigger**: RETRO-V61-001 multi-file backend + AI-driven case-mutation triggers
**Scope**: 4 files · ~440 LOC across `RegenerateMeshArgs` extension (lc_override field + 3-way mutual exclusion validator), `mesh_imported_case` plumbing, `run_gmsh_on_imported_case` parent-layer validation guard, ~14 new tests
**Self-estimated pass rate**: 75% (predicted 1-2 rounds — explicit §L1 calibration test mirroring V124's surface)
**Actual**: **3 rounds** — matching V124 exactly. **§L1 distinction doubly validated**: two consecutive no-contract-crossing DECs both converge in 3 rounds.

---

## Round-by-round summary

| Round | Commit | Findings | Severity | Verdict | Backend |
|---|---|---|---|---|---|
| R1 | fb38ee3 | 1 | P3 | CHANGES_REQUIRED | CRS gpt-5.4 high |
| R2 | 5e973f3 | 1 | P2 | CHANGES_REQUIRED | CRS gpt-5.4 high |
| R3 | 8953484 | 0 | — | **APPROVE clean** | CRS gpt-5.4 high |

---

## Round 1 · CHANGES_REQUIRED · 1 P3

- **P3 · non-positive lc_override silently fell through**: V125 added Pydantic `gt=0` validation at the AI-coach trust boundary, but a direct backend caller of `mesh_imported_case` → `run_gmsh_on_imported_case` that bypasses the schema would silently fall through. Inside `_gmsh_inline` the `if lc > 0` guard skipped the gmsh option setting for non-positive lc, gmsh fell back to defaults, mesh produced default-sized output that misrepresented the caller's intent. **Fix**: parent-layer guard at `run_gmsh_on_imported_case` entry — non-positive `characteristic_length_override` raises `ValueError` with a clear message before the subprocess spawn. Tests: ValueError on 0.0 (boundary), ValueError on -0.001 (negative), None passes through (negative control).

## Round 2 · CHANGES_REQUIRED · 1 P2

- **P2 · R1 fix overshot · ignored documented precedence**: R1's guard rejected non-positive `characteristic_length_override` unconditionally, but the documented precedence (target_cell_count > characteristic_length_override > mesh_mode) means the override is ignored anyway when target_cell_count is set. A direct caller with `target_cell_count=N` AND a stale sentinel `characteristic_length_override=0.0` (carried over from an older call shape) would have been previously tolerated, now hard-fails — a behavior regression for theoretical future callers. **Fix**: gate the validation on `target_cell_count is None`. The override only needs to be valid when it's actually going to be consumed. Test: `target_cell_count=100_000` + `characteristic_length_override=0.0` does NOT raise the must-be-positive ValueError.

## Round 3 · APPROVE clean · 0 findings

**Backend**: CRS `gpt-5.4` high. Verbatim verdict (Codex):

> "The lc_override guard now only runs when that value can actually affect sizing, which matches the documented precedence, and the rest of the meshing path is unchanged. I didn't find a regression introduced by this commit."

V125 closes at 3 rounds with R3 APPROVE clean at commit `8953484`.

---

## Methodology lessons

### L1 · §L1 calibration baseline DOUBLY validated

V123 chain §L1 hypothesized: "tool registry append, no contract crossing" ≈ 70%/1-2 rounds vs "cross pre-existing safety contract" ≈ 20%/7-10 rounds. V124 was the first calibration test → 3 rounds. V125 was the second → also 3 rounds. **Two independent samples now show no-contract-crossing tool-args extensions converge in ~3 rounds.** The distinction is empirically real and reproducible.

The 3-round pattern is also recognizable: R1 catches a defensive-hardening gap (visible-bug or near-bug), R2 refines the R1 fix's scope, R3 APPROVEs. This is the **signature of a well-scoped no-contract-crossing DEC**: bounded findings, each successive round strictly narrower than the prior, no Round-N introducing new surface.

### L2 · "Validation must respect documented precedence"

V125 R2 surfaced that R1's "validate everything" instinct was wrong when the validated field has documented precedence ordering. Defensive validation should fire only when the validated input *can affect output*. This is a generally-applicable discipline: when adding a new validation guard, check whether other parameters could supersede the validated one; if so, gate the validation on the supersession-condition being absent.

This is a NEW methodology lesson not covered in V122/V123/V124 chain reports. **RETRO candidate intake**: extend the V61-088 surface-scan checklist to include "are validation guards correctly gated by precedence rules" as an audit axis.

### L3 · Schema-layer + service-layer validation are complementary, not redundant

V125's split coverage is a worked example of healthy defense-in-depth:
- **Schema layer** (`RegenerateMeshArgs.lc_override` Pydantic `gt=0`): catches AI-coach-tool-route bad inputs at HTTP 400 with structured detail. The frontend ProposalCard can display "lc_override must be positive".
- **Service layer** (`run_gmsh_on_imported_case` ValueError guard): catches direct-backend-caller bad inputs at the parent process before subprocess spawn. Programming-error class — surfaces as 500 with traceback for the operator.

Both fire on the same input class but cover different caller paths. Removing either would leave a gap. This is the right shape for "trust-boundary plus defensive-backstop" validation.

---

## Counter / governance

- counter: 83 (V124) → **84** (V125 Accepted at R3 APPROVE clean)
- Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter 84 (counter ≥ 20 trigger continues to be deferred per ongoing user mandate "按你的顺序和建议，继续推进"), not governance-rule change → Kogami **NOT** triggered
- Notion sync: pending (V118-V125 all pending sync; MCP server still disconnected since V119)
- Self-pass-rate calibration: predicted 75% / 1-2 rounds; actual 3 rounds — calibrated band for "tool registry append, no contract crossing". Two independent samples (V124 + V125) at 3 rounds; treat as the canonical baseline going forward.

## Anchor

R3 APPROVE-clean commit: `8953484`

---
decision_id: DEC-V61-005
timestamp: 2026-04-20T20:40 local
scope: Path B · A-class metadata corrections on knowledge/whitelist.yaml — Circular Cylinder Wake Re=100 + Rayleigh-Bénard Ra=1e6 turbulence_model switch from "k-omega SST" to "laminar". Metadata-only edit. reference_values untouched.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
reversibility: fully-reversible-by-pr-revert
  (Two inline metadata field edits + explanatory comments in
  knowledge/whitelist.yaml. No reference_values change. No schema
  change. No test surface change. One `git revert -m 1 <merge-sha>`
  restores pre-edit state.)
notion_sync_status: PENDING
github_pr_url: null
github_merge_sha: null
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 92%
  (turbulence_model is explicitly listed in DEC-V61-003 §8 as an
  autonomous-editable metadata field. Physical rationale is
  well-established in primary literature. Main residual Gate-risk:
  Kogami may prefer to bundle A-class with B-class gold remediation
  in one unified external-gate package for traceability — but that
  would delay ~2 straightforward dashboard PASS flips unnecessarily.
  Metadata is orthogonal to gold-value correctness, so bundling is
  not a correctness requirement.)
supersedes: null
superseded_by: null
upstream: DEC-V61-004
---

# DEC-V61-005: A-class metadata corrections — Cylinder Re=100 + Rayleigh-Bénard Ra=1e6 → laminar

## Decision summary

Apply two precise `turbulence_model` metadata corrections in `knowledge/whitelist.yaml`:

| Case | Before | After | Rationale |
|---|---|---|---|
| `circular_cylinder_wake` (Re=100) | `k-omega SST` | `laminar` | Re=100 is in the 2D laminar Karman vortex shedding regime (Williamson 1996 — 3D transition ~Re=190). k-ω SST over-dissipates the wake and under-predicts St. |
| `rayleigh_benard_convection` (Ra=1e6) | `k-omega SST` | `laminar` | Ra=1e6 is steady-convective; fully turbulent onset ~Ra=1.5e8 for moderate Pr. Chaivat Nu=0.229·Ra^0.269 correlation assumes laminar steady regime. k-ω SST over-dissipates at this Ra and under-predicts Nu. |

Both entries gain an inline explanatory comment block above the `turbulence_model:` line so future readers see the physical reasoning without having to dig into this DEC.

## 禁区 compliance

| Area | Touched? |
|---|---|
| #1 `src/` and `tests/` | NOT TOUCHED |
| #2 `knowledge/gold_standards/**` | NOT TOUCHED |
| #3 `knowledge/whitelist.yaml` `reference_values` | NOT TOUCHED — only `turbulence_model` metadata field |
| #4 Notion DB destruction | NOT TOUCHED (one new page creation only) |

Per DEC-V61-003 §8: **"只有 metadata 字段 (geometry_type / flow_type / turbulence_model / solver / parameters) 可自主改"**. `turbulence_model` is explicitly on the autonomous-editable allowlist.

## Regression

Same 7-file pytest matrix as DEC-V61-004: 158/158 green. Whitelist metadata changes do not affect test fixtures or code paths; full suite passes unchanged.

## Expected dashboard impact

- **Circular Cylinder Wake** currently a dashboard PASS with HAZARD-prone characteristics (solver over-damps Karman shedding under k-ω SST). Switching to laminar pimpleFoam should tighten St convergence to the 0.165 gold within the 5% tolerance.
- **Rayleigh-Bénard** currently NO-RUN or near-miss; laminar buoyantFoam at Ra=1e6 is the canonical configuration for the Chaivat correlation. Should move toward PASS on Nu=10.5 ± 15%.

Neither case requires C1/C2/C3 pipeline fixes to benefit from this change — they are independent of the comparator alias layer and parameter-plumbing verifier. Dashboard will show this improvement on the next full validation run.

## Reversibility

One `git revert -m 1 <merge-sha>` restores the prior `k-omega SST` metadata on both entries. The explanatory comments revert with the field change.

## Rejected alternatives

1. **Bundle A-class with B-class gold remediation in one external-gate package** — REJECTED. A-class is pure metadata and explicitly within DEC-V61-003 autonomous turf. Bundling would delay two straightforward dashboard flips behind an external-gate waiting period that is not required by the correctness model.
2. **Also switch turbulent_flat_plate Re_x=25000 to laminar** (since Re_x=25000 is technically laminar too) — REJECTED. That case's gold uses Spalding's composite law which presumes some turbulence activity; switching to laminar without also correcting the gold-value (which is B-class, external-gate) would create an internally inconsistent record. Left to B-class package.
3. **Edit whitelist.yaml with no inline comment** — REJECTED. Comments cost nothing and make the decision self-documenting at the point of use, which matters more than decision-doc indirection for a metadata correction this small.
4. **Change `solver` alongside `turbulence_model`** — REJECTED. The solver choice (`pimpleFoam` for transient cylinder wake, `buoyantFoam` for Rayleigh-Bénard) is correct for the physics; laminar vs SST is the only variable needing adjustment.

## Next steps (queued)

1. Commit + push + PR #5.
2. On merge: mirror this DEC to Notion Decisions DB (data_source 54bb6521-2e59-4af5-93bd-17d55c7c34e1).
3. Proceed to §5c: write `.planning/gates/Q-new_whitelist_remediation.md` for B-class gold-value remediation and ping Kogami (mandatory stop for external gate).
4. Defer C3 (sampleDict auto-gen) to a dedicated design session — per-case sampling strategy (LDC centerline points / IJ Nu wall-heatflux / NACA Cp surface patch) needs thoughtful function-object selection before implementation.

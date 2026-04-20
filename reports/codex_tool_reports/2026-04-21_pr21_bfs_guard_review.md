# Post-merge Codex Review — PR #21 BFS Upstream Guard

Baseline: `ffa0bb1`  
Merge SHA: `67b129e`  
Scope: `src/foam_agent_adapter.py`, `tests/test_foam_agent_adapter.py`  
Review frame: Codex round 7; round 2 under v6.1 governance (`RETRO-V61-001`)  
Change under review: `P6-TD-001`

## Verdict

`APPROVED_WITH_NOTES`

## Findings

### 1. Low — automated regression coverage only hits one of the two changed BFS extractor paths

The new regression test at `tests/test_foam_agent_adapter.py:595-634` exercises the `postProcessing/sets` / `_parse_solver_log` path only. The same guard was also added to the writeObjects field path in `src/foam_agent_adapter.py:7397-7421` via `_parse_writeobjects_fields` -> `_extract_bfs_reattachment`, but there is no unit test for that route in this patch.

This is not merge-blocking because the mirrored logic is straightforward and a one-off manual reproduction against `_parse_writeobjects_fields` in the current tree behaved correctly: it emitted `reattachment_detection_upstream_artifact=True`, stored the negative raw `x` in `reattachment_detection_rejected_x`, and did not publish `reattachment_length`. It is still a real coverage gap for a change that intentionally duplicated logic in two places.

### 2. Low — the new guard is correct, but one explanatory comment is stale/internally inconsistent

`_extract_bfs_reattachment` documents the BFS mesh as `x ∈ [-1, 8]` at `src/foam_agent_adapter.py:7408`, but the current case generator does not match that statement:

- `_render_bfs_block_mesh_dict` builds the simplified rectangular channel on `x ∈ [-10H, 30H]` (`src/foam_agent_adapter.py:6374-6375`).
- `sampleDict` probes `wallProfile` only on `x ∈ [-1, 12]` (`src/foam_agent_adapter.py:1599-1619`).

This does not invalidate the `x > 0` guard, because the codebase consistently treats `x = 0` as the nominal step location. It does mean the domain-bounds comment should not be treated as authoritative.

## Review questions

### 1. Is `x > 0` the correct boundary?

Yes.

The codebase consistently anchors the nominal BFS step at `x = 0`:

- `_generate_backward_facing_step` says “step at `x=0`” (`src/foam_agent_adapter.py:1020`).
- `sampleDict` probes the wall profile from `x = -1` to `x = 12` specifically to find reattachment downstream of that location (`src/foam_agent_adapter.py:1599-1619`).

Within that coordinate convention, a physically meaningful reattachment point must be downstream of the step, so `x > 0` is the correct acceptance region.

One nuance: the current mesh generator is a simplified rectangular channel, not a literal stepped geometry. So `x = 0` is a benchmark-coordinate convention more than an explicit geometric discontinuity in the mesh. Even with that simplification, the intended interpretation remains “reject upstream detections,” and `x > 0` encodes that correctly.

### 2. Producer-flag naming consistency vs `DEC-ADWM-005` / `DEC-ADWM-006`

The new names are understandable and scoped well enough:

- `reattachment_detection_upstream_artifact`
- `reattachment_detection_rejected_x`

They are slightly less consistent with the existing boolean producer flags:

- `cf_spalding_fallback_activated`
- `strouhal_canonical_band_shortcut_fired`

Those established booleans use an event/result suffix (`_activated`, `_fired`). The new boolean is a noun phrase instead of a past-tense event. I would treat that as a naming-style note, not a reason to reopen the merge. If this family grows, a boolean suffix such as `_detected` or `_rejected` would make the convention cleaner.

Related note: unlike the existing DEC flags, `src/error_attributor.py` does not currently special-case the new reattachment flag. So the flag is preserved in raw `key_quantities`, but it does not yet feed a dedicated audit-concern label.

### 3. Test coverage of the §5d Part-2 failure mode?

Partial, not complete.

Covered:

- The merged test reproduces the observed failure mode on the `postProcessing/sets` / raw-sample path and proves that a negative `x` no longer becomes `reattachment_length`.

Not covered by automated test in this patch:

- The mirrored writeObjects field path (`_parse_writeobjects_fields` -> `_extract_bfs_reattachment`).
- The exact boundary case `reattachment_x == 0`.

I manually reproduced the field-path case in the current tree and observed the expected rejection behavior, so the implementation appears sound. The absence of a formal unit test remains the main note on this review.

### 4. Boundary case reattachment exactly at `x = 0` (`>` vs `>=`)?

`>` is the correct choice.

At `x = 0`, the reported point is at the step lip itself, not downstream of it. Accepting `x == 0` as a valid BFS reattachment would effectively allow a zero-length recirculation bubble, which is not a meaningful interpretation for this benchmark and is exactly the kind of edge-case numerical noise this guard is meant to suppress.

So for this guard:

- `x > 0` = valid downstream reattachment
- `x <= 0` = reject and flag as artifact / physically implausible

### 5. Collateral to non-BFS shared code?

No harmful behavioral collateral found.

The code changes are isolated to the two BFS reattachment extraction branches:

- `src/foam_agent_adapter.py:6869-6894`
- `src/foam_agent_adapter.py:7397-7421`

They do not modify shared helpers used by LDC, NC cavity, flat-plate, cylinder, airfoil, or jet extraction.

The only cross-cutting note is observability, not behavior: the new producer flag is stored in `key_quantities`, but there is not yet a dedicated consumer analogous to the existing `error_attributor` handling for `cf_spalding_fallback_activated` and `strouhal_canonical_band_shortcut_fired`.

## Validation evidence

Automated:

- `pytest -q tests/test_foam_agent_adapter.py -k 'bfs_reattachment or parse_solver_log_extracts_bfs_reattachment'`
- Result: `2 passed`

Manual spot-check:

- Constructed a minimal writeObjects field case with `Cx=[-8.0, -5.0, -4.5, -4.0]`, `Cy=[0.5, ...]`, and `Ux=[-1.0, -0.5, 0.1, 1.0]`.
- Called `_parse_writeobjects_fields(...)` directly.
- Observed output:
  - `reattachment_detection_upstream_artifact == True`
  - `reattachment_detection_rejected_x == -4.583333333333333`
  - no `reattachment_length` key published

## Bottom line

The merged fix addresses the reported physical-impossibility defect correctly. The strict `x > 0` boundary is the right choice, including for the `x == 0` edge case. The two follow-up notes are:

1. add a symmetric automated test for the writeObjects field path
2. optionally standardize the boolean flag naming / audit surfacing if this producer-flag family continues to expand

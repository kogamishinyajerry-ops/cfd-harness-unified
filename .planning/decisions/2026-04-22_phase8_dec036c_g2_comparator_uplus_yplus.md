---
decision_id: DEC-V61-036c
timestamp: 2026-04-22T11:35 local
scope: |
  Phase 8 Sprint 1 — G2 comparator coverage + dict-profile driver fix.
  Closes the last known schema-level PASS-washing path surfaced by Codex
  round 1 on DEC-V61-036 (B2 finding): `ResultComparator._compare_vector`
  did not read `u_plus` key and `_resolve_profile_axis` did not support
  `y_plus` axis. plane_channel_flow gold is DNS {y_plus, u_plus} tuples
  (Kim 1987 / Moser 1999); every iteration of `_compare_vector` picked
  `None` for every reference scalar → zero deviations → fake PASS even
  when a simulation emits a wildly wrong u+ profile.

  Also: dict-profile sampling in both acceptance drivers
  (phase5_audit_run + p2_acceptance_run) now covers NACA sampleDict
  `{x_over_c, Cp}` shape and plane_channel `{y_plus, u_plus}` shape,
  per Codex round-2 nit on DEC-V61-036.

autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: pending (pre-merge required; self-pass-rate ≤ 0.70)
codex_rounds: 0
codex_verdict: pending
codex_tool_report_path: []
counter_status: |
  v6.1 autonomous_governance counter 25 → 26 after this DEC. Next retro at 30.
reversibility: |
  Fully reversible. `_compare_vector` ref-scalar lookup widened from
  hardcoded chain to a tuple iteration; `_resolve_profile_axis` adds 2
  y_plus candidates; drivers' dict-profile fallback iterates a scalar
  key tuple. Revert = 3 files restored. No fixture regeneration needed.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
github_merge_sha: pending
github_merge_method: pre-merge Codex verdict required
external_gate_self_estimated_pass_rate: 0.70
  (Surgical change to 3 files, 2 of which are the acceptance drivers
  already reviewed across DEC-036 rounds 1+2. Main risk: profile axis
  resolution now has y_plus candidates that MIGHT trigger spurious
  matches for a case that uses `y_plus` as a legacy column name without
  being a true u+ DNS case. Mitigation: axis candidates are tried in
  order; the new y_plus pair only matches when the reference dict
  explicitly has `y_plus` key.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-036 Codex round 1 B2: "ResultComparator._compare_vector
    does not read u_plus, and axis resolution does not support y_plus"
  - DEC-V61-036 Codex round 2 nit: "NACA sampleDict can emit list[dict
    {x_over_c, Cp}] ... only handles dicts with `value`"
---

# DEC-V61-036c: G2 — comparator u+/y+ + dict-profile fix

## Why now

Codex round 1 on DEC-V61-036 flagged that plane_channel_flow's PASS
verdict (before DEC-036 G1 flipped it) was not just schema-level
PASS-washing — it was ALSO comparator-semantic PASS-washing. Even
after G1 now hard-FAILs the fixture (`extraction_source ==
key_quantities_fallback` → MISSING_TARGET_QUANTITY), a future
regression that emits a numerically valid but physically wrong u+
profile would still silently PASS because `_compare_vector` never
extracts the u+ reference scalar from the gold dict.

Test demonstration (`test_g2_comparator_honestly_fails_plane_channel_u_plus_profile`):
a simulation emits `[0, 27.0, 67.5, 114.0]` (5× the Kim 1987 DNS gold)
against gold `[0, 5.4, 13.5, 22.8]`. Before G2 → zero deviations →
PASS. After G2 → 3 non-trivial deviations → FAIL.

## What lands (this DEC)

### 1. Comparator ref-scalar lookup (`src/result_comparator.py::_compare_vector`)

Before:
```python
ref_scalars = [
    r.get("u") if r.get("u") is not None
    else r.get("value") if r.get("value") is not None
    else r.get("Nu") if r.get("Nu") is not None
    else r.get("Cp") if r.get("Cp") is not None
    else r.get("Cf") if r.get("Cf") is not None
    else r.get("f")
    for r in reference_values
]
```

After: tuple-iteration over `("u", "u_plus", "value", "Nu", "Cp", "Cf", "f", "St")`.
Adds `u_plus` (plane_channel DNS) + `St` (cylinder Strouhal future).

### 2. Comparator axis resolution (`src/result_comparator.py::_resolve_profile_axis`)

Adds two candidate pairs at the top of the axis list:
- `(f"{quantity}_y_plus", "y_plus")` — adapter conventional
- `("y_plus", "y_plus")` — direct match if adapter emits `y_plus` key

### 3. Driver dict-profile sampling (both `phase5_audit_run.py`
and `p2_acceptance_run.py`)

Dict-profile shapes other than `{value: X}` are now sampled — tuple
of conventional scalar keys `("value", "Cp", "Cf", "u", "u_plus",
"Nu", "f")`. Closes Codex round-2 nit on DEC-036.

### 4. Tests (4 new in `test_g2_comparator_uplus_yplus.py`)

- `test_g2_comparator_honestly_fails_plane_channel_u_plus_profile`
- `test_g2_comparator_passes_when_u_plus_matches_gold`
- `test_g2_driver_accepts_dict_profile_with_Cp_key`
- `test_g2_driver_accepts_dict_profile_with_u_plus_key`

All 4 green. Full suite: 190 → 194.

## What is NOT in this DEC

- Full unit-canonicalization table (unit `"Xr/H"` vs `"dimensionless"`)
  — deferred to a future DEC when a case actually has a unit mismatch
  that matters (current 10 cases all have matching units after G1's
  strict lookup).
- Per-case A3 residual floor tie-in — deferred.

## Counter + Codex

25 → 26. Self-pass 0.70 — still pre-merge per RETRO-V61-001.

## Related

- DEC-V61-036 G1 (a9d0831 + b3ed913) — complementary; G1 gates
  extraction, G2 gates comparison semantics
- DEC-V61-036b G3/G4/G5 (1fedfd6 + c3afe93) — post-extraction physics gates
- DEC-V61-038 A1..A6 (eb51dcf + 9716dd4) — pre-extraction attestor

# V61-112 Phase 2 · Codex pre-merge chain (R1 → R2 → R3 APPROVE)

**DEC**: DEC-V61-112-Phase2 — pimpleFoam profile + per-solver `name_pad`
**Backend**: 86gs `gpt-5.4` (xhigh) · governance baseline per RETRO-V61-001
**Trigger**: multi-file backend (case_solve service surface) + new config schema profile + ≤70% self-pass-rate gate — RETRO-V61-001 mandatory pre-merge
**Self-estimated pass rate**: 50% (calibrated DOWN from Phase 1's 60% per Phase 1 closure recommendation: "config-schema-migration anchor should drop to ~50%"). Actual: 3 rounds (1 P2 + 1 P3) — calibration honest.

---

## R1 (commit fb3170a) — CHANGES_REQUIRED · 0 P1 + 1 P2

> "The migration is close, but the new pimpleFoam controlDict path does not preserve existing output for common float-valued inputs such as the default `end_time=5.0`. That backward-compatibility regression is enough to make the patch incorrect."

| # | Sev | Finding | File | Closure |
|---|-----|---------|------|---------|
| 1 | P2 | `_format_number` strips `.0` from caller-passed integer-valued floats; V61-107.5 inline used Python f-string preserving `.0`. Default-caller path `setup_bc_from_stl_patches(..., end_time=5.0, delta_t=1.0)` rendered as `endTime 5; deltaT 1; maxDeltaT 1;` instead of `endTime 5.0; deltaT 1.0; maxDeltaT 1.0;`. Phase 2 R0 golden test used `end_time=5` (int) so missed the float-typed-integer path. | `bc_setup_from_stl_patches.py:768-770` (test gap) + `solver_profiles/schema.py:323-324` (root cause) | `_format_number` rewritten to preserve `.0` for integer-valued floats via `f"{value:.1f}"`. YAML int-vs-float type distinction round-trips author intent. Cascading cleanup: `write_interval_decimal` flag (Phase 2 R0 workaround) removed as redundant. 4 new caller-float regression tests pin the contract: float `end_time=5.0` → `5.0`; int `end_time=5` → `5`; float `delta_t=1.0` → both `deltaT 1.0` and `maxDeltaT 1.0` preserved; full default-caller-signature byte-identity (end_time=5.0, delta_t=1.0). |

**R1 fix commit**: `88a3692`

---

## R2 (commit 88a3692) — CHANGES_REQUIRED · 0 P1 + 0 P2 + 1 P3

> "The patch fixes the reported integer-float regression for explicit caller overrides, but it does so by changing the formatter globally. That also changes the behavior of supported default-rendering paths for float-backed profile values, so the patch is not fully correct."

| # | Sev | Finding | File | Closure |
|---|-----|---------|------|---------|
| 1 | P3 | `_format_number` now preserves `.0` globally; ControlDictBlock dataclass `float = X.0` defaults render with spurious `.0` for any profile that omits keys. Real call sites (simpleFoam.yaml + pimpleFoam.yaml) explicitly set values, so byte-identity for tested paths unaffected — but synthesized future profiles or test scenarios using the no-args path get `0.0/200.0/1.0/50.0` instead of `0/200/1/50`. | `solver_profiles/schema.py:325-329` | Tightened ControlDictBlock dataclass defaults from float literals to int values: `start_time = 0`, `end_time_default = 200`, `delta_t_default = 1`, `write_interval = 50`. Type hints stay `float` so callers + YAML retain flexibility. New regression test `test_schema_default_dataclass_values_render_as_integers` synthesizes a profile omitting all 4 fields and pins integer rendering. |

**R2 fix commit**: `fdf7215`

---

## R3 (commit fdf7215) — APPROVE clean

> "The behavioral change is limited to the dataclass defaults used when a solver profile omits several controlDict fields, and that path is now covered by a regression test. I did not find a concrete breakage introduced by this commit in the current codebase."

---

## Substantive convergence audit

| Round | P1 | P2 | P3 | Total | Δ severity (vs prior) |
|-------|-----|-----|-----|-------|----------------------|
| R1 | 0 | 1 | 0 | 1 | (baseline) |
| R2 | 0 | 0 | 1 | 1 | -1 severity (P2 → P3) |
| R3 | 0 | 0 | 0 | 0 | -1 · APPROVE |

Monotone severity decrease across rounds. R1's P2 was a substantive byte-identity gap (caller-passed floats); R2's P3 was a knock-on edge case from R1's fix (dataclass defaults); R3 confirmed both substantive concerns closed.

Notable R1 P2 was caught despite Phase 2 author having internalized Phase 1's "byte-identity gates need golden constants" methodology lesson — the failure was a different gap: golden bytes captured BEFORE rewire used `int` test inputs, but the real call path uses `float` inputs. **Methodology lesson update for next RETRO**: byte-identity golden snapshots MUST exercise the same input TYPES that real call sites use, not just the same VALUES. Specifically: when caller signatures are typed `float`, snapshot tests should pass float-typed integer values (`5.0` not `5`) to flush out type-vs-value formatter bugs.

---

## Self-pass-rate calibration

- **Predicted**: 50% (Phase 1 closure recommendation anchor for "config-schema-migration with golden-byte gate + schema validation")
- **Actual**: 3 rounds (R1 1 P2 substantive · R2 1 P3 edge case · R3 APPROVE)
- **Calibration verdict**: **honest** — predicted "2-3 rounds with possible P2 findings on the new SolverEntry shape validation". Got 3 rounds with the P2 finding on the formatter (different surface than predicted but same severity tier). Schema extension passed clean — Codex didn't flag SolverEntry validation, which means R0's parametrized name_pad tests + missing-body / unknown-keys / non-int-pad / negative-pad / zero-pad coverage was sufficient.

For RETRO-V61-001 trend: V61-112 Phase 1 needed 3 rounds; Phase 2 needed 3 rounds. Pattern is stable; ~50% baseline holds for "config-schema-migration with golden-byte gate". Phase 3 (LDC icoFoam migration) and Phase 4 (channel pimpleFoam migration) should anchor at the same baseline.

---

## Methodology lessons captured for next RETRO

### Lesson 1 (Phase 2 R1 P2): Golden snapshots must exercise real caller input types

**Pattern**: byte-identity acceptance gates need golden constants captured BEFORE rewire (Phase 1 R1 P2-2 lesson). But the snapshot tests must also exercise the same INPUT TYPES that real call sites use — not just the same VALUES.

**The trap**: Phase 2 R0 captured golden bytes for `end_time=5` (int) but the real caller signature is `def _build_pimplefoam_control_dict(end_time: float, delta_t: float)` and the call site passes `5.0` (float). Python's `f"{5}"` and `f"{5.0}"` differ in output (`"5"` vs `"5.0"`). The schema's `_format_number` for integer-valued floats happened to strip `.0`, breaking byte-identity for the float input that was never tested.

**The fix pattern**: when caller signatures declare `float` (or any union type), snapshot tests must pass values that exercise the type explicitly — `float(5.0)` not `int(5)`. Add at minimum:
- One test with int-typed integer values (`5`, `1`)
- One test with float-typed integer values (`5.0`, `1.0`)
- One test with float-typed non-integer values (`5.5`, `0.001`)

### Lesson 2 (Phase 2 R2 P3): Dataclass defaults are part of the contract

**Pattern**: schema dataclasses with `field: float = X.0` defaults appear identical to YAML-supplied float values at render time. Tightening defaults to int values where the rendered output should be int prevents drift in synthesized / no-args call paths.

**The fix pattern**: choose dataclass default LITERAL TYPE (int vs float) based on rendered output convention, not Python's natural float-default style. `start_time: float = 0` (int 0, type hint flexible) is preferred over `start_time: float = 0.0` (float 0.0) when output should be `"0"` not `"0.0"`.

---

## Cross-referenced artifacts

- DEC-V61-112-Phase2: `.planning/decisions/2026-05-03_v61_112_solver_profile_yaml_phase2.md`
- Phase 1 chain report: `reports/codex_tool_reports/v61_112_phase1_r1_r2_r3_chain.md`
- Implementation commits: `fb3170a` (Phase 2 initial) → `88a3692` (R1 fix) → `fdf7215` (R2 fix)
- Tests: 50 V61-112 (49 Phase 1+2 + 1 R2 dataclass-defaults regression) + 1131 CI-equivalent regression-clean
- Surface scan: `bc_setup_from_stl_patches.py:755-845 (V61-107.5 inline pimpleFoam) + bc_setup.py:822-906 (channel pimpleFoam — Phase 4 follow-up) + solver_profiles/schema.py:184-185 (Phase 1 hardcoded 2-space pad — extending)` · disposition `refactor existing`
- Phases 3-4 (deferred): icoFoam LDC migration · channel pimpleFoam migration → separate DECs

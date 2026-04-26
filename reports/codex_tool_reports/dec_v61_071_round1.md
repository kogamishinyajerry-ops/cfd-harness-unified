# DEC-V61-071 · Codex Review · Round 1

- Review date: 2026-04-26 11:47:27 CST
- Commit: `3296ae6` (`feat(task_runner): wire load_tolerance_policy into _build_trust_gate_report`)
- DEC: `.planning/decisions/2026-04-26_v61_071_load_tolerance_policy_wiring.md`
- Verdict: `CHANGES_REQUIRED`

## Findings

| Severity | File:Line | Finding | Recommended fix |
| --- | --- | --- | --- |
| MED | `src/task_runner.py:89-90`; `src/knowledge_db.py:66-67`; `src/notion_client.py:130-131`; `tests/test_task_runner_trust_gate.py:348-441` | `_build_trust_gate_report()` passes `task_name` straight into `load_tolerance_policy()`, but that loader is a case-id / filename-slug lookup (`.planning/case_profiles/<case_id>.yaml`). In this repo, two primary production feeders build `TaskSpec.name` from display titles, not slugs: whitelist tasks use `case["name"]` and Notion tasks use the page title. Reproduced locally: `load_tolerance_policy("lid_driven_cavity")` returns 4 observables, while `load_tolerance_policy("Lid-Driven Cavity")` returns 0; `_build_trust_gate_report(... task_name="Lid-Driven Cavity" ...)` likewise stamps `tolerance_policy_observables=[]` even though `lid_driven_cavity.yaml` exists. That means the new wiring silently misses real CaseProfiles on a common production path, which defeats the commit's stated goal of exercising policy dispatch in production. The 3 new tests only cover canonical ids, so they do not catch this. | Pass a canonical case id into `_build_trust_gate_report()`, or resolve one before calling `load_tolerance_policy()` via the existing whitelist/chain normalization path already used elsewhere in `TaskRunner`. Add a regression test that uses a real display-title task name and proves the matching slugged CaseProfile populates provenance. |
| LOW | `src/task_runner.py:89-98`; `src/task_runner.py:135-149` | The new loader call is eager: it runs before the `comparison is not None` branch and before the final `if not reports: return None`. On attestation-only and no-input paths, the helper now does filesystem I/O even though there is no comparison report to receive `tolerance_policy_observables`. On malformed YAML it can also emit a warning on paths that never produce comparison provenance, which is avoidable noise. | Lazy-load the policy only inside the comparison branch, or return early when `comparison is None`. Add regression coverage for `comparison=None, attestation="ATTEST_FAIL"` and `comparison=None, attestation=None` so the helper proves it skips the loader on those paths. |

## Specific Checks

- `load_tolerance_policy` placement relative to the `None` guards:
  No. It should be skipped when `comparison is None`, and definitely when both inputs are `None`. Today there is nowhere to surface the loaded policy except the comparison provenance, so eager loading only adds avoidable I/O and warning noise.

- Docstring accuracy:
  Mostly accurate about intent and unchanged verdict semantics. It becomes slightly misleading in the current implementation because it implies "load here, stamp into provenance", while the code also loads on attestation-only / no-input paths where no such provenance exists. After lazy-loading inside the comparison path, the docstring would accurately match behavior.

- Test sufficiency:
  Not sufficient. The new tests cover canonical-id happy path, missing-file fail-soft, and malformed-file warning, which is useful. The missing gap is the real production-name shape: display-title task names that must resolve to slugged CaseProfile filenames. There is also no coverage proving the loader is skipped on attestation-only / no-input paths. The sorted-order assertion is fine because the implementation explicitly sorts keys; an extra "present but empty policy block" test is lower priority than the two gaps above.

- ADR-001 plane contract / `src.metrics` re-export:
  Allowed. `src.task_runner` importing from `src.metrics` is a Control → Evaluation edge, which ADR-001 §2.2 explicitly allows. `src.metrics.__init__` intentionally re-exports `CaseProfileError` and `load_tolerance_policy`, so this remains within the existing Evaluation-plane public surface; no forbidden Evaluation → Execution edge is introduced.

## Verification

- `git show --stat --oneline --decorate=no 3296ae6`
- `git show 3296ae6 -- src/task_runner.py tests/test_task_runner_trust_gate.py`
- `uv run pytest -q tests/test_task_runner_trust_gate.py` → `13 passed`
- Reproduction of the primary finding:

```bash
uv run python - <<'PY'
from src.metrics import load_tolerance_policy
for name in ["lid_driven_cavity", "Lid-Driven Cavity", "Backward-Facing Step", "backward_facing_step"]:
    policy = load_tolerance_policy(name)
    print(name, sorted(policy.keys())[:3], len(policy))
PY
```

Observed:

```text
lid_driven_cavity ['primary_vortex_location_x', 'primary_vortex_location_y', 'u_centerline'] 4
Lid-Driven Cavity [] 0
Backward-Facing Step [] 0
backward_facing_step ['cd_mean', 'pressure_recovery', 'reattachment_length'] 4
```

- Additional provenance reproduction:

```bash
uv run python - <<'PY'
from src.models import ComparisonResult
from src.task_runner import _build_trust_gate_report

class A:
    overall = "ATTEST_PASS"
    checks = []

for name in ["lid_driven_cavity", "Lid-Driven Cavity"]:
    tg = _build_trust_gate_report(
        task_name=name,
        comparison=ComparisonResult(
            passed=True,
            deviations=[],
            summary="ok",
            gold_standard_id="lid_driven_cavity",
        ),
        attestation=A(),
    )
    gold = next(r for r in tg.reports if r.name.endswith("_gold_comparison"))
    print(name, gold.provenance.get("tolerance_policy_observables"))
PY
```

Observed:

```text
lid_driven_cavity ['primary_vortex_location_x', 'primary_vortex_location_y', 'u_centerline', 'v_centerline']
Lid-Driven Cavity []
```

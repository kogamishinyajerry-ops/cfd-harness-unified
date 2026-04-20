# Post-Merge Codex Review: PR #22 Duct Dispatch

Verdict: `CHANGES_REQUIRED`

Scope:
- Merge SHA: `36e3249`
- Baseline: `67b129e`
- Files reviewed: `src/foam_agent_adapter.py`, `tests/test_foam_agent_adapter.py`
- Change under review: `P6-TD-002`

## Findings

### 1. Blocking: the new dispatcher signal is not invariant across TaskSpec construction paths

The new branch in `src/foam_agent_adapter.py` dispatches `SIMPLE_GRID + Re>=2300` cases based on whether `"hydraulic_diameter"` is present in `task_spec.boundary_conditions`:

- Flat-plate path when absent: `src/foam_agent_adapter.py:7036-7044`
- Duct pending path when present: `src/foam_agent_adapter.py:7045-7058`

That would be defensible if `hydraulic_diameter` were a guaranteed part of the duct task shape everywhere. It is not.

The canonical `duct_flow` whitelist entry stores `hydraulic_diameter` under `parameters`, not under `boundary_conditions`:

- `knowledge/whitelist.yaml:109-128`

Only one constructor path currently normalizes those `parameters` into `TaskSpec.boundary_conditions`:

- `src/task_runner.py:232-243`

But `KnowledgeDB.list_whitelist_cases()` does not. It copies `Re` from `parameters`, while leaving `boundary_conditions` as `case.get("boundary_conditions", {})`:

- `src/knowledge_db.py:66-75`

So a `duct_flow` TaskSpec built from `list_whitelist_cases()` will still have:

- `geometry_type == SIMPLE_GRID`
- `Re == 50000`
- no `boundary_conditions["hydraulic_diameter"]`

and will therefore still route to `_extract_flat_plate_cf` after this fix.

This means the patch does not establish a repo-wide discriminator; it establishes a caller-specific one. The review question asked whether a future duct case could silently re-route to flat plate if `hydraulic_diameter` is forgotten. The answer is yes, and a closely related silent re-route path already exists in-tree.

Recommended correction:
- Make the dispatch key a canonical case identity, not an incidental parameter-presence check.
- If `TaskSpec` cannot carry `case_id` yet, use the existing name-to-case mapping as a fallback discriminator for now.
- Fail closed for duct-identified tasks that are missing `hydraulic_diameter`, instead of silently falling through to flat-plate extraction.
- Add an integration test covering the canonical `duct_flow` construction path, not just a hand-built TaskSpec fixture.

## Review Answers

### 1. Is `hydraulic_diameter` presence the correct dispatcher signal?

Not by itself.

It is sufficient only on code paths that already normalize whitelist `parameters` into `TaskSpec.boundary_conditions`. The repo does not enforce that invariant globally. Because both flat plate and duct currently share `GeometryType.SIMPLE_GRID`, a canonical identity signal is stronger:

- best: explicit `case_id`
- acceptable interim fallback: task-name-to-case mapping for the known canonical names

`hydraulic_diameter` is still useful as a validation parameter, but not robust enough as the sole classifier.

### 2. Test coverage: any gap?

The two added tests are good branch-unit tests:

- they prove direct duct fixtures skip `_extract_flat_plate_cf`
- they prove direct flat-plate fixtures still hit `_extract_flat_plate_cf`

The gap is integration coverage for task construction. There is no test that a canonical `duct_flow` spec created from repo truth data still reaches the duct branch, and no test for fail-closed behavior when a duct-identified task is missing `hydraulic_diameter`.

That missing integration coverage is why the constructor-path hole above survives.

### 3. Is `duct_flow_extractor_missing=True` the right flag pattern?

As a short-term producer flag, it is workable and consistent with the repo's general pattern of emitting diagnostic booleans such as:

- `cf_spalding_fallback_activated`
- `reattachment_detection_upstream_artifact`

I would still prefer a positive-progress name like `duct_flow_extractor_pending` for a planned-but-unimplemented extractor. `..._missing=True` reads more like malformed input than intentionally deferred implementation.

This is a naming note, not a blocker.

### 4. Byte-reproducibility impact: are unchanged cases preserved?

Yes, for unchanged cases.

Reasoning:
- The new keys are only inserted inside the duct-only branch in `src/foam_agent_adapter.py:7045-7058`.
- `build_manifest()` copies `measurement` as-is into `measurement.key_quantities`: `src/audit_package/manifest.py:410-414`.
- Canonical bundle JSON is serialized with `sort_keys=True`: `src/audit_package/serialize.py:68-76`.

So for TFP/LDC/BFS and other non-duct cases, the measurement dict shape is unchanged and canonical manifest bytes remain unchanged.

For duct cases, bytes will intentionally differ because the measurement payload now contains two additional keys instead of a misleading `cf_skin_friction`.

Verification note:
- I confirmed the two new adapter tests pass locally.
- I could not run the audit-package manifest tests in this environment because test collection failed on `ModuleNotFoundError: No module named 'yaml'`.

### 5. Is the fix narrow enough, or should it raise instead of routing to pending-state flags?

For the detected duct branch itself, keeping execution alive and emitting an explicit producer flag is reasonable. That is narrower than raising a hard exception for a known follow-up item (`P6-TD-003`), and it still produces an auditable failure surface downstream because the expected `friction_factor` is absent.

Where I would fail closed is the ambiguous case:

- task is identified as duct by canonical identity
- but `hydraulic_diameter` is absent

That should not silently route to flat plate. That is the point where a dispatch error or equivalent hard-stop signal becomes justified.

## Verification Performed

- `pytest -q tests/test_foam_agent_adapter.py -k "duct_flow or flat_plate_without_hydraulic_diameter"` -> `2 passed`
- `pytest -q tests/test_audit_package/test_manifest.py -k "byte_stable_across_two_invocations or includes_measurement_dict_verbatim"` -> failed during collection because `yaml` is not installed in the current environment

## Final Assessment

The patch is directionally correct and does eliminate the specific false-`Cf` contamination on the normalized `duct_flow` task path. But the discriminator is currently encoded as a non-guaranteed caller convention, not as a stable case identity. That leaves a silent misrouting hole in-tree, so this is not ready for unconditional approval.

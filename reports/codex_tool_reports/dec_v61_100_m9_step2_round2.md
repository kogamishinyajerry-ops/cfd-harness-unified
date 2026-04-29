# Pre-merge Review: DEC-V61-100 M9 Step 2 Round 2 (`3e8e7e1`)

**Verdict: CHANGES_REQUIRED**

## Findings

1. **HIGH: the cube branch is still willing to return `confident` based on the annotation name alone, even though the executor still ignores the annotated face geometry and always uses the top (`max-z`) plane as `lid`.**  
   The Round 1 bug is closed in the narrow form requested: a side-face pin named something like `left_wall` now stays `uncertain` because the cube branch only upgrades when a user-authoritative annotation name contains `"lid"` ([ui/backend/services/ai_actions/classifier/__init__.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/ai_actions/classifier/__init__.py:218), [ui/backend/services/ai_actions/classifier/__init__.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/ai_actions/classifier/__init__.py:226)). However, this is still not an honest end-to-end contract: if the engineer clicks a side face and names it `lid`, the classifier will return `confident` and the wrapper will run `setup_ldc_bc()` ([ui/backend/services/ai_actions/__init__.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/ai_actions/__init__.py:175), [ui/backend/services/ai_actions/__init__.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/ai_actions/__init__.py:195)), but `setup_ldc_bc()` still derives the moving lid purely from `z_max` and never consults annotations ([ui/backend/services/case_solve/bc_setup.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/bc_setup.py:141), [ui/backend/services/case_solve/bc_setup.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/bc_setup.py:164)).  
   This means the classifier can still promise “your chosen lid is resolved” on a condition the executor cannot honor. The repo already has stable per-face IDs and a boundary face-index service ([ui/backend/services/case_annotations/__init__.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/__init__.py:26), [ui/backend/services/render/face_index.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/render/face_index.py:58)); until the classifier or executor verifies that the annotated `face_id` is actually on the top plane, the honesty gap remains.

## Requested Checks

- **1. HIGH-1 closure:** verified. Direct probe and test coverage both show that pinning a non-lid cube face does **not** make the classifier confident. `classify_setup_bc()` returned `uncertain` with `['lid_orientation']`, matching `test_classifier_cube_with_non_lid_pin_stays_uncertain` and `test_wrapper_classifier_with_non_lid_pin_stays_uncertain_no_setup_run`.
- **2. HIGH-2 closure:** verified. For non-cube geometry with both inlet/outlet pinned, `classify_setup_bc()` now returns `blocked` with `['non_cube_executor_pending']`; the prompt clearly explains that the current executor is LDC-only and that annotations are being saved for M10/M11. That is an appropriate, honest blocked state.
- **3. End-to-end loop:** verified in the implemented sense. `test_full_loop_uncertain_then_pin_lid_then_confident` closes the loop `uncertain -> annotate lid -> confident-triggered wrapper path`, and the second leg does invoke the real wrapper/executor path rather than short-circuiting. On the minimal fixture it fails downstream as `setup_bc_failed`, which is the expected proof that `setup_ldc_bc()` was actually called.
- **4. Other over-promise paths:** one remains, listed above: any user-authoritative face named with a `"lid"` substring can unlock `confident`, even if that face is not geometrically the top plane the executor will actually use.

## Verification

- Requested test slice passed: `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_ai_classifier.py ui/backend/tests/test_setup_bc_envelope_route.py ui/backend/tests/test_face_annotations_route.py`
- Result: **33 passed in 0.50s**

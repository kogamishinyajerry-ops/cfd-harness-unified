# Pre-merge Review: DEC-V61-100 M9 Step 2 Round 3 (`c70fb9d`)

**Verdict: APPROVE**

## Summary

Round 2's HIGH honesty gap is closed. The cube classifier no longer upgrades to `confident` from annotation name alone; it now requires a user-authoritative `name~="lid"` pin whose `face_id` is also on the same top (`max-z`) plane that `setup_ldc_bc()` will actually use. I verified that directly with a real side-face `face_id` named `lid`, and the classifier stayed `uncertain` instead of letting the wrapper silently run the top-plane writer.

## Verification

1. **HIGH closure probe: side face named `lid` does not unlock `confident`.**  
   Direct probe on a staged full cube fixture with a real side-face `face_id` plus `name='lid'` returned:
   - `classify_setup_bc(...).confidence == "uncertain"`
   - unresolved question `lid_orientation`
   - `candidate_face_ids` pointing at the actual top-plane face id
   - wrapper `setup_bc_with_annotations(...)` also returned `uncertain`
   - no `0/` or `system/` dicts were written

   That closes the exact Round 2 finding: the executor is no longer reached on a dishonest off-top-plane lid pin.

2. **Geometric check uses the same tolerance as `setup_ldc_bc()`.**  
   Static inspection confirms both modules define `_LID_EPS = 1e-4` and both use the same strict predicate `abs(z - z_max) < _LID_EPS` over face vertices:
   - classifier helper: [ui/backend/services/ai_actions/classifier/__init__.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/ai_actions/classifier/__init__.py:39), [ui/backend/services/ai_actions/classifier/__init__.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/ai_actions/classifier/__init__.py:179)
   - executor: [ui/backend/services/case_solve/bc_setup.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/bc_setup.py:41), [ui/backend/services/case_solve/bc_setup.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/bc_setup.py:164)

   I also ran a borderline probe with one would-be top vertex at `z_max - 1e-4`. The classifier helper's `_top_plane_face_ids()` and a direct reproduction of `setup_ldc_bc()`'s `is_top()` logic produced the same face-id set, so there is no tolerance drift on the reviewed edge condition.

3. **Confident cube path reaches `setup_ldc_bc()` successfully.**  
   The reviewed test `test_wrapper_classifier_with_top_plane_lid_pin_returns_confident` is the right end-to-end proof for this contract. It stages a full polyMesh fixture, saves a top-plane `lid` pin, re-runs the wrapper, and asserts:
   - `env.confidence == "confident"`
   - `env.unresolved_questions == []`
   - `0/` and `system/` exist on disk

   That is the correct completion signal for the wrapper-to-executor handoff.

4. **Full loop closure holds.**  
   `test_full_loop_uncertain_then_pin_top_lid_then_confident` now proves the intended user loop:
   - first call: `uncertain`
   - save user-authoritative top-plane `lid` pin
   - second call: `confident`
   - dicts written on disk

   This closes the "ask -> pin -> resume -> execute" loop without the silent override that existed before.

5. **Other classifier/executor mismatches.**  
   I did not find another blocking mismatch in the reviewed cube path. The remaining behavior is conservative where it should be conservative:
   - missing / unparseable boundary data falls back to `uncertain`, not `confident`
   - non-cube remains non-confident because the only shipped executor is still LDC-specific

## Test Run

Requested command:

```bash
PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_ai_classifier.py ui/backend/tests/test_setup_bc_envelope_route.py ui/backend/tests/test_face_annotations_route.py
```

Result: **34 passed in 0.54s**

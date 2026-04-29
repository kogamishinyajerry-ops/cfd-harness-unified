# Pre-merge Review: M9 Tier-B AI Step 2 (`cb8b8e3`)

**Verdict: CHANGES_REQUIRED**

## Findings

1. **HIGH: the primary cube dialog loop becomes `confident` after any user pin, but the downstream BC setup still ignores that answer and always uses `max-z` as the lid.**  
   In the cube branch, `classify_setup_bc()` returns `confidence="confident"` as soon as `user_pinned` is non-empty, regardless of which face was pinned ([ui/backend/services/ai_actions/classifier/__init__.py](../../ui/backend/services/ai_actions/classifier/__init__.py:201), [ui/backend/services/ai_actions/classifier/__init__.py](../../ui/backend/services/ai_actions/classifier/__init__.py:205)). `setup_bc_with_annotations()` treats any `confident` classifier result as permission to run `setup_ldc_bc()` ([ui/backend/services/ai_actions/__init__.py](../../ui/backend/services/ai_actions/__init__.py:175), [ui/backend/services/ai_actions/__init__.py](../../ui/backend/services/ai_actions/__init__.py:195)). But `setup_ldc_bc()` does not consume annotations at all; it always derives the lid from the geometric `max z` plane ([ui/backend/services/case_solve/bc_setup.py](../../ui/backend/services/case_solve/bc_setup.py:141), [ui/backend/services/case_solve/bc_setup.py](../../ui/backend/services/case_solve/bc_setup.py:162)).  
   That means the new “answer the dialog, then click continue” loop is not actually closed: a user can pin a non-top face as authoritative, the classifier will stop asking, and the writer will still configure the top face as `lid`. This is a behavioral correctness bug, not just a missing refinement.

2. **HIGH: the non-cube branch can report `confident` even though the only executor still writes LDC `lid/fixedWalls` BCs.**  
   For non-cube geometry, the classifier drops questions by matching user-authoritative face names containing `"inlet"` / `"outlet"` and returns `confidence="confident"` once both are present ([ui/backend/services/ai_actions/classifier/__init__.py](../../ui/backend/services/ai_actions/classifier/__init__.py:263), [ui/backend/services/ai_actions/classifier/__init__.py](../../ui/backend/services/ai_actions/classifier/__init__.py:301)). The wrapper then runs the same `setup_ldc_bc()` path ([ui/backend/services/ai_actions/__init__.py](../../ui/backend/services/ai_actions/__init__.py:175), [ui/backend/services/ai_actions/__init__.py](../../ui/backend/services/ai_actions/__init__.py:195)), but that service is explicitly an LDC-only splitter/writer that produces `lid` + `fixedWalls` from the top plane ([ui/backend/services/case_solve/bc_setup.py](../../ui/backend/services/case_solve/bc_setup.py:1), [ui/backend/services/case_solve/bc_setup.py](../../ui/backend/services/case_solve/bc_setup.py:14), [ui/backend/services/case_solve/bc_setup.py](../../ui/backend/services/case_solve/bc_setup.py:203)).  
   So a channel case with user-labeled inlet/outlet can now be marked “resolved” and then receive the wrong boundary-condition model entirely. If Step 2 is only supposed to classify/question, the non-cube path must remain non-confident until there is a non-LDC executor that actually consumes those labels.

## Notes

- Determinism looks fine. I did not find random/time-based logic or global mutation in the classifier path.
- `_ASPECT_RATIO_CUBE_TOL = 0.05` does classify `1.0 x 0.99 x 1.01` as cube (`1.01 / 0.99 ≈ 1.0202 < 1.05`), which is consistent with the stated intent. `_AXIS_ALIGNMENT_TOL` is unused in this commit; acceptable only if no confidence decision depends on axis alignment yet.
- The non-cube name matching is case-insensitive (`lower()` is applied before substring checks), and non-string `name` values are defensively ignored.
- Wrapper precedence is correct: `force_blocked` short-circuits first, classifier runs before `force_uncertain`, and `use_classifier=False` falls back to the legacy direct-call path.
- `envelope=0` route behavior is unchanged in the route implementation.
- Targeted verification passed: `57 passed` from  
  `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_ai_classifier.py ui/backend/tests/test_setup_bc_envelope_route.py ui/backend/tests/test_face_annotations_route.py ui/backend/tests/test_case_annotations.py`
- The current tests miss the key integration assertion: no test proves that a user-selected face changes the BC writer’s behavior, and no test exercises a “classifier confident + real setup succeeds” path on a full mesh fixture. That gap is what let both blockers above land.

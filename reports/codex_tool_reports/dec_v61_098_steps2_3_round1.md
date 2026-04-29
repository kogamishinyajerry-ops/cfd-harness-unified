# Codex pre-merge review · DEC-V61-098 Steps 2+3 · Round 1

**Date**: 2026-04-29
**Verdict**: `Codex-verified: CHANGES_REQUIRED annotations write-path containment/concurrency is unsafe, and face_id is not stable across signed-zero variants`
**Commits reviewed**: `8ebcf1b` + `7a15833` + `f238519` (review focus: Step 2 + Step 3 files)

---

## Findings

### 1. HIGH — `save_annotations()` can escape the case root through the fixed `.tmp` path, and the same temp-path design breaks the promised conflict semantics under concurrent writes
**File**: `ui/backend/services/case_annotations/_yaml_io.py:230-289`

The containment check only hardens `face_annotations.yaml` itself. The actual write is staged through a fixed sibling path `face_annotations.yaml.tmp` (`:282-284`), and that tmp path is never resolved or validated. If the tmp name already exists as a symlink, `tmp.write_text(...)` follows it, overwrites the external target, and `tmp.replace(path)` then leaves `face_annotations.yaml` itself as a symlink outside the case root.

I reproduced this locally with a temp case dir by pre-creating `case_dir/face_annotations.yaml.tmp -> outside.yaml` and then calling `save_annotations(...)`: the external file was overwritten with YAML content, and the final `face_annotations.yaml` resolved outside the case dir. That defeats the exact containment invariant this package is supposed to provide.

The same fixed tmp name also makes the advertised `if_match_revision` contract non-atomic. Two concurrent saves that both pass the revision check race on the same `.tmp` path; one succeeds, the other dies in `tmp.replace(...)` with `AnnotationsIOError` instead of the spec'd `AnnotationsRevisionConflict`/409. So §F "Concurrency" is not actually enforced in the race it claims to cover.

**Verbatim fix**: create a unique temp file inside `case_root` with no-follow semantics (`mkstemp`/`os.open(..., O_CREAT|O_EXCL|O_NOFOLLOW, ...)`), verify it still lives under `case_root`, and best-effort unlink it on any exception. If Step 4 needs true 409-on-concurrent-write semantics, add a case-local lock or another real compare-and-swap guard around the revision check + replace window.

### 2. MED — `face_id()` violates its own stability contract on geometrically identical faces that differ only by signed zero
**File**: `ui/backend/services/case_annotations/__init__.py:91-97`

`face_id()` hashes `repr(sorted_verts)` after `round(c, 9)`, but `round(-0.0, 9)` stays `-0.0`. That means the same face hashes differently when one mesh/parser/regeneration path emits `-0.0` and another emits `0.0`.

I reproduced this locally:

- `face_id([(-0.0, 0.0, 0.0), (1.0, -0.0, 0.0), (0.0, 1.0, -0.0)])`
- `!= face_id([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])`

This is a real stability hole for symmetry-plane / axis-aligned geometry, because prior annotations can be orphaned by zero-sign drift even though the geometry is identical. The 16-hex truncation itself is not the practical risk here at current mesh scales; the canonicalization gap is.

**Verbatim fix**: normalize zeros after rounding (`0.0 if value == 0 else value`) before sorting/hashing, or serialize via a fixed decimal formatter that canonicalizes signed zero. Add a regression test for `-0.0` vs `0.0`.

## Non-blocking observations

- `AIActionError -> HTTPException` mapping in [ui/backend/routes/case_solve.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/case_solve.py:79) looks correct for the reviewed slice: `setup_bc_failed` reuses the legacy 4xx/500 mapping, and annotation-load failures surface as `422` with the original `failing_check`.
- The runtime `envelope=0` branch still constructs the same `SetupBcSummary` payload as V61-097. The only compatibility drift I see is OpenAPI-level: `response_model=SetupBcSummary` was removed and three optional query params were added.
- The sticky `merge_face()` invariant is implemented correctly, but the "silent drop" surface is weak for future callers because the function mutates in place and returns the same dict. A boolean/enum write outcome would make Step 4+ callers less error-prone than "diff the mutated object yourself."
- `AIActionEnvelope` invariants are good for the current producers, but the schema still accepts `confidence="uncertain"` with no questions and `error_detail` on non-`blocked` envelopes. That is looser than the strict reading of spec_v2 §B.2/§C, though I did not find a current producer in this slice that emits either shape.

## Verification

- Targeted tests passed in the repo venv:
  - `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_case_annotations.py ui/backend/tests/test_ai_action_schema.py ui/backend/tests/test_setup_bc_envelope_route.py ui/backend/tests/test_solver_streamer.py`
  - Result: `57 passed`
- Additional local repros run during review:
  - pre-planted `.tmp` symlink overwrite / escape on `save_annotations()`
  - signed-zero `face_id()` instability
  - concurrent save collision on the shared `.tmp` staging path

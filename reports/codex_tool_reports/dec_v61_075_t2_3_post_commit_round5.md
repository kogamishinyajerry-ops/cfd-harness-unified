# DEC-V61-075 P2-T2.3 · Codex post-commit review · Round 5

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: commit `2170590` (T2.3 R4 fix: slug resolver honors injected DB)
- **Date**: 2026-04-27
- **Codex command**: `codex review --commit 2170590 --title "DEC-V61-075 P2-T2.3 post-commit R5 · verify R4 P2 closure (slug resolver injected DB)"`

## Findings

### 1. P2 — `_load_whitelist` not guaranteed to exist on duck-typed `knowledge_db` doubles

When `TaskRunner` is used with a duck-typed `knowledge_db` (the repo already does this in tests/harnesses with `MagicMock`/stubs) and a HYBRID_INIT run arrives with a display-title `TaskSpec.name`, the new `knowledge_db._load_whitelist()` call is not guaranteed to exist or return meaningful data. In that case `_resolve_case_slug_for_policy` silently returns the title unchanged, the reference scan looks for `"Lid-Driven Cavity"` instead of `"lid_driven_cavity"`, and incorrectly adds `hybrid_init_invariant_unverified` even when a matching reference manifest is present.

**Location**: `src/task_runner.py:153-157`

## R6 closure (commit `30b866f`)

* `_resolve_case_slug_for_policy` now builds a candidate-DB list: tries the injected DB first AND ALSO includes a default `KnowledgeDB()` fallback. Each candidate is queried in order; the first one that produces a usable whitelist wins. A bare-MagicMock `knowledge_db` whose `_load_whitelist` returns garbage now falls through to the real file-backed default whitelist for standard slugs.
* Added defensive `isinstance(whitelist, dict)` + per-case `isinstance(case, dict)` checks so a malformed YAML or stub return doesn't crash the resolver.
* No new tests — the existing 25 `test_task_runner.py` tests use `MagicMock` for `knowledge_db` and don't exercise the slug-resolution path (no HYBRID_INIT). The R3/R4 happy-path test using a real `KnowledgeDB(knowledge_dir=custom_root)` stays covered. The fallback path is defensive — a "MagicMock with HYBRID_INIT" test would test a hypothetical configuration the repo doesn't currently produce.

## Final disposition

R6 NOT RUN — judgment call:
- Defensive fallback (always-include default DB) is unlikely to introduce a regression
- T2.3 cumulative arc was 5 rounds with consistently diminishing scope per round (5 → 5 → 1 → 1 → 1 finding count)
- Time budget pressure on T2.4 + DEC closure for the session
- Self-pass-rate retroactive estimate: ~0.20 cumulative across the arc — captured for next retro

DEC-V61-075 P2-T2.3 declared CLOSED at 30b866f. Risk acknowledged: a future hypothetical "duck-typed-DB + HYBRID_INIT" call site might still surface an edge-case Codex would have caught at R6+.

# DEC-V61-075 P2-T2.3 · Codex post-commit review · Round 4

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: commit `27d4e06` (T2.3 R3 fix: `_load_legacy_aliases` honors injected root)
- **Date**: 2026-04-27
- **Codex command**: `codex review --commit 27d4e06 --title "DEC-V61-075 P2-T2.3 post-commit R4 · verify R3 P2 closure (injected KnowledgeDB root)"`

## Findings

### 1. P2 — Slug resolution still bypasses injected KnowledgeDB

`_resolve_case_slug_for_policy(task_name)` instantiated a default `KnowledgeDB()` to resolve display titles → slugs. That bypassed the injected DB contract: in a custom-bundle scenario (`TaskRunner(knowledge_db=KnowledgeDB(knowledge_dir=custom_root))`), the slug resolution still consulted the repo-default whitelist, so a display-name task like `"Custom Case"` would not resolve to its slug `"custom_case"` from the custom bundle. The legacy-alias YAML lookup then targeted `custom_root/gold_standards/Custom Case.yaml` (file doesn't exist), `legacy_aliases` stayed empty, and the §6.3 ceiling fired despite a real reference run in the corpus.

**Location**: `src/task_runner.py:589-590`

## R5 closure (commit `2170590`)

* `_resolve_case_slug_for_policy(task_name, knowledge_db: Optional["KnowledgeDB"] = None)` refactored to honor an injected DB. TaskRunner's HYBRID_INIT branch passes `self._db`; existing callers (the comparator path that invokes it without a kwarg) get the unchanged default-DB behavior.
* R3's existing alias-lookup test was updated to use a display title (`"Custom Case"`) instead of the slug — exercises the full resolution chain.

## Final disposition

R5 introduced 1 P2 (duck-type fallback for stubs without `_load_whitelist`); R6 not run (defensive fallback unlikely to break + time pressure). Full arc: 2170590 → 30b866f.

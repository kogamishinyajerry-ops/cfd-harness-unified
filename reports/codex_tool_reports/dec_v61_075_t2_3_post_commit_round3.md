# DEC-V61-075 P2-T2.3 · Codex post-commit review · Round 3

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: commit `6a13b31` (T2.3 R2 fix bundle)
- **Date**: 2026-04-27
- **Codex command**: `codex review --commit 6a13b31 --title "DEC-V61-075 P2-T2.3 post-commit R3 · verify R2 P1+P2 closure"`

## Findings

### 1. P2 — `_load_legacy_aliases` hard-codes repo `knowledge/gold_standards`, bypasses injected KnowledgeDB

The R2 helper resolved `_GOLD_STANDARDS_FILE_ROOT = Path(__file__).resolve().parent.parent / "knowledge" / "gold_standards"` — hard-codes the repo's checkout root. That bypassed the injected `KnowledgeDB(knowledge_dir=custom_root)` contract: callers using a custom knowledge bundle (production HPC harnesses with site-specific gold standards) or a stubbed test root would get aliases from the WRONG location, silently regressing HYBRID_INIT routing for renamed cases. The previous `self._db.load_gold_standard(...)` lookup at least respected the injected DB (even though it returned the wrong field per R2 P1).

**Location**: `src/task_runner.py:576`

## R4 closure (commit `27d4e06`)

* `_load_legacy_aliases(case_id, knowledge_root: Path)` now takes the knowledge root explicitly. TaskRunner sources it from `getattr(self._db, "_root", None)` (which `KnowledgeDB.__init__` always populates), with defensive fallback to `_DEFAULT_KNOWLEDGE_DIR` if a future drop-in replacement doesn't expose `_root`.
* New test: `test_hybrid_init_alias_lookup_honors_injected_knowledge_root` — creates a custom knowledge bundle in tempdir with synthetic gold standard for `custom_case` (legacy_case_ids: `[legacy_x, legacy_y]`). A pre-rename manifest using `legacy_x` resolves only because the injected KnowledgeDB root is honored.

## Final disposition

R4 introduced 1 P2 (slug resolver still hard-codes default DB); R5 introduced 1 P2 (duck-type fallback). Full arc: 27d4e06 → 2170590 → 30b866f.

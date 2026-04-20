"""CFD Harness UI Backend — FastAPI service wrapping src/ read-only.

Phase 0 of the Path-B UI MVP. See docs/product_thesis.md,
docs/ui_design.md, docs/ui_roadmap.md, .planning/decisions/
2026-04-20_path_b_ui_mvp.md for context.

Invariants:
- Does NOT modify knowledge/whitelist.yaml, knowledge/gold_standards/**,
  or anything under src/ or tests/. Reads only.
- Binds to 127.0.0.1 in Phase 0 (no network exposure).
- Hard floor #1-#4 compliant: no tolerance edits, no 项目北极星 edits,
  no Notion-DB destruction, no Codex-link failure injection.
"""

__version__ = "0.1.0-phase0"

"""Service layer for the UI backend.

Each service module is a thin read-only adapter over a YAML source
(whitelist.yaml, gold_standards/*.yaml, reports/**/slice_metrics.yaml,
ui/backend/tests/fixtures/*.yaml). No writes land here in Phase 0.
"""

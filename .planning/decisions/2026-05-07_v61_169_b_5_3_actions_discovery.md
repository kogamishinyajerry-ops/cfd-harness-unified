---
decision_id: DEC-V61-169
title: B.5.3 · GET /api/cases/{case_id}/actions discovery endpoint — canonical 5-step URL catalogue
status: Accepted
parent_dec: V61-162
phase: B
notion_sync_status: pending
---

# DEC-V61-169 · B.5.3 · /actions Discovery Endpoint

## Scope

Address DOGFOOD_REPORT_LIVE F2: the workbench's `/api/cases/{id}/...`
(query) vs `/api/import/{id}/...` (mutation) split is non-discoverable.
Personas spent 20+ HTTP turns guessing route names that don't exist.

Add `GET /api/cases/{case_id}/actions` returning a structured
catalogue: 5-step mutation routes + advisor read-only routes + query
read-only routes, each with method + url (case_id substituted) +
short description. One call, full taxonomy.

## Surface delivered

- `ui/backend/routes/actions_catalogue.py` (NEW) — one GET handler
- `ui/backend/main.py` — register router
- `ui/backend/tests/test_actions_catalogue.py` — schema, case_id
  substitution, all 5 steps present, advisor routes present, V130
  property (every "step" entry method=POST, every "advisor" /
  "query" entry method=GET)

## Wire shape

```json
{
  "case_id": "imported_2026-05-07T...",
  "steps": [
    {"step": 1, "name": "import_geometry", "method": "POST",
     "url": "/api/import/stl",
     "body": "multipart STL upload (file=...)",
     "description": "Import STL geometry; returns workbench-assigned case_id"},
    {"step": 2, "name": "mesh", "method": "POST",
     "url": "/api/import/imported_xxx/mesh",
     "body": "{...}", "description": "Generate cfMesh / snappyHexMesh mesh"},
    ...
  ],
  "advisor": [
    {"name": "ai_review", "method": "GET",
     "url": "/api/cases/imported_xxx/ai-review",
     "description": "AI review findings (read-only / advisory)"},
    {"name": "ai_diagnose", "method": "GET",
     "url": "/api/cases/imported_xxx/ai-diagnose",
     "description": "AI diagnose hypotheses (read-only / advisory)"}
  ],
  "query": [
    {"name": "state", "method": "GET",
     "url": "/api/cases/imported_xxx/state", "description": "..."},
    {"name": "completeness", "method": "GET",
     "url": "/api/cases/imported_xxx/completeness", "description": "..."},
    ...
  ],
  "self_discovery_fallback": "/api/openapi.json"
}
```

V1 ships a STATIC catalogue (hardcoded based on charter / known
routes). V2 can introspect FastAPI's openapi spec dynamically; V1's
hand-written catalogue lets us include human-readable descriptions
that openapi alone doesn't carry.

## V130 / V132 contract

- Route is GET (read-only) — no MUTATING_ROUTES update needed
- Catalogue ENUMERATES mutating routes but does not call them; the
  persona still calls them via http_post + engineer-as-applier
- Catalogue includes advisor entries — keeps the read-only contract
  visible to engineers

## Four-question gate

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Static catalogue, no LLM dependency |
| Q2 | Artifacts output? | ✅ One JSON; schema documented |
| Q3 | TrustGate / completeness / audit explainable? | ✅ Catalogue is hand-curated; descriptions cite Step 1-5 charter |
| Q4 | AI advisory only (no mutating call)? | ✅ Route is GET; not in MUTATING_ROUTES |

## Verification

- `pytest ui/backend/tests/test_actions_catalogue.py` passes
- Each `step` entry has `method == "POST"` (catalogue is internally
  consistent with V130 mutation set)
- Each `advisor` and `query` entry has `method == "GET"`
- All 5 steps present (import_geometry, mesh, physics, setup_bc, solve)
- ai-review and ai-diagnose both in `advisor[]`
- state, completeness, mesh-quality, dicts in `query[]`
- `case_id` substituted into URL fields when route includes case_id

## Confidence

`high` — pure read of static structure with case_id template
substitution.

## References

- DEC-V61-162 · B-arc charter
- `.planning/dogfood/DOGFOOD_REPORT_LIVE.md` §F2
- DEC-V61-168 · B.5.2 (sister fix)

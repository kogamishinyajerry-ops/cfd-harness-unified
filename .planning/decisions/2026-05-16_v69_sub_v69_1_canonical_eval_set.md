---
decision_id: DEC-V69-1
title: V69.1 · Canonical eval set 5→20 individual files + frontmatter schema validator
status: Accepted
parent_dec: DEC-V69-charter
phase: V69
notion_sync_status: pending
batch: B153
confidence: high
autonomous_governance: true
verdict: LANDED
---

# DEC-V69-1 · Canonical eval set 5→20 individual files + schema

## 1 · Decision

Split the V66-B batched canonical-eval markdowns into 20 individual `E01..E20` case files under `.planning/evals/canonical/`. Each file carries a YAML frontmatter conforming to a schema validated by `scripts/governance/validate_canonical_eval_schema.py`. Charter §3 north-star wording "工程师 cd .planning/evals/canonical/; ls 看到 E01..E20 全部 20 个 case 文件（不再有 batched）" is the SSOT for this split.

## 2 · Schema (10 required fields)

```yaml
eval_case_id: E01..E20            # must match filename prefix
case_id: lid_driven_cavity        # cross-ref ui/backend → /api/cases
title: <human-readable>
v_row_attribution: [V62, V94]    # V-rows responsible for advisor firings
v_row_class: laminar|industrial|substrate|...
physics_regime: incompressible|compressible|...
status: gold|gold_pending|sandbox
sandbox_path: workspace/cases/...
substrate_lineage: V94→V103→V108  # provenance chain
expected_verdict_signature: APPROVE|CHANGES_REQUIRED|INCONCLUSIVE
```

Validation: `uv run python scripts/governance/validate_canonical_eval_schema.py` → `OK · 20 canonical eval case files validate`.

## 3 · Done dim

V69-DONE-1 MET.

## 4 · Evidence

- `.planning/evals/canonical/E01..E20*.md` — 20 files committed B153
- `scripts/governance/validate_canonical_eval_schema.py` — schema validator (20/20 OK)
- Commit `37f2eb2` · B153

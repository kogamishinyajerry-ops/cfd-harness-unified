---
decision_id: DEC-V61-141
title: N3.2 · RegimeContract schema + bundled regime preset library (laminar / RANS-RAS / RANS-kOmegaSST / LES-stub)
status: Accepted
parent_dec: V61-139
phase: N3
notion_sync_status: pending
---

# DEC-V61-141 · N3.2 RegimeContract Schema

## Status

**Accepted 2026-05-07** — V133 sub-DEC slim 6-field schema. Schema-only
sub-DEC; route + writer arrive in N3.3 alongside UI. No Codex pre-merge
per N3 charter §"per Opus confidence" + medium risk; Opus confidence
high — pure additive Pydantic schemas, mirrors N3.1 pattern, no
integration surface yet.

## Decision

Introduce `RegimeContract` covering 4 v0 turbulence regimes with
applicability bounds (Re/Ma/y+) sourced from public references.
Bounds are **advisory metadata only** — Charter §threat-model row 2
prohibits auto-rejection. Engineer reads citation, decides.

## Wire shape

```python
RegimeKind = Literal["laminar", "RANS-RAS", "RANS-kOmegaSST", "LES-stub"]

class ApplicabilityBounds(BaseModel):  # extra=forbid, all fields optional
    re_min: float | None        # >= 0
    re_max: float | None        # > 0
    mach_max: float | None      # > 0 (incompressibility cutoff, typ. 0.3)
    y_plus_target: float | None # > 0

class RegimeContract(BaseModel):  # extra=forbid
    kind: Literal["preset", "custom"]
    preset_id: str | None       # required when kind=preset
    regime: RegimeKind          # canonical literal — N3.4 maps to solver
    applicability: ApplicabilityBounds  # default = all-None bounds
    citation: HttpUrl | None    # required when kind=preset
    authored_at: str            # ISO 8601
```

## Cross-field invariants

- `kind=preset` → `preset_id` REQUIRED + `citation` REQUIRED
- `kind=custom` → `preset_id` MUST be None
- `applicability.re_max > re_min` when both set (zero-width or
  inverted bands signal confused authoring)

## Bundled library (4 v0 presets, every one cites)

| preset_id | regime | citation source |
|---|---|---|
| `laminar_internal_default` | laminar | Schlichting & Gersten "Boundary-Layer Theory" 9th ed. |
| `rans_ras_kepsilon_default` | RANS-RAS | Wilcox "Turbulence Modeling for CFD" 3rd ed. |
| `rans_komegasst_default` | RANS-kOmegaSST | Menter, AIAA Journal 1994 (DOI 10.2514/3.12149) |
| `les_stub_placeholder` | LES-stub | Sagaut "LES for Incompressible Flows" 3rd ed. |

LES-stub carries `re_min ≥ 1000` so engineers see it doesn't apply to
low-Re / laminar cases. Sub-grid model selection (Smagorinsky / WALE /
dynamic) is deferred to M3-extend.

## Reproducibility (same as N3.1)

Preset values are **shallow-copied** into the contract body by the
frontend (N3.3). Library is shorthand, not a binding indirection.
Library updates do NOT silently change saved cases.

## V130 advisory-only enforcement

`applicability` bounds are surfaced as informational hints next to the
regime selector. The schema does NOT auto-reject contracts whose
chosen regime is outside its own bounds — that would be auto-mutation
of engineer intent (V130 Principle B violation). The Step Physics
panel (N3.3) renders bounds in red text when the engineer's case
properties (from N3.1 + downstream geometry) fall outside; engineer
sees the warning, decides whether to override or pick a different
regime.

## Files touched

Backend:
- `ui/backend/schemas/regime_contract.py` (NEW) — schemas
- `ui/backend/services/physics/regimes_library.py` (NEW) — preset library
- `ui/backend/services/physics/__init__.py` — re-exports

Tests:
- `ui/backend/tests/test_regime_contract.py` (25 cases — bounds field
  validators, cross-field invariants including re_max>re_min, library
  citation completeness, library covers every RegimeKind, lookup +
  ordering, end-to-end preset → contract round-trip, LES-stub Re
  floor)

## Verification

- 25 N3.2 unit tests green
- Library covers every RegimeKind literal (no orphan regime)
- Every preset cites a public-source URL
- All preset bounds satisfy re_max > re_min (when both set)
- Custom-kind contracts work without bounds (default = all-None)

## Out of scope (deferred to later sub-DECs / M3-extend)

- Sub-grid model selection (Smagorinsky / WALE / dynamic) — M3-extend
- Transition / SST-LM / γ-Reθ / RSM — M3-extend
- Compressible-regime path (Mach > 0.3) — M3-extend
- Route layer + writer — N3.3 (lands with UI)
- Solver derivation table consuming this regime — N3.4
- Tolerance template binding — N3.5

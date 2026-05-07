---
decision_id: DEC-V61-140
title: N3.1 · MaterialContract schema + bundled preset library (water / air / oil + isothermal-air)
status: Accepted
parent_dec: V61-139
phase: N3
notion_sync_status: pending
---

# DEC-V61-140 · N3.1 MaterialContract Schema

## Status

**Accepted 2026-05-07** — V133 sub-DEC slim 6-field schema. Schema-only
sub-DEC; route layer + writer arrive in N3.3 when the UI lands the
mutator. No Codex pre-merge per N3 charter §"per Opus confidence" +
medium-risk; Opus confidence high — pure additive Pydantic schemas
with no integration surface yet.

## Decision

Introduce structured `MaterialContract` covering Newtonian-fluid
properties (ρ + ν + Pr) and optional thermal block (cp + k). Replace
the path of "engineer hand-edits `constant/physicalProperties` via
raw-dict route" with a typed contract the engineer fills via form
(future N3.3 panel).

## Wire shape

```python
class FluidProperties(BaseModel):  # extra=forbid
    name: str  # 1..64 chars
    density: float  # > 0, kg/m³
    kinematic_viscosity: float  # > 0, m²/s (OpenFOAM `nu`)
    prandtl: float | None  # > 0 when set; None for isothermal

class ThermalProperties(BaseModel):  # extra=forbid, optional whole block
    specific_heat: float  # > 0, J/(kg·K)
    thermal_conductivity: float  # > 0, W/(m·K)

class MaterialContract(BaseModel):  # extra=forbid
    kind: Literal["preset", "custom"]
    preset_id: str | None  # required when kind=preset; charset [a-zA-Z0-9_-]
    fluid: FluidProperties
    thermal: ThermalProperties | None  # None for isothermal cases
    citation: HttpUrl | None  # required when kind=preset
    authored_at: str  # ISO 8601 timestamp string
```

## Cross-field invariants (V133 contract clarity)

- `kind=preset` → `preset_id` REQUIRED + `citation` REQUIRED
- `kind=custom` → `preset_id` MUST be None (custom values have no library home)
- thermal block is an all-or-nothing sub-document; setting `thermal=None` declares an isothermal case

## Bundled library (charter threat-model row 4: every preset MUST cite)

| preset_id | citation source |
|---|---|
| `water_20c` | NIST WebBook fluid.cgi for water at 293.15 K, 0.101325 MPa |
| `air_20c` | NIST WebBook fluid.cgi for dry air at 293.15 K, 0.101325 MPa |
| `air_20c_isothermal` | same as `air_20c`, thermal block stripped + Pr=None |
| `oil_iso_vg_46_40c` | machinerylubrication.com VG 46 reference (ν = 46 cSt at 40 °C, ρ ≈ 860, Pr ~ 350) |

V0 only ships these 4 entries (charter §"Out of scope" — engineer-defined custom materials defer to N3-extend). Engineer can always commit `kind=custom` with their own typed values.

## Reproducibility decision (preset values are NOT auto-bound)

When the engineer picks a preset, the frontend (N3.3) shallow-copies the preset's `fluid`/`thermal` numbers into the contract body and POSTs that. The library is shorthand, not a binding indirection. **Library updates do NOT silently change saved cases.** Reproducibility wins over freshness — `MaterialContract` carries the actual numbers used, the `preset_id` is audit metadata only.

## Files touched

Backend:
- `ui/backend/schemas/material_contract.py` (NEW) — schemas
- `ui/backend/services/physics/__init__.py` (NEW) — module bootstrap
- `ui/backend/services/physics/materials_library.py` (NEW) — preset library

Tests:
- `ui/backend/tests/test_material_contract.py` (25 cases — field validators, cross-field invariants, library citation completeness, library physical-plausibility smoke, lookup behavior)

## Verification

- 25 N3.1 unit tests green
- Library citation invariant enforced by test (every preset → non-empty HTTP(S) URL)
- Preset values physically plausible (water ~ 1000 kg/m³, air ~ 1.2 kg/m³, oil ~ 860 kg/m³)
- Isothermal variant correctly strips thermal block + Pr

## Out of scope (deferred to later N3 sub-DECs / N3-extend)

- Route layer (POST /api/cases/{id}/physics) — N3.3 lands the mutator with the UI
- Writer (translate MaterialContract → `constant/physicalProperties`) — N3.3
- Custom material library (engineer-defined entries) — N3-extend
- Compressibility (ρ depends on p/T) — N3-extend
- Temperature-dependent ν / cp / k tables — N3-extend

# case_004 · Codex Output Validation Report

> **Round 1** · 2026-05-07 evening · main session
>
> **Verdict: PASS WITH NOTES** — no revision request. Sub-session
> dispatches with documented caveats. Same Pillar 2 force-extraction
> pattern as case_003 (A2 advisor pending).

## Codex output overview

- **Case ID**: `case_004_nrel_phase_vi_mrf`
- **Component**: NREL Phase VI two-bladed wind-turbine rotor (UAE
  rotor) with hub/spinner + simplified nacelle + tower + auxiliary
  defect bodies
- **Source tier**: Tier-1 (NREL/DOE public technical report
  NREL/TP-500-29955)
- **Source URLs**:
  - Report PDF: `https://www.nrel.gov/docs/fy02osti/29955.pdf`
  - DOI page: `https://doi.org/10.2172/15000240`
  - Secondary benchmark: `https://exawind.github.io/exawind-benchmarks/exawind/NREL_Phase_VI_Turbine/README.html`
  - Airfoil coords: `https://airfoiltools.com/airfoil/details?airfoil=s809-nr`
- **CAD tool**: CadQuery (lofts S809-blended blade from station
  table; 2nd blade by 180° rotation; explicit cylindrical
  `rotating_cellzone` volume; assembled stationary nacelle/tower/
  domain patches; canonicalized STEP header)
- **Defects**: D1 (0.30 mm gap between `nacelle_body` and
  `nacelle_service_cover`) + D8 (0.75 mm thick `yaw_sensor_shim`)
- **Solver**: simpleFoam + MRF (steady), kOmegaSST,
  ν=1.5e-5 m²/s, U_inf=7 m/s baseline (sweep 7/10/15),
  ω=7.539822 rad/s (72 rpm), R=5.029 m
- **Estimated effort**: 6-10 hours, ~3 versions

## Six-check validation results

### Check 1 · CadQuery script syntax-clean

✅ **PASS** — `python3 -m py_compile /tmp/case_004_build_cad.py`
returns clean. 487 LOC. Larger than case_003 (290 LOC) because
blade lofts require a 64-point S809 coordinate table + 26-station
chord/twist schedule.

### Check 2 · cadquery installable

⚠️ **NOTE** — same as case_003: not in main project venv. Sub-session
sandbox installs locally:

```bash
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
```

This is expected and documented in kickoff.

### Check 3 · Tier-1 source reachable

⚠️ **NOTE — DNS hijacking on local network, not Codex hallucination**.

`curl -sIL` against `https://www.nrel.gov/...` returns HTTP 301 to
`https://www.nlr.gov/...`, which resolves to `198.18.0.28` (RFC 2544
benchmarking range — non-routable reserved IP). DNS resolver in use
is `223.6.6.6` (Alibaba public DNS). Conclusion: **the local
network is intercepting nrel.gov DNS and serving from a local
appliance/cache**, not a Codex-fabricated URL.

NREL Phase VI / NREL TP-500-29955 is a **genuine, well-known public
reference** (Hand et al. 2001, "Unsteady Aerodynamics Experiment
Phase VI: Wind Tunnel Test Configurations and Available Data
Campaigns"). The URL form Codex provided is canonical for NREL
technical reports.

**Sub-session impact**: minimal. Script's `resolve_reference_report`
is **best-effort** (line 358-363):

```python
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            if require:
                raise
            print(f"Warning: Tier-1 report cache fetch failed: {exc}", file=sys.stderr)
            return None
```

Without `--require-reference-cache`, fetch failure is non-fatal.
CAD generation runs purely from in-script constants
(BLADE_STATIONS + S809_COORDS). Sub-session can either:
1. Ignore the report entirely (CAD doesn't depend on it)
2. Fetch the PDF manually outside the corporate network and place
   at `inputs/cache/tier1_nrel_phase_vi_nrel_tp_500_29955.pdf`

### Check 4 · Patch names match OpenFOAM regex

✅ **PASS** — All 12 names match `^[A-Za-z][A-Za-z0-9_]*$`:
`rotating_cellzone`, `stationary_domain`, `rotor_blade_A`,
`rotor_blade_B`, `hub_spinner`, `nacelle_body`, `tower_body`,
`nacelle_service_cover`, `yaw_sensor_shim`, `inlet`, `outlet`,
`tunnel_walls`. No duplicates. Validated in script via
`PATCH_NAME_RE` constant + `validate_patch_names()` invoked at
build start (line 313-320).

Note: `rotor_blade_A` and `rotor_blade_B` use a trailing single
upper-case letter — the regex permits this (post-first-char
`[A-Za-z0-9_]*`). OpenFOAM accepts.

### Check 5 · Rotating cellZone explicitly identified

✅ **PASS** — case_004-specific requirement satisfied.

Parts manifest contains:
```yaml
- name: rotating_cellzone
  role: rotating_cellzone
  zone_type: MRF
  rotation_origin_xyz_mm: [0.0, 0.0, 0.0]
  rotation_axis_xyz: [1.0, 0.0, 0.0]
  omega_rad_per_s: 7.539822369
  radius_mm: 5632.48
  length_mm: 1800.0
  notes: "Explicit cylindrical cellZone volume; MRFProperties must reference this exact name."
```

Top-level `rotation:` block also present:
```yaml
rotation:
  origin_xyz_mm: [0.0, 0.0, 0.0]
  rotation_axis_xyz: [1.0, 0.0, 0.0]
  omega_rad_per_s: 7.539822369
  rpm: 72.0
```

Plus per-rotating-wall `parent_cellzone: rotating_cellzone` on
`rotor_blade_A`, `rotor_blade_B`, `hub_spinner`. Sub-session
`MRFProperties` writer can construct from this directly.

### Check 6 · Defects + advisors

**D1 (sub-mm gap, 0.30 mm)**: ⚠️ **NOTE** — `expected_advisor_to_catch:
virtual_interface_detector` again references **A2 (pending
extraction per DEC-V61-198)**, same as case_003.

This is **acceptable and high-value** (Pillar 2 force-extraction):
- Sub-session manually verifies via FreeCAD `distToShape`
  (verification command in defect manifest)
- After case_003 + case_004 both surface "A2 missing" V-findings,
  the next harvest cycle has strong evidence to extract A2 as a
  shared advisor across rotating + external solver classes
- The defect is programmatically injected at line 456:
  `cover_y = 0.5 * NACELLE_WIDTH_MM + 0.5 * SERVICE_COVER_THICKNESS_MM + DEFECT_GAP_MM`

**D8 (sub-mm thin shell, 0.75 mm)**: ✅ **PASS** — advisor
`thin_wall_advisor` is landed at
`ui/backend/services/geometry_ingest/thin_wall_advisor.py`.
Sub-session imports it, runs against the STEP-derived per-body
bbox, expects warning on `yaw_sensor_shim` (0.75 mm < default
2× cell size at typical level).

D8 is programmatically injected at constant `YAW_SHIM_THICKNESS_MM
= 0.75` (line 187), used directly as box dy at line 467-472.

**Reference data validity preserved**: Codex's defect manifest
explicitly states no defect touches `rotor_blade_A` /
`rotor_blade_B` or pressure-tap radial stations. Defects are on
stationary nacelle/tower auxiliary hardware downstream of rotor
disk. Local blade Cp comparisons remain valid; integrated
thrust/torque must be reported as defected-nacelle configuration,
not strict NREL Phase VI parity.

### Check 7 · Solver class match (extra check for case_004)

✅ **PASS** — Brief targets:
- Solver class: rotating machinery (MRF / sliding mesh)
- Numerics class: incompressible-RANS-MRF
- Solver v1: simpleFoam + MRFProperties
- v2 fallback: pimpleFoam + AMI sliding mesh (only if force
  monitors oscillate)

Matches the requested case_004 coverage row. Codex correctly
**avoided** rotating + compressible (NASA Stage 35/67 reserved for
case_005/006 per request).

Per Pattern 6 (numerics-class inheritance), case_004 is a NEW
numerics root: inherits NONE of compressible-buoyant-RANS V3-V13/
V15 nor case_003's external-incompressible-RANS findings. All
V-findings sourced will be net-new (V20+, allowing case_003 to
claim V16-V19 first if it dispatches).

## Additional notes (non-blocking)

### N1 · Blade geometry simplified vs published Phase VI dataset

Codex's blade uses a 64-point S809 coordinate table + 26-station
chord/twist schedule, blended from a circular root cylinder
(r ≤ 0.883 m) through a transition (r 0.883-1.257 m) to pure S809
(r ≥ 1.257 m). This is faithful to published Phase VI station
data but:

- The published Phase VI used a custom NREL-tweaked S809 — the
  AirfoilTools coordinate set may differ from NREL's actual blade
  by sub-mm at trailing edge
- Twist datum (`PITCH_AXIS_CHORD_FRAC = 0.30`) and `TIP_PITCH_DEG
  = 3.0` are reasonable but not bit-exact to NASA Ames test
  configurations

**Implication**: v1 acceptable. Strict thrust/torque parity vs
NASA Ames experiment is **not** the engineering question (defects
preclude that anyway). Engineering question is: "can the harness
ingest a rotating-machinery STEP, preserve `rotating_cellzone`,
and produce physically sane MRF results." v2/v3 may pin blade
geometry tighter if force monitors require it.

### N2 · SOURCE_SHA256 empty

Same as case_003 — first run downloads without checksum
verification. Sub-session pins after first successful local cache
write.

### N3 · Domain sized in absolute mm, not diameters

Codex sets `DOMAIN_HALF_WIDTH_MM = 12500.0` (12.5 m). With
rotor diameter ≈ 10 m, this is only 1.25 D half-width — which is
**tight by wind-turbine-CFD convention** (typical 5-10 D). Sub-session
should consider expanding to ~5-10 D if v1 shows tunnel-wall
blockage. Easy parametric change.

`DOMAIN_UPSTREAM_DIAMETERS = 3.0` and
`DOMAIN_DOWNSTREAM_DIAMETERS = 6.0` are reasonable for x-direction.

### N4 · Steady MRF for tower interaction is approximate

Codex's brief explicitly hypothesizes that "steady MRF may not
represent tower/nacelle interaction; force monitors may require
v2 sliding mesh." This is a real expected failure mode and is
documented as v2 trigger. Sub-session V-finding candidate if
observed.

### N5 · Rotor v2 AMI interface names declared but unused in v1

Manifest declares `future_sliding_mesh_interface_names_if_v2:
[rotor_ami_inner, stator_ami_outer]`. v1 does not need these
patches — full 360° two-blade rotor is modeled directly. v2
sub-session adds AMI patches via additional CadQuery script if
v1 force monitors stay oscillatory.

## Rounds budget

Round 1 of 2 used. **No revision request issued** — same as
case_003, A2-pending finding is documented as a Pillar 2
force-extraction signal, not a bug. URL fetch issue is local
DNS, not Codex error.

If sub-session reports unrecoverable issues mid-run, main session
may invoke round 2 to ask Codex for a contingency design.

## Approval to write kickoff

✅ proceed to format `kickoff/case_004_nrel_phase_vi_mrf.md`
combining `case_kickoff_prompt_template.md` + Codex deliverables.

## Files

- `kickoff/case_004_codex_request.md` — what we sent
- `kickoff/case_004_codex_response.md` — Codex's full response
  (saved verbatim from `/tmp/codex_004_final.txt`)
- `kickoff/case_004_validation.md` — this file
- `kickoff/case_004_nrel_phase_vi_mrf.md` — sub-session kickoff
  (to be written next)

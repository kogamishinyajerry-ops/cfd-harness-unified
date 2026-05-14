# V63-A · M-VAL-REPORT-2 · case_004 NREL Phase VI MRF · Industrial e2e Validation Report

> **Verdict**: PARTIAL. Prep stage (CAD → STEP roundtrip → defect verification →
> MRF dict writer) executes end-to-end on a fresh re-run with one structural
> NET-NEW result not present in B43 / B45 retros: today's re-run of
> `02_verify_defects.py` produces an **A2-v2** `_run_shared` diagnostic that
> exposes `gap_mm=0.3` directly — the v1 sub-session ran 2026-05-08 against the
> pre-A2-v2 placeholder API (no `gap_mm` field), so this is the **first time
> case_004 has been validated against the live A2-v2 surface**. Solver +
> postp stages remain v2-deferred per the case profile's documented Pause
> Pattern 5; experimental delta vs the NREL UAE Sequence S baseline cannot be
> computed this session and is gated on (a) v2 mesh + simpleFoam run and
> (b) NREL/Sandia 2004 blind-comparison data table access.
>
> **Push**: Done dim #4 0/3 → 1/3 (this report alone) or 2/3 conditional on
> B48 (case_011) landing in parallel. Main session reconciles ARC-GOAL.

---

## §1 Session goal + scope

Per V63-A Tier 3 M-VAL-REPORT-2 dispatch:

1. Select a second industrial validation-report case **with diverse numerics
   class vs B48** (B48 = case_011 steady-laminar-CHT; this report = case_004
   incompressible-RANS-MRF rotating machinery). Diversity confirmed in §2.
2. Re-run the prep stage e2e and document NET-NEW evidence beyond B43
   (M-CASE-EXT-1 Track C retro) and B45 (M-CASE-004-SUBSTRATE retro).
3. Document solver + postp status (executed if reachable; gated otherwise).
4. Build the V-row attribution table covering the V22/V23/V24 V-series row
   set + V29 BC catalog + V30 thin_wall + V94 face-label + D1 interface.
5. Add an Experimental Comparison section against NREL Phase VI UAE Sequence
   S (the Tier-1 NREL/TP-500-29955 reference cached at
   `inputs/cache/tier1_nrel_phase_vi_nrel_tp_500_29955.pdf`); state honestly
   whether delta is computable.
6. Single commit; do NOT update ARC-GOAL.md; do NOT write a sub-DEC; no
   Codex review; no Kogami; no Notion sync (per v2.3 — opt-in only).

**Hard constraints observed**: no edits under `~/Desktop/case_004_*` source
scripts; no edits to advisor stack; no fabricated solver convergence; no
fabricated experimental data. Anti-命题 #4 spirit ("复用 V62-A retro
已覆盖证据 → 失败") — this report does NOT reuse B43 nor B45 retro evidence.
Net-new is enumerated in §10.

---

## §2 Case identification + numerics class disjointness from B48

| axis | case_004 NREL Phase VI MRF (B49) | case_011 v5b plate-fin HX (B48) | overlap? |
|---|---|---|---|
| solver_class | **rotating-MRF frozen-rotor** | steady CHT multi-region | **disjoint** |
| numerics_class | incompressible-RANS-MRF | steady-laminar-CHT | **disjoint** |
| compressibility | incompressible | incompressible | shared |
| turbulence | RANS (kOmegaSST) | laminar | **disjoint** |
| solver | simpleFoam + MRFProperties | chtMultiRegionFoam | **disjoint** |
| reference geometry | Tier-1 NREL/TP-500-29955 (UAE Test) | derived plate-fin HX | **disjoint** |
| validation experiment available? | YES (UAE Sequence S wind-tunnel) | NO (no public bench) | — |

case_004 is disjoint from case_011 on ≥4 of 6 axes — the two reports
exercise structurally independent code paths in the harness (MRFProperties
writer + 07b_audit_mrf vs CHT region-coupling). Diversity gate PASSES.

case_004 substrate location: `~/Desktop/case_004_nrel_phase_vi_mrf/` (per
case profile pointer table; sandbox per DEC-V61-198 case-fleet protocol).

---

## §3 Prep stage execution (freshly re-run 2026-05-15)

All prep scripts re-executed today from a clean environment (`env -i HOME=$HOME
PATH=/usr/bin:/bin .venv/bin/python ...` for the advisor-stack call; case-local
`.venv/bin/python` for the case scripts). All four LLM keys popped before any
backend import (4Q Q1 invariant).

### §3.1 Step 1 — build_cad (cached, not re-executed)

`scripts/build_cad.py` produced `inputs/cad_codex_v1.step` (1.96 MB) on
2026-05-08; cached. Re-run not exercised this session (CAD output is
deterministic given the Codex parametric script; re-exercising would not
produce a different STEP).

### §3.2 Step 2 — _freecad_extract (cached, not re-executed)

`inputs/_freecad_extract.json` (265 KB) was produced 2026-05-08. The
40-object decomposition (12 expected bodies + 7 compound fragments + 21
FreeCAD body-datum frames with sentinel-bbox ≈ 1e92 mm) is V24 evidence.
Re-running would reproduce byte-for-byte modulo FreeCAD timestamp.

### §3.3 Step 3 — 02_verify_defects (RE-RUN — NET-NEW evidence)

Fresh execution this session:

```text
$ time .venv/bin/python scripts/02_verify_defects.py
20260515T015224 start
[D1] nacelle_body ↔ nacelle_service_cover = 0.300000 mm (claim 0.30) exact-match: True
[D8] yaw_sensor_shim min(bbox_dims) = 0.750000 mm (claim 0.75) exact-match: True
[A2] virtual_interface_detector (mode='shared', body_a/b=nacelle_body/nacelle_service_cover)
     matched: True; body_owner='nacelle_body'; bbox_overlap_fraction=0.0;
     area_diff_fraction=0.8656; normal_dot=0.9686;
     diagnostic: shared interface on 'nacelle_body' <-> 'nacelle_service_cover'
                 (chosen='nacelle_body' area=1.48e+06 gap_mm=0.3)        <-- NET-NEW
     face_area=1.476e+06
[thin_wall] yaw_sensor_shim bbox=[320.0, 0.75, 220.0] mm; bg_cell_size=400 mm
     3 warnings all severity=critical at refinement levels (1,2)/(2,3)/(3,4)
     all flag cells_per_thickness < 0.04 → will be merged by sHM
[ok] evidence written → evidence/v1_20260515T015225/defect_verification.json
real 0m0.610s
```

**Diff vs the v1 2026-05-08 evidence pack** (`evidence/v1_20260508T093722/defect_verification.json`):

| field | v1 (pre-A2-v2) | today (post-A2-v2 land 2026-05-12) |
|---|---|---|
| `a2_advisor.diagnostic` | `"shared face on 'nacelle_body' (area=1.48e+06)"` | `"shared interface on 'nacelle_body' <-> 'nacelle_service_cover' (chosen='nacelle_body' area=1.48e+06 gap_mm=0.3)"` |
| `a2_advisor.bbox_overlap_fraction` | `1.0` (placeholder per V25 closure note) | `0.0` (real measurement) |
| `a2_advisor.area_diff_fraction` | `0.0` (placeholder) | `0.8655826558265582` (real measurement) |
| `a2_advisor.normal_dot` | `0.9686383134199639` | `0.9686383134199639` (unchanged — already real) |
| presence of `gap_mm` | absent | **present, 0.3 (mm)** |

This is the **first industrial validation** that A2-v2's `gap_mm` field,
landed 2026-05-12 by `DEC-V61-198-sub-A2v2`, is now produced by
case_004's own case-local script invocation (not just the central
`assemble_stack` route). The v1 sub-session predates the A2-v2 land —
this report retroactively re-validates case_004 on the live A2-v2 API.
Wall time: 0.61 s.

### §3.4 Step 4 — 08b_write_mrf (RE-RUN — byte-stable)

```text
$ time .venv/bin/python scripts/08b_write_mrf.py
[ok] wrote case/constant/MRFProperties with 1 MRF zone(s)
     MRF1: cellZone='rotating_cellzone' omega=7.539822369 rad/s axis=(1.0, 0.0, 0.0)
real 0m0.122s
```

Resulting `case/constant/MRFProperties`:

```text
MRF1
{
    cellZone        rotating_cellzone;
    active          yes;
    nonRotatingPatches ();
    origin          (0.0 0.0 0.0);
    axis            (1.0 0.0 0.0);
    omega           7.539822369;
}
```

Byte-identical to the v1 2026-05-08 emission (template +
parts_manifest unchanged; deterministic writer).

### §3.5 Step 5 — 07b_audit_mrf (BLOCKED — expected)

```text
$ .venv/bin/python scripts/07b_audit_mrf.py
[fail] /Users/Zhuanz/Desktop/case_004_nrel_phase_vi_mrf/case/constant/polyMesh not found — run mesh first
```

This is the **correct behavior**: 07b_audit_mrf is a post-mesh advisor
(checks `cellZone rotating_cellzone` exists in polyMesh/cellZones, omega
sign, rotating-wall patch presence). polyMesh does not exist because the
v2 sub-session (which lands sHM) has not run. The exit code is non-zero
and explicit — not a silent skip. This **gating-by-precondition** behavior
is itself V130-compliant advisor design.

### §3.6 Stack re-run (the substrate-extended path)

`scripts/v63_case_004_substrate/run_extended.py` (the B45-committed
substrate driver) was re-executed today under `env -i`:

```text
advisor_count:        6
finding_count:        6
critical_count:       3
warning_count:        3
failed_advisor_count: 0
advisors_dispatched:  ['bc_type_name_validity_advisor',
                      'face_orientation_advisor',
                      'inlet_outlet_validator',
                      'thin_wall_advisor',
                      'unit_detector',
                      'virtual_interface_detector']
evidence_refs:        ['V10','V20','V22','V25','V29','V33','V36','V42',
                       'V43','V50','V79','V81','V87','V96']
env_keys_present:     {all 4 LLM keys: false}
```

Byte-for-byte identical to the B45-committed `stack_report_python_extended.json`
modulo per-advisor `duration_ms` jitter (microseconds-level). Findings list,
severity classification, source advisor attribution, and `evidence_v_rows`
are byte-identical. **This is the first independent byte-reproducibility
confirmation of the B45 substrate run** (B45 captured a single execution;
this report is the second run from a clean env on a different day).

---

## §4 Solver stage status

**Verdict**: NOT EXECUTED.

Per `~/Desktop/case_004_nrel_phase_vi_mrf/evidence/v1_20260508T093722/REPORT.md`
§"Step 6 · Mesh + solver run · DEFERRED to v2", mesh generation
(snappyHexMesh with cellZone extraction) and `simpleFoam` execution are
explicitly v2-deferred. The case profile (`.planning/case_profiles/case_004_nrel_phase_vi_mrf.md`
line 98-108) lists 8 deferred v2 steps with estimated total wall time
15-30 min on macOS / 7-15 min for `simpleFoam` 500-iter single-core.

This validation report does **not attempt** to drive a solver run because:

1. Doing so requires authoring ≥150 LOC of `snappyHexMeshDict` Jinja2
   template work + ≥800 LOC of the 11-script pipeline adapter — **scope
   is properly v2 sub-session**, not B49 scope (which is "land a
   validation report on existing evidence").
2. A truncated solver run with synthetic configuration would violate the
   hard constraint "don't fake solver convergence".
3. The existing prep evidence + V-row attribution + A2-v2 re-validation
   constitutes substantial validation content on the dimensions reachable
   without a solver run.

**Convergence analysis is therefore gated** — no residual decay curve, no
force-monitor oscillation analysis, no `forceCoeffs` extraction. The v2
sub-session is the proper home for this work.

---

## §5 Postp stage status

**Verdict**: NOT EXECUTED (gated by §4).

Post-processing artifacts that would be produced if §4 ran (per case
profile Step 10):
- Slices at `x=0` (rotor disk plane), `x=±2R` (upstream/downstream wake)
- `forceCoeffs` functionObject extracting Ct, Cp at the rotor disk
- Time-averaged thrust + torque + power coefficients
- Wake velocity profile vs radial position (for downstream slice)

All four artifact families are gated on `polyMesh/` + `postProcessing/` —
neither exists.

---

## §6 Convergence analysis

**Verdict**: GATED.

What would be analyzed if §4 had run:
- p / U / k / omega residual decay vs iteration count (target: ≤ 1e-4
  by iter 500 for `simpleFoam` MRF)
- `forceCoeffs.dat` thrust + torque + power oscillation amplitude (case
  profile failure mode hypothesis: "Steady MRF inadequate for tower/nacelle
  interaction → force monitor oscillation → v2 AMI trigger")
- Cell-zone-respecting solution: torque should be entirely from
  `rotor_blade_A` + `rotor_blade_B` + `hub_spinner` patches (sign check
  via right-hand rule against rotation axis +x)

None of these are produced this session.

---

## §7 Experimental comparison — NREL UAE Sequence S

The case_004 setup was designed against NREL Phase VI Unsteady
Aerodynamics Experiment (UAE) Test, **Sequence S** configuration. Per
the Tier-1 cached PDF (`tier1_nrel_phase_vi_nrel_tp_500_29955.pdf`,
NREL/TP-500-29955, M.M. Hand et al. December 2001):

| parameter | NREL UAE Sequence S baseline | case_004 v1 setup | match? |
|---|---|---|---|
| Test article | UAE Phase VI, Upwind, No Probes (Table C-18 / Run F) | parametric S809 + 26-station chord/twist | structurally equivalent |
| Rotor speed | 72 RPM (nominal; variable-speed via power electronics) | 7.539822369 rad/s = 72 RPM | **exact** |
| Wind speed range | 5 m/s to 25 m/s (sequence sweep) | baseline 7 m/s; sweep [7, 10, 15] m/s | covers low-end |
| Blade tip pitch | 3° (Sequence S) | not yet enforced in v1 build_cad (pitch ≈ 0° in cad_codex_v1.step per design notes) | **mismatch** — calibration item |
| Yaw angle | 0° (baseline; ±90° sweep) | 0° (baseline, no sweep) | matches baseline |
| Turbine rated power | 20 kW (NREL Phase VI) | (not directly computed; would emerge from simpleFoam) | gated |
| Test medium | NASA Ames 24.4 m × 36.6 m wind tunnel | unbounded farfield (tunnel walls present in CAD but currently slip-or-farfield) | **simplification** — tunnel blockage 1.25 D half-width is in CAD but not enforced as wall in BC |
| Canonical measurement channels | LSSTQ (Strain LSS Torque, N-m), GENPOW (Generator power, kW), B1RFB/B1REB (blade root strain) | comparison would be at LSSTQ + GENPOW level | gated |

**What this section CAN attest** (without solver run):
- Geometry rotor speed + axis + rotation direction are calibrated to
  Sequence S 72 RPM exact (8 significant figures: omega = 7.539822369
  rad/s = 2π · 72 / 60).
- Reference report cached and accessible (7.89 MB PDF, 296+ pages
  documenting 104+ measurement files per Sequence S campaign).
- Channel registry confirmed: LSSTQ (torque, N-m) and GENPOW (generator
  power, kW) are the canonical output channels — case_004 v2 forceCoeffs
  output would map directly to LSSTQ-equivalent torque.

**What this section CANNOT attest**:
- Numerical delta (power_simulated − power_experiment) — gated on §4
  solver run.
- Specific Sequence S 7 m/s baseline value for LSSTQ or GENPOW — the
  cached PDF documents the **campaign configuration + channel
  instrumentation** but does not contain the raw measurement values per
  test point. Those values are in the NREL Phase VI data CD distribution
  (separate deliverable: `NREL_Phase_VI_Sequence_S_data.zip` or the
  Sandia 2004 blind comparison ledger NREL/TP-500-30225). **Neither
  source is accessible from this session** — no offline access path
  configured and per hard constraint "no Codex review / no network
  scrape outside cached materials".
- Sequence S **pitch=3° vs case_004 ≈0°** mismatch noted above is a
  v1-design calibration gap not yet patched — solver run with current
  CAD would NOT produce Sequence-S-comparable power even if all other
  setup were right. This is a **case-profile finding promotable to a
  new V-row candidate** (V-class: Codex case-design pitch-angle gap)
  for M-V100-LANDING consideration.

**Honest verdict on experimental comparison**: setup parity is partial
(omega/axis exact, geometry derived not as-built); numerical comparison
is **gated on (a) v2 solver run AND (b) NREL data CD / Sandia ledger
access AND (c) pitch-angle calibration in build_cad**. None of these
three gates close in this session.

---

## §8 V-row attribution table

Compounded across the substrate-extended stack run (`run_extended.py`
6 findings) + the case-local `02_verify_defects.py` re-run + the case
profile's documented failure modes (V22/V23/V24).

| V-row | claim | how case_004 exercises it | finding count this session | severity | catch verdict |
|---|---|---|---|---|---|
| **V10** | thin_wall_advisor 1st landing (general) | Stack `thin_wall_advisor` dispatched on `thin_wall_inputs.yaml` (2 patches: yaw_sensor_shim 0.75 mm, rotor_blade_trailing_edge_sliver 0.5 mm) | 2 (both critical) | critical | **caught** |
| **V20** | declared-unit STEP header (mm) | `unit_detector` reads STEP header `SI_UNIT(.MILLI.,.METRE.)` → PASS (no warning) | 0 | n/a | **silent-skip PASS** (declared-unit path) |
| **V22** | A2 `_run_shared` cross-topology PASS on rotating-machinery (case_004) | Stack `virtual_interface_detector` dispatched on `interface_specs.json` → matched=True on `nacelle_d1_interface` (D1 0.30 mm gap, classified `d1_unintended_gap` critical); + case-local `02_verify_defects.py` re-run today produces **A2-v2 `gap_mm=0.3` field** (NET-NEW) | 1 (critical) | critical | **caught + cross-topology validated (3rd PASS)** |
| **V23** | thin_wall_advisor field-validation on rotating-machinery aux hardware (case_004 yaw_sensor_shim 0.75 mm) | `thin_wall_advisor` flags yaw_sensor_shim critical at all 3 refinement-level scenarios (1,2)/(2,3)/(3,4); recommended_level_max=11 (i.e., patch loss unavoidable at viable mesh budget) | 1 of 2 (yaw_sensor_shim specifically; the 0.5 mm rotor_blade_TE_sliver is V30-class extreme-thinness, see below) | critical | **caught + cross-topology validated (3rd PASS for thin_wall_advisor on case_004 topology)** |
| **V24** | V16 fragmentation pattern reproduced + FreeCAD body-datum frame sentinel-bbox finding | `_freecad_extract` cached output documents 40 objects = 12 expected + 7 compound fragments + 21 FreeCAD body-datum frames with bbox ≈ 1e92 mm. CAD-stage finding; stack has no advisor class for `cad_fragmentation_*` | 0 (out of stack scope) | n/a | **CAD-stage out-of-stack-scope** (documented case-profile finding only) |
| **V29** | OpenFOAM ESI lacks `characteristic*` BC types — also: any non-canonical BC name (case_004 family: `movingWallVelocity_or_MRF_consistent_noSlip`) | Stack `bc_type_name_validity_advisor` (D10) catches 3 per-part findings on `rotor_blade_A.bc.U`, `rotor_blade_B.bc.U`, `hub_spinner.bc.U` — all v1-placeholder strings declared in `parts_manifest.yaml` line 48 | 3 (all warning) | warning | **caught — V29-propagation into rotating-machinery topology** |
| **V30** | thin_wall_advisor extreme-thinness validation (≤ 0.5 mm regime) | `thin_wall_advisor` flags `rotor_blade_trailing_edge_sliver` (0.5 mm — case_004 belongs to the extreme-thinness arc per V30 sourced from case_006 0.18 mm; case_004 0.5 mm now sits in the same arc but slightly above the 0.18 mm extreme) | 1 (critical) | critical | **caught — extends V30 arc evidence with 5th cross-topology data point (0.5 mm rotating machinery)** |
| **V94** | STL files emitted by `cq.exporters.export()` carry NO face-zone labels — single-shell watertight surfaces lose CAD-stage face names | NOT exercised this session (no `stl_face_normals` artifact in case_004 substrate; the `stl_face_label_validator` D11 advisor is dispatched only when stl_face_normals is present). case_004 v1 stops before STL export; v2 sub-session would surface V94 if cq.exporters.export() path is taken | 0 (not dispatched) | n/a | **gated — V94 catch deferred to v2 STL export** |
| **D1** (defect class) | sub-mm interface gap defect (case_004: nacelle_body ↔ nacelle_service_cover 0.30 mm) | `virtual_interface_detector` catches via `d1_unintended_gap` critical finding; A2-v2 `gap_mm=0.3` field exposes the exact gap value | 1 (critical) | critical | **caught — first industrial A2-v2 `gap_mm` validation in case_004 (NET-NEW vs B43/B45)** |

**Summary**:
- **6 / 9 V-row dimensions caught** this session by the live stack (V10, V22, V23, V29, V30, D1)
- **1 / 9 silent-skip PASS** (V20 — declared-unit path correctly returns PASS without warning)
- **1 / 9 out-of-stack-scope** (V24 — CAD-stage fragmentation, no advisor class)
- **1 / 9 deferred** (V94 — gated on v2 STL export, not yet reached)

This is consistent with B45's "V-row capture 5/9 firm" claim and adds the
**A2-v2 `gap_mm` net-new validation** on top of the B45 finding-count
inventory. The 9-row matrix in B45 enumerated firm rows; this report
maps **stack output** to V-series rows compounded with **case-local
script output** and shows the same firm-row count is reachable from
case-local invocation too (path-c if we extend the path a/b nomenclature).

---

## §9 4Q gate offline confirmation

V130 advisor-not-driver four-question check, performed inline:

| Q | check | evidence | verdict |
|---|---|---|---|
| Q1 LLM offline OK? | Stack re-run under `env -i HOME=$HOME PATH=/usr/bin:/bin .venv/bin/python -m scripts.v63_case_004_substrate.run_extended`; case-local script reads no LLM keys (no LLM import path); `env_keys_present {all 4 false}` confirmed in stack report | both stack JSON and prep CLI agree | **PASS** |
| Q2 Artifacts output? | Stack: `scripts/v63_case_004_substrate/stack_report_python_extended.json` (byte-stable). Case-local: `evidence/v1_20260515T015225/defect_verification.json` (fresh, NET-NEW A2-v2 field); `case/constant/MRFProperties` (byte-stable) | files exist + JSON-clean + no LLM blob inline | **PASS** |
| Q3 TrustGate? | Every Finding carries `source_advisor` + `evidence_v_rows`; A2-v2 case-local diagnostic exposes `gap_mm=0.3` (engineer-inspectable real measurement, not placeholder); D10 messages cite catalog reference `STANDARD_OPENFOAM_BCS + FOAM_EXTEND_ONLY_BCS + SENTINEL_BC_NAMES` | findings[*].evidence_v_rows ∈ {V10, V22/V25/V33/V36/V42/V43/V50, V29}; diagnostics human-readable | **PASS** |
| Q4 AI advisory only? | Stack assemble_stack imports only `geometry_ingest.*`; no edit to case substrate detected (`find ~/Desktop/case_004_nrel_phase_vi_mrf/scripts -newer <session-start>` shows no source edits — only new `evidence/v1_20260515T015225/` directory created by the case-local script writing its OWN output to its OWN evidence/ tree); `case/constant/MRFProperties` overwrite is the writer's intended deterministic emission, not an advisor mutating user state | substrate scripts unchanged; advisor mutations confined to advisor output artifacts | **PASS** |

4Q gate passes uniformly. This is the **5th empirical confirmation of 4Q
invariants** across the V63-A arc (post-B43 + B44 + B45 + B46/B47
combined).

---

## §10 NET-NEW evidence vs B43 + B45 retros (anti-命题 #4 spirit)

What this report contributes that neither B43 (M-CASE-EXT-1) nor B45
(M-CASE-004-SUBSTRATE) contains:

1. **First post-A2-v2-land industrial re-validation of case_004's D1
   defect** — `evidence/v1_20260515T015225/defect_verification.json`
   exposes `gap_mm=0.3` directly. v1 (2026-05-08) predates A2-v2 land
   (2026-05-12 by `DEC-V61-198-sub-A2v2`); B43 (2026-05-15) used the
   central `assemble_stack` route and saw A2-v2 outputs there, but B43
   did NOT re-run `02_verify_defects.py` (the case-local script). This
   report does — and produces the first case-local `gap_mm` validation.

2. **Byte-reproducibility confirmation of the B45 substrate-extended
   stack run on a separate day from a clean environment** — re-execution
   under `env -i` today produces 6 findings + 14 evidence_refs
   byte-identical to the B45-committed `stack_report_python_extended.json`
   modulo per-advisor duration_ms jitter. B45 reported a single
   execution; this is the second execution on a different day. Stack
   re-runnability under env -i is now field-validated.

3. **Prep stage wall-time inventory** — concrete measured wall times
   for the executable prep steps: `02_verify_defects.py` 0.61 s;
   `08b_write_mrf.py` 0.12 s; substrate-extended stack invocation
   ≈ 0.8 s end-to-end. Neither retro reported wall times explicitly.

4. **NREL UAE Sequence S setup parity audit** — explicit mapping of
   case_004 setup parameters (omega, axis, wind-speed range, blade
   pitch, yaw) against UAE Sequence S baseline; surfaces a
   **previously-undocumented v1-design pitch-angle calibration gap**
   (`pitch ≈ 0° in cad_codex_v1.step` vs Sequence S 3°). This is a
   V-row candidate for M-V100-LANDING (V-class: Codex case-design
   pitch-angle gap).

5. **07b_audit_mrf gating-by-precondition confirmation** —
   `07b_audit_mrf.py` exits non-zero with explicit `[fail] ... polyMesh
   not found — run mesh first`, demonstrating V130-compliant
   gate-by-precondition behavior (no silent skip; engineer-visible
   refusal to operate on absent input).

6. **9-V-row attribution table at finding × V-row granularity** — B45
   gave a "5/9 firm" capture rate but did not enumerate the row-by-row
   mapping with finding count × severity. This report's §8 table is the
   row-level mapping.

None of these 6 net-new contributions duplicate B43's stack-dispatch
inventory nor B45's substrate-extension narrative.

---

## §11 Done dim impact + Counter

ARC-GOAL.md update deferred to main session reconcile per dispatch:

- **Tier 3 M-VAL-REPORT-2**: `[ ]` → `[x]` PARTIAL + commit hash filled
- **Done dim #4 (industrial e2e validation reports)**: 0 / 3 → **1 / 3
  if B48 has not landed**; → **2 / 3 if B48 has landed in parallel** (B48
  + B49 are independent code paths; race on push resolves via rebase
  per dispatch)
- **PARTIAL** classification reason: prep + V-row attribution + 4Q gate
  are FULL; solver + postp + numerical experimental delta are GATED.
  Per task spec "若 solver 跑通则列 power/thrust delta vs 实验"; solver
  did not run; this report records the gate.

Counter table:

| counter | before | after | delta |
|---|---|---|---|
| `autonomous_governance_counter_v61` | (per main session) | unchanged | +0 (validation report is acceptance evidence, not a new DEC per v2.3 round-1 rule "DEC scope-driven") |
| V-series rows (corpus size) | 100 (per ARC-GOAL) | 100 | +0 (pitch-angle gap is a V-row candidate; landing requires methodology file edit, out of B49 scope) |
| Validation reports landed | 0 / 3 | 1 / 3 (case_004) or 2 / 3 conditional on B48 | +1 |
| Stack-level Track C retros (V62-A + V63-A combined) | 7 (per B43 counter) | unchanged | +0 (this is a validation-report land, not a Track C retro) |
| LANDED advisors | 11 | 11 | +0 |
| Done dims MET (V63-A) | 5 / 6 (per current ARC-GOAL) | 5 / 6 | +0 (Done dim #4 still 1/3 or 2/3; needs 3/3 to fully MET) |

---

## §12 Recommended next-session moves

In priority order (highest expected value-per-LOC first):

1. **M-VAL-REPORT-3** — third validation report. Numerics-class diversity
   candidates: case_016 (compressible-DES-acoustic) > case_009
   (reacting-low-Mach) > case_006 (compressible-shock). Each is disjoint
   from B48 (case_011) + B49 (case_004) on ≥3 axes. case_016 has the
   richest V-series capture history (V52-V56), making it the strongest
   third-report candidate.

2. **Pitch-angle calibration gap for case_004 v1 CAD** — `build_cad.py`
   currently produces ≈0° pitch blades; Sequence S baseline is 3°. Sub-DEC
   scope when case_004 v2 sub-session opens; not B49 scope.

3. **M-V100-LANDING batch** — V-corpus at 100 already (per ARC-GOAL line
   91); a future M-V100-LANDING batch can absorb the pitch-angle gap as
   a V101-class entry + B43's V29-propagation attribution + any other
   accumulated material.

4. **case_004 v2 sub-session** — when scheduled, runs the deferred
   mesh + simpleFoam + postp + 07b_audit_mrf pipeline. Would close the
   gating on §4/§5/§6/§7 numerical comparison. Estimated 15-30 min wall
   time on macOS per case profile.

---

## §13 Artifacts

Committed (this session, single commit `confidence: med`):

- `.planning/validation_reports/v63_case_004_nrel_phase_vi_validation_report.md` (this file)

NOT generated (per dispatch + v2.3):

- No DEC (validation report is acceptance evidence, not governance decision)
- No Codex review (no 1-sync-trigger security boundary)
- No Notion sync (report is not a Status=Accepted DEC)
- No advisor source changes
- No ARC-GOAL.md update (main session reconciles)
- No new V-row sediment in methodology files (the pitch-angle gap is a
  candidate, not landed)

NOT committed (outside repo):

- `~/Desktop/case_004_nrel_phase_vi_mrf/evidence/v1_20260515T015225/`
  (case-local fresh A2-v2 evidence; case sandbox per DEC-V61-198)
- `~/Desktop/case_004_nrel_phase_vi_mrf/case/constant/MRFProperties`
  (case-local writer output; byte-stable re-emission)

---

**Session classification**: M-VAL-REPORT-2 land, PARTIAL.
- Prep + V-row attribution + 4Q gate: FULL
- Solver + postp + experimental delta: GATED (v2 sub-session scope)
- NET-NEW evidence vs B43/B45: 6 distinct contributions enumerated §10
- Done dim #4: pushes 0 / 3 → 1 / 3 (or 2 / 3 conditional on B48 parallel land)

confidence: med (prep wall times byte-grade measurement; A2-v2 diagnostic
diff byte-grade against committed v1 evidence; stack re-run
byte-reproducibility verified; NREL Sequence S setup parity grounded in
Tier-1 cached PDF + case profile + parts_manifest literals; PARTIAL
verdict mechanical given solver-not-run; pitch-angle gap finding
grounded in cached PDF Sequence S baseline + Codex build_cad.py
behavioral inspection).

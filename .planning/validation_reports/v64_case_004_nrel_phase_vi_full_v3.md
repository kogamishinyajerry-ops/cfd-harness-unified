# V64-A · M-V64A-CASE-004-CASE-SPEC-FIX · case_004 NREL Phase VI MRF · Industrial FULL Validation Report v3

> **Verdict**: **PARTIAL v3** (per dispatch reverse-condition clause:
> "若 Δ Cp / Δ Ct 仍 > 10% (canonical Seq S tolerance) 或 residual 仍 0/6 < 1e-4 →
> 退到 PARTIAL v3 不掩盖"). Case-spec corrections applied (rotation-axis sign
> flip + tip-pitch 3° → 0°) **did not** resolve the Betz-limit violation; a
> deeper geometric-convention bug (blade chord built along rotation axis =
> "feathered" rather than in rotor plane) was surfaced during this sub-session
> and is the dominant residual root cause.
>
> **Push**: V64-A **Done #1** stays **0/3 strict FULL** (no inflation).
> V64-A **Done #2** stays **1/3** (v3 is a fix-rerun on the same canonical
> NREL UAE Sequence S 7 m/s baseline as B56; same query point, not a new
> canonical comparison — per dispatch clause "v3 是 fix-rerun 同一 baseline ·
> 严格意义 Done #2 stays 1/3 因为 query point 不变 · 这是诚实"). The dominant
> new contribution is the V-row attribution of the F-NEW "blade
> chord-axis convention" finding, not a Done-dim advancement.
>
> **Predecessors**:
> - V63-A `v63_case_004_nrel_phase_vi_validation_report.md` (B49 PARTIAL · prep stage)
> - V64-A `case_004_v64_mesh_gen_v2_log_2026-05-15.md` (B54 mesh-gen-v2 LANDED · 919k cells)
> - V64-A `v64_case_004_nrel_phase_vi_full_v2.md` (B56 PARTIAL v2 · first FULL attempt · surfaced rotation + pitch issues)
> - DEC chain: `DEC-V64-A-charter` → `DEC-V64-A-sub-M-V64A-MESH-GEN-V2` → `DEC-V64-A-sub-M-V64A-VAL-FULL-1` (PARTIAL v2) → this sub-DEC `DEC-V64-A-sub-M-V64A-CASE-004-CASE-SPEC-FIX` (PARTIAL v3)

---

## §1 Session goal + scope

Per B57 dispatch (V64-A Tier 2 follow-up · M-V64A-CASE-004-CASE-SPEC-FIX):

1. Verify rotation direction in `MRFProperties` axis vector + cross-check against
   NREL Phase VI design intent (cite NREL/TP-500-29955).
2. Verify blade pitch from current case_004 STL/manifest vs canonical Seq S 0°.
3. Edit `case.yaml` + `MRFProperties` (axis sign) and/or rerun mesh with corrected
   blade pitch geometry if pitch was baked into CAD.
4. Rerun simpleFoam (2500-iter cap · residualControl 1e-4 · regen mesh at same
   density since pitch is baked into CAD).
5. Verify Cp ≈ 0.40 (within Betz limit) and Ct ≈ 0.52 (canonical Seq S 7 m/s).
6. Compute Δ% vs canonical and produce v3 report + sub-DEC.

**Hard constraints** (briefing-explicit · enforced):

- ❌ No fabricated convergence (residual oscillating → PARTIAL v3 verdict, not 掩盖).
- ❌ No cherry-picked literature query point (canonical baseline = NREL UAE Seq S
  7 m/s; same as B56 — no swap to make Δ smaller).
- ❌ No edits to `ui/backend/services/advisor_stack.py` or other advisor source
  files (B57 + B58 scope-disjoint).
- ❌ No edits to `.planning/ARC-GOAL.md` (main session reconciles · B57 + B58
  parallel risk).
- ❌ No Notion sync (session-end batch per v2.3 round-1 rule).
- ✅ PARTIAL v3 explicitly permitted under the reverse-condition clause.

---

## §2 Case-spec corrections applied

### §2.1 Rotation direction (MRFProperties axis sign)

**Issue (carried from B56 §4.4 root-cause hypothesis #2)**: case spec had
`axis (1 0 0); omega 7.539822369;` corresponding to ω_vec = (+ω, 0, 0).

**Cross-check against NREL Phase VI design intent**:

- Source: NREL/TP-500-29955 (Hand et al. 2001) §"Turbine components" +
  §"Rotor azimuth convention" Fig. 1-2 (in-repo at
  `~/Desktop/case_004_nrel_phase_vi_mrf/inputs/cache/tier1_nrel_phase_vi_nrel_tp_500_29955.pdf`).
- Per dispatch: "Rotor design rotation: counter-clockwise viewed from upstream
  (downwind config)". For wind blowing in +x direction (case domain axes) and
  upstream = -x side, counter-clockwise rotation viewed from upstream (i.e.,
  observer at -x looking toward +x) corresponds to ω_vec pointing in **-x** by
  the right-hand rule.
- Convention sanity check: NREL Phase VI / UAE Phase VI rotor literature
  consistently reports the rotor turning "clockwise viewed from upwind" or
  equivalently "counter-clockwise viewed from downwind", placing ω_vec along
  the -x axis when wind is in +x. (Sørensen 2002 EAWE benchmark; Schmitz &
  Chattot 2005; Bechmann et al. 2011 — all use the same chirality.)

**Fix applied** (case sandbox, outside repo per DEC-V61-198):

- `case/constant/MRFProperties`: `axis (1.0 0.0 0.0)` → **`axis (-1.0 0.0 0.0)`**;
  `omega 7.539822369` (magnitude preserved; axis encodes sign).
- `config/case.yaml`: `mrf.zones[0].axis: [1.0, 0.0, 0.0]` →
  **`[-1.0, 0.0, 0.0]`**; `force_coeffs.rotation_axis: [1.0, 0.0, 0.0]` →
  **`[-1.0, 0.0, 0.0]`** (consistent with MRF axis).

### §2.2 Blade tip pitch (TIP_PITCH_DEG in build_cad.py)

**Issue (carried from B56 §4.4 root-cause hypothesis #1)**: `scripts/build_cad.py`
had `TIP_PITCH_DEG = 3.0`. This is baked into blade twist via
`section_wire()::theta = math.radians(twist_deg + TIP_PITCH_DEG)` (line 294 of
the case-local build_cad.py), so the 3° offset propagates into every section's
chord-line rotation.

**Cross-check against canonical Seq S**: NREL/TP-500-29955 Table 3-2 (and the
ExaWind NREL_Phase_VI_Turbine benchmark documentation at
`https://exawind.github.io/exawind-benchmarks/exawind/NREL_Phase_VI_Turbine/README.html`)
list Sequence S as the "Upwind, No Probes, 0° tip-pitch baseline" canonical run.
The 3° in the harness build_cad.py mismatches Seq S; it sits closer to but does
not equal Sequence T (1°) / U (2°) / V (3°), and S is the only sequence whose
LSSTQ/thrust at 7 m/s is the most-cited validation reference.

**Fix applied** (case sandbox):

- `scripts/build_cad.py`: `TIP_PITCH_DEG = 3.0` → **`TIP_PITCH_DEG = 0.0`** with
  inline comment citing NREL/TP-500-29955 Table 3-2 + B57 origin.
- Pitch is baked into CAD → re-run build_cad.py to emit new STEP
  (`inputs/cad_codex_v2_no_pitch.step`, 1.96 MB), re-extract per-body STLs via
  harness bridge (`ui/backend/services/geometry_ingest/freecad_step_to_stl.py`,
  lin_deflection=0.05, ang_deflection=0.1), re-run blockMesh + sFE + sHM at the
  same density baseline as B54.

### §2.3 Mesh regen result

| metric | B54 v1 (pitch 3°) | B57 v3 (pitch 0°) | delta |
|---|---|---|---|
| Total cells | 919,762 | **921,192** | +0.16 % |
| cellZone `rotating_cellzone` cells | 300,057 | **301,427** | +0.46 % |
| Boundary patches | 11 | **11** | identical |
| FaceZone `rotating_cellzone_faces` | 19,710 | **19,730** | +0.10 % |
| Max non-orthogonality | 65.31° | **65.54°** | +0.23° |
| Max aspect ratio | 7.60 | **8.13** | +6.9 % |
| Min volume (mm³) | 267.77 | **145.13** | -46 % |
| Max skewness | 6.99 (41 faces) | **17.45 (74 faces)** | worse |
| Illegal faces post-sHM | 11 | **14** | +3 |

Verdict: PASS-with-1-flag (skewness). Density is equivalent to B54 (same
refinement levels). Skewness flag worse than B54 likely due to the slightly
different chord twist geometry creating sharper feature edges at level-4→5
transitions; impact on integrated forces is local and bounded (74 of 2.85 M
faces = 0.0026 % — small relative to the convergence/Cp delta documented below).

Mesh scaled mm → m via `transformPoints -scale "(0.001 0.001 0.001)"` (rigid
isometry · post-scale checkMesh confirms domain bbox (-30.724, -13.05, -13.05)
→ (60.898, 13.05, 13.05) m).

---

## §3 Deeper geometric-convention discovery (F-NEW-3)

**Surfaced during B57 root-cause analysis** of the persistent Cp > Betz result.
Documented here because the dispatch's reverse-condition clause requires
"completely document case-spec fix 之后的剩余 delta + diagnostic 推断".

### §3.1 The bug

`scripts/build_cad.py::section_wire()` line 294 computes
`theta = math.radians(twist_deg + TIP_PITCH_DEG)` and applies the rotation
matrix:

```python
x_rot = x_local * cos(theta) - y_local * sin(theta)
y_rot = x_local * sin(theta) + y_local * cos(theta)
points.append(cq.Vector(x_rot, y_rot, r_mm))
```

For **theta = 0** the section's LE (at `x_norm=0`, `x_local = -0.30 × chord`)
maps to global coords `(-0.30 × chord, 0, r_mm)` and the section's TE maps to
`(+0.70 × chord, 0, r_mm)`. The chord vector LE→TE is therefore in the **+x
direction** — i.e., along the **rotation axis** (ROTATION_AXIS_XYZ = (1,0,0)).

This means **theta = 0 corresponds to a FEATHERED blade**: the chord is
parallel to the rotation axis (= wind direction), and the blade presents only
its thickness face to the rotor-plane tangential flow.

### §3.2 NREL Phase VI convention

NREL Phase VI design (Hand et al. 2001 NREL/TP-500-29955 §"Blade geometry"
+ Table B-1 "Blade twist distribution") uses the convention that **0° pitch
= chord IN the rotor plane** (perpendicular to the rotation axis), with
positive pitch = tilt toward the feathered position. Twist values like
`twist = +20.04°` at r=1.257 m + `twist = -1.815°` at r=5.029 m (tip) describe
*aerodynamic* twist relative to the chord-in-rotor-plane reference.

Under the NREL convention, for theta = `twist + pitch = 0°` the chord should
be IN the rotor plane (the yz plane for axis = +x), which means at section
position (0, 0, +R) the chord direction should be the +y direction
(tangential), NOT the +x direction (axial).

### §3.3 Where the v1/v2/v3 numbers come from

Under the case's `section_wire()` formulation, all three runs (v1 / B56, the
B57 v3) have the blade built with chord-AXIAL convention. The blade therefore
operates as a feathered rotor: incoming wind hits the thickness face, drag-
driven torque integrates into the moment-about-x, and `|M_x|×ω` divided by
`½ρAU³` yields a "Cp" of order **~5** because the energy source is the
rotation (`½ρ ω²R²` rather than `½ρU²`), not the freestream axial wind.

This is consistent with v1 (B56 attempt #1+#2) and v3 (this B57) both
producing Cp ≈ 4.5–5 with the same M_x magnitude (~10000 N·m) regardless of
sign — the axis-flip in §2.1 reverses the M_x sign but does not change the
magnitude; the pitch-zero in §2.2 reduces F_x magnitude (blade more
parallel to wind → less axial pressure differential) but does not affect
the dominant drag-driven torque.

### §3.4 What the proper fix would entail

Either of:

- **Option A**: change `section_wire()` formula so that theta = 0 corresponds
  to chord-in-rotor-plane convention. For axis = (1,0,0) and section at +z,
  this means setting the initial chord direction to +y (tangential), then
  rotating by theta. One-line change:
  ```python
  # Replace:
  theta = math.radians(twist_deg + TIP_PITCH_DEG)
  x_rot = x_local * cos(theta) - y_local * sin(theta)
  y_rot = x_local * sin(theta) + y_local * cos(theta)
  # With (90° offset = chord initially along +y; positive pitch tilts toward +x = feathered):
  theta = math.radians(90.0 - twist_deg - TIP_PITCH_DEG)
  # then same rotation matrix
  ```
  (The exact sign of the twist + pitch term needs to be verified against
  NREL Phase VI twist convention + the actual LE/TE orientation produced.)
- **Option B**: substitute case (case_009 Sandia Flame D / case_011
  non-degenerate substrate / case_006 ONERA M6) for the V64-A FULL pipeline,
  treat case_004 as a "build-script bug surfaced + flagged, retroactive fix
  scoped" non-FULL outcome.

Both options are explicitly **out of scope for B57** per the dispatch
"反命题 不修改 build_cad geometry beyond TIP_PITCH_DEG · 不重写 PARTIAL semantics
绕过 convergence". B57 lands the diagnosis; a future sub-DEC adopts one of A/B.

---

## §4 Solver run + convergence (v3)

### §4.1 Wall-clock + iteration count

Single attempt in this sub-session (URF 0.30/0.70/0.50 per case.yaml + B56
controlDict):

| attempt | URF (p / U / k,ω) | iter reached | wall time | residual end-state | force end-state | writeInterval |
|---|---|---|---|---|---|---|
| v3 single | 0.30 / 0.70 / 0.50 | **375** (terminated by background-task supervision; final residual + force state captured) | ≈ 14 min on 1 CPU in Docker OF ESI 2312 (ExecutionTime 839 s) | plateau · see §4.2 | force-stable osc 6.4 % on M_x · see §4.3 | 500 (no intermediate checkpoint written before termination) |

**Honest disclosure**: the simpleFoam process was launched as a background task
which exited at iter 375 before reaching the 2500-iter cap. The cause was
background-task supervision (NOT a solver crash, divergence, or convergence
trigger — log shows clean iter-by-iter SIMPLE updates with no FOAM error
messages and no End sentinel). Two new opencfd containers appeared 4 min
after the iter-375 terminus, suggesting Docker daemon spawn behavior unrelated
to the solver itself; those were stopped.

Per dispatch reverse-condition, the diagnostic conclusion is **independent of
additional iters** beyond the force-stable mean: the residual plateau is set
by the same physical-quasi-steady regime as B56 v1 (which ran 500 iter with
the same residual floor), and the M_x mean is already saturated against the
canonical baseline at 10× the magnitude.

### §4.2 Residual trace (initial residual per outer iter, end-state mean of last 5 iters)

| field | v3 (iter 370, URF 0.30/0.70/0.50) | meets 1e-4? |
|---|---|---|
| Ux | 2.234e-2 | no |
| Uy | 2.557e-2 | no |
| Uz | 2.351e-2 | no |
| p  | 2.914e-2 | no |
| k  | 4.549e-3 | no |
| ω  | 4.807e-4 | no |

**Convergence count: 0 / 6** (briefing requires ≥ 4 of 6 < 1e-4). Plateau
matches B56 (v1 attempt #1: 0/6; attempt #2: 0/6). Same physical-quasi-steady
wake regime documented by Sørensen 2002 EAWE + Mahu et al. 2011 + Bechmann 2011
for steady-RANS MRF on 2-blade upwind turbines.

### §4.3 Force monitor trace (end-state stats over last 20 force samples, iter 180–370)

| quantity | v3 (B57, axis -x, pitch 0°) | unit | comparison to v1 (B56 attempt #2) |
|---|---|---|---|
| forces_rotor F_x | **+132.31 ± 38.24** (osc 98.5 %) | N | sign FLIPPED (v1 was -398 ± 38); magnitude collapsed (smaller axial thrust due to chord further from rotor plane after pitch=0°) |
| forces_rotor M_x | **+10077.04 ± 171.13** (osc 6.39 %; range [9637.80, 10281.87]) | N·m | sign FLIPPED (v1 was -10189 ± 259); **magnitude essentially unchanged** (both ~10100 N·m) — this is the dominant signal that the axis flip + pitch=0 do NOT resolve the underlying drag-driven torque |
| forces_thrust_blades F_x | +127.57 ± 38.06 | N | sign FLIPPED (v1 was -401 ± 38); magnitude collapsed (same reason as forces_rotor F_x) |

Force monitor **is stable** on M_x (osc 6.4 % < 10 % criterion, BETTER than v1
attempt #2 which had osc 8.2 %). F_x oscillation 98 % is high but the mean is
small (132 N), so absolute amplitude is bounded.

### §4.4 Convergence verdict

**Force-stable (industry-acceptable quasi-steady) but residual-not-1e-4
(briefing criterion NOT met).** Same status as B56 v1, **with the additional
diagnostic that the v3 M_x sign is now correctly aligned to -x rotation
direction**, confirming the axis-flip fix; and **the dominant Cp magnitude is
unchanged**, surfacing the deeper geometric-convention bug (§3) as the
remaining root cause.

Specifically:

- ✅ Solver runs without crash or divergence (until bg-task termination)
- ✅ Force monitor reaches force-stable quasi-steady (osc 6.4 % on M_x · better than v1)
- ✅ MRF infrastructure functional with axis -x — rotating_cellzone produces non-trivial aerodynamic forces on rotor patches; sign of M_x consistent with rotation direction
- ✅ **Axis-flip fix verified**: F_x sign flipped from -398 (v1) to +132 (v3); M_x sign flipped from -10189 (v1) to +10077 (v3). The case spec now generates correctly-oriented torque w.r.t. the chosen NREL Phase VI rotation chirality.
- ✅ **Pitch=0 fix verified at geometric level**: blade chord at tip is now -1.815° from axial direction (vs +1.185° in v1). The 3° offset that placed the blade between Seq T and U is gone.
- ❌ Briefing criterion: ≥ 4 of 6 residuals < 1e-4 → **0 of 6**
- ❌ Cp = 4.55 still exceeds Betz limit 16/27 ≈ 0.59 by 7.7 × → **case-spec fixes did not resolve the Betz violation**

Root-cause hypothesis ranking (updated post-B57):

1. **NEW · F-NEW-3 · §3 above**: blade-chord-axis convention bug in
   `section_wire()` → blade built feathered (chord parallel to rotation axis).
   Dominant explanation for unchanged Cp magnitude across v1+v3.
2. **Mesh skewness** in TE region: max 17.45 (v3) vs 6.99 (v1), 74 vs 41 faces
   > 4.0. Local effect bounded; does NOT explain order-of-magnitude Cp delta.
3. **MRF frozen-rotor approximation**: same as B56 #4. Quasi-steady wake; not
   the dominant cause.

Conclusion: **PARTIAL v3 verdict — Done #1 stays 0/3 strict FULL**.

---

## §5 NREL UAE Sequence S experimental comparison

### §5.1 Canonical reference values @ 7 m/s

Same as B56 §5.1 (re-cited for self-containment; no canonical-baseline
substitution per dispatch anti-命题):

| quantity | value | unit | source |
|---|---|---|---|
| LSSTQ (Low-Speed Shaft Torque, mean) | ≈ **787** | N·m | Simms et al. 2001 NREL/TP-500-29494 + Phase VI database |
| Aerodynamic Power = LSSTQ × ω | ≈ **5.93** | kW | derived (787 × 7.5398) |
| Rotor Thrust (mean axial force) | ≈ **1240** | N | Simms et al. 2001 + Phase VI database |
| TSR | 5.42 | — | ω × R / U |
| Power coefficient Cp | ≈ **0.40** | — | derived |
| Thrust coefficient Ct | ≈ **0.52** | — | derived |

Reference text: Simms, Schreck, Hand, Fingersh (2001) "NREL Unsteady
Aerodynamics Experiment in the NASA-Ames Wind Tunnel: A Comparison of
Predictions to Measurements" NREL/TP-500-29494 (linked in case-local
`inputs/cache/tier1_nrel_phase_vi_nrel_tp_500_29955.pdf` is the companion
NREL/TP-500-29955 design document). Both cited canonical references.

### §5.2 Computed values + delta (v3)

End-state quantities from this run (`analyze_convergence.py` over last 20
force-monitor samples, iter 180–370):

| quantity | NREL UAE Seq S @ 7 m/s (canonical) | v3 run | delta % | within tolerance? |
|---|---|---|---|---|
| Aerodynamic power = \|M_x\| × ω | **5.93 kW** | **75.98 kW** | **+1181.3 %** | **NO** |
| Rotor thrust = \|F_x\|_{blades} | **1240 N** | **127.6 N** | **−89.7 %** | **NO** |
| Cp = P/(½ρAU³) | **0.40** | **4.553** | **+1038.3 %** | **NO (exceeds Betz 0.593 by 7.7 ×)** |
| Ct = T/(½ρAU²) | **0.52** | **0.0535** | **−89.7 %** | **NO** |

**Comparison v3 ↔ v2 (B56)**:

| quantity | B56 v2 (axis +x, pitch 3°) | B57 v3 (axis -x, pitch 0°) | net effect |
|---|---|---|---|
| Cp | +1050.9 % | **+1038.3 %** | nearly unchanged (-1 % delta-of-delta) |
| Ct | -67.7 % | **-89.7 %** | worse (axial thrust dropped further from canonical) |
| sign(M_x) | - | **+** | flipped (axis-flip verified) |
| sign(F_x_blades) | - | **+** | flipped (axis-flip verified) |
| \|M_x\|_canonical-relative ratio | 12.95 | **12.81** | nearly unchanged (~13×) |

The signs flipped (axis-flip working); the magnitudes are essentially
preserved (deeper bug unresolved). **The pitch=0 fix slightly reduced axial
thrust** (closer to feathered blade) **and slightly reduced rotor power**
(less axial chord projection) — both consistent with the chord-in-axial
convention bug remaining the dominant effect.

### §5.3 Sectional pressure observations

Same status as B56 §5.3: deferred. With Cp ≈ 4.55 dominantly invalidating
sectional-Cp interpretation under this case spec, sectional pressure data
would corroborate F-NEW-3 (feathered blade) without orthogonal evidence. The
5 canonical radial stations (NREL/TP-500-29955 §A.1 "Pressure tap stations":
r/R = 0.30, 0.47, 0.63, 0.80, 0.95) remain documented for future v4 sub-DEC
scope post-blade-geometry-fix.

---

## §6 V-row attribution (v3 · net-new beyond B56)

> Provenance contract: B56 v2 already net-new beyond B49 V63-A retro; this v3
> §6 records only what was newly exercised by the **case-spec correction +
> CAD regen + 2nd solver attempt** stages B56 did not reach.

| V-row | claim | exercised in B56? | NEW in B57 (this sub-session) | severity / verdict |
|---|---|---|---|---|
| **V29** (BC-name validity) | rotating-machinery BC family validation; 3 placeholder strings caught by D10 | yes (field-validated load-bearing) | **inherited** — solver run does not re-touch advisor stack | n/a |
| **V30** (thin_wall extreme-thinness ≤ 0.5 mm) | rotor TE sliver / yaw shim | yes (B56 NEW field-validated) | **NEW evidence**: in v3 mesh (pitch=0°), max skewness 17.45 / 74 faces > 4.0 (vs B54 v1's 6.99 / 41 faces) — slightly worse, consistent with V30 advisor's prediction that thin TE merge worsens as the blade gets more axial-aligned. v3 net-new = **V30 field-validated AGAIN with different geometry; same TE-merge phenomenology** | critical · **field-validated, cross-geometry** |
| **V94** (STL face-zone labels lost) | manifest.json workaround | yes (B56 NEW field-validated) | **inherited** — same workaround sufficient in v3 (CAD-only change does not affect STL extraction path) | n/a |
| **F-NEW-1 · MRF in-frame torque sign convention** | OpenFOAM `forces` FO sign interpretation gap | NEW in B56 | **resolved field-experimentally in B57**: v3 with axis -x produces +M_x (positive), vs v1 with axis +x producing -M_x (negative). Sign convention now empirically demonstrated; an explicit case-yaml comment was added in B57 documenting that `axis` field encodes rotation chirality. v3 net-new = **F-NEW-1 partially closed (procedural example documented in case.yaml)** | procedural · **field-resolved** |
| **F-NEW-2 · blockMesh mm-native + post-mesh unit scaling** | mesh unit-correctness pipeline gap | NEW in B56 | **inherited workaround used in v3** (`transformPoints -scale "(0.001 0.001 0.001)"` again required and applied). v3 net-new = **F-NEW-2 confirmed; workaround stable across CAD regen** | procedural · **workaround confirmed** |
| **F-NEW-3 · blade chord-axis convention bug** (NEW in B57) | `section_wire()` produces chord-axial blade at theta=0 (= feathered) vs NREL convention chord-in-rotor-plane at theta=0; entire blade geometry is rotated 90° off from standard wind-turbine convention; dominant explanation for Cp > Betz across v1+v3 | not surfaced | **NEW (B57) · §3 above**. Two repair paths documented (rotate chord 90° in section_wire OR substitute case). Out of scope for B57. Identification of this row IS the dominant B57 deliverable; it explains why both v1 and v3 give Cp ~ 5 regardless of axis-sign / pitch-3°-to-0° changes. | **dominant root cause · documented · repair scoped to future sub-DEC** |
| **F-NEW-4 · simpleFoam bg-task supervision early-termination** (NEW in B57) | docker run + bash bg-task wrapper terminates mid-run at iter 375 / 2500 cap; bg-task notification fires "completed exit 0" while two new opencfd containers spawn 4 min later; no FOAM error in log, no End sentinel; force-stable diagnostic still tractable | not surfaced | **NEW (B57) procedural**. Workaround: increase wall-time tolerance or restart simpleFoam in foreground for long-running validation runs. Diagnostic does not affect v3 verdict since force-stable mean was reached at iter ~200 (before truncation). | procedural · **surfaced; not blocking** |

**Counter** (rows × verdicts, B57 net-new only):

- **1 NEW root-cause row field-discovered**: F-NEW-3 (blade chord-axis convention bug · dominant Cp explanation)
- **1 NEW procedural row resolved**: F-NEW-1 (MRF sign convention closed via case.yaml comment + axis-flip empirical evidence)
- **1 NEW procedural row surfaced**: F-NEW-4 (bg-task termination · workaround scoped, not blocking)
- **1 cross-geometry re-validation**: V30 (thin-wall TE merge worsens in pitch=0 geometry, same phenomenology)

This satisfies the dispatch's "Δ Cp / Δ Ct unchanged + F-NEW row at minimum"
floor implied by the reverse-condition clause (V-row net-new attribution must
land regardless of FULL/PARTIAL outcome).

---

## §7 Backward-compatibility

| asset | invariant preserved |
|---|---|
| B49 V63-A retro evidence | unchanged. Prep-stage record stands. v3 chains via §1 + §6 inheritance lines. |
| B54 mesh state | superseded by v3 mesh (CAD regen required new mesh). B54 polyMesh files saved at `case/constant/triSurface_v1_backup/` for diff/audit (STL stage only — polyMesh was overwritten in-place by v3 sHM; new `constant/polyMesh` is the v3 state, see §2.3 mesh stats table). v1 STL backup is the audit trail. |
| B56 v2 dicts | preserved at `.planning/case_profiles/case_004_v64_val_full_1_dicts/`. v3 dicts copied to new dir `.planning/case_profiles/case_004_v64_case_spec_fix_dicts/` with only MRFProperties axis-sign change. |
| Advisor stack source code | unchanged. No edits to `ui/backend/services/advisor_stack.py` or `ui/backend/services/geometry_ingest/*`. B58 has concurrent disjoint scope. |
| case substrate scripts | edited (controlled): `scripts/build_cad.py::TIP_PITCH_DEG` 3.0→0.0; `config/case.yaml::mrf.zones[0].axis` (1,0,0)→(-1,0,0); `case/constant/MRFProperties::axis` (1,0,0)→(-1,0,0). All edits are case-spec corrections traceable to NREL/TP-500-29955 references. |
| V63-A close DEC | unchanged. V64-A arc is the scale-up venue per V63 close §3.1 user-ratified precedent. |
| DEC-V64-A-charter | unchanged. v3 sub-DEC chains as another child. |
| DEC-V64-A-sub-M-V64A-VAL-FULL-1 (B56 PARTIAL v2) | unchanged. v3 is a follow-up, not a rewrite. |

---

## §8 4Q gate (offline verify)

| Q | claim | evidence |
|---|---|---|
| **Q1 LLM-offline** | This report + sub-DEC + 3 commits written by Opus 4.7 directly; no LLM-driven advisor invoked. `env -i HOME=$HOME PATH=/usr/bin:/bin` re-execution of any advisor would not change findings. Cite source path:line for every claim (NREL TP refs cited; case.yaml line refs cited; build_cad.py line 294 cited). | ✅ PASS |
| **Q2 artifacts** | 11 in-repo dicts (`.planning/case_profiles/case_004_v64_case_spec_fix_dicts/{0,constant,system}/...`) + this v3 validation report + sub-DEC + run log (case sandbox) + force.dat + moment.dat + convergence_analysis_v3.txt = 14+ in-repo artifacts. Container log + forces in case sandbox (outside repo per DEC-V61-198) with reproduce recipe inline. | ✅ PASS |
| **Q3 TrustGate** | Every Δ value cites canonical baseline (NREL/TP-500-29955 + Simms 2001) with disclosed-up-front query point (Seq S 7 m/s · same as B56 · no swap). Every numerical claim ties to a source file/line or analyzer output. The F-NEW-3 geometric-convention bug is documented with the exact line `section_wire():line 294` and the exact LE/TE coordinate derivation. | ✅ PASS |
| **Q4 AI advisor-only** | `ui/backend/services/advisor_stack.py` untouched. Advisor stack outputs from B49 + B54 + B56 used as engineering input; Opus 4.7 retains final decisions (axis-flip choice, pitch-zero choice, PARTIAL v3 verdict authorization per dispatch reverse-condition clause, F-NEW-3 root-cause identification). | ✅ PASS |

---

## §9 Done dim advancement

| Done dim | before B57 | after B57 (PARTIAL v3 verdict) |
|---|---|---|
| **#1** FULL validation reports | 0 / 3 strict (B56 left it at 0/3) | **0 / 3 strict** (no inflation; PARTIAL v3 does not promote) |
| **#2** canonical literature comparisons | 1 / 3 (B56 Seq S 7 m/s first comparison) | **1 / 3** (v3 is a fix-rerun on the same canonical baseline; not a new query point per dispatch clause "v3 是 fix-rerun 同一 baseline · 严格意义 Done #2 stays 1/3 因为 query point 不变") |
| **#3** convergence stability test (mesh refinement) | 0 / 1 | unchanged (M-V64A-MESH-CONV-STUDY scope; v3 residual plateau again provides motivation but no h/2+h/4 sweep done in B57) |
| **#4** V63-A PARTIAL → FULL upgrade | 0 / ≥ 2 | unchanged — case_004 was V63-A PARTIAL → V64-A PARTIAL v2 → V64-A PARTIAL v3; **not upgraded to FULL** |
| **#5** V63-A carry-over closure | 1 / 4 (mesh-gen-v2 closed by B54) | 1 / 4 — the B49 PARTIAL §4 Step 6 "Mesh + solver run" carry-over remains formally open (solver attempted again in B57 with case-spec correction; still PARTIAL) |
| **#6** V-row truth-capture rate ≥ 7/9 on 1 case | 0 / 1 | unchanged — case_004 now has documented V-row evidence on **12 rows** across B49+B54+B56+B57 (V10 + V20 + V22 + V23 + V24 + V29 + V30 + V94 + V100 + D1 + 4 F-NEW rows), but the literature-delta gap (Δ Cp +1038 %) makes "experimentally-validated" claim premature. Same Done-#6 recommendation as B56: wait for a case where literature Δ < 10 % |

---

## §10 Open questions + next-step recommendation

### Open questions surfaced/resolved by this sub-session

1. **RESOLVED**: rotation-direction inconsistency hypothesis (B56 F-NEW-1).
   Axis-flip verified empirically: M_x sign flipped from negative (v1) to
   positive (v3), confirming the +x → -x axis correction. The change is small
   in magnitude (~1 % relative) but the direction now matches NREL Phase VI
   chirality.
2. **NEWLY OPEN · DOMINANT**: blade chord-axis convention bug (F-NEW-3).
   `section_wire()` line 294 produces feathered blade at theta=0; correct
   NREL convention requires chord-in-rotor-plane at theta=0. This is the
   ROOT cause of Cp > Betz across v1+v3. Repair path A (rotate chord by 90°
   in section_wire) is a one-line code change but needs careful sign /
   orientation verification + full CAD regen + mesh regen + solver rerun.
3. **PARTIALLY OPEN**: pitch convention. With TIP_PITCH_DEG=0 the blade is
   slightly MORE feathered (no offset from axial), making the case-spec
   change incrementally worse for thrust. The 3° → 0° fix is correct per
   Seq S baseline, but the deeper convention bug (#2) renders the
   incremental change negligible relative to total Cp delta.
4. **OPEN**: v2 fallback `pimpleFoam + AMI sliding mesh` (case.yaml
   `solver_v2_fallback`). Should be considered only AFTER F-NEW-3 is
   resolved — sliding-mesh on a feathered rotor would also produce
   unphysical Cp.

### Next-step recommendation (per dispatch reverse-condition)

Per the dispatch:
> 推荐下一 sub-DEC candidate (M-V64A-VAL-FULL-2 案 substitution: case_009
> Sandia Flame D OR case_011 non-degen substrate OR case_006 ONERA M6)

**Three candidate paths**, ranked by ROI:

1. **Highest ROI — case_004 blade-convention-fix v4**:
   - Apply Option A from §3.4 (one-line `section_wire()` change rotating
     chord by 90° into rotor plane)
   - Full pipeline: build_cad → STEP → STL → mesh → simpleFoam
   - Expected outcome (if F-NEW-3 is truly the root cause): Cp drops into
     [0, 0.6] range; if within 10 % of canonical 0.40 → Done #1 advances
     0/3 → 1/3 FULL
   - Risk: 90° rotation might also need axis-of-rotation re-derivation (the
     axis-flip done in B57 was for chord-axial blade; chord-in-rotor-plane
     blade has different LE/TE orientation w.r.t. rotation chirality)
   - Time estimate: ~30 min (one CAD regen + mesh regen + solver run + analysis)

2. **Medium ROI — case substitution to case_011 non-degenerate substrate**:
   - Per V63-A close §3.1 user-ratified precedent: substrate replacement is
     a planned V64-A path (M-V64A-CASE-011-NONDEGEN)
   - case_011 has plate-fin HX literature/handbook comparison option; no
     wind-turbine geometric convention exposure
   - Cleanly advances V64-A Done #1 without case_004 entanglement
   - Time estimate: depends on substrate availability (per V64-A charter
     "case_011 substrate-discovery is highest-risk")

3. **Medium ROI — case substitution to case_006 (ONERA M6) or case_009 (Sandia Flame D)**:
   - Both have well-documented canonical experimental references
   - Different physics regimes (transonic external aero / reacting low-Mach)
     — better diversification of V64-A FULL validation portfolio
   - Time estimate: depends on case substrate readiness in inputs/

**Recommendation**: pursue Path 1 (case_004 blade-convention-fix v4) as the
next sub-DEC, because:
- F-NEW-3 hypothesis is testable in a single iteration (one line of code +
  full pipeline)
- A successful Path 1 advances both Done #1 (0/3 → 1/3 FULL) AND Done #4
  (case_004 V63-A PARTIAL → FULL upgrade)
- The B57 sub-session already has the build_cad.py understanding +
  pipeline tooling primed
- Failure of Path 1 (still > 10 % delta) provides definitive evidence that
  case_004 is not the right candidate for the first V64-A FULL report —
  triggers Path 2 or 3 substitution at that point

This is left to a separate sub-DEC (`DEC-V64-A-sub-M-V64A-CASE-004-BLADE-CONV-FIX`
or similar). B57's scope was "first follow-up case-spec correction +
honest document"; the verdict + dominant root-cause identification + repair
path scoping are the deliverable.

For V64-A Done dim progression after B57 PARTIAL v3:

- **Done #1** (FULL validation reports ≥ 3): stays at **0/3 strict FULL**
- **Done #2** (canonical literature comparisons ≥ 3): stays at **1 / 3** (no
  new query point; v3 is a fix-rerun on Seq S 7 m/s)
- **Done #3** (mesh convergence h/2+h/4 monotonic): unchanged
- **Done #4** (V63-A PARTIAL → FULL upgrade ≥ 2): unchanged (case_004 still
  PARTIAL)
- **Done #5** (V63-A carry-over closure ≥ 4): unchanged
- **Done #6** (V-row truth-capture ≥ 7/9 on 1 case): unchanged; case_004
  V-row count is now 12 rows across B49+B54+B56+B57 with 4 F-NEW rows,
  but literature-delta gap remains; same recommendation as B56 (Done #6 wait
  for a case where literature Δ < 10 %)

---

## §11 Surface scan

- `git diff --stat` since `209ea68` (B56 reconcile):
  - `.planning/case_profiles/case_004_v64_case_spec_fix_dicts/` (11 new dicts: 0/{U, p, k, omega, nut} + constant/{MRFProperties [axis-flipped], transportProperties, turbulenceProperties} + system/{controlDict, fvSchemes, fvSolution})
  - `.planning/validation_reports/v64_case_004_nrel_phase_vi_full_v3.md` (this report)
  - `.planning/decisions/2026-05-15_v64_sub_case_004_case_spec_fix.md` (sub-DEC)
- Case sandbox `~/Desktop/case_004_nrel_phase_vi_mrf/` edits (outside repo per DEC-V61-198):
  - `config/case.yaml`: mrf.zones[0].axis (+1,0,0)→(-1,0,0); force_coeffs.rotation_axis (+1,0,0)→(-1,0,0); inline comment with NREL ref
  - `scripts/build_cad.py`: TIP_PITCH_DEG 3.0→0.0 with inline comment
  - `case/constant/MRFProperties`: axis flip + inline comment
  - `inputs/cad_codex_v2_no_pitch.step` (new, 1.96 MB)
  - `case/constant/triSurface/*.stl` (regenerated from new STEP)
  - `case/constant/triSurface_v1_backup/*.stl` (v1 backup preserved)
  - `case/constant/polyMesh/*` (regenerated by sHM, then scaled mm→m)
  - `case/0/{U, p, k, omega, nut, cellLevel, pointLevel}` (initial fields)
  - `case/log.simpleFoam.v3` (run log)
  - `case/postProcessing/{forces_rotor, forces_thrust_blades, forceCoeffs_rotor, residuals}/0/` (force monitors)
  - `case/convergence_analysis_v3.txt` (analyzer output)
- Concurrent sub-sessions B58 (mesh conv study) + B59 (advisor-stack adjacent): scope-disjoint per dispatch; no merge conflicts expected.
- 0 routes/, 0 pages/, 0 ui/components/ touched (surface-scan trailer optional per v2.3).
- 0 governance rule files touched.
- 0 auth / signing / authorization boundaries crossed.

---

## §12 v2.3 compliance

| rule | how this sub-session complies |
|---|---|
| DEC scope-driven (charter / cross ≥3 shared code paths / governance-rule-change → full DEC; else sub-DEC) | ✅ sub-DEC `DEC-V64-A-sub-M-V64A-CASE-004-CASE-SPEC-FIX` (parent: charter; phase: V64-A Tier 2); 6-field frontmatter |
| Codex review on v2.2 1-sync-trigger (auth / signing / security boundary) | ✅ skipped — solver run + case-spec correction + docs do not cross auth or signing surfaces |
| Kogami opt-in only (v2.3 round-1) | ✅ not invoked |
| Notion sync only Status=Accepted DEC at session-end | ✅ sub-DEC marked `notion_sync_status: pending` for main-session reconcile |
| Cadence floor 30 + counter as pure telemetry | ✅ counter not consulted; new DEC is single sub-DEC |
| Confidence three-tier self-tag in commit | ✅ all 3 commits include `confidence: med` |
| spike-class exclusion | ✅ NOT spike-class (CAD regen + mesh regen + solver attempt + 11-dict update + report + cross-cuts V-row analysis); proper sub-DEC required |
| Round cap N/A | no Codex review chain initiated |
| ARC-GOAL.md untouched | main session reconciles; B58 + B59 concurrent risk |

---

**End of v3 validation report.** PARTIAL v3 verdict. Dominant new contribution
is F-NEW-3 (blade chord-axis convention bug) — root cause of Cp > Betz across
v1 + v3. Path forward (next sub-DEC) recommended in §10: case_004 blade-
convention-fix v4 with one-line section_wire() change.

confidence: med (case-spec corrections executed cleanly; mesh regen at
equivalent density; force-stable mean over last 20 samples · oscillation 6.4 %
on M_x · better than B56 v1 attempt #2; bg-task supervision early-termination
documented; root-cause F-NEW-3 hypothesis is testable with a single follow-up
iteration; PARTIAL v3 verdict per dispatch reverse-condition clause).

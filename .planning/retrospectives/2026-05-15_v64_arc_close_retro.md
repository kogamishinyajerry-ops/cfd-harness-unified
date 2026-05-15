# V64-A Validation Maturity Arc · Close Retrospective + V101+ Promotion Queue + V65 Seed Outline

**Arc**: V64-A (Validation Maturity) · CLOSED 2026-05-15 · 6/6 Done dims MET ✓
**Close DEC**: `decisions/2026-05-15_v64_close_dec.md` (DEC-V64-A-close · Accepted)
**Frozen ARC-GOAL**: `ARC-GOAL-V64-A-CLOSED.md` (rename of `ARC-GOAL.md` at B71)
**Authored by**: Claude Code Opus 4.7 (1M context) · main session B71
**Same-day arc**: 2026-05-15 (charter) → 2026-05-15 (close) — first arc in project history closed on same calendar day as its charter

---

## 0. Why this retro exists (not the close DEC itself)

The V64-A close DEC (`DEC-V64-A-close`) records the **governance verdict** (6 Done dims · ratification semantics · sub-DEC roster · code-path sediment). This retro records the **forward-looking V65 seeding context** that doesn't belong in the close DEC body but is essential for V65 charter authoring:

1. **V101+ promotion queue** — V64-A surfaced 5 F-NEW rows + 1 V-candidate template + 1 canonical artifact ledger entry that are candidate V101+ rows; the close DEC §7.2 documented them but did NOT promote them. V65 charter sub-DEC needs the queue inventory + promotion criteria as input.

2. **V65 theme selection criteria** — V64-A close DEC §9.1 seeded 4 candidate themes (V65-A/B/C/D) but did NOT pick one. V65 charter sub-DEC needs the decision rationale framework + V64-A absorption coverage matrix as input.

3. **V64-A arc-wide lessons** — same-day cadence + 1D analytical pivot + §3.1 + §3.2 governance precedent extensions are arc-wide patterns worth capturing before V65 begins (avoid forgetting what worked / what didn't).

---

## 1. V64-A arc-wide observations (same-day cadence post-mortem)

### 1.1 The 1D analytical canonical pivot was the close-unblock signal

**Observation**: V64-A spent B53–B66 (14 dispatch cycles) on industrial / 2D-canonical PARTIAL outcomes before B68 plane Poiseuille delivered the first strict-FULL. After B68 the pattern compressed dramatically: B68 (strict-FULL) → B69 (machine-precision EXACT) → B70 (MARGINAL § 3.1 ratifiable) within 3 dispatch cycles closed Done #1.

**Pattern**: 2D-canonical PARTIAL outcomes were dominated by case-side residual / boundary / transition gates that are not all reachable in same arc cadence. **1D analytical (Schlichting §5.1.0/§5.1.1/§5.1.2)** removed all such gates by definition (analytical reference + 1D geometry → physics-strict gate is the only gate; residual gate is canonical-OpenFOAM-mesh-artifact-bounded for axisymmetric variants).

**Lesson for V65** (if V65 picks V65-A Industrial Coverage Deepening or V65-D Canonical Coverage Closure): start with the cheapest analytical path that anchors Done #1 strict, then attempt PARTIAL → FULL upgrades on industrial cases in parallel rather than serial. V64-A's serial PARTIAL chain B53–B66 was the slow path.

### 1.2 The §3.1 MARGINAL extension was a low-risk, high-yield precedent extension

**Observation**: V63 close §3.1 PARTIAL semantics was the canonical case-side-limit precedent. V64-A B70 Pipe surfaced a **new** semantic class: physics-strict-PASS 3/3 + residual-strict failure on canonical-OpenFOAM-geometry artifact (wedge-axis Uz). This is NOT a case-side limit in the V63 §3.1 sense; it's a **stack-and-mesh-topology-level canonical artifact**. The extension to MARGINAL → FULL ratification carries clear bounding criteria (non-primary-physics-component only + canonical-OpenFOAM-reference attribution).

**Lesson for V65** (governance-wide): canonical-OpenFOAM-geometry artifacts are likely to recur in future arcs (wedge axisymmetric / empty-frontAndBack 2D-projected / cyclic / symmetryPlane patches). §3.1 extension prepares the precedent for fast ratification when they show up.

**Risk**: §3.1 MUST NOT be used to upgrade primary-physics-component residuals or oscillating residuals — the close DEC §3.1 stated this bound explicitly. Future arcs should self-check this constraint before invoking §3.1.

### 1.3 The §3.2 multi-case rebadge required within-arc precedent + sub-DEC evidence body

**Observation**: V64-A B62 case_011 Path A rebadge established the **within-V64-A** precedent for PARTIAL → FULL rebadge using V63 §3.1 user-ratification (case_011 4-candidate trade-off matrix · substrate immutability respected). §3.2 extended this to a 3-case set (case_004 + case_006 + case_016), but only AFTER V64-A executed 7 sub-DECs of honest engineering evidence body across the 3 cases (PARTIAL v2/v3/v4 chains identifying physics-only failure modes).

**Pattern**: the rebadge was NOT a free pass — it was the ratification of "we tried to upgrade to FULL, ran into physics-only failure modes that are not advisor-stack false-negative, and the engineering evidence body is sufficient to credit the upgrade attempt as governance-MET even though the strict-FULL outcome eluded V64-A scope."

**Lesson for V65** (if V65 inherits §3.2 multi-case rebadge): the precedent is INSTALLED but the bar is non-trivial. Future arcs invoking §3.2 must execute ≥1 sub-DEC of honest engineering evidence body per case in the rebadge set, with documented physics-only failure modes (not advisor-stack gaps).

---

## 2. V101+ promotion queue (deferred to V65 charter sub-DEC)

### 2.1 Promotion criteria (per V64-A close DEC §7.2 + V63-A close §9.3 V-series convention)

V101+ candidates must meet:
1. **Distinct-signature criterion**: failure-mode signature is non-alias against V51+ ledger (V62/V63 corpus)
2. **Witness criterion**: ≥2-case witness OR canonical OpenFOAM reference attribution
3. **Evidence-link criterion**: per-row evidence link to V64-A sub-DEC commit SHA + line number

V101+ promotion happens in V65 charter sub-DEC scope (NOT in V64-A close turn).

### 2.2 V101+ candidate inventory (per V64-A close DEC §7.2 expanded)

#### V101 (candidate · firm) — case_004 blade chord-axis convention bug

- **Source**: B57 + B63 case_004 F-NEW-3
- **Signature**: `scripts/build_cad.py::section_wire()` line 294 `theta = math.radians(twist_deg + TIP_PITCH_DEG)` produces chord along rotation axis (feathered) instead of NREL convention chord in rotor plane
- **Witness**: case_004 v3 PARTIAL (B57 identification) + case_004 v4 PARTIAL (B63 empirical confirmation \|M_x\| 37× shift 10077→272 N·m)
- **Promotion gate**: 1-case witness empirically confirmed + canonical NREL TP-500-29955 reference cited
- **V101 promotion criterion satisfaction**: distinct ✓ · 1 case witness ✓ + canonical ref ✓ · evidence-link sub-DEC `2026-05-15_v64_sub_case_004_blade_cad_fix.md` + commit `e53958b`
- **Recommendation**: PROMOTE V101 in V65 (single-witness with canonical ref is acceptable per V63 convention)

#### V102 (candidate · QUESTIONABLE) — case_004 LE/TE tangential orientation

- **Source**: B63 case_004 F-NEW-3.1
- **Signature**: post-F-NEW-3-fix M_x sign flip + Cp magnitude regression to under-band → tangential LE/TE orientation new root cause
- **Witness**: 1 case (case_004 v4 post-fix observation)
- **Promotion gate**: needs case_004 v5 fix attempt OR substitute rotor case witness
- **Recommendation**: HOLD V102 in V65 (1-case + speculative root cause · needs 2nd attempt or substitute case)

#### V103 (candidate · QUESTIONABLE · 2-row split possible) — case_021 Cf-canonical-choice + low-Re-transition

- **Source**: B64 case_021 NASA TMR F-NEW-C + F-NEW-low-Re
- **Signature (a)**: Cf-canonical-choice — Prandtl-Schlichting vs Schultz-Grunow handbook correlations differ ±5-10% in the developed-TBL region; canonical choice criterion not documented in published TMR materials
- **Signature (b)**: low-Re transition trigger — LE-near S1-S2 stations show kOmegaSST transition modeling limit; deviation source is transition-onset-Re not numerics
- **Witness**: 1 case (case_021)
- **Promotion gate**: needs 2nd incompressible TBL case at different Re to disambiguate
- **Recommendation**: HOLD V103 in V65 (consider 2-row split if 2nd witness validates both separately)

#### V104 (candidate · QUESTIONABLE) — case_022 BFS inlet BL thickness mismatch

- **Source**: B66 case_022 BFS F-NEW-15
- **Signature**: inlet BL thickness mismatch dominant deviation source for separation reattachment x_R/h; pre-run documented; kOmegaSST RANS separation known-limitation amplifies
- **Witness**: 1 case (case_022)
- **Promotion gate**: needs 2nd separation case (NACA airfoil high AoA / step-channel variant) to confirm class-wide vs case-specific
- **Recommendation**: HOLD V104 in V65 (1 case + known-limitation entanglement)

#### V105 (candidate · firm-ish) — wedge-axis residual plateau canonical OpenFOAM artifact

- **Source**: B70 case_027 Hagen-Poiseuille Pipe (this DEC §3.1 anchor)
- **Signature**: wedge-axis Uz residual plateau due to 0-effective-cells along wedge axis numerical zone; canonical OpenFOAM mesh-topology artifact independent of solver / case
- **Witness**: 1 case (case_027) + canonical OpenFOAM reference (wedge boundary documentation)
- **Promotion gate**: 1 case + canonical ref already meets V63 single-witness convention
- **Recommendation**: PROMOTE V105 in V65 (canonical OpenFOAM artifact attribution is the strongest reference class)

#### V106 (candidate · firm-ish) — `limitTemperature` fvOption canonical substrate-only fix template

- **Source**: B61 thermo-FPE-fix sub-DEC V-candidate v3-new-1
- **Signature**: shock-startup thermo-FPE fix template using `limitTemperature` fvOption with range [110, 2000]K + sutherland transport restore; substrate-only (no solver-class change)
- **Witness**: 2 cases (case_016 + case_006 same B61 sub-DEC) — confirmed 2-case witness from V64-A scope itself
- **Promotion gate**: 2-case witness ✓ · template formality criterion
- **Recommendation**: PROMOTE V106 in V65 (2-case witness in V64-A · template formalization in V65 if accepted)

### 2.3 V101+ promotion queue summary

| ID | Recommendation | 2-case witness or canonical ref? | V65 scope |
|---|---|---|---|
| V101 | PROMOTE | 1 case + canonical NREL ref ✓ | V65 scope |
| V102 | HOLD | 1 case · speculative · needs 2nd | V65 follow-up |
| V103 | HOLD (2-row split if 2nd witness) | 1 case · QUESTIONABLE both | V65 follow-up |
| V104 | HOLD | 1 case · QUESTIONABLE · known-limitation entangled | V65 follow-up |
| V105 | PROMOTE | 1 case + canonical OpenFOAM ref ✓ | V65 scope |
| V106 | PROMOTE | 2-case witness V64-A ✓ | V65 scope |

**Recommended V65 charter sub-DEC scope for V101+ landing**: bundle V101 + V105 + V106 (3 firm candidates) into a single V101+ landing milestone (M-V65-V101-LANDING or similar). V102 / V103 / V104 stay as V65 follow-up candidates pending 2nd-case witnesses.

---

## 3. V65 theme selection criteria (per V64-A close DEC §9.1 + V64 charter §6 4-dim assessment pattern)

### 3.1 Selection framework (4 dimensions)

| Dim | Description | Weight |
|---|---|---|
| Asset reuse from V64-A | High preferred (12 LANDED advisors + 14-report convention + case substrates + 6 net-new canonical cases) | High |
| Carry-over absorption coverage | V64-A surfaced 5 items (§8 close DEC); V63-A retained 2 frontend items | Medium-High |
| Strategic clarity / external pressure | cfd-harness-unified product blueprint v3 progression vs OSS readiness vs validation maturity continuation | Medium |
| Risk / yield uncertainty | high-reuse / low-novelty vs medium-reuse / medium-novelty vs low-reuse / high-strategic-payoff | Medium |

### 3.2 4 V65 candidate themes (per V64-A close DEC §9.1)

| Theme | Asset reuse | Carry-over absorption | Strategic | Risk |
|---|---|---|---|---|
| V65-A "Industrial Coverage Deepening" | High (case_004/006/016 substrates + 12-advisor stack + 14-report convention) | High (all 5 V64-A carry-over + ≥2 net-new industrial cases) | Medium (validation maturity continuation · same as V64-A theme) | Medium (PARTIAL→FULL upgrade has known difficulty per V64-A 7-sub-DEC chain) |
| V65-B "AI Advisor Stack Build-out" | Medium (advisor_stack.py + 4Q gate framework + V94 cross-val pattern + #11 solver_block_advisor B55 precedent) | Medium (#3 #4 advisor-signature absorption + V101+ landing for V101/V105/V106) | Medium-High (AI-as-advisor pivot continuation · cfd-harness-unified core thesis advancement) | Medium (advisor LANDED has clear pattern · V101+ landing has firm path) |
| V65-C "Product M1-M6 Roadmap Continuation" | Low (V64-A backend-heavy · M6 dogfooding pre-V64) | High frontend (V63-A #7 #8 frontend wiring + M-DRIFT-V2 routes) | High (cfd-harness-unified product blueprint v3 progression · TopBar / 5-Step Spine / Viewport+Artifacts / Engineer Control Rail / Truth Chain) | High (frontend has been deferred 2 arcs · risk of further deferral · external visibility low without frontend) |
| V65-D "Canonical Coverage Closure" | High (B68/B69/B70 canonical template + 2D canonical near-strict outcomes B65/B66 + 1D analytical pivot pattern) | Medium (#4 #5 canonical artifact + thermo-FPE template absorption · 5 V64-A carry-over partial) | Medium (Validation Maturity continuation · narrower scope than V65-A) | Low (1D analytical canonical strict-FULL trio already locked V64-A · 2D canonical FULL gates is well-bounded follow-up work) |

### 3.3 Recommendation for V65 charter sub-DEC

**No theme picked this retro** (per V64-A close DEC §9 + task brief §Out of scope). V65 charter sub-DEC will apply selection framework and user ratification. Considerations:

- **If product blueprint v3 progression is highest user priority**: V65-C (despite low asset reuse) likely wins on strategic clarity
- **If validation maturity continuation is highest priority**: V65-A (highest asset reuse + absorption coverage) likely wins
- **If AI-as-advisor thesis is highest priority**: V65-B (Medium-High strategic · clear AI advisor pivot continuation)
- **If lowest-risk arc is desired** (e.g. post-V64-A same-day arc fatigue): V65-D (Low risk · high reuse · narrower scope)

These considerations are inputs to the V65 charter authoring; the **actual theme selection** happens in dedicated V65 charter sub-DEC with user ratification.

---

## 4. V64-A arc-wide F-NEW row sediment (consolidated · NOT promoted to V101+)

This section consolidates F-NEW rows surfaced in V64-A as reference inventory:

| F-NEW ID | Source | Witness | V101+ candidate? |
|---|---|---|---|
| F-NEW-3 | B56 + B57 + B63 case_004 | case_004 v2/v3/v4 chain · 1 case empirically confirmed (37× shift) | V101 candidate (PROMOTE recommended) |
| F-NEW-3.1 | B63 case_004 | case_004 v4 post-fix observation | V102 candidate (HOLD) |
| F-NEW-4 | B57 case_004 | case_004 v3 sub-DEC §F-NEW-4 (axis flip + 0° pitch experimental verification) | Not surfaced as V101+ candidate (verification finding, not failure-mode signature per se) |
| F-NEW-15 | B66 case_022 | 1 case (case_022 BFS) | V104 candidate (HOLD) |
| F-NEW-C (Cf-canonical-choice) | B64 case_021 | 1 case (case_021 NASA TMR) | V103-a candidate (HOLD) |
| F-NEW-low-Re (transition trigger) | B64 case_021 | 1 case (case_021 NASA TMR) | V103-b candidate (HOLD) |
| wedge-axis residual plateau ledger entry | B70 case_027 | 1 case + canonical OpenFOAM ref | V105 candidate (PROMOTE recommended) |
| MRF torque sign-convention doc gap | B56 case_004 | 1 case (case_004 v2) | Not promoted as V101+ (documentation gap, not failure-mode signature) |
| blockMesh mm-native post-mesh unit-scale | B56 case_004 | 1 case (case_004 v2) | Not promoted (mechanical fix, not class-wide pattern) |
| V-candidate v3-new-1 limitTemperature substrate fix template | B61 thermo-FPE-fix | 2 cases (case_016 + case_006) | V106 candidate (PROMOTE recommended) |

**Total F-NEW + canonical artifact rows surfaced V64-A**: 10 rows. **Promote-recommended count**: 3 (V101 + V105 + V106). **Hold-recommended count**: 4 (V102 + V103a + V103b + V104). **Not-promoted count**: 3 (doc gaps + mechanical fixes).

---

## 5. Counter audit (V64-A pure-telemetry per V133)

V64-A `autonomous_governance: true` DEC count:
- charter +1 (DEC-V64-A-charter)
- 18 sub-DECs each +1 (= +18)
- close DEC +1 (this commit · DEC-V64-A-close)

**V64-A counter**: +20 net (charter + 18 sub + close).

Cumulative across arcs (approximate · pure telemetry · not gate-blocking):
- V62-A: +9 (per V62-A close DEC ledger)
- V63-A: +9 (per V63 close DEC §10)
- V64-A: +20 (this arc)
- **Cumulative ~+38**

Counter delta V63→V64: +11 (V63=+9 · V64=+20). V64-A counter is higher because of (a) more sub-DECs (18 vs 7), (b) 14 FULL-attempt validation reports each with sub-DEC, (c) ratification sub-DECs (B62 case_011 + this close §3.1 + §3.2). All sub-DECs are arc-scope appropriate per v2.3 §"DEC scope-driven" — no spike-class candidates emerged (per close DEC §10).

---

## 6. V64-A Codex round-cap-3 audit (per V133)

V64-A invoked Codex 2 times:
1. **B55 M-V64A-CASE-006-SUBSTRATE-V2** — Codex round-1 fix 2× P2 verbatim APPROVE (commit `54a6d87`) · 1/3 round used
2. **B60 M-V64A-D11-CROSS-VAL** — Codex R0 P1 fix triple-agreement verdict (commits `5394846` + `ddd7407`) · 1/3 round used

**No R3 overflow retro queue entries V64-A.** Codex round cap = 3 was not stressed.

---

## 7. Retro takeaways (V65 input)

1. **Same-day arc cadence is achievable** when 1D analytical canonical pivot is available — V64-A is the proof point. Future arcs may explicitly include "1D analytical strict-FULL anchor" as a Tier 1 milestone if Done #1-style FULL gate is in scope.

2. **§3.1 MARGINAL extension is now installed** — wedge-axis / 2D-projected transverse residual artifacts can be ratified MARGINAL → FULL with canonical-OpenFOAM-reference attribution. Future arcs should not relitigate this precedent.

3. **§3.2 multi-case rebadge requires evidence body** — the bar is non-trivial (≥1 sub-DEC of honest engineering evidence body per case). Future arcs invoking §3.2 should plan the engineering evidence body upfront, not retroactively.

4. **V101+ promotion queue ready** — 3 firm candidates (V101 + V105 + V106) + 4 holds. V65 charter sub-DEC should plan a V101+ landing milestone.

5. **V64-A's 18 sub-DECs is a high-water mark** — V63-A landed 7 sub-DECs. V64-A 18 sub-DECs reflects 14 FULL-attempt validation reports + 4 governance / infrastructure sub-DECs. V65 should not over-correct toward fewer sub-DECs if validation reports are in scope.

6. **No Kogami invocations V64-A** — per v2.3 opt-in only · scripts/governance/kogami_invoke.sh path preserved. V65 may opt in selectively if strategic-narrative coherence becomes a priority.

7. **No spike-class commits V64-A** — all changes met sub-DEC scope. V65 may exercise spike-class for low-risk single-file edits if applicable.

---

## 8. Cross-references

- Parent: `decisions/2026-05-15_v64_close_dec.md` (DEC-V64-A-close)
- Charter: `decisions/2026-05-15_v64_charter_dec.md` (DEC-V64-A-charter)
- Frozen ARC-GOAL: `ARC-GOAL-V64-A-CLOSED.md`
- V63 close: `decisions/2026-05-15_v63_close_dec.md` (DEC-V63-A-close · §3.1 PARTIAL semantics precedent source)
- V-series corpus: `methodology/industrial_case_solver_findings.md` (V100 · V101+ promotion queue documented above)
- B62 within-V64-A rebadge anchor: `decisions/2026-05-15_v64_sub_case_011_nondegen_ratify.md`
- 18 V64-A sub-DECs: see V64-A close DEC §4 table
- 16 V64-A validation reports: see V64-A close DEC §5 table

---

**End of V64-A arc-close retrospective.** V101+ promotion queue + V65 theme selection criteria + arc-wide lessons documented for V65 charter sub-DEC input. V65 charter authoring deferred to dedicated sub-DEC (this retro is input; charter is the authoring artifact).

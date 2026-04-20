# Q-new: Whitelist B-class gold-value remediation (5 cases)

**Filed**: 2026-04-20T20:55 by claude-opus47-app (Sole Primary Driver under v6.1)
**Upstream DECs**: DEC-V61-004 (C1+C2 infra fixes) · DEC-V61-005 (A-class metadata)
**Related**: Q-1 (DHC gold — single-case subset of this gate), Q-2 (R-A-relabel pipe→duct)
**Blocking class**: Hard floor #3 — `knowledge/whitelist.yaml` `reference_values` edit required (禁区 #3)
**Decision requester**: Kogami (T0)
**Autonomy status**: **EXPLICITLY STOPPED** per DEC-V61-003 §8 and handoff §7 rule #3

---

## Why this is a gate, not autonomous turf

Under DEC-V61-003:

> "knowledge/whitelist.yaml 的 reference_values 字段同样受 gate 保护"

This gate is filed instead of self-approving the edits because:

1. Each of the 5 cases requires a literature re-sourcing decision (which paper's Cf / Nu / u+ to cite as canonical).
2. For two cases (Turbulent Flat Plate, Plane Channel), the correction also implies a **tolerance** change, which is not on the autonomous-metadata allowlist.
3. The DHC Ra=1e10 subset overlaps Q-1 (already on the queue) — this gate request explicitly unifies the five-case package so Kogami can decide the whole set coherently rather than piecemeal.

---

## Per-case summary

Taken from `docs/whitelist_audit.md` §5.2. Literature positions noted below are the audit's best-effort re-sourcing; final citations should be vetted by Kogami before committing.

### Case 4 — Turbulent Flat Plate (ZPG, Re_x = 25 000)

- **Current gold**: Spalding composite law `u+ = f(y+)` family (k-ω SST)
- **Audit finding**: Re_x = 25 000 is **laminar** (transition to turbulent onset ~Re_x = 3e5 to 5e5 on smooth plate). Spalding's composite law doesn't apply; correct reference is Blasius laminar BL.
- **Proposed correction**:
  - Either **(a)** change `turbulence_model: k-omega SST` → `laminar` *and* replace gold with Blasius `Cf = 0.664 / sqrt(Re_x)` → 0.00420 at Re_x=25 000 (reference value 0.664 comes from Blasius similarity solution; see Schlichting 7th ed. Ch.7);
  - Or **(b)** raise Re_x target into turbulent regime (e.g., Re_x = 1e6) and retain Spalding with updated gold `Cf ≈ 0.0046` (Coles-Prandtl 1/7 power-law).
- **Audit preference**: (a) — laminar is the smaller, more reversible change and better matches the "simple, well-known benchmark" role the case plays in the 10-case matrix.

### Case 6 — Differential Heated Cavity (DHC) at Ra = 1e10 (OVERLAPS Q-1)

- **Current gold**: `ref_value = 30.0` (Nu_avg on hot wall)
- **Audit finding**: Ra = 1e10 2D DHC literature (Ampofo & Karayiannis 2003, Dixit & Babu 2006) gives Nu ≈ 120–325 depending on BL resolution. 30 is inconsistent with Ra stated.
- **Proposed correction** (same two paths as Q-1 originally):
  - **Path P-1**: update ref_value to ~120–160 (Dixit & Babu 2006 DNS range); expand tolerance to ±25% to cover 256² mesh BL-resolution gap;
  - **Path P-2**: downgrade Ra target from 1e10 to 1e6–1e7 where Nu ≈ 10–20 is both well-documented and mesh-resolvable;
- **Relation to Q-1**: this subsumes Q-1. If Kogami picks P-1 or P-2 here, Q-1 can be closed with the same decision.

### Case 8 — Plane Channel DNS (Re_τ = 180)

- **Current gold**: `u+ @ y+=30` = 14.5
- **Audit finding**: Moser, Kim & Mansour 1999 DNS at Re_τ = 180 tabulates `u+(y+=30) ≈ 13.5` (log-law region; κ = 0.41, B = 5.2 gives `u+ = (1/0.41)·ln(30) + 5.2 = 13.49`).
- **Proposed correction**: `u+ @ y+=30` → 13.5 with tolerance 3–5% (Moser DNS uncertainty).

### Case 9 — Axisymmetric Impinging Jet (Re = 10 000, h/d = 2.0)

- **Current gold**: `Nu @ r/d=0` = 25.0, `Nu @ r/d=1.0` = 12.0
- **Audit finding**: Behnad et al. 2013 experimental PIV/TLC correlations at these conditions give `Nu @ r/d=0 ≈ 110–130` (stagnation region); `Nu @ r/d=1.0 ≈ 60`. Current gold is inconsistent — either citing wrong Re, wrong h/d, or wrong geometry (free jet vs. confined).
- **Proposed correction**: re-source against Cooper et al. 1993 or Behnad et al. 2013 for the stated (Re=10000, h/d=2.0) configuration; tolerance remains 15% if the re-sourced values match a single canonical paper.

### Case 10 — Rayleigh-Bénard Convection (Ra = 1e6, Pr = 0.71)

- **Current gold**: `Nu = 10.5`
- **Current metadata (post DEC-V61-005)**: `turbulence_model: laminar` ✅
- **Audit finding**: Chaivat correlation `Nu = 0.229 · Ra^0.269` at Ra = 1e6 gives Nu ≈ 7.2 (not 10.5). Current 10.5 may be citing a different reference or correlation variant.
- **Proposed correction**: Verify which correlation is being cited; either update ref_value to 7.2 (Chaivat) or to the correct value from the stated reference (`Chaivat et al. 2006`, DOI `10.1016/j.ijheatmasstransfer.2005.07.039` — needs re-examination).

---

## Requested Gate decision surface

For each of the 5 cases, Kogami picks one of:

| Option | Action |
|---|---|
| **A** | Apply audit-proposed correction verbatim |
| **B** | Apply audit-proposed correction with Kogami-specified tolerance adjustment |
| **C** | Hold — further literature re-sourcing required before any edit |
| **D** | Decline — current gold value is correct; audit misread the literature |

---

## If approved

Self can:

1. Edit `knowledge/whitelist.yaml` `reference_values` (and `tolerance` where specified) per the approved per-case decision.
2. Edit `knowledge/gold_standards/*.yaml` if a gold file exists for the case (Case 6 DHC is the most likely; others may not have separate files).
3. Land as PR #6 with title `fix(whitelist): B-class gold-value remediation (5 cases per Gate Q-new)`.
4. Write DEC-V61-006 recording the Gate decision verbatim + link to the approving message/page.
5. Update `docs/whitelist_audit.md` §5.2 changelog.
6. Regenerate auditor baselines if needed (one test file expected to touch: `tests/test_auto_verifier/test_task_runner_integration.py` fixtures may need refresh).

## Reversibility

If the Gate decision later proves wrong, one `git revert -m 1 <merge-sha>` of PR #6 restores pre-gate whitelist state. All edits are numeric — no schema changes, no new cases added, no cases removed.

---

## What is NOT in this gate

- C1+C2 infra fixes (landed autonomously in PR #4 per DEC-V61-004)
- C3 sampleDict auto-gen (deferred, design session pending — `src/` turf, autonomous)
- A-class metadata corrections (landed autonomously in PR #5 per DEC-V61-005 — `turbulence_model` field only)
- R-A-relabel pipe→duct (Q-2, separate gate — different case, different blocking class)

The three autonomous classes are **independent** of this gate. Dashboard improvements from C1/C2 + A-class will land regardless of Kogami's B-class decision. This gate only controls whether the five remaining golden-dashboard cases can move toward PASS.

## Ping

**Action required from Kogami**: review this gate, make per-case decision on the 5 cases in `## Per-case summary`, and reply on any surface (Notion Decisions DB, GitHub discussion on PR #4/#5, direct message). Once the decision is received I will land PR #6 with DEC-V61-006 mirroring.

**Blocking until**: Kogami reply received OR explicit waiver.

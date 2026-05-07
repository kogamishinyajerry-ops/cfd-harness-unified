# Advisor coverage matrix · 2026-05-08

> **Snapshot**: harvest cycle 001. Inventory of landed vs pending
> advisors crossed against case exercise pressure.

## Landed advisors (in `ui/backend/services/geometry_ingest/`)

| File | Advisor | Origin | Cases that exercise (live or queued) | Live falsification data |
|---|---|---|---|---|
| `geometry_surgery.py` | A3 — decimate-by-tier + axial stretch | DEC-V61-198 (APU bay V8) | case_005 D2 (queued, deferred) | None yet — case_005 sub-session deferred |
| `thin_wall_advisor.py` | V10 advisor — bbox-min vs cell-size warning | case_002b inheritance forced extraction (Pillar 2 in action) | case_002a/b (live), case_004 D8, case_007 D8, case_008 D8, case_010 D8 (all queued) | case_002a/b only; 4-case industrial trial pending |
| `stl_loader.py` | (utility) — STL parsing | (legacy) | All cases reuse | (utility, not advisory) |
| `patch_detector.py` | Patch type classification | (legacy) | All cases reuse | (utility) |
| `health_check.py` | STL watertight check | (legacy) | All cases reuse | (utility) |

## Pending advisor extractions (from DEC-V61-198 5-artifact list)

| Artifact | Destination | Compounded case pressure | Score = cases × impact / LOC | Priority |
|---|---|---|---|---|
| **A2** — `virtual_interface_detector.py` | `ui/backend/services/geometry_ingest/` (new) | **6 confirmed (003-008) + 2 expected (009-010)** | 8 × HIGH / ~150 LOC = **highest** | **EXTRACT NOW** |
| A1 — `cad_ingest_freecad.py` | `ui/backend/services/geometry_ingest/` (new) | 1 (case_002a only); cases 003-010 use CadQuery, not CATIA STEP | 1 × MED / ~80 LOC = low | DEFER until next CATIA case |
| A4 — mass conservation pre-flight | extends `case_bc/writer.py` | 1 (preventive in case_002a); none of 003-010 explicitly exercise | 1 × MED / ~50 LOC = low | DEFER until multi-inlet/multi-outlet case appears |
| A5 — solver convergence playbook | `.planning/methodology/solver_convergence_playbook.md` | LANDED already (S1-S12) | n/a | DONE |

## A2 extraction recommendation

**Decision recommendation**: Extract A2 in next implementation
window, regardless of when sub-sessions for cases 003-010 actually
run. Rationale:

1. **8-of-8 case pressure** is overdetermined; even if 50% of
   cases never run, A2 still has 4× compounded evidence — well
   above the 3-instance bar
2. **Source code already exists** in APU bay `02_domain_subtract.py`
   (`INTERFACE_SPECS` block with `mode: shared`). Extraction is
   refactor + generalize, not greenfield design
3. **Refactoring cost low** (≤250 LOC per V133 sub-DEC scope)
4. **Each deferred case gets cleaner V-finding signal** post-A2 —
   sub-sessions can validate against landed advisor instead of
   manually verifying with FreeCAD `distToShape`
5. **Defect distribution will rebalance** — Codex picks D1 in
   nearly every case partly because A2-pending creates a
   "sticky" force-extraction signal. Once A2 lands, future
   case briefs can pick D-defects more diversely (D3, D5, D6
   are under-exercised)

Proposed scope (single sub-DEC, <250 LOC):
- Geometric face matching: bbox overlap > 80%, area diff < 5%,
  normal dot product < -0.5 (per V2 finding)
- Two modes: `shared` (interface) and `endcap` (per APU bay
  precedent)
- Unit tests: synthetic 2-body fixtures with known-overlap and
  known-mismatch
- Wire into existing CAD-ingest pipeline (no new public route)

## D8 / thin_wall_advisor consistency trial (pending)

| Case | D8 geometry | Bbox min | Industrial topology |
|---|---|---|---|
| case_004 | yaw_sensor_shim | 0.75 mm | Stationary aux on rotor nacelle |
| case_007 | thin transom plate | 0.80 mm | Ship hull above waterline |
| case_008 | trailing_edge_tab | 0.80 mm | Airfoil TE |
| case_010 | underbody_sensor_cover | sub-mm | Vehicle underbody |

When all 4 sub-sessions run, the advisor will see 4 distinct
geometry classes. Convergent behavior → V10 closes (advisor
field-validated). Divergent → new V-finding "advisor topology
sensitivity," potential A3-class follow-up advisor.

This is queued data we can't act on until sub-sessions run.

## A3 / geometry_surgery first-falsification (pending)

case_005 D2 = 102,400-triangle throat-liner overlay. Sub-session
will exercise A3's decimate-by-tier on industrial-flavored
over-dense input (not toy fixture).

Outcomes worth instrumenting:
- A3 produces sane decimated mesh AND flags the overlay → V10b
  "advisor field-validated"
- A3 silent / produces broken mesh → V-finding "A3 toy-case
  bias" → exactly the Pillar 2 stale-assumption fix the new
  philosophy describes

case_005 sub-session not yet running → falsification deferred.
Worth flagging to user as "first sub-session to run after
A2 lands should be case_005, to maximize advisor-exercise yield
per harvest cycle."

## Defect-catalog distribution observed

| Defect | Cases targeting | Advisor mapping | Notes |
|---|---|---|---|
| D1 (sub-mm gap) | 003-010 (all 8) | virtual_interface_detector (A2-pending) | **Over-selected** — likely artifact of "Codex prefers known unknowns" pattern |
| D2 (over-dense) | 005, 009 | A3 (LANDED) | Healthy distribution |
| D4 (sliver) | 006 | A3 (likely wrong mapping per validation) | Single instance; advisor fit questionable |
| D5-D7 | none | (various) | **Under-exercised** — corrective opportunity |
| D8 (thin shell) | 002b, 004, 007, 008, 010 | thin_wall_advisor (LANDED) | Strong consistency trial |
| D9 (over-aggressive simplification) | none | (none) | **Under-exercised** |
| D10 (open shell) | none | health_check (LANDED) | **Under-exercised** |

After A2 lands, future case briefs should target D3/D5/D6/D7/D9/D10
to broaden defect-catalog coverage. Suggest adding a "defect
diversity" requirement to `codex_case_design_protocol.md` once
6-of-6 D1 saturation is acknowledged.

## References

- `.planning/methodology/component_bank.md` — defect catalog SSOT
- DEC-V61-198 — 5-artifact extraction list
- per-case `kickoff/case_*_validation.md` — advisor mapping evidence

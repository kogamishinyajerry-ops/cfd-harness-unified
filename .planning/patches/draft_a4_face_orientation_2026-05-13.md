# A4 face_orientation advisor · draft patch

**Status**: drafted · awaiting 2nd-case evidence (case_013 D7 sub-session)
**Parent milestone**: M-A4 (advisor_substrate_arc Tier 1)
**Sediment source**: V79 (case_012 D7 · 2026-05-12 backfill)
**Drafted**: 2026-05-13 by Claude Code Opus 4.7 (M-A4 research deliverable)
**Sister candidates**: A6 (`draft_a6_adpi_post_processor_2026-05-09.md`) · A8 (`draft_a8_shm_dict_validator_2026-05-09.md`)

---

## 1. Defect class (what A4 detects)

**Component-orientation defect** — a body whose dominant face normal deviates from declared/sibling-consensus orientation by more than a per-group tolerance.

**Distinct from existing advisors**:
- A1 (canonicalizer) — STEP unit / coordinate canonicalization · doesn't look at face normals
- A2-v2 (`_run_shared` gap detection) — face-pair shared-interface detection · consumes orientation, doesn't flag orientation as defect
- A3 (`geometry_surgery`) — face-count decimation · orientation-agnostic
- A7 (`step_canonicalizer`) — STEP FILE_NAME byte-determinism · file-level not geometry
- thin_wall_advisor — extreme-thinness · orientation-agnostic

A4 is the **first orientation-as-defect-signal** advisor in the stack.

---

## 2. Reference verification primitive (case_012 manual path)

`~/Desktop/case_012_hvac_supply_diffuser/scripts/check_face_normal.py` (~120 LOC) is the manual verification used to confirm V79's `38.000°` measurement. It:

1. Loads STEP via FreeCAD `Import.insert`
2. Finds the **largest planar face** per body (filters by `surf.__class__.__name__.endswith("Plane")`)
3. Computes outward normal at the parametric midpoint via `face.normalAt(u_mid, v_mid)`
4. Compares to intended normal via dot product → angle in degrees
5. Pass/fail on `tolerance_deg` (default 2.0° in case_012)

**Takeaway for A4**: the algorithm is settled. The advisor is mostly "wrap the primitive + read intended-normal source-of-truth from parts manifest".

---

## 3. Proposed API surface

**Location**: `ui/backend/services/geometry_ingest/face_orientation_advisor.py` (same dir as A1/A2-v2/A3/A7 — four-plane Lower Plane / `services/` layer)

```python
from dataclasses import dataclass
from typing import Iterable, Optional

@dataclass(frozen=True)
class FaceOrientationFinding:
    body_name: str
    intended_normal: tuple[float, float, float]
    actual_normal: tuple[float, float, float]
    angle_deviation_deg: float
    tolerance_deg: float
    severity: str  # "info" | "warning" | "critical"


@dataclass(frozen=True)
class FaceOrientationReport:
    findings: tuple[FaceOrientationFinding, ...]
    bodies_checked: int
    bodies_with_intended_normal: int  # how many had a declared normal in manifest
    bodies_skipped: int  # no planar face / no manifest entry / etc.


def check_face_orientation(
    parts_manifest: PartsManifest,
    *,
    default_tolerance_deg: float = 5.0,
    per_body_tolerance_deg: Optional[dict[str, float]] = None,
) -> FaceOrientationReport:
    """Flag bodies whose dominant face normal deviates from
    declared/sibling-consensus orientation.

    Inputs (via parts_manifest):
        - body.shape (FreeCAD Shape or path to STL/STEP)
        - body.expected_face_normal: tuple[float, float, float] (optional)
        - body.sibling_group: str (optional, e.g., "louver_vanes")

    For bodies with `expected_face_normal`: compare directly.
    For bodies with `sibling_group` (and no expected normal): compute
    consensus from siblings (median per-axis), compare each member.
    For bodies with neither: skipped (counted in `bodies_skipped`).

    Severity mapping:
        angle ≤ default_tolerance_deg → not reported
        default_tolerance < angle ≤ 2·default → "warning"
        angle > 2·default → "critical"
    """
    ...
```

---

## 4. Parts manifest schema delta

Add 2 optional fields to `PartsManifest` body entries:

```yaml
- name: louver_vane_2
  expected_face_normal: [0.0, -1.0, 0.0]   # NEW · A4 input
  sibling_group: louver_vanes              # NEW · A4 input (alternate)
  # … existing fields unchanged
```

If both fields present → `expected_face_normal` wins.
If neither → body is skipped by A4.

Schema delta is **additive only** · no contract break · sub-DEC scope-friendly.

---

## 5. Cross-topology promotion gate status

A4 cannot LAND until 2 cross-topology cases inject the defect (per `advisor_candidates_a4_a8.md` promotion-gate convention, same as V25→A2-v2):

| Case | Topology | D7 injection | Manual verification | Status |
|---|---|---|---|---|
| **case_012** | HVAC supply diffuser (incompressible-RANS) | ✅ `louver_vane_2` 38° rotation | ✅ `check_face_normal.py` (38.000° exact) | sediment-confirmed |
| **case_013** | dispatched-deferred (Phase 2 #1) | ⏳ pending sub-session | ⏳ pending | **BLOCKER** |

**M-A4 unblock path**:
1. Dispatch case_013 sub-session with D7 injection
2. Sub-session lands → 2 cross-topology evidence achieved
3. Promote A4 from `drafted` → `ready-to-land`
4. Implement per this patch
5. Sub-DEC under V61-198 (same pattern as V61-198-sub-A2v2 / sub-A7)

---

## 6. Implementation scope estimate

| Item | LOC est | Notes |
|---|---|---|
| `face_orientation_advisor.py` | ~120 | Mirrors `check_face_normal.py` primitive + parts-manifest integration |
| Parts manifest schema fields | ~5 | Additive only |
| Unit tests (`tests/services/test_face_orientation_advisor.py`) | ~150 | 4-6 tests: 1 sibling-consensus / 2 declared-normal / 1 below-tol / 1 above-tol / 1 missing-manifest-skip |
| Plumb into `/ai-review` route | ~10 | Per A2-v2 / A7 pattern |
| Sub-DEC document | ~200 lines markdown | Parent V61-198 · counter +1 (autonomous_governance: true) |

**Total**: ~285 LOC code + 200 lines DEC. **sub-DEC scope**, not spike-class (>30 LOC + schema delta).

---

## 7. Risk register

| Risk | Mitigation |
|---|---|
| **R1** Sibling-consensus algorithm is sensitive to a single rotated body misleading the consensus | Use median per-axis (robust against 1 outlier in group ≥ 3); document group ≥ 3 requirement |
| **R2** Largest-planar-face heuristic fails for curved-dominant bodies | Skip + report (don't try to flag a body whose dominant face isn't planar) |
| **R3** Floating-point precision of FreeCAD normals | Use `tolerance_deg` not `tolerance_dot_product`; 5° default has ~ 0.4% dot-product margin |
| **R4** case_013 sub-session never lands → A4 permanently `drafted` | If 3 weeks no case_013 progress, re-evaluate: either dispatch differently OR land A4 single-case with `[QUESTIONABLE]` status per V79 (same as A2 went through pre-V25) |

---

## 8. Next session pickup

Run order when M-A4 unblocks:

1. ✅ This patch exists (research deliverable · 2026-05-13)
2. ⏳ case_013 D7 sub-session dispatch + land (BLOCKS)
3. ⏳ Cross-topology evidence ≥ 2 confirmed
4. ⏳ Promote `drafted` → `ready-to-land` in `advisor_candidates_a4_a8.md`
5. ⏳ Implement per §3 + §4
6. ⏳ Tests per §6
7. ⏳ Sub-DEC `2026-XX-XX_v61_198_sub_a4_face_orientation.md`
8. ⏳ Commit · `feat(geometry_ingest/A4): land face_orientation_advisor · V79 closure (parent_dec V61-198 · sub-DEC V61-198-sub-A4)`
9. ⏳ Update ARC-GOAL.md M-A4 row with commit hash

If main session decides to land A4 single-case (skip case_013 wait) — that's a methodology-relaxation decision, document in a sub-DEC note and accept the `[QUESTIONABLE]` status until 2nd case lands.

---

## 9. Cross-references

- **V79** in `industrial_solver_findings_v_series.md` — defect-class sediment + ground truth (38.000°)
- **case_012** at `~/Desktop/case_012_hvac_supply_diffuser/`
- **`check_face_normal.py`** — algorithm reference (case_012 scripts/)
- **`advisor_candidates_a4_a8.md`** — promotion-gate convention SSOT
- **`advisor_coverage_2026-05-09.md`** — A-number allocation SSOT (A4 reserved)
- **DEC-V61-198-sub-A2v2** / **sub-A7** — sub-DEC pattern to follow
- **ARC-GOAL.md** M-A4 row — tracking

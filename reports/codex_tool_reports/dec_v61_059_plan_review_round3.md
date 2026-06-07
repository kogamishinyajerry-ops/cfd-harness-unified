# DEC-V61-059 — Codex round-3 review summary

- **Branch**: `dec-v61-059-pc` (commits 48cf994 → 0a649d7, post round-2 fixes)
- **Reviewer**: Codex CLI v0.118.0, model `gpt-5.4` (forced via `-c model="gpt-5.4"`), reasoning effort xhigh
- **Account**: ramaiamandhabdbs@gmail.com (score 48% remaining at run start)
- **Invocation**: `codex review --base origin/main -c model="gpt-5.4"`
- **Verdict tier**: P2 + P3 — 2 findings; **NOT a clean close** (round-4 needed for clean APPROVE)
- **Trend**: severity is monotonically dropping (round-1: 2×P2 → round-2: 1×P1 + 1×P2 → round-3: 1×P2 + 1×P3). Round-2's P1 was the cross-plane integration gap; once fixed, round-3 only finds finer-grained tightening.

## Findings

### F5 [P2 / MED] — `src/comparator_gates.py:414-415` — log-law band too loose

**Issue (verbatim from Codex):**
> The new two-region safeguard is looser than the surrounding comment
> describes. `has_loglaw = any(yp >= 30.0 ...)` counts the `y+=100`
> centerline reference as "log-law", so a plane-channel profile that
> matches only `y+=5` and `y+=100` (but clearly misses the real `y+=30`
> log-law point) still emits `CANONICAL_BAND_SHORTCUT_LAMINAR_DNS`.
> That creates false hard-fails for profiles whose viscous and centerline
> values happen to land near the canonical band without actually
> reproducing the log-law region.

**Impact:** False-positive risk. A laminar profile that coincidentally
matches u+ at y+=5 (viscous sublayer is naturally u+≈y+) AND at y+=100
(centerline u+ depends on Re_b) but misses y+=30 (log-law) would still
fire G2. Real laminar profiles often DO land near canonical at exactly
those endpoints (sublayer is identical; centerline can match by Re_b
coincidence) without ever passing through the canonical log-law point.
The gate would then false-FAIL legitimate "off-target Re_b" laminar runs
that are not unit-mismatch shortcuts.

**Fix (committed in this round):** Tighten `has_loglaw` to
`any(10.0 < yp < 60.0)`. The canonical log-law band where
`(1/0.41)·ln(y+)+5.2` governs runs roughly y+ ∈ (10, 60); centerline
y+≥60 is its own asymptotic regime and cannot stand in for log-law
evidence. Now G2 requires viscous (y+≤10) AND log-law (10<y+<60),
matching the docstring intent.

**Tests:**
- `test_g2_silent_when_only_viscous_and_centerline_hit_no_loglaw` —
  profile hits y+=5 (u+=5.4 canonical) AND y+=100 (u+=18.3 canonical)
  but at y+=30 sits at u+=8.0 (rel_err 0.41, far outside tolerance).
  Asserts G2 does NOT fire.
- `test_g2_fires_when_actual_loglaw_y_plus_30_is_hit` — companion
  positive case: y+=30 hits canonical 13.5 → G2 fires (regression
  preventing F5 from over-tightening).

### F6 [P3 / LOW] — `scripts/phase5_audit_run.py:639-646` — G2 gated on phase7a artifacts

**Issue (verbatim):**
> G2 is described here as artifact-independent, but the entire
> `check_all_gates(...)` call is still nested under `if phase7a_timestamp
> is not None`. In the existing direct-call mode of `_audit_fixture_doc()`
> where `phase7a_timestamp=None` (for example the helper-style calls in
> `ui/backend/tests/*`), a plane-channel report with canonical-band
> `u+/y+` will never append `CANONICAL_BAND_SHORTCUT_LAMINAR_DNS`, so
> this helper can still surface PASS/HAZARD for the exact shortcut
> DEC-V61-059 is supposed to block. Only G3/G4/G5 need the Phase 7a
> artifacts; G2 can run whenever `case_id` and `kq` are present.

**Impact (P3):** Lower severity than F5 because the affected code
path is a test/helper surface, but a real correctness gap: the
`ui/backend/tests/*` helpers exercise `_audit_fixture_doc()` directly
without phase7a artifacts, and the round-2 F3 verdict-engine fix
relies on G2 emit reaching `audit_concerns[]` via this driver.

**Fix (committed in this round):** Lift the gate battery call out
from the `if phase7a_timestamp is not None:` wrapper. `check_all_gates`
already has correct semantics — G3/G4/G5 silently no-op when
log_path/vtk_dir are None, G2 runs whenever case_id+kq are present.
The phase7a guard now only nulls the log_path/vtk_dir args before
forwarding (so G3/G4/G5 don't try to read non-existent files), but
G2 always runs on the canonical id + key_quantities pair.

## Calibration trend

| Round | Self-est | Actual | Findings | Severity max |
|-------|----------|--------|----------|--------------|
| 1     | 0.40     | ~0.55  | 2        | P2           |
| 2     | (post-fix expected clean) | not clean | 2 | **P1** |
| 3     | (post-fix expected clean) | not clean | 2 | P2 |

The Codex pessimism is converging — round-2's P1 was a structural gap
(verdict-engine wiring) that any reviewer reading the diff in
isolation would miss without exercising the full pipeline. Round-3's
findings are about *invariant tightening* (F5) and *driver wiring*
(F6), both surfaced once the structural integration was already in
place. The "clean close at round 3" precedent from V61-053 is not
universal — V61-053 was a Type III with a single Strouhal scalar;
V61-059's Type II with cross-plane gate plumbing is structurally
deeper.

## Round-4 readiness

- F5 + F6 fixes landed (this commit)
- 75 DEC-V61-059 tests green (+2 round-3 regressions: viscous+centerline-only-no-fire,
  loglaw-hit-still-fires)
- Codex budget remaining: **1 round** (per intake §8: 4-round soft target,
  rounds 1+2+3 spent; round 4 is the planned-checkpoint round, not
  early halt; round 5 = halt_risk_flag, round 6 = abandonment).
- Round-4 should be the clean-close. If it returns CHANGES_REQUIRED,
  intake §8 directs round-5 health-check before any further fixes.

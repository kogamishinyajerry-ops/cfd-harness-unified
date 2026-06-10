# Codex round-3 overflow · V73.A transonic-SBLI scaffold (DEC-V61-238)

- date: 2026-06-10
- chain: R0 CHANGES_REQUIRED (P1+2×P2) → fix d3309bb → R1 CHANGES_REQUIRED
  (P1+P2, both introduced by the R0 fixes) → fix 31eb107 → R2 CHANGES_REQUIRED
  (P1+P2, both against the R1 asymmetric band) → **cap=3 reached**.
- reports: `reports/codex_tool_reports/2026-06-10_v73a_scaffold_R{0,1,2}.md`

## What remains open for USER ratification

R2's two findings were FIXED in the cap-closing commit (vertex-recovered
chord + tight 2% symmetric band + unbiased x/c frame; 6 new regressions;
190 passed) — in exactly the direction Codex prescribed ("reject under-sized
surfaces", "renormalize before reporting x/c") — but per round cap=3 there is
NO R3 re-review of that fix. Options:

1. **Ratify as-is** (recommended): the fix is prescription-aligned, fully
   regression-pinned, and V73.B's live probe will exercise the exact
   face-centre path against real solver output — any residual defect surfaces
   there with frozen evidence.
2. Order a discretionary R3 spot-review of the closing commit (outside cap).

## Why three rounds (retro note)

R1 and R2 both bit on MY fix iterations, not the original scaffold: the
snapshot/origin fixes were right, but my first chord-guard relaxation traded
fail-closed-ness for coarse-mesh tolerance. The durable lesson (matches the
MicroCOMAC fail-safe canon): **when a guard must tolerate a legitimate
physical effect, bound the tolerance BY the effect's own data-derived
magnitude (end-face half-lengths here), never by a global constant** — a
global band either false-rejects (2%) or opens a smuggling window (10%).
Candidate intake-template risk_flag: "guard relaxation without a data-derived
bound".

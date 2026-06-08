# Codex Tool Report — DEC-V61-232 · P4 wedge oblique-shock V&V scaffolding

- **Relay backend**: 86gamestore (`~/.codex-relay`), model `gpt-5.4`, reasoning `xhigh` (governance baseline, RETRO-V61-001).
- **Command**: `codex review --base d966ba5` (the exact P4 diff: commits `c9ee2aa`..HEAD).
- **Round cap**: 3 (R0 + 2 fix iterations). **Outcome: CLOSED within cap — all P1 resolved.**
- **Raw logs**: `v61_232_p4_wedge_scaffolding_report_raw.txt` (R0), `_r1_raw.txt` (R1), `_r2_raw.txt` (R2).
- **Adversarial pre-pass**: in-house red-team workflow `wig61u2wt` (5 attackers + triage) → verdict **HELD** (0 real holes); fixed a 4→5 hard-gate doc miscount; logged 2 deferred hardenings.

## Round-by-round

### R0 — CHANGES_REQUIRED (2 findings) → fix `3c65256`
- **[P1] wedge-wall β offset** (`wedge_oblique_shock_extractor.py`): a shockLine sampled
  from the wedge wall reports height above the wall, not the apex; `atan2(y, x)` omitted
  the `x·tanθ` offset → a correct 45° shock read ~36°. The step-function fixture hid it.
  **Fix**: `shock_line_origin_y` param + gold field; `β = atan2(origin_y + dist, x)`.
- **[P2] probe-name contract** (`...extractor.py`): gold publishes singular regions
  `freestream`/`postShock`, but the extractor hardcoded 8 private per-field dirs → a
  contract-authored bundle would `FileNotFoundError`. **Fix**: read the named region
  probes as multi-field `surfaceFieldValue.dat`, column order discovered from the header;
  fixture regenerated to the 2-probe layout.
- **[P2] deep_acceptance manifests** — PRE-EXISTING regeneration noise, out of P4 scope
  (see R2 disposition).

### R1 — CHANGES_REQUIRED (2 findings) → fix `9f9d38f`
- **[P2] `_find_xy` arbitrary `.xy`**: a live shockLine writes rho alongside p/U; same
  sort key → `matches[-1]` filesystem-arbitrary → β from the wrong field. **Fix**: select
  the latest-time `.xy` carrying the density field token (`shock_line_field`, default
  `rho`); ambiguous → fail closed.
- **[P1] 25%-of-total-variation guard rejected smeared shocks**: rhoCentralFoam smears a
  shock over several cells, so no single step holds 25% → a correct live profile failed
  closed. **Fix**: localised-steepening guard (peak slope ≥ 3× mean slope — rejects flat
  fields + smooth ramps, admits smeared shocks) + LOCATE at the 50%-rise crossing
  (unbiased for a smeared front; the peak-step alone sits at the smear edge).

### R2 — 1 P1 (verbatim) + 1 P2 (pre-existing) → fix `9ed18aa`
- **[P1] lone `.xy` bypassed field validation**: a single non-density file (only
  `line_p.xy`) was accepted unconditionally → β from pressure. **Fix (applied verbatim,
  no 4th round per the round-cap-3 verbatim-exception)**: EVERY selection must positively
  carry the density field token; a lone non-matching file raises. Documented the 2-column
  `.xy` assumption (multi-field single `.xy` column-resolution deferred to the live slice).
- **[P2] deep_acceptance `*_manifest.json` provenance**: PRE-EXISTING auto-regeneration
  noise (`generated_at`/`head_sha`/`branch_name`/timestamp paths only; `case_count` and
  `class_counts` content unchanged), predating this session, unrelated to P4. **Disposition**:
  reverted to the committed state to clean the working tree; not a P4 code issue.

## Net verdict

**APPROVE-equivalent — chain CLOSED within cap=3, all P1 resolved.** Every Codex finding
was a live-replay-robustness gap the offline synthetic fixture could not expose — the
exact value of cross-family review on scaffolding-first work. The honesty-critical
invariants (anti-tautology extractor, fail-closed gate, no overclaim, self-verifying gold,
four-plane purity) were never breached across any round. Final: 28 p4 tests green, 367 p3
no-regression, four-plane law + `.importlinter` byte-repro in sync, extractor Execution-pure
(stdlib-only). Two forward-hardenings (6th cross-consistency gate; multi-field `.xy`
column-resolution) deferred to the LIVE rhoCentralFoam slice with the Docker/ESI provision.

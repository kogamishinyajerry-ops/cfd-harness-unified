# Codex Tool Report — DEC-V61-233 · P4 LIVE rhoCentralFoam wedge (V&V validation)

- **Relay backend**: 86gamestore (`~/.codex-relay`), model `gpt-5.4`, reasoning `xhigh` (governance baseline, RETRO-V61-001).
- **Command**: `codex review --uncommitted` (the staged live-flip slice vs HEAD `2bb68ee`).
- **Round cap**: 3 (R0 + 2 fix iterations) — **chain CLOSED at R2** (R2 found no functional regression; only P3 doc-hygiene on this report, fixed in place).
- **Raw logs**: `_r0_raw.txt` / `_r1_raw.txt` / `_r2_raw.txt` are **local-only** (gitignored via `.gitignore:92 reports/codex_tool_reports/*.txt` — they contain the full diff + scratch). **This tracked `.md` is the canonical, self-contained review trail**; the raw logs are not needed to read it (Codex R2 P3-1).
- **In-house adversarial pre-pass**: red-team workflow `wjjm4tbtp` (5 distinct lenses + triage) →
  verdict **HELD** (0 real holes); fixed 2 cosmetic nits inline (stale "five hard gates" docstring → six;
  added `SHA256SUMS` tamper-manifest to the frozen probe).

## The headline correction this review forced

The slice was authored claiming it **flipped runnable-coverage 2 → 3**. Codex R0 correctly showed
that claim is an **overclaim**, and the artifacts were corrected to the honest outcome:
**the rhoCentralFoam V&V benchmark is LIVE-VALIDATED, but runnable-coverage STAYS 2.**

Per Blueprint v4 **Law-1** + the P4-inherited **DEC-V61-224(b)** provision, "runnable" requires the
workbench **execution backend (`foam_agent_adapter`) wired to the image AND reconciled with the
`cfdtrust` V&V backend** — not merely a solver run. This slice ran `rhoCentralFoam` **directly in a raw
container**, bypassing both backends (the adapter has no density-based routing branch;
`cfdtrust/backends/openfoam.py` hardcodes `simpleFoam`). The W3.3b precedent (the 1→2 flip) is NOT
exculpatory: the adapter HAS a CHT routing branch (`GeometryType.CHT_MULTI_REGION →
chtMultiRegionSimpleFoam`), so CHT met the workbench-runnable bar; the wedge does not.

## Round-by-round

### R0 — 2× P2 (no P1) → both ADDRESSED (documentation/framing honesty corrections)

- **[P2-1] Capability-matrix overclaim** (`.planning/cfd_capability_matrix.md:41`): marking
  `rhoCentralFoam` **✅ PR** / "runnable-coverage compute types = 3" asserts the workbench can run it
  end-to-end (the matrix's own definition + anti-fraud charter §6), which is false.
  **Fix**: reverted to **GAP-TRACKED** with an explicit "V&V benchmark LIVE-VALIDATED" note; Solvers PR
  stays 6/10; **runnable-coverage stays 2**; the flip is gated on the deferred backend wiring. The same
  honest framing was propagated to DEC-V61-233 (title/body/closing), STATE.md (ANCHOR-36), RESUME.md
  (MOST RECENT), the gold header comment, the gate-test docstring, and REPRODUCE.md.
- **[P2-2] `validation_status` is dead metadata** (`knowledge/gold_standards/wedge_oblique_shock.yaml`):
  no `src/`/`ui/`/`scripts/` consumer reads `case_info.validation_status`; existing gold-status consumers
  (`report_engine/contract_dashboard.py`, `error_attributor.py`, `scripts/preflight_case_visual`) read
  `physics_contract.contract_status`. **Fix**: kept the key (renamed to `validation_status` to avoid
  colliding with that load-bearing `physics_contract.contract_status`) but **reframed it honestly** — it
  is a **test-enforced honesty invariant** (the gold self-test reads it and blocks an un-run reference
  being machine-read as validated) **plus a forward hook**, NOT a claim that production coverage tooling
  reads it today. Comments/DEC/tests updated to say exactly that.

### R1 — confirmation re-review → 1 NEW P2 (a test-rigor gap R0 missed) → ADDRESSED

R1 confirmed the R0 corrections (coverage framing + `validation_status`) and surfaced one
genuinely new gap the headline rewrite had created:

- **[P2-R1] θ=10 discrimination test passes for the wrong reason**
  (`tests/p4/test_wedge_oblique_shock_gate.py:test_secondary_theta10_gold_discriminates_operating_point`):
  when `_PROBE` switched to the live bundle (sampling geometry x=0.12, origin_y=0.05) but the
  θ=10 gold still carried the scaffold geometry (x=0.5, origin_y=0), gating the live probe against
  the θ=10 gold re-extracted the shock line as a garbage **β≈8°** and failed on GEOMETRY — so the
  test no longer proved REFERENCE-VALUE discrimination (it would not catch θ=15 references
  accidentally copied into the θ=10 gold). **Fix**: set the θ=10 gold's `x_shock_station=0.12` +
  `shock_line_origin_y=0.05` (a valid station for a 10° wedge too — shock at y≈0.098 > origin 0.05),
  so β now extracts correctly (~45.24) and the gate fails on a genuine reference-value mismatch
  (45.24 vs the θ=10 reference 39.31). Test strengthened to assert the extracted β≈45.24 (not ~8)
  AND the β observable fails against the θ=10 reference — locking the discrimination to reference
  values, not a geometry artifact. (Also fixed: the `validation_status` inline comments still said
  "coverage tooling reads THIS" — reworded to the honest "test-enforced invariant + forward hook".)

### R2 — final confirmation (round-cap 3) → CLEAN on code; 2× P3 (this report only) → fixed

R2 verbatim: *"I did not find a functional regression in the wedge gate, gold, or test changes.
The only issues I found are non-blocking audit-trail completeness problems in the new Codex report
artifact."* The code/gold/test arc is **APPROVE-equivalent**. The two P3 were self-referential to
this `.md`, fixed in place:

- **[P3-R2-1] dangling raw-log references** — the `*_raw.txt` logs are gitignored, so a clean
  checkout can't open them. **Fix**: this `.md` is now stated to be the canonical self-contained
  trail; the raw logs are local-only.
- **[P3-R2-2] empty R2 placeholder** — the report claimed an R2 round but left it blank. **Fix**:
  this section (you are reading it).

## Net verdict — APPROVE-equivalent, chain CLOSED within cap=3

Across R0→R1→R2 Codex raised **no P1 and no functional/logic defect**; every finding was an
**honesty / audit-trail correction**, each round narrower than the last (R0: a coverage-flip
overclaim + dead metadata → P2; R1: a test-rigor gap the headline rewrite created → P2; R2: two
P3 doc-hygiene nits on this report). The live wedge V&V itself (analytical θ-β-M gold,
anti-tautology Execution-plane extractor, 6 fail-closed hard gates, a real rhoCentralFoam solve
matching within 0.5%) was sound from R0 and never regressed. The honest standing of the slice:
a **V&V-validation milestone** — the rhoCentralFoam benchmark is LIVE-VALIDATED — **NOT a
runnable-coverage flip** (coverage stays 2). The remaining work for an actual flip — wiring
`foam_agent_adapter` + reconciling `cfdtrust` to dispatch `rhoCentralFoam` via the ESI image so
the workbench launches a supersonic case end-to-end — is an explicitly-deferred separate slice.
In-house red-team (`wjjm4tbtp`, 5 lenses + triage) independently HELD (0 real holes). Final test
state: 32 p4 + 367 p3 + 11 gold-schema green; four-plane byte-repro in sync.

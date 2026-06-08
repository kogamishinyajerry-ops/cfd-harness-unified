# Codex round-cap close · P4 V71.A (DEC-V61-234) — wedge backend wiring, coverage 2→3

> Per the cap=3 rule (`~/CLAUDE.md` + project CLAUDE.md): the Codex chain hit
> round cap = 3 (R0 + 2 fix). Unlike a P1-residual overflow, this chain **closed
> cleanly on the binding axis** — R2 carried **zero P1**. This note records the two
> NON-blocking findings deferred to the retro queue (the cap=3 rule routes remaining
> P2/P3 here rather than iterating further) — they are tracked, not iterated.

- **Date**: 2026-06-08
- **Phase**: P4 V71.A (rhoCentralFoam supersonic-wedge backend wiring; runnable-coverage 2→3)
- **Chain**: R0 (3×P2 + 1×P3, all addressed) → R1 (1×P1, addressed) → R2 (NO P1; 1×P2
  fixed verbatim + 1×P3 deferred). 86gs gpt-5.4 xhigh, all three rounds.
  Report: `reports/codex_tool_reports/v61_234_p4_wedge_backend_wiring_report.md`.
- **Verdict**: APPROVE-equivalent (0 P1 at close). DEC-V61-234 → Accepted.

## What was NOT deferred (closed inline)

- **R1 P1** (the escalation of R0 P2-3): the wedge was exposed-but-unverifiable
  through TaskRunner. Fixed in-chain by wiring `run_task()` → `_verify_supersonic_wedge`
  → `gate_wedge_against_gold` (`src/task_runner.py`). The choice was architecturally
  FORCED (the adapter dispatches on `GeometryType.SUPERSONIC_WEDGE`, so the enum must
  be loadable — it cannot hide like the CHT `COMPLEX` sentinel), so it MUST be
  verifiable through the normal pipeline. 5 hermetic locks added.
- **R2 P2** (ingest env-fork): fixed verbatim (Codex's own suggested fix → `不再走一轮`
  per the verbatim-exception rule). `ingest()` now sources the image-fork env-setup,
  completing the 224(b) reconciliation across both `run()` and `ingest()`. 2 locks added.

## Deferred → retro queue (non-blocking, tracked)

1. **[Codex R2 P3] `case_export.py` specialized-gate metadata** — the export route
   reads inline `case['gold_standard']` only, so the wedge (and CHT `case_002a`, same
   shape) export with `Quantity: unknown` + dropped tolerance. **Correct fix**: an
   export-side fallback to the file-backed `knowledge/gold_standards/<case>.yaml` that
   handles the multi-doc / multi-observable specialized-gate shape (no single
   quantity/tolerance). **Why deferred, not quick-fixed**: the obvious inline-stub fix
   would REGRESS the R1 wiring — a non-None `load_gold_standard` re-routes the wedge
   through the generic comparator, bypassing the specialized gate. Root cause is
   pre-existing and CHT-shared. Severity cosmetic (reference-bundle README metadata;
   never a false PASS / safety failure).
2. **[noted at R0] `auto_verifier` specialized-physics-gate hook** — the generic
   residual comparator in `src/auto_verifier` cannot judge oblique-shock (or
   conjugate-energy) physics, so neither the wedge nor the CHT anchor is wired into it.
   CHT-shared, pre-existing. A future hook should let auto_verifier delegate to the
   registered specialized gate (`whitelist.yaml::verification_gate`).

## Lessons (RETRO-V61-001 intake)

1. **Registering a benchmark in the whitelist has TWO halves, not one** (R1 defect
   class): closing the `get_execution_chain` lookup gap (R0 P2-3) silently opened an
   `load_gold_standard`/verification gap (R1 P1), because `SUPERSONIC_WEDGE` — unlike
   the CHT `COMPLEX` sentinel — is a *loadable* enum. **New intake risk_flag**:
   `whitelist-anchor-loadability` — when adding a specialized-gate anchor to
   `whitelist.yaml`, assert up front whether its `geometry_type` is a loadable enum;
   if loadable, the verification path (not just the lookup path) MUST be wired in the
   same slice, or the anchor is exposed-but-unverifiable.
2. **A pre-declared "out-of-scope" follow-up is still a real gap a reviewer will
   flag** (R2 P2): the DEC pre-declared ESI-ingest as out-of-scope, but Codex
   correctly surfaced that it leaves `ingest()` broken for the very image the slice
   adds. When the deferral is a one-line verbatim fix that *completes a claim the DEC
   makes* ("reconciled"), land it rather than defer — deferral of a cheap
   reconciliation-completing fix reads as an honesty gap.
3. **`case_export` / consumer fan-out for specialized-gate anchors**: the same
   "no-inline-gold" property that protects the R1 wiring (so the generic comparator
   doesn't fire) breaks naive inline-gold consumers. Specialized-gate anchors need a
   *documented consumer contract* (read the file-backed gold via `gold_standard_file`,
   not inline `gold_standard`) so future consumers don't each rediscover the gap.

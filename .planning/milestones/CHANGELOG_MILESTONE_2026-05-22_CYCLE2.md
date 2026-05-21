# Milestone Changelog · 2026-05-22 · Cycle-2

> Stakeholder-facing summary for the cfd-harness-unified M2.6 **second**
> close on 2026-05-22 (afternoon). Builds on the cycle-1 milestone
> close — see `CHANGELOG_MILESTONE_2026-05-22.md` for that arc's headline.
>
> Engine HEAD at this milestone: `600022b` (project-governor SHIP-verdict).
> Project-governor checkpoint: `.planning/milestones/PROJECT_GOVERNOR_CHECKPOINT_2_2026-05-22.md`.

## Headline

**6 production blockers closed + 1 engine-snitched-on-itself moment, shipped in 19 commits over a single day.** Cycle-2 lands the multi-region CHT data layer (case_011 plate-fin HX, 47M cells), advances the LES regime BLOCK reason "one door deeper" (case_010 DrivAer), meets industrial run-script conventions (step-numbered mesh logs), bounds the streaming-parser RSS for industrial-scale logs (3.3 GiB → bounded), AND catches one same-arc honesty cleanup the engine found in its own dogfood (Gap #32 sentinel leak). Test suite at **441 passed / 1 skipped**, +32 vs cycle-1.

---

## What landed since cycle-1 (since commit `5769673`)

### Production-blocker DECs (2)

| DEC | Closes | Commit | Verdict |
|---|---|---|---|
| `DEC-V61-201-SUB-INGEST-MULTI-REGION-BC` | Gap #11 — multi-region CHT entry blocker | feat `01d5567` · merge `f108e13` | data layer ON; verdict layer intentionally BLOCKED (honest deferral) |
| `DEC-V61-201-SUB-INGEST-BC-REGEX-GROUPED-PATCHES` | Gap #23 — compressible aero BC regex | feat `4db8ecc` · merge `19f8dfa` | unblocks case_006 / case_030 / case_031 / case_036 in one shot |

### Spike-class closures (4)

| Spike | Closes | Commit | Confidence |
|---|---|---|---|
| TBD-15 + TBD-20 | reactingFoam log fallback + bounded-RSS streaming parser | `e8691f3` · merge `8981f63` | high |
| Gap #26-#27 | step-numbered mesh-pipeline log discovery | `68f4a70` · merge `0ed2b06` | high |
| Gap #29 + #31 | `0.orig/` fallback + LES turb-model derivation | `914f944` · merge `de38f49` | high |
| Gap #35 | gate-JSON-loss recovery path streaming follow-up | `16e8dcf` | med |

### Same-arc honesty cleanups (2)

| Gap | Symptom | Commit | Confidence |
|---|---|---|---|
| Gap #32 | `__none_laminar__` sentinel leaking into per-region `expected_fields` | `77825b8` | high (39 LOC + 1 named test) |
| Gap #35 (streaming continuation) | bounded-RSS path also needs to cover the gate-loss recovery branch | `16e8dcf` | med |

### Re-dogfood verification (2)

| Case | Cycle-1 outcome | Cycle-2 outcome | Verifier |
|---|---|---|---|
| case_011 plate-fin CHT | FAIL (single-region blind) | **BLOCKED honestly** with `multi_region_bc_validation_not_yet_wired`; 3 regions enumerated; 5 residual fields tracked (was 1) | `DOGFOOD_CASE_011_CYCLE2_REDOGFOOD.md` |
| case_010 DrivAer LES | BLOCKED at wrong door (`case_dir_not_openfoam_compatible`) | **BLOCKED at correct door** (`no_time_directory_found`); `solver_execution: skipped` (not `ingested`) | `DOGFOOD_CASE_010_CYCLE2_REDOGFOOD.md` |

---

## Honesty fence integrity · cycle-2

All cycle-1 fences continue to hold. Cycle-2 introduces no new fence-bypass paths.

| Fence | Status |
|---|---|
| validated → solver_execution = real | ✓ held |
| PASS → solver_execution = real | ✓ held |
| ingested → validation_status ≤ partial | ✓ held |
| case_011 multi-region: verdict BLOCKED, not fabricated | ✓ held (new this cycle) |
| case_010 LES: solver_execution = skipped, not ingested | ✓ held (preserved) |

**0 false PASS introduced. 0 fabricated verdicts. 0 over-promises.**

---

## Capability matrix · cycle-2 deltas

The cycle-1 9-regime matrix carries forward. Cycle-2 deltas:

| Regime / case | Cycle-1 status | Cycle-2 status |
|---|---|---|
| case_011 CHT multi-region | FAIL (engine blind to per-region 0/) | **BLOCKED-honest** + 3/3 residual fields tracked (was 1/1) + Gap #12 next-step text branch confirmed landed |
| case_010 LES (DrivAer) | BLOCK at wrong door | **BLOCK one door deeper** (correct reason); LES expected-fields derivation (WALE / Smagorinsky / kEqn / laminar) lands in code |
| case_006 / case_030 / case_031 / case_036 compressible aero | regex-grouped patches failed bc_audit | **regex-grouped patches now parsed** (Gap #23) — 4 cases unblocked at the BC-parse layer |
| case_009 reactingFoam (industrial-scale logs) | text-path parser OOM'd at 13 GiB RSS on 3.3 GiB log | **bounded chunk streaming** (TBD-20); byte-identical proven |
| Industrial run scripts (any case using step-numbered mesh logs) | engine didn't walk `01_*.log` form | **walks both step-numbered + unprefixed**, latest-step-number wins |

---

## The cycle-2 hero moment · Gap #32

Found during case_011 cycle-2 re-dogfood at 2026-05-21T19:57:53Z. The
multi-region branch was faithfully propagating the manifest sentinel
`__none_laminar__` (meant to signal "laminar — no turbulence-field
expected") into each region's `expected_fields` as if it were a literal
field name. Each region then dutifully reported `__none_laminar__` as a
missing file at `0/region_<X>/__none_laminar__`.

This is exactly the cycle-1 TBD-17 pattern: the engine catches its own
cosmetic-but-honesty-adjacent leaks during dogfood, and ships the fix in
the same arc, not in a triage queue. Fix landed at commit `77825b8` — 39
LOC, 1 named test (`test_collect_bc_sentinel_turbulence_fields_filtered_out`),
12 commits after the discovery. Confidence: high.

This is the demo's load-bearing trust beat for cycle-2.

---

## Test posture at cycle-2 close

```
pytest ui/backend/audit/  →  441 passed · 1 skipped (pre-existing R15)
Cycle-1 baseline: 409 → +32 tests this cycle
```

Per-DEC named tests added:
- Gap #11: multi-region bc_quality.json detection + per-region walking
- Gap #23: regex-grouped patch coverage in `test_bc_contract.py` (+91 LOC)
- TBD-15 / TBD-20: `test_log_fallback_includes_reacting_family` · `test_stream_parser_equivalence`
- Gap #26-#27: mesh-pipeline log discovery (step-numbered)
- Gap #29 / #31: 0.orig acceptance branches + turb-model derivation branches
- Gap #32: `test_collect_bc_sentinel_turbulence_fields_filtered_out`
- Gap #35: covered by `test_stream_parser_equivalence` (byte-identical-by-construction)

No new flakies. Suite 2.94s, no hangs.

---

## What's queued post-M2.6-cycle-2 (honest)

These are queued, not done. Do not claim coverage that doesn't exist.

### Charter-class (DEC-scale, multi-day each)
- **Gap #18** `compressible_contract` schema — thermophysicalProperties / perfectGas / sutherland / rho / T / Mach validation
- **Gap #28** `les_contract` schema — turbulenceProperties / delta cubeRootVol / SGS-eddy-viscosity / simulationType LES validation
- **TBD-3** `vof_contract` schema — phase-field awareness for interFoam class
- **TBD-18** `reacting_contract` schema — species_list / inlet_compositions / combustion_model / chemistry_solver / thermo_temperature_range

### Spike-leftover
- TBD-16 sub-second physical-time iter=0 collapse (breaks unsteady iteration discriminator across reactingFoam / pisoFoam / fireFoam / pimpleFoam)
- Audit-subcommand inspection-only mode (case_010 Gap #26-baseline scope — would unblock end-to-end witness of Gap #31 LES turb-model derivation on scaffold-only cases)
- Multi-region bc_contract verdict-layer wiring (the deferred half of Gap #11)

### Governance follow-up (not blocking)
- Cadence-floor Codex relay-review retry post-demo as a background scrub (the 86gs gpt-5.4 xhigh heartbeat hung at ~32 min on cycle-2's 5769-LOC / 56-file diff). Per-DEC R0-R3 chains during cycle-1 dev are intact; remaining 4 cycle-2 commits are spike-class exempt.
- DEC frontmatter `notion_sync_status` for the 2 new sub-DECs (Gap #11, Gap #23) needs session-end batch sync per CLAUDE.md v2.3 Notion-only-Accepted rule.

### M2-M6 long-term roadmap
- `project_cfd_harness_roadmap_v2.md` remains 3-6 months out. Cycle-3 should not attempt charter-class without a discrete planning arc.

---

## Provenance · cycle-2 commits

`git log --oneline 5769673..HEAD` (19 commits, HEAD = `600022b`):

```
600022b docs(milestone): project-governor checkpoint #2 · SHIP THE DEMO
16e8dcf fix(audit-ingest): Gap #35 stream solver log in gate-JSON-loss recovery path
77825b8 fix(audit-ingest): Gap #32 strip __sentinel__ markers from turbulence_fields
7c42b2a docs(dogfood): cycle-2 re-dogfood case_011 + case_010 with cycle-1 fixes (Agent F)
0ed2b06 Merge: Gap #26-#27 spike-class (step-numbered mesh-pipeline log discovery)
68f4a70 fix(audit-ingest): Gap #26-#27 step-numbered mesh-pipeline log discovery
8981f63 Merge: TBD-15 + TBD-20 spike-class (reacting log fallback + streaming parser)
e8691f3 fix(audit-ingest): TBD-15 + TBD-20 spikes (reacting log fallback + streaming parser)
de38f49 Merge: Gap #29 + #31 · 0.orig fallback + turb-model derivation (Agent C spike-class)
f108e13 Merge: Gap #11 · multi-region CHT BC parser (DEC-V61-201-SUB-INGEST-MULTI-REGION-BC)
19f8dfa Merge: Gap #23 · regex-grouped patches for compressible aero (DEC-V61-201-SUB-INGEST-BC-REGEX-GROUPED-PATCHES)
01d5567 feat(audit-ingest): detect + parse 0/region_*/ multi-region CHT BC layout (Gap #11)
914f944 fix(audit-ingest): close 2 case_010 LES dogfood spikes (Gap #29 + #31)
4db8ecc feat(audit-ingest): handle regex-grouped patch blocks in bc_audit (Gap #23)
7f40730 docs(demo): Chinese MG video — kinetic typography + real-screenshot inserts + persistent rule update
6cf9a1c docs(demo): render cfdtrust_demo_2026-05-22.mp4 — 7:38 MP4 from real captures + real plots
1176dae docs(demo): polish hero plots — re-ingest case_021 + case_009 surfaces TBD-17 BLOCK live
0f4703e docs(demo): video production package — real captures + real plots + ParaView macros + persistent marketing-director agent
e1867aa docs(demo): ship 2026-05-22 milestone demo materials + dogfood reports
```

The first 5 listed commits (e1867aa..7f40730) are cycle-1's demo
production tail; the engine-changing cycle-2 work is in the bottom 14.

---

## Recommendation

**Ship the cycle-2 demo.** The video at `.demo/cfdtrust_demo_mg_cn_2026-05-22_cycle2.mp4` features 5 net-new beats not present in the cycle-1 video, all backed by real captures + real artifacts + real commit SHAs. The pitch remains "honesty is the differentiator" — case_011's BLOCKED-not-yet-wired and Gap #32's self-discovery are this cycle's two strongest evidence points for that pitch.

For cycle-3 (post-demo, not blocking): retry the cadence-floor Codex relay-review as a background scrub; pick ONE charter-class queue item (recommend Gap #18 compressible_contract since case_006 + case_030 + case_036 light up simultaneously); finish the Gap #11 multi-region verdict-layer wiring. **Do not stack two charter-class arcs into one cycle** — single-charter-per-cycle has been the sustainable rhythm.

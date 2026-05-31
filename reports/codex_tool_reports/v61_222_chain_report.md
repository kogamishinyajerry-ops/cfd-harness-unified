# Codex chain report · DEC-V61-222 (P3 W3.1 CHT v9 rule distillation)

- **Date**: 2026-05-31
- **Relay**: ALL rounds on **CRS `gpt-5.4` high** (governance baseline 86gs `gpt-5.4`
  xhigh was **5-for-5 unavailable** this session — hung/no-output on R0 attempt +
  the four W3.0.x precedents; CRS used per DEC-V61-214 fallback. Effort-downgrade
  xhigh→high logged. CRS also threw transient 429s twice — cleared on a paced retry).
- **Target**: the W3.1 surface (`--base 5f1a6a9`, commits `6adce39..97b2ca6`):
  `rules.py` (R13/R14 predicates), `v9_advisor_rules.{json,ts}` + `v9_parity_fixtures.json`
  (4-layer ruleset), `pattern_matcher.py` + `advisor_pattern_matcher.ts` (frozen
  contract docs), `manifest_adapter.py` (deriver→regions adapter), the UI adapters
  (later reverted), + p3 tests.
- **Outcome**: chain hit **round cap = 3** (R0 + 2 fix iterations). Each round was
  CHANGES_REQUIRED, each on a DIFFERENT (converging) layer of one root concern —
  *production reachability requires the producer side, which is W3.2*. Two user
  adjudications (charter-trigger + round-cap). Final W3.1 = 2 faithful rules
  (R13+R14) + deriver-path readiness; R15/R16 + the full UI/producer path → W3.2.

---

## R0 — CHANGES_REQUIRED (1×P1 + 1×P2) · CRS high

Pre-Codex: the in-workflow 2-lens `test-red-team` had already caught + fixed R13
(unsound case-wide Rad/non-Rad heuristic → **regrounded** to a faithful
dangling-coupled-interface-reference predicate; dead `neighbour_map` removed) and
R15 commentary dishonesty (narrated a v5b mechanism it couldn't detect → rewrote +
disclosed gap), plus a W3.0.6 byte-reproducibility test whose "no rule reads regions"
premise W3.1 invalidated.

- **P1** — R13–R16 unreachable in production: `derive_slice_from_manifest()` never
  populated `RunArtifactSlice.regions` → rules could only fire on synthetic tests.
- **P2** — the UI adapters (`adaptRunDetailToSlice`/`adaptBridgeArtifactToSlice`)
  dropped region payload → test-only on the frontend too.

**Fix (`e1d2f13`)**: wired a forward-compatible `_regions_from_manifest()` into the
deriver (bulletproof-graceful — 106 adversarial malformed-manifest cases, zero
raises; honest-refusal; defines the `manifest["regions"]` contract W3.2 emits) +
carried regions through both UI adapters + a production-path test proving
`matches_for_manifest()` surfaces R14 end-to-end through the REAL deriver.

## R1 — CHANGES_REQUIRED (2×P1) · CRS high — the deep cross-artifact finding

R1 cross-referenced the W3.0.x extractors' OWN docstrings (a blind spot the
same-family red-team missed):

- **P1** — R16 FACE_ZONE_LOSS false-fires on the canonical healthy case:
  `shm_dict_multi_region` documents case_002b's 6 solids are `topoSet`+
  `extrudeToRegionMesh` (NOT sHM) → legitimately `shm_snapshot_ref=None`. R16's
  XOR would warn on healthy case_002b. `shm_snapshot_ref=None` = "extruded", not
  "face-zone lost".
- **P1** — R15 CONDUCTION_DOMINANCE can't catch V92: `RegionSlice.kind` is from
  `regionProperties` (declared); a mesh-lost fluid still reads `kind="fluid"` →
  `n_fluid` never hits 0 → R15 silent on its cited scenario.

Root: the frozen W3.0.6 schema carries DECLARED topology, not produced-mesh
presence. R15/R16 (like R13's original flaw) lack a faithful signal.

**Charter-trigger surfaced to user** (the charter's "3–4 rules" assumed 4 were
distillable; the honesty constraint forbids shipping unfaithful rules). **User
decision: ship R13+R14, defer R15+R16.**

**Fix (`27913a5`)**: removed R15+R16 from all 4 layers (v9.3.1→v9.4.0, 14 rules) +
their tests; documented the deferral + produced-vs-declared finding (rules.py,
pattern_matcher.py, advisor_pattern_matcher.ts — RS#38 doc parity); kept the
now-unread `kind`/`shm_snapshot_ref` fields as carried-for-deferred. Red-team sweep
+ doc-honesty residue fix (stale "R15 fires" docstrings).

## R2 — CHANGES_REQUIRED (1×P1) · CRS high — round cap reached

- **P1** — the run-detail backend API (`run_history.py` schema + `get_run_detail()`)
  never emits `regions`, so the TS `RunDetail.regions` field the R1 fix added is
  always `undefined` on real data → R13/R14 unreachable in the production UI (+ a
  TS↔Python schema parity gap the R1 fix introduced).

Same root as R0/R1 (producer side unwired); now at the run-detail-API layer.
**Round cap = 3 reached.** Per discipline (3rd-round P1 → user adjudication) +
standing mandate (stop on Codex-stuck-at-round-cap), surfaced to user.

**User decision: revert the premature UI-adapter wiring; W3.1's boundary is the
deriver/commentary path; the entire UI live-card path + producer-side emission is
one coherent W3.2 unit.**

**Resolution (`97b2ca6`)**: reverted the UI adapter + TS `RunDetail`/`BridgeArtifact`
regions fields + the adapter test. R2 P1 **ratified as a W3.2-deferred scope
boundary** (NOT a defect) → overflow retro `codex_round3_overflow_w31.md`. No R3
review (cap reached + the flagged code is removed).

---

## Outcome

- **W3.1 shipped**: 14 rules (R1–R12 + **R13 COUPLED_INTERFACE_DANGLING_REF** +
  **R14 PER_REGION_THERMO_MISSING**), each faithful + naming a real V-row (R13←V94
  dangling coupled ref; R14←V14/V92 missing per-region thermo) + the deriver-path
  consumer readiness (`_regions_from_manifest`, tested end-to-end, defines the
  W3.2 manifest contract).
- **Deferred to W3.2** (tracked): R15 CONDUCTION_DOMINANCE + R16 FACE_ZONE_LOSS
  (need a per-region produced-mesh-presence field — additive schema extension);
  the full producer-side data flow (build_manifest emit + run-detail API emit +
  UI adapters).
- Tests: **448 p3+v9 backend green** · `tsc --noEmit` clean · 24 TS contract tests.
  No regression; R1–R12 untouched.

## Calibration (RETRO-V61-001 intake)

1. **Cross-artifact review beats single-artifact red-team**: R1's two P1s (R15/R16
   signals don't mean what the rules assume) required reading the *extractors'*
   docstrings, not just the rules + fixtures. The same-family red-team validated
   the rules in isolation; Codex (异源) caught the semantic mismatch. Carry-forward:
   for advisor-rule phases, the understand phase MUST cross-reference the upstream
   data-producer semantics, not just the consumer contract.
2. **Rules-ahead-of-data sequencing invites repeated "unreachable" findings**: R0/R1/R2
   each peeled a producer-side layer. A reviewer without charter context correctly
   keeps finding "another unwired layer." Carry-forward: when a phase ships a
   consumer ahead of its producer, state the producer-side boundary IN THE DIFF
   (code comments) up front so review can assess the deferral, not re-discover it.
3. **86gs is now 5-for-5 unavailable this session** (W3.0.1 502×2 · W3.0.2 stream-fail
   · W3.0.6 R2 hang · W3.1 R0 hang/no-output). CRS carried every governance review
   (with 2 transient 429s cleared by paced retry). **Strongly recommend promoting
   CRS to governance-primary** (effort=high) until 86gs xhigh stabilizes — carried
   to retro for a routing-policy DEC.

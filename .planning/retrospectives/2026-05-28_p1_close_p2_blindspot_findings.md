# P1 V&V-loop close + P2 entry · two blind-spot findings · 2026-05-28

> Parents: DEC-V61-207 (Blueprint v4 charter) · DEC-V61-209 (flat-plate V&V de-fake,
> Accepted) · DEC-V61-210 (cfdtrust canonical V&V runner).
> Arc: 13 commits `dc900d5`→`37c58be`, all local (unpushed — L2 autonomy, push
> needs explicit user confirm).
> Trigger: phase-close (P1 V&V-loop deliverable COMPLETE) + 2 post-R3 / blind-spot
> findings that warrant methodology capture (per RETRO-V61-001 cadence).
> Codex this session: relays were 503 → governance review ran on LOCAL `codex exec`
> (`~/.codex/`, DEC-209 ADDENDUM 5 / frontmatter `codex_review_relay: local`); the
> two P2 distillation/advisory commits were advisory-additive (non-verdict,
> non-security) → not mandatory Codex sync-triggers under v2.3 risk-tier.

## 做了什么 (what)

**P1 — closed the incompressible-RANS-aero V&V loop (Blueprint v4 Law-2).**
The flat-plate `flat_plate_rans_sst` case went from a Phase-0 MOCK to an
honest, gated, real-solve PASS over cycles 3b→3i:

- **3b** Re coherence fix — nu 1.5e-5 → 6e-6 so Re/L = U/nu = 5e6 matches NASA
  TMR (the cycle-2 mismatch was producing the 15-17% Cf error the gate had
  been blaming on the reference).
- **3c** flipped `solver_backend: mocked → openfoam` — real Docker simpleFoam
  solve, real NASA Cf(x) comparison. Honest **FAIL** on a near-LE band.
- **3e** real validated PASS with NASA pre-plate (symmetry→plate) topology.
- **3g** **reverted a rationalized PASS back to honest FAIL** — Codex caught
  that moving `x_min_compare_m` 0.01→0.03 to clear the surviving near-LE
  failures was post-hoc gate movement, not scoping. Kept NASA's own 0.01.
- **3h** sponsor decision (option B): gate on **NASA TMR's own convention** —
  `gate_mode: nasa_integrated` = integrated-Cf drag + Cf@x=0.97008. Near-LE
  per-point deviations demoted to `known_deviations` (computed, written,
  reported — not excluded, not hidden).
- **3i** Codex R0 caveat closed: added a **developed-region per-point shape
  guard** (`developed_region_min_m: 0.1`) as a THIRD PASS condition — integral
  + single station alone can't reject a shape-wrong curve whose ±area errors
  cancel; every point at x≥0.1 m must be within tol or it's a real FAIL.
  → **DEC-V61-209 Accepted.** Final honest verdict: integrated drag 0.83%,
  Cf@0.97008 1.28%, developed region (157 pts) max 2.13% / 0 failures; 4
  near-LE points (0.0129≤x≤0.0232, worst 21.2%) survive correct Re + NASA
  topology + NASA freestream + y+~1 + a 180→260 grid probe → a genuine
  OpenFOAM-kΩSST-vs-CFL3D LE formulation discrepancy, reported as such.

- **DEC-V61-210** — declared **cfdtrust the canonical V&V runner** (sponsor
  decision A); the legacy adapter reconciliation is queued as a separate DEC,
  not silently dual-tracked. P1 V&V-loop is COMPLETE.

**P2 entry — pre-flight signals + offline ruleset distillation (Law-3).**

- **W2.0** added per-predicate boundary true-negatives for v9 rules
  R1/R5/R6/R7/R8 (the matcher had positive coverage but thin negative
  coverage); recorded the W1.1 re-scope.
- **W2.1** distilled the **solver-divergence death-mode → R9** into the offline
  v9 ruleset (`RESIDUAL_DIVERGENCE_V9_R9`: last-4 p-residuals monotonically
  increasing AND final > 1.0), dual-binding (Python + TS predicates + JSON
  SSOT + shared parity fixture), cross-language parity green.
- **W1.0′** the meaningful Reynolds-coherence pre-check, relocated to the
  **audit namespace** (`cfdtrust/qoi/flow_coherence.py`) — non-circular by
  construction (reads the case's ACTUAL `constant/transportProperties` nu vs an
  INDEPENDENTLY-sourced `physics.canonical_reynolds_per_length`), advisory-only
  (stashed in gate `details`, never changes a verdict). It would have flagged
  the exact DEC-209 cycle-2 drift.
- **W2-hygiene** repaired **fabricated provenance in 5 of 8 shipped v9 rules**
  (see finding 2).

## 关键发现 (key findings)

1. **Adversarial multi-agent review catches "theater" that passes self-review.**
   The user opted into a Workflow for the W1.1 cycle (a naive pre-flight
   Reynolds check comparing `Re_computed` to the manifest's `derived[Re]`). An
   adversarial agent established that the workbench YAMLs author `derived[Re]`
   from the *same* U·L/ν the check recomputes — so the check is **circular: it
   can only ever agree with itself.** It would have shipped as a green
   "pre-flight signal" that validates nothing. I'd reviewed the same design and
   not seen it; the independent skeptic, prompted to refute, did.
   **Lesson**: a coherence check is only worth its green light if the two sides
   have **independent provenance**. The fix wasn't to delete the idea but to
   **relocate it where the provenance genuinely diverges** — the audit
   namespace, comparing the solver's actual `transportProperties` nu (what runs)
   against a benchmark-cited canonical Re (W1.0′). Same instinct, real signal.
   This is the DEC-209-3g lesson (don't rationalize) at the *design* layer
   rather than the *threshold* layer: **self-consistency is not validation.**

2. **Provenance must be audited like code — 5 of 8 v9 rules shipped with
   FABRICATED citations.** Auditing the ruleset before extending it, I found 5
   of the 8 existing rules cited provenance that **did not exist**: `.md` files
   that aren't in the repo, and `V-row` corpus numbers pointing at unrelated
   topics. They had passed every prior review because **nobody dereferences a
   citation during a normal diff read** — a plausible-looking
   `Reference: V-031` is invisible to the eye and to the matcher tests (which
   only check predicate behavior, not citation validity). Repaired to real
   textbook references **without inventing section numbers** (an unknown page
   is left unknown — the finding-1 / DEC-209 rule again: a fabricated specific
   is worse than an honest gap).
   **Lesson**: for a governance-critical artifact (the offline ruleset is the
   advisor's SSOT), **a citation is a claim and must be verifiable at write
   time.** Candidate guard: a test that every rule's `provenance` resolves to a
   real corpus path / row, or is explicitly `provenance: textbook:<title>` with
   no fake specificity. This is the *same class* as the M5.5 "a default is a
   claim" finding, now on metadata: **an unchecked reference is an unfalsified
   assertion the reader trusts by default.**

3. **Integration checks against the REAL file catch parser bugs unit fixtures
   never will.** The W1.0′ nu parser's first regex grabbed `0.2` out of a
   `// ... x>=0.2;` *comment* in the real flat-plate `transportProperties`
   (instead of `nu = 6e-6`), because the real file's comments mention "nu" and
   numbers — structure no hand-written unit fixture had. Caught only by running
   the parser against the actual case file and seeing Re/L come out 25× wrong.
   Fix: line-anchored regex that stays on the `nu` key's line (`[^;\n]`) +
   a **regression test built from the real comment structure**.
   **Lesson**: the unit fixtures encode what I *imagined* the input looks like;
   the real artifact encodes what it *is*. For any parser over
   solver-authored files, one test must feed a verbatim slice of a real file.

4. **A prose claim can contradict the machine-readable artifact — only a review
   that reads BOTH catches it (86gs reconciliation, ADDENDUM 6).** When the
   relays recovered, the 86gs re-review of the DEC-209 gate (which the 2026-05-27
   *local* fallback had APPROVE'd) surfaced a P2 the local pass missed: the
   manifest `notes` claimed "PASS, validated" while the committed
   `trust_report.json` honestly says MOCKED, and `tools/cwos_status.py` derives
   the cockpit from the latter — so the dashboards report the case as
   *unvalidated*. The MOCKED readout is *correct* (committed artifacts are mock
   by the pollution-guard convention; real solve output is never committed). The
   contradiction lived only in the prose. **Lesson**: same class as findings 1-3
   (an unverified claim is trusted by default), now between a human-readable
   field and a machine-readable one. The fix is prose, not a committed VALIDATED
   report — committing solve output would break the convention tests and make
   the dashboard *lie*. Also a concrete win for the "reconcile local-review
   provenance when relays recover" rule: the canonical baseline caught what the
   emergency fallback didn't.

5. **Meta: the scalar-rule space is saturating.** R9 (divergence) genuinely
   fit the scalar `RunArtifactSlice` (residuals/forces/convergence_stats), but
   most remaining V-series death-modes are *spatial* (field gradients, y+ maps,
   recirculation) and don't map onto the current scalar artifact. Further
   honest distillation needs **richer artifact data** (extend `RunArtifactSlice`
   with spatial gold-delta) or **pre-run data** (mesh/BC signals before solve) —
   not more scalar rules squeezed from a saturated space. Inventing scalar
   rules past this point risks manufacturing finding-1-style theater.

## 治理 (governance)

| Gate | Status |
|---|---|
| Four-question gate (DEC-209/W1.0′/R9) | ✅ LLM-offline (pure Python/TS predicates + audit functions); artifacts (trust_report.json + gate details); TrustGate explains (honest known_deviations, advisory message); AI advisory-only (W1.0′ never changes verdict; R9 is a matcher hint) |
| Truth-chain | ✅ honest FAIL kept over rationalized PASS (3g); known_deviations reported not hidden; fabricated provenance repaired (finding 2); refused to ship circular theater (finding 1) |
| Gate-gaming guard | ✅ x_min_compare_m held at NASA's 0.01, tolerance held at 0.10 — neither moved to mask the LE band; sponsor convention is NASA's own, not tuned-to-pass |
| Codex round cap=3 | ✅ DEC-209 closed within cap (R0 caveat → ADDENDUM 5) |
| Codex relay | ✅ RECONCILED — relays recovered mid-session; DEC-209 verdict-affecting guard re-reviewed on canonical 86gs gpt-5.4 xhigh (was local fallback on 2026-05-27): APPROVE_WITH_COMMENTS, guard sound, 1 P2 (truth-chain consistency) addressed inline. P2 advisory/distillation commits non-verdict + non-security → not mandatory sync-triggers (v2.3) |
| Test pollution | ✅ source case dir kept clean (polyMesh=.gitkeep, artifacts=MOCK placeholders); live solver output is verification proof, never committed (`git checkout HEAD -- artifacts/` + remove generated time/polyMesh dirs ×3) |
| Cross-language parity | ✅ R9 Python + TS predicates green against shared fixture |
| confidence | high (DEC-209 real-solve validated; W1.0′/R9 pure-fn + tests; findings are durable methodology, not code risk) |

## 下一步 / 风险 (next / risks)

- **~18 commits local & unpushed** — push needs **explicit per-push user
  confirmation** (L2 autonomy). DEC-209's local-review provenance is now
  RECONCILED on 86gs (ADDENDUM 6), so the eventual push carries a clean
  canonical-baseline trail.
- **Deferred design question (separate DEC, queued)**: should a V&V-grade
  *validated reference* case commit a real `trust_report.json` as canonical
  evidence, superseding the mock-placeholder convention for that class? It
  would change the pollution guard + two convention tests — out of scope for
  the DEC-209 gate fix; needs its own DEC + user input.
- **Session-end Notion sync** — Accepted DECs V61-206/207/208/209/210 to push
  to Decisions DB (only Status=Accepted; not this retro, not drafts).
- **W1.1′** (advisory Re-coherence → hard pre-run gate) is verdict-affecting →
  **needs Codex** (security/verdict boundary) and a separate DEC; do NOT
  promote silently.
- **W2.2** — only distill V-rows that genuinely map to the scalar
  `RunArtifactSlice`; per finding 4, prefer extending the artifact (spatial
  gold-delta) over squeezing the saturated scalar space.
- **Provenance-validity test** (finding 2) — ✅ DONE this session
  (`tests/test_v9_provenance_validity.py`, commit `e05e63c`): enforces that any
  repo-path / V-row citation resolves; textbook §-numbers deliberately not
  faked; adversarially self-verified non-vacuous; full v9 suite 89 green.
- **PRODUCT backlog (non-blocking)**: `cfdtrust run` should clean stale time
  dirs before solving (it currently relies on a clean checkout).
- **P3 (CHT end-to-end)** is the next Blueprint v4 phase after P2 signal/ruleset
  work matures — not started.

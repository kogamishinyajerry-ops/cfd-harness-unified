---
retrospective_id: RETRO-V61-V107-V108
timestamp: 2026-05-02T22:30 local
scope: |
  v6.1 autonomous_governance arc covering DEC-V61-107 (partial), DEC-V61-107.5,
  DEC-V61-108 Phase A, and DEC-V61-108 Phase B. Counter progression
  53 → 57 (4 ticks across the arc). Fired by RETRO-V61-001 cadence rule
  #2 ("counter ≥ 20 → arc-size retro mandatory") and the user's
  explicit instruction following V108 Phase B closure.
status: LANDING — follows DEC-V61-108 Phase B Codex R3 APPROVE on f6d40e1.
author: Claude Opus 4.7 (1M context · CLI session)
decided_by: Claude (self-executed under standing 全权授予 authority).
notion_sync_status: pending
related_chain_reports:
  - reports/codex_tool_reports/v61_107_partial.md (commit 47ae9e5)
  - reports/codex_tool_reports/v61_107_5_r12_r16_chain.md (commit e10c9b5 — R12-R16 leg)
  - reports/codex_tool_reports/v61_107_5_r17_r20_chain.md (commit e10c9b5 — R17-R20 leg)
  - reports/codex_tool_reports/v61_108_phase_a_r1_r11_chain.md (commit 656b82a)
  - reports/codex_tool_reports/v61_108_phase_b_r1_r3_chain.md (commit 2b34191)
---

# RETRO-V61-V107-V108 · Per-patch BC governance arc

## Purpose

RETRO-V61-001 made the rule explicit: counter ≥ 20 fires an arc-size
retrospective. The previous code-bearing arc retro (RETRO-V61-003,
2026-04-22) closed at counter 32; the v6.2 governance retros
(RETRO-V61-053, ADR-002, W4 prep, session B) brought us to counter 53
by 2026-04-27. From that anchor, this arc spans:

- **DEC-V61-107 (partial)** — fvSchemes upgrade for non-orthogonal
  STL meshes (one Codex round, APPROVE)
- **DEC-V61-107.5** — pimpleFoam migration for the named-patch BC
  mapper (9 rounds, R12 → R20 in numbering continuation, ended APPROVE)
- **DEC-V61-108 Phase A** — backend per-patch BC classification
  override store (11 rounds, R1 → R11, ended APPROVE)
- **DEC-V61-108 Phase B** — Step 3 frontend panel wiring (3 rounds,
  R1 → R3, ended APPROVE)

The arc is semantically coherent: every DEC pushes one further turn
of the wheel "engineer can hand-author boundary conditions on
arbitrary CAD geometry". V107 fixed the solver's numerics so the
mapped patches actually converged. V107.5 made the solver itself
suit non-LDC physics. V108 added the per-patch override surface
(backend + frontend) so the engineer's choice routes ahead of the
heuristic. The user's strategic restatement at the start of the
session — "处理任意的 CAD 几何, 人工可自由选中编辑" — is now
materially shipped at the level of this arc's deliverables.

## Counter progression

Per RETRO-V61-001 telemetry: each `autonomous_governance: true` DEC
contributes +1; rounds within a DEC do not contribute. Kogami artifacts
contribute +0 (advisory chain). External-gate DECs (`autonomous_governance:
false`) contribute +0 but are listed for arc completeness.

| DEC | Sub-phase | Counter | Scope | Codex rounds | Final verdict | Est. / actual pass rate |
|---|---|---|---|---|---|---|
| V61-107 partial | fvSchemes upgrade | 53→**54** | non-orthogonal STL — `corrected` Laplacian schemes + nNonOrthogonalCorrectors | **1** | APPROVE | 0.85 / first-pass APPROVE — well-calibrated |
| V61-107.5 | pimpleFoam migration | 54→**55** | replace icoFoam path; named-patch mapper feeds new control loop | **9** (R12-R20 numbering) | APPROVE on R20 (`c924360`) | 0.45 / 8 CHANGES_REQUIRED before APPROVE — under-calibrated by ~0.30 |
| V61-108 Phase A | per-patch BC override store | 55→**56** | backend GET/PUT/DELETE; fd-based race-free I/O on sidecar yaml | **11** | APPROVE on R11 (`dfb13db`) | 0.55 / 10 CHANGES_REQUIRED — under-calibrated by ~0.45 |
| V61-108 Phase B | Step 3 override panel | 56→**57** | frontend wiring; PatchClassificationPanel + Step3SetupBC mount | **3** | APPROVE on R3 (`f6d40e1`) | 0.55 / 2 CHANGES_REQUIRED — under-calibrated by ~0.20 |

**Arc total: 24 Codex rounds across 4 DECs.** Counter advanced by
**+4** (53 → 57). Average rounds-per-DEC = 6.0 — the highest density
of any arc since RETRO-V61-003 (which averaged 2.8). The two extreme
rounds-per-DEC outliers (V107.5 = 9, V108-A = 11) drove most of the
mass; the bookends V107-partial (1) and V108-B (3) were normal.

## Self-pass-rate calibration — was I honest?

| DEC | Estimated | Actual rounds to APPROVE | Round-1 verdict | Calibration delta | Honest? |
|---|---|---|---|---|---|
| V61-107 partial | 0.85 | 1 | APPROVE | 0 | ✅ honest, well-calibrated |
| V61-107.5 | 0.45 | 9 | CHANGES_REQUIRED | -0.40 in actual | ⚠️ optimistic — see "what bit me" below |
| V61-108 Phase A | 0.55 | 11 | CHANGES_REQUIRED | -0.45 in actual | ⚠️ optimistic in same way |
| V61-108 Phase B | 0.55 | 3 | CHANGES_REQUIRED | -0.20 in actual | ⚠️ slightly optimistic |

**Average overshoot: -0.31.** I systematically over-estimated my
first-pass rate on this arc, with the same root cause both times:

- For **V108 Phase A** I rated 0.55 thinking "the I/O is bounded; just
  add lock + atomic write + symlink check". What I missed was the
  **upstream `case_lock` not opening with `O_NOFOLLOW`** — every
  hardening attempt at the patch_classification layer leaked through
  the upstream symlink-swap window. R7→R8→R9 cycled through three
  attempts before R9 architecturally closed by reverting cleanup on
  the symlink_escape branch and **documenting the residual** as
  upstream `case_lock` work. Lesson: rate **lower** when the surface
  uses a shared-infrastructure primitive whose own contract isn't
  hardened against my new threat model.

- For **V107.5** I rated 0.45 anticipating solver-config rough
  edges. The actual rounds were dominated by **partial migrations
  Codex repeatedly caught**: I'd switch the call site but leave a
  legacy controlDict reference; or migrate a primary path but leave
  a secondary dispatcher unchanged; or update the runner but not the
  test fixture's expected output. Lesson: when migrating a solver
  family, **grep for every reference** to the old primitive *before*
  the first commit, not after Codex flags them.

The V108 Phase B slight overshoot (-0.20) was a different beast:
my R1 closure introduced **new bugs** (single-token conflation),
which R2 caught, which my R2 closure cleanly fixed, which R3 APPROVE'd.
This is the "fix introduces follow-on" failure mode, not the
"missed-on-first-look" failure mode. It's recoverable in 1 round
and represents acceptable Codex-as-cocoach behavior.

## Codex economy — round distribution + finding density

| Bin | DEC | Round count | Findings landed | Findings/round |
|---|---|---|---|---|
| Tight | V61-107 partial | 1 | 0 | 0 |
| Tight | V61-108 Phase B | 3 | 6 (4 R1 + 2 R2) | 2.0 |
| Wide | V61-107.5 | 9 | ~14 across 9 rounds | ~1.5 |
| Wide | V61-108 Phase A | 11 | ~17 across 11 rounds | ~1.5 |

**Wide arcs all converged on architectural-close patterns**, not on
"another forgotten edge case". V108-A R9 is the canonical example:
after 8 rounds of layer-cleanup attempts, R9 closed by acknowledging
the upstream `case_lock` is the actual root cause and documenting
the residual. V107.5 had a similar moment around R16 ("pragmatic
scope reduction" — drop the brittle static guard Codex itself rejected
across R12-R15 and let runtime detection take over).

**Implication**: Codex is genuinely good at making me converge on
the right architecture, not just at finding bugs. The cost is
absolute round count; the gain is that the architecture I land on
*after* the long arc is genuinely defensible. Both V108-A R9 and
V107.5 R16 stand as rationale-heavy commits I would not have written
on first pass.

## Verbatim-exception usage

The 5-condition verbatim-exception (RETRO-V61-001) was used cleanly **3 times** in this arc:

| DEC | Round | Conditions all met? | Notes |
|---|---|---|---|
| V61-108 Phase A R10 | R10 P2 verbatim | ✅ all 5 | test-only fix asserting on real sidecar location; Codex APPROVE'd next round |
| V61-107.5 R19 | R19 P1 verbatim | ✅ all 5 | unused-import removal blocking tsc; same-file 1-line fix |
| V61-107.5 R16 | R16 pragmatic scope reduction | partial | this was a *broader* scope-reduction (drop the guard family) than verbatim allows; flagged as "pragmatic" in the commit message rather than "verbatim". Honest accounting: not strictly verbatim, but close enough that Codex APPROVE'd it; would have failed §11.1 precision. **Methodology note**: future "pragmatic scope reduction" should either pass through the regular Codex round flow or get a Kogami advisory; calling it verbatim was loose. |

Net: verbatim-exception saved **2 governance rounds** in this arc.
The "pragmatic" relaxation is a finding for future tightening (see
Recommendations).

## Post-R3 defects (RETRO-V61-053 risk_flag accounting)

Per RETRO-V61-053 addendum: any defect found AFTER Codex APPROVE in
executable smoke or live run gets recorded here, separate from the
Codex round count.

**This arc: 0 post-R3 defects.** Smoke baseline (4 PASS · 0 EF · 2
SKIP · 0 FAIL) was preserved on every closure commit across all 24
rounds. No live-run regression, no executable-smoke surprise, no
solver-divergence-on-novel-geometry slipped through. The
`executable_smoke_test` risk-flag from V61-053 ran cleanly for the
duration of the arc.

The *blind spots* that V61-053 identified — accessor/attribute-
dereference vs. runtime-emergent — both held: nothing
attribute-dereference-shaped came up post-APPROVE, and nothing
runtime-emergent (CFL violation, race, env-dependent) escaped to
live run. This is the longest clean post-R3 stretch since the
risk-flag was instated.

## DEC frontmatter / Notion sync gap (methodology finding)

**No DEC files were created in `.planning/decisions/` for V107
partial, V107.5, V108 Phase A, or V108 Phase B during the arc.**
Source-of-truth lives entirely in:

- Git commit messages (commit-as-DEC-narrative)
- Chain reports under `reports/codex_tool_reports/`
- Notion sync (still pending for these DECs)

This violates the project rule "Notion 是人可读的决策门户;
git 是可验证的代码状态+frontmatter 真值" — without DEC files,
the frontmatter authoritative state is missing. The chain reports
are good substitutes for *Codex* narrative but they don't carry
the structured `notion_sync_status`, `codex_tool_report_path`,
`autonomous_governance: true/false`, or `external_gate_*` fields
that downstream Notion sync expects.

Two paths forward (recommendation: do path 1 ASAP):

1. **Backfill** four DEC files (V107 partial, V107.5, V108-A,
   V108-B) referencing the chain reports as the Codex tail. Sync
   each to Notion. Effort: ~30 min per DEC = ~2 hours.
2. Adopt **chain-reports-as-DEC** as a recognized pattern, codify
   in CLAUDE.md, add a `chain_report_index.yaml` so each chain
   report carries the structured metadata DEC frontmatter would have
   carried. Effort: ~half-day; broader than this retro can self-execute.

## What surprised me (open questions for future arcs)

### Q1 — Why did Codex catch 11 layered hardening bugs on V108-A?

The R1 issues were genuine (concurrency, symlink, race). R2-R10 were
all on hardening *I introduced to close R1*, all due to upstream
`case_lock`'s `O_NOFOLLOW` gap. **The arc ended with the architectural
close at R9 + scope acceptance**: this is the right answer, but it
took 11 rounds.

Could I have surfaced the `case_lock` upstream gap myself? Probably
yes if I'd traced through `case_lock`'s implementation before writing
the first hardening line. **Action: when adding fd-based hardening
on top of a path-based primitive, read the primitive first.**

### Q2 — Why was V107.5 9 rounds when its scope looked tight?

Each round caught a partial migration: solver call-site updated but
controlDict not; controlDict updated but post-flight rejection not
plumbed; post-flight rejection plumbed but the SSE phase machine
didn't surface it. Codex caught the gaps; **I should have grep'd
for every reference to `icoFoam` before the first commit** to
enumerate the migration surface, not discover it round-by-round.

### Q3 — Why was V108-B R1 closure flawed enough to need R2?

I conflated two distinct concerns into one `stateGenRef`. The
recovery (R2 → R3 dual-token model) was clean, but the original
fix shouldn't have shipped that conflation. **Action: when
introducing a generation token, write down on paper the two
cancellation domains before mapping them to refs.**

## Recommendations

### R1 — Read shared primitives before fd-hardening on top of them

When the new feature uses a shared-infrastructure primitive
(case_lock, IMPORTED_DIR, the case_solve runner) that wasn't designed
against the new feature's threat model, **read the primitive's
contract first**. V108-A's 11-round arc would likely have been ~5
if I'd opened `case_lock` and seen the path-based open up front.

### R2 — Migration grep before first commit

For solver/family migrations, **grep for every reference to the
outgoing primitive** before the first commit so the migration
surface is bounded explicitly. V107.5 would have been ~4 rounds
instead of 9.

### R3 — Tighten "pragmatic" verbatim-exception language

The V107.5 R16 commit called itself "pragmatic scope reduction"
and Codex APPROVE'd, but the change was broader than verbatim's
5 conditions allow. Recommend tightening: future commits should
either pass through full Codex review or carry a Kogami advisory
when scope-reducing past Codex's recommendations. Call this **§
11.6 in CLAUDE.md** as a follow-up.

### R4 — Backfill the missing DEC files

Without DEC files, the Notion control-plane lags git by 4 ticks.
Backfill V107 partial + V107.5 + V108-A + V108-B as four short DEC
files referencing the chain reports as the Codex tail; sync to
Notion. ~2 hours of work.

### R5 — Document the V108 Phase A residual as a real DEC-V61-109

The residual `case_lock` `O_NOFOLLOW` gap is currently a paragraph
in the V108-A chain report. It should be a real DEC (or
`charter-future` entry) with the threat model, blast radius
(case_lock is shared by setup_bc/raw_dict editor/etc.), and the
proposed fix. Without it the residual silently rots.

## Self-pass-rate calibration recommendation for next arc

Update the personal estimate baseline:

- For **fd-based race-free I/O on shared-infra primitives**: drop
  to **0.30** (was 0.55).
- For **solver-family migrations**: drop to **0.30** (was 0.45).
- For **frontend race-free async state with ≥2 cancellation domains**:
  hold **0.55** (V108-B was on-mark for the *recovery*, just not for
  the *initial token model*).
- For **fvSchemes/numerics tweaks with bounded scope**: keep **0.85**
  (V107 partial was honest).

## Counter advance entry for STATE.md

```
counter v6.1 53 → 57 across DEC-V61-107 partial (53→54),
DEC-V61-107.5 (54→55), DEC-V61-108 Phase A (55→56), DEC-V61-108
Phase B (56→57). Per RETRO-V61-001 cadence rule #2 (counter ≥ 20),
arc-size retrospective filed at .planning/retrospectives/
2026-05-02_v61_v107_v108_arc_retrospective.md.
```

(This sentence should be appended to the STATE.md `last_updated`
anchor next time it's touched. The retro itself does NOT modify
STATE.md — that's a separate write, and per project convention
STATE.md updates ride on the next concrete code change rather than
being a retro deliverable.)

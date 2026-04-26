---
doc_id: METHODOLOGY_V2_§10.5_§11_DRAFT
status: DRAFT (pending CFDJerry promotion to Active)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-26
authored_under: 治理收口 2026-04-26 → 2026-05-03 anchor session
parent_rule: Methodology v2.0 §10 治理降级 standing rule
related_decisions:
  - DEC-V61-072 (Sampling Audit Anchor · First Execution) — co-lands §10.5
  - DEC-V61-073 (proposed) — promotes §11 anti-drift rules to Active
related_retros:
  - RETRO-V61-001 (Codex-per-risky-PR baseline · 3 new triggers + 5-condition verbatim exception)
  - RETRO-V61-004 (P1 Metrics & Trust arc complete)
notion_sync_status: pending
---

# Methodology v2.0 · §10.5 (Sampling Audit Anchor) + §11 (Anti-Drift Standing Rules)

> **Status**: DRAFT for promotion. CFDJerry must sign-off via Notion Decisions
> DB before §10.5 / §11 become Active. Until then, this document is advisory
> and **does not** override §10 (current Active rule) or §10.4 (Line-A/B
> isolation contract per OPS-2026-04-25-001).

---

## §10.5 · Sampling Audit Anchor (NEW · co-lands with DEC-V61-072)

### §10.5.1 Trigger conditions

Outside the trust-core 5 modules (gold_standards / auto_verifier /
convergence_attestor / audit_package / foam_agent_adapter), commits ship
under §10 治理降级 without Codex review. §10.5 introduces a **retroactive
sampling audit** so the degradation rule's blind spots become observable.

A retroactive 1-round Codex audit fires when the **earlier** of:

- **20-commit interval**: every 20 non-trust-core commits since the previous
  sampling audit (counted on `origin/main`, excluding doc-only / chore-only
  commits).
- **Phase boundary**: any time a Phase transitions to `Done` status in the
  Phases DB (e.g. Foundation-Freeze → P1 → P2 transitions).

The first execution (DEC-V61-072 · 2026-04-26) covered the 9-commit Workbench
M1-M4 + 3-extension arc (`3d3509e..faf8446`).

### §10.5.2 Audit scope

Codex receives the commit list + the §10 rule definition + the 5 audit
categories (boundary violations / operator-layer security / cross-file
mechanical refactor / reproducibility-determinism / solver-stability on
novel input). Goal is the **degradation-rule blind-spot report**, not bug
hunt — Codex enumerates rule gaps, not line-level fix recommendations.

Time budget: 15-30 minutes per audit. Output: a Markdown report at
`reports/codex_tool_reports/dec_v61_<NNN>_sampling_audit_<execution_n>.md`.

### §10.5.3 Audit verdict + handling

Codex returns one of three verdicts per audit:

| Verdict | Meaning | Required action |
| --- | --- | --- |
| `CLEAN` | Zero blind spots. §10 degradation correctly applied. | Land DEC + advance counter. No retro. |
| `BLIND_SPOTS_IDENTIFIED` | One or more findings flagged at LOW/MED severity. | Land DEC. Add findings to §11.5 SSOT consistency check. Defer fixes to next phase. |
| `DEGRADATION_RULE_AT_RISK` | At least one HIGH-severity finding (e.g. trust-core boundary actually crossed under workbench cover). | Land DEC. **Recall the offending merges** to a quarantine branch + open mini-retro within 48h. |

**Recall mechanics** (verdict 3 only): the offending commits are reverted on
`origin/main` and re-landed via the standard PR + Codex-per-risky-PR review
path (RETRO-V61-001). The original commits stay on a quarantine branch for
reference.

### §10.5.4 Counter calibration loop (amended by DEC-V61-073)

The §10 degradation rule is **not unconditional**. After each sampling
audit:

- **3 consecutive `CLEAN` verdicts** → sampling interval may relax 20 → 40
  commits (effective from the 4th audit forward).
- **1 `BLIND_SPOTS_IDENTIFIED`** → interval stays at current value.
- **1 `DEGRADATION_RULE_AT_RISK`** → interval drops to **5 commits**.
  After each subsequent clean audit the interval ratchets up smoothly
  via **5 → 7 → 10 → 15 → 20** (per DEC-V61-073 audit Q1(c) finding:
  the original "stays at 5 until 2 clean" path risked starvation /
  false-permissiveness binary; the smooth ratchet provides graduated
  re-trust).

Calibration state is recorded in the DEC-V61-XXX sampling audit DEC's
`Counter calibration` section and mirrored in `.planning/STATE.md`.

### §10.5.4b · Per-fire token budget cap (NEW · DEC-V61-073 H3)

Each sampling-audit fire is capped at **≤100k Codex tokens**. Rationale
(audit Q1(c)): with interval=5, P2 main-line will trigger ~3 audits over
its arc; without a cap, a worst-case ~3×500k=1.5M token spend would
greatly exceed the RETRO-V61-004 P1 arc 460k precedent and starve the
Codex review budget. ≤100k/fire keeps total under ~300k for typical P2
arc — well within precedent.

If the prompt + per-commit diff load exceeds 100k, the auditor must:
- Sample-scope (audit the most-changed N commits to fit budget), OR
- Defer to next sampling fire with explicit `BUDGET_DEFERRED` marker
  in the DEC frontmatter.

The cap is advisory until the §10.5 promotion to Active formalizes it.

### §10.5.4a · Pre-flagged audit-required surfaces (§10 amendment · expanded by DEC-V61-073)

Following the DEC-V61-072 first-execution finding that §10 module-only
gating was too weak, the following **non-trust-core surfaces** are now
audit-required at commit time even though they live outside the
trust-core 5 modules. The list grows from 5 (original) to 7
(DEC-V61-073 H1 spillover):

1. **FoamAgentExecutor call sites** — any new caller of
   `FoamAgentExecutor.execute(...)` outside the 5 trust-core modules.
2. **Docker / subprocess reachability changes** — any commit that adds
   or modifies subprocess invocations reaching Docker, container
   runtimes, or filesystem mount points.
3. **`/api/**` route registration** — any new or renamed FastAPI route
   under `ui/backend/routes/` (route-namespace collision check
   mandatory; see Finding 2).
4. **`reports/` durable persistence** — any commit that writes new
   artifact paths under `reports/` or changes the schema/discovery of
   existing paths.
5. **`user_drafts/` → `TaskSpec` plumbing** — any commit that lets
   user-drafted YAML influence `TaskSpec` or solver inputs without
   per-case range / whitelist compatibility validation.
6. **`correction_spec/` write paths (NEW · DEC-V61-073 A4)** — any
   commit creating or modifying `CorrectionSpec` artifact paths under
   `reports/{case_id}/correction_specs/` or
   `knowledge/correction_patterns/`. CorrectionSpec influences the
   Evaluation→Knowledge plane edge; silently changing its shape can
   corrupt downstream FailurePattern / CorrectionPattern records.
7. **`.planning/case_profiles/` write paths (NEW · DEC-V61-073 A4)** —
   direct edits to `.planning/case_profiles/<case_id>.yaml`,
   especially `tolerance_policy` blocks. These are physical-truth-source-
   adjacent without being formal trust-core 5 modules; a bad
   tolerance_policy can silently mask real numerical deviation.

A commit touching any of the 7 surfaces requires Codex review per §10
baseline regardless of `autonomous_governance` flag. The pre-commit
hook `tools/methodology_guards/audit_required_surfaces.sh` (TBD ·
shipped under §11.5 enforcement work) detects these surfaces and blocks
direct-to-main commits without an `Audit-Required: <ID>` trailer
referencing a Codex tool report.

### §10.5.4a Pre-flagged audit-required surfaces (§10 amendment)

Following the DEC-V61-072 first-execution finding that §10 module-only
gating was too weak, the following **non-trust-core surfaces** are now
audit-required at commit time even though they live outside the
trust-core 5 modules:

1. **FoamAgentExecutor call sites** — any new caller of
   `FoamAgentExecutor.execute(...)` outside the 5 trust-core modules.
2. **Docker / subprocess reachability changes** — any commit that adds
   or modifies subprocess invocations reaching Docker, container
   runtimes, or filesystem mount points.
3. **`/api/**` route registration** — any new or renamed FastAPI route
   under `ui/backend/routes/` (route-namespace collision check
   mandatory; see Finding 2).
4. **`reports/` durable persistence** — any commit that writes new
   artifact paths under `reports/` or changes the schema/discovery of
   existing paths.
5. **`user_drafts/` → `TaskSpec` plumbing** — any commit that lets
   user-drafted YAML influence `TaskSpec` or solver inputs without
   per-case range / whitelist compatibility validation.

A commit touching any of the 5 surfaces requires Codex review per §10
baseline regardless of `autonomous_governance` flag. The pre-commit
hook `tools/methodology_guards/audit_required_surfaces.sh` (TBD ·
shipped under §11.5 enforcement work) detects these surfaces and blocks
direct-to-main commits without an `Audit-Required: <ID>` trailer
referencing a Codex tool report.

### §10.5.5 First execution result (DEC-V61-072 · 2026-04-26)

See `reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md`.

**Verdict**: `DEGRADATION_RULE_AT_RISK` (2 HIGH + 2 MED findings)

**Findings summary**:

| # | Cat | Severity | Affected commits | Evidence |
| --- | --- | --- | --- | --- |
| 1 | 2 (Operator-layer security/auth) | **HIGH** | 3d3509e / ce0a8ce / 5fff107 / 6b7492c / faf8446 | FoamAgentExecutor.execute() exposed via workbench, draft YAML feeds real run, /api routes registered, reports/ persistence, operator-facing failure semantics from stderr |
| 2 | 3 (Cross-file rename) | MED | 5fff107 / 74a93f1 | /api/cases/{id}/runs collided with Learn /runs handler, fixed reactively in 74a93f1 |
| 3 | 4 (Reproducibility/determinism) | MED | 5fff107 / faf8446 | Second-level run_id timestamps, idempotent overwrite, silent partial-write skip, reports/* discovery by directory shape |
| 4 | 5 (Solver-stability on novel input) | **HIGH** | ce0a8ce → 5fff107 / e83067c / faf8446 | user_drafts/{case_id}.yaml takes priority over whitelist.yaml; draft parameters + boundary_conditions feed straight into TaskSpec without per-case range validation |

**Counter calibration**: NO — the 9-commit batch did NOT warrant §10
degradation. Module-only gating was too weak; trust-core files stayed
clean but operator-layer surfaces (real solver execution, durable
artifacts, /api routes, user-draft → solver plumbing) crossed into
audit-required territory.

**Action taken** (per Codex recommendation §10.5.4a):
- 5 surfaces added to §10.5.4a pre-flagged audit-required list (above).
- Sampling interval dropped 20 → 5 commits until 2 consecutive clean
  audits.
- Merges **kept** (no trust-core bleed; commits are functional). Mini-
  retro filed under RETRO-V61-005 agenda for Day 7 closeout review.
- The 9 commits remain on `origin/main` HEAD `faf8446`. The 4 specific
  blind-spot surfaces (FoamAgentExecutor call sites, /api routes,
  reports/ persistence, user_drafts→TaskSpec) are now under §10.5.4a
  audit-required list for any future change.

### §10.5.5a Original audit window (M1-M4 + 3 extensions, 9 commits):
- 3d3509e M1 RealSolverDriver (line-A wrapper of FoamAgentExecutor)
- ce0a8ce M2 EditCasePage param-form
- 5fff107 M3 run history
- 74a93f1 M3 route rename
- 6b7492c M4 Docker fail classifier
- ecc1981 .gitignore exclude run history
- e83067c /compare two-up overlay
- 61052a9 /workbench landing index
- faf8446 /workbench/today cross-case feed

---

## §11 · Anti-Drift Standing Rules (NEW · 5 rules)

These five rules were drafted under the 治理收口 2026-04-26 → 2026-05-03
anchor session in response to the Pivot Charter v1.0-pivot risk-mitigation
mandate. Each rule has a clear **scope**, **trigger**, **enforcement
mechanism**, and **escape hatch**.

### §11.1 Workbench Feature Freeze

> **Rule**: No new Workbench features (UI routes, run-history fields,
> classifier categories, compare modes, etc.) ship to `origin/main` until
> P4 KOM (Knowledge Object Model) Draft promotes to Active via
> SPEC_PROMOTION_GATE.
>
> **Why**: Workbench M1-M4 + 3 extensions delivered the operability
> closed-loop. Further additions before KOM lands in Active risk
> hardcoding schema-shaped assumptions that KOM will need to undo.
>
> **Enforcement**: pre-commit hook `tools/methodology_guards/workbench_freeze.sh`
> rejects diffs that add files under `ui/backend/services/workbench_*` or
> `ui/frontend/pages/workbench/*` unless the commit message contains
> `BREAK_FREEZE: <rationale>` AND the rationale references an active DEC.
>
> **Escape hatch**: a `BREAK_FREEZE` commit requires Codex review per §10
> baseline + a same-day DEC. Three escape hatches in a 30-day window
> automatically trigger a §11.1 review retro.

### §11.2 Sampling Audit Anchor (= §10.5)

> **Rule**: Every 20 non-trust-core commits OR phase boundary, whichever
> is earlier, fire a Codex retroactive 1-round audit per §10.5.
>
> **Why**: §10 治理降级 must remain falsifiable. §10.5 makes its blind
> spots observable.
>
> **Enforcement**: `.github/workflows/sampling_audit_reminder.yml` posts
> a comment to the most recent commit on `origin/main` when 20 commits
> have elapsed since the last DEC-V61-XXX-SAMPLING-AUDIT-N. Phase
> transitions are detected via Notion API webhook + reciprocal repo CI
> step.
>
> **Escape hatch**: none. Skipping a sampling audit is itself a §11.5
> SSOT inconsistency event.

### §11.3 North-Star Drift Monthly Self-Check

> **Rule**: On the 1st of each month, the maintainer (CFDJerry) reviews
> the most recent 4 weeks of commits + DECs against the Pivot Charter
> v1.0-pivot North Star ("OpenFOAM 是唯一真相源 / surrogate 仅作 plugin /
> Knowledge Protocol 先于功能发散 / 四层架构 import 方向不可反向").
>
> **Why**: Pivot Charter risk #1 is "治理层叙事 drift". Without monthly
> friction-tax, drift compounds invisibly.
>
> **Enforcement**: `.planning/north_star_drift_log/<YYYY-MM>.md` must
> exist by the 5th of each month. CI step `north-star-drift-check`
> WARN-fails when missing for >5 days; HARD-fails when missing for >12
> days.
>
> **Escape hatch**: skipping one month is recorded as "drift_check_skipped"
> in STATE.md; two consecutive skips trigger an Opus 4.7 Gate review of
> the Pivot Charter itself.

### §11.4 Workbench Quarterly Commit Quota

> **Rule**: Across any rolling 90-day window, no more than **30 commits**
> may land on `origin/main` whose primary path is `ui/backend/services/workbench_*`
> or `ui/frontend/pages/workbench/*`.
>
> **Why**: Operability work is high-leverage when it unblocks dogfood,
> but feature creep is the silent failure mode (see Pivot Charter §3
> "「多做几个 case」不再算进度"). 30 commits/90 days = ~1 commit per 3
> days, sustainable for genuine progress.
>
> **Enforcement**: weekly cron `bin/check_workbench_quota.sh` reports the
> rolling 90-day count. >25 commits → WARN. >30 commits → blocks new
> Workbench commits via pre-commit hook (overridable only with same-day
> DEC explicitly extending the quota for one specific PR).
>
> **Escape hatch**: extend quota by +5 commits per signed Opus 4.7 Gate
> ruling. Standing extension caps at +10 per quarter to prevent
> rule-of-the-rules erosion.

### §11.5 SSOT Consistency Check Per Phase

> **Rule**: Every phase transition (Phase X Status → Done in Phases DB)
> requires a fresh **SSOT consistency check** before the phase is
> archived. The check verifies:
>
> 1. Every DEC-V61-XXX issued during the phase has frontmatter
>    `notion_sync_status: synced <date> (<url>)` matching its Notion page.
> 2. Every Notion page in the phase has a corresponding repo file (DECs
>    in `.planning/decisions/`, retros in `.planning/retrospectives/`).
> 3. STATE.md `last_updated` timestamp ≥ the latest commit in the phase.
> 4. `external_gate_queue.md` reflects the latest external-gate state.
>
> **Why**: Phase 5 audit work and the post-pivot Foundation-Freeze both
> showed that SSOT drift accumulates silently between Notion and repo,
> producing audit ambiguity at retro time.
>
> **Enforcement**: `.github/workflows/ssot_consistency_check.yml` runs
> automatically when a Phase transitions to Done in Phases DB. Output is
> a `.planning/ssot_audits/<phase_id>_<date>.md` report. **The phase
> cannot be archived until the report shows zero discrepancies.**
>
> **Escape hatch**: discrepancies may be acknowledged + deferred to a
> follow-up phase via a same-day DEC, but the report stays in the audit
> trail. ≥3 discrepancies in a single phase audit → mini-retro within 7
> days.

---

## Glossary (used by §10.5 + §11)

- **Trust-core 5 modules** (per §10): `src/gold_standards/`,
  `src/auto_verifier/`, `src/convergence_attestor.py`,
  `src/audit_package/`, `src/foam_agent_adapter.py`.
- **Line-A** (operability layer, per §10.4 / OPS-2026-04-25-001):
  Workbench, wizard, run-history, dashboards. Ships under §10 degradation
  by default.
- **Line-B** (case-physics layer): per-case extractor branches
  (dec-v61-XXX-* line-B branches). Codex review mandatory regardless of
  §10 — line-B always touches gold-standard adjacent paths.
- **§10 治理降级**: standing rule that exempts non-trust-core changes
  from mandatory Codex review.
- **§10.4 Line-A/B isolation contract**: OPS-2026-04-25-001 dual-track
  plan that prevents Line-A and Line-B from cross-polluting each other's
  staged changes.

---

## Promotion checklist (DRAFT → Active)

- [ ] DEC-V61-072 (sampling audit first execution) lands with §10.5
      reference + Codex audit report attached.
- [ ] CFDJerry signs §10.5 / §11 Active in Decisions DB (DEC-V61-073 or
      via DEC-PIVOT amendment).
- [ ] §11.1-§11.5 enforcement scripts (`tools/methodology_guards/*`)
      shipped in a follow-up commit (out of scope for the 治理收口
      window — backlog item).
- [ ] Notion main page §10.5 + §11 added to "架构核心原则
      (Non-Negotiable · Post-Pivot)" section.
- [ ] STATE.md `methodology_active_sections` field updated to
      include `§10.5` and `§11`.

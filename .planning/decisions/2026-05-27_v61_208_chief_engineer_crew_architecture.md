---
decision_id: DEC-V61-208
title: Chief Engineer (商业-CAE 总工程师) agent + crew architecture v2 + graduated dev-crew autonomy ladder
status: Accepted
parent_dec: DEC-V61-207 (Blueprint v4 charter — the arc this role drives) · DEC-V61-133 (v2.3 governance simplification — anti-over-engineering constraint) · DEC-V61-130 (AI-advisor pivot — the product invariant this role must NOT relax)
phase: Governance-architecture charter (crew org + autonomy model)
notion_sync_status: pending
autonomous_governance: false
confidence: high
date: 2026-05-27
ratified_by: user ("请商业CFD软件总工程师专门作为一个agent，负责项目掌控。添加到多agent施工队里，优化整个施工队分工和架构。成熟后，允许团队全权开发推进。" 2026-05-27)
---

# DEC-V61-208 · Chief Engineer agent + crew architecture v2 + graduated autonomy

## TL;DR

The user asked for a **commercial-CAE 总工程师 (Chief Engineer)** as a dedicated
agent that **owns project control**, added to the multi-agent crew, with the
crew's division of labor + architecture optimized, and — **once mature** — full
team autonomy to develop and push.

An audit of the existing `.claude/agents/` crew (15 agents) found the
director-tier (`project-governor`, `strategy-director`, `cfd-vv-director`,
`engineering-director`, `system-architect`, `benchmark-director`,
`product-ui-director`, `progress-intelligence-agent`) is **dormant scaffold**:
every one require-reads a `docs/project-memory/` + `.cwos/` CWOS system that
**does not exist in this repo** (`tools/cwos_event.py` missing, all
`docs/{project-memory,strategy,vv,status,engineering}/` missing). Real delivery
runs on a single Opus driver + Codex relay + Kogami (opt-in) + `.planning/` DECs
(574 commits) + STATE.md + Blueprint v4.

The precise gap: **nobody owned the Blueprint-v4 → P1→P4 delivery arc.** The
directors are domain gatekeepers; the user is sponsor; Opus-main implements;
Codex/Kogami review. None *drives* delivery and makes runnable-coverage go/no-go
calls. That seat is the Chief Engineer.

## Decision

1. **Create `cfd-chief-engineer`** (`.claude/agents/cfd-chief-engineer.md`,
   model: opus) as the **apex delivery-owner** of the Blueprint v4 vertical arc.
   It sequences phases, defines exit gates in terms of **Law 1
   (runnable-coverage)**, makes go/no-go calls **on evidence**, coordinates the
   crew, authors sub-DECs, and applies the four-question gate. It is wired to the
   **live `.planning/` system**, explicitly NOT to the dormant CWOS scaffold.

2. **Crew architecture v2** (documented in `AGENTS.md`): honest reclassification —
   sponsor (user) / apex delivery-owner (chief-engineer) / implementation engineers
   / audit (test-red-team + global evaluators) / independent review (Codex + Kogami)
   / archive (Notion) / dormant CWOS directors (disposition deferred to user:
   retire most; optionally repoint `cfd-vv-director` + `system-architect` as
   on-demand consults). This **adds no orchestration layer** — it names one driver
   and tells the truth about which agents are live, consistent with v2.3's
   anti-over-engineering stance (DEC-V61-133; "single agent ≥ multi-agent").

3. **Graduated dev-crew autonomy ladder** (the "成熟后全权" grant, staged):
   - **L0 · Advisory (current)**: drives inside a user-approved phase; stops at
     every phase boundary; no autonomous push.
   - **L1 · Supervised**: executes + pushes passing work within a phase; stops at
     exit gates for the next-phase go/no-go.
   - **L2 · Full autonomy**: drives multi-phase, makes exit-gate calls, pushes
     validated work; only charter/direction changes + escalations + guardrail
     conflicts return to the user.
   Graduation is **evidence-gated, dependency-triggered (no calendar)**: zero
   gate-violations, every exit-gate call confirmed correct by evidence, ≤1 Codex
   round-3 overflow (L0→L1); ≥2 L1 phases with zero blind-spot post-merge defects,
   zero tolerance-integrity incidents, zero advisor-not-driver violations, Law 2
   V&V loop closed on ≥1 vertical (L1→L2). **Each promotion is a governance-rule
   change → its own DEC + explicit user ratification.** Starting level = **L0**
   (the user's "成熟后" framing = autonomy is earned, not granted up front).

## The two autonomies — kept orthogonal (the load-bearing distinction)

- **DEV-crew autonomy** (this DEC grants it, graduated): the crew may develop and
  eventually push autonomously once mature.
- **PRODUCT-AI advisor-not-driver** (DEC-V61-130, untouchable): the shipped
  product's AI never drives a simulation / mutates a case.

Granting the first **never** relaxes the second. The Chief Engineer's hard
guardrails (independent of autonomy level) enforce this wall: it may never wire a
mutating route or let the product AI write a case, never declare coverage without
runnable+benchmark-passed, never weaken a tolerance, never bypass the
four-question gate or cadence hook, never override a Codex CHANGES_REQUIRED by
fiat (round cap=3), never auto-invoke Kogami, never push above its current level,
never kill processes / squat ports, no date gating.

## Governance

- **Governance-architecture charter** (crew org + autonomy model) → full DEC per
  CLAUDE.md v2.3 scope rules (governance-rule-change).
- **Kogami strategic review**: available (opt-in) and **recommended** to the user
  given this is a governance-architecture change — but **not auto-invoked** per
  v2.3. User may invoke `bash scripts/governance/kogami_invoke.sh` if a strategic
  second opinion is wanted before raising the autonomy level past L0.
- **Four-question gate**: this is a dev-process construct, not a product feature —
  no runtime change, no mutating route; it *reinforces* advisor-not-driver. Passes.
- **No code changed** by this DEC; it adds two agent/architecture docs + this DEC.
- Counter: `autonomous_governance: false` (user-ratified direction) — N/A to the
  v6.1 counter.

## Files

- `.claude/agents/cfd-chief-engineer.md` (NEW — the agent charter + autonomy ladder)
- `AGENTS.md` → "Crew architecture v2" section (NEW)
- this DEC

## Dormant-director disposition (RESOLVED 2026-05-27)

User chose "retire most + repoint 2". Actioned:
- **Retired (deleted, git-recoverable)**: `project-governor`, `strategy-director`,
  `engineering-director`, `benchmark-director`, `product-ui-director`,
  `progress-intelligence-agent` (6). Their delivery-driving intent is absorbed by
  `cfd-chief-engineer`; their process/scope intent lives in CLAUDE.md v2.3 + `.planning/` DECs.
- **Repointed onto the live system as on-demand consults (2)**: `cfd-vv-director`
  (V&V / tolerance / "covered" semantics, anchored to `v9_advisor/` + gold
  standards + TrustGate + Blueprint v4 Law 1/2) and `system-architect`
  (boundaries / four-plane law ADR-001/002 / adapter / `ui/backend/schemas/`).
- Crew is now **10 agents**.

## Open items

- **First autonomy promotion (L0→L1)**: gated on the Chief Engineer driving
  Blueprint v4 P1 at L0 with a clean track record, then user ratification.

## Ratification

User explicitly requested a dedicated Chief Engineer agent owning project control,
added to the crew, with crew architecture optimized and full autonomy granted once
mature (2026-05-27). Status = Accepted. notion_sync_status = pending (session-end
batch sync, Accepted DEC).

## Autonomy grant addendum — L2 granted early by sponsor (2026-05-27)

The sponsor (user) granted **full autonomy (L2) directly** —
"全权授予团队持续开发的权限，继续" — **without traversing the L0→L1→L2 maturity
ladder**. The sponsor is the final authority and may promote at will; the
evidence-gating criteria (§ graduated autonomy) are **waived by sponsor decision**,
not met. `cfd-chief-engineer.md` `autonomy_level` set L0 → **L2**.

**What L2 grants**: the crew develops continuously and drives multi-phase
(P1→P2→P3…) without per-phase user ratification; makes exit-gate go/no-go calls
itself; **commits locally** autonomously as dev cadence.

**What L2 does NOT change (hard guardrails — persist at every level, per the agent
charter's "independent of autonomy level" clause)**:
- **PRODUCT-AI advisor-not-driver (DEC-V61-130) — untouchable.** Dev-crew autonomy
  is orthogonal to and never relaxes the product's advisor-not-driver invariant.
- Correctness-critical / risk-tier changes still go through **Codex review (round cap = 3)**.
- **Four-question gate** on every PR/DEC/UI change.
- **V&V tolerance integrity** — never weaken a tolerance to pass.
- No `CODEX_CADENCE_OVERRIDE` without explicit per-use authorization.
- No process-killing / port-squatting.
- **Push remains per-push-confirmed** — pushing is an outward-facing/irreversible
  action; L2 autonomy covers develop + local-commit, not autonomous publish-to-remote.

**Demotion clause unchanged**: a hard-guardrail violation or a wrong exit-gate call
caught post-hoc demotes one level and is logged in the next retro — the sponsor's
early grant does not disable the safety net, only the upfront evidence-gating.

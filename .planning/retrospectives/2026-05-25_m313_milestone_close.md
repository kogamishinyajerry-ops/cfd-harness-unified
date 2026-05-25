# M3.13 milestone close · 2026-05-25

> Parent charter: `DEC-V61-202` · governance DEC: **`DEC-V61-203`** (Accepted, user-ratified)
> 1 cycle · full DEC (governance-rule-change) · 0 Codex rounds · 0 Kogami · final commit `f6e06c4`

## 做了什么 (what)

Added a `pre-commit` hook (`frontend-typecheck`) that runs `tsc -b` for
ui/frontend and **blocks commits on a typecheck failure**, scoped to
`ui/frontend/**/*.{ts,tsx}`. Script: `scripts/governance/check_frontend_typecheck.sh`.
Full rationale/scope/rollback in `DEC-V61-203`.

## 为什么 (why)

- **User-ratified** ("A", 2026-05-25). This is a governance-rule-change (alters
  the commit gate for all frontend work) → per v2.3 it needs a full DEC + user
  sign-off, NOT autonomous spike-class. I surfaced it in the M3.11/M3.12 retros
  and waited for the nod before doing it.
- **Closes the exact gap that caused M3.11**: the prior session committed a RED
  `tsc -b` to HEAD undetected. pre-commit (not pre-push) chosen because the
  failure persisted across local commits that weren't pushed for a long time —
  only a per-commit gate guarantees a green frontend HEAD.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ full DEC | governance-rule-change → DEC-V61-203 (Accepted, ratified_by: user) |
| Codex round cap=3 | ✅ N/A (0) | shell+yaml gate; not a security/byte-repro trigger |
| Kogami opt-in | ✅ not invoked | user ratified directly; no strategic-layer review requested |
| Four-question gate (V130) | ✅ Y/n-a | LLM-offline (build tooling) · artifacts n/a · TrustGate n/a · AI advisory-only |
| Verification | ✅ proven | clean→Passed; type-error probe→Failed (TS2322+override hint)→removed→Passed; live commit self-skipped correctly on non-frontend files |
| Notion sync | ⏳ session-end | DEC-V61-203 Accepted → syncs to Decisions DB (only Accepted DEC this session) |
| Port / date gating | ✅ honored / none | |

## 下次候选 (next)

- **Mirror the gate in CI** (`.github/workflows/ci.yml`) so a `--no-verify`
  bypass can't reach the remote default branch unchecked (DEC-V61-203 §Follow-up).
- **DRY `VtkCanvasV3` onto `webgl_support`** — low priority.
- **M4 charter scoping** — deferred (multi-day, needs Kogami opt-in / user召唤).
- Carry-overs: vscode:// jump · raw YAML viewer modal · "replace whole node"
  recovery · backend `gap.why` enrichment.

## Bottom line

Turns the M3.11 lesson into a durable guardrail: a broken frontend build is now
un-committable. Properly treated as a governance-rule-change (full DEC,
user-ratified) rather than slipped in autonomously. The gate proved correct in
the real commit flow — it self-skipped on this non-frontend governance commit,
confirming the scoping works.

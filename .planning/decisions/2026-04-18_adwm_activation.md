---
decision_id: DEC-ADWM-001
timestamp: 2026-04-18T20:45 local
autonomous_governance: true
reversibility: reversible
notion_sync_status: synced 2026-04-19 (Decisions DB page https://www.notion.so/346c68942bed8171a795c5a85fbabe4e; confirmed by re-probe 2026-04-20T12:20)
---

# DEC-ADWM-001: Accept ADWM v5.2 activation and commit to 5-goal plan

## Decision summary
Under Kogami-signed ADWM v5.2 grant, opus47-main accepts autonomous deep-work mode
for the 48–72h window and commits to goals G1–G5 as enumerated in
`.planning/adwm/2026-04-18_activation_plan.md`. External Notion Gate veto is
suspended; self-trigger conditions a–h will re-invoke deep acceptance.

## Trigger / evidence
- Kogami activation prompt delivered 2026-04-18 (this session).
- Hard floors 1–10 acknowledged active.
- State snapshot: Phase 9 EX-1 track at n=7, rolling override_rate=0.143, all D4+
  rules untriggered (see .planning/STATE.md S-003j).
- Outstanding methodology gap: EX-1-007 B1 post-commit Nu=66.25 due to
  `_extract_nc_nusselt` local-vs-mean bug (foam_agent_adapter.py L6656-6712).

## Alternatives considered
- **A. Stay in v5.1 self-Gate, wait for external Kogami push**: Slower progress;
  fails Kogami's explicit grant and wastes the authorization window.
- **B. Accept ADWM but narrow to G1 only**: Safer, but forfeits G2 demo-ready
  deliverable which is a depth-acceptance trigger on its own (condition c).
- **C. Accept ADWM and expand beyond G5 to include src/error_attributor.py
  refactor**: Too broad; pattern rule #2 (two consecutive override ≥0.5) risk
  grows as slice count grows.

## Chosen: commit to G1-G5 as planned
Rationale: G1 closes the loudest open methodology bug; G2 converts existing clean
PASSes into demo-ready form (zero incremental code risk); G3 closes 1/10
producer→consumer gap; G4+G5 are governance hygiene.

## External-Gate pass-through likelihood estimate
- 80% — Kogami's activation prompt already pre-authorizes ADWM; the main delta
  versus external Gate is logistics (local Decisions file vs Notion record).
- Lowest-confidence sub-item: G1 CHK-2 (Nu ∈ [25, 32] on B1 mesh post-refactor).
  If Dhir 2001 gold-standard definition itself is ambiguous, CHK-2 may slip to
  ±20% band and a second-round Gate.

## Reversibility
- FULL reversible within 3 commits:
  1. G5 local files can be deleted
  2. G4 dashboard can be deleted
  3. G1/G3 Codex dispatches each land as one atomic commit (revert via `git revert`)
  4. G2 reports can be deleted

## Touched hard-floor boundaries
- None touched; G1 + G3 WILL trigger hard floor #2 (禁区 dispatch-to-codex)
  and floor #7 (commit trailer). These are normal operating procedure under
  ADWM, not boundary violations.

## Artifacts
- Activation plan: `.planning/adwm/2026-04-18_activation_plan.md`
- This decision: `.planning/decisions/2026-04-18_adwm_activation.md`
- Next decisions (expected): DEC-ADWM-002 (G1 Fix Plan self-APPROVE),
  DEC-ADWM-003 (G3 restructure self-APPROVE), etc.

## Notion mirror TODO
When MCP reachable, create under "cfd-harness-unified > Decisions DB":
- Name: `DEC-ADWM-001: ADWM v5.2 activation accept`
- Properties: autonomous_governance=true, reversibility=reversible
- Body: this file verbatim

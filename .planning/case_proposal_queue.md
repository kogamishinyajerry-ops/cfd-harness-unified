# Case Proposal Queue · Codex-driven (replaces case_list.md)

> **2026-05-07 evening reframe.** Old `case_list.md` (static
> Ahmed/NACA/S-duct roster) deleted by user direction: "your case
> list mostly lacks ready STEP files — meaning you are NOT being
> 出题 by anything." New model: **Codex 出题, geometry from public
> sources first**, with Codex generating CadQuery only as fallback.
>
> This queue is what main session works through, NOT a static
> menu. Items get proposed by Codex on demand, validated by main
> session, then dispatched to sub-sessions.

## Workflow

```
                    ┌─────────────────────┐
                    │ Project main session │
                    │ (this Claude Code)   │
                    └──────────┬───────────┘
                               │
              "Need a new case in solver-class X"
                               │
                               ▼
                  ┌────────────────────────┐
                  │ codex-relay-with gpt-5.5 │
                  │ Codex (case 出题者)        │
                  └──────────┬───────────────┘
                             │
        Tier 1 priority → public source check first
                             │
                             ▼
              ┌────────────────────────────┐
              │ Codex returns 5 deliverables: │
              │   1. Engineering brief         │
              │   2. CAD generation script     │
              │   3. STEP file (post-defect)   │
              │   4. Parts manifest YAML       │
              │   5. Defect manifest YAML      │
              └──────────┬─────────────────┘
                         │
                         ▼
              ┌────────────────────────────┐
              │ Main session validates:      │
              │   ✓ script executes          │
              │   ✓ STEP imports             │
              │   ✓ patch names valid        │
              │   ✓ defects actually present │
              │   ✓ solver class matches     │
              └──────────┬─────────────────┘
                         │
                  pass / fail (≤3 rounds)
                         │
                         ▼
                ┌──────────────────┐
                │ Per-case kickoff   │
                │ (paste-to-sub-session)│
                └──────────┬───────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ User opens new Claude Code  │
              │ session, pastes kickoff      │
              │ → sub-session executes        │
              └──────────────────────────┘
```

## Coverage map progress (where to point Codex next)

When main session asks Codex for the NEXT case, target a row that
is **pending** or **partially covered**:

| Solver class | Numerics class | Coverage | Next-case priority |
|---|---|---|---|
| Internal flow + buoyancy + forced convection | compressible-buoyant-RANS | ✅ case_002a (active, v14+) | LOW (covered) |
| CHT (multi-region + radiation) | compressible-buoyant-RANS + solid-thermo | ✅ case_002b (active, v2 norad) | LOW (covered, v3 in case_002b) |
| External flow + high-Re + boundary layer | incompressible-RANS | 🟧 NOT YET COVERED | **HIGH · ask Codex now** |
| Internal compressible diffuser (subsonic to transonic) | compressible-RANS | ⏸️ pending | MEDIUM |
| Rotating machinery (MRF / sliding mesh) | incompressible-RANS-MRF | ⏸️ pending | MEDIUM |
| Compressible high-speed (shock-density-based) | compressible-shock-density-based | ⏸️ pending | MEDIUM |
| Multiphase / VOF | multiphase-VOF | ⏸️ deferred Tier 3 | LOW (no concrete brief yet) |
| Combustion / reacting flow | reacting-low-Mach | ⏸️ deferred Tier 3 | LOW |
| Transient LES / DES | incompressible-LES OR compressible-LES | ⏸️ deferred Tier 3 | LOW |

## Active queue (proposed but not yet dispatched)

(empty — case_003 dispatched 2026-05-07 evening)

## Dispatched (kickoff paste-ready, awaiting sub-session start)

| case_id | Solver class | Codex 出题 round | CAD source | Defects | Kickoff file | Dispatched | Status note |
|---|---|---|---|---|---|---|---|
| `case_003_crm_hls_boundary_layer` | External high-Re + boundary layer | 1 of 2 (no revision needed) | Tier-1 NASA/AIAA HLPW6 CRM-HLS | D1 (0.35 mm gap) + D8 (0.80 mm thin plate) | `methodology/kickoff/case_003_crm_hls_boundary_layer.md` | 2026-05-07 evening | **DEFERRED** — awaiting user resources to start sub-session. Kickoff remains valid; pick up anytime |

## In-flight sub-sessions

Tracked in `case_index.md` as authoritative status. Cases with
`status: active` in `case_index.md` are running.

## Closed cases

Tracked in `case_index.md` "Closed threads" section.

## How to add a new entry to this queue

Main session, when ready to enqueue a new case:

1. Pick target solver-class from coverage map (HIGH priority row)
2. Pick CAD source preference:
   - Tier 1 (NASA CRM / ONERA M6 / NREL / etc.) if a published
     reference fits the solver-class
   - Tier 3 (Codex from-scratch) if no Tier 1/2 fits
3. Pick component bank preferred ID (if Tier 3) OR target public
   source (if Tier 1/2)
4. Pick 1-2 defect catalog IDs to inject
5. Write Codex prompt at
   `.planning/methodology/kickoff/case_<NNN>_<name>_codex_request.md`
6. Send via `codex-relay-with gpt-5.5 < <prompt-file>`
7. Receive Codex's response (5 deliverables); save at
   `kickoff/case_<NNN>_<name>_codex_response.md`
8. Validate per protocol §"Main session validation step"
9. If pass: write per-case kickoff at
   `kickoff/case_<NNN>_<name>.md` (template + Codex brief slot)
10. Add row to "Dispatched" section of this file with kickoff
    file pointer
11. Inform user: "case_<NNN> kickoff ready, paste into new Claude
    Code session"

If validation fails after 3 Codex rounds: escalate to user.

## Concurrency policy

Up to 4 sub-sessions in parallel (per `case_list.md` removed →
captured here):
- 1 active in-flight v.N optimization (e.g., case_002a)
- 1 fresh sub-session on a new solver-class
- 1 secondary on a different solver-class
- 1 reserved for high-priority custom user brief

Beyond 4, harvest cadence stalls.

## Why "queue" not "list"

The old `case_list.md` was a static enumerable list. This is
explicitly NOT that — it's a **queue** because:

- New entries arrive on-demand (main session asks Codex when
  coverage gap warrants)
- Order is dynamic (priority recalculated each turn based on
  what's covered)
- Items have lifecycle (queued → dispatched → in-flight → closed)
- The queue's contents are NEVER pre-allocated more than 1-2
  cases ahead — premature enqueueing wastes Codex compute

## Promotion: from "proposed" to "dispatched"

A queued case promotes to dispatched when:
1. Codex round-trip complete + 5 deliverables in repo
2. Main session validation pass (all 6 checks)
3. Per-case kickoff written
4. CAD adapter pipeline (if Tier 1/2 source) executed; STEP file
   in case-thread sandbox
5. User confirms ready to start sub-session

## Demotion: from "in-flight" to "queued for re-design"

A case can return to the queue if the sub-session reports the
geometry/brief is fundamentally unworkable (e.g., the component
chosen by Codex requires solver-class capability the project
doesn't support yet, surfaced only mid-run). Main session asks
Codex to revise.

This is rare — Tier 1 sources are validated; Tier 3 generation is
predictable. Most "broken" cases are recoverable with v2/v3 case
iterations within the sub-session, not by re-queuing.

## References

- `codex_case_design_protocol.md` — what Codex returns
- `component_bank.md` — Tier-3 from-scratch menu
- `public_cad_sources.md` — Tier 1+2 catalog
- `case_kickoff_prompt_template.md` — sub-session briefing template
- `case_index.md` — active/closed thread tracker (this queue is
  intake-side; case_index is execution-side)
- DEC-V61-198 — strategic philosophy SSOT

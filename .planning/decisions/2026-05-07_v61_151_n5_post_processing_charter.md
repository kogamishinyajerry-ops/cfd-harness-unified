---
decision_id: DEC-V61-151
dec_id: DEC-V61-151
title: N5 phase charter · Post-processing report upgrade (beginner + honest + audit triad)
status: Accepted
parent_dec: V61-130
phase: N5
notion_sync_status: pending
parent_artifacts:
  - .planning/strategic/blueprint_v3_2026-05-07.md
  - .planning/strategic/n3_n6_outline_2026-05-07.md
  - .planning/decisions/2026-05-07_v61_134_n2_mesh_control_parity_charter.md
  - .planning/decisions/2026-05-07_v61_139_n3_physics_materials_charter.md
  - .planning/decisions/2026-05-07_v61_145_n4_bc_solver_unification_charter.md
trigger: V130 charter mandates workbench-first parity build-out; M5 (post-processing report) is the post-N4 capability phase that turns the existing 2x2-figure-grid Step 5 into the beginner report + honest issue list + audit-ready export triad
autonomous_governance: true
counter_impact: +1
codex_review_relay: pending
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-07
confidence: high
---

# DEC-V61-151 · N5 Phase Charter · Post-Processing Report Upgrade

## Status

**Accepted 2026-05-07** — user mandate "继续 N5". N4 phase closed
cleanly (charter + N4.1-N4.5 sub-DECs). N5 begins per blueprint v3
§convergence sequencing.

## Context

V130 (strategic pivot · 2026-05-06) established AI as advisor.
N1 closed AI-as-actor; N2 delivered mesh control; N3 delivered
material + regime contracts; N4 delivered BC + solver-config
contracts. **N5 is the post-processing report parity phase** —
converts Step 5 (Results) from a single 2×2-figure-grid + summary
into a structured triad: beginner report (markdown + PDF) +
honest issue list (rule-based, no AI prose) + audit-ready zip
package (HMAC-signed manifest with full provenance).

## Naming clarification

The N3-N6 outline §3 calls this "post-processing report upgrade".
The current Step 5 (`Step5ResultsView.tsx`) and existing audit
infrastructure (`src/audit_package/`, `ui/backend/routes/audit_package.py`,
`services/comparison_report.py`, `services/validation_report.py`)
already provide foundations. **N5 builds on these** — not a
greenfield rewrite. Each sub-DEC explicitly notes whether it
extends existing surface or adds a new one.

## Decision

Adopt the **N5 four-step phase plan** in
`.planning/strategic/n3_n6_outline_2026-05-07.md` §3:

| Sub-phase | Capability | Slim DEC ID (planned) | Risk | Pre-merge Codex? |
|---|---|---|---|---|
| **N5.1** | Beginner report: markdown + PDF · 5-section template (geometry/mesh/physics/solver/verdict) auto-filled from case state | DEC-V61-152 | medium | per Opus confidence |
| **N5.2** | Honest issue list: enumerates DISCLAIMER reasons + missed completeness items + checkMesh warnings + residual stalls | DEC-V61-153 | medium | per Opus confidence |
| **N5.3** | Audit package V2: zip + HMAC + manifest.toml provenance (case state SHA + solver log SHA + figure SHAs + DEC trail) | DEC-V61-154 | medium | post-merge async per v2.2 (HMAC + byte-repro is async-trigger row 2) |
| **N5.4** | Export formats: SVG export of 2×2 grid + CSV of centerline samples (PNG already exists) | DEC-V61-155 | low | no |

**Sequencing**: strict serial N5.1 → N5.2 → N5.3 → N5.4.

## Rationale

### Why charter DEC, not 4 slim DECs only

Per V133 §2.2 scope-driven rule, charter DEC is required when scope
spans ≥3 modules **and** introduces a new architectural surface. N5:

- Extends `services/comparison_report.py` + `services/validation_report.py`
  (existing surface)
- Adds `services/case_report/` (NEW for N5.1 beginner-report builder)
- Adds `services/case_issues/` (NEW for N5.2 honest-issue enumerator)
- Extends `src/audit_package/` (NEW manifest.toml provenance fields,
  same HMAC machinery)
- Extends `services/export_csv.py` (existing) for centerline sampling
- Adds frontend Step 5 panels (report viewer + issue list + export
  buttons)

Cross 6+ modules + new architectural surface (structured report
contract) = full charter DEC pattern.

### Why this sequence

- **N5.1 first**: beginner report consumes geometry / mesh / physics /
  solver / verdict — needs all upstream contracts (N2 + N3 + N4) to
  populate. Builds first because it shapes the structured "case
  state summary" that N5.2 (issue list) and N5.3 (audit) both consume.
- **N5.2 second**: issue list reuses the same case-state walker that
  N5.1 builds, but emits a complementary view (red flags vs verdict).
  Building on top of N5.1's walker avoids two parallel walkers.
- **N5.3 third**: audit V2 consumes both N5.1 report bytes and N5.2
  issue list as part of the manifest provenance (each is a SHA'd
  artifact). Building before N5.1+N5.2 would mean stub manifest
  entries that get re-defined.
- **N5.4 last**: pure export-format work; depends on the report +
  figure infrastructure being stable.

### Why no parallel sub-DEC work within N5

Same reasoning as N2/N3/N4 charters — schema coordination, V132
registry migration sequencing, Codex review chain auditability.

## Workbench-first acceptance (V130 Principle B + Blueprint v3 §5)

Every N5 sub-DEC MUST satisfy these gates before Status=Accepted:

1. **Q1 LLM-offline reachability**: with `LLM_PROVIDER=disabled`,
   engineer can generate the report + issue list + audit zip via
   form-driven exports. No LLM call required. Charter §risk-register
   row 2 explicit: "Honest issue list MUST NOT generate AI prose; it
   lists structured data only".
2. **Q2 artifacts output**: writes `report.md` + `report.pdf` (N5.1),
   `issues.json` (N5.2), `audit.zip` + `manifest.toml` (N5.3),
   `centerline.csv` + `figure.svg` (N5.4). Engineer can `cat` /
   open / verify each.
3. **Q3 audit explainable**: report cites section-level provenance
   (which case-state field populated each section); issue list cites
   each issue's source rule; audit manifest.toml includes case state
   SHA + solver log SHA + figure SHAs + DEC trail.
4. **Q4 AI advisory only**: NO AI-generated prose anywhere in the
   report. The "verdict" section is rule-based — uses N4.3/N4.5
   advisor outputs and N5.2 issue list to derive a structured
   verdict literal (e.g., `verdict: ready_for_review`,
   `has_open_issues`, `physics_setup_incomplete`). Engineer reads
   the verdict + issue list, decides.

## Out of scope (charter §"Out of scope" + N5-extend)

- Auto-comparison against another run — defer to N5-extend
- Live re-render on parameter change — defer to N5-extend
- Multi-case batch report — defer to N5-extend
- Report localization (zh / en) — defer; v0 ships en-only with
  comments noting where translation hooks would go
- Report customization (engineer-authored sections) — defer; v0
  ships fixed 5-section template

## Threat model

| Threat | Vector | Mitigation |
|---|---|---|
| Report PDF rendering on macOS Docker — no system wkhtmltopdf | Cross-platform PDF dep | N5.1 ships markdown-first; PDF rendering is optional via WeasyPrint (pure-Python, no system deps); explicit failure mode when WeasyPrint not installed |
| Honest issue list drifts into AI prose | Engineer asks "make it sound nice" | N5.2 emits ONLY structured `Issue` records with literal severity + source-rule-id; no free-form text generation. Tests assert no LLM imports in N5.2 module |
| HMAC key leak from new audit V2 manifest | Adding new key | N5.3 reuses existing `audit_key` infrastructure (DEC-V61-014); does NOT introduce new secret |
| Audit V2 manifest mismatch between local and CI builds | Time-dependent fields | N5.3 manifest excludes wall-clock timestamps from byte-repro hash; only case-state-derived fields contribute |
| SVG / CSV export include sensitive case data | Engineer-shared exports leak | N5.4 export bundle includes only the engineer-selected figure / centerline; no manifest / case-id leakage |
| Issue list false-positives noise out real issues | Over-eager rule emission | N5.2 issue rules carry severity + scope; UI groups by severity; engineer filter shows critical-only |

## Verification (charter-level)

- [x] Outline doc `.planning/strategic/n3_n6_outline_2026-05-07.md` §3 reachable
- [ ] Sub-DECs N5.1-N5.4 use slim 6-field schema (per V133)
- [ ] Each sub-DEC PR includes Blueprint v3 four-question gate results
- [ ] N5 phase counter increments only by sub-DEC count (charter +1, sub-DECs +4 → N5 final delta = 5)
- [ ] N5.3 byte-reproducibility verified: same case state → identical
      manifest.toml SHA across two builds (excluding wall-clock fields)

## Counter / governance bookkeeping

- `counter_impact: +1` (charter DEC)
- Sub-DECs: +4 (N5.1-N5.4)
- N5 phase total counter delta: **+5**
- No Kogami review (opt-in per V133)

## References

- DEC-V61-130 · Strategic pivot to AI-as-advisor
- DEC-V61-132 · MUTATING_ROUTES registry contract
- DEC-V61-133 · B+ governance simplification
- DEC-V61-014 · Audit package HMAC signing (V61-014; reused by N5.3)
- DEC-V61-145 · N4 phase charter (immediate predecessor)
- `.planning/strategic/blueprint_v3_2026-05-07.md`
- `.planning/strategic/n3_n6_outline_2026-05-07.md`

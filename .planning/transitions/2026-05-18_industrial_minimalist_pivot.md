# Transition · 2026-05-18 · Industrial-Minimalist Workbench Pivot

> **Status**: PREP / SAVEPOINT — not a DEC. User is generating new blueprint UI externally (GPT image-2). This file captures the consolidated state of cfd-harness-unified at the moment of pivot so the new UI shape can land cleanly without re-discovering what is load-bearing vs replaceable.
>
> **Trigger** (user verbatim · 2026-05-18):
> > 我决定走工业级极简风格工作台路线，现在的重文本路线无法接受，教学case也只是作为隐藏后台的档案资产，不要暴露给用户。我正在让gpt生成新的蓝图UI。请先做好预备工作，进行整理收口。
>
> Translation: industrial-grade minimalist workbench route. Current heavy-text approach unacceptable. Teaching cases are backstage archive only — not user-facing. New blueprint UI being generated externally; do preparation work / organize / finalize current state first.

---

## 1 · Pivot constraints (verbatim · binding for next arc)

1. **工业级极简风格** — industrial-minimalist (STAR-CCM+ / Fluent / Bloomberg parity, NOT dashboard-card / commentary-card aesthetic)
2. **重文本路线无法接受** — heavy-text approach rejected (verbose commentary cards, full-paragraph advisor narrative, multi-tab text panels are out)
3. **教学case只作为隐藏后台档案资产** — teaching cases (case_001..case_016) are backstage archive only · MUST NOT be exposed in user-facing UI · prominent CaseBrowser / case picker is out
4. New blueprint UI is being generated externally (GPT image-2) — current Claude-side task is **prepare + organize + finalize**, NOT draw new UI

## 2 · State at pivot (V91 closed)

- **V91 close gate**: ✅ MET at iter-0+iter-1 (initial 2-consec ≥99) · ✅ RE-CONFIRMED at iter-6+iter-7 (post-Codex-fix + post-stash-recovery)
- **14-arc no-scoring-change streak**: ✅ ATTAINED
- **V130 defense layers**: 7 (V83-V91)
- **V132 endpoint lock**: 9 (unchanged across V91)
- **Tests green**: 786 frontend + 195 backend, 3/3 vitest, 185/185 Playwright (modulo iter-2/3/5 load-induced flake disposed as V78 1-vote-veto class)
- **27th "CFD能力" verbatim mandate**: 5th re-issue cohort closed cleanly
- **Codex round-1 fixes preserved**: P1#2 solver_success-based crash detection · P1#3 real-schema observables list + singleton key_quantities · P2#4 `Time = Ns` regex with optional `s?`

## 3 · What V91 delivers · UI-AGNOSTIC (KEEP · load-bearing)

V91's substantive value is **data-layer**, not UI-bound. The new minimalist UI consumes the same artifacts:

| Asset | Path | Why UI-agnostic |
|---|---|---|
| Rule corpus JSON SSOT | `ui/frontend/src/data/v9_advisor_rules.json` | Canonical 6053-byte JSON · TS + Python both bind from this · presentation-free |
| TS matcher | `ui/frontend/src/data/advisor_pattern_matcher.ts` + `v9_advisor_rules.ts` | Pure function · returns `MatchedCommentary[]` · caller chooses presentation |
| Python matcher | `ui/backend/services/v9_advisor/pattern_matcher.py` + `rules.py` | Pure function · byte-identical to TS · no UI dependency |
| Manifest adapter | `ui/backend/services/v9_advisor/manifest_adapter.py` | Real-schema-aware (`solver_success` · observables-list · singleton key_quantities) |
| Audit-package sidecar | `commentary/matched.json` inside `bundle.zip` | Emitted by `src/audit_package/serialize.py` + `ui/backend/routes/audit_package.py` · byte-reproducible · HMAC-signed envelope intact |
| Cross-language parity | 6 frozen fixtures × 8 rules in `__fixtures__/v9_parity_fixtures.json` | Guarantees TS↔Python match on any future UI |

**Implication for new UI**: render `MatchedCommentary[]` however the new minimalist blueprint demands (e.g., severity-badge row, single-line glyph, status-strip) — the data contract is stable, no churn needed in matcher/SSOT layer.

## 4 · What gets deprecated (REPLACE · once new blueprint UI lands)

| Component | Path | Why deprecated |
|---|---|---|
| `PostRunAdvisorV9` verbose commentary cards | `ui/frontend/src/pages/workbench/v3/components/right-panel/AdvisorContent.tsx` | Heavy-text · multi-paragraph card stacks — contradicts 重文本无法接受 |
| `CaseBrowserV3` prominent case picker | (search `pages/workbench/v3/**/CaseBrowser*`) | Exposes teaching cases as user-facing — contradicts 隐藏后台档案资产 |
| Dense multi-tab right panel | `RightPanelV3.tsx` | Multi-tab + text body composition is not minimalist-industrial |
| 5-step pipeline visual strip (current variant) | `WorkbenchShellV3.tsx` step strip section | Likely to be re-shaped by new blueprint — wait for new UI |

**Do NOT pre-emptively delete** any of these. They are working code, V91 close gate verified them. New UI lands → side-by-side comparison → THEN deprecate. Avoid orphaning V91's audit trail before the new shape is concrete.

## 5 · Load-bearing invariants (DO NOT BREAK · regardless of UI changes)

| Invariant | Source | Verification |
|---|---|---|
| **V130 advisor-not-driver** (4Q gate) | DEC-V61-130 · feedback_cfd_four_question_gate.md | Every new component PR must answer: LLM-offline runnable? artifacts emitted? TrustGate intact? AI advisory-only? |
| **V132 endpoint lock = 9** | DEC-V61-132 | `grep -r "MUTATING_ROUTES" ui/backend/` — count stays at 9; new UI must not add mutation endpoints |
| **HMAC byte-reproducibility** | RS#36 (V91) + audit_package contract | `serialize_zip_bytes(manifest) × 2 → identical bytes` · 3× SHA-256 cross-check test |
| **JSON SSOT canonical** | RS#37 (V91) | `sorted_keys=True · indent=2 · trailing newline` — TS + Python load identically |
| **Cross-language matcher parity** | RS#38 (V91) | 6 fixtures × 8 rules · TS test + Python test both green |
| **Manifest adapter graceful degrade** | RS#39 (V91) | log_tail parse fail → empty commentary, not crash |
| **OpenFOAM backend authority** | V130 + V-series corpus | Solver = source of truth · UI never substitutes |
| **Gold-standard comparator** | V61-198 + RBC / TFP / DHC / cylinder cases | Comparator verdict is the only PASS/FAIL judgment · UI presents, never decides |

## 6 · Backstage archive (teaching cases · KEEP · just hide)

Per user constraint "教学case只作为隐藏后台档案资产":

- `case_profiles/case_001..case_016/` — KEEP all files (DEC trails, RESUME.md, manifests, gold-standard refs)
- `tests/case_*/` — KEEP (regression coverage)
- Internal `.planning/intel/v_series/` V-series corpus — KEEP (Claude Code session is the V-advisor, reads V-series directly)
- New UI: **NO case picker · NO case browser · NO "select example" landing screen**. User loads their own STEP/STL or chooses from minimalist saved-runs list, not from a curated teaching catalog.

If new UI needs to render a "recent runs" list: source it from `audit_packages/` directory listings, not from `case_profiles/`. Teaching cases stay invisible to end users.

## 7 · Pending V92 Open Q's (carry forward · unchanged by pivot)

From V91 retro / close DEC:

1. V78 scorer 1-vote-veto on load-sensitive metrics (2-arc evidence now: V90 iter-1 + V91 iter-2/3)
2. V9.E: replay matcher on already-archived bundles
3. BridgeArtifact widening for history-array residuals (3 dormant rules R1/R5/R7)
4. `elapsed_seconds` hardcoded to 0.0 in some emission paths
5. Live-browser E2E for V9.D (download zip · unzip · verify `commentary/matched.json` present)
6. **NEW**: never use `git stash push --keep-index -u` for narrow Codex review again — use targeted commit-and-revert OR move-aside-and-rsync pattern

## 8 · Dev environment snapshot (handoff)

- Backend: was running PID 18762 on `:8000` — **STOPPED** at 2026-05-18 during this consolidation
- Frontend: was running PID 18790 on `:5181` — **STOPPED** at 2026-05-18 during this consolidation
- Restart commands (when new blueprint UI lands):
  ```bash
  source .venv/bin/activate
  bash scripts/start-ui-dev.sh       # backend :8000
  CFD_FRONTEND_PORT=5181 bash scripts/start-frontend-dev.sh   # frontend (port 5181 to avoid stomp on other Vite)
  ```
- Working tree: 14 arcs (V76-V91) uncommitted M files + V76-V91 ARC-GOAL.md untracked · stash@{0} present as safety net (do NOT pop until V92 commit strategy decided)

## 9 · Recommended next action when new blueprint UI arrives

1. User shows new blueprint images (from GPT image-2)
2. Claude reads images + extracts: layout grid · color palette · component inventory · interaction model
3. Map each new-UI component back to: (a) existing V91 data contract it consumes · (b) existing component to replace · (c) new component to write
4. Score 6-pillar UI parity (industrial minimalism · density · color discipline · interaction clarity · audit visibility · advisor-not-driver respect)
5. Phase the implementation: skeleton → data wiring → polish · each phase gated by 4Q + V132=9 + byte-repro tests
6. Do NOT bulk-delete deprecated components until new ones land green — old + new can coexist behind a feature flag during transition

## 10 · NOT in scope for this savepoint

- ❌ Writing new image-2 prompts (user is doing this externally)
- ❌ New DEC for the pivot (it's a strategic redirection, not yet a scoped phase — wait until new UI shape concretizes)
- ❌ Deleting deprecated components (premature; wait for new UI to land green)
- ❌ Refactoring matcher / SSOT / audit-package paths (V91 closed them; they are UI-agnostic and stable)
- ❌ Committing 14-arc backlog (separate strategic decision; pivot doesn't force this either way)

---

— Industrial-Minimalist Pivot Savepoint · 2026-05-18 · awaiting new blueprint UI from user

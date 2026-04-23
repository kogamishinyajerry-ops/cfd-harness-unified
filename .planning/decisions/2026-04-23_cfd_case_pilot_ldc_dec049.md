---
decision_id: DEC-V61-049
title: lid_driven_cavity single-case pilot · CFD-novice end-to-end walk · pattern-before-rollout
status: IN_PROGRESS (codex round 1 CFD-novice walk running · PID 77739 · 2026-04-23T10:00 local)
commits_in_scope:
  - (none yet — remediation commits will land after codex findings + user batch approval)
codex_verdict: PENDING
autonomous_governance: true
autonomous_governance_counter_v61: 36
external_gate_self_estimated_pass_rate: 0.55
codex_tool_report_path: .planning/reviews/case_pilot_ldc_findings.md (pending codex write)
notion_sync_status: synced 2026-04-23T10:05 (page_id=34bc6894-2bed-81e5-bdc4-d42466bc8e2c, Status=Proposed, https://www.notion.so/DEC-V61-049-lid_driven_cavity-single-case-pilot-CFD-novice-end-to-end-walk-34bc68942bed81e5bdc4d42466bc8e2c)
github_sync_status: pushed (6d8e8f5 on origin/main)
related:
  - DEC-V61-046 (demo-first convergence · APPROVE_WITH_COMMENTS)
  - DEC-V61-047 (2-persona pedagogy · APPROVE_WITH_COMMENTS)
  - DEC-V61-048 (4-batch content depth · AWAITING_USER_READ)
  - This DEC **supersedes** the "covering all 10 cases uniformly is
    the best use of effort" assumption in V61-048. After V61-048's 4
    batches, user judged it still insufficient and redirected to a
    single-case pilot: if we can make ONE case reproduction-worthy
    end-to-end (novice reads /learn → runs OpenFOAM → compares
    against gold with ≥5 dimensions → writes a 1000-word report),
    the same patch pattern rolls to the other 9. This is
    higher-bar-per-case in exchange for sequential rollout.
timestamp: 2026-04-23T10:00 local
author: Claude Opus 4.7 (1M context, v6.2 Main Driver)
---

## Why this DEC exists

V61-048 shipped 4 batches (benchmark lineage + TeachingCard 2.0 +
reproducibility runbook + troubleshooting + flagship physics-
intuition for 3 cases). User's post-V61-048 redirect:

> 需要 codex 作为一名 CFD 初学者，根据目前项目的每个 case 的展示
> 内容，进行仿真复现、逐步理解、后处理分析、报告撰写。整个过程中
> 一定会有很多困惑、难以理解的地方，例如，目前项目 case 的云图很
> 多和展示出来的算例几何轮廓不一致，或者说看起来很不像，而且仿真
> 出来的结果和参考的 gold case 的结果对比不显著，至少也得选 5 个
> 对比维度。

This is a different bar than V61-046/047/048 measured:

- V61-046 asked: is the demo honest about what it produces?
- V61-047 asked: is each case factually correct (expert) + first-
  click readable (novice)?
- V61-048 asked: does each case carry textbook-chapter content
  depth (lineage / teaching / runbook / troubleshooting / physics)?
- **V61-049 asks**: can a CFD novice, using only the current /learn
  page, actually reproduce the run + compare against gold with ≥5
  dimensions + write a 1000-word reproduction report?

This is the **end-to-end student walk** bar — reading alone is not
enough; the page has to support downstream reproduction.

## Why single-case pilot (not 10-at-once)

V61-048 updated all 10 cases per batch, then asked the user to read.
Result: user bounce ("这不够"). The remediation loop was 10 cases
wide and patch quality was uniform, so per-case depth was capped.

V61-049 inverts the scaling: fix ONE case to "novice can reproduce
+ write report" standard, then decide whether the patch pattern
rolls. Case chosen: **lid_driven_cavity**, because:
- difficulty=intro; supposed to be the first case a novice reads
- codex V61-048 round 1 scored it among the lowest (4/10)
- V61-048 batch 4 added physics_intuition for it — this DEC checks
  whether batch 1-4 aggregate is enough or still has gaps
- if LDC upgrades work, batches 1-4 schema is uniform across cases
  so rolling to BFS / cylinder / TFP / etc. is mostly content-fill

## Scope

- **In**:
  - Single case: lid_driven_cavity (not BFS, not LDC+RBC, just LDC)
  - Novice-persona end-to-end walk: read → reproduce → compare ≥5 dims → report
  - Compare-tab dimension expansion if <5 today
  - Contour / render quality check (user complaint: 云图 vs geometry mismatch)
  - Workflow_steps executability check (is it enough for a novice?)
- **Out**:
  - Other 9 cases (wait for user approval of LDC pilot)
  - V&V methodology / physics_contract schema
  - Gold numeric values or tolerances
  - Backend solver routing / Phase 9
  - Frontend component refactor

## Single-persona codex review approach

One persona: **CFD 研究生第一学期学生** (Anderson CFD Basics Ch1-5,
ran cavity tutorial once, never validated). Persona 强制: "我不懂"
must be explicit, not soft.

Output: structured findings at `.planning/reviews/case_pilot_ldc_findings.md`
with 6 sections (persona check / Step 1-5 walk / Step 6 patches /
verdict). Expected 4000-6000 words.

## Iteration plan

1. **Round 1** — codex CFD-novice walk, one pass, LDC only. Running.
2. Claude reads findings, triages by "will this actually help a
   novice reproduce", proposes patch batches to user.
3. User confirms priority; Claude implements batches with atomic
   commits + push + Notion sync per batch.
4. User re-reads LDC `/learn` page.
5. If satisfied: decide whether patch pattern rolls to other 9 cases.
   If not: next codex round on LDC only (up to 1 more round).

## Exit criteria

- User re-read of LDC `/learn` says "novice could reproduce + write
  report using only this page" (subjective user gate).
- `pytest tests/ ui/backend/tests/` still green.
- `npm run typecheck` + `npm run build` green.
- GitHub: all pilot commits pushed to `origin/main`.
- Notion: DEC-V61-049 row Status reflects pilot outcome.

## Sync discipline (same as V61-046/047/048)

Per batch:
1. Implementation commit local
2. `git push origin main`
3. Update DEC frontmatter (github_sync_status, commit SHAs)
4. Notion sync (page children append)
5. Only then start next batch

## Risk flags

- **Scope creep**: it's tempting to fix "obvious" issues in other
  cases while reading LDC findings. Resist — stay on LDC until user
  approves the pattern.
- **Codex quota**: if multi-round is needed, `cx-auto 20` prefix
  mandatory. Current account (kogamishinyajerry) 72% remaining.
- **Contour rendering**: if the user complaint "云图 vs geometry
  不一致" requires regenerating PNGs from fresh simpleFoam runs,
  that's a different workstream than content editing — may need a
  sub-scope carve-out.

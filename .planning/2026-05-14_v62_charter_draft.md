# V62 Charter · DRAFT (北极星候选 3 选 1) · SUPERSEDED 2026-05-14

> **SUPERSEDED**: User selected North Star **V62-A (Stack consolidation)** on 2026-05-14.
> Finalized charter at `.planning/2026-05-14_v62_charter.md` (10-12 milestones · Tier 1/2/3).
> This DRAFT preserved for retro audit trail.

**Generated**: 2026-05-14 by M-V62 charter preparation session (Claude Code Opus 4.7)
**Status**: **SUPERSEDED** (was DRAFT) — V62-A selected
**Predecessor**: DEC-V61-198 (closed by `.planning/decisions/2026-05-14_v61_198_CLOSE.md` DRAFT · arc 2026-05-07 → 2026-05-14 = 7 days)
**Successor placeholder**: V63 (TBD post-arc-2)
**Format**: ROADMAP-style (matches V61-198 arc plan convention · not yet a DEC)

> 这个 DRAFT 不是最终 charter。主会话需要做的 finalize 动作 = 选 North Star
> (A / B / C 或自创 D) → 把对应 Done Definition + milestone 表迁入新文件
> `.planning/2026-05-1?_v62_charter.md` → 写 V62 charter DEC（如果 scope
> 升到 charter 级 per v2.3）。

---

## 0. Why a new charter (and not just open V62 arc plan)

V61-198 closes the "advisor substrate arc" with 5/6 Done dims MET pending
B20 left-axis fix. The thesis "Claude Code session = 工业级 CFD advisor"
is empirically demonstrated across 6 cases. **Three independent next-step
vectors emerged from arc-close retrospective**:

1. **Stack vs modules** — 8 advisors LANDED but they are loose modules; no integrated routing into `/ai-review` and `/ai-diagnose` user-facing routes. The thesis is module-level proven, not stack-level proven.
2. **Numerics class breadth vs depth** — 3 e2e classes met arc bar; 7+ classes (multiphase / compressible-shock / Lagrangian / radiation / DEM / LES / acoustic) still unexercised at e2e. Substrate ceiling for "container that accumulates industrial CFD experience" framing (V61-198 §Pillar 1).
3. **Harvest cycle closure** — 9 open-loop items (§6 in close DEC) carried into V62 represent harvest-003 backlog (D6/D9/D10 promotion + case_007/008/014-020 dispatch + D3/D4 catalog gap + A6/A9 2nd-case unlock).

V62's North Star must pick **one primary direction** — covering all three
in one arc replicates the over-broad-scope pattern that produced 22-round
review chains (per v2.3 round-1 retro). The 3 candidates below isolate
each vector.

---

## 1. North Star candidates

### Candidate A · **Stack consolidation** (high-leverage on M6 charter)

> **让 advisor stack 从 "8 个 LANDED 模块" 升级为 "1 个 LANDED stack" — plumbed into `/ai-review` + `/ai-diagnose` live routes · LLM 离线四问门控全通过 · 跨 ≥3 industrial case 的 stack-level e2e 验证。**

**Why this North Star matters**: M6 charter (AI advisor stack) was the
原始 V61-130 strategic pivot end-goal. V61-198 arc proved each advisor
works **standalone**; but real M6 charter empirical proof requires the
**stack** answering "case X most resembles case Y at V-row Z" via a
single user-facing route. Without stack-level closure, M6 stays at
"individually validated module" level, not "operational system".

**Done Definition (V62-A)**:

| # | 维度 | 起点 (2026-05-14) | Done 阈值 |
|---|---|---|---|
| 1 | Advisor stack 路由聚合 (`/ai-review` + `/ai-diagnose`) | 0 (no stack-level route) | **2 routes LANDED · 每条路由调用 ≥ 3 advisor 模块** |
| 2 | 四问门控全通过 cross-feature audit | partial (per-advisor LLM-offline OK, stack-level not audited) | **stack-level 4-question gate audit + sign-off · LLM offline 全功能可用** |
| 3 | Stack-level Track C e2e on NEW case | 0 (Track C arc 全 module-level walkthrough) | **≥ 2 Track C session · advisor stack 接管决策 (engineer 只 review，不写)** |
| 4 | D-class advisor LANDED (literal closure of V61-198 §5.2) | 0 D-class LANDED | **≥ 1 (D6 or D9 or D10) promoted** |
| 5 | 雷达图右半轴 AI axis | 9.0 | **≥ 9.5** (stack-level operationalization signal) |
| 6 | 雷达图左半轴维持 | 7.20 (post-B20) | **≥ 7.20** (no regression) |

**Tier 1 (解锁性)**: stack assembly layer · 路由 endpoint scaffold · 四问门控 audit framework
**Tier 2 (verification)**: Track C stack-level session 1 + 2 · D6/D9 promotion (pick 1)
**Tier 3 (charter close)**: Stack-level Track C session 3 · V62 charter close + V63 candidate selection

**估计 milestone 数**: 10-12 milestones (3 + 4 + 3-5)

---

### Candidate B · **Numerics class breadth** (high-leverage on V61-198 §Pillar 1)

> **扩 e2e numerics class 覆盖到 ≥ 6 类 · 加 multiphase-VOF + compressible-shock + Lagrangian-particle · 每新类至少 1 个 industrial case 通过 Track C e2e · V-series 行数突破 130。**

**Why this North Star matters**: V61-198 §Pillar 1 framed the project as
"container that accumulates industrial CFD experience" with capability
described by "solver-class coverage rows × sediment depth per class".
At 3 e2e classes, the container has covered the **easy** classes
(buoyant-RANS / CHT / reacting-low-Mach all share dict-driven solver
patterns). The **hard** classes (multiphase / compressible-shock /
Lagrangian) require schema + advisor changes that V61-198 deliberately
deferred. V62-B exercises this expansion.

**Done Definition (V62-B)**:

| # | 维度 | 起点 (2026-05-14) | Done 阈值 |
|---|---|---|---|
| 1 | e2e numerics class 数 | 3 | **≥ 6** (3 new: multiphase-VOF + compressible-shock + Lagrangian-particle) |
| 2 | V-series 行数 | 100 | **≥ 130** (~10 V-rows per new class) |
| 3 | Track C session 通过 case 数 | 6 | **≥ 10** (≥ 1 case per new class + 1 stress case) |
| 4 | Schema 扩展 (multiphase BC + shock-capture solver controls + particle injection) | 0 (current schema dict-driven mono-phase) | **3 new schema 模块 LANDED · per-class advisor 新增 ≥ 2** |
| 5 | 雷达图物理覆盖 axis | 8.0 | **≥ 9.0** (new class breadth signal) |
| 6 | 雷达图求解器健壮性 axis | 7.0 | **≥ 8.0** (3 new solver families surfaced + V-row coverage) |

**Tier 1**: multiphase-VOF case dispatch + interFoam schema + advisor scaffold
**Tier 2**: compressible-shock case dispatch + rhoCentralFoam schema + V-row family · Lagrangian particle case dispatch + reactingParcelFoam schema
**Tier 3**: stress-test case (e.g. KCS ship VOF · M219 cavity DES · DrivAer LES — picks from advisor_coverage §catalog) · V62 charter close

**估计 milestone 数**: 14-18 milestones (4 + 6-8 + 4-6) · **higher arc volume than V62-A**

---

### Candidate C · **Harvest cycle closure** (high-leverage on harvest-003 backlog)

> **closes harvest-003 cycle 全部 9 个 open-loop items: D6/D9/D10 D-class advisor promotion + A6 hvac_adpi 2nd-HVAC-case unlock + A9 mrf_setup_advisor 2nd-MRF-case unlock + case_007/008/014-020 dispatch wave + D3/D4 catalog gap close。**

**Why this North Star matters**: V61-198 arc dispatched 11 cases but
case_007/008/014-020 (7 cases) never sedimented; D3 + D4 defect catalog
gaps remain 0 sediment after 11-case batch; harvest cycle effectively
**stalled at harvest-003** because Track C session pacing prioritized
e2e numerics class breadth (Done dim 4) over dispatch breadth. V62-C
explicitly catches up the dispatch backlog and promotes drafted D-class
advisors that have been waiting on 2-of-3 sediment gates.

**Done Definition (V62-C)**:

| # | 维度 | 起点 (2026-05-14) | Done 阈值 |
|---|---|---|---|
| 1 | Dispatched-but-not-sedimented cases | 7 (case_007/008/014-020) | **≤ 2** (≥ 5 newly sedimented) |
| 2 | D-class advisor LANDED | 0 | **≥ 2** (D6 + D9 from 2-of-3 sediment gate · D10 if case_020 sediments) |
| 3 | A6 hvac_adpi promotion | drafted | **LANDED** (case_015 HVAC diffuser provides 2nd HVAC-class sediment) |
| 4 | A9 mrf_setup_advisor promotion | candidate registered | **LANDED OR drafted-to-spec** (case_014 compressor MRF provides 2nd MRF-class sediment) |
| 5 | D3 + D4 defect catalog | 0 sediment each | **≥ 1 each** (Codex case-design protocol amendment seeded these in dispatched batch) |
| 6 | V-series 行数 | 100 | **≥ 120** (~3 V-rows per newly sedimented case × 7 cases) |

**Tier 1**: case_007 + case_008 + case_014 + case_015 sediment (dispatch backlog Track C sessions)
**Tier 2**: case_016 + case_017 + case_018 sediment · D6/D9 promotion to LANDED
**Tier 3**: case_020 sediment · A6/A9 advisor land · D3/D4 catalog gap close · V62 charter close

**估计 milestone 数**: 12-14 milestones (4 + 4-5 + 4-5)

---

## 2. Candidate comparison summary (for main-session decision)

| Axis | V62-A Stack | V62-B Breadth | V62-C Harvest |
|---|---|---|---|
| Primary leverage | M6 charter operationalization | V61-198 §Pillar 1 thesis (container depth) | harvest-003 backlog cleanup |
| Risk | High (UI/route work · 四问门控 audit hard) | Medium-High (schema rewrites · new solver families) | Low-Medium (proven advisor pattern · known case substrate) |
| Reversibility | Medium (route + audit framework hard to undo) | High (per-class additive) | High (per-case additive) |
| advisor stack code growth | High (路由 + audit + stack-level integration) | Medium (3-5 new advisors per class) | Medium (D6/D9/D10 promotion + A6/A9 land) |
| Numerics class coverage growth | 0 (depth not breadth) | +3 (1→6) | 0 (depth not breadth) |
| V-series row growth | Low (+10-20) | High (+30) | Medium (+20) |
| User-visible value if shipped to OSS | High (live AI advisor stack demo) | Medium (broader CFD validity claims) | Low (internal hygiene) |
| Aligns with v2.3 governance (scope-driven) | Charter-level (≥3 modules · routes/) | Charter-level (≥3 schema modules) | sub-DEC arc + 1 light charter ok |
| Estimated arc duration (calibrated to V61-198 7-day) | **14-21 days** (4-7 LOC-heavy milestones · UI surface) | **21-30 days** (multiphase + shock are 2-3× substrate cost each) | **10-14 days** (proven pattern · pacing similar to V61-198) |
| Recommended if user signals: | "wants to ship advisor stack as M6 charter close" | "wants the container to actually cover broad industrial CFD" | "wants to finish what V61-198 started before opening new arcs" |

---

## 3. Resource analysis (based on V61-198 7-day arc data)

V61-198 arc actuals (substrate window 2026-05-07 → 2026-05-14):
- **Duration**: 7 calendar days (≈ 7 working sessions per ARC-GOAL timestamps)
- **Sub-DECs landed**: 13 (avg 1.9 per day · DRAFT-then-Accepted pattern)
- **Advisor modules landed**: 5 new (A4, A5, A7, A8, A10 — pre-A2-v2 already in V61-198 §C extraction) · effective rate ≈ 0.7 advisor/day
- **Track C sessions**: 5 (sessions 2-6 · session 1 case_010 pre-existed arc start) · pacing ≈ 0.7 session/day
- **V-series rows**: 84 → 100 (+16 rows · effective rate ≈ 2.3 rows/day)
- **Radar axis Δ**: left half +0.7 (6.40 → 7.10) over 7 days · right half +0.5 (8.67 → 9.17)

**Scaling assumptions for V62 (same engineer + Claude Code velocity)**:
- V62-A (stack · 10-12 milestones): ≈ 2 weeks if pacing holds; UI/route surface adds friction so plan 3 weeks
- V62-B (breadth · 14-18 milestones, schema + solver families harder): ≈ 3-4 weeks; multiphase + compressible-shock each demand new advisor pair
- V62-C (harvest · 12-14 milestones, proven pattern): ≈ 2 weeks at V61-198 cadence

**Hard floor for arc-close decision**: do NOT open more than one V62
arc concurrently. Pick A, B, or C — do not blend. Blending recreates the
22-round review chain failure mode (per v2.3 round-1 retro · DEC-V61-133).

---

## 4. Triggering redirect conditions (preserve from V61-198 §4)

| Condition | Action |
|---|---|
| Commercial CAE AI score ≥ 5 (Siemens Industrial Copilot GA / ANSYS GenAI release) | Strategic review — V62 may pivot toward OSS readiness ahead of charter close |
| Any milestone stalls ≥ 3 weeks | Skip + retro · do not death-march |
| User focus drift ≥ 1 week (demo / OSS / frontend pull) | Pause + redirect review |
| Cross-cutting refactor surfaces (≥ 3 service files schema change) | Upgrade arc to full charter DEC · don't keep it as a plan-file arc |
| Advisor stack scope grows past charter (per v2.3 ≥ 3 shared code paths trigger) | New charter DEC under V62; sub-arc rules apply |

---

## 5. Out of scope (explicit defer list · same as V61-198 §"故意不投资")

1. HPC scaling beyond 4-core ARM substrate
2. Multi-field FSI / multi-physics chain coupling
3. Polyhedral mesh
4. Industrial GUI / web dashboard postproc realtime
5. N2-N6 workbench frontend parity (unblocked by v2.3 but **not in V62**)
6. OSS release / pilot user onboarding (defer to V63 unless V62-A signals stack-ready)
7. New numerics class beyond V62-B scope (cavitation / DEM / EHD if not picked)

---

## 6. Provisional Tier 1/2/3 outline (per candidate · main-session refines)

### Provisional outline · V62-A (Stack)

```
Tier 1 · 解锁性
  - M-STACK-ASSEMBLY · advisor stack assembly layer (dispatch + composition)
  - M-ROUTE-AI-REVIEW · /ai-review route scaffold + 4-question gate audit framework
  - M-ROUTE-AI-DIAGNOSE · /ai-diagnose route scaffold + V-series corpus retrieval contract
  - M-4Q-AUDIT · 四问门控 cross-feature audit + LLM-offline acceptance test
Tier 2 · advisor 加宽 + D-class literal closure
  - M-D6-PROMOTE · D6 extra_body_in_fluid LANDED
  - M-TRACK-A1 · Stack-level Track C session 1 (existing case_011 v5b OR new case)
  - M-TRACK-A2 · Stack-level Track C session 2 (new numerics class crossover)
  - M-DRIFT-V2 · stack-level corpus drift hook (V-series ↔ runtime corpus)
Tier 3 · charter close
  - M-TRACK-A3 · Stack-level Track C session 3 (validation case)
  - M-RADAR-V3 · capability radar v3 (AI axis ≥ 9.5 verification)
  - M-V63 · V62 close DEC + V63 charter draft
```

### Provisional outline · V62-B (Breadth)

```
Tier 1 · 解锁性
  - M-VOF-SCHEMA · interFoam multiphase BC schema + writer
  - M-VOF-CASE · multiphase-VOF case dispatch + e2e (candidate: KCS ship)
  - M-SHOCK-SCHEMA · rhoCentralFoam compressible-shock schema + writer
  - M-SHOCK-CASE · compressible-shock case dispatch + e2e (candidate: nozzle / RAE M2129)
Tier 2 · 第三新类 + 配套 advisor
  - M-LAGRANGE-SCHEMA · reactingParcelFoam Lagrangian schema
  - M-LAGRANGE-CASE · Lagrangian-particle case dispatch + e2e
  - M-A11 · multiphase BC validator advisor
  - M-A12 · shock-capture flux scheme advisor
  - M-A13 · particle injection point advisor
Tier 3 · 收口 + V63
  - M-STRESS-CASE · 6th e2e numerics class stress validation
  - M-V130 · V-series 行数 ≥ 130 marker
  - M-RADAR-V3 · radar 重画 (物理 axis ≥ 9.0, 求解器 ≥ 8.0)
  - M-V63 · V62 close DEC + V63 charter draft
```

### Provisional outline · V62-C (Harvest)

```
Tier 1 · 解锁性
  - M-CASE-007 · case_007 ship transom sediment (D8 9th cross-topology)
  - M-CASE-008 · case_008 airfoil TE sediment
  - M-CASE-014 · case_014 compressor MRF (A9 2nd-MRF unlock)
  - M-CASE-015 · case_015 HVAC diffuser (A6 2nd-HVAC unlock)
Tier 2 · advisor land + promotion
  - M-A6-LAND · A6 hvac_adpi LANDED
  - M-A9-LAND · A9 mrf_setup_advisor LANDED (or drafted-to-spec if 2-of-3 not yet met)
  - M-CASE-016 · case_016 sediment + D6/D9 sediment count
  - M-CASE-017 · case_017 sediment + D9/D10 sediment count
  - M-D6-PROMOTE · D6 LANDED (2-of-3 met)
  - M-D9-PROMOTE · D9 LANDED (2-of-3 met)
Tier 3 · catalog close + V63
  - M-CASE-018 · case_018 sediment
  - M-CASE-020 · case_020 sediment + D10 2-of-3 check
  - M-D3-D4 · Codex protocol amendment + dispatch wave seeding D3 + D4
  - M-V120 · V-series 行数 ≥ 120 marker
  - M-V63 · V62 close DEC + V63 charter draft
```

---

## 7. Main-session decision points

The main session **must** resolve these before flipping this DRAFT to charter:

1. **North Star selection**: A / B / C — or articulate a 4th candidate D combining 2 of 3 (with explicit scope cap to avoid 22-round review chain)
2. **Done Definition ratification**: take the selected candidate's table verbatim OR amend thresholds (e.g., V62-B's "≥130 V-rows" may be too lenient at 30 rows over 21 days at V61-198 cadence of 2.3/day)
3. **Tier outline finalize**: turn provisional milestone IDs into ROADMAP-style entries with deps annotation (matching V61-198 §3 format)
4. **Charter vs plan-file question**: per v2.3 scope-driven rule, V62-A and V62-B both cross ≥3 shared code paths → likely warrant full charter DEC. V62-C may fit as sub-DEC arc + light plan-file (no full charter). Main session decides.
5. **B20 prerequisite confirmation**: does V62 start AFTER V61-198 CLOSE flips to Accepted (post-B20), or does V62 open concurrently with B20 landing? Recommend **after** to keep arc-close pattern clean (matches V61-198's V61-130-pivot pattern).
6. **Notion sync timing**: per v2.3 round-1 rule, neither this DRAFT nor V61-198 CLOSE DRAFT syncs to Notion until both flip to Accepted. Main session runs session-end batch sync.

---

## 8. Carry-over from V61-198 §6 (sediment NOT closed)

Regardless of which North Star V62 picks, these 9 items remain open:

1. A6 hvac_adpi · drafted
2. A9 mrf_setup_advisor · candidate
3. D6/D9/D10 promotion · drafted
4. case_007/008/014-020 dispatch · 7 cases
5. D3 + D4 catalog gap
6. case_011 V94 face-zone loss · open
7. case_003 V98 external-RANS y+ infeasibility · documented not fixed
8. APU bay v33 mesh quality regression (V95 sediment · CLOSED NEGATIVE in V61-198)
9. unit_detector promotion to LANDED counter (not yet promoted despite B16 V96+V97 hardening)

V62-A defers these explicitly. V62-B addresses (1) + (2) + (3) only if intersect new numerics class cases. V62-C addresses (1)-(5) directly. (6)-(9) remain V63 candidates regardless.

---

## 9. Naming candidates for V62

If V62-A selected: **"Advisor Stack Closure Arc"**
If V62-B selected: **"Numerics Class Breadth Arc"** or **"Container Depth Arc"**
If V62-C selected: **"Harvest Cycle Closure Arc"**

---

**End of DRAFT.** Main session: select North Star → write
`.planning/2026-05-1?_v62_charter.md` final → optionally write
charter DEC `.planning/decisions/2026-05-1?_v62_<scope>_charter.md`
if scope hits v2.3 charter threshold.

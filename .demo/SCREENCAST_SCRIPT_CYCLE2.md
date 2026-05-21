# SCREENCAST_SCRIPT_CYCLE2 — cfd-harness-unified · M2.6 Cycle-2 · 2026-05-22 PM

Frame-by-frame manifest for the **cycle-2** Chinese MG demo. Builds on the
cycle-1 video (`cfdtrust_demo_mg_cn_2026-05-22.mp4`) by featuring 5 NEW
beats — the cycle-1 demo's TBD-17 moment is referenced but not re-told.

- **Total runtime**: 4:10
- **Renderer**: `.demo/build_demo_video_mg_cn_cycle2.py`
- **Output**: `.demo/cfdtrust_demo_mg_cn_2026-05-22_cycle2.mp4`
- **Captures dir**: `.demo/captures/2026-05-22T1600Z/`
- **Screenshots dir**: `.demo/screenshots_cycle2/`
- **Postproc**: `.demo/postproc/case_011/residual_plot_cycle2.png`
- **HEAD**: `600022b` (post-SHIP-verdict)
- **Project-governor checkpoint**: `.planning/milestones/PROJECT_GOVERNOR_CHECKPOINT_2_2026-05-22.md`

All numbers, commit SHAs, file paths in this script are verifiable —
the renderer scenes embed them character-by-character.

---

## Pacing summary

| Scene | Time | Beat | Source capture | Source PNG |
|---|---|---|---|---|
| Hook | 0:00–0:10 | "6 个生产 blocker 关闭" count-up | — | — |
| Recap | 0:10–0:25 | cycle-1 truth-chain still standing (9 围栏) | — | — |
| Beat 1 | 0:25–1:00 | case_011 multi-region CHT · BLOCKED-not-FAIL | `stage_01_case_011_multiregion.txt` | `shot_c2_case011_bc_quality.png` / `shot_c2_case011_trust_blocked.png` |
| Beat 2 | 1:00–1:35 | case_010 LES · BLOCK reason one door deeper | `stage_02_case_010_les_progress.txt` | `shot_c2_case010_les_block_reason.png` |
| Beat 3 | 1:35–1:55 | step-numbered mesh logs · industrial compat | `stage_03_step_numbered_logs.txt` | `shot_c2_step_numbered_logs.png` |
| Beat 4 | 1:55–2:30 | TBD-20 streaming · 13 GiB → bounded · 1/1→5/5 | `stage_04_streaming_parser.txt` | `shot_c2_streaming_payoff.png` |
| Beat 5 | 2:30–3:15 | **Gap #32 self-discovered + same-arc-fixed** (load-bearing) | `stage_05_gap32_self_discovered.txt` | `shot_c2_gap32_diff.png` |
| Real-shot interlude | 3:15–3:35 | 3 real screenshots interleaved | — | `shot_c2_case011_bc_quality.png` · `shot_c2_streaming_payoff.png` · `shot_c2_cycle2_commits.png` |
| Open queue | 3:35–3:55 | what's still queued (honest) | — | — |
| Closing | 3:55–4:10 | 441 / 19 / 6 / 0 / 1 stat cards | `stage_06_provenance_tests.txt` | — |

---

## Scene 1 · Hook (0:00–0:10)

**MG style**: dark bg, big number count-up from 0 to 6 (golden 220pt mono).

**On-screen Chinese**:
- Top: "上一轮 · 9 个物理域诚实 BLOCK"
- Center big number: animated 0 → 6
- Center subtitle: "个生产 blocker 关闭"
- Bottom: "+ 1 个引擎自己抓住自己" (red, fades in)

**Voice-over (optional)** (Mandarin): "上一周我们给 9 个物理域一个诚实的 BLOCK。这一周，我们又关了 6 个生产 blocker，外加引擎再一次抓住自己的一个 bug。"

**Provenance trailer for top-bar**: `cfd-harness-unified · 第二轮交付 · 2026-05-22`

---

## Scene 2 · Recap (0:10–0:25)

**MG style**: 9 circular regime badges in 3×3 grid, fade-in stagger.

**On-screen Chinese**:
- Title: "上一轮的 9 个围栏"
- Subtitle: "今天依然在"
- 9 badges (each is a regime): 层流 · 湍流 · CHT · 旋转 · 跨音速 · 多相 · LES · 工业 · 反应流
- Bottom strap: "9 / 9 围栏完整 · 0 个 false PASS"

**Voice-over**: "先回顾上一轮 — 九个物理域、九套围栏，今天都还在。引擎依然拒绝伪造 PASS。"

---

## Scene 3 · Beat 1 · case_011 multi-region CHT (0:25–1:00)

**MG style**: 3 colored region boxes appear (cold_fluid cyan / hot_fluid red / solid gold), then `layout: "multi_region"` Mono label flashes, then BLOCKED gold stamp drops in from above.

**Source evidence**:
- Real `bc_quality.json` showing `layout: "multi_region"` + 3 regions enumerated
  (`/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/bc_quality.json`, 2451 bytes)
- Real `trust_report.json` `bc_contract.status == BLOCKED` with reason
  `multi_region_bc_validation_not_yet_wired`
- DEC: `DEC-V61-201-SUB-INGEST-MULTI-REGION-BC` · commit `01d5567` · merge `f108e13`

**On-screen Chinese**:
- Title: "case_011 · plate-fin 紧凑式换热器"
- Subtitle: "chtMultiRegionSimpleFoam · 47M cell · 200/300 iter"
- Region boxes: 冷流体 (region_cold_fluid) / 热流体 (region_hot_fluid) / 固体 (region_solid)
- Label: `bc_quality.json · layout: "multi_region"` (mono, green)
- Underneath: "数据层 · 引擎看见了 3 个 region"
- BLOCKED stamp: "BLOCKED" + "reason: multi_region_bc_validation_not_yet_wired"
- Below stamp: "verdict 层故意不发证 · schema 还没完全接通"
- Bottom: "→ 引擎承认自己「还不能」 · 不是「不行」 · 也不是「随便给个 PASS」"

**Voice-over**: "case_011 — 多区共轭传热案例。引擎现在看得见 3 个 region 的边界条件数据；但 verdict 层故意不发证书，因为 schema 还没完全接通。这是诚实的推迟，不是 false-FAIL。"

---

## Scene 4 · Beat 2 · case_010 LES "one door deeper" (1:00–1:35)

**MG style**: 3 "doors" lined up horizontally; cycle-1 arrow stops at door 1 (red X), cycle-2 arrow advances to door 2 (green).

**Source evidence**:
- Capture `stage_02_case_010_les_progress.txt`
- Real cfdtrust output: BLOCK reason `no_time_directory_found` (was
  `case_dir_not_openfoam_compatible` in cycle-1)
- commit `914f944` · Gap #29 + Gap #31

**On-screen Chinese**:
- Title: "case_010 · DrivAer fastback · LES"
- Subtitle: "Gap #29 · 0.orig 规范布局接受 · commit 914f944"
- 3 door labels: "门 1 案例目录形状" / "门 2 时间目录存在" / "门 3 求解器证据"
- Mono subtexts: `case_dir_not_openfoam_compatible` / `no_time_directory_found` / `solver evidence missing`
- Cycle-1 arrow (red, into door 1): "Cycle-1: 卡在门 1 (错原因)"
- Cycle-2 arrow (green, into door 2): "Cycle-2: 通过门 1 → 卡在门 2"
- Bottom: "可验证的进度 · 不是 over-promise"
- Sub-bottom: "BLOCK 原因深入一层 · solver_execution 依然 skipped (不是 ingested)"
- Last: "→ 引擎拒绝声称自己跑过案例 (因为它没跑过)"

**Voice-over**: "case_010 是个 LES 外流场案例 — 上一轮在「案例目录形状」这道门就被拦下了，而且拦错了原因。这一轮通过了第一道门，老实卡在「时间目录存在」这一道门。这是可验证的进度，不是 over-promise — solver_execution 仍然是 skipped，引擎拒绝声称自己跑过这个案例。"

---

## Scene 5 · Beat 3 · step-numbered mesh logs (1:35–1:55)

**MG style**: 5 step-numbered log file boxes slide in from below, left-to-right. Then an arrow with "step 号最大 = canonical evidence" label.

**Source evidence**:
- Capture `stage_03_step_numbered_logs.txt` (git show 68f4a70 --stat)
- commit `68f4a70` · Gap #26-#27 · +67 LOC engine / +47 LOC tests · confidence: high

**On-screen Chinese**:
- Title: "在用户实际命名脚本的地方碰见用户"
- Subtitle (mono): "industrial run-script step-numbering · commit 68f4a70"
- 5 file boxes (mono): `01_blockMesh.log` / `02_snappyHexMesh.log` / `03_extrudeMesh.log` / `04_decomposePar.log` / `05_simpleFoam.log` (last in green)
- Arrow + label: "step 号最大 = canonical evidence"
- Conclusion: "我们不强制用户按特定风格命名" / "我们去找用户实际在用的命名"
- Provenance: "+ 67 LOC engine · +47 LOC tests · confidence: high"

**Voice-over**: "工业 CFD shop 普遍把脚本步号命名 — 01_blockMesh.log、02_snappyHexMesh.log。引擎现在两套命名都走，step 号最大的为 canonical evidence。我们不强制用户改命名 — 我们去找用户实际在用的命名。"

---

## Scene 6 · Beat 4 · streaming parser (1:55–2:30)

**MG style**: red bar grows to 13 GiB (cycle-1), then green tiny bar (cycle-2 bounded). Below: 1/1 → 5/5 fields with golden arrow between.

**Source evidence**:
- Capture `stage_04_streaming_parser.txt`
- Real `residuals.csv` header: `iter,Ux,Uy,Uz,h,p_rgh` (5 fields, 200 iter)
- commits `e8691f3` (TBD-15 + TBD-20) and `16e8dcf` (Gap #35 streaming follow-up)
- Test: `test_stream_parser_equivalence` (byte-identical proven)

**On-screen Chinese**:
- Title: "3.3 GiB 日志不再撑爆引擎"
- Subtitle (mono): "TBD-20 · streaming chunk parser · commit e8691f3"
- Red bar (cycle-1): "13 GiB" · "Cycle-1 · OOM"
- Green bar (cycle-2): "bounded chunk" · "Cycle-2 · OK"
- Sub-section title: "意外加成 · case_011 残差字段追踪"
- 1/1 card (red) → arrow → 5/5 card (green)
- Footer: "Ux · Uy · Uz · h · p_rgh — 全部进 residuals.csv"
- Sub-footer: "(byte-identical proven by test_stream_parser_equivalence)"

**Voice-over**: "case_009 级别的反应流日志能到 3.3 GiB，老的 text-path parser 读到 13 GiB RSS 就 OOM 了。新的 streaming parser 用 bounded chunk，输出 byte-identical proven by test。意外加成是 case_011 cycle-2：残差字段从 1 个跳到 5 个全 tracked，因为 streaming parser 顺手覆盖了 DILUPBiCGStab 和 multi-region 残差行。"

---

## Scene 7 · Beat 5 · Gap #32 self-discovery (2:30–3:15) — LOAD-BEARING

**MG style**: 3-phase emotional beat —
- Phase 1 (0.12-0.45): show 3 region rows with `__none_laminar__` chips highlighted in red, then golden annotation "★ __none_laminar__ 不是真字段 — 是 manifest 的 sentinel"
- Phase 2 (0.45-0.78): 3 horizontal panels: dogfood 发现 (gold) → 同弧修复 (green) → 12 commit 内落地 (cyan), each connected by golden arrow
- Phase 3 (0.78-1.0): anchor to cycle-1 TBD-17 — "这是 cycle-1 TBD-17 时刻的同型再现" / "诚实, 不是「打算诚实」"

**Source evidence**:
- Capture `stage_05_gap32_self_discovered.txt` (git show 77825b8 --stat)
- Dogfood report: `.planning/dogfood/DOGFOOD_CASE_011_CYCLE2_REDOGFOOD.md` §Gap #32
- commit `77825b8` · +39 LOC · +1 named test · confidence: high

**On-screen Chinese**:
- Big title (red mono): "Gap #32"
- Sub-title: "dogfood agent 自发现 · 同弧落地修复"
- Phase 1: 3 region rows showing leaked sentinel chips
- Phase 1 annotation: "★ __none_laminar__ 不是真字段 — 是 manifest 的 sentinel"
- Phase 2 panel titles: "dogfood 发现" / "同弧修复" / "12 commit 内落地"
- Phase 2 panel bodies:
  - "case_011 cycle-2 re-dogfood" / "见 sentinel 泄漏"
  - "commit 77825b8" / "+39 LOC · +1 test · confidence: high"
  - "不进 triage 队列" / "围栏依然完整"
- Phase 3: "这是 cycle-1 TBD-17 时刻的同型再现"
- Phase 3 body: "引擎依然在自己的运行中发现自己 · 不是 marketing fluff"
- Phase 3 punchline: "诚实, 不是「打算诚实」"

**Voice-over**: "这是这一轮的承重时刻。在 cycle-2 re-dogfood case_011 时，我们的 dogfood agent 发现 `__none_laminar__` 这个 manifest authoring 留的 sentinel 标记，泄漏到了 per-region expected_fields 里 — 引擎把它当成了真的字段。Cycle-2 自己抓住了自己。修复 commit 77825b8 在 12 个 commit 内落地，39 行，1 个 named test，confidence high。这是上一轮 TBD-17 时刻的同型再现 — 引擎依然在自己的运行中发现自己。这不是 marketing fluff，这是诚实，不是「打算诚实」。"

---

## Scene 8 · Real-screenshot interlude (3:15–3:35)

3 real PNG inserts, ~6.6s each, fade in/hold/fade out:

1. `shot_c2_case011_bc_quality.png` (75 KB) — caption: "case_011 · 真实 bc_quality.json · 多区数据层"
2. `shot_c2_streaming_payoff.png` (70 KB) — caption: "TBD-20 streaming · 真实 residuals.csv · 5 字段全 tracked"
3. `shot_c2_cycle2_commits.png` (160 KB) — caption: "Cycle-2 · 19 个 commit · 颜色按类别分"

**Voice-over**: "这些不是占位符 — 真实的 bc_quality.json，真实的 residuals.csv，真实的 19 个 commit。"

---

## Scene 9 · Open queue (3:35–3:55)

**MG style**: 6 tagged rows slide in from left, charter-class in red badge, spike-leftover in gold.

**On-screen Chinese**:
- Title: "仍未落地的工作"
- Subtitle: "我们不会说「即将上线」· 我们说「排队中」"
- Rows (tag · item · note):
  - [charter-class] Gap #18 · compressible_contract schema · thermophysical / perfectGas / sutherland / rho / T / Mach
  - [charter-class] Gap #28 · les_contract schema · turbulenceProperties / delta cubeRootVol / SGS
  - [charter-class] TBD-3 · vof_contract schema · interFoam phase-field awareness
  - [charter-class] TBD-18 · reacting_contract schema · species_list / inlet_compositions / combustion_model
  - [spike-leftover] TBD-16 · sub-second physical-time iter=0 collapse · breaks unsteady iteration discriminator
  - [spike-leftover] Multi-region bc_contract verdict-layer wiring · the deferred half of Gap #11

**Voice-over**: "诚实的开放清单：四个 charter-class schema 排队中 — 可压缩、LES、VOF、反应流。两个 spike-leftover 排队中。我们不说「即将上线」，我们说「排队中」。"

---

## Scene 10 · Closing CTA (3:55–4:10)

**MG style**: 5 stat cards (mono numbers, big), title slides up from bottom.

**On-screen Chinese**:
- Title: "诚实的 CFD 审计引擎"
- Subtitle: "第二轮交付 · 6 个生产 blocker 关闭"
- 5 cards:
  - 441 测试通过 (green)
  - 19 cycle-2 commit (cyan)
  - 6 生产 blocker 关闭 (gold)
  - 0 false PASS (green)
  - 1 引擎自发现 · 同弧修复 (red)
- Bottom-1: "AI 顾问 = Claude Code session · 读 V-series · 拒绝胡乱 PASS"
- Bottom-2 (big): "排队中, not coming soon"

**Voice-over**: "441 测试通过。19 个 cycle-2 commit。6 个生产 blocker 关闭。0 个 false PASS。1 个引擎自发现并在同一轮修复。AI 顾问就是这个 Claude Code session 在读 V-series corpus，拒绝胡乱发 PASS。剩下的工作排队中，not coming soon。"

---

## Production notes

- **No live re-runs**: every capture under `.demo/captures/2026-05-22T1600Z/` is real text from real commands run at HEAD `600022b`. The renderer embeds the text character-by-character via `font(size, "mono")`.
- **Cycle-1 anchor**: the cycle-1 video remains the foundation reference (`cfdtrust_demo_mg_cn_2026-05-22.mp4`). Cycle-2 video does NOT re-tell TBD-17 — it references it in scene 7 as the "this is the same shape" anchor.
- **Cycle-1 truth-chain not re-explained**: scene 2 just shows the 9-regime badge grid without re-explaining what each regime is. Audience either saw cycle-1 or doesn't need the recap.
- **Real screenshot policy**: 3 of the 7 cycle-2 PNGs are embedded directly in scene 8 (real-shot interlude). The other 4 are reserve material for OBS-style productions that want to swap in more screenshots.
- **Closing card stat sources** (verifiable):
  - 441 tests: PROJECT_GOVERNOR_CHECKPOINT_2 §3
  - 19 commits: `git log --oneline 5769673..HEAD | wc -l`
  - 6 blockers: 2 production-blocker DECs + 4 spike-class closures
  - 0 false PASS: re-dogfood reports confirm
  - 1 self-discovered: Gap #32 (commit 77825b8)

---

## Amendment 2026-05-22 post-Codex R0

**Trigger**: After the cycle-2 MP4 was already rendered, Codex 86gs gpt-5.4
xhigh ran a cadence-floor review of the full 32-commit M2.6 arc and
returned **CHANGES_REQUIRED** with 2 P1 + 1 P2 findings. The engine
refused to ship the demo before all 3 findings closed.

**Resolution**: All 3 findings RESOLVED in 1 round at commit `b585cd9`.
This is the cycle-2 equivalent of the cycle-1 TBD-17 self-discovery beat —
except now the snitch is Codex (independent reviewer) instead of dogfood.

**Findings (real text from `/private/.../tasks/bz3oof9ba.output`)**:

| Sev | Tag | Location | Substance |
|---|---|---|---|
| P1 | Gap #36 | `openfoam.py:1611-1613` | 0.orig multi-region detection blind spot — `_detect_multi_region_layout()` only inspected `0/`; case_011 CHT staged as `0.orig/region_*/` fell through to single-region path |
| P1 | Gap #37 | `openfoam.py:2341-2345` | step-numbered logs inside `log_*/` subdirs — walker only tried exact basenames; case_006 `log_v64_v3/02_rhoSimpleFoam.log` missed |
| P2 | schema | `case_manifest.schema.json` | `bc_contract.turbulence_fields` required + minItems:1 blocked Gap #31 model-derived fallback from CLI path |

**Test delta**: 441 → 443 passed (2 new regression tests cover both P1).

**Round arc**: R0 CHANGES_REQUIRED → R1 RESOLVED. Codex round cap = 3
(per DEC-V61-133); used 1.

### Addendum deliverable (45s standalone MP4)

- **Renderer**: `.demo/build_demo_codex_r0_r1_addendum.py`
- **Output**: `.demo/cfdtrust_demo_mg_cn_2026-05-22_codex_r0_r1_addendum.mp4`
- **Duration**: 45.0s · 1280×720 · 24fps · 446 KB
- **Capture**: `.demo/captures/2026-05-22T1700Z/stage_codex_r0_r1_resolved.txt` (real `git log`, `git diff --stat b585cd9~1 b585cd9`, real `pytest` output)
- **Screenshot**: `.demo/screenshots_cycle2/shot_codex_r0_resolved.png` (renders real review text styled as terminal capture)

**5-scene structure**:

| Scene | Time | Beat |
|---|---|---|
| Hook | 0:00–0:06 | "上线前最后一刻，Codex 又抓住 3 个漏网之鱼" |
| Review-In | 0:06–0:18 | Codex R0 badge · CHANGES_REQUIRED verdict · P1×2 P2×1 count-up |
| Findings | 0:18–0:30 | 3 finding cards slide in (Gap #36 / Gap #37 / schema) |
| Resolution | 0:30–0:38 | 3 findings → b585cd9 → R1 RESOLVED · tests count-up 441 → 443 |
| Punchline | 0:38–0:45 | "引擎再一次被引擎抓住 · 诚实是承诺" · 3/1/1 stat strip |

**Elevator pitch (Chinese, one line)**:
> 引擎再一次被引擎抓住——Codex 在上线前最后一刻挑出 3 个 cycle-2 修复
> 没补全的窟窿，1 个 commit 关掉全部 3 个 finding，1 轮 round，诚实是承诺。

**Why standalone (not re-rendered into the full MP4)**:
Re-rendering the full 4:10 cycle-2 video to splice in a 45s beat costs
~6× the frame count for 18% added runtime; producing a standalone
addendum lets the stakeholder choose to play it inline after the main
demo, or send it separately as a "by the way" beat. The cycle-2 MP4 at
HEAD `600022b` stays canonical; the addendum is at HEAD `b585cd9`.

**Voice-over**:
> "上线前最后一刻，Codex 又抓住 3 个漏网之鱼。两个 P1，一个 P2，全部
> 集中在 cycle-2 修复 cycle-1 漏洞的衔接处——0.orig 多区布局没合上、
> step-numbered log 子目录没合上、schema 把新的 Gap #31 回退路径锁
> 死。一个 commit b585cd9 关掉全部三个 finding，441 个测试涨到 443，
> 多写了 2 个回归测试。Codex round cap 是 3，用了 1，剩 2 没用。引擎
> 再一次被引擎抓住。3 个 finding，1 个 commit，1 轮 round。诚实是承诺。"

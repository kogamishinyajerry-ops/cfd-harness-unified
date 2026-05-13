# 1-Page Speaking Cheat Sheet

> Print this or load on phone/iPad. Reference during demo; don't read aloud.

## Opening (Segment 1)

> "工业算例：APU 舱通风评估。MES day 55 °C 极端工况，燃烧室出口 2.8 kg/s @ 616 K 注入舱内，apu_intake 4.85 kg/s 抽吸出去，14 个 APU body 表面温度 343-674 K。问题：bay 平均空气温度、body 对流传热、抽吸路径效率。
> 传统流程：CAD ingest → mesh → BC → solver 调试 → 后处理，5-7 天 + 多次发散。
> 今天 30 分钟，Claude Code session 全程驱动 + AI advisor 在关键决策点给建议但不代替我决定。"

**Tone**: peer-to-peer. Don't sell.

---

## Segment 2 — CAD → Mesh

| Talking beat | Trigger when |
|---|---|
| "17 个 patch，全部 frozen 在 `naming.yaml`" | After `cat config/naming.yaml` |
| "patch 名 = STL 名 = mesh 名 = BC 名 = post 名" | After patch list |
| "refinementBox jet L3 + 3 层 prism，工业 trade-off" | After `sed snappyHexMeshDict` |
| "943k cells，sweet spot for ARM 4-core" | After sHM log |

**Don't say**: "我们的 mesh 算法很先进" — peers want numbers, not adjectives.

---

## Segment 3 — V-series Corpus

| Talking beat | Trigger when |
|---|---|
| "84 V-row，runtime-loadable，不是 PDF 不是 web 抓的" | After `wc -l` + `grep -c "^### V"` |
| "V84 昨天才沉淀，今天 demo 已经在用这个原则" | After V84 awk |
| "find_relevant 是 `/ai-review` 走的同一个 path" | After `sed corpus_loader.py` |
| "**这就是 LLM-offline 可跑的根** — corpus 查询不需要任何 LLM" | After ad-hoc query |

**Beat to land**: "corpus = project asset". Peers will then trust the advisor moments in Segment 5.

---

## Segment 4 — Solver Highlights

| Image | One-line | Time |
|---|---|---|
| 01 T axial Z=0 | "燃烧室 600 K 锥形热源，边界 fixedValue 忠实呈现" | 40 s |
| 03 \|U\| axial Z=0 | "jet 冲击 + recirculation 结构，速度场不受能量耗散影响" | 40 s |
| 04 Inner_Surf T | "14 个 APU body 表面温度梯度，对流冷却建立" | 40 s |
| 05 firewall + combustor | "firewall 局部，热扩散范围 — **注意这里下游有点冷**" | 30 s |
| 06 streamlines combustor | "燃烧室出口流线" | 30 s |
| 07 streamlines intake | "apu_intake 抽吸流线 — 通风路径全可视化" | 30 s |
| 08 combined | "综合视图，工业级交付物" | 30 s |

**Segue line into Segment 5**:
> "定性结论都对。**但**理论能量平衡 bay 均温应该是 494 K，仿真出来 328-350 K — 30 % 低估。为什么？听 AI advisor 怎么诊断。"

---

## Segment 5 — Advisor Videos

| Moment | Setup line (10 s) | Wrap line (10 s) |
|---|---|---|
| 1 | "先看一个 mesh 决策时刻 — max_skew 6.87，能跑吗？" | "引了 V84 + V8 + S3，给了 5-min smoke 验证 — 没替我决定" |
| 2 | "现在看温度低估的诊断" | "三个数值耗散根因 + 4 条路线 + 每条 ETA + ARM 4-core 成本，可审计" |
| 3 | "我说我只有 7 天 ARM 4-core，advisor 怎么排优先级" | "给了 Mon-Sun 周计划 + 显式说哪条 deprioritize + 反问我一个 calibration 问题" |

**After all 3 videos** (15 s):
> "Note what just happened — advisor 引用 corpus、命名根因、给可审计 ETA，整个过程**工作台仍然 LLM-offline 可跑**，**AI 只给建议**，**每个 claim 都有 corpus 引用**。这就是 4 问门控全部 PASS 的姿态。"

---

## Segment 6 — Positioning

> "DEC-V61-198 四个 pillar 全部有实证：Run-and-correct（mesh debug arc）/ Sediment-as-you-go（V-series 实时沉淀）/ Strategic narrative coherence（Claude Code session = 唯一窗口）/ Solver execution from Bash（case_002a F4b · 10.4h 验证）。
> 差异化 vs 其他 CFD AI 工具：(1) LLM offline runnable — 工作台全流程不依赖 LLM 在线 / (2) AI advisor not driver — 4 问门控强制 / (3) V-series sediment — 每个 case 都补一行，项目自有 corpus 不爬 web。
> Q&A 时间。"

---

## Hard rules during demo

1. **不说**："AI 自动完成"、"无需人工"、"智能助手"
2. **要说**："advisor 给建议"、"工程师决定"、"corpus-cited"
3. 被追问"AI 准确率多少" → 答："不是准确率问题 — advisor 引用 corpus，corpus 是项目自有，accuracy = corpus quality + 工程师 judgment，两者都可审计"
4. 被追问"这跟 ChatGPT 包装有什么不同" → 答："corpus_loader 离线工作；advisor 失败时工作台不退化；4 问门控不允许 AI 写算例文件 — 三条都是结构性差异不是 UX 差异"
5. Q&A 失控时硬停："时间到了 — 我会把 `~/Desktop/cfd-harness-unified/CLAUDE.md` 和 corpus 链接发给大家，深入聊会后约"

---

## 紧急情况脚本

- **terminal 卡了** → "我们走 plan B" → 切换到 backup 全程 screencast
- **HTML 报告打不开** → 直接 `open paraview_HD_v3_smooth/` 用 Preview 翻图
- **advisor 视频卡** → "我口述一下 — Moment N 的核心是 [10s key beat]，回头发完整视频"
- **超时 27 min** → 跳过 Segment 6 positioning，直接进 Q&A

# 05 · Dialogue Script · 完整对白 + 字幕

> 每幕：工程师气泡 / Advisor 气泡 / 屏底主字幕 / 屏底副字幕。
> 配音 (若有) 跟气泡 + 字幕同步。
> 中文断句原则：主字幕 ≤ 18 字、副字幕 ≤ 24 字。

---

## E0 · 钩子 (12 s)

**无对白**（无角色气泡 — 营造孤独感）

**屏底主字幕**：
> 你做 CFD 的时候，是不是也这样？

**屏底副字幕**（小字 mono 灰色）：
> APU 舱通风 · 943k cells · Day 6 · solver still diverging

---

## E1 · 痛点 ① (8 s)

**👷 工程师 (思考)**：
> 我的 patch 名呢？

**屏底主字幕**：
> V1 · CATIA STEP 标签丢失

**屏底副字幕**：
> 17 patches 变 19 个 Part00X

---

## E2 · 痛点 ② (8 s)

**🧑‍💻 工程师 (说话)**：
> ω 怎么又炸了？

**🤖 Advisor (说话 · 首次出现)**：
> 要不要我查 V3？

**屏底主字幕**：
> V3 · k-ωSST + 零 IC → ω blowup

**屏底副字幕**：
> potentialFoam -writePhi 预热可解

---

## E3 · 痛点 ③ (8 s)

**🧑‍💻 工程师 (思考)**：
> 看起来对，但…

**屏底主字幕**：
> 30% 数值耗散 — 工程师的责任是诚实

**屏底副字幕**：
> cfd-harness 主动写进 CAVEAT.md

---

## E4 · 发现 (10 s)

**🧑‍💻 工程师 (说话)**：
> 你是？

**🤖 Advisor (说话)**：
> 我是 Advisor。
> 我不替你做决定，我给你依据。

**屏底主字幕**：
> 工程师 + AI 副驾 = cfd-harness-unified

**屏底副字幕**：
> ① LLM offline runnable  ② Advisor not driver
> ③ V-series sediment  ④ Project-owned corpus

---

## E5 · 步骤 1 — 几何 ingest (20 s)

**🤖 Advisor (说话)**：
> naming.yaml = 单一真相源。
> 从 STL 一路贯穿到 BC 和后处理。

**🧑‍💻 工程师 (说话 · 点头)**：
> 命名对了，下一步。

**屏底主字幕**：
> ① 几何 ingest · 17 patches 锁进 naming.yaml

**屏底副字幕**：
> Part::insert ✗  →  Import.insert ✓

---

## E6 · 步骤 2 — 网格决策 (25 s)

**🧑‍💻 工程师 (思考 · 看向 advisor)**：
> max_skew 6.87，能跑吗？

**🤖📋 Advisor (说话 · 翻书到 V84)**：
> V84 说，跑 50 步 smoke test 看看。
> 5 分钟比 7 小时值得。

**🧑‍💻 工程师 (说话 · 跨步)**：
> 5 分钟不要紧。

**屏底主字幕**：
> ② 网格决策 · V84 · 5 分钟 smoke > 7 小时重 mesh

**屏底副字幕**：
> max_skew 6.87 stably · 943,289 cells · potentialFoam -writePhi

---

## E7 · 步骤 3 — 求解 (30 s)

**🧑‍💻 工程师 (说话 · 看屏幕)**：
> 0 FATAL。
> 943k cells，10.4 小时，4-core ARM。
> 值。

**屏底主字幕**：
> ③ 求解 · 943k cells · 10.4 h · 4-core ARM · 0 FATAL

**屏底副字幕**：
> p_rgh 1.8e-5  ·  omega 1.4e-4  ·  k 6.4e-4

---

## E8 · 步骤 4 — 后处理 + 审计 (30 s)

**🧑‍💻 工程师 (说话 · 指向图)**：
> |U| 对，结构对。
> 但温度偏低 30%。

**🧑‍💻 工程师 (说话 · 敲键)**：
> 记下来，V85。

**🤖 Advisor (说话 · 点头)**：
> 85 行 corpus 又多了一行。

**屏底主字幕**：
> ④ 后处理 + 审计 · 8 HD · CAVEAT 诚实写 · V85 沉淀

**屏底副字幕**：
> 理论 494 K vs 仿真 350 K · 差距 30% · 数值耗散三根因

---

## E9 · 收尾 (15 s)

**🧑‍💻 工程师 (说话 · 看 advisor)**：
> 工作台永远能跑。
> 决策永远是我的。

**屏底主字幕**：
> 4-pillar 治理 · 工程师的 AI 副驾

**屏底副字幕**：
> LLM-offline · advisor-not-driver · V-series sediment · project corpus

---

## E10 · End Card (5 s)

**全屏白字** (无气泡、无字幕条)：

```
cfd-harness-unified
工程师的 AI 副驾

1 个真实 APU 舱算例  ·  943k cells  ·  10.4 h
84 V-rows corpus       ·  4-core ARM  ·  0 FATAL
30% 偏差诚实写进 CAVEAT.md
```

底部 mono 18 灰字：
> 基于 cfd-harness-unified + apu-bay-ventilation-cht · 2026-06-01

---

## 字幕断句规范

| 规则 | 示例 |
|---|---|
| 主字幕 ≤ 18 字 | "V3 · k-ωSST + 零 IC → ω blowup" |
| 副字幕 ≤ 24 字 | "potentialFoam -writePhi 预热可解" |
| 数字用 mono 字体，与文字分开 | "943k cells · 10.4 h" |
| 英文术语用 mono 字体 | "V84 · potentialFoam" |
| 表情 emoji 仅用于角色对话 | 💭 (思考) / 💬 (说话) |
| 屏幕文字用半透明背景 | 字幕条 #000 80% alpha |
| 同义不重复 | "FATAL" 出现一次；"0 FATAL" 出现一次 |
| 关键数字用 highlight color | "30%" 黄高亮、"6.87" 黄高亮 |

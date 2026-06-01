# 00 · Concept · 科普动画级 Demo v2

> 目标：把现有 v6N B+ advisor demo 升级为「Kurzgesagt × 3Blue1Brown」风格的科普动画。
> 保留真实工程截图作为信用锚，叠加 emoji 人物 + 叙事弧线 + 注释式注意力设计。

---

## 1. 受众 & 时长

| 维度 | v1 (现有) | v2 (本次规划) |
|---|---|---|
| 受众 | CFD 同侪 (peer) | CFD peer + 决策层 + 公众科普 |
| 时长 | 5 min | 3 min (主片) + 90 s (预告片，可选) |
| 平台 | 会议演讲 + 录屏 | 视频平台 + 嵌入 PPT + 独立公众号 / B 站 |
| 配音 | 现场口播 | 旁白录制 (中文，可选) |
| 风格 | 工程文档 + 字幕条 | 科普动画 |

## 2. 关键差异 (v1 → v2)

| 维度 | v1 | v2 |
|---|---|---|
| **叙事** | 无，纯信息陈列 | 9 幕故事弧线：钩子 → 痛点 → 发现 → 解决 → 沉淀 → 收尾 |
| **人物** | 无 | 🧑‍💻 工程师 + 🤖 Advisor + 工具集 emoji |
| **交互** | 静态截图 + 字幕 | 人物移动到文档/工具、翻页、指向、打勾 |
| **注意力** | 靠字幕 + 切镜 | 黄圈聚光 / 红箭头 / 数字徽章 / 闪烁高亮 / 推近 |
| **真实内容** | 25+ 张整图 | 同样的图，但**裁切 + 局部放大 + 注释** |
| **知识库引用** | 仅口播 | 屏幕上演示翻到 V84 / V1 / V3 真实文本 |
| **V-series sediment 演示** | 仅口播 | 工程师亲自打一行新 V85 进 corpus |
| **品牌信息** | 30-min 现场 | 4-pillar checklist 视觉化收尾 |

## 3. 三大不变 (信用锚)

> 无论风格怎么变，下面三条是 CFD peer 信任的底线，v2 必须保留：

1. **真实工程截图** — 943k cells / max_skew 6.875 / 10.4h / 4-core ARM / HD ParaView 8 张 / ENGINEERING_CAVEAT 30% 数字
2. **真实 V-series 引用** — 翻到 V1 / V3 / V84 的真实文本，不是编造
3. **诚实 caveat** — 30% bay-T 偏差不藏起来，反而在第 8 幕正面讲，作为「advisor 提示 + 工程师决定」的范本

## 4. 一句话定位

> **"工程师 + AI 副驾，一起把工业 CFD 跑成可审计的工程交付物。"**

副驾 = advisor 角色（不替代方向盘），可审计 = 4-pillar 治理 + corpus 引用链 + 工程师最终决定。

## 5. 9 幕概览 (3 min 节奏)

| # | 幕名 | 时长 | 目的 | 关键真实素材 |
|---|---|---|---|---|
| E0 | 钩子 — 2AM 工程师 | 12 s | 共情 | solver log NaN 行 + 便利贴 |
| E1 | 痛点 ① — 几何标签丢失 | 8 s | 引 V1 | naming.yaml patch 名 + STEP 输出对比 |
| E2 | 痛点 ② — k-ωSST 零 IC 爆炸 | 8 s | 引 V3 | solver log NaN + potentialFoam 命令 |
| E3 | 痛点 ③ — 30% 温度偏差 | 8 s | 引 CAVEAT | 理论 494K vs 仿真 350K 柱图 |
| E4 | 发现 — Advisor 出现 | 10 s | 介绍角色 | 4-pillar 名词卡 |
| E5 | 步骤 1 — 几何 ingest | 20 s | 演示 | naming.yaml 30 patches + 真实 STL 3D 渲染图 |
| E6 | 步骤 2 — 网格决策 | 25 s | 演示 + 决策 | sHM 网格图 + V84 真实文本 + 残留曲线 |
| E7 | 步骤 3 — 求解 | 30 s | 演示 | residuals.png 真实曲线 + sHM log 末 30 行 |
| E8 | 步骤 4 — 后处理 + 审计 | 30 s | 演示 + 沉淀 | 8 HD 缩略 + ENGINEERING_CAVEAT 节选 + 新 V85 行 |
| E9 | 收尾 — 4-pillar checklist | 15 s | 收口 | 4-pillar 4 卡片 + 项目名 + corpus 编号 |
| **E10** | **end card** | **5 s** | **品牌** | **1 APU 算例 (943k, 10.4h) · 84 V-rows · 工程师永远决策** |

合计约 **3 min** (181 s)

## 6. 文件目录

```
.planning/demos/2026-06-01_emoji_animation_v2/
├── 00_concept.md          ← 本文件
├── 01_design_system.md    ← 视觉 + 角色 + 注释 + 镜头
├── 02_storyboard.md       ← 9 幕分镜 (每幕：时长/动作/对白/字幕/资产/标注)
├── 03_asset_inventory.md  ← 每个真实素材的绝对路径 + 行号
├── 04_production_pipeline.md  ← PIL + ffmpeg 制作流程
├── 05_dialogue_script.md  ← 完整对白 + 字幕 + 旁白
├── 06_prototype/          ← 演示 E6 一幕的 HTML prototype
│   ├── prototype.html     ← 单文件 HTML+CSS+JS，浏览器打开看
│   └── README.md          ← 怎么用 prototype 验收
├── 99_PLAN.md             ← 给执行 agent 的总规划 (v2 制作时直接照这个跑)
└── storyboard_frames/     ← 9 幕概念帧 (用 PIL 预生成 1 张/幕作锚)
```

## 7. 验收标准 (Definition of Done)

v2 主片 3 min 必须满足：

- [ ] 9 幕顺序 / 时长 / 关键资产全部按 02_storyboard.md 落地
- [ ] 至少 **5 个 V-row 真实文本** 在动画里被高亮 (V1 / V3 / V8 / V84 + 新 V85)
- [ ] 至少 **6 张真实工程截图** 被裁切使用 (不是原图整张)
- [ ] 至少 **3 次注意力引导** 用 yellow circle / red arrow / number badge
- [ ] 至少 **1 次镜头推近** (zoom 1.0x → 1.4x on a real content)
- [ ] 至少 **1 次焦平面拉** (background blur when character 思考)
- [ ] 4-pillar checklist 出现在 E9 收尾
- [ ] 30% 偏差 honesty 在 E8 正面出现
- [ ] 工程师角色全程出场，Advisor 在 E4 出现后贯穿
- [ ] 旁白中文，断句 ≤ 12 字 / 句
- [ ] 字幕中文，断句 ≤ 18 字 / 行

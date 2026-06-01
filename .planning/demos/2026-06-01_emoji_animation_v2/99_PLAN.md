# cfd-harness-unified · 科普动画级 Demo v2 · 总规划

> **作者**：Claude Code Opus 4.7 session · **日期**：2026-06-01
> **状态**：规划完成 (本文件) + 1 幕 HTML 原型 (E6)
> **目标**：把现有 5-min v1 advisor demo 升级为 3-min 科普动画版，叠加 emoji 人物 + 叙事弧线 + 注释式注意力设计

---

## 1. 执行摘要 (30 秒读完)

**v1 现状**：5 分钟视频 = 25+ 张真实工程截图 + 底部字幕 + fade 转场。优点是真实可信，缺点是**没有人物、没有叙事、没有注意力设计** — 像产品文档视频，不像科普动画。

**v2 目标**：3 分钟视频，**保留 v1 全部真实资产**作为信用锚，**叠加 4 层增量价值**：
1. 🧑‍💻🤖 **角色 + 叙事弧线** (9 幕：钩子 → 痛点 → 发现 → 解决 → 沉淀 → 收尾)
2. 💭💬 **思考/说话气泡** (工程师问，Advisor 答，引用真实 V-row)
3. 🟡🔴🟢 **注释式注意力设计** (黄圈聚光 / 红箭头 / 绿框 / 数字徽章 / 闪烁高亮)
4. 🎬 **镜头运镜** (推近 / 拉远 / 摇移 / 焦平面拉 / 高光扫)

**受众**：CFD peer (工程师语态) + 决策层 (4-pillar 收口) + 公众科普 (emoji 视觉)

**最关键的差异**：v2 的每一幕都会**演示一次工程师与 advisor 的互动 + 引用一个真实 V-row**，让 peer 看到「这工具是真的在工程师手边用，不是 PPT 包装」。

---

## 2. v1 → v2 关键差异表

| 维度 | v1 (现有) | v2 (本次) | 增量价值 |
|---|---|---|---|
| **时长** | 5 min (v6N B+) | 3 min (主片) + 90 s 预告 | 紧凑 + 复用 |
| **叙事** | 无 | 9 幕弧线 | 观众记得住故事 |
| **人物** | 无 | 🧑‍💻 + 🤖 + 📚 + 🖥️ + 🎨 + 🕸️ + 📈 + 📦 | 工程师与 AI 副驾具象化 |
| **对白** | 仅现场口播 | 工程师 / Advisor 气泡 + 字幕 | 文字可读 + 配音可加 |
| **真实内容** | 25+ 张整图 | 同样图，**裁切 + 注释** | 注意力聚焦 |
| **V-series 引用** | 仅口播 | 屏幕上演示翻到 V84 真实文本 | trust gate 显式化 |
| **Sediment 演示** | 仅口播 | 工程师敲 V85 入 corpus | "真的在沉淀" 视觉化 |
| **4-pillar 收尾** | 仅口播 | E9 4 卡片动画 | 品牌信息视觉化 |
| **30% 偏差** | 仅 ENGINEERING_CAVEAT.md 链接 | E3 + E8 正面演 | honesty 显式化 |
| **可复用性** | 1 个视频文件 | 9 个 HTML 模块 (E[0-9]) | 易改易复用 |

---

## 3. 9 幕 3 min 节奏

| # | 幕名 | 时长 | 关键真实素材 | 视觉重心 |
|---|---|---|---|---|
| **E0** | 钩子 — 2AM 工程师 | 12 s | 真实 solver log NaN 行 | 暗室 + 暖橙台灯 |
| **E1** | 痛点 ① — 几何标签丢失 | 8 s | V1 文本 + naming.yaml 19 patch | 红箭头 + 红叉 |
| **E2** | 痛点 ② — k-ωSST 零 IC 爆炸 | 8 s | V3 文本 + NaN log | 💥 爆炸 + `potentialFoam` 绿框 |
| **E3** | 痛点 ③ — 30% 温度偏差 | 8 s | CAVEAT 理论 494K vs 仿真 350K | 数字滚动 + 黄圈 |
| **E4** | 发现 — Advisor 出现 | 10 s | 4-pillar 4 卡片 | 文件夹展开 + light sweep |
| **E5** | 步骤 1 — 几何 ingest | 20 s | naming.yaml + 真实 STL 渲染 | 数字徽章 ① + 旋转 3D |
| **E6** | 步骤 2 — 网格决策 | 25 s | **V84 真实文本** + sHM log + residual 曲线 | **数字徽章 ② + 闪烁高亮 6.87** |
| **E7** | 步骤 3 — 求解 | 30 s | residuals.png + log p_rgh 1.8e-5 | 5 个绿框 + 时钟快进 |
| **E8** | 步骤 4 — 后处理 + 审计 | 30 s | 8 HD 缩略 + CAVEAT + V85 合成行 | 数字徽章 ④ + 字符打字 |
| **E9** | 收尾 — 4-pillar checklist | 15 s | 4 卡片 + ✅ + 项目名 | 4 卡片依次 pop-in |
| **E10** | End Card | 5 s | 1 算例 · 84 V-rows · 30% honesty | 全屏白字 |

合计 **171 s** ≈ **3 min 00 s** (含 11 段幕间 fade 0.4 s)

> **优先级**：E0 / E4 / E5 / E6 / E7 / E8 / E9 是 P0 必做；E1-E3 痛点可快闪合并；E10 可选。

---

## 4. 文档结构

```
.planning/demos/2026-06-01_emoji_animation_v2/
├── 00_concept.md                    ← 概念 / 受众 / 时长 / 验收标准
├── 01_design_system.md              ← 色板 / 角色 / 气泡 / 注释 / 镜头
├── 02_storyboard.md                 ← 9 幕分镜 (时长/动作/对白/字幕/资产/标注)
├── 03_asset_inventory.md            ← 真实素材出处 (绝对路径 + 行号)
├── 04_production_pipeline.md        ← HTML 动画 + 浏览器录屏 + ffmpeg
├── 05_dialogue_script.md            ← 完整对白 + 字幕规范
├── 06_prototype/                    ← E6 概念验证
│   ├── prototype.html               ← 单文件 HTML+CSS+JS · 18s 循环
│   └── README.md                    ← 怎么打开 + 时间轴 + 录屏方法
├── 99_PLAN.md                       ← 本文件 (执行摘要)
└── storyboard_frames/               ← 9 幕概念帧 (制作时填充)
```

---

## 5. 视觉系统速览 (详见 `01_design_system.md`)

### 色板
- `bg-deep` `#0E1A2B` 主背景
- `accent-warm` `#FFA94D` 暖橙 — 角色光、聚光、CTA
- `accent-yellow` `#FFD43B` 高亮黄 — 关键信息、聚光、勾
- `ok-green` `#51CF66` 收敛 / ✅
- `ng-red` `#FF6B6B` 失败 / NaN / 偏差 / ✗
- `accent-cyan` `#74C0FC` 信息蓝 — 链接、副标题、V-id

### 角色
- 🧑‍💻 工程师 (贯穿)
- 🤖📋 Advisor (E4 出现后贯穿)
- 📚 知识库 (E4 / E6 / E8)
- 🖥️ Solver (E7)
- 🎨 CAD / 🕸️ Mesh / 📈 Plot / 📦 Audit (按幕出现)

### 注释元素
- 🟡 黄圈聚光 (脉冲 0.8 Hz)
- 🔴 红箭头
- 🟢 绿框 (带角标)
- ① ② ③ ④ 数字徽章 (暖橙底白字 mono)
- ✨ 闪烁高亮 (1.2 Hz 文字下黄底)
- 🔍 放大镜 (推近时)

### 镜头运镜
- 推近 (zoom 1.0 → 1.4)
- 拉远 (zoom 1.4 → 1.0)
- 摇移 (horizontal pan)
- 焦平面拉 (Gaussian blur 4 px)
- 高光扫 (light sweep)
- 数字滚动 (counter 0 → target)
- 字符打字 (type-on 40 ms/字)
- 窗口淡入淡出 (scale 0.95 ↔ 1, alpha 0 ↔ 1)

---

## 6. 真实内容出处 (peer 可验证)

> 5 个 V-row 真实文本 + 11 张真实图像 + 3 个真实配置文件 + 1 个真实 log 文件
> 全部绝对路径，见 `03_asset_inventory.md` §F 「数据来源对照」表

| 幕 | 资产 | 绝对路径 |
|---|---|---|
| E0 | solver log | `case_refined_v2/log/pimple_v2_plateau.log` |
| E1 | V1 + naming.yaml | `industrial_solver_findings_v_series.md:56-67` + `inputs/naming.yaml` |
| E2 | V3 + NaN log | `:81-92` + log grep "NaN" |
| E3 | CAVEAT | `reports/v6N/ENGINEERING_CAVEAT.md` |
| E5 | naming.yaml + 3D 渲染 | `inputs/naming.yaml` + `reports/v7_steady/CHT_role_iso_back.png` |
| **E6** | **V84 + 网格 + sHM log** | **`: grep "^### V84"` + `V8_sceneE_envelope_side_Ym.png` + `sHM_v2_tight.log`** |
| E7 | residuals.png + log | `reports/v6N/plots/residuals.png` + `pimple_v2_plateau.log` |
| E8 | 8 HD 缩略 + CAVEAT | `reports/v6N/paraview_HD_v3_smooth/0[1-8]*.png` |

---

## 7. 生产流程 (详见 `04_production_pipeline.md`)

### 选型：HTML + CSS + JS + 浏览器录屏

> v1 走的是 PIL 拼帧 + ffmpeg。v2 改用 **HTML 动画**：
> - emoji 渲染零摩擦 (系统字体原生支持)
> - CSS 动画丰富 (`transform / filter / animation / transition`)
> - 9 幕单文件，复制 9 份改文字/时间轴即可
> - 浏览器录屏 → ffmpeg concat → 整片

### 时间线 (8 天)

| 阶段 | 天数 | 产出 |
|---|---|---|
| D1 概念 + 设计 + 分镜 | 1 | 本规划 6 份文档 |
| D2 资产预处理 | 1 | 9 份裁切 + 缩放图 |
| D3 HTML 模板 + E0/E4/E9 | 1.5 | 3 幕 HTML |
| D4 E1/E2/E3 痛点 | 0.5 | 3 幕 HTML (或合并 1 幕) |
| D5 E5/E6 | 1.5 | 2 幕 HTML |
| D6 E7/E8 | 1.5 | 2 幕 HTML |
| D7 E10 + 字幕 + QA | 1 | 终版 MP4 |
| **总** | **8** | 3 min MP4 |

### 紧凑版 (3 痛点合并)：6 天
### 豪华版 (加配音 + 双语)：10 天

---

## 8. 验收标准 (Definition of Done)

v2 主片 3 min 必须满足：

- [ ] 9 幕顺序 / 时长 / 关键资产全部按 `02_storyboard.md` 落地
- [ ] 至少 **5 个 V-row 真实文本** 在动画里被高亮 (V1 / V3 / V8 / V84 + 新 V85)
- [ ] 至少 **6 张真实工程截图** 被裁切使用 (不是原图整张)
- [ ] 至少 **3 次注意力引导** 用 yellow circle / red arrow / number badge
- [ ] 至少 **1 次镜头推近** (zoom 1.0x → 1.4x on a real content)
- [ ] 至少 **1 次焦平面拉** (background blur when character 思考)
- [ ] 4-pillar checklist 出现在 E9 收尾
- [ ] 30% 偏差 honesty 在 E3 + E8 正面出现
- [ ] 工程师角色全程出场，Advisor 在 E4 出现后贯穿
- [ ] 旁白中文，断句 ≤ 12 字 / 句
- [ ] 字幕中文，断句 ≤ 18 字 / 行
- [ ] 总时长 170-185 s
- [ ] 文件 < 50 MB
- [ ] HTML 在 Chrome / Safari 正常

---

## 9. 风险与备选

| 风险 | 等级 | 备选 |
|---|---|---|
| PIL 渲染 emoji 失败 | 高 | **已选 HTML 方案规避** |
| 浏览器录屏分辨率低 | 中 | `--window-size=1920,1080` + `--force-device-scale-factor=1` |
| 真实资产文件丢失 | 中 | 路径已在 inventory 标好，从 git 拉 |
| 3 min 太长 peer 看不完 | 低 | 做 90 s 预告片 (E0 + E4 + E6 + E9) |
| 30% 偏差引发 peer 怀疑 | **机会** | **反而要正面讲 — 是 demo 的核心 credibility 点** |
| 没有配音依赖字幕 | 中 | 找志愿者录 3 min 旁白, ffmpeg `-i voiceover.wav` |
| 浏览器录屏字符打字不准 | 低 | 改用预录视频 + 文字 overlay |
| HTML 动画跨平台兼容 | 低 | Chrome / Safari 99% 一致，Firefox emoji 字体回退 |

---

## 10. 原型已就位

> **E6 「网格决策」HTML 原型已写完**，可在浏览器直接打开：

**URL**：`http://127.0.0.1:8766/prototype.html`
**本地文件**：`/Users/Zhuanz/Desktop/cfd-harness-unified/.planning/demos/2026-06-01_emoji_animation_v2/06_prototype/prototype.html`

打开后看到什么：
- 18s 循环 (按 Replay 可重看)
- 🧑‍💻 工程师走入 → 真实 sHM 网格 PNG 出现 → 数字徽章 ② → 黄圈聚光 6.875
- 💭 思考气泡「max_skew 6.87，能跑吗？」
- 🤖📋 Advisor 走入 → 📚 知识书出现 → V84 文档窗口
- 💬 Advisor 说话气泡「V84 说，跑 50 步 smoke test 看看」
- 终端窗口显示 `potentialFoam -writePhi` + 50 iters
- SVG 残留曲线从红→绿动态绘制，5e-5 → 1.8e-5
- 底部字幕 + 4-pillar 角注 + 时间码

**这一个幕的视觉语言** = 整 9 幕的视觉语言。看完后如果觉得 OK，按相同模板复制 8 份即可。

---

## 11. 下一步 (按用户选择)

| 选项 | 内容 | 时间 |
|---|---|---|
| **A. 进入制作 · 完整 9 幕** | 按 D3-D7 流程做完整 3 min 主片 | 8 天 |
| **B. 制作 90 s 预告片** | E0 + E4 + E6 + E9 4 幕压缩 | 2 天 |
| **C. 调整设计方向** | 改色板 / 改角色 / 改叙事 / 改时长 | 0.5 天 |
| **D. 先做更多原型** | 补 E0 / E4 / E9 三个原型让用户比较 | 1 天 |
| **E. 仅保留规划** | 不做制作，把规划归档 | 0 |

---

## 12. 文档版本

| 版本 | 日期 | 备注 |
|---|---|---|
| v0.1 | 2026-06-01 | 概念 + 设计 + 分镜 + 资产 + 流程 + 对白 + 原型 + 总规划 |

---

**下一步等用户决策**：是按 A 进入完整制作，还是先看 E0 / E4 / E9 三个原型对齐方向？或调整设计？

# 02 · Storyboard · 9 幕分镜

> 每幕给出：时长 / 镜头 / 角色动作 / 真实内容 / 注释 / 对白 / 字幕 / 切镜。
> 所有时长合计 181 s ≈ 3 min 01 s。

---

## E0 · 钩子 — 2AM 工程师 (12 s)

**镜头**：固定中景，1.0x，背景焦平面拉
**场景**：暗室 `#0A1422`，一盏暖橙台灯，只照到桌面
**角色**：🧑‍💻 工程师坐在桌前，伏在键盘上
**桌面道具**：
- 屏幕：黑色底，mono 字体显示 solver log 末三行（真实）：
  ```
  Time = 0.045
  DICPCG: Solving for p_rgh: solution convergence failed
  nut = NaN
  ```
  末行 NaN 用红色 1.4x 字号
- 便利贴：黄色 200x120，钉在屏幕右上角：「Day 6 — solver still diverging」
- 咖啡杯 ☕：旁边，蒸汽消失
- 时钟 🕐 指针：2:00 AM

**注释**：
- 红色 ✗ 浮在 NaN 上方
- 黄色便利贴描边高亮
- 时钟 2:00 数字微微闪烁 0.8 Hz

**对白**：无 (无角色气泡)
**字幕** (屏底)：
> 你做 CFD 的时候，是不是也这样？
**切镜**：fade to black 0.5 s

---

## E1 · 痛点 ① — 几何标签丢失 (8 s)

**镜头**：推近 1.0x → 1.4x over 1 s
**场景**：`bg-deep` 蓝底，左半屏文件柜 + 右半屏代码
**角色**：👷 工程师工业态，立于左，指着文件柜
**道具**：
- 文件柜 (左)：打开抽屉「STEP 文件」
- 输出卡 (中)：白色文档，半透明
  ```
  📂 apu_assembly.stp  (in)
  ⬇
  📂 Part001
  📂 Part002
  📂 Part003
  ...
  📂 Part019
  ```
- 期望卡 (右)：灰色，被红叉覆盖
  ```
  combustor_outlet ✗
  apu_intake ✗
  farfield_cylinder ✗
  Outer_Surf ✗
  ```
- 红箭头：从「Part019」指向「combustor_outlet ✗」

**注释**：
- 🔴 红箭头 1
- 红色 ✗ 4 个
- 黄圈聚光在「Part001」上
- 真实 V1 文本浮窗（小字）:
  > **V1** · `Part::insert` drops CATIA labels → use `Import.insert`

**对白**：
- 👷 工程师气泡 (思考) 💭：「我的 patch 名呢？」

**字幕**：
> V1 · CATIA STEP 标签丢失
> 17 patches 变 19 个 Part00X

**切镜**：fade to black 0.4 s

---

## E2 · 痛点 ② — Solver NaN 8 s

**镜头**：抖动 (camera shake 4 px / 200 ms 一次) over 4 s → 静止
**场景**：`bg-deep` 蓝底，工程师面对一个大显示器
**角色**：🧑‍💻 工程师站在屏幕前
**道具**：
- 屏幕 (大)：终端样式，mono 字体
  ```
  $ buoyantPimpleFoam
  Time = 0.001s
  Time = 0.002s
  Time = 0.003s  ← 红
  omegaWallFunction::evaluate
  → sqrt(k) ≈ 0 → ω = 1e+42
  FATAL: nut = NaN
  
  Backtrace:
  Foam::error::printStack
  omegaWallFunction::evaluate
  ```
- 爆炸特效 💥：屏幕中央一次 0.6 s
- 真实 V3 文本浮窗 (右上小卡片)：
  > **V3** · `kOmegaSST` + zero IC → ω blowup
  > Fix: `potentialFoam -writePhi` warm start
- 绿色 ✓ 浮在 `potentialFoam -writePhi` 文字旁

**注释**：
- 🔴 红色高亮在「NaN」「ω = 1e+42」「FATAL」三处
- 🟢 绿框包住 `potentialFoam -writePhi` 浮窗
- 数字 1.4x 字号
- 红叉 ✗ 在「Time = 0.003s」

**对白**：
- 🧑‍💻 工程师气泡 (说话) 💬：「ω 怎么又炸了？」
- 🤖 Advisor 气泡 (出现，**首次**) 💬：「要不要我查 V3？」

**字幕**：
> V3 · k-ωSST + 零初始场 → ω blowup
> potentialFoam 预热可解

**切镜**：fade to black 0.4 s

---

## E3 · 痛点 ③ — 30% 温度偏差 (8 s)

**镜头**：固定，1.0x，背景轻焦平面拉
**场景**：`bg-deep` 蓝底，工程师面对一个对比图
**角色**：🧑‍💻 工程师立中央，左手指向图，右手指向自己脑袋
**道具**：
- 对比图 (中)：双柱图
  ```
  T_bay (K)
  600 ┤
  500 ┤ ██ 理论 494 K  (绿色 #51CF66)
  400 ┤ ██
  300 ┤ ██ ██ 仿真 350 K  (暖橙 #FFA94D, 偏低)
  200 ┤ ██ ██
  100 ┤ ██ ██
        理论  仿真
  ```
- 数字滚动 (mono) 30% 偏低，从 0% 滚到 30% over 1.2 s
- 真实 ENGINEERING_CAVEAT.md 节选浮窗 (右下小卡片)：
  > 差距 ~150 K（30% 低估）根因：
  > 1. **CFL=35,000 + Euler 1 阶**
  > 2. **limitedLinear 1 → 1 阶 upwind**
  > 3. **cellLimited grad 全开**
  > — `reports/v6N/ENGINEERING_CAVEAT.md`

**注释**：
- 🟢 绿框包「理论 494 K」
- 暖橙描边包「仿真 350 K」
- 黄色高亮在「30%」
- 黄圈聚光在「CFL=35,000」

**对白**：
- 🧑‍💻 工程师气泡 (思考) 💭：「看起来对，但…」

**字幕**：
> 30% 数值耗散 — 工程师的责任是诚实
> (cfd-harness 主动写进 CAVEAT.md)

**切镜**：fade to black 0.4 s

---

## E4 · 发现 — Advisor 出现 (10 s)

**镜头**：拉远 1.4x → 1.0x over 0.8 s
**场景**：`bg-deep` 蓝底 → 渐变到 `bg-canvas` 中蓝 (明亮一点)
**角色**：
- 🧑‍💻 工程师在左
- 🤖 Advisor 右侧出现 (pop-in + 0.5 s, scale 0.8 → 1.0)
**道具**：
- 中间悬浮一个发光文件夹 📁：暖橙描边，标题「cfd-harness-unified」
- 文件夹展开 → 弹出 4 个子文件卡：
  ```
  📂 naming.yaml       ← 单一真相源
  📂 V-series corpus   ← 84 V-rows
  📂 ENGINEERING_CAVEAT.md
  📂 AI Advisor 🤖     ← (高亮闪烁)
  ```
- 知识库 📚 厚书一摞，立于 Advisor 身后
- 4-pillar 名称卡 (右下，30% 透明)：
  ```
  ① LLM offline runnable
  ② Advisor not driver
  ③ V-series sediment
  ④ Project-owned corpus
  ```

**注释**：
- 黄圈聚光在「📂 AI Advisor」上，0.8 Hz 闪烁
- 暖橙发光线沿文件夹轮廓 (light sweep 1.5 s)
- 数字徽章 ①②③④ 在 4-pillar 卡上

**对白**：
- 🧑‍💻 工程师气泡 💬：「你是？」
- 🤖 Advisor 气泡 (出现 + 高亮) 💬：「我是 Advisor。我不替你做决定，我给你依据。」

**字幕**：
> 工程师 + AI 副驾 = cfd-harness-unified

**切镜**：fade to black 0.4 s

---

## E5 · 步骤 1 — 几何 ingest (20 s)

**镜头**：水平摇移 (engineer 跨步) + 推近到 STL 渲染图
**场景**：`bg-canvas` 中蓝，工程师从左移到中
**角色**：
- 🧑‍💻 工程师左→中
- 👷 工程师工业态 0.5 s 闪现 (CAD 阶段)，换成 🧑‍💻
- 🤖 Advisor 右侧跟随
**道具**：
- 桌面：3D 模型器 (大窗户)
- 3D 真实渲染图：`CHT_role_iso_back.png` (APU 圆柱体外壳 + 14 内部 body)
  - 数字徽章 ① 在左上
  - 黄圈聚光在 patch 色条 (右侧命名)
  - 模型慢慢旋转 360° / 5 s
- 浮窗 (右)：真实 FreeCAD 代码 2 行
  ```python
  # ✗ 错的写法
  Part.insert("apu.STEP", doc.Name)
  # ✓ 对的写法
  Import.insert("apu.STEP", doc.Name)  ← 黄底高亮
  ```
- 浮窗 (下)：真实 `naming.yaml` 卡片，30 patches 节选
  ```yaml
  patches:
    - name: combustor_outlet  # 🟢
      type: mass_flow_inlet
    - name: apu_intake        # 🟢
      type: mass_flow_outlet
    - name: body_3            # 🟢
      type: wall_hot
  ```
- ✅ 大勾 出现在「naming.yaml」文字上方 (pop-in 100ms)

**注释**：
- 数字徽章 ①
- 🟢 绿框包 patch 名
- 黄色高亮 `Import.insert`
- 黄圈聚光在 STL 渲染图的「patch 色条」上
- 真实 V1 文本小字底部带

**对白**：
- 🤖 Advisor 💬：「naming.yaml = 单一真相源，从 STL 一路贯穿到 BC 和后处理。」
- 🧑‍💻 工程师 💬：「命名对了，下一步。」

**字幕**：
> ① 几何 ingest · 17 patches 锁进 naming.yaml

**切镜**：fade to black 0.4 s

---

## E6 · 步骤 2 — 网格决策 (25 s)

> **这是 prototype HTML 演示的一幕**，因为它浓缩了 v2 全部视觉特征。

**镜头**：
1. (0-3 s) 水平摇移 engineer 走向右
2. (3-8 s) 推近 1.0x → 1.4x on mesh PNG
3. (8-13 s) 焦平面拉 — 背景虚化，advisor 翻书突出
4. (13-18 s) 推近 1.0x → 1.4x on V84 文本
5. (18-25 s) 拉远 1.4x → 1.0x，决策完成

**场景**：`bg-canvas` 中蓝
**角色**：
- 🧑‍💻 工程师在左
- 🤖📋 Advisor 在中
- 📚 知识库在中后
**道具**：
- 真实网格 PNG：`V8_sceneE_envelope_side_Ym.png` (snappyHexMesh 结果)
  - 数字徽章 ②
  - 黄圈聚光在底部 sHM log 输出
- sHM log 末 8 行 (左下小卡片 mono 22 px)：
  ```
  Max skewness = 6.875
  Skew faces: 20 / 3,100,000
  Max non-orth = 67.3  OK
  Aspect ratio = 41.2  OK
  Cells: 943,289
  ```
- 真实 V84 文本页 (中央, 文档样式, 出现 8-13 s 推近)：
  > ### V84 · max_skewness 4 is sHM's reject-wall, NOT a solver-instability ceiling
  > buoyantSimpleFoam runs stably on **max_skew 6.87** / 20-skew-face industrial mesh with production-tuned schemes
  > (case_002a F4b 2026-05-12/13, 2689 SIMPLE iters / 10.4 h ExecutionTime, zero FATAL/FPE)
  >
  > **Lesson**: the right diagnostic question is NOT "does mesh pass checkMesh defaults" but
  > **"does the solver run cleanly for ~50 iters with the schemes I plan to use"**.
  > Five minutes of solver smoke beats seven hours of mesh debug.
- 终端浮窗 (右, 出现 18-25 s)：
  ```bash
  $ potentialFoam -writePhi    ← 黄底高亮
  $ buoyantPimpleFoam | tee smoke.log
  ... 50 iters ...
  p_rgh final = 1.8e-5   ← 绿勾
  ```
- 残留曲线 (右下)：
  - 真实 residuals.png 局部 (p_rgh 面板) — 50 iter 内的 5e-5 → 2e-5 段
  - 黄圈聚光在曲线底部

**注释**：
- 数字徽章 ②
- ✨ 闪烁高亮在「6.87」「stably」「NOT」
- 黄圈聚光在 sHM log 的「6.875」
- 黄圈聚光在 V84 文本的「6.87」
- 🟢 绿框包「p_rgh final = 1.8e-5」
- 黄色高亮 `potentialFoam -writePhi`
- 数字徽章 1.4x 字号在「50 iters」

**对白**：
- 🧑‍💻 工程师气泡 (思考) 💭：「max_skew 6.87，能跑吗？」
- 🤖📋 Advisor 💬：「V84 说，跑 50 步 smoke test 看看。」
- 🧑‍💻 工程师 💬 (点头 + 跨步)：「5 分钟不要紧。」

**字幕**：
> ② 网格决策 · V84 · 5 分钟 smoke > 7 小时重 mesh

**切镜**：fade to black 0.4 s

---

## E7 · 步骤 3 — 求解 (30 s)

**镜头**：
1. (0-5 s) 拉远看全貌 — 工程师 + 大计算机 (带风扇)
2. (5-20 s) 推近到 solver log + 残留曲线
3. (20-25 s) 焦平面拉 — engineer 点头
4. (25-30 s) 拉远看全貌 — 工程师露出笑

**场景**：`bg-canvas` 中蓝
**角色**：
- 🧑‍💻 工程师左
- 🖥️ Solver (大计算机 + 风扇) 中
- 🤖 Advisor 右
**道具**：
- 大计算机 🖥️：屏幕显示真实 residuals.png (三联图，U/h/p_rgh)
  - p_rgh 面板：6 张带颜色
  - 数字徽章 ③
- 真实 log 节选 (右上 mono 22 px)：
  ```
  Time = 0.213
  U  : 2.4e-5 ← 🟢
  h  : 1.4e-3 ← 🟢
  p_rgh: 1.8e-5 ← 🟢
  omega: 1.4e-4 ← 🟢
  k   : 6.4e-4 ← 🟢
  ```
- 时钟：从 2 AM → 12 PM (10.4 h 压缩) 数字滚动
- 数字徽章：
  - 943,289 cells (滚动 0 → 943289)
  - 10.4 h (滚动 0 → 10.4)
  - 4-core ARM (静态)

**注释**：
- 数字徽章 ③
- 🟢 绿框包每行 log 残差 (5 个)
- 黄色高亮「p_rgh: 1.8e-5」(金色 #FFD43B)
- 黄圈聚光在时钟「12 PM」

**对白**：
- 🧑‍💻 工程师 💬：「0 FATAL。943k cells，10.4 小时，4-core ARM，值。」

**字幕**：
> ③ 求解 · 943k cells · 10.4 h · 4-core ARM · 0 FATAL

**切镜**：fade to black 0.4 s

---

## E8 · 步骤 4 — 后处理 + 审计 (30 s)

**镜头**：
1. (0-8 s) 摇移到「报告桌」(右)
2. (8-16 s) 8 张 HD 缩略横向滚动
3. (16-22 s) 推近 ENGINEERING_CAVEAT.md
4. (22-30 s) 工程师敲入 V85

**场景**：`bg-canvas` 中蓝 → 暖橙台灯聚焦
**角色**：
- 🧑‍💻 工程师右前
- 🤖 Advisor 左
- 📦 Audit (浮窗) 右上
**道具**：
- 报告桌 (大显示器)：8 张 HD ParaView 缩略横向排列 (4×2 grid)
  - 数字徽章 ④
  - 黄圈聚光在第 1 张 (T 切片) → 第 3 张 (|U|)
- ENGINEERING_CAVEAT.md 卡片 (推近 16-22 s)：
  > ### APU Bay Ventilation CHT v6N — Engineering Caveat
  > **算例**：`case_refined_v2`（943k cells, refinementBox jet level 3, 3 layer prism）
  > **求解器**：`buoyantPimpleFoam`（4-core MPI）
  > **工况**：55°C MES day plateau (t=150-200)
  > **combustor_outlet**：mdot=2.8 kg/s @ 615.6 K
  > **apu_intake**：mdot=4.85 kg/s
  >
  > **理论** T_avg ≈ **494 K**
  > **仿真** T_avg ≈ **328–350 K**
  > **差距** ~150 K（30% 低估）
  >
  > **根因**：
  > 1. **CFL=35,000 + Euler 1 阶**...
  > 2. **limitedLinear 1 → 1 阶 upwind**...
  > 3. **cellLimited grad 全开**...
  >
  > **结论**：定性结论对，定量结论受数值耗散限制。
- 工程师敲入 V85 终端 (推近 22-30 s)：
  ```bash
  $ editor reports/v6N/V85.md
  # V85 · 2026-06-01 · APU bay 30% 数值耗散
  # 原因：CFL=35k + Euler 1 阶
  #       + limitedLinear 退 upwind
  #       + cellLimited 全开
  # Status: partial
  # Lesson: 工业工程级 (qualitative)
  #         ≠ 精确热载荷 (quantitative)
  ```
  字符逐字打字效果 (40 ms/字)
- 终端上方出现一个绿色 ✅ 飞入 corpus 库
- corpus 库 (中后)：从 84 行变成 85 行，「V85」行高亮闪烁 1.5 s

**注释**：
- 数字徽章 ④
- 🟢 绿框包「理论 494 K」「仿真 350 K」「差距 ~150 K」
- ✨ 闪烁高亮「30%」
- 黄圈聚光在「V85」
- 黄色高亮「30% 数值耗散」
- 🔒 锁图标出现在 Audit 浮窗

**对白**：
- 🧑‍💻 工程师 💬：「 |U| 对，结构对，但温度偏低 30%。」
- 🧑‍💻 工程师 💬：「记下来，V85。」 (敲键)
- 🤖 Advisor 💬 (点头)：「85 行 corpus 又多了一行。」

**字幕**：
> ④ 后处理 + 审计 · 8 HD · CAVEAT 诚实写 · V85 沉淀

**切镜**：fade to black 0.4 s

---

## E9 · 收尾 — 4-pillar checklist (15 s)

**镜头**：拉远 1.4x → 1.0x
**场景**：`bg-canvas` 中蓝 → 渐变到 `bg-deep` 深蓝 (庄重收口)
**角色**：
- 🧑‍💻 工程师左
- 🤖 Advisor 右
**道具**：
- 中央悬浮 4-pillar 4 卡片 (2×2 网格)，每张：
  ```
  ①  LLM offline runnable
      工作台无 LLM 也能跑
      ✅
  ②  Advisor not driver
      AI 给建议，工程师决定
      ✅
  ③  V-series sediment
      每个 case 沉淀一行
      ✅
  ④  Project-owned corpus
      84 V-rows 工业自有
      ✅
  ```
- 每张卡片按 1.2 s 间隔依次 pop-in (scale 0.8 → 1.0)
- 每个 ✅ 同步 pop-in
- 卡片下方出现项目名：
  ```
  cfd-harness-unified
  工程师的 AI 副驾
  ```

**注释**：
- 4 个 ✅ 大勾
- 暖橙描边卡片 1.5 px
- 数字徽章 ①②③④ 暖橙底白字

**对白**：
- 🧑‍💻 工程师 💬：「工作台永远能跑，决策永远是我的。」

**字幕**：
> 4-pillar 治理 · LLM-offline · advisor-not-driver · V-series sediment · project corpus

**切镜**：fade to E10 end card 0.4 s

---

## E10 · End Card (5 s)

**镜头**：固定 1.0x
**场景**：`bg-deep` 深蓝
**道具** (全屏白字居中)：
```
cfd-harness-unified
工程师的 AI 副驾

1 个真实 APU 舱算例  ·  943k cells  ·  10.4 h
84 V-rows corpus       ·  4-core ARM  ·  0 FATAL
30% 偏差诚实写进 CAVEAT.md
```

底部 footer mono 18：
> 基于 `~/Desktop/cfd-harness-unified` + `~/Desktop/apu-bay-ventilation-cht` · 2026-06-01

---

## 总时长

| 幕 | 时长 (s) |
|---|---|
| E0 | 12 |
| E1 | 8 |
| E2 | 8 |
| E3 | 8 |
| E4 | 10 |
| E5 | 20 |
| E6 | 25 |
| E7 | 30 |
| E8 | 30 |
| E9 | 15 |
| E10 | 5 |
| **合** | **171** |

加上 11 个幕间 fade 0.4 s = 4.4 s → 约 **3 min 00 s**

---

## 制作优先级 (P0 必做 / P1 加分 / P2 选做)

- P0：E0 / E4 / E5 / E6 / E7 / E8 / E9 (核心叙事链)
- P1：E1 / E2 / E3 (痛点快速闪过)
- P2：E10 (品牌卡)

如时间紧，可压缩痛点三幕为「三连快闪」1 幕 (4-6 s)。

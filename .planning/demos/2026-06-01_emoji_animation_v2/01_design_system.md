# 01 · Design System · 视觉语言 + 角色 + 注释

> 整片 9 幕的视觉原子：色板 / 角色 / 气泡 / 注释 / 镜头。
> 任何一个元素变了，先在这里改，再传导到分镜。

---

## 1. 色板 (深空 + 暖橙工程感)

| 角色 | HEX | 用法 |
|---|---|---|
| `bg-deep` | `#0E1A2B` | 主背景，工程深邃感 |
| `bg-canvas` | `#152234` | 角色 + 道具站立的「地面」 |
| `bg-room` | `#0A1422` | E0 暗室 |
| `accent-warm` | `#FFA94D` | 暖橙 — 角色光、聚光圈、CTA |
| `accent-yellow` | `#FFD43B` | 高亮黄 — 关键信息、聚光、勾 |
| `accent-cyan` | `#74C0FC` | 信息蓝 — 链接、副标题、corpus V-id |
| `ok-green` | `#51CF66` | 通过 / 收敛 / ✅ |
| `ng-red` | `#FF6B6B` | 失败 / NaN / 偏差 / ✗ |
| `text-primary` | `#F8F9FA` | 主文字 |
| `text-dim` | `#ADB5BD` | 副文字 / 单位 / 时间码 |
| `code-mono` | `#C0C5CC` | mono 字体 (技术 ID、citation) |
| `bubble-think` | `#FFF9DB` | 思考气泡背景 |
| `bubble-talk` | `#F8F9FA` | 说话气泡背景 |
| `bubble-aside` | `#495057` | 旁白气泡背景 |

> v1 用了纯黑底 + 白字 — 工程感强但视觉单薄。
> v2 加暖橙 + 高亮黄，让「工程师的辛苦」和「Advisor 的建议」有温度差。

## 2. 字体

| 角色 | 字体 | 来源 (macOS) |
|---|---|---|
| 主标题 | PingFang SC Heavy 64-72 | `/System/Library/Fonts/Hiragino Sans GB.ttc` index 2 |
| 字幕 | PingFang SC Regular 36 | 同上 index 1 |
| 副字幕 | PingFang SC Light 26 | 同上 index 0 |
| 工程师 / 角色对话 | PingFang SC Medium 30 | 同上 index 1 |
| 旁白 | PingFang SC Light 28 italic | 同上 index 0 |
| 代码 / V-id / log | JetBrains Mono / Menlo 22-32 | `/System/Library/Fonts/Menlo.ttc` |
| 数字徽章 | JetBrains Mono Bold 36 | 同上 |
| Footer tag | JetBrains Mono Regular 18 | 同上 |

## 3. 角色 (emoji + 简单身体语言)

> 原则：emoji 大尺寸 + 简单的 2-frame 动画 (眨眼 / 手臂 / 头部偏转)。
> **不画复杂 2D 角色** — 时间预算 + 风格统一 + emoji 已是科普动画通用语。

| 角色 | emoji | 站姿 (px) | 动作语言 | 出现幕 |
|---|---|---|---|---|
| 工程师 · C | 🧑‍💻 | 220x220, base 坐姿, 头微倾 8° | 眨眼、点头、敲键盘、扶额、指向、跨步 | E0-E10 贯穿 |
| 工程师 · 工业 | 👷 | 220x220, 戴安全帽 | 仅在 E0 痛点 + E5 几何 | E0 / E5 |
| Advisor | 🤖 | 240x240, base 站姿, 头略大 | 翻页、指向、点头、拿出放大镜 | E4 出现后贯穿 |
| Advisor · 文档态 | 🤖📋 | 240x240, 持剪贴板 | 在 E6 网格决策时 | E6 |
| 知识库 | 📚 | 200x150, 立体书本 | 翻页（页角卷起动画） | E4 / E6 / E8 |
| CAD 模型 | 🎨 → 真实 STL 缩略 | 320x320 | 旋转 360° / 5s | E5 |
| 网格 | 🕸️ → 真实网格缩略 | 320x320 | 高亮 max_skew 数字闪烁 | E6 |
| Solver | 🖥️ + 💨 风扇 | 240x240 | 风扇旋转 4-frame 循环 | E7 |
| Plot | 📈 → 真实 residuals.png | 480x360 | 曲线从右往左画 | E7 |
| Audit | 📦 + 🔒 | 200x200 | 盖上 + 印 seal | E8 / E9 |
| 勾 | ✅ | 64x64 | pop-in 100ms | 每个决策点 |
| 叉 | ❌ | 64x64 | pop-in 100ms | 每个失败点 |

## 4. 气泡系统

```
💭  思考气泡      💬  对话气泡      旁白气泡 (无角色边框)
┌──────────┐     ┌──────────┐     ┌──────────┐
│ 工程师的 │     │ Advisor │     │  旁白：  │
│  疑问？  │     │  引用   │     │ 30% 偏低│
└────╲─────┘     └────│─────┘     └──────────┘
     圆点×2          尖角            底部条幅
```

| 类型 | 背景 | 边框 | 字号 | 位置 |
|---|---|---|---|---|
| 思考 💭 | `#FFF9DB` (浅黄) | 无 | 28 | 角色头顶上 60-120 px |
| 对话 💬 | `#F8F9FA` | 1 px `#495057` | 30 | 角色侧上方 |
| 旁白 (无角色) | `#495057` 80% alpha | 无 | 26 | 屏底字幕条上方 20 px |
| 引用 💬🔗 | `#1A2A3D` + 1 px `#74C0FC` | 1 px | 24 mono | 真实内容上方 |
| 警告 ⚠️ | `#FFF3BF` | 2 px `#FAB005` | 28 | 错误信息位置 |

## 5. 注释系统 (注意力设计核心)

> 这是 v2 区别于 v1 的最大视觉特征。v1 把整张图放上去；v2 把图的局部**裁切 + 注释**。

| 注释元素 | 形态 | 用法 | 出现示例 |
|---|---|---|---|
| 🟡 **黄圈聚光** | 直径 80-160 px 描边圆, 2.5 px 黄色 #FFD43B, 半透明 30% | 「看这里」 | E6 max_skew 6.87 周围 |
| 🔴 **红箭头** | 2 px 红色 #FF6B6B 直线 + 12 px 三角头 | 「问题在这」 | E1 Part001 上 |
| 🟢 **绿框** | 2 px 绿色 #51CF66 矩形 + 角标 | 「这是结果」 | E5 naming.yaml patch 名 |
| ① ② ③ **数字徽章** | 直径 50 px 圆, 暖橙 #FFA94D 底, 白字粗体 36 px mono | 「顺序」 | E5-E8 每步骤左上 |
| ✨ **闪烁高亮** | 2 px 黄色 + 阴影发光 8 px, 1.2 Hz 闪烁 | 「这是关键」 | E6「6.87」「stably」 |
| 📏 **连接线** | 1 px 虚线 #ADB5BD 80% | 把标签连到图中对象 | 命名对应 |
| 🅱️ **底栏标签** | 60% alpha 黑色条, 白字 mono 22 | 时间码 / 工况标签 | 全程底栏右下 |
| 🔍 **放大镜** | emoji 🔍 + 60% 圆, 4 px 黄边 | 推近时套在被放大的对象外 | E6 推近 max_skew |
| ▢ **窗口框** | 6 px 圆角 8, 1 px #74C0FC 边, 顶部 tab 8% alpha 黑色 | 「这是一张文档」 | 所有真实内容容器 |
| 🟨 **重点句黄色底** | 文字下方 6 px 黄色 #FFD43B 50% | 「这段要读」 | V84 引用行 |

## 6. 镜头语言

| 运镜 | 实现 | 用法 |
|---|---|---|
| **推近 (push-in)** | PIL crop + resize, 1.0x → 1.4x over 1.2 s ease-out | 注意力「聚焦」到一个细节 |
| **拉远 (pull-out)** | 1.4x → 1.0x over 0.8 s ease-in-out | 「讲完了，看全貌」 |
| **摇移 (pan)** | 水平 x 偏移 ±200 px over 1.5 s linear | 角色移动的视觉同步 |
| **焦平面拉 (focus pull)** | 背景 layer 4 px Gaussian blur, 前景不变 | 角色「思考」时背景虚化 |
| **高光扫 (light sweep)** | 半透明 30% 白条从左到右 1.5 s 一次 | 强调「这行被扫到」 |
| **数字滚动 (counter)** | 数字从 0 → 终值 ease-out 1 s | 943k / 6.87 / 30% |
| **字符打字 (type-on)** | mono 字体从左到右逐字显现, 40 ms/字 | 终端 / log 滚动 |
| **窗口淡入** | opacity 0 → 1, scale 0.95 → 1, 0.3 s ease-out | 新文档 / 角色出现 |
| **窗口淡出** | opacity 1 → 0, scale 1 → 0.95, 0.3 s ease-in | 文档 / 角色退场 |
| **循环强调 (pulse)** | 0.8 Hz 缩放 1.0 ↔ 1.05 | 黄圈 / 红框等注释 |

## 7. 字幕与旁白

- 字幕条：底部 80 px 高，#000000 80% alpha，圆角 12 px
- 主字幕：PingFang SC 36 px，白色
- 副字幕（半透明叠在主字幕下方）：26 px，`#ADB5BD`
- 时间码：右下角 mono 22 px，`#495057`：「00:42 · E6」
- 工程师姓名 (脚注)：右下角 mono 18 px，`#ADB5BD`：「cfd-harness · v6N B+ · 2026-06-01」
- 幕间黑场：幕尾 fade-to-black 0.4 s

## 8. 拒绝清单 (anti-patterns)

> v2 制作时**不允许**出现以下元素：

- ❌ 3D 角色 (与 emoji 风格不统一)
- ❌ 真实人脸照片 (peer 场景会失专业感)
- ❌ 大段英文 (peer 受众以中文为主)
- ❌ 「AI 自动完成」「无需人工」等 marketing 词 (与项目 4-pillar 矛盾)
- ❌ 整张 HD 图直接放上去，不裁切 (浪费注意力)
- ❌ 把 30% 偏差藏起来 (peer 看得见，藏就失信)
- ❌ 暖橙 + 亮黄同时用在一个元素 (打架)
- ❌ 气泡超过 3 行 (观众读不完)
- ❌ 旁白超过 6 秒 (节奏会断)

## 9. 复用关系 — v1 → v2 元素映射

| v1 元素 | v2 复用方式 |
|---|---|
| `BG = (12,12,16)` 黑底 | 升级为 `bg-deep #0E1A2B` |
| `caption_main` 字幕条 | 升级：主 + 副 + 时间码 + footer 四段 |
| `CAPTION_HIGHLIGHT` 颜色 | 沿用为 `accent-yellow` |
| `FONT_CN_PATH` Hiragino | 沿用 + 加 Heavt 变体 |
| `SHOT` dataclass | 升级为 `Scene` dataclass (含角色列表、注释列表、镜头运镜) |
| `ffmpeg concat` 流水线 | 沿用，扩为分幕 → 整片两级 concat |
| `fade in/out` 0.5 s | 沿用，扩为 8 种镜头 (见 §6) |
| 25 张真实 PNG | 全部沿用，**但走「裁切 + 注释」pipeline** |
| 0 角色 | 新增 emoji 角色层 (PIL 帧序列) |
| 0 知识库文本 | 新增 V-row 真实文本高亮层 |
| 0 V-series sediment 演示 | 新增「工程师敲入 V85」动画 |
| 0 4-pillar 视觉 | 新增 E9 4-pillar checklist 收尾 |

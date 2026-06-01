# 06 · Prototype · E6 网格决策 (单幕 HTML)

> 验证 v2 视觉语言是否成立：emoji 角色 + 真实内容 + 注释 + 镜头 + 字幕。

## 怎么打开

```bash
# macOS
open .planning/demos/2026-06-01_emoji_animation_v2/06_prototype/prototype.html

# 或在浏览器
file:///Users/Zhuanz/Desktop/cfd-harness-unified/.planning/demos/2026-06-01_emoji_animation_v2/06_prototype/prototype.html
```

## 推荐分辨率

- 1920x1080 (原生)
- 缩放 0.5-0.8x 在笔记本上也清晰

## 时间轴 (18 s 循环)

| t (s) | 元素 | 视觉效果 |
|---|---|---|
| 0.5 | 🧑‍💻 工程师走入 | pop-in + 呼吸动画 |
| 2.5 | 真实网格 PNG 出现 | doc-window 淡入 (V8_sceneE_envelope_side_Ym.png) |
| 2.5 | 数字徽章 ② | pop-in |
| 4.0 | sHM log 卡片 | 真实 log 文本 (6.875 红色高亮) |
| 5.5 | 黄圈聚光 | 在 log 6.875 上 + 1.5 Hz 脉冲 |
| 6.0 | 工程师思考气泡 | "max_skew 6.87，能跑吗？" |
| 7.0 | 🤖📋 Advisor 走入 | pop-in |
| 8.0 | 📚 知识书出现 | 头顶居中 |
| 9.5 | V84 文档窗口出现 | 真实 V84 文本 + 6.87 / NOT 黄高亮 + 闪烁 |
| 11.5 | Advisor 说话气泡 | "V84 说，跑 50 步 smoke test 看看" |
| 13.0 | 终端窗口出现 | `potentialFoam -writePhi` 黄底 + 50 iters 残差收敛 |
| 14.5 | 残留曲线窗口 | SVG 曲线从红→绿动态绘制，5e-5 → 1.8e-5 |
| 17.5 | 循环结束 | 回到 0s 重新开始 |

## 验证的视觉特征

- ✅ emoji 角色 + 简单身体语言 (呼吸动画)
- ✅ 真实工程截图 (V8_sceneE PNG)
- ✅ 真实 V-row 文本 (V84 完整 lesson)
- ✅ 真实 sHM log 输出 (6.875 / 943,289 cells)
- ✅ 真实 residual 曲线 (从 log 推算 50-iter 段)
- ✅ 黄圈聚光 + 数字徽章 + 文字高亮
- ✅ 气泡 (思考黄 / 说话白)
- ✅ 字幕条 + 4-pillar 角注
- ✅ 镜头 : 1.0x (本幕不推近，留给 E7 / E8)
- ✅ 时间码 + footer info

## 浏览器兼容性

- ✅ Safari 15+ (macOS / iOS)
- ✅ Chrome 90+
- ✅ Edge 90+
- ⚠️ Firefox : emoji 字体可能回退到系统字体 (Apple Color Emoji → Twemoji)

## 录屏方法 (用于视频化)

```bash
# macOS QuickTime
# 1. 打开 prototype.html
# 2. QuickTime Player → File → New Screen Recording
# 3. 选窗口 → 录制 20s → 保存
# 4. ffmpeg 转码
ffmpeg -i screen-recording.mov \
  -c:v libx264 -pix_fmt yuv420p -crf 20 \
  -vf "scale=1920:1080" \
  E6_prototype.mp4
```

## 下一幕可复用此模板

把 prototype.html 当作模板，按 `02_storyboard.md` 复制 9 份，每份替换：
1. 元素 ID + 内容 (mesh / log / v84 / terminal / plot)
2. TIMELINE 数组 (t 时间 + fn 触发)
3. 字幕 / 副字幕文本
4. 角色 (E0 = 🧑‍💻 独角 / E4+ = 双角色)

每幕 HTML 单文件 → 9 个 HTML → 9 段录屏 → ffmpeg concat → 整片。

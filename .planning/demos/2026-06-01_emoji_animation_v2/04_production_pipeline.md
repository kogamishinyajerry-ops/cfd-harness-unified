# 04 · Production Pipeline · 从脚本到 3 分钟成片

> 技术选型：**PIL/Pillow 单帧合成 + ffmpeg 编码 + 镜头后处理**。
> 复用 v1 demo 的 `build_video.py` 架构，但升级为「分幕渲染 + 多层合成 + 镜头运镜」。

---

## 1. 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│                     storyboard.yaml                           │
│  (9 幕时序 + 镜头 + 角色 + 资产 + 注释 + 对白 + 字幕)         │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│              render_scene.py  (per scene)                     │
│                                                               │
│  输入: storyboard.yaml + assets/                              │
│  输出: frames/E[0-9]/f00000.png  (30 fps)                     │
│        + caption.srt (per scene)                              │
│        + notes.json (注释 + 镜头 metadata)                    │
│                                                               │
│  Step 1: 加载背景层 (bg)                                       │
│  Step 2: 加载真实内容 (real content) + 裁切/缩放                │
│  Step 3: 放置角色 (emoji PIL draw 或预渲染)                    │
│  Step 4: 添加注释 (黄圈/红箭头/绿框/数字徽章)                  │
│  Step 5: 应用镜头 (crop+resize 按 zoom/pan 系数)                │
│  Step 6: 合成字幕 (PIL 文字到半透明条)                         │
│  Step 7: 输出 PNG 帧                                          │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│              concat.py  (per scene → per part → full)         │
│                                                               │
│  Step 1: ffmpeg per-frame → per-clip (h264 + fade)            │
│  Step 2: ffmpeg concat per scene                              │
│  Step 3: ffmpeg concat per part (E0-E3, E4-E8, E9-E10)        │
│  Step 4: ffmpeg concat full → advisor_moments_v2.mp4          │
└──────────────────────────────────────────────────────────────┘
```

## 2. 目录结构 (production)

```
.planning/demos/2026-06-01_emoji_animation_v2/
├── 00_concept.md
├── 01_design_system.md
├── 02_storyboard.md
├── 03_asset_inventory.md
├── 04_production_pipeline.md       ← 本文件
├── 05_dialogue_script.md
├── 06_prototype/                   ← 概念验证 (单幕 HTML)
├── storyboard.yaml                 ← 9 幕机器可读剧本
├── assets/                         ← 预处理的真实资产
│   ├── images/                     ← PIL 预缩放 + 预裁切
│   ├── crops/                      ← 各幕用的局部放大图
│   ├── text/                       ← V-row 文本片段
│   ├── overlays/                   ← 注释元素 (黄圈, 红箭头, 绿框, 数字徽章)
│   └── characters/                 ← emoji 预渲染 (8-frame 循环)
├── frames/                         ← 渲染产物 (E[0-9]/f*.png)
├── clips/                          ← 渲染产物 (E[0-9]/c*.mp4)
├── recordings/
│   ├── part1_pain.mp4              ← E0-E3
│   ├── part2_process.mp4           ← E4-E8
│   ├── part3_close.mp4             ← E9-E10
│   └── advisor_moments_v2.mp4      ← 3 min 完整版
├── build_video.py                  ← 主入口 (替代 v1 版本)
├── build_shots.py                  ← 镜头/分幕数据
├── render_scene.py                 ← 单幕渲染
├── concat.py                       ← 合成
├── requirements.txt                ← pillow, pyyaml
└── README.md
```

## 3. storyboard.yaml (机器可读)

```yaml
# 9 幕 3 min · 30 fps · 1920x1080
video:
  width: 1920
  height: 1080
  fps: 30
  duration_s: 180

scenes:
  - id: E0
    duration_s: 12
    camera: {start_zoom: 1.0, end_zoom: 1.0, focus_pull: true}
    background: bg-room
    characters:
      - {name: engineer, emoji: "🧑‍💻", pose: sit, x: 600, y: 700, scale: 1.0}
    props:
      - {type: screen, x: 400, y: 200, w: 800, h: 450,
         content: log.NaN_lines, font: mono}
      - {type: sticky_note, x: 1100, y: 150, w: 200, h: 120,
         text: "Day 6 — solver still diverging", bg: yellow}
      - {type: emoji, value: "☕", x: 950, y: 720, scale: 1.2}
      - {type: emoji, value: "🕐", x: 120, y: 200, scale: 1.5}
    annotations:
      - {type: red_x, target: "screen.NaN", pulse: 0.8}
      - {type: yellow_circle, target: "sticky_note", pulse: 0.8}
    dialogue: []  # no character speech
    subtitle:
      main: "你做 CFD 的时候，是不是也这样？"
      main_color: white
    transition_out: fade_black 0.5

  - id: E1
    duration_s: 8
    camera: {start_zoom: 1.0, end_zoom: 1.4, focus_pull: false}
    background: bg-deep
    characters:
      - {name: engineer_industrial, emoji: "👷", pose: stand, x: 200, y: 700}
    props:
      - {type: drawer_open, x: 100, y: 200, w: 250, h: 600,
         contents: ["📂 apu_assembly.stp"]}
      - {type: doc_card, x: 500, y: 300, w: 380, h: 450,
         title: "STEP 输出 (FreeCAD 默认)", body: "Part001\nPart002\n..."}
      - {type: doc_card, x: 950, y: 300, w: 380, h: 450,
         title: "我期望的命名", body: "combustor_outlet\napu_intake\n..."}
      - {type: text_callout, x: 880, y: 100, w: 380, h: 100,
         text: "**V1** · `Part::insert` drops CATIA labels\nFix: `Import.insert`", font: mono}
    annotations:
      - {type: red_arrow, from: [550, 500], to: [1000, 350]}
      - {type: red_x, count: 4, target: "doc_card.right"}
      - {type: yellow_circle, target: "Part001"}
    dialogue:
      - {character: engineer_industrial, type: think, text: "我的 patch 名呢？"}
    subtitle:
      main: "V1 · CATIA STEP 标签丢失"
      sub: "17 patches 变 19 个 Part00X"
    transition_out: fade_black 0.4

  # ... E2-E10 同样 schema ...
```

## 4. PIL 帧合成 (核心 render_scene.py)

```python
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import yaml, math, time

# ── Load storyboard
SB = yaml.safe_load(open("storyboard.yaml"))

# ── Load assets (预加载)
BG = {
    "bg-room": Image.open("assets/backgrounds/bg-room.png"),
    "bg-deep": Image.open("assets/backgrounds/bg-deep.png"),
    "bg-canvas": Image.open("assets/backgrounds/bg-canvas.png"),
}
EMOJI_FONT = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 220)
CN_FONT_HEAVY = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 64, index=2)
CN_FONT = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 36, index=1)
CN_FONT_LIGHT = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 26, index=0)
MONO_FONT = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 22)

# ── 预渲染 overlay 元素
def render_yellow_circle(size, line_w=2.5, alpha=80):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([(line_w, line_w), (size[0]-line_w, size[1]-line_w)],
              outline=(255, 212, 59, 255), width=line_w)
    return img

def render_number_badge(n, size=50):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([(0, 0), (size, size)], fill=(255, 169, 77, 255))
    bbox = d.textbbox((0, 0), str(n), font=MONO_FONT_BOLD)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - w) / 2, (size - h) / 2 - 4), str(n),
           fill=(255, 255, 255, 255), font=MONO_FONT_BOLD)
    return img

# ── 镜头推近
def apply_camera(canvas, zoom, focus_pull=False):
    W, H = canvas.size
    crop_w, crop_h = int(W / zoom), int(H / zoom)
    crop_x = (W - crop_w) // 2
    crop_y = (H - crop_h) // 2
    cropped = canvas.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
    if focus_pull:
        cropped = cropped.filter(ImageFilter.GaussianBlur(radius=4))
    return cropped.resize((W, H), Image.LANCZOS)

# ── 单幕渲染
def render_scene(scene, out_dir):
    dur_s = scene["duration_s"]
    n_frames = int(dur_s * 30)
    bg = BG[scene["background"]].copy().convert("RGBA")

    for frame_idx in range(n_frames):
        t = frame_idx / 30.0
        t_norm = frame_idx / max(n_frames - 1, 1)

        # ── 镜头插值
        cam = scene["camera"]
        zoom = cam["start_zoom"] + (cam["end_zoom"] - cam["start_zoom"]) * t_norm

        # ── 角色动作 (简单相位动画)
        canvas = bg.copy()
        for ch in scene["characters"]:
            pose_offset = math.sin(t * 2 * math.pi / 1.0) * 5  # 1s 周期呼吸
            draw_emoji(canvas, ch, y_offset=pose_offset)

        # ── 道具 (按 scene.props)
        for prop in scene["props"]:
            draw_prop(canvas, prop, t)

        # ── 注释 (按 scene.annotations)
        for ann in scene["annotations"]:
            draw_annotation(canvas, ann, t)

        # ── 字幕 (屏底)
        draw_subtitle(canvas, scene["subtitle"])

        # ── 镜头
        canvas = apply_camera(canvas, zoom, cam.get("focus_pull", False))

        # ── 落帧
        canvas.convert("RGB").save(out_dir / f"f{frame_idx:05d}.png")

# ── ffmpeg 合成单幕
def ffmpeg_scene(scene_dir, out_clip, dur_s):
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", "30", "-i", f"{scene_dir}/f%05d.png",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "20",
        "-t", f"{dur_s:.3f}",
        out_clip,
    ], check=True)
```

## 5. 镜头运镜实现 (camera.py)

| 运镜 | 实现 |
|---|---|
| 推近 (push-in) | `zoom` 从 1.0 线性插值到 1.4 |
| 拉远 (pull-out) | `zoom` 从 1.4 线性插值到 1.0 |
| 摇移 (pan) | crop 起点 x 偏移 ±200 px |
| 焦平面拉 (focus pull) | `ImageFilter.GaussianBlur(radius=4)` on bg layer |
| 高光扫 (light sweep) | 半透明白条从左到右，0.4 alpha |
| 数字滚动 (counter) | `t * target_value` ease-out |
| 字符打字 (type-on) | `text[: int(t * chars_per_sec * len(text))]` |
| 窗口淡入 (pop-in) | scale 0.95 → 1.0, alpha 0 → 1, 0.3 s ease-out |

## 6. 注释元素渲染 (annotations.py)

```python
def draw_yellow_circle(canvas, x, y, r, pulse_hz=0.8):
    t = time.time()
    scale = 1.0 + 0.05 * math.sin(t * 2 * math.pi * pulse_hz)
    d = ImageDraw.Draw(canvas, "RGBA")
    d.ellipse([(x - r * scale, y - r * scale), (x + r * scale, y + r * scale)],
              outline=(255, 212, 59, 240), width=3)

def draw_red_arrow(canvas, from_xy, to_xy):
    d = ImageDraw.Draw(canvas, "RGBA")
    d.line([from_xy, to_xy], fill=(255, 107, 107, 255), width=3)
    # arrowhead
    import math
    dx, dy = to_xy[0] - from_xy[0], to_xy[1] - from_xy[1]
    angle = math.atan2(dy, dx)
    head_size = 16
    p1 = (to_xy[0] - head_size * math.cos(angle - 0.5),
          to_xy[1] - head_size * math.sin(angle - 0.5))
    p2 = (to_xy[0] - head_size * math.cos(angle + 0.5),
          to_xy[1] - head_size * math.sin(angle + 0.5))
    d.polygon([to_xy, p1, p2], fill=(255, 107, 107, 255))

def draw_green_box(canvas, x, y, w, h):
    d = ImageDraw.Draw(canvas, "RGBA")
    d.rectangle([(x, y), (x + w, y + h)], outline=(81, 207, 102, 255), width=2)
    # 角标
    for cx, cy in [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]:
        d.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)],
                  fill=(81, 207, 102, 255))

def draw_number_badge(canvas, x, y, n, size=50):
    d = ImageDraw.Draw(canvas, "RGBA")
    d.ellipse([(x, y), (x + size, y + size)], fill=(255, 169, 77, 255))
    txt = str(n)
    bbox = d.textbbox((0, 0), txt, font=MONO_BOLD)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((x + (size - tw) / 2, y + (size - th) / 2 - 4), txt,
           fill=(255, 255, 255, 255), font=MONO_BOLD)
```

## 7. emoji 角色渲染 (PIL 限制 + 备选)

> PIL 渲染 emoji 有兼容性问题 (颜色 emoji 字体在 PIL 不能直接 draw)。**两个解决方案**：

### 方案 A：预渲染 emoji PNG (推荐)

```python
import subprocess
def prerender_emoji(emoji, size=220, out_path="assets/characters/eng_sit.png"):
    # 用 macOS 系统「文本编辑」或 ImageMagick 渲染 emoji 到 PNG
    cmd = [
        "convert", "-size", f"{size}x{size}",
        "-background", "none",
        f"label:{emoji}",
        out_path
    ]
    subprocess.run(cmd, check=True)
```

或者用 Python 的 `playwright` 打开一个透明 HTML + 截图：
```python
from playwright.sync_api import sync_playwright
def prerender_emoji(emoji, size, out_path):
    html = f'<html><body style="margin:0;background:transparent"><div style="font-size:{size}px">{emoji}</div></body></html>'
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": size, "height": size})
        page.set_content(html)
        page.screenshot(path=out_path, omit_background=True)
        b.close()
```

### 方案 B：HTML 渲染整片 (更省事)

> 整片不用 PIL 拼帧，直接用 **HTML + CSS + JS 动画**，再用 **headless browser 录视频**。

```bash
# 用 chrome 录 html → mp4
google-chrome --headless --disable-gpu --no-sandbox \
  --window-size=1920,1080 \
  --screenshot=frame.png \
  file://$PWD/index.html

# 或用 ffmpeg 抓浏览器画面
ffmpeg -f x11grab -video_size 1920x1080 -framerate 30 -i :99 \
  -t 180 -c:v libx264 -pix_fmt yuv420p out.mp4
```

> **方案 B 优势**：emoji 渲染零摩擦，CSS 动画丰富 (transform / filter / animation 一应俱全)。
> **方案 B 劣势**：依赖浏览器 (单幕 15-30s 录屏流畅，整片 3 min 需分段录再 concat)。

**最终选型**：**方案 B** (HTML 动画 + 浏览器录屏)。
v1 用 PIL 拼图是为了「离线 + 可重复」，v2 用 HTML 是为了「emoji 渲染无障碍 + CSS 动画丰富」。
把 HTML 当 source of truth，截屏帧是 deliverable。

## 8. 时间预算 (按 9 幕主片)

| 阶段 | 内容 | 天数 |
|---|---|---|
| D1 | 概念 + 设计系统 + 分镜 (本规划) | 1 |
| D2 | 真实资产预处理 (裁切/缩放/背景合成) | 1 |
| D3 | HTML 模板 + E0 / E4 / E9 三幕 HTML | 1.5 |
| D4 | E1 / E2 / E3 痛点三连 | 0.5 |
| D5 | E5 / E6 几何 + 网格 | 1.5 |
| D6 | E7 / E8 求解 + 审计 | 1.5 |
| D7 | E10 end card + 字幕校对 + QA | 1 |
| **总** | | **8 天** |

> 紧凑版 (3 痛点合并 1 幕)：6 天。
> 豪华版 (加配音 + 字幕双语)：10 天。

## 9. QA 检查清单

- [ ] 每幕真实资产路径与 03_asset_inventory.md 表对得上
- [ ] 每幕 ≥ 1 个 V-row 真实文本片段
- [ ] 每幕 ≥ 1 张真实图像
- [ ] 每幕 ≥ 1 个注释元素 (黄圈/红箭头/绿框/数字徽章)
- [ ] 30% 偏差 honesty 在 E3 + E8 正面出现
- [ ] 工程师角色在 E0 出现后贯穿
- [ ] Advisor 在 E4 出现后贯穿
- [ ] 4-pillar 4 卡片在 E9 出现
- [ ] 字幕断句 ≤ 18 字
- [ ] 总时长在 170-185 s 之间
- [ ] 文件 < 50 MB
- [ ] HTML 在 Chrome / Safari 浏览器打开正常
- [ ] emoji 在 macOS / iOS 系统正常显示

## 10. 风险与备选

| 风险 | 影响 | 备选 |
|---|---|---|
| PIL 渲染 emoji 失败 | 高 | 改用 HTML 渲染 + 浏览器录屏 |
| 真实资产文件丢失 | 中 | 路径已在 inventory 标好，重新从 git 拉 |
| 3 min 太长，peer 看不完 | 低 | 制作 90 s 预告片 (E0 + E4 + E6 + E9) |
| 30% 偏差引发 peer 怀疑 | 中 | 反而要正面讲 — 是 demo 的核心 credibility 点 |
| 没有配音，依赖字幕 | 中 | 找志愿者录 3 min 旁白 (中文), 加 ffmpeg `-i voiceover.wav` |
| 浏览器录屏分辨率低 | 中 | 用 `--window-size=1920,1080` + `--force-device-scale-factor=1` |

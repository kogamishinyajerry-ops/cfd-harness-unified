#!/usr/bin/env python3
"""Render Chinese MG demo for cfd-harness-unified cycle-2 · 2026-05-22 PM.

Structure (8 scenes · ~4:10 total):

  0:00-0:10  Hook        — "上一周关了 9 个 regime. 这一周又关了 6 个 blocker."
  0:10-0:25  Recap       — cycle-1 truth-chain still standing
  0:25-1:00  Beat 1      — case_011 multi-region CHT · BLOCKED-not-FAIL
  0:30-1:35  Beat 2      — case_010 LES BLOCK reason "one door deeper"
  1:35-1:55  Beat 3      — step-numbered mesh logs · industrial compat
  1:55-2:30  Beat 4      — streaming parser 13 GiB → bounded · 1/1 → 5/5
  2:30-3:15  Beat 5      — Gap #32 self-discovery (load-bearing emotional beat)
  3:15-3:35  Open        — what's still queued (honest)
  3:35-4:00  Closing CTA — 441 tests · 6 blockers closed · 排队中

Inherits cycle-1 MG style: PingFang SC text, dark navy bg, ease-in-out-cubic
animations, kinetic typography, real-screenshot intercuts.

Borrows scene primitives from build_demo_video_mg_cn.py — the cycle-1
renderer is the SSOT for visual style.

Run:  python3 .demo/build_demo_video_mg_cn_cycle2.py
Out:  .demo/cfdtrust_demo_mg_cn_2026-05-22_cycle2.mp4
"""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[1]
SHOTS_C1 = REPO_ROOT / ".demo" / "screenshots"
SHOTS_C2 = REPO_ROOT / ".demo" / "screenshots_cycle2"
PLOTS = REPO_ROOT / ".demo" / "postproc"
OUT_MP4 = REPO_ROOT / ".demo" / "cfdtrust_demo_mg_cn_2026-05-22_cycle2.mp4"
FRAMES_DIR = Path("/tmp/cfdtrust_demo_mg_cn_cycle2_frames")

W, H = 1280, 720
FPS = 24

# Color palette (matches cycle-1)
BG = (10, 20, 40)
BG_DARK = (4, 10, 20)
ACCENT_GOLD = (240, 198, 116)
ACCENT_CYAN = (110, 193, 228)
ACCENT_GREEN = (165, 200, 130)
ACCENT_RED = (255, 107, 107)
ACCENT_PURPLE = (200, 150, 240)
TEXT_PRIMARY = (245, 245, 245)
TEXT_SECONDARY = (180, 180, 190)
TEXT_TERTIARY = (130, 130, 145)

PINGFANG = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
            "86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/"
            "AssetData/PingFang.ttc")
STHEITI = "/System/Library/Fonts/STHeiti Medium.ttc"
MENLO = "/System/Library/Fonts/Menlo.ttc"


def font(size, kind="zh"):
    try:
        if kind == "zh":
            return ImageFont.truetype(PINGFANG, size, index=0)
        if kind == "zh_bold":
            return ImageFont.truetype(PINGFANG, size, index=4)
        if kind == "mono":
            return ImageFont.truetype(MENLO, size)
    except Exception:
        if kind in ("zh", "zh_bold"):
            return ImageFont.truetype(STHEITI, size, index=0)
        raise


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def fresh_canvas(bg=BG):
    img = Image.new("RGB", (W, H), bg)
    return img, ImageDraw.Draw(img)


def text_size(d, text, fnt):
    bbox = d.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def text_centered(d, text, fnt, cy, color=TEXT_PRIMARY, alpha=1.0,
                  cx=None, anchor_left=False):
    cx = W // 2 if cx is None else cx
    w, h = text_size(d, text, fnt)
    x = cx - (0 if anchor_left else w // 2)
    if alpha < 1.0:
        color = tuple(int(c * alpha + bg * (1 - alpha))
                      for c, bg in zip(color, BG))
    d.text((x, cy - h // 2), text, font=fnt, fill=color)


def rounded_rect(d, box, radius, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline,
                        width=width)


def draw_arrow(d, p1, p2, color, width=3, head=10):
    d.line([p1, p2], fill=color, width=width)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    a = (p2[0] - ux * head + px * head * 0.5,
         p2[1] - uy * head + py * head * 0.5)
    b = (p2[0] - ux * head - px * head * 0.5,
         p2[1] - uy * head - py * head * 0.5)
    d.polygon([p2, a, b], fill=color)


def draw_check(d, x, y, size, color=ACCENT_GREEN, width=4):
    d.line([(x - size // 2, y),
            (x - size // 6, y + size // 2),
            (x + size // 2, y - size // 2)],
           fill=color, width=width, joint="curve")


def paste_image(canvas, path, x, y, w, alpha=1.0, shadow=True):
    if not path or not Path(path).exists():
        return
    im = Image.open(path).convert("RGBA")
    aspect = im.height / im.width
    h_ = int(w * aspect)
    im = im.resize((w, h_), Image.LANCZOS)
    if shadow:
        sh = Image.new("RGBA", (w + 20, h_ + 20), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.rounded_rectangle([10, 10, w + 10, h_ + 10], 8,
                             fill=(0, 0, 0, 80))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        canvas.paste(sh, (x - 10, y - 10), sh)
    if alpha < 1.0:
        bg = Image.new("RGBA", im.size, (BG[0], BG[1], BG[2], 255))
        im = Image.blend(bg, im, alpha)
    canvas.paste(im, (x, y), im)


def topbar(d, label):
    d.text((20, 14), label, font=font(14, "zh"), fill=TEXT_TERTIARY)


# ---- scene builders -------------------------------------------------------

def scene_hook(t_local, t_total):
    """0:00-0:10 · Hook: 9 → 9+6 count-up + 'cycle-2'."""
    img, d = fresh_canvas()
    topbar(d, "cfd-harness-unified · 第二轮交付 · 2026-05-22")
    progress = t_local / t_total

    # cycle-1 anchor text fades in early
    a1 = ease_out_cubic(clamp(progress / 0.2))
    text_centered(d, "上一轮 · 9 个物理域诚实 BLOCK",
                  font(28, "zh"), 200,
                  color=TEXT_SECONDARY, alpha=a1)

    # Big number count-up: 6 production blockers closed
    if progress > 0.15:
        cu_t = ease_out_cubic((progress - 0.15) / 0.45)
        cnt = int(round(lerp(0, 6, cu_t)))
        text_centered(d, str(cnt), font(220, "mono"), 380,
                      color=ACCENT_GOLD)
        text_centered(d, "个生产 blocker 关闭", font(36, "zh_bold"), 530,
                      color=TEXT_PRIMARY)

    # bottom strap
    if progress > 0.7:
        a2 = ease_out_cubic((progress - 0.7) / 0.3)
        text_centered(d, "+ 1 个引擎自己抓住自己",
                      font(28, "zh"), H - 80,
                      color=ACCENT_RED, alpha=a2)

    return img


def scene_recap(t_local, t_total):
    """0:10-0:25 · Recap: cycle-1 truth-chain still standing."""
    img, d = fresh_canvas()
    topbar(d, "01 · 上一轮回顾 · 信任契约仍在")
    progress = t_local / t_total

    a = ease_out_cubic(clamp(progress / 0.15))
    text_centered(d, "上一轮的 9 个围栏", font(42, "zh_bold"), 100,
                  color=TEXT_PRIMARY, alpha=a)
    text_centered(d, "今天依然在", font(24, "zh"), 145,
                  color=TEXT_SECONDARY, alpha=a)

    # 9 hexagons in a 3x3-ish grid representing 9 regimes
    regimes = [
        ("layer", "层流"),
        ("turb", "湍流"),
        ("CHT", "CHT"),
        ("MRF", "旋转"),
        ("comp", "跨音速"),
        ("VOF", "多相"),
        ("LES", "LES"),
        ("ind", "工业"),
        ("rea", "反应流"),
    ]
    for i, (en, cn) in enumerate(regimes):
        r0 = i // 3
        c0 = i % 3
        cx = 320 + c0 * 320
        cy = 250 + r0 * 130
        appear_t = 0.2 + i * 0.04
        ga = ease_out_cubic(clamp((progress - appear_t) / 0.08))
        if ga < 0.05:
            continue
        sz = int(54 * ga)
        if sz < 10:
            continue
        # hex-ish circle
        d.ellipse([cx - sz, cy - sz, cx + sz, cy + sz],
                  outline=ACCENT_GREEN,
                  fill=(20, 40, 30) if ga > 0.5 else None,
                  width=2)
        if ga > 0.5:
            text_centered(d, cn, font(20, "zh_bold"), cy - 2,
                          color=ACCENT_GREEN, cx=cx)

    if progress > 0.7:
        ab = ease_out_cubic((progress - 0.7) / 0.3)
        text_centered(d, "9 / 9 围栏完整 · 0 个 false PASS",
                      font(26, "zh"), H - 60,
                      color=ACCENT_GOLD, alpha=ab)
    return img


def scene_beat1_case011(t_local, t_total):
    """0:25-1:00 · Beat 1: case_011 multi-region CHT BLOCKED-not-FAIL.

    Show: 3 region boxes appear → bc_quality.json snippet → BLOCKED stamp
    with explicit "not_yet_wired" reason.
    """
    img, d = fresh_canvas()
    topbar(d, "02 · case_011 · 多区 CHT · 端到端")
    progress = t_local / t_total

    # title
    ta = ease_out_cubic(clamp(progress / 0.1))
    text_centered(d, "case_011 · plate-fin 紧凑式换热器",
                  font(34, "zh_bold"), 70,
                  color=ACCENT_GOLD, alpha=ta)
    text_centered(d, "chtMultiRegionSimpleFoam · 47M cell · 200/300 iter",
                  font(18, "mono"), 110,
                  color=TEXT_SECONDARY, alpha=ta)

    # 3 region boxes animate in
    region_labels = [
        ("region_cold_fluid", "冷流体", ACCENT_CYAN),
        ("region_hot_fluid", "热流体", ACCENT_RED),
        ("region_solid", "固体", ACCENT_GOLD),
    ]
    for i, (en, cn, col) in enumerate(region_labels):
        appear_t = 0.15 + i * 0.08
        ga = ease_out_cubic(clamp((progress - appear_t) / 0.12))
        if ga < 0.05:
            continue
        bx = 90 + i * 380
        by = 200
        bw, bh = 320, 130
        scale = lerp(0.7, 1.0, ga)
        bbw = int(bw * scale)
        bbh = int(bh * scale)
        bxc = bx + bw // 2
        byc = by + bh // 2
        box = [bxc - bbw // 2, byc - bbh // 2,
               bxc + bbw // 2, byc + bbh // 2]
        rounded_rect(d, box, 14,
                     fill=tuple(int(c * 0.18 + b * 0.82)
                                for c, b in zip(col, BG)),
                     outline=col, width=3)
        if ga > 0.5:
            text_centered(d, cn, font(28, "zh_bold"), byc - 12,
                          color=col, cx=bxc)
            text_centered(d, en, font(14, "mono"), byc + 25,
                          color=TEXT_SECONDARY, cx=bxc)

    # connecting arc / label
    if progress > 0.45:
        la = ease_out_cubic((progress - 0.45) / 0.15)
        text_centered(d, 'bc_quality.json · layout: "multi_region"',
                      font(22, "mono"), 380,
                      color=ACCENT_GREEN, alpha=la)
        text_centered(d, "数据层 · 引擎看见了 3 个 region",
                      font(20, "zh"), 415,
                      color=TEXT_PRIMARY, alpha=la)

    # BLOCKED stamp drops in
    if progress > 0.62:
        st = ease_out_cubic((progress - 0.62) / 0.18)
        sy = int(lerp(280, 530, st))
        stamp_box = [W // 2 - 230, sy - 42,
                     W // 2 + 230, sy + 42]
        rounded_rect(d, stamp_box, 12, outline=ACCENT_GOLD, width=5,
                     fill=(70, 56, 16))
        text_centered(d, "BLOCKED", font(46, "mono"), sy,
                      color=ACCENT_GOLD)
        if progress > 0.78:
            ra = ease_out_cubic((progress - 0.78) / 0.22)
            text_centered(d, "reason: multi_region_bc_validation_not_yet_wired",
                          font(20, "mono"), 610,
                          color=ACCENT_GOLD, alpha=ra)
            text_centered(d, "verdict 层故意不发证 · schema 还没完全接通",
                          font(20, "zh_bold"), 645,
                          color=TEXT_PRIMARY, alpha=ra)
            text_centered(d, "→ 引擎承认自己「还不能」 · 不是「不行」 · 也不是「随便给个 PASS」",
                          font(17, "zh"), 680,
                          color=ACCENT_GREEN, alpha=ra)

    return img


def scene_beat2_case010(t_local, t_total):
    """1:00-1:35 · Beat 2: case_010 LES BLOCK reason 'one door deeper'."""
    img, d = fresh_canvas()
    topbar(d, "03 · case_010 · LES · 验证进度 · 没有 over-promise")
    progress = t_local / t_total

    ta = ease_out_cubic(clamp(progress / 0.1))
    text_centered(d, "case_010 · DrivAer fastback · LES",
                  font(32, "zh_bold"), 70,
                  color=ACCENT_PURPLE, alpha=ta)
    text_centered(d, "Gap #29 · 0.orig 规范布局接受 · commit 914f944",
                  font(18, "mono"), 108,
                  color=TEXT_SECONDARY, alpha=ta)

    # "doors" diagram: 3 doors, BLOCK arrow moves from door 1 to door 2
    doors = [
        ("门 1", "案例目录形状", "case_dir_not_openfoam_compatible"),
        ("门 2", "时间目录存在", "no_time_directory_found"),
        ("门 3", "求解器证据",   "solver evidence missing"),
    ]
    door_y = 290
    door_w, door_h = 280, 200
    for i, (idx, cn, en) in enumerate(doors):
        cx = 180 + i * 320
        appear_t = 0.18 + i * 0.06
        ga = ease_out_cubic(clamp((progress - appear_t) / 0.1))
        if ga < 0.05:
            continue
        scale = lerp(0.7, 1.0, ga)
        dw = int(door_w * scale)
        dh = int(door_h * scale)
        box = [cx - dw // 2, door_y, cx + dw // 2, door_y + dh]
        # door frame
        rounded_rect(d, box, 6,
                     fill=(BG[0] + 8, BG[1] + 12, BG[2] + 24),
                     outline=TEXT_TERTIARY, width=2)
        if ga > 0.5:
            text_centered(d, idx, font(22, "zh_bold"), door_y + 30,
                          color=ACCENT_CYAN, cx=cx)
            text_centered(d, cn, font(18, "zh"), door_y + 70,
                          color=TEXT_PRIMARY, cx=cx)
            text_centered(d, en, font(11, "mono"), door_y + 120,
                          color=TEXT_TERTIARY, cx=cx)

    # cycle-1 arrow stops at door 1
    if 0.45 < progress < 0.65:
        a1 = ease_out_cubic((progress - 0.45) / 0.2)
        # arrow into door 1 with red X over its center
        draw_arrow(d, (180, 240), (180, door_y - 6),
                   color=ACCENT_RED, width=4, head=14)
        if a1 > 0.5:
            text_centered(d, "Cycle-1: 卡在门 1 (错原因)",
                          font(18, "zh_bold"), 220,
                          color=ACCENT_RED, cx=180, alpha=a1)

    # cycle-2 arrow shifts to door 2
    if progress > 0.55:
        a2 = ease_out_cubic((progress - 0.55) / 0.2)
        # arrow into door 2
        draw_arrow(d, (500, 240), (500, door_y - 6),
                   color=ACCENT_GREEN, width=5, head=16)
        if a2 > 0.4:
            text_centered(d, "Cycle-2: 通过门 1 → 卡在门 2",
                          font(18, "zh_bold"), 220,
                          color=ACCENT_GREEN, cx=500, alpha=a2)

    if progress > 0.78:
        b = ease_out_cubic((progress - 0.78) / 0.22)
        text_centered(d, "可验证的进度 · 不是 over-promise",
                      font(28, "zh_bold"), 580,
                      color=ACCENT_GOLD, alpha=b)
        text_centered(d, "BLOCK 原因深入一层 · solver_execution 依然 skipped (不是 ingested)",
                      font(18, "zh"), 620,
                      color=TEXT_PRIMARY, alpha=b)
        text_centered(d, "→ 引擎拒绝声称自己跑过案例 (因为它没跑过)",
                      font(16, "zh"), 652,
                      color=ACCENT_CYAN, alpha=b)

    return img


def scene_beat3_step_logs(t_local, t_total):
    """1:35-1:55 · Beat 3: step-numbered mesh logs · industrial compat."""
    img, d = fresh_canvas()
    topbar(d, "04 · 工业脚本兼容 · Gap #26-#27")
    progress = t_local / t_total

    ta = ease_out_cubic(clamp(progress / 0.1))
    text_centered(d, "在用户实际命名脚本的地方碰见用户",
                  font(30, "zh_bold"), 80,
                  color=ACCENT_GOLD, alpha=ta)
    text_centered(d, "industrial run-script step-numbering · commit 68f4a70",
                  font(16, "mono"), 118,
                  color=TEXT_SECONDARY, alpha=ta)

    # 5 step-numbered log file boxes appearing left to right
    logs = [
        "01_blockMesh.log",
        "02_snappyHexMesh.log",
        "03_extrudeMesh.log",
        "04_decomposePar.log",
        "05_simpleFoam.log",
    ]
    box_w = 220
    y = 280
    for i, name in enumerate(logs):
        appear_t = 0.15 + i * 0.08
        ga = ease_out_cubic(clamp((progress - appear_t) / 0.1))
        if ga < 0.05:
            continue
        x = 60 + i * 240
        # slide from below
        slide = int(lerp(40, 0, ga))
        col = ACCENT_GREEN if i == 4 else ACCENT_CYAN
        box = [x, y + slide, x + box_w, y + 90 + slide]
        rounded_rect(d, box, 9,
                     fill=tuple(int(c * 0.2 + b * 0.8)
                                for c, b in zip(col, BG)),
                     outline=col, width=2)
        if ga > 0.5:
            text_centered(d, name, font(15, "mono"), y + 45 + slide,
                          color=col, cx=x + box_w // 2)
            text_centered(d, f"step {i + 1}", font(13, "zh"), y + 68 + slide,
                          color=TEXT_SECONDARY, cx=x + box_w // 2)

    # "highest step wins" arrow
    if progress > 0.6:
        a = ease_out_cubic((progress - 0.6) / 0.2)
        draw_arrow(d, (W // 2 - 200, 430), (W - 160, 430),
                   color=ACCENT_GOLD, width=4, head=14)
        text_centered(d, "step 号最大 = canonical evidence",
                      font(20, "zh_bold"), 460,
                      color=ACCENT_GOLD, alpha=a)

    if progress > 0.78:
        c = ease_out_cubic((progress - 0.78) / 0.22)
        text_centered(d, "我们不强制用户按特定风格命名",
                      font(22, "zh"), 540,
                      color=TEXT_PRIMARY, alpha=c)
        text_centered(d, "我们去找用户实际在用的命名",
                      font(22, "zh_bold"), 580,
                      color=ACCENT_GREEN, alpha=c)
        text_centered(d, "+ 67 LOC engine · +47 LOC tests · confidence: high",
                      font(14, "mono"), 630,
                      color=TEXT_TERTIARY, alpha=c)

    return img


def scene_beat4_streaming(t_local, t_total):
    """1:55-2:30 · Beat 4: streaming parser 13 GiB → bounded · 1/1 → 5/5."""
    img, d = fresh_canvas()
    topbar(d, "05 · TBD-20 · streaming · 工业规模就绪")
    progress = t_local / t_total

    ta = ease_out_cubic(clamp(progress / 0.08))
    text_centered(d, "3.3 GiB 日志不再撑爆引擎",
                  font(32, "zh_bold"), 70,
                  color=TEXT_PRIMARY, alpha=ta)
    text_centered(d, "TBD-20 · streaming chunk parser · commit e8691f3",
                  font(16, "mono"), 110,
                  color=TEXT_SECONDARY, alpha=ta)

    # Two bars: before (13 GiB, red, animates growing) vs after (bounded, green)
    bar_x = 220
    bar_max_w = 800

    if progress > 0.15:
        ga = ease_out_cubic(clamp((progress - 0.15) / 0.3))
        # before bar grows then settles
        bw = int(bar_max_w * ga)
        d.rectangle([bar_x, 200, bar_x + bw, 245], fill=ACCENT_RED,
                    outline=ACCENT_RED)
        if ga > 0.7:
            t1 = ease_out_cubic((ga - 0.7) / 0.3)
            text_centered(d, "13 GiB", font(28, "mono"), 222,
                          color=TEXT_PRIMARY, cx=bar_x + bw + 80, alpha=t1)
            text_centered(d, "Cycle-1 · OOM", font(16, "zh"), 180,
                          color=ACCENT_RED, cx=200, alpha=t1, anchor_left=False)

    if progress > 0.4:
        ga = ease_out_cubic(clamp((progress - 0.4) / 0.25))
        bw = int(60 * ga)
        d.rectangle([bar_x, 300, bar_x + bw, 345], fill=ACCENT_GREEN,
                    outline=ACCENT_GREEN)
        if ga > 0.6:
            t2 = ease_out_cubic((ga - 0.6) / 0.4)
            text_centered(d, "bounded chunk", font(24, "mono"), 322,
                          color=TEXT_PRIMARY, cx=bar_x + 180, alpha=t2)
            text_centered(d, "Cycle-2 · OK", font(16, "zh"), 280,
                          color=ACCENT_GREEN, cx=200, alpha=t2)

    # bonus payoff: 1/1 → 5/5 fields
    if progress > 0.65:
        a = ease_out_cubic((progress - 0.65) / 0.2)
        # left side small text + arrow to right side count
        text_centered(d, "意外加成 · case_011 残差字段追踪",
                      font(22, "zh_bold"), 430,
                      color=ACCENT_GOLD, alpha=a)

        # left "1/1"
        cx1 = 350
        rounded_rect(d, [cx1 - 90, 470, cx1 + 90, 560], 12,
                     fill=(70, 30, 30), outline=ACCENT_RED, width=3)
        text_centered(d, "1 / 1", font(48, "mono"), 510,
                      color=ACCENT_RED, cx=cx1)
        text_centered(d, "Cycle-1", font(16, "zh"), 575,
                      color=TEXT_SECONDARY, cx=cx1)

        # arrow
        draw_arrow(d, (cx1 + 110, 515), (W - cx1 - 110, 515),
                   color=ACCENT_GOLD, width=4, head=16)

        # right "5/5"
        cx2 = W - cx1
        rounded_rect(d, [cx2 - 90, 470, cx2 + 90, 560], 12,
                     fill=(30, 60, 40), outline=ACCENT_GREEN, width=3)
        text_centered(d, "5 / 5", font(48, "mono"), 510,
                      color=ACCENT_GREEN, cx=cx2)
        text_centered(d, "Cycle-2", font(16, "zh"), 575,
                      color=TEXT_SECONDARY, cx=cx2)

    if progress > 0.85:
        b = ease_out_cubic((progress - 0.85) / 0.15)
        text_centered(d, "Ux · Uy · Uz · h · p_rgh — 全部进 residuals.csv",
                      font(15, "mono"), 615,
                      color=TEXT_PRIMARY, alpha=b)
        text_centered(d, "(byte-identical proven by test_stream_parser_equivalence)",
                      font(13, "mono"), 645,
                      color=TEXT_TERTIARY, alpha=b)
    return img


def scene_beat5_gap32(t_local, t_total):
    """2:30-3:15 · Beat 5: Gap #32 self-discovery (load-bearing emotional beat)."""
    img, d = fresh_canvas()
    topbar(d, "06 · Gap #32 · 引擎再次抓住自己")
    progress = t_local / t_total

    # Title big
    ta = ease_out_cubic(clamp(progress / 0.08))
    text_centered(d, "Gap #32", font(80, "mono"), 90,
                  color=ACCENT_RED, alpha=ta)
    text_centered(d, "dogfood agent 自发现 · 同弧落地修复",
                  font(28, "zh_bold"), 150,
                  color=TEXT_PRIMARY, alpha=ta)

    # Phase 1: the leak — show the sentinel propagation
    if 0.12 <= progress < 0.45:
        a = ease_out_cubic((progress - 0.12) / 0.3)
        # 3 region rows with __none_laminar__ tagged in red
        rows = [
            ("region_cold_fluid", ["U", "p", "__none_laminar__"]),
            ("region_hot_fluid",  ["U", "p", "__none_laminar__"]),
            ("region_solid",      ["U", "p", "__none_laminar__"]),
        ]
        for i, (region, fields) in enumerate(rows):
            row_t = 0.12 + i * 0.06
            ra = ease_out_cubic(clamp((progress - row_t) / 0.08))
            if ra < 0.05:
                continue
            y_row = 240 + i * 56
            d.text((90, y_row), region, font=font(20, "mono"),
                   fill=ACCENT_CYAN if ra > 0.6 else TEXT_TERTIARY)
            d.text((430, y_row), "expected_fields:",
                   font=font(16, "zh"), fill=TEXT_SECONDARY)
            x_chip = 660
            for fld in fields:
                col = ACCENT_RED if fld.startswith("__") else ACCENT_GREEN
                wc, hc = text_size(d, fld, font(16, "mono"))
                rounded_rect(d, [x_chip - 8, y_row - 6,
                                 x_chip + wc + 8, y_row + hc + 6],
                             8,
                             fill=(70, 30, 30) if col == ACCENT_RED
                                  else (30, 60, 40) if ra > 0.7 else None,
                             outline=col, width=2)
                if ra > 0.6:
                    d.text((x_chip, y_row), fld,
                           font=font(16, "mono"), fill=col)
                x_chip += wc + 28
        if a > 0.7:
            text_centered(d, "★ __none_laminar__ 不是真字段 — 是 manifest 的 sentinel",
                          font(22, "zh_bold"), 460,
                          color=ACCENT_GOLD, alpha=(a - 0.7) / 0.3)

    # Phase 2: discovery + same-arc fix
    elif 0.45 <= progress < 0.78:
        a = ease_out_cubic((progress - 0.45) / 0.3)

        # 3 panels: discovery → fix → ship
        panels = [
            ("dogfood 发现",  "case_011 cycle-2 re-dogfood",
             "见 sentinel 泄漏",                      ACCENT_GOLD),
            ("同弧修复",       "commit 77825b8",
             "+39 LOC · +1 test · confidence: high", ACCENT_GREEN),
            ("12 commit 内落地", "不进 triage 队列",
             "围栏依然完整",                          ACCENT_CYAN),
        ]
        for i, (title, mid, bot, col) in enumerate(panels):
            pa = ease_out_cubic(clamp((progress - 0.45 - i * 0.08) / 0.12))
            if pa < 0.05:
                continue
            cx = 220 + i * 410
            cy = 360
            scale = lerp(0.7, 1.0, pa)
            pw = int(340 * scale)
            ph = int(200 * scale)
            box = [cx - pw // 2, cy - ph // 2,
                   cx + pw // 2, cy + ph // 2]
            rounded_rect(d, box, 14,
                         fill=tuple(int(c * 0.15 + b * 0.85)
                                    for c, b in zip(col, BG)),
                         outline=col, width=3)
            if pa > 0.6:
                text_centered(d, title, font(24, "zh_bold"), cy - 50,
                              color=col, cx=cx)
                text_centered(d, mid, font(17, "mono"), cy - 10,
                              color=TEXT_PRIMARY, cx=cx)
                text_centered(d, bot, font(16, "zh"), cy + 30,
                              color=TEXT_SECONDARY, cx=cx)
            # arrow to next
            if i < 2 and pa > 0.8:
                draw_arrow(d, (cx + pw // 2 + 4, cy),
                           (cx + pw // 2 + 60, cy),
                           color=ACCENT_GOLD, width=4, head=12)

    # Phase 3: anchor to cycle-1 TBD-17
    if progress >= 0.78:
        a = ease_out_cubic((progress - 0.78) / 0.22)
        text_centered(d, "这是 cycle-1 TBD-17 时刻的同型再现",
                      font(28, "zh_bold"), 540,
                      color=ACCENT_GOLD, alpha=a)
        text_centered(d, "引擎依然在自己的运行中发现自己 ·"
                      "不是 marketing fluff",
                      font(20, "zh"), 580,
                      color=TEXT_PRIMARY, alpha=a)
        text_centered(d, "诚实, 不是「打算诚实」",
                      font(22, "zh_bold"), 620,
                      color=ACCENT_GREEN, alpha=a)
        text_centered(d,
                      "commit 77825b8 · 39 LOC · 1 test · confidence: high",
                      font(15, "mono"), 660,
                      color=TEXT_TERTIARY, alpha=a)

    return img


def scene_screenshot_interlude(t_local, t_total):
    """3:15-3:35 · Real screenshot inserts (cycle-2)."""
    img, d = fresh_canvas()
    topbar(d, "07 · 真实运行截图")
    progress = t_local / t_total

    shots = [
        (SHOTS_C2 / "shot_c2_case011_bc_quality.png",
         "case_011 · 真实 bc_quality.json · 多区数据层"),
        (SHOTS_C2 / "shot_c2_streaming_payoff.png",
         "TBD-20 streaming · 真实 residuals.csv · 5 字段全 tracked"),
        (SHOTS_C2 / "shot_c2_cycle2_commits.png",
         "Cycle-2 · 19 个 commit · 颜色按类别分"),
    ]
    seg = 1.0 / len(shots)
    for i, (path, cap) in enumerate(shots):
        s0 = i * seg
        s1 = (i + 1) * seg
        if progress < s0 or progress > s1:
            continue
        local_t = (progress - s0) / seg
        if local_t < 0.12:
            a = ease_out_cubic(local_t / 0.12)
        elif local_t > 0.85:
            a = ease_out_cubic((1.0 - local_t) / 0.15)
        else:
            a = 1.0
        text_centered(d, cap, font(24, "zh_bold"), 75,
                      color=ACCENT_GOLD, alpha=a)
        paste_image(img, path, x=140, y=110, w=1000, alpha=a)
        text_centered(d, "源文件: 真实工件 · 不是占位符",
                      font(16, "zh"), 670,
                      color=TEXT_SECONDARY, alpha=a)
    return img


def scene_open_queue(t_local, t_total):
    """3:35-3:55 · What's still open (honest)."""
    img, d = fresh_canvas()
    topbar(d, "08 · 仍未落地的工作 · 排队中, not coming soon")
    progress = t_local / t_total

    ta = ease_out_cubic(clamp(progress / 0.12))
    text_centered(d, "仍未落地的工作", font(38, "zh_bold"), 70,
                  color=TEXT_PRIMARY, alpha=ta)
    text_centered(d, "我们不会说「即将上线」· 我们说「排队中」",
                  font(20, "zh"), 110,
                  color=ACCENT_GOLD, alpha=ta)

    items = [
        ("charter-class", "Gap #18 · compressible_contract schema",
         "thermophysical / perfectGas / sutherland / rho / T / Mach", ACCENT_RED),
        ("charter-class", "Gap #28 · les_contract schema",
         "turbulenceProperties / delta cubeRootVol / SGS", ACCENT_RED),
        ("charter-class", "TBD-3 · vof_contract schema",
         "interFoam phase-field awareness", ACCENT_RED),
        ("charter-class", "TBD-18 · reacting_contract schema",
         "species_list / inlet_compositions / combustion_model", ACCENT_RED),
        ("spike-leftover", "TBD-16 · sub-second physical-time iter=0 collapse",
         "breaks unsteady iteration discriminator", ACCENT_GOLD),
        ("spike-leftover", "Multi-region bc_contract verdict-layer wiring",
         "the deferred half of Gap #11", ACCENT_GOLD),
    ]
    y0 = 180
    for i, (tag, item, note, col) in enumerate(items):
        appear_t = 0.18 + i * 0.06
        a = ease_out_cubic(clamp((progress - appear_t) / 0.08))
        if a < 0.05:
            continue
        slide = int(lerp(-100, 0, a))
        y = y0 + i * 62
        # tag chip
        wc, hc = text_size(d, tag, font(14, "mono"))
        rounded_rect(d, [80 + slide, y - 18,
                         100 + slide + wc, y + 16], 9,
                     outline=col, width=2,
                     fill=tuple(int(c * 0.15 + b * 0.85)
                                for c, b in zip(col, BG)))
        if a > 0.5:
            d.text((90 + slide, y - 12), tag,
                   font=font(14, "mono"), fill=col)
            d.text((230 + slide, y - 20), item,
                   font=font(20, "zh_bold"), fill=TEXT_PRIMARY)
            d.text((230 + slide, y + 8), note,
                   font=font(14, "mono"), fill=TEXT_TERTIARY)

    return img


def scene_closing(t_local, t_total):
    """3:55-4:10 · Closing CTA."""
    img, d = fresh_canvas(bg=BG_DARK)
    progress = t_local / t_total

    title_t = ease_out_cubic(clamp(progress / 0.25))
    title_y = int(lerp(H, 160, title_t))
    text_centered(d, "诚实的 CFD 审计引擎",
                  font(56, "zh_bold"), title_y,
                  color=ACCENT_GOLD)

    if progress > 0.2:
        a = ease_out_cubic((progress - 0.2) / 0.25)
        text_centered(d, "第二轮交付 · 6 个生产 blocker 关闭",
                      font(28, "zh"), 240,
                      color=TEXT_PRIMARY, alpha=a)

    facts = [
        ("441", "测试通过", ACCENT_GREEN),
        ("19",  "cycle-2 commit", ACCENT_CYAN),
        ("6",   "生产 blocker 关闭", ACCENT_GOLD),
        ("0",   "false PASS", ACCENT_GREEN),
        ("1",   "引擎自发现 · 同弧修复", ACCENT_RED),
    ]
    # mini grid of stat cards
    if progress > 0.35:
        for i, (num, label, col) in enumerate(facts):
            appear_t = 0.35 + i * 0.07
            a = ease_out_cubic(clamp((progress - appear_t) / 0.1))
            if a < 0.05:
                continue
            cx = 130 + i * 240
            cy = 380
            scale = lerp(0.7, 1.0, a)
            cw = int(200 * scale)
            ch = int(140 * scale)
            box = [cx - cw // 2, cy - ch // 2,
                   cx + cw // 2, cy + ch // 2]
            rounded_rect(d, box, 12,
                         outline=col, width=2,
                         fill=tuple(int(c * 0.18 + b * 0.82)
                                    for c, b in zip(col, BG_DARK)))
            if a > 0.5:
                text_centered(d, num, font(50, "mono"), cy - 14,
                              color=col, cx=cx)
                text_centered(d, label, font(15, "zh"), cy + 36,
                              color=TEXT_PRIMARY, cx=cx)

    if progress > 0.78:
        cta = ease_out_cubic((progress - 0.78) / 0.22)
        text_centered(d, "AI 顾问 = Claude Code session · 读 V-series · 拒绝胡乱 PASS",
                      font(20, "zh"), H - 80,
                      color=ACCENT_CYAN, alpha=cta)
        text_centered(d, "排队中, not coming soon",
                      font(22, "zh_bold"), H - 40,
                      color=ACCENT_GOLD, alpha=cta)

    return img


# ---- timeline -------------------------------------------------------------
# Scenes sum to 250s = 4:10. Within the 3-5 min stakeholder demo target.

TIMELINE = [
    (0.0,   10.0, scene_hook),
    (10.0,  25.0, scene_recap),
    (25.0,  60.0, scene_beat1_case011),
    (60.0,  95.0, scene_beat2_case010),
    (95.0,  115.0, scene_beat3_step_logs),
    (115.0, 150.0, scene_beat4_streaming),
    (150.0, 195.0, scene_beat5_gap32),
    (195.0, 215.0, scene_screenshot_interlude),
    (215.0, 235.0, scene_open_queue),
    (235.0, 250.0, scene_closing),
]


def build_video():
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True)

    total_secs = TIMELINE[-1][1]
    total_frames = int(total_secs * FPS)
    print(f"[cycle2] {total_secs:.1f}s · {total_frames} frames @ {FPS}fps")

    frame_idx = 0
    for (start, end, builder) in TIMELINE:
        seg_len = end - start
        seg_frames = int(seg_len * FPS)
        for i in range(seg_frames):
            t_local = i / FPS
            img = builder(t_local, seg_len)
            img.save(FRAMES_DIR / f"f_{frame_idx:06d}.png",
                     optimize=False, compress_level=1)
            frame_idx += 1
            if frame_idx % 240 == 0:
                print(f"[cycle2]   {frame_idx}/{total_frames}"
                      f" ({100 * frame_idx / total_frames:.0f}%)")

    print(f"[cycle2] {frame_idx} frames rendered · encoding")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "f_%06d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "21",
        "-preset", "medium",
        "-movflags", "+faststart",
        str(OUT_MP4),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:], file=sys.stderr)
        raise SystemExit(r.returncode)
    size_mb = OUT_MP4.stat().st_size / (1024 * 1024)
    print(f"[cycle2] OUT {OUT_MP4} · {size_mb:.1f} MB")
    shutil.rmtree(FRAMES_DIR)


if __name__ == "__main__":
    build_video()

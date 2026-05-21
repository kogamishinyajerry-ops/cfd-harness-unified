#!/usr/bin/env python3
"""Render Chinese MG (motion-graphics) demo for cfd-harness-unified 2026-05-22.

Differences from build_demo_video.py:
- Chinese narration via PingFang SC / STHeiti
- MG style: kinetic typography, shape animations, count-up numbers,
  diagrams. NOT terminal text scrolling.
- Real project screenshots interspersed as illustration cuts
  (from .demo/screenshots/ — extracted from the prior terminal-style demo).
- Real residual plots from .demo/postproc/.

Run:  python3 .demo/build_demo_video_mg_cn.py
Out:  .demo/cfdtrust_demo_mg_cn_2026-05-22.mp4  (~3:30, ~5-10 MB)
"""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[1]
SHOTS = REPO_ROOT / ".demo" / "screenshots"
PLOTS = REPO_ROOT / ".demo" / "postproc"
OUT_MP4 = REPO_ROOT / ".demo" / "cfdtrust_demo_mg_cn_2026-05-22.mp4"
FRAMES_DIR = Path("/tmp/cfdtrust_demo_mg_cn_frames")

W, H = 1280, 720
FPS = 24                              # smoother than 10 for MG transitions

# Color palette (dark theme + accents)
BG = (10, 20, 40)                     # deep navy
BG_DARK = (4, 10, 20)
ACCENT_GOLD = (240, 198, 116)
ACCENT_CYAN = (110, 193, 228)
ACCENT_GREEN = (165, 200, 130)
ACCENT_RED = (255, 107, 107)
ACCENT_PURPLE = (200, 150, 240)
TEXT_PRIMARY = (245, 245, 245)
TEXT_SECONDARY = (180, 180, 190)
TEXT_TERTIARY = (130, 130, 145)

# Fonts (verified available at module load)
PINGFANG = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"
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


# ---- math helpers ---------------------------------------------------------

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


# ---- drawing primitives ---------------------------------------------------

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
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline,
                        width=width)


def draw_arrow(d, p1, p2, color, width=3, head=10):
    d.line([p1, p2], fill=color, width=width)
    # arrowhead
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / L, dy / L
    # perpendicular
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


def draw_cross(d, x, y, size, color=ACCENT_RED, width=4):
    d.line([(x - size // 2, y - size // 2),
            (x + size // 2, y + size // 2)],
           fill=color, width=width)
    d.line([(x - size // 2, y + size // 2),
            (x + size // 2, y - size // 2)],
           fill=color, width=width)


def draw_triangle_warn(d, x, y, size, color=ACCENT_GOLD, width=4):
    pts = [(x, y - size // 2), (x - size // 2, y + size // 2),
           (x + size // 2, y + size // 2)]
    d.polygon(pts, outline=color, width=width)
    # exclamation
    d.line([(x, y - size // 6), (x, y + size // 8)],
           fill=color, width=width - 1)
    d.ellipse([(x - 2, y + size // 4 - 2), (x + 2, y + size // 4 + 2)],
              fill=color)


def paste_image(canvas, path, x, y, w, alpha=1.0, shadow=True):
    if not path or not Path(path).exists():
        return
    im = Image.open(path).convert("RGBA")
    aspect = im.height / im.width
    h_ = int(w * aspect)
    im = im.resize((w, h_), Image.LANCZOS)
    if shadow:
        # soft shadow behind
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


# ---- scene builders -------------------------------------------------------

def scene_hook(t_local, t_total):
    """0:00-0:12 · Hook: PASS badge cracks, question mark grows."""
    img, d = fresh_canvas()
    # title bar tiny
    d.text((20, 14), "cfd-harness-unified · 诚实的 CFD 审计引擎",
           font=font(14, "zh"), fill=TEXT_TERTIARY)

    progress = t_local / t_total

    # First half: PASS badge appears + grows
    if progress < 0.35:
        scale = ease_out_cubic(progress / 0.35)
        badge_w = int(280 * scale)
        badge_h = int(120 * scale)
        cx, cy = W // 2, H // 2 - 30
        if badge_w > 30:
            box = [cx - badge_w // 2, cy - badge_h // 2,
                   cx + badge_w // 2, cy + badge_h // 2]
            rounded_rect(d, box, 16, fill=(40, 90, 50),
                         outline=ACCENT_GREEN, width=3)
            if scale > 0.6:
                draw_check(d, cx - 80, cy, 50, color=ACCENT_GREEN, width=6)
                text_centered(d, "PASS", font(56, "mono"),
                              cy, color=ACCENT_GREEN, cx=cx + 30)

    # 0.35-0.65: hold + question mark grows
    elif progress < 0.7:
        cx, cy = W // 2, H // 2 - 30
        # solid PASS badge
        rounded_rect(d, [cx - 140, cy - 60, cx + 140, cy + 60], 16,
                     fill=(40, 90, 50), outline=ACCENT_GREEN, width=3)
        draw_check(d, cx - 80, cy, 50, color=ACCENT_GREEN, width=6)
        text_centered(d, "PASS", font(56, "mono"), cy,
                      color=ACCENT_GREEN, cx=cx + 30)
        # question mark grows from the right
        qprogress = (progress - 0.35) / 0.35
        qscale = ease_out_cubic(qprogress)
        qsize = int(160 * qscale)
        if qsize > 20:
            qfnt = font(qsize, "zh_bold")
            text_centered(d, "?", qfnt, cy, color=ACCENT_RED,
                          cx=cx + 220)

    # 0.7-1.0: text fades in below
    else:
        cx, cy = W // 2, H // 2 - 30
        rounded_rect(d, [cx - 140, cy - 60, cx + 140, cy + 60], 16,
                     fill=(40, 90, 50), outline=ACCENT_GREEN, width=3)
        draw_check(d, cx - 80, cy, 50, color=ACCENT_GREEN, width=6)
        text_centered(d, "PASS", font(56, "mono"), cy,
                      color=ACCENT_GREEN, cx=cx + 30)
        text_centered(d, "?", font(160, "zh_bold"), cy,
                      color=ACCENT_RED, cx=cx + 220)

        t_fade = ease_out_cubic((progress - 0.7) / 0.3)
        text_centered(d, "CFD 报告上写着 PASS",
                      font(36, "zh_bold"), H - 200,
                      color=TEXT_PRIMARY, alpha=t_fade)
        text_centered(d, "你敢签字吗？",
                      font(44, "zh_bold"), H - 140,
                      color=ACCENT_GOLD, alpha=t_fade)

    return img


def scene_problem(t_local, t_total):
    """0:12-0:35 · 传统 CFD 审计只信求解器自己说"."""
    img, d = fresh_canvas()
    d.text((20, 14), "01 · 问题", font=font(14, "zh"),
           fill=TEXT_TERTIARY)

    progress = t_local / t_total

    # title fade in
    title_alpha = ease_out_cubic(clamp(progress / 0.15))
    text_centered(d, "传统 CFD 审计", font(42, "zh_bold"), 100,
                  color=TEXT_PRIMARY, alpha=title_alpha)
    text_centered(d, "信任「求解器自己说收敛」",
                  font(28, "zh"), 150,
                  color=TEXT_SECONDARY, alpha=title_alpha)

    # 3-box pipeline appears sequentially
    box_w, box_h = 200, 90
    y = 320
    boxes = [
        (180, "求解器", "Solver", ACCENT_CYAN),
        (540, "结果文件", "Output", ACCENT_CYAN),
        (900, "审计报告", "Audit", ACCENT_CYAN),
    ]
    # box appearance phases
    for i, (cx, label_cn, label_en, col) in enumerate(boxes):
        appear_t = 0.2 + i * 0.12
        b_alpha = ease_out_cubic(clamp((progress - appear_t) / 0.12))
        if b_alpha > 0.05:
            scale = lerp(0.6, 1.0, b_alpha)
            bw = int(box_w * scale)
            bh = int(box_h * scale)
            box = [cx - bw // 2, y - bh // 2, cx + bw // 2, y + bh // 2]
            fill = tuple(int(c * 0.3 + b * 0.7) for c, b in zip(col, BG))
            rounded_rect(d, box, 12, fill=fill, outline=col, width=2)
            if b_alpha > 0.5:
                text_centered(d, label_cn, font(22, "zh_bold"),
                              y - 12, color=col, cx=cx)
                text_centered(d, label_en, font(14, "mono"),
                              y + 18, color=TEXT_SECONDARY, cx=cx)
        # arrow to next box
        if i < 2:
            arr_t = 0.32 + i * 0.12
            arr_a = ease_out_cubic(clamp((progress - arr_t) / 0.1))
            if arr_a > 0.3:
                draw_arrow(d, (cx + box_w // 2 + 10, y),
                           (boxes[i + 1][0] - box_w // 2 - 10, y),
                           color=TEXT_SECONDARY, width=3, head=14)

    # 0.65-1.0: "PASS" stamp lands at end + cracks
    if progress > 0.65:
        stamp_t = ease_out_cubic((progress - 0.65) / 0.2)
        # PASS stamp slides down onto audit box
        sy = int(lerp(y - 200, y + 130, stamp_t))
        rounded_rect(d, [820, sy - 22, 980, sy + 22], 6,
                     outline=ACCENT_GREEN, width=3,
                     fill=(40, 90, 50))
        text_centered(d, "PASS", font(28, "mono"), sy,
                      color=ACCENT_GREEN, cx=900)

    # 0.85-1.0: red question + critique line
    if progress > 0.85:
        critique_a = ease_out_cubic((progress - 0.85) / 0.15)
        text_centered(d, "→ 求解器没收敛、证据不全、围栏也不在，照样输出 PASS",
                      font(22, "zh"), 540,
                      color=ACCENT_RED, alpha=critique_a)

    return img


def scene_solution(t_local, t_total):
    """0:35-1:15 · cfdtrust ingest · 6-gate trust contract + honesty fences."""
    img, d = fresh_canvas()
    d.text((20, 14), "02 · 我们的做法", font=font(14, "zh"),
           fill=TEXT_TERTIARY)

    progress = t_local / t_total

    # title
    title_alpha = ease_out_cubic(clamp(progress / 0.12))
    text_centered(d, "cfdtrust ingest", font(48, "mono"), 90,
                  color=ACCENT_GOLD, alpha=title_alpha)
    text_centered(d, "把外部跑过的 OpenFOAM 算例装进审计引擎，但绝不替它说 PASS",
                  font(22, "zh"), 140,
                  color=TEXT_SECONDARY, alpha=title_alpha)

    # 6 gates as circles in arc
    gates = [
        ("geometry", "几何"),
        ("mesh", "网格"),
        ("BC", "边界"),
        ("solver", "求解器"),
        ("QoI", "目标量"),
        ("reference", "对照"),
    ]
    arc_cx, arc_cy = W // 2, 360
    arc_r = 200
    for i, (en, cn) in enumerate(gates):
        angle = math.pi + math.pi * i / (len(gates) - 1)  # 180 to 360
        cx = arc_cx + int(arc_r * math.cos(angle))
        cy = arc_cy + int(arc_r * math.sin(angle) * 0.45)
        appear_t = 0.18 + i * 0.06
        g_alpha = ease_out_cubic(clamp((progress - appear_t) / 0.1))
        if g_alpha < 0.05:
            continue
        r = int(40 * g_alpha)
        if r > 10:
            d.ellipse([cx - r, cy - r, cx + r, cy + r],
                      fill=(BG[0] + 30, BG[1] + 40, BG[2] + 50),
                      outline=ACCENT_CYAN, width=2)
            if g_alpha > 0.6:
                text_centered(d, cn, font(16, "zh_bold"), cy - 4,
                              color=TEXT_PRIMARY, cx=cx)
                text_centered(d, en, font(10, "mono"), cy + 14,
                              color=TEXT_SECONDARY, cx=cx)

    # honesty fence rules appearing below
    if progress > 0.6:
        rule_a = ease_out_cubic((progress - 0.6) / 0.2)
        rules = [
            ("围栏 1", "validated  →  solver_execution = real",
             "已验证的报告必须来自被引擎亲眼看过的运行"),
            ("围栏 2", "PASS  →  solver_execution = real",
             "PASS 不能来自外部算例 · 顶多到 WARN"),
            ("围栏 3", "ingested  →  validation_status ≤ partial",
             "外部导入的最高只能 partial · 拿不到 validated"),
        ]
        for i, (badge, rule_en, rule_cn) in enumerate(rules):
            row_t = 0.6 + i * 0.08
            r_alpha = ease_out_cubic(clamp((progress - row_t) / 0.1))
            if r_alpha < 0.1:
                continue
            y_row = 540 + i * 50
            rounded_rect(d, [80, y_row - 18, 200, y_row + 18], 9,
                         fill=ACCENT_GOLD if r_alpha > 0.5 else None,
                         outline=ACCENT_GOLD, width=2)
            if r_alpha > 0.5:
                text_centered(d, badge, font(18, "zh_bold"), y_row,
                              color=BG, cx=140)
                d.text((230, y_row - 14), rule_en,
                       font=font(16, "mono"), fill=TEXT_PRIMARY)
                d.text((230, y_row + 2), rule_cn,
                       font=font(14, "zh"), fill=TEXT_SECONDARY)

    return img


def scene_proof_matrix(t_local, t_total):
    """1:15-2:25 · 9 regimes capability matrix + count-up numbers."""
    img, d = fresh_canvas()
    d.text((20, 14), "03 · 真实证据 · 9 个物理域",
           font=font(14, "zh"), fill=TEXT_TERTIARY)

    progress = t_local / t_total

    title_alpha = ease_out_cubic(clamp(progress / 0.08))
    text_centered(d, "9 个物理域 · 真实工业算例", font(38, "zh_bold"), 70,
                  color=TEXT_PRIMARY, alpha=title_alpha)
    text_centered(d, "层流 · 湍流 · CHT · 旋转 · 跨音速 · 多相 · LES · 工业 · 反应流",
                  font(18, "zh"), 110,
                  color=TEXT_SECONDARY, alpha=title_alpha)

    # 9 rows table
    rows = [
        ("case_027", "Hagen-Poiseuille", "层流管流",
         "✓ 端到端通过", ACCENT_GREEN),
        ("case_021", "NASA TMR", "湍流 RANS k-ωSST",
         "✓ Gap #9 修复后 5 字段收敛", ACCENT_GREEN),
        ("case_011", "plate-fin HX", "CHT 多区 · 47M cell",
         "✓ 端到端通过", ACCENT_GREEN),
        ("case_004", "NREL Phase VI", "MRF 旋转",
         "✓ 端到端通过", ACCENT_GREEN),
        ("case_006", "ONERA M6", "跨音速可压",
         "△ 机械通过 · 物理盲", ACCENT_GOLD),
        ("case_007", "KCS ship", "多相 VOF",
         "△ 机械通过 · VOF 盲", ACCENT_GOLD),
        ("case_028", "APU bay 工业", "浮升 CHT · 34 patch",
         "✓ FAIL 在边界枚举上", ACCENT_GREEN),
        ("case_010", "DrivAer LES", "外流场 LES",
         "✗ 诚实 BLOCK · 缺时间目录", ACCENT_RED),
        ("case_009", "Sandia Flame D", "反应流低马赫 · 20 species",
         "✗ TBD-17 BLOCK · 命名不匹配", ACCENT_RED),
    ]
    y0 = 160
    row_h = 42
    for i, (case_id, eng, cn, verdict, color) in enumerate(rows):
        appear_t = 0.1 + i * 0.05
        r_alpha = ease_out_cubic(clamp((progress - appear_t) / 0.08))
        if r_alpha < 0.05:
            continue
        # slide in from left
        slide = lerp(-300, 0, r_alpha)
        y_row = y0 + i * row_h
        x_off = int(slide)
        # row background
        rounded_rect(d, [70 + x_off, y_row - 18,
                         W - 70 + x_off, y_row + 18], 8,
                     fill=(BG[0] + 10, BG[1] + 15, BG[2] + 25))
        # case_id
        d.text((90 + x_off, y_row - 13), case_id,
               font=font(15, "mono"), fill=ACCENT_CYAN)
        # English benchmark name
        d.text((220 + x_off, y_row - 13), eng,
               font=font(15, "mono"), fill=TEXT_SECONDARY)
        # CN regime
        d.text((420 + x_off, y_row - 11), cn,
               font=font(17, "zh"), fill=TEXT_PRIMARY)
        # verdict marker + text on right
        d.text((780 + x_off, y_row - 11), verdict,
               font=font(17, "zh_bold"), fill=color)

    # bottom: animated count-up summaries
    if progress > 0.75:
        cu_alpha = ease_out_cubic((progress - 0.75) / 0.15)
        cu_progress = ease_out_cubic(clamp((progress - 0.75) / 0.2))
        # 9 regimes
        cnt1 = int(round(lerp(0, 9, cu_progress)))
        # 427 tests
        cnt2 = int(round(lerp(374, 427, cu_progress)))
        # 21 commits
        cnt3 = int(round(lerp(0, 21, cu_progress)))
        text_centered(d, str(cnt1), font(48, "mono"), 640,
                      color=ACCENT_GOLD, alpha=cu_alpha, cx=240)
        text_centered(d, "物理域", font(18, "zh"), 670,
                      color=TEXT_SECONDARY, alpha=cu_alpha, cx=240)
        text_centered(d, str(cnt2), font(48, "mono"), 640,
                      color=ACCENT_CYAN, alpha=cu_alpha, cx=640)
        text_centered(d, "测试通过", font(18, "zh"), 670,
                      color=TEXT_SECONDARY, alpha=cu_alpha, cx=640)
        text_centered(d, str(cnt3), font(48, "mono"), 640,
                      color=ACCENT_GREEN, alpha=cu_alpha, cx=1040)
        text_centered(d, "提交合并", font(18, "zh"), 670,
                      color=TEXT_SECONDARY, alpha=cu_alpha, cx=1040)

    return img


def scene_real_screenshots(t_local, t_total):
    """2:25-3:15 · interleave 3 real screenshots with narration."""
    img, d = fresh_canvas()
    d.text((20, 14), "04 · 真实运行截图", font=font(14, "zh"),
           fill=TEXT_TERTIARY)

    progress = t_local / t_total

    # Three sub-scenes within
    shots = [
        (SHOTS / "shot_case027_ingest.png",
         "case_027 · 层流管流",
         "求解器收敛但引擎抓住了 mesh_contract 上一个 missing axis BC，照样返回 FAIL"),
        (SHOTS / "shot_case010_block.png",
         "case_010 · LES 外流场",
         "案例处于脚手架状态 · 没有时间目录 · 引擎诚实 BLOCK · 拒绝伪造 PASS"),
        (SHOTS / "shot_case021_live_block.png",
         "case_021 · NASA TMR · TBD-17 实战",
         "解析器找到 5 个残差字段但只有 1 个匹配 manifest 命名 · 围栏拒绝颁发 PASS"),
    ]

    seg = 1.0 / len(shots)
    for i, (path, cap_cn_top, cap_cn_bot) in enumerate(shots):
        seg_start = i * seg
        seg_end = (i + 1) * seg
        if progress < seg_start or progress > seg_end:
            continue
        local_t = (progress - seg_start) / seg

        # fade in 0-0.15, hold 0.15-0.85, fade out 0.85-1
        if local_t < 0.15:
            shot_alpha = ease_out_cubic(local_t / 0.15)
        elif local_t > 0.85:
            shot_alpha = ease_out_cubic((1.0 - local_t) / 0.15)
        else:
            shot_alpha = 1.0

        text_centered(d, cap_cn_top, font(28, "zh_bold"), 80,
                      color=ACCENT_GOLD, alpha=shot_alpha)
        paste_image(img, path, x=140, y=120, w=1000,
                    alpha=shot_alpha)
        text_centered(d, cap_cn_bot, font(22, "zh"), 680,
                      color=TEXT_PRIMARY, alpha=shot_alpha)

    return img


def scene_tbd17_hero(t_local, t_total):
    """3:15-4:00 · TBD-17 hero story · self-discovery + same-arc fix."""
    img, d = fresh_canvas()
    d.text((20, 14), "05 · 引擎自己抓住自己的 bug",
           font=font(14, "zh"), fill=TEXT_TERTIARY)

    progress = t_local / t_total

    # title fade
    title_alpha = ease_out_cubic(clamp(progress / 0.1))
    text_centered(d, "TBD-17", font(72, "mono"), 80,
                  color=ACCENT_RED, alpha=title_alpha)
    text_centered(d, "案例 009 · 火焰 D · 子门诚实自发现",
                  font(28, "zh_bold"), 130,
                  color=TEXT_PRIMARY, alpha=title_alpha)

    # 0.15-0.5: 27 fields → 3 fields animation
    if 0.15 <= progress < 0.55:
        a = ease_out_cubic((progress - 0.15) / 0.4)
        # left side: 27 boxes appear
        for j in range(27):
            jr, jc = divmod(j, 9)
            x = 130 + jc * 35
            y = 220 + jr * 35
            box = [x, y, x + 28, y + 28]
            if j < int(27 * a):
                rounded_rect(d, box, 5,
                             fill=(60, 90, 130) if j >= 3 else None,
                             outline=ACCENT_CYAN if j >= 3 else ACCENT_GOLD,
                             width=2)
            else:
                rounded_rect(d, box, 5, outline=TEXT_TERTIARY, width=1)
        d.text((130, 350), "manifest 声明 27 个目标字段",
               font=font(20, "zh"), fill=TEXT_PRIMARY)

        # right side: 3 matched
        if a > 0.5:
            mc_a = (a - 0.5) / 0.5
            for j in range(3):
                x = 780 + j * 60
                y = 230
                if mc_a * 3 > j:
                    rounded_rect(d, [x, y, x + 50, y + 50], 8,
                                 fill=(90, 40, 40),
                                 outline=ACCENT_RED, width=3)
                    draw_check(d, x + 25, y + 25, 26, color=ACCENT_RED,
                               width=3)
            d.text((780, 305), "解析器只识别 3 个",
                   font=font(20, "zh"), fill=ACCENT_RED)

        # arrow connecting
        if a > 0.8:
            draw_arrow(d, (480, 280), (740, 250),
                       color=ACCENT_GOLD, width=4, head=14)
            d.text((520, 200), "命名不匹配",
                   font=font(18, "zh_bold"), fill=ACCENT_GOLD)

    # 0.55-0.8: BLOCKED stamp slams down
    elif 0.55 <= progress < 0.85:
        # keep previous layout drawn briefly
        for j in range(27):
            jr, jc = divmod(j, 9)
            x = 130 + jc * 35
            y = 220 + jr * 35
            rounded_rect(d, [x, y, x + 28, y + 28], 5,
                         fill=(60, 90, 130) if j >= 3 else None,
                         outline=ACCENT_CYAN if j >= 3 else ACCENT_GOLD,
                         width=2)
        for j in range(3):
            x = 780 + j * 60
            y = 230
            rounded_rect(d, [x, y, x + 50, y + 50], 8,
                         fill=(90, 40, 40),
                         outline=ACCENT_RED, width=3)
            draw_check(d, x + 25, y + 25, 26, color=ACCENT_RED, width=3)
        d.text((130, 350), "manifest 声明 27 个目标字段",
               font=font(20, "zh"), fill=TEXT_PRIMARY)
        d.text((780, 305), "解析器只识别 3 个",
               font=font(20, "zh"), fill=ACCENT_RED)
        draw_arrow(d, (480, 280), (740, 250),
                   color=ACCENT_GOLD, width=4, head=14)

        # BLOCKED stamp
        stamp_t = ease_out_cubic((progress - 0.55) / 0.2)
        stamp_y = int(lerp(50, 470, stamp_t))
        stamp_box = [W // 2 - 220, stamp_y - 50,
                     W // 2 + 220, stamp_y + 50]
        rounded_rect(d, stamp_box, 12, outline=ACCENT_RED, width=5,
                     fill=(80, 30, 30))
        text_centered(d, "BLOCKED", font(56, "mono"), stamp_y,
                      color=ACCENT_RED)
        if progress > 0.7:
            text_centered(d, "围栏拒绝在证据不全时颁发 PASS",
                          font(22, "zh"), 560,
                          color=TEXT_PRIMARY)

    # 0.85-1.0: same-day fix · commit SHA
    elif progress >= 0.85:
        fix_a = ease_out_cubic((progress - 0.85) / 0.15)
        text_centered(d, "同一天发现 · 同一天修复",
                      font(36, "zh_bold"), 300,
                      color=ACCENT_GREEN, alpha=fix_a)
        text_centered(d, "commit  3b5c43f", font(48, "mono"), 380,
                      color=ACCENT_GOLD, alpha=fix_a)
        text_centered(d,
                      "incomplete_residual_coverage · "
                      "manifest target fields 必须全部匹配后才能 PASS",
                      font(20, "zh"), 460,
                      color=TEXT_SECONDARY, alpha=fix_a)
        # paste the hero plot small
        paste_image(img, PLOTS / "case_009" / "residual_plot.png",
                    x=240, y=500, w=800, alpha=fix_a)

    return img


def scene_closing(t_local, t_total):
    """4:00-4:30 · closing CTA."""
    img, d = fresh_canvas(bg=BG_DARK)

    progress = t_local / t_total

    # main title slides up
    title_t = ease_out_cubic(clamp(progress / 0.3))
    title_y = int(lerp(H, 200, title_t))
    text_centered(d, "诚实的 CFD 审计引擎",
                  font(54, "zh_bold"), title_y,
                  color=ACCENT_GOLD)

    if progress > 0.25:
        sub_a = ease_out_cubic((progress - 0.25) / 0.2)
        text_centered(d,
                      "9 个物理域 · 1 个自发现 bug · 同一弧修复",
                      font(28, "zh"), 280,
                      color=TEXT_PRIMARY, alpha=sub_a)

    # 5 fact bullets stagger in
    facts = [
        "9 个物理域端到端验证",
        "9/9 案例诚实围栏全部保持",
        "427 个测试通过 · 比起步 +53",
        "4 个 Accepted DEC 已同步 Notion",
        "子门自发现 + 同弧落地修复 (TBD-17)",
    ]
    for i, fact in enumerate(facts):
        appear_t = 0.4 + i * 0.07
        f_alpha = ease_out_cubic(clamp((progress - appear_t) / 0.1))
        if f_alpha < 0.05:
            continue
        y = 360 + i * 40
        draw_check(d, 380, y + 4, 22, color=ACCENT_GREEN, width=3)
        if f_alpha > 0.3:
            d.text((420, y - 12), fact,
                   font=font(22, "zh"),
                   fill=tuple(int(TEXT_PRIMARY[c] * f_alpha
                                  + BG_DARK[c] * (1 - f_alpha))
                              for c in range(3)))

    # bottom CTA
    if progress > 0.75:
        cta_a = ease_out_cubic((progress - 0.75) / 0.2)
        text_centered(d, "AI 顾问 = Claude Code · 读 V-series 死亡链 · 拒绝颁发不诚实的 PASS",
                      font(20, "zh"), H - 70,
                      color=ACCENT_CYAN, alpha=cta_a)

    return img


# ---- timeline -------------------------------------------------------------

TIMELINE = [
    (0.0, 12.0, scene_hook),
    (12.0, 35.0, scene_problem),
    (35.0, 75.0, scene_solution),
    (75.0, 145.0, scene_proof_matrix),
    (145.0, 195.0, scene_real_screenshots),
    (195.0, 240.0, scene_tbd17_hero),
    (240.0, 270.0, scene_closing),
]


def build_video():
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True)

    total_secs = TIMELINE[-1][1]
    total_frames = int(total_secs * FPS)
    print(f"[mg-cn] {total_secs:.1f}s · {total_frames} frames @ {FPS}fps")

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
            if frame_idx % 200 == 0:
                print(f"[mg-cn]   {frame_idx}/{total_frames}"
                      f" ({100 * frame_idx / total_frames:.0f}%)")

    print(f"[mg-cn] {frame_idx} frames rendered · encoding")
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
    print(f"[mg-cn] OUT {OUT_MP4} · {size_mb:.1f} MB")
    shutil.rmtree(FRAMES_DIR)


if __name__ == "__main__":
    build_video()

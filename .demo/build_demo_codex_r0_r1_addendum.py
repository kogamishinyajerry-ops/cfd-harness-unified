#!/usr/bin/env python3
"""Render Chinese MG addendum — Codex R0 → R1 honesty beat · 2026-05-22.

Standalone 45s addendum to the cycle-2 demo. Triggered when Codex 86gs
gpt-5.4 xhigh ran a cadence-floor review of the 32-commit M2.6 arc AFTER
the cycle-2 MP4 was already rendered, and returned CHANGES_REQUIRED with
2 P1 + 1 P2. All 3 findings closed in 1 round at commit b585cd9.

This is the cycle-2 equivalent of the cycle-1 TBD-17 self-discovery beat,
except now the snitch is Codex (independent reviewer) instead of dogfood-agent.

Structure (5 scenes · ~45s total):

  0:00-0:06  Hook        — "上线前最后一刻，Codex 又抓住 3 个漏网之鱼"
  0:06-0:18  Review In   — Codex review icon · CHANGES_REQUIRED verdict
  0:18-0:30  Findings    — 2 P1 + 1 P2 listed (Gap #36 / #37 / schema)
  0:30-0:38  Resolution  — 1 commit fixes all 3 · count-up 441 → 443
  0:38-0:45  Punchline   — "诚实是承诺"

Style consistent with .demo/build_demo_video_mg_cn_cycle2.py.

Run:  python3 .demo/build_demo_codex_r0_r1_addendum.py
Out:  .demo/cfdtrust_demo_mg_cn_2026-05-22_codex_r0_r1_addendum.mp4
"""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[1]
SHOTS_C2 = REPO_ROOT / ".demo" / "screenshots_cycle2"
OUT_MP4 = (REPO_ROOT / ".demo" /
           "cfdtrust_demo_mg_cn_2026-05-22_codex_r0_r1_addendum.mp4")
FRAMES_DIR = Path("/tmp/cfdtrust_addendum_codex_r0_frames")

W, H = 1280, 720
FPS = 24

# Color palette (matches cycle-2)
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
        if kind == "mono_bold":
            return ImageFont.truetype(MENLO, size, index=1)
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


def text_left(d, text, fnt, x, cy, color=TEXT_PRIMARY, alpha=1.0):
    _, h = text_size(d, text, fnt)
    if alpha < 1.0:
        color = tuple(int(c * alpha + bg * (1 - alpha))
                      for c, bg in zip(color, BG))
    d.text((x, cy - h // 2), text, font=fnt, fill=color)


def rounded_rect(d, box, radius, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline,
                        width=width)


def topbar(d, label):
    d.text((20, 14), label, font=font(14, "zh"), fill=TEXT_TERTIARY)


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


def count_up(value, t):
    """Animate integer count from 0 → value with ease-out-cubic."""
    return int(round(value * ease_out_cubic(t)))


# ---- scenes ---------------------------------------------------------------

def scene_hook(t_local, t_total):
    """0:00-0:06 · Hook."""
    img, d = fresh_canvas(BG_DARK)
    topbar(d, "cfd-harness-unified · 第二轮交付 · 上线前补遗 · 2026-05-22")
    progress = t_local / t_total

    # Subtle pulse for tension
    pulse_alpha = 0.4 + 0.3 * (math.sin(t_local * 4) + 1) / 2

    # Top eyebrow
    a0 = ease_out_cubic(clamp(progress / 0.2))
    text_centered(d, "ADDENDUM · post-cycle-2 · Codex review",
                  font(15, "mono"), 130,
                  color=ACCENT_PURPLE, alpha=a0)

    # Hook text · large
    a1 = ease_out_cubic(clamp((progress - 0.1) / 0.25))
    text_centered(d, "上线前最后一刻",
                  font(58, "zh_bold"), 270,
                  color=TEXT_PRIMARY, alpha=a1)

    a2 = ease_out_cubic(clamp((progress - 0.30) / 0.25))
    text_centered(d, "Codex 又抓住 3 个漏网之鱼",
                  font(46, "zh_bold"), 360,
                  color=ACCENT_RED, alpha=a2)

    # Small red dot pulsing under the headline
    if progress > 0.4:
        cy = 430
        r = 6 + int(2 * pulse_alpha * 4)
        d.ellipse([W // 2 - r, cy - r, W // 2 + r, cy + r],
                  fill=ACCENT_RED)

    # Subline
    a3 = ease_out_cubic(clamp((progress - 0.55) / 0.3))
    text_centered(d, "32-commit M2.6 弧 · cadence-floor review · 86gs gpt-5.4 xhigh",
                  font(18, "zh"), 510,
                  color=TEXT_SECONDARY, alpha=a3)

    a4 = ease_out_cubic(clamp((progress - 0.7) / 0.3))
    text_centered(d, "cycle-2 video 渲完之后才跑的独立审查",
                  font(16, "zh"), 555,
                  color=TEXT_TERTIARY, alpha=a4)

    return img


def scene_review_in(t_local, t_total):
    """0:06-0:18 · Codex review icon + CHANGES_REQUIRED verdict."""
    img, d = fresh_canvas()
    topbar(d, "Codex 86gs gpt-5.4 xhigh · 独立第二意见")
    progress = t_local / t_total

    # Center icon: stylized "review" badge
    cx_icon, cy_icon = W // 2, 220
    icon_a = ease_out_cubic(clamp(progress / 0.25))
    icon_r = int(60 * icon_a)
    rounded_rect(d, [cx_icon - icon_r, cy_icon - icon_r,
                     cx_icon + icon_r, cy_icon + icon_r],
                 radius=12,
                 outline=ACCENT_PURPLE, width=3,
                 fill=tuple(int(c * 0.15 + b * 0.85)
                            for c, b in zip(ACCENT_PURPLE, BG_DARK)))
    if icon_a > 0.6:
        text_centered(d, "Codex", font(22, "zh_bold"), cy_icon - 12,
                      color=ACCENT_PURPLE)
        text_centered(d, "R0", font(20, "mono_bold"), cy_icon + 14,
                      color=ACCENT_PURPLE)

    # Verdict text · staged reveal
    a1 = ease_out_cubic(clamp((progress - 0.3) / 0.2))
    text_centered(d, "▼ 审查结果",
                  font(22, "zh"), 350,
                  color=TEXT_SECONDARY, alpha=a1)

    a2 = ease_out_cubic(clamp((progress - 0.45) / 0.25))
    # Red verdict badge with stamp effect
    verdict_w, verdict_h = 480, 80
    vx, vy = W // 2 - verdict_w // 2, 390
    scale = lerp(1.15, 1.0, ease_out_cubic(clamp((progress - 0.45) / 0.2)))
    if a2 > 0.05:
        vw_s = int(verdict_w * scale)
        vh_s = int(verdict_h * scale)
        vx_s = W // 2 - vw_s // 2
        vy_s = 390 - (vh_s - verdict_h) // 2
        rounded_rect(d, [vx_s, vy_s, vx_s + vw_s, vy_s + vh_s], 8,
                     outline=ACCENT_RED, width=3,
                     fill=tuple(int(c * 0.20 + b * 0.80)
                                for c, b in zip(ACCENT_RED, BG_DARK)))
        text_centered(d, "CHANGES_REQUIRED",
                      font(34, "mono_bold"), 430,
                      color=ACCENT_RED, alpha=a2)

    # Counter underneath
    a3 = ease_out_cubic(clamp((progress - 0.65) / 0.25))
    p1_count = count_up(2, clamp((progress - 0.65) / 0.2))
    p2_count = count_up(1, clamp((progress - 0.72) / 0.2))
    text_centered(d, f"P1 × {p1_count}      P2 × {p2_count}",
                  font(28, "mono"), 525,
                  color=ACCENT_RED if a3 > 0.5 else TEXT_TERTIARY,
                  alpha=a3)

    a4 = ease_out_cubic(clamp((progress - 0.8) / 0.2))
    text_centered(d, "都集中在 cycle-2 cycle-1 修复的衔接处",
                  font(18, "zh"), 580,
                  color=TEXT_SECONDARY, alpha=a4)
    text_centered(d, "(blast radius 已知 · 同弧可修)",
                  font(16, "zh"), 612,
                  color=TEXT_TERTIARY, alpha=a4)

    return img


def scene_findings(t_local, t_total):
    """0:18-0:30 · 3 findings listed."""
    img, d = fresh_canvas()
    topbar(d, "3 个 finding · 引擎说 cycle-2 修复不全")
    progress = t_local / t_total

    text_centered(d, "Codex 抓出的 3 个漏",
                  font(28, "zh_bold"), 80,
                  color=ACCENT_PURPLE,
                  alpha=ease_out_cubic(clamp(progress / 0.15)))

    findings = [
        (ACCENT_RED, "P1", "Gap #36",
         "多区 CHT · 0.orig 布局",
         "_detect_multi_region_layout() 只看 0/ · case_011 漏",
         "openfoam.py:1611-1613"),
        (ACCENT_RED, "P1", "Gap #37",
         "step-numbered logs",
         "log_v64_v3/02_rhoSimpleFoam.log · case_006 production",
         "openfoam.py:2341-2345"),
        (ACCENT_GOLD, "P2", "schema",
         "turbulence_fields 必填",
         "Gap #31 model-derived 在 CLI 路径上不可达",
         "case_manifest.schema.json"),
    ]

    for i, (col, sev, gap, title_zh, detail_zh, path_en) in enumerate(findings):
        appear_t = 0.18 + i * 0.20
        a = ease_out_cubic(clamp((progress - appear_t) / 0.15))
        if a < 0.05:
            continue
        y = 150 + i * 150
        x_slide = lerp(-40, 0, a)
        # Severity badge
        bx, by = 60 + int(x_slide), y
        rounded_rect(d, [bx, by, bx + 70, by + 36], 4,
                     fill=tuple(int(c * 0.22 + b * 0.78)
                                for c, b in zip(col, BG_DARK)),
                     outline=col, width=2)
        text_left(d, sev, font(20, "mono_bold"), bx + 16, by + 18,
                  color=col, alpha=a)
        # Gap tag
        text_left(d, gap, font(20, "mono"), bx + 90, by + 8,
                  color=col, alpha=a)
        # Chinese title
        text_left(d, title_zh, font(22, "zh_bold"),
                  bx + 230, by + 8,
                  color=TEXT_PRIMARY, alpha=a)
        # Detail (Chinese + mono path snippet)
        if a > 0.5:
            a2 = ease_out_cubic(clamp((progress - appear_t - 0.05) / 0.15))
            text_left(d, detail_zh, font(16, "zh"),
                      bx + 90, by + 56,
                      color=TEXT_SECONDARY, alpha=a2)
            text_left(d, path_en, font(13, "mono"),
                      bx + 90, by + 92,
                      color=TEXT_TERTIARY, alpha=a2)

    # Bottom: tagline
    if progress > 0.85:
        a = ease_out_cubic((progress - 0.85) / 0.15)
        text_centered(d, "三处都在 cycle-2 修复的衔接处 · 引擎被引擎拍肩",
                      font(18, "zh"), H - 50,
                      color=ACCENT_PURPLE, alpha=a)

    return img


def scene_resolution(t_local, t_total):
    """0:30-0:38 · 1 commit fixes all 3 · count-up 441 → 443."""
    img, d = fresh_canvas()
    topbar(d, "R0 → R1 · 1 commit · 1 round · 0 escalation")
    progress = t_local / t_total

    # Eyebrow
    a0 = ease_out_cubic(clamp(progress / 0.15))
    text_centered(d, "解决方案",
                  font(22, "zh"), 80,
                  color=TEXT_SECONDARY, alpha=a0)

    # Big arrow row: 3 findings → 1 commit → R1 APPROVE
    a1 = ease_out_cubic(clamp((progress - 0.15) / 0.2))

    # Left card: 3 findings
    bx1 = 80
    rounded_rect(d, [bx1, 160, bx1 + 280, 320], 12,
                 outline=ACCENT_RED, width=2,
                 fill=tuple(int(c * 0.15 + b * 0.85)
                            for c, b in zip(ACCENT_RED, BG_DARK)))
    if a1 > 0.5:
        text_centered(d, "3 findings",
                      font(22, "zh_bold"), 190,
                      color=ACCENT_RED, cx=bx1 + 140)
        text_centered(d, "(2 P1 + 1 P2)",
                      font(16, "mono"), 220,
                      color=TEXT_SECONDARY, cx=bx1 + 140)
        text_centered(d, "Gap #36",
                      font(15, "mono"), 250,
                      color=TEXT_PRIMARY, cx=bx1 + 140)
        text_centered(d, "Gap #37",
                      font(15, "mono"), 272,
                      color=TEXT_PRIMARY, cx=bx1 + 140)
        text_centered(d, "schema relax",
                      font(15, "mono"), 294,
                      color=TEXT_PRIMARY, cx=bx1 + 140)

    # Middle: arrow + commit SHA
    a2 = ease_out_cubic(clamp((progress - 0.30) / 0.2))
    if a2 > 0.05:
        # arrow
        ax1, ax2 = bx1 + 290, 540
        d.line([(ax1, 240), (ax2, 240)],
               fill=ACCENT_GOLD, width=3)
        d.polygon([(ax2, 240), (ax2 - 14, 232), (ax2 - 14, 248)],
                  fill=ACCENT_GOLD)
        text_centered(d, "b585cd9",
                      font(20, "mono_bold"), 215,
                      color=ACCENT_GOLD, cx=(ax1 + ax2) // 2)
        text_centered(d, "1 commit",
                      font(16, "zh"), 265,
                      color=TEXT_PRIMARY, cx=(ax1 + ax2) // 2)

    # Right card: R1 APPROVE
    a3 = ease_out_cubic(clamp((progress - 0.45) / 0.2))
    bx3 = 580
    if a3 > 0.05:
        rounded_rect(d, [bx3, 160, bx3 + 280, 320], 12,
                     outline=ACCENT_GREEN, width=2,
                     fill=tuple(int(c * 0.15 + b * 0.85)
                                for c, b in zip(ACCENT_GREEN, BG_DARK)))
        if a3 > 0.5:
            text_centered(d, "R1 RESOLVED",
                          font(22, "zh_bold"), 190,
                          color=ACCENT_GREEN, cx=bx3 + 140)
            text_centered(d, "all 3 closed",
                          font(16, "mono"), 220,
                          color=TEXT_SECONDARY, cx=bx3 + 140)
            text_centered(d, "1 round",
                          font(15, "mono"), 250,
                          color=TEXT_PRIMARY, cx=bx3 + 140)
            text_centered(d, "cap=3 used 1",
                          font(15, "mono"), 272,
                          color=TEXT_PRIMARY, cx=bx3 + 140)
            text_centered(d, "+ 2 regression tests",
                          font(14, "mono"), 294,
                          color=ACCENT_GREEN, cx=bx3 + 140)

    # Bottom: count-up 441 → 443
    a4 = ease_out_cubic(clamp((progress - 0.60) / 0.3))
    if a4 > 0.05:
        # animate the right number from 441 to 443
        cur = 441 + int(round(2 * ease_out_cubic(
            clamp((progress - 0.60) / 0.3))))
        text_centered(d, "tests:",
                      font(22, "zh"), 410,
                      color=TEXT_SECONDARY,
                      cx=W // 2 - 140, alpha=a4)
        text_centered(d, "441",
                      font(60, "mono"), 440,
                      color=TEXT_TERTIARY,
                      cx=W // 2 - 50, alpha=a4)
        # arrow
        d.line([(W // 2 - 5, 440), (W // 2 + 60, 440)],
               fill=ACCENT_GOLD, width=3)
        d.polygon([(W // 2 + 60, 440),
                   (W // 2 + 46, 432), (W // 2 + 46, 448)],
                  fill=ACCENT_GOLD)
        text_centered(d, f"{cur}",
                      font(60, "mono_bold"), 440,
                      color=ACCENT_GREEN, cx=W // 2 + 130, alpha=a4)
        text_centered(d, "passed",
                      font(22, "zh"), 410,
                      color=TEXT_SECONDARY,
                      cx=W // 2 + 240, alpha=a4)

    # Tagline at bottom
    if progress > 0.85:
        a = ease_out_cubic((progress - 0.85) / 0.15)
        text_centered(d, "Codex round cap = 3 · 用了 1 · 剩 2 没用",
                      font(18, "zh"), H - 80,
                      color=TEXT_SECONDARY, alpha=a)
        text_centered(d, "per DEC-V61-133 · v2.3 治理简化",
                      font(15, "zh"), H - 50,
                      color=TEXT_TERTIARY, alpha=a)

    return img


def scene_punchline(t_local, t_total):
    """0:38-0:45 · Closing CTA."""
    img, d = fresh_canvas(BG_DARK)
    topbar(d, "cfd-harness-unified · 诚实是承诺")
    progress = t_local / t_total

    # Big honesty headline
    a1 = ease_out_cubic(clamp(progress / 0.25))
    text_centered(d, "引擎再一次被引擎抓住",
                  font(40, "zh_bold"), 230,
                  color=ACCENT_GOLD, alpha=a1)

    # Stat strip · 3 numbers
    a2 = ease_out_cubic(clamp((progress - 0.20) / 0.30))
    if a2 > 0.05:
        stats = [
            ("3", "finding", ACCENT_RED),
            ("1", "commit", ACCENT_GOLD),
            ("1", "round", ACCENT_GREEN),
        ]
        for i, (num, label, col) in enumerate(stats):
            cx = 300 + i * 340
            cy = 380
            scale = lerp(0.6, 1.0, a2)
            cw = int(220 * scale)
            ch = int(140 * scale)
            box = [cx - cw // 2, cy - ch // 2,
                   cx + cw // 2, cy + ch // 2]
            rounded_rect(d, box, 14,
                         outline=col, width=2,
                         fill=tuple(int(c * 0.18 + b * 0.82)
                                    for c, b in zip(col, BG_DARK)))
            if a2 > 0.4:
                text_centered(d, num, font(64, "mono_bold"), cy - 14,
                              color=col, cx=cx)
                text_centered(d, label, font(17, "zh"), cy + 40,
                              color=TEXT_PRIMARY, cx=cx)

    # Punchline
    a3 = ease_out_cubic(clamp((progress - 0.55) / 0.30))
    text_centered(d, "诚实是承诺",
                  font(38, "zh_bold"), 540,
                  color=ACCENT_CYAN, alpha=a3)

    a4 = ease_out_cubic(clamp((progress - 0.75) / 0.25))
    text_centered(d, "(443 tests passed · 0 false PASS · cycle-2 SHIP 保留)",
                  font(15, "zh"), 595,
                  color=TEXT_TERTIARY, alpha=a4)

    return img


# ---- timeline -------------------------------------------------------------

TIMELINE = [
    (0.0,   6.0,  scene_hook),
    (6.0,   18.0, scene_review_in),
    (18.0,  30.0, scene_findings),
    (30.0,  38.0, scene_resolution),
    (38.0,  45.0, scene_punchline),
]


def build_video():
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True)

    total_secs = TIMELINE[-1][1]
    total_frames = int(total_secs * FPS)
    print(f"[addendum] {total_secs:.1f}s · {total_frames} frames @ {FPS}fps")

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
            if frame_idx % 120 == 0:
                print(f"[addendum]   {frame_idx}/{total_frames}"
                      f" ({100 * frame_idx / total_frames:.0f}%)")

    print(f"[addendum] {frame_idx} frames rendered · encoding")
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
    print(f"[addendum] OUT {OUT_MP4} · {size_mb:.1f} MB")
    shutil.rmtree(FRAMES_DIR)


if __name__ == "__main__":
    build_video()

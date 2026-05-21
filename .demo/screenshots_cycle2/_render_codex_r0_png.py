#!/usr/bin/env python3
"""Render the real Codex R0 review output as a terminal-styled PNG.

Source text: /private/tmp/claude-502/-Users-Zhuanz/f221ca55-9038-4935-af35-d16693030ff7/tasks/bz3oof9ba.output
First ~80 lines are the actual Codex 86gs gpt-5.4 xhigh review verdict for
the 32-commit M2.6 cycle-2 arc. Used as MG illustration cut in the
Codex-R0-R1 addendum video (cfdtrust_demo_mg_cn_2026-05-22_codex_r0_r1_addendum.mp4).

Output: shot_codex_r0_resolved.png (1280x720)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent

W, H = 1280, 720
BG = (22, 24, 28)
FG = (220, 220, 220)
DIM = (140, 140, 150)
AMBER = (240, 198, 116)
GREEN = (165, 200, 130)
RED = (255, 107, 107)
CYAN = (110, 193, 228)
BLUE = (130, 160, 220)
PURPLE = (200, 150, 240)

MENLO = "/System/Library/Fonts/Menlo.ttc"
PINGFANG = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
            "86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/"
            "AssetData/PingFang.ttc")


def fmono(sz, bold=False):
    return ImageFont.truetype(MENLO, sz, index=1 if bold else 0)


def fzh(sz, bold=False):
    try:
        return ImageFont.truetype(PINGFANG, sz, index=4 if bold else 0)
    except Exception:
        return ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", sz)


def render():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Title bar
    d.rectangle([0, 0, W, 32], fill=(14, 16, 22))
    d.line([(0, 32), (W, 32)], fill=(50, 60, 80), width=1)
    d.text((16, 7), "● ● ●", font=fmono(13), fill=DIM)
    d.text((80, 7), "Codex R0 · cadence-floor review · 32-commit arc",
           font=fzh(14, bold=True), fill=FG)
    d.text((W - 360, 9), "86gs · gpt-5.4 xhigh · 2026-05-22",
           font=fmono(11), fill=DIM)

    # Verdict header
    y = 50
    d.text((40, y), "$ codex-review-relay --base origin/main",
           font=fmono(15), fill=CYAN)
    y += 30
    d.text((40, y), "▼ Verdict:", font=fmono(15, bold=True), fill=FG)
    d.text((150, y), "CHANGES_REQUIRED", font=fmono(15, bold=True), fill=RED)
    y += 26
    d.text((40, y),
           "  (2 P1 + 1 P2 · same-arc fixable · round cap=3, used 1)",
           font=fmono(13), fill=DIM)
    y += 30

    # Headline quote (from real review text)
    headline = [
        "Several of the new ingest/BC fixes are incomplete in the real",
        "layouts they target: multi-region 0.orig cases and numbered logs",
        "under log_* dirs still fail, and the new turbulence-field",
        "derivation cannot be reached through normal manifest validation.",
    ]
    for line in headline:
        d.text((40, y), line, font=fmono(14), fill=FG)
        y += 21
    y += 14

    # P1-1
    d.text((40, y), "- [P1]", font=fmono(14, bold=True), fill=RED)
    d.text((100, y), "Handle 0.orig multi-region layouts in BC collection",
           font=fmono(14), fill=FG)
    y += 21
    d.text((60, y),
           "openfoam.py:1611-1613  ·  CHT case_011 falls through to single-region",
           font=fmono(12), fill=DIM)
    y += 26

    # P1-2
    d.text((40, y), "- [P1]", font=fmono(14, bold=True), fill=RED)
    d.text((100, y), "Match numbered logs inside log_* ingest subdirs",
           font=fmono(14), fill=FG)
    y += 21
    d.text((60, y),
           "openfoam.py:2341-2345  ·  case_006 log_v64_v3/02_rhoSimpleFoam.log missed",
           font=fmono(12), fill=DIM)
    y += 26

    # P2
    d.text((40, y), "- [P2]", font=fmono(14, bold=True), fill=AMBER)
    d.text((100, y), "Relax manifest validation for derived turbulence fields",
           font=fmono(14), fill=FG)
    y += 21
    d.text((60, y),
           "openfoam.py:1660-1665  ·  schema blocks Gap #31 fallback from CLI",
           font=fmono(12), fill=DIM)
    y += 36

    # Right-side annotation box (Chinese)
    box = [880, 80, 1240, 410]
    d.rectangle(box, outline=AMBER, width=2)
    d.text((895, 92), "引擎被引擎抓住", font=fzh(20, bold=True), fill=AMBER)
    notes_zh = [
        "Codex 86gs gpt-5.4 xhigh",
        "对 32-commit M2.6 弧",
        "独立 cadence-floor 审查",
        "",
        "查出 cycle-2 修复 fix 不全：",
        "• 0.orig 多区 CHT 漏",
        "• 编号 log 子目录漏",
        "• schema 把 Gap #31 锁死",
        "",
        "→ 同弧可修",
        "→ blast radius 已知",
        "→ 不允许 demo 上线",
    ]
    yn = 130
    for n in notes_zh:
        d.text((895, yn), n, font=fzh(15), fill=FG if n else FG)
        yn += 22

    # Bottom: resolution banner
    by = H - 110
    d.rectangle([0, by, W, H], fill=(8, 18, 12))
    d.line([(0, by), (W, by)], fill=GREEN, width=2)
    d.text((40, by + 14),
           "→ R1 RESOLVED at commit b585cd9 · 1 round · 0 escalation",
           font=fmono(16, bold=True), fill=GREEN)
    d.text((40, by + 42),
           "  443 tests passed (was 441) · 2 regression tests added",
           font=fmono(13), fill=FG)
    d.text((40, by + 66),
           "  Codex round cap=3 (per DEC-V61-133) · used 1 · 2 unused",
           font=fmono(13), fill=DIM)

    out = OUT / "shot_codex_r0_resolved.png"
    img.save(out, optimize=True)
    print(f"[shot] {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    render()

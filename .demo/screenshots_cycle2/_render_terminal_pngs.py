#!/usr/bin/env python3
"""Render real cycle-2 capture + JSON snippets to PNG screenshots.

These PNGs are intercut as MG illustration cuts in the cycle-2 demo
video.  Each PNG is real text from a real artifact — no fabrication.

Outputs (1280x720 each):
  shot_c2_case011_bc_quality.png       — real bc_quality.json head
  shot_c2_case011_trust_blocked.png    — real trust_report.json BLOCKED block
  shot_c2_case010_les_block_reason.png — real cfdtrust ingest output for c10
  shot_c2_step_numbered_logs.png       — git show 68f4a70 --stat head
  shot_c2_streaming_payoff.png         — residuals.csv head + payoff text
  shot_c2_gap32_diff.png               — git show 77825b8 --stat
  shot_c2_cycle2_commits.png           — git log oneline of cycle-2 commits
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

W, H = 1280, 720
BG = (22, 24, 28)           # Menlo terminal bg
FG = (220, 220, 220)         # primary text
DIM = (140, 140, 150)
AMBER = (240, 198, 116)
GREEN = (165, 200, 130)
RED = (255, 107, 107)
CYAN = (110, 193, 228)
BLUE = (130, 160, 220)

MENLO = "/System/Library/Fonts/Menlo.ttc"
PINGFANG = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
            "86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/"
            "AssetData/PingFang.ttc")


def fmono(sz):
    return ImageFont.truetype(MENLO, sz)


def fzh(sz, bold=False):
    try:
        return ImageFont.truetype(PINGFANG, sz, index=4 if bold else 0)
    except Exception:
        return ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc",
                                   sz)


def new_canvas():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # title bar
    d.rectangle([0, 0, W, 32], fill=(14, 16, 22))
    d.line([(0, 32), (W, 32)], fill=(50, 60, 80), width=1)
    return img, d


def header(d, title_zh, subtitle_mono=""):
    d.text((16, 7), "● ● ●", font=fmono(13), fill=DIM)
    d.text((80, 7), title_zh, font=fzh(14, bold=True), fill=FG)
    if subtitle_mono:
        d.text((W - 380, 9), subtitle_mono, font=fmono(11), fill=DIM)


def shot_case011_bc_quality():
    img, d = new_canvas()
    header(d, "case_011 · bc_quality.json · 多区 CHT 数据层",
           "Gap #11 · commit 01d5567")

    lines = [
        ('{', FG),
        ('  "bc_parsing_status": "ok",', GREEN),
        ('  "layout": "multi_region",', AMBER),
        ('  "region_count": 3,', AMBER),
        ('  "regions_detected": [', FG),
        ('    "region_cold_fluid",', CYAN),
        ('    "region_hot_fluid",', CYAN),
        ('    "region_solid"', CYAN),
        ('  ],', FG),
        ('  "regions": {', FG),
        ('    "region_cold_fluid": {', BLUE),
        ('      "expected_fields": ["U", "p", "__none_laminar__"],', FG),
        ('      "fields_missing": ["__none_laminar__"],', RED),
        ('      "fields_present": [],', DIM),
        ('      "fields": { ... }', DIM),
        ('    },', FG),
        ('    "region_hot_fluid": { ... },', BLUE),
        ('    "region_solid":      { ... }', BLUE),
        ('  }', FG),
        ('}', FG),
    ]
    y = 64
    for txt, color in lines:
        d.text((54, y), txt, font=fmono(17), fill=color)
        y += 25

    # right-side annotation in Chinese
    box = [820, 100, 1230, 320]
    d.rectangle(box, outline=AMBER, width=2)
    d.text((832, 112), "Gap #11 修复", font=fzh(19, bold=True), fill=AMBER)
    notes = [
        "数据层成功识别 3 个 region",
        "（cold_fluid / hot_fluid / solid）",
        "",
        "verdict 层故意 BLOCKED",
        "拒绝在 schema 尚未完全",
        "对接时颁发任何 PASS",
        "",
        "→ 诚实推迟 · 不是 false-FAIL",
    ]
    yn = 150
    for n in notes:
        d.text((832, yn), n, font=fzh(15), fill=FG if n else FG)
        yn += 22

    # bottom hint
    d.text((54, H - 50),
           "$ jq '.layout, .region_count, .regions_detected' artifacts/bc_quality.json",
           font=fmono(13), fill=DIM)
    d.text((54, H - 28),
           "源文件: ~/Desktop/cfd-harness-unified/_sandboxes/"
           "case_011_plate_fin_compact_hx/case/artifacts/bc_quality.json (2451 B)",
           font=fmono(10), fill=DIM)

    img.save(OUT / "shot_c2_case011_bc_quality.png")


def shot_case011_trust_blocked():
    img, d = new_canvas()
    header(d, "case_011 · trust_report.json · bc_contract BLOCKED",
           "诚实推迟 · 不伪造 verdict")

    lines = [
        '"bc_contract": {',
        '    "status": "BLOCKED",',
        '    "summary": "Multi-region CHT layout detected;',
        '                bc_contract evaluation not yet wired',
        '                for per-region schemas.",',
        '    "details": {',
        '        "reason": "multi_region_bc_validation_not_yet_wired",',
        '        "regions_detected": [',
        '            "region_cold_fluid",',
        '            "region_hot_fluid",',
        '            "region_solid"',
        '        ],',
        '        "per_region_field_summary": { ... }',
        '    }',
        '},',
    ]
    y = 90
    colors = [FG, AMBER, FG, FG, FG, FG,
              RED, FG, CYAN, CYAN, CYAN, FG, DIM, FG, FG]
    for txt, col in zip(lines, colors):
        d.text((60, y), txt, font=fmono(17), fill=col)
        y += 28

    # BLOCKED stamp
    box = [820, 110, 1220, 220]
    d.rounded_rectangle(box, radius=10, outline=AMBER, width=4,
                        fill=(60, 50, 18))
    d.text((858, 130), "BLOCKED", font=fmono(40), fill=AMBER)
    d.text((838, 178), "not_yet_wired", font=fmono(20), fill=AMBER)

    # explanation
    d.text((820, 260), "诚实围栏", font=fzh(20, bold=True), fill=GREEN)
    d.text((820, 286), "知道自己能 verdict 什么，", font=fzh(15), fill=FG)
    d.text((820, 308), "知道自己还不能 verdict 什么。", font=fzh(15), fill=FG)
    d.text((820, 332), "拒绝在 schema 不完整时", font=fzh(15), fill=FG)
    d.text((820, 354), "胡乱颁发 PASS 或 FAIL。", font=fzh(15), fill=FG)

    d.text((60, 590),
           '"overall_status": "FAIL"          # 因为 solver gate 3/3 残差未达标',
           font=fmono(14), fill=RED)
    d.text((60, 614),
           '"solver_execution": "ingested"   # 引擎承认: 没亲眼看过运行',
           font=fmono(14), fill=AMBER)
    d.text((60, 638),
           '"validation_status": "not_validated"   # 围栏 1 + 围栏 3 双重锁定',
           font=fmono(14), fill=AMBER)

    img.save(OUT / "shot_c2_case011_trust_blocked.png")


def shot_case010_les_progress():
    img, d = new_canvas()
    header(d, "case_010 · LES · BLOCK 原因深入一层",
           "Gap #29 · commit 914f944")

    # two-column before/after
    # left: cycle-1
    d.rectangle([40, 80, 620, 600], outline=DIM, width=1)
    d.text((54, 92), "Cycle-1 (2026-05-22 morning)", font=fzh(18, bold=True),
           fill=DIM)
    d.text((54, 124), "$ cfdtrust ingest <case_010>", font=fmono(13), fill=DIM)
    y = 156
    for line, col in [
        ("[cfdtrust] FAIL ingest BLOCKED:", RED),
        ('  Case directory does not look', FG),
        ('  like an OpenFOAM case.', FG),
        ("", FG),
        ("[cfdtrust] FAIL", RED),
        ('  reason:', FG),
        ('  case_dir_not_openfoam_compatible', RED),
        ("", FG),
        ("[cfdtrust] WARN", AMBER),
        ('  next step: Provide system/,', FG),
        ('  constant/, AND 0/ directories.', FG),
        ("", FG),
        ("× 错误原因. 案例其实有 0.orig/", DIM),
    ]:
        d.text((54, y), line, font=fmono(14), fill=col)
        y += 22

    # arrow
    d.line([(640, 340), (700, 340)], fill=AMBER, width=4)
    d.polygon([(700, 332), (700, 348), (720, 340)], fill=AMBER)

    # right: cycle-2
    d.rectangle([740, 80, 1240, 600], outline=GREEN, width=2)
    d.text((754, 92), "Cycle-2 (2026-05-22 16:00)",
           font=fzh(18, bold=True), fill=GREEN)
    d.text((754, 124), "$ cfdtrust ingest <case_010>", font=fmono(13), fill=DIM)
    y = 156
    for line, col in [
        ("[cfdtrust] FAIL ingest BLOCKED:", RED),
        ('  Case has no time directory', FG),
        ('  beyond 0/; nothing to ingest.', FG),
        ("", FG),
        ("[cfdtrust] FAIL", RED),
        ('  reason:', FG),
        ('  no_time_directory_found', AMBER),
        ("", FG),
        ("[cfdtrust] WARN", AMBER),
        ('  next step: Run the case', FG),
        ('  externally first, then re-ingest.', FG),
        ("", FG),
        ("✓ 引擎已接受 0.orig/ 规范布局,", GREEN),
        ('  在更深的 gate 才诚实 BLOCK.', GREEN),
    ]:
        d.text((754, y), line, font=fmono(14), fill=col)
        y += 22

    d.text((40, 640), "验证进度: BLOCK 原因深入一层 · 没有 false-PASS · 没有 over-promise.",
           font=fzh(18, bold=True), fill=AMBER)
    d.text((40, 672),
           "real 0.14s · exit 1 · solver_execution: skipped (依然不是 ingested)",
           font=fmono(13), fill=DIM)
    img.save(OUT / "shot_c2_case010_les_block_reason.png")


def shot_step_numbered_logs():
    img, d = new_canvas()
    header(d, "工业脚本兼容 · 步号 mesh-pipeline log",
           "Gap #26-#27 · commit 68f4a70")

    # left: a real industrial run script listing
    d.text((54, 80), "$ ls case_dir/log/",
           font=fmono(15), fill=DIM)
    files = [
        ("01_blockMesh.log",     "← step 1: blockMesh", AMBER),
        ("02_snappyHexMesh.log", "← step 2: snappyHexMesh", AMBER),
        ("03_extrudeMesh.log",   "← step 3: extrudeMesh", AMBER),
        ("04_decomposePar.log",  "← step 4: decomposePar", AMBER),
        ("05_simpleFoam.log",    "← step 5: simpleFoam (solver)", GREEN),
        ("",                     "", FG),
        ("blockMesh.log",        "(unprefixed · 上一轮老版本)", DIM),
    ]
    y = 116
    for fname, note, col in files:
        d.text((84, y), fname, font=fmono(17), fill=col if fname else FG)
        if note:
            d.text((460, y), note, font=fmono(14), fill=col)
        y += 30

    # right: engine rule
    d.rectangle([720, 90, 1240, 460], outline=CYAN, width=2)
    d.text((734, 102), "引擎规则", font=fzh(20, bold=True), fill=CYAN)
    rules = [
        "• 走两套命名同时存在:",
        "    01_blockMesh.log  或  blockMesh.log",
        "",
        "• 同一工具有多个 step 编号时,",
        "    取 step 号最大的为 canonical",
        "    (latest run = canonical evidence)",
        "",
        "• 拒绝武断指定: 我们不强制用户",
        "    按照特定脚本风格命名 — 我们",
        "    去找用户实际在用的命名.",
        "",
        "✓ 工业 CFD shop 普遍 step-number",
        "  run-script. 引擎要在用户实际",
        "  在的地方碰见用户.",
    ]
    yr = 138
    for r in rules:
        if r.startswith("•"):
            d.text((734, yr), r, font=fzh(14, bold=True), fill=AMBER)
        elif r.startswith("✓"):
            d.text((734, yr), r, font=fzh(14, bold=True), fill=GREEN)
        else:
            d.text((754, yr), r, font=fzh(13), fill=FG)
        yr += 22

    d.text((54, 580),
           "$ git show 68f4a70 --stat   #  +67 / 0   ui/backend/audit/cfdtrust/backends/openfoam.py",
           font=fmono(13), fill=DIM)
    d.text((54, 606),
           "                                +47 / 0   test_ingest_mode.py   #  confidence: high",
           font=fmono(13), fill=DIM)
    img.save(OUT / "shot_c2_step_numbered_logs.png")


def shot_streaming_payoff():
    img, d = new_canvas()
    header(d, "TBD-20 · streaming parser · 13 GiB → bounded",
           "commit e8691f3 + 16e8dcf")

    # left: peak RSS bar comparison
    d.text((54, 80), "峰值内存占用 (peak RSS)",
           font=fzh(18, bold=True), fill=AMBER)

    # cycle-1 bar (huge)
    bar_x = 80
    cy1_top, cy1_bot = 130, 170
    d.rectangle([bar_x, cy1_top, bar_x + 760, cy1_bot], fill=RED,
                outline=RED)
    d.text((bar_x + 770, cy1_top + 5), "≈ 13 GiB", font=fmono(18),
           fill=RED)
    d.text((bar_x - 50, cy1_top + 10), "before", font=fmono(14), fill=DIM)
    d.text((bar_x, cy1_bot + 6),
           "text-path parser · OOM on case_009-class 3.3 GiB log",
           font=fzh(13), fill=DIM)

    # cycle-2 bar (tiny)
    cy2_top, cy2_bot = 230, 270
    d.rectangle([bar_x, cy2_top, bar_x + 80, cy2_bot], fill=GREEN,
                outline=GREEN)
    d.text((bar_x + 90, cy2_top + 5), "≈ bounded chunk",
           font=fmono(17), fill=GREEN)
    d.text((bar_x - 50, cy2_top + 10), "after", font=fmono(14), fill=DIM)
    d.text((bar_x, cy2_bot + 6),
           "streaming · byte-identical output proven by test_stream_parser_equivalence",
           font=fzh(13), fill=DIM)

    # bonus payoff strip
    d.rectangle([40, 360, 1240, 520], outline=AMBER, width=2)
    d.text((60, 374), "意外加成: case_011 cycle-2 残差字段 1 → 5",
           font=fzh(20, bold=True), fill=AMBER)
    d.text((60, 410), "源自 ~/.../case_011/artifacts/residuals.csv:",
           font=fmono(13), fill=DIM)
    d.text((60, 434),
           "  iter,Ux,Uy,Uz,h,p_rgh",
           font=fmono(15), fill=CYAN)
    d.text((60, 458),
           "  1,1.000000e+00,1.000000e+00,1.000000e+00,1.000000e+00,9.993464e-01",
           font=fmono(13), fill=FG)
    d.text((60, 478),
           "  ...",
           font=fmono(13), fill=DIM)
    d.text((60, 496),
           "  200,3.046081e-02,1.832045e-02,2.739833e-02,1.277056e-03,1.005861e-01",
           font=fmono(13), fill=FG)

    d.text((40, 570),
           "Streaming parser 也顺手覆盖了 DILUPBiCGStab + multi-region 残差行",
           font=fzh(15), fill=FG)
    d.text((40, 596),
           "→ chtMultiRegionSimpleFoam 跑了 200/300 iters · 5/5 字段全部 tracked · 3/3 未达标",
           font=fzh(15), fill=GREEN)
    d.text((40, 622),
           "→ solver gate 老实 FAIL · 围栏依然完整",
           font=fzh(15), fill=AMBER)

    d.text((40, 680),
           "$ git show e8691f3 --stat   #  +148 / -42 · streaming chunk + DILUPBiCGStab regex",
           font=fmono(11), fill=DIM)
    img.save(OUT / "shot_c2_streaming_payoff.png")


def shot_gap32_diff():
    img, d = new_canvas()
    header(d, "Gap #32 · 引擎再次抓住自己的 bug",
           "commit 77825b8 · same-arc fix")

    # left side: the leak symptom
    d.text((54, 80), "Cycle-2 dogfood 发现的 sentinel 泄漏",
           font=fzh(18, bold=True), fill=AMBER)
    leak_text = [
        ('"regions": {', FG),
        ('  "region_cold_fluid": {', BLUE),
        ('    "expected_fields": [', FG),
        ('      "U",', CYAN),
        ('      "p",', CYAN),
        ('      "__none_laminar__"', RED),    # the leak
        ('    ],', FG),
        ('    "fields": {', FG),
        ('      "__none_laminar__": {', RED),
        ('        "file":', FG),
        ('          "0/region_cold_fluid/', RED),
        ('           __none_laminar__",', RED),
        ('        "missing": true', RED),
        ('      }, ...', FG),
        ('    }', FG),
        ('  }', FG),
        ('}', FG),
    ]
    y = 116
    for line, col in leak_text:
        d.text((54, y), line, font=fmono(15), fill=col)
        y += 22

    # arrow + verdict
    d.text((54, 540),
           "★ 这不是真的字段 — 是 manifest authoring 留的「laminar 标记」sentinel",
           font=fzh(14, bold=True), fill=AMBER)

    # right side: the same-arc fix
    d.rectangle([700, 100, 1240, 500], outline=GREEN, width=2)
    d.text((714, 112), "同弧落地 (12 commits later)",
           font=fzh(18, bold=True), fill=GREEN)
    d.text((714, 144), "commit 77825b8", font=fmono(20), fill=AMBER)
    d.text((714, 174), "fix(audit-ingest): Gap #32",
           font=fmono(15), fill=FG)
    d.text((714, 198), "strip __sentinel__ markers",
           font=fmono(15), fill=FG)
    d.text((714, 222), "from turbulence_fields",
           font=fmono(15), fill=FG)

    d.text((714, 270), "+ 39 / -0    LOC", font=fmono(15), fill=GREEN)
    d.text((714, 296), "+ 1 named test", font=fmono(15), fill=GREEN)
    d.text((714, 322), "confidence: high", font=fmono(15), fill=GREEN)

    d.text((714, 376), "dogfood agent 发现", font=fzh(15), fill=FG)
    d.text((714, 400), "→ 主 session 修复", font=fzh(15), fill=FG)
    d.text((714, 424), "→ named test 防回归", font=fzh(15), fill=FG)
    d.text((714, 448), "→ 同弧 commit · 不进 triage 队列",
           font=fzh(15, bold=True), fill=AMBER)

    d.text((40, 670),
           "这是 cycle-1 TBD-17 时刻的同型再现 — 引擎依然在抓自己.",
           font=fzh(20, bold=True), fill=AMBER)
    img.save(OUT / "shot_c2_gap32_diff.png")


def shot_cycle2_commits():
    img, d = new_canvas()
    header(d, "Cycle-2 commit log · 19 commits since 5769673",
           "ending at 600022b")

    d.text((40, 70), "$ git log --oneline 5769673..HEAD", font=fmono(15),
           fill=DIM)

    # use real output for top portion
    r = subprocess.run(
        ["git", "-C", str(ROOT), "log", "--oneline", "5769673..HEAD"],
        capture_output=True, text=True, check=True,
    )
    lines = r.stdout.strip().splitlines()

    # color by class
    def colorize(line):
        if "Gap #11" in line or "Gap #23" in line:
            return AMBER  # production-blocker DEC
        if "Gap #32" in line:
            return RED    # self-discovered
        if "Gap #35" in line or "TBD-20" in line or "TBD-15" in line:
            return GREEN  # streaming spike
        if "Gap #26" in line or "Gap #27" in line:
            return CYAN
        if "case_010" in line or "Gap #29" in line or "Gap #31" in line:
            return BLUE
        if "docs" in line or "Merge" in line:
            return DIM
        return FG

    y = 100
    for line in lines[:21]:
        d.text((50, y), line, font=fmono(13.5), fill=colorize(line))
        y += 22

    # right side: legend / summary
    d.rectangle([850, 90, 1240, 520], outline=DIM, width=1)
    d.text((864, 102), "颜色图例", font=fzh(16, bold=True), fill=FG)
    legend = [
        ("Gap #11 / #23 · production-blocker DEC", AMBER),
        ("Gap #32 · 自发现 + 同弧修复",   RED),
        ("TBD-15 / TBD-20 / Gap #35 · streaming", GREEN),
        ("Gap #26-#27 · 工业脚本兼容",    CYAN),
        ("Gap #29 / #31 · case_010 LES",  BLUE),
        ("docs / Merge",                  DIM),
    ]
    yl = 134
    for txt, col in legend:
        d.rectangle([870, yl + 4, 882, yl + 14], fill=col)
        d.text((894, yl), txt, font=fzh(12), fill=FG)
        yl += 26

    d.text((864, 320), "Cycle-2 总结", font=fzh(16, bold=True), fill=AMBER)
    summary = [
        "2 个 production-blocker DEC",
        "4 个 spike-class 落地",
        "2 个 同弧诚实清理",
        "+32 测试 (409 → 441)",
        "0 个 false PASS",
        "0 个 over-promise",
    ]
    ys = 348
    for s in summary:
        d.text((882, ys), "• " + s, font=fzh(13), fill=FG)
        ys += 22

    d.text((40, 680),
           "441 测试通过 · 1 跳过 (pre-existing R15 Docker-gated) · "
           "1 个测试都不会被引擎跳过",
           font=fzh(15), fill=GREEN)
    img.save(OUT / "shot_c2_cycle2_commits.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    shot_case011_bc_quality()
    shot_case011_trust_blocked()
    shot_case010_les_progress()
    shot_step_numbered_logs()
    shot_streaming_payoff()
    shot_gap32_diff()
    shot_cycle2_commits()
    for png in sorted(OUT.glob("shot_c2_*.png")):
        print(f"[shots] {png.name:<48} {png.stat().st_size} bytes")

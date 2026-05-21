#!/usr/bin/env python3
"""Render the 2026-05-22 cfd-harness-unified milestone demo into a 720p MP4.

Reads real terminal captures from .demo/captures/2026-05-22T0145Z/ and real
residual plots from .demo/postproc/case_*/. Composites a "watchable but
honest" terminal-recording-style video: typed commands, line-by-line output,
plot fades during key beats, voice-over as subtitle.

Run:  python3 .demo/build_demo_video.py
Out:  .demo/cfdtrust_demo_2026-05-22.mp4   (~5:30, ~30-60 MB)

No live cfdtrust invocation — every byte of terminal text is replayed from
the capture files committed in this repo.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPTURES = REPO_ROOT / ".demo" / "captures" / "2026-05-22T0145Z"
POSTPROC = REPO_ROOT / ".demo" / "postproc"
OUT_MP4 = REPO_ROOT / ".demo" / "cfdtrust_demo_2026-05-22.mp4"
FRAMES_DIR = Path("/tmp/cfdtrust_demo_frames")

# ---- video config ---------------------------------------------------------

W, H = 1280, 720
FPS = 10
BG = (10, 14, 20)           # near-black
TITLE_BG = (29, 31, 33)
TITLE_FG = (197, 200, 198)
TERM_FG = (197, 200, 198)
TERM_PROMPT = (181, 189, 104)    # green
TERM_HIGHLIGHT = (240, 198, 116)  # yellow
TERM_ERR = (204, 102, 102)        # red
TERM_OK = (181, 189, 104)         # green
SUB_BG = (0, 0, 0)
SUB_FG = (240, 240, 240)
OVERLAY_BG = (29, 31, 33)
OVERLAY_FG = (240, 198, 116)

FONT_MONO = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
FONT_MONO_SMALL = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 12)
FONT_TITLE = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 22)
FONT_BIG = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 28)
FONT_SUB = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 16)

LINE_H = 18  # for FONT_MONO
TERM_TOP = 100              # below title bar + overlay banner
TERM_LEFT = 30
TERM_RIGHT_PLOT = 700       # when plot pane is shown, terminal ends here
TERM_RIGHT_FULL = 1250
PLOT_X_DEFAULT = 710        # plot pane left edge
PLOT_Y_DEFAULT = 105        # plot pane top
SUB_TOP = 645
TITLE_BAR_H = 40
OVERLAY_TOP = 50            # overlay banner starts just below title bar
OVERLAY_H = 30


def fresh_frame():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # title bar
    d.rectangle([0, 0, W, TITLE_BAR_H], fill=TITLE_BG)
    d.text((20, 11), "cfd-harness-unified · 2026-05-22 milestone demo",
           font=FONT_TITLE, fill=TITLE_FG)
    return img, d


def draw_terminal(d, lines, color_map=None, right_edge=TERM_RIGHT_FULL):
    """lines = list of (text, optional_color); color_map = {idx: color}.
    Auto-wraps each line to fit right_edge."""
    color_map = color_map or {}
    char_w = 8  # approximate Menlo 14pt advance
    max_chars = (right_edge - TERM_LEFT) // char_w
    y = TERM_TOP
    for idx, raw in enumerate(lines):
        if isinstance(raw, tuple):
            text, color = raw
        else:
            text, color = raw, color_map.get(idx, TERM_FG)
        # word-wrap-ish: just hard-wrap at max_chars to respect right edge
        if not text:
            y += LINE_H
            continue
        for chunk in wrap(text, max_chars, drop_whitespace=False,
                          replace_whitespace=False) or [""]:
            d.text((TERM_LEFT, y), chunk, font=FONT_MONO, fill=color)
            y += LINE_H
            if y > SUB_TOP - 10:
                return
        # don't add extra space; wrap continues seamlessly


def colorize_line(text):
    """Pick color based on simple line content."""
    t = text.strip()
    if t.startswith("[cfdtrust] OK"):
        return TERM_OK
    if t.startswith("[cfdtrust] WARN"):
        return TERM_HIGHLIGHT
    if t.startswith("[cfdtrust] FAIL"):
        return TERM_ERR
    if t.startswith("$ ") or t.startswith("> "):
        return TERM_PROMPT
    if t.startswith("---") or t.startswith("==="):
        return TERM_HIGHLIGHT
    if t.startswith("#"):
        return TERM_HIGHLIGHT
    if "PASS" in t and "FAIL" not in t:
        return TERM_OK
    if "FAIL" in t or "BLOCKED" in t or "FAILED" in t:
        return TERM_ERR
    return TERM_FG


def draw_subtitle(d, text):
    if not text:
        return
    # background bar
    d.rectangle([0, SUB_TOP, W, H], fill=SUB_BG)
    # text wrapped to 2 lines max
    max_chars = (W - 60) // 10
    chunks = wrap(text, max_chars)[:2]
    y = SUB_TOP + 12
    for c in chunks:
        d.text((30, y), c, font=FONT_SUB, fill=SUB_FG)
        y += 22


def draw_overlay(d, text):
    if not text:
        return
    d.rectangle([20, OVERLAY_TOP, W - 20, OVERLAY_TOP + OVERLAY_H],
                fill=OVERLAY_BG)
    d.text((30, OVERLAY_TOP + 6), text, font=FONT_SUB, fill=OVERLAY_FG)


def paste_plot(img, plot_path, alpha=1.0, target_w=540,
               x=PLOT_X_DEFAULT, y=PLOT_Y_DEFAULT):
    """Paste a plot PNG. Optionally fade by alpha (0-1)."""
    if not plot_path.exists():
        return
    p = Image.open(plot_path).convert("RGBA")
    aspect = p.height / p.width
    target_h = int(target_w * aspect)
    p = p.resize((target_w, target_h), Image.LANCZOS)
    if alpha < 1.0:
        bg = Image.new("RGBA", p.size, (10, 14, 20, 255))
        p = Image.blend(bg, p, alpha)
    img.paste(p, (x, y), p)


def render_frame_n(n, scene):
    """scene: dict with optional keys: title_card, overlay, subtitle,
    term_lines, plot, plot_alpha, plot_box (w, x, y)."""
    img, d = fresh_frame()

    if scene.get("title_card"):
        # big centered text
        title = scene["title_card"]
        thesis = scene.get("thesis", "")
        # center vertically
        ty = (H - 200) // 2
        d.text((W // 2 - len(title) * 9, ty), title,
               font=FONT_BIG, fill=TITLE_FG)
        if thesis:
            tw_chars = max(1, len(thesis) // 2)
            d.text((W // 2 - tw_chars * 9, ty + 60), thesis,
                   font=FONT_TITLE, fill=OVERLAY_FG)
        sub = scene.get("subtitle")
        if sub:
            draw_subtitle(d, sub)
        return img

    if scene.get("overlay"):
        draw_overlay(d, scene["overlay"])

    if scene.get("term_lines"):
        # colorize per line if no explicit color
        lines = []
        for ln in scene["term_lines"]:
            if isinstance(ln, tuple):
                lines.append(ln)
            else:
                lines.append((ln, colorize_line(ln)))
        right = TERM_RIGHT_PLOT if scene.get("plot") else TERM_RIGHT_FULL
        draw_terminal(d, lines, right_edge=right)

    if scene.get("plot"):
        paste_plot(img, scene["plot"],
                   alpha=scene.get("plot_alpha", 1.0),
                   target_w=scene.get("plot_w", 520),
                   x=scene.get("plot_x", 720),
                   y=scene.get("plot_y", 80))

    if scene.get("subtitle"):
        draw_subtitle(d, scene["subtitle"])

    return img


def read_capture(name):
    p = CAPTURES / name
    return p.read_text().splitlines() if p.exists() else [f"<missing: {name}>"]


# ---- timeline -------------------------------------------------------------
# Each scene: (start_sec, end_sec, scene_builder_fn(t_local, t_total) -> scene dict)

def title_scene(_t, _total):
    return {
        "title_card": "cfd-harness-unified",
        "thesis": '"refuses to fabricate verdicts"',
        "subtitle": ("2026-05-22 milestone demo  ·  "
                     "9 physics regimes  ·  TBD-17 self-discovery"),
    }


def closing_scene(_t, _total):
    return {
        "title_card": "the engine doesn't lie",
        "thesis": "9 regimes  ·  1 self-discovered bug  ·  same-arc fix",
        "subtitle": "commit 1176dae · 427 tests · main · cfdtrust ingest",
    }


def make_typing_scene(capture_name, voice_over, overlay,
                      plot=None, plot_w=520, plot_appear_at=0.4,
                      plot_x=720, plot_y=80):
    """Returns a builder that types out the capture file gradually."""
    raw_lines = read_capture(capture_name)

    def builder(t_local, t_total):
        # how many lines visible at t_local
        progress = min(1.0, t_local / max(t_total - 0.5, 0.5))
        visible_line_count = int(progress * len(raw_lines))
        visible_line_count = max(1, visible_line_count)
        visible = raw_lines[:visible_line_count]

        # if there are too many lines to fit, scroll: show last ~28 lines
        max_lines = 28
        if len(visible) > max_lines:
            visible = visible[-max_lines:]

        # prepend a fake prompt for the command that produced this output
        scene = {
            "overlay": overlay,
            "term_lines": visible,
            "subtitle": voice_over,
        }
        if plot:
            scene["plot"] = plot
            scene["plot_w"] = plot_w
            scene["plot_x"] = plot_x
            scene["plot_y"] = plot_y
            # fade-in plot starting at plot_appear_at fraction
            if progress >= plot_appear_at:
                fade_progress = (progress - plot_appear_at) / max(
                    1.0 - plot_appear_at, 0.01)
                scene["plot_alpha"] = min(1.0, fade_progress * 2)
            else:
                # don't show plot at all
                del scene["plot"]
        return scene
    return builder


def make_command_scene(prompt_text, capture_name, voice_over, overlay,
                       plot=None, plot_w=520, plot_appear_at=0.3,
                       plot_x=720, plot_y=80):
    """Show a $ prompt with command, then typed-out capture output."""
    cmd_line = f"$ {prompt_text}"
    body = read_capture(capture_name)

    def builder(t_local, t_total):
        # phase 1 (0 - 8% of scene): type the command
        # phase 2 (8% - 100%): output appears line-by-line
        progress = min(1.0, t_local / max(t_total - 0.5, 0.5))
        if progress < 0.08:
            cmd_progress = progress / 0.08
            typed = cmd_line[:max(1, int(len(cmd_line) * cmd_progress))]
            visible = [(typed, TERM_PROMPT)]
        else:
            out_progress = (progress - 0.08) / 0.92
            n_visible = int(out_progress * len(body))
            n_visible = max(1, n_visible)
            output_lines = body[:n_visible]
            # scroll if too long
            max_lines = 27
            if len(output_lines) > max_lines:
                output_lines = output_lines[-max_lines:]
            visible = [(cmd_line, TERM_PROMPT)] + output_lines

        scene = {"overlay": overlay,
                 "term_lines": visible,
                 "subtitle": voice_over}
        if plot:
            if progress >= plot_appear_at:
                fade = (progress - plot_appear_at) / max(
                    1.0 - plot_appear_at, 0.01)
                scene["plot"] = plot
                scene["plot_w"] = plot_w
                scene["plot_x"] = plot_x
                scene["plot_y"] = plot_y
                scene["plot_alpha"] = min(1.0, fade * 2)
        return scene
    return builder


TIMELINE = [
    # (start_sec, end_sec, builder)
    (0.0, 8.0, title_scene),

    (8.0, 32.0, make_command_scene(
        "git log --oneline 5250bb7..HEAD",
        "stage_01_git_log.txt",
        "21 commits in 24 hours. 7-round Codex review, 3 follow-up sub-DECs, "
        "9 physics-regime dogfoods.",
        "Stage 1 · the trail · 21-commit arc"
    )),

    (32.0, 80.0, make_command_scene(
        "cfdtrust ingest .../_sandboxes/case_027_hagen_poiseuille_pipe/case_v65",
        "stage_02a_case_027_ingest.txt",
        "Stage 2. Laminar Hagen-Poiseuille pipe — solver converged 5000 "
        "iterations but watch the verdict.",
        "Stage 2a · case_027 ingest · laminar wedge",
        plot=POSTPROC / "case_027" / "residual_plot.png",
        plot_appear_at=0.55,
    )),

    (80.0, 110.0, make_command_scene(
        "cfdtrust report .../case_027_hagen_poiseuille_pipe/case_v65",
        "stage_02b_case_027_report.txt",
        "cfdtrust report writes the trust_report.json and the WARN line says "
        "this is not a real validation — even though the solver converged.",
        "Stage 2b · trust_report.json · honesty fence held",
        plot=POSTPROC / "case_027" / "residual_plot.png",
        plot_appear_at=0.0,
    )),

    (110.0, 155.0, make_command_scene(
        "cfdtrust explain .../case_027_hagen_poiseuille_pipe/case_v65",
        "stage_02c_case_027_explain.txt",
        "Surprise: the mesh contract gate FAILed on a missing axis BC the user "
        "never declared. Engine refuses to certify what it cannot see.",
        "Stage 2c · explain · mesh_contract FAILed honestly"
    )),

    (155.0, 200.0, make_command_scene(
        "cfdtrust ingest .../_sandboxes/case_010_drivaer_fastback_les/case",
        "stage_03_case_010_block.txt",
        "Stage 3. Case_010 DrivAer LES is at scaffold state — no time "
        "directories, no solver log. Engine BLOCKs honestly. No fabricated PASS.",
        "Stage 3 · honest precondition BLOCK · case_010 LES"
    )),

    (200.0, 240.0, make_command_scene(
        "git log --grep=TBD-17 --format=fuller",
        "stage_04a_tbd17_grep.txt",
        "Stage 4. Mid-arc the engine snitched on itself. case_009 reacting "
        "showed sub-gate PASS on 3/27 fields. We caught it, logged TBD-17.",
        "Stage 4a · TBD-17 self-discovered honesty bug"
    )),

    (240.0, 270.0, make_command_scene(
        "git show 3b5c43f --stat",
        "stage_04b_tbd17_show.txt",
        "Same arc, same day. 3 files changed, 302 insertions. Fence: gate "
        "BLOCKs with incomplete_residual_coverage when manifest names mismatch.",
        "Stage 4b · TBD-17 fix · commit 3b5c43f"
    )),

    (270.0, 320.0, make_command_scene(
        "cfdtrust ingest .../case_021_nasa_tmr_flat_plate/case_v65   # re-ingest",
        "stage_06a_case_021_tbd17_block.txt",
        "Stage 5. Watch TBD-17 work LIVE. case_021 NASA TMR — parser found 5 "
        "residual fields but only 1 matches manifest names. BLOCKED.",
        "Stage 5 · case_021 · TBD-17 LIVE in production",
        plot=POSTPROC / "case_021" / "residual_plot.png",
        plot_appear_at=0.3,
    )),

    (320.0, 380.0, make_command_scene(
        "cfdtrust ingest .../case_009_sandia_flame_d/case   # re-ingest",
        "stage_06b_case_009_tbd17_block.txt",
        "Stage 6. The hero. Reacting flame, 28 fields parsed including CH2 "
        "singlet/triplet via TBD-19. Gate still BLOCKs — 3/27 names match. "
        "Coverage ≠ trust.",
        "Stage 6 · case_009 hero · reactingFoam · BLOCKED honestly",
        plot=POSTPROC / "case_009" / "residual_plot.png",
        plot_appear_at=0.3,
    )),

    (380.0, 415.0, make_command_scene(
        "pytest ui/backend/audit/cfdtrust_tests/ -q",
        "stage_05a_test_count.txt",
        "Stage 7. 427 tests passing, 1 skipped. Up from 374 baseline.",
        "Stage 7 · 427 tests green · 53 net added this arc"
    )),

    (415.0, 445.0, make_command_scene(
        "find .../_sandboxes -name 'DOGFOOD_CASE_*.md'",
        "stage_05b_dogfood_inventory.txt",
        "9 dogfood mds across 9 physics regimes. Laminar to reacting "
        "low-Mach. Every honesty fence held.",
        "Stage 7b · capability inventory · 9 regimes verified"
    )),

    (445.0, 458.0, closing_scene),
]


def build_video():
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True)

    total_secs = TIMELINE[-1][1]
    total_frames = int(total_secs * FPS)
    print(f"[demo] total runtime {total_secs:.1f}s · {total_frames} frames @ {FPS}fps")

    frame_idx = 0
    for (start, end, builder) in TIMELINE:
        seg_len = end - start
        seg_frames = int(seg_len * FPS)
        for i in range(seg_frames):
            t_local = i / FPS
            scene = builder(t_local, seg_len)
            img = render_frame_n(frame_idx, scene)
            img.save(FRAMES_DIR / f"f_{frame_idx:06d}.png",
                     optimize=False, compress_level=1)
            frame_idx += 1
            if frame_idx % 100 == 0:
                pct = 100 * frame_idx / total_frames
                print(f"[demo]   {frame_idx}/{total_frames} frames ({pct:.0f}%)")

    print(f"[demo] rendered {frame_idx} frames · encoding via ffmpeg")
    OUT_MP4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "f_%06d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        "-preset", "medium",
        "-movflags", "+faststart",
        str(OUT_MP4),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("[demo] ffmpeg stderr:", r.stderr[-1500:], file=sys.stderr)
        raise SystemExit(r.returncode)
    size_mb = OUT_MP4.stat().st_size / (1024 * 1024)
    print(f"[demo] OUT {OUT_MP4} · {size_mb:.1f} MB")
    print("[demo] cleaning frames")
    shutil.rmtree(FRAMES_DIR)


if __name__ == "__main__":
    build_video()

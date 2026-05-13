"""
Build advisor_moments_final.mp4 v2 — REAL engineering process imagery.

Pure visuals: CAD / mesh / convergence plots / temperature & velocity fields
/ streamlines. Bottom-of-frame Chinese captions only. No dashboard, no
section headers, no markdown slideshow.

Sequence (~5 min):
  - Group 1: Geometry / CAD (~60s)
  - Group 2: Mesh / topology (~50s)
  - Group 3: Convergence plots (~60s)
  - Group 4: Field results (T, U, streamlines) (~140s)
  - Group 5: Combined summary (~30s)

Pipeline:
  for each source PNG:
    1. PIL: load, scale-to-fit into 1920x1080 with dark canvas
    2. PIL: overlay bottom Chinese caption (PingFang SC) on translucent bar
    3. write frame PNG
  ffmpeg per-frame mp4 clip with fade in/out
  ffmpeg concat all clips -> recordings/advisor_moments_final.mp4
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

# ───── Config ───────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).parent
CASE_ROOT = Path.home() / "Desktop" / "apu-bay-ventilation-cht"
FRAMES_DIR = WORKSPACE / "build_frames"
OUTPUT_VIDEO = WORKSPACE / "recordings" / "advisor_moments_final.mp4"

W, H = 1920, 1080
BG = (12, 12, 16)              # near-black
CAPTION_BG = (0, 0, 0, 180)    # semi-transparent black band
CAPTION_FG = (245, 245, 245)
CAPTION_DIM = (175, 195, 215)  # subtitle / context line
CAPTION_HIGHLIGHT = (255, 200, 100)  # numbers / key technical terms

FONT_CN_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_MONO_PATH = "/System/Library/Fonts/Menlo.ttc"
FONT_MAIN_SIZE = 42
FONT_SUB_SIZE = 28
CAPTION_BAND_H = 160
CAPTION_PAD_X = 80
CAPTION_PAD_Y = 28

FADE_SEC = 0.5


@dataclass
class Shot:
    src: Path
    caption_main: str       # primary Chinese caption line
    caption_sub: str = ""   # optional subtitle (smaller, dim)
    duration: float = 8.0   # seconds


# ───── Shot list — only existing files; durations tuned for 4-5 min total ─

def build_shots() -> List[Shot]:
    """Curate 25-30 frames across 5 groups using real v6N/v7_steady assets."""
    p = lambda rel: CASE_ROOT / rel
    shots: List[Shot] = []

    # ── Group 1: 几何 / CAD（约 60s） ──────────────────────────────────
    shots += [
        Shot(p("reports/v7_steady/STL_preview_side.png"),
             "APU 舱通风算例 · 几何概览",
             "MES day 55 °C 工况 · 14 个 APU 本体 + 燃烧室 + 进气道", 8),
        Shot(p("reports/v7_steady/STL_v3_bodies_side.png"),
             "STL 清理 · 内部本体侧视",
             "v3 STL 手术后 patch 总数：30", 8),
        Shot(p("reports/v7_steady/CHT_role_iso_back.png"),
             "patch 角色分配 · CHT 视角",
             "wall_hot / wall_adiabatic / mass_flow / pressure 边界分类", 9),
        Shot(p("reports/v7_steady/CHT_role_top.png"),
             "patch 角色分配 · 顶视",
             "naming.yaml 作为单一真相源 · 贯穿 STL → mesh → BC → 后处理", 9),
        Shot(p("reports/v7_steady/V6_scene1_PO_beams_Inner_side_Ym.png"),
             "外蒙皮 + 内部梁结构 · 工业 CAD 复杂度",
             "Plane_Outer_Surf + 14 本体 + 燃烧室出口 / 进气 patch", 9),
        Shot(p("reports/v7_steady/V10_sceneE_v4v10_duct_iso_back.png"),
             "管道 + 集气腔拓扑",
             "燃烧室 → 进气抽吸 通风路径", 8),
    ]

    # ── Group 2: 网格 / Mesh（约 50s） ─────────────────────────────────
    shots += [
        Shot(p("reports/v7_steady/SKINS_3layer_bottom.png"),
             "snappyHexMesh 边界层 · 3 层 prism",
             "贴体网格 · 用于壁面对流传热分辨", 10),
        Shot(p("reports/v7_steady/V8_sceneE_envelope_side_Ym.png"),
             "网格包络体 · 侧视",
             "refinementBox 加密 · jet 区域 L3", 8),
        Shot(p("reports/v7_steady/V12_A_PO_opaque_beams_side_Ym.png"),
             "结构梁与流体域耦合视图",
             "943k cells · max_skew 6.875 · 20 skew faces", 10),
        Shot(p("reports/v7_steady/V13_A_PO_opaque_beams_iso_back.png"),
             "完整组装视图 · 等轴",
             "工业 CAD 直入 OpenFOAM · 无简化预处理", 9),
    ]

    # ── Group 3: 求解器收敛 / Plots（约 60s） ──────────────────────────
    shots += [
        Shot(p("reports/v6N/plots/residuals.png"),
             "求解器残差收敛 · buoyantPimpleFoam",
             "动量 U · 能量 h · 压力 p_rgh · log 标度", 12),
        Shot(p("reports/v6N/plots/p_rgh_inner_iters.png"),
             "压力 p_rgh 内迭代趋势",
             "PIMPLE outer=5 · residualControl 5e-5", 10),
        Shot(p("reports/v6N/plots/mdot_ramp.png"),
             "边界流量 ramp · 燃烧室 + apu_intake",
             "combustor 2.8 kg/s @ 616 K · intake 4.85 kg/s 抽吸", 11),
        Shot(p("reports/v6N/plots/T_ramp.png"),
             "进口温度时序",
             "ramp 到 plateau · t=150-200s 取样窗口", 9),
        Shot(p("reports/v6N/plots/rho_history_full.png"),
             "压缩密度 ρ 时序 · 全程",
             "compressible 解算 · ρ 无失稳信号", 9),
    ]

    # ── Group 4: 流场云图 / Fields（约 140s） ──────────────────────────
    shots += [
        Shot(p("reports/v6N/paraview_HD_v3_smooth/03_Umag_axial_Z0_HD.png"),
             "|U| 速度场 · 轴向 Z=0 切片",
             "燃烧室 jet 冲击 + 涡卷起 · 速度场不受能量耗散影响", 12),
        Shot(p("reports/v6N/paraview_HD_v3_smooth/05_firewall_combustor_T_HD.png"),
             "燃烧室 + firewall 局部温度",
             "出口 615 K fixedValue 边界忠实呈现", 11),
        Shot(p("reports/v6N/paraview_HD_v3_smooth/04_Inner_Surf_T_HD.png"),
             "APU 内表面温度分布",
             "对流冷却建立壁面 T 梯度 · 14 个 body fixedValue 343-674 K", 11),
        Shot(p("reports/v6N/paraview_HD_v3_smooth/06_streamlines_combustor_HD.png"),
             "燃烧室出口流线",
             "热射流 + 主舱卷吸涡 · 通风结构清晰", 12),
        Shot(p("reports/v6N/paraview_HD_v3_smooth/07_streamlines_intake_HD.png"),
             "apu_intake 抽吸流线",
             "舱内空气 → 4.85 kg/s 抽吸出口 · 通风路径全可视化", 11),
        Shot(p("reports/v6N/paraview_phase4c_t200/04_streamlines_farfield.png"),
             "远场流线 · farfield_cylinder",
             "外部大气 + 抽吸驱动的整体流向", 10),
        Shot(p("reports/v6N/paraview_phase4c_t200/06_T_multi_X_slices.png"),
             "多 X 切面温度分布",
             "热扩散沿燃烧室轴向衰减", 11),
        Shot(p("reports/v6N/paraview_phase4c_t200/07_T_volume_3D.png"),
             "温度场 3D 体绘",
             "诚实呈现 · bay 平均 T 比理论低 ~30%（数值耗散主因）", 12),
        Shot(p("reports/v6N/paraview_phase4c_t200/03b_T_top_view_Y079.png"),
             "Y=0.79m 高度温度顶视",
             "热源局部 vs 远场冷 · 工程定性结论可用", 10),
    ]

    # ── Group 5: 综合 / Summary（约 30s） ──────────────────────────────
    shots += [
        Shot(p("reports/v6N/paraview_HD_v3_smooth/08_combined_view_HD.png"),
             "综合视图 · 4-tier 对比交付物",
             "T 切片 + 流线 + |U| + 表面 T 一体化报告", 14),
        Shot(p("reports/v6N/plots/run10_full_trajectory.png"),
             "完整运行 trajectory · 10.4 小时",
             "Claude Code session 端到端驱动 · 4-core MPI", 14),
    ]

    return shots


# ───── Frame composition ────────────────────────────────────────────────

def fit_into_canvas(src: Image.Image) -> Image.Image:
    """Scale src to fit into (W, H - CAPTION_BAND_H) image area while preserving
    aspect; center it on dark canvas; return W×H RGB image."""
    avail_h = H - CAPTION_BAND_H
    sw, sh = src.size
    scale = min(W / sw, avail_h / sh)
    new_w, new_h = int(sw * scale), int(sh * scale)
    if (new_w, new_h) != (sw, sh):
        src = src.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), BG)
    off_x = (W - new_w) // 2
    off_y = (avail_h - new_h) // 2
    canvas.paste(src, (off_x, off_y))
    return canvas


def draw_caption(canvas: Image.Image, main: str, sub: str) -> None:
    """Overlay bottom translucent caption band + text."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    band_y0 = H - CAPTION_BAND_H
    # Translucent gradient-ish band (single solid for simplicity)
    od.rectangle([(0, band_y0), (W, H)], fill=CAPTION_BG)
    # Subtle top accent line
    od.line([(0, band_y0), (W, band_y0)], fill=(135, 196, 255, 220), width=2)

    font_main = ImageFont.truetype(FONT_CN_PATH, FONT_MAIN_SIZE, index=1)
    font_sub = ImageFont.truetype(FONT_CN_PATH, FONT_SUB_SIZE, index=0)

    # Main line
    od.text((CAPTION_PAD_X, band_y0 + CAPTION_PAD_Y), main,
            fill=CAPTION_FG, font=font_main)

    if sub:
        # Sub line — split tokens; highlight digits & well-known technical IDs
        sub_y = band_y0 + CAPTION_PAD_Y + FONT_MAIN_SIZE + 14
        od.text((CAPTION_PAD_X, sub_y), sub,
                fill=CAPTION_DIM, font=font_sub)

    # Footer (small) — project tag bottom-right
    font_tag = ImageFont.truetype(FONT_MONO_PATH, 20)
    tag = "cfd-harness · v6N B+"
    tw = od.textbbox((0, 0), tag, font=font_tag)[2]
    od.text((W - CAPTION_PAD_X - tw, H - 32), tag, fill=(110, 130, 160, 200),
            font=font_tag)

    # Composite
    out = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    canvas.paste(out)


def render_frame(shot: Shot, out_path: Path) -> None:
    src = Image.open(shot.src).convert("RGB")
    canvas = fit_into_canvas(src)
    draw_caption(canvas, shot.caption_main, shot.caption_sub)
    canvas.save(out_path, "PNG")


# ───── ffmpeg ───────────────────────────────────────────────────────────

def build_clip(png: Path, duration: float, out_clip: Path) -> None:
    vf = (
        f"format=yuv420p,"
        f"fade=t=in:st=0:d={FADE_SEC},"
        f"fade=t=out:st={duration - FADE_SEC}:d={FADE_SEC}"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", "30", "-i", str(png),
        "-vf", vf,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "20",
        "-r", "30",
        str(out_clip),
    ]
    subprocess.run(cmd, check=True)


def concat(clips: List[Path], out: Path) -> None:
    listfile = clips[0].parent / "concat.txt"
    listfile.write_text("\n".join(f"file '{c.resolve()}'" for c in clips))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(listfile),
        "-c", "copy",
        str(out),
    ]
    subprocess.run(cmd, check=True)


# ───── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)

    shots = build_shots()

    # Filter missing files (warn)
    valid: List[Shot] = []
    for s in shots:
        if s.src.exists():
            valid.append(s)
        else:
            print(f"  WARN missing source: {s.src}", file=sys.stderr)

    total_dur = sum(s.duration for s in valid)
    print(f"Shots: {len(valid)}; planned duration: {total_dur:.1f}s "
          f"({total_dur / 60:.2f} min)", file=sys.stderr)

    # Render frames
    clips: List[Path] = []
    for i, s in enumerate(valid):
        frame_path = FRAMES_DIR / f"frame_{i:03d}.png"
        clip_path = FRAMES_DIR / f"clip_{i:03d}.mp4"
        render_frame(s, frame_path)
        build_clip(frame_path, s.duration, clip_path)
        clips.append(clip_path)
        print(f"  shot {i + 1}/{len(valid)}: {s.src.name} ({s.duration:.1f}s)",
              file=sys.stderr, end="\r")
    print(file=sys.stderr)

    concat(clips, OUTPUT_VIDEO)
    print(f"\n✓ Final: {OUTPUT_VIDEO}", file=sys.stderr)
    print(f"  size: {OUTPUT_VIDEO.stat().st_size / (1024 * 1024):.1f} MB",
          file=sys.stderr)
    print(f"  duration: {total_dur:.1f}s ({total_dur / 60:.2f} min)",
          file=sys.stderr)


if __name__ == "__main__":
    main()

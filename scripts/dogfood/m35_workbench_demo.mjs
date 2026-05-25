// DEC-V61-202 M3.5 cycle 1 · full-workflow CFD demo recording.
// Records a .webm video walking through all 6 workbench steps with
// (a) in-browser Chinese caption overlay (title + body)
// (b) highlighted custom cursor (red circle) tracking real mouse motion
// (c) deliberate cursor moves + hovers to demonstrate UI interaction.
//
// USAGE · node scripts/dogfood/m35_workbench_demo.mjs
// REQUIRES · uvicorn :8001 + vite :5173 running · m33_ux_demo_seed staged
// OUTPUT · .webm path printed at end

import { mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const playwrightUrl = new URL(
  "../../ui/frontend/node_modules/playwright/index.mjs",
  import.meta.url,
);
const { chromium } = await import(playwrightUrl.href);

const OUT_DIR = resolve("/tmp/cfd_demo_recording");
mkdirSync(OUT_DIR, { recursive: true });

const CASE_ID = "m33_ux_demo_seed";
const BASE = "http://localhost:5173";

const STEPS = [
  {
    step: "geometry",
    title: "第 1 步 · 几何 (Geometry) · 导入 CAD",
    narration:
      "工程师在这里上传 CAD。\n当前案例还没有 CAD → 工作台显示「未找到可渲染几何 / No CAD geometry yet」+ 醒目「↑ 上传 CAD / Upload CAD」CTA (M3.4 cycle 3 polish 成果)。\n右栏 case_family 字段提示 + 「待补充」amber 标签 (M3.2 severity surfacing 工作)。\n📋 + 📝 复制按钮可见 (M3.2 cycle 3-5)。",
    holdMs: 7000,
    interact: async (page) => {
      const cta = page.getByTestId("v4-mode-geometry-upload-cta");
      if (await cta.count()) {
        const box = await cta.boundingBox();
        if (box) {
          await page.mouse.move(720, 400, { steps: 30 });
          await page.waitForTimeout(800);
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 40 });
          await page.waitForTimeout(1500);
        }
      }
      // hover the copy field_path button to show ✓ + toast
      const copyBtn = page.getByTestId("dynamic-frame-copy-field-path");
      if (await copyBtn.count()) {
        const box2 = await copyBtn.boundingBox();
        if (box2) {
          await page.mouse.move(box2.x + box2.width / 2, box2.y + box2.height / 2, { steps: 30 });
          await page.waitForTimeout(800);
          await copyBtn.click();
          await page.waitForTimeout(1500);
        }
      }
    },
  },
  {
    step: "mesh",
    title: "第 2 步 · 网格 (Mesh) · 生成 / 检查",
    narration:
      "网格质量审计。\n中心 3D 视口渲染 mesh.glb (vtk.js + WebGL)。\n底部 4 列质量指标 histogram: 偏度 / 表面质量 / 单元质量 / 正交性 / 长宽比。\n右栏「Step 2 · 网格就绪 / Mesh ready」+ AI 助理 ADVISORY ONLY · 80% 准备度 · 18.86 万单元 / mesh.glb / 5 项 histogram。",
    holdMs: 6000,
    interact: async (page) => {
      await page.mouse.move(720, 450, { steps: 25 });
      await page.waitForTimeout(800);
      // sweep across the 4 stat columns at bottom
      await page.mouse.move(280, 760, { steps: 20 });
      await page.waitForTimeout(700);
      await page.mouse.move(540, 760, { steps: 20 });
      await page.waitForTimeout(700);
      await page.mouse.move(800, 760, { steps: 20 });
      await page.waitForTimeout(700);
    },
  },
  {
    step: "physics",
    title: "第 3 步 · 物理 (Physics) · 湍流 + 材料",
    narration:
      "湍流模型 + 材料 + 工况。\n5 个湍流模型卡片: SST k-ω (已选 · RANS) · Spalart-Allmaras · k-ε · Laminar · Energy off。\n材料库 5 个: 空气 / 钛合金 / 钢 / inconel / 隔热层。\n底部 stats: 5 物理模型 · 5 材料 · 稳态 · 28.6 万估算单元。\n右栏 Step 3 · 物理已设。",
    holdMs: 6000,
    interact: async (page) => {
      await page.mouse.move(500, 100, { steps: 25 });
      await page.waitForTimeout(800);
      await page.mouse.move(500, 220, { steps: 20 });
      await page.waitForTimeout(800);
      await page.mouse.move(500, 340, { steps: 20 });
      await page.waitForTimeout(800);
    },
  },
  {
    step: "boundary",
    title: "第 4 步 · 边界 (Boundary) · BC 识别 + 编辑",
    narration:
      "在 3D 模型上识别 + 编辑边界条件。\n中心 3D 模型带 label: 入口 / 出口 / 壁面 / 转子域 / 未识别。\nBC 表: 28 入口 + 27 出口 + 1 热壁面 + 4 转子域 + 9 壁面 + 1 未识别。\n右栏 Step 4 · 边界已设 · 边界数 61 + 覆盖度 98.4% + 应用 AI 建议。\n底部 stats: 28 入口 / 27 出口 / 6 壁面 / 1 转子域。",
    holdMs: 6000,
    interact: async (page) => {
      await page.mouse.move(600, 280, { steps: 25 });
      await page.waitForTimeout(800);
      await page.mouse.move(800, 280, { steps: 20 });
      await page.waitForTimeout(800);
      await page.mouse.move(900, 380, { steps: 20 });
      await page.waitForTimeout(800);
    },
  },
  {
    step: "solver",
    title: "第 5 步 · 求解 (Solver) · 启动 + 监控",
    narration:
      "Solver 配置 + 监控启动。\nsolver 类型 (simpleFoam / pimpleFoam / interFoam) · 时间步 · 迭代次数 · 收敛准则。\n监控面板预备: 残差曲线 · 字段采样 · 实时探针 · log tail。\n右栏 Step 5 rail 显示当前可启动状态或仍在缺字段。",
    holdMs: 5500,
    interact: async (page) => {
      await page.mouse.move(700, 400, { steps: 25 });
      await page.waitForTimeout(900);
      await page.mouse.move(1000, 400, { steps: 20 });
      await page.waitForTimeout(900);
    },
  },
  {
    step: "post",
    title: "第 6 步 · 后处理 (Post) · 可视化 + 报告",
    narration:
      "ParaView/Trame 远程 viewport + 后处理工具。\n字段: 压力 / 速度 / 涡量 / 温度 / 湍流量。\n工具: slice · clip · streamline · contour · 探针线 · 截面绘图。\n报告: 图片 / VTP / FOAM / Notion 同步。",
    holdMs: 5500,
    interact: async (page) => {
      await page.mouse.move(750, 450, { steps: 25 });
      await page.waitForTimeout(900);
      await page.mouse.move(1100, 450, { steps: 20 });
      await page.waitForTimeout(900);
    },
  },
];

const overlayScript = `(() => {
  // M3.5 cycle 2 fix: addInitScript fires before document.body exists.
  // Defer to DOMContentLoaded so appendChild has a target.
  const init = () => {
    if (!document.body) return;
    if (document.getElementById('m35-demo-caption')) return;
    const cap = document.createElement('div');
    cap.id = 'm35-demo-caption';
    cap.style.cssText = 'position:fixed;bottom:24px;left:24px;right:24px;background:rgba(8,12,20,0.94);color:#f1f5f9;padding:14px 18px;border:1px solid #475569;border-radius:6px;font-family:-apple-system,SF Pro Text,system-ui,sans-serif;font-size:14px;line-height:1.55;z-index:2147483647;box-shadow:0 8px 24px rgba(0,0,0,0.5);white-space:pre-line;backdrop-filter:blur(4px);pointer-events:none;';
    cap.innerHTML = '<div id="m35-cap-title" style="font-size:15px;font-weight:600;color:#5eead4;margin-bottom:6px;"></div><div id="m35-cap-body"></div>';
    document.body.appendChild(cap);

    const cur = document.createElement('div');
    cur.id = 'm35-demo-cursor';
    cur.style.cssText = 'position:fixed;width:28px;height:28px;margin:-14px 0 0 -14px;border-radius:50%;background:radial-gradient(circle,rgba(248,113,113,0.6),rgba(248,113,113,0));border:2.5px solid rgba(248,113,113,0.95);box-shadow:0 0 18px rgba(248,113,113,0.55);pointer-events:none;z-index:2147483646;left:-100px;top:-100px;transition:transform 0.04s linear;';
    document.body.appendChild(cur);
    document.addEventListener('mousemove', (e) => {
      cur.style.left = e.clientX + 'px';
      cur.style.top = e.clientY + 'px';
    }, { capture: true, passive: true });
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();`;

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: OUT_DIR, size: { width: 1440, height: 900 } },
  permissions: ["clipboard-read", "clipboard-write"],
});
await context.addInitScript({ content: overlayScript });

const page = await context.newPage();

const setCaption = async (title, body) =>
  page.evaluate(
    ({ t, b }) => {
      const tt = document.getElementById("m35-cap-title");
      const bb = document.getElementById("m35-cap-body");
      if (tt) tt.textContent = t;
      if (bb) bb.textContent = b;
    },
    { t: title, b: body },
  );

await page.goto(`${BASE}/workbench/case/${CASE_ID}?step=geometry`);
await page.waitForResponse((r) => r.url().includes("/workbench_frame") && r.status() === 200);
await page.getByTestId("dynamic-frame-panel").waitFor();
await page.waitForTimeout(1000);

await setCaption(
  "CFD 工作台 0→1 全流程演示 · M3.2-M3.4 改进总验",
  "案例: m33_ux_demo_seed · 走完 6 步 (Geometry→Mesh→Physics→Boundary→Solver→Post) · 红色光标 = 鼠标轨迹 · 底部黑色框 = 中文标注 · 录制开始",
);
await page.mouse.move(720, 450, { steps: 40 });
await page.waitForTimeout(3500);

for (const s of STEPS) {
  await page.goto(`${BASE}/workbench/case/${CASE_ID}?step=${s.step}`);
  await page.waitForResponse((r) => r.url().includes("/workbench_frame") && r.status() === 200);
  await page.waitForTimeout(1000);
  await setCaption(s.title, s.narration);
  if (s.interact) await s.interact(page);
  await page.waitForTimeout(s.holdMs);
}

await setCaption(
  "演示完成 · M3.2 / M3.3 / M3.4 全部生效",
  "本 session 17 commits · 3 milestone close · 0 post-R3 defects · v2.3 round-1 loosen 全程践行 · 多 agent 施工队架构在 M3.3-M3.4 全规模部署 · 视觉 spot-check 永久接入流程",
);
await page.mouse.move(720, 450, { steps: 60 });
await page.waitForTimeout(4500);

const videoPromise = page.video()?.path();
await page.close();
await context.close();
await browser.close();
const videoPath = await videoPromise;
console.log(`recorded · ${videoPath}`);

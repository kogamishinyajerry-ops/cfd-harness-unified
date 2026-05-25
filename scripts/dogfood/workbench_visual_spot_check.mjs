// Workbench visual spot-check tool (per .planning/methodology/screenshot_spot_check.md).
// USAGE: from anywhere, `node scripts/dogfood/workbench_visual_spot_check.mjs [flags]`.
// playwright is resolved from ui/frontend/node_modules via absolute path so
// CWD does not matter (ESM resolves bare specifiers from script location). Flags:
//   --case-id <id>   (default: m33_ux_demo_seed)
//   --step <step>    (default: geometry)
//   --out-dir <dir>  (default: /tmp/cfd_workbench_screenshots/)
import { mkdirSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const playwrightUrl = new URL(
  "../../ui/frontend/node_modules/playwright/index.mjs",
  import.meta.url,
);
const { chromium } = await import(playwrightUrl.href);

const args = process.argv.slice(2);
const flag = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback;
};
const caseId = flag("--case-id", "m33_ux_demo_seed");
const step = flag("--step", "geometry");
const outDir = resolve(flag("--out-dir", "/tmp/cfd_workbench_screenshots/"));
mkdirSync(outDir, { recursive: true });

const url = `http://localhost:5173/workbench/case/${encodeURIComponent(caseId)}?step=${encodeURIComponent(step)}`;
const browser = await chromium.launch({
  headless: true,
  args: ["--use-gl=swiftshader", "--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"],
});
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  permissions: ["clipboard-read", "clipboard-write"],
});
const page = await ctx.newPage();

await page.goto(url);
await page.waitForResponse(
  (r) => r.url().includes("/workbench_frame") && r.status() === 200,
  { timeout: 15_000 },
);
await page.getByTestId("dynamic-frame-panel").waitFor({ timeout: 15_000 });
await page.waitForTimeout(800);

const saved = [];
const shot = async (suffix, opts = {}) => {
  const p = join(outDir, `${caseId}_${suffix}.png`);
  await page.screenshot({ path: p, fullPage: false, ...opts });
  saved.push(p);
};

await shot("idle");

const fieldBtn = page.getByTestId("dynamic-frame-copy-field-path");
if (await fieldBtn.count()) {
  await fieldBtn.click();
  await page.waitForTimeout(150);
  await shot("field_copy");
}

const bodyBtn = page.getByTestId("dynamic-frame-copy-body-text");
if (await bodyBtn.count()) {
  await page.waitForTimeout(1700);
  await bodyBtn.click();
  await page.waitForTimeout(150);
  await shot("body_copy");
}

await page.waitForTimeout(1700);
await shot("full", { fullPage: true });

await browser.close();
console.log("saved:");
for (const p of saved) console.log(`  ${p}`);

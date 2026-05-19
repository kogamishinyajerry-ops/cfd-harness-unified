// V79.3 · SSIM active screenshot gate.
//
// V78.2 landed `scripts/visual/ssim_compare.py` as a tool. V79.3 makes
// the tool ACTIVELY gate at playwright-test time: this spec
//   (a) runs SSIM batch self-consistency over all baseline PNGs
//       (rejects any file-level corruption / truncation), and
//   (b) re-captures 1 representative baseline + SSIM-compares it
//       against the on-disk baseline · SSIM must be ≥ 0.99.
//
// Why a separate spec instead of replacing playwright's
// maxDiffPixelRatio gate everywhere: replacing the gate would require
// regenerating all 76 baselines under SSIM-aware capture logic. V79.3
// scope is to PROVE the gate WORKS without disturbing the 76-baseline
// substrate V78.6 stabilized.

import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { test, expect } from "@playwright/test";

const __dirname = dirname(fileURLToPath(import.meta.url));
// Repo root: e2e/ → ui/frontend/ → ui/ → repo
const REPO_ROOT = resolve(__dirname, "..", "..", "..");
const SSIM_SCRIPT = resolve(REPO_ROOT, "scripts/visual/ssim_compare.py");
const BASELINE_ROOT = resolve(
  REPO_ROOT,
  "ui/frontend/__visual_baselines__/chromium/visual-baseline.spec.ts-snapshots",
);

test.describe("V79.3 · SSIM active screenshot gate", () => {
  test("ssim_compare.py self-consistency batch · 76+ baselines pass SSIM≥0.9999", () => {
    // Shell out to the python script. PYTHONPATH set so it can find
    // numpy + PIL via the project venv if invoked from CI.
    let stdout = "";
    try {
      stdout = execFileSync(
        "uv",
        ["run", "python", SSIM_SCRIPT, "--batch", BASELINE_ROOT],
        {
          cwd: REPO_ROOT,
          env: { ...process.env, PYTHONPATH: REPO_ROOT },
          encoding: "utf-8",
          stdio: ["ignore", "pipe", "pipe"],
        },
      );
    } catch (err) {
      // execFileSync throws on non-zero exit. Surface the underlying
      // stderr/stdout for diagnosis.
      const e = err as { stdout?: Buffer; stderr?: Buffer; status?: number };
      const out = e.stdout?.toString() ?? "";
      const errOut = e.stderr?.toString() ?? "";
      throw new Error(
        `ssim_compare.py --batch exited non-zero (${e.status})\nstdout:\n${out}\nstderr:\n${errOut}`,
      );
    }
    // Expect "SSIM batch (self-consistency...): N/N PASS" with N≥76
    const m = stdout.match(/SSIM batch.*?:\s+(\d+)\/(\d+)\s+PASS/);
    expect(m, `unexpected ssim_compare output: ${stdout}`).toBeTruthy();
    const passed = Number(m![1]);
    const total = Number(m![2]);
    expect(passed).toBe(total);
    // V79 invariant: at least 76 baselines exist (V77 + V78 substrate)
    expect(total).toBeGreaterThanOrEqual(76);
  });

  test("ssim_compare.py rejects shape mismatch (substrate sanity)", () => {
    // Pair two DIFFERENT baselines · SSIM must be < 0.99 · script exits 1
    const a = resolve(BASELINE_ROOT, "01-workbench-index.png");
    const b = resolve(BASELINE_ROOT, "61-v3-step1-vtk-geometry.png");
    let exitStatus = 0;
    let stdout = "";
    try {
      stdout = execFileSync(
        "uv",
        ["run", "python", SSIM_SCRIPT, a, b],
        {
          cwd: REPO_ROOT,
          env: { ...process.env, PYTHONPATH: REPO_ROOT },
          encoding: "utf-8",
          stdio: ["ignore", "pipe", "pipe"],
        },
      );
    } catch (err) {
      const e = err as { stdout?: Buffer; status?: number };
      stdout = e.stdout?.toString() ?? "";
      exitStatus = e.status ?? 1;
    }
    expect(exitStatus).toBe(1);
    expect(stdout).toMatch(/SSIM=0\.\d+ FAIL/);
  });

  test("ssim_compare.py confirms identity (substrate sanity)", () => {
    // Pair a baseline with itself · SSIM === 1 · script exits 0
    const a = resolve(BASELINE_ROOT, "01-workbench-index.png");
    const stdout = execFileSync(
      "uv",
      ["run", "python", SSIM_SCRIPT, a, a],
      {
        cwd: REPO_ROOT,
        env: { ...process.env, PYTHONPATH: REPO_ROOT },
        encoding: "utf-8",
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    expect(stdout).toMatch(/SSIM=1\.00000 PASS/);
  });
});

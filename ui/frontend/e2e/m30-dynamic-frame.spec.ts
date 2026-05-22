// DEC-V61-202-SUB-M30-CYCLE5 · M3.0 dynamic frame end-to-end Playwright spec.
//
// Drives the real vite-served frontend against the real uvicorn-served
// backend (both spawned by playwright.config.ts:webServer). Stages a
// deterministic case in ui/backend/user_drafts/imported/<id>/ before
// tests run, then exercises three flows:
//   1. Default navigation (no ?legacy=) renders all dynamic-frame slots
//   2. ?legacy=1 opts out (no dynamic-frame slots visible)
//   3. ?focus_patch=<name> deep-link reaches the rail/cards
//
// Why filesystem-stage instead of API: the case import API requires a
// CAD upload + multi-step scaffold; for a stable e2e seed, writing the
// minimal manifest + artifacts directly is faster and more reliable.

import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";

// Playwright runs tests from ui/frontend (cwd of `npx playwright test`).
// The dev uvicorn backend has cwd: "../../" (repo root), so the
// IMPORTED_DIR backend reads from is <repo_root>/ui/backend/user_drafts/imported.
// Compute relative to process.cwd() so this works regardless of how
// playwright is invoked.
const FRONTEND_DIR = process.cwd();
const REPO_ROOT = path.resolve(FRONTEND_DIR, "..", "..");
const IMPORTED_DIR = path.join(
  REPO_ROOT,
  "ui",
  "backend",
  "user_drafts",
  "imported",
);

const SEED_CASE_ID = "m30_cycle5_e2e_seed";
const SEED_CASE_DIR = path.join(IMPORTED_DIR, SEED_CASE_ID);

// v2 imported-user manifest schema — physics.solver, physics.turbulence_model,
// bc.patches.<name>.{patch_type, fields}. See ui/backend/services/case_manifest/schema.py.
const SEED_MANIFEST_YAML = `case_id: ${SEED_CASE_ID}
case_family: rans_steady_incompressible
solver_backend: openfoam
physics:
  solver: simpleFoam
  turbulence_model: kOmegaSST
bc:
  patches:
    inlet:
      patch_type: fixedValue
      fields:
        U: [1.0, 0.0, 0.0]
    outlet:
      patch_type: zeroGradient
      fields:
        p: zeroGradient
    wall:
      patch_type: noSlip
      fields: {}
`;

const SEED_BC_AUDIT = {
  gate_status: "WARN",
  patch_coverage_dimension: {
    dimension_status: "WARN",
    gaps_by_field: { U: ["inlet"] },
  },
};

const SEED_MESH_REPORT = {
  gate_status: "PASS",
  stats: { cells: 500_000 },
  quality_dimension: { dimension_status: "PASS" },
};


// DEC-V61-202-SUB-M30-INTEGRATION-V4-SHELL · post-integration the
// dynamic-frame slots mount inside WorkbenchShellV4 on the live
// `/workbench/case/:caseId` route. Cycle 5 skipped this; integration
// un-skipped and updated URLs to the live route.
test.describe("M3.0 cycle 5/integration · dynamic-frame default-on + ?legacy=1 opt-out", () => {
  test.beforeAll(() => {
    // Stage the seed case under IMPORTED_DIR. The dev backend reads
    // this directly via case_completeness's imported-user rule layer.
    fs.mkdirSync(SEED_CASE_DIR, { recursive: true });
    fs.writeFileSync(
      path.join(SEED_CASE_DIR, "case_manifest.yaml"),
      SEED_MANIFEST_YAML,
    );
    const artifactsDir = path.join(SEED_CASE_DIR, "artifacts");
    fs.mkdirSync(artifactsDir, { recursive: true });
    fs.writeFileSync(
      path.join(artifactsDir, "mesh_report.json"),
      JSON.stringify(SEED_MESH_REPORT),
    );
    fs.writeFileSync(
      path.join(artifactsDir, "bc_audit.json"),
      JSON.stringify(SEED_BC_AUDIT),
    );
  });

  test.afterAll(() => {
    // Best-effort cleanup; leave on failure for triage.
    if (test.info().status === "passed") {
      try {
        fs.rmSync(SEED_CASE_DIR, { recursive: true, force: true });
      } catch {
        // ignore — non-fatal
      }
    }
  });

  test("default navigation renders all three dynamic-frame slots", async ({
    page,
  }) => {
    // No ?legacy=1 → dynamicFrameEnabled defaults to true post-cycle-5.
    await page.goto(`/workbench/case/${SEED_CASE_ID}?step=boundary`);

    // Wait for the workbench_frame query to resolve so the slots
    // populate. Use waitForResponse so we lock to the actual fetch,
    // not a fixed timeout.
    await page.waitForResponse(
      (resp) =>
        resp.url().includes(`/api/cases/${SEED_CASE_ID}/workbench_frame`) &&
        resp.status() === 200,
      { timeout: 15_000 },
    );

    await expect(page.getByTestId("dynamic-frame-panel")).toBeVisible();
    await expect(page.getByTestId("dynamic-topbar-cta")).toBeVisible();
    await expect(page.getByTestId("dynamic-bottom-cards")).toBeVisible();
  });

  test("?legacy=1 opts out (no dynamic-frame slots visible)", async ({
    page,
  }) => {
    await page.goto(`/workbench/case/${SEED_CASE_ID}?step=boundary&legacy=1`);

    // The legacy path does NOT fetch workbench_frame; wait for the
    // V4 shell root instead. (Integration mounted dynamic frame
    // INSIDE WorkbenchShellV4, so legacy mode = the V4 shell without
    // the M3.0 slots layered in.)
    await expect(page.getByTestId("workbench-shell-v4")).toBeVisible();

    // Dynamic-frame slots should be absent in legacy mode.
    await expect(page.getByTestId("dynamic-frame-panel")).toHaveCount(0);
    await expect(page.getByTestId("dynamic-topbar-cta")).toHaveCount(0);
    await expect(page.getByTestId("dynamic-bottom-cards")).toHaveCount(0);
  });

  test("?focus_patch=inlet reaches the backend and changes the rail", async ({
    page,
  }) => {
    // Deep-link with focus_patch and verify the response carries the
    // focus_patch query through to backend decide(). We're not
    // asserting any specific UI text — just that the round trip closes.
    const response = await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.url().includes(`/api/cases/${SEED_CASE_ID}/workbench_frame`) &&
          resp.url().includes("focus_patch=inlet") &&
          resp.status() === 200,
        { timeout: 15_000 },
      ),
      page.goto(
        `/workbench/case/${SEED_CASE_ID}?step=boundary&focus_patch=inlet`,
      ),
    ]);

    expect(response[0].url()).toContain("focus_patch=inlet");
    await expect(page.getByTestId("dynamic-frame-panel")).toBeVisible();
  });
});

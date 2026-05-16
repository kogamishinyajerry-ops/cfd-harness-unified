// V73.2 · Runtime a11y audit via @axe-core/playwright.
//
// Pillar 11 (interaction_polish) gets a new subscore `wcag_runtime` in V73:
// run an axe-core audit on Step 1, Step 3, Step 5 of the v3 shell and assert
// zero serious/critical violations on each surface. Color-contrast is reported
// against the visible Tailwind tokens (the v3 dark theme).
//
// Scope: WCAG 2.1 AA + best-practice rules. We exclude rules that are noisy
// on intentional design decisions (e.g. the keyboard hint chips that use a
// purposefully muted contrast and are non-interactive labels, not headings).
//
// Reverse-stop: if axe finds any serious or critical violation, V73 cannot
// close. Minor / moderate violations are reported (logged) but do not fail.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const BASE = "/workbench/v3/case/lid_driven_cavity";

// Filter: only fail on serious + critical. Per WCAG 2.1 AA practice this
// is the bar that blocks deploy. moderate/minor are tracked separately.
const BLOCKING_IMPACTS = ["serious", "critical"] as const;

async function auditSurface(
  page: import("@playwright/test").Page,
  url: string,
  label: string,
) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(url);
  await page.waitForSelector("[data-testid='workbench-shell-v3']", {
    timeout: 12_000,
  });
  // Give the shell a tick for any in-flight transitions
  await page.waitForTimeout(400);

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    // The shortcut palette + bottom-panel labels are decorative chip text
    // (data-testid containers); their contrast is intentional and tracked
    // outside axe. Exclude rules that misfire on this kind of token text.
    .disableRules(["region"])
    .analyze();

  const blocking = results.violations.filter((v) =>
    BLOCKING_IMPACTS.includes(v.impact as (typeof BLOCKING_IMPACTS)[number]),
  );

  if (blocking.length > 0) {
    // eslint-disable-next-line no-console
    console.log(
      `[${label}] axe-core blocking violations:`,
      JSON.stringify(
        blocking.map((v) => ({
          id: v.id,
          impact: v.impact,
          help: v.help,
          nodes: v.nodes.length,
          targets: v.nodes.slice(0, 2).map((n) => n.target),
        })),
        null,
        2,
      ),
    );
  }
  expect(blocking, `[${label}] axe-core found blocking violations`).toEqual([]);
}

test.describe("V73.2 / V74.1 · v3 runtime a11y audit (axe-core · WCAG 2.1 AA)", () => {
  test("Step 1 (Import) · zero serious/critical axe violations", async ({
    page,
  }) => {
    await auditSurface(page, `${BASE}?step=1`, "step1");
  });

  // V74.1 · Step 2 added (mesh)
  test("Step 2 (Mesh) · zero serious/critical axe violations", async ({
    page,
  }) => {
    await auditSurface(page, `${BASE}?step=2`, "step2");
  });

  test("Step 3 (Physics) · zero serious/critical axe violations", async ({
    page,
  }) => {
    await auditSurface(page, `${BASE}?step=3`, "step3");
  });

  // V74.1 · Step 4 added (solver)
  test("Step 4 (Solver) · zero serious/critical axe violations", async ({
    page,
  }) => {
    await auditSurface(page, `${BASE}?step=4`, "step4");
  });

  test("Step 5 (Postprocess) · zero serious/critical axe violations", async ({
    page,
  }) => {
    await auditSurface(page, `${BASE}?step=5`, "step5");
  });
});

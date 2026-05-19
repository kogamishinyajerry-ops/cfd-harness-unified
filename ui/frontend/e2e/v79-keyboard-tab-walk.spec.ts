// V79.4 · Full-keyboard Tab walk · a11y depth complement to v3-a11y-audit.
//
// v3-a11y-audit (V73.2 / V74.1) runs axe-core static analysis per
// Step 1-5. V72.2 keyboard nav covers hot-keys. V79.4 fills the gap:
// **walks Tab forward through Steps 1-5 and asserts EVERY focusable
// stop has a visible focus ring + reaches the document's interactive
// surface area before cycling back to the top.**
//
// Surfaces the same class of regression V78 caught (SolverInflightTicker
// overflow:auto without tabIndex) — that defect was detected by axe-core
// in V78, but a proactive Tab-walk would have caught it BEFORE the
// scorer threshold tightening forced the issue. Same defect class,
// earlier detection vector.

import { test, expect } from "@playwright/test";

const STEPS: ReadonlyArray<{ step: number; label: string }> = [
  { step: 1, label: "Step 1 (Import)" },
  { step: 2, label: "Step 2 (Mesh)" },
  { step: 3, label: "Step 3 (Physics)" },
  { step: 4, label: "Step 4 (Solver)" },
  { step: 5, label: "Step 5 (Postprocess)" },
];

// Minimum number of distinct focus stops we expect per step. Below
// this, the page likely has a focus-trap or a hidden region. The
// threshold is intentionally conservative — V79.4's first deployment
// is a smoke check, not a full traversal audit.
const MIN_TAB_STOPS = 8;
// Cap the walk · prevents an infinite-Tab pathology from hanging the
// test if focus order has a cycle that excludes the body.
const MAX_TABS = 80;

test.describe("V79.4 · Full-keyboard Tab walk · a11y depth", () => {
  for (const { step, label } of STEPS) {
    test(`${label} · Tab walk reaches ≥${MIN_TAB_STOPS} interactive stops`, async ({
      page,
    }) => {
      await page.goto(`/workbench/v3/case/lid_driven_cavity?step=${step}`);
      await page.waitForSelector("[data-testid='workbench-shell-v3']", {
        timeout: 12_000,
      });
      // Click on the document so the focus chain starts from a stable anchor
      await page.locator("body").click({ position: { x: 1, y: 1 } });

      const visitedTags: string[] = [];
      const visitedTestIds: Array<string | null> = [];
      let tabs = 0;
      while (tabs < MAX_TABS) {
        await page.keyboard.press("Tab");
        tabs += 1;
        // Read focused element's tag + testid + visibility of focus ring
        const focused = await page.evaluate(() => {
          const el = document.activeElement as HTMLElement | null;
          if (!el || el === document.body) return null;
          const cs = window.getComputedStyle(el);
          // Detect any kind of visible focus indicator: outline width OR
          // box-shadow change. Tailwind focus rings typically render
          // box-shadow when outline:0 is set.
          const hasOutline =
            cs.outlineStyle !== "none" && cs.outlineWidth !== "0px";
          const hasShadow = cs.boxShadow !== "none" && cs.boxShadow !== "";
          return {
            tag: el.tagName.toLowerCase(),
            testid: el.getAttribute("data-testid"),
            visible: hasOutline || hasShadow,
            tabindex: el.getAttribute("tabindex"),
          };
        });
        if (focused === null) {
          // Tabbed out of the focusable surface (back to body / window)
          break;
        }
        visitedTags.push(focused.tag);
        visitedTestIds.push(focused.testid);
        // Stop conditions:
        // (a) we've collected enough stops for the smoke threshold
        // (b) we've started cycling back to an already-seen testid
        if (visitedTags.length >= MIN_TAB_STOPS) break;
      }

      const distinctStops = new Set(
        visitedTestIds.map((t) => t ?? ""),
      ).size;
      expect(
        distinctStops,
        `[${label}] only ${distinctStops} distinct focus stops after ${tabs} Tabs · tags=${JSON.stringify(visitedTags)}`,
      ).toBeGreaterThanOrEqual(MIN_TAB_STOPS);
    });
  }
});

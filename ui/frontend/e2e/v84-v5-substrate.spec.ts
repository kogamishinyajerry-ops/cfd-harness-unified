// V84.2 · V5 substrate e2e behavior proof
//
// V83 shipped V5.A-V5.D as vitest contract tests + 4 visual baselines
// (V84.1 added 80-83). This spec adds REAL-BROWSER behavior tests that
// vitest can't cover:
//   - cinematic auto-advance live wall-clock timing (vitest used fake timers)
//   - sandbox + failure-mode + provenance integrated with the live shell
//   - V83 reverse-stop verification in the browser (no mutating backend
//     calls during sandbox)
//
// Closes V83 retro Open Q #2.

import { test, expect, type Request } from "@playwright/test";

test.describe("V84.2 · V5 substrate live-browser proof", () => {
  test("V5.A sandbox mode · ?demo=2 mounts pill + does NOT call mutating routes", async ({
    page,
  }) => {
    // Capture all backend requests during sandbox traversal
    const mutatingRequests: { method: string; url: string }[] = [];
    page.on("request", (req: Request) => {
      const method = req.method();
      if (
        method === "POST" ||
        method === "PUT" ||
        method === "DELETE" ||
        method === "PATCH"
      ) {
        mutatingRequests.push({ method, url: req.url() });
      }
    });

    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1&demo=2");
    await page.waitForSelector("[data-testid='demo-sandbox-v5']", {
      timeout: 12_000,
    });
    await expect(page.getByTestId("sandbox-mode-pill")).toBeVisible();

    // Click through Steps 2-5 via the pipeline strip
    for (const step of [2, 3, 4, 5] as const) {
      const stepButton = page.getByTestId(`pipeline-step-${step}`);
      await stepButton.click();
      // The shell should reflect the new step
      await page.waitForFunction(
        (s) => {
          const sandbox = document.querySelector(
            "[data-testid='demo-sandbox-v5']",
          );
          return sandbox?.getAttribute("data-step-id") === String(s);
        },
        step,
        { timeout: 6_000 },
      );
    }

    // CRITICAL: zero mutating backend calls during the entire sandbox flow
    expect(mutatingRequests).toEqual([]);
  });

  test("V5.A sandbox exit clears ?demo param + unmounts pill", async ({
    page,
  }) => {
    await page.goto("/workbench/v3/case/lid_driven_cavity?step=1&demo=2");
    await page.waitForSelector("[data-testid='sandbox-mode-pill']", {
      timeout: 12_000,
    });
    await page.getByTestId("sandbox-exit").click();
    await expect(page.getByTestId("demo-sandbox-v5")).toHaveCount(0);
    expect(new URL(page.url()).searchParams.get("demo")).toBeNull();
  });

  test("V5.B failure-mode showcase · ?failmode=1 mounts 3 cards", async ({
    page,
  }) => {
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=2&tab=advisor&failmode=1",
    );
    await page.waitForSelector("[data-testid='failure-mode-showcase']", {
      timeout: 12_000,
    });
    for (let i = 1; i <= 3; i++) {
      await expect(page.getByTestId(`failure-card-${i}`)).toBeVisible();
    }
    // Footer reasserts V132
    const footer = await page.getByTestId("failure-mode-v132-footer").textContent();
    expect(footer).toMatch(/0 fixes applied/);
  });

  test("V5.B failure-mode is gated · NOT visible without ?failmode=1", async ({
    page,
  }) => {
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=2&tab=advisor",
    );
    await page.waitForSelector("[data-testid='workbench-shell-v3']", {
      timeout: 12_000,
    });
    await page.waitForTimeout(400);
    await expect(page.getByTestId("failure-mode-showcase")).toHaveCount(0);
  });

  test("V5.C cinematic mode · LIVE 12s auto-advance (vitest used fake timers)", async ({
    page,
  }) => {
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=1&demo=1&tour=1&cinema=1",
    );
    await page.waitForSelector("[data-testid='cinematic-mode-active']", {
      timeout: 12_000,
    });
    const banner = page.getByTestId("demo-banner");
    await expect(banner).toHaveAttribute("data-tour-step", "1");
    // Wait for the auto-advance · CINEMA_BEAT_MS = 12000ms · give some slack
    await page.waitForFunction(
      () =>
        document
          .querySelector("[data-testid='demo-banner']")
          ?.getAttribute("data-tour-step") === "2",
      undefined,
      { timeout: 15_000 },
    );
    expect(await banner.getAttribute("data-tour-step")).toBe("2");
  });

  test("V5.C pause stops auto-advance · resume restarts", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=1&demo=1&tour=1&cinema=1",
    );
    await page.waitForSelector("[data-testid='cinematic-pause']", {
      timeout: 12_000,
    });
    await page.getByTestId("cinematic-pause").click();
    await expect(page.getByTestId("cinematic-resume")).toBeVisible();
    // 13s elapses while paused — tour MUST NOT advance
    await page.waitForTimeout(13_000);
    expect(
      await page.getByTestId("demo-banner").getAttribute("data-tour-step"),
    ).toBe("1");
    // Resume + wait for advance
    await page.getByTestId("cinematic-resume").click();
    await page.waitForFunction(
      () =>
        document
          .querySelector("[data-testid='demo-banner']")
          ?.getAttribute("data-tour-step") === "2",
      undefined,
      { timeout: 15_000 },
    );
  });

  test("V5.D provenance card · only Finish triggers (Skip does NOT)", async ({
    page,
  }) => {
    // First test: Skip from middle should NOT trigger provenance
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=2&demo=1&tour=3",
    );
    await page.waitForSelector("[data-testid='demo-banner']", {
      timeout: 12_000,
    });
    await page.getByTestId("demo-banner-skip").click();
    await page.waitForTimeout(300);
    await expect(page.getByTestId("provenance-card")).toHaveCount(0);

    // Second test: Finish from last beat DOES trigger provenance
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=5&demo=1&tour=6",
    );
    await page.waitForSelector("[data-testid='demo-banner']", {
      timeout: 12_000,
    });
    await page.getByTestId("demo-banner-next").click();
    await expect(page.getByTestId("provenance-card")).toBeVisible();
    // 4 stats present
    for (const kind of ["cases", "steps", "commentary", "citations"]) {
      await expect(
        page.getByTestId(`provenance-stats-${kind}`),
      ).toBeVisible();
    }
  });

  test("V5.D provenance sandbox CTA · sets ?demo=2 + closes card", async ({
    page,
  }) => {
    // Land on last beat then Finish to surface the card
    await page.goto(
      "/workbench/v3/case/lid_driven_cavity?step=5&demo=1&tour=6",
    );
    await page.waitForSelector("[data-testid='demo-banner']", {
      timeout: 12_000,
    });
    await page.getByTestId("demo-banner-next").click();
    await page.waitForSelector("[data-testid='provenance-card']", {
      timeout: 6_000,
    });
    await page.getByTestId("provenance-sandbox-cta").click();
    await expect(page.getByTestId("provenance-card")).toHaveCount(0);
    expect(new URL(page.url()).searchParams.get("demo")).toBe("2");
    // Sandbox pill should now be present
    await expect(page.getByTestId("sandbox-mode-pill")).toBeVisible();
  });
});

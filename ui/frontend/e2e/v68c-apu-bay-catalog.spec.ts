// V68-C.3 · case_002a APU bay catalog entry e2e against real backend.
//
// Asserts the V68-C.3 invariant end-to-end:
//   1. GET /api/cases includes case_002a (catalog grew 10→11)
//   2. case_002a carries case_kind=imported_user + gold_pending=true
//   3. /workbench index renders the gold-pending badge for case_002a
//
// Real fastapi backend serves whitelist.yaml so this is genuine
// integration coverage — not msw-mocked.

import { test, expect } from "@playwright/test";

const API_BASE =
  process.env.PLAYWRIGHT_API_BASE ?? "http://127.0.0.1:8001";

test.describe("V68-C.3 · case_002a APU bay catalog entry (real backend)", () => {
  test("GET /api/cases returns 11 entries including case_002a with gold_pending=true", async ({
    request,
  }) => {
    const res = await request.get(`${API_BASE}/api/cases`);
    expect(res.status()).toBe(200);
    const body = (await res.json()) as Array<{
      case_id: string;
      case_kind?: string;
      gold_pending?: boolean;
      has_gold_standard?: boolean;
    }>;
    expect(body.length).toBeGreaterThanOrEqual(11);
    const apu = body.find((e) => e.case_id === "case_002a");
    expect(apu, "case_002a missing from /api/cases").toBeDefined();
    expect(apu!.case_kind).toBe("imported_user");
    expect(apu!.gold_pending).toBe(true);
    expect(apu!.has_gold_standard).toBe(false);
  });

  test("workbench index renders ⏳ gold pending badge for case_002a", async ({
    page,
  }) => {
    await page.goto("/workbench");
    await page
      .waitForLoadState("networkidle", { timeout: 8_000 })
      .catch(() => {});
    const card = page.getByTestId("case-card-case_002a");
    await expect(card).toBeAttached({ timeout: 12_000 });
    const badge = page.getByTestId("case-card-gold-pending-badge");
    await expect(badge).toBeAttached();
    const disclaimer = page.getByTestId(
      "case-card-gold-pending-disclaimer-case_002a",
    );
    await expect(disclaimer).toBeAttached();
    const disclaimerText = (await disclaimer.textContent()) ?? "";
    expect(disclaimerText).toMatch(/gold pending|trust gate stays PENDING/i);
  });
});

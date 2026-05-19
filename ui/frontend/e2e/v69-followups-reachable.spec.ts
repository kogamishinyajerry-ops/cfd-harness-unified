// V69.4 · followups directory reachability + content verification.
//
// V69 introduced two followup tracking files (V69-FOLLOWUP-1 and
// V69-FOLLOWUP-2). This spec verifies they're parseable + carry the
// expected schema fields so future arcs can pick them up programmatically.

import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = resolve(__dirname, "../../..");
const FOLLOWUPS_DIR = resolve(REPO_ROOT, ".planning/followups");

test.describe("V69.4 · followups schema reachability", () => {
  test("V69 opened ≥2 followup files in .planning/followups/", async () => {
    const files = readdirSync(FOLLOWUPS_DIR).filter((f) => f.endsWith(".md"));
    const v69 = files.filter((f) => f.includes("v69"));
    expect(v69.length).toBeGreaterThanOrEqual(2);
  });

  test("each V69 followup carries required frontmatter schema", async () => {
    const required = [
      "followup_id",
      "title",
      "opened",
      "opened_by",
      "priority",
      "status",
    ];
    const files = readdirSync(FOLLOWUPS_DIR)
      .filter((f) => f.endsWith(".md") && f.includes("v69"));
    expect(files.length).toBeGreaterThanOrEqual(2);
    for (const file of files) {
      const text = readFileSync(resolve(FOLLOWUPS_DIR, file), "utf8");
      // Quick frontmatter probe — lines between first two --- markers
      const fmMatch = text.match(/^---\n([\s\S]*?)\n---/);
      expect(fmMatch, `${file}: missing frontmatter`).not.toBeNull();
      const fm = fmMatch![1];
      for (const field of required) {
        expect(fm, `${file}: missing ${field}`).toContain(`${field}:`);
      }
    }
  });
});

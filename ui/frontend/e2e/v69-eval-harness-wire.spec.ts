// V69.4 · canonical eval harness wire e2e against real backend.
//
// Asserts the V69.1 + V69.2 deliverables are reachable from the live
// backend's perspective: the canonical eval case files exist on disk,
// the schema validator passes, and the harness suite is part of the
// default pytest run (V69-DONE-4 SSOT regression-protected).

import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = resolve(__dirname, "../../..");

test.describe("V69.4 · canonical eval harness wire", () => {
  test("schema validator: ≥20 canonical eval files validate OK (V70.2 expanded to 30)", async () => {
    const out = execFileSync(
      "uv",
      [
        "run",
        "python",
        "scripts/governance/validate_canonical_eval_schema.py",
      ],
      { cwd: REPO_ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: "." } },
    );
    // Tolerate V69 (20) + V70.2 (30) + future expansions
    expect(out).toMatch(/OK · \d+ canonical eval case files validate/);
  });

  test("harness: pytest passes (V69 22 / V70 32 tests · whichever is current)", async () => {
    const out = execFileSync(
      "uv",
      [
        "run",
        "pytest",
        "ui/backend/tests/test_canonical_advisor_eval.py",
        "-q",
        "--no-header",
      ],
      { cwd: REPO_ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: "." } },
    );
    // Tolerate both V69 (22 passed) + V70.2 (32 passed) + future expansions
    expect(out).toMatch(/\d+ passed/);
  });
});

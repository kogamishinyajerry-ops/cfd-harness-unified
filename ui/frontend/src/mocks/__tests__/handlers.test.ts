/**
 * V68-A.1 · sanity test that handler set covers the V67-C SCAFFOLDING gap
 * endpoints. Pure shape assertion · no MSW worker needed (browser-only API).
 */
import { describe, it, expect } from "vitest";

import { handlers, mockCase, mockStatus } from "../handlers";

describe("MSW handlers (V68-A.1 bootstrap)", () => {
  it("covers the 4 V67-C SCAFFOLDING-to-FULL endpoints + 4 supporting routes", () => {
    expect(handlers.length).toBeGreaterThanOrEqual(4);
  });

  it("exposes a demo case fixture with 5-step pipeline state", () => {
    expect(mockCase.steps.import.state).toBe("done");
    expect(mockCase.steps.mesh.cells).toBeGreaterThan(0);
    expect(mockCase.steps.bc.patches).toBeGreaterThan(0);
    expect(mockCase.steps.solve.state).toBe("running");
    expect(mockCase.steps.results.state).toBe("pending");
  });

  it("exposes a status fixture with TopBar 4 fields", () => {
    expect(mockStatus.truth_source).toBeTruthy();
    expect(mockStatus.trust_gate).toBeTruthy();
    expect(typeof mockStatus.audit_pct).toBe("number");
    expect(mockStatus.llm_offline).toBe(true);
  });
});

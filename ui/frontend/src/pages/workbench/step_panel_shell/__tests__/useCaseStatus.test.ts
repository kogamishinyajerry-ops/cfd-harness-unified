/**
 * V68-A.2 · useCaseStatus normalization tests (pure-function path · no
 * React Query / fetch). Verifies backend snake_case → TopBar camelCase
 * + safe-default fallback semantics.
 */
import { describe, it, expect } from "vitest";

import { normalizeCaseStatus } from "../useCaseStatus";

describe("normalizeCaseStatus (V68-A.2)", () => {
  it("returns blueprint-safe defaults when raw is undefined", () => {
    const s = normalizeCaseStatus("case-1", undefined);
    expect(s.caseId).toBe("case-1");
    expect(s.truthSource).toBe("unknown");
    expect(s.trustGate).toBe("PENDING");
    expect(s.auditPct).toBe(null);
    // V130 invariant: default to llmOffline=true when unspecified.
    expect(s.llmOffline).toBe(true);
  });

  it("maps audit-passing trust_gate → PASS", () => {
    const s = normalizeCaseStatus("c", { trust_gate: "audit-passing" });
    expect(s.trustGate).toBe("PASS");
  });

  it("maps audit-failing → FAIL and clamps invalid audit_pct → null", () => {
    const s = normalizeCaseStatus("c", {
      trust_gate: "audit-failing",
      audit_pct: 150,
    });
    expect(s.trustGate).toBe("FAIL");
    expect(s.auditPct).toBe(null);
  });

  it("passes through valid audit_pct in [0,100]", () => {
    const s = normalizeCaseStatus("c", { audit_pct: 87 });
    expect(s.auditPct).toBe(87);
  });

  it("maps msw-mock truth_source → mock", () => {
    const s = normalizeCaseStatus("c", { truth_source: "msw-mock" });
    expect(s.truthSource).toBe("mock");
  });

  it("maps openfoam-native (kebab) and openfoam_native (snake) → openfoam_native", () => {
    expect(normalizeCaseStatus("c", { truth_source: "openfoam-native" }).truthSource).toBe(
      "openfoam_native",
    );
    expect(normalizeCaseStatus("c", { truth_source: "openfoam_native" }).truthSource).toBe(
      "openfoam_native",
    );
  });

  it("only flips llmOffline to false when explicit false (V130 invariant)", () => {
    expect(normalizeCaseStatus("c", { llm_offline: false }).llmOffline).toBe(false);
    expect(normalizeCaseStatus("c", { llm_offline: true }).llmOffline).toBe(true);
    expect(normalizeCaseStatus("c", {}).llmOffline).toBe(true);
    // V130: a missing/null llm_offline still defaults to true (offline-first).
    expect(normalizeCaseStatus("c", { llm_offline: null }).llmOffline).toBe(true);
  });

  it("ignores unknown trust_gate strings and falls to PENDING", () => {
    const s = normalizeCaseStatus("c", { trust_gate: "garbage-value" });
    expect(s.trustGate).toBe("PENDING");
  });

  it("passes through last_action / validation when present, null otherwise", () => {
    const s = normalizeCaseStatus("c", {
      last_action: "imported geom.stl",
      validation: "mesh OK",
    });
    expect(s.lastAction).toBe("imported geom.stl");
    expect(s.validation).toBe("mesh OK");
    const empty = normalizeCaseStatus("c", {});
    expect(empty.lastAction).toBe(null);
    expect(empty.validation).toBe(null);
  });
});

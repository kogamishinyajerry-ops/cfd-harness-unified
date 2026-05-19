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

describe("normalizeCaseStatus · V68-B.2 real-backend /completeness shape", () => {
  it("derives truthSource=openfoam_native from case_kind='whitelist'", () => {
    const s = normalizeCaseStatus("lid_driven_cavity", {
      case_kind: "whitelist",
      ready_for_archive: false,
      percentage: 93.8,
    });
    expect(s.truthSource).toBe("openfoam_native");
  });

  it("derives truthSource=unknown for case_kind='imported_user'", () => {
    const s = normalizeCaseStatus("c", { case_kind: "imported_user" });
    expect(s.truthSource).toBe("unknown");
  });

  it("derives trustGate=PASS when ready_for_archive=true", () => {
    const s = normalizeCaseStatus("c", {
      case_kind: "whitelist",
      ready_for_archive: true,
      blocked_by_critical: 0,
    });
    expect(s.trustGate).toBe("PASS");
  });

  it("derives trustGate=FAIL when blocked_by_critical > 0", () => {
    const s = normalizeCaseStatus("c", {
      case_kind: "whitelist",
      ready_for_archive: false,
      blocked_by_critical: 1,
    });
    expect(s.trustGate).toBe("FAIL");
  });

  it("derives trustGate=PASS_WITH_DISCLAIMER when not archive-ready and no critical blockers", () => {
    const s = normalizeCaseStatus("c", {
      case_kind: "whitelist",
      ready_for_archive: false,
      blocked_by_critical: 0,
    });
    expect(s.trustGate).toBe("PASS_WITH_DISCLAIMER");
  });

  it("derives auditPct from percentage field (93.8 from real backend)", () => {
    const s = normalizeCaseStatus("lid_driven_cavity", {
      case_kind: "whitelist",
      percentage: 93.8,
    });
    expect(s.auditPct).toBe(93.8);
  });

  it("clamps invalid percentage to null (defense against ill-shaped payload)", () => {
    expect(normalizeCaseStatus("c", { percentage: 150 }).auditPct).toBe(null);
    expect(normalizeCaseStatus("c", { percentage: -1 }).auditPct).toBe(null);
  });

  it("V68-A legacy fast-path wins over V68-B derivation when both present", () => {
    // truth_source (legacy) wins over case_kind (V68-B)
    const s = normalizeCaseStatus("c", {
      truth_source: "msw-mock",
      case_kind: "whitelist",
    });
    expect(s.truthSource).toBe("mock");
    // audit_pct (legacy) wins over percentage (V68-B)
    const s2 = normalizeCaseStatus("c", {
      audit_pct: 42,
      percentage: 93.8,
    });
    expect(s2.auditPct).toBe(42);
  });

  it("real-backend lid_driven_cavity completeness fixture maps to expected status", () => {
    // Snapshot of real backend response for lid_driven_cavity (Phase-0 contract).
    const s = normalizeCaseStatus("lid_driven_cavity", {
      case_id: "lid_driven_cavity",
      case_kind: "whitelist",
      ready_for_archive: false,
      blocked_by_critical: 1,
      present_count: 15,
      total_count: 16,
      percentage: 93.8,
    });
    expect(s.caseId).toBe("lid_driven_cavity");
    expect(s.truthSource).toBe("openfoam_native");
    expect(s.trustGate).toBe("FAIL"); // 1 critical block
    expect(s.auditPct).toBe(93.8);
    expect(s.llmOffline).toBe(true);
  });
});

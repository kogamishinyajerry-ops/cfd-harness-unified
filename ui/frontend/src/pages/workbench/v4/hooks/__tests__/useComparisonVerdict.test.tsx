/**
 * DEC-V61-205 (M5 C4) · useComparisonVerdict state contract.
 *
 * Codex R2 P2 regression guard: a DISABLED query (no run to compare — an
 * unsolved or failed-only case passes runLabel=null) must resolve to the
 * honest "none" state, NOT a perpetual "loading" that would strand the Post
 * surfaces in "对比中…"/"…". "loading" is reserved for an enabled fetch in
 * flight.
 */
import { describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";

import { useComparisonVerdict } from "../useComparisonVerdict";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return createElement(QueryClientProvider, { client: qc }, children);
}

describe("useComparisonVerdict disabled-state contract (R2 P2)", () => {
  it("resolves to 'none' (not 'loading') when there is no run to compare", () => {
    const { result } = renderHook(
      () => useComparisonVerdict("case-x", null),
      { wrapper },
    );
    expect(result.current.state).toBe("none");
    expect(result.current.state).not.toBe("loading");
    expect(result.current.level).toBeNull();
  });

  it("resolves to 'none' when the caseId itself is missing", () => {
    const { result } = renderHook(
      () => useComparisonVerdict(null, "run-1"),
      { wrapper },
    );
    expect(result.current.state).toBe("none");
  });
});

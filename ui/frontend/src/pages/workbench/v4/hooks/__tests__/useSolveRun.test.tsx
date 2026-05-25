// DEC-V61-204 · M4 cycle 2 · useSolveRun mutation tests.

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const apiMock = vi.hoisted(() => ({
  solve: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, solve: apiMock.solve },
  };
});

import { useSolveRun } from "../useSolveRun";
import type { SolveSummary } from "@/types/case_solve";

const SUMMARY: SolveSummary = {
  case_id: "test_case",
  end_time_reached: 100,
  last_initial_residual_p: 8.7e-4,
  last_initial_residual_U: [3.2e-4, 2.9e-4, null],
  last_continuity_error: 1.1e-6,
  n_time_steps_written: 5,
  time_directories: ["0", "100"],
  wall_time_s: 42.3,
  converged: true,
};

function TestHarness({ caseId }: { caseId: string | null | undefined }) {
  const run = useSolveRun(caseId);
  return (
    <div>
      <button type="button" data-testid="trigger" onClick={() => run.runSolve()}>
        {run.isRunning ? "running" : "idle"}
      </button>
      <span data-testid="summary">{run.summary?.wall_time_s ?? "—"}</span>
      <span data-testid="error">{run.error?.message ?? "—"}</span>
    </div>
  );
}

function renderHarness(caseId: string | null | undefined = "test_case") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    ...render(
      <QueryClientProvider client={qc}>
        <TestHarness caseId={caseId} />
      </QueryClientProvider>,
    ),
    qc,
  };
}

describe("useSolveRun", () => {
  beforeEach(() => {
    // The hoisted apiMock.solve is shared across tests; clear call
    // history so the leakage-sensitive assertions below (not-called /
    // called-once) see only this test's invocations.
    vi.clearAllMocks();
  });

  it("calls api.solve(caseId) on runSolve", async () => {
    apiMock.solve.mockResolvedValueOnce(SUMMARY);
    renderHarness();
    await userEvent.click(screen.getByTestId("trigger"));
    await waitFor(() => {
      expect(apiMock.solve).toHaveBeenCalledWith("test_case");
    });
    await waitFor(() => {
      expect(screen.getByTestId("summary").textContent).toBe("42.3");
    });
  });

  it("invalidates the post-run V4 queries on success", async () => {
    apiMock.solve.mockResolvedValueOnce(SUMMARY);
    const { qc } = renderHarness();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");
    await userEvent.click(screen.getByTestId("trigger"));
    await waitFor(() => {
      for (const prefix of [
        "v4-residual-series",
        "v4-ctx-runs",
        "v4-ctx-detail",
        "v4-advisor-runs",
        "v4-report-bundle",
      ]) {
        expect(invalidateSpy).toHaveBeenCalledWith({
          queryKey: [prefix, "test_case"],
        });
      }
    });
  });

  it("surfaces the error message when the solve fails", async () => {
    apiMock.solve.mockRejectedValueOnce(new Error("solver exited 1"));
    renderHarness();
    await userEvent.click(screen.getByTestId("trigger"));
    await waitFor(() => {
      expect(screen.getByTestId("error").textContent).toBe("solver exited 1");
    });
  });

  it("does not call api.solve when no case is selected", async () => {
    renderHarness(null);
    await userEvent.click(screen.getByTestId("trigger"));
    // give any async mutation a tick to (not) fire
    await new Promise((r) => setTimeout(r, 20));
    expect(apiMock.solve).not.toHaveBeenCalled();
  });

  it("ignores a second click while a run is in flight (no double-solve)", async () => {
    let resolveSolve: (s: SolveSummary) => void = () => {};
    apiMock.solve.mockImplementationOnce(
      () =>
        new Promise<SolveSummary>((res) => {
          resolveSolve = res;
        }),
    );
    renderHarness();
    const trigger = screen.getByTestId("trigger");
    await userEvent.click(trigger);
    await waitFor(() => expect(trigger.textContent).toBe("running"));
    await userEvent.click(trigger); // second click while pending
    resolveSolve(SUMMARY);
    await waitFor(() => expect(trigger.textContent).toBe("idle"));
    expect(apiMock.solve).toHaveBeenCalledTimes(1);
  });
});

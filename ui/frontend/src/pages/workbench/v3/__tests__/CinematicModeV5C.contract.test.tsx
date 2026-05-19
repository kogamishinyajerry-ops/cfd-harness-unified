/**
 * V83.4 · CinematicMode (V5.C) contract test · DemoBannerV4 extension
 *
 * Asserts the V5.C contract from .planning/blueprints/v5/INDEX.md:
 *   - ?demo=1 alone does NOT activate cinematic
 *   - ?demo=1&cinema=1 BOTH set activates cinematic-mode-active pill
 *   - Pause button toggles between cinematic-pause and cinematic-resume
 *   - Auto-advance fires after CINEMA_BEAT_MS (12s) → tour-step increments
 *   - Pausing stops auto-advance · resuming restarts
 *   - prefers-reduced-motion: reduce disables auto-advance entirely
 *   - Back button decrements tour-step
 *   - Exit-cinema removes only ?cinema, preserves ?demo+?tour
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useSearchParams } from "react-router-dom";

import { DemoBannerV4 } from "../components/DemoBannerV4";

function Harness({ initial }: { initial: string }) {
  function ParamProbe() {
    const [params] = useSearchParams();
    return (
      <span data-testid="param-probe">{params.toString()}</span>
    );
  }
  return (
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route
          path="/"
          element={
            <>
              <DemoBannerV4 />
              <ParamProbe />
            </>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("CinematicMode V5.C · V83.4", () => {
  beforeEach(() => {
    // Default: matchMedia returns reduced-motion=false
    if (typeof window !== "undefined") {
      Object.defineProperty(window, "matchMedia", {
        configurable: true,
        value: (query: string) => ({
          matches: false,
          media: query,
          onchange: null,
          addEventListener: () => {},
          removeEventListener: () => {},
          addListener: () => {},
          removeListener: () => {},
          dispatchEvent: () => false,
        }),
      });
    }
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("?demo=1 alone (no cinema) does NOT show cinematic-mode-active", async () => {
    render(<Harness initial="/?demo=1&tour=1" />);
    // Wait for the mount effect to flip mounted=true
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("demo-banner")).toBeInTheDocument();
    expect(screen.queryByTestId("cinematic-mode-active")).not.toBeInTheDocument();
  });

  it("?demo=1&cinema=1 activates cinematic pill + pause/back/exit controls", async () => {
    render(<Harness initial="/?demo=1&tour=1&cinema=1" />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("cinematic-mode-active")).toBeInTheDocument();
    expect(screen.getByTestId("cinematic-pause")).toBeInTheDocument();
    expect(screen.getByTestId("cinematic-back")).toBeInTheDocument();
    expect(screen.getByTestId("cinematic-exit")).toBeInTheDocument();
    expect(screen.getByTestId("cinematic-progress")).toBeInTheDocument();
  });

  it("pause toggles between cinematic-pause and cinematic-resume", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Harness initial="/?demo=1&tour=1&cinema=1" />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("cinematic-pause")).toBeInTheDocument();
    await user.click(screen.getByTestId("cinematic-pause"));
    expect(screen.getByTestId("cinematic-resume")).toBeInTheDocument();
    expect(screen.queryByTestId("cinematic-pause")).not.toBeInTheDocument();
    // Progress indicator hidden when paused
    expect(screen.queryByTestId("cinematic-progress")).not.toBeInTheDocument();
  });

  it("auto-advance fires after CINEMA_BEAT_MS (12000ms)", async () => {
    render(<Harness initial="/?demo=1&tour=1&cinema=1" />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("demo-banner").getAttribute("data-tour-step")).toBe(
      "1",
    );
    await act(async () => {
      vi.advanceTimersByTime(12_100);
    });
    expect(screen.getByTestId("demo-banner").getAttribute("data-tour-step")).toBe(
      "2",
    );
  });

  it("pause stops auto-advance · resume restarts it", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Harness initial="/?demo=1&tour=1&cinema=1" />);
    await act(async () => {
      await Promise.resolve();
    });
    await user.click(screen.getByTestId("cinematic-pause"));
    // 12s elapses while paused · should NOT advance
    await act(async () => {
      vi.advanceTimersByTime(12_100);
    });
    expect(screen.getByTestId("demo-banner").getAttribute("data-tour-step")).toBe(
      "1",
    );
    await user.click(screen.getByTestId("cinematic-resume"));
    await act(async () => {
      vi.advanceTimersByTime(12_100);
    });
    expect(screen.getByTestId("demo-banner").getAttribute("data-tour-step")).toBe(
      "2",
    );
  });

  it("prefers-reduced-motion: reduce disables auto-advance + hides controls", async () => {
    // Override matchMedia to return reduced-motion=true
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: (query: string) => ({
        matches: query.includes("prefers-reduced-motion"),
        media: query,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
      }),
    });

    render(<Harness initial="/?demo=1&tour=1&cinema=1" />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("cinematic-mode-active")).toBeInTheDocument();
    // Auto-advance disabled · pause/back/exit hidden · only manual Next/Skip
    expect(screen.queryByTestId("cinematic-pause")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cinematic-back")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cinematic-exit")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cinematic-progress")).not.toBeInTheDocument();
    // 12s elapses · NO advance because reduced-motion
    await act(async () => {
      vi.advanceTimersByTime(12_100);
    });
    expect(screen.getByTestId("demo-banner").getAttribute("data-tour-step")).toBe(
      "1",
    );
    expect(
      screen.getByTestId("demo-banner").getAttribute("data-reduced-motion"),
    ).toBe("true");
  });

  it("exit-cinema removes ?cinema but keeps ?demo and ?tour (graceful drop)", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Harness initial="/?demo=1&tour=2&cinema=1" />);
    await act(async () => {
      await Promise.resolve();
    });
    await user.click(screen.getByTestId("cinematic-exit"));
    const params = screen.getByTestId("param-probe").textContent ?? "";
    expect(params).toMatch(/demo=1/);
    expect(params).toMatch(/tour=2/);
    expect(params).not.toMatch(/cinema/);
    // Banner still mounted (V4 tour mode still active)
    expect(screen.getByTestId("demo-banner")).toBeInTheDocument();
  });

  it("back button decrements tour-step (when not on step 1)", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Harness initial="/?demo=1&tour=3&cinema=1" />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("demo-banner").getAttribute("data-tour-step")).toBe(
      "3",
    );
    await user.click(screen.getByTestId("cinematic-back"));
    expect(screen.getByTestId("demo-banner").getAttribute("data-tour-step")).toBe(
      "2",
    );
  });

  it("back button is disabled at tour-step 1", async () => {
    render(<Harness initial="/?demo=1&tour=1&cinema=1" />);
    await act(async () => {
      await Promise.resolve();
    });
    const back = screen.getByTestId("cinematic-back") as HTMLButtonElement;
    expect(back.disabled).toBe(true);
  });
});

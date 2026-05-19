/**
 * V85.5 · V6.D Bridge Truth-Gate Disclosure contract test
 *
 * Asserts the V6.D contract from .planning/blueprints/v6/INDEX.md:
 *   - Renders nothing when artifact is null OR ?bridge absent
 *   - When active: pill "LIVE DATA · advisor in passive mode · no AI mutation"
 *   - Provenance line: case_id · run_id · exit code · audit-package href
 *   - "× exit to curated" button clears ?bridge query param (URL state only,
 *     no backend mutation)
 *   - Failed run renders exit code in accent color (data attribute mirrors)
 *   - V130 invariant: only 1 button (exit) · zero form/input/select
 */
import { describe, expect, it } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { BridgeModeShowcase } from "../components/BridgeModeShowcase";
import type { BridgeArtifact } from "@/data/run_artifact_reader";

const SUCCESS_ARTIFACT: BridgeArtifact = {
  case_id: "lid_driven_cavity",
  run_id: "2026-04-27T10-01-18Z",
  started_at: "2026-04-27T10:01:18Z",
  duration_s: 2476.66,
  success: true,
  exit_code: 0,
  verdict_summary: "PASS",
  failure_category: null,
};

const FAILED_ARTIFACT: BridgeArtifact = {
  case_id: "lid_driven_cavity",
  run_id: "2026-04-27T10-42-35Z",
  started_at: "2026-04-27T10:42:35Z",
  duration_s: 47.3,
  success: false,
  exit_code: 1,
  verdict_summary: "FAIL",
  failure_category: "solver_diverged",
};

function Harness({
  bridge = true,
  artifact = SUCCESS_ARTIFACT as BridgeArtifact | null,
  bundleId = null as string | null,
}) {
  const path = bridge ? "/?bridge=1" : "/";
  return (
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/"
          element={
            <BridgeModeShowcase artifact={artifact} bundleId={bundleId} />
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("BridgeModeShowcase contract · V85.5 · V6.D", () => {
  it("renders nothing when ?bridge is absent", () => {
    render(<Harness bridge={false} artifact={SUCCESS_ARTIFACT} />);
    expect(screen.queryByTestId("bridge-mode-showcase")).not.toBeInTheDocument();
  });

  it("renders nothing when artifact is null (even with ?bridge=1)", () => {
    render(<Harness bridge artifact={null} />);
    expect(screen.queryByTestId("bridge-mode-showcase")).not.toBeInTheDocument();
  });

  it("renders pill + provenance when ?bridge=1 + artifact present", () => {
    render(<Harness bridge artifact={SUCCESS_ARTIFACT} />);
    expect(screen.getByTestId("bridge-mode-showcase")).toBeInTheDocument();
    expect(screen.getByTestId("bridge-mode-pill")).toBeInTheDocument();
    expect(screen.getByTestId("bridge-exit")).toBeInTheDocument();
    expect(screen.getByTestId("bridge-provenance-line")).toBeInTheDocument();
  });

  it("pill text declares LIVE DATA + passive mode + no AI mutation", () => {
    render(<Harness bridge artifact={SUCCESS_ARTIFACT} />);
    const pill = screen.getByTestId("bridge-mode-pill");
    expect(pill.textContent).toMatch(/LIVE DATA/);
    expect(pill.textContent).toMatch(/advisor in passive mode/);
    expect(pill.textContent).toMatch(/no AI mutation/);
  });

  it("provenance line includes case_id + run_id + exit code", () => {
    render(<Harness bridge artifact={SUCCESS_ARTIFACT} />);
    expect(screen.getByTestId("bridge-provenance-case").textContent).toMatch(
      /lid_driven_cavity/,
    );
    expect(screen.getByTestId("bridge-provenance-run").textContent).toMatch(
      /2026-04-27T10-01-18Z/,
    );
    expect(screen.getByTestId("bridge-provenance-exit").textContent).toMatch(/0/);
  });

  it("failed artifact surfaces exit=1 in the provenance line", () => {
    render(<Harness bridge artifact={FAILED_ARTIFACT} />);
    expect(screen.getByTestId("bridge-provenance-exit").textContent).toMatch(/1/);
    const root = screen.getByTestId("bridge-mode-showcase");
    expect(root.getAttribute("data-artifact-success")).toBe("false");
    expect(root.getAttribute("data-run-id")).toBe("2026-04-27T10-42-35Z");
  });

  it("audit-package link surfaces when bundleId provided", () => {
    render(<Harness bridge artifact={SUCCESS_ARTIFACT} bundleId="bundle_abc" />);
    const auditLink = screen.getByTestId("bridge-provenance-audit");
    expect(auditLink).toBeInTheDocument();
    expect(auditLink.getAttribute("href")).toBe(
      "/api/audit-packages/bundle_abc/manifest.json",
    );
    expect(auditLink.getAttribute("target")).toBe("_blank");
    expect(auditLink.getAttribute("rel")).toContain("noopener");
  });

  it("audit link is absent when bundleId is null", () => {
    render(<Harness bridge artifact={SUCCESS_ARTIFACT} bundleId={null} />);
    expect(
      screen.queryByTestId("bridge-provenance-audit"),
    ).not.toBeInTheDocument();
  });

  it("exit button clears ?bridge query param (URL state only · no mutation)", async () => {
    const user = userEvent.setup();
    render(<Harness bridge artifact={SUCCESS_ARTIFACT} />);
    expect(screen.getByTestId("bridge-mode-showcase")).toBeInTheDocument();
    await act(async () => {
      await user.click(screen.getByTestId("bridge-exit"));
    });
    // After exit: showcase unmounts (bridge param gone → active=false)
    expect(screen.queryByTestId("bridge-mode-showcase")).not.toBeInTheDocument();
  });

  it("V130: only 1 button (exit) + zero form/input/select", () => {
    render(<Harness bridge artifact={SUCCESS_ARTIFACT} bundleId="b1" />);
    const root = screen.getByTestId("bridge-mode-showcase");
    const buttons = root.querySelectorAll("button");
    expect(buttons.length).toBe(1);
    expect(buttons[0].getAttribute("data-testid")).toBe("bridge-exit");
    expect(root.querySelectorAll("form").length).toBe(0);
    expect(root.querySelectorAll("input").length).toBe(0);
    expect(root.querySelectorAll("textarea").length).toBe(0);
    expect(root.querySelectorAll("select").length).toBe(0);
  });

  it("data attributes mirror artifact for V6.C + e2e inspection", () => {
    render(<Harness bridge artifact={FAILED_ARTIFACT} />);
    const root = screen.getByTestId("bridge-mode-showcase");
    expect(root.getAttribute("data-case-id")).toBe("lid_driven_cavity");
    expect(root.getAttribute("data-run-id")).toBe("2026-04-27T10-42-35Z");
    expect(root.getAttribute("data-artifact-success")).toBe("false");
  });
});

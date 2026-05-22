// DEC-V61-202-SUB-M30-CYCLE1 · DynamicViewportOverlays tests.

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { DynamicViewportOverlays } from "../DynamicViewportOverlays";
import type { ViewportOverlay } from "@/types/workbench_frame";

describe("DynamicViewportOverlays", () => {
  it("renders nothing when empty", () => {
    const { container } = render(<DynamicViewportOverlays overlays={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders patch_highlight overlay with target label", () => {
    const overlays: ViewportOverlay[] = [
      {
        kind: "patch_highlight",
        target: "inlet",
        severity: "info",
        label: "inlet",
      },
    ];
    render(<DynamicViewportOverlays overlays={overlays} />);
    const ov = screen.getByTestId("viewport-overlay");
    expect(ov.dataset.kind).toBe("patch_highlight");
    expect(ov).toHaveTextContent("inlet");
  });

  it("renders cell count badge severity info", () => {
    const overlays: ViewportOverlay[] = [
      {
        kind: "cell_count_badge",
        target: null,
        severity: "info",
        label: "1.2M cells",
      },
    ];
    render(<DynamicViewportOverlays overlays={overlays} />);
    expect(screen.getByText("1.2M cells")).toBeInTheDocument();
  });

  it("flags checkmesh_warn with fail severity for severe non-orthogonality", () => {
    const overlays: ViewportOverlay[] = [
      {
        kind: "checkmesh_warn",
        target: null,
        severity: "fail",
        label: "non-orthogonality 88°",
      },
    ];
    render(<DynamicViewportOverlays overlays={overlays} />);
    const ov = screen.getByTestId("viewport-overlay");
    expect(ov.dataset.severity).toBe("fail");
    expect(ov).toHaveTextContent("non-orthogonality 88°");
  });

  it("renders multiple overlays in order", () => {
    const overlays: ViewportOverlay[] = [
      {
        kind: "patch_highlight",
        target: "inlet",
        severity: "info",
        label: "inlet",
      },
      {
        kind: "cell_count_badge",
        target: null,
        severity: "info",
        label: "50k cells",
      },
    ];
    render(<DynamicViewportOverlays overlays={overlays} />);
    const all = screen.getAllByTestId("viewport-overlay");
    expect(all).toHaveLength(2);
    expect(all[0].dataset.kind).toBe("patch_highlight");
    expect(all[1].dataset.kind).toBe("cell_count_badge");
  });
});

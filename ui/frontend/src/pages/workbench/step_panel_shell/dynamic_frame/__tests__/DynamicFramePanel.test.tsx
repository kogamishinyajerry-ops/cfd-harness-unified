// DEC-V61-202-SUB-M30-CYCLE1 · DynamicFramePanel tests.
//
// Coverage: tone selection per kind, body_text + field_path rendering,
// CTA visibility, provenance disclosure toggle, empty-body fallback.

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { DynamicFramePanel } from "../DynamicFramePanel";
import type { RailPrimary } from "@/types/workbench_frame";

// Cycle 2: DynamicFramePanel uses useManifestPatch internally → needs
// QueryClientProvider context. Wrap render in a fresh client per test.
function renderPanel(rail: RailPrimary, props?: { caseId?: string; manifestStateSha?: string }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <DynamicFramePanel rail={rail} {...props} />
    </QueryClientProvider>,
  );
}

const PROBLEM_RAIL: RailPrimary = {
  kind: "problem_fix",
  title: "BC fields missing",
  body_text: "interFoam expects 0/p_rgh; not found on disk",
  field_path: "bc_contract.pressure",
  suggested_default: null,
  suggested_skeleton: null,
  cta_label: "查看 / View",
  provenance: [
    "step=4 · problem_fix · severity=fail",
    "source=bc_quality.json",
  ],
};

const GAP_RAIL: RailPrimary = {
  kind: "info_gap",
  title: "补充字段 / Fill: vof_contract.phases",
  body_text: "interFoam case requires vof_contract.phases",
  field_path: "vof_contract.phases",
  suggested_default: ["water", "air"],
  suggested_skeleton: null,
  cta_label: "填入 / Apply",
  provenance: ["step=3 · info_gap · severity=critical"],
};

const DEFAULT_RAIL: RailPrimary = {
  kind: "step_default",
  title: "Step 3 · 物理已设 / Physics set",
  body_text: "当前步无阻塞 — 可以进入下一步。",
  field_path: null,
  suggested_default: null,
  suggested_skeleton: null,
  cta_label: "下一步 / Next",
  provenance: ["step=3 · step_default · no blockers"],
};

// DEC-V61-202-SUB-M31-CYCLE1: ship_vof bc.patches skeleton rail
const SKELETON_RAIL: RailPrimary = {
  kind: "info_gap",
  title: "补充字段 / Fill: bc.patches",
  body_text: "at least one boundary patch required for interFoam",
  field_path: "bc.patches",
  suggested_default: null,
  suggested_skeleton: {
    inlet: { patch_type: "fixedValue", fields: { U: [1.0, 0.0, 0.0] } },
    outlet: { patch_type: "zeroGradient", fields: { p: "zeroGradient" } },
    wall: { patch_type: "noSlip", fields: {} },
  },
  cta_label: "应用骨架 / Apply skeleton",
  provenance: [
    "step=4 · info_gap · severity=critical",
    "field_path=bc.patches",
    "skeleton_keys=['inlet', 'outlet', 'wall']",
  ],
};

describe("DynamicFramePanel", () => {
  it("renders problem_fix kind with rose-toned label", () => {
    renderPanel(PROBLEM_RAIL);
    const panel = screen.getByTestId("dynamic-frame-panel");
    expect(panel.dataset.kind).toBe("problem_fix");
    expect(screen.getByText("需修复")).toBeInTheDocument();
    expect(screen.getByText("BC fields missing")).toBeInTheDocument();
    expect(screen.getByText(/interFoam expects 0\/p_rgh/)).toBeInTheDocument();
    expect(screen.getByText("bc_contract.pressure")).toBeInTheDocument();
  });

  it("renders info_gap kind with amber label + CTA", () => {
    renderPanel(GAP_RAIL);
    expect(screen.getByText("待补充")).toBeInTheDocument();
    expect(
      screen.getByText("补充字段 / Fill: vof_contract.phases"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("dynamic-frame-cta")).toHaveTextContent(
      "填入 / Apply",
    );
  });

  it("renders step_default kind with emerald label", () => {
    renderPanel(DEFAULT_RAIL);
    expect(screen.getByText("就绪")).toBeInTheDocument();
    expect(
      screen.getByText("Step 3 · 物理已设 / Physics set"),
    ).toBeInTheDocument();
  });

  it("toggles provenance disclosure on click", async () => {
    renderPanel(PROBLEM_RAIL);
    // Collapsed by default.
    expect(
      screen.queryByText("step=4 · problem_fix · severity=fail"),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("▸ 为什么显示这个"));
    expect(
      screen.getByText("step=4 · problem_fix · severity=fail"),
    ).toBeInTheDocument();
  });

  it("omits body section when body_text is null", () => {
    const noBody: RailPrimary = { ...DEFAULT_RAIL, body_text: null };
    renderPanel(noBody);
    expect(screen.getByText(DEFAULT_RAIL.title)).toBeInTheDocument();
    expect(
      screen.queryByText("当前步无阻塞 — 可以进入下一步。"),
    ).not.toBeInTheDocument();
  });

  // DEC-V61-202-SUB-M31-CYCLE1 · form-helper skeleton CTA tests

  it("renders skeleton CTA when suggested_skeleton is present", () => {
    renderPanel(SKELETON_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    const skeletonBtn = screen.getByTestId("dynamic-frame-skeleton-cta");
    expect(skeletonBtn).toBeInTheDocument();
    expect(skeletonBtn).toHaveTextContent("应用骨架 / Apply skeleton");
    expect(skeletonBtn).not.toBeDisabled();
  });

  it("omits skeleton CTA when suggested_skeleton is null", () => {
    renderPanel(GAP_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    expect(
      screen.queryByTestId("dynamic-frame-skeleton-cta"),
    ).not.toBeInTheDocument();
  });

  it("omits skeleton CTA when caseId or manifestStateSha missing", () => {
    // caseId only, no sha → cannot PATCH yet → no skeleton CTA
    renderPanel(SKELETON_RAIL, { caseId: "case_007" });
    expect(
      screen.queryByTestId("dynamic-frame-skeleton-cta"),
    ).not.toBeInTheDocument();
  });

  it("scalar and skeleton CTAs can coexist", () => {
    const both: RailPrimary = {
      ...SKELETON_RAIL,
      suggested_default: { inlet: { patch_type: "fixedValue" } },
      cta_label: "填入 / Apply",
    };
    renderPanel(both, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    expect(screen.getByTestId("dynamic-frame-cta")).toHaveTextContent(
      "填入 / Apply",
    );
    expect(
      screen.getByTestId("dynamic-frame-skeleton-cta"),
    ).toHaveTextContent("应用骨架 / Apply skeleton");
  });

  it("clicking skeleton CTA calls the PATCH mutation", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          applied_path: "bc.patches",
          new_state_sha: "b".repeat(64),
          validation_errors: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    try {
      renderPanel(SKELETON_RAIL, {
        caseId: "case_007",
        manifestStateSha: "a".repeat(64),
      });
      await userEvent.click(screen.getByTestId("dynamic-frame-skeleton-cta"));
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/cases/case_007/manifest"),
        expect.objectContaining({ method: "PATCH" }),
      );
      // Payload should carry the full skeleton, not the scalar default.
      const [, init] = fetchSpy.mock.calls[0]!;
      const body = JSON.parse((init as RequestInit).body as string);
      expect(body.field_path).toBe("bc.patches");
      expect(Object.keys(body.value)).toEqual(
        expect.arrayContaining(["inlet", "outlet", "wall"]),
      );
    } finally {
      fetchSpy.mockRestore();
    }
  });
});

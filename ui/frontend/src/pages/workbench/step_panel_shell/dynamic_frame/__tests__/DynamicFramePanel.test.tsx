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
  severity: "fail",
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
  severity: "warn",
  provenance: ["step=3 · info_gap · severity=warning"],
};

const DEFAULT_RAIL: RailPrimary = {
  kind: "step_default",
  title: "Step 3 · 物理已设 / Physics set",
  body_text: "当前步无阻塞 — 可以进入下一步。",
  field_path: null,
  suggested_default: null,
  suggested_skeleton: null,
  cta_label: "下一步 / Next",
  severity: "info",
  provenance: ["step=3 · step_default · no blockers"],
};

// DEC-V61-202-SUB-M31-CYCLE1: ship_vof bc.patches skeleton rail.
// Codex R0 P2 fix: when only a skeleton is offered, the backend sets
// `cta_label = null` so the frontend doesn't render a duplicate
// disabled "Apply skeleton" primary button alongside the live secondary
// skeleton button. Only the secondary `dynamic-frame-skeleton-cta`
// renders for skeleton-only rails.
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
  cta_label: null,
  severity: "warn",
  provenance: [
    "step=4 · info_gap · severity=warning",
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

  // DEC-V61-202-SUB-M32-CYCLE1: severity-aware info_gap tone.
  // critical → rose 需修复 (M3.1 cycle 7 corrupted-manifest);
  // warn    → amber 待补充 (existing case_family-missing path);
  // info    → sky 建议 (M3.1 cycle 8 typo'd patch_type).

  it("renders critical info_gap (severity=fail) with rose 需修复 label", () => {
    const criticalRail: RailPrimary = {
      ...GAP_RAIL,
      severity: "fail",
      title: "补充字段 / Fill: case_manifest.yaml",
      body_text:
        "Imported case_manifest.yaml is parseable YAML but fails schema validation.",
      field_path: "case_manifest.yaml",
    };
    renderPanel(criticalRail);
    expect(screen.getByText("需修复")).toBeInTheDocument();
    // Should NOT show the amber "待补充" label
    expect(screen.queryByText("待补充")).not.toBeInTheDocument();
    // Pill carries the rose tone classes
    const panel = screen.getByTestId("dynamic-frame-panel");
    expect(panel.dataset.kind).toBe("info_gap");
  });

  it("renders info-tier info_gap (severity=info) with sky 建议 label", () => {
    const advisoryRail: RailPrimary = {
      ...GAP_RAIL,
      severity: "info",
      title: "补充字段 / Fill: bc.patches.inlet.patch_type",
      body_text:
        "Patch 'inlet' has patch_type='fixedValue_typo', not in workbench vocabulary.",
      field_path: "bc.patches.inlet.patch_type",
    };
    renderPanel(advisoryRail);
    expect(screen.getByText("建议")).toBeInTheDocument();
    expect(screen.queryByText("待补充")).not.toBeInTheDocument();
    expect(screen.queryByText("需修复")).not.toBeInTheDocument();
  });

  it("renders warn-tier info_gap (severity=warn) with amber 待补充 label (existing default)", () => {
    // GAP_RAIL has severity="warn" by default fixture; this test pins
    // the existing behavior so cycle-1 doesn't accidentally re-tone it.
    renderPanel(GAP_RAIL);
    expect(screen.getByText("待补充")).toBeInTheDocument();
    expect(screen.queryByText("需修复")).not.toBeInTheDocument();
    expect(screen.queryByText("建议")).not.toBeInTheDocument();
  });

  it("renders problem_fix with rose label regardless of severity field (kind wins)", () => {
    // Even if backend somehow emits problem_fix + severity=info, the
    // kind-specific tone wins (problem_fix is always urgent).
    const oddProblem: RailPrimary = {
      ...PROBLEM_RAIL,
      severity: "info",  // shouldn't happen in practice but defensible
    };
    renderPanel(oddProblem);
    expect(screen.getByText("需修复")).toBeInTheDocument();
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

  it("does NOT render primary CTA when only skeleton is offered (Codex R0 P2)", () => {
    // When the rail has suggested_skeleton but no suggested_default,
    // backend sets cta_label=null so frontend renders only the
    // secondary skeleton button. Pre-fix, this would have shown two
    // identical 'Apply skeleton' buttons (one disabled, one live).
    renderPanel(SKELETON_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    expect(
      screen.queryByTestId("dynamic-frame-cta"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByTestId("dynamic-frame-skeleton-cta"),
    ).toBeInTheDocument();
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

  // DEC-V61-202-SUB-M31-CYCLE2: inline scalar input affordance.
  // Renders when the rail surfaces a field_path with no auto-apply
  // payload (no suggested_default, no suggested_skeleton) and PATCH
  // context is available. case_family is the first user-visible surface.
  const INLINE_EDIT_RAIL: RailPrimary = {
    kind: "info_gap",
    title: "补充字段 / Fill: case_family",
    body_text:
      "This interFoam case could be ship_vof, sloshing, etc. — label to unlock skeleton.",
    field_path: "case_family",
    suggested_default: null,
    suggested_skeleton: null,
    cta_label: "编辑 / Edit",
    severity: "warn",
    provenance: [
      "step=1 · info_gap · severity=warning",
      "field_path=case_family",
    ],
  };

  it("renders inline edit input + Apply button for scalar gap with no auto-apply payload", () => {
    renderPanel(INLINE_EDIT_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    expect(screen.getByTestId("dynamic-frame-inline-edit")).toBeInTheDocument();
    expect(screen.getByTestId("dynamic-frame-inline-input")).toBeInTheDocument();
    expect(screen.getByTestId("dynamic-frame-inline-apply")).toBeInTheDocument();
  });

  it("suppresses the original disabled primary CTA when inline edit is shown", () => {
    renderPanel(INLINE_EDIT_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    // The "编辑 / Edit" disabled button should NOT render alongside the inline input.
    expect(
      screen.queryByTestId("dynamic-frame-cta"),
    ).not.toBeInTheDocument();
  });

  it("omits inline edit when caseId or manifestStateSha missing", () => {
    renderPanel(INLINE_EDIT_RAIL, { caseId: "case_007" });
    expect(
      screen.queryByTestId("dynamic-frame-inline-edit"),
    ).not.toBeInTheDocument();
  });

  it("Apply button stays disabled for empty / whitespace-only input", async () => {
    renderPanel(INLINE_EDIT_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    const apply = screen.getByTestId("dynamic-frame-inline-apply");
    expect(apply).toBeDisabled();
    // Type whitespace only — Apply should remain disabled.
    const input = screen.getByTestId("dynamic-frame-inline-input");
    await userEvent.type(input, "   ");
    expect(apply).toBeDisabled();
  });

  it("typing + Apply PATCHes field_path with trimmed value", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          applied_path: "case_family",
          new_state_sha: "b".repeat(64),
          validation_errors: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    try {
      renderPanel(INLINE_EDIT_RAIL, {
        caseId: "case_007",
        manifestStateSha: "a".repeat(64),
      });
      const input = screen.getByTestId("dynamic-frame-inline-input");
      // Include leading/trailing whitespace to verify trim().
      await userEvent.type(input, "  ship_vof  ");
      const apply = screen.getByTestId("dynamic-frame-inline-apply");
      expect(apply).not.toBeDisabled();
      await userEvent.click(apply);
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/cases/case_007/manifest"),
        expect.objectContaining({ method: "PATCH" }),
      );
      const [, init] = fetchSpy.mock.calls[0]!;
      const body = JSON.parse((init as RequestInit).body as string);
      expect(body.field_path).toBe("case_family");
      expect(body.value).toBe("ship_vof"); // trimmed
      expect(body.expected_state_sha).toBe("a".repeat(64));
    } finally {
      fetchSpy.mockRestore();
    }
  });

  it("does NOT render inline edit when suggested_default exists (existing primary CTA still rules)", () => {
    renderPanel(GAP_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    // Existing scalar Apply CTA renders, inline-edit affordance does not.
    expect(screen.getByTestId("dynamic-frame-cta")).toBeInTheDocument();
    expect(
      screen.queryByTestId("dynamic-frame-inline-edit"),
    ).not.toBeInTheDocument();
  });

  it("does NOT render inline edit when suggested_skeleton exists (skeleton CTA still rules)", () => {
    renderPanel(SKELETON_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    expect(
      screen.getByTestId("dynamic-frame-skeleton-cta"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("dynamic-frame-inline-edit"),
    ).not.toBeInTheDocument();
  });

  // DEC-V61-202-SUB-M31-CYCLE2 Codex R0 P1 fix: gate on info_gap kind.
  // Existing problem_fix rails (audit findings) carry field_path for
  // viewport navigation but must stay as view-only diagnostics. The
  // inline editor must NOT render for them.
  it("does NOT render inline edit for problem_fix rails (audit findings stay view-only)", () => {
    // PROBLEM_RAIL has field_path=bc_contract.pressure, no payloads.
    // Before R0 P1 fix this would have rendered an editable text box
    // for an audit-finding card, letting engineers PATCH arbitrary
    // strings into a structural field path. The kind=problem_fix
    // guard prevents that regression.
    renderPanel(PROBLEM_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    expect(
      screen.queryByTestId("dynamic-frame-inline-edit"),
    ).not.toBeInTheDocument();
  });

  // DEC-V61-202-SUB-M31-CYCLE2 Codex R0 P2 fix: explicit allow-list of
  // scalar field paths. Non-string-typed gaps (like bc.patches when
  // no skeleton exists) or bracketed paths (which the PATCH endpoint
  // rejects) must NOT render the text input.
  it("does NOT render inline edit for non-allowlisted scalar paths (e.g. bc.patches)", () => {
    // info_gap rail with field_path=bc.patches but no payloads — this
    // is the "case_family unknown, no helper" state. The field is
    // structurally a dict, not a string; rendering a text box would
    // mislead engineers into typing string values for a dict-typed
    // field that PATCH would reject.
    const bcPatchesNoPayload: RailPrimary = {
      kind: "info_gap",
      title: "补充字段 / Fill: bc.patches",
      body_text: "Boundary patches required",
      field_path: "bc.patches",
      suggested_default: null,
      suggested_skeleton: null,
      cta_label: "编辑 / Edit",
      severity: "warn",
      provenance: ["step=4 · info_gap · severity=warning"],
    };
    renderPanel(bcPatchesNoPayload, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    expect(
      screen.queryByTestId("dynamic-frame-inline-edit"),
    ).not.toBeInTheDocument();
  });

  // DEC-V61-202-SUB-M31-CYCLE2 Codex R1 P2 fix: bc.patches gap with no
  // skeleton (case_family still unknown) used to fall back to a
  // permanently disabled "编辑 / Edit" button. Now suppressed entirely
  // — no false-action affordance. Problem_fix rails keep their CTA.
  it("suppresses dead primary CTA on info_gap rails with no action path", () => {
    const bcPatchesNoActionRail: RailPrimary = {
      kind: "info_gap",
      title: "补充字段 / Fill: bc.patches",
      body_text: "Boundary patches required",
      field_path: "bc.patches",
      suggested_default: null,
      suggested_skeleton: null,
      cta_label: "编辑 / Edit",
      severity: "warn",
      provenance: ["step=4 · info_gap · severity=warning"],
    };
    renderPanel(bcPatchesNoActionRail, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    // The disabled "编辑 / Edit" button is hidden — no misleading affordance.
    expect(
      screen.queryByTestId("dynamic-frame-cta"),
    ).not.toBeInTheDocument();
    // Inline editor also not shown (bc.patches not in allow-list).
    expect(
      screen.queryByTestId("dynamic-frame-inline-edit"),
    ).not.toBeInTheDocument();
    // The rail title + body still render — just no action button.
    expect(screen.getByText("补充字段 / Fill: bc.patches")).toBeInTheDocument();
    expect(screen.getByText("Boundary patches required")).toBeInTheDocument();
  });

  it("preserves problem_fix CTA even when no action path exists (view-only)", () => {
    // PROBLEM_RAIL has cta_label="查看 / View" + no suggested_default.
    // Problem_fix rails are diagnostics — the View button stays (even
    // disabled if no nav target) so engineers know the audit finding
    // exists.
    renderPanel(PROBLEM_RAIL, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    expect(screen.getByTestId("dynamic-frame-cta")).toBeInTheDocument();
    expect(screen.getByTestId("dynamic-frame-cta")).toHaveTextContent(
      "查看 / View",
    );
  });

  it("does NOT render inline edit for bracketed paths the backend would reject", () => {
    // The PATCH endpoint's `_parse_field_path` rejects bracket
    // segments. Even if an info_gap surfaces a bracketed path, the
    // inline editor must not offer a text box that would 400 on Apply.
    const bracketedPath: RailPrimary = {
      kind: "info_gap",
      title: "补充字段 / Fill: physics_contract.physics_precondition[0]",
      body_text: "...",
      field_path: "physics_contract.physics_precondition[0]",
      suggested_default: null,
      suggested_skeleton: null,
      cta_label: "编辑 / Edit",
      severity: "warn",
      provenance: ["step=3 · info_gap · severity=warning"],
    };
    renderPanel(bracketedPath, {
      caseId: "case_007",
      manifestStateSha: "a".repeat(64),
    });
    expect(
      screen.queryByTestId("dynamic-frame-inline-edit"),
    ).not.toBeInTheDocument();
  });
});

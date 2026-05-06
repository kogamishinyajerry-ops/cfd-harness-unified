// Step 2 Mesh wired-body tests (M-PANELS spec_v2 §E Step 5).

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError } from "@/api/client";
import type { MeshSuccessResponse } from "@/types/mesh_imported";
import type { PrismLayersSuccessResponse } from "@/types/mesh_prism_layers";

const apiMock = vi.hoisted(() => ({
  meshImported: vi.fn(),
  meshPrismLayers: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: {
      ...actual.api,
      meshImported: apiMock.meshImported,
      meshPrismLayers: apiMock.meshPrismLayers,
    },
  };
});

import { Step2Mesh } from "../steps/Step2Mesh";

function renderStep(props: {
  caseId?: string;
  onStepComplete?: () => void;
  onStepError?: (msg: string) => void;
}) {
  let registered: (() => Promise<void>) | null = null;
  const registerAiAction = vi.fn(
    (action: (() => Promise<void>) | null) => {
      registered = action;
    },
  );
  const utils = render(
    <Step2Mesh
      caseId={props.caseId ?? "abc"}
      onStepComplete={props.onStepComplete ?? (() => {})}
      onStepError={props.onStepError ?? (() => {})}
      registerAiAction={registerAiAction}
    />,
  );
  return {
    ...utils,
    registerAiAction,
    triggerAi: () => {
      if (!registered) throw new Error("no AI action registered");
      return registered();
    },
  };
}

const FAKE_MESH_RESPONSE: MeshSuccessResponse = {
  case_id: "abc",
  mesh_summary: {
    cell_count: 1234567,
    face_count: 7000000,
    point_count: 234567,
    generation_time_s: 42.5,
    polyMesh_path: "/tmp/case/constant/polyMesh",
    msh_path: "/tmp/case/mesh.msh",
    mesh_mode_used: "beginner",
    warning: null,
  },
};

const FAKE_PRISM_RESPONSE: PrismLayersSuccessResponse = {
  case_id: "abc",
  prism_summary: {
    cell_count: 0,
    face_count: 0,
    layers_added: 5,
    coverage_fraction: 0.92,
    polyMesh_path: "/tmp/case/constant/polyMesh",
    log_path: "/tmp/case/log.snappyHexMesh",
    generation_time_s: 12.5,
  },
};

describe("Step2Mesh · wired body", () => {
  beforeEach(() => {
    apiMock.meshImported.mockReset();
    apiMock.meshPrismLayers.mockReset();
  });

  it("registers an AI action with the shell on mount", () => {
    const { registerAiAction } = renderStep({});
    expect(registerAiAction).toHaveBeenCalled();
    // last call should be a function (the trigger), not null
    const lastCall =
      registerAiAction.mock.calls[registerAiAction.mock.calls.length - 1];
    expect(typeof lastCall[0]).toBe("function");
  });

  it("clears the registration on unmount", () => {
    const { registerAiAction, unmount } = renderStep({});
    unmount();
    // after unmount the cleanup fires registerAiAction(null)
    expect(registerAiAction).toHaveBeenLastCalledWith(null);
  });

  it("renders the beginner / power radio with beginner pre-selected", () => {
    renderStep({});
    const beginner = screen.getByTestId("step2-mesh-mode-beginner");
    const power = screen.getByTestId("step2-mesh-mode-power");
    expect(
      beginner.querySelector("input[type=radio]"),
    ).toHaveProperty("checked", true);
    expect(
      power.querySelector("input[type=radio]"),
    ).toHaveProperty("checked", false);
  });

  it("flips selection when 'power' radio is clicked", async () => {
    const user = userEvent.setup();
    renderStep({});
    const powerRadio = screen
      .getByTestId("step2-mesh-mode-power")
      .querySelector("input[type=radio]") as HTMLInputElement;
    await user.click(powerRadio);
    expect(powerRadio.checked).toBe(true);
  });

  it("registered action POSTs the mesh request with the selected mode + fires onStepComplete", async () => {
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const onStepComplete = vi.fn();
    const { triggerAi } = renderStep({
      caseId: "abc",
      onStepComplete,
    });
    await triggerAi();
    // DEC-V61-135 (N2.1): meshImported now takes (caseId, mode, sizingField).
    // The advanced panel is collapsed by default so the third arg is null.
    // DEC-V61-136 (N2.2): fourth arg = refinementZones; closed panel → null.
    expect(apiMock.meshImported).toHaveBeenCalledWith(
      "abc",
      "beginner",
      null,
      null,
    );
    expect(onStepComplete).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.getByTestId("step2-mesh-success")).toBeInTheDocument();
    });
  });

  it("re-registers when meshMode changes so the next trigger uses the new mode", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValue(FAKE_MESH_RESPONSE);
    const { triggerAi } = renderStep({});

    const powerRadio = screen
      .getByTestId("step2-mesh-mode-power")
      .querySelector("input[type=radio]") as HTMLInputElement;
    await user.click(powerRadio);
    await triggerAi();
    expect(apiMock.meshImported).toHaveBeenLastCalledWith(
      expect.any(String),
      "power",
      null,
      null,
    );
  });

  it("renders a structured rejection panel + calls onStepError on ApiError detail", async () => {
    apiMock.meshImported.mockRejectedValueOnce(
      new ApiError(422, "rejected", {
        failing_check: "cell_cap_exceeded",
        reason: "would exceed 50M cells",
      }),
    );
    const onStepError = vi.fn();
    const { triggerAi } = renderStep({ onStepError });
    await expect(triggerAi()).rejects.toBeInstanceOf(ApiError);
    expect(screen.getByTestId("step2-mesh-rejection")).toHaveTextContent(
      /cell_cap_exceeded/,
    );
    expect(onStepError).toHaveBeenCalledWith(
      expect.stringContaining("cell_cap_exceeded"),
    );
  });

  it("renders a network-error panel for non-ApiError rejections", async () => {
    apiMock.meshImported.mockRejectedValueOnce(new Error("Failed to fetch"));
    const onStepError = vi.fn();
    const { triggerAi } = renderStep({ onStepError });
    await expect(triggerAi()).rejects.toThrow(/Failed to fetch/);
    expect(
      screen.getByTestId("step2-mesh-network-error"),
    ).toHaveTextContent(/Failed to fetch/);
    expect(onStepError).toHaveBeenCalledWith("Failed to fetch");
  });

  // DEC-V61-135 (N2.1): advanced sizing-field disclosure tests.
  it("collapses the advanced sizing panel by default", () => {
    renderStep({});
    const details = screen.getByTestId(
      "step2-mesh-advanced-sizing",
    ) as HTMLDetailsElement;
    expect(details.open).toBe(false);
  });

  it("sends sizing_field when advanced panel is open + values entered", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const { triggerAi } = renderStep({});

    // Open the disclosure
    const summary = screen
      .getByTestId("step2-mesh-advanced-sizing")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);

    const baseInput = screen
      .getByTestId("step2-mesh-sizing-base_lc")
      .querySelector("input") as HTMLInputElement;
    await user.type(baseInput, "0.05");

    await triggerAi();
    expect(apiMock.meshImported).toHaveBeenLastCalledWith(
      expect.any(String),
      "beginner",
      expect.objectContaining({ base_lc: 0.05 }),
      null,
    );
  });

  it("blocks the request and surfaces an inline error when min_lc > max_lc", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const onStepError = vi.fn();
    const { triggerAi } = renderStep({ onStepError });

    const summary = screen
      .getByTestId("step2-mesh-advanced-sizing")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);

    const minInput = screen
      .getByTestId("step2-mesh-sizing-min_lc")
      .querySelector("input") as HTMLInputElement;
    const maxInput = screen
      .getByTestId("step2-mesh-sizing-max_lc")
      .querySelector("input") as HTMLInputElement;
    await user.type(minInput, "0.5");
    await user.type(maxInput, "0.1");

    await triggerAi();

    // No POST happened (validation guard fired before)
    expect(apiMock.meshImported).not.toHaveBeenCalled();
    expect(
      screen.getByTestId("step2-mesh-sizing-error"),
    ).toHaveTextContent(/min_lc must be ≤ max_lc/);
    expect(onStepError).toHaveBeenCalledWith(
      expect.stringMatching(/sizing-field validation/),
    );
  });

  // Codex R0 P2 #2: FastAPI request-validation 422 returns
  // detail = [...] (array). Old code treated any object-like detail as
  // MeshRejectionDetail and rendered "mesh rejected: undefined". The
  // sizing-field surface makes that path reachable, so the catch
  // block must distinguish array (422) from {reason, failing_check}.
  it("renders FastAPI 422 array detail as networkError, not blank rejection", async () => {
    apiMock.meshImported.mockRejectedValueOnce(
      new ApiError(422, "request validation failed", [
        {
          loc: ["body", "sizing_field", "base_lc"],
          msg: "Input should be greater than 0",
          type: "greater_than",
        },
      ]),
    );
    const onStepError = vi.fn();
    const { triggerAi } = renderStep({ onStepError });

    await expect(triggerAi()).rejects.toBeInstanceOf(ApiError);

    // No structured rejection panel
    expect(screen.queryByTestId("step2-mesh-rejection")).toBeNull();
    // Network-error panel shows the validation issues
    const netErr = screen.getByTestId("step2-mesh-network-error");
    expect(netErr).toHaveTextContent(/request validation failed/);
    expect(netErr).toHaveTextContent(/sizing_field.base_lc/);
    expect(netErr).toHaveTextContent(/greater than 0/);
    expect(onStepError).toHaveBeenCalledWith(
      expect.stringMatching(/request validation failed/),
    );
  });

  it("still renders structured pipeline rejection ({reason, failing_check})", async () => {
    apiMock.meshImported.mockRejectedValueOnce(
      new ApiError(422, "mesh rejected", {
        reason: "mesh has 60M cells exceeds the 50M-cell hard cap",
        failing_check: "cell_cap_exceeded",
      }),
    );
    const onStepError = vi.fn();
    const { triggerAi } = renderStep({ onStepError });

    await expect(triggerAi()).rejects.toBeInstanceOf(ApiError);

    const rejection = screen.getByTestId("step2-mesh-rejection");
    expect(rejection).toHaveTextContent(/cell_cap_exceeded/);
    expect(rejection).toHaveTextContent(/60M cells/);
    expect(onStepError).toHaveBeenCalledWith(
      "mesh rejected: cell_cap_exceeded",
    );
  });

  it("reset button clears the sizing field back to preset", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const { triggerAi } = renderStep({});

    const summary = screen
      .getByTestId("step2-mesh-advanced-sizing")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);

    const baseInput = screen
      .getByTestId("step2-mesh-sizing-base_lc")
      .querySelector("input") as HTMLInputElement;
    await user.type(baseInput, "0.05");

    const resetBtn = screen.getByTestId("step2-mesh-sizing-reset");
    await user.click(resetBtn);

    await triggerAi();
    // After reset: panel still open but all fields null → meshImported
    // gets called but the api client strips the sizing_field body. The
    // mock receives the literal sizingField object passed in (with all
    // nulls); the wire-stripping happens inside the real client.
    expect(apiMock.meshImported).toHaveBeenLastCalledWith(
      expect.any(String),
      "beginner",
      expect.objectContaining({
        base_lc: null,
        min_lc: null,
        max_lc: null,
      }),
      null,
    );
  });

  // DEC-V61-136 (N2.2): refinement-zones repeater tests.
  it("collapses the refinement-zones panel by default", () => {
    renderStep({});
    const details = screen.getByTestId(
      "step2-mesh-refinement-zones",
    ) as HTMLDetailsElement;
    expect(details.open).toBe(false);
  });

  it("adds a box zone via the + button and sends it on next trigger", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const { triggerAi } = renderStep({});

    const summary = screen
      .getByTestId("step2-mesh-refinement-zones")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);

    await user.click(screen.getByTestId("step2-mesh-zones-add-box"));

    await triggerAi();
    expect(apiMock.meshImported).toHaveBeenLastCalledWith(
      expect.any(String),
      "beginner",
      null,
      [
        expect.objectContaining({
          geometry: "box",
          bbox: [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
          level: 2,
        }),
      ],
    );
  });

  it("adds a sphere zone and edits radius before send", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const { triggerAi } = renderStep({});

    const summary = screen
      .getByTestId("step2-mesh-refinement-zones")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);

    await user.click(screen.getByTestId("step2-mesh-zones-add-sphere"));

    const radiusInput = screen.getByTestId(
      "step2-mesh-zone-0-radius",
    ) as HTMLInputElement;
    await user.clear(radiusInput);
    await user.type(radiusInput, "0.25");

    await triggerAi();
    expect(apiMock.meshImported).toHaveBeenLastCalledWith(
      expect.any(String),
      "beginner",
      null,
      [
        expect.objectContaining({
          geometry: "sphere",
          radius: 0.25,
          level: 2,
        }),
      ],
    );
  });

  it("blocks the request and surfaces an inline error when a box zone is zero-extent", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const onStepError = vi.fn();
    const { triggerAi } = renderStep({ onStepError });

    const summary = screen
      .getByTestId("step2-mesh-refinement-zones")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);
    await user.click(screen.getByTestId("step2-mesh-zones-add-box"));

    // Collapse the box to zero extent on x by setting xmax = xmin.
    const xmaxInput = screen.getByTestId(
      "step2-mesh-zone-0-xmax",
    ) as HTMLInputElement;
    await user.clear(xmaxInput);
    await user.type(xmaxInput, "0");

    await triggerAi();

    expect(apiMock.meshImported).not.toHaveBeenCalled();
    expect(screen.getByTestId("step2-mesh-zones-error")).toHaveTextContent(
      /zero or inverted extent/,
    );
    expect(onStepError).toHaveBeenCalledWith(
      expect.stringContaining("zone validation"),
    );
  });

  it("renders a refinement-zone-invalid hint on backend rejection", async () => {
    apiMock.meshImported.mockRejectedValueOnce(
      new ApiError(422, "rejected", {
        failing_check: "refinement_zone_invalid",
        reason:
          "refinement_zones[0] (box) bbox=[10,10,10,11,11,11] has no overlap with case AABB=[0,0,0,1,1,1]; the gmsh field would be a no-op.",
      }),
    );
    const { triggerAi } = renderStep({});
    await expect(triggerAi()).rejects.toBeInstanceOf(ApiError);
    const panel = screen.getByTestId("step2-mesh-rejection");
    expect(panel).toHaveTextContent(/refinement_zone_invalid/);
    expect(panel).toHaveTextContent(/no overlap with the case geometry/);
  });

  // R0 P1 (Codex CRS): coordinate inputs must accept partial /
  // negative edits without snapping back to 0.
  it("accepts negative coordinates and partial decimals in zone inputs", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const { triggerAi } = renderStep({});

    const summary = screen
      .getByTestId("step2-mesh-refinement-zones")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);
    await user.click(screen.getByTestId("step2-mesh-zones-add-box"));

    const xminInput = screen.getByTestId(
      "step2-mesh-zone-0-xmin",
    ) as HTMLInputElement;
    await user.clear(xminInput);
    await user.type(xminInput, "-0.5");

    const yminInput = screen.getByTestId(
      "step2-mesh-zone-0-ymin",
    ) as HTMLInputElement;
    await user.clear(yminInput);
    await user.type(yminInput, ".25");

    await triggerAi();

    expect(apiMock.meshImported).toHaveBeenLastCalledWith(
      expect.any(String),
      "beginner",
      null,
      [
        expect.objectContaining({
          geometry: "box",
          // Negative xmin and partial-decimal ymin must round-trip.
          bbox: [-0.5, 0.25, 0.0, 1.0, 1.0, 1.0],
        }),
      ],
    );
  });

  // R0 P2 (Codex CRS): collapsing the disclosure must NOT silently
  // drop configured zones. Zones list is data; disclosure is UX.
  it("sends configured zones even when the disclosure is collapsed", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const { triggerAi } = renderStep({});

    const detailsEl = screen.getByTestId(
      "step2-mesh-refinement-zones",
    ) as HTMLDetailsElement;
    const summary = detailsEl.querySelector("summary") as HTMLElement;
    await user.click(summary);
    await user.click(screen.getByTestId("step2-mesh-zones-add-box"));

    // Collapse the panel. Zones state remains.
    await user.click(summary);
    expect(detailsEl.open).toBe(false);

    await triggerAi();

    expect(apiMock.meshImported).toHaveBeenLastCalledWith(
      expect.any(String),
      "beginner",
      null,
      [
        expect.objectContaining({
          geometry: "box",
          level: 2,
        }),
      ],
    );
  });

  // R1 P2 (Codex CRS): submitting while a zone input is in a partial
  // draft state (raw "-" / "" / ".") must NOT silently use the previous
  // committed value while still showing the draft. triggerMesh blurs
  // the active element first so the displayed value snaps back to the
  // committed canonical and submission == display.
  it("blurs focused zone input before submitting so display matches submitted state", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const { triggerAi } = renderStep({});

    const summary = screen
      .getByTestId("step2-mesh-refinement-zones")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);
    await user.click(screen.getByTestId("step2-mesh-zones-add-box"));

    // Type a non-committing draft state ("-") into xmin and leave the
    // cursor focused there.
    const xminInput = screen.getByTestId(
      "step2-mesh-zone-0-xmin",
    ) as HTMLInputElement;
    await user.clear(xminInput);
    await user.type(xminInput, "-");
    expect(xminInput.value).toBe("-");

    // Trigger via the action — internally blurs first.
    await triggerAi();

    // After blur, the input snaps back to the canonical default 0.
    expect(xminInput.value).toBe("0");
    // And the submitted bbox matches the display (xmin=0), NOT some
    // half-typed "-" that was visible on the screen.
    expect(apiMock.meshImported).toHaveBeenLastCalledWith(
      expect.any(String),
      "beginner",
      null,
      [
        expect.objectContaining({
          geometry: "box",
          bbox: [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
        }),
      ],
    );
  });

  // DEC-V61-137 (N2.3): prism-layers panel tests.
  it("collapses the prism-layers panel by default", () => {
    renderStep({});
    const details = screen.getByTestId(
      "step2-mesh-prism-layers",
    ) as HTMLDetailsElement;
    expect(details.open).toBe(false);
  });

  // R0 P2 (Codex 86gs): the previous version disabled the Apply
  // button when local `response` was null, but cases meshed in
  // earlier sessions arrive at Step 2 with response=null even though
  // the polyMesh is on disk. The disabled gate broke that flow.
  // Now: button is enabled by default; the backend's structured
  // polyMesh_not_ready 422 is the source of truth.
  it("keeps Apply prism layers enabled even without a current-session mesh", async () => {
    const user = userEvent.setup();
    renderStep({});

    const summary = screen
      .getByTestId("step2-mesh-prism-layers")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);

    const applyBtn = screen.getByTestId(
      "step2-mesh-prism-apply",
    ) as HTMLButtonElement;
    expect(applyBtn.disabled).toBe(false);
  });

  it("surfaces backend polyMesh_not_ready hint when prism applied without polyMesh", async () => {
    const user = userEvent.setup();
    apiMock.meshPrismLayers.mockRejectedValueOnce(
      new ApiError(422, "rejected", {
        failing_check: "polyMesh_not_ready",
        reason: "polyMesh not ready under .../polyMesh — run the gmsh stage first.",
      }),
    );
    renderStep({});

    const summary = screen
      .getByTestId("step2-mesh-prism-layers")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);
    await user.click(screen.getByTestId("step2-mesh-prism-apply"));

    await waitFor(() => {
      const rej = screen.getByTestId("step2-mesh-prism-rejection");
      expect(rej).toHaveTextContent(/polyMesh_not_ready/);
      expect(rej).toHaveTextContent(/Run the mesh stage first/);
    });
  });

  it("enables and POSTs prism layers after a successful mesh", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    apiMock.meshPrismLayers.mockResolvedValueOnce(FAKE_PRISM_RESPONSE);
    const { triggerAi } = renderStep({});

    // First, run the mesh stage.
    await triggerAi();
    await waitFor(() => {
      expect(screen.getByTestId("step2-mesh-success")).toBeInTheDocument();
    });

    // Open the prism panel and click apply.
    const summary = screen
      .getByTestId("step2-mesh-prism-layers")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);

    const applyBtn = screen.getByTestId(
      "step2-mesh-prism-apply",
    ) as HTMLButtonElement;
    expect(applyBtn.disabled).toBe(false);
    await user.click(applyBtn);

    expect(apiMock.meshPrismLayers).toHaveBeenLastCalledWith("abc", [
      expect.objectContaining({
        patch: "walls",
        first_cell_height: 1.0e-4,
        expansion_ratio: 1.2,
        num_layers: 5,
      }),
    ]);
    await waitFor(() => {
      expect(
        screen.getByTestId("step2-mesh-prism-success"),
      ).toHaveTextContent(/Prism layers applied/);
    });
  });

  it("renders a structured rejection on backend prism failure", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    apiMock.meshPrismLayers.mockRejectedValueOnce(
      new ApiError(422, "rejected", {
        failing_check: "patch_not_found",
        reason: "patch(es) ['airfoil'] not present in .../boundary",
      }),
    );
    const onStepError = vi.fn();
    const { triggerAi } = renderStep({ onStepError });

    await triggerAi();
    const summary = screen
      .getByTestId("step2-mesh-prism-layers")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);
    await user.click(screen.getByTestId("step2-mesh-prism-apply"));

    await waitFor(() => {
      const rej = screen.getByTestId("step2-mesh-prism-rejection");
      expect(rej).toHaveTextContent(/patch_not_found/);
      expect(rej).toHaveTextContent(/does not match any patch/);
    });
    expect(onStepError).toHaveBeenCalledWith(
      expect.stringContaining("patch_not_found"),
    );
  });

  it("blocks prism apply with inline error when expansion_ratio out of bounds", async () => {
    const user = userEvent.setup();
    apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
    const onStepError = vi.fn();
    const { triggerAi } = renderStep({ onStepError });

    await triggerAi();
    const summary = screen
      .getByTestId("step2-mesh-prism-layers")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);

    const erInput = screen
      .getByTestId("step2-mesh-prism-expansion_ratio")
      .querySelector("input") as HTMLInputElement;
    await user.clear(erInput);
    await user.type(erInput, "5");  // > MAX

    await user.click(screen.getByTestId("step2-mesh-prism-apply"));

    expect(apiMock.meshPrismLayers).not.toHaveBeenCalled();
    expect(screen.getByTestId("step2-mesh-prism-error")).toHaveTextContent(
      /expansion_ratio/,
    );
    expect(onStepError).toHaveBeenCalledWith(
      expect.stringContaining("prism validation"),
    );
  });

  it("removes a zone via Remove button", async () => {
    const user = userEvent.setup();
    const { container } = renderStep({});

    const summary = screen
      .getByTestId("step2-mesh-refinement-zones")
      .querySelector("summary") as HTMLElement;
    await user.click(summary);

    await user.click(screen.getByTestId("step2-mesh-zones-add-box"));
    expect(container.querySelector('[data-testid="step2-mesh-zone-0"]'))
      .toBeTruthy();

    await user.click(screen.getByTestId("step2-mesh-zone-0-remove"));
    expect(container.querySelector('[data-testid="step2-mesh-zone-0"]'))
      .toBeNull();
  });
});

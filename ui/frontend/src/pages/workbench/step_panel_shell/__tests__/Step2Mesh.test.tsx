// Step 2 Mesh wired-body tests (M-PANELS spec_v2 §E Step 5).

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError } from "@/api/client";
import type { MeshSuccessResponse } from "@/types/mesh_imported";

const apiMock = vi.hoisted(() => ({
  meshImported: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, meshImported: apiMock.meshImported },
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

describe("Step2Mesh · wired body", () => {
  beforeEach(() => {
    apiMock.meshImported.mockReset();
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
    expect(apiMock.meshImported).toHaveBeenCalledWith("abc", "beginner", null);
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
    );
  });
});

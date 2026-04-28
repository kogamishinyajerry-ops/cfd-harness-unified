// Step 2 Mesh wired-body tests (M-PANELS spec_v2 §E Step 5).

import { describe, expect, it, vi } from "vitest";
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
    expect(apiMock.meshImported).toHaveBeenCalledWith("abc", "beginner");
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
});

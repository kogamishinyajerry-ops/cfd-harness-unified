// DEC-V61-108 Phase B · PatchClassificationPanel coverage.
//
// Tests the panel in isolation with mocked api client. Step3SetupBC
// integration is covered by Step3SetupBC.test.tsx (which mounts the
// real shell + provider stack).

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PatchClassificationPanel } from "../PatchClassificationPanel";
import { ApiError } from "@/api/client";
import type {
  FaceIndexDocument,
  PatchClassificationState,
} from "../types";

const {
  getPatchClassificationMock,
  putPatchClassificationMock,
  deletePatchClassificationMock,
  getFaceIndexMock,
} = vi.hoisted(() => ({
  getPatchClassificationMock: vi.fn(),
  putPatchClassificationMock: vi.fn(),
  deletePatchClassificationMock: vi.fn(),
  getFaceIndexMock: vi.fn(),
}));

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: {
      ...actual.api,
      getPatchClassification: (...args: unknown[]) =>
        getPatchClassificationMock(...args),
      putPatchClassification: (...args: unknown[]) =>
        putPatchClassificationMock(...args),
      deletePatchClassification: (...args: unknown[]) =>
        deletePatchClassificationMock(...args),
      getFaceIndex: (...args: unknown[]) => getFaceIndexMock(...args),
    },
  };
});

const baseState: PatchClassificationState = {
  case_id: "case-1",
  schema_version: 1,
  available_patches: ["inlet", "outlet", "wall_left"],
  auto_classifications: {
    inlet: "velocity_inlet",
    outlet: "pressure_outlet",
    wall_left: "no_slip_wall",
  },
  overrides: {},
};

const baseFaceIndex: FaceIndexDocument = {
  case_id: "case-1",
  primitives: [
    { patch_name: "inlet", face_ids: ["f0", "f1"] },
    { patch_name: "outlet", face_ids: ["f2"] },
    { patch_name: "wall_left", face_ids: ["f3", "f4", "f5"] },
  ],
};

beforeEach(() => {
  getPatchClassificationMock.mockReset();
  putPatchClassificationMock.mockReset();
  deletePatchClassificationMock.mockReset();
  getFaceIndexMock.mockReset();
  // Default: face-index resolves so picked-face highlighting can be
  // exercised by the dedicated test. Tests that need it absent
  // override with mockRejectedValueOnce.
  getFaceIndexMock.mockResolvedValue(baseFaceIndex);
});

describe("PatchClassificationPanel", () => {
  it("renders all patches with auto + override columns", async () => {
    getPatchClassificationMock.mockResolvedValueOnce(baseState);
    render(<PatchClassificationPanel caseId="case-1" pickedFaceId={null} />);

    const panel = await screen.findByTestId("patch-classification-panel");
    for (const name of baseState.available_patches) {
      const row = within(panel).getByTestId(`patch-row-${name}`);
      expect(row).toBeTruthy();
      expect(within(row).getByText(baseState.auto_classifications[name])).toBeTruthy();
      // Override dropdown defaults to "" (inherit auto).
      const select = within(row).getByTestId(
        `override-select-${name}`,
      ) as HTMLSelectElement;
      expect(select.value).toBe("");
    }
  });

  it("PUTs an override and re-renders with the merged state", async () => {
    getPatchClassificationMock.mockResolvedValueOnce(baseState);
    putPatchClassificationMock.mockResolvedValueOnce({
      ...baseState,
      overrides: { wall_left: "symmetry" },
    });

    render(<PatchClassificationPanel caseId="case-1" pickedFaceId={null} />);
    await screen.findByTestId("patch-classification-panel");

    const select = await screen.findByTestId(
      "override-select-wall_left",
    );
    await userEvent.selectOptions(select, "symmetry");

    await waitFor(() => {
      expect(putPatchClassificationMock).toHaveBeenCalledWith("case-1", {
        patch_name: "wall_left",
        bc_class: "symmetry",
      });
    });
    await waitFor(() => {
      expect(
        (
          screen.getByTestId(
            "override-select-wall_left",
          ) as HTMLSelectElement
        ).value,
      ).toBe("symmetry");
    });
  });

  it("DELETEs the override when the engineer picks 'inherit auto'", async () => {
    getPatchClassificationMock.mockResolvedValueOnce({
      ...baseState,
      overrides: { wall_left: "symmetry" },
    });
    deletePatchClassificationMock.mockResolvedValueOnce({
      ...baseState,
      overrides: {},
    });

    render(<PatchClassificationPanel caseId="case-1" pickedFaceId={null} />);
    await screen.findByTestId("patch-classification-panel");

    const select = (await screen.findByTestId(
      "override-select-wall_left",
    )) as HTMLSelectElement;
    expect(select.value).toBe("symmetry");
    await userEvent.selectOptions(select, "");

    await waitFor(() => {
      expect(deletePatchClassificationMock).toHaveBeenCalledWith(
        "case-1",
        "wall_left",
      );
    });
    await waitFor(() => {
      expect(
        (
          screen.getByTestId(
            "override-select-wall_left",
          ) as HTMLSelectElement
        ).value,
      ).toBe("");
    });
  });

  it("highlights the row whose patch contains the picked face", async () => {
    getPatchClassificationMock.mockResolvedValueOnce(baseState);

    render(<PatchClassificationPanel caseId="case-1" pickedFaceId="f3" />);
    // wait for both fetches to resolve before reading data-picked
    await screen.findByTestId("patch-classification-panel");
    await waitFor(() => {
      expect(getFaceIndexMock).toHaveBeenCalledWith("case-1");
    });

    await waitFor(() => {
      const wallRow = screen.getByTestId("patch-row-wall_left");
      expect(wallRow.getAttribute("data-picked")).toBe("true");
      // Other rows must not be highlighted.
      expect(
        screen.getByTestId("patch-row-inlet").getAttribute("data-picked"),
      ).toBeNull();
    });
  });

  it("surfaces the failing_check on a 422 PUT failure", async () => {
    getPatchClassificationMock.mockResolvedValueOnce(baseState);
    putPatchClassificationMock.mockRejectedValueOnce(
      new ApiError(422, "rejected", {
        failing_check: "patch_not_in_mesh",
        detail: "patch_name not in current mesh",
      }),
    );

    render(<PatchClassificationPanel caseId="case-1" pickedFaceId={null} />);
    await screen.findByTestId("patch-classification-panel");

    await userEvent.selectOptions(
      screen.getByTestId("override-select-inlet"),
      "no_slip_wall",
    );

    const errBox = await screen.findByTestId("override-error-inlet");
    expect(errBox.textContent).toContain("patch_not_in_mesh");
    // The PUT failed → the dropdown reverts to whatever last-good
    // state was (here: "" because no successful save happened yet).
    expect(
      (
        screen.getByTestId("override-select-inlet") as HTMLSelectElement
      ).value,
    ).toBe("");
  });

  it("surfaces ApiError.failing_check on a 404 load failure", async () => {
    getPatchClassificationMock.mockRejectedValueOnce(
      new ApiError(404, "getPatchClassification failed (404)", {
        failing_check: "case_not_found",
        detail: "case_id absent from imported drafts",
      }),
    );
    render(<PatchClassificationPanel caseId="case-1" pickedFaceId={null} />);
    const errBox = await screen.findByTestId(
      "patch-classification-load-error",
    );
    // Codex R1 P3 closure: prefer the structured failing_check over
    // the generic "getPatchClassification failed (404)" message.
    expect(errBox.textContent).toContain("case_not_found");
    expect(errBox.textContent).toContain(
      "case_id absent from imported drafts",
    );
  });

  it("renders the no-mesh state when available_patches is empty", async () => {
    getPatchClassificationMock.mockResolvedValueOnce({
      ...baseState,
      available_patches: [],
      auto_classifications: {},
      overrides: {},
    });
    render(<PatchClassificationPanel caseId="case-1" pickedFaceId={null} />);
    await screen.findByTestId("patch-classification-no-mesh");
  });

  // ─── Codex R1 P1 #1 closure · request-generation token ───
  // Two saves on different rows fire in order A, B but resolve in
  // reverse order B, A. Without the generation guard the older A
  // response would clobber the newer B state. With the guard the
  // stale A is dropped and the panel reflects B's payload.
  it("rejects out-of-order PUT resolutions (last-issued wins)", async () => {
    getPatchClassificationMock.mockResolvedValueOnce(baseState);

    let resolveA!: (s: PatchClassificationState) => void;
    let resolveB!: (s: PatchClassificationState) => void;
    const pendingA = new Promise<PatchClassificationState>((r) => {
      resolveA = r;
    });
    const pendingB = new Promise<PatchClassificationState>((r) => {
      resolveB = r;
    });
    putPatchClassificationMock
      .mockReturnValueOnce(pendingA)
      .mockReturnValueOnce(pendingB);

    render(<PatchClassificationPanel caseId="case-1" pickedFaceId={null} />);
    await screen.findByTestId("patch-classification-panel");

    // Issue A (inlet → no_slip_wall) then B (outlet → symmetry).
    await userEvent.selectOptions(
      screen.getByTestId("override-select-inlet"),
      "no_slip_wall",
    );
    await userEvent.selectOptions(
      screen.getByTestId("override-select-outlet"),
      "symmetry",
    );

    // Resolve B first (newest), then A (stale). The stale A response
    // claims overrides={inlet: no_slip_wall} only, dropping outlet.
    // The panel must NOT regress to that state.
    resolveB({
      ...baseState,
      overrides: { inlet: "no_slip_wall", outlet: "symmetry" },
    });
    resolveA({
      ...baseState,
      overrides: { inlet: "no_slip_wall" },
    });

    await waitFor(() => {
      expect(
        (
          screen.getByTestId(
            "override-select-outlet",
          ) as HTMLSelectElement
        ).value,
      ).toBe("symmetry");
    });
    // And inlet's override stays from B's payload — not regressed.
    expect(
      (
        screen.getByTestId("override-select-inlet") as HTMLSelectElement
      ).value,
    ).toBe("no_slip_wall");
  });

  // ─── Codex R2 P1 closure · A succeeds after B fails ───
  // The R1 single-token model dropped this case: bumping the gen on
  // every save invalidated A's older response even though no newer
  // save had successfully landed. The R2 split (caseGen vs
  // committedSeq) only advances committedSeq on success, so A still
  // commits when B fails before A.
  it("commits an older save's response after a newer save fails", async () => {
    getPatchClassificationMock.mockResolvedValueOnce(baseState);

    let resolveA!: (s: PatchClassificationState) => void;
    let rejectB!: (e: unknown) => void;
    const pendingA = new Promise<PatchClassificationState>((r) => {
      resolveA = r;
    });
    const pendingB = new Promise<PatchClassificationState>((_r, rj) => {
      rejectB = rj;
    });
    putPatchClassificationMock
      .mockReturnValueOnce(pendingA)
      .mockReturnValueOnce(pendingB);

    render(<PatchClassificationPanel caseId="case-1" pickedFaceId={null} />);
    await screen.findByTestId("patch-classification-panel");

    // Issue A first (inlet → no_slip_wall), then B (outlet → symmetry).
    await userEvent.selectOptions(
      screen.getByTestId("override-select-inlet"),
      "no_slip_wall",
    );
    await userEvent.selectOptions(
      screen.getByTestId("override-select-outlet"),
      "symmetry",
    );

    // B fails before A resolves.
    rejectB(
      new ApiError(422, "rejected", {
        failing_check: "patch_not_in_mesh",
        detail: "outlet vanished",
      }),
    );
    // Then A succeeds with its full-state response. Even though
    // saveSeq has already advanced past A, committedSeq is still 0
    // (B failed → didn't advance), so A's mySeq=1 > 0 wins.
    resolveA({ ...baseState, overrides: { inlet: "no_slip_wall" } });

    await waitFor(() => {
      expect(
        (
          screen.getByTestId("override-select-inlet") as HTMLSelectElement
        ).value,
      ).toBe("no_slip_wall");
    });
    // B's error stays surfaced on its row.
    expect(screen.getByTestId("override-error-outlet").textContent).toContain(
      "patch_not_in_mesh",
    );
  });

  // ─── Codex R2 P3 closure · faceIndex survives a parallel save ───
  // The R1 model guarded faceIndex with the same gen token as saves,
  // so any save dispatched before the faceIndex GET resolved would
  // permanently drop the highlight data. The R2 split scopes
  // faceIndex to caseGen only, never to save-seq.
  it("preserves faceIndex when a save lands before it resolves", async () => {
    getPatchClassificationMock.mockResolvedValueOnce(baseState);
    putPatchClassificationMock.mockResolvedValueOnce({
      ...baseState,
      overrides: { wall_left: "symmetry" },
    });

    let resolveFaceIndex!: (doc: FaceIndexDocument) => void;
    const pendingFaceIndex = new Promise<FaceIndexDocument>((r) => {
      resolveFaceIndex = r;
    });
    getFaceIndexMock.mockReset();
    getFaceIndexMock.mockReturnValueOnce(pendingFaceIndex);

    render(<PatchClassificationPanel caseId="case-1" pickedFaceId="f3" />);
    await screen.findByTestId("patch-classification-panel");

    // Save fires + completes BEFORE faceIndex resolves.
    await userEvent.selectOptions(
      screen.getByTestId("override-select-wall_left"),
      "symmetry",
    );
    await waitFor(() => {
      expect(
        (
          screen.getByTestId(
            "override-select-wall_left",
          ) as HTMLSelectElement
        ).value,
      ).toBe("symmetry");
    });

    // Now faceIndex finally resolves — must still highlight the row.
    resolveFaceIndex(baseFaceIndex);
    await waitFor(() => {
      expect(
        screen
          .getByTestId("patch-row-wall_left")
          .getAttribute("data-picked"),
      ).toBe("true");
    });
  });

  // ─── Codex R1 P1 #2 closure · caseId mid-flight ───
  // The parent mounts the panel with key={caseId}, so a caseId switch
  // remounts and starts fresh. As an extra defense, the panel itself
  // bumps stateGenRef on caseId change so even an in-flight GET from
  // the previous case is dropped before it can rehydrate the new one.
  it("drops a stale GET that resolves after caseId changes", async () => {
    let resolveOld!: (s: PatchClassificationState) => void;
    const oldGet = new Promise<PatchClassificationState>((r) => {
      resolveOld = r;
    });
    const newState: PatchClassificationState = {
      ...baseState,
      case_id: "case-2",
      overrides: { inlet: "velocity_inlet" },
    };
    getPatchClassificationMock
      .mockReturnValueOnce(oldGet)
      .mockResolvedValueOnce(newState);

    const { rerender } = render(
      <PatchClassificationPanel caseId="case-1" pickedFaceId={null} />,
    );
    // Switch to case-2 BEFORE the case-1 GET resolves.
    rerender(<PatchClassificationPanel caseId="case-2" pickedFaceId={null} />);

    // Now resolve the stale case-1 GET with surprising data; it must
    // not land because the generation token has moved.
    resolveOld({ ...baseState, overrides: { wall_left: "symmetry" } });

    // The case-2 fetch should win — the inlet override is the marker.
    await waitFor(() => {
      expect(
        (
          screen.getByTestId("override-select-inlet") as HTMLSelectElement
        ).value,
      ).toBe("velocity_inlet");
    });
    // wall_left from the stale response must NOT have leaked through.
    expect(
      (
        screen.getByTestId(
          "override-select-wall_left",
        ) as HTMLSelectElement
      ).value,
    ).toBe("");
  });
});

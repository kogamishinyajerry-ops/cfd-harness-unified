// Step3SetupBC face-annotation save path tests (DEC-V61-098 Step 7b
// Codex round 1 HIGH closure — 409 revision_conflict re-fetch).

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Step3SetupBC } from "../steps/Step3SetupBC";
import {
  FacePickProvider,
  useFacePick,
} from "../FacePickContext";
import type { ReactNode } from "react";

const {
  setupBCMock,
  getFaceAnnotationsMock,
  putFaceAnnotationsMock,
} = vi.hoisted(() => ({
  setupBCMock: vi.fn(),
  getFaceAnnotationsMock: vi.fn(),
  putFaceAnnotationsMock: vi.fn(),
}));

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: {
      ...actual.api,
      setupBC: (...args: unknown[]) => setupBCMock(...args),
      getFaceAnnotations: (...args: unknown[]) =>
        getFaceAnnotationsMock(...args),
      putFaceAnnotations: (...args: unknown[]) =>
        putFaceAnnotationsMock(...args),
    },
  };
});

// A small harness that primes a picked face so the AnnotationPanel
// renders inside Step3SetupBC's body.
function PickedHarness({
  caseId,
  faceId,
  children,
}: {
  caseId: string;
  faceId: string;
  children: ReactNode;
}) {
  return (
    <FacePickProvider>
      <Primer faceId={faceId} />
      {children}
      <span data-testid="harness-case-id">{caseId}</span>
    </FacePickProvider>
  );
}

function Primer({ faceId }: { faceId: string }) {
  const { setPicked } = useFacePick();
  // Set the picked face on first render. Production wires this through
  // the Viewport's onFacePick callback; the test bypasses the kernel.
  if (faceId) {
    setTimeout(
      () => setPicked({ faceId, worldPosition: [0.5, 0.5, 0.5] }),
      0,
    );
  }
  return null;
}

describe("Step3SetupBC face-annotation save path", () => {
  beforeEach(() => {
    setupBCMock.mockReset();
    getFaceAnnotationsMock.mockReset();
    putFaceAnnotationsMock.mockReset();
  });

  it("happy path: save dispatches putFaceAnnotations with revision + sticky annotated_by", async () => {
    getFaceAnnotationsMock.mockResolvedValue({
      schema_version: 1,
      case_id: "abc",
      revision: 3,
      last_modified: "2026-04-29T00:00:00Z",
      faces: [],
    });
    putFaceAnnotationsMock.mockResolvedValue({
      schema_version: 1,
      case_id: "abc",
      revision: 4,
      last_modified: "2026-04-29T00:00:01Z",
      faces: [],
    });

    const user = userEvent.setup();
    render(
      <PickedHarness caseId="abc" faceId="fid_demo">
        <Step3SetupBC
          caseId="abc"
          onStepComplete={vi.fn()}
          onStepError={vi.fn()}
          registerAiAction={vi.fn()}
        />
      </PickedHarness>,
    );

    // Wait for the picked face to surface the AnnotationPanel.
    const nameInput = await screen.findByTestId("annotation-panel-name");
    await user.type(nameInput, "lid");
    await user.click(screen.getByTestId("annotation-panel-save"));

    await waitFor(() => expect(putFaceAnnotationsMock).toHaveBeenCalled());
    const [caseIdArg, body] = putFaceAnnotationsMock.mock.calls[0];
    expect(caseIdArg).toBe("abc");
    expect(body).toMatchObject({
      if_match_revision: 3,
      annotated_by: "human",
      faces: [
        expect.objectContaining({
          face_id: "fid_demo",
          name: "lid",
          confidence: "user_authoritative",
        }),
      ],
    });
  });

  it("Codex Step 7b R1: 409 revision_conflict re-fetches the latest doc", async () => {
    const { ApiError } = await import("@/api/client");
    getFaceAnnotationsMock
      .mockResolvedValueOnce({
        schema_version: 1,
        case_id: "abc",
        revision: 3,
        last_modified: "2026-04-29T00:00:00Z",
        faces: [],
      })
      // Re-fetch after the 409 returns the bumped revision.
      .mockResolvedValueOnce({
        schema_version: 1,
        case_id: "abc",
        revision: 5,
        last_modified: "2026-04-29T00:00:05Z",
        faces: [
          {
            face_id: "fid_demo",
            name: "lid_from_concurrent_writer",
            confidence: "ai_confident",
          },
        ],
      });
    putFaceAnnotationsMock.mockRejectedValueOnce(
      new ApiError(409, "putFaceAnnotations failed (409)", {
        failing_check: "revision_conflict",
        attempted_revision: 3,
        current_revision: 5,
      }),
    );

    const user = userEvent.setup();
    render(
      <PickedHarness caseId="abc" faceId="fid_demo">
        <Step3SetupBC
          caseId="abc"
          onStepComplete={vi.fn()}
          onStepError={vi.fn()}
          registerAiAction={vi.fn()}
        />
      </PickedHarness>,
    );

    const nameInput = await screen.findByTestId("annotation-panel-name");
    await user.type(nameInput, "lid");
    await user.click(screen.getByTestId("annotation-panel-save"));

    // The first PUT errors; the panel surfaces an inline message and
    // the component re-fetches.
    await waitFor(() =>
      expect(getFaceAnnotationsMock).toHaveBeenCalledTimes(2),
    );
    await waitFor(() =>
      expect(screen.getByTestId("annotation-panel-error")).toHaveTextContent(
        /revision conflict/i,
      ),
    );

    // Now retrying must use the BUMPED revision (5).
    putFaceAnnotationsMock.mockResolvedValueOnce({
      schema_version: 1,
      case_id: "abc",
      revision: 6,
      last_modified: "2026-04-29T00:00:06Z",
      faces: [],
    });
    await user.click(screen.getByTestId("annotation-panel-save"));

    await waitFor(() =>
      expect(putFaceAnnotationsMock).toHaveBeenCalledTimes(2),
    );
    const [, retryBody] = putFaceAnnotationsMock.mock.calls[1];
    expect(retryBody).toMatchObject({
      if_match_revision: 5,
      annotated_by: "human",
    });
  });
});

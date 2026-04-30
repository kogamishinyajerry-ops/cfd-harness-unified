// Step3SetupBC face-annotation save path tests (DEC-V61-098 Step 7b
// Codex round 1 HIGH closure — 409 revision_conflict re-fetch).

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { Step3SetupBC } from "../steps/Step3SetupBC";
import {
  FacePickProvider,
  useFacePick,
} from "../FacePickContext";
import { Step3StateProvider } from "../Step3StateContext";
import type { ReactNode } from "react";

const {
  setupBCMock,
  setupBCWithEnvelopeMock,
  getFaceAnnotationsMock,
  putFaceAnnotationsMock,
} = vi.hoisted(() => ({
  setupBCMock: vi.fn(),
  setupBCWithEnvelopeMock: vi.fn(),
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
      setupBCWithEnvelope: (...args: unknown[]) =>
        setupBCWithEnvelopeMock(...args),
      getFaceAnnotations: (...args: unknown[]) =>
        getFaceAnnotationsMock(...args),
      putFaceAnnotations: (...args: unknown[]) =>
        putFaceAnnotationsMock(...args),
    },
  };
});

// A small harness that primes a picked face so the AnnotationPanel
// renders inside Step3SetupBC's body. Wrapped in MemoryRouter so
// useSearchParams (M9 envelope-mode wiring) works.
function PickedHarness({
  caseId,
  faceId,
  children,
  initialEntries = ["/?ai_mode="],
}: {
  caseId: string;
  faceId: string;
  children: ReactNode;
  initialEntries?: string[];
}) {
  return (
    <MemoryRouter initialEntries={initialEntries}>
      <FacePickProvider>
        <Step3StateProvider caseId={caseId}>
          <Primer faceId={faceId} />
          {children}
          <span data-testid="harness-case-id">{caseId}</span>
        </Step3StateProvider>
      </FacePickProvider>
    </MemoryRouter>
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
    setupBCWithEnvelopeMock.mockReset();
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

describe("Step3SetupBC envelope-mode (M9 Tier-B AI)", () => {
  beforeEach(() => {
    setupBCMock.mockReset();
    setupBCWithEnvelopeMock.mockReset();
    getFaceAnnotationsMock.mockReset();
    putFaceAnnotationsMock.mockReset();
  });

  it("ai_mode=force_uncertain: clicking [AI 处理] dispatches envelope mode + renders DialogPanel", async () => {
    getFaceAnnotationsMock.mockResolvedValue({
      schema_version: 1,
      case_id: "abc",
      revision: 1,
      last_modified: "2026-04-29T00:00:00Z",
      faces: [],
    });
    setupBCWithEnvelopeMock.mockResolvedValueOnce({
      confidence: "uncertain",
      summary: "Please confirm the lid orientation.",
      annotations_revision_consumed: 1,
      annotations_revision_after: 1,
      unresolved_questions: [
        {
          id: "lid_orientation",
          kind: "face_label",
          prompt: "Click the lid face.",
          needs_face_selection: true,
          candidate_face_ids: [],
          candidate_options: [],
          default_answer: null,
        },
      ],
      next_step_suggestion: "Click [继续 AI 处理].",
      error_detail: null,
    });

    let registeredAction: (() => Promise<void>) | null = null;
    const registerAiAction = vi.fn(
      (action: (() => Promise<void>) | null) => {
        registeredAction = action;
      },
    );
    render(
      <MemoryRouter initialEntries={["/?ai_mode=force_uncertain"]}>
        <FacePickProvider>
          <Step3StateProvider caseId="abc">
            <Step3SetupBC
              caseId="abc"
              onStepComplete={vi.fn()}
              onStepError={vi.fn()}
              registerAiAction={registerAiAction}
            />
          </Step3StateProvider>
        </FacePickProvider>
      </MemoryRouter>,
    );

    expect(
      await screen.findByTestId("step3-envelope-mode-banner"),
    ).toBeInTheDocument();

    // The shell calls the registered action (simulated [AI 处理] click).
    await waitFor(() => expect(registerAiAction).toHaveBeenCalled());
    expect(registeredAction).not.toBeNull();
    await registeredAction!();

    await waitFor(() =>
      expect(setupBCWithEnvelopeMock).toHaveBeenCalledWith(
        "abc",
        expect.objectContaining({ forceUncertain: true }),
      ),
    );
    expect(await screen.findByTestId("dialog-panel")).toBeInTheDocument();
    expect(screen.getByTestId("dialog-panel-confidence")).toHaveTextContent(
      "uncertain",
    );
  });

  it("face pick during dialog routes to the active face question", async () => {
    getFaceAnnotationsMock.mockResolvedValue({
      schema_version: 1,
      case_id: "abc",
      revision: 1,
      last_modified: "2026-04-29T00:00:00Z",
      faces: [],
    });
    setupBCWithEnvelopeMock.mockResolvedValueOnce({
      confidence: "uncertain",
      summary: "Please confirm the lid.",
      annotations_revision_consumed: 1,
      annotations_revision_after: 1,
      unresolved_questions: [
        {
          id: "lid_orientation",
          kind: "face_label",
          prompt: "Click the lid face.",
          needs_face_selection: true,
          candidate_face_ids: [],
          candidate_options: [],
          default_answer: null,
        },
      ],
      next_step_suggestion: null,
      error_detail: null,
    });

    let registeredAction: (() => Promise<void>) | null = null;
    render(
      <MemoryRouter initialEntries={["/?ai_mode=force_uncertain"]}>
        <FacePickProvider>
          <Step3StateProvider caseId="abc">
            <Primer faceId="" />
            <Step3SetupBC
              caseId="abc"
              onStepComplete={vi.fn()}
              onStepError={vi.fn()}
              registerAiAction={(action) => {
                registeredAction = action;
              }}
            />
            <FacePushHelper />
          </Step3StateProvider>
        </FacePickProvider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(registeredAction).not.toBeNull());
    await registeredAction!();
    await screen.findByTestId("dialog-panel");

    // Simulate a viewport pick: clicking the FacePushHelper button
    // calls setPicked({ faceId: 'fid_lid_a', ... }). The Step3SetupBC
    // useEffect routes that to the active face question.
    const user = userEvent.setup();
    await user.click(screen.getByTestId("test-pick-button"));

    await waitFor(() =>
      expect(
        screen.getByTestId("dialog-panel-face-hint-lid_orientation"),
      ).toHaveTextContent(/picked: fid_lid_a/i),
    );
  });

  it("envelope confident on first call → step completes (no dialog)", async () => {
    getFaceAnnotationsMock.mockResolvedValue({
      schema_version: 1,
      case_id: "abc",
      revision: 1,
      last_modified: "2026-04-29T00:00:00Z",
      faces: [],
    });
    setupBCWithEnvelopeMock.mockResolvedValueOnce({
      confidence: "confident",
      summary: "All set.",
      annotations_revision_consumed: 1,
      annotations_revision_after: 1,
      unresolved_questions: [],
      next_step_suggestion: null,
      error_detail: null,
    });

    let registeredAction: (() => Promise<void>) | null = null;
    const onStepComplete = vi.fn();
    render(
      <MemoryRouter initialEntries={["/?ai_mode=force_uncertain"]}>
        <FacePickProvider>
          <Step3StateProvider caseId="abc">
            <Step3SetupBC
              caseId="abc"
              onStepComplete={onStepComplete}
              onStepError={vi.fn()}
              registerAiAction={(action) => {
                registeredAction = action;
              }}
            />
          </Step3StateProvider>
        </FacePickProvider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(registeredAction).not.toBeNull());
    await registeredAction!();
    await waitFor(() => expect(onStepComplete).toHaveBeenCalled());
    expect(screen.queryByTestId("dialog-panel")).toBeNull();
    expect(
      await screen.findByTestId("step3-envelope-success"),
    ).toBeInTheDocument();
  });

  it("[继续 AI 处理] saves picked face as user_authoritative + re-runs envelope", async () => {
    getFaceAnnotationsMock.mockResolvedValue({
      schema_version: 1,
      case_id: "abc",
      revision: 1,
      last_modified: "2026-04-29T00:00:00Z",
      faces: [],
    });
    setupBCWithEnvelopeMock
      .mockResolvedValueOnce({
        confidence: "uncertain",
        summary: "Confirm lid.",
        annotations_revision_consumed: 1,
        annotations_revision_after: 1,
        unresolved_questions: [
          {
            id: "lid_orientation",
            kind: "face_label",
            prompt: "Pick the lid.",
            needs_face_selection: true,
            candidate_face_ids: [],
            candidate_options: [],
            default_answer: null,
          },
        ],
        next_step_suggestion: null,
        error_detail: null,
      })
      // Re-run after resume returns confident.
      .mockResolvedValueOnce({
        confidence: "confident",
        summary: "Done.",
        annotations_revision_consumed: 2,
        annotations_revision_after: 2,
        unresolved_questions: [],
        next_step_suggestion: null,
        error_detail: null,
      });
    putFaceAnnotationsMock.mockResolvedValue({
      schema_version: 1,
      case_id: "abc",
      revision: 2,
      last_modified: "2026-04-29T00:00:01Z",
      faces: [{ face_id: "fid_lid_a", name: "lid_orientation" }],
    });

    let registeredAction: (() => Promise<void>) | null = null;
    const onStepComplete = vi.fn();
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/?ai_mode=force_uncertain"]}>
        <FacePickProvider>
          <Step3StateProvider caseId="abc">
            <Step3SetupBC
              caseId="abc"
              onStepComplete={onStepComplete}
              onStepError={vi.fn()}
              registerAiAction={(action) => {
                registeredAction = action;
              }}
            />
            <FacePushHelper />
          </Step3StateProvider>
        </FacePickProvider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(registeredAction).not.toBeNull());
    await registeredAction!();
    await screen.findByTestId("dialog-panel");

    // Pick the lid face → routes to lid_orientation question.
    await user.click(screen.getByTestId("test-pick-button"));
    await waitFor(() =>
      expect(
        screen.getByTestId("dialog-panel-face-hint-lid_orientation"),
      ).toHaveTextContent(/picked: fid_lid_a/i),
    );

    // Click [继续 AI 处理]. Resume composes "<face_id>:<label>" if a
    // text answer was typed; in this test the engineer didn't type
    // anything, so DialogPanel sends just "<face_id>".
    await user.click(screen.getByTestId("dialog-panel-resume"));

    await waitFor(() => expect(putFaceAnnotationsMock).toHaveBeenCalled());
    const [, putBody] = putFaceAnnotationsMock.mock.calls[0];
    expect(putBody).toMatchObject({
      if_match_revision: 1,
      annotated_by: "human",
      faces: [
        expect.objectContaining({
          face_id: "fid_lid_a",
          confidence: "user_authoritative",
        }),
      ],
    });

    // Re-run envelope mode without force flags.
    await waitFor(() =>
      expect(setupBCWithEnvelopeMock).toHaveBeenCalledTimes(2),
    );
    const [, secondCallOpts] = setupBCWithEnvelopeMock.mock.calls[1];
    expect(secondCallOpts).toEqual({});
    await waitFor(() => expect(onStepComplete).toHaveBeenCalled());
  });
});

// Helper: a small button that pushes a face pick into the context.
// The envelope-mode tests use this to simulate a viewport pick
// without spinning up the kernel.
function FacePushHelper() {
  const { setPicked } = useFacePick();
  return (
    <button
      type="button"
      data-testid="test-pick-button"
      onClick={() =>
        setPicked({
          faceId: "fid_lid_a",
          worldPosition: [0.5, 0.5, 1.0],
        })
      }
    >
      pick lid
    </button>
  );
}

describe("Step3SetupBC multi-question slot routing (M9 Step 3)", () => {
  beforeEach(() => {
    setupBCMock.mockReset();
    setupBCWithEnvelopeMock.mockReset();
    getFaceAnnotationsMock.mockReset();
    putFaceAnnotationsMock.mockReset();
  });

  it("two unresolved face questions → no auto-route until 'Select this face' is clicked", async () => {
    getFaceAnnotationsMock.mockResolvedValue({
      schema_version: 1,
      case_id: "abc",
      revision: 1,
      last_modified: "2026-04-29T00:00:00Z",
      faces: [],
    });
    setupBCWithEnvelopeMock.mockResolvedValueOnce({
      confidence: "uncertain",
      summary: "Channel needs inlet + outlet.",
      annotations_revision_consumed: 1,
      annotations_revision_after: 1,
      unresolved_questions: [
        {
          id: "inlet_face",
          kind: "face_label",
          prompt: "Pick the inlet.",
          needs_face_selection: true,
          candidate_face_ids: [],
          candidate_options: [],
          default_answer: "inlet",
        },
        {
          id: "outlet_face",
          kind: "face_label",
          prompt: "Pick the outlet.",
          needs_face_selection: true,
          candidate_face_ids: [],
          candidate_options: [],
          default_answer: "outlet",
        },
      ],
      next_step_suggestion: null,
      error_detail: null,
    });

    let registeredAction: (() => Promise<void>) | null = null;
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/?ai_mode="]}>
        <FacePickProvider>
          <Step3StateProvider caseId="abc">
            <Step3SetupBC
              caseId="abc"
              onStepComplete={vi.fn()}
              onStepError={vi.fn()}
              registerAiAction={(action) => {
                registeredAction = action;
              }}
            />
            <FacePushHelper />
          </Step3StateProvider>
        </FacePickProvider>
      </MemoryRouter>,
    );
    // ai_mode is empty (URL has ?ai_mode=) → envelope mode active.
    await waitFor(() => expect(registeredAction).not.toBeNull());
    await registeredAction!();
    await screen.findByTestId("dialog-panel");

    // Without clicking 'Select this face', a viewport pick should NOT
    // route to either question (multi-q safety).
    await user.click(screen.getByTestId("test-pick-button"));
    // Brief wait for any effect.
    await new Promise((r) => setTimeout(r, 30));
    expect(
      screen.getByTestId("dialog-panel-face-hint-inlet_face"),
    ).not.toHaveTextContent(/picked:/i);
    expect(
      screen.getByTestId("dialog-panel-face-hint-outlet_face"),
    ).not.toHaveTextContent(/picked:/i);
    // M9 Step 3 R1 Finding 2 (LOW) closure: a stray pick while an
    // envelope-with-face-questions is open MUST NOT surface
    // AnnotationPanel — the dialog flow is the only sanctioned
    // mutation surface in that state.
    expect(screen.queryByTestId("annotation-panel")).toBeNull();

    // Now click 'Select this face' on the outlet question, then pick.
    await user.click(
      screen.getByTestId("dialog-panel-select-face-outlet_face"),
    );
    await user.click(screen.getByTestId("test-pick-button"));
    await waitFor(() =>
      expect(
        screen.getByTestId("dialog-panel-face-hint-outlet_face"),
      ).toHaveTextContent(/picked: fid_lid_a/i),
    );
    // Inlet still empty.
    expect(
      screen.getByTestId("dialog-panel-face-hint-inlet_face"),
    ).not.toHaveTextContent(/picked:/i);
  });
});

// DialogPanel — renders unresolved_questions when AI returns
// confidence='uncertain' or 'blocked' (DEC-V61-098 spec_v2 §A7).

import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DialogPanel } from "../DialogPanel";
import type { AIActionEnvelope } from "../types";

function buildEnvelope(
  overrides: Partial<AIActionEnvelope> = {},
): AIActionEnvelope {
  return {
    confidence: "uncertain",
    summary: "I need a few inputs to finish.",
    annotations_revision_consumed: 0,
    annotations_revision_after: 0,
    unresolved_questions: [],
    next_step_suggestion: null,
    error_detail: null,
    ...overrides,
  };
}

describe("DialogPanel", () => {
  it("renders the summary and confidence badge", () => {
    render(
      <DialogPanel
        envelope={buildEnvelope({ summary: "Help me classify this face." })}
        onResume={vi.fn()}
      />,
    );
    expect(screen.getByTestId("dialog-panel")).toBeInTheDocument();
    expect(screen.getByTestId("dialog-panel-confidence")).toHaveTextContent(
      "uncertain",
    );
    expect(screen.getByText("Help me classify this face.")).toBeInTheDocument();
  });

  it("disables [继续 AI 处理] until every question is answered", async () => {
    const envelope = buildEnvelope({
      unresolved_questions: [
        {
          id: "q1",
          kind: "boundary_type",
          prompt: "What is the patch type for face A?",
          needs_face_selection: false,
          candidate_face_ids: [],
          candidate_options: ["wall", "patch"],
          default_answer: null,
        },
        {
          id: "q2",
          kind: "physics_value",
          prompt: "Inlet velocity (m/s)?",
          needs_face_selection: false,
          candidate_face_ids: [],
          candidate_options: [],
          default_answer: null,
        },
      ],
    });
    const user = userEvent.setup();
    render(<DialogPanel envelope={envelope} onResume={vi.fn()} />);

    const resume = screen.getByTestId("dialog-panel-resume");
    expect(resume).toBeDisabled();

    // Answer one question — still not enough.
    await user.selectOptions(
      screen.getByTestId("dialog-panel-options-q1"),
      "wall",
    );
    expect(resume).toBeDisabled();

    // Answer the second — now armed.
    await user.type(screen.getByTestId("dialog-panel-input-q2"), "1.5");
    await waitFor(() => expect(resume).not.toBeDisabled());
  });

  it("face-selection question stays incomplete until pickedFaceIdForQuestion is set", async () => {
    const envelope = buildEnvelope({
      unresolved_questions: [
        {
          id: "qFace",
          kind: "face_label",
          prompt: "Which face is the inlet?",
          needs_face_selection: true,
          candidate_face_ids: [],
          candidate_options: [],
          default_answer: null,
        },
      ],
    });
    const { rerender } = render(
      <DialogPanel
        envelope={envelope}
        pickedFaceIdForQuestion={{}}
        onResume={vi.fn()}
      />,
    );
    expect(screen.getByTestId("dialog-panel-face-hint-qFace")).toHaveTextContent(
      /click a face/i,
    );
    expect(screen.getByTestId("dialog-panel-resume")).toBeDisabled();

    rerender(
      <DialogPanel
        envelope={envelope}
        pickedFaceIdForQuestion={{ qFace: "fid_picked123" }}
        onResume={vi.fn()}
      />,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("dialog-panel-face-hint-qFace"),
      ).toHaveTextContent(/picked: fid_picked12/i);
    });
    expect(screen.getByTestId("dialog-panel-resume")).not.toBeDisabled();
  });

  it("seeds default_answer values into the form", () => {
    const envelope = buildEnvelope({
      unresolved_questions: [
        {
          id: "qD",
          kind: "boundary_type",
          prompt: "x?",
          needs_face_selection: false,
          candidate_face_ids: [],
          candidate_options: ["wall", "patch"],
          default_answer: "wall",
        },
      ],
    });
    render(<DialogPanel envelope={envelope} onResume={vi.fn()} />);
    expect(
      (screen.getByTestId("dialog-panel-options-qD") as HTMLSelectElement)
        .value,
    ).toBe("wall");
    expect(screen.getByTestId("dialog-panel-resume")).not.toBeDisabled();
  });

  it("dispatches onResume with answers; face questions embed face_id", async () => {
    const onResume = vi.fn(() => Promise.resolve());
    const envelope = buildEnvelope({
      unresolved_questions: [
        {
          id: "qFace",
          kind: "face_label",
          prompt: "Which face is the inlet?",
          needs_face_selection: true,
          candidate_face_ids: [],
          candidate_options: [],
          default_answer: null,
        },
        {
          id: "qBdy",
          kind: "boundary_type",
          prompt: "patch type?",
          needs_face_selection: false,
          candidate_face_ids: [],
          candidate_options: ["wall", "patch"],
          default_answer: null,
        },
      ],
    });
    const user = userEvent.setup();
    render(
      <DialogPanel
        envelope={envelope}
        pickedFaceIdForQuestion={{ qFace: "fid_inlet_99" }}
        onResume={onResume}
      />,
    );
    await user.type(
      screen.getByTestId("dialog-panel-input-qFace"),
      "primary",
    );
    await user.selectOptions(
      screen.getByTestId("dialog-panel-options-qBdy"),
      "patch",
    );
    await user.click(screen.getByTestId("dialog-panel-resume"));
    await waitFor(() => expect(onResume).toHaveBeenCalledTimes(1));
    expect(onResume).toHaveBeenCalledWith({
      qFace: "fid_inlet_99:primary",
      qBdy: "patch",
    });
  });

  it("renders error_detail when envelope.confidence='blocked'", () => {
    const envelope = buildEnvelope({
      confidence: "blocked",
      error_detail: "Mesh has multiple disconnected components.",
      unresolved_questions: [],
    });
    render(<DialogPanel envelope={envelope} onResume={vi.fn()} />);
    expect(screen.getByTestId("dialog-panel-confidence")).toHaveTextContent(
      "blocked",
    );
    expect(screen.getByTestId("dialog-panel-error-detail")).toHaveTextContent(
      /multiple disconnected components/,
    );
  });

  it("re-seeds answers when envelope identity changes", async () => {
    const env1 = buildEnvelope({
      unresolved_questions: [
        {
          id: "q1",
          kind: "boundary_type",
          prompt: "a?",
          needs_face_selection: false,
          candidate_face_ids: [],
          candidate_options: ["wall"],
          default_answer: "wall",
        },
      ],
    });
    const env2 = buildEnvelope({
      unresolved_questions: [
        {
          id: "q2",
          kind: "boundary_type",
          prompt: "b?",
          needs_face_selection: false,
          candidate_face_ids: [],
          candidate_options: ["patch"],
          default_answer: "patch",
        },
      ],
    });
    const { rerender } = render(
      <DialogPanel envelope={env1} onResume={vi.fn()} />,
    );
    expect(screen.queryByTestId("dialog-panel-options-q1")).toBeInTheDocument();
    rerender(<DialogPanel envelope={env2} onResume={vi.fn()} />);
    await waitFor(() => {
      expect(
        screen.queryByTestId("dialog-panel-options-q2"),
      ).toBeInTheDocument();
    });
    expect(screen.queryByTestId("dialog-panel-options-q1")).toBeNull();
  });
});

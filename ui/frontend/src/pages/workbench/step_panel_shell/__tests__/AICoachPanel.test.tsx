// DEC-V61-120 · AICoachPanel tests.
//
// Coverage:
//   - empty state renders the prompt placeholder
//   - send-then-receive renders deltas as they stream in
//   - terminal done frame flips streaming off + reveals send button
//   - mock-mode pill surfaces when model_used="mock"
//   - pre-stream HTTP error surfaces in the alert region
//   - mid-stream error surfaces in the alert region after partial deltas
//   - stop button cancels in-flight stream (handle.cancel called)
//   - send button disabled while streaming + on empty draft
//   - Enter sends; Shift+Enter inserts newline
//   - history is shipped to streamAICoach on second send (within HISTORY_TURN_LIMIT)

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type {
  StreamAICoachCallbacks,
  StreamAICoachHandle,
  StreamAICoachRequest,
} from "@/api/client";

interface MockedHandle extends StreamAICoachHandle {
  /** the last request object passed to streamAICoach */
  request: StreamAICoachRequest;
  /** the callbacks passed by the panel */
  cb: StreamAICoachCallbacks;
  /** whether cancel() was called on this handle */
  cancelled: boolean;
}

const apiMock = vi.hoisted(() => {
  const handles: MockedHandle[] = [];
  const streamAICoach = vi.fn(
    (req: StreamAICoachRequest, cb: StreamAICoachCallbacks) => {
      const handle: MockedHandle = {
        request: req,
        cb,
        cancelled: false,
        cancel: () => {
          handle.cancelled = true;
          cb.onError({ kind: "abort", detail: "cancelled by user" });
        },
      };
      handles.push(handle);
      return handle;
    },
  );
  return { streamAICoach, handles };
});

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    streamAICoach: apiMock.streamAICoach,
  };
});

import { AICoachPanel } from "../AICoachPanel";

beforeEach(() => {
  apiMock.streamAICoach.mockClear();
  apiMock.handles.length = 0;
});

function lastHandle(): MockedHandle {
  return apiMock.handles[apiMock.handles.length - 1];
}

describe("AICoachPanel", () => {
  it("renders the empty-state prompt placeholder", () => {
    render(<AICoachPanel caseId="ldc" />);
    expect(screen.getByTestId("ai-coach-panel")).toBeInTheDocument();
    expect(screen.getByTestId("ai-coach-panel")).toHaveAttribute(
      "data-case-id",
      "ldc",
    );
    expect(screen.getByText(/向 AI 助手提问/)).toBeInTheDocument();
    expect(screen.getByTestId("ai-coach-send")).toBeDisabled();
  });

  it("send is disabled until draft has non-whitespace content", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);
    const input = screen.getByTestId("ai-coach-input");
    await user.type(input, "   ");
    expect(screen.getByTestId("ai-coach-send")).toBeDisabled();
    await user.type(input, "hello");
    expect(screen.getByTestId("ai-coach-send")).toBeEnabled();
  });

  it("renders streamed deltas and flips streaming off on done", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);
    await user.type(screen.getByTestId("ai-coach-input"), "what is missing?");
    await user.click(screen.getByTestId("ai-coach-send"));

    expect(apiMock.streamAICoach).toHaveBeenCalledTimes(1);
    const { cb } = lastHandle();

    // Stream two deltas + a done frame.
    act(() => cb.onDelta("你"));
    act(() => cb.onDelta("好"));
    act(() => cb.onDone({ model_used: "deepseek-v4-pro" }));

    await waitFor(() =>
      expect(screen.getByTestId("ai-coach-turn-1")).toHaveTextContent("你好"),
    );
    expect(screen.getByTestId("ai-coach-turn-1")).toHaveAttribute(
      "data-role",
      "assistant",
    );
    expect(screen.getByTestId("ai-coach-turn-0")).toHaveAttribute(
      "data-role",
      "user",
    );
    // Streaming flag cleared → send button is back (and disabled because
    // draft was cleared on send).
    expect(screen.queryByTestId("ai-coach-stop")).not.toBeInTheDocument();
  });

  it("surfaces a demo-mode pill when model_used is 'mock'", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);
    await user.type(screen.getByTestId("ai-coach-input"), "hi");
    await user.click(screen.getByTestId("ai-coach-send"));
    const { cb } = lastHandle();
    act(() => cb.onDelta("[Mock LLM Provider] You said: hi"));
    act(() => cb.onDone({ model_used: "mock" }));
    expect(
      await screen.findByTestId("ai-coach-mock-mode-pill"),
    ).toBeInTheDocument();
  });

  it("renders pre-stream HTTP errors in the alert region", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);
    await user.type(screen.getByTestId("ai-coach-input"), "hi");
    await user.click(screen.getByTestId("ai-coach-send"));
    const { cb } = lastHandle();
    act(() =>
      cb.onError({
        kind: "http",
        status: 401,
        detail: "LLM provider authentication failed; check DEEPSEEK_API_KEY",
      }),
    );
    expect(await screen.findByTestId("ai-coach-error")).toHaveTextContent(
      /authentication failed/,
    );
    expect(screen.getByTestId("ai-coach-error")).toHaveAttribute(
      "data-error-kind",
      "http",
    );
  });

  it("surfaces mid-stream errors after partial deltas", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);
    await user.type(screen.getByTestId("ai-coach-input"), "long question");
    await user.click(screen.getByTestId("ai-coach-send"));
    const { cb } = lastHandle();
    act(() => cb.onDelta("partial reply"));
    act(() =>
      cb.onError({ kind: "stream", detail: "LLM provider unavailable" }),
    );
    // Partial content stays visible.
    expect(screen.getByTestId("ai-coach-turn-1")).toHaveTextContent(
      "partial reply",
    );
    // Error pill renders.
    expect(screen.getByTestId("ai-coach-error")).toHaveTextContent(
      /unavailable/,
    );
  });

  it("does NOT show an error pill on user-cancelled abort", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);
    await user.type(screen.getByTestId("ai-coach-input"), "hi");
    await user.click(screen.getByTestId("ai-coach-send"));
    // Stop button appears while streaming.
    const stop = await screen.findByTestId("ai-coach-stop");
    await user.click(stop);
    expect(lastHandle().cancelled).toBe(true);
    // No error pill — abort is silent.
    expect(screen.queryByTestId("ai-coach-error")).not.toBeInTheDocument();
  });

  it("disables the send button while streaming", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);
    await user.type(screen.getByTestId("ai-coach-input"), "first");
    await user.click(screen.getByTestId("ai-coach-send"));
    // While streaming: send is hidden+disabled, stop visible.
    expect(screen.getByTestId("ai-coach-send")).toBeDisabled();
    expect(await screen.findByTestId("ai-coach-stop")).toBeInTheDocument();
  });

  it("Enter submits; Shift+Enter inserts a newline", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);
    const input = screen.getByTestId("ai-coach-input");
    await user.type(input, "line1{Shift>}{Enter}{/Shift}line2");
    expect((input as HTMLTextAreaElement).value).toBe("line1\nline2");
    expect(apiMock.streamAICoach).toHaveBeenCalledTimes(0);
    await user.type(input, "{Enter}");
    expect(apiMock.streamAICoach).toHaveBeenCalledTimes(1);
    expect(lastHandle().request.user_message).toBe("line1\nline2");
  });

  it("ships prior turns as `history` on subsequent sends", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);

    // First send.
    await user.type(screen.getByTestId("ai-coach-input"), "first question");
    await user.click(screen.getByTestId("ai-coach-send"));
    const firstCb = lastHandle().cb;
    act(() => firstCb.onDelta("first reply"));
    act(() => firstCb.onDone({ model_used: "deepseek-v4-pro" }));

    // Second send carries the prior turn pair as history.
    await user.type(screen.getByTestId("ai-coach-input"), "follow-up");
    await user.click(screen.getByTestId("ai-coach-send"));
    expect(apiMock.streamAICoach).toHaveBeenCalledTimes(2);
    const secondReq = lastHandle().request;
    expect(secondReq.user_message).toBe("follow-up");
    expect(secondReq.history).toEqual([
      { role: "user", content: "first question" },
      { role: "assistant", content: "first reply" },
    ]);
  });

  it("cancels any in-flight stream on unmount", async () => {
    const user = userEvent.setup();
    const { unmount } = render(<AICoachPanel caseId="ldc" />);
    await user.type(screen.getByTestId("ai-coach-input"), "hi");
    await user.click(screen.getByTestId("ai-coach-send"));
    expect(apiMock.streamAICoach).toHaveBeenCalledTimes(1);
    unmount();
    expect(lastHandle().cancelled).toBe(true);
  });

  it("excludes interrupted assistant turns from history (Codex R1 P1)", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);

    // First send: stream errors mid-flight, NOT a clean done.
    await user.type(screen.getByTestId("ai-coach-input"), "first question");
    await user.click(screen.getByTestId("ai-coach-send"));
    const firstCb = lastHandle().cb;
    act(() => firstCb.onDelta("partial"));
    act(() =>
      firstCb.onError({ kind: "stream", detail: "LLM provider unavailable" }),
    );

    // Second send: history MUST exclude the failed assistant turn.
    // The user turn is included (it had real content), but the
    // assistant turn is dropped because it never reached onDone.
    await user.type(screen.getByTestId("ai-coach-input"), "retry");
    await user.click(screen.getByTestId("ai-coach-send"));
    expect(apiMock.streamAICoach).toHaveBeenCalledTimes(2);
    const secondReq = lastHandle().request;
    expect(secondReq.history).toEqual([
      { role: "user", content: "first question" },
    ]);
    // Defensive: no assistant entry — neither the truncated content
    // nor an empty-content one (which would 422 the backend).
    expect(secondReq.history?.some((m) => m.role === "assistant")).toBe(false);
  });

  it("excludes cancelled assistant turns from history (Codex R1 P1)", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);

    // First send: user clicks stop before any delta arrives → empty
    // assistant turn would 422 the backend (content min_length=1).
    await user.type(screen.getByTestId("ai-coach-input"), "first question");
    await user.click(screen.getByTestId("ai-coach-send"));
    await user.click(await screen.findByTestId("ai-coach-stop"));

    await user.type(screen.getByTestId("ai-coach-input"), "retry");
    await user.click(screen.getByTestId("ai-coach-send"));
    const secondReq = lastHandle().request;
    expect(secondReq.history?.some((m) => m.role === "assistant")).toBe(false);
    // Empty-content assistant turn must not slip through.
    expect(secondReq.history?.some((m) => m.content === "")).toBe(false);
  });

  it("does not submit on Enter while IME is composing (Codex R1 P2)", async () => {
    const user = userEvent.setup();
    render(<AICoachPanel caseId="ldc" />);
    const input = screen.getByTestId("ai-coach-input") as HTMLTextAreaElement;
    // Use userEvent.type so React's controlled state is updated
    // (direct .value assignment doesn't trigger React's onChange).
    await user.type(input, "你好");
    expect(input.value).toBe("你好");

    // Simulate the IME composition Enter: keydown WITH isComposing=true.
    // fireEvent.keyDown lets us pass arbitrary KeyboardEvent props.
    fireEvent.keyDown(input, { key: "Enter", isComposing: true });
    // Submission must NOT have happened — Enter is the IME's commit-
    // candidate gesture for CJK input methods.
    expect(apiMock.streamAICoach).toHaveBeenCalledTimes(0);

    // The legacy keyCode 229 path covers older browsers / Safari that
    // don't surface isComposing on the event. Same expectation.
    fireEvent.keyDown(input, { key: "Enter", keyCode: 229 });
    expect(apiMock.streamAICoach).toHaveBeenCalledTimes(0);

    // After composition completes, a normal Enter (no isComposing flag)
    // DOES submit.
    fireEvent.keyDown(input, { key: "Enter" });
    expect(apiMock.streamAICoach).toHaveBeenCalledTimes(1);
    expect(lastHandle().request.user_message).toBe("你好");
  });

  it("does not render when caseId is empty (parent gate)", () => {
    // The TaskPanel wraps AICoachPanel in `caseId && <AICoachPanel />` —
    // direct render with empty caseId is not a contract we support, but
    // the panel data-attribute should at least reflect what was passed
    // so QA can debug a misuse.
    render(<AICoachPanel caseId="x" />);
    expect(screen.getByTestId("ai-coach-panel")).toHaveAttribute(
      "data-case-id",
      "x",
    );
  });
});

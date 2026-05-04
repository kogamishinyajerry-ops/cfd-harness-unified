// DEC-V61-120 · AI coach chat panel.
//
// Pinned-bottom region in TaskPanel right rail. Streaming consumer
// for /api/ai-coach/stream (V61-119). Read-only adviser — V1 has no
// tool calling, no actions, no persistence (deferred to V61-121).
//
// The panel grounds AI responses in the case completeness snapshot
// (V61-116) via the system prompt the backend composes. Engineers
// can ask free-form questions about their case and get streamed
// answers that reference field_path coordinates from the analyzer.
//
// Layout decision: ~280px fixed-height region with internal scroll
// for messages + textarea input pinned to bottom. Engineers always
// see the chat without scrolling past the per-step Body. Mobile
// adaptation is out of V1 scope (workbench is desktop-first).

import { useCallback, useEffect, useRef, useState } from "react";

import {
  streamAICoach,
  type StreamAICoachHandle,
} from "@/api/client";

interface AICoachPanelProps {
  caseId: string;
}

interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  /** Set on the assistant turn currently being streamed. */
  streaming?: boolean;
  /**
   * Codex R1 P1: only assistant turns that finished via onDone are
   * eligible for history replay on the next request. Cancelled
   * (abort) or errored streams MUST be excluded — empty content
   * would 422 the backend (CoachHistoryMessage.content min_length=1)
   * and truncated content would mislead the LLM with incomplete
   * prior context. Set ONLY in the onDone callback.
   */
  complete?: boolean;
  /** Set on the assistant turn whose final frame reported model="mock" — UI surfaces a "demo mode" pill. */
  mockMode?: boolean;
}

interface ErrorState {
  detail: string;
  /** "http" / "stream" / "network" — surfaced in audit-log title attribute, not in detail string. */
  kind: string;
}

const PANEL_HEIGHT_PX = 280;
const HISTORY_TURN_LIMIT = 16; // matches backend CoachStreamRequest.history max_length=32 with headroom

export function AICoachPanel({ caseId }: AICoachPanelProps) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<ErrorState | null>(null);

  const handleRef = useRef<StreamAICoachHandle | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const stickyBottomRef = useRef(true);

  // Auto-scroll to bottom on new content unless the user has scrolled
  // up — sticky-bottom heuristic so engineers reading earlier replies
  // aren't yanked away.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !stickyBottomRef.current) return;
    el.scrollTop = el.scrollHeight;
  }, [turns]);

  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.clientHeight - el.scrollTop;
    stickyBottomRef.current = distanceFromBottom < 24;
  }, []);

  const cancelInFlight = useCallback(() => {
    if (handleRef.current) {
      handleRef.current.cancel();
      handleRef.current = null;
    }
  }, []);

  // Cancel any in-flight stream when the component unmounts (e.g. case
  // switch via StepPanelShell's key={caseId} remount path). Without
  // this, a streaming request would race against the new mount and
  // its callbacks would fire into the unmounted component.
  useEffect(() => {
    return () => cancelInFlight();
  }, [cancelInFlight]);

  const send = useCallback(() => {
    const trimmed = draft.trim();
    if (!trimmed || streaming) return;

    const userTurn: ChatTurn = { role: "user", content: trimmed };
    const assistantTurn: ChatTurn = {
      role: "assistant",
      content: "",
      streaming: true,
    };
    // Take a snapshot of the prior turns to send as `history`. The
    // backend rejects role="system" in history (V119 validator), and
    // CoachHistoryMessage.content has min_length=1. Codex R1 P1: a
    // cancelled or errored assistant turn carries empty/truncated
    // content — exclude those (only `complete === true` is eligible).
    // User turns are ALWAYS eligible (they have content by definition
    // and never enter a streaming state).
    const historyForBackend = turns
      .filter((t) => t.role === "user" || t.complete === true)
      .slice(-HISTORY_TURN_LIMIT)
      .map(({ role, content }) => ({ role, content }));

    setTurns((prev) => [...prev, userTurn, assistantTurn]);
    setDraft("");
    setStreaming(true);
    setError(null);
    stickyBottomRef.current = true;

    handleRef.current = streamAICoach(
      {
        case_id: caseId,
        user_message: trimmed,
        history: historyForBackend,
      },
      {
        onDelta: (delta) => {
          setTurns((prev) => {
            // Append to the LAST assistant turn (the one we just
            // pushed). Defensive: only append if it's still streaming.
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (lastIdx >= 0 && next[lastIdx].streaming) {
              next[lastIdx] = {
                ...next[lastIdx],
                content: next[lastIdx].content + delta,
              };
            }
            return next;
          });
        },
        onDone: (final) => {
          setTurns((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (lastIdx >= 0 && next[lastIdx].streaming) {
              next[lastIdx] = {
                ...next[lastIdx],
                streaming: false,
                // Codex R1 P1: ONLY successful completion marks the
                // turn eligible for history replay. Errors and aborts
                // leave `complete` undefined, so the next send's
                // history filter drops them.
                complete: true,
                mockMode: final.model_used === "mock",
              };
            }
            return next;
          });
          setStreaming(false);
          handleRef.current = null;
        },
        onError: (err) => {
          // For abort: silently clean up the partially-streamed turn
          // (engineers explicitly cancelled, no error UI needed).
          setTurns((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (lastIdx >= 0 && next[lastIdx].streaming) {
              if (err.kind === "abort") {
                // Mark as no-longer-streaming; keep whatever content arrived.
                next[lastIdx] = { ...next[lastIdx], streaming: false };
              } else {
                // Non-abort error: keep the partial content but flip
                // streaming off so the user can retry.
                next[lastIdx] = { ...next[lastIdx], streaming: false };
              }
            }
            return next;
          });
          if (err.kind !== "abort") {
            setError({ detail: err.detail, kind: err.kind });
          }
          setStreaming(false);
          handleRef.current = null;
        },
      },
    );
  }, [caseId, draft, streaming, turns]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter sends; Shift+Enter inserts newline.
      // Codex R1 P2: when a CJK IME is mid-composition, the Enter
      // key commits the active candidate AND fires keydown — we
      // must not interpret that as "submit", or Chinese/Japanese/
      // Korean engineers send partial pinyin/romaji instead of
      // their actual prompt. `isComposing` (and the legacy
      // `keyCode === 229`) flag this case.
      const isComposing =
        e.nativeEvent.isComposing || e.nativeEvent.keyCode === 229;
      if (e.key === "Enter" && !e.shiftKey && !isComposing) {
        e.preventDefault();
        send();
      }
    },
    [send],
  );

  return (
    <section
      role="region"
      aria-label="AI 助手对话"
      data-testid="ai-coach-panel"
      data-case-id={caseId}
      className="flex flex-col border-t border-surface-800 bg-surface-950/60"
      style={{ height: `${PANEL_HEIGHT_PX}px`, minHeight: `${PANEL_HEIGHT_PX}px` }}
    >
      <header className="flex items-center justify-between border-b border-surface-800 px-3 py-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono uppercase tracking-wider text-surface-300">
            AI 助手
          </span>
          {turns.some((t) => t.mockMode) && (
            <span
              data-testid="ai-coach-mock-mode-pill"
              className="rounded bg-amber-900/40 px-1.5 py-0.5 text-[10px] font-mono uppercase text-amber-300"
              title="DEEPSEEK_API_KEY 未配置 · 当前回复来自 Mock provider"
            >
              demo mode
            </span>
          )}
        </div>
        {streaming && (
          <button
            type="button"
            onClick={cancelInFlight}
            data-testid="ai-coach-stop"
            aria-label="终止当前回复"
            className="rounded border border-surface-700 px-2 py-0.5 text-[11px] font-mono text-surface-200 hover:bg-surface-800"
          >
            stop
          </button>
        )}
      </header>

      <div
        ref={scrollRef}
        onScroll={onScroll}
        data-testid="ai-coach-scroll"
        className="flex-1 overflow-y-auto px-3 py-2 text-xs text-surface-200"
      >
        {turns.length === 0 ? (
          <p className="text-surface-500">
            向 AI 助手提问当前 case 的完整性、缺失字段或推荐做法。AI 只读，不会修改 case 数据。
          </p>
        ) : (
          turns.map((turn, idx) => (
            <div
              key={idx}
              data-testid={`ai-coach-turn-${idx}`}
              data-role={turn.role}
              className="mb-2"
            >
              <span
                className={`mr-1 inline-block font-mono text-[10px] uppercase tracking-wider ${
                  turn.role === "user"
                    ? "text-surface-400"
                    : "text-emerald-400"
                }`}
              >
                {turn.role === "user" ? "你" : "AI"}
              </span>
              <span
                aria-live={turn.streaming ? "polite" : "off"}
                className="whitespace-pre-wrap"
              >
                {turn.content}
                {turn.streaming && (
                  <span
                    className="ml-0.5 inline-block animate-pulse text-surface-500"
                    aria-hidden="true"
                  >
                    ▍
                  </span>
                )}
              </span>
            </div>
          ))
        )}
      </div>

      {error && (
        <div
          role="alert"
          data-testid="ai-coach-error"
          data-error-kind={error.kind}
          className="border-t border-rose-800/60 bg-rose-950/40 px-3 py-1 text-[11px] text-rose-200"
        >
          {error.detail}
        </div>
      )}

      <div className="border-t border-surface-800 p-2">
        <div className="flex gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={streaming}
            rows={2}
            placeholder="向 AI 助手提问 …  (Enter 发送, Shift+Enter 换行)"
            aria-label="向 AI 助手提问"
            data-testid="ai-coach-input"
            className="flex-1 resize-none rounded border border-surface-700 bg-surface-900 px-2 py-1 text-xs text-surface-100 placeholder:text-surface-600 disabled:cursor-not-allowed disabled:opacity-60"
          />
          <button
            type="button"
            onClick={send}
            disabled={!draft.trim() || streaming}
            data-testid="ai-coach-send"
            aria-label="发送"
            className="self-stretch rounded border border-emerald-700 bg-emerald-900/40 px-3 text-xs font-mono uppercase text-emerald-200 hover:bg-emerald-800/60 disabled:cursor-not-allowed disabled:opacity-50"
          >
            send
          </button>
        </div>
      </div>
    </section>
  );
}

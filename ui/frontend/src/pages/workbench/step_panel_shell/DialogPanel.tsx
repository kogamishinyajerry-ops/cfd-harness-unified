// Right-rail AI dialog panel (DEC-V61-098 spec_v2 §A7).
//
// Renders unresolved_questions when the AIActionEnvelope returns
// confidence='uncertain' or 'blocked'. Each question carries a kind:
//   - face_label / boundary_type: shown as a candidate-options dropdown
//   - physics_value: free-text input
//   - free_text: free-text textarea
//
// When `needs_face_selection` is set, the question can ONLY be answered
// after the engineer picks a face in the Viewport. The shell exposes
// that signal via `pickedFaceIdForQuestion` — until it's set the row
// stays in "awaiting face selection" state.
//
// Once every required question has an answer the [继续 AI 处理] button
// arms; clicking it calls `onResume` with the assembled answers map.

import { useEffect, useState } from "react";

import type { AIActionEnvelope, UnresolvedQuestion } from "./types";

interface DialogPanelProps {
  envelope: AIActionEnvelope;
  /** Map from question.id → currently-picked face_id. The shell wires
   *  this from the FacePickContext when a face question is "active".
   *  Optional — face questions surface a "select a face" hint until set.
   */
  pickedFaceIdForQuestion?: Record<string, string | undefined>;
  /** The id of the face-selection question that should currently
   *  receive viewport picks. Codex M9 Step 1 R1 flagged that picking
   *  always routed to "first unresolved" — under rapid double-clicks
   *  the second pick silently overwrote the first. Step 3 fix: the
   *  engineer explicitly picks WHICH question to answer next via the
   *  "Select this face" button on each row. The shell tracks the
   *  active id and routes pick events to that specific slot.
   *  Falls back to the first unresolved face question when unset.
   */
  activeFaceQuestionId?: string | null;
  /** Fired when the engineer clicks "Select this face" on a question
   *  row to direct the next viewport pick. Caller stores in shell state.
   */
  onSelectActiveFaceQuestion?: (questionId: string) => void;
  /** Disabled while the AI is mid-run or the page is offline. */
  disabled?: boolean;
  /** Fires when the engineer clicks [继续 AI 处理]. The map keys are
   *  question.id values. The caller is responsible for re-running the
   *  AI action with the answers + the new revision token. */
  onResume: (answers: Record<string, string>) => Promise<void>;
}

function isAnswerComplete(
  q: UnresolvedQuestion,
  answer: string | undefined,
  pickedFaceId: string | undefined,
): boolean {
  if (q.needs_face_selection) {
    // Face-selection questions: a picked face is sufficient. Any text
    // answer is supplementary (e.g., a label). The DialogPanel
    // composes "<face_id>:<text>" only when text is present.
    return Boolean(pickedFaceId);
  }
  if (q.kind === "free_text") {
    return Boolean(answer && answer.trim().length > 0);
  }
  return Boolean(answer && answer.length > 0);
}

export function DialogPanel({
  envelope,
  pickedFaceIdForQuestion = {},
  activeFaceQuestionId = null,
  onSelectActiveFaceQuestion,
  disabled = false,
  onResume,
}: DialogPanelProps) {
  // Seed answers from each question's default_answer so confident
  // re-runs require minimal clicks.
  const [answers, setAnswers] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      envelope.unresolved_questions.map((q) => [
        q.id,
        q.default_answer ?? "",
      ]),
    ),
  );
  const [resumeInFlight, setResumeInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-seed when the envelope identity changes (a new AI run produced
  // a different question set).
  useEffect(() => {
    setAnswers(
      Object.fromEntries(
        envelope.unresolved_questions.map((q) => [
          q.id,
          q.default_answer ?? "",
        ]),
      ),
    );
    setError(null);
    setResumeInFlight(false);
  }, [envelope]);

  const allAnswered = envelope.unresolved_questions.every((q) =>
    isAnswerComplete(
      q,
      answers[q.id],
      pickedFaceIdForQuestion[q.id],
    ),
  );

  const submit = async () => {
    setError(null);
    setResumeInFlight(true);
    try {
      // For face-selection questions the resolved face_id is part of
      // the answer — embed it as `<face_id>:<answer>` so the action
      // wrapper can split it (or use the pickedFaceId alone if no
      // text answer was needed).
      const finalAnswers: Record<string, string> = { ...answers };
      for (const q of envelope.unresolved_questions) {
        if (q.needs_face_selection) {
          const fid = pickedFaceIdForQuestion[q.id];
          if (fid) {
            finalAnswers[q.id] = answers[q.id]
              ? `${fid}:${answers[q.id]}`
              : fid;
          }
        }
      }
      await onResume(finalAnswers);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setResumeInFlight(false);
    }
  };

  const isLocked = disabled || resumeInFlight;
  const accent =
    envelope.confidence === "blocked"
      ? "border-rose-500/40 bg-rose-500/10"
      : "border-amber-500/40 bg-amber-500/10";

  return (
    <div
      data-testid="dialog-panel"
      data-confidence={envelope.confidence}
      className={`space-y-3 rounded-sm border ${accent} p-3 text-[12px]`}
    >
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-surface-300">
          AI is asking
        </h3>
        <span
          data-testid="dialog-panel-confidence"
          className="rounded-sm border border-surface-700 bg-surface-950/60 px-1.5 py-0.5 font-mono text-[10px] uppercase text-surface-300"
        >
          {envelope.confidence}
        </span>
      </div>

      <p className="text-[11px] text-surface-200">{envelope.summary}</p>

      {envelope.error_detail && (
        <p
          data-testid="dialog-panel-error-detail"
          className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200"
        >
          {envelope.error_detail}
        </p>
      )}

      <ul className="space-y-2">
        {envelope.unresolved_questions.map((q) => {
          const pickedFid = pickedFaceIdForQuestion[q.id];
          const complete = isAnswerComplete(q, answers[q.id], pickedFid);
          const isActiveFaceSlot =
            q.needs_face_selection && activeFaceQuestionId === q.id;
          // Border highlight for the active question — engineer sees
          // at a glance which slot the next viewport pick fills.
          const borderClass = isActiveFaceSlot
            ? "border-emerald-400/60"
            : "border-surface-800";
          return (
            <li
              key={q.id}
              data-testid={`dialog-panel-question-${q.id}`}
              data-question-complete={complete ? "true" : "false"}
              data-question-active={isActiveFaceSlot ? "true" : "false"}
              className={`space-y-1 rounded-sm border ${borderClass} bg-surface-950/40 p-2`}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[11px] text-surface-100">{q.prompt}</span>
                <span className="font-mono text-[10px] text-surface-500">
                  {q.kind}
                </span>
              </div>

              {q.needs_face_selection && (
                <div className="flex items-center justify-between gap-2">
                  <div
                    data-testid={`dialog-panel-face-hint-${q.id}`}
                    className={`text-[10px] ${pickedFid ? "text-emerald-300" : "text-amber-200"}`}
                  >
                    {pickedFid
                      ? `Picked: ${pickedFid.slice(0, 12)}…`
                      : isActiveFaceSlot
                        ? "Click a face in the viewport now."
                        : "Click 'Select this face' to direct your next pick here."}
                  </div>
                  {onSelectActiveFaceQuestion && (
                    <button
                      type="button"
                      onClick={() => onSelectActiveFaceQuestion(q.id)}
                      disabled={isLocked || isActiveFaceSlot}
                      data-testid={`dialog-panel-select-face-${q.id}`}
                      className="rounded-sm border border-surface-600 bg-surface-900/80 px-2 py-0.5 text-[10px] font-mono text-surface-200 transition hover:bg-surface-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isActiveFaceSlot
                        ? "Active"
                        : pickedFid
                          ? "Re-pick"
                          : "Select this face"}
                    </button>
                  )}
                </div>
              )}

              {q.candidate_options.length > 0 ? (
                <select
                  value={answers[q.id] ?? ""}
                  disabled={isLocked}
                  onChange={(e) =>
                    setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                  }
                  data-testid={`dialog-panel-options-${q.id}`}
                  className="w-full rounded-sm border border-surface-700 bg-surface-900 px-2 py-1 text-[12px] text-surface-100 focus:border-emerald-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="">— choose —</option>
                  {q.candidate_options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : q.kind === "free_text" ? (
                <textarea
                  value={answers[q.id] ?? ""}
                  disabled={isLocked}
                  onChange={(e) =>
                    setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                  }
                  rows={2}
                  data-testid={`dialog-panel-textarea-${q.id}`}
                  className="w-full rounded-sm border border-surface-700 bg-surface-900 px-2 py-1 text-[11px] text-surface-100 focus:border-emerald-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                />
              ) : (
                <input
                  type="text"
                  value={answers[q.id] ?? ""}
                  disabled={isLocked}
                  onChange={(e) =>
                    setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                  }
                  data-testid={`dialog-panel-input-${q.id}`}
                  className="w-full rounded-sm border border-surface-700 bg-surface-900 px-2 py-1 text-[12px] text-surface-100 focus:border-emerald-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                />
              )}
            </li>
          );
        })}
      </ul>

      {error && (
        <p
          className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200"
          data-testid="dialog-panel-resume-error"
        >
          {error}
        </p>
      )}

      <div className="flex items-center justify-end pt-1">
        <button
          type="button"
          onClick={submit}
          disabled={isLocked || !allAnswered}
          data-testid="dialog-panel-resume"
          className="rounded-sm border border-emerald-500/60 bg-emerald-500/15 px-3 py-1 text-[11px] text-emerald-100 transition hover:bg-emerald-500/25 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {resumeInFlight ? "Resuming…" : "继续 AI 处理"}
        </button>
      </div>
    </div>
  );
}

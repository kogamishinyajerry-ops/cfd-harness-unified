// DEC-V61-121 · Inline approval card for an AI-emitted proposal.
//
// State machine (per card):
//
//     idle ──[Accept]──► applying ──┬─2xx─► applied
//                                   └─error─► error
//     idle ──[Reject]──► rejected (terminal)
//
// applied / rejected are TERMINAL — buttons hide so the engineer
// can't double-act. error returns to idle on the explicit "retry"
// affordance (clicking [Accept] again).
//
// Idempotency: while applying, [Accept] is disabled. The backend's
// V108 `upsert_override` is naturally idempotent for V1's only
// tool, but the UI still guards against double-click for future
// tools that may not be (V61-121 risk register #3).

import { useCallback, useState } from "react";

import {
  applyAIProposal,
  ApiError,
  type ApplyAIProposalResponse,
} from "@/api/client";

import type { ParsedProposal } from "./proposal_parser";

interface ProposalCardProps {
  caseId: string;
  proposal: ParsedProposal;
  /** model_used reported on the assistant turn that emitted this
   *  proposal; passed through to the audit entry. */
  modelUsed: string | null;
  /** Stable identifier of the assistant turn this proposal came from;
   *  passed through to the audit entry so operators can correlate
   *  proposals to chat turns. */
  turnId: string | null;
  /** Optional callback invoked after a successful apply so the parent
   *  can append a confirmation message to the chat history. */
  onApplied?: (result: ApplyAIProposalResponse) => void;
}

type CardState =
  | { kind: "idle" }
  | { kind: "applying" }
  | { kind: "applied"; result: ApplyAIProposalResponse }
  | { kind: "rejected" }
  | { kind: "error"; detail: string };

export function ProposalCard({
  caseId,
  proposal,
  modelUsed,
  turnId,
  onApplied,
}: ProposalCardProps) {
  const [state, setState] = useState<CardState>({ kind: "idle" });

  const accept = useCallback(async () => {
    if (state.kind === "applying" || state.kind === "applied") return;
    if (!proposal.ok || !proposal.tool || !proposal.args) return;
    setState({ kind: "applying" });
    try {
      const result = await applyAIProposal({
        case_id: caseId,
        tool: proposal.tool,
        args: proposal.args,
        model_used: modelUsed,
        conversation_turn_id: turnId,
      });
      setState({ kind: "applied", result });
      onApplied?.(result);
      // DEC-V61-131 N1.1: tools may now return advisory results
      // (e.g. regenerate_mesh after the strip). Advisory results
      // describe a SUGGESTION but do not mutate the case, so we MUST
      // NOT emit ``ai-coach:proposal-applied`` — listeners
      // (MeshQualityCard, Step2Mesh, PatchClassificationPanel) treat
      // that event as a real case mutation and would re-fetch /
      // display stale data as if the mesh had been regenerated.
      const isAdvisory =
        (result as { advisory?: boolean }).advisory === true;
      if (!isAdvisory) {
        // Codex base-review-4 P2: notify any open panels backed by
        // the case state we just mutated so they can re-fetch and
        // avoid showing stale data. PatchClassificationPanel (Step
        // 3) is the V121 case for set_patch_bc_type; future tools
        // that mutate case state should fold their relevant panel
        // listeners here. Using a window CustomEvent keeps the
        // parent-tree decoupled — ProposalCard doesn't need to know
        // which panel is mounted.
        try {
          window.dispatchEvent(
            new CustomEvent("ai-coach:proposal-applied", {
              detail: {
                caseId,
                tool: proposal.tool,
                audit_id: result.audit_id,
              },
            }),
          );
        } catch {
          // SSR / non-browser context — no-op.
        }
      }
    } catch (err) {
      let detail = "apply failed";
      if (err instanceof ApiError) {
        if (
          typeof err.detail === "object" &&
          err.detail !== null &&
          "failing_check" in err.detail
        ) {
          // V123 R2 P2-2: prefer the underlying typed code
          // (cell_cap_exceeded / symlink_escape / gmshToFoam_failed
          // etc) when the dispatcher carries one, so the engineer
          // sees the actionable remediation hint instead of the
          // generic 'underlying_service_error' wrapper.
          const d = err.detail as {
            failing_check: string;
            inner_failing_check?: string;
            tool?: string;
          };
          const code = d.inner_failing_check ?? d.failing_check;
          detail = `${code}${d.tool ? ` (${d.tool})` : ""}`;
        } else {
          detail = err.message;
        }
      } else if (err instanceof Error) {
        detail = err.message;
      }
      setState({ kind: "error", detail });
    }
  }, [caseId, modelUsed, onApplied, proposal, state.kind, turnId]);

  const reject = useCallback(() => {
    if (state.kind === "applying") return;
    setState({ kind: "rejected" });
  }, [state.kind]);

  if (!proposal.ok) {
    // Malformed — render a warning row instead of action buttons so
    // engineers see that the AI tried to propose something but the
    // format was wrong. Risk-1 in DEC: never throw.
    return (
      <div
        role="status"
        data-testid={`proposal-card-${proposal.index}`}
        data-card-state="malformed"
        className="my-2 rounded border border-amber-800/60 bg-amber-950/30 p-2 text-[11px] text-amber-200"
      >
        <div className="font-mono uppercase tracking-wider text-amber-300">
          AI 提案格式有误
        </div>
        <div className="mt-1">
          {proposal.malformedReason ?? "PROPOSAL block could not be parsed."}
        </div>
      </div>
    );
  }

  return (
    <div
      role="region"
      aria-label={`AI 提案 · ${proposal.tool}`}
      data-testid={`proposal-card-${proposal.index}`}
      data-card-state={state.kind}
      data-tool={proposal.tool ?? undefined}
      className="my-2 rounded border border-cyan-800/60 bg-cyan-950/30 p-2 text-[11px] text-cyan-100"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono uppercase tracking-wider text-cyan-300">
          AI 提案 · {proposal.tool}
        </span>
        {state.kind === "applied" && (
          <span
            className="rounded bg-emerald-900/40 px-1.5 py-0.5 text-[10px] uppercase text-emerald-300"
            data-testid={`proposal-card-applied-pill-${proposal.index}`}
          >
            ✓ 已应用
          </span>
        )}
        {state.kind === "rejected" && (
          <span className="rounded bg-surface-800 px-1.5 py-0.5 text-[10px] uppercase text-surface-400">
            已拒绝
          </span>
        )}
      </div>

      {proposal.reason && (
        <div className="mt-1 text-cyan-200">{proposal.reason}</div>
      )}

      <pre
        data-testid={`proposal-card-args-${proposal.index}`}
        className="mt-1 whitespace-pre-wrap rounded bg-surface-900/60 px-1.5 py-1 font-mono text-[10px] text-surface-300"
      >
        {JSON.stringify(proposal.args, null, 2)}
      </pre>

      {state.kind === "applied" && (
        <div className="mt-1 text-emerald-300" data-testid={`proposal-card-summary-${proposal.index}`}>
          {state.result.summary}
          {state.result.audit_warning && (
            <div className="mt-1 text-amber-300">
              ⚠ {state.result.audit_warning}
            </div>
          )}
        </div>
      )}

      {state.kind === "error" && (
        <div
          role="alert"
          data-testid={`proposal-card-error-${proposal.index}`}
          className="mt-1 text-rose-300"
        >
          {state.detail}
        </div>
      )}

      {(state.kind === "idle" || state.kind === "error") && (
        <div className="mt-1.5 flex gap-2">
          <button
            type="button"
            onClick={accept}
            data-testid={`proposal-card-accept-${proposal.index}`}
            className="rounded border border-emerald-700 bg-emerald-900/40 px-2 py-0.5 text-[11px] font-mono uppercase text-emerald-200 hover:bg-emerald-800/60"
          >
            {state.kind === "error" ? "重试" : "接受"}
          </button>
          <button
            type="button"
            onClick={reject}
            data-testid={`proposal-card-reject-${proposal.index}`}
            className="rounded border border-surface-700 bg-surface-900 px-2 py-0.5 text-[11px] font-mono uppercase text-surface-300 hover:bg-surface-800"
          >
            拒绝
          </button>
        </div>
      )}

      {state.kind === "applying" && (
        <div className="mt-1.5 text-cyan-300">应用中…</div>
      )}
    </div>
  );
}

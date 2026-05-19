// DEC-V61-160 (N6.4) · AI advisor panel (AI 审查 / AI 诊断 entries).
//
// Renders inside the right-rail Body region (alongside CompletenessCard
// + step-specific cards). Hosts the two V130 advisory entry points:
//
//   * AI 审查 — case review hypothesis list, GET /api/cases/{id}/ai-review
//   * AI 诊断 — failure-mode hypotheses, GET /api/cases/{id}/ai-diagnose
//
// Hard contracts (charter §Q4 + §"Why citation grounding is mandatory"):
//   * NO apply / submit / execute buttons. Only copy-to-clipboard
//     buttons for `message` / `recommended_change` / `summary` /
//     `suggested_fix`. Engineers read, decide, and act manually.
//   * Every finding/hypothesis renders its citation chip with path +
//     section anchor + sha[:8]. Click the chip to expand and read
//     the cited corpus chunk text inline (verifiable trail).
//   * `llm_available: false` → degradation banner explains the
//     rule-based path.
//   * "Advisory only — no mutation" badge always visible at top.

import { useCallback, useState } from "react";

import { api, ApiError } from "@/api/client";
import type {
  DiagnoseResponse,
  DiagnosisHypothesis,
  ReviewFinding,
  ReviewResponse,
} from "@/types/ai_advisor";

interface AIAdvisorPanelProps {
  caseId: string;
}

type AdvisorTab = "review" | "diagnose";

// V68-C.2 · LLM-offline graceful fallback. 5xx + network errors classify
// as "advisor offline" — the UI shows a calm degradation banner instead
// of a red ERROR card so engineers know the workbench is still safe (V130:
// advisor offline never blocks the rest of the workbench). 4xx errors are
// kept as harsh "error" because they signal a contract bug (invalid case
// id, bad query param) the engineer needs to fix.
type AdvisorFailureKind = "offline" | "error";

export interface ClassifiedAdvisorFailure {
  kind: AdvisorFailureKind;
  detail: string;
  status: number | null;
}

export function classifyAdvisorFailure(exc: unknown): ClassifiedAdvisorFailure {
  if (exc instanceof ApiError) {
    // 503/502 (upstream gateway / LLM provider down) + 500 (unhandled
    // backend exception) → offline. 504 timeout also offline.
    if (exc.status >= 500) {
      return {
        kind: "offline",
        detail: `${exc.status}: ${exc.message}`,
        status: exc.status,
      };
    }
    // 408 request timeout → offline (advisor took too long).
    if (exc.status === 408) {
      return { kind: "offline", detail: `${exc.status}: ${exc.message}`, status: exc.status };
    }
    // 4xx other than 408 = client/contract error → harsh error.
    return {
      kind: "error",
      detail: `${exc.status}: ${exc.message}`,
      status: exc.status,
    };
  }
  if (exc instanceof TypeError) {
    // `fetch` throws TypeError on network failure (DNS, CORS, dropped
    // connection) — backend is unreachable, which is functionally
    // identical to "advisor offline" from the engineer's POV.
    return { kind: "offline", detail: exc.message, status: null };
  }
  if (exc instanceof Error) {
    return { kind: "error", detail: exc.message, status: null };
  }
  return { kind: "error", detail: String(exc), status: null };
}

export function AIAdvisorPanel({ caseId }: AIAdvisorPanelProps) {
  const [activeTab, setActiveTab] = useState<AdvisorTab | null>(null);
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [diagnose, setDiagnose] = useState<DiagnoseResponse | null>(null);
  const [loading, setLoading] = useState<AdvisorTab | null>(null);
  const [failure, setFailure] = useState<ClassifiedAdvisorFailure | null>(null);

  const runReview = useCallback(async () => {
    setLoading("review");
    setFailure(null);
    setActiveTab("review");
    try {
      const resp = await api.getAIReview(caseId);
      setReview(resp);
    } catch (exc) {
      setFailure(classifyAdvisorFailure(exc));
    } finally {
      setLoading(null);
    }
  }, [caseId]);

  const runDiagnose = useCallback(async () => {
    setLoading("diagnose");
    setFailure(null);
    setActiveTab("diagnose");
    try {
      const resp = await api.getAIDiagnose(caseId);
      setDiagnose(resp);
    } catch (exc) {
      setFailure(classifyAdvisorFailure(exc));
    } finally {
      setLoading(null);
    }
  }, [caseId]);

  return (
    <section
      data-testid="ai-advisor-panel"
      aria-label="AI advisor"
      className="border-b border-surface-800 px-3 py-3 space-y-3"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-mono uppercase tracking-wider text-surface-300">
          AI 顾问
        </h3>
        <span
          data-testid="ai-advisor-advisory-badge"
          className="text-[10px] uppercase rounded border border-amber-700 bg-amber-950/30 px-1.5 py-0.5 text-amber-300"
          title="AI 仅给建议，不执行任何写入。Engineer reads, decides, applies manually."
        >
          advisory only · no mutation
        </span>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          data-testid="ai-advisor-review-button"
          onClick={runReview}
          disabled={loading !== null}
          className="flex-1 rounded border border-surface-700 bg-surface-900 px-2 py-1.5 text-xs hover:bg-surface-800 disabled:opacity-50"
        >
          {loading === "review" ? "AI 审查中…" : "AI 审查"}
        </button>
        <button
          type="button"
          data-testid="ai-advisor-diagnose-button"
          onClick={runDiagnose}
          disabled={loading !== null}
          className="flex-1 rounded border border-surface-700 bg-surface-900 px-2 py-1.5 text-xs hover:bg-surface-800 disabled:opacity-50"
        >
          {loading === "diagnose" ? "AI 诊断中…" : "AI 诊断"}
        </button>
      </div>

      {failure?.kind === "offline" && (
        <div
          data-testid="ai-advisor-offline"
          data-status={failure.status ?? "network"}
          role="status"
          className="rounded border border-amber-700 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-200"
        >
          <div className="font-mono uppercase tracking-wider text-[10px] text-amber-300">
            AI advisor offline · rest of workbench unaffected
          </div>
          <div className="mt-0.5 text-amber-200/80">
            The advisor is temporarily unreachable ({failure.detail}). Engineer
            can continue mesh / BC / solver work; click again later to retry.
          </div>
        </div>
      )}
      {failure?.kind === "error" && (
        <div
          data-testid="ai-advisor-error"
          role="alert"
          className="rounded border border-red-800 bg-red-950/30 px-2 py-1.5 text-xs text-red-300"
        >
          {failure.detail}
        </div>
      )}

      {activeTab === "review" && review && (
        <ReviewResultBlock data={review} />
      )}
      {activeTab === "diagnose" && diagnose && (
        <DiagnoseResultBlock data={diagnose} />
      )}
    </section>
  );
}

function DegradationBanner({ note }: { note: string }) {
  return (
    <div
      data-testid="ai-advisor-degradation-banner"
      role="note"
      className="rounded border border-amber-800 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-300"
    >
      <div className="font-mono uppercase tracking-wider text-[10px]">
        LLM unavailable · rule-based subset
      </div>
      <div className="mt-0.5 text-amber-200/80">{note}</div>
    </div>
  );
}

function CorpusFingerprint({ sha }: { sha: string }) {
  return (
    <div
      data-testid="ai-advisor-corpus-sha"
      className="text-[10px] font-mono text-surface-500"
      title="SHA-256 fingerprint of the loaded corpus — verify the rendered citations were sourced from a known corpus state"
    >
      corpus:{sha.slice(0, 12)}…
    </div>
  );
}

// ───────── Review block ─────────

function ReviewResultBlock({ data }: { data: ReviewResponse }) {
  return (
    <div data-testid="ai-advisor-review-block" className="space-y-2">
      {!data.llm_available && data.degradation_note && (
        <DegradationBanner note={data.degradation_note} />
      )}
      <CorpusFingerprint sha={data.corpus_sha} />
      {data.findings.length === 0 ? (
        <div className="text-xs text-surface-400 italic">
          No findings emitted. Either the case is clean or no corpus
          chunk grounded a hypothesis.
        </div>
      ) : (
        <ul className="space-y-2">
          {data.findings.map((finding, idx) => (
            <FindingItem
              key={`${finding.area}-${finding.severity}-${idx}`}
              finding={finding}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function FindingItem({ finding }: { finding: ReviewFinding }) {
  const sevClass =
    finding.severity === "critical"
      ? "border-red-700 bg-red-950/30 text-red-200"
      : finding.severity === "warning"
        ? "border-amber-700 bg-amber-950/30 text-amber-200"
        : "border-blue-800 bg-blue-950/30 text-blue-200";
  return (
    <li
      data-testid="ai-advisor-finding"
      data-severity={finding.severity}
      data-area={finding.area}
      data-source={finding.source}
      className={`rounded border px-2 py-1.5 text-xs ${sevClass}`}
    >
      <div className="flex items-center gap-2 text-[10px] uppercase font-mono">
        <span>{finding.severity}</span>
        <span>·</span>
        <span>{finding.area}</span>
        <span>·</span>
        <span>{finding.source}</span>
      </div>
      <div className="mt-1 text-surface-200">
        <CopyableText label="message" text={finding.message} />
      </div>
      {finding.recommended_change && (
        <div className="mt-1 text-surface-300/80">
          <CopyableText
            label="recommended_change"
            text={finding.recommended_change}
          />
        </div>
      )}
      <CitationChip
        chunkId={finding.citation.chunk_id}
        path={finding.citation.path}
        sectionAnchor={finding.citation.section_anchor}
        sha={finding.citation.sha}
        text={finding.citation.text}
      />
    </li>
  );
}

// ───────── Diagnose block ─────────

function DiagnoseResultBlock({ data }: { data: DiagnoseResponse }) {
  return (
    <div data-testid="ai-advisor-diagnose-block" className="space-y-2">
      {!data.llm_available && data.degradation_note && (
        <DegradationBanner note={data.degradation_note} />
      )}
      <CorpusFingerprint sha={data.corpus_sha} />
      {data.problem_hint && (
        <div className="text-[10px] font-mono text-surface-400">
          problem hint: {data.problem_hint}
        </div>
      )}
      {data.hypotheses.length === 0 ? (
        <div className="text-xs text-surface-400 italic">
          No hypotheses emitted. Either the case is clean or no
          corpus chunk grounded a diagnosis.
        </div>
      ) : (
        <ul className="space-y-2">
          {data.hypotheses.map((h, idx) => (
            <HypothesisItem
              key={`${h.failure_mode}-${idx}`}
              hypothesis={h}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function HypothesisItem({ hypothesis }: { hypothesis: DiagnosisHypothesis }) {
  const likeClass =
    hypothesis.likelihood === "high"
      ? "border-red-700 bg-red-950/30 text-red-200"
      : hypothesis.likelihood === "medium"
        ? "border-amber-700 bg-amber-950/30 text-amber-200"
        : "border-blue-800 bg-blue-950/30 text-blue-200";
  return (
    <li
      data-testid="ai-advisor-hypothesis"
      data-failure-mode={hypothesis.failure_mode}
      data-likelihood={hypothesis.likelihood}
      data-source={hypothesis.source}
      className={`rounded border px-2 py-1.5 text-xs ${likeClass}`}
    >
      <div className="flex items-center gap-2 text-[10px] uppercase font-mono">
        <span>{hypothesis.likelihood}</span>
        <span>·</span>
        <span>{hypothesis.failure_mode}</span>
        <span>·</span>
        <span>{hypothesis.source}</span>
      </div>
      <div className="mt-1 text-surface-200">
        <CopyableText label="summary" text={hypothesis.summary} />
      </div>
      {Object.keys(hypothesis.evidence).length > 0 && (
        <div className="mt-1 space-y-0.5 text-[11px] text-surface-300/80">
          {Object.entries(hypothesis.evidence).map(([k, v]) => (
            <div key={k} className="font-mono">
              <span className="text-surface-500">{k}:</span> {v}
            </div>
          ))}
        </div>
      )}
      {hypothesis.suggested_fix && (
        <div className="mt-1 text-surface-300/80">
          <CopyableText
            label="suggested_fix"
            text={hypothesis.suggested_fix}
          />
        </div>
      )}
      <CitationChip
        chunkId={hypothesis.citation.chunk_id}
        path={hypothesis.citation.path}
        sectionAnchor={hypothesis.citation.section_anchor}
        sha={hypothesis.citation.sha}
        text={hypothesis.citation.text}
      />
    </li>
  );
}

// ───────── Shared sub-components ─────────

function CopyableText({ label, text }: { label: string; text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      }
    } catch {
      // Best-effort; clipboard may be unavailable in some contexts.
    }
  }, [text]);

  return (
    <div className="flex items-start gap-2">
      <span className="flex-1 whitespace-pre-wrap break-words">{text}</span>
      <button
        type="button"
        onClick={copy}
        data-testid={`copy-${label}`}
        className="shrink-0 rounded border border-surface-700 px-1.5 py-0.5 text-[10px] uppercase font-mono hover:bg-surface-800"
        aria-label={`copy ${label}`}
        title={`Copy ${label} to clipboard (Engineer applies manually)`}
      >
        {copied ? "✓" : "copy"}
      </button>
    </div>
  );
}

function CitationChip({
  chunkId,
  path,
  sectionAnchor,
  sha,
  text,
}: {
  chunkId: string;
  path: string;
  sectionAnchor: string | null;
  sha: string;
  text: string;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="mt-1.5">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        data-testid="ai-advisor-citation-chip"
        data-chunk-id={chunkId}
        className="text-[10px] font-mono text-surface-400 underline decoration-dotted hover:text-surface-200"
        title="Click to expand the cited corpus chunk text"
      >
        {path}
        {sectionAnchor ? ` § ${sectionAnchor}` : ""} · sha:{sha.slice(0, 8)}
      </button>
      {expanded && (
        <pre
          data-testid="ai-advisor-citation-text"
          className="mt-1 max-h-48 overflow-y-auto whitespace-pre-wrap rounded border border-surface-700 bg-surface-950 px-2 py-1 text-[11px] text-surface-300"
        >
          {text}
        </pre>
      )}
    </div>
  );
}

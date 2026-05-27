/**
 * V71-UI-V3 · AdvisorContent · right-panel Advisor tab
 *
 * Per .planning/blueprints/v3/INDEX.md Image 06 (Advisor surface).
 *
 * V130/V132 invariants (HARD CONTRACT · enforced by V71.4 contract test):
 *   - GET-only · NEVER mutates case state · no POST/PUT/DELETE
 *   - NO "apply" / "submit" / "execute" / "run" / "auto-fix" buttons
 *   - Every finding/hypothesis carries a citation block (path · sha · anchor)
 *   - llm_available=false → "advisor offline" calm banner · not red error
 *   - The recommended_change / suggested_fix render as text the engineer
 *     copies and applies manually.
 */
import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type {
  DiagnoseResponse,
  DiagnosisHypothesis,
  ReviewFinding,
  ReviewResponse,
  CitedChunk,
} from "@/types/ai_advisor";
import type { CaseIndexEntry } from "@/types/validation";
import type { StepId } from "../../WorkbenchShellV3";
import { SkeletonAdvisor } from "../SkeletonV3";
import { AdvisorCommentaryV4 } from "./AdvisorCommentaryV4";
import { FailureModeShowcaseV5 } from "./FailureModeShowcaseV5";
import { PostRunAdvisorV9 } from "./PostRunAdvisorV9";
import type { MatchedCommentary } from "@/data/advisor_pattern_matcher";

interface AdvisorContentProps {
  caseId: string | null;
  stepId: StepId;
  /** V83.3 · V5.B failure-mode showcase opt-in · plumbed from
   *  WorkbenchShellV3 which is already inside a Router context. */
  failmodeActive?: boolean;
  /** V90.4 · V9.A post-run advisor surface props · optional ·
   *  parent (WorkbenchShellV3) supplies these when a completed run is
   *  available (V7.D handoff). When missing, V9.A renders empty-state. */
  postRunRunId?: string | null;
  postRunMatches?: MatchedCommentary[];
  postRunRulesetVersion?: string;
}

type AdvisorMode = "review" | "diagnose";

interface ClassifiedFailure {
  kind: "offline" | "error";
  detail: string;
}

function classifyFailure(exc: unknown): ClassifiedFailure {
  if (exc instanceof ApiError) {
    if (exc.status >= 500 || exc.status === 408) {
      return { kind: "offline", detail: `${exc.status}: ${exc.message}` };
    }
    return { kind: "error", detail: `${exc.status}: ${exc.message}` };
  }
  if (exc instanceof TypeError) {
    return { kind: "offline", detail: exc.message };
  }
  return {
    kind: "error",
    detail: exc instanceof Error ? exc.message : String(exc),
  };
}

function CitationChip({ chunk }: { chunk: CitedChunk }) {
  const [open, setOpen] = useState(false);
  const sha8 = chunk.sha.slice(0, 8);
  const anchor = chunk.section_anchor ? `#${chunk.section_anchor}` : "";
  return (
    <div className="mt-2">
      <button
        type="button"
        data-testid="advisor-citation-chip"
        onClick={() => setOpen((v) => !v)}
        className="text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary hover:text-v3-textSecondary border border-v3-border rounded px-1.5 py-0.5 font-mono"
      >
        {chunk.path}
        {anchor} · {sha8}
      </button>
      {open && (
        <pre className="mt-2 text-[11px] text-v3-textSecondary bg-v3-surface1 border border-v3-border rounded p-2 whitespace-pre-wrap break-words font-mono leading-relaxed">
          {chunk.text}
        </pre>
      )}
    </div>
  );
}

function SeverityDot({ severity }: { severity: ReviewFinding["severity"] }) {
  const color =
    severity === "critical"
      ? "bg-v3-wall"
      : severity === "warning"
      ? "bg-v3-symmetry"
      : "bg-v3-textTertiary";
  return (
    <span
      aria-hidden
      className={`inline-block w-1.5 h-1.5 rounded-full ${color} mr-2 align-middle`}
    />
  );
}

function FindingCard({ finding }: { finding: ReviewFinding }) {
  return (
    <div
      data-testid="advisor-finding"
      data-severity={finding.severity}
      className="border border-v3-border rounded-md px-3 py-2.5 mb-2.5"
    >
      <div className="flex items-center text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-1.5">
        <SeverityDot severity={finding.severity} />
        <span>{finding.severity}</span>
        <span className="mx-1.5 text-v3-textTertiary/50">·</span>
        <span>{finding.area}</span>
        <span className="mx-1.5 text-v3-textTertiary/50">·</span>
        <span>{finding.source === "llm" ? "llm" : "rule-based"}</span>
      </div>
      <p className="text-[13px] text-v3-textPrimary leading-relaxed">
        {finding.message}
      </p>
      {finding.recommended_change && (
        <p
          data-testid="advisor-recommendation"
          className="mt-2 text-[12.5px] text-v3-textSecondary leading-relaxed border-l-2 border-v3-accent/40 pl-2.5"
        >
          {finding.recommended_change}
        </p>
      )}
      <CitationChip chunk={finding.citation} />
    </div>
  );
}

function HypothesisCard({ hypothesis }: { hypothesis: DiagnosisHypothesis }) {
  return (
    <div
      data-testid="advisor-hypothesis"
      data-likelihood={hypothesis.likelihood}
      className="border border-v3-border rounded-md px-3 py-2.5 mb-2.5"
    >
      <div className="flex items-center text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-1.5">
        <span>{hypothesis.failure_mode.replace(/_/g, " ")}</span>
        <span className="mx-1.5 text-v3-textTertiary/50">·</span>
        <span>likelihood {hypothesis.likelihood}</span>
        <span className="mx-1.5 text-v3-textTertiary/50">·</span>
        <span>{hypothesis.source === "llm" ? "llm" : "rule-based"}</span>
      </div>
      <p className="text-[13px] text-v3-textPrimary leading-relaxed">
        {hypothesis.summary}
      </p>
      {Object.keys(hypothesis.evidence).length > 0 && (
        <dl className="mt-2 text-[12px] text-v3-textSecondary space-y-1">
          {Object.entries(hypothesis.evidence).map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between gap-3">
              <dt className="text-v3-textTertiary">{k}</dt>
              <dd className="font-mono text-right text-v3-textPrimary truncate max-w-[60%]">
                {v}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {hypothesis.suggested_fix && (
        <p
          data-testid="advisor-suggested-fix"
          className="mt-2 text-[12.5px] text-v3-textSecondary leading-relaxed border-l-2 border-v3-accent/40 pl-2.5"
        >
          {hypothesis.suggested_fix}
        </p>
      )}
      <CitationChip chunk={hypothesis.citation} />
    </div>
  );
}

function AdvisoryBadge() {
  return (
    <div
      data-testid="advisor-advisory-badge"
      className="text-[10px] uppercase tracking-[0.10em] text-v3-textTertiary border border-v3-border rounded px-2 py-0.5 inline-block"
    >
      advisory only · no mutation
    </div>
  );
}

function useCaseList() {
  return useQuery<CaseIndexEntry[]>({
    queryKey: ["v3-case-list"],
    queryFn: () => api.listCases(),
    staleTime: 30_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function AdvisorContent({
  caseId,
  stepId,
  failmodeActive = false,
  postRunRunId = null,
  postRunMatches = [],
  postRunRulesetVersion = "v9.1.0",
}: AdvisorContentProps) {
  const [mode, setMode] = useState<AdvisorMode>("review");
  // V73.1 · pre-flight check · is this a whitelist (gold-reference) case?
  // The advisor backend only accepts imported_user cases (its case_dir
  // resolver lives under user_drafts/imported). Whitelist cases would 404
  // with a raw error — V73 explains the architecture instead.
  const { data: cases, isLoading: casesLoading } = useCaseList();
  const thisCase = Array.isArray(cases)
    ? cases.find((c) => c.case_id === caseId)
    : undefined;
  const isWhitelist = thisCase?.case_kind === "whitelist";
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [diagnose, setDiagnose] = useState<DiagnoseResponse | null>(null);
  const [loading, setLoading] = useState<AdvisorMode | null>(null);
  const [failure, setFailure] = useState<ClassifiedFailure | null>(null);

  const runReview = useCallback(async () => {
    if (!caseId) return;
    setLoading("review");
    setFailure(null);
    setMode("review");
    try {
      const resp = await api.getAIReview(caseId);
      setReview(resp);
    } catch (exc) {
      setFailure(classifyFailure(exc));
    } finally {
      setLoading(null);
    }
  }, [caseId]);

  const runDiagnose = useCallback(async () => {
    if (!caseId) return;
    setLoading("diagnose");
    setFailure(null);
    setMode("diagnose");
    try {
      const resp = await api.getAIDiagnose(caseId);
      setDiagnose(resp);
    } catch (exc) {
      setFailure(classifyFailure(exc));
    } finally {
      setLoading(null);
    }
  }, [caseId]);

  if (!caseId) {
    return (
      <div className="text-[13px] text-v3-textSecondary">
        <AdvisoryBadge />
        <p className="mt-4 leading-relaxed">
          Select a case from the left panel to consult the advisor.
        </p>
        <p className="mt-2 text-[12px] text-v3-textTertiary">
          The advisor reads case files + corpus citations and emits text
          recommendations. It never modifies the case.
        </p>
      </div>
    );
  }

  // V75.2 · skeleton while the pre-flight case-kind classification is in flight
  if (casesLoading) {
    return (
      <div className="text-[13px]">
        <AdvisoryBadge />
        <div className="mt-4">
          <SkeletonAdvisor />
        </div>
      </div>
    );
  }

  // V73.1 · whitelist case → advisor architecture explanation, not raw 404.
  // This is what the user would see on lid_driven_cavity / naca0012 / etc.
  if (isWhitelist) {
    return (
      <div className="text-[13px] text-v3-textSecondary">
        <AdvisoryBadge />
        <div
          data-testid="advisor-whitelist-explanation"
          className="mt-4 border border-v3-border rounded-md px-3 py-3 motion-safe:transition-colors"
        >
          <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
            advisor scope · this case is a whitelist gold-standard
          </div>
          <p className="text-v3-textPrimary leading-relaxed mb-3">
            AI Advisor reviews <em>user-imported</em> cases against the
            corpus. <span className="font-mono text-v3-textPrimary">{caseId}</span>{" "}
            is a whitelist gold-reference case — its validation is already
            attested.
          </p>
          <p className="text-[12px] text-v3-textTertiary leading-relaxed">
            For its existing trust verdict + provenance chain, see the{" "}
            <strong className="text-v3-textPrimary">TruthChain</strong> tab.
            To consult the advisor on a real case, import one from{" "}
            <strong className="text-v3-textPrimary">+ new case</strong>.
          </p>
        </div>
        <p
          data-testid="advisor-architecture-note"
          className="mt-3 text-[11px] text-v3-textTertiary leading-relaxed"
        >
          Why this gate exists: advisor reads case files under{" "}
          <span className="font-mono">user_drafts/imported/</span>; whitelist
          cases live at a different path. The pre-flight prevents a confusing
          404 from the backend.
        </p>

        {/* V80.3 · depth commentary still surfaces for whitelist cases ·
            it's the canonical demo target (lid_driven_cavity), so the curated
            mesh/convergence/result narrative is the point of the Advisor tab
            here even without a live consult call. */}
        <AdvisorCommentaryV4 caseId={caseId} stepId={stepId} />

        {/* V83.3 · V5.B failure-mode showcase available in whitelist branch
            too · ?failmode=1 opt-in */}
        <FailureModeShowcaseV5 active={failmodeActive} />

        {/* V90.4 · V9.A post-run advisor surface · pure presentational ·
            human-curated rule matching · NO LLM call · empty-state graceful */}
        <PostRunAdvisorV9
          caseId={caseId}
          runId={postRunRunId}
          matches={postRunMatches}
          rulesetVersion={postRunRulesetVersion}
        />
      </div>
    );
  }

  const active =
    mode === "review"
      ? review
      : diagnose;
  const findings =
    mode === "review" && review ? review.findings : [];
  const hypotheses =
    mode === "diagnose" && diagnose ? diagnose.hypotheses : [];
  const degradationNote =
    active?.llm_available === false ? active.degradation_note : null;

  return (
    <div className="text-[13px]">
      <AdvisoryBadge />

      {/* V80.3 · depth commentary · 3 curated cards · advisory only */}
      <AdvisorCommentaryV4 caseId={caseId} stepId={stepId} />

      {/* V83.3 · V5.B · failure-mode showcase · ?failmode=1 opt-in */}
      <FailureModeShowcaseV5 active={failmodeActive} />

      <div
        data-testid="advisor-mode-tabs"
        className="mt-4 flex items-center text-[12px] border-b border-v3-border pb-2"
      >
        <button
          type="button"
          data-testid="advisor-mode-review"
          data-active={mode === "review" ? "true" : "false"}
          onClick={() => setMode("review")}
          className={`mr-4 ${
            mode === "review"
              ? "text-v3-textPrimary"
              : "text-v3-textSecondary hover:text-v3-textPrimary"
          }`}
        >
          AI 审查
        </button>
        <button
          type="button"
          data-testid="advisor-mode-diagnose"
          data-active={mode === "diagnose" ? "true" : "false"}
          onClick={() => setMode("diagnose")}
          className={
            mode === "diagnose"
              ? "text-v3-textPrimary"
              : "text-v3-textSecondary hover:text-v3-textPrimary"
          }
        >
          AI 诊断
        </button>
      </div>

      <div className="mt-4 flex items-center gap-2 text-[12px]">
        {mode === "review" ? (
          <button
            type="button"
            data-testid="advisor-run-review"
            onClick={runReview}
            disabled={loading !== null}
            className="border border-v3-border hover:border-v3-borderActive text-v3-textPrimary px-3 py-1 rounded disabled:opacity-50"
          >
            {loading === "review" ? "consulting…" : "consult advisor"}
          </button>
        ) : (
          <button
            type="button"
            data-testid="advisor-run-diagnose"
            onClick={runDiagnose}
            disabled={loading !== null}
            className="border border-v3-border hover:border-v3-borderActive text-v3-textPrimary px-3 py-1 rounded disabled:opacity-50"
          >
            {loading === "diagnose" ? "diagnosing…" : "diagnose run"}
          </button>
        )}
        <span className="text-[11px] text-v3-textTertiary">
          step {stepId} · GET only · no mutation
        </span>
      </div>

      {failure && (
        <div
          data-testid={
            failure.kind === "offline"
              ? "advisor-offline-banner"
              : "advisor-error"
          }
          className={`mt-4 text-[12px] px-3 py-2 rounded border ${
            failure.kind === "offline"
              ? "border-v3-border text-v3-textSecondary"
              : "border-v3-wall/60 text-v3-wall"
          }`}
        >
          {failure.kind === "offline"
            ? "Advisor offline — workbench still safe. The corpus + rule-based path remains available; re-try later."
            : `Error · ${failure.detail}`}
        </div>
      )}

      {degradationNote && (
        <div
          data-testid="advisor-degradation-note"
          className="mt-4 text-[12px] px-3 py-2 rounded border border-v3-border text-v3-textSecondary"
        >
          {degradationNote}
        </div>
      )}

      {mode === "review" && review && (
        <div data-testid="advisor-review-findings" className="mt-4">
          <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
            {findings.length === 0
              ? "no findings · case is consistent w/ corpus"
              : `${findings.length} finding${findings.length === 1 ? "" : "s"}`}
          </div>
          {findings.map((f, i) => (
            <FindingCard key={i} finding={f} />
          ))}
          <div className="text-[10px] text-v3-textTertiary mt-2 font-mono">
            corpus_sha {review.corpus_sha.slice(0, 12)}
          </div>
        </div>
      )}

      {mode === "diagnose" && diagnose && (
        <div data-testid="advisor-diagnose-hypotheses" className="mt-4">
          <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
            {hypotheses.length === 0
              ? "no failure modes detected"
              : `${hypotheses.length} hypotheses · ranked`}
          </div>
          {hypotheses.map((h, i) => (
            <HypothesisCard key={i} hypothesis={h} />
          ))}
          <div className="text-[10px] text-v3-textTertiary mt-2 font-mono">
            corpus_sha {diagnose.corpus_sha.slice(0, 12)}
          </div>
        </div>
      )}

      {!review && !diagnose && !failure && (
        <p className="mt-4 text-[12px] text-v3-textTertiary leading-relaxed">
          {mode === "review"
            ? "AI 审查 reads case YAML + dict + corpus and lists findings ranked by severity. Each finding carries a corpus citation you can verify."
            : "AI 诊断 reads the most recent run residuals + log and lists failure-mode hypotheses ranked by likelihood. Each hypothesis carries a corpus citation."}
        </p>
      )}

      {/* V90.4 · V9.A post-run advisor surface · pure presentational ·
          human-curated rule matching · NO LLM call · empty-state graceful */}
      <PostRunAdvisorV9
        caseId={caseId}
        runId={postRunRunId}
        matches={postRunMatches}
        rulesetVersion={postRunRulesetVersion}
      />
    </div>
  );
}

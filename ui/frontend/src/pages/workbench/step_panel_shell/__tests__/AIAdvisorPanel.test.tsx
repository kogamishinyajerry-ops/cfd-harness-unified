// DEC-V61-160 (N6.4) · AIAdvisorPanel component tests.
//
// Covers:
//   * Initial render: two buttons, advisory-only badge, no result blocks
//   * Review fetch: button click → API call → findings rendered with
//     citation chip + copy button (no apply button)
//   * Diagnose fetch: same shape with hypotheses
//   * Degradation banner: llm_available=false surfaces note
//   * Citation chip expand: click reveals full chunk text
//   * Hard contract: NO apply / submit / execute buttons exist
//     anywhere in the rendered tree (V130/V132 invariant)

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AIAdvisorPanel } from "../AIAdvisorPanel";
import type {
  DiagnoseResponse,
  ReviewResponse,
} from "@/types/ai_advisor";

const CASE_ID = "imported_2026-05-07T00-00-00Z_abcd";

const REVIEW_FIXTURE: ReviewResponse = {
  case_id: CASE_ID,
  llm_available: true,
  corpus_sha: "a".repeat(64),
  degradation_note: null,
  generated_at: "2026-05-07T12:00:00Z",
  findings: [
    {
      severity: "warning",
      area: "mesh",
      message: "Check non-orthogonality near elbow.",
      recommended_change: "Reduce snappy refinement by 1.",
      source: "llm",
      citation: {
        chunk_id: "docs/openfoam_corpus/mesh.md:0:abc1234567890",
        source: "openfoam_corpus",
        path: "docs/openfoam_corpus/mesh.md",
        sha: "b".repeat(64),
        section_anchor: "Mesh quality",
        byte_offset: 0,
        text: "Full chunk content here that expands when chip is clicked.",
      },
    },
  ],
};

const REVIEW_OFFLINE_FIXTURE: ReviewResponse = {
  ...REVIEW_FIXTURE,
  llm_available: false,
  degradation_note: "DEEPSEEK_API_KEY unset — rule-based subset.",
  findings: [
    {
      ...REVIEW_FIXTURE.findings[0],
      source: "rule_based",
      recommended_change: null,
    },
  ],
};

const DIAGNOSE_FIXTURE: DiagnoseResponse = {
  case_id: CASE_ID,
  problem_hint: null,
  llm_available: true,
  corpus_sha: "c".repeat(64),
  degradation_note: null,
  generated_at: "2026-05-07T12:00:00Z",
  hypotheses: [
    {
      failure_mode: "stalled_residuals",
      likelihood: "high",
      summary: "Residuals plateau at iter 200.",
      evidence: { plateau_at: "200", last_residuals: "1e-3,1e-3,1e-3" },
      citation: {
        chunk_id: "docs/openfoam_corpus/residuals.md:0:def4567890123",
        source: "openfoam_corpus",
        path: "docs/openfoam_corpus/residuals.md",
        sha: "d".repeat(64),
        section_anchor: "Residual diagnostics",
        byte_offset: 0,
        text: "Stalled residuals indicate physics setup issues.",
      },
      suggested_fix: "Tighten pressure URF from 0.3 to 0.2.",
      source: "llm",
    },
  ],
};

let reviewResponse: ReviewResponse = REVIEW_FIXTURE;
let diagnoseResponse: DiagnoseResponse = DIAGNOSE_FIXTURE;
let failNext = false;

beforeEach(() => {
  reviewResponse = REVIEW_FIXTURE;
  diagnoseResponse = DIAGNOSE_FIXTURE;
  failNext = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      const url = typeof input === "string" ? input : input.toString();
      if (failNext) {
        return new Response("upstream timeout", { status: 502 });
      }
      if (url.includes("/ai-review")) {
        return new Response(JSON.stringify(reviewResponse), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.includes("/ai-diagnose")) {
        return new Response(JSON.stringify(diagnoseResponse), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response("{}", { status: 200 });
    }),
  );
});

describe("AIAdvisorPanel · initial render", () => {
  it("renders two advisor buttons + advisory-only badge", () => {
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    expect(screen.getByTestId("ai-advisor-review-button")).toBeInTheDocument();
    expect(
      screen.getByTestId("ai-advisor-diagnose-button"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("ai-advisor-advisory-badge"),
    ).toBeInTheDocument();
  });

  it("does NOT render any apply/submit/execute button by default", () => {
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    // Hard V130 invariant: no actionable mutating control should
    // exist in the advisor panel.
    expect(screen.queryByRole("button", { name: /apply/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /submit/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /execute/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /应用/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /提交/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /执行/ })).toBeNull();
  });
});

describe("AIAdvisorPanel · AI 审查 flow", () => {
  it("fetches review and renders findings with citation chip", async () => {
    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);

    await user.click(screen.getByTestId("ai-advisor-review-button"));

    const finding = await screen.findByTestId("ai-advisor-finding");
    expect(finding).toHaveAttribute("data-severity", "warning");
    expect(finding).toHaveAttribute("data-area", "mesh");
    expect(finding).toHaveAttribute("data-source", "llm");
    expect(
      within(finding).getByText(/Check non-orthogonality/),
    ).toBeInTheDocument();
    expect(
      within(finding).getByTestId("ai-advisor-citation-chip"),
    ).toBeInTheDocument();
  });

  it("renders the recommended_change as text + copy button (no apply)", async () => {
    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    await user.click(screen.getByTestId("ai-advisor-review-button"));

    const finding = await screen.findByTestId("ai-advisor-finding");
    expect(
      within(finding).getByText(/Reduce snappy refinement/),
    ).toBeInTheDocument();
    expect(
      within(finding).getByTestId("copy-recommended_change"),
    ).toBeInTheDocument();
    // Hard invariant: no apply button on the recommended change.
    expect(
      within(finding).queryByRole("button", { name: /apply/i }),
    ).toBeNull();
  });

  it("expands the citation chip to show the cited chunk text", async () => {
    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    await user.click(screen.getByTestId("ai-advisor-review-button"));

    const chip = await screen.findByTestId("ai-advisor-citation-chip");
    expect(
      screen.queryByTestId("ai-advisor-citation-text"),
    ).toBeNull();
    await user.click(chip);
    expect(
      screen.getByTestId("ai-advisor-citation-text"),
    ).toBeInTheDocument();
  });

  it("surfaces degradation banner when llm_available=false", async () => {
    reviewResponse = REVIEW_OFFLINE_FIXTURE;
    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    await user.click(screen.getByTestId("ai-advisor-review-button"));

    expect(
      await screen.findByTestId("ai-advisor-degradation-banner"),
    ).toBeInTheDocument();
    const banner = screen.getByTestId("ai-advisor-degradation-banner");
    // Header + note both reference "rule-based"; we just verify
    // the note mentions DEEPSEEK_API_KEY (the engineer-actionable
    // diagnostic).
    expect(
      within(banner).getByText(/DEEPSEEK_API_KEY/),
    ).toBeInTheDocument();
  });

  it("renders error banner on API failure", async () => {
    failNext = true;
    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    await user.click(screen.getByTestId("ai-advisor-review-button"));

    expect(
      await screen.findByTestId("ai-advisor-error"),
    ).toBeInTheDocument();
  });

  it("renders empty-state message when findings list is empty", async () => {
    reviewResponse = { ...REVIEW_FIXTURE, findings: [] };
    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    await user.click(screen.getByTestId("ai-advisor-review-button"));

    expect(
      await screen.findByText(/No findings emitted/i),
    ).toBeInTheDocument();
  });
});

describe("AIAdvisorPanel · AI 诊断 flow", () => {
  it("fetches diagnose and renders hypotheses with evidence", async () => {
    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    await user.click(screen.getByTestId("ai-advisor-diagnose-button"));

    const hyp = await screen.findByTestId("ai-advisor-hypothesis");
    expect(hyp).toHaveAttribute("data-failure-mode", "stalled_residuals");
    expect(hyp).toHaveAttribute("data-likelihood", "high");
    expect(within(hyp).getByText(/Residuals plateau/)).toBeInTheDocument();
    expect(within(hyp).getByText(/plateau_at:/)).toBeInTheDocument();
    expect(
      within(hyp).getByText(/Tighten pressure URF/),
    ).toBeInTheDocument();
  });

  it("does NOT render apply controls on suggested_fix", async () => {
    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    await user.click(screen.getByTestId("ai-advisor-diagnose-button"));

    const hyp = await screen.findByTestId("ai-advisor-hypothesis");
    expect(within(hyp).getByTestId("copy-suggested_fix")).toBeInTheDocument();
    expect(
      within(hyp).queryByRole("button", { name: /apply/i }),
    ).toBeNull();
    expect(
      within(hyp).queryByRole("button", { name: /submit/i }),
    ).toBeNull();
  });
});

describe("AIAdvisorPanel · API contract", () => {
  it("calls GET /api/cases/{id}/ai-review on review click", async () => {
    const fetchSpy = vi.fn(async () => {
      return new Response(JSON.stringify(REVIEW_FIXTURE), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchSpy);

    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    await user.click(screen.getByTestId("ai-advisor-review-button"));

    await screen.findByTestId("ai-advisor-finding");

    const calls = (fetchSpy as unknown as {
      mock: { calls: Array<[RequestInfo, RequestInit?]> };
    }).mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    const url = calls[0][0] as string;
    expect(url).toContain(`/api/cases/${CASE_ID}/ai-review`);
    // Method must be GET (or default which is GET) — never POST/PUT.
    const init = calls[0][1] as RequestInit | undefined;
    const method = init?.method ?? "GET";
    expect(method.toUpperCase()).toBe("GET");
  });

  it("calls GET /api/cases/{id}/ai-diagnose on diagnose click", async () => {
    const fetchSpy = vi.fn(async () => {
      return new Response(JSON.stringify(DIAGNOSE_FIXTURE), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchSpy);

    const user = userEvent.setup();
    render(<AIAdvisorPanel caseId={CASE_ID} />);
    await user.click(screen.getByTestId("ai-advisor-diagnose-button"));

    await screen.findByTestId("ai-advisor-hypothesis");

    const calls = (fetchSpy as unknown as {
      mock: { calls: Array<[RequestInfo, RequestInit?]> };
    }).mock.calls;
    const url = calls[0][0] as string;
    expect(url).toContain(`/api/cases/${CASE_ID}/ai-diagnose`);
    const init = calls[0][1] as RequestInit | undefined;
    const method = init?.method ?? "GET";
    expect(method.toUpperCase()).toBe("GET");
  });
});

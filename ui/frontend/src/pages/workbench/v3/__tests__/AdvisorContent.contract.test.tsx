/**
 * V71.4 · V71.O · AdvisorContent V130/V132 contract regression test
 *
 * Hard contract assertion: the v3 Advisor surface is GET-only · advisory-only ·
 * NEVER mutates case state. This test exhaustively scans the rendered DOM
 * after consult() + diagnose() to assert that no mutating UI affordance
 * exists in any state (idle / loading / success-review / success-diagnose /
 * offline / error).
 *
 * Reverse-stop: if any check fails, V71 is in violation of V130/V132 invariants
 * and the offending commit MUST revert.
 */
import type { ReactElement } from "react";
import { describe, expect, it, beforeEach, vi } from "vitest";
import { render as rtlRender, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AdvisorContent } from "../components/right-panel/AdvisorContent";
import type {
  DiagnoseResponse,
  ReviewResponse,
} from "@/types/ai_advisor";

const CASE_ID = "lid_driven_cavity";

// V73.1 · contract tests target the advisor execution path (imported_user
// case). Whitelist cases hit the V73.1 pre-flight explanation branch — that
// path has its own dedicated test below. Mock /api/cases accordingly so the
// pre-flight passes through to the advisor consult UI.
const CASES_IMPORTED = [
  {
    case_id: CASE_ID,
    name: CASE_ID,
    case_kind: "imported_user" as const,
    physics: "incompressible",
    difficulty: "novice",
    solver: "icoFoam",
    tags: [],
    available_demo_dirs: [],
  },
];

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const REVIEW: ReviewResponse = {
  case_id: CASE_ID,
  llm_available: true,
  corpus_sha: "a".repeat(64),
  degradation_note: null,
  generated_at: "2026-05-16T12:00:00Z",
  findings: [
    {
      severity: "warning",
      area: "mesh",
      message: "Aspect ratio is high near elbow.",
      recommended_change: "Reduce snappy refinement by 1.",
      source: "llm",
      citation: {
        chunk_id: "chunk:1",
        source: "openfoam_corpus",
        path: "docs/openfoam_corpus/mesh.md",
        sha: "b".repeat(64),
        section_anchor: "Mesh quality",
        byte_offset: 0,
        text: "Full corpus chunk text · expanded inline on citation chip click.",
      },
    },
  ],
};

const DIAGNOSE: DiagnoseResponse = {
  case_id: CASE_ID,
  problem_hint: "stalled_residuals",
  llm_available: true,
  corpus_sha: "c".repeat(64),
  degradation_note: null,
  generated_at: "2026-05-16T12:01:00Z",
  hypotheses: [
    {
      failure_mode: "stalled_residuals",
      likelihood: "high",
      summary: "Pressure residual oscillation suggests under-relaxation drift.",
      evidence: { iter: "132", p_residual: "5.1e-3" },
      citation: {
        chunk_id: "chunk:2",
        source: "openfoam_corpus",
        path: "docs/openfoam_corpus/residuals.md",
        sha: "d".repeat(64),
        section_anchor: "Residual diagnostics",
        byte_offset: 0,
        text: "Stalled residuals indicate physics setup issues.",
      },
      suggested_fix: "Tighten p URF from 0.3 to 0.2 (manual change).",
      source: "llm",
    },
  ],
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/api/cases")) {
        return new Response(JSON.stringify(CASES_IMPORTED), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.includes("/ai-review")) {
        return new Response(JSON.stringify(REVIEW), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.includes("/ai-diagnose")) {
        return new Response(JSON.stringify(DIAGNOSE), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response("{}", { status: 200 });
    }),
  );
});

// Build a comprehensive list of regex patterns for mutating button names.
// V130/V132 contract: NONE of these may match any button in the DOM at any
// point in the Advisor lifecycle.
const FORBIDDEN_BUTTON_PATTERNS = [
  /apply/i,
  /submit/i,
  /execute/i,
  /auto-fix/i,
  /^run$/i, // "consult advisor" + "diagnose run" are OK · plain "run" is not
  /应用/,
  /提交/,
  /执行/,
  /自动修复/,
  /^运行$/,
];

function assertNoForbiddenButtons(label: string) {
  for (const pattern of FORBIDDEN_BUTTON_PATTERNS) {
    const found = screen.queryByRole("button", { name: pattern });
    expect(
      found,
      `[${label}] V130/V132 violation: button matching ${pattern} exists`,
    ).toBeNull();
  }
}

function assertNoForbiddenFormControls(label: string) {
  // No <input>, <textarea>, or <select> elements should exist in advisor
  // beyond what's needed for the read-only citation chip expand toggle
  // (which is a <button>, not a form control).
  const inputs = document.querySelectorAll(
    "[data-testid^='advisor-'] input, [data-testid^='advisor-'] textarea, [data-testid^='advisor-'] select",
  );
  expect(
    inputs.length,
    `[${label}] V130 violation: form controls exist in advisor surface`,
  ).toBe(0);
}

describe("V71.O · AdvisorContent V130/V132 contract", () => {
  it("idle state · no mutating buttons or form controls", () => {
    render(<AdvisorContent caseId={CASE_ID} stepId={1} />);
    expect(
      screen.getByTestId("advisor-advisory-badge"),
    ).toBeInTheDocument();
    assertNoForbiddenButtons("idle");
    assertNoForbiddenFormControls("idle");
  });

  it("after consult review · zero mutating affordance on rendered findings", async () => {
    const user = userEvent.setup();
    render(<AdvisorContent caseId={CASE_ID} stepId={3} />);
    await user.click(screen.getByTestId("advisor-run-review"));
    await waitFor(() =>
      expect(
        screen.getByTestId("advisor-review-findings"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("advisor-finding")).toBeInTheDocument();
    expect(
      screen.getByTestId("advisor-recommendation"),
    ).toBeInTheDocument();
    assertNoForbiddenButtons("after review");
    assertNoForbiddenFormControls("after review");
  });

  it("after diagnose · suggested_fix rendered as text · no fix button", async () => {
    const user = userEvent.setup();
    render(<AdvisorContent caseId={CASE_ID} stepId={4} />);
    await user.click(screen.getByTestId("advisor-mode-diagnose"));
    await user.click(screen.getByTestId("advisor-run-diagnose"));
    await waitFor(() =>
      expect(
        screen.getByTestId("advisor-diagnose-hypotheses"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("advisor-hypothesis"),
    ).toBeInTheDocument();
    // Suggested fix renders inside hypothesis card as <p> text, not button
    const fix = screen.getByTestId("advisor-suggested-fix");
    expect(fix.tagName).toBe("P");
    assertNoForbiddenButtons("after diagnose");
    assertNoForbiddenFormControls("after diagnose");
  });

  it("citation chip click expands corpus chunk text inline", async () => {
    const user = userEvent.setup();
    render(<AdvisorContent caseId={CASE_ID} stepId={3} />);
    await user.click(screen.getByTestId("advisor-run-review"));
    await waitFor(() =>
      expect(
        screen.getByTestId("advisor-review-findings"),
      ).toBeInTheDocument(),
    );
    const chip = screen.getByTestId("advisor-citation-chip");
    await user.click(chip);
    // The expanded <pre> appears with corpus text
    expect(
      screen.getByText(/Full corpus chunk text/),
    ).toBeInTheDocument();
  });

  it("llm_available=false renders calm offline banner · not red error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("upstream offline", { status: 503 })),
    );
    const user = userEvent.setup();
    render(<AdvisorContent caseId={CASE_ID} stepId={4} />);
    await user.click(screen.getByTestId("advisor-run-review"));
    await waitFor(() =>
      expect(
        screen.getByTestId("advisor-offline-banner"),
      ).toBeInTheDocument(),
    );
    // Calm tone · not "Error · 503"
    expect(
      screen.queryByText(/Error · 503/),
    ).toBeNull();
    assertNoForbiddenButtons("offline");
  });

  it("4xx client error renders harsh error · still no mutating buttons", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("bad case id", { status: 400 })),
    );
    const user = userEvent.setup();
    render(<AdvisorContent caseId={CASE_ID} stepId={4} />);
    await user.click(screen.getByTestId("advisor-run-review"));
    await waitFor(() =>
      expect(
        screen.getByTestId("advisor-error"),
      ).toBeInTheDocument(),
    );
    assertNoForbiddenButtons("error");
    assertNoForbiddenFormControls("error");
  });

  // V73.1 · whitelist pre-flight surface
  it("whitelist case · renders advisor-scope explanation instead of 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        const url = typeof input === "string" ? input : input.toString();
        if (url.endsWith("/api/cases")) {
          return new Response(
            JSON.stringify([
              {
                ...CASES_IMPORTED[0],
                case_kind: "whitelist",
              },
            ]),
            { status: 200, headers: { "content-type": "application/json" } },
          );
        }
        // V73.1 contract: no consult fetch should fire for whitelist
        return new Response("would have 404'd", { status: 404 });
      }),
    );
    render(<AdvisorContent caseId={CASE_ID} stepId={3} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("advisor-whitelist-explanation"),
      ).toBeInTheDocument(),
    );
    // Calm tone · no harsh "Error · 404"
    expect(screen.queryByText(/Error · 404/)).toBeNull();
    // Architecture note explains the scope (V73.1 success criterion)
    expect(screen.getByText(/whitelist gold-reference case/)).toBeInTheDocument();
    // V130/V132 still hold on this surface
    assertNoForbiddenButtons("whitelist");
    assertNoForbiddenFormControls("whitelist");
  });
});

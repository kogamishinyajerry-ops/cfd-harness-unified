/**
 * V92-UI-V4 · AdvisorPillStack contract test
 *
 * Mirrors PostRunAdvisorV9.contract.test.tsx invariants, asserted against
 * the new industrial-minimalist pill UI. Same data contract
 * (MatchedCommentary[]) — only the presentation changed.
 *
 * Asserts:
 *   - V130: NO LLM endpoint imported (literal-source absence)
 *   - V130: lexical denylist · NO "AI generates" / "AI suggests" / "AI
 *     diagnoses" verbiage in rendered text
 *   - V130: structural · NO useEffect / fetch / useQuery in component code
 *     (component is pure-presentational; the fetch lives in the hook layer)
 *   - Empty-state graceful when no runId
 *   - Empty-state graceful when runId but zero matches
 *   - Renders one pill per match · each carries rule_id + severity dot
 *   - Progressive disclosure: collapsed by default, click toggles expanded
 *   - Severity → data attribute mapping (advise / warn / info)
 *   - data-attributes exposed for inspection (match-count · ruleset-version
 *     · run-id · loading)
 *   - Advisory microcopy present ("curated patterns" header)
 *
 * Pure render test · runs in <200ms.
 */
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { AdvisorPillStack } from "../components/AdvisorPillStack";
import type { MatchedCommentary } from "@/data/advisor_pattern_matcher";

const SAMPLE_MATCHES: MatchedCommentary[] = [
  {
    rule_id: "MAX_ITERS_REACHED_V9_R2",
    matched_at: "convergence_stats",
    commentary_excerpt:
      "Solver reached its iteration cap without meeting the convergence tolerance. The case is technically not finished.",
    provenance: ".planning/intel/v_series/V18_max_iters.md",
    severity: "advise",
  },
  {
    rule_id: "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4",
    matched_at: "gold_delta_8.20pct",
    commentary_excerpt:
      "Maximum absolute deviation from the gold-standard reference exceeds 5%.",
    provenance: ".planning/intel/v_series/V46_gold_delta_drift.md",
    severity: "warn",
  },
  {
    rule_id: "HEALTHY_CONVERGENCE_V9_R8",
    matched_at: "healthy_convergence_p",
    commentary_excerpt:
      "Pressure residual decreased monotonically over the last 8 iterations.",
    provenance: "Versteeg & Malalasekera · An Introduction to CFD · §11.3",
    severity: "info",
  },
];

function harness(props: {
  runId?: string | null;
  matches?: MatchedCommentary[];
  rulesetVersion?: string;
  isLoading?: boolean;
}) {
  return render(
    <AdvisorPillStack
      runId={"runId" in props ? props.runId! : "R-OK-1"}
      matches={props.matches ?? SAMPLE_MATCHES}
      rulesetVersion={props.rulesetVersion ?? "v9.0.0"}
      isLoading={props.isLoading ?? false}
    />,
  );
}

describe("V92-UI-V4 · AdvisorPillStack · V130 invariants", () => {
  it("source file does NOT import any LLM endpoint (carry-forward RS#31)", () => {
    const src = readFileSync(
      resolve(__dirname, "../components/AdvisorPillStack.tsx"),
      "utf-8",
    );
    const codeOnly = src
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/\/\/.*$/gm, "");
    expect(codeOnly).not.toMatch(/\/ai-review/);
    expect(codeOnly).not.toMatch(/\/ai-diagnose/);
    expect(codeOnly).not.toMatch(/streamAICoach/);
    expect(codeOnly).not.toMatch(/ai_advisor/);
    // pure presentational — no api client import either
    expect(codeOnly).not.toMatch(/from\s+["']@\/api\/client/);
  });

  it("lexical denylist · NO 'AI generates / suggests / diagnoses / recommends / advises' verbiage", () => {
    const { container } = harness({});
    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("ai generates");
    expect(text).not.toContain("ai suggests");
    expect(text).not.toContain("ai diagnoses");
    expect(text).not.toContain("ai recommends");
    expect(text).not.toContain("ai advises");
  });

  it("structural · NO useEffect / fetch / useQuery in component code (pure-presentational)", () => {
    const src = readFileSync(
      resolve(__dirname, "../components/AdvisorPillStack.tsx"),
      "utf-8",
    );
    const codeOnly = src
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/\/\/.*$/gm, "");
    expect(codeOnly).not.toMatch(/\buseEffect\b/);
    expect(codeOnly).not.toMatch(/\bfetch\(/);
    expect(codeOnly).not.toMatch(/\buseQuery\b/);
  });
});

describe("V92-UI-V4 · AdvisorPillStack · honest framing", () => {
  it("header surfaces curated-pattern framing (not 'AI suggestions')", () => {
    const { container } = harness({});
    const text = container.textContent ?? "";
    expect(text).toContain("诊断模式");
    expect(text).toContain("curated patterns");
  });

  it("ruleset version surfaces in header", () => {
    harness({ rulesetVersion: "v9.1.7" });
    const root = screen.getByTestId("v4-advisor-pill-stack");
    expect(root.getAttribute("data-ruleset-version")).toBe("v9.1.7");
  });
});

describe("V92-UI-V4 · AdvisorPillStack · empty-state graceful", () => {
  it("renders empty-state when runId is null", () => {
    harness({ runId: null, matches: [] });
    expect(
      screen.getByTestId("v4-advisor-pill-stack-empty-no-run"),
    ).toBeTruthy();
    expect(
      screen.queryByTestId("v4-advisor-pill-MAX_ITERS_REACHED_V9_R2"),
    ).toBeNull();
  });

  it("renders no-matches empty-state when runId present but matches empty", () => {
    harness({ runId: "R-clean", matches: [] });
    expect(
      screen.getByTestId("v4-advisor-pill-stack-empty-no-matches"),
    ).toBeTruthy();
  });

  it("renders loading indicator when isLoading", () => {
    harness({ runId: null, matches: [], isLoading: true });
    expect(
      screen.getByTestId("v4-advisor-pill-stack-loading"),
    ).toBeTruthy();
    // loading takes precedence over empty-state
    expect(
      screen.queryByTestId("v4-advisor-pill-stack-empty-no-run"),
    ).toBeNull();
  });

  it("does NOT show 'error' / 'failed' wording when empty", () => {
    const { container } = harness({ runId: null, matches: [] });
    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("error");
    expect(text).not.toContain("failed");
  });
});

describe("V92-UI-V4 · AdvisorPillStack · pill rendering", () => {
  it("renders one pill per match", () => {
    harness({});
    for (const m of SAMPLE_MATCHES) {
      expect(screen.getByTestId(`v4-advisor-pill-${m.rule_id}`)).toBeTruthy();
    }
  });

  it("each pill carries severity attribute matching the rule", () => {
    harness({});
    expect(
      screen
        .getByTestId(`v4-advisor-pill-MAX_ITERS_REACHED_V9_R2`)
        .getAttribute("data-severity"),
    ).toBe("advise");
    expect(
      screen
        .getByTestId(`v4-advisor-pill-GOLD_DELTA_EXCEEDS_5_PCT_V9_R4`)
        .getAttribute("data-severity"),
    ).toBe("warn");
    expect(
      screen
        .getByTestId(`v4-advisor-pill-HEALTHY_CONVERGENCE_V9_R8`)
        .getAttribute("data-severity"),
    ).toBe("info");
  });

  it("pills start collapsed (no expanded body visible)", () => {
    harness({});
    for (const m of SAMPLE_MATCHES) {
      expect(
        screen.queryByTestId(`v4-advisor-pill-${m.rule_id}-body`),
      ).toBeNull();
      const root = screen.getByTestId(`v4-advisor-pill-${m.rule_id}`);
      expect(root.getAttribute("data-expanded")).toBe("false");
    }
  });

  it("click toggle expands the pill body with full commentary + provenance + matched_at", () => {
    harness({});
    const target = SAMPLE_MATCHES[0];
    const toggle = screen.getByTestId(
      `v4-advisor-pill-${target.rule_id}-toggle`,
    );
    fireEvent.click(toggle);

    const root = screen.getByTestId(`v4-advisor-pill-${target.rule_id}`);
    expect(root.getAttribute("data-expanded")).toBe("true");

    const body = screen.getByTestId(
      `v4-advisor-pill-${target.rule_id}-body`,
    );
    expect(body.textContent).toContain(target.commentary_excerpt.slice(0, 40));
    expect(
      screen.getByTestId(`v4-advisor-pill-${target.rule_id}-matched-at`)
        .textContent,
    ).toContain(target.matched_at);
    expect(
      screen.getByTestId(`v4-advisor-pill-${target.rule_id}-provenance`)
        .textContent,
    ).toContain(target.provenance.slice(0, 30));
  });

  it("second click on the toggle collapses again", () => {
    harness({});
    const target = SAMPLE_MATCHES[0];
    const toggle = screen.getByTestId(
      `v4-advisor-pill-${target.rule_id}-toggle`,
    );
    fireEvent.click(toggle); // expand
    fireEvent.click(toggle); // collapse

    expect(
      screen.queryByTestId(`v4-advisor-pill-${target.rule_id}-body`),
    ).toBeNull();
    expect(
      screen
        .getByTestId(`v4-advisor-pill-${target.rule_id}`)
        .getAttribute("data-expanded"),
    ).toBe("false");
  });

  it("collapsed pill title is a single-line summary (≤ 50 chars + ellipsis if longer)", () => {
    harness({});
    const titleEl = screen.getByTestId(
      `v4-advisor-pill-MAX_ITERS_REACHED_V9_R2-title`,
    );
    const text = (titleEl.textContent ?? "").trim();
    expect(text.length).toBeLessThanOrEqual(50);
    // Original commentary first sentence ends with "."; either truncated or
    // ends with the sentence period or ellipsis.
    expect(
      text.endsWith(".") || text.endsWith("…") || text.endsWith("。"),
    ).toBe(true);
  });
});

describe("V92-UI-V4 · AdvisorPillStack · data-attribute inspection surface", () => {
  it("exposes data-match-count + data-ruleset-version + data-run-id on root", () => {
    harness({ runId: "R-XYZ", matches: SAMPLE_MATCHES, rulesetVersion: "v9.0.5" });
    const root = screen.getByTestId("v4-advisor-pill-stack");
    expect(root.getAttribute("data-match-count")).toBe(
      String(SAMPLE_MATCHES.length),
    );
    expect(root.getAttribute("data-ruleset-version")).toBe("v9.0.5");
    expect(root.getAttribute("data-run-id")).toBe("R-XYZ");
  });

  it("data-run-id falls back to __none__ when null", () => {
    harness({ runId: null, matches: [] });
    const root = screen.getByTestId("v4-advisor-pill-stack");
    expect(root.getAttribute("data-run-id")).toBe("__none__");
  });

  it("data-loading reflects isLoading prop", () => {
    harness({ isLoading: true });
    const root = screen.getByTestId("v4-advisor-pill-stack");
    expect(root.getAttribute("data-loading")).toBe("true");
  });
});

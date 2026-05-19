/**
 * V90.4 · V9.A PostRunAdvisorV9 contract test
 *
 * Asserts:
 *   - V130: NO LLM endpoint imported (literal-source absence)
 *   - V130: NO "AI generates" / "AI suggests" / "AI diagnoses" verbiage
 *     in rendered text (lexical denylist)
 *   - V130: NO useEffect that fires fetch (structural mount-time fetch-zero · purely presentational)
 *   - Empty-state graceful when no runId (reverse-stop #34)
 *   - Empty-state graceful when runId but zero matches
 *   - Matches render as cards · each card carries rule_id + severity +
 *     excerpt + matched_at + provenance
 *   - Severity chip class matches severity level
 *   - data-attributes exposed for inspection (match-count · ruleset-version)
 *
 * Pure render test · runs in <200ms.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { PostRunAdvisorV9 } from "../components/right-panel/PostRunAdvisorV9";
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
  caseId?: string | null;
  runId?: string | null;
  matches?: MatchedCommentary[];
  rulesetVersion?: string;
}) {
  return render(
    <PostRunAdvisorV9
      caseId={"caseId" in props ? props.caseId! : "lid_driven_cavity"}
      runId={"runId" in props ? props.runId! : "R-OK-1"}
      matches={props.matches ?? SAMPLE_MATCHES}
      rulesetVersion={props.rulesetVersion ?? "v9.0.0"}
    />,
  );
}

describe("V90.4 · PostRunAdvisorV9 · V130 invariants", () => {
  it("source file does NOT import any LLM endpoint (reverse-stop #31)", () => {
    const src = readFileSync(
      resolve(
        __dirname,
        "../components/right-panel/PostRunAdvisorV9.tsx",
      ),
      "utf-8",
    );
    // Strip JSDoc / line comments before grep · we check actual code
    // imports, not whether the docs reference these endpoints.
    const codeOnly = src
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/\/\/.*$/gm, "");
    expect(codeOnly).not.toMatch(/\/ai-review/);
    expect(codeOnly).not.toMatch(/\/ai-diagnose/);
    expect(codeOnly).not.toMatch(/streamAICoach/);
    expect(codeOnly).not.toMatch(/ai_advisor/);
    // The component should NOT import from api/client either (pure presentational)
    expect(codeOnly).not.toMatch(/from\s+["']@\/api\/client/);
  });

  it("V130 lexical denylist · NO 'AI generates' / 'AI suggests' / 'AI diagnoses' verbiage (reverse-stop #33)", () => {
    const { container } = harness({});
    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("ai generates");
    expect(text).not.toContain("ai suggests");
    expect(text).not.toContain("ai diagnoses");
    expect(text).not.toContain("ai recommends");
    expect(text).not.toContain("ai advises");
  });

  it("V130 structural · NO useEffect / no fetch / no useQuery in code (not just comments)", () => {
    const src = readFileSync(
      resolve(
        __dirname,
        "../components/right-panel/PostRunAdvisorV9.tsx",
      ),
      "utf-8",
    );
    // Strip JSDoc and line comments before checking — we want to know if
    // the actual CODE uses these hooks, not just whether docs mention them.
    const codeOnly = src
      .replace(/\/\*[\s\S]*?\*\//g, "") // block comments
      .replace(/\/\/.*$/gm, ""); // line comments
    // Pure presentational — no React hooks that fire fetch
    expect(codeOnly).not.toMatch(/\buseEffect\b/);
    expect(codeOnly).not.toMatch(/\bfetch\(/);
    expect(codeOnly).not.toMatch(/\buseQuery\b/);
  });
});

describe("V90.4 · PostRunAdvisorV9 · honest framing", () => {
  it("heading reads 'Curated diagnostic patterns' NOT 'AI suggestions'", () => {
    harness({});
    const heading = screen.getByTestId("post-run-advisor-v9-heading");
    expect(heading.textContent).toBe("Curated diagnostic patterns");
  });

  it("ruleset version surfaces in header", () => {
    harness({ rulesetVersion: "v9.1.7" });
    const version = screen.getByTestId("post-run-advisor-v9-ruleset-version");
    expect(version.textContent).toContain("v9.1.7");
  });
});

describe("V90.4 · PostRunAdvisorV9 · empty-state graceful (reverse-stop #34)", () => {
  it("renders empty-state when runId is null (no completed run yet)", () => {
    harness({ runId: null, matches: [] });
    expect(screen.getByTestId("post-run-advisor-v9-empty-no-run")).toBeTruthy();
    expect(
      screen.queryByTestId("post-run-advisor-v9-card-list"),
    ).toBeNull();
  });

  it("renders no-matches empty-state when runId present but matches empty", () => {
    harness({ runId: "R-clean", matches: [] });
    expect(
      screen.getByTestId("post-run-advisor-v9-empty-no-matches"),
    ).toBeTruthy();
    expect(
      screen.queryByTestId("post-run-advisor-v9-card-list"),
    ).toBeNull();
  });

  it("does NOT show error when no run or no matches", () => {
    const { container } = harness({ runId: null, matches: [] });
    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("error");
    expect(text).not.toContain("failed");
  });
});

describe("V90.4 · PostRunAdvisorV9 · card rendering", () => {
  it("renders one card per match", () => {
    harness({});
    for (const m of SAMPLE_MATCHES) {
      expect(
        screen.getByTestId(`post-run-advisor-v9-card-${m.rule_id}`),
      ).toBeTruthy();
    }
  });

  it("each card surfaces rule_id + severity + excerpt + matched_at + provenance", () => {
    harness({});
    const target = SAMPLE_MATCHES[0];
    expect(
      screen.getByTestId(`post-run-advisor-v9-card-${target.rule_id}-id`)
        .textContent,
    ).toBe(target.rule_id);
    expect(
      screen.getByTestId(
        `post-run-advisor-v9-card-${target.rule_id}-severity`,
      ).textContent,
    ).toBe(target.severity);
    expect(
      screen
        .getByTestId(
          `post-run-advisor-v9-card-${target.rule_id}-excerpt`,
        )
        .textContent?.includes(target.commentary_excerpt.slice(0, 40)),
    ).toBe(true);
    expect(
      screen
        .getByTestId(
          `post-run-advisor-v9-card-${target.rule_id}-matched-at`,
        )
        .textContent?.includes(target.matched_at),
    ).toBe(true);
    expect(
      screen
        .getByTestId(
          `post-run-advisor-v9-card-${target.rule_id}-provenance`,
        )
        .textContent?.includes(target.provenance.slice(0, 30)),
    ).toBe(true);
  });

  it("severity chip uses distinct visual treatment for advise / warn / info", () => {
    harness({});
    const advise = screen
      .getByTestId(`post-run-advisor-v9-card-MAX_ITERS_REACHED_V9_R2`)
      .getAttribute("data-severity");
    const warn = screen
      .getByTestId(`post-run-advisor-v9-card-GOLD_DELTA_EXCEEDS_5_PCT_V9_R4`)
      .getAttribute("data-severity");
    const info = screen
      .getByTestId(`post-run-advisor-v9-card-HEALTHY_CONVERGENCE_V9_R8`)
      .getAttribute("data-severity");
    expect(advise).toBe("advise");
    expect(warn).toBe("warn");
    expect(info).toBe("info");
  });
});

describe("V90.4 · PostRunAdvisorV9 · data-attribute inspection surface", () => {
  it("exposes data-match-count + data-ruleset-version + data-run-id on root", () => {
    harness({ runId: "R-XYZ", matches: SAMPLE_MATCHES, rulesetVersion: "v9.0.5" });
    const root = screen.getByTestId("post-run-advisor-v9");
    expect(root.getAttribute("data-match-count")).toBe(String(SAMPLE_MATCHES.length));
    expect(root.getAttribute("data-ruleset-version")).toBe("v9.0.5");
    expect(root.getAttribute("data-run-id")).toBe("R-XYZ");
  });

  it("exposes data-case-id (may be __none__ when null)", () => {
    harness({ caseId: null });
    const root = screen.getByTestId("post-run-advisor-v9");
    expect(root.getAttribute("data-case-id")).toBe("__none__");
  });
});

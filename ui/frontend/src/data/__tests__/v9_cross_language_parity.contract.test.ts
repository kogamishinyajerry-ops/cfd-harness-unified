/**
 * V91.2 RS#38 · Cross-language parity test (TS side)
 *
 * Loads the frozen fixture at `__fixtures__/v9_parity_fixtures.json` and
 * asserts the TS matcher produces byte-identical output. The Python test
 * `tests/test_v9_cross_language_parity.py` does the same on the Python
 * side. Both passing → cross-language parity proved.
 */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  matchAdvisorPatterns,
  type RunArtifactSlice,
  type MatchedCommentary,
} from "../advisor_pattern_matcher";
import { V9_ADVISOR_RULES } from "../v9_advisor_rules";

const FIXTURE_PATH = resolve(__dirname, "../__fixtures__/v9_parity_fixtures.json");

interface ParityFixture {
  name: string;
  slice: RunArtifactSlice;
  expected_matches: MatchedCommentary[];
}

interface ParityFixtureCorpus {
  version: string;
  fixtures: ParityFixture[];
}

function loadFixtures(): ParityFixtureCorpus {
  return JSON.parse(readFileSync(FIXTURE_PATH, "utf-8"));
}

describe("V91.2 RS#38 · cross-language parity · TS matcher vs frozen fixture", () => {
  const corpus = loadFixtures();

  for (const fx of corpus.fixtures) {
    it(`TS matcher reproduces fixture: ${fx.name}`, () => {
      const actual = matchAdvisorPatterns(fx.slice, V9_ADVISOR_RULES);
      expect(actual).toEqual(fx.expected_matches);
    });
  }

  it("fixture covers all V9 rule ids (every rule appears in ≥1 fixture)", () => {
    const matchedIds = new Set<string>();
    for (const fx of corpus.fixtures) {
      for (const m of fx.expected_matches) {
        matchedIds.add(m.rule_id);
      }
    }
    const ruleIds = new Set(V9_ADVISOR_RULES.map((r) => r.id));
    const missing = [...ruleIds].filter((id) => !matchedIds.has(id));
    expect(missing).toEqual([]);
  });
});

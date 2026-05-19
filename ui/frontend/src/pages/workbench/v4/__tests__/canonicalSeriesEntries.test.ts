/**
 * V4 R8 polish 1 · canonical legend order contract test.
 *
 * Closes Codex R7 polish-item #1 (frontend unit test for canonical
 * legend order). Pins the rule that drives chart-legend stability:
 *
 *   1. Keys in CANONICAL_ORDER come first, in declared order
 *      (Ux, Uy, Uz, p, k, omega, epsilon, T)
 *   2. Keys NOT in CANONICAL_ORDER come after, sorted alphabetically
 *   3. The set of returned entries equals the input set (no drops)
 *
 * The chart in ModeRendererPost depends on this so the user's eye
 * doesn't need to relearn series-color mapping across cases.
 */
import { describe, expect, it } from "vitest";

import {
  CANONICAL_ORDER,
  canonicalSeriesEntries,
} from "../components/modes/ModeRendererPost";

describe("canonicalSeriesEntries", () => {
  it("CANONICAL_ORDER matches the CFD convention (Ux, Uy, Uz, p, k, omega, epsilon, T)", () => {
    expect(CANONICAL_ORDER).toEqual([
      "Ux",
      "Uy",
      "Uz",
      "p",
      "k",
      "omega",
      "epsilon",
      "T",
    ]);
  });

  it("orders canonical keys in their declared sequence regardless of insertion order", () => {
    // Insert in deliberately scrambled order.
    const series = { p: 1, Uz: 2, Ux: 3, Uy: 4 };
    const ordered = canonicalSeriesEntries(series);
    expect(ordered.map(([k]) => k)).toEqual(["Ux", "Uy", "Uz", "p"]);
  });

  it("places non-canonical keys after canonical, alphabetically sorted", () => {
    const series = { zeta: 1, alpha: 2, Ux: 3, p: 4 };
    const ordered = canonicalSeriesEntries(series);
    expect(ordered.map(([k]) => k)).toEqual(["Ux", "p", "alpha", "zeta"]);
  });

  it("works on the full canonical set (no dropped keys)", () => {
    const series = {
      T: "t",
      epsilon: "e",
      omega: "o",
      k: "k",
      p: "p",
      Uz: "z",
      Uy: "y",
      Ux: "x",
    };
    const ordered = canonicalSeriesEntries(series);
    expect(ordered.map(([k]) => k)).toEqual([
      "Ux",
      "Uy",
      "Uz",
      "p",
      "k",
      "omega",
      "epsilon",
      "T",
    ]);
    // Values must travel with their keys (tuple integrity).
    expect(ordered.map(([, v]) => v)).toEqual([
      "x",
      "y",
      "z",
      "p",
      "k",
      "o",
      "e",
      "t",
    ]);
  });

  it("returns the full input set (no drops, no duplicates)", () => {
    const series = { Ux: 1, foo: 2, p: 3, bar: 4 };
    const ordered = canonicalSeriesEntries(series);
    const returnedKeys = ordered.map(([k]) => k).sort();
    expect(returnedKeys).toEqual(["Ux", "bar", "foo", "p"]);
  });

  it("handles empty input gracefully", () => {
    expect(canonicalSeriesEntries({})).toEqual([]);
  });

  it("handles only-non-canonical input (pure alphabetical fallback)", () => {
    const series = { zeta: 1, alpha: 2, mu: 3 };
    const ordered = canonicalSeriesEntries(series);
    expect(ordered.map(([k]) => k)).toEqual(["alpha", "mu", "zeta"]);
  });

  it("is stable across runs (sort determinism)", () => {
    const series = { Ux: 1, p: 2, k: 3, T: 4 };
    const run1 = canonicalSeriesEntries(series).map(([k]) => k);
    const run2 = canonicalSeriesEntries({ ...series }).map(([k]) => k);
    expect(run1).toEqual(run2);
  });
});

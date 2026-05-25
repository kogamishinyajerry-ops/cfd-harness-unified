// DEC-V61-205 (M5 C2) bug #2 · patch-selection logic for the Post
// surface overlay. Pins the tiering so the workbench picks a real,
// informative wall patch on every case class instead of the old
// hardcoded `engine` (which 404'd everywhere but APU bay).
import { describe, expect, it } from "vitest";

import {
  pickSurfacePatch,
  type PostPatch,
} from "../hooks/usePostPatches";

const p = (name: string, bytes: number): PostPatch => ({ name, bytes });

describe("pickSurfacePatch", () => {
  it("returns null for an empty patch set (no solve / no patches)", () => {
    expect(pickSurfacePatch([])).toBeNull();
  });

  it("prefers a wall-like patch over a much larger flow boundary", () => {
    // LDC: a huge inlet (flow boundary, tier 2) must lose to the small
    // fixedWalls (wall-like, tier 0). 'lid' is tier-1 neutral by name, so
    // the explicitly wall-like fixedWalls also outranks it.
    const chosen = pickSurfacePatch([
      p("inlet", 999_999),
      p("fixedWalls", 4_000),
      p("lid", 8_000),
    ]);
    expect(chosen).toBe("fixedWalls");
  });

  it("uses byte size as the tiebreak within the wall tier", () => {
    expect(
      pickSurfacePatch([p("fixedWalls", 9_000), p("lid", 3_000)]),
    ).toBe("fixedWalls");
  });

  it("falls back to a neutral patch over a flow boundary", () => {
    // backward_step style: a generic 'walls' (matches wall) beats outlet.
    expect(
      pickSurfacePatch([p("outlet", 50_000), p("walls", 1_000)]),
    ).toBe("walls");
  });

  it("picks the largest neutral patch when none are wall-like", () => {
    expect(
      pickSurfacePatch([p("zoneA", 2_000), p("zoneB", 5_000)]),
    ).toBe("zoneB");
  });

  it("still returns a flow boundary if that's all that exists", () => {
    // Degenerate: only boundaries. Better a surface than none.
    expect(
      pickSurfacePatch([p("inlet", 2_000), p("outlet", 9_000)]),
    ).toBe("outlet");
  });

  it("recognizes the canonical APU 'engine' patch as wall-like", () => {
    expect(
      pickSurfacePatch([p("farfield", 99_000), p("engine", 1_000)]),
    ).toBe("engine");
  });
});

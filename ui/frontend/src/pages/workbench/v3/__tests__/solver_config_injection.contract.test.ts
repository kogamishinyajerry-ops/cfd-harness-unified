/**
 * V89.2 · V8 state-injection harness contract tests
 *
 * Asserts the V89.2 contract from .planning/decisions/2026-05-17_v89_charter_dec.md §6:
 *   - Reverse-stop #28: ONLY active in dev/test env · production discards
 *   - Reverse-stop #29: returns synthetic state · no fetch fired here
 *     (caller MUST also short-circuit handlers · enforced at shell)
 *   - Returns null for unknown keys (forward-compat)
 *   - Returns null for null/empty keys
 *
 * Tests are pure (no React) · run in <50ms.
 */
import { describe, expect, it } from "vitest";

import { readInjectionState } from "../components/solver_config_injection";

describe("V89.2 · readInjectionState · env gating (reverse-stop #28)", () => {
  it("returns null when envMode='production' even with valid key", () => {
    expect(readInjectionState("dirty", "production")).toBeNull();
    expect(readInjectionState("diff_open", "production")).toBeNull();
    expect(readInjectionState("error", "production")).toBeNull();
  });

  it("returns slice when envMode='development'", () => {
    const slice = readInjectionState("dirty", "development");
    expect(slice).not.toBeNull();
    expect(slice?.injectionKey).toBe("dirty");
  });

  it("returns slice when envMode='test'", () => {
    const slice = readInjectionState("dirty", "test");
    expect(slice).not.toBeNull();
  });
});

describe("V89.2 · readInjectionState · null/empty key", () => {
  it("returns null for null key", () => {
    expect(readInjectionState(null, "development")).toBeNull();
  });

  it("returns null for undefined key", () => {
    expect(readInjectionState(undefined, "development")).toBeNull();
  });

  it("returns null for empty-string key", () => {
    expect(readInjectionState("", "development")).toBeNull();
  });
});

describe("V89.2 · readInjectionState · forward-compat unknown key", () => {
  it("returns null for unknown injection key (does NOT crash)", () => {
    expect(readInjectionState("v90_new_thing", "development")).toBeNull();
    expect(readInjectionState("anything", "development")).toBeNull();
  });
});

describe("V89.2 · readInjectionState · dirty slice", () => {
  it("returns state=dirty + endTime edited + no errors + diff closed", () => {
    const slice = readInjectionState("dirty", "development")!;
    expect(slice.state).toBe("dirty");
    expect(slice.fields.endTime).toBe("20.0");
    expect(slice.baseline.endTime).toBe("10.0");
    expect(slice.validationErrors).toEqual([]);
    expect(slice.errorMessage).toBeNull();
    expect(slice.forceDiffOpen).toBe(false);
    expect(slice.injectionKey).toBe("dirty");
  });

  it("dirty slice has 1 changed field (endTime) vs baseline", () => {
    const slice = readInjectionState("dirty", "development")!;
    const fields = Object.keys(slice.baseline) as Array<
      keyof typeof slice.baseline
    >;
    const changed = fields.filter(
      (f) => (slice.fields[f] ?? "") !== (slice.baseline[f] ?? ""),
    );
    expect(changed).toEqual(["endTime"]);
  });
});

describe("V89.2 · readInjectionState · diff_open slice", () => {
  it("returns state=dirty + forceDiffOpen=true", () => {
    const slice = readInjectionState("diff_open", "development")!;
    expect(slice.state).toBe("dirty");
    expect(slice.forceDiffOpen).toBe(true);
    expect(slice.fields.endTime).toBe("20.0");
    expect(slice.validationErrors).toEqual([]);
    expect(slice.injectionKey).toBe("diff_open");
  });
});

describe("V89.2 · readInjectionState · error slice", () => {
  it("returns state=error + 409-style errorMessage + diff closed", () => {
    const slice = readInjectionState("error", "development")!;
    expect(slice.state).toBe("error");
    expect(slice.errorMessage).toContain("409");
    expect(slice.errorMessage).toContain("refresh");
    expect(slice.forceDiffOpen).toBe(false);
    expect(slice.injectionKey).toBe("error");
  });

  it("error slice does NOT include a manifest-mutating payload (reverse-stop #29)", () => {
    const slice = readInjectionState("error", "development")!;
    // The slice is presentation-only. It MUST NOT include any field
    // that the shell could use to fire a POST. We verify by checking
    // the structural keys are presentation-layer only.
    const allowedKeys = new Set([
      "state",
      "fields",
      "baseline",
      "validationErrors",
      "errorMessage",
      "forceDiffOpen",
      "injectionKey",
    ]);
    for (const key of Object.keys(slice)) {
      expect(allowedKeys.has(key)).toBe(true);
    }
  });
});

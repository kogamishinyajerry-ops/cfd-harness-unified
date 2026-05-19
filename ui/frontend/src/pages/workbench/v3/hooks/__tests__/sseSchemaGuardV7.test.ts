/**
 * V87.4 · V7.B SSE schema-drift guard contract tests
 *
 * Asserts the V87.4 contract from .planning/decisions/2026-05-17_v87_charter_dec.md §6 #22:
 *   - Each guard returns FALSE for malformed payloads (graceful degrade)
 *   - Each guard returns TRUE for canonical valid shapes
 *   - Edge cases: extra fields tolerated · null / array / primitive rejected
 *   - V87 reverse-stop #22: invalid events → guard returns false → caller
 *     skips dispatch · NOT crash · NOT state corruption
 *
 * Tests are pure (no React) · run in <100ms.
 */
import { describe, expect, it } from "vitest";

import {
  isStartEvent,
  isDoneEvent,
  isErrorEvent,
  isResidualEvent,
} from "../sseSchemaGuardV7";

describe("V87.4 · isStartEvent", () => {
  it("accepts {run_id: string}", () => {
    expect(isStartEvent({ run_id: "R-1" })).toBe(true);
    expect(isStartEvent({ run_id: "2026-05-17T12-00-00Z" })).toBe(true);
  });

  it("rejects empty run_id", () => {
    expect(isStartEvent({ run_id: "" })).toBe(false);
  });

  it("rejects missing / wrong-type run_id", () => {
    expect(isStartEvent({})).toBe(false);
    expect(isStartEvent({ run_id: 123 })).toBe(false);
    expect(isStartEvent({ run_id: null })).toBe(false);
    expect(isStartEvent({ runId: "R-1" })).toBe(false);
  });

  it("rejects non-object payloads", () => {
    expect(isStartEvent(null)).toBe(false);
    expect(isStartEvent(undefined)).toBe(false);
    expect(isStartEvent("R-1")).toBe(false);
    expect(isStartEvent(["R-1"])).toBe(false);
    expect(isStartEvent(42)).toBe(false);
  });

  it("tolerates extra fields", () => {
    expect(
      isStartEvent({ run_id: "R-1", extra: "ignored", ts: 12345 }),
    ).toBe(true);
  });
});

describe("V87.4 · isDoneEvent", () => {
  it("accepts empty payload (run_id + success both optional)", () => {
    expect(isDoneEvent({})).toBe(true);
  });

  it("accepts payload with valid run_id + success", () => {
    expect(isDoneEvent({ run_id: "R-1", success: true })).toBe(true);
    expect(isDoneEvent({ run_id: "R-2", success: false })).toBe(true);
  });

  it("rejects payload with wrong-type run_id", () => {
    expect(isDoneEvent({ run_id: 42 })).toBe(false);
    expect(isDoneEvent({ run_id: null })).toBe(false);
  });

  it("rejects payload with wrong-type success", () => {
    expect(isDoneEvent({ success: "yes" })).toBe(false);
    expect(isDoneEvent({ success: 1 })).toBe(false);
  });

  it("rejects non-object payloads", () => {
    expect(isDoneEvent(null)).toBe(false);
    expect(isDoneEvent(["done"])).toBe(false);
    expect(isDoneEvent("PASS")).toBe(false);
  });
});

describe("V87.4 · isErrorEvent", () => {
  it("accepts empty payload (message optional)", () => {
    expect(isErrorEvent({})).toBe(true);
  });

  it("accepts payload with string message", () => {
    expect(isErrorEvent({ message: "diverged" })).toBe(true);
  });

  it("rejects payload with wrong-type message", () => {
    expect(isErrorEvent({ message: 42 })).toBe(false);
    expect(isErrorEvent({ message: ["err"] })).toBe(false);
  });

  it("rejects non-object payloads", () => {
    expect(isErrorEvent(null)).toBe(false);
    expect(isErrorEvent("error")).toBe(false);
  });
});

describe("V87.4 · isResidualEvent", () => {
  it("accepts canonical residual payload", () => {
    expect(
      isResidualEvent({
        iteration: 1,
        values: { p: 0.1, U_x: 0.05 },
        ts_ms: 1000,
      }),
    ).toBe(true);
  });

  it("accepts empty values dict (no residual variables yet)", () => {
    expect(
      isResidualEvent({ iteration: 0, values: {}, ts_ms: 500 }),
    ).toBe(true);
  });

  it("rejects missing iteration", () => {
    expect(isResidualEvent({ values: { p: 0.1 }, ts_ms: 1 })).toBe(false);
  });

  it("rejects wrong-type iteration", () => {
    expect(
      isResidualEvent({ iteration: "1", values: {}, ts_ms: 1 }),
    ).toBe(false);
    expect(
      isResidualEvent({ iteration: null, values: {}, ts_ms: 1 }),
    ).toBe(false);
  });

  it("rejects NaN / Infinity iteration", () => {
    expect(
      isResidualEvent({ iteration: NaN, values: {}, ts_ms: 1 }),
    ).toBe(false);
    expect(
      isResidualEvent({ iteration: Infinity, values: {}, ts_ms: 1 }),
    ).toBe(false);
  });

  it("rejects missing / wrong-type ts_ms", () => {
    expect(isResidualEvent({ iteration: 1, values: {} })).toBe(false);
    expect(
      isResidualEvent({ iteration: 1, values: {}, ts_ms: "1000" }),
    ).toBe(false);
  });

  it("rejects missing / wrong-shape values", () => {
    expect(isResidualEvent({ iteration: 1, ts_ms: 1 })).toBe(false);
    expect(
      isResidualEvent({ iteration: 1, values: [0.1], ts_ms: 1 }),
    ).toBe(false);
    expect(
      isResidualEvent({ iteration: 1, values: null, ts_ms: 1 }),
    ).toBe(false);
  });

  it("rejects values with non-number entries", () => {
    expect(
      isResidualEvent({
        iteration: 1,
        values: { p: "0.1" },
        ts_ms: 1,
      }),
    ).toBe(false);
    expect(
      isResidualEvent({
        iteration: 1,
        values: { p: NaN },
        ts_ms: 1,
      }),
    ).toBe(false);
    expect(
      isResidualEvent({
        iteration: 1,
        values: { p: Infinity },
        ts_ms: 1,
      }),
    ).toBe(false);
  });

  it("rejects non-object payloads", () => {
    expect(isResidualEvent(null)).toBe(false);
    expect(isResidualEvent([1, 2, 3])).toBe(false);
    expect(isResidualEvent("residual")).toBe(false);
  });
});

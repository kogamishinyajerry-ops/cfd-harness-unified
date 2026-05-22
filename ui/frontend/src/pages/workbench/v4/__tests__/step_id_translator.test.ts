// DEC-V61-202-SUB-M30-INTEGRATION-V4-SHELL · step translator unit tests.

import { describe, expect, it } from "vitest";

import { v4StepToBackendStep } from "../step_id_translator";

describe("v4StepToBackendStep", () => {
  it("maps import → 1 (geometry on-ramp)", () => {
    expect(v4StepToBackendStep("import")).toBe(1);
  });

  it("maps geometry → 1", () => {
    expect(v4StepToBackendStep("geometry")).toBe(1);
  });

  it("maps mesh → 2", () => {
    expect(v4StepToBackendStep("mesh")).toBe(2);
  });

  it("maps physics → 3", () => {
    expect(v4StepToBackendStep("physics")).toBe(3);
  });

  it("maps boundary → 4", () => {
    expect(v4StepToBackendStep("boundary")).toBe(4);
  });

  it("maps solver → 5 (solve+postp spine)", () => {
    expect(v4StepToBackendStep("solver")).toBe(5);
  });

  it("maps post → 5 (same spine as solver)", () => {
    expect(v4StepToBackendStep("post")).toBe(5);
  });

  it("maps doe → 5 (higher-order solver)", () => {
    expect(v4StepToBackendStep("doe")).toBe(5);
  });
});

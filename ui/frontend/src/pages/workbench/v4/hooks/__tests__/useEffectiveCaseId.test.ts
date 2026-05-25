// Regression test for the M3.11 build-blocking tsc fix: useEffectiveCaseId now
// accepts an undefined activeStep (TopBarV4's prop is optional). Also pins the
// blueprint-vs-case gate behavior contract documented in the hook's docstring.
import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useEffectiveCaseId } from "../useEffectiveCaseId";

describe("useEffectiveCaseId", () => {
  it("accepts undefined activeStep → case mode (no crash, not blueprint)", () => {
    const { result } = renderHook(() =>
      useEffectiveCaseId("circular_cylinder_wake", undefined),
    );
    expect(result.current.isBlueprintMode).toBe(false);
    expect(result.current.isDoe).toBe(false);
    expect(result.current.isGeometryBlueprint).toBe(false);
    expect(result.current.effectiveCaseId).toBe("circular_cylinder_wake");
  });

  it("doe step → always blueprint mode (effectiveCaseId null)", () => {
    const { result } = renderHook(() => useEffectiveCaseId("some_case", "doe"));
    expect(result.current.isDoe).toBe(true);
    expect(result.current.isBlueprintMode).toBe(true);
    expect(result.current.effectiveCaseId).toBeNull();
  });

  it("geometry step + no case → geometry blueprint", () => {
    const { result } = renderHook(() => useEffectiveCaseId(null, "geometry"));
    expect(result.current.isGeometryBlueprint).toBe(true);
    expect(result.current.isBlueprintMode).toBe(true);
    expect(result.current.effectiveCaseId).toBeNull();
  });

  it("geometry step + case loaded → case mode", () => {
    const { result } = renderHook(() =>
      useEffectiveCaseId("circular_cylinder_wake", "geometry"),
    );
    expect(result.current.isGeometryBlueprint).toBe(false);
    expect(result.current.isBlueprintMode).toBe(false);
    expect(result.current.effectiveCaseId).toBe("circular_cylinder_wake");
  });
});

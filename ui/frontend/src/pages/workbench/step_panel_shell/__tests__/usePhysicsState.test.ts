/**
 * V68-C.1 · usePhysicsState parser unit tests.
 *
 * Hook integration (committed / reference / loading / error transitions)
 * is exercised through MaterialCard.test.tsx; this file isolates the
 * pure parsing functions so a regex regression surfaces with a tight
 * error message regardless of React rendering noise.
 */
import { describe, expect, it } from "vitest";

import {
  parsePhysicalProperties,
  parseMomentumTransport,
  parsePhysicsState,
  parseCaseDetailReference,
} from "../usePhysicsState";
import type { CaseDetail } from "@/types/validation";
import type { PhysicsStateResponse } from "@/types/physics";

describe("parsePhysicalProperties · transportProperties dict", () => {
  it("parses Newtonian + dimensioned nu", () => {
    const text = [
      "transportModel  Newtonian;",
      "nu              [0 2 -1 0 0 0 0] 1e-3;",
    ].join("\n");
    const parsed = parsePhysicalProperties(text);
    expect(parsed.transportModel).toBe("Newtonian");
    expect(parsed.nu).toBeCloseTo(1e-3, 6);
  });

  it("parses bare nu without dimensions", () => {
    const parsed = parsePhysicalProperties("nu  1.5e-5;");
    expect(parsed.nu).toBeCloseTo(1.5e-5, 12);
  });

  it("parses rho with and without dimensions", () => {
    expect(parsePhysicalProperties("rho 1.225;").rho).toBeCloseTo(1.225, 6);
    expect(
      parsePhysicalProperties("rho  [1 -3 0 0 0 0 0] 1000.0;").rho,
    ).toBeCloseTo(1000.0, 6);
  });

  it("returns no fields when dict is empty / commented out", () => {
    expect(parsePhysicalProperties("// nothing here")).toEqual({});
    expect(parsePhysicalProperties("")).toEqual({});
  });

  it("does not match nuField (false-positive guard)", () => {
    // OpenFOAM dicts often contain `nuField wallFunction` keys — the
    // regex must require the literal `nu` token boundary, not a prefix.
    const parsed = parsePhysicalProperties("nuField 1.0;");
    expect(parsed.nu).toBeUndefined();
  });
});

describe("parseMomentumTransport · momentumTransport dict", () => {
  it("parses laminar simulationType", () => {
    expect(parseMomentumTransport("simulationType  laminar;").simulationType).toBe(
      "laminar",
    );
  });

  it("parses RAS + RASModel nested", () => {
    const text = [
      "simulationType  RAS;",
      "RAS",
      "{",
      "    RASModel        kOmegaSST;",
      "    turbulence      on;",
      "}",
    ].join("\n");
    const parsed = parseMomentumTransport(text);
    expect(parsed.simulationType).toBe("RAS");
    expect(parsed.rasModel).toBe("kOmegaSST");
  });

  it("returns no fields on empty dict", () => {
    expect(parseMomentumTransport("")).toEqual({});
  });
});

describe("parsePhysicsState · combined committed state", () => {
  it("merges material + regime parses into one ParsedPhysics", () => {
    const state: PhysicsStateResponse = {
      case_id: "case_001",
      material_dict_text:
        "transportModel  Newtonian;\nnu  [0 2 -1 0 0 0 0] 1e-3;\nrho 1000.0;",
      regime_dict_text: "simulationType  laminar;",
    };
    const parsed = parsePhysicsState(state);
    expect(parsed.transportModel).toBe("Newtonian");
    expect(parsed.nu).toBeCloseTo(1e-3, 6);
    expect(parsed.rho).toBeCloseTo(1000.0, 6);
    expect(parsed.simulationType).toBe("laminar");
    // Whitelist-only fields remain null when source is dict text.
    expect(parsed.solver).toBeNull();
    expect(parsed.reynolds).toBeNull();
  });

  it("handles null dict texts (freshly scaffolded case)", () => {
    const state: PhysicsStateResponse = {
      case_id: "case_002",
      material_dict_text: null,
      regime_dict_text: null,
    };
    const parsed = parsePhysicsState(state);
    expect(parsed.transportModel).toBeNull();
    expect(parsed.simulationType).toBeNull();
    expect(parsed.nu).toBeNull();
  });
});

describe("parseCaseDetailReference · whitelist fallback", () => {
  const baseDetail = (): CaseDetail => ({
    case_id: "naca0012_airfoil",
    name: "NACA 0012",
    reference: null,
    doi: null,
    flow_type: "EXTERNAL",
    geometry_type: "AIRFOIL",
    compressibility: "INCOMPRESSIBLE",
    steady_state: "STEADY",
    solver: "simpleFoam",
    turbulence_model: "k-omega SST",
    parameters: { Re: 3_000_000, angle_of_attack: 0.0 },
    gold_standard: null,
    preconditions: [],
    contract_status_narrative: null,
  });

  it("derives RAS simulationType from k-omega turbulence_model", () => {
    const parsed = parseCaseDetailReference(baseDetail());
    expect(parsed.solver).toBe("simpleFoam");
    expect(parsed.turbulenceModel).toBe("k-omega SST");
    expect(parsed.simulationType).toBe("RAS");
    expect(parsed.reynolds).toBe(3_000_000);
  });

  it("derives laminar simulationType from laminar turbulence_model", () => {
    const detail = { ...baseDetail(), turbulence_model: "laminar" };
    expect(parseCaseDetailReference(detail).simulationType).toBe("laminar");
  });

  it("derives LES simulationType from LES turbulence_model", () => {
    const detail = { ...baseDetail(), turbulence_model: "LES Smagorinsky" };
    expect(parseCaseDetailReference(detail).simulationType).toBe("LES");
  });

  it("leaves simulationType null for unrecognized turbulence model", () => {
    const detail = { ...baseDetail(), turbulence_model: "???" };
    expect(parseCaseDetailReference(detail).simulationType).toBeNull();
  });

  it("handles missing Re parameter gracefully", () => {
    const detail = { ...baseDetail(), parameters: {} };
    expect(parseCaseDetailReference(detail).reynolds).toBeNull();
  });
});

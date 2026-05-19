/**
 * V88.3 · V8.B solver_config_validator contract tests
 *
 * Asserts the V8.B contract from .planning/blueprints/v8/INDEX.md:
 *   - Returns empty array on valid input
 *   - Each ValidationKind triggers on its specific malformed case
 *   - Cross-field constraints (deltaT > endTime · writeInterval > endTime)
 *     surface as "too_large" on the offending field
 *   - Schema-drift discipline: extra/unknown fields are tolerated, NOT crashed
 *   - parseControlDictFields recovers key/value lines from OpenFOAM text
 *   - serializeControlDictFields preserves baseContent header + only patches
 *     known keys
 *
 * Pure functions · no React · no fetch · runs in <50ms.
 */
import { describe, expect, it } from "vitest";

import {
  validateControlDictFields,
  parseControlDictFields,
  serializeControlDictFields,
  KNOWN_SOLVERS,
  ALLOWED_WRITE_FORMATS,
} from "../components/solver_config_validator";

const validBaseline = {
  application: "icoFoam",
  endTime: "10.0",
  deltaT: "0.01",
  writeInterval: "1.0",
  writeFormat: "ascii",
};

describe("V88.3 · validateControlDictFields · happy path", () => {
  it("returns [] on canonical valid input", () => {
    expect(validateControlDictFields(validBaseline)).toEqual([]);
  });

  it("accepts all known solvers", () => {
    for (const solver of KNOWN_SOLVERS) {
      const errs = validateControlDictFields({
        ...validBaseline,
        application: solver,
      });
      expect(errs).toEqual([]);
    }
  });

  it("accepts both allowed write formats", () => {
    for (const fmt of ALLOWED_WRITE_FORMATS) {
      const errs = validateControlDictFields({
        ...validBaseline,
        writeFormat: fmt,
      });
      expect(errs).toEqual([]);
    }
  });

  it("accepts scientific notation for numeric fields", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      deltaT: "1e-3",
      endTime: "1e2",
    });
    expect(errs).toEqual([]);
  });
});

describe("V88.3 · validateControlDictFields · missing", () => {
  it("reports each required field missing when fields={}", () => {
    const errs = validateControlDictFields({});
    expect(errs.length).toBeGreaterThanOrEqual(5);
    expect(errs.every((e) => e.kind === "missing")).toBe(true);
    const missingFields = errs.map((e) => e.field).sort();
    expect(missingFields).toEqual(
      [
        "application",
        "deltaT",
        "endTime",
        "writeFormat",
        "writeInterval",
      ].sort(),
    );
  });

  it("treats blank/whitespace as missing", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      application: "   ",
    });
    expect(errs.some((e) => e.field === "application" && e.kind === "missing")).toBe(true);
  });
});

describe("V88.3 · validateControlDictFields · invalid_solver", () => {
  it("rejects unknown solver name", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      application: "bogusFoam",
    });
    expect(errs).toEqual([
      {
        field: "application",
        kind: "invalid_solver",
        message: expect.stringContaining("bogusFoam"),
      },
    ]);
  });
});

describe("V88.3 · validateControlDictFields · invalid_format", () => {
  it("rejects unknown writeFormat", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      writeFormat: "json",
    });
    expect(errs).toEqual([
      {
        field: "writeFormat",
        kind: "invalid_format",
        message: expect.stringContaining("ascii"),
      },
    ]);
  });
});

describe("V88.3 · validateControlDictFields · non_numeric", () => {
  it("rejects non-numeric endTime", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      endTime: "ten",
    });
    expect(errs).toEqual([
      {
        field: "endTime",
        kind: "non_numeric",
        message: expect.stringContaining("endTime"),
      },
    ]);
  });

  it("rejects Infinity / NaN as non_numeric", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      deltaT: "Infinity",
    });
    expect(errs.some((e) => e.field === "deltaT" && e.kind === "non_numeric")).toBe(true);
  });
});

describe("V88.3 · validateControlDictFields · negative", () => {
  it("rejects negative endTime", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      endTime: "-1",
    });
    expect(errs).toEqual([
      {
        field: "endTime",
        kind: "negative",
        message: expect.stringContaining("> 0"),
      },
    ]);
  });

  it("rejects zero deltaT (must be strictly > 0)", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      deltaT: "0",
    });
    expect(errs.some((e) => e.field === "deltaT" && e.kind === "negative")).toBe(true);
  });
});

describe("V88.3 · validateControlDictFields · too_large", () => {
  it("flags deltaT > endTime", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      endTime: "1.0",
      deltaT: "5.0",
    });
    expect(errs).toEqual([
      {
        field: "deltaT",
        kind: "too_large",
        message: expect.stringContaining("endTime"),
      },
    ]);
  });

  it("flags writeInterval > endTime", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      endTime: "1.0",
      writeInterval: "5.0",
    });
    expect(errs).toEqual([
      {
        field: "writeInterval",
        kind: "too_large",
        message: expect.stringContaining("endTime"),
      },
    ]);
  });
});

describe("V88.3 · validateControlDictFields · schema-drift discipline", () => {
  it("ignores unknown/extra fields without crashing (V87.4 carry)", () => {
    const errs = validateControlDictFields({
      ...validBaseline,
      // @ts-expect-error · test schema-drift tolerance
      mysteryField: "future-foam-arc",
    });
    expect(errs).toEqual([]);
  });
});

describe("V88.3 · validateControlDictFields · multi-error accumulation", () => {
  it("returns all distinct errors for a fully-broken input", () => {
    const errs = validateControlDictFields({
      application: "noSuchFoam",
      endTime: "-5",
      deltaT: "abc",
      writeInterval: "",
      writeFormat: "yaml",
    });
    expect(errs.some((e) => e.field === "application" && e.kind === "invalid_solver")).toBe(true);
    expect(errs.some((e) => e.field === "endTime" && e.kind === "negative")).toBe(true);
    expect(errs.some((e) => e.field === "deltaT" && e.kind === "non_numeric")).toBe(true);
    expect(errs.some((e) => e.field === "writeInterval" && e.kind === "missing")).toBe(true);
    expect(errs.some((e) => e.field === "writeFormat" && e.kind === "invalid_format")).toBe(true);
  });
});

describe("V88.3 · parseControlDictFields", () => {
  it("recovers fields from canonical OpenFOAM-style content", () => {
    const content = `
FoamFile { version 2.0; }
application     icoFoam;
startTime       0;
endTime         10.0;
deltaT          0.005;
writeInterval   0.5;
writeFormat     ascii;
runTimeModifiable yes;
`;
    const fields = parseControlDictFields(content);
    expect(fields).toEqual({
      application: "icoFoam",
      endTime: "10.0",
      deltaT: "0.005",
      writeInterval: "0.5",
      writeFormat: "ascii",
    });
  });

  it("returns empty object for empty content (graceful)", () => {
    expect(parseControlDictFields("")).toEqual({});
  });

  it("returns empty object for non-controlDict content (graceful)", () => {
    const fields = parseControlDictFields("random text without keys");
    expect(fields).toEqual({});
  });
});

describe("V88.3 · serializeControlDictFields", () => {
  it("patches existing key lines in baseContent in-place", () => {
    const base = `
application     icoFoam;
endTime         10.0;
deltaT          0.005;
writeInterval   0.5;
writeFormat     ascii;
`;
    const out = serializeControlDictFields(
      {
        application: "simpleFoam",
        endTime: "100.0",
        deltaT: "0.01",
        writeInterval: "1.0",
        writeFormat: "binary",
      },
      base,
    );
    expect(out).toContain("application     simpleFoam;");
    expect(out).toContain("endTime         100.0;");
    expect(out).toContain("deltaT          0.01;");
    expect(out).toContain("writeInterval   1.0;");
    expect(out).toContain("writeFormat     binary;");
    // Did NOT introduce icoFoam (replaced cleanly).
    expect(out).not.toContain("icoFoam");
  });

  it("emits minimal block when no baseContent", () => {
    const out = serializeControlDictFields(
      {
        application: "icoFoam",
        endTime: "10.0",
        deltaT: "0.005",
        writeInterval: "0.5",
        writeFormat: "ascii",
      },
      "",
    );
    expect(out).toContain("application    icoFoam;");
    expect(out).toContain("endTime    10.0;");
  });
});

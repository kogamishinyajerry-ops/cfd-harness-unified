/**
 * V91.1 · V9.C JSON SSOT contract
 *
 * Asserts the rule corpus file at `src/data/v9_advisor_rules.json` is in
 * canonical form so that the Python matcher (`ui/backend/services/v9_advisor/`)
 * loads byte-identical content. Canonical = JSON.stringify with sorted keys,
 * indent=2, UTF-8, trailing newline.
 *
 * This is the V91 RS#37 enforcement point. RS#32 (non-empty provenance) is
 * enforced at runtime by `buildRules()` in v9_advisor_rules.ts; we also
 * assert it here for static-source proof.
 */
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const JSON_PATH = resolve(__dirname, "../v9_advisor_rules.json");

function canonicalize(value: unknown): string {
  const sortKeys = (v: unknown): unknown => {
    if (v === null || typeof v !== "object") return v;
    if (Array.isArray(v)) return v.map(sortKeys);
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(v as Record<string, unknown>).sort()) {
      out[k] = sortKeys((v as Record<string, unknown>)[k]);
    }
    return out;
  };
  return JSON.stringify(sortKeys(value), null, 2) + "\n";
}

describe("V91.1 · V9 rule corpus JSON SSOT · canonical form", () => {
  it("JSON file is byte-identical to its canonical re-serialization (RS#37)", () => {
    const raw = readFileSync(JSON_PATH, "utf-8");
    const parsed = JSON.parse(raw);
    const recanonical = canonicalize(parsed);
    expect(raw).toBe(recanonical);
  });

  it("top-level shape: {version: string, rules: array}", () => {
    const data = JSON.parse(readFileSync(JSON_PATH, "utf-8"));
    expect(typeof data.version).toBe("string");
    expect(Array.isArray(data.rules)).toBe(true);
    expect(data.rules.length).toBeGreaterThanOrEqual(6);
  });

  it("each rule has id + severity + commentary + provenance · all non-empty (RS#32)", () => {
    const data = JSON.parse(readFileSync(JSON_PATH, "utf-8"));
    for (const r of data.rules) {
      expect(typeof r.id).toBe("string");
      expect(r.id.length).toBeGreaterThan(0);
      expect(["advise", "warn", "info"]).toContain(r.severity);
      expect(typeof r.commentary).toBe("string");
      expect(r.commentary.length).toBeGreaterThan(20);
      expect(typeof r.provenance).toBe("string");
      expect(r.provenance.length).toBeGreaterThan(0);
    }
  });

  it("rule ids are unique", () => {
    const data = JSON.parse(readFileSync(JSON_PATH, "utf-8"));
    const ids = data.rules.map((r: { id: string }) => r.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });

  it("file ends with a single trailing newline (RS#37)", () => {
    const raw = readFileSync(JSON_PATH, "utf-8");
    expect(raw.endsWith("\n")).toBe(true);
    expect(raw.endsWith("\n\n")).toBe(false);
  });
});

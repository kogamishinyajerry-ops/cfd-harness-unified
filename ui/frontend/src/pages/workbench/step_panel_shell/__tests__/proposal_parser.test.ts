// DEC-V61-121 · proposal parser unit tests.

import { describe, expect, it } from "vitest";

import { parseProposals } from "../proposal_parser";

describe("parseProposals", () => {
  it("returns the input unchanged when no PROPOSAL block is present", () => {
    const result = parseProposals("hello, no proposals here");
    expect(result.displayText).toBe("hello, no proposals here");
    expect(result.proposals).toEqual([]);
    expect(result.pendingPartial).toBe(false);
  });

  it("strips a complete proposal from displayText and parses its YAML", () => {
    const input = `here's an idea
<<PROPOSAL
tool: set_patch_bc_type
args:
  patch_name: walls
  bc_class: no_slip_wall
reason: walls should be no-slip
PROPOSAL>>
let me know if you want me to do this`;
    const result = parseProposals(input);
    expect(result.displayText).toContain("here's an idea");
    expect(result.displayText).toContain(
      "let me know if you want me to do this",
    );
    expect(result.displayText).not.toContain("<<PROPOSAL");
    expect(result.displayText).not.toContain("PROPOSAL>>");
    expect(result.proposals).toHaveLength(1);
    const [p] = result.proposals;
    expect(p.ok).toBe(true);
    expect(p.tool).toBe("set_patch_bc_type");
    expect(p.args).toEqual({ patch_name: "walls", bc_class: "no_slip_wall" });
    expect(p.reason).toBe("walls should be no-slip");
    expect(result.pendingPartial).toBe(false);
  });

  it("flags a partial open as pendingPartial and hides it from displayText", () => {
    const input = `working on this:
<<PROPOSAL
tool: set_patch_bc_type
args:
  patch_n`;
    const result = parseProposals(input);
    expect(result.displayText).toBe("working on this:\n");
    expect(result.pendingPartial).toBe(true);
    expect(result.proposals).toHaveLength(0);
  });

  it("handles multiple proposals in one assistant turn", () => {
    const input = `first:
<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: walls, bc_class: no_slip_wall}
PROPOSAL>>
and the inlet:
<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: inlet, bc_class: velocity_inlet}
PROPOSAL>>
that's it`;
    const result = parseProposals(input);
    expect(result.proposals).toHaveLength(2);
    expect(result.proposals[0].args).toEqual({
      patch_name: "walls",
      bc_class: "no_slip_wall",
    });
    expect(result.proposals[1].args).toEqual({
      patch_name: "inlet",
      bc_class: "velocity_inlet",
    });
    expect(result.proposals[0].index).toBe(0);
    expect(result.proposals[1].index).toBe(1);
    expect(result.displayText).toContain("first:");
    expect(result.displayText).toContain("and the inlet:");
    expect(result.displayText).toContain("that's it");
  });

  it("ignores PROPOSAL blocks inside a Markdown code fence", () => {
    const input = `here's how a proposal looks:
\`\`\`
<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: walls, bc_class: no_slip_wall}
PROPOSAL>>
\`\`\`
ask me to do that and i will.`;
    const result = parseProposals(input);
    // No real proposals (the fenced one is an example).
    expect(result.proposals).toHaveLength(0);
    // The fenced text remains visible verbatim — engineers see the
    // example.
    expect(result.displayText).toContain("<<PROPOSAL");
    expect(result.displayText).toContain("PROPOSAL>>");
  });

  it("emits a malformed proposal entry on YAML parse failure", () => {
    const input = `<<PROPOSAL
tool: set_patch_bc_type
args: : : not yaml
PROPOSAL>>`;
    const result = parseProposals(input);
    expect(result.proposals).toHaveLength(1);
    const [p] = result.proposals;
    expect(p.ok).toBe(false);
    expect(p.malformedReason).toBeDefined();
    expect(p.rawYaml).toContain("not yaml");
  });

  it("emits malformed when required keys are missing", () => {
    const input = `<<PROPOSAL
just: random keys
PROPOSAL>>`;
    const result = parseProposals(input);
    expect(result.proposals[0].ok).toBe(false);
    expect(result.proposals[0].malformedReason).toContain("missing required keys");
  });

  it("ignores `<<PROPOSAL` substrings inside narrative prose", () => {
    const input =
      "i won't actually emit a <<PROPOSAL block here, just talking about them";
    const result = parseProposals(input);
    expect(result.proposals).toHaveLength(0);
    expect(result.displayText).toBe(input);
    expect(result.pendingPartial).toBe(false);
  });

  it("requires open and close on their own lines", () => {
    // CLOSE on a line with trailing text is not a real close.
    const input = `<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: walls, bc_class: no_slip_wall}
PROPOSAL>> trailing words here`;
    const result = parseProposals(input);
    // No complete block recognized → pending partial, no proposals.
    expect(result.proposals).toHaveLength(0);
    expect(result.pendingPartial).toBe(true);
  });

  it("ignores PROPOSAL inside an UNCLOSED code fence (Codex R1 P2)", () => {
    // The assistant is mid-stream: it opened ``` to start an example
    // but the closing ``` has not arrived yet. A `<<PROPOSAL` inside
    // that open fence MUST NOT register as a real action — the user
    // would see an Accept button for inert documentation.
    const input = `here's the format:
\`\`\`
<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: walls, bc_class: no_slip_wall}
PROPOSAL>>`;
    // No closing ``` yet.
    const result = parseProposals(input);
    expect(result.proposals).toHaveLength(0);
  });

  it("recognizes a real PROPOSAL once a code-fence example is fully closed", () => {
    // Same as above but now with the ``` closer arrived AFTER the
    // (example) PROPOSAL block — fenced content is masked, so the
    // example is correctly ignored. A REAL proposal AFTER the close
    // is recognized.
    const input = `here's the format:
\`\`\`
<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: ex, bc_class: no_slip_wall}
PROPOSAL>>
\`\`\`
now the actual proposal:
<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: real_walls, bc_class: no_slip_wall}
PROPOSAL>>`;
    const result = parseProposals(input);
    expect(result.proposals).toHaveLength(1);
    expect(result.proposals[0].args).toEqual({
      patch_name: "real_walls",
      bc_class: "no_slip_wall",
    });
  });

  it("preserves stable indices across cumulative re-parses", () => {
    // Simulating streaming: first half just text, then proposal arrives.
    const r1 = parseProposals("text only so far");
    expect(r1.proposals).toHaveLength(0);

    const r2 = parseProposals(`text only so far
<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: walls, bc_class: no_slip_wall}
PROPOSAL>>`);
    expect(r2.proposals[0].index).toBe(0);

    const r3 = parseProposals(`text only so far
<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: walls, bc_class: no_slip_wall}
PROPOSAL>>
<<PROPOSAL
tool: set_patch_bc_type
args: {patch_name: inlet, bc_class: velocity_inlet}
PROPOSAL>>`);
    expect(r3.proposals.map((p) => p.index)).toEqual([0, 1]);
  });
});

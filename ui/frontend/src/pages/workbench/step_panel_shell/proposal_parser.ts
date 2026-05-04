// DEC-V61-121 · PROPOSAL delimiter parser.
//
// Pure function that takes the cumulative streamed assistant text
// and returns:
//   - displayText: the text the user sees, with complete PROPOSAL
//     blocks STRIPPED so the chat doesn't show YAML noise.
//   - proposals: ordered list of parsed proposals (one per complete
//     <<PROPOSAL ... PROPOSAL>> block), with raw YAML preserved so
//     the UI can inspect / show on hover.
//   - pendingPartial: true iff a `<<PROPOSAL` opening delimiter has
//     been seen but no closing `PROPOSAL>>` yet — UI uses this to
//     decide whether to suppress the trailing partial text from the
//     visible bubble.
//
// Strict invariants:
//   - Both delimiters MUST appear on lines by themselves (whitespace-
//     only allowed). This rejects `<<PROPOSAL` inside narrative prose
//     ("we'll <<PROPOSAL>>") which would otherwise false-positive.
//   - PROPOSAL blocks inside Markdown code fences (``` ... ```) are
//     IGNORED — they're examples, not real actions (Risk-2 in DEC).
//   - Malformed YAML inside a complete block produces a `malformed`
//     proposal entry; the raw text is still extracted so the UI can
//     surface a "format error" warning instead of silently dropping.

import yaml from "js-yaml";

export interface ParsedProposal {
  /** Stable index within the assistant turn (0-based). Used as React key. */
  index: number;
  /** Tool name from the YAML, or null if malformed/missing. */
  tool: string | null;
  /** Args object from the YAML, or null if malformed/missing. */
  args: Record<string, unknown> | null;
  /** Optional reason string from the YAML. */
  reason: string | null;
  /** True iff parse succeeded AND tool/args are present + well-shaped. */
  ok: boolean;
  /** When ok is false, a one-line operator-friendly explanation. */
  malformedReason?: string;
  /** The raw YAML text between the delimiters (for debugging / inspection). */
  rawYaml: string;
}

export interface ParseResult {
  displayText: string;
  proposals: ParsedProposal[];
  /** True iff an opening `<<PROPOSAL` has been seen but not closed. */
  pendingPartial: boolean;
}

const OPEN = "<<PROPOSAL";
const CLOSE = "PROPOSAL>>";

/**
 * Strip Markdown ``` code fences from `text`, replacing each fenced
 * block with a placeholder of equal length so positions outside the
 * fences are unchanged. The parser only looks for PROPOSAL delimiters
 * OUTSIDE code fences (Risk-2).
 *
 * The returned string is for INTERNAL parsing only; the user-visible
 * displayText uses the original text minus matched proposals.
 */
function maskCodeFences(text: string): string {
  // Naive matcher for ```...``` blocks (single or multi-line). The
  // chat is plain text so there's no nested-fence concern. Replace
  // with same-length spaces so substring offsets line up.
  return text.replace(/```[\s\S]*?```/g, (match) => " ".repeat(match.length));
}

function isLineWith(text: string, lineStart: number, lineEnd: number, target: string): boolean {
  const line = text.slice(lineStart, lineEnd).trim();
  return line === target;
}

/** Find the start-of-line position at or before `idx`. */
function lineStartAt(text: string, idx: number): number {
  let i = idx;
  while (i > 0 && text[i - 1] !== "\n") i -= 1;
  return i;
}

/** Find the end-of-line position at or after `idx` (returns the index
 *  of the next "\n" or text.length). */
function lineEndAt(text: string, idx: number): number {
  const nl = text.indexOf("\n", idx);
  return nl === -1 ? text.length : nl;
}

/**
 * Locate the next PROPOSAL block boundary in `masked` starting at
 * `searchFrom`. Returns the open/close character offsets in the
 * ORIGINAL text (which is identical-length to `masked`).
 */
function findNextBlock(
  masked: string,
  searchFrom: number,
): { openStart: number; openLineEnd: number; closeStart: number; closeLineEnd: number } | null {
  const openIdx = masked.indexOf(OPEN, searchFrom);
  if (openIdx === -1) return null;
  // Must be on its own line (whitespace-only).
  const openLineStart = lineStartAt(masked, openIdx);
  const openLineEnd = lineEndAt(masked, openIdx);
  if (!isLineWith(masked, openLineStart, openLineEnd, OPEN)) {
    // The `<<PROPOSAL` substring occurred in narrative prose; skip past
    // it and keep looking.
    return findNextBlock(masked, openIdx + OPEN.length);
  }
  // Find the next CLOSE on its own line, after the open line.
  let cursor = openLineEnd + 1;
  while (cursor < masked.length) {
    const closeIdx = masked.indexOf(CLOSE, cursor);
    if (closeIdx === -1) return null; // No close yet — partial.
    const closeLineStart = lineStartAt(masked, closeIdx);
    const closeLineEnd = lineEndAt(masked, closeIdx);
    if (isLineWith(masked, closeLineStart, closeLineEnd, CLOSE)) {
      return {
        openStart: openLineStart,
        openLineEnd: openLineEnd,
        closeStart: closeLineStart,
        closeLineEnd: closeLineEnd,
      };
    }
    cursor = closeLineEnd + 1;
  }
  return null;
}

function parseYamlBlock(rawYaml: string, index: number): ParsedProposal {
  let parsed: unknown;
  try {
    parsed = yaml.load(rawYaml);
  } catch (err) {
    return {
      index,
      tool: null,
      args: null,
      reason: null,
      ok: false,
      malformedReason: `YAML parse failed: ${(err as Error)?.message ?? "unknown"}`,
      rawYaml,
    };
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return {
      index,
      tool: null,
      args: null,
      reason: null,
      ok: false,
      malformedReason: "PROPOSAL body must be a YAML mapping",
      rawYaml,
    };
  }
  const obj = parsed as Record<string, unknown>;
  const tool = typeof obj.tool === "string" ? obj.tool : null;
  const args =
    obj.args && typeof obj.args === "object" && !Array.isArray(obj.args)
      ? (obj.args as Record<string, unknown>)
      : null;
  const reason = typeof obj.reason === "string" ? obj.reason : null;
  if (!tool || !args) {
    return {
      index,
      tool,
      args,
      reason,
      ok: false,
      malformedReason: "PROPOSAL missing required keys: tool, args",
      rawYaml,
    };
  }
  return {
    index,
    tool,
    args,
    reason,
    ok: true,
    rawYaml,
  };
}

/**
 * Parse the cumulative assistant text. Idempotent + order-preserving:
 * calling multiple times as new chunks stream in returns proposals in
 * the same order with stable indices.
 */
export function parseProposals(text: string): ParseResult {
  const masked = maskCodeFences(text);
  const proposals: ParsedProposal[] = [];
  // We build displayText by concatenating slices of the ORIGINAL text
  // in between matched blocks.
  let consumed = 0;
  let displayText = "";
  let pendingPartial = false;
  let nextIndex = 0;

  while (consumed < masked.length) {
    const block = findNextBlock(masked, consumed);
    if (block === null) {
      // No more complete blocks. Check if a partial open exists in the
      // remaining slice — if so, hide everything from that line onward
      // so the user doesn't see partial YAML.
      const remaining = masked.slice(consumed);
      const partialOpen = remaining.indexOf(OPEN);
      if (partialOpen !== -1) {
        // Verify it's on its own line (or at least starts a line).
        const absOpen = consumed + partialOpen;
        const lineStart = lineStartAt(masked, absOpen);
        const lineEnd = lineEndAt(masked, absOpen);
        // For a partial, the line might not be complete yet — accept
        // a "starts with `<<PROPOSAL`" line beginning.
        const lineSoFar = masked.slice(lineStart, lineEnd).trim();
        if (lineSoFar === OPEN || lineSoFar.startsWith(OPEN)) {
          displayText += text.slice(consumed, lineStart);
          pendingPartial = true;
          break;
        }
      }
      // Otherwise, take the rest verbatim.
      displayText += text.slice(consumed);
      break;
    }
    // Emit the prose between the previous consumed point and the
    // opening delimiter line.
    displayText += text.slice(consumed, block.openStart);
    // The YAML body sits between the open line and the close line,
    // exclusive.
    const yamlStart = block.openLineEnd + 1;
    const yamlEnd = block.closeStart;
    const rawYaml = text.slice(yamlStart, yamlEnd);
    proposals.push(parseYamlBlock(rawYaml, nextIndex));
    nextIndex += 1;
    // Skip past the close-line newline if present.
    consumed = block.closeLineEnd < masked.length ? block.closeLineEnd + 1 : block.closeLineEnd;
  }

  return { displayText, proposals, pendingPartial };
}

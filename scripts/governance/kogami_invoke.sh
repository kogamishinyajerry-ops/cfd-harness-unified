#!/usr/bin/env bash
# P-1.5 — Kogami subprocess wrapper.
# Per DEC-V61-087 §3.1, §3.4. Implements Tier 1 physical isolation:
#   --tools ""  --strict-mcp-config  --mcp-config <empty>
#   --exclude-dynamic-system-prompt-sections  --no-session-persistence
#   --output-format json  --max-turns 1  (or 2 on retry)
# + cd to fresh empty tmpdir (prevents project CLAUDE.md auto-discovery + git status leak)
# + stdin prompt (--mcp-config <configs...> is variadic; positional prompt is unsafe)
#
# Usage:
#   bash scripts/governance/kogami_invoke.sh \
#       <artifact_path> <topic_slug> [<trigger>]
#
# Outputs to .planning/reviews/kogami/<topic_slug>_<YYYY-MM-DD>/:
#   prompt.txt, briefing_manifest.json, prompt_sha256.txt   (from P-2)
#   review.json, review.md, invoke_meta.json                (from this wrapper)
#
# Exit codes:
#   0 = review committed (any verdict including INCONCLUSIVE)
#   1 = unrecoverable error (briefing failed, claude not installed, etc.)
#   2 = schema validation failed twice → review = INCONCLUSIVE (still exits 0; logs to stderr)

set -euo pipefail

ARTIFACT="${1:?usage: $0 <artifact_path> <topic_slug> [trigger]}"
TOPIC="${2:?usage: $0 <artifact_path> <topic_slug> [trigger]}"
TRIGGER="${3:-manual-invoke}"

DATE=$(date -u +%Y-%m-%d)
REPO_ROOT=$(git rev-parse --show-toplevel)
OUT_DIR="${REPO_ROOT}/.planning/reviews/kogami/${TOPIC}_${DATE}"
mkdir -p "$OUT_DIR"

# ─────────────────────────────────────────────────────────────────────
# Dependency-triggered Q1 canary (per DEC-V61-087 §3.6 + 项目"禁用日期/调度门控"原则)
# Trigger: claude CLI version change (NOT calendar). If `claude --version`
# differs from .planning/governance/claude_version_baseline.txt, run Q1 canary
# before allowing Kogami invocation. Canary fail → abort with Tier 2 escalation.
# ─────────────────────────────────────────────────────────────────────
BASELINE_FILE="${REPO_ROOT}/.planning/governance/claude_version_baseline.txt"
CURRENT_VERSION=$(claude --version 2>&1 | tr -d '\r\n')

if [[ ! -f "$BASELINE_FILE" ]]; then
    echo "[kogami] no version baseline yet — first-run canary required"
    NEED_CANARY=1
elif [[ "$(cat "$BASELINE_FILE" | tr -d '\r\n')" != "$CURRENT_VERSION" ]]; then
    echo "[kogami] claude CLI version change detected:"
    echo "  baseline: $(cat "$BASELINE_FILE")"
    echo "  current : $CURRENT_VERSION"
    echo "[kogami] dependency-triggered canary required"
    NEED_CANARY=1
else
    NEED_CANARY=0
fi

if [[ "$NEED_CANARY" == "1" ]]; then
    echo "[kogami] running Q1 canary regression test (5 runs)..."
    if python3 "${REPO_ROOT}/scripts/governance/verify_q1_canary.py" --runs 5; then
        echo "$CURRENT_VERSION" > "$BASELINE_FILE"
        echo "[kogami] Q1 canary PASS — baseline updated to: $CURRENT_VERSION"
    else
        echo "[kogami] ⛔ Q1 canary FAIL — Tier 2 escalation triggered (per DEC-V61-087 §3.6)"
        echo "[kogami] Refusing to invoke Kogami. Open an independent DEC for Tier 2 OS sandbox."
        exit 2
    fi
fi

EMPTY_CWD=$(mktemp -d /tmp/strategic_brief_cwd_XXXXXX)
EMPTY_MCP=$(mktemp /tmp/strategic_brief_mcp_XXXXXX.json)
echo '{"mcpServers": {}}' > "$EMPTY_MCP"

cleanup() { rm -rf "$EMPTY_CWD" "$EMPTY_MCP"; }
trap cleanup EXIT

echo "[kogami] artifact: $ARTIFACT"
echo "[kogami] topic: $TOPIC"
echo "[kogami] trigger: $TRIGGER"
echo "[kogami] output dir: $OUT_DIR"
echo "[kogami] empty cwd: $EMPTY_CWD"

# Step 1: P-2 builds the briefing
python3 "${REPO_ROOT}/scripts/governance/kogami_brief.py" \
    --artifact "$ARTIFACT" \
    --output-dir "$OUT_DIR" \
    --trigger "$TRIGGER"

PROMPT_FILE="$OUT_DIR/prompt.txt"
PROMPT_SHA=$(cat "$OUT_DIR/prompt_sha256.txt")

# Step 2: invoke Kogami subprocess (Tier 1 flag combo, runs in EMPTY_CWD)
invoke_once() {
    local max_turns="$1"
    cat "$PROMPT_FILE" | (cd "$EMPTY_CWD" && claude -p \
        --mcp-config "$EMPTY_MCP" \
        --tools "" \
        --strict-mcp-config \
        --exclude-dynamic-system-prompt-sections \
        --no-session-persistence \
        --output-format json \
        --max-turns "$max_turns")
}

extract_and_validate() {
    local raw="$1"
    # Extract .result string from envelope, then parse it as Kogami JSON
    local kogami_json
    kogami_json=$(echo "$raw" | jq -r '.result' 2>/dev/null) || return 2

    # Strip optional code fences if model wrapped in ```json ... ```
    kogami_json=$(echo "$kogami_json" | sed -E 's/^```json[[:space:]]*//' | sed -E 's/```[[:space:]]*$//')

    # Validate required fields
    echo "$kogami_json" | jq -e '
        (.verdict // empty) and
        (.summary // empty) and
        (.findings // empty | type == "array" or . == []) and
        (.strategic_assessment // empty) and
        (.recommended_next // empty)
    ' > /dev/null 2>&1 || return 3

    echo "$kogami_json"
    return 0
}

ATTEMPT=1
RAW_OUTPUT=""
KOGAMI_REVIEW=""
SCHEMA_OK=0

for max_turns in 1 2; do
    echo "[kogami] invoke attempt $ATTEMPT (max-turns=$max_turns) ..."
    RAW_OUTPUT=$(invoke_once "$max_turns" 2>&1) || true

    if KOGAMI_REVIEW=$(extract_and_validate "$RAW_OUTPUT"); then
        SCHEMA_OK=1
        echo "[kogami] schema validation PASSED on attempt $ATTEMPT"
        break
    fi
    echo "[kogami] schema validation FAILED on attempt $ATTEMPT, retrying ..."
    ATTEMPT=$((ATTEMPT + 1))
done

# Extract envelope metadata for invoke_meta.json
META=$(echo "$RAW_OUTPUT" | jq -c '{
    subtype, num_turns, duration_ms, total_cost_usd, stop_reason, terminal_reason, session_id, uuid,
    model_keys: (.modelUsage | keys),
    cache_creation_tokens: .usage.cache_creation_input_tokens,
    cache_read_tokens: .usage.cache_read_input_tokens,
    output_tokens: .usage.output_tokens
}' 2>/dev/null || echo '{"_meta_extract_failed": true}')

INVOKE_META=$(jq -n \
    --arg attempt "$ATTEMPT" \
    --arg schema_ok "$SCHEMA_OK" \
    --arg prompt_sha "$PROMPT_SHA" \
    --arg empty_cwd "$EMPTY_CWD" \
    --arg trigger "$TRIGGER" \
    --arg artifact "$ARTIFACT" \
    --arg date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson envelope "$META" \
    '{
        wrapper_version: "1.0",
        attempt: ($attempt | tonumber),
        schema_ok: ($schema_ok == "1"),
        prompt_sha256: $prompt_sha,
        empty_cwd: $empty_cwd,
        trigger: $trigger,
        artifact: $artifact,
        invoked_at_utc: $date,
        envelope: $envelope
    }')

echo "$INVOKE_META" > "$OUT_DIR/invoke_meta.json"

if [[ "$SCHEMA_OK" == "0" ]]; then
    # Two failures → INCONCLUSIVE per DEC §3.4
    echo "[kogami] both attempts failed schema validation → review = INCONCLUSIVE"
    INCONCLUSIVE_REVIEW=$(jq -n \
        --arg reason "schema_validation_failed_2x" \
        --arg raw_head "$(echo "$RAW_OUTPUT" | head -c 400)" \
        '{
            verdict: "INCONCLUSIVE",
            summary: "Subprocess output did not satisfy schema after 2 attempts. Review marked INCONCLUSIVE per DEC-V61-087 §3.4.",
            findings: [],
            strategic_assessment: "Cannot assess; subprocess output unparseable.",
            recommended_next: "escalate-to-user-discussion",
            _meta: { reason: $reason, raw_output_head: $raw_head }
        }')
    echo "$INCONCLUSIVE_REVIEW" > "$OUT_DIR/review.json"
else
    echo "$KOGAMI_REVIEW" > "$OUT_DIR/review.json"
fi

# Render review.md (human-readable)
python3 - <<PY > "$OUT_DIR/review.md"
import json, sys
r = json.load(open("$OUT_DIR/review.json"))
print(f"# Kogami Review · ${TOPIC} · ${DATE}")
print()
print(f"**Verdict**: \`{r.get('verdict','?')}\`")
print(f"**Recommended next**: \`{r.get('recommended_next','?')}\`")
print(f"**Trigger**: ${TRIGGER}")
print(f"**Artifact**: \`${ARTIFACT}\`")
print(f"**Prompt SHA256**: \`${PROMPT_SHA}\`")
print()
print("## Summary")
print()
print(r.get("summary", "(empty)"))
print()
print("## Strategic Assessment")
print()
print(r.get("strategic_assessment", "(empty)"))
print()
print("## Findings")
print()
findings = r.get("findings", [])
if not findings:
    print("_No findings._")
else:
    for f in findings:
        print(f"### [{f.get('severity','?')}] {f.get('title','(no title)')}")
        print(f"**Position**: {f.get('position','?')}")
        print()
        print(f"**Problem**: {f.get('problem','(empty)')}")
        print()
        print(f"**Recommendation**: {f.get('recommendation','(empty)')}")
        print()
PY

VERDICT=$(jq -r '.verdict' "$OUT_DIR/review.json")
echo
echo "[kogami] verdict: $VERDICT"
echo "[kogami] review JSON: $OUT_DIR/review.json"
echo "[kogami] review MD:   $OUT_DIR/review.md"
echo "[kogami] invoke meta: $OUT_DIR/invoke_meta.json"
echo "[kogami] briefing:    $OUT_DIR/prompt.txt + briefing_manifest.json + prompt_sha256.txt"
exit 0

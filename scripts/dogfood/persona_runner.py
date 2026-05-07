"""Single-persona run driver for the B-arc dogfood harness.

Drives an LLM tool-use loop:
  1. Send case brief + system prompt.
  2. Receive AssistantMessage (text + tool_calls).
  3. Execute each tool_call via WorkbenchToolExecutor.
  4. Append tool result to the conversation; repeat until the model
     emits a final `submit_verdict` tool call (terminal) or budget
     caps trip.

B.1 ships a stub system prompt; B.2 fills the real persona library.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from scripts.dogfood.case_brief import CaseBrief, VerdictResult, check_verdict
from scripts.dogfood.friction_log import FrictionLog
from scripts.dogfood.llm_clients import (
    AssistantMessage,
    LLMClient,
    ToolCall,
    ToolDef,
)
from scripts.dogfood.workbench_tools import (
    WorkbenchToolExecutor,
    workbench_tool_defs,
)

logger = logging.getLogger(__name__)


_STUB_SYSTEM_PROMPT = (
    "You are a CFD engineer driving the cfd-harness-unified workbench through "
    "its 5-step workflow (geometry → mesh → physics → BC → solver) to answer "
    "the question in the case brief. Use only the http_get and http_post tools "
    "exposed to you; do not reference files, shells, or local processes. The "
    "AI advisor (GET /api/cases/{id}/ai-review and /ai-diagnose) is read-only "
    "and ADVISORY — YOU as the engineer decide whether to apply any change. "
    "Never explain a mutation as 'the AI told me to'. When you have an answer "
    "for the case's reference metric, call submit_verdict with the observed "
    "value and a short rationale. If you cannot proceed, call submit_drop "
    "with a reason. Persona prompts will be expanded in B.2."
)


_VERDICT_TOOL = ToolDef(
    name="submit_verdict",
    description=(
        "Terminal tool: report your observed value for the case's reference "
        "metric. The harness machine-checks observed against reference ± tolerance."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "observed_value": {"type": "number", "description": "Numerical value for the brief's reference metric"},
            "rationale": {"type": "string", "description": "How you arrived at this value"},
        },
        "required": ["observed_value", "rationale"],
    },
)


_DROP_TOOL = ToolDef(
    name="submit_drop",
    description="Terminal tool: declare you cannot complete the case and explain why.",
    input_schema={
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Why you are dropping the case"},
        },
        "required": ["reason"],
    },
)


@dataclass
class PersonaConfig:
    """Identifies a persona run."""

    persona_name: str
    family: str  # anthropic | deepseek | openai_compat
    model_id: str
    system_prompt: str = _STUB_SYSTEM_PROMPT
    max_steps: int = 30
    max_input_tokens: int = 200_000
    max_output_tokens: int = 4096
    # B-ext.1 / DEC-V61-173 (F6) — conversation pruning controls.
    # Keep the last `prune_keep_full` assistant+tool_result turn-pairs
    # in full; older tool_result blocks get content compressed to a
    # one-liner. The initial user brief is always preserved.
    # Set keep_full=0 to disable pruning (legacy behavior).
    prune_keep_full: int = 6
    prune_min_turns_before_active: int = 4


def _prune_messages(
    messages: list[dict[str, Any]],
    *,
    keep_full: int,
    min_turns_before_active: int,
) -> list[dict[str, Any]]:
    """Compress tool_result content for older turns to control token growth.

    Strategy:
    - The initial user message (case brief) is always preserved verbatim.
    - The last `keep_full` `(assistant, user_tool_results)` pairs are
      preserved verbatim.
    - Earlier `tool_result` blocks have their `content` field replaced
      with a one-liner stub: `[pruned: tool_use_id=... · is_error=False]`.
      The persona still sees the call/response existed but doesn't
      carry the body in context.
    - Older `assistant` text+tool_use blocks are kept (they're small;
      they document persona decisions).

    No-op if pruning is disabled or the conversation is short enough.
    """
    if keep_full <= 0 or len(messages) <= min_turns_before_active:
        return messages

    # Find indices of "user" messages that contain tool_result blocks.
    # The initial brief is index 0 (or the first 'user' string-content
    # message), which we preserve.
    pruneable_user_indices: list[int] = []
    for i, msg in enumerate(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        if any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        ):
            pruneable_user_indices.append(i)

    if len(pruneable_user_indices) <= keep_full:
        return messages

    cutoff_idx = pruneable_user_indices[-keep_full]
    pruned: list[dict[str, Any]] = []
    for i, msg in enumerate(messages):
        if i >= cutoff_idx or msg.get("role") != "user" or not isinstance(
            msg.get("content"), list
        ):
            pruned.append(msg)
            continue
        content = msg["content"]
        if not any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        ):
            pruned.append(msg)
            continue
        # Compress tool_result content
        new_blocks: list[dict[str, Any]] = []
        for b in content:
            if not isinstance(b, dict):
                new_blocks.append(b)
                continue
            if b.get("type") == "tool_result":
                tool_use_id = b.get("tool_use_id", "")
                is_error = bool(b.get("is_error"))
                stub = (
                    f"[pruned for context · tool_use_id={tool_use_id} · "
                    f"is_error={is_error}]"
                )
                new_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": stub,
                        "is_error": is_error,
                    }
                )
            else:
                new_blocks.append(b)
        pruned.append({"role": "user", "content": new_blocks})
    return pruned


@dataclass
class RunResult:
    """Outcome of one persona run."""

    run_id: str
    case_id: str
    persona: str
    model_id: str
    steps: int
    verdict: VerdictResult | None
    dropped: bool
    drop_reason: str | None
    total_input_tokens: int
    total_output_tokens: int
    error: str | None = None
    transcript: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "persona": self.persona,
            "model_id": self.model_id,
            "steps": self.steps,
            "verdict": self.verdict.to_dict() if self.verdict else None,
            "dropped": self.dropped,
            "drop_reason": self.drop_reason,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "error": self.error,
        }


def _build_user_messages(brief: CaseBrief) -> list[dict[str, Any]]:
    """Initial conversation: persona receives the structured brief."""
    return [
        {
            "role": "user",
            "content": (
                "Here is the case brief. Drive the workbench to answer the "
                "question and call submit_verdict when ready.\n\n"
                + brief.to_persona_text()
            ),
        }
    ]


def _record_tool_use(
    log: FrictionLog,
    call: ToolCall,
    *,
    rationale: str,
) -> None:
    log.emit(
        "tool_use",
        tool_name=call.tool_name,
        call_id=call.call_id,
        arguments=call.arguments,
        rationale=rationale,
    )


def _terminal_call(call: ToolCall) -> str | None:
    if call.tool_name in {"submit_verdict", "submit_drop"}:
        return call.tool_name
    return None


def run_persona(
    *,
    config: PersonaConfig,
    brief: CaseBrief,
    client: LLMClient,
    log: FrictionLog,
    executor: WorkbenchToolExecutor,
) -> RunResult:
    """Drive one persona × case run end-to-end.

    Returns a RunResult; the friction log captures the full event trail.
    """
    tools: list[ToolDef] = [*workbench_tool_defs(), _VERDICT_TOOL, _DROP_TOOL]
    messages = _build_user_messages(brief)

    transcript: list[dict[str, Any]] = []
    total_in = 0
    total_out = 0
    verdict_result: VerdictResult | None = None
    dropped = False
    drop_reason: str | None = None
    error: str | None = None

    step = 0
    for step in range(1, config.max_steps + 1):
        outbound_messages = _prune_messages(
            messages,
            keep_full=config.prune_keep_full,
            min_turns_before_active=config.prune_min_turns_before_active,
        )
        if outbound_messages is not messages and len(outbound_messages) == len(
            messages
        ):
            log.emit(
                "decision",
                step=step,
                detail=(
                    f"conversation pruned: keep_full={config.prune_keep_full} "
                    f"turn_pairs (F6)"
                ),
            )
        try:
            response: AssistantMessage = client.chat(
                system=config.system_prompt,
                messages=outbound_messages,
                tools=tools,
                max_tokens=config.max_output_tokens,
            )
        except Exception as exc:  # pragma: no cover - network paths
            error = f"llm_chat_failed: {exc!s}"
            log.emit("error", phase="llm_chat", detail=error)
            break

        usage = response.raw_usage or {}
        total_in += int(usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or 0)
        total_out += int(usage.get("output_tokens", 0) or usage.get("completion_tokens", 0) or 0)

        transcript.append(
            {
                "step": step,
                "assistant_text": response.text,
                "tool_calls": [
                    {"name": c.tool_name, "args": c.arguments} for c in response.tool_calls
                ],
            }
        )

        if not response.tool_calls:
            log.emit(
                "decision",
                step=step,
                detail="model returned text without tool calls; treated as drop",
                text=response.text[:1000],
            )
            dropped = True
            drop_reason = "no_tool_call"
            break

        # Append assistant message with tool_use blocks (Anthropic-shaped;
        # OpenAI-compat clients also accept this generic shape via our
        # tool_calls list — both providers ignore unknown fields).
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": response.text},
                    *[
                        {
                            "type": "tool_use",
                            "id": c.call_id or f"call_{step}_{i}",
                            "name": c.tool_name,
                            "input": c.arguments,
                        }
                        for i, c in enumerate(response.tool_calls)
                    ],
                ],
            }
        )

        terminal_seen: str | None = None
        tool_results_block: list[dict[str, Any]] = []
        for call in response.tool_calls:
            rationale = str(call.arguments.get("rationale", ""))
            _record_tool_use(log, call, rationale=rationale)

            terminal = _terminal_call(call)
            if terminal == "submit_verdict":
                observed_raw = call.arguments.get("observed_value")
                try:
                    observed = float(observed_raw) if observed_raw is not None else None
                except (TypeError, ValueError):
                    observed = None
                verdict_result = check_verdict(brief, observed)
                log.emit(
                    "verdict",
                    observed=observed,
                    passed=verdict_result.passed,
                    detail=verdict_result.detail,
                    rationale=str(call.arguments.get("rationale", "")),
                )
                terminal_seen = terminal
                break
            if terminal == "submit_drop":
                dropped = True
                drop_reason = str(call.arguments.get("reason", "unspecified"))
                log.emit("drop", reason=drop_reason)
                terminal_seen = terminal
                break

            # Non-terminal tool: execute against workbench
            tool_result = executor.execute(call)
            log.emit(
                "api_call",
                method=(
                    "GET" if call.tool_name == "http_get"
                    else "PUT" if call.tool_name == "http_put"
                    else "POST"
                ),
                url=str(call.arguments.get("url", "")),
                status=tool_result.status,
                ok=tool_result.ok,
                truncated_at_bytes=tool_result.truncated_at_bytes,
                error=tool_result.error,
                rationale=rationale,
            )
            tool_results_block.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.call_id or "",
                    "content": json.dumps(tool_result.to_message_payload(), ensure_ascii=False),
                    "is_error": not tool_result.ok,
                }
            )

        if terminal_seen is not None:
            break

        if tool_results_block:
            messages.append({"role": "user", "content": tool_results_block})

        if total_in >= config.max_input_tokens:
            log.emit(
                "budget_check",
                phase="input_tokens",
                total_in=total_in,
                cap=config.max_input_tokens,
                exceeded=True,
            )
            error = "input_token_budget_exceeded"
            break

    if step == config.max_steps and verdict_result is None and not dropped and error is None:
        log.emit("budget_check", phase="max_steps", steps=step, exceeded=True)
        error = "max_steps_reached"

    return RunResult(
        run_id=log.run_id,
        case_id=brief.case_id,
        persona=config.persona_name,
        model_id=config.model_id,
        steps=step,
        verdict=verdict_result,
        dropped=dropped,
        drop_reason=drop_reason,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        error=error,
        transcript=transcript,
    )


__all__ = ["PersonaConfig", "RunResult", "run_persona"]

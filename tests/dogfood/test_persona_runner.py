"""Tests for scripts/dogfood/persona_runner.py — tool-use loop with mock LLM."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from scripts.dogfood.case_brief import CaseBrief, Reference
from scripts.dogfood.friction_log import FrictionLog, grep_events, read_log
from scripts.dogfood.llm_clients import (
    AssistantMessage,
    LLMClient,
    ToolCall,
    ToolDef,
)
from scripts.dogfood.persona_runner import PersonaConfig, run_persona
from scripts.dogfood.workbench_tools import WorkbenchToolExecutor


def _brief() -> CaseBrief:
    return CaseBrief(
        case_id="c1",
        title="t",
        geometry="g",
        physics={},
        question="q",
        reference=Reference(
            metric="m", value=1.0, tolerance=0.05, tolerance_kind="rel", source="s"
        ),
    )


class _ScriptedClient:
    """Replays a fixed list of AssistantMessages."""

    def __init__(self, model_id: str, scripted: list[AssistantMessage]) -> None:
        self.model_id = model_id
        self._scripted = list(scripted)
        self._idx = 0
        self.calls: list[dict[str, Any]] = []

    def chat(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> AssistantMessage:
        self.calls.append({"system": system, "n_messages": len(messages)})
        if self._idx >= len(self._scripted):
            return AssistantMessage(
                text="(exhausted)",
                tool_calls=(),
                raw_usage={"input_tokens": 0, "output_tokens": 0},
            )
        msg = self._scripted[self._idx]
        self._idx += 1
        return msg


def _executor() -> WorkbenchToolExecutor:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/api/cases/c1/state":
            return httpx.Response(200, json={"step": "geometry"})
        return httpx.Response(404, json={"error": "not found"})

    return WorkbenchToolExecutor(
        client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="http://localhost:8000",
        )
    )


def test_runner_passes_verdict_branch(tmp_path: Path) -> None:
    scripted = [
        AssistantMessage(
            text="checking state",
            tool_calls=(
                ToolCall(
                    call_id="t1",
                    tool_name="http_get",
                    arguments={"url": "/api/cases/c1/state", "rationale": "verify"},
                ),
            ),
            raw_usage={"input_tokens": 10, "output_tokens": 5},
        ),
        AssistantMessage(
            text="submitting",
            tool_calls=(
                ToolCall(
                    call_id="t2",
                    tool_name="submit_verdict",
                    arguments={"observed_value": 1.02, "rationale": "computed via post"},
                ),
            ),
            raw_usage={"input_tokens": 15, "output_tokens": 5},
        ),
    ]
    client: LLMClient = _ScriptedClient("claude-sonnet-4-6", scripted)
    log_path = tmp_path / "fl.jsonl"
    executor = _executor()
    config = PersonaConfig(
        persona_name="novice", family="anthropic", model_id="claude-sonnet-4-6"
    )
    with FrictionLog(
        path=log_path,
        run_id="r",
        case_id="c1",
        persona="novice",
        model_id="claude-sonnet-4-6",
    ) as log:
        result = run_persona(
            config=config, brief=_brief(), client=client, log=log, executor=executor
        )
    executor.close()

    assert result.verdict is not None
    assert result.verdict.passed is True
    assert result.dropped is False
    assert result.steps == 2
    events = read_log(log_path)
    api = grep_events(events, "api_call")
    verdict = grep_events(events, "verdict")
    tool_use = grep_events(events, "tool_use")
    assert len(api) == 1
    assert api[0]["url"] == "/api/cases/c1/state"
    assert api[0]["rationale"] == "verify"
    assert len(verdict) == 1
    assert verdict[0]["passed"] is True
    # tool_use captures every call (http_get + submit_verdict)
    assert len(tool_use) >= 2


def test_runner_drop_branch(tmp_path: Path) -> None:
    scripted = [
        AssistantMessage(
            text="cant do",
            tool_calls=(
                ToolCall(
                    call_id="t1",
                    tool_name="submit_drop",
                    arguments={"reason": "STL import failed"},
                ),
            ),
            raw_usage={"input_tokens": 5, "output_tokens": 2},
        ),
    ]
    client: LLMClient = _ScriptedClient("deepseek-chat", scripted)
    executor = _executor()
    config = PersonaConfig(
        persona_name="debug", family="deepseek", model_id="deepseek-chat"
    )
    with FrictionLog(
        path=tmp_path / "fl.jsonl",
        run_id="r",
        case_id="c1",
        persona="debug",
        model_id="deepseek-chat",
    ) as log:
        result = run_persona(
            config=config, brief=_brief(), client=client, log=log, executor=executor
        )
    executor.close()
    assert result.verdict is None
    assert result.dropped is True
    assert "STL" in (result.drop_reason or "")


def test_runner_stops_at_max_steps(tmp_path: Path) -> None:
    scripted = [
        AssistantMessage(
            text=f"step{i}",
            tool_calls=(
                ToolCall(
                    call_id=f"t{i}",
                    tool_name="http_get",
                    arguments={"url": "/api/cases/c1/state", "rationale": "loop"},
                ),
            ),
            raw_usage={"input_tokens": 1, "output_tokens": 1},
        )
        for i in range(20)
    ]
    client: LLMClient = _ScriptedClient("gpt-5.4", scripted)
    executor = _executor()
    config = PersonaConfig(
        persona_name="exp", family="openai_compat", model_id="gpt-5.4", max_steps=3
    )
    with FrictionLog(
        path=tmp_path / "fl.jsonl",
        run_id="r",
        case_id="c1",
        persona="exp",
        model_id="gpt-5.4",
    ) as log:
        result = run_persona(
            config=config, brief=_brief(), client=client, log=log, executor=executor
        )
    executor.close()
    assert result.verdict is None
    assert result.dropped is False
    assert result.error == "max_steps_reached"
    assert result.steps == 3


def test_runner_no_tool_call_treated_as_drop(tmp_path: Path) -> None:
    scripted = [
        AssistantMessage(
            text="I have no idea",
            tool_calls=(),
            raw_usage={"input_tokens": 1, "output_tokens": 1},
        )
    ]
    client: LLMClient = _ScriptedClient("claude-sonnet-4-6", scripted)
    executor = _executor()
    config = PersonaConfig(
        persona_name="novice", family="anthropic", model_id="claude-sonnet-4-6"
    )
    with FrictionLog(
        path=tmp_path / "fl.jsonl",
        run_id="r",
        case_id="c1",
        persona="novice",
        model_id="claude-sonnet-4-6",
    ) as log:
        result = run_persona(
            config=config, brief=_brief(), client=client, log=log, executor=executor
        )
    executor.close()
    assert result.dropped is True
    assert result.drop_reason == "no_tool_call"

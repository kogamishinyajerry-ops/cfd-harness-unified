"""B-arc dogfood harness CLI entry.

Usage:
    python -m scripts.dogfood.harness --selftest
    python -m scripts.dogfood.harness \
        --case cases/naca0012.json \
        --persona experienced_fluent \
        --family openai_compat --model gpt-5.4 \
        --run-id <uuid>

B.1 ships `--selftest` (mock-LLM smoke against stubbed workbench, no
keys required) + the production CLI shape. B.2 fills personas; B.3
fills cases.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from scripts.dogfood.case_brief import CaseBrief, Reference, load_brief
from scripts.dogfood.friction_log import FrictionLog
from scripts.dogfood.llm_clients import (
    AssistantMessage,
    LLMClient,
    ToolCall,
    ToolDef,
    assert_non_opus,
    build_client,
)
from scripts.dogfood.persona_runner import PersonaConfig, run_persona
from scripts.dogfood.workbench_tools import WorkbenchToolExecutor

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )


def _runs_dir(base: Path | None = None) -> Path:
    base = base or Path(".planning/dogfood/runs")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _resolve_run_id(arg: str | None) -> str:
    return arg or uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Selftest scaffolding (mock LLM + mock workbench)
# ---------------------------------------------------------------------------


class _ScriptedMockClient:
    """LLMClient stand-in that replays a pre-recorded sequence of responses.

    Used for `--selftest` to verify the harness end-to-end without
    requiring API keys or network access.
    """

    def __init__(self, model_id: str, scripted: list[AssistantMessage]) -> None:
        assert_non_opus(model_id)
        self.model_id = model_id
        self._scripted = list(scripted)
        self._idx = 0

    def chat(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> AssistantMessage:
        if self._idx >= len(self._scripted):
            return AssistantMessage(
                text="(scripted exhausted)",
                tool_calls=(),
                raw_usage={"input_tokens": 0, "output_tokens": 0},
            )
        msg = self._scripted[self._idx]
        self._idx += 1
        return msg


class _MockWorkbenchTransport:
    """httpx transport that returns canned responses for selftest."""

    def __init__(self) -> None:
        import httpx

        def _handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/cases/selftest/state":
                return httpx.Response(
                    200,
                    json={"case_id": "selftest", "step": "geometry", "completeness": 0.0},
                )
            return httpx.Response(404, json={"error": "not found"})

        self._transport = httpx.MockTransport(_handler)

    def as_client(self) -> "httpx.Client":
        import httpx

        return httpx.Client(transport=self._transport, base_url="http://localhost:8000")


def _selftest_brief() -> CaseBrief:
    return CaseBrief(
        case_id="selftest",
        title="Harness selftest fixture",
        geometry="(stub) cube",
        physics={"regime": "incompressible_steady"},
        question="What is the harness's selftest reference value?",
        reference=Reference(
            metric="selftest_value",
            value=1.0,
            tolerance=0.05,
            tolerance_kind="rel",
            source="harness selftest fixture",
        ),
        notes="Selftest only; not a real CFD case.",
    )


def _selftest_run(out_dir: Path) -> int:
    brief = _selftest_brief()
    run_id = _resolve_run_id(None)
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "friction_log.jsonl"

    scripted = [
        AssistantMessage(
            text="Querying case state to confirm starting position.",
            tool_calls=(
                ToolCall(
                    call_id="call_1",
                    tool_name="http_get",
                    arguments={
                        "url": "/api/cases/selftest/state",
                        "rationale": "verify selftest case is reachable",
                    },
                ),
            ),
            raw_usage={"input_tokens": 100, "output_tokens": 20},
        ),
        AssistantMessage(
            text="Submitting verdict.",
            tool_calls=(
                ToolCall(
                    call_id="call_2",
                    tool_name="submit_verdict",
                    arguments={
                        "observed_value": 1.0,
                        "rationale": "selftest fixture produces the reference value",
                    },
                ),
            ),
            raw_usage={"input_tokens": 110, "output_tokens": 5},
        ),
    ]

    client: LLMClient = _ScriptedMockClient("scripted-mock", scripted)
    transport = _MockWorkbenchTransport().as_client()
    executor = WorkbenchToolExecutor(client=transport)

    config = PersonaConfig(
        persona_name="selftest",
        family="mock",
        model_id="scripted-mock",
        max_steps=5,
    )

    with FrictionLog(
        path=log_path,
        run_id=run_id,
        case_id=brief.case_id,
        persona=config.persona_name,
        model_id=config.model_id,
    ) as log:
        result = run_persona(
            config=config,
            brief=brief,
            client=client,
            log=log,
            executor=executor,
        )

    executor.close()
    transport.close()

    (run_dir / "result.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Selftest run_id={run_id}")
    print(f"  log: {log_path}")
    print(f"  verdict.passed: {result.verdict.passed if result.verdict else None}")
    if not result.verdict or not result.verdict.passed:
        print(f"  detail: {result.verdict.detail if result.verdict else result.error}")
        return 1
    return 0


# ---------------------------------------------------------------------------
# Production CLI path
# ---------------------------------------------------------------------------


def _production_run(args: argparse.Namespace) -> int:
    if args.case is None or args.persona is None or args.family is None or args.model is None:
        print("Production run requires --case --persona --family --model", file=sys.stderr)
        return 2
    brief = load_brief(Path(args.case))
    run_id = _resolve_run_id(args.run_id)
    runs_root = _runs_dir(Path(args.runs_dir) if args.runs_dir else None)
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "friction_log.jsonl"

    client = build_client(args.family, args.model)
    executor = WorkbenchToolExecutor(base_url=args.workbench_base_url)

    config = PersonaConfig(
        persona_name=args.persona,
        family=args.family,
        model_id=args.model,
        max_steps=args.max_steps,
    )

    with FrictionLog(
        path=log_path,
        run_id=run_id,
        case_id=brief.case_id,
        persona=config.persona_name,
        model_id=config.model_id,
    ) as log:
        result = run_persona(
            config=config,
            brief=brief,
            client=client,
            log=log,
            executor=executor,
        )

    executor.close()
    if hasattr(client, "close"):
        client.close()  # type: ignore[attr-defined]

    (run_dir / "result.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if (result.verdict and result.verdict.passed) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B-arc dogfood harness")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--case", type=str, help="Path to case brief JSON")
    parser.add_argument("--persona", type=str)
    parser.add_argument(
        "--family",
        type=str,
        choices=["anthropic", "deepseek", "openai_compat"],
    )
    parser.add_argument("--model", type=str)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument(
        "--workbench-base-url",
        type=str,
        default="http://localhost:8000",
    )
    parser.add_argument("--runs-dir", type=str, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    if args.selftest:
        with tempfile.TemporaryDirectory() as tmp:
            return _selftest_run(Path(tmp))

    return _production_run(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

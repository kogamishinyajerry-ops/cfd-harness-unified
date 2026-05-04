"""DEC-V61-119 · LLM-wrapped completeness coaching (SSE streaming).
DEC-V61-121 · AI coach action proposals (apply-proposal route).

POST /api/ai-coach/stream — pre-fetches the case completeness report,
composes a governance-aware system prompt, then streams an LLM
completion frame-by-frame as SSE events.

POST /api/ai-coach/apply-proposal — V61-121 dispatcher that takes a
proposal the user [Accepted] in the chat panel UI, validates the
tool against the registry, applies it via the V108-style service
layer, writes an audit entry, and returns the apply result.

Wire format (one SSE event per JSON line):
    data: {"delta":"...","done":false,"model_used":"deepseek-v4-pro"}
    ...
    data: {"delta":"","done":true,"usage":{...},"model_used":"..."}

On mid-stream upstream failure, the route emits a final
``data: {"error":"<class>","detail":"..."}`` event then closes. Status
codes BEFORE the stream opens follow the same mapping as
``/api/ai-chat`` (401/403/429/4xx/5xx → typed HTTP error). Once the
stream has opened, the route returns 200 even if the underlying LLM
call fails — the failure is delivered as the terminal SSE event.

Security: shares the loopback guard with ``ai_chat`` via
:mod:`._loopback_guard`. Same env-var override.

Per DEC-V61-119 §V1 explicit scope-down: NO LLM-side tool calling,
NO mid-stream fallback, NO SSE reconnect. Single request scope.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ui.backend.routes._loopback_guard import require_loopback
from ui.backend.services.case_completeness import (
    CaseNotFoundError,
    analyze_case_completeness,
)
from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import IMPORTED_DIR
from ui.backend.services.mesh_quality import (
    MeshQualityNotAvailableError,
    MeshQualityParseError,
    MeshQualityReport,
    analyze_mesh_quality,
)
from ui.backend.services.llm_coach import (
    AuditWriteError,
    ToolArgError,
    ToolDispatchError,
    UnknownToolError,
    build_coach_system_prompt,
    dispatch as dispatch_tool,
    write_audit,
)
from ui.backend.services.llm_provider import (
    ChatMessage,
    ChatRequest,
    LLMAuthError,
    LLMBadRequestError,
    LLMConfigError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
    get_default_provider,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ────────── Request schema ──────────


_DEFAULT_MODEL = "deepseek-v4-pro"


class CoachHistoryMessage(BaseModel):
    """One prior turn in the coaching conversation. Restricted to
    user/assistant — the system message is OWNED by the route handler
    (composed from completeness + project rules) and cannot be set
    by the caller."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(min_length=1)

    @field_validator("role")
    @classmethod
    def _role_subset(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("history role must be 'user' or 'assistant'")
        return v


class CoachStreamRequest(BaseModel):
    """Inbound request. ``case_id`` is REQUIRED so the analyzer can
    pre-fetch the snapshot. ``user_message`` is the engineer's current
    turn. ``history`` is the prior conversation; the route appends
    ``user_message`` as the final user turn before opening the stream."""

    case_id: str = Field(min_length=1, max_length=128)
    user_message: str = Field(min_length=1, max_length=8192)
    history: list[CoachHistoryMessage] = Field(default_factory=list, max_length=32)
    model: str = _DEFAULT_MODEL
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)


# ────────── Stream event helpers ──────────


def _sse_event(payload: dict) -> str:
    """Serialize one SSE event. Single-line JSON, no event names —
    keeps the wire format minimal per DEC §V1 explicit scope-down."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ────────── Route ──────────


@router.post("/ai-coach/stream")
async def ai_coach_stream(
    body: CoachStreamRequest, http_request: Request
) -> StreamingResponse:
    """Open an SSE stream coaching the engineer through their case.

    Status code mapping (BEFORE the stream opens):
      * 200 → stream opened (mid-stream errors emit a final SSE error event)
      * 400 → invalid request body (Pydantic returns 422 on schema errors)
      * 403 → non-loopback caller without override
      * 404 → case_id resolves to nothing
      * 502 → completeness analyzer crashed on this case
      * 500 → unexpected
    """
    require_loopback(http_request, route_label="/api/ai-coach/stream")

    # Pre-fetch SYNCHRONOUSLY before opening the stream so a 404 on
    # case_id surfaces as a clean HTTP 404, not as a stream that
    # immediately errors. Acceptable latency: the analyzer is in-memory
    # file reads (~50-200ms typical).
    try:
        report = analyze_case_completeness(body.case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"case_id={body.case_id!r} not found",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — analyzer crash mapped to 502
        logger.exception("Completeness analyzer crashed for case_id=%r", body.case_id)
        raise HTTPException(
            status_code=502,
            detail=f"Completeness analyzer error: {type(exc).__name__}",
        ) from exc

    # DEC-V61-122: best-effort fetch the mesh-quality report so the
    # AI can ground answers in the actual polyMesh state when the
    # case has been meshed. Missing polyMesh is a normal pre-mesh
    # state — log debug, prompt skips the section. Parse errors are
    # logged but do NOT abort the chat — the engineer's coaching
    # continues without mesh data.
    mesh_quality_report: MeshQualityReport | None = None
    if is_safe_case_id(body.case_id):
        case_dir = IMPORTED_DIR / body.case_id
        if case_dir.is_dir():
            try:
                mesh_quality_report = analyze_mesh_quality(case_dir)
            except MeshQualityNotAvailableError:
                # Pre-mesh case state — expected, no log noise.
                pass
            except MeshQualityParseError as exc:
                logger.warning(
                    "mesh-quality parse failed for case_id=%r failing_check=%s; "
                    "proceeding without mesh section in coach prompt",
                    body.case_id,
                    exc.failing_check,
                )

    system_prompt = build_coach_system_prompt(
        report, mesh_quality_report=mesh_quality_report
    )

    # Build the LLM ChatRequest. The system message is OWNED by the
    # route — caller cannot inject (CoachHistoryMessage validator
    # rejects role='system').
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system_prompt)
    ]
    for turn in body.history:
        messages.append(ChatMessage(role=turn.role, content=turn.content))  # type: ignore[arg-type]
    messages.append(ChatMessage(role="user", content=body.user_message))

    # Validate the model name against the LLMProvider's allowed set
    # by constructing the ChatRequest. Pydantic will raise on an
    # unknown literal — surface that as 400.
    try:
        chat_req = ChatRequest(
            messages=messages,
            model=body.model,  # type: ignore[arg-type]
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid LLM request: {exc}",
        ) from exc

    provider = get_default_provider()

    # Codex R1 P1: peek the first chunk BEFORE committing the
    # StreamingResponse. If the upstream rejects the request
    # pre-stream-open (bad key, 429, oversized payload, 5xx) the
    # provider's chat_stream raises a typed exception on the very
    # first __anext__. We map those to HTTP status codes per the
    # documented contract, mirroring /api/ai-chat. Only mid-stream
    # failures — i.e. after the first chunk has already been
    # received — are surfaced as SSE error frames (the response
    # status is already committed to 200 at that point).
    stream_iter = provider.chat_stream(chat_req)
    try:
        first_chunk = await stream_iter.__anext__()
    except StopAsyncIteration:
        # Empty stream — synthesize a single done frame so the
        # client still sees a terminal event.
        first_chunk = None
    except LLMAuthError as exc:
        logger.error("AI coach auth error (pre-stream): %s", exc)
        raise HTTPException(
            status_code=401,
            detail="LLM provider authentication failed; check DEEPSEEK_API_KEY",
        ) from exc
    except LLMRateLimitError as exc:
        logger.warning("AI coach rate-limited (pre-stream): %s", exc)
        raise HTTPException(
            status_code=429,
            detail="LLM provider rate-limited; please retry shortly",
        ) from exc
    except LLMBadRequestError as exc:
        logger.warning("AI coach bad request (pre-stream): %s", exc)
        raise HTTPException(
            status_code=400,
            detail=(
                "LLM provider rejected the request "
                "(likely oversized or malformed payload); adjust and retry"
            ),
        ) from exc
    except (LLMUpstreamError, LLMTimeoutError) as exc:
        logger.error("AI coach upstream error (pre-stream): %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider unavailable: {exc.__class__.__name__}",
        ) from exc
    except LLMConfigError as exc:
        logger.error("AI coach config error (pre-stream): %s", exc)
        raise HTTPException(
            status_code=500,
            detail="LLM provider misconfigured",
        ) from exc
    except LLMProviderError as exc:
        logger.exception("AI coach unexpected provider error (pre-stream)")
        raise HTTPException(
            status_code=500,
            detail=f"LLM provider error: {exc.__class__.__name__}",
        ) from exc

    async def event_source() -> AsyncIterator[str]:
        """Generate SSE events from the provider stream.

        The first chunk has already been pulled by the pre-stream peek
        (Codex R1 P1) and is yielded first. Mid-stream failures emit a
        terminal SSE error event then close. Disconnect detection: poll
        ``http_request.is_disconnected`` between yields so we don't
        keep pulling chunks for a client that's gone away.

        Codex R2 P2: every early-return path (terminal-as-first-chunk,
        empty-stream synthetic done, client disconnect, mid-stream
        error) MUST close ``stream_iter`` so the underlying
        ``httpx.AsyncClient.stream()`` context exits deterministically
        instead of waiting on GC. The try/finally wraps the entire
        body so ``aclose()`` runs regardless of exit path.
        """
        try:
            if first_chunk is not None:
                yield _sse_event(first_chunk.model_dump(exclude_none=True))
                if first_chunk.done:
                    return
            else:
                # Empty stream synthesized terminal frame.
                yield _sse_event(
                    {"delta": "", "done": True, "model_used": chat_req.model}
                )
                return
            async for chunk in stream_iter:
                if await http_request.is_disconnected():
                    logger.info(
                        "/api/ai-coach/stream client disconnected mid-stream; "
                        "abandoning case_id=%r",
                        body.case_id,
                    )
                    return
                yield _sse_event(chunk.model_dump(exclude_none=True))
                if chunk.done:
                    return
        except LLMAuthError as exc:
            logger.error("AI coach auth error (mid-stream): %s", exc)
            yield _sse_event(
                {
                    "error": "LLMAuthError",
                    "detail": "LLM provider authentication failed",
                    "done": True,
                }
            )
        except LLMRateLimitError as exc:
            logger.warning("AI coach rate-limited (mid-stream): %s", exc)
            yield _sse_event(
                {
                    "error": "LLMRateLimitError",
                    "detail": "LLM provider rate-limited",
                    "done": True,
                }
            )
        except LLMBadRequestError as exc:
            logger.warning("AI coach bad request (mid-stream): %s", exc)
            yield _sse_event(
                {
                    "error": "LLMBadRequestError",
                    "detail": "LLM provider rejected request",
                    "done": True,
                }
            )
        except (LLMUpstreamError, LLMTimeoutError) as exc:
            logger.error("AI coach upstream error (mid-stream): %s", exc)
            yield _sse_event(
                {
                    "error": exc.__class__.__name__,
                    "detail": "LLM provider unavailable",
                    "done": True,
                }
            )
        except LLMConfigError as exc:
            logger.error("AI coach config error (mid-stream): %s", exc)
            yield _sse_event(
                {
                    "error": "LLMConfigError",
                    "detail": "LLM provider misconfigured",
                    "done": True,
                }
            )
        except LLMProviderError as exc:
            logger.exception("AI coach unexpected provider error (mid-stream)")
            yield _sse_event(
                {
                    "error": exc.__class__.__name__,
                    "detail": "LLM provider error",
                    "done": True,
                }
            )
        finally:
            # Codex R2 P2: deterministic cleanup of the upstream
            # iterator on every exit path. ``aclose`` is idempotent
            # — Python async generators tolerate a second call as
            # a no-op, and httpx.AsyncClient.stream's __aexit__ is
            # idempotent too. Skip when the iterator was never
            # opened (defensive — should always exist by this point).
            aclose = getattr(stream_iter, "aclose", None)
            if aclose is not None:
                try:
                    await aclose()
                except Exception:
                    logger.exception(
                        "/api/ai-coach/stream upstream aclose failed; "
                        "stream socket will close on GC"
                    )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            # Disable proxy buffering so chunks reach the client as
            # they're emitted (nginx default would buffer until
            # response close).
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

# ────────── DEC-V61-121 · Apply proposal ──────────


class ApplyProposalRequest(BaseModel):
    """Body for POST /api/ai-coach/apply-proposal.

    Sent by the UI when the engineer clicks [Accept] on a
    ProposalCard rendered from the chat stream.
    """

    case_id: str = Field(min_length=1, max_length=128)
    tool: str = Field(min_length=1, max_length=64)
    args: dict = Field(default_factory=dict)
    model_used: str | None = Field(default=None, max_length=64)
    conversation_turn_id: str | None = Field(default=None, max_length=64)


@router.post("/ai-coach/apply-proposal")
async def ai_coach_apply_proposal(
    body: ApplyProposalRequest, http_request: Request
):
    """Validate + apply an AI proposal, write audit, return result.

    Status code mapping:
      * 200 → applied (and audited; if audit failed, response carries
              `audit_warning` so the UI can surface it without
              undoing the change)
      * 400 → unknown tool, malformed args, bad case_id
      * 403 → non-loopback caller without override
      * 404 → case_id resolves to no case directory
      * 422 → underlying service-layer error (V108 store IO failure,
              symlink escape, lock contention, etc)
      * 500 → unexpected dispatch failure
    """
    require_loopback(http_request, route_label="/api/ai-coach/apply-proposal")

    if not is_safe_case_id(body.case_id):
        raise HTTPException(
            status_code=400,
            detail={"failing_check": "bad_case_id", "case_id": body.case_id},
        )
    case_dir = IMPORTED_DIR / body.case_id
    if not case_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={"failing_check": "case_not_found", "case_id": body.case_id},
        )

    try:
        result = dispatch_tool(case_dir, body.tool, body.args)
    except UnknownToolError as exc:
        logger.warning("apply-proposal unknown tool: %s", exc.tool_name)
        raise HTTPException(
            status_code=400,
            detail={
                "failing_check": "unknown_tool",
                "tool": exc.tool_name,
            },
        ) from exc
    except ToolArgError as exc:
        logger.warning(
            "apply-proposal arg validation failed for %s: %s",
            exc.tool_name,
            exc.validation_errors,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "failing_check": "arg_validation_failed",
                "tool": exc.tool_name,
                "errors": exc.validation_errors,
            },
        ) from exc
    except ToolDispatchError as exc:
        if exc.failing_check == "underlying_service_error":
            logger.error("apply-proposal underlying service error: %s", exc)
            raise HTTPException(
                status_code=422,
                detail={
                    "failing_check": "underlying_service_error",
                    "tool": body.tool,
                    "message": str(exc),
                },
            ) from exc
        logger.exception("apply-proposal unexpected dispatch failure")
        raise HTTPException(
            status_code=500,
            detail={
                "failing_check": "unexpected",
                "tool": body.tool,
            },
        ) from exc

    # Dispatch succeeded — write audit. If the audit fails, the
    # change is already applied; we surface a warning rather than
    # report an overall failure (the route contract above documents
    # this compensation decision, V61-121 risk register #4).
    audit_warning: str | None = None
    audit_id: str | None = None
    try:
        audit_id = write_audit(
            case_dir,
            tool=body.tool,
            args=body.args,
            model_used=body.model_used,
            conversation_turn_id=body.conversation_turn_id,
        )
    except AuditWriteError as exc:
        logger.exception("apply-proposal audit write failed AFTER dispatch")
        audit_warning = (
            f"action applied but audit log write failed: {exc}. "
            "Operators should grep the FastAPI logs for the underlying error."
        )

    response = {
        "applied": True,
        "tool": result.tool,
        "summary": result.summary,
        "state_after": result.state_after,
        "audit_id": audit_id,
    }
    if audit_warning is not None:
        response["audit_warning"] = audit_warning
    return response


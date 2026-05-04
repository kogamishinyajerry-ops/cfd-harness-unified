"""DeepSeek API adapter.

Targets ``https://api.deepseek.com/v1/chat/completions`` with the
OpenAI-compatible request/response format. Implements the V1 fallback
chain: ``deepseek-v4-pro`` → ``deepseek-v4-flash`` on
rate-limit / 5xx / timeout. Auth errors and config errors do NOT
trigger fallback (changing model won't fix bad credentials).

Secrets handling: the API key is held as instance state, never logged
or included in ``__repr__`` / error messages. The Authorization
header is only ever attached at request time.
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

from ui.backend.services.llm_provider.base import (
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    DeepSeekModelId,
    LLMAuthError,
    LLMBadRequestError,
    LLMProvider,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
)

logger = logging.getLogger(__name__)

_DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_DEFAULT_READ_TIMEOUT_SECONDS = 60.0
_DEFAULT_TIMEOUT = httpx.Timeout(_DEFAULT_READ_TIMEOUT_SECONDS, connect=10.0)
_FALLBACK_MAP: dict[DeepSeekModelId, DeepSeekModelId] = {
    "deepseek-v4-pro": "deepseek-v4-flash",
}


class DeepSeekProvider(LLMProvider):
    """OpenAI-compatible adapter for the DeepSeek API.

    Constructor takes the API key explicitly so test fixtures can
    inject a known value without setting env vars. The
    :func:`~ui.backend.services.llm_provider.factory.get_default_provider`
    factory reads ``DEEPSEEK_API_KEY`` and instantiates this for
    production use.
    """

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = _DEEPSEEK_ENDPOINT,
        timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            # Defensive: factory already guards this, but a direct
            # constructor call with empty key would otherwise produce
            # a 401 surprise far from the construction site.
            raise ValueError("DeepSeekProvider requires a non-empty api_key")
        self._api_key = api_key
        self._endpoint = endpoint
        self._timeout = timeout
        # Codex R1 P3: in production paths, the factory hands every
        # request the SAME provider instance (singleton). The client
        # is lazily created on first POST and reused thereafter so
        # subsequent completions get keep-alive connection pooling
        # instead of fresh DNS+TLS handshakes per turn. Tests inject
        # an httpx.MockTransport via this same field, so the lazy/
        # injected paths share one code path.
        self._client = client
        self._owns_client = client is None

    async def aclose(self) -> None:
        """Close the long-lived AsyncClient. Idempotent.

        Lifecycle contract (single-loop, single-thread):
          * Designed to run from the same event loop as ``chat()``.
          * Intended call site is the FastAPI ``lifespan`` shutdown
            hook, which fires AFTER the server stops accepting new
            requests, so there are no in-flight ``chat()`` calls
            when this runs.
          * Skips closing when the client was caller-injected
            (test path) — the caller owns its lifetime.

        Cross-loop / multi-thread close is intentionally out of
        scope: the V1 deployment is single uvicorn worker, single
        loop. Codex R7 chain (commit dc04f86 → 5cbeb00 → 59111b8)
        explored drain-based and time-delayed eviction; both opened
        race surfaces that exceeded V1 scope. Decision documented in
        DEC-V61-118 §risk register R5.
        """
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def __repr__(self) -> str:
        # Never embed the api_key.
        return f"DeepSeekProvider(endpoint={self._endpoint!r})"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        primary = request.model
        try:
            return await self._chat_with_model(request, primary, fallback_used=False)
        except (LLMRateLimitError, LLMUpstreamError, LLMTimeoutError) as exc:
            # Codex R1 P2: LLMBadRequestError (4xx non-auth/non-429)
            # is intentionally NOT in the retry tuple — same payload
            # against a different model would just waste a quota slot
            # and obscure the actionable client error.
            fallback = _FALLBACK_MAP.get(primary)
            if fallback is None:
                # No fallback configured for this primary (e.g. the
                # caller explicitly asked for v4-flash). Re-raise.
                raise
            logger.warning(
                "DeepSeek %s failed (%s); falling back to %s",
                primary,
                exc.__class__.__name__,
                fallback,
            )
            return await self._chat_with_model(request, fallback, fallback_used=True)

    async def _chat_with_model(
        self,
        request: ChatRequest,
        model: DeepSeekModelId,
        *,
        fallback_used: bool,
    ) -> ChatResponse:
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = await self._post(payload, headers)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"DeepSeek request timed out after {self._timeout.read}s"
            ) from exc
        except httpx.HTTPError as exc:
            # Network-layer failure (connection refused, DNS, etc).
            raise LLMUpstreamError(
                f"DeepSeek transport error: {type(exc).__name__}"
            ) from exc

        if response.status_code in (401, 403):
            raise LLMAuthError(f"DeepSeek auth failed (status {response.status_code})")
        if response.status_code == 429:
            raise LLMRateLimitError("DeepSeek rate-limited")
        if response.status_code >= 500:
            raise LLMUpstreamError(
                f"DeepSeek upstream error (status {response.status_code})"
            )
        if 400 <= response.status_code < 500:
            # Codex R1 P2: a 400/422 (e.g. context_length_exceeded,
            # invalid_request_error) is the caller's problem, not
            # ours. Surface as LLMBadRequestError so chat()'s retry
            # tuple does NOT match — same payload would just produce
            # the same 400 from the fallback model. The route maps
            # this to HTTP 400 with the upstream's error code so the
            # caller can adjust their request.
            raise LLMBadRequestError(
                f"DeepSeek rejected request (status {response.status_code})"
            )
        if response.status_code != 200:
            # Defensive: any non-2xx not enumerated above (1xx/3xx).
            # Not retryable — surface as bad request.
            raise LLMBadRequestError(
                f"DeepSeek unexpected status {response.status_code}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMUpstreamError("DeepSeek returned non-JSON response") from exc

        return self._parse_response(body, model, fallback_used)

    async def _post(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        # Codex R1 P3: lazy-create a long-lived AsyncClient on first
        # use and reuse for all subsequent completions. Singleton
        # provider + persistent client = HTTP keep-alive across chat
        # turns, no per-request DNS+TLS handshake. Test paths inject
        # client up-front (with MockTransport) so they bypass this
        # lazy branch entirely.
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return await self._client.post(
            self._endpoint, json=payload, headers=headers, timeout=self._timeout
        )

    async def chat_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatStreamChunk]:
        """Stream a chat completion via DeepSeek's OpenAI-compatible SSE.

        Yields :class:`ChatStreamChunk` per delta frame, then a terminal
        frame with ``done=True``. Mid-stream upstream failure raises
        the appropriate :class:`LLMProviderError` subclass; callers
        in the route layer translate that to a final SSE error event.

        Per DEC-V61-119 §V1 explicit scope-down: NO mid-stream
        fallback. The stream commits to ``request.model`` and surfaces
        any failure to the caller.
        """
        model = request.model
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)

        try:
            async with self._client.stream(
                "POST",
                self._endpoint,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            ) as response:
                # Pre-stream status check: if the upstream rejected the
                # request before opening the stream, we still know the
                # status code and can map it the same way `chat()` does.
                if response.status_code in (401, 403):
                    raise LLMAuthError(
                        f"DeepSeek auth failed (status {response.status_code})"
                    )
                if response.status_code == 429:
                    raise LLMRateLimitError("DeepSeek rate-limited")
                if response.status_code >= 500:
                    raise LLMUpstreamError(
                        f"DeepSeek upstream error (status {response.status_code})"
                    )
                if 400 <= response.status_code < 500:
                    raise LLMBadRequestError(
                        f"DeepSeek rejected request (status {response.status_code})"
                    )
                if response.status_code != 200:
                    raise LLMBadRequestError(
                        f"DeepSeek unexpected status {response.status_code}"
                    )

                # Stream loop. httpx.aiter_lines() handles line-buffered
                # framing across TCP read boundaries — never byte-buffer
                # manually (Risk-1 in the DEC).
                final_usage: dict[str, int] | None = None
                terminal_emitted = False
                async for line in response.aiter_lines():
                    if not line:
                        # Blank line = SSE event separator; ignore.
                        continue
                    if not line.startswith("data:"):
                        # OpenAI/DeepSeek SSE only ever uses `data:`
                        # lines; `event:`/`id:` etc. would be silently
                        # skipped.
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        # Terminal marker. Emit the synthesized done
                        # chunk with whatever usage we accumulated.
                        yield ChatStreamChunk(
                            delta="",
                            done=True,
                            usage=final_usage,
                            model_used=model,
                            fallback_used=False,
                        )
                        terminal_emitted = True
                        break
                    try:
                        event = json.loads(data)
                    except ValueError as exc:
                        raise LLMUpstreamError(
                            "DeepSeek stream emitted malformed JSON event"
                        ) from exc
                    # Capture usage if the upstream attached it to this
                    # frame (typically the finish_reason frame).
                    usage_raw = event.get("usage")
                    if isinstance(usage_raw, dict):
                        final_usage = {
                            k: int(v)
                            for k, v in usage_raw.items()
                            if isinstance(v, (int, float))
                            and k in {"prompt_tokens", "completion_tokens", "total_tokens"}
                        }
                    # Extract delta content if present. Frames without
                    # a content delta (e.g. role-announce frame, usage
                    # frame, finish_reason frame) are silently skipped
                    # — callers that concatenate `delta`s see only the
                    # text payload.
                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    delta_obj = choices[0].get("delta") or {}
                    content = delta_obj.get("content")
                    if not isinstance(content, str) or content == "":
                        continue
                    yield ChatStreamChunk(
                        delta=content,
                        done=False,
                        model_used=model,
                        fallback_used=False,
                    )

                # Some providers close the stream without an explicit
                # `[DONE]` marker. If we exited the loop normally,
                # synthesize the terminal chunk so consumers always
                # see exactly one done=True frame per stream.
                if not terminal_emitted:
                    yield ChatStreamChunk(
                        delta="",
                        done=True,
                        usage=final_usage,
                        model_used=model,
                        fallback_used=False,
                    )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"DeepSeek stream timed out after {self._timeout.read}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMUpstreamError(
                f"DeepSeek transport error: {type(exc).__name__}"
            ) from exc

    @staticmethod
    def _parse_response(
        body: dict[str, Any],
        model: DeepSeekModelId,
        fallback_used: bool,
    ) -> ChatResponse:
        # OpenAI-compatible response shape:
        # {choices: [{message: {role, content}, ...}], usage: {...}, ...}
        try:
            choice = body["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMUpstreamError("DeepSeek response missing choices/content") from exc
        if not isinstance(content, str):
            raise LLMUpstreamError("DeepSeek choices[0].message.content is not a string")
        usage_raw = body.get("usage") or {}
        usage = {
            k: int(v)
            for k, v in usage_raw.items()
            if isinstance(v, (int, float))
            and k in {"prompt_tokens", "completion_tokens", "total_tokens"}
        }
        return ChatResponse(
            content=content,
            model_used=model,
            fallback_used=fallback_used,
            usage=usage,
        )

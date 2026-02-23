"""HTTP interception for LLM traffic (httpx + requests)."""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

import httpx

from ..trace import LLMStep
from ..trace import get_current_trace

_original_async_send: Optional[Callable[..., Any]] = None
_original_sync_send: Optional[Callable[..., Any]] = None
_original_requests_send: Optional[Callable[..., Any]] = None
_installed = False


def install_ai_interceptor():
    global _installed, _original_async_send, _original_sync_send, _original_requests_send
    if _installed:
        return
    _installed = True

    _original_async_send = httpx.AsyncClient.send
    _original_sync_send = httpx.Client.send

    async def async_send(self: httpx.AsyncClient, request: httpx.Request, *args, **kwargs):  # type: ignore[override]
        _record_if_llm(request)
        if _original_async_send:
            return await _original_async_send(self, request, *args, **kwargs)
        return None

    def sync_send(self: httpx.Client, request: httpx.Request, *args, **kwargs):  # type: ignore[override]
        _record_if_llm(request)
        if _original_sync_send:
            return _original_sync_send(self, request, *args, **kwargs)
        return None

    httpx.AsyncClient.send = async_send  # type: ignore[assignment]
    httpx.Client.send = sync_send  # type: ignore[assignment]

    try:
        import requests

        _original_requests_send = requests.Session.send

        def requests_send(self, request, *args, **kwargs):  # type: ignore[override]
            _record_if_llm_request(request)
            if _original_requests_send:
                return _original_requests_send(self, request, *args, **kwargs)
            return None

        requests.Session.send = requests_send  # type: ignore[assignment]
    except Exception:
        _original_requests_send = None


def uninstall_ai_interceptor():
    global _installed
    if not _installed:
        return
    _installed = False
    if _original_async_send:
        httpx.AsyncClient.send = _original_async_send  # type: ignore[assignment]
    if _original_sync_send:
        httpx.Client.send = _original_sync_send  # type: ignore[assignment]
    if _original_requests_send:
        import requests

        requests.Session.send = _original_requests_send  # type: ignore[assignment]


def _record_if_llm(request: httpx.Request):
    trace = get_current_trace()
    if not trace:
        return
    url = str(request.url)
    try:
        body = request.read()
    except Exception:
        body = b""
    _record_common(trace, url, body)


def _record_if_llm_request(request):
    trace = get_current_trace()
    if not trace:
        return
    url = str(request.url)
    body = request.body if hasattr(request, "body") else b""
    if isinstance(body, str):
        body_bytes = body.encode()
    else:
        body_bytes = body or b""
    _record_common(trace, url, body_bytes)


def _record_common(trace, url: str, body_bytes: bytes):
    try:
        payload = json.loads(body_bytes.decode() or "{}")
    except Exception:
        payload = {}
    model = payload.get("model") or _infer_model_from_url(url)
    prompt = None
    completion = None
    messages = payload.get("messages") or []
    if messages:
        prompt_parts = [m.get("content") for m in messages if m.get("role") == "user"]
        prompt = "\n\n".join([p for p in prompt_parts if p])
    if "stream" in payload and payload.get("stream") is True:
        completion = "(streamed)"
    trace.record_llm_step(LLMStep(model=model or "unknown", provider=_infer_provider(url), prompt=prompt, completion=completion))


def _infer_provider(url: str) -> Optional[str]:
    if "openai.com" in url or "/v1/chat/completions" in url:
        return "openai"
    if "generativelanguage" in url:
        return "gemini"
    if "x.ai" in url or "grok" in url:
        return "grok"
    return None


def _infer_model_from_url(url: str) -> Optional[str]:
    if "gpt" in url:
        return "gpt"
    if "grok" in url:
        return "grok"
    return None

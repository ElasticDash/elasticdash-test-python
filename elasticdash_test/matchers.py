"""Assertion helpers for traces."""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Callable, Iterable, Optional

import httpx

from .trace import TraceHandle, LLMStep, ToolCall, CustomStep


class Expectation:
    def __init__(self, subject: Any):
        self.subject = subject

    # --- LLM steps ---
    def to_have_llm_step(
        self,
        *,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        contains: Optional[str] = None,
        prompt_contains: Optional[str] = None,
        output_contains: Optional[str] = None,
        times: Optional[int] = None,
        min_times: Optional[int] = None,
        max_times: Optional[int] = None,
    ):
        trace = _ensure_trace(self.subject)
        steps = trace.get_llm_steps()

        def matches(step: LLMStep) -> bool:
            if model and step.model != model:
                return False
            if provider and step.provider != provider:
                return False
            if contains and not _contains(step.prompt, contains) and not _contains(step.completion, contains):
                return False
            if prompt_contains and not _contains(step.prompt, prompt_contains):
                return False
            if output_contains and not _contains(step.completion, output_contains):
                return False
            return True

        _assert_count("LLM step", steps, matches, times, min_times, max_times)
        return trace

    # --- Tool calls ---
    def to_call_tool(
        self,
        name: Optional[str] = None,
        *,
        times: Optional[int] = None,
        min_times: Optional[int] = None,
        max_times: Optional[int] = None,
    ):
        trace = _ensure_trace(self.subject)
        calls = trace.get_tool_calls()

        def matches(call: ToolCall) -> bool:
            if name and call.name != name:
                return False
            return True

        _assert_count("tool call", calls, matches, times, min_times, max_times)
        return trace

    # --- Custom steps ---
    def to_have_custom_step(
        self,
        *,
        kind: Optional[str] = None,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        contains: Optional[str] = None,
        result_contains: Optional[str] = None,
        payload_contains: Optional[str] = None,
        metadata_contains: Optional[str] = None,
        times: Optional[int] = None,
        min_times: Optional[int] = None,
        max_times: Optional[int] = None,
    ):
        trace = _ensure_trace(self.subject)
        steps = trace.get_custom_steps()

        def matches(step: CustomStep) -> bool:
            if kind and step.kind != kind:
                return False
            if name and step.name != name:
                return False
            if tag and tag not in (step.tags or []):
                return False
            if contains and not (_contains(step.payload, contains) or _contains(step.result, contains)):
                return False
            if result_contains and not _contains(step.result, result_contains):
                return False
            if payload_contains and not _contains(step.payload, payload_contains):
                return False
            if metadata_contains and not _contains(step.metadata, metadata_contains):
                return False
            return True

        _assert_count("custom step", steps, matches, times, min_times, max_times)
        return trace

    # --- Prompt filtering ---
    def to_have_prompt_where(
        self,
        *,
        filter_contains: Optional[str] = None,
        require_contains: Optional[str] = None,
        require_not_contains: Optional[str] = None,
        times: Optional[int] = None,
        min_times: Optional[int] = None,
        max_times: Optional[int] = None,
        index: Optional[int] = None,
        nth: Optional[int] = None,
    ):
        trace = _ensure_trace(self.subject)
        steps = trace.get_llm_steps()

        def matches(step: LLMStep) -> bool:
            if filter_contains and not _contains(step.prompt, filter_contains):
                return False
            if require_contains and not _contains(step.prompt, require_contains):
                return False
            if require_not_contains and _contains(step.prompt, require_not_contains):
                return False
            return True

        if nth is not None:
            index = nth
        if index is not None:
            if index < 0 or index >= len(steps):
                raise AssertionError(f"Prompt index {index} out of range")
            step = steps[index]
            if not matches(step):
                raise AssertionError("Prompt at requested index did not match filter")
            return trace

        _assert_count("prompt", steps, matches, times, min_times, max_times)
        return trace

    # --- Semantic output matching ---
    async def to_match_semantic_output(
        self,
        expected: str,
        *,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        trace = _ensure_trace(self.subject)
        actual = _latest_completion(trace)
        score = await _semantic_match(
            expected=expected,
            actual=actual,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        if score < 0.5:
            raise AssertionError(f"Semantic match score too low: {score:.2f}")
        return trace

    # --- Output metric evaluation ---
    async def to_evaluate_output_metric(
        self,
        evaluation_prompt: str,
        *,
        nth: Optional[int] = None,
        index: Optional[int] = None,
        condition: Optional[dict] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        trace = _ensure_trace(self.subject)
        actual = _latest_completion(trace, index=index, nth=nth)
        score = await _score_output(
            evaluation_prompt=evaluation_prompt,
            actual=actual,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        if condition:
            _check_condition(score, condition)
        return score


def expect(subject: Any) -> Expectation:
    return Expectation(subject)


# --- Helpers ---


def _ensure_trace(subject: Any) -> TraceHandle:
    if not isinstance(subject, TraceHandle):
        raise AssertionError("Expect subject must be a TraceHandle")
    return subject


def _contains(container: Any, needle: str) -> bool:
    if container is None:
        return False
    return needle.lower() in str(container).lower()


def _assert_count(
    label: str,
    items: Iterable[Any],
    predicate: Callable[[Any], bool],
    times: Optional[int],
    min_times: Optional[int],
    max_times: Optional[int],
):
    matches = [item for item in items if predicate(item)]
    count = len(matches)
    if times is not None and count != times:
        raise AssertionError(f"Expected {label} {times} time(s); observed {count}")
    if min_times is not None and count < min_times:
        raise AssertionError(f"Expected {label} at least {min_times} time(s); observed {count}")
    if max_times is not None and count > max_times:
        raise AssertionError(f"Expected {label} at most {max_times} time(s); observed {count}")
    if times is None and min_times is None and max_times is None and count == 0:
        raise AssertionError(f"Expected {label} but none recorded")


def _latest_completion(trace: TraceHandle, index: Optional[int] = None, nth: Optional[int] = None) -> str:
    steps = trace.get_llm_steps()
    if not steps:
        raise AssertionError("No LLM steps recorded")
    if nth is not None:
        index = nth
    if index is None:
        return steps[-1].completion or ""
    if index < 0 or index >= len(steps):
        raise AssertionError(f"LLM step index {index} out of range")
    return steps[index].completion or ""


def _openai_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


async def _semantic_match(
    *,
    expected: str,
    actual: str,
    provider: str,
    model: Optional[str],
    api_key: Optional[str],
    base_url: Optional[str],
) -> float:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AssertionError("OPENAI_API_KEY is required for semantic match")
    model = model or "gpt-4o-mini"
    url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    prompt = (
        "You are grading a semantic similarity test. "
        "Respond with a JSON object {\"score\": number between 0 and 1} "
        "where 1 means actual matches expected perfectly."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps({"expected": expected, "actual": actual}),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=_openai_headers(api_key), json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
            return float(parsed.get("score", 0))
        except Exception as exc:
            raise AssertionError(f"Unexpected model response: {content}") from exc


async def _score_output(
    *,
    evaluation_prompt: str,
    actual: str,
    provider: str,
    model: Optional[str],
    api_key: Optional[str],
    base_url: Optional[str],
) -> float:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AssertionError("OPENAI_API_KEY is required for evaluation")
    model = model or "gpt-4o-mini"
    url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    prompt = (
        "You are grading model output. Return JSON {\"score\": number between 0 and 1}. "
        "Score higher when the output satisfies the evaluation prompt."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": evaluation_prompt},
            {"role": "assistant", "content": actual},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=_openai_headers(api_key), json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
            return float(parsed.get("score", 0))
        except Exception as exc:
            raise AssertionError(f"Unexpected model response: {content}") from exc


def _check_condition(score: float, condition: dict):
    if "at_least" in condition and score < condition["at_least"]:
        raise AssertionError(f"Score {score:.2f} below threshold {condition['at_least']}")
    if "at_most" in condition and score > condition["at_most"]:
        raise AssertionError(f"Score {score:.2f} above threshold {condition['at_most']}")
    if "equals" in condition and abs(score - condition["equals"]) > 1e-6:
        raise AssertionError(f"Score {score:.2f} not equal to {condition['equals']}")

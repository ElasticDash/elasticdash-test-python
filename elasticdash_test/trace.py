"""Tracing primitives for AI test runs."""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class LLMStep:
    model: str
    provider: Optional[str] = None
    prompt: Optional[str] = None
    completion: Optional[str] = None
    contains: Optional[str] = None


@dataclass
class ToolCall:
    name: str
    args: Optional[dict] = None
    result: Optional[Any] = None


@dataclass
class CustomStep:
    kind: str
    name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    payload: Optional[Any] = None
    result: Optional[Any] = None
    metadata: Optional[dict] = None


class TraceHandle:
    def __init__(self):
        self._llm_steps: List[LLMStep] = []
        self._tool_calls: List[ToolCall] = []
        self._custom_steps: List[CustomStep] = []

    def record_llm_step(self, step: Optional[LLMStep] = None, **kwargs):
        """Record an LLM step; accepts LLMStep or keyword args."""
        if step is None:
            step = LLMStep(**kwargs)
        self._llm_steps.append(step)

    def record_tool_call(self, call: Optional[ToolCall] = None, **kwargs):
        """Record a tool call; accepts ToolCall or keyword args."""
        if call is None:
            call = ToolCall(**kwargs)
        self._tool_calls.append(call)

    def record_custom_step(self, step: Optional[CustomStep] = None, **kwargs):
        """Record a custom step; accepts CustomStep or keyword args."""
        if step is None:
            step = CustomStep(**kwargs)
        self._custom_steps.append(step)

    def get_llm_steps(self) -> List[LLMStep]:
        return list(self._llm_steps)

    def get_tool_calls(self) -> List[ToolCall]:
        return list(self._tool_calls)

    def get_custom_steps(self) -> List[CustomStep]:
        return list(self._custom_steps)

    def get_steps(self) -> List[Any]:
        return [
            *self.get_llm_steps(),
            *self.get_tool_calls(),
            *self.get_custom_steps(),
        ]


@dataclass
class AITestContext:
    trace: TraceHandle


_current_trace: ContextVar[Optional[TraceHandle]] = ContextVar("_current_trace", default=None)


def set_current_trace(trace: Optional[TraceHandle]):
    _current_trace.set(trace)


def get_current_trace() -> Optional[TraceHandle]:
    return _current_trace.get()

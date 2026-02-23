"""Async test runner."""
from __future__ import annotations

import asyncio
import importlib.util
import time
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, List, Optional, TypedDict

from .registry import get_registry
from .trace import TraceHandle, AITestContext, set_current_trace


class TestSpec(TypedDict):
    name: str
    fn: Callable[..., Any]


@dataclass
class TestResult:
    name: str
    status: str
    duration: float
    error: Optional[BaseException] = None
    trace: Optional[TraceHandle] = None


@dataclass
class FileResult:
    file: str
    tests: List[TestResult] = field(default_factory=list)
    before_all_error: Optional[BaseException] = None
    after_all_error: Optional[BaseException] = None


async def run_files(files: List[str]) -> List[FileResult]:
    results: List[FileResult] = []
    for file in files:
        results.append(await run_file(file))
    return results


async def run_file(file: str) -> FileResult:
    module = _import_file(file)
    reg = get_registry(file)
    if reg is None:
        # No tests registered after import
        return FileResult(file=file, tests=[])
    result = FileResult(file=file)

    try:
        await _run_hooks(_hook_list(reg, "before_all_hooks"))
    except BaseException as exc:  # noqa: BLE001
        result.before_all_error = exc
        return result

    for test in _tests_list(reg):
        trace = TraceHandle()
        ctx = AITestContext(trace=trace)
        set_current_trace(trace)
        start = time.perf_counter()
        status = "passed"
        err: Optional[BaseException] = None
        try:
            await _run_hooks(_hook_list(reg, "before_each_hooks"), ctx)
            await _maybe_await(test["fn"], ctx)
        except AssertionError as exc:
            status = "failed"
            err = exc
        except BaseException as exc:  # noqa: BLE001
            status = "error"
            err = exc
        finally:
            try:
                await _run_hooks(_hook_list(reg, "after_each_hooks"), ctx)
            finally:
                set_current_trace(None)
        duration = time.perf_counter() - start
        result.tests.append(
            TestResult(
                name=test["name"],
                status=status,
                duration=duration,
                error=err,
                trace=trace,
            )
        )

    try:
        await _run_hooks(_hook_list(reg, "after_all_hooks"))
    except BaseException as exc:  # noqa: BLE001
        result.after_all_error = exc
    return result


async def _run_hooks(hooks: List[Callable[..., Any]], ctx: Optional[AITestContext] = None):
    for hook in hooks:
        await _maybe_await(hook, ctx)


async def _maybe_await(func: Callable[..., Any], ctx: Optional[AITestContext]):
    if ctx is not None:
        res = func(ctx) if _accepts_ctx(func) else func()
    else:
        res = func()
    if asyncio.iscoroutine(res):
        return await res
    return res


def _accepts_ctx(func: Callable[..., Any]) -> bool:
    return func.__code__.co_argcount >= 1


def _import_file(path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location("elasticdash_test_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hook_list(reg: dict[str, Any], key: str) -> List[Callable[..., Any]]:
    hooks = reg.get(key) or []
    if not isinstance(hooks, list):
        return []
    # Trust registry to only store callables; keep guard for type checkers
    return [h for h in hooks if callable(h)]


def _tests_list(reg: dict[str, Any]) -> List[TestSpec]:
    tests = reg.get("tests") or []
    if not isinstance(tests, list):
        return []
    filtered: List[TestSpec] = []
    for item in tests:
        if isinstance(item, dict) and "name" in item and "fn" in item:
            filtered.append(TestSpec(name=item["name"], fn=item["fn"]))
    return filtered

"""Test registration decorators and storage."""
from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional

RegistryEntry = Dict[str, List[Callable[..., Any]]]
TestEntry = Dict[str, Any]

# Registry keyed by file path to keep test definitions isolated per module
_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _ensure_registry(file_path: str) -> Dict[str, Any]:
    if file_path not in _REGISTRY:
        _REGISTRY[file_path] = {
            "tests": [],
            "before_all_hooks": [],
            "after_all_hooks": [],
            "before_each_hooks": [],
            "after_each_hooks": [],
        }
    return _REGISTRY[file_path]


def _infer_file(func: Callable[..., Any]) -> Optional[str]:
    """Best-effort inference of the declaring file for a function."""
    module = inspect.getmodule(func)
    if module and getattr(module, "__file__", None):
        return module.__file__
    # Fallback to the code object's filename; works when inspect.getmodule fails
    if getattr(func, "__code__", None):
        return func.__code__.co_filename
    return None


def ai_test(name_or_func=None, func: Optional[Callable[..., Any]] = None):
    """Decorator or functional form to register an AI test."""

    def decorator(test_fn: Callable[..., Any]):
        file_path = _infer_file(test_fn)
        if not file_path:
            raise RuntimeError("Unable to infer file path for ai_test")
        registry = _ensure_registry(file_path)
        registry["tests"].append({"name": test_name or test_fn.__name__, "fn": test_fn})
        return test_fn

    if callable(name_or_func) and func is None:
        test_fn = name_or_func
        test_name = test_fn.__name__
        return decorator(test_fn)

    test_name = name_or_func if isinstance(name_or_func, str) else None

    if func is not None:
        return decorator(func)

    return decorator


def before_all(func: Callable[..., Any]):
    file_path = _infer_file(func)
    if file_path is None:
        raise RuntimeError("Unable to infer file path for before_all hook")
    registry = _ensure_registry(file_path)
    registry["before_all_hooks"].append(func)
    return func


def after_all(func: Callable[..., Any]):
    file_path = _infer_file(func)
    if file_path is None:
        raise RuntimeError("Unable to infer file path for after_all hook")
    registry = _ensure_registry(file_path)
    registry["after_all_hooks"].append(func)
    return func


def before_each(func: Callable[..., Any]):
    file_path = _infer_file(func)
    if file_path is None:
        raise RuntimeError("Unable to infer file path for before_each hook")
    registry = _ensure_registry(file_path)
    registry["before_each_hooks"].append(func)
    return func


def after_each(func: Callable[..., Any]):
    file_path = _infer_file(func)
    if file_path is None:
        raise RuntimeError("Unable to infer file path for after_each hook")
    registry = _ensure_registry(file_path)
    registry["after_each_hooks"].append(func)
    return func


def clear_registry(file_path: Optional[str] = None):
    if file_path is None:
        _REGISTRY.clear()
        return
    if file_path in _REGISTRY:
        del _REGISTRY[file_path]


def get_registry(file_path: Optional[str] = None):
    if file_path:
        return _REGISTRY.get(file_path, None)
    return _REGISTRY

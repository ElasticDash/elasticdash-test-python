"""Console reporter for elasticdash test runs."""
from __future__ import annotations

import shutil
from typing import List

from .runner import FileResult, TestResult

try:
    import colorama

    colorama.init()
    _COLOR = True
except Exception:
    _COLOR = True  # ANSI works on most modern terminals


_DEF = "\033[0m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_DIM = "\033[2m"


def _c(text: str, color: str) -> str:
    if not _COLOR:
        return text
    return f"{color}{text}{_DEF}"


def print_results(results: List[FileResult]):
    total_tests = 0
    passed = 0
    failed = 0
    errored = 0
    width = shutil.get_terminal_size((80, 20)).columns

    for file_result in results:
        if file_result.before_all_error:
            print(_c(f"✗ {file_result.file} before_all failed: {file_result.before_all_error}", _RED))
            errored += 1
            continue
        for test in file_result.tests:
            total_tests += 1
            if test.status == "passed":
                passed += 1
                mark = _c("✓", _GREEN)
            elif test.status == "failed":
                failed += 1
                mark = _c("✗", _RED)
            else:
                errored += 1
                mark = _c("✗", _RED)
            name = f"{mark} {test.name} ({test.duration:.2f}s)"
            print(name)
            if test.error:
                msg = str(test.error)
                for line in msg.splitlines():
                    print("    → " + line)
        if file_result.after_all_error:
            print(_c(f"✗ {file_result.file} after_all failed: {file_result.after_all_error}", _RED))
            errored += 1

    summary = [
        _c(f"{passed} passed", _GREEN),
        _c(f"{failed} failed", _RED) if failed else None,
        _c(f"{errored} errored", _YELLOW) if errored else None,
    ]
    summary = [s for s in summary if s]
    print(" ".join(summary))
    print(f"Total: {total_tests}")

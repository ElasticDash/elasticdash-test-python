"""CLI entry point for elasticdash tests."""
from __future__ import annotations

import asyncio
import glob
import importlib.util
import os
from pathlib import Path
from typing import Dict, List, Optional

import click

from .runner import run_file, run_files
from .reporter import print_results


DEFAULT_MATCH = ["**/*.ai_test.py"]


def _load_config(cwd: Path) -> Dict:
    config = {}
    
    # Load main config
    config_path = cwd / "elasticdash.config.py"
    if config_path.exists():
        spec = importlib.util.spec_from_file_location("elasticdash_config", config_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            config.update(getattr(module, "config", {}))
    
    # Load ed_agents config
    agents_path = cwd / "ed_agents.py"
    if agents_path.exists():
        spec = importlib.util.spec_from_file_location("ed_agents", agents_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            config["agents"] = getattr(module, "config", {})
    
    # Import ed_workflows module
    workflows_path = cwd / "ed_workflows.py"
    if workflows_path.exists():
        spec = importlib.util.spec_from_file_location("ed_workflows", workflows_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            config["workflows_module"] = module
    
    # Import ed_tools module
    tools_path = cwd / "ed_tools.py"
    if tools_path.exists():
        spec = importlib.util.spec_from_file_location("ed_tools", tools_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            config["tools_module"] = module
    
    return config


def _discover_files(root: Path, patterns: List[str]) -> List[str]:
    files: List[str] = []
    for pattern in patterns:
        files.extend(glob.glob(str(root / pattern), recursive=True))
    return sorted(dict.fromkeys(files))


def _should_enable_browser_ui(flag: bool) -> bool:
    if os.getenv("ELASTICDASH_BROWSER_UI", "1") == "0":
        return False
    return flag


def _summarize_results(file_results):
    total = 0
    passed = 0
    failed = 0
    errored = 0
    for fr in file_results:
        if fr.before_all_error:
            errored += 1
            continue
        for t in fr.tests:
            total += 1
            if t.status == "passed":
                passed += 1
            elif t.status == "failed":
                failed += 1
            else:
                errored += 1
        if fr.after_all_error:
            errored += 1
    return {"total": total, "passed": passed, "failed": failed, "errored": errored}


@click.group()
def main():
    """elasticdash test runner"""


@main.command(name="test")
@click.argument("path", default=".")
@click.option("--no-browser-ui", "no_browser_ui", is_flag=True, help="Disable browser UI")
@click.option("--browser-ui-port", default=4571, help="Browser UI port")
@click.option(
    "--browser-ui-keep-open",
    default=3.0,
    show_default=True,
    help="Seconds to keep browser UI alive after run (avoid connection refused on short runs)",
)
def test_cmd(path: str, no_browser_ui: bool, browser_ui_port: int, browser_ui_keep_open: float):
    cwd = Path(path).resolve()
    config = _load_config(cwd)
    patterns = config.get("test_match") or DEFAULT_MATCH
    files = _discover_files(cwd, patterns)
    browser_ui_enabled = _should_enable_browser_ui(not no_browser_ui)

    async def _run():
        server = None
        if browser_ui_enabled:
            try:
                from .browser_ui import start_browser_ui_server

                server = await start_browser_ui_server(port=browser_ui_port, auto_open=True)
                server.send({"type": "run-start", "payload": {"files": files}})
            except Exception:
                server = None
        results = []
        for file in files:
            if server:
                server.send({"type": "file-start", "payload": {"file": file}})
            file_result = await run_file(file)
            results.append(file_result)
            if server:
                for test in file_result.tests:
                    server.send(
                        {
                            "type": "test-finish",
                            "payload": {
                                "file": file,
                                "name": test.name,
                                "status": test.status,
                                "duration": test.duration,
                                "error": str(test.error) if test.error else None,
                            },
                        }
                    )
        if server:
            server.send({"type": "run-summary", "payload": _summarize_results(results)})
            if browser_ui_keep_open > 0:
                await asyncio.sleep(browser_ui_keep_open)
            await server.close()
        print_results(results)

    asyncio.run(_run())


@main.command(name="run")
@click.argument("file")
@click.option("--no-browser-ui", "no_browser_ui", is_flag=True, help="Disable browser UI")
@click.option("--browser-ui-port", default=4571, help="Browser UI port")
@click.option(
    "--browser-ui-keep-open",
    default=3.0,
    show_default=True,
    help="Seconds to keep browser UI alive after run (avoid connection refused on short runs)",
)
def run_single(file: str, no_browser_ui: bool, browser_ui_port: int, browser_ui_keep_open: float):
    browser_ui_enabled = _should_enable_browser_ui(not no_browser_ui)

    async def _run():
        server = None
        if browser_ui_enabled:
            try:
                from .browser_ui import start_browser_ui_server

                server = await start_browser_ui_server(port=browser_ui_port, auto_open=True)
                server.send({"type": "run-start", "payload": {"files": [file]}})
            except Exception:
                server = None
        result = await run_file(file)
        if server:
            for test in result.tests:
                server.send(
                    {
                        "type": "test-finish",
                        "payload": {
                            "file": file,
                            "name": test.name,
                            "status": test.status,
                            "duration": test.duration,
                            "error": str(test.error) if test.error else None,
                        },
                    }
                )
            server.send({"type": "run-summary", "payload": _summarize_results([result])})
            if browser_ui_keep_open > 0:
                await asyncio.sleep(browser_ui_keep_open)
            await server.close()
        print_results([result])

    asyncio.run(_run())


if __name__ == "__main__":
    main()

"""Dashboard server for browsing workflows."""
from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from aiohttp import web


def scan_workflows(cwd: Path) -> list[dict[str, Any]]:
    """Scan ed_workflows.py for callable functions.
    
    Returns list of dicts with keys: name, is_async, signature, file_path, source_file, source_module
    """
    workflows_path = cwd / "ed_workflows.py"
    workflows = []
    
    if not workflows_path.exists():
        return workflows
    
    try:
        spec = importlib.util.spec_from_file_location("ed_workflows", workflows_path)
        if not spec or not spec.loader:
            return workflows
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Extract all callables
        for name in dir(module):
            if name.startswith("_"):
                continue
            
            obj = getattr(module, name)
            if callable(obj) and not isinstance(obj, type):
                # Get signature
                try:
                    sig = inspect.signature(obj)
                    sig_str = str(sig)
                except (ValueError, TypeError):
                    sig_str = "()"
                
                # Get source file and module
                source_file = None
                source_module = None
                try:
                    source_file = inspect.getsourcefile(obj)
                    if source_file:
                        source_file = str(Path(source_file))
                    # Try to get the module name
                    if hasattr(obj, "__module__"):
                        source_module = obj.__module__
                except (TypeError, OSError):
                    pass
                
                # Use actual source file if available, otherwise use ed_workflows.py
                display_file_path = source_file if source_file else str(workflows_path)
                
                workflows.append({
                    "name": name,
                    "is_async": inspect.iscoroutinefunction(obj),
                    "signature": sig_str,
                    "file_path": display_file_path,
                    "source_file": source_file,
                    "source_module": source_module,
                })
    except Exception as e:
        print(f"Warning: Failed to scan ed_workflows.py: {e}")
    
    return workflows


def open_browser(url: str) -> None:
    """Open URL in default browser (platform-aware)."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", url])
    elif sys.platform == "linux":
        subprocess.Popen(["xdg-open", url])
    elif sys.platform == "win32":
        subprocess.Popen(["start", url], shell=True)


async def start_dashboard_server(
    cwd: Path,
    port: int = 4573,
    auto_open: bool = True,
) -> web.AppRunner:
    """Start dashboard server and optionally open browser.
    
    Args:
        cwd: Project root directory
        port: Server port
        auto_open: Whether to auto-open browser
    
    Returns:
        AppRunner that can be awaited/cleaned up
    """
    # Scan workflows once at startup
    workflows = scan_workflows(cwd)
    
    # Create aiohttp app
    app = web.Application()
    
    # API endpoint
    async def api_workflows(request: web.Request) -> web.Response:
        """Return list of workflows as JSON."""
        return web.json_response({"workflows": workflows})
    
    app.router.add_get("/api/workflows", api_workflows)
    
    # Serve dashboard HTML
    async def dashboard(request: web.Request) -> web.Response:
        html = _get_dashboard_html()
        return web.Response(text=html, content_type="text/html")
    
    app.router.add_get("/", dashboard)
    app.router.add_get("/dashboard", dashboard)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", port)
    await site.start()
    
    url = f"http://localhost:{port}"
    print(f"Dashboard running at {url}")
    
    if auto_open:
        open_browser(url)
    
    return runner


def _get_dashboard_html() -> str:
    """Return inline dashboard HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ElasticDash Workflows</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        h1 {
            font-size: 28px;
            margin-bottom: 16px;
            color: #1a1a1a;
        }
        
        .search-box {
            display: flex;
            gap: 10px;
        }
        
        input[type="text"] {
            flex: 1;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #0066cc;
            box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
        }
        
        .result-count {
            padding: 10px 12px;
            background: #f0f0f0;
            border-radius: 6px;
            font-size: 14px;
            color: #666;
        }
        
        .workflows-list {
            display: grid;
            gap: 12px;
        }
        
        .workflow-card {
            background: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.2s;
            border-left: 4px solid #0066cc;
        }
        
        .workflow-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }
        
        .workflow-card.hidden {
            display: none;
        }
        
        .workflow-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }
        
        .workflow-name {
            font-weight: 600;
            font-size: 16px;
            color: #1a1a1a;
            font-family: "Monaco", "Courier New", monospace;
        }
        
        .async-badge {
            display: inline-block;
            background: #e8f3ff;
            color: #0066cc;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .workflow-signature {
            font-family: "Monaco", "Courier New", monospace;
            font-size: 12px;
            color: #666;
            background: #f9f9f9;
            padding: 6px 8px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre;
        }
        
        .workflow-path {
            font-size: 12px;
            color: #999;
            margin-top: 8px;
            font-family: "Monaco", "Courier New", monospace;
        }
        
        .workflow-source {
            font-size: 12px;
            color: #0066cc;
            margin-top: 4px;
            font-family: "Monaco", "Courier New", monospace;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #999;
        }
        
        .empty-state p {
            margin: 8px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ElasticDash Workflows</h1>
            <div class="search-box">
                <input 
                    type="text" 
                    id="searchInput" 
                    placeholder="Search workflows by name, source module, or file path..."
                    autocomplete="off"
                >
                <div class="result-count">
                    <span id="resultCount">0</span> workflows
                </div>
            </div>
        </header>
        
        <div id="workflowsContainer" class="workflows-list">
            <div class="empty-state">
                <p>Loading workflows...</p>
            </div>
        </div>
    </div>
    
    <script>
        const searchInput = document.getElementById("searchInput");
        const workflowsContainer = document.getElementById("workflowsContainer");
        const resultCount = document.getElementById("resultCount");
        
        let allWorkflows = [];
        
        async function loadWorkflows() {
            try {
                const res = await fetch("/api/workflows");
                const data = await res.json();
                allWorkflows = data.workflows || [];
                renderWorkflows();
            } catch (err) {
                workflowsContainer.innerHTML = `
                    <div class="empty-state">
                        <p>Failed to load workflows</p>
                        <p>${err.message}</p>
                    </div>
                `;
            }
        }
        
        function filterWorkflows(searchTerm) {
            if (!searchTerm.trim()) {
                return allWorkflows;
            }
            
            const term = searchTerm.toLowerCase();
            return allWorkflows.filter(w => 
                w.name.toLowerCase().includes(term) ||
                w.file_path.toLowerCase().includes(term) ||
                (w.source_module && w.source_module.toLowerCase().includes(term)) ||
                (w.source_file && w.source_file.toLowerCase().includes(term))
            );
        }
        
        function renderWorkflows(searchTerm = "") {
            const filtered = filterWorkflows(searchTerm);
            resultCount.textContent = filtered.length;
            
            if (filtered.length === 0) {
                workflowsContainer.innerHTML = `
                    <div class="empty-state">
                        <p>${allWorkflows.length === 0 ? "No workflows found" : "No results matching your search"}</p>
                    </div>
                `;
                return;
            }
            
            workflowsContainer.innerHTML = filtered.map(w => `
                <div class="workflow-card">
                    <div class="workflow-header">
                        <span class="workflow-name">${escapeHtml(w.name)}</span>
                        ${w.is_async ? '<span class="async-badge">async</span>' : ''}
                    </div>
                    <div class="workflow-signature">${escapeHtml(w.name)}${escapeHtml(w.signature)}</div>
                    ${w.source_module ? `<div class="workflow-source">from ${escapeHtml(w.source_module)}</div>` : ''}
                    <div class="workflow-path">${escapeHtml(w.file_path)}</div>
                </div>
            `).join("");
        }
        
        function escapeHtml(text) {
            const div = document.createElement("div");
            div.textContent = text;
            return div.innerHTML;
        }
        
        searchInput.addEventListener("input", (e) => {
            renderWorkflows(e.target.value);
        });
        
        // Load workflows on page load
        loadWorkflows();
    </script>
</body>
</html>"""

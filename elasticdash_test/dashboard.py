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

from aiohttp import web # type: ignore


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
                source_code = None
                try:
                    source_file = inspect.getsourcefile(obj)
                    if source_file:
                        source_file = str(Path(source_file))
                    # Try to get the module name
                    if hasattr(obj, "__module__"):
                        source_module = obj.__module__
                    # Get source code
                    source_code = inspect.getsource(obj)
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
                    "source_code": source_code,
                })
    except Exception as e:
        print(f"Warning: Failed to scan ed_workflows.py: {e}")
    
    return workflows


def scan_tools(cwd: Path) -> list[dict[str, Any]]:
    """Scan ed_tools.py for callable functions.
    
    Returns list of dicts with keys: name, is_async, signature, file_path, source_code
    """
    tools_path = cwd / "ed_tools.py"
    tools = []
    
    if not tools_path.exists():
        return tools
    
    try:
        spec = importlib.util.spec_from_file_location("ed_tools", tools_path)
        if not spec or not spec.loader:
            return tools
        
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
                
                # Get source info
                source_file = None
                source_module = None
                source_code = None
                try:
                    source_file = inspect.getsourcefile(obj)
                    if source_file:
                        source_file = str(Path(source_file))
                    if hasattr(obj, "__module__"):
                        source_module = obj.__module__
                    source_code = inspect.getsource(obj)
                except (TypeError, OSError):
                    pass
                
                display_file_path = source_file if source_file else str(tools_path)
                
                tools.append({
                    "name": name,
                    "is_async": inspect.iscoroutinefunction(obj),
                    "signature": sig_str,
                    "file_path": display_file_path,
                    "source_file": source_file,
                    "source_module": source_module,
                    "source_code": source_code,
                })
    except Exception as e:
        print(f"Warning: Failed to scan ed_tools.py: {e}")
    
    return tools


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
    tools = scan_tools(cwd)
    
    # Create aiohttp app
    app = web.Application()
    
    # API endpoint
    async def api_workflows(request: web.Request) -> web.Response:
        """Return list of workflows as JSON."""
        return web.json_response({"workflows": workflows})
    
    async def api_code_index(request: web.Request) -> web.Response:
        """Return combined index of workflows and tools for matching."""
        return web.json_response({
            "workflows": workflows,
            "tools": tools
        })
    
    app.router.add_get("/api/workflows", api_workflows)
    app.router.add_get("/api/code-index", api_code_index)
    
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
    <title>ElasticDash Dashboard</title>
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
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
            max-height: 60vh;
            display: flex;
            flex-direction: column;
        }
        
        .workflows-table {
            width: 100%;
            border-collapse: collapse;
            flex: 1;
            overflow-y: auto;
        }
        
        .workflows-table thead {
            background: #f5f5f5;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .workflows-table th {
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            color: #333;
            border-bottom: 2px solid #ddd;
        }
        
        .workflows-table td {
            padding: 12px 16px;
            border-bottom: 1px solid #eee;
            vertical-align: middle;
        }
        
        .workflows-table tbody tr {
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .workflows-table tbody tr:hover {
            background-color: #f9f9f9;
        }
        
        .workflows-table tbody tr:active {
            background-color: #e8f3ff;
        }
        
        .workflow-name-cell {
            font-family: "Monaco", "Courier New", monospace;
            font-weight: 600;
            color: #0066cc;
            white-space: nowrap;
        }
        
        .workflow-path-cell {
            font-family: "Monaco", "Courier New", monospace;
            font-size: 12px;
            color: #666;
            overflow-x: auto;
            word-break: break-all;
            max-width: 400px;
        }
        
        .async-badge {
            display: inline-block;
            background: #e8f3ff;
            color: #0066cc;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            margin-left: 8px;
            white-space: nowrap;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #999;
        }
        
        .empty-state p {
            margin: 8px 0;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal.open {
            display: flex;
        }
        
        .modal-content {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 90%;
            max-width: 600px;
            max-height: 90vh;
            overflow-y: auto;
            padding: 30px;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        
        .modal-title {
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #999;
            transition: color 0.2s;
        }
        
        .modal-close:hover {
            color: #333;
        }
        
        .modal-intro {
            background: #f0f7ff;
            border-left: 4px solid #0066cc;
            padding: 12px 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
        }
        
        .modal-intro strong {
            color: #0066cc;
        }
        
        .modal-intro ol {
            margin: 8px 0 0 20px;
            padding: 0;
        }
        
        .modal-intro li {
            margin: 6px 0;
        }
        
        .upload-area {
            border: 2px dashed #ddd;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            background: #fafafa;
        }
        
        .upload-area:hover {
            border-color: #0066cc;
            background: #f0f7ff;
        }
        
        .upload-area.drag-over {
            border-color: #0066cc;
            background: #e8f3ff;
        }
        
        .upload-icon {
            font-size: 32px;
            margin-bottom: 12px;
        }
        
        .upload-text {
            font-weight: 500;
            margin-bottom: 4px;
            color: #1a1a1a;
        }
        
        .upload-hint {
            font-size: 13px;
            color: #999;
        }
        
        input[type="file"] {
            display: none;
        }
        
        .upload-status {
            margin-top: 20px;
            padding: 12px;
            border-radius: 6px;
            font-size: 14px;
            display: none;
        }
        
        .upload-status.success {
            display: block;
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #c8e6c9;
        }
        
        .upload-status.error {
            display: block;
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ffcdd2;
        }
        
        .trace-viewer {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
            border: 1px solid #ddd;
        }
        
        .trace-viewer.visible {
            display: block;
        }
        
        .trace-header {
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid #0066cc;
        }
        
        .trace-title {
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 8px;
        }
        
        .trace-meta {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            font-size: 13px;
            color: #666;
        }
        
        .trace-meta-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .trace-meta-item strong {
            color: #333;
        }
        
        .trace-section {
            margin-bottom: 16px;
        }
        
        .trace-section-title {
            font-size: 14px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 8px;
            padding: 8px 0;
            border-bottom: 1px solid #ddd;
        }
        
        .trace-io {
            background: white;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            font-size: 13px;
            line-height: 1.6;
        }
        
        .trace-io strong {
            display: block;
            margin-bottom: 4px;
            color: #0066cc;
        }
        
        .observation-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .observation-card {
            background: white;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #0066cc;
            font-size: 13px;
        }
        
        .observation-card.generation {
            border-left-color: #4caf50;
        }
        
        .observation-card.span {
            border-left-color: #ff9800;
        }
        
        .observation-card.tool {
            border-left-color: #9c27b0;
        }
        
        .observation-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        
        .observation-name {
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .observation-type {
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 3px;
            background: #e0e0e0;
            color: #666;
        }
        
        .observation-type.generation {
            background: #e8f5e9;
            color: #2e7d32;
        }
        
        .observation-type.span {
            background: #fff3e0;
            color: #e65100;
        }
        
        .observation-type.tool {
            background: #f3e5f5;
            color: #6a1b9a;
        }
        
        .observation-details {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            color: #666;
            font-size: 12px;
            margin-top: 6px;
        }
        
        .observation-cost {
            color: #0066cc;
            font-weight: 500;
        }
        
        .observation-match {
            margin-top: 10px;
            padding: 10px;
            background: #f0f7ff;
            border-radius: 4px;
            border-left: 3px solid #0066cc;
        }
        
        .observation-match-header {
            font-size: 12px;
            color: #0066cc;
            font-weight: 600;
            margin-bottom: 6px;
        }
        
        .observation-match-code {
            font-family: "Monaco", "Courier New", monospace;
            font-size: 11px;
            color: #333;
            background: white;
            padding: 8px;
            border-radius: 3px;
            overflow-x: auto;
            white-space: pre;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .observation-match-path {
            font-size: 11px;
            color: #666;
            margin-top: 4px;
        }
        
        .scores-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
        }
        
        .score-card {
            background: white;
            padding: 10px 12px;
            border-radius: 6px;
            border-left: 3px solid #0066cc;
        }
        
        .score-name {
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
        }
        
        .score-value {
            font-size: 18px;
            font-weight: 700;
            color: #1a1a1a;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Select Workflow Function to be Fixed</h1>
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
            <table class="workflows-table">
                <thead>
                    <tr>
                        <th style="width: 30%">Function Name</th>
                        <th style="width: 70%">File Path</th>
                    </tr>
                </thead>
                <tbody id="workflowsTableBody">
                    <tr>
                        <td colspan="2" class="empty-state" style="text-align: center; padding: 40px;">Loading workflows...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Trace Upload Modal -->
    <div id="traceModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Step 2: Import Failed Trace</h2>
                <button class="modal-close" id="closeModal">&times;</button>
            </div>
            
            <div class="modal-intro">
                <strong>Prepare to debug workflow execution:</strong>
                <ol>
                    <li>Export a trace from <strong>Langfuse</strong> for the failed workflow execution</li>
                    <li>Upload the trace file below (typically a JSON export)</li>
                    <li>The trace will be analyzed to help you understand what went wrong</li>
                </ol>
            </div>
            
            <div id="uploadArea" class="upload-area">
                <div class="upload-icon">📤</div>
                <div class="upload-text">Drop trace file here or click to select</div>
                <div class="upload-hint">JSON trace export from Langfuse</div>
                <input type="file" id="traceFile" accept=".json,.jsonl,.txt" />
            </div>
            
            <div id="uploadStatus" class="upload-status"></div>
            
            <div id="traceViewer" class="trace-viewer">
                <div class="trace-header">
                    <div class="trace-title" id="traceName">Loading...</div>
                    <div class="trace-meta" id="traceMeta"></div>
                </div>
                
                <div class="trace-section">
                    <div class="trace-section-title">Input & Output</div>
                    <div class="trace-io">
                        <strong>Input:</strong>
                        <div id="traceInput">-</div>
                    </div>
                    <div class="trace-io">
                        <strong>Output:</strong>
                        <div id="traceOutput">-</div>
                    </div>
                </div>
                
                <div class="trace-section" id="scoresSection" style="display: none;">
                    <div class="trace-section-title">Evaluation Scores</div>
                    <div class="scores-grid" id="scoresGrid"></div>
                </div>
                
                <div class="trace-section">
                    <div class="trace-section-title">Observations</div>
                    <div class="observation-list" id="observationList"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const searchInput = document.getElementById("searchInput");
        const workflowsContainer = document.getElementById("workflowsContainer");
        const resultCount = document.getElementById("resultCount");
        const traceModal = document.getElementById("traceModal");
        const closeModal = document.getElementById("closeModal");
        const uploadArea = document.getElementById("uploadArea");
        const traceFile = document.getElementById("traceFile");
        const uploadStatus = document.getElementById("uploadStatus");
        
        let allWorkflows = [];
        let workflowsMap = new Map(); // Map to store workflows by index
        let selectedWorkflow = null;
        let codeIndex = { workflows: [], tools: [] }; // Store all available code
        
        // Modal controls
        closeModal.addEventListener("click", () => {
            traceModal.classList.remove("open");
            uploadStatus.className = "upload-status";
            uploadStatus.textContent = "";
            traceFile.value = "";
        });
        
        traceModal.addEventListener("click", (e) => {
            if (e.target === traceModal) {
                traceModal.classList.remove("open");
                uploadStatus.className = "upload-status";
                uploadStatus.textContent = "";
                traceFile.value = "";
            }
        });
        
        // Upload area drag and drop
        uploadArea.addEventListener("click", () => {
            traceFile.click();
        });
        
        uploadArea.addEventListener("dragover", (e) => {
            e.preventDefault();
            uploadArea.classList.add("drag-over");
        });
        
        uploadArea.addEventListener("dragleave", () => {
            uploadArea.classList.remove("drag-over");
        });
        
        uploadArea.addEventListener("drop", (e) => {
            e.preventDefault();
            uploadArea.classList.remove("drag-over");
            if (e.dataTransfer.files.length > 0) {
                traceFile.files = e.dataTransfer.files;
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });
        
        traceFile.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                handleFileUpload(e.target.files[0]);
            }
        });
        
        function handleFileUpload(file) {
            uploadStatus.className = "upload-status";
            uploadStatus.textContent = "";
            document.getElementById("traceViewer").classList.remove("visible");
            
            if (!file.name.match(/\.(json|jsonl|txt)$/i)) {
                uploadStatus.className = "upload-status error";
                uploadStatus.textContent = "❌ Invalid file format. Please upload a JSON, JSONL, or TXT file.";
                return;
            }
            
            if (file.size > 50 * 1024 * 1024) {
                uploadStatus.className = "upload-status error";
                uploadStatus.textContent = "❌ File too large. Maximum size is 50MB.";
                return;
            }
            
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const content = e.target.result;
                    let traceData;
                    
                    // Try to parse as JSON
                    try {
                        traceData = JSON.parse(content);
                    } catch (parseErr) {
                        uploadStatus.className = "upload-status error";
                        uploadStatus.textContent = `❌ Invalid JSON format: ${parseErr.message}`;
                        return;
                    }
                    
                    uploadStatus.className = "upload-status success";
                    uploadStatus.textContent = `✓ Successfully loaded trace file: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
                    
                    // Display the trace
                    displayTrace(traceData);
                    
                    console.log("Trace loaded:", {
                        workflow: selectedWorkflow.name,
                        filename: file.name,
                        size: file.size,
                        timestamp: new Date().toISOString(),
                        traceId: traceData.trace?.id
                    });
                } catch (err) {
                    uploadStatus.className = "upload-status error";
                    uploadStatus.textContent = `❌ Error processing trace: ${err.message}`;
                }
            };
            reader.onerror = () => {
                uploadStatus.className = "upload-status error";
                uploadStatus.textContent = "❌ Error reading file.";
            };
            reader.readAsText(file);
        }
        
        // Match observation to source code by exact name
        function matchObservationToCode(obs) {
            const obsName = obs.name || '';
            const obsType = (obs.type || '').toUpperCase();
            
            // For TOOL observations, match by exact name
            if (obsType === 'TOOL') {
                // Search in tools first
                for (const tool of codeIndex.tools) {
                    if (tool.name === obsName) {
                        return tool;
                    }
                }
                
                // Search in workflows as fallback
                for (const workflow of codeIndex.workflows) {
                    if (workflow.name === obsName) {
                        return workflow;
                    }
                }
            }
            
            // For GENERATION observations, match by prompt name
            if (obsType === 'GENERATION') {
                const promptName = obs.promptName || '';
                if (promptName) {
                    for (const workflow of codeIndex.workflows) {
                        if (workflow.name === promptName) {
                            return workflow;
                        }
                    }
                }
            }
            
            return null;
        }
        
        function displayTrace(data) {
            const traceViewer = document.getElementById("traceViewer");
            const trace = data.trace || data;
            
            // Trace header
            document.getElementById("traceName").textContent = trace.name || "Unnamed Trace";
            
            // Meta information
            const meta = [];
            if (trace.id) meta.push(`<span class="trace-meta-item"><strong>ID:</strong> ${escapeHtml(trace.id.substring(0, 8))}...</span>`);
            if (trace.timestamp) {
                const date = new Date(trace.timestamp);
                meta.push(`<span class="trace-meta-item"><strong>Time:</strong> ${date.toLocaleString()}</span>`);
            }
            if (trace.latency) meta.push(`<span class="trace-meta-item"><strong>Duration:</strong> ${trace.latency.toFixed(2)}s</span>`);
            if (trace.userId) meta.push(`<span class="trace-meta-item"><strong>User:</strong> ${escapeHtml(trace.userId.substring(0, 12))}...</span>`);
            document.getElementById("traceMeta").innerHTML = meta.join("");
            
            // Input & Output
            document.getElementById("traceInput").textContent = formatIO(trace.input);
            document.getElementById("traceOutput").textContent = formatIO(trace.output);
            
            // Scores
            if (trace.scores && trace.scores.length > 0) {
                document.getElementById("scoresSection").style.display = "block";
                const scoresGrid = document.getElementById("scoresGrid");
                scoresGrid.innerHTML = trace.scores.map(score => `
                    <div class="score-card">
                        <div class="score-name">${escapeHtml(score.name)}</div>
                        <div class="score-value">${score.value !== null ? score.value : 'N/A'}</div>
                    </div>
                `).join("");
            } else {
                document.getElementById("scoresSection").style.display = "none";
            }
            
            // Observations - filter to only GENERATION and TOOL
            const observations = data.observations || trace.observations || [];
            const filteredObservations = observations.filter(obs => {
                const type = (obs.type || '').toUpperCase();
                return type === 'GENERATION' || type === 'TOOL';
            });
            
            const observationList = document.getElementById("observationList");
            observationList.innerHTML = filteredObservations.map(obs => {
                const details = [];
                if (obs.latency) details.push(`⏱️ ${obs.latency.toFixed(3)}s`);
                if (obs.totalCost) details.push(`<span class="observation-cost">💰 $${obs.totalCost.toFixed(6)}</span>`);
                if (obs.model) details.push(`🤖 ${escapeHtml(obs.model)}`);
                if (obs.totalUsage) details.push(`📊 ${obs.totalUsage} tokens`);
                
                const type = (obs.type || 'span').toLowerCase();
                
                // Try to match observation to source code
                const matchedCode = matchObservationToCode(obs);
                let matchHtml = '';
                if (matchedCode && matchedCode.source_code) {
                    matchHtml = `
                        <div class="observation-match">
                            <div class="observation-match-header">📂 Matched Function:</div>
                            <div class="observation-match-code">${escapeHtml(matchedCode.source_code)}</div>
                            <div class="observation-match-path">📁 ${escapeHtml(matchedCode.file_path)}</div>
                        </div>
                    `;
                }
                
                return `
                    <div class="observation-card ${type}">
                        <div class="observation-header">
                            <span class="observation-name">${escapeHtml(obs.name || obs.id)}</span>
                            <span class="observation-type ${type}">${obs.type || 'SPAN'}</span>
                        </div>
                        ${details.length > 0 ? `<div class="observation-details">${details.join(' • ')}</div>` : ''}
                        ${matchHtml}
                    </div>
                `;
            }).join("");
            
            // Show trace viewer
            traceViewer.classList.add("visible");
        }
        
        function formatIO(text) {
            if (!text) return "-";
            try {
                // Try to parse if it's a JSON string
                const parsed = JSON.parse(text);
                if (typeof parsed === "string") return parsed;
                return JSON.stringify(parsed, null, 2);
            } catch {
                return text;
            }
        }
        
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
        
        async function loadCodeIndex() {
            try {
                const res = await fetch("/api/code-index");
                const data = await res.json();
                codeIndex = data;
                console.log("Code index loaded:", {
                    workflows: codeIndex.workflows.length,
                    tools: codeIndex.tools.length
                });
            } catch (err) {
                console.error("Failed to load code index:", err);
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
            const tableBody = document.getElementById("workflowsTableBody");
            
            if (filtered.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="2" style="text-align: center; padding: 40px; color: #999;">
                            ${allWorkflows.length === 0 ? "No workflows found" : "No results matching your search"}
                        </td>
                    </tr>
                `;
                return;
            }
            
            // Clear the map and rebuild
            workflowsMap.clear();
            
            tableBody.innerHTML = filtered.map((w, index) => {
                workflowsMap.set(index, w);
                return `
                    <tr data-workflow-index="${index}">
                        <td>
                            <div class="workflow-name-cell">
                                ${escapeHtml(w.name)}
                                ${w.is_async ? '<span class="async-badge">async</span>' : ''}
                            </div>
                        </td>
                        <td>
                            <div class="workflow-path-cell">${escapeHtml(w.file_path)}</div>
                        </td>
                    </tr>
                `;
            }).join("");
            
            // Attach click handlers to table rows
            document.querySelectorAll("#workflowsTableBody tr[data-workflow-index]").forEach(row => {
                row.addEventListener("click", () => {
                    const index = parseInt(row.dataset.workflowIndex);
                    selectedWorkflow = workflowsMap.get(index);
                    traceModal.classList.add("open");
                    uploadStatus.className = "upload-status";
                    uploadStatus.textContent = "";
                    traceFile.value = "";
                });
            });
        }
        
        function escapeHtml(text) {
            const div = document.createElement("div");
            div.textContent = text;
            return div.innerHTML;
        }
        
        searchInput.addEventListener("input", (e) => {
            renderWorkflows(e.target.value);
        });
        
        // Load workflows and code index on page load
        loadWorkflows();
        loadCodeIndex();
    </script>
</body>
</html>"""

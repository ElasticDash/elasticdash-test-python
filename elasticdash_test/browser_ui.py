"""Simple SSE browser UI server."""
from __future__ import annotations

import asyncio
import json
import os
import socket
import webbrowser
from dataclasses import dataclass, field
from typing import Any, List

from aiohttp import web


@dataclass
class BrowserUIServer:
    app: web.Application
    runner: web.AppRunner
    site: web.TCPSite
    queues: List[asyncio.Queue] = field(default_factory=list)
    history: List[dict] = field(default_factory=list)

    def send(self, event: dict):
        self.history.append(event)
        for queue in list(self.queues):
            queue.put_nowait(event)

    async def _sse_handler(self, request: web.Request):
        queue: asyncio.Queue = asyncio.Queue()
        self.queues.append(queue)
        response = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await response.prepare(request)

        # Replay history to late joiners
        for event in self.history:
            await response.write(_format_sse(event))

        try:
            while True:
                event = await queue.get()
                await response.write(_format_sse(event))
        except asyncio.CancelledError:
            pass
        finally:
            self.queues.remove(queue)
            await response.write_eof()
        return response

    async def _index(self, request: web.Request):
        return web.Response(text=_INDEX_HTML, content_type="text/html")

    def close(self):
        async def _shutdown():
            await self.site.stop()
            await self.runner.cleanup()

        asyncio.create_task(_shutdown())


async def start_browser_ui_server(port: int = 4571, auto_open: bool = True) -> BrowserUIServer:
    app = web.Application()
    server = BrowserUIServer(app=app, runner=None, site=None)  # type: ignore[arg-type]

    app.router.add_get("/", server._index)
    app.router.add_get("/events", server._sse_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    server.runner = runner
    server.site = site

    if auto_open:
        _open_browser(port)
    return server


def _open_browser(port: int):
    url = f"http://localhost:{port}/"
    try:
        webbrowser.open(url)
    except Exception:
        pass


def _format_sse(event: dict) -> bytes:
    data = json.dumps(event)
    return f"data: {data}\n\n".encode()


_INDEX_HTML = """<!doctype html>
<html>
<head>
  <title>elasticdash tests</title>
  <style>
    body { font-family: sans-serif; background: #0b1021; color: #e6ecff; margin: 0; padding: 24px; }
    .card { background: #121a33; border: 1px solid #1f2a4d; border-radius: 10px; padding: 16px; margin-bottom: 12px; }
    .pass { color: #7bd88f; }
    .fail { color: #ff8c8c; }
    .pending { color: #f1fa8c; }
    .header { font-size: 18px; margin-bottom: 8px; }
  </style>
</head>
<body>
  <div class="header">elasticdash test run</div>
  <div id="list"></div>
  <script>
    const list = document.getElementById('list');
    const state = new Map();

    function render() {
      list.innerHTML = '';
      for (const [key, value] of state.entries()) {
        const div = document.createElement('div');
        div.className = 'card';
        const statusClass = value.status === 'passed' ? 'pass' : value.status === 'failed' ? 'fail' : 'pending';
        div.innerHTML = `<div><strong>${value.name}</strong></div>` +
          `<div class="${statusClass}">${value.status}</div>` +
          `<div>${value.duration ? value.duration.toFixed(2) + 's' : ''}</div>` +
          (value.error ? `<div>${value.error}</div>` : '');
        list.appendChild(div);
      }
    }

    const es = new EventSource('/events');
    es.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data);
        if (event.type === 'test-finish') {
          const key = `${event.payload.file}:${event.payload.name}`;
          state.set(key, event.payload);
          render();
        }
      } catch (e) { console.error(e); }
    };
  </script>
</body>
</html>
"""

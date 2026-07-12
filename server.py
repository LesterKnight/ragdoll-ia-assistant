#!/usr/bin/env python3
"""Servidor web do ragdoll (antigo monitor.py).

- HTTP na porta 8765 serve as paginas (frontend/observer).
- WebSocket na porta 8766 empurra os logs ao vivo.
- O banco (RAG/log.db) e o unico contrato: o pipeline so escreve (loghub);
  este servidor so le e empurra. Nenhum dos lados conhece o outro.

Fluxo: ao abrir, a pagina manda o `site` pelo WS; o servidor envia o SNAPSHOT
(ultimas N do site, ordem cronologica) e, em seguida, empurra cada linha nova
(pattern observer: a pagina so recebe o que mudou).

Uso:
    python server.py --site docsgodotengineorg [--port 8765]
"""
import asyncio
import json
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import websockets

import logdb
from templates import TEMPLATE, TEMPLATE_NOVO, MAIN_TABS, RAG_TABS, BACK_LINK

HTTP_PORT = 8765
WS_PORT = 8766
SITE = ""

MOCK_DISPLAY = {
    "docsgodotengineorg": "docsgodotengine.org",
    "godotengineorg": "godotengine.org",
    "docsunity3dcom": "docs.unity3d.com",
}


def resolve_display_domain(site: str) -> str:
    dom = logdb.site_progress(site).get("domain")
    if dom:
        return dom
    return MOCK_DISPLAY.get(site, site)


async def handler(websocket):
    try:
        site = await websocket.recv()
    except Exception:
        return
    if not site:
        return
    snap = logdb.recent(site, 500)
    last_id = snap[-1]["id"] if snap else 0
    prog = logdb.site_progress(site)
    await websocket.send(json.dumps(prog))
    await websocket.send(json.dumps({"type": "snapshot", "rows": snap}))
    try:
        while True:
            rows = logdb.after(site, last_id)
            if rows:
                last_id = rows[-1]["id"]
                for r in rows:
                    await websocket.send(json.dumps({"type": "event", "row": r}))
            await asyncio.sleep(0.5)
    except websockets.exceptions.ConnectionClosed:
        return


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            site, tabs, back = SITE, MAIN_TABS, ""
            domain_disp = ""
        elif path.startswith("/rag/"):
            domain = path[len("/rag/"):].strip("/")
            if not domain:
                self.redirect("/")
                return
            site, tabs, back = domain, RAG_TABS, BACK_LINK
            domain_disp = resolve_display_domain(domain)
        elif path in ("/novo", "/novo/"):
            body = TEMPLATE_NOVO.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"pagina nao encontrada")
            return
        body = (TEMPLATE
                .replace("__SITE__", site or "")
                .replace("__DOMAIN__", domain_disp or "")
                .replace("__WSPORT__", str(WS_PORT))
                .replace("__TABS__", tabs)
                .replace("__BACK__", back)
                ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, loc):
        self.send_response(302)
        self.send_header("Location", loc)
        self.end_headers()

    def log_message(self, *a):
        pass


def main():
    global SITE, HTTP_PORT, WS_PORT
    http_port = HTTP_PORT
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--site":
            SITE = args[i + 1]
            i += 2
            continue
        if a == "--port":
            http_port = int(args[i + 1])
            i += 2
            continue
        i += 1
    if not SITE:
        SITE = logdb._autosite()
    HTTP_PORT = http_port
    WS_PORT = http_port + 1
    threading.Thread(
        target=lambda: ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), H).serve_forever(),
        daemon=True,
    ).start()
    print(f"Servidor ragdoll: http://0.0.0.0:{HTTP_PORT}  (WebSocket :{WS_PORT}, site={SITE})")

    async def serve():
        async with websockets.serve(handler, "0.0.0.0", WS_PORT):
            await asyncio.Future()

    asyncio.run(serve())


if __name__ == "__main__":
    main()

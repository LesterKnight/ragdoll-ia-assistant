#!/usr/bin/env python3
"""Servidor web do RagThulhu (antigo monitor.py).

- HTTP na porta 8765 serve as paginas (frontend/observer).
- WebSocket na porta 8766 empurra os logs ao vivo + status (observer pattern).
- O banco (RAG/log.db) e o unico contrato: o pipeline so escreve (loghub);
  este servidor so le e empurra. Nenhum dos lados conhece o outro.

Alem do monitor, expoe a API JSON que liga o frontend as funcionalidades de
backend (run/query/programador/benchmark/gerenciamento de bases).

Uso:
    python server.py --site docsgodotengineorg [--port 8765]
"""
import asyncio
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import websockets

import logdb
import config_util
from templates import TEMPLATE, TEMPLATE_NOVO, MAIN_TABS, RAG_TABS, BACK_LINK

HTTP_PORT = 8765
WS_PORT = 8766
SITE = ""

ROOT = Path(__file__).resolve().parent
DETACHED = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
SLUG_RE = re.compile(r"^[a-z0-9]+$")


def simplify_domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return re.sub(r"[^a-z0-9]", "", host.lower())


def display_domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host


def run_detached(script: str, args: list) -> int:
    """Dispara um script em background isolado (nao bloqueia a requisicao)."""
    cmd = [sys.executable, str(ROOT / script)] + args
    if os.name == "nt":
        proc = subprocess.Popen(cmd, creationflags=DETACHED,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        proc = subprocess.Popen(cmd, start_new_session=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.pid


def run_capture(script: str, args: list, timeout: int = 320) -> tuple:
    """Roda um script e captura stdout/stderr (para query/programador)."""
    cmd = [sys.executable, str(ROOT / script)] + args
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        return -1, (e.stdout or ""), "tempo esgotado (generacao muito longa)"


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
    await websocket.send(json.dumps(logdb.site_status(site)))
    await websocket.send(json.dumps({"type": "snapshot", "rows": snap}))
    try:
        while True:
            rows = logdb.after(site, last_id)
            if rows:
                last_id = rows[-1]["id"]
                for r in rows:
                    await websocket.send(json.dumps({"type": "event", "row": r}))
            await websocket.send(json.dumps(logdb.site_status(site)))
            await asyncio.sleep(0.5)
    except websockets.exceptions.ConnectionClosed:
        return


class H(BaseHTTPRequestHandler):
    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _body_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._page(SITE, MAIN_TABS, "")
            return
        if path.startswith("/rag/"):
            domain = path[len("/rag/"):].strip("/")
            if not domain:
                self.redirect("/")
                return
            if not SLUG_RE.match(domain):
                self._json({"error": "dominio invalido"}, 400)
                return
            self._page(domain, RAG_TABS, BACK_LINK)
            return
        if path in ("/novo", "/novo/"):
            self._send(200, TEMPLATE_NOVO.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/bases":
            self._json({"bases": logdb.list_bases()})
            return
        if path.startswith("/api/bench/"):
            slug = path[len("/api/bench/"):].strip("/")
            if not SLUG_RE.match(slug):
                self._json({"error": "dominio invalido"}, 400)
                return
            recs = logdb._bench_records(slug)
            tests = []
            for r in recs:
                rag = r.get("rag", {}) or {}
                norag = r.get("norag", {}) or {}
                tests.append({
                    "n": r.get("n"), "q": r.get("q"), "time_s": r.get("time_s"),
                    "ragOk": bool(rag.get("pass")), "noragOk": bool(norag.get("pass")),
                    "ragVal": rag.get("val"), "noragVal": norag.get("val"),
                })
            self._json({"domain": slug, "total": len(tests), "done": len(tests), "tests": tests})
            return
        if path == "/api/config":
            self._json({"schema": config_util.SCHEMA, "values": config_util.load_config()})
            return
        self._send(404, b"pagina nao encontrada", "text/plain; charset=utf-8")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        data = self._body_json()

        # ---- criar/rodar nova base (Fase A->B->C) ----
        if path == "/api/run":
            url = (data.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                self._json({"error": "url invalida (use http/https)"}, 400)
                return
            slug = simplify_domain(url)
            if not SLUG_RE.match(slug):
                self._json({"error": "nao foi possivel derivar o dominio"}, 400)
                return
            escopo = int(data.get("escopo") or 2)
            delay = int(data.get("delay") or 2000)
            args = ["all", "--url", url, "--escopo", str(escopo), "--delay", str(delay)]
            limite = data.get("limite")
            if limite:
                args += ["--limite", str(int(limite))]
            run_detached("run.py", args)
            self._json({"slug": slug, "domain": display_domain(url),
                        "message": "pipeline iniciado em background"})
            return

        # ---- benchmark (Etapa D) ----
        if path == "/api/bench":
            slug = (data.get("dominio") or "").strip()
            if not SLUG_RE.match(slug):
                self._json({"error": "dominio invalido"}, 400)
                return
            bench = config_util.load_config().get("benchmark", {})
            tasks = data.get("tasks") or bench.get("tasks") or str(ROOT / "stage_d" / "tasks_godot.json")
            lang = data.get("lang") or bench.get("lang") or "GDScript"
            ext = data.get("ext") or bench.get("ext") or "gd"
            mode = data.get("mode") or bench.get("mode") or "code"
            model = data.get("model") or bench.get("model") or "qwen2.5-coder:7b"
            topk = int(data.get("topk") or bench.get("topk") or 15)
            num_predict = int(data.get("num_predict") or bench.get("num_predict") or 600)
            temperature = float(data.get("temperature") or bench.get("temperature") or 0.2)
            validator = data.get("validator") or ""
            tasks_path = tasks if os.path.isabs(tasks) else str(ROOT / tasks)
            args = ["--domain", slug, "--mode", mode, "--lang", lang, "--ext", ext, "--tasks", tasks_path,
                    "--model", model, "--topk", str(topk),
                    "--num_predict", str(num_predict), "--temperature", str(temperature)]
            if validator:
                args += ["--validator", validator]
            run_detached("stage_d/benchmark.py", args)
            self._json({"slug": slug, "mode": mode, "message": "benchmark iniciado em background"})
            return

        # ---- config (salvar) ----
        if path == "/api/config":
            values = data.get("values", {})
            cfg, errors = config_util.validate_and_apply(values)
            if errors:
                self._json({"error": "validacao falhou", "errors": errors}, 400)
                return
            self._json({"ok": True, "values": cfg})
            return

        # ---- wipe total (banco + artefatos) ----
        if path == "/api/wipe":
            res = logdb.wipe_all()
            self._json(res)
            return

        # ---- consulta (query.py) ----
        if path == "/api/query":
            question = (data.get("question") or "").strip()
            dominio = (data.get("dominio") or "").strip()
            if not question:
                self._json({"error": "pergunta vazia"}, 400)
                return
            if dominio and not SLUG_RE.match(dominio):
                self._json({"error": "dominio invalido"}, 400)
                return
            args = [question]
            if dominio:
                args += ["--dominio", dominio]
            args += ["--topk", str(int(data.get("topk") or 5))]
            rc, out, err = run_capture("query.py", args)
            self._json({"answer": out, "sources": err, "rc": rc})
            return

        # ---- geracao de codigo (programador.py) ----
        if path == "/api/programador":
            task = (data.get("task") or "").strip()
            dominio = (data.get("dominio") or "").strip()
            if not task:
                self._json({"error": "tarefa vazia"}, 400)
                return
            if dominio and not SLUG_RE.match(dominio):
                self._json({"error": "dominio invalido"}, 400)
                return
            args = [task]
            if dominio:
                args += ["--dominio", dominio]
            args += ["--topk", str(int(data.get("topk") or 15))]
            model = data.get("model") or "qwen2.5-coder:7b"
            args += ["--model", model]
            rc, out, err = run_capture("programador.py", args)
            self._json({"code": out, "sources": err, "rc": rc})
            return

        # ---- exportar base (.zip) ----
        m = re.match(r"^/api/bases/([a-z0-9]+)/zip$", path)
        if m:
            slug = m.group(1)
            folder = ROOT / "RAG" / slug
            if not folder.exists():
                self._json({"error": "base inexistente"}, 404)
                return
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for f in folder.rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(folder))
            body = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{slug}.zip"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # ---- excluir base ----
        m = re.match(r"^/api/bases/([a-z0-9]+)/delete$", path)
        if m:
            slug = m.group(1)
            folder = ROOT / "RAG" / slug
            if not folder.exists():
                self._json({"error": "base inexistente"}, 404)
                return
            shutil.rmtree(folder)
            self._json({"slug": slug, "message": "base removida"})
            return

        self._json({"error": "rota nao encontrada"}, 404)

    def _page(self, site, tabs, back):
        domain_disp = resolve_display_domain(site) if site else ""
        body = (TEMPLATE
                .replace("__SITE__", site or "")
                .replace("__DOMAIN__", domain_disp or "")
                .replace("__WSPORT__", str(WS_PORT))
                .replace("__TABS__", tabs)
                .replace("__BACK__", back)
                ).encode("utf-8")
        self._send(200, body, "text/html; charset=utf-8")

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
    print(f"Servidor RagThulhu: http://0.0.0.0:{HTTP_PORT}  (WebSocket :{WS_PORT}, site={SITE})")

    async def serve():
        async with websockets.serve(handler, "0.0.0.0", WS_PORT):
            await asyncio.Future()

    asyncio.run(serve())


if __name__ == "__main__":
    main()

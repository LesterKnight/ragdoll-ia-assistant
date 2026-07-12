#!/usr/bin/env python3
"""Monitor da Fase C via browser usando WebSocket (arquitetura desacoplada).

- HTTP na porta 8765 serve a pagina (frontend/observer).
- WebSocket na porta 8766 empurra os logs ao vivo.
- O banco (RAG/log.db) e o unico contrato: o pipeline so escreve (loghub);
  este monitor so le e empurra. Nenhum dos lados conhece o outro.

Fluxo: ao abrir, a pagina manda o `site` pelo WS; o monitor envia o SNAPSHOT
(ultimas N do site, ordem cronologica) e, em seguida, empurra cada linha nova
(pattern observer: a pagina so recebe o que mudou).

Uso:
    python monitor.py --site docsgodotengineorg [--port 8765]
"""
import asyncio
import json
import sqlite3
import sys
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import websockets

BASE = Path(__file__).resolve().parent
DB = BASE / "RAG" / "log.db"
HTTP_PORT = 8765
WS_PORT = 8766
SITE = ""


def _sp():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/Sao_Paulo")
    except Exception:
        return timezone(timedelta(hours=-3))


SP = _sp()


def conv(dtstr):
    """Converte data_hora UTC (SQLite) para horario de Sao Paulo."""
    if not dtstr:
        return ""
    dt = datetime.strptime(dtstr, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.astimezone(SP).strftime("%Y-%m-%d %H:%M:%S %z")


def _read(query, params):
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    rows = c.execute(query, params).fetchall()
    c.close()
    out = []
    for r in rows:
        d = dict(r)
        d["data_hora"] = conv(d["data_hora"])
        out.append(d)
    return out


def recent(site: str, n: int = 500):
    return _read(
        "SELECT * FROM (SELECT * FROM log WHERE site=? ORDER BY id DESC LIMIT ?) ORDER BY id",
        (site, n),
    )


def after(site: str, last_id: int):
    return _read(
        "SELECT * FROM log WHERE site=? AND id>? ORDER BY id", (site, last_id)
    )


async def handler(websocket):
    try:
        site = await websocket.recv()
    except Exception:
        return
    if not site:
        return
    snap = recent(site, 500)
    last_id = snap[-1]["id"] if snap else 0
    prog = site_progress(site)
    await websocket.send(json.dumps(prog))
    await websocket.send(json.dumps({"type": "snapshot", "rows": snap}))
    try:
        while True:
            rows = after(site, last_id)
            if rows:
                last_id = rows[-1]["id"]
                for r in rows:
                    await websocket.send(json.dumps({"type": "event", "row": r}))
            await asyncio.sleep(0.5)
    except websockets.exceptions.ConnectionClosed:
        return


def _autosite():
    try:
        c = sqlite3.connect(str(DB))
        c.row_factory = sqlite3.Row
        r = c.execute("SELECT site FROM log ORDER BY id DESC LIMIT 1").fetchone()
        c.close()
        return r["site"] if r else ""
    except Exception:
        return ""


def site_progress(site: str) -> dict:
    """Retorna progresso real (process_state.json) + ETA."""
    state_path = BASE / "RAG" / site / "process_state.json"
    done = 0
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            done = len(state.get("done", []))
        except Exception:
            pass
    total = done or 1
    manifest_path = BASE / "RAG" / site / "crawl_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            total = len(manifest.get("pages", []))
        except Exception:
            pass
    elif (BASE / "RAG" / site / "clean.jsonl").exists():
        try:
            total = sum(1 for _ in (BASE / "RAG" / site / "clean.jsonl").open(encoding="utf-8"))
        except Exception:
            pass

    eta = ""
    if done > 0 and done < total:
        try:
            c = sqlite3.connect(str(DB))
            rows = c.execute(
                "SELECT data_hora FROM log WHERE site=? AND log LIKE '%processado%' ORDER BY id DESC LIMIT 20",
                (site,),
            ).fetchall()
            c.close()
            if len(rows) >= 2:
                times = sorted(
                    datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    for r in rows
                )
                span = (times[-1] - times[0]).total_seconds()
                rate = (len(times) - 1) / span  # pages/sec
                remaining = (total - done) / rate if rate > 0 else 0
                h, r = divmod(int(remaining), 3600)
                m, s = divmod(r, 60)
                if h:
                    eta = f"{h}h {m}m"
                elif m:
                    eta = f"{m}m {s}s"
                else:
                    eta = f"{s}s"
        except Exception:
            pass

    return {"done": done, "total": total, "eta": eta, "type": "progress"}


HTML = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>ragdoll — log ao vivo (WebSocket)</title>
<style>
 body{font:14px/1.45 monospace;background:#0c0c0c;color:#3f6;padding:14px;margin:0}
 h2{color:#6f9;margin:0 0 6px} .muted{color:#789} .k{color:#6cf} .e{color:#f86}
 .bar{background:#1a1a1a;height:18px;border:1px solid #3f6;margin:6px 0;border-radius:3px;overflow:hidden}
 .fill{background:linear-gradient(90deg,#1f6,#3f9);height:100%;width:0}
 pre{background:#000;padding:10px;border:1px solid #143;height:70vh;overflow:auto;margin-top:8px;border-radius:4px;white-space:pre-wrap;word-break:break-word}
 #status{color:#789;margin-left:8px;font-size:12px}
</style></head><body>
<h2>ragdoll — log ao vivo <span id="status" class="muted">conectando…</span></h2>
<div>Site: <span class="k" id="site">__SITE__</span></div>
 <div>Progresso: <span class="k" id="done">?</span> / <span class="k" id="total">?</span> <span class="k" id="pct"></span>  ETA: <span class="k" id="eta"></span></div>
<div class="bar"><div class="fill" id="fill"></div></div>
<div>Fallbacks: <span class="e" id="fb">0</span></div>
<h3 class="muted">Log (SQLite → WebSocket)</h3>
<pre id="log"></pre>
<script>
const SITE = "__SITE__";
const WSPORT = __WSPORT__;
const pre = document.getElementById('log');
const statusEl = document.getElementById('status');
const ws = new WebSocket('ws://' + location.hostname + ':' + WSPORT + '/');
ws.onopen = function(){
  statusEl.textContent = 'aberto — enviando site';
  ws.send(SITE);
};
ws.onmessage = function(e){
  const msg = JSON.parse(e.data);
  if (msg.type === 'progress'){
    setProgress(msg.done, msg.total, msg.eta);
  } else if (msg.type === 'snapshot'){
    pre.textContent = '';
    msg.rows.forEach(appendRow);
    countFallbacks();
  } else if (msg.type === 'event'){
    appendRow(msg.row);
    countFallbacks();
  }
};
ws.onerror = function(){ statusEl.textContent = 'erro no WebSocket'; };
ws.onclose = function(){ statusEl.textContent = 'fechado'; };
function appendRow(r){
  const cls = r.tipo_log === 'erro' ? 'erro' : (r.tipo_log === 'excecao' ? 'excecao' : 'sucesso');
  const line = '[' + r.data_hora + '] [' + r.etapa + '/' + r.tipo_log + '] ' + r.log + '\\n';
  pre.textContent += line;
  pre.scrollTop = pre.scrollHeight;
}
function setProgress(done, total, eta){
  document.getElementById('done').textContent = done;
  document.getElementById('total').textContent = total;
  const pct = total ? Math.round(100*done/total) : 0;
  document.getElementById('pct').textContent = pct + '%';
  document.getElementById('fill').style.width = pct + '%';
  document.getElementById('eta').textContent = eta || '';
}
function countFallbacks(){
  document.getElementById('fb').textContent = (pre.textContent.match(/fallback deterministico/g) || []).length;
}
</script>
</body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
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
        SITE = _autosite()
    HTTP_PORT = http_port
    WS_PORT = http_port + 1
    global HTML
    HTML = HTML.replace("__SITE__", SITE or "").replace("__WSPORT__", str(WS_PORT))

    threading.Thread(
        target=lambda: ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), H).serve_forever(),
        daemon=True,
    ).start()
    print(f"Monitor ragdoll: http://0.0.0.0:{HTTP_PORT}  (WebSocket :{WS_PORT}, site={SITE})")

    async def serve():
        async with websockets.serve(handler, "0.0.0.0", WS_PORT):
            await asyncio.Future()

    asyncio.run(serve())


if __name__ == "__main__":
    main()

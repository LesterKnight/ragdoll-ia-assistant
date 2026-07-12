#!/usr/bin/env python3
"""LogDB - camada de leitura (read-only) do banco RAG/log.db.

Este modulo e o unico contrato de leitura da UI: quem escreve e o pipeline
(loghub); quem le e a UI (server.py, via WebSocket). Nao sabe nada de
web/WebSocket.

Uso:
    import logdb
    linhas = logdb.recent("docsgodotengineorg", 500)
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "RAG" / "log.db"


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

    # dominio real (com pontos) para exibicao; o slug (site) e a chave segura
    domain = site
    for cand in (state_path, manifest_path, BASE / "RAG" / site / "index.json"):
        if cand.exists():
            try:
                d = json.loads(cand.read_text(encoding="utf-8"))
                if d.get("domain"):
                    domain = d["domain"]
                    break
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

    return {"done": done, "total": total, "eta": eta, "domain": domain, "type": "progress"}

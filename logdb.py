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
import shutil
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


def _last_log_ts(site: str):
    try:
        c = sqlite3.connect(str(DB))
        r = c.execute(
            "SELECT data_hora FROM log WHERE site=? ORDER BY id DESC LIMIT 1", (site,)
        ).fetchone()
        c.close()
        if not r:
            return None
        return datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def count_fallbacks(site: str) -> dict:
    """Contagem persistente de 'fallback deterministico' por etapa, para um site."""
    out = {"total": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    try:
        c = sqlite3.connect(str(DB))
        rows = c.execute(
            "SELECT etapa, COUNT(*) FROM log WHERE site=? "
            "AND log LIKE '%fallback deterministico%' GROUP BY etapa", (site,)
        ).fetchall()
        c.close()
        for etapa, n in rows:
            if etapa in out:
                out[etapa] = n
                out["total"] += n
    except Exception:
        pass
    return out


def _bench_records(site: str):
    """Linhas de benchmark (stage_d/benchmark_results.jsonl) do dominio."""
    path = BASE / "stage_d" / "benchmark_results.jsonl"
    out = []
    if not path.exists():
        return out
    try:
        for line in path.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("domain") == site:
                out.append(r)
    except Exception:
        pass
    return out


def site_status(site: str) -> dict:
    """Status completo de um site: progresso A/B/C/D, execucao, dominio, etapa maxima."""
    if not site:
        return {"domain": "", "stage": "A", "exec": "Parado",
                "A": {"done": 0, "total": 0}, "B": {"done": 0, "total": 0},
                "C": {"done": 0, "total": 0, "eta": ""}, "D": {"done": 0, "total": 0}}
    folder = BASE / "RAG" / site
    domain = site
    for cand in (folder / "process_state.json", folder / "crawl_manifest.json", folder / "index.json"):
        if cand.exists():
            try:
                d = json.loads(cand.read_text(encoding="utf-8"))
                if d.get("domain"):
                    domain = d["domain"]
                    break
            except Exception:
                pass

    # A — coleta
    manifest = None
    mp = folder / "crawl_manifest.json"
    if mp.exists():
        try:
            manifest = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            manifest = None
    a_total = len(manifest.get("pages", [])) if manifest else 0
    raw = folder / "raw"
    a_done = 0
    if raw.exists():
        a_done = sum(1 for p in raw.iterdir() if p.suffix == ".html")
    elif manifest:
        a_done = a_total

    # B — limpeza
    clean = folder / "clean.jsonl"
    b_done = 0
    if clean.exists():
        try:
            b_done = sum(1 for _ in clean.open(encoding="utf-8"))
        except Exception:
            b_done = 0
    b_total = a_total

    # C — indexacao
    c = site_progress(site)
    c_done, c_total, c_eta = c.get("done", 0), c.get("total", 0), c.get("eta", "")

    # D — avaliacao
    d_recs = _bench_records(site)
    d_done = len(d_recs)
    d_total = d_done

    # etapa maxima alcancada
    stage = "A"
    if (folder / "crawl_manifest.json").exists():
        stage = "A"
    if (folder / "clean.jsonl").exists():
        stage = "B"
    if (folder / "documents.jsonl").exists():
        stage = "C"
    if d_done > 0:
        stage = "D"

    # execucao: log recente (<90s) para o site
    ts = _last_log_ts(site)
    exec_ = "Parado"
    if ts:
        ago = (datetime.now(timezone.utc) - ts).total_seconds()
        if ago < 90:
            exec_ = "Executando"

    # operacao em execucao = etapa do log mais recente
    etapa_exec = ""
    try:
        c2 = sqlite3.connect(str(DB))
        rr = c2.execute(
            "SELECT etapa FROM log WHERE site=? ORDER BY id DESC LIMIT 1", (site,)
        ).fetchone()
        c2.close()
        if rr:
            etapa_exec = rr[0]
    except Exception:
        pass

    return {"domain": domain, "stage": stage, "exec": exec_, "etapa": etapa_exec,
            "fallbacks": count_fallbacks(site),
            "A": {"done": a_done, "total": a_total},
            "B": {"done": b_done, "total": b_total},
            "C": {"done": c_done, "total": c_total, "eta": c_eta},
            "D": {"done": d_done, "total": d_total}}


def list_bases() -> list:
    """Lista as bases RAG reais (pastas em RAG/)."""
    out = []
    rag = BASE / "RAG"
    if not rag.exists():
        return out
    names = {"A": "Coleta", "B": "Limpeza", "C": "Indexação", "D": "Avaliação"}
    for d in sorted(rag.iterdir()):
        if not d.is_dir():
            continue
        slug = d.name
        st = site_status(slug)
        done_c, total_c = st["C"]["done"], st["C"]["total"]
        if (d / "documents.jsonl").exists() and total_c and done_c >= total_c:
            sit = "Completo"
        else:
            sit = f"Incompleto · fase: {names.get(st['stage'], st['stage'])}"
        out.append({"slug": slug, "domain": st["domain"], "stage": st["stage"],
                    "situacao": sit, "exec": st["exec"]})
    return out


def wipe_all() -> dict:
    """Apaga banco de log e TODOS os artefatos gerados (bases RAG + benchmark).
    Nao toca em codigo-fonte nem em config.json."""
    removed = []
    rag = BASE / "RAG"
    if rag.exists():
        for child in rag.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed.append(str(child.relative_to(BASE)))
            except Exception:
                pass
    # resultados de benchmark (stage_d/)
    bench = BASE / "stage_d" / "benchmark_results.jsonl"
    if bench.exists():
        try:
            bench.unlink()
            removed.append(str(bench.relative_to(BASE)))
        except Exception:
            pass
    return {"ok": True, "removed": removed}

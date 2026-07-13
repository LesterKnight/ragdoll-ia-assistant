#!/usr/bin/env python3
"""LogHub - unico ponto de escrita de log do RagThulhu.

Banco SQLite geral (RAG/log.db) com a tabela `log`. Quem gera log
(pipeline A/B/C) so chama loghub.log(...); nao sabe nada de web/WebSocket.
O monitor so le o banco; nao sabe nada do pipeline. O banco e o unico
contrato entre os lados (arquitetura desacoplada).

Uso:
    import loghub
    loghub.log("docsgodotengineorg", "C", "sucesso", "processado: page 291")
"""
import sqlite3
import threading
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "RAG" / "log.db"

_lock = threading.Lock()
_CONN = None


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            site      TEXT NOT NULL,
            etapa     TEXT NOT NULL,
            tipo_log  TEXT NOT NULL,
            log       TEXT NOT NULL,
            data_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # migra tabela antiga que tinha CHECK restritivo em etapa/tipo_log
    # (impedia registrar a etapa D do benchmark / U de uso)
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='log' AND type='table'"
        ).fetchone()
        sql = row[0] if row else ""
        if sql and ("IN ('A','B','C')" in sql or "IN ('sucesso','erro','excecao')" in sql):
            conn.execute(
                "CREATE TABLE IF NOT EXISTS log_new ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT NOT NULL, "
                "etapa TEXT NOT NULL, tipo_log TEXT NOT NULL, log TEXT NOT NULL, "
                "data_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO log_new "
                "(id, site, etapa, tipo_log, log, data_hora) "
                "SELECT id, site, etapa, tipo_log, log, data_hora FROM log"
            )
            conn.execute("DROP TABLE log")
            conn.execute("ALTER TABLE log_new RENAME TO log")
            conn.commit()
    except Exception:
        pass
    return conn


def _conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        _CONN = _connect()
    return _CONN


def log(site: str, etapa: str, tipo_log: str, message: str) -> None:
    """Insere uma linha de log. tipo_log: 'sucesso' | 'erro' | 'excecao'."""
    with _lock:
        _conn().execute(
            "INSERT INTO log (site, etapa, tipo_log, log) VALUES (?, ?, ?, ?)",
            (site, etapa, tipo_log, message),
        )
        _CONN.commit()

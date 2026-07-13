"""
Retrieval compartilhado do RAG.

Usado por query.py (resposta) e programador.py (geracao de codigo).
Responsabilidades:
- listar dominios disponiveis em RAG/
- escolher dominio por heuristica (ou usar o informado)
- embedding da query (nomic-embed-text)
- busca por cosseno (forca bruta + numpy) -> top-k chunks
"""

import json
from pathlib import Path

import numpy as np
import requests

import config_util

CONF = config_util.load_config()
OLLAMA = CONF["ollama"]["url"]
EMBED_MODEL = CONF["ollama"]["embed_model"]

RAG_ROOT = Path(__file__).resolve().parent / "RAG"


def ollama_embed(text: str, timeout: int = 120):
    r = requests.post(
        f"{OLLAMA}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json().get("embedding", [])


def list_domains():
    if not RAG_ROOT.exists():
        return []
    return [p.name for p in RAG_ROOT.iterdir()
            if p.is_dir() and (p / "documents.jsonl").exists()]


def choose_domain(question: str, domains: list) -> str:
    """Heuristica simples: casa palavras da pergunta com o summary de cada dominio."""
    if len(domains) == 1:
        return domains[0]
    q = question.lower()
    best, best_score = domains[0], -1
    for d in domains:
        score = 0
        summ = RAG_ROOT / d / "summary.md"
        if summ.exists():
            text = summ.read_text(encoding="utf-8").lower()
            score = sum(1 for w in set(q.split()) if len(w) > 3 and w in text)
        if score > best_score:
            best, best_score = d, score
    return best


def load_docs(domain: str):
    path = RAG_ROOT / domain / "documents.jsonl"
    texts, vectors, metas = [], [], []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            texts.append(rec["text"])
            vectors.append(rec["vector"])
            metas.append({"url": rec.get("url", ""), "title": rec.get("title", "")})
    return texts, np.array(vectors, dtype=np.float32), metas


def cosine_topk(query_vec, matrix, k):
    q = np.array(query_vec, dtype=np.float32)
    q_norm = q / (np.linalg.norm(q) + 1e-9)
    m_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    sims = m_norm @ q_norm
    idx = np.argsort(-sims)[:k]
    return idx, sims[idx]


def retrieve_chunks(query: str, domain: str = None, topk: int = 5):
    """
    Retorna (dominio_escolhido, [{"texto":..., "url":..., "titulo":..., "score":...}]).
    Lanca RuntimeError se nao houver base ou dominio invalido.
    """
    domains = list_domains()
    if not domains:
        raise RuntimeError("nenhuma base RAG encontrada em RAG/")

    if domain is None:
        domain = choose_domain(query, domains)
    elif domain not in domains:
        raise RuntimeError(f"dominio '{domain}' nao encontrado. Disponiveis: {domains}")

    texts, matrix, metas = load_docs(domain)
    if len(texts) == 0:
        raise RuntimeError(
            f"base do dominio '{domain}' esta vazia (documents.jsonl sem chunks). "
            f"Rode: python process.py --dir RAG/{domain}"
        )
    qvec = ollama_embed(query)
    idx, sims = cosine_topk(qvec, matrix, min(topk, len(texts)))

    resultados = []
    for i, s in zip(idx, sims):
        resultados.append({
            "texto": texts[i],
            "url": metas[i]["url"],
            "titulo": metas[i]["title"],
            "score": float(s),
        })
    return domain, resultados

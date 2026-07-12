"""
ETAPA D — avaliacao INTERATIVA e facilitadora (stage 4).

Pergunta o numero de iteracoes (testes) e, para cada uma, compara:
  - MODELO COM RAG  (recebe trechos recuperados da doc)
  - MODELO SEM RAG  (so a pergunta, sem contexto)
e diz, para cada um, se POSSUI INFORMACAO DE CONTEXTO ou nao.

Como se mede "contexto" (generico, nao-Godot):
  - amostra uma pagina de API da base indexada; extrai o simbolo `term`.
  - RAG: recupera trechos; se achou trecho relevante (contem `term`) ->
    POSSUI CONTEXTO = SIM. (e checa se a resposta usou o termo)
  - SEM-RAG: nao recebe contexto -> POSSUI CONTEXTO = NAO.
    (bônus: se a resposta mesma assim contiver `term`, o modelo ja sabia
     de treino — raro para APIs novas.)

Sintese roda com qwen2.5-coder:7b (sem qwen3/gemma/qwythos).

Uso:
  python stage_d/etapa_d.py
  (responda: nº de iteracoes, dominio, modelo, top-k)
"""

import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

import rag_retrieve

OLLAMA = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder:7b"
STOP = {"node", "godot", "object", "resource", "engine", "script", "method",
        "function", "class", "signal", "property", "vector", "transform",
        "godotengine", "index", "doc", "docs", "page", "main", "introduction",
        "faq", "license", "stable", "enum", "const", "var", "type", "types",
        "english", "about", "tutorials", "manual", "contributing", "community"}


def term_from_url(url):
    seg = url.rstrip("/").split("/")[-1].lower()
    seg = re.sub(r"\.(html?|php)$", "", seg)
    m = re.match(
        r"^(?:class|enum|typedef|struct|interface|method|func|function|"
        r"property|signal|constant|module)_([a-z0-9_]+)$", seg)
    if m:
        return m.group(1)
    return None


def term_from_title(title):
    # so aceita PascalCase real (maiuscula interna), ex.: CharacterBody2D
    for t in re.findall(r"[A-Z][a-z]+[A-Z][A-Za-z0-9]+", title or ""):
        if t.lower() not in STOP:
            return t.lower()
    return None


def load_candidates(domain, n):
    """Stream documents.jsonl; coleta candidatos de paginas de API."""
    path = rag_retrieve.RAG_ROOT / domain / "documents.jsonl"
    if not path.exists():
        print(f"[erro] base nao encontrada: {path}")
        sys.exit(1)
    cap = max(1500, n * 4)
    cands = []
    seen = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            if len(cands) >= cap:
                break
            try:
                rec = json.loads(line)
            except Exception:
                continue
            url = rec.get("url", "")
            term = term_from_url(url) or term_from_title(rec.get("title", ""))
            if not term or term in STOP or term in seen:
                continue
            seen.add(term)
            cands.append({"url": url, "title": rec.get("title", ""), "term": term})
    return cands


def ask_model(prompt, model, num_predict=500):
    r = requests.post(
        f"{OLLAMA}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False,
              "options": {"temperature": 0.2, "num_predict": num_predict}},
        timeout=600,
    )
    r.raise_for_status()
    return r.json().get("response", "")


def main():
    print("=" * 64)
    print("ETAPA D — avaliacao RAG x SEM-RAG (contexto)")
    print("=" * 64)
    try:
        n = int(input("Numero de iteracoes (testes): ").strip())
    except Exception:
        n = 10
    domain = (input("Dominio [docsgodotengineorg]: ").strip() or "docsgodotengineorg")
    model = (input(f"Modelo [{DEFAULT_MODEL}]: ").strip() or DEFAULT_MODEL)
    try:
        topk = int(input("Top-k [15]: ").strip() or 15)
    except Exception:
        topk = 5

    print("\n[carregando candidatos da base...]", flush=True)
    cands = load_candidates(domain, n)
    if len(cands) < n:
        print(f"[aviso] so {len(cands)} candidatos uteis; usando {len(cands)}")
        n = len(cands)
    if n == 0:
        print("[erro] nenhum candidato utili na base.")
        sys.exit(1)
    random.seed()
    sample = random.sample(cands, n)

    rag_ctx = norag_ctx = 0
    print(f"\nRodando {n} teste(s):\n")
    for i, item in enumerate(sample, 1):
        term = item["term"]
        question = (
            f"Responda em portugues, de forma tecnica e objetiva, sobre a "
            f"documentacao: explique o que eh e como se usa '{term}'. "
            f"Mencione as principals APIs/metodos envolvidos."
        )

        # --- COM RAG ---
        print(f"  [{i:02d}/{n}] RAG: recuperando contexto...", flush=True)
        try:
            _, chunks = rag_retrieve.retrieve_chunks(question, domain, topk)
            relevant = any(term in (c["texto"] + c["url"]).lower() for c in chunks)
            ctx = "\n\n".join(
                f"[Trecho {j}] ({c['url']})\n{c['texto']}" for j, c in enumerate(chunks, 1)
            )
            rag_prompt = (
                "Use SOMENTE os TRECHOS para responder.\n\n"
                f"TRECHOS:\n{ctx}\n\nPERGUNTA: {question}\n\nRESPOSTA:"
            )
            rag_ans = ask_model(rag_prompt, model)
            rag_usou = term in rag_ans.lower()
        except Exception as e:
            relevant = False
            rag_ans = ""
            rag_usou = False
            print(f"  [RAG erro: {e}]")
        rag_ctx += int(relevant)
        r = "SIM" if relevant else "NAO"

        # --- SEM RAG ---
        print(f"  [{i:02d}/{n}] SEM-RAG: gerando resposta...", flush=True)
        norag_prompt = f"{question}\n\nRESPOSTA:"
        norag_ans = ask_model(norag_prompt, model)
        norag_usou = term in norag_ans.lower()
        nr = "NAO"  # por definicao: nao recebeu contexto

        print(f"[{i:02d}/{n}] term='{term}'")
        print(f"      RAG     contexto = {r}" + (f"  (usa '{term}': {rag_usou})" if relevant else ""))
        print(f"      SEM-RAG contexto = {nr}  (modelo sabia de treino: {norag_usou})")

    print("\n" + "=" * 64)
    print(f"RESUMO ({n} testes, modelo {model}):")
    print(f"  RAG     com contexto : {rag_ctx}/{n} ({100*rag_ctx/n:.0f}%)")
    print(f"  SEM-RAG com contexto : 0/{n} (0%)  <- nao recebe contexto")
    if rag_ctx:
        print(f"  Ganho do RAG        : +{rag_ctx}/{n} testes com contexto")
    print("=" * 64)


if __name__ == "__main__":
    main()

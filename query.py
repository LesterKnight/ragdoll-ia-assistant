"""
Consumo / runtime - responde perguntas usando a base RAG.

Uso:
    python query.py "sua pergunta"                  # escolhe a pasta automaticamente
    python query.py "sua pergunta" --dominio docsgodotengineorg
    python query.py "sua pergunta" --topk 5 --model qwen2.5-coder:1.5b

Fluxo:
1. rag_retrieve escolhe o dominio e recupera top-k chunks (cosseno)
2. monta prompt com os chunks -> modelo responde
"""

import argparse
import sys

import requests

import rag_retrieve

OLLAMA = "http://localhost:11434"
ANSWER_MODEL = "qwen2.5-coder:1.5b"


def ollama_chat(prompt: str, model: str, timeout: int = 300) -> str:
    r = requests.post(
        f"{OLLAMA}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False,
              "options": {"temperature": 0.2}},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json().get("response", "")


def answer(question: str, domain: str = None, topk: int = 5, model: str = ANSWER_MODEL):
    try:
        domain, chunks = rag_retrieve.retrieve_chunks(question, domain, topk)
    except RuntimeError as e:
        print(f"[ERRO]: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[dominio]: {domain}")

    context_parts, sources = [], []
    for rank, ch in enumerate(chunks, 1):
        context_parts.append(f"[Trecho {rank}] (fonte: {ch['url']})\n{ch['texto']}")
        sources.append(ch["url"])

    context = "\n\n".join(context_parts)
    prompt = (
        "Responda a PERGUNTA usando SOMENTE os TRECHOS fornecidos. "
        "Se a resposta nao estiver nos trechos, diga que nao encontrou. "
        "Responda em portugues, de forma clara e objetiva.\n\n"
        f"TRECHOS:\n{context}\n\n"
        f"PERGUNTA: {question}\n\nRESPOSTA:"
    )
    resp = ollama_chat(prompt, model)

    print("\n" + "=" * 60)
    print(resp.strip())
    print("=" * 60)
    print("\nFontes:")
    for s in dict.fromkeys(sources):
        print(f"  - {s}")


def main():
    ap = argparse.ArgumentParser(description="Consumo RAG")
    ap.add_argument("pergunta")
    ap.add_argument("--dominio", default=None, help="pasta do dominio (ex: docsgodotengineorg)")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--model", default=ANSWER_MODEL, help=f"modelo de resposta (padrao: {ANSWER_MODEL})")
    args = ap.parse_args()
    answer(args.pergunta, args.dominio, args.topk, args.model)


if __name__ == "__main__":
    main()

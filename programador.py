"""
Gerador de codigo fundamentado no RAG (Camada 3).

Uso:
    python programador.py "tarefa" [--dominio X] [--topk N] [--model M]
                          [--contexto "codigo existente"] [--idioma pt|en] [--out arquivo]

Fluxo:
1. reescreve a tarefa em termos de busca (com fallback para a tarefa direta)
2. recupera top-k trechos da doc via rag_retrieve
3. monta prompt de codigo (usa SOMENTE os trechos)
 4. modelo de geracao (default qwen2.5-coder:1.5b, cabe na GPU) gera o codigo
5. imprime no stdout (e grava em --out se informado)

Nao orquestra nada: pipeline fixo. Toda decisao agentica fica no agente que o chama.
"""

import argparse
import sys
from pathlib import Path

import requests

import rag_retrieve

OLLAMA = "http://localhost:11434"
GEN_MODEL = "qwen2.5-coder:1.5b"


def _is_reasoning_model(model: str) -> bool:
    m = model.lower()
    return "qwen3" in m or "qwythos" in m


def ollama_chat(prompt: str, model: str, temperature: float = 0.2, timeout: int = 600) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False,
               "options": {"temperature": temperature}}
    if _is_reasoning_model(model):
        payload["think"] = False  # desliga cadeia de raciocinio (mais rapido, saida direta)
    r = requests.post(f"{OLLAMA}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "")


def rewrite_query(tarefa: str, model: str) -> str:
    """Transforma a tarefa em termos de busca (palavras-chave/API). Fallback: a propria tarefa."""
    prompt = (
        "Extraia da TAREFA abaixo os termos de busca (palavras-chave, nomes de API, conceitos) "
        "que ajudariam a encontrar documentacao relevante. "
        "Responda APENAS com os termos separados por espaco, sem explicacao.\n\n"
        f"TAREFA: {tarefa}\n\nTERMOS:"
    )
    try:
        termos = ollama_chat(prompt, model, temperature=0.0, timeout=120).strip()
        termos = termos.splitlines()[0].strip() if termos else ""
        return termos if len(termos) >= 3 else tarefa
    except Exception:
        return tarefa


def gerar(tarefa: str, dominio: str = None, topk: int = 5, model: str = GEN_MODEL,
          contexto: str = "", idioma: str = "pt", reescrever: bool = False):
    query = rewrite_query(tarefa, model) if reescrever else tarefa

    try:
        dominio, chunks = rag_retrieve.retrieve_chunks(query, dominio, topk)
    except RuntimeError as e:
        print(f"[ERRO]: {e}", file=sys.stderr)
        sys.exit(1)

    doc = "\n\n".join(
        f"[Trecho {i} | fonte: {c['url']}]\n{c['texto']}" for i, c in enumerate(chunks, 1)
    )

    idioma_txt = "portugues" if idioma == "pt" else "ingles"
    contexto_bloco = f"\n\nCODIGO EXISTENTE (contexto):\n{contexto}\n" if contexto.strip() else ""

    prompt = (
        "Voce e um programador experiente. Gere codigo para a TAREFA usando como referencia "
        "os TRECHOS DA DOCUMENTACAO abaixo. Baseie-se nos trechos; nao invente APIs que nao aparecem neles. "
        f"Comente o codigo em {idioma_txt}. Responda com o codigo e uma breve explicacao.\n\n"
        f"TRECHOS DA DOCUMENTACAO (dominio: {dominio}):\n{doc}\n"
        f"{contexto_bloco}\n"
        f"TAREFA: {tarefa}\n\nCODIGO:"
    )

    resp = ollama_chat(prompt, model)
    saida = resp.strip()

    print(f"[dominio]: {dominio} | [modelo]: {model} | [query]: {query}", file=sys.stderr)
    return saida, chunks


def mostrar_fontes(chunks):
    """Imprime os trechos da doc que foram recuperados e injetados no prompt."""
    print("\n" + "=" * 60, file=sys.stderr)
    print(f"TRECHOS DA DOC USADOS ({len(chunks)}):", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    for i, c in enumerate(chunks, 1):
        snippet = c["texto"][:200].replace("\n", " ")
        print(f"\n[{i}] score={c['score']:.3f} | {c['url']}", file=sys.stderr)
        print(f"    {snippet}...", file=sys.stderr)


def extrair_codigo(texto: str) -> str:
    """
    Extrai o codigo do texto para gravar arquivo limpo.
    Robusto a modelos de raciocinio: remove <think>...</think> e pega o ULTIMO
    bloco ```...``` (o codigo final, nao rascunhos do raciocinio).
    """
    import re
    # remove blocos de raciocinio
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL)
    blocos = re.findall(r"```[a-zA-Z0-9_+-]*\n(.*?)```", texto, re.DOTALL)
    if blocos:
        return blocos[-1].rstrip()
    return texto.strip()


def main():
    from config_util import load_config
    cfg = load_config("config_programador.json")
    gen_default = cfg.get("model", GEN_MODEL)

    ap = argparse.ArgumentParser(description="Gerador de codigo fundamentado no RAG")
    ap.add_argument("tarefa")
    ap.add_argument("--dominio", default=cfg.get("dominio"), help="pasta do dominio (default: auto)")
    ap.add_argument("--topk", type=int, default=cfg.get("topk", 5))
    ap.add_argument("--model", default=gen_default,
                    help=f"modelo de geracao (default config: {gen_default})")
    ap.add_argument("--contexto", default="", help="codigo existente para dar contexto")
    ap.add_argument("--idioma", default=cfg.get("idioma", "pt"), choices=["pt", "en"],
                    help="idioma dos comentarios")
    ap.add_argument("--reescrever", action="store_true", default=cfg.get("reescrever", False),
                    help="reescreve a tarefa em termos de busca (mais lento, +1 chamada)")
    ap.add_argument("--out", default=None, help="grava o codigo gerado neste arquivo")
    ap.add_argument("--fontes", action="store_true",
                    help="mostra os trechos da doc recuperados (prova que o RAG foi usado)")
    args = ap.parse_args()

    saida, chunks = gerar(args.tarefa, args.dominio, args.topk, args.model,
                          args.contexto, args.idioma, args.reescrever)

    if args.fontes:
        mostrar_fontes(chunks)

    print(saida)
    if args.out:
        # grava so o codigo (sem cercas markdown nem explicacao)
        Path(args.out).write_text(extrair_codigo(saida) + "\n", encoding="utf-8")
        print(f"\n[gravado em]: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()

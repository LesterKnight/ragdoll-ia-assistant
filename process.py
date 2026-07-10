"""
Fase B - Processamento (offline, sem rede exceto Ollama local).

Uso:
    python process.py --dir RAG/<dominio-simplificado>

Responsabilidades:
- Limpa HTML (remove nav/menu/footer/sidebar)
- Preserva codigo, tabelas, titulos, Mermaid
- Chunking SEMANTICO via qwen3.6 (com fallback deterministico por titulo)
- Gera embeddings de cada chunk (nomic-embed-text)
- Monta documents.jsonl + index.json + summary.md
- Cria/atualiza RAG/index.md (catalogo-mestre)
"""

import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString

OLLAMA = "http://localhost:11434"
CHUNK_MODEL = "gemma4"      # chunking: roda por pagina, gemma4 e ~5x mais rapido
SUMMARY_MODEL = "qwythos9b"  # summary: roda 1x por site; cabe na GPU, sem crash de VRAM
EMBED_MODEL = "nomic-embed-text"

TARGET_TOKENS = 400      # alvo por chunk (~aproximado)
MAX_TOKENS = 500
OVERLAP_TOKENS = 50

# tags de navegacao/ruido a remover
JUNK_SELECTORS = [
    "nav", "footer", "header", "aside",
    ".sidebar", ".nav", ".navbar", ".menu", ".toc", ".breadcrumb",
    ".header", ".footer", "[role=navigation]", ".wy-nav-side",
    ".rst-footer-buttons", ".headerlink", "script", "style", "noscript",
]


# ------------------------- utilidades -------------------------

def approx_tokens(text: str) -> int:
    """Estimativa barata de tokens (~4 chars/token)."""
    return max(1, len(text) // 4)


NUM_CTX = None  # definido pelo config; limita o KV cache (evita crash do qwen3.6 na VRAM)


def ollama_chat(prompt: str, model: str, timeout: int = 600) -> str:
    options = {"temperature": 0.1}
    if NUM_CTX:
        options["num_ctx"] = NUM_CTX
    payload = {"model": model, "prompt": prompt, "stream": False, "options": options}
    # qwen3.6 tem modo "thinking" (lento); desliga. Outros modelos ignoram.
    if "qwen3" in model:
        payload["think"] = False
    r = requests.post(f"{OLLAMA}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "")


def ollama_embed(text: str, timeout: int = 120):
    r = requests.post(
        f"{OLLAMA}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json().get("embedding", [])


# ------------------------- limpeza HTML -------------------------

def find_main(soup: BeautifulSoup):
    """Tenta achar o container de conteudo principal."""
    for sel in ["main", "[role=main]", "article", ".document", ".rst-content",
                ".md-content", "#content", ".content", ".body"]:
        el = soup.select_one(sel)
        if el:
            return el
    return soup.body or soup


def clean_html(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for sel in JUNK_SELECTORS:
        for el in soup.select(sel):
            el.decompose()
    main = find_main(soup)
    return main


def block_text(main) -> str:
    """
    Extrai texto preservando estrutura: titulos como marcadores, blocos de
    codigo e tabelas intactos, paragrafos separados.
    """
    parts = []

    def walk(node):
        if node.name is None:
            return
        name = node.name.lower()
        if re.fullmatch(r"h[1-6]", name):
            level = int(name[1])
            parts.append("\n" + "#" * level + " " + node.get_text(" ", strip=True) + "\n")
            return
        if name == "pre":
            code = node.get_text("", strip=False)
            parts.append("\n```\n" + code.rstrip() + "\n```\n")
            return
        if name == "table":
            parts.append("\n" + _table_to_md(node) + "\n")
            return
        # mermaid (div class mermaid ou code class language-mermaid)
        classes = " ".join(node.get("class", []))
        if "mermaid" in classes:
            parts.append("\n```mermaid\n" + node.get_text("", strip=False).strip() + "\n```\n")
            return
        if name in ("p", "li", "dd", "dt", "blockquote"):
            txt = node.get_text(" ", strip=True)
            if txt:
                parts.append(txt)
            return
        for child in node.children:
            if isinstance(child, NavigableString):
                continue
            walk(child)

    walk(main)
    text = "\n\n".join(p for p in parts if p.strip())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _table_to_md(table) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if cells:
            rows.append("| " + " | ".join(cells) + " |")
    if not rows:
        return ""
    if len(rows) > 1:
        ncol = rows[0].count("|") - 1
        sep = "| " + " | ".join(["---"] * ncol) + " |"
        rows.insert(1, sep)
    return "\n".join(rows)


# ------------------------- chunking -------------------------

def chunk_by_headings(text: str):
    """Fallback deterministico: corta por titulos e por tamanho, com overlap."""
    sections = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    chunks = []
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        if approx_tokens(sec) <= MAX_TOKENS:
            chunks.append(sec)
        else:
            chunks.extend(_split_large(sec))
    return _apply_overlap(chunks)


def _split_large(text: str):
    """Divide um bloco grande em pedacos <= MAX_TOKENS, sem cortar cerca de codigo."""
    paras = text.split("\n\n")
    out, cur = [], ""
    in_code = False
    for para in paras:
        if para.strip().startswith("```"):
            in_code = not in_code
        candidate = (cur + "\n\n" + para).strip() if cur else para
        if approx_tokens(candidate) > MAX_TOKENS and cur and not in_code:
            out.append(cur.strip())
            cur = para
        else:
            cur = candidate
    if cur.strip():
        out.append(cur.strip())
    return out


def _apply_overlap(chunks):
    if len(chunks) <= 1:
        return chunks
    out = [chunks[0]]
    for i in range(1, len(chunks)):
        prev = chunks[i - 1]
        tail = prev[-OVERLAP_TOKENS * 4:]
        out.append((tail + "\n\n" + chunks[i]).strip())
    return out


MODEL_INPUT_TOKENS = 6000  # teto por chamada ao modelo (mantem inferencia rapida e confiavel)


def _semantic_one(section: str):
    """Segmenta UMA secao (ja de tamanho controlado) via qwen3.6."""
    if approx_tokens(section) <= MAX_TOKENS:
        return [section]
    prompt = (
        "Voce e um segmentador de documentos para RAG. Divida o TEXTO abaixo em "
        "trechos semanticamente coerentes de no maximo ~400 palavras cada. "
        "Nunca corte no meio de um bloco de codigo (```) ou tabela. "
        "Responda APENAS com JSON valido no formato "
        '{\"chunks\": [\"trecho1\", \"trecho2\", ...]} sem texto extra.\n\n'
        "TEXTO:\n" + section
    )
    try:
        resp = ollama_chat(prompt, CHUNK_MODEL)
        data = _extract_json(resp)
        chunks = data.get("chunks", [])
        chunks = [c.strip() for c in chunks if isinstance(c, str) and c.strip()]
        if chunks and sum(len(c) for c in chunks) >= 0.5 * len(section):
            return chunks
    except Exception as e:
        print(f"  (chunking semantico falhou: {e} -> fallback deterministico)", flush=True)
    return chunk_by_headings(section)


def chunk_semantic(text: str):
    """
    Chunking via qwen3.6 com pre-divisao: paginas grandes sao quebradas por
    titulos ANTES de irem ao modelo, garantindo chamadas pequenas e confiaveis.
    """
    if approx_tokens(text) <= MAX_TOKENS:
        return [text]

    # pre-divide por titulos para nunca enviar uma pagina gigante inteira
    sections = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    all_chunks = []
    buffer = ""
    for sec in sections:
        candidate = (buffer + "\n\n" + sec).strip() if buffer else sec
        if approx_tokens(candidate) > MODEL_INPUT_TOKENS and buffer:
            all_chunks.extend(_semantic_one(buffer))
            buffer = sec
        else:
            buffer = candidate
    if buffer:
        all_chunks.extend(_semantic_one(buffer))

    return _apply_overlap(all_chunks)


def _extract_json(s: str):
    """Extrai o PRIMEIRO objeto JSON balanceado de uma string (tolera texto/JSON extra ao redor)."""
    start = s.find("{")
    if start == -1:
        raise ValueError("sem JSON na resposta")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(s[start:i + 1])
    raise ValueError("JSON nao balanceado na resposta")


# ------------------------- summary -------------------------

def build_summary(domain: str, url_base: str, docs_meta: list) -> str:
    titles = "\n".join(f"- {d['title']} ({d['url']})" for d in docs_meta[:60])
    prompt = (
        f"Gere um resumo conciso em portugues da documentacao do dominio '{domain}'. "
        "Descreva do que trata, os principais topicos e como esta organizada. "
        "Responda em Markdown, maximo 300 palavras.\n\n"
        f"Paginas processadas:\n{titles}"
    )
    try:
        return ollama_chat(prompt, SUMMARY_MODEL).strip()
    except Exception as e:
        return f"# Resumo\n\nDocumentacao de {domain}. ({len(docs_meta)} paginas). "\
               f"(resumo automatico indisponivel: {e})"


# ------------------------- catalogo mestre -------------------------

def update_master_index(rag_root: Path):
    """Reconstroi RAG/index.md a partir de todos os index.json existentes."""
    rows = []
    for idx_file in sorted(rag_root.glob("*/index.json")):
        try:
            data = json.loads(idx_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows.append(data)

    lines = [
        "# Catalogo RAG",
        "",
        "Indice mestre de todas as documentacoes processadas.",
        "Para responder, escolha a pasta do dominio relevante e consulte seu documents.jsonl.",
        "",
        "| Dominio | Pasta | URL base | Paginas | Chunks | Data |",
        "|---------|-------|----------|---------|--------|------|",
    ]
    for d in rows:
        lines.append(
            f"| {d.get('domain','')} | `{d.get('domain_slug','')}/` | {d.get('url_base','')} "
            f"| {d.get('pages',0)} | {d.get('chunks',0)} | {d.get('date','')} |"
        )
    (rag_root / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------- pipeline -------------------------

def process(dir_path: str, limpar_raw: bool = False,
            chunk_model: str = None, summary_model: str = None, num_ctx: int = None):
    global CHUNK_MODEL, SUMMARY_MODEL, NUM_CTX
    if chunk_model:
        CHUNK_MODEL = chunk_model
    if summary_model:
        SUMMARY_MODEL = summary_model
    if num_ctx:
        NUM_CTX = num_ctx
    print(f"modelos: chunking={CHUNK_MODEL} | summary={SUMMARY_MODEL} | num_ctx={NUM_CTX}", flush=True)

    t_inicio = time.perf_counter()
    out_dir = Path(dir_path).resolve()
    raw_dir = out_dir / "raw"
    manifest_file = out_dir / "crawl_manifest.json"

    if not manifest_file.exists():
        print(f"[ERRO]: manifesto nao encontrado em {manifest_file}", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    domain = manifest.get("domain", "")
    domain_slug = manifest.get("domain_slug", out_dir.name)
    url_base = manifest.get("url_base", "")

    documents_path = out_dir / "documents.jsonl"
    docs_meta = []
    total_chunks = 0
    errors = 0

    pages = manifest.get("pages", [])
    total_pages = len(pages)
    with documents_path.open("w", encoding="utf-8") as fout:
        for n, page in enumerate(pages, 1):
            print(f"[{n}/{total_pages}] processando: {page['url']}", flush=True)
            html_file = raw_dir / page["file"]
            if not html_file.exists():
                errors += 1
                continue
            try:
                html = html_file.read_text(encoding="utf-8")
                main = clean_html(html)
                text = block_text(main)
                if not text.strip():
                    continue

                chunks = chunk_semantic(text)
                for order, chunk in enumerate(chunks):
                    vector = ollama_embed(chunk)
                    record = {
                        "text": chunk,
                        "vector": vector,
                        "url": page["url"],
                        "title": page.get("title", ""),
                        "order": order,
                    }
                    fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total_chunks += 1

                docs_meta.append({"url": page["url"], "title": page.get("title", ""),
                                  "chunks": len(chunks)})
                print(f"processado: {page['url']} -> {len(chunks)} chunks", flush=True)
            except Exception as e:
                errors += 1
                print(f"[ERRO] {page['url']}: {e}", flush=True)

    # index.json da pasta
    index_data = {
        "domain": domain,
        "domain_slug": domain_slug,
        "url_base": url_base,
        "pages": len(docs_meta),
        "chunks": total_chunks,
        "errors": errors,
        "date": datetime.date.today().isoformat(),
        "documents": docs_meta,
    }
    (out_dir / "index.json").write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # summary.md
    print("gerando summary.md via qwen3.6 (pode demorar)...", flush=True)
    summary = build_summary(domain, url_base, docs_meta)
    (out_dir / "summary.md").write_text(summary + "\n", encoding="utf-8")

    # catalogo mestre
    update_master_index(out_dir.parent)

    # limpeza opcional do raw/ (so se sucesso: sem erros e com chunks gerados)
    raw_removido = False
    if limpar_raw:
        if errors == 0 and total_chunks > 0:
            import shutil
            shutil.rmtree(raw_dir, ignore_errors=True)
            raw_removido = True
            print("raw/ removido (--limpar-raw, processamento sem erros)", flush=True)
        else:
            print("raw/ mantido: houve erros ou nenhum chunk gerado", flush=True)

    elapsed = time.perf_counter() - t_inicio
    m, s = divmod(int(elapsed), 60)
    tempo_str = f"{m}m {s}s" if m else f"{s}s"

    print(f"\n[RESULTADO]")
    print(f"pasta: {out_dir}")
    print(f"documentos: {len(docs_meta)}")
    print(f"chunks: {total_chunks}")
    print(f"erros: {errors}")
    print(f"raw removido: {'sim' if raw_removido else 'nao'}")
    print(f"tempo total: {tempo_str} ({elapsed:.1f}s)")


def main():
    from config_util import load_config
    cfg = load_config("config_espiao.json").get("process", {})

    ap = argparse.ArgumentParser(description="Fase B - processamento RAG")
    ap.add_argument("--dir", required=True, help="pasta RAG/<dominio-simplificado>")
    ap.add_argument("--limpar-raw", action="store_true",
                    help="apaga raw/ ao final se o processamento for bem-sucedido")
    ap.add_argument("--chunk-model", default=cfg.get("chunk_model"),
                    help=f"modelo de chunking (default config: {cfg.get('chunk_model', CHUNK_MODEL)})")
    ap.add_argument("--summary-model", default=cfg.get("summary_model"),
                    help=f"modelo do summary (default config: {cfg.get('summary_model', SUMMARY_MODEL)})")
    ap.add_argument("--num-ctx", type=int, default=cfg.get("num_ctx"),
                    help=f"limite de contexto (default config: {cfg.get('num_ctx')})")
    args = ap.parse_args()
    process(args.dir, args.limpar_raw, args.chunk_model, args.summary_model, args.num_ctx)


if __name__ == "__main__":
    main()

"""
Fase C - Indexacao (offline, sem rede exceto Ollama local).

Uso:
    python process.py --dir RAG/<dominio-simplificado>

Responsabilidades:
- Consome clean.jsonl (texto JA limpo pela Fase B/parse.py)
- Chunking SEMANTICO via CHUNK_MODEL (qwen2.5-coder:1.5b) com fallback deterministico
- Gera embeddings de cada chunk (nomic-embed-text)
- Monta documents.jsonl + index.json
- summary.md: esqueleto estrutural + prosa offload para o hy3 (SUMMARY_MODEL=None)
- Cria/atualiza RAG/index.md (catalogo-mestre)

Obs: as funcoes de limpeza (clean_html/block_text) moram aqui, mas sao aplicadas
pela Fase B (parse.py), que gera o clean.jsonl.
"""

import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, NavigableString

OLLAMA = "http://localhost:11434"
CHUNK_MODEL = "qwen2.5-coder:1.5b"  # chunking: leve (1GB), especialista em codigo; 0% fallback nos testes
SUMMARY_MODEL = None  # None = summary offload para hy3 (veja _summary_skeleton)
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


NUM_CTX = None  # definido pelo config; limita o KV cache (evita crash do modelo na VRAM)


def ollama_chat(prompt: str, model: str, timeout: int = 600) -> str:
    options = {"temperature": 0.1}
    if NUM_CTX:
        options["num_ctx"] = NUM_CTX
    payload = {"model": model, "prompt": prompt, "stream": False, "options": options}
    # modelos de raciocinio (qwen3, qwythos) tem modo "thinking" (lento); desliga.
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


def _sanitize_for_json(s: str) -> str:
    """Remove caracteres de controle invalidos em JSON (mantem \\t \\n \\r)."""
    return "".join(ch if (ord(ch) >= 0x20 or ch in "\t\n\r") else " " for ch in s)


def _parse_chunks(resp: str, section: str):
    """Extrai e valida a lista de chunks do JSON. Levanta se invalido."""
    data = _extract_json(resp)
    chunks = data.get("chunks", [])
    if not isinstance(chunks, list):
        raise ValueError("campo 'chunks' nao e lista")
    chunks = [c.strip() for c in chunks if isinstance(c, str) and c.strip()]
    if not chunks:
        raise ValueError("JSON valido mas sem chunks uteis")
    if sum(len(c) for c in chunks) < 0.5 * len(section):
        raise ValueError("JSON valido mas incompleto (<50% do texto)")
    return chunks


def _semantic_one(section: str, max_retries: int = 2):
    """Segmenta UMA secao via modelo, com sanitizacao + retry antes do fallback."""
    if approx_tokens(section) <= MAX_TOKENS:
        return [section]
    base_prompt = (
        "Voce e um segmentador de documentos para RAG. Divida o TEXTO abaixo em "
        "trechos semanticamente coerentes de no maximo ~400 palavras cada. "
        "Nunca corte no meio de um bloco de codigo (```) ou tabela. "
        "Responda APENAS com JSON valido no formato "
        '{"chunks": ["trecho1", "trecho2", ...]} sem texto extra.\n\n'
        "TEXTO:\n" + section
    )
    last_err = None
    for attempt in range(max_retries + 1):
        prompt = base_prompt
        if attempt > 0:
            prompt = ("IMPORTANTE: sua resposta anterior NAO era um JSON valido. "
                      "Responda APENAS o objeto JSON, sem caracteres de controle e "
                      "sem texto antes/depois.\n\n" + base_prompt)
        try:
            resp = ollama_chat(prompt, CHUNK_MODEL)
            resp = _sanitize_for_json(resp)
            return _parse_chunks(resp, section)
        except Exception as e:
            last_err = e
            print(f"  (chunking semantico tentativa {attempt + 1} falhou: {e})", flush=True)
    print(f"  (chunking semantico esgotou tentativas: {last_err} -> fallback deterministico)",
          flush=True)
    return chunk_by_headings(section)


def chunk_semantic(text: str):
    """
    Chunking via CHUNK_MODEL com pre-divisao: paginas grandes sao quebradas por
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
                return json.loads(s[start:i + 1], strict=False)
    raise ValueError("JSON nao balanceado na resposta")


# ------------------------- summary -------------------------

def _agrupar_por_secao(url_base: str, docs_meta: list) -> dict:
    """Agrupa as paginas pela secao (primeiro segmento apos o prefixo da url_base)."""
    from collections import defaultdict
    base_parts = [p for p in urlparse(url_base).path.split("/") if p]
    n = len(base_parts)  # ex: /en/stable -> 2
    secoes = defaultdict(list)
    for d in docs_meta:
        parts = [p for p in urlparse(d["url"]).path.split("/") if p]
        secao = parts[n] if len(parts) > n else "(raiz)"
        secoes[secao].append(d.get("title", ""))
    return secoes


def _amostra_distribuida(docs_meta: list, n: int) -> list:
    """Pega n titulos igualmente espacados ao longo de toda a base (representa o todo)."""
    total = len(docs_meta)
    if total <= n:
        return [d.get("title", "") for d in docs_meta]
    passo = total / n
    return [docs_meta[int(i * passo)].get("title", "") for i in range(n)]


def _build_overview(domain: str, url_base: str, docs_meta: list) -> str:
    """
    Painel estrutural da base (secoes+contagens ou amostra de titulos),
    usado tanto pelo summary via modelo quanto pelo esqueleto offload.
    """
    secoes = _agrupar_por_secao(url_base, docs_meta)
    # ignora pastas tecnicas (downloads/imagens/assets) na decisao
    secoes_uteis = {s: t for s, t in secoes.items() if not s.startswith(("_", "."))}

    if len(secoes_uteis) >= 3:
        linhas = []
        for sec, titles in sorted(secoes_uteis.items(), key=lambda x: -len(x[1])):
            exemplos = "; ".join(t.split("—")[0].strip() for t in titles[:6] if t)
            linhas.append(f"- {sec}: {len(titles)} paginas (ex: {exemplos})")
        return "Estrutura por secoes:\n" + "\n".join(linhas)
    amostra = [t for t in _amostra_distribuida(docs_meta, 80) if t]
    return ("Amostra de titulos distribuida por toda a base:\n"
            + "\n".join(f"- {t}" for t in amostra))


def build_summary(domain: str, url_base: str, docs_meta: list) -> str:
    """
    Gera um panorama que cobre a base INTEIRA sem estourar o contexto.
    Estrategia adaptativa (funciona em qualquer estrutura de site):
    - site ESTRUTURADO (>= 3 secoes uteis): panorama por secao (contagem + exemplos)
    - site PLANO (poucas secoes): amostra de titulos distribuida por toda a base
    """
    overview = _build_overview(domain, url_base, docs_meta)
    prompt = (
        f"Gere um resumo conciso em portugues da documentacao do dominio '{domain}' "
        f"(total: {len(docs_meta)} paginas). Descreva do que trata, os principais topicos "
        "e como esta organizada. Responda em Markdown, maximo 350 palavras.\n\n"
        f"{overview}"
    )
    try:
        return ollama_chat(prompt, SUMMARY_MODEL).strip()
    except Exception as e:
        return (f"# Resumo\n\nDocumentacao de {domain} ({len(docs_meta)} paginas).\n\n"
                f"{overview}\n\n(resumo automatico indisponivel: {e})")


def _summary_skeleton(domain: str, url_base: str, docs_meta: list) -> str:
    """Esqueleto estrutural quando o summary e offload para o hy3 (sem modelo local)."""
    overview = _build_overview(domain, url_base, docs_meta)
    return (
        f"# Resumo — {domain}\n\n"
        "> Offload de qwythos9b para o assistente hy3. Abaixo o esqueleto "
        "estrutural; a prosa em portugues e redigida pelo hy3 sob demanda.\n\n"
        f"Total: {len(docs_meta)} paginas.\n\n{overview}"
    )


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
            chunk_model: str = None, summary_model: str = None, num_ctx: int = None,
            reset: bool = False):
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
    state_path = out_dir / "process_state.json"
    pages = manifest.get("pages", [])
    total_pages = len(pages)
    errors = 0

    # --- Fase C consome a SAIDA da Fase B (parse.py): texto JA limpo (clean.jsonl) ---
    # A Fase B so termina apos obter os HTMLs E limpa-los; portanto a Fase C
    # nunca relê raw/ nem executa clean_html/block_text. Se faltar texto limpo
    # de alguma pagina, a Fase B nao concluiu e abortamos.
    clean_path = out_dir / "clean.jsonl"
    if not clean_path.exists():
        print("[ERRO]: clean.jsonl ausente — Fase A (obter HTML + limpar) nao concluida.",
              file=sys.stderr)
        sys.exit(1)
    clean_map = {}
    with clean_path.open(encoding="utf-8") as fclean:
        for line in fclean:
            try:
                r = json.loads(line)
                clean_map[r["url"]] = r
            except Exception:
                pass
    print(f"clean.jsonl carregado: {len(clean_map)} paginas com texto limpo", flush=True)
    faltando = [p["url"] for p in pages if p["url"] not in clean_map]
    if faltando:
        print(f"[ERRO]: Fase A incompleta — {len(faltando)} pagina(s) sem texto limpo:",
              file=sys.stderr)
        for u in faltando[:10]:
            print(f"  - {u}", file=sys.stderr)
        sys.exit(1)

    # --- retomada (resume) ---
    if reset:
        documents_path.unlink(missing_ok=True)
        state_path.unlink(missing_ok=True)
        print("reset: documents.jsonl e estado apagados; processando do zero", flush=True)

    done = set()
    if state_path.exists():
        try:
            done = set(json.loads(state_path.read_text(encoding="utf-8")).get("done", []))
        except Exception:
            done = set()

    # sanea documents.jsonl: mantem apenas chunks de paginas CONCLUIDAS
    # (descarta chunks parciais de uma pagina interrompida por crash)
    if documents_path.exists():
        kept = []
        for line in documents_path.read_text(encoding="utf-8").splitlines():
            try:
                if json.loads(line).get("url") in done:
                    kept.append(line)
            except Exception:
                pass
        documents_path.write_text(("\n".join(kept) + "\n") if kept else "", encoding="utf-8")

    if done:
        print(f"retomando: {len(done)} de {total_pages} paginas ja feitas serao puladas", flush=True)

    def _save_done():
        state_path.write_text(json.dumps({"done": sorted(done)}, ensure_ascii=False),
                              encoding="utf-8")

    # modo append: nunca trunca o que ja foi processado
    with documents_path.open("a", encoding="utf-8") as fout:
        for n, page in enumerate(pages, 1):
            if page["url"] in done:
                continue
            print(f"[{n}/{total_pages}] processando: {page['url']}", flush=True)
            try:
                # texto JA limpo pela Fase A (clean.jsonl) — sem reler raw/clean_html
                text = clean_map[page["url"]].get("text", "")
                if not text.strip():
                    done.add(page["url"]); _save_done()
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
                fout.flush()  # garante que a pagina foi persistida antes de marcar como feita
                done.add(page["url"]); _save_done()
                pendentes = total_pages - len(done)
                print(f"processado: {page['url']} -> {len(chunks)} chunks | "
                      f"concluidas {len(done)}/{total_pages} | faltam {pendentes}", flush=True)
            except Exception as e:
                errors += 1
                print(f"[ERRO] {page['url']}: {e}", flush=True)

    # --- finaliza: reconstroi docs_meta e contagem a partir do arquivo COMPLETO ---
    docs_meta = []
    total_chunks = 0
    seen = {}
    if documents_path.exists():
        for line in documents_path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            total_chunks += 1
            u = r.get("url", "")
            if u not in seen:
                seen[u] = {"url": u, "title": r.get("title", ""), "chunks": 0}
                docs_meta.append(seen[u])
            seen[u]["chunks"] += 1

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

    # summary.md (offload para hy3 quando SUMMARY_MODEL=None)
    print("gerando summary.md...", flush=True)
    if SUMMARY_MODEL:
        summary = build_summary(domain, url_base, docs_meta)
    else:
        summary = _summary_skeleton(domain, url_base, docs_meta)
        print("  (summary offload: esqueleto escrito; prosa PT gerada por hy3)", flush=True)
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

    ap = argparse.ArgumentParser(description="Fase C - processamento/indexacao RAG")
    ap.add_argument("--dir", required=True, help="pasta RAG/<dominio-simplificado>")
    ap.add_argument("--limpar-raw", action="store_true",
                    help="apaga raw/ ao final se o processamento for bem-sucedido")
    ap.add_argument("--chunk-model", default=cfg.get("chunk_model"),
                    help=f"modelo de chunking (default config: {cfg.get('chunk_model', CHUNK_MODEL)})")
    ap.add_argument("--summary-model", default=cfg.get("summary_model"),
                    help=f"modelo do summary (default config: {cfg.get('summary_model', SUMMARY_MODEL)})")
    ap.add_argument("--num-ctx", type=int, default=cfg.get("num_ctx"),
                    help=f"limite de contexto (default config: {cfg.get('num_ctx')})")
    ap.add_argument("--reset", action="store_true",
                    help="ignora progresso salvo e reprocessa tudo do zero")
    args = ap.parse_args()
    process(args.dir, args.limpar_raw, args.chunk_model, args.summary_model,
            args.num_ctx, args.reset)


if __name__ == "__main__":
    main()

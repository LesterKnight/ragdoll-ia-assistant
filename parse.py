"""
Fase B - Parser (limpeza: HTML -> texto limpo).

Le o HTML bruto de raw/ UMA vez, extrai apenas o conteudo util (titulos, codigo,
tabelas, texto) e grava em clean.jsonl (compacto, ~1% do tamanho do HTML).

Beneficios:
    - a Fase C (process.py) le clean.jsonl (~MBs) em vez de reparsear GBs de HTML;
- reprocessar (trocar chunk model, etc.) fica rapido;
- da para arquivar/apagar o raw/ e ainda reprocessar a partir do clean.jsonl.

Uso:
    python parse.py --dir "RAG/<dominio-simplificado>" [--reset]

E resumivel: pula paginas ja presentes no clean.jsonl.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from process import clean_html, block_text  # reusa a limpeza/extracao ja existente

import loghub

SITE = ""


def L(tipo: str, msg: str):
    if SITE:
        loghub.log(SITE, "B", tipo, msg)


def parse(dir_path: str, reset: bool = False):
    global SITE
    SITE = Path(dir_path).resolve().name
    t0 = time.perf_counter()
    out_dir = Path(dir_path).resolve()
    raw_dir = out_dir / "raw"
    manifest_file = out_dir / "crawl_manifest.json"
    clean_path = out_dir / "clean.jsonl"

    L("sucesso", f"Fase B iniciada — pasta {SITE}")
    if not manifest_file.exists():
        L("erro", f"manifesto nao encontrado em {manifest_file}")
        sys.exit(1)

    if reset:
        clean_path.unlink(missing_ok=True)
        L("sucesso", "reset: clean.jsonl apagado; reparseando do zero")

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    pages = manifest.get("pages", [])
    total = len(pages)

    # resume: pula urls ja presentes no clean.jsonl
    done = set()
    if clean_path.exists():
        for line in clean_path.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line).get("url"))
            except Exception:
                pass
    if done:
        L("sucesso", f"retomando: {len(done)} de {total} paginas ja limpas serao puladas")

    raw_bytes = 0
    clean_bytes = 0
    parsed = 0
    vazias = 0
    faltando = 0

    with clean_path.open("a", encoding="utf-8") as fout:
        for n, page in enumerate(pages, 1):
            if page["url"] in done:
                continue
            L("sucesso", f"[{n}/{total}] limpando: {page['url']}")
            html_file = raw_dir / page["file"]
            if not html_file.exists():
                faltando += 1
                L("erro", f"HTML bruto ausente para {page['url']} (pulando)")
                continue
            try:
                html = html_file.read_text(encoding="utf-8")
                raw_bytes += len(html)
                text = block_text(clean_html(html))
                if not text.strip():
                    vazias += 1
                    continue
                clean_bytes += len(text)
                rec = {"url": page["url"], "title": page.get("title", ""),
                       "file": page["file"], "text": text}
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                parsed += 1
                feitas = len(done) + parsed
            except Exception as e:
                L("excecao", f"erro ao limpar {page['url']}: {e}")

    elapsed = time.perf_counter() - t0
    L("sucesso", f"RESULTADO Fase B: {parsed} limpas | {vazias} vazias | {faltando} sem HTML | {total} total | tempo {elapsed:.1f}s")
    if raw_bytes:
        pass


def main():
    ap = argparse.ArgumentParser(description="Fase B - parser (limpeza HTML->texto)")
    ap.add_argument("--dir", required=True, help="pasta RAG/<dominio-simplificado>")
    ap.add_argument("--reset", action="store_true", help="reparseia tudo do zero")
    args = ap.parse_args()
    parse(args.dir, args.reset)


if __name__ == "__main__":
    main()

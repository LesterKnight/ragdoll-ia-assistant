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


def parse(dir_path: str, reset: bool = False):
    t0 = time.perf_counter()
    out_dir = Path(dir_path).resolve()
    raw_dir = out_dir / "raw"
    manifest_file = out_dir / "crawl_manifest.json"
    clean_path = out_dir / "clean.jsonl"

    if not manifest_file.exists():
        print(f"[ERRO]: manifesto nao encontrado em {manifest_file}", file=sys.stderr)
        sys.exit(1)

    if reset:
        clean_path.unlink(missing_ok=True)
        print("reset: clean.jsonl apagado", flush=True)

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
        print(f"retomando: {len(done)} de {total} paginas ja parseadas", flush=True)

    raw_bytes = 0
    clean_bytes = 0
    parsed = 0
    vazias = 0
    faltando = 0

    with clean_path.open("a", encoding="utf-8") as fout:
        for n, page in enumerate(pages, 1):
            if page["url"] in done:
                continue
            html_file = raw_dir / page["file"]
            if not html_file.exists():
                faltando += 1
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
                print(f"parseada: {page['url']} | concluidas {feitas}/{total} | "
                      f"faltam {total - feitas}", flush=True)
            except Exception as e:
                print(f"[ERRO] {page['url']}: {e}", flush=True)

    elapsed = time.perf_counter() - t0
    print(f"\n[RESULTADO parse]")
    print(f"clean.jsonl: {clean_path}")
    print(f"paginas parseadas nesta execucao: {parsed}")
    print(f"vazias: {vazias} | faltando raw: {faltando}")
    if raw_bytes:
        print(f"HTML lido: {raw_bytes/1024/1024:.1f} MB -> texto: {clean_bytes/1024/1024:.1f} MB "
              f"(reducao {100*(1-clean_bytes/raw_bytes):.1f}%)")
    print(f"tempo: {elapsed:.1f}s")


def main():
    ap = argparse.ArgumentParser(description="Fase B - parser (limpeza HTML->texto)")
    ap.add_argument("--dir", required=True, help="pasta RAG/<dominio-simplificado>")
    ap.add_argument("--reset", action="store_true", help="reparseia tudo do zero")
    args = ap.parse_args()
    parse(args.dir, args.reset)


if __name__ == "__main__":
    main()

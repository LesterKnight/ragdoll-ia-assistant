"""
Fase A - Captura de documentacao web.

Uso:
    python crawl.py --url <URL> --escopo <1|2|3> --delay <ms> [--limite N]

Responsabilidades (deterministicas):
- Deriva RAG/<dominio-simplificado>/ da URL
- Navega a partir da URL inicial, respeitando escopo (1/2/3) e delay
- Usa um unico navegador (headed), sessao persistente e sequencial
- Espera render completo (networkidle) antes de capturar
- Salva HTML renderizado em raw/ e monta a arvore de links (dedup)

Nao faz limpeza, chunking, embeddings ou parsing semantico (isso e o process.py).
"""

import argparse
import json
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


# ------------------------- Normalizacao -------------------------

def simplify_domain(url: str) -> str:
    """docs.godotengine.org -> docsgodotengineorg (sem www, sem pontos/aspas)."""
    host = urlparse(url).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return re.sub(r"[^a-z0-9]", "", host.lower())


def normalize_url(url: str) -> str:
    """Remove fragmento (#secao) e barra final para deduplicar."""
    url, _ = urldefrag(url)
    if url.endswith("/") and len(urlparse(url).path) > 1:
        url = url[:-1]
    return url


def same_domain(url: str, base_host: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host == base_host


def base_host_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def url_to_filename(url: str) -> str:
    """Converte URL em nome de arquivo seguro para raw/."""
    p = urlparse(url)
    path = p.path.strip("/")
    if not path:
        path = "index"
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", path)
    if not safe.endswith(".html"):
        safe += ".html"
    return safe


# ------------------------- Extracao de links -------------------------

def extract_links(html: str, current_url: str, base_host: str):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        absolute = urljoin(current_url, a["href"])
        absolute = normalize_url(absolute)
        if absolute.startswith("http") and same_domain(absolute, base_host):
            links.append(absolute)
    return list(dict.fromkeys(links))


# ------------------------- Crawl principal -------------------------

def crawl(url: str, escopo: int, delay_ms: int, limite: int, restart_every: int = 40):
    base_host = base_host_of(url)
    domain_slug = simplify_domain(url)
    project_root = Path(__file__).resolve().parent
    out_dir = project_root / "RAG" / domain_slug
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    start = normalize_url(url)
    delay_s = max(0, delay_ms) / 1000.0

    manifest = []
    errors = []
    visited = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        pages_since_restart = 0

        def restart_browser():
            nonlocal browser, page, pages_since_restart
            page.close()
            browser.close()
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            pages_since_restart = 0

        # escopo = profundidade a partir da URL inicial (1=so ela, 2=+links, 3=+links dos links)
        queue = deque([(start, 1)])

        while queue:
            if limite and len(manifest) >= limite:
                break
            current, depth = queue.popleft()
            current = normalize_url(current)
            if current in visited:
                continue
            visited.add(current)

            try:
                page.goto(current, wait_until="domcontentloaded", timeout=30000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except PWTimeout:
                    pass  # render pesado; segue com o que tem
                html = page.content()
                title = page.title()

                fname = url_to_filename(current)
                (raw_dir / fname).write_text(html, encoding="utf-8")
                manifest.append({"url": current, "file": fname, "title": title, "depth": depth})
                print(f"[URL]: {current}")
                print(f"[STATUS]: sucesso")

                # descobre links da pagina se ainda houver profundidade no escopo
                if depth < escopo:
                    for link in extract_links(html, current, base_host):
                        if link not in visited:
                            queue.append((link, depth + 1))

            except Exception as e:
                errors.append({"url": current, "error": str(e)})
                print(f"[URL]: {current}")
                print(f"[STATUS]: falha")
                print(f"[ERRO]: {e}")

            pages_since_restart += 1
            if pages_since_restart >= restart_every:
                restart_browser()

            if delay_s:
                time.sleep(delay_s)

        page.close()
        browser.close()

    # manifesto da captura (consumido pelo process.py)
    manifest_data = {
        "url_base": start,
        "domain": base_host,
        "domain_slug": domain_slug,
        "escopo": escopo,
        "delay_ms": delay_ms,
        "discovery": "crawl",
        "pages": manifest,
        "errors": errors,
    }
    (out_dir / "crawl_manifest.json").write_text(
        json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n[RESULTADO]")
    print(f"pasta: {out_dir}")
    print(f"paginas: {len(manifest)}")
    print(f"erros: {len(errors)}")
    return manifest_data


def main():
    from config_util import load_config
    cfg = load_config("config_espiao.json").get("crawl", {})

    ap = argparse.ArgumentParser(description="Fase A - captura de documentacao")
    ap.add_argument("--url", required=True)
    ap.add_argument("--escopo", type=int, choices=[1, 2, 3], default=cfg.get("escopo", 2),
                    help=f"profundidade (default do config: {cfg.get('escopo', 2)})")
    ap.add_argument("--delay", type=int, default=cfg.get("delay_ms", 2000),
                    help=f"delay entre requisicoes em ms (default: {cfg.get('delay_ms', 2000)})")
    ap.add_argument("--limite", type=int, default=cfg.get("limite", 0),
                    help=f"limite de paginas, 0 = sem limite (default: {cfg.get('limite', 0)})")
    args = ap.parse_args()

    if not args.url.startswith(("http://", "https://")):
        print("[ERRO]: URL deve iniciar com http:// ou https://", file=sys.stderr)
        sys.exit(1)

    crawl(args.url, args.escopo, args.delay, args.limite)


if __name__ == "__main__":
    main()

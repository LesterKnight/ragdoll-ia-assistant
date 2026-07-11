"""Teste pontual: qwen2.5-coder:1.5b como chunker semantico (mesmo papel do gemma4).
Nao toca em clean.jsonl/documents.jsonl — limpa o HTML cru direto do raw/."""
import json, time, sys
from pathlib import Path
import process as P

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:1.5b"
P.CHUNK_MODEL = MODEL

raw_dir = Path("RAG/docsgodotengineorg/raw")
manifest = json.loads(Path("RAG/docsgodotengineorg/crawl_manifest.json",
                           encoding="utf-8").read_text())
pages = manifest["pages"]

N = 10
idxs = [round(i * (len(pages) - 1) / (N - 1)) for i in range(N)]  # amostra distribuida
sample = [pages[i] for i in idxs]

fallback_events = 0
fallback_pages = 0
orig_fb = P.chunk_by_headings
def track(text):
    global fallback_events
    fallback_events += 1
    return orig_fb(text)
P.chunk_by_headings = track

def clean_text(page):
    html = (raw_dir / page["file"]).read_text(encoding="utf-8", errors="ignore")
    return P.block_text(P.clean_html(html))

print(f"TESTE chunker={P.CHUNK_MODEL} | {N} paginas (amostra distribuida)", flush=True)
t0 = time.perf_counter()
for i, page in enumerate(sample, 1):
    before = fallback_events
    text = clean_text(page)
    chunks = P.chunk_semantic(text)
    if fallback_events > before:
        fallback_pages += 1
    print(f"[{i}/{N}] idx={idxs[i-1]} {page['url']} -> {len(chunks)} chunks | "
          f"fallback={'SIM' if fallback_events > before else 'nao'}", flush=True)

elapsed = time.perf_counter() - t0
print(f"\n[RESULTADO] {P.CHUNK_MODEL}", flush=True)
print(f"paginas com fallback: {fallback_pages}/{N} ({100*fallback_pages/N:.0f}%)", flush=True)
print(f"eventos de fallback (secoes): {fallback_events}", flush=True)
print(f"tempo total: {elapsed:.1f}s", flush=True)

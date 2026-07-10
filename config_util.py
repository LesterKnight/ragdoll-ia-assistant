"""
Carregador simples de config JSON para defaults dos agentes.

Precedencia: CLI (argparse) > arquivo de config > default hardcoded.
Uso tipico:
    cfg = load_config("config_espiao.json")
    valor = cfg.get("crawl", {}).get("delay_ms", 2000)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_config(nome: str) -> dict:
    """Le um JSON de config na raiz do projeto. Retorna {} se nao existir ou for invalido."""
    caminho = ROOT / nome
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[aviso] config {nome} invalida, usando defaults internos: {e}")
        return {}

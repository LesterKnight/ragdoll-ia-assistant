"""
Configuracao central do ragdoll (um unico arquivo: config.json).

Tudo que e parametrizavel e SEGURO de mudar em runtime vive aqui.
Parametros que quebram o app se alterados entre etapas (ex.: modelo de
embedding, que precisa ser igual na indexacao e na consulta) SAO mantidos
no arquivo, mas NAO sao exposotos na UI (ui=False no SCHEMA).

Precedencia: CLI (argparse) > config.json > DEFAULTS.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"

# Modelos disponiveis (para os <select> da UI). Ajuste conforme seu Ollama.
MODEL_OPTIONS = [
    "qwen2.5-coder:1.5b",
    "qwen2.5-coder:7b",
    "qwen3.6",
    "qwythos9b",
    "gemma4",
    "bati-ai/qwen3.6-27b",
]


DEFAULTS = {
    "ollama": {
        "url": "http://localhost:11434",
        "embed_model": "nomic-embed-text",
    },
    "crawl": {
        "escopo": 2,
        "delay_ms": 2000,
        "limite": 0,
        "nav_timeout": 30000,
        "idle_timeout": 15000,
    },
    "process": {
        "chunk_model": "qwen2.5-coder:1.5b",
        "summary_model": None,
        "num_ctx": 16384,
    },
    "query": {
        "model": "qwen2.5-coder:1.5b",
        "topk": 5,
    },
    "programador": {
        "model": "qwen2.5-coder:7b",
        "topk": 15,
        "idioma": "pt",
        "reescrever": False,
    },
    "benchmark": {
        "model": "qwen2.5-coder:7b",
        "topk": 15,
        "num_predict": 600,
        "temperature": 0.2,
        "lang": "GDScript",
        "ext": "gd",
        "tasks": "stage_d/tasks_godot.json",
    },
}

# SCHEMA: cada campo editavel na aba Configuracoes.
# ui=False => existe no config mas NAO aparece na UI (mudanca perigosa).
SCHEMA = [
    # Ollama
    {"path": "ollama.url", "group": "Ollama", "label": "URL do Ollama", "type": "url", "ui": True,
     "help": "Endpoint do Ollama. Usado por todas as etapas que chamam LLM/embeddings."},
    {"path": "ollama.embed_model", "group": "Ollama", "label": "Modelo de embedding", "type": "text", "ui": False,
     "help": "Fixo: nao mudar (quebraria a compatibilidade dos vetores indexados vs consultados)."},

    # Coleta (Fase A)
    {"path": "crawl.escopo", "group": "Coleta (Fase A)", "label": "Escopo", "type": "select",
     "options": [1, 2, 3], "ui": True,
     "help": "Profundidade do crawl (1 = so a pagina; 2/3 seguem mais links)."},
    {"path": "crawl.delay_ms", "group": "Coleta (Fase A)", "label": "Delay entre requisicoes (ms)",
     "type": "number", "min": 0, "max": 60000, "ui": True},
    {"path": "crawl.limite", "group": "Coleta (Fase A)", "label": "Limite de paginas (0 = sem limite)",
     "type": "number", "min": 0, "max": 100000, "ui": True},
    {"path": "crawl.nav_timeout", "group": "Coleta (Fase A)", "label": "Timeout de navegacao (ms)",
     "type": "number", "min": 1000, "max": 300000, "ui": True},
    {"path": "crawl.idle_timeout", "group": "Coleta (Fase A)", "label": "Timeout de idle (ms)",
     "type": "number", "min": 1000, "max": 300000, "ui": True},

    # Indexacao (Fase C)
    {"path": "process.chunk_model", "group": "Indexacao (Fase C)", "label": "Modelo de chunking",
     "type": "select", "options": MODEL_OPTIONS, "ui": True},
    {"path": "process.summary_model", "group": "Indexacao (Fase C)", "label": "Modelo de resumo (vazio = offload)",
     "type": "select", "options": [""] + MODEL_OPTIONS, "ui": True},
    {"path": "process.num_ctx", "group": "Indexacao (Fase C)", "label": "Contexto (num_ctx)",
     "type": "number", "min": 2048, "max": 131072, "ui": True},

    # Consulta (Uso)
    {"path": "query.model", "group": "Consulta (Uso)", "label": "Modelo de resposta",
     "type": "select", "options": MODEL_OPTIONS, "ui": True},
    {"path": "query.topk", "group": "Consulta (Uso)", "label": "Top-k trechos",
     "type": "number", "min": 1, "max": 50, "ui": True},

    # Geracao de codigo (Uso)
    {"path": "programador.model", "group": "Geracao de codigo (Uso)", "label": "Modelo de geracao",
     "type": "select", "options": MODEL_OPTIONS, "ui": True},
    {"path": "programador.topk", "group": "Geracao de codigo (Uso)", "label": "Top-k trechos",
     "type": "number", "min": 1, "max": 50, "ui": True},
    {"path": "programador.idioma", "group": "Geracao de codigo (Uso)", "label": "Idioma dos comentarios",
     "type": "select", "options": ["pt", "en"], "ui": True},
    {"path": "programador.reescrever", "group": "Geracao de codigo (Uso)", "label": "Reescrever tarefa em termos de busca",
     "type": "bool", "ui": True},

    # Avaliacao (Etapa D)
    {"path": "benchmark.model", "group": "Avaliacao (Etapa D)", "label": "Modelo de sintese",
     "type": "select", "options": MODEL_OPTIONS, "ui": True},
    {"path": "benchmark.topk", "group": "Avaliacao (Etapa D)", "label": "Top-k trechos",
     "type": "number", "min": 1, "max": 50, "ui": True},
    {"path": "benchmark.num_predict", "group": "Avaliacao (Etapa D)", "label": "Limite de tokens",
     "type": "number", "min": 50, "max": 8192, "ui": True},
    {"path": "benchmark.temperature", "group": "Avaliacao (Etapa D)", "label": "Temperatura",
      "type": "number", "min": 0, "max": 2, "step": 0.05, "ui": True},
    # Obs.: linguagem, extensao, arquivo de tarefas e modo deixaram de ser configuracoes
    # fixas; agora sao parametros de CADA rodada, escolhidos no painel da aba Avaliacao.
    # Mantidos aqui apenas como defaults internos (nao editaveis na UI).
]


# ----------------------------- helpers -----------------------------------

def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(name: str = None) -> dict:
    """Le a config. Se `name` for dado (legado), le aquele arquivo avulso.
    Senao, mescla config.json sobre os DEFAULTS."""
    if name:
        p = ROOT / name
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    user = {}
    if CONFIG_PATH.exists():
        try:
            user = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            user = {}
    return _merge(DEFAULTS, user)


def save_config(data: dict):
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_path(d: dict, path: str, default=None):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def set_path(d: dict, path: str, value):
    parts = path.split(".")
    cur = d
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _coerce(raw, spec):
    t = spec["type"]
    if t == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if t in ("number", "select"):
        opts = spec.get("options")
        numeric_opts = opts and all(_is_number(o) for o in opts)
        if isinstance(raw, bool):
            raise ValueError("tipo invalido")
        s = str(raw).strip()
        if t == "number" or numeric_opts:
            if "." in s or spec.get("step"):
                return float(s)
            return int(s)
        # select textual
        if opts is not None and s not in [str(o) for o in opts] and s not in opts:
            if s == "" and spec.get("path") == "process.summary_model":
                return None
            raise ValueError("valor fora das opcoes")
        return s
    # text / url
    return str(raw)


def _in_range(val, spec):
    if not _is_number(val):
        return True
    if spec.get("min") is not None and val < spec["min"]:
        return False
    if spec.get("max") is not None and val > spec["max"]:
        return False
    return True


def validate_and_apply(values: dict):
    """Aplica `values` ({path: raw}) validando tipos/intervalo.
    So aceita campos com ui=True. Retorna (config_mesclado, erros)."""
    cfg = load_config()
    errors = {}
    ui = {s["path"]: s for s in SCHEMA if s.get("ui")}
    for path, raw in values.items():
        spec = ui.get(path)
        if not spec:
            errors[path] = "campo nao editavel pela UI"
            continue
        try:
            val = _coerce(raw, spec)
        except Exception as e:
            errors[path] = f"valor invalido: {e}"
            continue
        if not _in_range(val, spec):
            errors[path] = f"fora do intervalo [{spec.get('min')}, {spec.get('max')}]"
            continue
        set_path(cfg, path, val)
    if errors:
        return cfg, errors
    save_config(cfg)
    return cfg, errors

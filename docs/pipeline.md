# Pipeline: arquivos e orquestração

Resumo autocontido da arquitetura de execução do RagThulhu, para fechar as
dúvidas recorrentes: **(1) quais arquivos Python compõem a pipeline** e
**(2) se as etapas precisam de um agente orquestrador**. Tudo aqui já existe
espalhado por "Como funciona" / "Três momentos" / "Componentes" — este arquivo
apenas consolida.

## 1. Os passos rodam em arquivos Python? Sim

Cada estágio é um script Python autônomo, com responsabilidade única e
**retomável** (pula trabalho já feito). O encadeamento é feito por `run.py`.

| Estágio | Arquivo | Entrada → Saída | Responsabilidade |
|---|---|---|---|
| **Fase A — Captura** | `crawl.py` | URL → `raw/` + `crawl_manifest.json` | Playwright navega o site (escopo 1/2/3 + delay anti-ban), respeita profundidade, salva HTML renderizado. Não limpa nem indexa. |
| **Fase B — Limpeza** | `parse.py` | `raw/*.html` → `clean.jsonl` | Extrai só conteúdo útil (títulos, código, tabelas, texto) e grava JSONL compacto. Retomável. |
| **Fase C — Indexação** | `process.py` | `clean.jsonl` → `documents.jsonl` + `index.json` + `summary.md` + `RAG/index.md` | Chunking semântico (`qwen2.5-coder:1.5b`), embeddings (`nomic-embed-text`), catálogo-mestre. |
| **Orquestrador A→B→C** | `run.py` | — | Encadeia `crawl.py` → `parse.py` → `process.py` via `subprocess` (sequencial; Fase C em background). Subcomandos `all`/`crawl`/`parse`/`process` + retomada. |
| **Etapa D — Avaliação** | `stage_d/benchmark.py` | base indexada → métricas RAG × SEM-RAG | Compara RAG contra PURO, valida com compilador do usuário (genérico). Incremental (`manifest.json`). |

**Consumidores (fora do treino A/B/C):** `query.py` (busca em linguagem natural),
`programador.py` (geração de código fundamentada no RAG), `rag_retrieve.py`
(recuperação por cosseno compartilhada). O serviço web é `server.py` + `templates.py`.

## 2. Precisa de um agente orquestrador? Não (para A→B→C)

As etapas são **modulares por design**, mas completas e retomáveis — **não
precisam de um agente de IA para rodar**. `run.py` é um **orquestrador de
script** (chamadas `subprocess` sequenciais), não um agente. A execução mecânica
já existe.

Os modelos locais são bons para tarefas estreitas (chunk, embed, resumo,
gerar/compor código a partir de trechos), mas **não navegam nem entendem a
estrutura do projeto** — essa decisão de *o que* rodar é sua ou do assistente
remoto (hy3). Ou seja: o *porquê* é humano/assistente; o *como* é script.

Os **agentes** (`.opencode/agents/extrator.md`, `programador.md`, `qa.md`) são
subagentes do OpenCode para tarefas **específicas** e só entram em dois momentos
à parte do core:

- **Uso / Consumo** (`programador.py` + agente `qa`): loop gerar → QA → entregar.
- **Etapa D** (`benchmark.py` + agente `qa`): avaliação RAG × PURO.

Eles **nunca** participam do treinamento A/B/C.

## Diagrama de dependências

```
URL
 │  python run.py all --url <URL> --escopo N --delay MS [--limite K]
 ▼
[crawl.py]   ──A──▶  raw/ + crawl_manifest.json
 │
 ▼  parse.py
[parse.py]   ──B──▶  clean.jsonl
 │
 ▼  process.py  (background)
[process.py] ──C──▶ documents.jsonl + index.json + summary.md + RAG/index.md
                       │
                       ▼  (consumo — fora do treino A/B/C)
                  query.py / programador.py  ──▶  rag_retrieve.py
                       │
                       ▼  Etapa D (isolada do core)
                  stage_d/benchmark.py  +  agente qa
```

## Exemplo mínimo ponta a ponta

Construir uma base pequena (só a página inicial) e depois avaliá-la:

```bash
# Treino A→B→C (Fase C sobe em background)
python run.py all --url "https://docs.godotengine.org/" --escopo 1 --delay 2000 --limite 1

# Consumo (exemplo): pergunta fundamentada na base
python query.py --dir RAG/docsgodotengineorg --q "como mover um CharacterBody2D?"

# Etapa D: avaliar ganho do RAG vs SEM-RAG
python stage_d/benchmark.py --domain docsgodotengineorg --lang GDScript --ext gd \
    --tasks stage_d/tasks_godot.json
```

`--escopo 1` captura só a página inicial; `2` = 1 nível de links; `3` = crawling
profundo. `--limite N` limita o número de páginas (0 = sem limite).

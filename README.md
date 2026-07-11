# ragdoll

Sistema local de **RAG de documentação** com **geração de código fundamentada**.

Captura a documentação de qualquer site, transforma em uma base pesquisável por
significado e usa essa base para responder perguntas e **gerar código apoiado na
documentação real** — compensando o desconhecimento de modelos locais menores.

Tudo roda **localmente** via [Ollama](https://ollama.com), sem enviar dados para a nuvem.

---

## Como funciona

```
FASE A (captura)   FASE B (limpeza)   FASE C (indexação)        USO (fora das fases)
crawl.py           parse.py            process.py                query.py / programador.py
   │                  │                    │                          │
 navega o site    HTML → texto limpo  chunk + embeddings →     busca semantica (cosseno)
 (Playwright)     (clean.jsonl)       documents.jsonl          → contexto → modelo responde/gera
```

1. **Fase A — Captura** (`crawl.py`): um navegador único (Playwright) percorre o site em
   sequência, respeitando profundidade (escopo) e delay entre requisições (anti-ban).
   Saída: `raw/` + `crawl_manifest.json`.
2. **Fase B — Limpeza** (`parse.py`): remove navegação/rodapé, preserva código/tabelas/
   títulos e gera `clean.jsonl` (texto limpo por página).
3. **Fase C — Indexação** (`process.py`): corta em chunks semânticos, gera embeddings e
   monta a base (`documents.jsonl` + `index.json` + `summary.md` + `RAG/index.md`).
4. **Uso / Consumo** (fora das fases): recupera os trechos mais relevantes por similaridade
   e entrega ao modelo para responder (`query.py`) ou gerar código (`programador.py`).

---

## Componentes

| Arquivo | Papel |
|---------|-------|
| `crawl.py` | Fase A — captura das páginas |
| `parse.py` | Fase B — limpeza (HTML → clean.jsonl) |
| `process.py` | Fase C — indexação (chunking, embeddings, summary) |
| `query.py` | uso — consulta em linguagem natural |
| `programador.py` | uso — geração de código fundamentada no RAG |
| `rag_retrieve.py` | recuperação compartilhada (busca por cosseno) |
| `config_espiao.json` | defaults de captura/processamento |
| `config_programador.json` | defaults da geração de código |
| `.opencode/agents/espiao.md` | agente orquestrador de captura |
| `.opencode/agents/programador.md` | agente de programação |
| `.opencode/tools/code_generator.ts` | expõe o gerador como ferramenta |

---

## Modelos (Ollama)

| Papel | Modelo |
|-------|--------|
| Chunking semântico | `gemma4` |
| Resumo (`summary.md`) | `qwen3.6` |
| Embeddings (768d) | `nomic-embed-text` |
| Geração de código | `qwen2.5-coder:7b` |
| Consulta rápida | `qwen2.5-coder:1.5b` |

---

## Instalação

```bash
pip install -r requirements.txt
python -m playwright install chromium

ollama pull nomic-embed-text
ollama pull qwen2.5-coder:7b
# (gemma4, qwen3.6 e qwen2.5-coder:1.5b conforme uso)
```

---

## Uso

### 1. Capturar documentação
```bash
python crawl.py --url "https://docs.exemplo.com/inicio" --escopo 2 --delay 2000
python parse.py --dir "RAG/docsexemplocom"
python process.py --dir "RAG/docsexemplocom"
```
> A pasta de saída é derivada do domínio: `RAG/<dominio-simplificado>/`.

### 2. Consultar
```bash
python query.py "como faço X?"
```

### 3. Gerar código fundamentado na doc
```bash
python programador.py "crie uma função que faz Y" --out solucao.gd --fontes
```
> `--fontes` mostra os trechos da documentação usados (transparência do RAG).

---

## Estrutura da base gerada

```
RAG/
├── index.md                    catálogo-mestre de todas as docs processadas
└── <dominio-simplificado>/
    ├── raw/                    HTML renderizado (fonte para reprocessar)
    ├── documents.jsonl         chunks + vetores + metadados (o coração do RAG)
    ├── index.json              índice da pasta
    └── summary.md              resumo da documentação
```

---

## Requisitos

- Python 3.12+
- Ollama rodando localmente (`localhost:11434`)
- GPU recomendada (testado em RTX 3060 Ti, 8GB)

---

## Notas de projeto

- O crawling é **sequencial** e com delay, priorizando **não ser bloqueado**.
- A base RAG (`RAG/`) **não é versionada** — é regenerável a partir dos scripts.
- Detalhes de arquitetura e decisões em [`requisito.md`](./requisito.md).

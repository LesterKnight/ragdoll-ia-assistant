# ragdoll

Sistema local de **RAG de documentação** com **geração de código fundamentada**.

Captura a documentação de qualquer site, transforma em uma base pesquisável por
significado e usa essa base para responder perguntas e **gerar código apoiado na
documentação real** — compensando o desconhecimento de modelos locais menores.

A **indexação** roda 100% local via [Ollama](https://ollama.com). O **consumo** (perguntas/código) e o **resumo** podem ser offload para o assistente hy3 (nuvem) — ver seção "Offload de síntese".

> ⚡ **SEÇÃO PARA IAs LOCAIS PEQUENAS** — leia apenas até o marcador `<!-- FIM-IA -->` abaixo.
> Assim que tiver as instruções, **PARE de ler este arquivo** e execute/retorne o que foi pedido.
> Não processe as seções seguintes (humanos: podem ignorar este bloco).

## Início rápido para IAs pequenas

Orquestrador (recomendado — a lógica fica no script, não no modelo):
- `python run.py all --url "<URL>" --escopo 2 --delay 2000` → Fase A→B→C (Fase C em background)
- `python run.py process --dir RAG/<dominio>` → retoma só a Fase C se o job cair
  - Exemplo real: `python run.py process --dir RAG/docsgodotengineorg` retoma a indexação do Godot docs
- flags: `--foreground` (rodar no terminal), `--limpar-raw`, `--chunk-model`, `--summary-model`, `--reset`

Comandos diretos (um por fase):
- `python crawl.py --url "<URL>" --escopo 1|2|3 --delay <ms> [--limite N]`
- `python parse.py --dir "RAG/<dominio>" [--reset]`
- `python process.py --dir "RAG/<dominio>" [--limpar-raw] [--chunk-model M] [--summary-model M] [--reset]`
- `python query.py "pergunta" [--dominio <slug>] [--topk N]`
- `python programador.py "tarefa" --dominio <slug> --out arquivo.gd [--model M] [--topk N] [--reescrever] [--fontes]`

Modelos (Ollama, locais): chunking `qwen2.5-coder:1.5b` · embeddings `nomic-embed-text`. Resumo e uso são **offload para o hy3** (sem modelo local de síntese).
Pasta de saída: `RAG/<dominio-simplificado>/` (ex.: `docs.godotengine.org` → `RAG/docsgodotengineorg`).

**Não leia o resto do README.** <!-- FIM-IA -->

---

## Objetivo

Construir uma base RAG de documentação que roda 100% offline (exceto a API do
Ollama local). A base é **construída** localmente (Fases A→C) e **consumida** em
runtime por um modelo que cabe na GPU, rápido, compensando sua falta de
conhecimento via recuperação semântica.

> Os modelos locais são bons para tarefas **estreitas** (chunk, embed, resumo,
> responder/compor código a partir de trechos). Eles **não** navegam nem entendem
> a estrutura/razão do projeto — essa orquestração é feita pelo assistente remoto
> (hy3) ou por você.

---

## Como funciona

```
FASE A (captura)   FASE B (limpeza)   FASE C (treinamento)      USO (consumo)        ETAPA D (avaliacao)
crawl.py           parse.py            process.py                query.py /          stage_d/benchmark.py
   │                  │                    │                       programador.py          │
  navega o site    HTML → texto limpo  chunk + embeddings →     busca semantica      compara RAG x PURO
  (Playwright)     (clean.jsonl)       documents.jsonl          (cosseno) → modelo   + valida no Godot
                                            │                    responde/gera              │
                                            └──── base RAG ───────┘  ◄──────────────── qa (agente de avaliacao)
```

> **Core (A/B/C) = ler websites + treinamento/indexação.** O consumo
> (`query.py`/`programador.py`) usa a base; a **Etapa D** (`stage_d/`) é a
> avaliação isolada — não polui o core e só depende de `programador.py` + Godot.

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

## Três momentos distintos (treinamento × uso × avaliação)

O projeto tem **três momentos isolados**; o loop de gerar→QA só existe em um deles.

1. **Treinamento (Fases A/B/C) — construção da base.** `crawl.py` → `parse.py` →
   `process.py` apenas capturam, limpam e indexam (chunk + embeddings + resumo).
   **Não geram nem verificam código** e **nunca** acionam o agente `programador`
   nem o QA. O chunking usa `qwen2.5-coder:1.5b`; o resumo é offload para o hy3.
   Tudo vive em `RAG/` (gitignored).

2. **Uso / Consumo — geração para o usuário.** `programador.py` (+ `code_generator`)
   recupera trechos do RAG e gera código com `qwen2.5-coder:7b`. **Aqui** vale o
   fluxo gerar → **QA** (`qa.md`, que confere contra o RAG e roda o validador) →
   **só entrega ao usuário se PASS**. Falhando, regenera em loop. É o único lugar
   do loop de verificação.

3. **Etapa D — Avaliação (isolada em `stage_d/`).** `benchmark.py` / agente `qa`
   comparam RAG × SEM-RAG e medem validade (compilador do usuário). É desvinculada
   do core e do consumo: não indexa e não entrega código ao usuário.

> O QA com RAG é usado tanto no **Uso** (filtrar o código entregue) quanto na
> **Etapa D** (avaliar o ganho do RAG). Em nenhum dos dois ele participa do
> **Treinamento**.

---

## Componentes

| Arquivo | Papel |
|---------|-------|
| `crawl.py` | Fase A — captura das páginas |
| `parse.py` | Fase B — limpeza (HTML → clean.jsonl) |
| `process.py` | Fase C — indexação (chunking, embeddings, summary) |
| `run.py` | orquestrador (A→B→C + retomada) |
| `query.py` | uso — consulta em linguagem natural |
| `programador.py` | uso — geração de código fundamentada no RAG |
| `rag_retrieve.py` | recuperação compartilhada (busca por cosseno) |
| `stage_d/benchmark.py` | **Etapa D** — avaliação: RAG x PURO + validação no Godot (isolada do core) |
| `config_espiao.json` | defaults de captura/processamento |
| `config_programador.json` | defaults da geração de código |
| `.opencode/agents/espiao.md` | agente orquestrador de captura |
| `.opencode/agents/programador.md` | agente de programação (consumer) |
| `.opencode/agents/qa.md` | **Etapa D** — agente de QA: compara RAG x PURO e valida c/ compilador do usuario (generico) |
| `.opencode/tools/code_generator.ts` | expõe o gerador como ferramenta |

---

## Modelos (Ollama)

| Papel | Modelo | Override |
|-------|--------|----------|
| Chunking semântico (Fase C) | `qwen2.5-coder:1.5b` (leve, 0% fallback) | `process.py --chunk-model` |
| Resumo (`summary.md`, Fase C) | **offload p/ hy3** (`SUMMARY_MODEL=None`) | `process.py --summary-model M` |
| Embeddings (768d) | `nomic-embed-text` | — |
| Uso / geração de código | **offload p/ hy3** (ou `qwythos9b` local p/ uso offline) | `programador.py --model` |
| Tarefas auxiliares (`small_model`) | `ollama/qwythos9b` | config global do OpenCode |

- Modelos de raciocínio (`qwen3`, `qwythos`) rodam com `think: false` na geração —
  mais rápido e evita blocos `<think>` na saída.
- Chunking roda com `qwen2.5-coder:1.5b` (~1GB, cabe folgado na RTX 3060 Ti de 8GB).
  A síntese (resumo/Uso) foi **offload para o hy3** — ver seção abaixo.

---

## Offload de síntese para o hy3

O `qwythos9b` só faz **síntese** (resumo da base + responder/gerar código no Uso) — nunca
o trabalho pesado (chunk/embed). Como essas são poucas chamadas e o assistente remoto (hy3)
sintetiza melhor, o `qwythos9b` foi **removido do pipeline local** e seu papel foi assumido
pelo hy3:

- **Fase C — `summary.md`**: o `process.py` escreve um **esqueleto estrutural** (seções +
  contagens/títulos) e marca o offload; a **prosa em português é redigida pelo hy3** sob
  demanda (veja `RAG/docsgodotengineorg/summary.md` como exemplo). Para usar um modelo local
  mesmo assim, passe `--summary-model qwythos9b`.
- **Uso / Consumo**: em vez de `query.py`/`programador.py` chamarem `qwythos9b`, **pergunte
  ao hy3**, que recupera os chunks relevantes de `documents.jsonl` e responde/gera código.
  Os scripts `query.py`/`programador.py` permanecem disponíveis para **uso 100% offline**
  (com `qwythos9b` local), se a privacidade exigir.

Ganho: a GPU local passa a rodar só `qwen2.5-coder:1.5b` (chunk, 1GB) + `nomic-embed-text`
(embed) — libera ~6.8GB de VRAM que o `qwythos9b` ocupava.

---

## Estrutura de arquivos do projeto

```
<raiz-do-projeto>/
├── crawl.py                      ← Fase A (captura HTML)
├── parse.py                      ← Fase B (limpeza: HTML → clean.jsonl)
├── process.py                    ← Fase C (indexação, consome clean.jsonl)
├── query.py                      ← uso/consumo (busca + resposta) [fora das fases]
├── programador.py                ← uso/consumo (geração de código) [fora das fases]
├── rag_retrieve.py               ← recuperação semântica compartilhada
├── requirements.txt              ← dependências Python
├── config_espiao.json            ← defaults de captura/processamento
├── config_programador.json       ← defaults da geração de código
├── docs/                          ← documentação centralizada
│   ├── README.md                  ← este documento (fonte única)
│   ├── NEXT_STEPS.md              ← próximos passos e ideias
│   ├── gaps_qwythos_gdscript.md   ← baseline Qwythos SEM RAG (análise)
│   └── stage_d.md                 ← documentação da Etapa D
├── .opencode/agents/espiao.md    ← o agente maestro (orquestração)
├── .opencode/agents/programador.md ← agente de programação
├── .opencode/tools/code_generator.ts ← custom tool que expõe o gerador
└── RAG/
    ├── index.md                  ← catálogo-mestre de todos os scraps
    └── <dominio-simplificado>/
        ├── raw/                  ← HTML renderizado (fonte p/ reprocessar; opcional)
        ├── crawl_manifest.json   ← manifesto da captura (consumido pelas Fases B e C)
        ├── clean.jsonl           ← texto limpo por página (SAÍDA Fase B)
        ├── documents.jsonl       ← {texto, vetor, metadados} por chunk (coração do RAG)
        ├── index.json            ← índice de docs da pasta
        ├── summary.md            ← resumo (qwythos9b, adaptativo)
        └── process_state.json    ← progresso da Fase C (indexação, retomada)
```

---

## Arquivos de configuração (defaults)

Dois JSON na raiz definem os defaults dos agentes. Precedência:
**CLI > arquivo de config > default interno**.

`config_espiao.json` (captura + processamento):
```json
{
  "crawl":   { "escopo": 2, "delay_ms": 2000, "limite": 0 },
  "process": { "chunk_model": "qwen2.5-coder:1.5b", "summary_model": null, "num_ctx": 16384 }
}
```
- `num_ctx` limita o KV cache do modelo (evita crash do modelo de raciocínio na VRAM de 8GB).

`config_programador.json` (geração de código):
```json
{ "model": "qwythos9b", "topk": 5, "idioma": "pt", "dominio": null, "reescrever": false }
```
- `model` = modelo usado por `programador.py` (arg `--model` sobrescreve).
- O modelo do **orquestrador** (agente `@programador`) fica no próprio
  `.opencode/agents/programador.md` (trocável ali). Alvo: usar o melhor modelo que
  couber na GPU nos dois papéis (atualmente `qwythos9b`, unificado).

Loader: `config_util.py` (lê o JSON; se ausente/inválido, cai nos defaults internos).

---

## Normalização de domínio

- subdomínios **separados** (`docs.` ≠ `api.`)
- remover `www`
- ignorar protocolo e porta
- remover pontos/aspas/caracteres inválidos
- ex: `https://docs.godotengine.org/...` → `RAG/docsgodotengineorg/`

---

## Fase A — `crawl.py` (captura)

> Fase A produz os HTMLs (`raw/` + `crawl_manifest.json`). A limpeza (Fase B) e a
> indexação (Fase C) consomem essa saída. A limpeza NÃO pertence à Fase C.

Tecnologia: **Playwright**, navegador **único**, **com tela** (headed), sessão persistente, sequencial.

Uso:
```
python crawl.py --url "<URL>" --escopo <1|2|3> --delay <ms> [--limite N]
```

Fluxo:
```
1. deriva RAG/<dominio-simplificado>/ da URL
2. crawl a partir da URL inicial (SEM sitemap):
     escopo = profundidade a partir da URL
       1 = só a página informada
       2 = a página + links diretos
       3 = a página + links + links dos links
3. para cada URL (respeitando escopo + delay):
     visita → espera domcontentloaded → tenta networkidle (timeout tolerante)
     → salva HTML renderizado em raw/
     → extrai links do mesmo domínio → cresce a árvore
        (dedup: conjunto de "vistas" + normalização de URL: sem fragmento #, sem barra final)
     → navega para a próxima (mesmo navegador)
4. gera crawl_manifest.json e fecha navegador
```

- **Sitemap foi removido**: conflitava com o conceito de escopo (listava o site inteiro e pegava versão errada). O escopo a partir da URL inicial é a única forma de descoberta.
- Anti-ban: uma sessão humana, sequencial, delay explícito, cache de assets reusado.
- Robustez: reinício do navegador a cada 40 páginas (memória).
- Saída em tempo real: `[URL]` / `[STATUS]: sucesso|falha` / `[ERRO]`.

---

## Fase B — `parse.py` (limpeza: HTML → `clean.jsonl`)

> Consome os HTMLs da Fase A e gera `clean.jsonl` (texto limpo por página). A Fase C
> (indexação) consome **apenas** o `clean.jsonl` — nunca reparseia o `raw/`.

Uso:
```
python parse.py --dir "RAG/<dominio-simplificado>"
```

Detalhes:
- Remove nav/menu/footer/sidebar; preserva títulos (`#`), código (```), tabelas e Mermaid.
- É resumível (append; pula URLs já em `clean.jsonl`).
- A Fase A só está completa quando todo o `crawl_manifest.json` tem registro correspondente
  em `clean.jsonl` (a Fase C aborta caso contrário).
- Progresso por página: `parseada: <url> | concluidas X/total | faltam Y`.

---

## Fase C — `process.py` (indexação)

> Fase C é segura para rodar em background; salva estado **após cada página** e
> retoma de onde parou. Chunking e embeddings rodam 100% local; o resumo é offload para o hy3.

Uso:
```
python process.py --dir "RAG/<dominio-simplificado>" [--limpar-raw] [--reset]
                  [--chunk-model <modelo>] [--summary-model <modelo>] [--num-ctx N]
```

Modelos configuráveis via CLI (defaults: `qwen2.5-coder:1.5b` chunking, summary offload p/ hy3).
`think: false` é aplicado automaticamente a modelos de raciocínio (`qwen3`, `qwythos`).

Retomada (resume):
- Estado salvo em `process_state.json` (páginas concluídas) após CADA página.
- `documents.jsonl` é aberto em modo APPEND (nunca trunca o já feito).
- Ao reiniciar: pula páginas concluídas, saneia chunks parciais de uma página
  interrompida por crash, e continua de onde parou.
- `--reset` força reprocessar tudo do zero.
- `docs_meta`/contagens são reconstruídos do `documents.jsonl` completo no fim
  (funciona mesmo após várias retomadas).

Fluxo:
```
para cada TEXTO LIMPO em clean.jsonl (SAÍDA da Fase B; SERIAL, uma página por vez; pula se já concluída):
    1. chunking SEMÂNTICO via qwen2.5-coder:1.5b sobre o texto já limpo:
        - pré-divide páginas grandes por títulos (teto ~6000 tokens por chamada)
        - cada seção vira JSON {chunks:[...]} validado
        - fallback determinístico (corte por título + tamanho) se a saída for malformada
   2. overlap (~50 tokens) entre chunks
   3. embedding de cada chunk via nomic-embed-text (serial)
   4. flush + marca página como concluída no process_state.json
monta (reconstruído do documents.jsonl completo):
   5. documents.jsonl + index.json
    6. summary.md (esqueleto estrutural + prosa redigida pelo hy3 — offload)
   7. cria/atualiza RAG/index.md (catálogo-mestre)
```

Detalhes de implementação:
- **Extrator de JSON robusto** — pega o primeiro objeto JSON balanceado (tolera texto/JSON extra).
- **`--limpar-raw`** — apaga `raw/` ao final **apenas se** o processamento foi bem-sucedido (0 erros e ≥1 chunk). Caso contrário, mantém `raw/` para reprocessar.
- Saída sem buffer (`flush=True`) + progresso por página: `processado: <url> -> N chunks | concluidas X/total | faltam Y`.
- **Contador de tempo total** exibido nas estatísticas finais.

Estatísticas finais impressas: pasta, documentos, chunks, erros, raw removido, tempo total.

---

## Uso / Consumo

> **Offload para o hy3:** a forma recomendada de consumir a base é perguntar ao assistente
> remoto (hy3), que recupera os chunks de `documents.jsonl` e responde/gera código. Os scripts
> abaixo (`query.py`/`programador.py`) permanecem para **uso 100% offline** com `qwythos9b` local.

### `query.py` (consulta em linguagem natural) [fora das fases]

Uso:
```
python query.py "sua pergunta" [--dominio <slug>] [--topk N]
```

Fluxo:
```
1. lista domínios em RAG/ (pastas com documents.jsonl)
2. escolhe a pasta: --dominio explícito, ou heurística por palavras do summary.md
3. embedding da pergunta (nomic-embed-text)
4. busca por cosseno no documents.jsonl (força bruta + numpy) → top-k chunks
5. monta prompt com os chunks → qwythos9b responde (em português, com fontes)
```

### `programador.py` (geração de código fundamentada) [fora das fases]

Objetivo: gerar código **fundamentado na documentação** indexada. Modelo alvo:
**o melhor que couber na GPU** para uso offline (atualmente `qwythos9b` — Q4_K_M, ~6.3GB, 100% na GPU); em uso online, o hy3 assume a geração.

Método principal (recomendado): script direto
```
python programador.py "tarefa" --dominio <slug> --out arquivo.ext
                      [--model M] [--topk N] [--idioma pt|en] [--reescrever] [--fontes]
```
- Rápido, confiável, saída limpa (remove cercas markdown ao gravar com `--out`).
- `--reescrever` (opcional): reescreve a tarefa em termos de busca (+1 chamada, ~3x mais lento).
- `--fontes` (opcional): imprime no stderr os trechos da doc recuperados (URL + score + snippet),
  provando que o RAG foi usado. Não polui o código gerado (que sai no stdout).

Orquestração agêntica (`@programador`) — **funciona** com `qwythos9b`:
- faz **tool-calling corretamente** (chama `code_generator`, grava o arquivo).
- **cabe 100% na GPU**; fluxo completo em ~34s; código Godot 4 idiomático.
- Histórico: `qwen2.5-coder:7b` não faz tool-calling; `qwen3.6` roda 74% na CPU (~90s+);
  `qwythos9b` resolveu (tool-calling correto **e** cabe na GPU).
- O **script direto** (`programador.py`) continua disponível como caminho rápido e sem orquestração.

---

## Etapa D — Avaliação (isolada em `stage_d/`, **genérica / não-Godot**)

Não faz parte do core (A/B/C). Mede o ganho do RAG comparando o `programador`
(com recuperação) contra o modelo de síntese **puro** (sem RAG) e valida a saída
com o **compilador/checador que o usuário informar** (Godot, `py_compile`, `tsc`,
JSON, etc.). Não assume nenhuma linguagem.

- Agente: `.opencode/agents/qa.md` (pergunta linguagem/validador/tarefas e sempre
  compara RAG x PURO, obtendo métricas de conhecimento + validade).
- Script: `stage_d/benchmark.py` (genérico, incremental/resumível; roda
  `python stage_d/benchmark.py --domain <dom> --lang <L> --ext <ext> --validator "<cmd {file}>" --tasks <tarefas.json>`).
- Exemplo (Godot): RAG compila **40%** vs PURO **0%**; acerto de conhecimento 50% vs 30%.
  Sem nenhum modelo "qwen" (síntese = `qwythos9b`). Troque `--tasks`/`--validator`
  para avaliar qualquer domínio/indexação.

## Agente maestro (`espiao`)

Definido em `.opencode/agents/espiao.md` (temperature 0.1, bash+question allow, edit+webfetch deny).

Interativo, árvore binária:
```
INVOCADO
  recebeu parâmetros inline? → SIM → RECUSA ("me invoque sem parâmetros")
  NÃO → pergunta URL (valida http/https)
         ↓ (deriva domínio → RAG/<dominio>/)
       pergunta escopo (1/2/3)
         ↓
       pergunta delay (ms; recomenda 2000)
         ↓
       (opcional) pergunta limite de páginas
         ↓
        (opcional) modelos: padrão chunking=qwen2.5-coder:1.5b, summary offload hy3 (ou troca com --chunk-model/--summary-model; mostra `ollama list`)
         ↓
       confirma → dispara crawl.py → dispara process.py [--chunk-model/--summary-model]
         ↓
       reporta: pasta, nº páginas, nº chunks, erros
```

Papel do agente: **só orquestrar** — perguntar, validar, disparar scripts, reportar. Nunca processa HTML/chunks/vetores.

---

## Stack / dependências

- Python 3.12
- `playwright>=1.40` (+ `python -m playwright install chromium`), `beautifulsoup4>=4.12`, `numpy>=1.26`, `requests>=2.31`
- Ollama API (`localhost:11434`)
- Vector store: `.jsonl` + `numpy` (cosseno, força bruta — suficiente pra docs)

---

## Correções aplicadas durante a implementação

1. **Sitemap removido** — conflitava com o escopo (pegava versão errada, ignorava a URL de partida).
2. **Encoding UTF-8** garantido em todos os arquivos gerados.
3. **`think: false`** em modelos de raciocínio — ~9x mais rápido; resolveu travamento do `summary.md`.
4. **Parsing JSON robusto** — extrai só o primeiro objeto balanceado.
5. **Pré-divisão de páginas grandes** por títulos antes do chunking semântico (teto ~6000 tokens/chamada).
6. **Saída sem buffer** (`flush`) + progresso serial `[n/total]` visível por página.
7. **`--limpar-raw`** — remoção opcional e segura do `raw/`.
8. **Contador de tempo total** no `process.py`.
9. **`small_model`** — o agente oculto `title` usava o modelo pesado e travava a GPU antes do
   trabalho; corrigido com `"small_model": "ollama/qwythos9b"` na config global.
10. **Chunking robusto** — sanitização de control chars + retry (2×) antes do fallback
    determinístico; `json.loads(..., strict=False)`.
11. **Chunker trocado para `qwen2.5-coder:1.5b`** — benchmark vs `gemma4`: 0% vs 10% de
    fallback e ~4× mais rápido (gemma4 nem cabe na VRAM de 8GB); mantém texto integral.
12. **Offload de síntese para hy3** — `summary_model=None` por padrão; resumo e Uso feitos
    pelo assistente remoto, tirando `qwythos9b` do pipeline local.

---

## Como usar (resumo)

1. **Tudo num comando** (orquestrador): `python run.py all --url "<URL>" --escopo 2 --delay 2000`
   (Fase C roda em background; use `--foreground` para acompanhar no terminal).
2. Captura + processamento via agente: invoque `@espiao` (ele pergunta URL/escopo/delay).
3. Ou manualmente:
   ```
   python crawl.py --url "<URL>" --escopo 2 --delay 2000
   python parse.py --dir "RAG/<dominio>"
   python process.py --dir "RAG/<dominio>"
   ```
4. Consulta / código:
   ```
   python query.py "sua pergunta"
   python programador.py "crie uma função que faz Y" --out solucao.gd --fontes
   ```

---

## Orquestrador (`run.py`)

Encapsula A→B→C num único comando. **O entendimento da ordem/retomada mora no
script**, não no modelo — assim um modelo pequeno (ou você) só precisa chamar um
comando simples para iniciar a pipeline.

Subcomandos:
```
python run.py all     --url "<URL>" [--escopo 1|2|3] [--delay ms] [--limite N]
                      [--limpar-raw] [--chunk-model M] [--summary-model M]
                      [--reset] [--foreground]
python run.py crawl   --url "<URL>" [--escopo 1|2|3] [--delay ms] [--limite N]
python run.py parse   --dir "RAG/<dominio>" [--reset]
python run.py process --dir "RAG/<dominio>" [--limpar-raw] [--chunk-model M]
                      [--summary-model M] [--reset] [--foreground]
```

Comportamento:
- `all`: roda Fase A (crawl) → Fase B (parse) → Fase C (process). Se A ou B falham, aborta.
- A **Fase C roda em background por padrão** (jobs longos como o crawl do Godot, 1592
  páginas) e salva o log em `process_<dominio>.log`. Use `--foreground` para rodar no
  terminal e esperar o fim.
- `process` é retomável sozinho (via `process_state.json` do `process.py`): se a Fase C
  cair, basta `python run.py process --dir RAG/<dominio>` para continuar de onde parou.
- Defaults de modelo vêm do `config_espiao.json`; os flags `--chunk-model`/`--summary-model`
  sobrescrevem.

Exemplo (Godot docs, retomável):
```
python run.py all --url "https://docs.godotengine.org/en/stable/" --escopo 2 --delay 2000
```

---

## Instalação

```bash
pip install -r requirements.txt
python -m playwright install chromium

ollama pull nomic-embed-text
ollama pull qwen2.5-coder:1.5b   # chunker (padrao)
# opcionais (fora do padrao):
ollama pull gemma4              # chunker alternativo (nao cabe na VRAM de 8GB)
ollama pull qwythos9b           # uso 100% offline (query.py/programador.py)
```

---

## Teste ponta a ponta (validado)

- Alvo: `docs.godotengine.org` (escopo 2, delay 1500ms, limite 4)
- Fase A: 4 páginas capturadas (crawl), 0 erros
- Fase B: parse → `clean.jsonl` (4 registros)
- Fase C: 39 chunks, 0 erros, `summary.md` + `index.md` gerados, tempo ~6m38s
- Query "recursos de física" → resposta correta em português com fontes citadas
- Sistema é **genérico**: funciona com qualquer site

---

## Requisitos

- Python 3.12+
- Ollama rodando localmente (`localhost:11434`)
- GPU recomendada (testado em RTX 3060 Ti, 8GB)

---

## Notas de projeto

- O crawling é **sequencial** e com delay, priorizando **não ser bloqueado**.
- A base RAG (`RAG/`) **não é versionada** — é regenerável a partir dos scripts.
- Modelos locais fazem o trabalho estreito das fases (chunk/embed); a **síntese**
  (resumo e uso) foi offload para o assistente remoto (hy3), e a orquestração/
  entendimento do projeto também fica com o hy3 ou com você.

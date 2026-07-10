# Sistema RAG de Documentação — Implementado

> Status: **implementado e validado ponta a ponta** (Godot docs, escopo 2, 4 páginas, 39 chunks, 0 erros).

## Objetivo
Construir uma base RAG de documentação. O `qwen3.6` (forte) constrói a base **offline**; o `qwen2.5-coder` **consome** em runtime, rápido, compensando sua falta de conhecimento via recuperação semântica.

## Modelos

| Papel | Modelo | Status |
|-------|--------|--------|
| Chunking semântico (por página) | `gemma4` (9.6GB, ~5x mais rápido que qwen3.6) | instalado |
| `summary.md` (1x por site) | `qwythos9b` (cabe na GPU, sem crash) | instalado |
| Embeddings (768 dims) | `nomic-embed-text` | instalado |
| Consumo (runtime) | `qwen2.5-coder:1.5b` | instalado |

## Estrutura de arquivos do projeto

```
<raiz-do-projeto>/
├── crawl.py                      ← Fase A (captura)
├── process.py                    ← Fase B (processamento)
├── query.py                      ← consumo/runtime (busca + resposta)
├── requirements.txt              ← dependências Python
├── requisito.md                  ← este documento
├── .opencode/agents/espiao.md    ← o agente maestro
└── RAG/
    ├── index.md                  ← catálogo-mestre de todos os scraps
    └── <dominio-simplificado>/
        ├── raw/                  ← HTML renderizado (opcional após processar)
        ├── crawl_manifest.json   ← manifesto da captura (consumido pela Fase B)
        ├── documents.jsonl       ← {texto, vetor, metadados} por chunk
        ├── index.json            ← índice de docs da pasta
        ├── summary.md            ← resumo (qwythos9b, adaptativo)
        └── process_state.json    ← progresso da Fase B (retomada)
```

## Arquivos de configuração (defaults)

Dois arquivos JSON na raiz definem os defaults dos agentes. Precedência:
**CLI > arquivo de config > default interno**.

`config_espiao.json` (captura + processamento):
```json
{
  "crawl":   { "escopo": 2, "delay_ms": 2000, "limite": 0 },
  "process": { "chunk_model": "gemma4", "summary_model": "qwythos9b", "num_ctx": 16384 }
}
```
- `num_ctx` limita o KV cache do modelo (evita o crash do qwen3.6 na VRAM de 8GB).

`config_programador.json` (geração de código):
```json
{ "model": "qwythos9b", "topk": 5, "idioma": "pt", "dominio": null, "reescrever": false }
```
- `model` = modelo usado pelo `code_generator`/`programador.py` (arg `--model` sobrescreve).
- O modelo do **orquestrador** (agente `@programador`) fica no próprio `.opencode/agents/programador.md`
  (trocável ali ou via Tab no TUI). São ajustes independentes; o alvo é usar **o melhor modelo
  que couber na GPU** nos dois papéis (atualmente `qwythos9b`, unificado e sem troca de modelo).

Loader: `config_util.py` (lê o JSON; se ausente/inválido, cai nos defaults internos).

## Normalização de domínio
- subdomínios **separados** (`docs.` ≠ `api.`)
- remover `www`
- ignorar protocolo e porta
- remover pontos/aspas/caracteres inválidos
- ex: `https://docs.godotengine.org/...` → `RAG/docsgodotengineorg/`

## Fase A — `crawl.py` (captura)

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

## Fase B — `process.py` (offline, exceto Ollama local)

Uso:
```
python process.py --dir "RAG/<dominio-simplificado>" [--limpar-raw] [--reset]
                  [--chunk-model <modelo>] [--summary-model <modelo>] [--num-ctx N]
```

Modelos configuráveis (defaults: `gemma4` chunking, `qwythos9b` summary):
- `--chunk-model` — troca o modelo do chunking por qualquer outro instalado no Ollama.
- `--summary-model` — troca o modelo do summary.
- `think: false` é aplicado automaticamente a modelos de raciocínio (`qwen3`, `qwythos`).

Retomada (resume) — seguro para jobs longos:
- Estado salvo em `process_state.json` (páginas concluídas) após CADA página.
- `documents.jsonl` é aberto em modo APPEND (nunca trunca o já feito).
- Ao reiniciar: pula páginas concluídas, saneia chunks parciais de uma página
  interrompida por crash, e continua de onde parou.
- `--reset` força reprocessar tudo do zero.
- `docs_meta`/contagens são reconstruídos do `documents.jsonl` completo no fim
  (funciona mesmo após várias retomadas).

Fluxo:
```
para cada HTML em raw/ (SERIAL, uma página por vez; pula se já concluída):
   1. limpa (remove nav/menu/footer/sidebar/scripts via seletores)
   2. acha container principal (main/article/.rst-content/etc.)
   3. extrai texto preservando: títulos (#), blocos de código (```), tabelas (markdown), Mermaid
   4. chunking SEMÂNTICO via gemma4:
        - pré-divide páginas grandes por títulos (teto ~6000 tokens por chamada)
        - cada seção vira JSON {chunks:[...]} validado
        - fallback determinístico (corte por título + tamanho) se a saída for malformada
   5. overlap (~50 tokens) entre chunks
   6. embedding de cada chunk via nomic-embed-text (serial)
   7. flush + marca página como concluída no process_state.json
monta (reconstruído do documents.jsonl completo):
   8. documents.jsonl + index.json
   9. summary.md (qwythos9b, adaptativo: por seção ou amostra distribuída)
   9. cria/atualiza RAG/index.md (catálogo-mestre)
```

Detalhes de implementação:
- **`think: false`** nas chamadas ao `qwen3.6` — desliga a cadeia de raciocínio (~9x mais rápido; resolveu travamento na geração do resumo).
- **Extrator de JSON robusto** — pega o primeiro objeto JSON balanceado (tolera texto/JSON extra).
- **`--limpar-raw`** — apaga `raw/` ao final **apenas se** o processamento foi bem-sucedido (0 erros e ≥1 chunk). Caso contrário, mantém `raw/` para reprocessar.
- Saída sem buffer (`flush=True`) + progresso `[n/total]` por página.
- **Contador de tempo total** exibido nas estatísticas finais.

Estatísticas finais impressas: pasta, documentos, chunks, erros, raw removido, tempo total.

## Consumo — `query.py` (runtime)

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
5. monta prompt com os chunks → qwen2.5-coder responde (em português, com fontes)
```

## O agente maestro (`espiao`)

Definido em `.opencode/agents/espiao.md` (primary, temperature 0.1, bash+question allow, edit+webfetch deny).

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
        (opcional) modelos: padrão (gemma4/qwen3.6) ou troca (mostra `ollama list`)
           ↓
        confirma → dispara crawl.py → dispara process.py [--chunk-model/--summary-model]
           ↓
        reporta: pasta, nº páginas, nº chunks, erros
```

Papel do agente: **só orquestrar** — perguntar, validar, disparar scripts, reportar. Nunca processa HTML/chunks/vetores.

## Planilha de delegação

| Delegado a | O que realiza |
|------------|---------------|
| **Agente** | Perguntar URL, escopo, delay, limite (um por vez) |
| **Agente** | Recusar invocação inline |
| **Agente** | Derivar `RAG/<dominio>/` da URL |
| **Agente** | Validar entrada; disparar scripts na ordem; reportar |
| **`crawl.py`** | Crawl a partir da URL (delay+escopo); render completo; salvar `raw/`; manifesto; árvore dedup |
| **`process.py`** | Limpar HTML; preservar código/tabelas/títulos/Mermaid; chunking via `gemma4` (+pré-divisão+fallback); embeddings; `documents.jsonl`/`index.json`/`summary.md`; retomada (`process_state.json`); atualizar `RAG/index.md`; `--limpar-raw`; tempo total |
| **`gemma4` / `qwythos9b`** | Chunking semântico (gemma4) + `summary.md` (qwythos9b) |
| **`query.py`** | Runtime: escolhe domínio → busca cosseno → prompt |
| **`qwen2.5-coder`** | Responder usando os chunks recuperados |

## Stack / dependências
- Python 3.12
- `playwright>=1.40` (+ `python -m playwright install chromium`), `beautifulsoup4>=4.12`, `numpy>=1.26`, `requests>=2.31`
- Ollama API (`localhost:11434`)
- Vector store: `.jsonl` + `numpy` (cosseno, força bruta — suficiente pra docs)

## Correções aplicadas durante a implementação
1. **Sitemap removido** — conflitava com o escopo (pegava versão errada, ignorava a URL de partida).
2. **Encoding UTF-8** garantido em todos os arquivos gerados.
3. **`think: false`** no `qwen3.6` — ~9x mais rápido; resolveu travamento do `summary.md`.
4. **Parsing JSON robusto** — extrai só o primeiro objeto balanceado.
5. **Pré-divisão de páginas grandes** por títulos antes do chunking semântico (teto ~6000 tokens/chamada).
6. **Saída sem buffer** (`flush`) + progresso serial `[n/total]` visível.
7. **`--limpar-raw`** — remoção opcional e segura do `raw/`.
8. **Contador de tempo total** no `process.py`.

## Como usar (resumo)
1. Captura + processamento via agente: invoque `@espiao` (ele pergunta URL/escopo/delay).
2. Ou manualmente:
   ```
   python crawl.py --url "<URL>" --escopo 2 --delay 2000
   python process.py --dir "RAG/<dominio>"
   ```
3. Consulta:
   ```
   python query.py "sua pergunta"
   ```

## Camada de programação (consumo do RAG para gerar código)

Objetivo: gerar código **fundamentado na documentação** indexada. Modelo alvo: **o melhor
que couber na GPU** (atualmente `qwythos9b` — Qwythos-9B Q4_K_M, ~6.3GB, 100% na GPU).

### Componentes
```
rag_retrieve.py                   ← retrieval compartilhado (query.py + programador.py)
programador.py                    ← gerador de código fundamentado (Camada 3)
.opencode/tools/code_generator.ts ← custom tool que expõe o gerador (Camada 2)
.opencode/agents/programador.md   ← agente orquestrador (Camada 1)
```

### Método principal (recomendado): script direto
```
python programador.py "tarefa" --dominio <slug> --out arquivo.ext
                      [--model M] [--topk N] [--idioma pt|en] [--reescrever] [--fontes]
```
- Rápido, confiável, saída limpa (remove cercas markdown ao gravar com `--out`)
- Default de geração: `qwythos9b` (cabe na 3060 Ti, roda 100% na GPU)
- `--reescrever` (opcional): reescreve a tarefa em termos de busca (+1 chamada, ~3x mais lento)
- `--fontes` (opcional): imprime no stderr os trechos da doc recuperados (URL + score + snippet),
  provando que o RAG foi usado. Não polui o código gerado (que sai no stdout).

### Modelos
| Papel | Modelo | Override |
|-------|--------|----------|
| Geração de código | `qwythos9b` (Qwythos-9B Q4_K_M) | `--model` / arg da tool |
| Embeddings (retrieval) | `nomic-embed-text` | — |

### Orquestração agêntica (`@programador`) — FUNCIONA com Qwythos-9B
O agente `@programador` orquestra de ponta a ponta usando o **Qwythos-9B** como modelo
(orquestrador **e** gerador — um único modelo, sem troca):
- faz **tool-calling corretamente** (chama `code_generator`, grava o arquivo)
- **cabe 100% na GPU** (Q4_K_M, ~6.3GB nos 8GB da 3060 Ti)
- fluxo completo em ~34s; código Godot 4 idiomático (`velocity` + `move_and_slide`)

Histórico (por que Qwythos resolveu):
- `qwen2.5-coder:7b` como orquestrador: rápido, mas **não faz tool-calling** (emite como texto).
- `qwen3.6` como orquestrador: faz tool-calling, mas roda 74% na CPU (~90s+/tarefa).
- `qwythos9b`: tool-calling correto **e** cabe na GPU → melhor dos dois mundos.

Notas de implementação:
- Modelos de raciocínio (`qwen3`, `qwythos`) rodam com `think: false` na geração — mais
  rápido e evita blocos `<think>` na saída.
- `extrair_codigo` remove `<think>...</think>` e pega o último bloco ``` (código final).

O **script direto** (`programador.py`) continua disponível como caminho rápido e sem orquestração.

### Correção relevante: `small_model`
O agente oculto `title` (gera título de sessão) usava o modelo pesado e travava a GPU antes
do trabalho começar. Corrigido com `"small_model": "ollama/qwen2.5-coder:1.5b"` na config
global — tarefas auxiliares (título/resumo) agora usam um modelo leve.

## Teste ponta a ponta (validado)
- Alvo: `docs.godotengine.org` (escopo 2, delay 1500ms, limite 4)
- Fase A: 4 páginas capturadas, 0 erros
- Fase B: 39 chunks, 0 erros, `summary.md` + `index.md` gerados, tempo ~6m38s
- Query "recursos de física" → resposta correta em português com fontes citadas
- Sistema é **genérico**: funciona com qualquer site.

# save.md — Estado da sessão (handoff para continuar depois)

Documento de continuidade do projeto **ragdoll**. Leia isto para retomar de onde paramos.

---

## O que é o ragdoll
Assistente local de documentação: captura docs de um site → transforma em base RAG
pesquisável por significado → usa para responder perguntas e **gerar código fundamentado**
na doc. Tudo local via Ollama. Repo: https://github.com/LesterKnight/ragdoll-ia-assistant

---

## Arquitetura (3 fases)
```
FASE A   crawl.py    -> baixa HTML (Playwright, headed, sequencial) -> RAG/<slug>/raw/ + crawl_manifest.json
FASE A.5 parse.py    -> HTML -> texto limpo compacto -> clean.jsonl   (NOVO, ~99% menor)
FASE B   process.py  -> limpa/chunk/embeddings -> documents.jsonl + index.json + summary.md
CONSUMO  query.py       -> pergunta -> busca cosseno -> resposta
         programador.py -> tarefa -> busca -> gera código (qwythos9b)
```

## Modelos (Ollama)
| Papel | Modelo |
|-------|--------|
| Chunking (por página) | `gemma4` |
| Summary (1x/site) | `qwythos9b` |
| Embeddings (768d) | `nomic-embed-text` |
| Geração de código | `qwythos9b` (Q4_K_M, cabe 100% na GPU 3060 Ti 8GB) |
| Consulta rápida | `qwen2.5-coder:1.5b` |
| small_model (OpenCode, títulos) | `qwen2.5-coder:1.5b` |

Qwythos foi baixado via: `ollama pull hf.co/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF:Q4_K_M`
e copiado para o nome curto `qwythos9b` (`ollama cp`).

---

## ESTADO ATUAL (onde paramos)

### Concluído
- **Crawl completo**: `RAG/docsgodotengineorg/` com **1592 páginas** válidas em `raw/` + `crawl_manifest.json`.
  (site: `https://docs.godotengine.org/en/stable/`, escopo 3. Já limpo: removidas 67 páginas 404, 9 `_downloads`, 4 `_images`.)
- Base cobre: classes (1079), tutorials (393), engine_details (66), getting_started (33), community (12), about (7).
- **Backup**: usuário salvou um `RAG.zip` (167MB) FORA do projeto, com o conteúdo de `RAG/` (raw + manifesto).
  Com ele + código (git) + modelos (ollama), dá para regenerar tudo sem re-crawlear.

### Pendente / próximo passo IMEDIATO
1. **Testar o `parse.py`** — foi interrompido no meio (usuário reiniciou a máquina).
   Rodar: `python -u parse.py --dir "RAG/docsgodotengineorg"` → gera `clean.jsonl` (~20MB, redução ~99%).
   É resumível (append; pula URLs já em clean.jsonl).
2. **Adaptar o `process.py`** para LER o `clean.jsonl` (em vez de reparsear 2.3GB de HTML).
   AINDA NÃO FEITO. Ideia: se `clean.jsonl` existe, iterar sobre ele (url/title/text) e pular
   `clean_html`/`block_text`; senão, fallback para ler raw. Manter a lógica de resume (done set por url).
3. **Rodar a Fase B** (`process.py --dir RAG/docsgodotengineorg`) — leva horas; roda em background com log.
4. Depois: benchmark (comparar Qwythos com/sem RAG — ver `gaps_qwythos_gdscript.md`).

---

## Arquivos do projeto
| Arquivo | Papel | Estado |
|---------|-------|--------|
| `crawl.py` | Fase A (captura) | pronto; filtro de prefixo + timeouts + page.url p/ links relativos |
| `parse.py` | Fase A.5 (HTML->clean.jsonl) | **criado, NÃO testado por completo, NÃO commitado** |
| `process.py` | Fase B | pronto e RESUMÍVEL (process_state.json); **falta adaptar p/ clean.jsonl** |
| `query.py` | consulta | pronto |
| `programador.py` | geração de código | pronto (default qwythos9b, --fontes, extração robusta a <think>) |
| `rag_retrieve.py` | retrieval compartilhado | pronto |
| `config_util.py` | loader de config | pronto |
| `config_espiao.json` | defaults crawl+process | escopo2, delay2000, nav30000, idle15000; chunk=gemma4, summary=qwythos9b, num_ctx=16384 |
| `config_programador.json` | defaults geração | model=qwythos9b, topk5, idioma pt |
| `.opencode/agents/espiao.md` | agente captura | timeouts+delay OBRIGATÓRIOS a cada interação |
| `.opencode/agents/programador.md` | agente programador | model qwythos9b |
| `.opencode/tools/code_generator.ts` | tool custom | pronto |
| `requisito.md` | especificação viva | atualizado |
| `NEXT_STEPS.md` | melhorias pendentes | item 1a (resume Fase B) FEITO; 1b (resume crawl) pendente |
| `gaps_qwythos_gdscript.md` | baseline p/ benchmark | pronto |
| `setup_ssh_servidor.ps1` | habilita SSH (rodar como admin) | pronto |
| `README.md` | apresentação | pronto |

---

## Git
- Remoto: `origin` = https://github.com/LesterKnight/ragdoll-ia-assistant (branch `main`)
- Último commit local: `39f45bf` "Retomada da Fase B..."
- **Commits locais NÃO enviados (push pendente)** — havia vários à frente do remoto.
- **NÃO commitado ainda**: `parse.py` e este `save.md`.
- `.gitignore` ignora: `RAG/`, `RAG.zip`, `*.zip`, `__pycache__/`, `*.log`, `*.gd` de teste.

---

## Comandos úteis
```bash
# Fase A.5 (parser intermediário)
python -u parse.py --dir "RAG/docsgodotengineorg"

# Fase B (processamento) - background com log
nohup python -u process.py --dir "RAG/docsgodotengineorg" > process_full.log 2>&1 &
grep -c '"url"' RAG/docsgodotengineorg/documents.jsonl   # progresso (chunks)

# Consulta / geração
python query.py "pergunta"
python programador.py "tarefa" --dominio docsgodotengineorg --out arq.gd --fontes

# Ollama (caminho no Windows)
"/c/Users/kiko2/AppData/Local/Programs/Ollama/ollama.exe" list
# OpenCode CLI
"/c/Users/kiko2/AppData/Roaming/npm/opencode.cmd" agent list
```

---

## Acesso remoto (em andamento)
Objetivo: usar este PC (GPU) como backend e operar de outro computador (a GPU faz o trabalho).
- Plano: **Tailscale** (VPN sem abrir portas, funciona com CGNAT) + **SSH**.
- `setup_ssh_servidor.ps1` instala o OpenSSH Server (rodar como ADMIN). Usuário SSH: `kiko2`.
- Falta: usuário instalar Tailscale nas duas máquinas; depois `ssh kiko2@<ip-100.x.x.x>`.

---

## Ambiente
- Windows, shell bash (git bash). GPU: RTX 3060 Ti 8GB. RAM 64GB.
- Python 3.12. Playwright chromium instalado. Ollama em localhost:11434.
- PowerShell tem ExecutionPolicy que já foi ajustada (RemoteSigned/CurrentUser).

---

## Regras de trabalho definidas pelo usuário
- **NÃO fazer nada por conta própria — SEMPRE perguntar antes** de criar/editar/rodar/commitar.
- Crawl/processamento longos: rodar em background com log; monitorar por URL/progresso.
- Alvo de modelo = "o melhor que couber na GPU" (hoje qwythos9b).

## Decisão pendente de discussão
- Adaptar `process.py` para consumir `clean.jsonl` (parser intermediário) — validar abordagem antes.

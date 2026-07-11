# save.md — Estado ragdoll (handoff enxuto)

Assistente RAG local de documentação: captura → base pesquisável → resposta/código
fundamentado na doc. Tudo local via Ollama. Repo: https://github.com/LesterKnight/ragdoll-ia-assistant

## Fases
- **A** `crawl.py` (captura) → `raw/` + `crawl_manifest.json`
- **B** `parse.py` (limpeza) → `clean.jsonl`
- **C** `process.py` (indexação) → `documents.jsonl` + `index.json` + `summary.md`
- **Uso** `query.py` / `programador.py` (fora das fases)

## Modelos (Ollama)
chunk=gemma4 · summary=qwythos9b · embed=nomic-embed-text · geração/uso=qwythos9b · small_model=ollama/qwythos9b

## Como executar (raiz do projeto; pasta alvo: `RAG/docsgodotengineorg`)

**Fase A — captura**
```bash
python crawl.py --url "https://docs.godotengine.org/en/stable/" --escopo 3 --delay 2000
```
Shell: imprime `[URL]` + `[STATUS]: sucesso|falha` por página; total no `[RESULTADO]` ao fim.

**Fase B — limpeza**
```bash
python parse.py --dir "RAG/docsgodotengineorg"
```
Shell (por página): `parseada: <url> | concluidas X/total | faltam Y`.

**Fase C — indexação** (longa: ~13h p/ 1592 páginas → background + log)
```bash
nohup python -u process.py --dir "RAG/docsgodotengineorg" > process_full.log 2>&1 &
tail -f process_full.log                                   # acompanhar ao vivo
grep -c '.' RAG/docsgodotengineorg/documents.jsonl          # nº de chunks prontos
```
Shell (por página): `processado: <url> -> N chunks | concluidas X/total | faltam Y`.
Ao fim: `[RESULTADO]` com documentos/chunks/erros/tempo.

## Monitoramento do shell
- Fase C em background: `tail -f process_full.log` mostra o progresso ao vivo.
- **Cada página concluída solta uma mensagem com a conclusão (url + chunks) e quantas ainda estão pendentes (`faltam Y`).**
- Retomada automática: ao reiniciar `process.py`, ele pula as páginas já em `process_state.json`.

## Estado atual
- Fase A e B: **concluídas** (`clean.jsonl` = 1592/1592 registros, ~13 MB).
- Fase C: **SEGURA / PARADA** em **17/1592** páginas (última: `.../getting_started/step_by_step/nodes_and_scenes.html`). Não está rodando.
  Retomar: `python -u process.py --dir "RAG/docsgodotengineorg"` continua da página 18.

## Git (alterações não commitadas)
`process.py`, `query.py`, `requisito.md`, `save.md`, `README.md`, `NEXT_STEPS.md`, `.opencode/agents/espiao.md`.
Remoto: origin/main · HEAD = b725675 · 4 commits à frente.

## Regras (usuário)
- **NUNCA disparar execuções por conta própria**: só iniciar com pedido explícito ou autorização prévia
  (válido p/ crawls, Fase C, background jobs, etc.). Autorização vem ANTES do disparo.
- Crawl/processamento longos: rodar em background com log e monitorar por progresso.

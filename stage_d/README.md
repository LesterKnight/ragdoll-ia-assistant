# Etapa D — Avaliação do RAG

Esta pasta é a **Etapa D** do ragdoll e fica **isolada do core (A/B/C)** de
propósito: ela não faz parte do pipeline de construção da base, apenas a mede.

## O que ela faz
- Gera código GDScript para N tarefas que exigem APIs **novas** do Godot
  (desconhecidas do treino do modelo de síntese).
- Para cada tarefa, gera **duas** versões:
  1. **RAG** — via `programador.py` (recupera trechos da doc + modelo de síntese)
  2. **PURO** — só o modelo de síntese, sem RAG
- Valida os dois GDScript no **Godot real** (método do agente `gdtester`):
  `godot --headless --check-only --script <arquivo>` → compila ou não.
- Reporta: acerto de conhecimento (símbolo da API na saída) e validade real
  (compila no Godot).

## Modelo
Nenhum "qwen" é usado. A síntese roda com **qwythos9b** (offload local). O
`qwen2.5-coder:1.5b` é usado apenas na Fase C (chunking), nunca aqui.

## Arquivos
- `benchmark.py` — roda a avaliação. É **incremental/resumível** (grava
  `manifest.json` após cada tarefa; re-rodar retoma onde parou).

## Uso (a partir da raiz do repo)
```
python stage_d/benchmark.py
```
Saída: `<temp>/opencode/bench/` com 20 `.gd` (rag_XX.gd / norag_XX.gd) +
`manifest.json` + tabela resumida no stdout.

## Validação (gdtester)
A checagem de sintaxe é idêntica à do agente `.opencode/agents/gdtester.md`,
que pode ser invocado diretamente no chat (`@gdtester`) para validar qualquer
script à parte do benchmark.

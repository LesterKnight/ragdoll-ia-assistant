# Etapa D — Avaliação do RAG (genérica, não-Godot)

Esta pasta é a **Etapa D** do RagThulhu e fica **isolada do core (A/B/C)** de
propósito: ela não faz parte do pipeline de construção da base, apenas a mede.
**Não é específica para Godot** — valida qualquer linguagem cujo compilador/
checador você informar.

## O que ela faz
- Gera código para N tarefas (definidas em `--tasks`, um JSON).
- Para cada tarefa, gera **duas** versões com o mesmo modelo de síntese:
  1. **COM RAG** — via `programador.py` (recupera trechos da doc + gera).
  2. **SEM RAG** — só o modelo, sem recuperação.
- Valida as duas saídas com o **validador que você passar** (ex.: compilador,
  `tsc`, `py_compile`, checador JSON, ou o Godot para GDScript).
- Reporta métricas: acerto de conhecimento (símbolo esperado na saída) e
  validade real (passou no validador).

## Modelo
Nenhum "qwen" é usado. A síntese roda com **qwythos9b** (offload local).

## Arquivos
- `../stage_d/benchmark.py` — engine genérico da Etapa D (incremental/resumível).
- `../stage_d/tasks_godot.json` — **exemplo** de tarefas (APIs novas do Godot 4.3+); troque
  por qualquer domínio/indexação que você tiver em `RAG/`.
- `stage_d.md` — este arquivo.

## Uso (a partir da raiz do repo)

Exemplo GDScript (validador = Godot):
```
python stage_d/benchmark.py --domain docsgodotengineorg --lang GDScript --ext gd \
  --validator "\"C:/.../Godot.exe\" --headless --check-only --script {file}" \
  --tasks stage_d/tasks_godot.json
```

Exemplo Python (validador = py_compile):
```
python stage_d/benchmark.py --domain <pasta> --lang Python --ext py \
  --validator "python -c \"import py_compile; py_compile.compile(r'{file}', doraise=True)\"" \
  --tasks stage_d/tasks.json
```

Sem `--validator`, só a métrica de conhecimento é calculada.

## Agente de QA
O `../.opencode/agents/qa.md` é o agente que **orquestra** essa avaliação de forma
genérica: ele pergunta linguagem/validador/tarefas ao usuário e sempre compara
RAG × SEM-RAG, obtendo as métricas. Pode usar este `benchmark.py` por baixo.

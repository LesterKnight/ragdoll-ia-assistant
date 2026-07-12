# Gaps de conhecimento — Qwythos-9B em GDScript (Godot 4)

Documento base para **benchmark**: mede o que o `qwythos9b` sabe de GDScript **sem RAG**,
para depois comparar com o desempenho **com RAG** (após aumentar a base).

- Modelo testado: `qwythos9b` (Qwythos-9B Claude-Mythos-5-1M, Q4_K_M)
- Condição: geração direta no Ollama, `think: false`, `temperature: 0.2`, **sem RAG**
- Data do baseline: 2026-07-10
- Alvo da doc: Godot Engine 4.7 (`docs.godotengine.org/en/4.7`)

---

## Metodologia

Perguntas de código GDScript enviadas direto ao modelo (sem contexto de documentação).
Cada item classificado como:
- ✅ **correto** — API real e idiomática
- ⚠️ **parcial** — parte certo, parte alucinado
- ❌ **errado** — API inexistente/incorreta
- 🟡 **honesto** — admitiu não saber (melhor que alucinar)

---

## Resultados do baseline (SEM RAG)

| # | Tópico | Resultado | Observação |
|---|--------|-----------|------------|
| Q1 | CharacterBody2D: gravidade + pulo + movimento | ✅ correto | `velocity`, `is_on_floor()`, `move_and_slide()`, `Input.get_axis()` corretos (bug lógico menor no pulo) |
| Q2 | Signals: declarar, emitir, `await` | ✅ correto | `signal`, `emit_signal`, `await`, `Callable` corretos |
| Q3 | Tween: `create_tween().tween_property` | ✅ correto | API 4.x correta |
| Q4 | NavigationAgent2D: mover até alvo | ⚠️ parcial | `set_target_position()` certo; **alucinou** `agent.move_and_slide()` (não existe; correto é `get_next_path_position()`) |
| Q5 | Feature recente (TypedDictionary 4.3/4.4+) | 🟡 honesto | admitiu "não sei" |

---

## Onde o modelo é FORTE (RAG agrega pouco)

- Nós comuns 2D: `CharacterBody2D`, `Node2D`, `Sprite2D`
- Fluxo de física: `_physics_process`, `velocity`, `move_and_slide`, `is_on_floor`
- Signals e `await`
- `Tween` / `create_tween`
- Input: `Input.get_axis`, `is_action_pressed`
- Anotações: `@export`

## Onde o modelo FALHA (RAG deve cobrir)

1. **APIs de classes menos comuns** — métodos específicos que ele confunde ou inventa
   (ex.: `NavigationAgent2D`, provavelmente também `TileMap`, `AnimationTree`,
   `PhysicsServer`, `RenderingServer`, `MultiplayerAPI`).
2. **Recursos de versões recentes** (4.3 / 4.4 / 4.7) — features novas fora do treino.
3. **Assinaturas exatas** — nomes de parâmetros, enums e valores de retorno de métodos
   menos usados.
4. **Nós/áreas especializadas** — navegação, shaders, XR, áudio espacial, rede.

---

## Plano de benchmark (futuro)

Após o scrap total da doc, repetir as MESMAS perguntas em duas condições e comparar:

1. **Baseline (sem RAG):** já registrado acima.
2. **Com RAG:** `python programador.py "<pergunta>" --dominio docsgodotengineorg --fontes`

Métrica sugerida por questão:
- correção da API (✅/⚠️/❌)
- se os `--fontes` recuperados continham a resposta (relevância do retrieval)
- redução de alucinação vs baseline

### Conjunto de teste sugerido (expandir)
- Q1–Q5 acima (já com baseline)
- adicionar: TileMap (colisão/camadas), AnimationPlayer/AnimationTree, Area2D signals,
  Resource customizado (`class_name`/`@export`), Timer, HTTPRequest, save/load com
  `FileAccess`, `ResourceSaver`/`ResourceLoader`.

---

## Notas

- O RAG só melhora o resultado se a base contiver a página certa (referência de API /
  tutorial). A base inicial (4 páginas de introdução) era rasa demais — daí o scrap total.
- Objetivo do benchmark: quantificar **quanto** o RAG reduz alucinação nas áreas fracas,
  justificando o custo de indexar a documentação completa.

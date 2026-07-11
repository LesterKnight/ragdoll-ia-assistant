# Next Steps — ragdoll

Lista de melhorias pendentes e ideias para lembrar depois. Nada aqui está implementado.

---

## 1. Retomada — PARCIALMENTE FEITO

### 1a. Retomada do processamento (Fase C) — FEITO ✅
`process.py` agora retoma: estado em `process_state.json` (por página), `documents.jsonl`
em modo append, saneia chunks parciais de crash, pula páginas já feitas, `--reset` para
recomeçar. Testado com simulação de crash.

### 1b. Retomada do crawl (Fase A) — PENDENTE
O crawl ainda **não retoma**. Se cair energia / for interrompido:
- o conjunto `visited` e a fila vivem só na memória → perdidos;
- não há checagem de arquivo existente → ao reiniciar, **re-baixa tudo do zero**;
- o `crawl_manifest.json` só é gravado **no fim** → interrupção deixa HTMLs sem manifesto.

**Melhorias (ordenadas por custo/benefício):**
1. **Pular páginas já baixadas** — se `raw/<arquivo>.html` já existe, não re-navegar.
2. **Manifesto incremental** — gravar `crawl_manifest.json` a cada N páginas.
3. **Persistir estado** — salvar `visited` + fila em `crawl_state.json` periodicamente.

---

## 2. Cache binário de vetores no retrieval (escala)

**Problema:** `rag_retrieve.py` recarrega e re-parseia o `documents.jsonl` inteiro a cada
consulta. Com base grande (a Class Reference é enorme) isso fica lento por query.

**Melhoria:** salvar os vetores em `.npy` (numpy) no `process.py` e carregar com `np.load`
(mmap) no retrieval. Ganho grande de latência, risco baixo.

---

## 3. Seleção de domínio mais robusta

**Problema:** `query.py`/`rag_retrieve.py` escolhem o domínio por heurística de palavras do
`summary.md`. Com várias docs indexadas, pode rotear errado.

**Melhoria:** rankear por similaridade de embedding contra o summary de cada domínio, ou
permitir `--dominio` obrigatório quando houver ambiguidade.

---

## 4. Benchmark do RAG (Uso — medir o ganho)

Já temos o baseline em `gaps_qwythos_gdscript.md` (conhecimento do Qwythos SEM RAG).

**A fazer depois do scrap total:**
- repetir as perguntas Q1–Q5 (+ expandir) COM RAG (`programador.py ... --fontes`);
- medir: correção da API (✅/⚠️/❌), se os `--fontes` continham a resposta, redução de alucinação;
- foco nas áreas fracas (NavigationAgent2D, APIs de classes menos comuns, features recentes).

---

## 5. Qualidade de geração de código (Uso)

**Observado:** mesmo com RAG, o gerador às vezes alucina API quando a base não tem a página
certa (base rasa). Com a Class Reference completa, reavaliar. Considerar:
- aumentar `topk` para tarefas de API;
- incluir no prompt a instrução de citar o método/classe exatos dos trechos.

---

## 6. Agêntico (@programador) — confiabilidade (Uso)

**Observado:** o orquestrador local (Qwythos-9B) às vezes decide **não** usar o
`code_generator` e não completa a tarefa. Funciona de forma inconsistente.

**Ideias:**
- endurecer o prompt do agente ("SEMPRE use code_generator; SEMPRE grave o arquivo");
- ou aceitar o script direto (`programador.py`) como caminho principal (já é o recomendado).

---

## 7. Orquestrador `run.py` (Fases A→B→C)

Script único que executa a sequência **Fase A → Fase B → Fase C** num só ponto de entrada:
- Ex.: `python run.py --url <URL> --escopo <N> --delay <MS>` faz captura → limpeza → indexação.
- Parâmetros de modelo (`--chunk-model`, `--summary-model`) e de domínio repassados às fases.
- Respeita retomada de cada fase (`process_state.json`; futuro `crawl_state.json` da item 1b).
- Pára em erro de fase anterior (ex.: não indexa se `clean.jsonl` estiver incompleto).
- Não cobre o **Uso** (query/programador) — esse é executado separadamente pelo usuário.
- Reúne os passos hoje espalhados em `requisito.md` / `.opencode/agents/espiao.md` num só comando.

---

## 8. Fine-tuning / QLoRA no corpus limpo (possibilidade futura)

Usar o material do RAG para **treinar** (e não só recuperar) um modelo local:
- Insumo já pronto: `clean.jsonl` (corpus limpo/estruturado) e `documents.jsonl` (chunks) são o dataset de partida.
- Modalidades: continued pre-training (injetar conhecimento do Godot nos pesos); SFT/instruction-tuning (ensinar a responder/gerar no estilo da doc); LoRA/QLoRA (adapters leves, **factível na 3060 Ti 8GB**); híbrido RAG + modelo fine-tunado.
- Pode-se sintetizar um dataset de Q&A com o próprio RAG (ou modelo forte) a partir dos chunks — destilação de conhecimento para um modelo menor.
- Trade-off vs RAG atual: inferência mais rápida e modelo "conhece" o domínio, mas fica estático (re-treino p/ atualizar) e há risco de catastrophic forgetting. Full fine-tune de 9B não cabe em 8GB; QLoRA 4-bit em 7–9B cabe.
- Os gaps medidos em `gaps_qwythos_gdscript.md` são os candidatos a reduzir com treino.
- **Apenas uma possibilidade anotada — não será feito agora.**

---

## Notas
- Base RAG (`RAG/`) não é versionada (`.gitignore`) — é regenerável.
- Scrap atual em andamento: `docs.godotengine.org/en/stable/` escopo 3.

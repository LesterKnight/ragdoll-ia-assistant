# Next Steps — ragdoll

Lista de melhorias pendentes e ideias para lembrar depois. Nada aqui está implementado.

---

## 1. Retomada de crawl (resume) — PRIORIDADE

**Problema:** o crawl atual **não retoma**. Se cair energia / for interrompido:
- o conjunto `visited` e a fila vivem só na memória → perdidos;
- não há checagem de arquivo existente → ao reiniciar, **re-baixa tudo do zero**, sobrescrevendo `raw/`;
- o `crawl_manifest.json` só é gravado **no fim** → uma interrupção deixa os HTMLs em `raw/`
  **sem manifesto**, e o `process.py` depende do manifesto (arquivos "órfãos").

**Melhorias (ordenadas por custo/benefício):**
1. **Pular páginas já baixadas** — se `raw/<arquivo>.html` já existe, não re-navegar.
   (mais barato, resolve ~80% do problema de retomada)
2. **Manifesto incremental** — escrever/atualizar `crawl_manifest.json` a cada N páginas,
   não só no fim. Assim uma interrupção deixa uma base processável.
3. **Persistir estado** — salvar `visited` + fila em `crawl_state.json` periodicamente,
   para retomar exatamente de onde parou (fila pendente inclusa).

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

## 4. Benchmark do RAG (medir o ganho)

Já temos o baseline em `gaps_qwythos_gdscript.md` (conhecimento do Qwythos SEM RAG).

**A fazer depois do scrap total:**
- repetir as perguntas Q1–Q5 (+ expandir) COM RAG (`programador.py ... --fontes`);
- medir: correção da API (✅/⚠️/❌), se os `--fontes` continham a resposta, redução de alucinação;
- foco nas áreas fracas (NavigationAgent2D, APIs de classes menos comuns, features recentes).

---

## 5. Qualidade de geração de código

**Observado:** mesmo com RAG, o gerador às vezes alucina API quando a base não tem a página
certa (base rasa). Com a Class Reference completa, reavaliar. Considerar:
- aumentar `topk` para tarefas de API;
- incluir no prompt a instrução de citar o método/classe exatos dos trechos.

---

## 6. Agêntico (@programador) — confiabilidade

**Observado:** o orquestrador local (Qwythos-9B) às vezes decide **não** usar o
`code_generator` e não completa a tarefa. Funciona de forma inconsistente.

**Ideias:**
- endurecer o prompt do agente ("SEMPRE use code_generator; SEMPRE grave o arquivo");
- ou aceitar o script direto (`programador.py`) como caminho principal (já é o recomendado).

---

## Notas
- Base RAG (`RAG/`) não é versionada (`.gitignore`) — é regenerável.
- Scrap atual em andamento: `docs.godotengine.org/en/stable/` escopo 3.

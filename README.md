# RagThulhu

Servidor de observação e gerência do pipeline RAG (Coleta → Limpeza →
Indexação → Avaliação). Expõe a UI em `http://127.0.0.1:8765` (HTTP) e um
WebSocket em `:8766` que empurra os logs ao vivo.

## Banco de dados (`RAG/log.db`)

O único banco do sistema é um SQLite em `RAG/log.db`, no modo WAL
(`log.db-wal`, `log.db-shm` como sibling files). É o contrato entre o
pipeline (escrita via `loghub.py`) e a UI (leitura via `logdb.py`); nenhum
dos lados conhece o outro.

> **Nunca apague o `log.db` manualmente.** Se o ficheiro sumir, a tabela
> `log` deixa de existir e o servidor passa a responder `no such table: log`
> até ser reiniciado (`logdb.ensure()` recria a tabela no arranque).

### Schema da tabela `log`

Criada por `loghub._connect()`:

```sql
CREATE TABLE IF NOT EXISTS log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    site      TEXT NOT NULL,    -- slug da base (ex: docsgodotengineorg)
    etapa     TEXT NOT NULL,    -- 'A' Coleta | 'B' Limpeza | 'C' Indexação
                                -- | 'D' Avaliação | 'U' Uso (query/programador)
    tipo_log  TEXT NOT NULL,    -- 'sucesso' | 'erro' | 'excecao'
    log       TEXT NOT NULL,    -- mensagem/linha de log
    data_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP  -- UTC
);
```

- `data_hora` é armazenado em **UTC**; `logdb.conv()` o converte para o
  horário de São Paulo (`America/Sao_Paulo`) na leitura.
- `id` é auto-incrementado e usado para paginação ao vivo (`logdb.after`).

### Leitura (UI / `logdb.py`)

| Função | Uso |
|--------|-----|
| `recent(site, n=500)` | últimas `n` linhas do site (mais antigas primeiro) |
| `after(site, last_id)` | linhas novas desde `last_id` (stream ao vivo) |
| `list_bases()` | lista as bases = **pastas** em `RAG/` (não lê o banco) |
| `site_status(site)` | saúde/estágio/contagens por etapa |
| `wipe_all()` | limpa registros e recria bases em falta (ver abaixo) |
| `ensure()` | recria `log.db` + tabela se não existirem (arranque) |

### Escrita (pipeline / `loghub.py`)

`loghub.log(site, etapa, tipo_log, message)` é o **único** ponto de escrita.

## Estrutura de pastas

```
RAG/
  log.db                 <- banco de log (NÃO apagar)
  log.db-wal / log.db-shm <- WAL do SQLite
  <slug>/                <- uma base RAG (ex: docsgodotengineorg/)
stage_d/
  benchmark_results.jsonl <- resultados de avaliação (artefato)
```

`list_bases()` descobre as bases lendo as **pastas** em `RAG/`; por isso
apagar a pasta de uma base a remove da listagem automaticamente.

## Política de bases — NUNCA excluir bases

> **Excluir uma base quebra a aplicação.** Por isso **não existe** botão nem
> endpoint para remover bases. As bases fazem parte da aplicação.

### "Limpar tudo" / Wipe = esquecer o trabalho (apaga bases também)

O botão **"Esquecer todo o trabalho (apagar bases + logs)"** (`POST /api/wipe`)
faz delete físico de **tudo o que é trabalho**, incluindo as próprias pastas
das bases:

| O que é apagado | Onde | Como |
|-----------------|------|------|
| Registros de log | tabela `log` (em `RAG/log.db`) | `DELETE FROM log` (a tabela/banco permanece) |
| Pastas das bases | `RAG/<slug>` (inteiras) | `shutil.rmtree` |
| Ficheiros soltos em `RAG/` (não-banco) | `RAG/*` | `unlink` |
| Resultados de benchmark | `stage_d/benchmark_results.jsonl` | `unlink` |

| O que é **preservado** | Porquê |
|------------------------|--------|
| O próprio `RAG/log.db` (estrutura/tabela) | é a database do sistema; `logdb.ensure()` garante que existe |

Resultado: após o wipe, **nenhuma base aparece** (`list_bases()` lê as pastas
em `RAG/`, e estas foram apagadas) e **nenhum registro retorna** — tudo foi
eliminado da persistência. O app continua funcional (mostra "ainda não há
itens"); as bases voltam a existir quando um novo crawl as recriar.

> `list_bases()` descobre as bases lendo as **pastas** em `RAG/`.

## Como rodar

```bash
python server.py               # site auto-detectado via logdb._autosite()
python server.py --site docsgodotengineorg
```

Porta HTTP `8765`, WebSocket `8766` (HTTP + 1).

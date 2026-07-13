"""
ETAPA D — Avaliacao do RAG (isolada do core A/B/C, GENERICA / nao-Godot).

Compara o modelo de sintese COM RAG (programador.py) contra o MESMO modelo SEM
RAG, e valida a saida com o compilador/checador que o usuario informar.

E generica: nao assume Godot nem nenhuma linguagem. Tudo vem de parametro:
  --domain    pasta em RAG/ (doc indexada)
  --lang      so para rotulo (ex.: GDScript, Python)
  --ext       extensao dos arquivos gerados (ex.: gd, py, ts)
  --validator comando shell com {file} no lugar do caminho (exit 0 = valido)
  --tasks     JSON com a lista de tarefas: [{q, expect[], legacy[]}]

Sintese roda com qwen2.5-coder:7b (sem qwen3/gemma/qwythos).
Se --validator for omitido, so a metrica de CONHECIMENTO e computada.

Uso (a partir da raiz do repo):
  python stage_d/benchmark.py --domain docsgodotengineorg --lang GDScript --ext gd \
      --validator "\"C:/.../Godot.exe\" --headless --check-only --script {file}" \
      --tasks stage_d/tasks_godot.json

E incremental/resumivel (grava manifest.json apos cada tarefa).
"""

import argparse
import json
import os
import subprocess
import sys
import time

# permite importar programador.py que esta na raiz do repo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

import config_util
import rag_retrieve
import programador

CONF = config_util.load_config()
OLLAMA = CONF["ollama"]["url"]
BENCH = CONF.get("benchmark", {})
DEFAULT_MODEL = BENCH.get("model", "qwen2.5-coder:7b")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
TASKS_REL = BENCH.get("tasks") or "stage_d/tasks_godot.json"
DEFAULT_TASKS = TASKS_REL if os.path.isabs(TASKS_REL) else os.path.join(REPO_ROOT, TASKS_REL)
BENCHDIR = r"C:/Users/kiko2/AppData/Local/Temp/opencode/bench"


def bare_gen(prompt: str, model: str, num_predict: int = 600, temperature: float = 0.2) -> str:
    r = requests.post(
        f"{OLLAMA}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False,
              "options": {"temperature": temperature, "num_predict": num_predict}},
        timeout=600,
    )
    r.raise_for_status()
    return r.json().get("response", "")


def validate(path: str, validator: str):
    """Roda o comando do usuario (template {file}) e interpreta exit code."""
    if not validator:
        return None, ""
    cmd = validator.replace("{file}", path)
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        ok = p.returncode == 0
        err = ""
        if not ok:
            for line in (p.stderr + p.stdout).splitlines():
                if "ERROR" in line or "Error" in line or "error" in line:
                    err = line.strip()
                    break
            err = err or (p.stderr or p.stdout).strip().splitlines()[-1] if (p.stderr or p.stdout).strip() else "exit != 0"
        return ok, err
    except Exception as e:
        return False, f"erro ao rodar validador: {e}"


def score(out: str, expect, legacy):
    has = [s for s in expect if s.lower() in out.lower()]
    wrong = [s for s in legacy if s.lower() in out.lower()]
    return (len(has) >= 1, has, wrong)


def _pass(val, kw):
    """pass/fail geral: validade se houver validador, senao acerto de conhecimento."""
    return bool(val) if val is not None else bool(kw)


def append_record(jsonl_f, run_meta, n, q, dt, rag_ok, rag_vd, rag_err,
                  norag_ok, norag_vd, norag_err):
    """Grava UMA linha JSONL por pergunta (append-only, incremental)."""
    rec = dict(run_meta)
    rec.update({
        "n": n, "q": q, "time_s": dt,
        "rag": {"pass": _pass(rag_vd, rag_ok), "kw": rag_ok, "val": rag_vd, "err": rag_err},
        "norag": {"pass": _pass(norag_vd, norag_ok), "kw": norag_ok, "val": norag_vd, "err": norag_err},
    })
    jsonl_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    jsonl_f.flush()


def main():
    ap = argparse.ArgumentParser(description="Etapa D — benchmark RAG x PURO (generico)")
    ap.add_argument("--domain", default="docsgodotengineorg")
    ap.add_argument("--lang", default=BENCH.get("lang", ""))
    ap.add_argument("--ext", default=BENCH.get("ext", "gd"))
    ap.add_argument("--mode", default=BENCH.get("mode", "code"), choices=["code", "facts"],
                    help="code=gera codigo vs PURO; facts=recupera passagens de base nao-codigo (livro) vs PURO")
    ap.add_argument("--validator", default="", help="comando com {file}; exit 0 = valido")
    ap.add_argument("--tasks", default=DEFAULT_TASKS, help="JSON [{q, expect[], legacy[]}]")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--topk", type=int, default=BENCH.get("topk", 15))
    ap.add_argument("--num_predict", type=int, default=BENCH.get("num_predict", 600), help="limite de tokens da geracao")
    ap.add_argument("--temperature", type=float, default=BENCH.get("temperature", 0.2), help="temperatura da geracao")
    ap.add_argument("--note", default="", help="anotacao livre (ex.: quant, variant, etc.)")
    ap.add_argument("--limit", type=int, default=0, help="roda so N tarefas")
    args = ap.parse_args()

    tasks = json.load(open(args.tasks, encoding="utf-8"))
    if args.limit:
        tasks = tasks[:args.limit]

    os.makedirs(BENCHDIR, exist_ok=True)
    safe = args.model.replace(":", "_").replace("/", "_")
    manifest_path = os.path.join(BENCHDIR, f"manifest_{safe}_{args.domain}_{args.mode}.json")
    results = []
    done = set()
    if os.path.exists(manifest_path):
        try:
            loaded = json.load(open(manifest_path, encoding="utf-8"))
            if isinstance(loaded, list) and all(
                    isinstance(r, dict) and "val_rag" in r for r in loaded):
                results = loaded
                done = {r["n"] for r in results}
                print(f"[retomando] {len(done)}/{len(tasks)} ja feitas", flush=True)
            else:
                print("[manifest incompativel] ignorando resultados anteriores", flush=True)
        except Exception:
            results = []
    t0 = time.time()
    run_meta = {
        "domain": args.domain,
        "model": args.model,
        "mode": args.mode,
        "lang": args.lang,
        "ext": args.ext,
        "validator": bool(args.validator),
        "topk": args.topk,
        "num_predict": args.num_predict,
        "temperature": args.temperature,
        "note": args.note,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    jsonl_path = os.path.join(HERE, "benchmark_results.jsonl")
    jsonl_f = open(jsonl_path, "a", encoding="utf-8")

    for i, t in enumerate(tasks, 1):
        if i in done:
            print(f"[{i:02d}] (ja feita, pulando)", flush=True)
            continue
        print(f"[{i:02d}/{len(tasks)}] {t['q'][:62]}...", flush=True)
        t_task = time.time()

        if args.mode == "facts":
            # --- COM RAG: recupera passagens da base e checa recall ---
            _, chunks = rag_retrieve.retrieve_chunks(t["q"], args.domain, topk=args.topk)
            rag_ctx = "\n".join(c["texto"] for c in chunks)
            rag_ok, rag_hit, _ = score(rag_ctx, t.get("expect", []), [])
            rag_vd, rag_err = None, ""
            open(os.path.join(BENCHDIR, f"rag_{i:02d}.ctx.txt"), "w", encoding="utf-8").write(rag_ctx)
            # --- SEM RAG: modelo sem contexto (conhecimento proprio) ---
            prompt = (
                "Responda a pergunta abaixo com base no seu conhecimento geral. "
                "Seja direto e cite os fatos pedidos.\n\n"
                f"PERGUNTA: {t['q']}\n\nRESPOSTA:"
            )
            norag_out = bare_gen(prompt, args.model, num_predict=args.num_predict,
                                 temperature=args.temperature)
            norag_ok, norag_hit, _ = score(norag_out, t.get("expect", []), [])
            norag_vd, norag_err = None, ""
            norag_wrong = []
            rag_path = os.path.join(BENCHDIR, f"rag_{i:02d}.ctx.txt")
            norag_path = os.path.join(BENCHDIR, f"norag_{i:02d}.ans.txt")
            open(norag_path, "w", encoding="utf-8").write(norag_out)
        else:
            # --- COM RAG: gera codigo com contexto ---
            rag_out, _ = programador.gerar(t["q"], args.domain, topk=args.topk,
                                            model=args.model, idioma="pt", reescrever=False,
                                            temperature=args.temperature, num_predict=args.num_predict)
            rag_code = programador.extrair_codigo(rag_out)
            rag_path = os.path.join(BENCHDIR, f"rag_{i:02d}.{args.ext}")
            open(rag_path, "w", encoding="utf-8").write(rag_code + "\n")
            rag_ok, rag_hit, _ = score(rag_out, t.get("expect", []), t.get("legacy", []))
            rag_vd, rag_err = validate(rag_path, args.validator)

            # --- SEM RAG: gera codigo sem contexto ---
            prompt = (
                "Voce e um programador experiente. Gere codigo para a TAREFA abaixo. "
                "Comente em portugues. Responda com o codigo.\n\n"
                f"TAREFA: {t['q']}\n\nCODIGO:"
            )
            norag_out = bare_gen(prompt, args.model, num_predict=args.num_predict,
                                 temperature=args.temperature)
            norag_code = programador.extrair_codigo(norag_out)
            norag_path = os.path.join(BENCHDIR, f"norag_{i:02d}.{args.ext}")
            open(norag_path, "w", encoding="utf-8").write(norag_code + "\n")
            norag_ok, norag_hit, norag_wrong = score(norag_out, t.get("expect", []), t.get("legacy", []))
            norag_vd, norag_err = validate(norag_path, args.validator)

        results.append({
            "n": i, "q": t["q"], "expect": t.get("expect", []),
            "kw_rag": rag_ok, "kw_hit_rag": rag_hit,
            "kw_norag": norag_ok, "kw_hit_norag": norag_hit, "legacy_norag": norag_wrong,
            "val_rag": rag_vd, "val_err_rag": rag_err,
            "val_norag": norag_vd, "val_err_norag": norag_err,
            "rag_path": rag_path, "norag_path": norag_path,
        })
        json.dump(results, open(manifest_path, "w"), ensure_ascii=False, indent=2)
        dt = round(time.time() - t_task, 1)
        append_record(jsonl_f, run_meta, i, t["q"], dt,
                      rag_ok, rag_vd, rag_err, norag_ok, norag_vd, norag_err)
        fmt = lambda b, e: ("OK" if b else "FAIL") + (f" ({e[:48]})" if (e and not b) else "")
        print(f"   RAG : kw={rag_ok}({','.join(rag_hit)}) val={fmt(rag_vd, rag_err) if rag_vd is not None else 'n/a'}  [{dt}s]", flush=True)
        print(f"   PURO: kw={norag_ok}({','.join(norag_hit)}) val={fmt(norag_vd, norag_err) if norag_vd is not None else 'n/a'}", flush=True)

    total = len(results)
    kw_rag = sum(1 for r in results if r["kw_rag"])
    kw_norag = sum(1 for r in results if r["kw_norag"])
    vals = [r for r in results if r["val_rag"] is not None]
    val_rag = sum(1 for r in vals if r["val_rag"])
    val_norag = sum(1 for r in vals if r["val_norag"])
    print("\n" + "=" * 72)
    print(f"ETAPA D — modo={args.mode}   TAREFAS: {total}   lingua={args.lang or '?'}   modelo={args.model}   (tempo: {int(time.time()-t0)}s)")
    print("-" * 72)
    print(f"ACERTO DE CONHECIMENTO (simbolo esperado na saida):")
    print(f"  RAG : {kw_rag}/{total} ({100*kw_rag/total:.0f}%)")
    print(f"  PURO: {kw_norag}/{total} ({100*kw_norag/total:.0f}%)")
    if vals:
        print(f"VALIDADE ({'validador informado'}) :")
        print(f"  RAG : {val_rag}/{len(vals)} ({100*val_rag/len(vals):.0f}%)")
        print(f"  PURO: {val_norag}/{len(vals)} ({100*val_norag/len(vals):.0f}%)")
        if val_norag:
            print(f"Ganho relativo do RAG (validade): +{(val_rag-val_norag)/val_norag*100:.0f}%")
        else:
            print(f"Ganho absoluto do RAG (validade): +{val_rag}/{len(vals)} tarefas validas")
    print("=" * 72)
    print(f"Arquivos: {BENCHDIR}")
    jsonl_f.close()
    print(f"Resultados JSONL (1 linha/pergunta, incremental): {jsonl_path}")


if __name__ == "__main__":
    main()

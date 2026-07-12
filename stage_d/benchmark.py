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

Sem "qwen": sintese roda com qwythos9b (offload local).
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

import programador

OLLAMA = "http://localhost:11434"
DEFAULT_MODEL = "qwythos9b"
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TASKS = os.path.join(HERE, "tasks_godot.json")
BENCHDIR = r"C:/Users/kiko2/AppData/Local/Temp/opencode/bench"


def bare_gen(prompt: str, model: str, num_predict: int = 600) -> str:
    r = requests.post(
        f"{OLLAMA}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False,
              "options": {"temperature": 0.2, "num_predict": num_predict}},
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


def main():
    ap = argparse.ArgumentParser(description="Etapa D — benchmark RAG x PURO (generico)")
    ap.add_argument("--domain", default="docsgodotengineorg")
    ap.add_argument("--lang", default="")
    ap.add_argument("--ext", default="gd")
    ap.add_argument("--validator", default="", help="comando com {file}; exit 0 = valido")
    ap.add_argument("--tasks", default=DEFAULT_TASKS, help="JSON [{q, expect[], legacy[]}]")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="roda so N tarefas")
    args = ap.parse_args()

    tasks = json.load(open(args.tasks, encoding="utf-8"))
    if args.limit:
        tasks = tasks[:args.limit]

    os.makedirs(BENCHDIR, exist_ok=True)
    manifest_path = os.path.join(BENCHDIR, "manifest.json")
    results = []
    done = set()
    if os.path.exists(manifest_path):
        try:
            results = json.load(open(manifest_path, encoding="utf-8"))
            done = {r["n"] for r in results}
            print(f"[retomando] {len(done)}/{len(tasks)} ja feitas", flush=True)
        except Exception:
            results = []
    t0 = time.time()

    for i, t in enumerate(tasks, 1):
        if i in done:
            print(f"[{i:02d}] (ja feita, pulando)", flush=True)
            continue
        print(f"[{i:02d}/{len(tasks)}] {t['q'][:62]}...", flush=True)

        # --- COM RAG ---
        rag_out, _ = programador.gerar(t["q"], args.domain, topk=args.topk,
                                       model=args.model, idioma="pt", reescrever=False)
        rag_code = programador.extrair_codigo(rag_out)
        rag_path = os.path.join(BENCHDIR, f"rag_{i:02d}.{args.ext}")
        open(rag_path, "w", encoding="utf-8").write(rag_code + "\n")
        rag_ok, rag_hit, _ = score(rag_out, t.get("expect", []), t.get("legacy", []))
        rag_vd, rag_err = validate(rag_path, args.validator)

        # --- SEM RAG ---
        prompt = (
            "Voce e um programador experiente. Gere codigo para a TAREFA abaixo. "
            "Comente em portugues. Responda com o codigo.\n\n"
            f"TAREFA: {t['q']}\n\nCODIGO:"
        )
        norag_out = bare_gen(prompt, args.model)
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
        fmt = lambda b, e: ("OK" if b else "FAIL") + (f" ({e[:48]})" if (e and not b) else "")
        print(f"   RAG : kw={rag_ok}({','.join(rag_hit)}) val={fmt(rag_vd, rag_err) if rag_vd is not None else 'n/a'}", flush=True)
        print(f"   PURO: kw={norag_ok}({','.join(norag_hit)}) val={fmt(norag_vd, norag_err) if norag_vd is not None else 'n/a'}", flush=True)

    total = len(results)
    kw_rag = sum(1 for r in results if r["kw_rag"])
    kw_norag = sum(1 for r in results if r["kw_norag"])
    vals = [r for r in results if r["val_rag"] is not None]
    val_rag = sum(1 for r in vals if r["val_rag"])
    val_norag = sum(1 for r in vals if r["val_norag"])
    print("\n" + "=" * 72)
    print(f"ETAPA D — TAREFAS: {total}   lingua={args.lang or '?'}   modelo={args.model}   (tempo: {int(time.time()-t0)}s)")
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


if __name__ == "__main__":
    main()

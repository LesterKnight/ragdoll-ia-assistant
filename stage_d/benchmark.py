"""
ETAPA D — Avaliacao do RAG (isolada do core A/B/C).

Compara o programador (RAG + modelo de sintese) contra o modelo de sintese PURO
(sem RAG) e valida o GDScript gerado compilando-o no Godot real (metodo do agente
gdtester: `godot --headless --check-only --script`).

Isola o ganho do RAG: mesmo modelo, so muda a presenca dos trechos da doc.
NENHUM modelo "qwen" e usado: a sintese roda com qwythos9b (offload local).

10 tarefas que exigem APIs NOVAS do Godot (doc estavel = 4.7; APIs de 4.3+),
desconhecidas do treino do modelo de sintese (qwythos9b).

Metricas por tarefa:
- kw_rag / kw_norag        : simbolo da nova API presente na saida? (acerto de conhecimento)
- godot_rag / godot_norag  : o GDScript gerado COMPILA no Godot? (validade real)

Uso (a partir da raiz do repo):
    python stage_d/benchmark.py
Resultado: <temp>/bench/ (20 .gd) + manifest.json + tabela no stdout.

Nao polui o core: fica em stage_d/ e so depende de programador.py e do Godot.
"""

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
MODEL = "qwythos9b"

# Godot fixo (mesmo do agente gdtester) — validacao de sintaxe real
GODOT = r"C:/Users/kiko2/OneDrive/Área de Trabalho/GODOT/Godot_v4.6.3-stable_win64.exe"
BENCHDIR = r"C:/Users/kiko2/AppData/Local/Temp/opencode/bench"

# cada tarefa: instrucao (PT, SEM vazar o nome da API) + simbolo(s) esperado(s)
# da nova API + termo(s) legado/errado que o modelo base costuma produzir
TAREFAS = [
    {"q": "Crie um script que adiciona uma camada de tiles e desenha um tile na posicao (3,4) da grade, usando a API de tiles da versao mais recente do Godot.",
     "expect": ["TileMapLayer"], "legacy": ["create_tile", "TileMap("]},
    {"q": "Crie um AudioStream que toque uma lista de musicas em sequencia, uma apos a outra, sem cortar o audio entre elas.",
     "expect": ["AudioStreamPlaylist"], "legacy": ["AudioStreamPlayer"]},
    {"q": "Crie um AudioStream que sincronize dois audios (voz + musica) para tocarem perfeitamente alinhados no mesmo playback.",
     "expect": ["AudioStreamSynchronized"], "legacy": ["AudioStreamPlayer"]},
    {"q": "Crie um efeito de pos-processamento personalizado via shader que roda na passada de composicao da camera.",
     "expect": ["CompositorEffect"], "legacy": ["VisualServer", "WorldEnvironment"]},
    {"q": "Crie um modificador que aplica fisica a um Skeleton3D fazendo os ossos reagirem a colisoes, usando a classe de modificador esqueleto.",
     "expect": ["SkeletonModifier3D"], "legacy": ["SkeletonIK", "BoneAttachment"]},
    {"q": "Crie uma textura de gradiente 2D configuravel por pontos, usando a classe de textura de gradiente 2D nova.",
     "expect": ["GradientTexture2D"], "legacy": ["GradientTexture("]},
    {"q": "Crie um obstaculo de navegacao que agentes evitam em runtime, usando a classe de obstaculo de navegacao 2D.",
     "expect": ["NavigationObstacle2D"], "legacy": ["NavigationMesh", "navmesh"]},
    {"q": "Crie um loop que processa tarefas pesadas em varias threads usando o pool de threads do engine, sem criar Threads manuais.",
     "expect": ["WorkerThreadPool"], "legacy": ["Thread.new", "OS.threads"]},
    {"q": "Crie um sistema multiplayer que instancia automaticamente uma cena para cada novo peer conectado, usando o node spawner.",
     "expect": ["MultiplayerSpawner"], "legacy": ["rpc(", "instance_child"]},
    {"q": "Crie um node que emite sinal quando um objeto 3D entra ou sai da area visivel da camera.",
     "expect": ["VisibleOnScreenNotifier3D"], "legacy": ["VisibilityNotifier", "VisibilityEnabler"]},
]


def bare_gen(prompt: str, num_predict: int = 600) -> str:
    r = requests.post(
        f"{OLLAMA}/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False,
              "options": {"temperature": 0.2, "num_predict": num_predict}},
        timeout=600,
    )
    r.raise_for_status()
    return r.json().get("response", "")


def godot_validate(path: str):
    """Valida sintaxe via Godot (mesmo metodo do agente gdtester)."""
    try:
        p = subprocess.run(
            [GODOT, "--headless", "--check-only", "--script", path],
            capture_output=True, text=True, timeout=120,
        )
        ok = p.returncode == 0
        err = ""
        for line in (p.stderr + p.stdout).splitlines():
            if "SCRIPT ERROR" in line or "ERROR:" in line:
                err = line.strip()
                break
        return ok, ("" if ok else err)
    except Exception as e:
        return False, f"erro ao rodar godot: {e}"


def score(out: str, expect, legacy):
    has = [s for s in expect if s.lower() in out.lower()]
    wrong = [s for s in legacy if s.lower() in out.lower()]
    return (len(has) >= 1, has, wrong)


def main():
    os.makedirs(BENCHDIR, exist_ok=True)
    manifest_path = os.path.join(BENCHDIR, "manifest.json")
    results = []
    done = set()
    if os.path.exists(manifest_path):
        try:
            results = json.load(open(manifest_path, encoding="utf-8"))
            done = {r["n"] for r in results}
            print(f"[retomando] {len(done)}/{len(TAREFAS)} ja feitas", flush=True)
        except Exception:
            results = []
    t0 = time.time()

    for i, t in enumerate(TAREFAS, 1):
        if i in done:
            print(f"[{i:02d}/10] (ja feita, pulando)", flush=True)
            continue
        print(f"[{i:02d}/10] {t['q'][:62]}...", flush=True)

        # --- RAG side (programador + modelo de sintese) ---
        rag_out, _ = programador.gerar(t["q"], "docsgodotengineorg", topk=5,
                                       model=MODEL, idioma="pt", reescrever=False)
        rag_code = programador.extrair_codigo(rag_out)
        rag_path = os.path.join(BENCHDIR, f"rag_{i:02d}.gd")
        open(rag_path, "w", encoding="utf-8").write(rag_code + "\n")
        rag_ok, rag_hit, _ = score(rag_out, t["expect"], t["legacy"])
        rag_gd, rag_err = godot_validate(rag_path)

        # --- no-RAG side (modelo de sintese puro) ---
        prompt = (
            "Voce e um programador Godot experiente. Gere codigo GDScript para a "
            "TAREFA abaixo. Comente em portugues. Responda com o codigo.\n\n"
            f"TAREFA: {t['q']}\n\nCODIGO:"
        )
        norag_out = bare_gen(prompt)
        norag_code = programador.extrair_codigo(norag_out)
        norag_path = os.path.join(BENCHDIR, f"norag_{i:02d}.gd")
        open(norag_path, "w", encoding="utf-8").write(norag_code + "\n")
        norag_ok, norag_hit, norag_wrong = score(norag_out, t["expect"], t["legacy"])
        norag_gd, norag_err = godot_validate(norag_path)

        results.append({
            "n": i, "q": t["q"], "expect": t["expect"],
            "kw_rag": rag_ok, "kw_hit_rag": rag_hit,
            "kw_norag": norag_ok, "kw_hit_norag": norag_hit, "legacy_norag": norag_wrong,
            "godot_rag": rag_gd, "godot_err_rag": rag_err,
            "godot_norag": norag_gd, "godot_err_norag": norag_err,
            "rag_path": rag_path, "norag_path": norag_path,
        })
        json.dump(results, open(manifest_path, "w"), ensure_ascii=False, indent=2)
        print(f"   RAG  : kw={rag_ok}({','.join(rag_hit)}) godot={'OK' if rag_gd else 'FAIL'}"
              + (f' ({rag_err[:50]})' if rag_err else ''), flush=True)
        print(f"   PURO : kw={norag_ok}({','.join(norag_hit)}) godot={'OK' if norag_gd else 'FAIL'}"
              + (f' ({norag_err[:50]})' if norag_err else ''), flush=True)

    total = len(results)
    kw_rag = sum(1 for r in results if r["kw_rag"])
    kw_norag = sum(1 for r in results if r["kw_norag"])
    godot_rag = sum(1 for r in results if r["godot_rag"])
    godot_norag = sum(1 for r in results if r["godot_norag"])
    print("\n" + "=" * 72)
    print(f"ETAPA D — TAREFAS: {total}   (tempo: {int(time.time()-t0)}s)")
    print("-" * 72)
    print(f"ACERTO DE CONHECIMENTO (simbolo da API nova na saida):")
    print(f"  RAG : {kw_rag}/{total} ({100*kw_rag/total:.0f}%)")
    print(f"  PURO: {kw_norag}/{total} ({100*kw_norag/total:.0f}%)")
    print(f"VALIDADE REAL (GDScript compila no Godot 4.6.3):")
    print(f"  RAG : {godot_rag}/{total} ({100*godot_rag/total:.0f}%)")
    print(f"  PURO: {godot_norag}/{total} ({100*godot_norag/total:.0f}%)")
    if godot_norag:
        print(f"Ganho relativo do RAG (validade): +{(godot_rag-godot_norag)/godot_norag*100:.0f}%")
    else:
        print(f"Ganho absoluto do RAG (validade): +{godot_rag}/{total} tarefas compilaveis")
    print("=" * 72)
    print(f"Arquivos: {BENCHDIR}")


if __name__ == "__main__":
    main()

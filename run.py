"""
Orquestrador das fases A -> B -> C do ragdoll.

Uso:
    python run.py all --url "<URL>" --escopo 2 --delay 2000
    python run.py crawl  --url "<URL>" --escopo 2 --delay 2000
    python run.py parse  --dir "RAG/<dominio>"
    python run.py process --dir "RAG/<dominio>" [--foreground]

A Fase C (process) roda em background por padrao (jobs longos); use --foreground
para acompanhar no terminal. Todas as fases sao retomaveis nos proprios scripts.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
RAG = ROOT / "RAG"

DETACHED = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)


def simplify_domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return re.sub(r"[^a-z0-9]", "", host.lower())


def run_inline(script: str, args: list) -> int:
    cmd = [sys.executable, str(ROOT / script)] + args
    return subprocess.run(cmd).returncode


def run_background(script: str, args: list, slug: str) -> int:
    cmd = [sys.executable, str(ROOT / script)] + args
    if os.name == "nt":
        proc = subprocess.Popen(cmd, creationflags=DETACHED,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        proc = subprocess.Popen(cmd, start_new_session=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.pid


def crawl_opts(args: argparse.Namespace) -> list:
    opts = []
    if args.escopo is not None:
        opts += ["--escopo", str(args.escopo)]
    if args.delay is not None:
        opts += ["--delay", str(args.delay)]
    if args.limite is not None:
        opts += ["--limite", str(args.limite)]
    return opts


def cmd_all(args: argparse.Namespace):
    slug = simplify_domain(args.url)
    d = RAG / slug
    if run_inline("crawl.py", ["--url", args.url] + crawl_opts(args)) != 0:
        sys.exit(1)
    if run_inline("parse.py", ["--dir", str(d)]) != 0:
        sys.exit(1)
    pargs = ["--dir", str(d)]
    if args.limpar_raw:
        pargs.append("--limpar-raw")
    if args.chunk_model:
        pargs += ["--chunk-model", args.chunk_model]
    if args.summary_model:
        pargs += ["--summary-model", args.summary_model]
    if args.reset:
        pargs.append("--reset")
    if args.foreground:
        if run_inline("process.py", pargs) != 0:
            sys.exit(1)
    else:
        run_background("process.py", pargs, slug)


def cmd_crawl(args: argparse.Namespace):
    if run_inline("crawl.py", ["--url", args.url] + crawl_opts(args)) != 0:
        sys.exit(1)


def cmd_parse(args: argparse.Namespace):
    pargs = ["--dir", args.dir]
    if args.reset:
        pargs.append("--reset")
    if run_inline("parse.py", pargs) != 0:
        sys.exit(1)


def cmd_process(args: argparse.Namespace):
    pargs = ["--dir", args.dir]
    if args.limpar_raw:
        pargs.append("--limpar-raw")
    if args.chunk_model:
        pargs += ["--chunk-model", args.chunk_model]
    if args.summary_model:
        pargs += ["--summary-model", args.summary_model]
    if args.reset:
        pargs.append("--reset")
    slug = Path(args.dir).name
    if args.foreground:
        if run_inline("process.py", pargs) != 0:
            sys.exit(1)
    else:
        run_background("process.py", pargs, slug)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Orquestrador ragdoll (A->B->C)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("all", help="executa A+B+C (Fase C em background)")
    pa.add_argument("--url", required=True)
    pa.add_argument("--escopo", type=int, default=None)
    pa.add_argument("--delay", type=int, default=None)
    pa.add_argument("--limite", type=int, default=None)
    pa.add_argument("--limpar-raw", action="store_true")
    pa.add_argument("--chunk-model", default=None)
    pa.add_argument("--summary-model", default=None)
    pa.add_argument("--reset", action="store_true")
    pa.add_argument("--foreground", action="store_true", help="Fase C no terminal (nao background)")
    pa.set_defaults(func=cmd_all)

    pc = sub.add_parser("crawl", help="so Fase A")
    pc.add_argument("--url", required=True)
    pc.add_argument("--escopo", type=int, default=None)
    pc.add_argument("--delay", type=int, default=None)
    pc.add_argument("--limite", type=int, default=None)
    pc.set_defaults(func=cmd_crawl)

    pp = sub.add_parser("parse", help="so Fase B")
    pp.add_argument("--dir", required=True)
    pp.add_argument("--reset", action="store_true")
    pp.set_defaults(func=cmd_parse)

    pp2 = sub.add_parser("process", help="so Fase C (retomavel)")
    pp2.add_argument("--dir", required=True)
    pp2.add_argument("--limpar-raw", action="store_true")
    pp2.add_argument("--chunk-model", default=None)
    pp2.add_argument("--summary-model", default=None)
    pp2.add_argument("--reset", action="store_true")
    pp2.add_argument("--foreground", action="store_true")
    pp2.set_defaults(func=cmd_process)

    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)

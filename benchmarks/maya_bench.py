#!/usr/bin/env python3
"""Maya's fixed-input decode/prefill procedure for a pinned DeepSeek HIP engine.

Use maya-bench-inputs.json for the repository's matched comparisons: one warm-up,
three answers capped at 256 tokens (greedy, thinking off), and 2048/8192-token
prompts from Project Maya v1.1.28's public documentation. It constructs the explicit
DeepSeek chat wrapper; the pack's Jinja template is not used. The release config
supplies the engine, pack and settings. Qualification owns the guarded systemd lifecycle.

    python maya_bench.py run <config.json> <engine-source> <inputs.json> <out-dir>
    python maya_bench.py prepare <v1.1.28-source> <tokenizer-dir> <new-inputs.json>

Input text/questions: Project Maya (MIT), source commit and file digests inside the
JSON; license in PROJECT-MAYA-LICENSE. Output includes actual native DONE records,
token counts, per-request timings and the arithmetic mean of the three decode rates.
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

# v1.1.28 maya.py BENCH_TOPICS, its warm-up question and its DeepSeek chat format (issue #416)
TOPICS = [
    "Write a Python function that parses a CSV file into a list of dictionaries, with type hints and a docstring.",
    "Explain how photosynthesis works, step by step, for a high-school student.",
    "Write a complete HTML page with a canvas that draws a bouncing ball animation in JavaScript.",
]
WARMUP = "Say hello in five languages."
LENS = (2048, 8192)
DECODE_TOKENS, WARMUP_TOKENS = 256, 64


def chat_text(q):
    return "<｜begin▁of▁sentence｜><｜User｜>" + q + "<｜Assistant｜></think>"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def doc_files(root):
    """bench()'s docs: README.md, docs/*.md, bench/results/*.md, in that order, those that exist."""
    return [p for p in [root / "README.md"] + sorted((root / "docs").glob("*.md")) +
            sorted((root / "bench" / "results").glob("*.md")) if p.exists()]


def prepare(root, tokenizer, out):
    root, tokenizer = Path(root), Path(tokenizer)
    sys.path.insert(0, str(root / "tools"))
    sys.path.insert(0, str(root))
    import strata_tokenizer as ST
    tok = ST.Tokenizer.from_dir(tokenizer)
    files = doc_files(root)
    text = "\n\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files)
    doc = tok.encode(text)
    chat = lambda q: tok.encode(chat_text(q), parse_special=True)   # noqa: E731
    lens = [n for n in LENS if n <= len(doc)]
    data = {
        "procedure": "maya.py v1.1.28 bench(), DeepSeek on HIP",
        "root_commit": subprocess.run(("git", "-C", str(root), "rev-parse", "HEAD"), capture_output=True, text=True,
                                      check=True).stdout.strip(),
        "docs": [{"path": str(p.relative_to(root)), "sha256": sha(p.read_bytes())} for p in files],
        "tokenizer": {p.name: sha(p.read_bytes()) for p in sorted(tokenizer.iterdir()) if p.is_file()},
        "warmup": chat(WARMUP),
        "decode": [{"question": q, "ids": chat(q)} for q in TOPICS],
        "prefill_warmup": doc[-lens[0]:] if lens else [],
        "prefill": [{"tokens": n, "ids": doc[i * 997:i * 997 + n]} for i, n in enumerate(lens)],
    }
    Path(out).write_text(json.dumps(data) + "\n")
    print(json.dumps({"inputs": str(out), "sha256": sha(Path(out).read_bytes()), "doc_tokens": len(doc), "lens": lens}))


def engine(cfg_path, root):
    """The config as maya.py reads it and the engine's command and environment from the root's own server."""
    root = Path(root)
    sys.path.insert(0, str(root / "tools"))
    sys.path.insert(0, str(root))
    import maya_names as N
    import serve.server as SV
    cfg = N.env_in(json.loads(Path(cfg_path).read_text(encoding="utf-8-sig")))
    return cfg, [cfg["exe"], "--serve"] + SV.engine_args(cfg), SV.child_env(cfg)


def run(cfg_path, root, inputs_path, out):
    out = Path(out)
    inputs = json.loads(Path(inputs_path).read_text())
    cfg, cmd, env = engine(cfg_path, root)
    args = cfg.get("args") or []
    ctx = int(args[args.index("--max-context") + 1]) if "--max-context" in args[:-1] else 32768
    prefill = [p for p in inputs["prefill"] if p["tokens"] + 64 <= ctx]
    done_lines, results = [], []
    t0 = time.time()
    with open(out / "engine.log", "w", encoding="utf-8") as log:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True, env=env,
                             cwd=cfg.get("cwd") or str(root), bufsize=1)

        def gen(ids, n_new, what):
            p.stdin.write(f"GEN {n_new} temperature=0 " + ",".join(map(str, ids)) + "\n")
            p.stdin.flush()
            while True:
                line = p.stdout.readline()
                if not line:
                    raise SystemExit("the engine stopped during the benchmark")
                if line.startswith("DONE") or line.startswith("ERR"):
                    done_lines.append({"what": what, "line": line.strip()})
                    return line.split()

        while True:
            line = p.stdout.readline()
            if not line:
                raise SystemExit("the engine stopped while loading")
            if line.startswith("READY"):
                break
        load_seconds = round(time.time() - t0, 1)
        gen(inputs["warmup"], WARMUP_TOKENS, "warm-up answer")
        for d in inputs["decode"]:
            f = gen(d["ids"], DECODE_TOKENS, d["question"])
            if f[0] == "DONE" and float(f[4]) > 0:
                results.append({"kind": "decode", "what": d["question"], "generated": int(f[1]),
                                "decode_ms": float(f[4]), "tokens_per_second": int(f[1]) / float(f[4]) * 1000.0})
        if prefill:
            gen(inputs["prefill_warmup"], 1, "prompt warm-up")
        for d in prefill:
            f = gen(d["ids"], 1, f"{d['tokens']}-token prompt")
            if f[0] == "DONE" and float(f[3]) > 0:
                results.append({"kind": "prefill", "what": f"{d['tokens']} tokens", "tokens": d["tokens"],
                                "prompt_ms": float(f[3]), "tokens_per_second": d["tokens"] / float(f[3]) * 1000.0})
        p.stdin.write("QUIT\n")
        p.stdin.flush()
        try:
            p.wait(timeout=120)
        except subprocess.TimeoutExpired:
            p.kill()
    dec = [r["tokens_per_second"] for r in results if r["kind"] == "decode"]
    data = {"config": str(cfg_path), "config_sha256": sha(Path(cfg_path).read_bytes()), "root": str(root),
            "inputs_sha256": sha(Path(inputs_path).read_bytes()), "context": ctx, "load_seconds": load_seconds,
            "decode_mean_tokens_per_second": sum(dec) / max(1, len(dec)), "decode_answers": len(dec),
            "prefill_tokens_per_second": {str(r["tokens"]): r["tokens_per_second"]
                                          for r in results if r["kind"] == "prefill"},
            "results": results, "done_lines": done_lines, "engine_exit": p.returncode}
    (out / "bench.json").write_text(json.dumps(data, indent=1) + "\n")
    print(json.dumps({k: data[k] for k in ("decode_mean_tokens_per_second", "prefill_tokens_per_second")}))
    if len(dec) != len(inputs["decode"]) or len(data["prefill_tokens_per_second"]) != len(prefill):
        raise SystemExit("a bench request did not finish")


if __name__ == "__main__":
    if sys.argv[1] == "prepare":
        prepare(*sys.argv[2:5])
    elif sys.argv[1] == "run":
        run(*sys.argv[2:6])
    else:
        raise SystemExit(__doc__)

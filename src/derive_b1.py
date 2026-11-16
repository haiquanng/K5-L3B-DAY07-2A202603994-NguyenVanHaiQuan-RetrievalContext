"""Derive the chosen configuration B1 from baseline traces: same agent outputs + deterministic citation expansion.

  python -m src.derive_b1 --suite advanced --split test

B1 differs from the baseline only by a post-processing step (agent.expand_citations), so applying it to the
baseline traces gives B1's output for the same agent answers (a paired comparison without re-sampling the model).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agent import distinctive_numbers, expand_citations  # noqa: E402
from src.eval_retrieval import load  # noqa: E402
from src.retrieval import Retriever  # noqa: E402
from src.run_agent import summarize  # noqa: E402

R = ROOT / "starter" / "results" / "agent"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--split", required=True)
    a = ap.parse_args()
    src, dst = R / f"{a.suite}.{a.split}.baseline", R / f"{a.suite}.{a.split}.chosen_B1"
    traces = json.loads((src / "traces.json").read_text())
    out = []
    for t in traces:
        t = json.loads(json.dumps(t))
        t["config"]["cite_expand"] = True
        if t["status"] == "answered":
            seen = {c["chunk_id"]: c for c in t["context"]}
            extra = expand_citations(t["answer"], t["citations"], seen)
            if extra:
                t["events"].insert(-1, {"event": "citation_expansion", "added": extra,
                                        "numbers": sorted(distinctive_numbers(t["answer"]))})
                t["answer"] += "\n\nNguồn có cùng số liệu: " + " ".join(f"[{c}]" for c in extra)
                t["citations"] = t["citations"] + extra
                by = {c["chunk_id"]: c for c in t["context"]}
                t["citation_sources"] += [{k: by[c][k] for k in ("chunk_id", "pdf_page", "printed_page", "kind", "bbox", "crop_path")}
                                          for c in extra]
        t["derived_from"] = f"{src.name} (deterministic citation expansion, no model re-run)"
        out.append(t)
    _, gold = load(a.suite, a.split)
    retr = Retriever(embedder=object())  # only chunk texts are needed; no model is loaded
    dst.mkdir(parents=True, exist_ok=True)
    meta = json.loads((src / "auto.json").read_text())
    summary = {**{k: meta[k] for k in ("suite", "split", "code_commit", "embedding_model")}, "name": "chosen_B1",
               "derived_from": src.name, "config": {**meta["config"], "cite_expand": True},
               "label_type": meta["label_type"], **summarize(out, gold, retr)}
    (dst / "traces.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    (dst / "auto.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    print(a.suite, a.split, "strict", summary["proxy_strict_pass"])


if __name__ == "__main__":
    main()

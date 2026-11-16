"""Retrieval comparison on the benchmark with an AUTOMATIC PROXY label (dev selection only).

  python -m src.eval_retrieval --suite advanced --split dev --methods dense bm25 bm25_bigram hybrid

Retrieval runs on the ORIGINAL question text from queries/*.json (no gold). Afterwards, and only here,
gold evidence is compared to the ranking:

  chunk supports evidence E  <=>  chunk.pdf_page == E.pdf_page  AND  ( >= half of E.quotes occur in the chunk
                                   text  OR  the chunk bbox covers >= half of E.bbox_pt )

This proxy is for comparing configurations on dev. It is NOT the human label the benchmark scorer requires
(benchmark/fpt_2025/tools.py): test retrieval / context labels are assigned by the human reviewer.
Metrics over answerable questions: Hit@1, Hit@3 (>=1 evidence), Full@3 (an all_of group complete in top-3),
Hit@10, MRR@10, plus latency.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark" / "fpt_2025"
OUT = ROOT / "starter" / "results" / "retrieval"


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", t).lower()).strip()


def cover(chunk_bbox, gold_bbox) -> float:
    x0, y0 = max(chunk_bbox[0], gold_bbox[0]), max(chunk_bbox[1], gold_bbox[1])
    x1, y1 = min(chunk_bbox[2], gold_bbox[2]), min(chunk_bbox[3], gold_bbox[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    area = (gold_bbox[2] - gold_bbox[0]) * (gold_bbox[3] - gold_bbox[1])
    return inter / area if area > 0 else 0.0


def supports(hit: dict, ev: dict) -> bool:
    if hit["pdf_page"] != ev["pdf_page"]:
        return False
    text = norm(hit["text"])
    quotes = ev.get("quotes") or []
    q_ok = bool(quotes) and sum(norm(q) in text for q in quotes) * 2 >= len(quotes)
    b_ok = bool(ev.get("bbox_pt")) and cover(hit["bbox"], ev["bbox_pt"]) >= 0.5
    return q_ok or b_ok


def evidence_in(hits: list[dict], case: dict) -> set[str]:
    return {ev["id"] for h in hits for ev in case["gold"] if supports(h, ev)}


def complete(case: dict, found: set[str]) -> bool:
    return any(set(g["all_of"]) <= found for g in case["evidence_groups"])


def load(suite: str, split: str) -> tuple[list[dict], dict[str, dict]]:
    queries = json.loads((BENCH / "queries" / f"{suite}.{split}.json").read_text(encoding="utf-8"))
    gold = {c["id"]: c for c in json.loads((BENCH / "gold" / f"{suite}.{split}.json").read_text(encoding="utf-8"))}
    return queries, gold


def evaluate(retriever, method: str, queries: list[dict], gold: dict[str, dict], k: int = 10, **kw) -> dict:
    rows, lat = [], []
    for q in queries:  # retrieval sees only the question
        hits, ms = retriever.search(q["question"], method, k, **kw)
        lat.append(ms)
        rows.append({"id": q["id"], "hits": hits})
    per = []
    for r in rows:  # gold used only from here on
        c = gold[r["id"]]
        if not c["answerable"]:
            continue
        ranks = [i for i, h in enumerate(r["hits"], 1) if evidence_in([h], c)]
        per.append({"id": r["id"], "category": c["primary_category"],
                    "hit1": bool(ranks and ranks[0] == 1), "hit3": bool(ranks and ranks[0] <= 3),
                    "full3": complete(c, evidence_in(r["hits"][:3], c)), "hit10": bool(ranks),
                    "rr": 1 / ranks[0] if ranks else 0.0,
                    "top3": [(h["chunk_id"], h["score"]) for h in r["hits"][:3]]})
    n = len(per)

    def rate(key, subset=per):
        return {"n": sum(p[key] for p in subset), "N": len(subset),
                "rate": round(sum(p[key] for p in subset) / len(subset), 3) if subset else None}
    cats = sorted({p["category"] for p in per})
    return {"method": method, "params": {"k": k, **kw}, "answerable": n,
            "hit_at_1": rate("hit1"), "hit_at_3": rate("hit3"), "full_at_3": rate("full3"), "hit_at_10": rate("hit10"),
            "mrr_at_10": round(sum(p["rr"] for p in per) / n, 3) if n else None,
            "hit_at_3_by_category": {c: rate("hit3", [p for p in per if p["category"] == c]) for c in cats},
            "latency_ms_median": round(statistics.median(lat), 1), "per_query": per, "rankings": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", choices=["basic", "advanced"], required=True)
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--methods", nargs="+", default=["dense", "bm25", "bm25_bigram", "hybrid"])
    ap.add_argument("--allow-test", action="store_true", help="test is only run after the config is frozen")
    a = ap.parse_args()
    if a.split == "test" and not a.allow_test:
        sys.exit("refusing to evaluate on test: freeze the configuration on dev first, then pass --allow-test")
    sys.path.insert(0, str(ROOT))
    from src.retrieval import Retriever
    retriever = Retriever()
    queries, gold = load(a.suite, a.split)
    OUT.mkdir(parents=True, exist_ok=True)
    table = []
    for m in a.methods:
        res = evaluate(retriever, m, queries, gold)
        if m == "rerank" and hasattr(retriever, "rerank_usage"):
            u = dict(retriever.rerank_usage)
            res["rerank_usage"] = u
            res["rerank_cost_usd"] = round((u["input"] * 0.75 + u["output"] * 4.50) / 1e6, 4)
            retriever.rerank_usage = {"input": 0, "output": 0, "calls": 0}
        res.update(suite=a.suite, split=a.split, at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   label_type="automatic proxy (page + quote/bbox overlap); not human review")
        (OUT / f"{a.suite}.{a.split}.{m}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
        table.append(res)
    print(f"\n{a.suite}/{a.split}: answerable N={table[0]['answerable']} (proxy labels)")
    print(f"{'method':14s} {'Hit@1':>12s} {'Hit@3':>12s} {'Full@3':>12s} {'Hit@10':>12s} {'MRR@10':>7s} {'ms':>6s}")
    for r in table:
        f = lambda m: f"{m['n']}/{m['N']} {m['rate']:.2f}"  # noqa: E731
        print(f"{r['method']:14s} {f(r['hit_at_1']):>12s} {f(r['hit_at_3']):>12s} {f(r['full_at_3']):>12s} "
              f"{f(r['hit_at_10']):>12s} {r['mrr_at_10']:>7.3f} {r['latency_ms_median']:>6.0f}")
    cats = sorted(table[0]["hit_at_3_by_category"])
    print("\nHit@3 by category: " + " | ".join(cats))
    for r in table:
        print(f"{r['method']:14s} " + " | ".join(f"{r['hit_at_3_by_category'][c]['n']}/{r['hit_at_3_by_category'][c]['N']}"
                                                for c in cats))


if __name__ == "__main__":
    main()

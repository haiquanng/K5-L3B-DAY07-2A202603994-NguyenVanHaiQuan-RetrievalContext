"""Run the agent on a benchmark split and summarize with automatic (proxy) labels.

  python -m src.run_agent --suite advanced --split dev --name hybrid_k5 --method hybrid --top-k 5
  python -m src.run_agent --suite advanced --split dev --name hybrid_k5 --limit 10      # quick smoke run

Outputs (starter/results/agent/<suite>.<split>.<name>/):
  traces.json   one trace per query in the format benchmark/fpt_2025/tools.py score expects (+ extra fields)
  auto.json     proxy summary: retrieval Hit@1/3 on the ORIGINAL question ranking, context evidence,
                cited chunks that overlap gold evidence, status / abstention, judge grades, latency, cost
The agent only receives queries/*.json (id + question). Gold is read afterwards, here, for the proxy.
Proxy and LLM-judge labels are for comparing configurations on dev; the reported test result must come
from human review (benchmark/fpt_2025/README.md).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agent import PRICES, Agent, AgentConfig, cost_usd  # noqa: E402
from src.eval_retrieval import complete, evidence_in, load  # noqa: E402
from src.retrieval import Retriever  # noqa: E402

OUT = ROOT / "starter" / "results" / "agent"

JUDGE = """Bạn chấm câu trả lời của hệ thống RAG so với đáp án chuẩn (tiếng Việt). Không cần kiểm tra citation.
answerable=true: grade 2 = đúng và đủ mọi ý bắt buộc, đúng đơn vị/kỳ/phép tính (cho phép diễn đạt khác,
làm tròn hợp lý); 1 = đúng một phần hoặc thiếu ý; 0 = sai, từ chối, hoặc không trả lời.
answerable=false: abstain_ok=true nếu hệ thống từ chối/nói rõ tài liệu không có thông tin được hỏi và không
đưa ra con số/khẳng định suy đoán cho phần đó (được phép nêu thông tin liên quan có nguồn).
unsupported=true nếu câu trả lời có khẳng định cụ thể mâu thuẫn hoặc không có trong đáp án chuẩn/lý do."""
JUDGE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["grade", "abstain_ok", "unsupported", "reason"],
                "properties": {"grade": {"type": "integer", "enum": [0, 1, 2]}, "abstain_ok": {"type": "boolean"},
                               "unsupported": {"type": "boolean"}, "reason": {"type": "string"}}}


def judge(client, model: str, case: dict, trace: dict) -> dict:
    ref = ({"expected_answer": case["expected_answer"], "required_facts": case["required_facts"]} if case["answerable"]
           else {"expected_answer": case["expected_answer"], "missing_information": case.get("absence_check", {}).get("missing_information")})
    msg = json.dumps({"question": case["question"], "answerable": case["answerable"], **ref,
                      "system_status": trace["status"], "system_answer": trace["answer"]}, ensure_ascii=False)
    r = client.chat.completions.create(
        model=model, reasoning_effort="low", messages=[{"role": "system", "content": JUDGE}, {"role": "user", "content": msg}],
        response_format={"type": "json_schema", "json_schema": {"name": "grade", "strict": True, "schema": JUDGE_SCHEMA}})
    out = json.loads(r.choices[0].message.content)
    out["cost_usd"] = cost_usd(model, {"input": r.usage.prompt_tokens, "cached": 0, "output": r.usage.completion_tokens})
    return out


def ratio(n: int, d: int) -> dict:
    return {"n": n, "N": d, "rate": round(n / d, 3) if d else None}


def summarize(traces: list[dict], gold: dict[str, dict], retr: Retriever) -> dict:
    by = {c: retr.by_id[c] for t in traces for c in t.get("context_ids", []) if c in retr.by_id}
    ans, neg, rows = [], [], []
    for t in traces:
        c = gold[t["query_id"]]
        rank = [{"text": retr.by_id[h["chunk_id"]]["content"], "bbox": list(retr.by_id[h["chunk_id"]]["bbox"]),
                 "pdf_page": h["pdf_page"]} for h in t.get("original_query_ranking", [])]
        ctx = [{"text": by[i]["content"], "bbox": list(by[i]["bbox"]), "pdf_page": by[i]["pdf_page"]}
               for i in t.get("context_ids", []) if i in by]
        cited = [{"text": by[i]["content"], "bbox": list(by[i]["bbox"]), "pdf_page": by[i]["pdf_page"]}
                 for i in t.get("citations", []) if i in by]
        cite_ok = sum(bool(evidence_in([x], c)) for x in cited)
        j = t.get("judge", {})
        row = {"id": t["query_id"], "category": c["primary_category"], "answerable": c["answerable"],
               "status": t["status"], "hit1": bool(evidence_in(rank[:1], c)), "hit3": bool(evidence_in(rank[:3], c)),
               "ctx_complete": complete(c, evidence_in(ctx, c)), "cites": len(cited), "cites_on_gold": cite_ok,
               "cited_complete": complete(c, evidence_in(cited, c)), "grade": j.get("grade"),
               "abstain_ok": j.get("abstain_ok"), "unsupported": j.get("unsupported")}
        # strict proxy pass mirrors the scorer: answered, judge 2, full evidence in context and in citations
        row["proxy_pass"] = (row["status"] == "answered" and row["grade"] == 2 and row["ctx_complete"]
                             and row["cited_complete"] and not row["unsupported"]) if c["answerable"] else \
            (row["status"] == "abstain" and bool(row["abstain_ok"]) and not row["unsupported"])
        rows.append(row)
        (ans if c["answerable"] else neg).append(row)
    times = sorted(t["elapsed_ms"] for t in traces if t.get("elapsed_ms") is not None)
    costs = [t["cost_usd"] for t in traces if t.get("cost_usd") is not None]
    ok = [t for t in traces if t["status"] in ("answered", "abstain")]
    cats = sorted({r["category"] for r in rows})
    return {
        "N": len(rows), "answerable": len(ans), "unanswerable": len(neg),
        "proxy_strict_pass": ratio(sum(r["proxy_pass"] for r in rows), len(rows)),
        "proxy_pass_by_category": {k: ratio(sum(r["proxy_pass"] for r in rows if r["category"] == k),
                                            sum(r["category"] == k for r in rows)) for k in cats},
        "retrieval_hit_at_1_original": ratio(sum(r["hit1"] for r in ans), len(ans)),
        "retrieval_hit_at_3_original": ratio(sum(r["hit3"] for r in ans), len(ans)),
        "context_evidence_rate": ratio(sum(r["ctx_complete"] for r in ans), len(ans)),
        "judge_grade_counts": dict(Counter(r["grade"] for r in ans)),
        "judge_grade_mean_over_2": round(sum(r["grade"] or 0 for r in ans) / (2 * len(ans)), 3) if ans else None,
        "citations_on_gold_evidence": ratio(sum(r["cites_on_gold"] for r in rows), sum(r["cites"] for r in rows)),
        "answers_with_citation": ratio(sum(r["cites"] > 0 for r in rows if r["status"] == "answered"),
                                       sum(r["status"] == "answered" for r in rows)),
        "correct_abstention": ratio(sum(r["proxy_pass"] for r in neg), len(neg)),
        "false_abstention": ratio(sum(r["status"] == "abstain" for r in ans), len(ans)),
        "statuses": dict(Counter(t["status"] for t in traces)),
        "tool_use": ratio(sum(t.get("search_calls", 0) > 0 for t in ok), len(ok)),
        "search_calls": dict(sorted(Counter(t.get("search_calls", 0) for t in traces).items())),
        "latency_ms_median": statistics.median(times) if times else None,
        "latency_ms_p95": times[math.ceil(.95 * len(times)) - 1] if times else None,
        "agent_cost_usd": round(sum(costs), 4), "judge_cost_usd": round(sum(t.get("judge", {}).get("cost_usd") or 0 for t in traces), 4),
        "tokens": {k: sum(t["usage"][k] for t in traces if t.get("usage")) for k in ("input", "output", "reasoning")},
        "rows": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", choices=["basic", "advanced"], required=True)
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--name", required=True, help="configuration name (output folder)")
    ap.add_argument("--method", default="hybrid", choices=["dense", "bm25", "bm25_bigram", "hybrid", "rerank"])
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--max-steps", type=int, default=6)
    ap.add_argument("--budget", type=int, default=24000)
    ap.add_argument("--model", default="gpt-5.4-mini", choices=sorted(PRICES))
    ap.add_argument("--reasoning", default="low")
    ap.add_argument("--prompt", default="v1", choices=["v1", "v2", "v3"])
    ap.add_argument("--view-image", action="store_true")
    ap.add_argument("--cite-expand", action="store_true")
    ap.add_argument("--decompose", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", nargs="+", help="run only these query ids (debugging; not a reported run)")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--allow-test", action="store_true")
    a = ap.parse_args()
    if a.split == "test" and not a.allow_test:
        sys.exit("refusing to run test: freeze the configuration on dev first, then pass --allow-test")
    load_dotenv(ROOT / ".env")
    from openai import OpenAI
    client = OpenAI(max_retries=3, timeout=180)
    retr = Retriever()
    lock = threading.Lock()  # one embedding / rerank forward pass at a time (MPS)
    orig_search = retr.search

    def locked_search(*x, **kw):
        with lock:
            return orig_search(*x, **kw)
    retr.search = locked_search  # type: ignore[method-assign]
    cfg = AgentConfig(model=a.model, reasoning_effort=a.reasoning, method=a.method, top_k=a.top_k,
                      max_steps=a.max_steps, budget_chars=a.budget, prompt=a.prompt, view_image=a.view_image,
                      cite_expand=a.cite_expand, decompose=a.decompose)
    agent = Agent(retr, cfg, client)
    queries, gold = load(a.suite, a.split)
    queries = [q for q in queries if not a.ids or q["id"] in a.ids]
    queries = queries[:a.limit] if a.limit else queries
    out = OUT / f"{a.suite}.{a.split}.{a.name}"
    out.mkdir(parents=True, exist_ok=True)

    def one(q: dict) -> dict:
        t = agent.run(q["question"], q["id"])  # agent sees only id + question
        if not a.no_judge and t["status"] in ("answered", "abstain"):
            t["judge"] = judge(client, a.model, gold[q["id"]], t)  # gold only after the agent finished
        print(f"  {q['id']} {t['status']:8s} searches={t.get('search_calls')} {t['elapsed_ms']}ms "
              f"grade={t.get('judge', {}).get('grade')}", flush=True)
        return t

    with ThreadPoolExecutor(a.workers) as ex:
        traces = list(ex.map(one, queries))
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    meta = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "suite": a.suite, "split": a.split,
            "name": a.name, "config": cfg.__dict__, "code_commit": commit, "embedding_model": retr.emb.key,
            "label_type": "automatic proxy + LLM judge (dev selection only; not human review)"}
    (out / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=1) + "\n")
    summary = {**meta, **summarize(traces, gold, retr)}
    (out / "auto.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

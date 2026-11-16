"""Print the proxy summary tables for the frozen test runs (baseline vs chosen_B1) in report markdown."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "starter" / "results" / "agent"
f = lambda r: f"{r['n']}/{r['N']}" + (f" ({100 * r['rate']:.1f}%)" if r["rate"] is not None else "")  # noqa: E731

lines = ["| Cấu hình / suite test | Strict pass proxy | Hit@1 / Hit@3 câu gốc | Context đủ | Judge 2/1/0 | Citation trên gold | "
         "Từ chối đúng | Từ chối nhầm | Lỗi | Chi phí | p50 / p95 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
cats = {}
for name in ("baseline", "chosen_B1"):
    for suite in ("basic", "advanced"):
        p = R / f"{suite}.test.{name}" / "auto.json"
        if not p.exists():
            lines.append(f"| {name} / {suite} | (chưa chạy) |||||||||| ")
            continue
        s = json.loads(p.read_text())
        g = s["judge_grade_counts"]
        lines.append(f"| {name} / {suite} | **{f(s['proxy_strict_pass'])}** | {f(s['retrieval_hit_at_1_original'])} / "
                     f"{f(s['retrieval_hit_at_3_original'])} | {f(s['context_evidence_rate'])} | "
                     f"{g.get('2', 0)}/{g.get('1', 0)}/{g.get('0', 0)} | {f(s['citations_on_gold_evidence'])} | "
                     f"{f(s['correct_abstention'])} | {f(s['false_abstention'])} | {s['statuses'].get('error', 0)} | "
                     f"${s['agent_cost_usd']:.2f} | {s['latency_ms_median'] / 1000:.1f} / {s['latency_ms_p95'] / 1000:.1f} s |")
        if suite == "advanced":
            cats[name] = s
out = "\n".join(lines)
if "chosen_B1" in cats:
    s = cats["chosen_B1"]
    rows = s["rows"]
    out += "\n\nAdvanced test theo nhóm (cấu hình đã chọn B1, proxy; nhóm thiếu evidence tách riêng):\n\n| Nhóm | Đạt / tổng |\n|---|---|\n"
    for c in ("table", "image", "chart", "multi_hop", "text"):
        sub = [r for r in rows if r["category"] == c and r["answerable"]]
        out += f"| {c} | {sum(r['proxy_pass'] for r in sub)}/{len(sub)} |\n"
    neg = [r for r in rows if not r["answerable"]]
    out += f"| thiếu bằng chứng | {sum(r['proxy_pass'] for r in neg)}/{len(neg)} |\n"
    out += f"| **toàn bộ** | **{f(s['proxy_strict_pass'])}** (ngưỡng bonus ≥ 63/70, cần nhãn người chấm) |\n"
print(out)
if len(sys.argv) > 1:  # write into the report placeholder
    rp = Path(sys.argv[1])
    rp.write_text(rp.read_text().replace("TEST_RESULTS_PLACEHOLDER", out))

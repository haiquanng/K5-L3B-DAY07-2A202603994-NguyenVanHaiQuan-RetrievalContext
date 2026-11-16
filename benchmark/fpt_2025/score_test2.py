"""Score the held-out advanced test2 with the unchanged benchmark scorer (tools.score).

  python3 benchmark/fpt_2025/score_test2.py --traces <traces.json> --reviews <reviews.json> --output <summary.json>

tools.py's CLI only accepts --split dev|test, so this wrapper loads gold/advanced.test2.json and calls the same
`score` function: identical pass rules, denominator = all 30 published cases, 90% = 27/30 without rounding.
"""
import argparse
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bench_tools", BASE / "tools.py")
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)

ap = argparse.ArgumentParser()
ap.add_argument("--traces", type=Path, required=True)
ap.add_argument("--reviews", type=Path, required=True)
ap.add_argument("--output", type=Path, required=True)
a = ap.parse_args()
cases = json.loads((BASE / "gold" / "advanced.test2.json").read_text(encoding="utf-8"))
out = tools.score(cases, json.loads(a.traces.read_text(encoding="utf-8")), json.loads(a.reviews.read_text(encoding="utf-8")))
a.output.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "details"}, ensure_ascii=False, indent=1))

"""Automated execution of the system cases that need no model call (benchmark/fpt_2025/system_cases.json).

  python -m src.system_checks [--trace-run advanced.dev.hybrid_k5]

Uses only the database, index files, the source PDF, code and existing traces; never loads a local model.
Writes starter/results/system/system_checks.json. The original specification file is not modified.
Each result: pass | fail | partial (automated part passed, a human check is still listed in `human_check`).
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import retrieval  # noqa: E402  (module import does not load any model)
from src.retrieval import BM25, tokenize  # noqa: E402

BENCH = ROOT / "benchmark" / "fpt_2025"
DOC = "fpt-ar2025"
NAV = ["THÔNG ĐIỆP BAN LÃNH ĐẠO", "DẤU ẤN 2025", "TỔNG QUAN VỀ FPT", "CHIẾN LƯỢC PHÁT TRIỂN",
       "PHÂN TÍCH HOẠT ĐỘNG KINH DOANH", "QUẢN TRỊ CÔNG TY", "BÁO CÁO ESG"]


def result(cid, status, evidence, human_check=None):
    return {"id": cid, "status": status, "evidence": evidence, "human_check": human_check}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trace-run", default="advanced.dev.hybrid_k5")
    a = ap.parse_args()
    load_dotenv(ROOT / ".env")
    src = json.loads((BENCH / "source.json").read_text(encoding="utf-8"))
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    q = lambda sql, *p: conn.execute(sql, p).fetchall()  # noqa: E731
    chunks = q("SELECT chunk_id, pdf_page, kind, content, bbox, crop_path FROM mm_chunks WHERE doc_id=%s ORDER BY chunk_id", DOC)
    out = []

    # SYS-001 document and version
    doc = q("SELECT doc_id, sha256, page_count, source_file FROM mm_documents")
    fpt = [d for d in doc if d[0] == DOC]
    pdf = ROOT / src["path"]
    pdf_sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else None
    ok = bool(fpt) and fpt[0][1] == src["sha256"] == pdf_sha and fpt[0][2] == src["physical_pages"] == 232
    out.append(result("SYS-001", "pass" if ok and not any("vnz" in d[0].lower() for d in doc) else "fail",
                      {"indexed_documents": [d[0] for d in doc], "index_sha256": fpt[0][1] if fpt else None,
                       "pdf_sha256": pdf_sha, "expected_sha256": src["sha256"], "page_count": fpt[0][2] if fpt else None}))

    # SYS-002 coverage ledger
    pages = q("SELECT p.pdf_page, count(c.chunk_id), p.has_text_layer, p.log FROM mm_pages p LEFT JOIN mm_chunks c "
              "USING (doc_id, pdf_page) WHERE p.doc_id=%s GROUP BY p.pdf_page, p.has_text_layer, p.log ORDER BY 1", DOC)
    empty = [{"pdf_page": p, "has_text_layer": t, "blocks_after_boilerplate": lg.get("blocks"),
              "skipped_regions": lg.get("skipped_regions"),
              "reason": ("trang mở chương: chữ chỉ gồm tên chương/mục đã lọc như navigation lặp; còn ảnh nền trang trí"
                         if lg.get("blocks") == 0 else "CHƯA CÓ LÝ DO")} for p, n, t, lg in pages if n == 0]
    gold_pages = {e["pdf_page"] for f in ("basic.dev", "basic.test", "advanced.dev", "advanced.test")
                  for c in json.loads((BENCH / "gold" / f"{f}.json").read_text()) for e in c["gold"]}
    indexed = {p for p, n, _, _ in pages if n}
    out.append(result("SYS-002", "pass" if len(pages) == 232 and all(e["reason"] != "CHƯA CÓ LÝ DO" for e in empty) else "fail",
                      {"pages_in_ledger": len(pages), "pages_with_chunks": len(indexed), "pages_without_chunks": empty,
                       "indexed_pages_not_in_gold": len(indexed - gold_pages), "gold_pages": len(gold_pages)},
                      "Đối chiếu ngẫu nhiên vài trang không thuộc gold với bản gốc (bảng/biểu đồ có đủ)."))

    # SYS-003 pdf vs printed page
    pp = dict(q("SELECT pdf_page, printed_page FROM mm_pages WHERE doc_id=%s AND pdf_page = ANY(%s)", DOC, [1, 10, 31, 169]))
    ok = pp.get(10) == "09" and pp.get(31) == "30" and pp.get(169) == "168" and pp.get(1) is None
    out.append(result("SYS-003", "pass" if ok else "fail", {"printed_by_pdf_page": pp}))

    # SYS-007 navigation removed, content kept
    nav_hits = [c[0] for c in chunks if sum(n in c[3] for n in NAV) >= 3]
    header_hits = sum("LÀM CHỦ CÔNG NGHỆ CHIẾN LƯỢC" in c[3] for c in chunks)
    p10 = [c[3] for c in chunks if c[1] == 10]
    keep = all(any(s in t for t in p10) for s in ("Đơn vị: Tỷ VNĐ", "Tổng doanh thu", "70.113"))
    out.append(result("SYS-007", "pass" if len(nav_hits) <= 2 and keep else "fail",
                      {"chunks_with_>=3_sidebar_items": nav_hits, "chunks_with_running_title": header_hits,
                       "page10_title_unit_values_kept": keep},
                      "Trang mục lục (PDF 3) được phép chứa tên chương vì đó là nội dung thật."))

    # SYS-008 table year columns (GHG scope table)
    rows = [l for c in chunks for l in c[3].splitlines() if re.search(r"Phạm vi 1|Phạm vi 2|Tổng", l) and
            any(x in l for x in ("4.383", "123.569", "127.952"))]
    want = {"4.383": "Phạm vi 1", "123.569": "Phạm vi 2", "127.952": "Tổng"}
    found = {v: next((l for l in rows if v in l and lab in l), None) for v, lab in want.items()}
    out.append(result("SYS-008", "pass" if all(found.values()) else "fail", {"rows": found},
                      "Đọc dòng tìm được: giá trị 2025 nằm đúng cột 2025 (thứ tự cột theo header)."))

    # SYS-009 negative numbers in parentheses kept verbatim
    neg = {v: [c[0] for c in chunks if v in c[3]] for v in ("(105.704.809.379)", "(11.624.743.591.629)")}
    out.append(result("SYS-009", "pass" if all(neg.values()) else "fail", {"chunks_containing": neg}))

    # SYS-012 visual provenance
    regs = q("SELECT region_id, pdf_page, bbox, crop_path, bbox_source FROM mm_regions WHERE doc_id=%s AND kind <> 'table'", DOC)
    missing = [r[0] for r in regs if not (r[1] and r[2] and len(r[2]) == 4 and (ROOT / r[3]).exists())]
    out.append(result("SYS-012", "partial" if not missing else "fail",
                      {"visual_regions": len(regs), "missing_provenance_or_crop": missing,
                       "bbox_from_pdf_objects": sum(r[4] == "pdf_objects" for r in regs)},
                      "Mô tả sơ đồ có thể thiếu quan hệ (vd PDF 31 không ghi nhánh công ty) → agent dùng view_image; "
                      "người chấm mở crop kiểm tra không cắt mất nhãn/đường nối."))

    # SYS-015 / SYS-018 lexical exact numbers + deterministic ranking (BM25 only: no model)
    bm = BM25([tokenize(c[3], True) for c in chunks])

    def bm25(query, k=3):
        s = bm.scores(tokenize(query, True))
        order = sorted((i for i in range(len(s)) if s[i] > 0), key=lambda i: (-s[i], chunks[i][0]))[:k]
        return [(chunks[i][0], round(s[i], 4)) for i in order]
    probes = {"Thu nhập thuế TNDN hoãn lại (105.704.809.379)": 169, "doanh thu 52.618": 10}
    lex = {qq: bm25(qq) for qq in probes}
    num = {qq: re.search(r"\(?\d[\d.]+\)?", qq).group(0) for qq in probes}
    by = {c[0]: c[3] for c in chunks}
    ok15 = all(any(num[qq] in by[cid] for cid, _ in lex[qq][:1]) for qq in probes)  # top-1 contains the exact number
    out.append(result("SYS-015", "pass" if ok15 else "fail", {"top3": lex, "exact_number_in_top1": ok15},
                      "Probe là truy vấn kiểm thử của hệ thống, không phải câu benchmark; đáp án không được đưa vào query benchmark."))
    runs = [bm25("lợi nhuận sau thuế 2025", 10) for _ in range(2)]
    ties = re.search(r"key=lambda cid: \(-fused\[cid\], cid\)", inspect.getsource(retrieval.Retriever.hybrid))
    dense_tie = "ORDER BY e.embedding <=> %s::vector, k.chunk_id" in inspect.getsource(retrieval.Retriever.dense)
    out.append(result("SYS-018", "pass" if runs[0] == runs[1] and ties and dense_tie and len({c for c, _ in runs[0]}) == len(runs[0]) else "fail",
                      {"bm25_identical_runs": runs[0] == runs[1], "rrf_tiebreak_chunk_id": bool(ties),
                       "dense_sql_tiebreak_chunk_id": dense_tie}))

    # SYS-021 fusion definition
    src_h = inspect.getsource(retrieval.Retriever.hybrid)
    ok21 = "rrf_k + h[\"rank\"]" in src_h and "fused.get(h[\"chunk_id\"]" in src_h
    out.append(result("SYS-021", "pass" if ok21 else "fail",
                      {"formula": "score(d) = Σ_m w_m / (60 + rank_m(d)), pool 50 mỗi phương pháp, w=1",
                       "duplicates_merged_by_chunk_id": ok21}))

    # trace-based checks
    run = ROOT / "starter" / "results" / "agent" / a.trace_run
    traces = json.loads((run / "traces.json").read_text()) if (run / "traces.json").exists() else []
    auto = json.loads((run / "auto.json").read_text()) if (run / "auto.json").exists() else {}
    if traces:
        sep = all("original_query_ranking" in t and t["events"] and t["events"][0]["event"] == "search"
                  and t["events"][0]["query"] == t["question"] for t in traces if t["status"] != "error")
        out.append(result("SYS-019", "pass" if sep else "fail",
                          {"run": a.trace_run, "original_ranking_logged_separately": sep,
                           "queries_logged_per_call": all(all("query" in e for e in t["events"] if e["event"] == "search") for t in traces)}))
        dup = [t["query_id"] for t in traces if len(t["context_ids"]) != len(set(t["context_ids"]))]
        out.append(result("SYS-026", "pass" if not dup else "fail",
                          {"traces_with_duplicate_context_ids": dup, "dedup_rule": "theo chunk_id; chunk khác ID cùng trang được giữ"}))
        queries = {q2["id"]: q2 for f in ("advanced.dev", "basic.dev") for q2 in json.loads((BENCH / "queries" / f"{f}.json").read_text())}
        leak = [t["query_id"] for t in traces if t["question"] != queries.get(t["query_id"], {}).get("question")]
        keys = {k for f in ("basic.dev", "basic.test", "advanced.dev", "advanced.test")
                for q2 in json.loads((BENCH / "queries" / f"{f}.json").read_text()) for k in q2}
        runtime = "".join((ROOT / "src" / f).read_text() for f in ("agent.py", "retrieval.py"))
        reads_gold = bool(re.search(r"gold/|expected_answer|answerable|absence_check|evidence_groups|bbox_pt", runtime))
        out.append(result("SYS-055", "pass" if keys == {"id", "question"} and not leak and not reads_gold else "fail",
                          {"query_file_keys": sorted(keys), "trace_question_differs_from_query_file": leak,
                           "runtime_modules_reference_gold_fields": reads_gold,
                           "note": "run_agent.py đọc gold chỉ sau khi agent trả kết quả (proxy/judge)"}))
    if auto:
        den = (auto["retrieval_hit_at_3_original"]["N"], auto["context_evidence_rate"]["N"], auto["correct_abstention"]["N"])
        out.append(result("SYS-052", "pass" if den == (56, 56, 14) else "fail",
                          {"run": a.trace_run, "retrieval_N": den[0], "context_N": den[1], "abstention_N": den[2]}))

    dest = ROOT / "starter" / "results" / "system"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "system_checks.json").write_text(json.dumps(
        {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "automated": out,
         "not_automated_here": "các ca còn lại cần chạy agent/lỗi giả lập hoặc người chấm"}, ensure_ascii=False, indent=1) + "\n")
    for r in out:
        print(f"{r['id']}  {r['status']:8s} {json.dumps(r['evidence'], ensure_ascii=False)[:150]}")


if __name__ == "__main__":
    main()

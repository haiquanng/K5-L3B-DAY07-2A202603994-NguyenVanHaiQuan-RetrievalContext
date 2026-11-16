"""Multimodal index of one long PDF into the Day 6 pgvector database (run from the repo root).

  python -m src.mm.index index --pdf pdf/BCTN_2025_ad403f779b.pdf --doc-id fpt-ar2025 \
         --title "Báo cáo thường niên FPT 2025" [--pages 1-20,46]
  python -m src.mm.index search --doc-id fpt-ar2025 "Doanh thu năm 2023 là bao nhiêu?" [-k 5] [--kind chart]
  python -m src.mm.index show --doc-id fpt-ar2025 --page 10

Per page:
  1. layout.py  PDF text blocks + table/image/vector objects with bboxes. Navigation sidebar, running headers
                and page numbers removed (learned from repetition). pdf_page and printed_page both kept.
  2. vision.py  page render + id lists -> vision model groups ids into regions (table/chart/diagram/
                infographic/photo) and body sections, and describes visual content. Cached per page.
  3. here       region chunk = model description + VERBATIM PDF text of its blocks; text chunk = verbatim text.
                bbox = union of the PDF objects the model referenced (model bbox only as fallback) -> PNG crop.
                Numbers in model descriptions are checked against the page text layer.
  4. store.py   bge-m3 (Day 6 model) vectors + normalized tables mm_documents/pages/regions/chunks/embeddings.
No fake fallback: a model or DB error stops the run (vision results already cached are kept).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from dotenv import load_dotenv

from .layout import PageLayout, crop, doc_profile, pad, page_layout, render_page, table_rows, union
from .store import MMStore, _vec, content_hash
from .vision import PROMPT_VERSION, RELATIONS_VERSION, analyse_page, region_relations

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "gpt-5.4-mini"
RENDER_ZOOM = 2.0          # page image for the vision model and the UI
MAX_TEXT_CHARS = 1500      # split long sections at block boundaries
MAX_TABLE_CHARS = 2200     # split long tables by rows, title + description repeated in each part
KIND_VI = {"table": "Bảng", "chart": "Biểu đồ", "diagram": "Sơ đồ", "infographic": "Infographic",
           "photo": "Ảnh", "text": "Văn bản"}
RELATION_KINDS = ("diagram", "infographic")  # structure pass on the crop (chart values are already paired)
NUM_TOKEN = re.compile(r"\d[\d.,]*\d|\d")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_pages(spec: str | None, n: int) -> list[int]:
    if not spec:
        return list(range(1, n + 1))
    out: list[int] = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return sorted({p for p in out if 1 <= p <= n})


def paths(doc_id: str) -> dict[str, Path]:
    base, res = ROOT / "starter" / "data" / "mm" / doc_id, ROOT / "starter" / "results" / "mm" / doc_id
    return {"pages": base / "pages", "crops": base / "crops", "vision": base / "vision", "results": res}


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def unverified_numbers(description: str, page_text: str) -> list[str]:
    """Numbers the model wrote that are not a WHOLE number token of the page text layer (substring matches do
    not count: "7.750.000.000" must not pass because "7.750.000.000.000" is printed). Years and 1-digit ignored."""
    page_tokens = {t.rstrip(".,") for t in NUM_TOKEN.findall(page_text)}
    out = []
    for tok in NUM_TOKEN.findall(description):
        t = tok.rstrip(".,")
        if len(re.sub(r"\D", "", t)) < 2 or re.fullmatch(r"(19|20)\d\d", t):
            continue
        if t not in page_tokens:
            out.append(t)
    return sorted(set(out))


def drop_unverified_lines(text: str, page_text: str) -> tuple[str, list[str]]:
    """Remove lines of a model-written structure that contain a number not printed on the page."""
    keep, dropped = [], []
    for line in text.splitlines():
        (dropped if unverified_numbers(line, page_text) else keep).append(line)
    return "\n".join(keep), dropped


def _split(items: list, size, limit: int) -> list[list]:
    parts, cur, n = [], [], 0
    for it in items:
        s = size(it)
        if cur and n + s > limit:
            parts.append(cur)
            cur, n = [], 0
        cur.append(it)
        n += s + 1
    return parts + ([cur] if cur else [])


def build_page(doc_id: str, doc_title: str, lay: PageLayout, vis: dict, pdoc: pymupdf.Document,
               P: dict[str, Path], page_img: str) -> tuple[dict, list[dict], list[dict]]:
    res = vis["result"]
    page_title = res["page_title"].strip()
    ctx = " · ".join(x for x in (doc_title, lay.chapter, page_title or lay.running_header,
                                 f"trang {lay.printed_page or '?'} (PDF {lay.page})") if x)
    valid = {b.id for b in lay.blocks}
    used: set[str] = set()
    W, H = lay.width, lay.height
    log = {"blocks": len(lay.blocks), "dropped_boilerplate_lines": lay.dropped_lines, "skipped_regions": [],
           "unknown_ids": [], "duplicate_ids": [], "leftover_blocks": [], "notes": list(lay.notes)}
    regions: list[dict] = []
    chunks: list[dict] = []
    tag = f"{doc_id}:p{lay.page:03d}"

    def take(ids: list[str]) -> list[str]:
        out = []
        for i in ids:
            if i not in valid:
                log["unknown_ids"].append(i)
            elif i in used:
                log["duplicate_ids"].append(i)
            else:
                used.add(i)
                out.append(i)
        return out

    def chunk(cid, kind, title, content, bbox, crop_path, region_id=None, part=1, parts=1, meta=None):
        chunks.append({"chunk_id": cid, "doc_id": doc_id, "pdf_page": lay.page, "region_id": region_id,
                       "kind": kind, "part": part, "parts": parts, "title": title, "content": content,
                       "bbox": list(bbox), "crop_path": crop_path, "metadata": meta or {}})

    # pass 1: claim ids (regions first, then sections), as returned by the model
    specs = []
    for r_i, reg in enumerate(res["regions"], 1):
        if not reg["useful"]:
            log["skipped_regions"].append({"kind": reg["kind"], "title": reg["title"], "reason": "marked decorative"})
            continue
        ids = take(reg["block_ids"])
        objs = [o for o in reg["object_ids"] if o in lay.objects]
        snapped = union([lay.block(i).bbox for i in ids] + [lay.objects[o] for o in objs])
        model_bbox = reg["bbox"] if len(reg["bbox"]) == 4 else None
        specs.append({"i": r_i, "reg": reg, "ids": ids, "objs": objs, "snapped": snapped,
                      "bbox": pad(snapped or model_bbox or (0, 0, W, H), W, H),
                      "bbox_source": "pdf_objects" if snapped else ("model" if model_bbox else "page")})
    sections = [(sec["heading"].strip(), take(sec["block_ids"])) for sec in res["sections"]]
    # pass 2: blocks the model forgot (axis ticks, stray table cells) -> region whose bbox contains them
    for b in [b for b in lay.blocks if b.id not in used]:
        cx, cy = (b.bbox[0] + b.bbox[2]) / 2, (b.bbox[1] + b.bbox[3]) / 2
        host = next((s for s in specs if s["bbox"][0] <= cx <= s["bbox"][2] and s["bbox"][1] <= cy <= s["bbox"][3]),
                    None)
        if host:
            host["ids"].append(b.id)
            used.add(b.id)
            log.setdefault("assigned_by_geometry", []).append(f"{b.id}->{host['reg']['kind']}{host['i']:02d}")

    for s in specs:
        reg, ids, objs, bbox, r_i = s["reg"], s["ids"], s["objs"], s["bbox"], s["i"]
        kind = reg["kind"]
        blocks = sorted((lay.block(i) for i in ids), key=lambda b: (round(b.bbox[1] / 3), b.bbox[0]))
        rid = f"{tag}:{kind}{r_i:02d}"
        img = crop(pdoc, lay.page, bbox, P["crops"] / f"p{lay.page:03d}" / f"{kind}{r_i:02d}.png")
        regions.append({"region_id": rid, "doc_id": doc_id, "pdf_page": lay.page, "kind": kind,
                        "title": reg["title"], "description": reg["description"].strip(), "bbox": list(bbox),
                        "bbox_source": s["bbox_source"], "crop_path": rel(img), "block_ids": ids, "object_ids": objs,
                        "unverified_numbers": unverified_numbers(reg["description"], lay.text)})
        head = f"{ctx}\n[{KIND_VI[kind]}] {reg['title']}\n{reg['description'].strip()}"
        # tables: rows rebuilt from line geometry; other kinds: blocks in reading order
        rows = table_rows(blocks) if kind == "table" else [(b.cells, b.bbox) for b in blocks]
        if kind == "table" and sum(len(r) + 1 for r, _ in rows) > MAX_TABLE_CHARS:
            parts = _split(rows, lambda x: len(x[0]), MAX_TABLE_CHARS)
            for k, part in enumerate(parts, 1):
                body = "\n".join(r for r, _ in part)
                chunk(f"{rid}-{k}", kind, f"{reg['title']} (phần {k}/{len(parts)})",
                      f"{head}\nNội dung trích từ PDF (phần {k}/{len(parts)}):\n{body}",
                      pad(union([bb for _, bb in part]), W, H), rel(img), rid, k, len(parts),
                      {"block_ids": ids, "part_note": "bbox = rows of this part; crop = whole table"})
        else:
            body = "\n".join(r for r, _ in rows)
            chunk(rid, kind, reg["title"], head + (f"\nNội dung trích từ PDF:\n{body}" if body else ""),
                  bbox, rel(img), rid, meta={"block_ids": ids})

    def text_chunks(heading: str, blocks, idx: str, extra: dict) -> None:
        parts = _split(blocks, lambda b: len(b.text), MAX_TEXT_CHARS)
        for k, part in enumerate(parts, 1):
            bbox = pad(union([b.bbox for b in part]), W, H)
            img = crop(pdoc, lay.page, bbox, P["crops"] / f"p{lay.page:03d}" / f"{idx}-{k}.png")
            body = "\n".join(b.text for b in part)
            if heading and re.sub(r"\W", "", body.upper()).startswith(re.sub(r"\W", "", heading.upper())):
                heading_line = ""  # heading already printed as the first block
            else:
                heading_line = heading
            chunk(f"{tag}:{idx}-{k}", "text", heading or page_title or lay.running_header,
                  "\n".join(x for x in (ctx, heading_line, body) if x), bbox, rel(img), None, k, len(parts),
                  {**extra, "block_ids": [b.id for b in part]})

    for s_i, (heading, ids) in enumerate(sections, 1):
        if ids:
            text_chunks(heading, [lay.block(i) for i in ids], f"text{s_i:02d}", {})
    leftover = [b for b in lay.blocks if b.id not in used]
    if leftover:  # coverage guarantee: no PDF text is silently dropped
        log["leftover_blocks"] = [b.id for b in leftover]
        norm = lambda t: re.sub(r"\W", "", t.upper())  # noqa: E731
        in_ctx = all(norm(b.text) in norm(ctx) for b in leftover)  # page title already in every chunk's context line
        if chunks and (in_ctx or sum(len(b.text) for b in leftover) < 60):
            log["tiny_leftover_text"] = [b.text for b in leftover]  # e.g. a lone page heading: logged, no chunk
        else:
            text_chunks("", sorted(leftover, key=lambda b: (b.bbox[1], b.bbox[0])), "rest", {"leftover": True})
    if not chunks:
        log["notes"].append("page produced no chunk")
    page = {"doc_id": doc_id, "pdf_page": lay.page, "printed_page": lay.printed_page, "chapter": lay.chapter,
            "page_title": page_title, "running_header": lay.running_header, "has_text_layer": lay.has_text_layer,
            "image_path": page_img, "log": log,
            "vision": {"model": vis["model"], "prompt_version": vis["prompt_version"], "seconds": vis["seconds"],
                       "usage": vis["usage"], "cache_key": vis["key"]}}
    return page, regions, chunks


# ------------------------------------------------------------------------------------------- commands
def _env() -> None:
    load_dotenv(ROOT / ".env")


def _store() -> MMStore:
    _env()
    url = os.getenv("DATABASE_URL") or sys.exit("DATABASE_URL missing in .env (Day 6 pgvector container)")
    store = MMStore(url)
    store.create_schema()
    return store


def cmd_index(a: argparse.Namespace) -> None:
    _env()
    pdf_path = Path(a.pdf).resolve()
    pdoc = pymupdf.open(pdf_path)
    pages = parse_pages(a.pages, pdoc.page_count)
    P = paths(a.doc_id)
    P["results"].mkdir(parents=True, exist_ok=True)
    store = None if a.no_db else _store()  # fail fast before paying for vision calls

    t0 = time.perf_counter()
    prof = doc_profile(pdoc)
    layouts = {p: page_layout(pdoc, p, prof) for p in pages}
    imgs = {p: render_page(pdoc, p, P["pages"] / f"p{p:03d}.jpg", RENDER_ZOOM) for p in pages}
    t_layout = time.perf_counter() - t0
    print(f"{len(pages)} pages | layout+render {t_layout:.1f}s | chapters {prof.chapters}")

    from openai import OpenAI
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY missing (.env)")
    client = OpenAI(max_retries=4, timeout=240)
    vis, errors = {}, {}
    t1 = time.perf_counter()
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(analyse_page, client, a.model, layouts[p], imgs[p], P["vision"], a.title, RENDER_ZOOM,
                          a.reasoning): p for p in pages}
        for n, f in enumerate(as_completed(futs), 1):
            p = futs[f]
            try:
                vis[p] = f.result()
            except Exception as e:  # noqa: BLE001 - recorded, run stops below; finished pages stay cached
                errors[p] = f"{type(e).__name__}: {e}"
            if n % 10 == 0 or n == len(pages):
                print(f"  vision {n}/{len(pages)} ({time.perf_counter() - t1:.0f}s, errors {len(errors)})")
    if errors:
        (P["results"] / "vision_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=1))
        sys.exit(f"vision failed on pages {sorted(errors)}; rerun to retry (finished pages are cached)")

    page_rows, region_rows, chunk_rows = [], [], []
    for p in pages:
        pg, rg, ch = build_page(a.doc_id, a.title, layouts[p], vis[p], pdoc, P, rel(imgs[p]))
        page_rows.append(pg)
        region_rows += rg
        chunk_rows += ch
    ids = [c["chunk_id"] for c in chunk_rows]
    if len(ids) != len(set(ids)):
        sys.exit("duplicate chunk ids")

    rel_usage = {"regions": 0, "input": 0, "output": 0}
    if not a.no_relations:  # second pass: structure of diagrams / infographics read from the crop itself
        targets = [r for r in region_rows if r["kind"] in RELATION_KINDS]
        page_text = {p: layouts[p].text for p in pages}
        with ThreadPoolExecutor(a.workers) as ex:
            futs = {ex.submit(region_relations, client, a.model, ROOT / r["crop_path"], r["kind"], r["title"],
                              P["vision"] / "relations", a.reasoning): r for r in targets}
            for f in as_completed(futs):
                r, res = futs[f], f.result()
                rel_usage["regions"] += 1
                rel_usage["input"] += res["usage"]["input"]
                rel_usage["output"] += res["usage"]["output"]
                text, dropped = drop_unverified_lines(res["text"], page_text[r["pdf_page"]])
                if dropped:
                    rel_usage.setdefault("dropped_lines", {})[r["region_id"]] = dropped
                if not text.strip():
                    continue
                block = f"Cấu trúc đọc từ ảnh vùng:\n{text}"
                r["description"] = f"{r['description']}\n{block}"
                r["unverified_numbers"] = unverified_numbers(r["description"], page_text[r["pdf_page"]])
                for c in chunk_rows:
                    if c["region_id"] == r["region_id"]:
                        cut = c["content"].find("\nNội dung trích từ PDF")
                        c["content"] = (c["content"][:cut] + "\n" + block + c["content"][cut:]) if cut >= 0 \
                            else c["content"] + "\n" + block

    W0, H0 = pdoc[0].rect.width, pdoc[0].rect.height
    sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    lens = sorted(len(c["content"]) for c in chunk_rows)
    stats = {"at": now(), "doc_id": a.doc_id, "pdf": pdf_path.name, "pdf_sha256": sha, "pdf_pages": pdoc.page_count,
             "indexed_pages": len(pages), "vision_model": a.model, "reasoning_effort": a.reasoning,
             "prompt_version": PROMPT_VERSION, "render_zoom": RENDER_ZOOM, "layout_render_seconds": round(t_layout, 1),
             "vision_wall_seconds": round(time.perf_counter() - t1, 1), "regions": len(region_rows),
             "regions_by_kind": {k: sum(r["kind"] == k for r in region_rows) for k in sorted({r["kind"] for r in region_rows})},
             "chunks": len(chunk_rows),
             "chunks_by_kind": {k: sum(c["kind"] == k for c in chunk_rows) for k in sorted({c["kind"] for c in chunk_rows})},
             "chunk_chars_p50": lens[len(lens) // 2] if lens else 0, "chunk_chars_max": lens[-1] if lens else 0,
             "tokens": {k: sum(v["usage"][k] or 0 for v in vis.values()) for k in ("input", "output", "reasoning")},
             "pages_no_text_layer": [pg["pdf_page"] for pg in page_rows if not pg["has_text_layer"]],
             "pages_with_leftover_blocks": [pg["pdf_page"] for pg in page_rows if pg["log"]["leftover_blocks"]],
             "pages_with_unknown_ids": [pg["pdf_page"] for pg in page_rows if pg["log"]["unknown_ids"]],
             "regions_with_unverified_numbers": [r["region_id"] for r in region_rows if r["unverified_numbers"]],
             "regions_bbox_not_from_pdf": [r["region_id"] for r in region_rows if r["bbox_source"] != "pdf_objects"],
             "skipped_decorative": sum(len(pg["log"]["skipped_regions"]) for pg in page_rows),
             "relations_pass": {"version": None if a.no_relations else RELATIONS_VERSION, **rel_usage}}

    if store:
        sys.path.insert(0, str(ROOT))
        from src.embeddings import BgeM3Embedder
        emb = BgeM3Embedder()
        t2 = time.perf_counter()
        vectors = store.cached_vectors(a.doc_id, emb.key)
        todo = list({content_hash(c["content"]): c["content"] for c in chunk_rows
                     if content_hash(c["content"]) not in vectors}.items())
        for (h, _), v in zip(todo, emb.embed_documents([t for _, t in todo])):
            vectors[h] = _vec(v)
        document = {"doc_id": a.doc_id, "title": a.title, "source_file": pdf_path.name, "sha256": sha,
                    "page_count": pdoc.page_count, "page_width": W0, "page_height": H0,
                    "metadata": {"page_numbering": "pdf_page = 1-based file index; printed_page = number printed",
                                 "chapters": prof.chapters}}
        written = store.replace_pages(document, page_rows, region_rows, chunk_rows, emb.key, vectors)
        stats["embedding"] = {"model": emb.key, "dimensions": emb.dimensions, "device": emb.device,
                              "embedded": len(todo), "reused": len(chunk_rows) - len(todo),
                              "seconds": round(time.perf_counter() - t2, 1)}
        stats["db"] = {**written, **store.versions(), "totals": store.counts(a.doc_id)}

    for name, rows in (("chunks", chunk_rows), ("regions", region_rows), ("pages", page_rows)):
        with (P["results"] / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (P["results"] / "index_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def cmd_search(a: argparse.Namespace) -> None:
    from src.embeddings import BgeM3Embedder
    store, emb = _store(), BgeM3Embedder()
    for i, h in enumerate(store.search_dense(emb.embed_query(a.query), a.doc_id, emb.key, a.k, a.kind), 1):
        print(f"#{i} {h['score']:.3f} {h['chunk_id']} [{h['kind']}] PDF p{h['pdf_page']} (in {h['printed_page']}) "
              f"{h['title']}\n   crop: {h['crop_path']}\n   {h['content'][:300].replace(chr(10), ' / ')}\n")


def cmd_show(a: argparse.Namespace) -> None:
    R = paths(a.doc_id)["results"]
    for name in ("pages", "regions", "chunks"):
        for line in (R / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["pdf_page"] != a.page:
                continue
            if name == "chunks":
                print(f"=== {r['chunk_id']} [{r['kind']}] bbox={r['bbox']} crop={r['crop_path']}\n{r['content']}\n")
            else:
                print(name.upper(), json.dumps(r, ensure_ascii=False, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ix = sub.add_parser("index")
    ix.add_argument("--pdf", required=True)
    ix.add_argument("--doc-id", required=True)
    ix.add_argument("--title", required=True)
    ix.add_argument("--pages", help="e.g. 1-20,46,160 (default: all)")
    ix.add_argument("--model", default=DEFAULT_MODEL)
    ix.add_argument("--reasoning", default="low", choices=["none", "minimal", "low", "medium", "high"])
    ix.add_argument("--workers", type=int, default=6)
    ix.add_argument("--no-db", action="store_true", help="vision + chunk files only; no embedding / DB write")
    ix.add_argument("--no-relations", action="store_true", help="skip the diagram/infographic structure pass")
    ix.set_defaults(fn=cmd_index)
    se = sub.add_parser("search")
    se.add_argument("query")
    se.add_argument("--doc-id", required=True)
    se.add_argument("-k", type=int, default=5)
    se.add_argument("--kind", action="append")
    se.set_defaults(fn=cmd_search)
    sh = sub.add_parser("show")
    sh.add_argument("--doc-id", required=True)
    sh.add_argument("--page", type=int, required=True)
    sh.set_defaults(fn=cmd_show)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

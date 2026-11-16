"""Source-image candidates for interactive chat; no extra model calls or benchmark changes.

Portraits must have a named caption, the same name in PDF-extracted text, and a name match
in this turn's cited evidence. Other figures must be cited directly. Attachments are kept
separate from the model's context/citations so their lookup cannot inflate retrieval metrics.
"""
from __future__ import annotations

import re
import struct
import unicodedata
from collections import defaultdict
from pathlib import Path


def normalized(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.casefold()).replace("đ", "d")
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in plain if not unicodedata.combining(c))))


def mentions(text: str, name: str) -> bool:
    return f" {normalized(name)} " in f" {normalized(text)} "


def portrait_name(chunk: dict) -> str | None:
    title = chunk.get("title") or ""
    match = re.fullmatch(r"(?:Ảnh chân dung\s+)?(?:Ông|Bà)\s+(.+?)(?:\s+[–—-]\s+.*|,.*)?",
                         title.strip(), re.IGNORECASE)
    if not match or "chan dung" not in normalized(chunk.get("content", "")):
        return None
    name = match[1].strip()
    words = normalized(name).split()
    # Reject group captions, roles and partial names; do not infer identity from faces.
    if (not 2 <= len(words) <= 6 or any(w in {"va", "ong", "ba", "chu", "tich", "giam", "doc"}
                                       or w.isdigit() for w in words)):
        return None
    return name


def png_asset(chunk: dict, project_root: Path, asset_root: Path) -> tuple[Path, int, int] | None:
    if not chunk.get("crop_path"):
        return None
    try:
        path = (project_root / chunk["crop_path"]).resolve()
        if not path.is_relative_to(asset_root.resolve()):
            return None
        with path.open("rb") as file:
            header = file.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR" or len(header) < 24:
            return None
        width, height = struct.unpack(">II", header[16:24])
        return (path, width, height) if width and height else None
    except (OSError, ValueError, RuntimeError):
        return None


def select_answer_images(trace: dict, chunks: list[dict], *, project_root: Path,
                         asset_root: Path, doc_id: str, limit: int = 3) -> list[dict]:
    if trace.get("status") != "answered" or limit <= 0:
        return []
    by_id = {c["chunk_id"]: c for c in chunks if c["chunk_id"].startswith(doc_id + ":")}
    cited = {c["chunk_id"]: c for c in trace.get("context", [])
             if c["chunk_id"] in trace.get("citations", []) and c["chunk_id"] in by_id}
    if not cited:
        return []

    # Standalone text or the original PDF blocks retained inside an image region.
    # A vision-generated caption alone is insufficient identity evidence.
    page_text = defaultdict(list)
    for chunk in by_id.values():
        content = chunk.get("content", "")
        original = content if chunk["kind"] == "text" else content.partition("Nội dung trích từ PDF:\n")[2]
        if original:
            page_text[chunk["pdf_page"]].append((chunk["chunk_id"], original))

    candidates = []
    for chunk in by_id.values():
        if chunk["kind"] != "photo" or not (name := portrait_name(chunk)):
            continue
        if not mentions(trace.get("answer", ""), name):
            continue
        support = [cid for cid, hit in cited.items() if mentions(hit.get("text", ""), name)]
        identity = [cid for cid, text in page_text[chunk["pdf_page"]] if mentions(text, name)]
        if support and identity:
            candidates.append((chunk, "portrait_name", name, support, identity))
    # Prefer a directly cited portrait, then a portrait on the cited biography's page.
    cited_pages = {hit["pdf_page"] for hit in cited.values()}
    candidates.sort(key=lambda c: (c[0]["chunk_id"] not in cited,
                                    c[0]["pdf_page"] not in cited_pages, c[0]["chunk_id"]))
    for cid in dict.fromkeys(trace.get("citations", [])):
        chunk = by_id.get(cid)
        if cid in cited and chunk and chunk["kind"] in {"table", "chart", "diagram", "infographic"}:
            candidates.append((chunk, "cited_region", None, [cid], []))

    images, used_paths, used_names = [], set(), set()
    for chunk, match, name, support, identity in candidates:
        asset = png_asset(chunk, project_root, asset_root)
        if not asset or asset[0] in used_paths or (name and normalized(name) in used_names):
            continue
        _, width, height = asset
        title = f"Chân dung {name}" if name else chunk.get("title") or "Hình trích từ báo cáo"
        images.append({"chunk_id": chunk["chunk_id"], "pdf_page": chunk["pdf_page"],
                       "printed_page": chunk.get("printed_page"), "kind": chunk["kind"],
                       "title": title, "alt": f"{title} — Báo cáo FPT 2025, trang PDF {chunk['pdf_page']}",
                       "width": width, "height": height, "bbox": list(chunk.get("bbox", [])),
                       "matched_by": match, "supporting_chunk_ids": support,
                       "identity_source_chunk_ids": identity})
        used_paths.add(asset[0])
        if name:
            used_names.add(normalized(name))
        if len(images) == limit:
            break
    return images


def image_delivery(trace: dict, candidates: list[dict], selection: object) -> dict:
    """Default to the sidebar; honor only grounded image choices from the final-answer tool.

    The model interprets the current user's request. The adapter checks its quoted request
    and restricts inline images to validated source regions actually seen during this turn.
    A request from previous history alone must never turn images on for subsequent answers.
    """
    selection = selection if isinstance(selection, dict) else {}
    quote = selection.get("request_quote", "")
    ids = selection.get("chunk_ids", [])
    question = " ".join(trace.get("question", "").split()).casefold()
    valid_quote = (isinstance(quote, str) and bool(quote.strip())
                   and " ".join(quote.split()).casefold() in question)
    inline = []
    if trace.get("status") == "answered" and valid_quote and isinstance(ids, list):
        seen = {c["chunk_id"] for c in trace.get("context", [])}
        available = {image["chunk_id"]: image for image in candidates}
        for cid in ids:
            if isinstance(cid, str) and cid in seen and cid in available:
                inline.append(available.pop(cid))
                if len(inline) == 2:
                    break
    all_images = {image["chunk_id"]: image for image in inline + candidates}
    return {"answer_images": inline,
            "source_images": list(all_images.values())[:3] if trace.get("status") == "answered" else [],
            "image_presentation": {"mode": "inline" if inline else "sidebar",
                                   "request_quote": quote.strip() if valid_quote else "",
                                   "selected_chunk_ids": [image["chunk_id"] for image in inline]}}

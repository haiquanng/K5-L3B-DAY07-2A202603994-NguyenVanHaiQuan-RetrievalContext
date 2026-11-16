"""Deterministic PDF layer: text blocks, graphic objects with bboxes, boilerplate removal, renders, crops.

Coordinates are PDF points, origin top-left (PyMuPDF). Boilerplate is learned from the document itself
(`DocProfile`): lines in the margin zones (left navigation sidebar, top band, bottom band) whose text
repeats on >= MIN_REPEAT pages are dropped from content, so a repeated table of contents or running
header does not pollute every chunk. Table headers in the body are never touched (body is not a margin).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

MIN_REPEAT = 3
NUM_RE = re.compile(r"^\d{1,3}$")
WHITE = 0xFFFFFF


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().upper()


@dataclass
class DocProfile:
    sidebar_x: float          # lines ending left of this are in the navigation sidebar
    top_y: float              # lines ending above this are in the top band
    bottom_y: float           # lines starting below this are in the bottom band
    repeated: set[str]        # normalized texts repeated in margin zones
    chapters: dict[str, str]  # "04" -> "CHIẾN LƯỢC PHÁT TRIỂN" (from the sidebar)

    def zone(self, bbox) -> str | None:
        if bbox[2] <= self.sidebar_x:
            return "sidebar"
        if bbox[3] <= self.top_y:
            return "top"
        if bbox[1] >= self.bottom_y:
            return "bottom"
        return None


def _lines(page: pymupdf.Page):
    for b in page.get_text("dict", sort=True)["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            t = "".join(s["text"] for s in l["spans"])
            if t.strip():
                yield b, l, t


def doc_profile(doc: pymupdf.Document, sidebar_frac: float = 0.19, top_frac: float = 0.12,
                bottom_frac: float = 0.93) -> DocProfile:
    W, H = doc[0].rect.width, doc[0].rect.height
    prof = DocProfile(W * sidebar_frac, H * top_frac, H * bottom_frac, set(), {})
    counts: Counter[str] = Counter()
    chapter_rows: Counter[tuple[str, str]] = Counter()
    for page in doc:
        seen = set()
        rows: dict[int, list[str]] = {}
        for _, l, t in _lines(page):
            if prof.zone(l["bbox"]):
                seen.add(_norm(t))
            if l["bbox"][2] <= prof.sidebar_x:
                rows.setdefault(round(l["bbox"][1] / 4), []).append(t.strip())
        counts.update(seen)
        for parts in rows.values():  # sidebar row "04" + "CHIẾN LƯỢC PHÁT TRIỂN"
            nums = [p for p in parts if re.fullmatch(r"0\d", p)]
            names = [p for p in parts if not NUM_RE.match(p) and p.isupper()]
            if len(nums) == 1 and len(names) == 1:
                chapter_rows[(nums[0], names[0])] += 1
    prof.repeated = {t for t, c in counts.items() if c >= MIN_REPEAT}
    for (num, name), _ in chapter_rows.most_common():
        prof.chapters.setdefault(num, name)
    return prof


@dataclass
class Block:
    id: str
    bbox: tuple[float, float, float, float]
    lines: list[str]
    size: float  # max font size
    line_boxes: list[tuple[float, float, float, float]] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(l.strip() for l in self.lines if l.strip())

    @property
    def cells(self) -> str:  # table rows: one line per cell
        return " | ".join(l.strip() for l in self.lines if l.strip())


def table_rows(blocks: list[Block]) -> list[tuple[str, tuple]]:
    """Rebuild table rows from line geometry (not block order): lines whose vertical centres overlap form
    one row, cells sorted left to right. Unruled financial tables often put each cell in its own block,
    so block order mixes rows; geometry does not."""
    lines = [(bx, t.strip()) for b in blocks for bx, t in zip(b.line_boxes or [b.bbox], b.lines) if t.strip()]
    lines.sort(key=lambda x: ((x[0][1] + x[0][3]) / 2, x[0][0]))
    rows: list[list] = []
    for bx, t in lines:
        cy, h = (bx[1] + bx[3]) / 2, bx[3] - bx[1]
        if rows and abs(cy - rows[-1][0]) <= max(2.5, 0.45 * min(h, rows[-1][1])):
            rows[-1][2].append((bx[0], t, bx))
        else:
            rows.append([cy, h, [(bx[0], t, bx)]])
    return [(" | ".join(t for _, t, _ in sorted(cells, key=lambda c: c[0])), union([c[2] for c in cells]))
            for _, _, cells in rows]


@dataclass
class PageLayout:
    page: int                       # 1-based PDF page
    printed_page: str | None        # page number printed on the page (may differ from PDF page)
    chapter: str | None             # "04 CHIẾN LƯỢC PHÁT TRIỂN"
    running_header: str             # repeated top-band text (kept as context, removed from content)
    width: float
    height: float
    blocks: list[Block]
    objects: dict[str, tuple[float, float, float, float]]  # i* raster image, d* vector-drawing cluster
    dropped_lines: int = 0
    has_text_layer: bool = True
    notes: list[str] = field(default_factory=list)

    def block(self, bid: str) -> Block | None:
        return next((b for b in self.blocks if b.id == bid), None)

    @property
    def text(self) -> str:
        return "\n".join(b.cells for b in self.blocks)


def _round(r) -> tuple[float, float, float, float]:
    return tuple(round(float(x), 1) for x in r)  # type: ignore[return-value]


def page_layout(doc: pymupdf.Document, pno: int, prof: DocProfile) -> PageLayout:
    page = doc[pno - 1]
    W, H = page.rect.width, page.rect.height
    blocks: list[Block] = []
    printed, chapter_num, header_parts, dropped = None, None, [], 0
    raw_chars = 0
    cur: dict[int, list] = {}
    active_by_name = False
    for b, l, t in _lines(page):
        raw_chars += len(t.strip())
        zone, key = prof.zone(l["bbox"]), _norm(t)
        if zone == "sidebar":
            colors = {s["color"] for s in l["spans"] if s["text"].strip()}
            name_to_num = {v: k for k, v in prof.chapters.items()}
            if t.strip() in name_to_num and colors - {0x0, 0x231F20, WHITE}:
                chapter_num = name_to_num[t.strip()]  # highlighted chapter name: most reliable signal
                active_by_name = True
            elif re.fullmatch(r"0\d", t.strip()) and colors == {WHITE} and not active_by_name:
                chapter_num = chapter_num or t.strip()
            elif NUM_RE.match(t.strip()) and l["bbox"][1] > 0.85 * H:
                printed = t.strip()
        if zone and (key in prof.repeated or (zone == "sidebar" and NUM_RE.match(t.strip()))):
            dropped += 1
            if zone == "top" and key in prof.repeated:
                header_parts.append(t.strip())
            continue
        if zone == "bottom" and NUM_RE.match(t.strip()):
            printed = printed or t.strip()
            dropped += 1
            continue
        size = max((s["size"] for s in l["spans"]), default=0)
        cur.setdefault(id(b), [b, []])[1].append((l["bbox"], t, size))
    for b, kept in cur.values():
        bbox = (min(x[0][0] for x in kept), min(x[0][1] for x in kept),
                max(x[0][2] for x in kept), max(x[0][3] for x in kept))
        blocks.append(Block(f"b{len(blocks)}", _round(bbox), [x[1] for x in kept],
                            round(max(x[2] for x in kept), 1), [_round(x[0]) for x in kept]))
    area = W * H
    # Graphic objects, coordinates straight from the PDF structure (never guessed by the model):
    #   t* ruled tables (find_tables), i* raster images, d* vector-drawing clusters (charts, diagrams).
    cands: list[tuple[str, pymupdf.Rect]] = []
    try:
        cands += [("t", pymupdf.Rect(t.bbox)) for t in page.find_tables().tables]
    except Exception:  # noqa: BLE001 - table finder can fail on odd pages; images/drawings still used
        pass
    cands += [("i", pymupdf.Rect(info["bbox"])) for info in page.get_image_info()]
    try:
        cands += [("d", pymupdf.Rect(r)) for r in page.cluster_drawings()]
    except Exception:  # noqa: BLE001 - malformed paths: no vector objects for this page
        pass
    keep: list[tuple[str, pymupdf.Rect]] = []
    for kind, r in sorted(cands, key=lambda x: -(x[1].width * x[1].height)):
        r = r & page.rect
        a = r.width * r.height
        if r.is_empty or a < 0.002 * area or a > 0.85 * area or r.x1 <= prof.sidebar_x * 1.15 or r.width < 20 or r.height < 12:
            continue  # icons, rules, full-page backgrounds, sidebar logo
        if any((r & k).width * (r & k).height > 0.8 * a for _, k in keep):
            continue  # nested inside a larger object already listed (tutora-ai dedup rule)
        keep.append((kind, r))
    keep.sort(key=lambda x: (round(x[1].y0), x[1].x0))  # reading order
    objects: dict[str, tuple] = {}
    for kind, r in keep:
        objects[f"{kind}{sum(k.startswith(kind) for k in objects)}"] = _round(r)
    chapter = f"{chapter_num} {prof.chapters.get(chapter_num, '')}".strip() if chapter_num else None
    lay = PageLayout(pno, printed, chapter, " · ".join(dict.fromkeys(header_parts)), W, H, blocks, objects,
                     dropped, raw_chars > 20)
    if not lay.has_text_layer:
        lay.notes.append("no text layer (image-only page): content comes from the vision description only")
    return lay


def union(rects) -> tuple[float, float, float, float] | None:
    rects = [r for r in rects if r]
    if not rects:
        return None
    return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))


def pad(r, W: float, H: float, p: float = 6) -> tuple[float, float, float, float]:
    return (round(max(0, r[0] - p), 1), round(max(0, r[1] - p), 1), round(min(W, r[2] + p), 1),
            round(min(H, r[3] + p), 1))


def render_page(doc: pymupdf.Document, pno: int, out: Path, zoom: float, quality: int = 85) -> Path:
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        pix = doc[pno - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        out.write_bytes(pix.tobytes("jpeg", jpg_quality=quality))
    return out


def crop(doc: pymupdf.Document, pno: int, bbox, out: Path, zoom: float = 2.5) -> Path:
    """PNG (lossless: tables/charts are mostly small digits that JPEG blurs); ~180 dpi."""
    out.parent.mkdir(parents=True, exist_ok=True)
    pix = doc[pno - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(bbox), alpha=False)
    pix.save(out)
    return out

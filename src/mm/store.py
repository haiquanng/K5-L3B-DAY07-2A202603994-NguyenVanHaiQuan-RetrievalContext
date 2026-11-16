"""Normalized pgvector store for the multimodal index (schema in schema.sql).

Re-indexing a page range replaces those pages atomically (delete pages -> cascade to regions, chunks,
embeddings -> insert). Vectors are reused by (model, content_hash), so re-running after a prompt or
chunking change only embeds chunks whose text actually changed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import psycopg

SCHEMA = Path(__file__).with_name("schema.sql")
DIM = 1024


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


class MMStore:
    def __init__(self, url: str) -> None:
        self.url = url

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.url, connect_timeout=5)

    def create_schema(self) -> None:
        with self.connect() as c:
            c.execute(SCHEMA.read_text(encoding="utf-8"))

    def versions(self) -> dict[str, str]:
        with self.connect() as c:
            r = c.execute("SELECT current_setting('server_version'), "
                          "(SELECT extversion FROM pg_extension WHERE extname='vector')").fetchone()
        return {"postgresql": r[0], "pgvector": r[1]}

    def cached_vectors(self, doc_id: str, model: str) -> dict[str, str]:
        """content_hash -> vector literal, for every chunk of this document already embedded with `model`."""
        with self.connect() as c:
            rows = c.execute("SELECT DISTINCT ON (e.content_hash) e.content_hash, e.embedding::text "
                             "FROM mm_embeddings e JOIN mm_chunks k USING (chunk_id) "
                             "WHERE k.doc_id=%s AND e.model=%s", (doc_id, model)).fetchall()
        return dict(rows)

    def replace_pages(self, document: dict, pages: list[dict], regions: list[dict], chunks: list[dict],
                      model: str, vectors: dict[str, str]) -> dict[str, int]:
        """One transaction. `vectors` maps content_hash -> vector literal for every chunk."""
        missing = [c["chunk_id"] for c in chunks if content_hash(c["content"]) not in vectors]
        if missing:
            raise ValueError(f"no vector for chunks {missing[:5]}")
        with self.connect() as c, c.cursor() as cur:
            cur.execute("""
                INSERT INTO mm_documents (doc_id, title, source_file, sha256, page_count, page_width, page_height, metadata)
                VALUES (%(doc_id)s, %(title)s, %(source_file)s, %(sha256)s, %(page_count)s, %(page_width)s,
                        %(page_height)s, %(metadata)s::jsonb)
                ON CONFLICT (doc_id) DO UPDATE SET title=EXCLUDED.title, source_file=EXCLUDED.source_file,
                    sha256=EXCLUDED.sha256, page_count=EXCLUDED.page_count, page_width=EXCLUDED.page_width,
                    page_height=EXCLUDED.page_height, metadata=EXCLUDED.metadata, indexed_at=now()""",
                        {**document, "metadata": json.dumps(document["metadata"], ensure_ascii=False)})
            cur.execute("DELETE FROM mm_pages WHERE doc_id=%s AND pdf_page = ANY(%s)",
                        (document["doc_id"], [p["pdf_page"] for p in pages]))
            deleted = cur.rowcount
            cur.executemany("""
                INSERT INTO mm_pages (doc_id, pdf_page, printed_page, chapter, page_title, running_header,
                                      has_text_layer, image_path, vision, log)
                VALUES (%(doc_id)s, %(pdf_page)s, %(printed_page)s, %(chapter)s, %(page_title)s, %(running_header)s,
                        %(has_text_layer)s, %(image_path)s, %(vision)s::jsonb, %(log)s::jsonb)""",
                [{**p, "vision": json.dumps(p["vision"], ensure_ascii=False),
                  "log": json.dumps(p["log"], ensure_ascii=False)} for p in pages])
            cur.executemany("""
                INSERT INTO mm_regions (region_id, doc_id, pdf_page, kind, title, description, bbox, bbox_source,
                                        crop_path, block_ids, object_ids, unverified_numbers)
                VALUES (%(region_id)s, %(doc_id)s, %(pdf_page)s, %(kind)s, %(title)s, %(description)s, %(bbox)s,
                        %(bbox_source)s, %(crop_path)s, %(block_ids)s, %(object_ids)s, %(unverified_numbers)s)""",
                [{**r, "bbox": [float(x) for x in r["bbox"]]} for r in regions])
            cur.executemany("""
                INSERT INTO mm_chunks (chunk_id, doc_id, pdf_page, region_id, kind, part, parts, title, content,
                                       content_hash, bbox, crop_path, metadata)
                VALUES (%(chunk_id)s, %(doc_id)s, %(pdf_page)s, %(region_id)s, %(kind)s, %(part)s, %(parts)s,
                        %(title)s, %(content)s, %(content_hash)s, %(bbox)s, %(crop_path)s, %(metadata)s::jsonb)""",
                [{**k, "bbox": [float(x) for x in k["bbox"]], "content_hash": content_hash(k["content"]),
                  "metadata": json.dumps(k["metadata"], ensure_ascii=False)} for k in chunks])
            cur.executemany("INSERT INTO mm_embeddings (chunk_id, model, content_hash, embedding) "
                            "VALUES (%s,%s,%s,%s::vector)",
                            [(k["chunk_id"], model, h, vectors[h])
                             for k in chunks for h in [content_hash(k["content"])]])
        return {"pages_replaced": deleted, "pages": len(pages), "regions": len(regions), "chunks": len(chunks)}

    def counts(self, doc_id: str) -> dict[str, Any]:
        with self.connect() as c:
            kinds = dict(c.execute("SELECT kind, count(*) FROM mm_chunks WHERE doc_id=%s GROUP BY kind ORDER BY kind",
                                   (doc_id,)).fetchall())
            pages = c.execute("SELECT count(*) FROM mm_pages WHERE doc_id=%s", (doc_id,)).fetchone()[0]
            regions = c.execute("SELECT count(*) FROM mm_regions WHERE doc_id=%s", (doc_id,)).fetchone()[0]
            emb = dict(c.execute("SELECT e.model, count(*) FROM mm_embeddings e JOIN mm_chunks k USING (chunk_id) "
                                 "WHERE k.doc_id=%s GROUP BY e.model", (doc_id,)).fetchall())
        return {"pages": pages, "regions": regions, "chunks_by_kind": kinds, "embeddings_by_model": emb}

    def search_dense(self, qvec: list[float], doc_id: str, model: str, k: int = 5,
                     kinds: list[str] | None = None) -> list[dict[str, Any]]:
        where, params = ["k.doc_id=%s", "e.model=%s"], [doc_id, model]
        if kinds:
            where.append("k.kind = ANY(%s)")
            params.append(kinds)
        q = _vec(qvec)
        sql = (f"SELECT k.chunk_id, k.kind, k.pdf_page, p.printed_page, k.title, k.content, k.bbox, k.crop_path, "
               f"k.region_id, k.metadata, 1 - (e.embedding <=> %s::vector) AS score "
               f"FROM mm_embeddings e JOIN mm_chunks k USING (chunk_id) "
               f"JOIN mm_pages p ON p.doc_id=k.doc_id AND p.pdf_page=k.pdf_page "
               f"WHERE {' AND '.join(where)} ORDER BY e.embedding <=> %s::vector, k.chunk_id LIMIT %s")
        with self.connect() as c:
            cur = c.execute(sql, [q, *params, q, k])
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

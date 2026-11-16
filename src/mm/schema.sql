-- Multimodal index schema (Day 7). Lives in the Day 6 PostgreSQL + pgvector database, next to the
-- untouched Day 6 table `chunks`. All tables are prefixed mm_.
--
--   mm_documents 1─* mm_pages 1─* mm_regions 1─* mm_chunks 1─* mm_embeddings
--                               └───────────────* mm_chunks (text chunks have no region)
--
-- * page numbers: pdf_page (1-based index in the file) is the key everywhere; printed_page is what the
--   page shows (FPT: printed = pdf - 1). Benchmarks must say which one they use.
-- * bbox: [x0, y0, x1, y1] in PDF points, origin top-left (PyMuPDF). Crops are re-creatable from bbox.
-- * mm_embeddings is keyed by (chunk_id, model) so several embedding models can be compared on the same
--   chunks; vectors are reused across re-index runs through content_hash.
-- * Exact cosine search (no ANN index): a few thousand rows, so filters never shrink recall.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS mm_documents (
    doc_id        text PRIMARY KEY,
    title         text NOT NULL,
    source_file   text NOT NULL,
    sha256        text NOT NULL,
    page_count    int  NOT NULL,
    page_width    real NOT NULL,
    page_height   real NOT NULL,
    metadata      jsonb NOT NULL DEFAULT '{}',
    indexed_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mm_pages (
    doc_id          text NOT NULL REFERENCES mm_documents ON DELETE CASCADE,
    pdf_page        int  NOT NULL CHECK (pdf_page >= 1),
    printed_page    text,
    chapter         text,
    page_title      text,
    running_header  text,
    has_text_layer  boolean NOT NULL,
    image_path      text NOT NULL,             -- full-page render
    vision          jsonb NOT NULL DEFAULT '{}', -- model, prompt_version, tokens, seconds
    log             jsonb NOT NULL DEFAULT '{}', -- leftover / unknown ids, skipped decorative regions
    PRIMARY KEY (doc_id, pdf_page)
);

CREATE TABLE IF NOT EXISTS mm_regions (
    region_id           text PRIMARY KEY,      -- <doc>:p010:chart02
    doc_id              text NOT NULL,
    pdf_page            int  NOT NULL,
    kind                text NOT NULL CHECK (kind IN ('table','chart','diagram','infographic','photo')),
    title               text NOT NULL,
    description         text NOT NULL,         -- vision-model text (NOT verbatim; see unverified_numbers)
    bbox                real[] NOT NULL CHECK (cardinality(bbox) = 4),
    bbox_source         text NOT NULL CHECK (bbox_source IN ('pdf_objects','model','page')),
    crop_path           text NOT NULL,
    block_ids           text[] NOT NULL,
    object_ids          text[] NOT NULL,
    unverified_numbers  text[] NOT NULL,       -- numbers in description not found in the page text layer
    FOREIGN KEY (doc_id, pdf_page) REFERENCES mm_pages ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mm_chunks (
    chunk_id      text PRIMARY KEY,            -- <doc>:p010:chart02  |  <doc>:p059:table01-2  |  <doc>:p012:text03-1
    doc_id        text NOT NULL,
    pdf_page      int  NOT NULL,
    region_id     text REFERENCES mm_regions ON DELETE CASCADE,  -- NULL for body-text chunks
    kind          text NOT NULL CHECK (kind IN ('text','table','chart','diagram','infographic','photo')),
    part          int  NOT NULL DEFAULT 1,
    parts         int  NOT NULL DEFAULT 1,
    title         text NOT NULL,
    content       text NOT NULL,               -- exactly what is embedded / shown to the LLM
    content_hash  text NOT NULL,
    bbox          real[] NOT NULL CHECK (cardinality(bbox) = 4),
    crop_path     text NOT NULL,
    metadata      jsonb NOT NULL DEFAULT '{}',
    tsv           tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
    FOREIGN KEY (doc_id, pdf_page) REFERENCES mm_pages ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS mm_chunks_doc_page ON mm_chunks (doc_id, pdf_page);
CREATE INDEX IF NOT EXISTS mm_chunks_kind ON mm_chunks (doc_id, kind);
CREATE INDEX IF NOT EXISTS mm_chunks_tsv ON mm_chunks USING gin (tsv);

CREATE TABLE IF NOT EXISTS mm_embeddings (
    chunk_id      text NOT NULL REFERENCES mm_chunks ON DELETE CASCADE,
    model         text NOT NULL,               -- BAAI/bge-m3@5617a9f61b02
    content_hash  text NOT NULL,
    embedding     vector(1024) NOT NULL,
    PRIMARY KEY (chunk_id, model)
);
CREATE INDEX IF NOT EXISTS mm_embeddings_hash ON mm_embeddings (model, content_hash);

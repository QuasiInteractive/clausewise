CREATE EXTENSION IF NOT EXISTS vector;

-- One row per official source document (an Act reprint, a guidance page).
CREATE TABLE IF NOT EXISTS sources (
    id          SERIAL PRIMARY KEY,
    url         TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    licence     TEXT NOT NULL,          -- recorded before ingesting, see docs/SOURCES.md
    fetched_at  TIMESTAMPTZ NOT NULL
);

-- Heading-aware chunks. `heading_path` is e.g. "Part 5 > Division 2 > s 185".
CREATE TABLE IF NOT EXISTS chunks (
    id            SERIAL PRIMARY KEY,
    source_id     INT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    heading_path  TEXT NOT NULL,
    anchor        TEXT,                 -- deep link fragment, when the source has one
    body          TEXT NOT NULL,
    scope         TEXT NOT NULL DEFAULT 'general', -- residential | rooming | general | other | admin
    embedding     vector(384),
    tsv           tsvector GENERATED ALWAYS AS (
                      to_tsvector('english', heading_path || ' ' || body)) STORED
);

-- databases created before the scope column existed
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'general';

CREATE INDEX IF NOT EXISTS chunks_scope_idx ON chunks (scope);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);

from datetime import datetime

import psycopg
from pgvector.psycopg import register_vector

from clausewise.config import settings
from clausewise.ingest.chunk import Chunk


def connect() -> psycopg.Connection:
    conn = psycopg.connect(settings.database_url)
    register_vector(conn)
    return conn


def replace_source(
    conn: psycopg.Connection,
    *,
    url: str,
    title: str,
    licence: str,
    fetched_at: datetime,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> int:
    """Swap a source's chunks in one transaction, so a re-ingest never leaves half a source."""
    import numpy as np

    with conn.transaction():
        conn.execute("DELETE FROM sources WHERE url = %s", (url,))
        source_id = conn.execute(
            "INSERT INTO sources (url, title, licence, fetched_at) VALUES (%s, %s, %s, %s)"
            " RETURNING id",
            (url, title, licence, fetched_at),
        ).fetchone()[0]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (source_id, heading_path, anchor, body, scope, embedding)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                [
                    (source_id, c.heading_path, c.anchor, c.body, c.scope,
                     np.array(e, dtype=np.float32))
                    for c, e in zip(chunks, embeddings, strict=True)
                ],
            )
    return source_id

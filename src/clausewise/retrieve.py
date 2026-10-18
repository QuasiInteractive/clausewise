"""Hybrid retrieval: keyword (Postgres full-text) + meaning (pgvector), fused with reciprocal
rank fusion, then re-ranked by a cross-encoder.

Why both: legal questions mix exact terms ("bond", "entry notice", "s 185") with paraphrase
("can they come in without telling me"). See docs/DECISIONS.md 004.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import psycopg
from fastembed.rerank.cross_encoder import TextCrossEncoder

from clausewise.embed import embed_query

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
RRF_K = 60  # the usual constant; dampens the gap between rank 1 and rank 2
LEASE_SCOPES = ("residential", "general")


@dataclass(frozen=True)
class Hit:
    chunk_id: int
    source_title: str
    url: str
    anchor: str | None
    heading_path: str
    body: str
    scope: str
    score: float

    @property
    def link(self) -> str:
        return f"{self.url}#{self.anchor}" if self.anchor else self.url


@lru_cache(maxsize=4)
def _reranker(model: str) -> TextCrossEncoder:
    return TextCrossEncoder(model)


_SELECT = """
    SELECT c.id, s.title, s.url, c.anchor, c.heading_path, c.body, c.scope
    FROM chunks c JOIN sources s ON s.id = c.source_id
    WHERE c.scope = ANY(%(scopes)s)
"""


def search(
    conn: psycopg.Connection,
    query: str,
    *,
    scopes: tuple[str, ...] = LEASE_SCOPES,
    k: int = 6,
    candidates: int = 40,
    rerank_pool: int = 25,
    mode: str = "hybrid",  # hybrid | vector | keyword (the last two exist for evals)
    rerank_model: str | None = RERANK_MODEL,
) -> list[Hit]:
    params = {"scopes": list(scopes), "n": candidates}

    vector_rows = [] if mode == "keyword" else conn.execute(
        _SELECT + " ORDER BY c.embedding <=> %(v)s LIMIT %(n)s",
        {**params, "v": np.array(embed_query(query), dtype=np.float32)},
    ).fetchall()

    # plainto_tsquery ANDs every word, which finds nothing for a chatty question; OR them instead
    keyword_rows = conn.execute(
        _SELECT
        + """ AND c.tsv @@ to_tsquery('english',
                  replace(plainto_tsquery('english', %(q)s)::text, ' & ', ' | '))
             ORDER BY ts_rank_cd(c.tsv, to_tsquery('english',
                  replace(plainto_tsquery('english', %(q)s)::text, ' & ', ' | '))) DESC
             LIMIT %(n)s""",
        {**params, "q": query},
    ).fetchall() if query.strip() and mode != "vector" else []

    fused: dict[int, float] = {}
    rows: dict[int, tuple] = {}
    for ranked in (vector_rows, keyword_rows):
        for rank, row in enumerate(ranked):
            fused[row[0]] = fused.get(row[0], 0.0) + 1.0 / (RRF_K + rank + 1)
            rows[row[0]] = row

    pool = sorted(fused, key=fused.get, reverse=True)[:rerank_pool]
    if not pool:
        return []
    if rerank_model is None:
        return [Hit(*rows[i], score=fused[i]) for i in pool[:k]]
    texts = [f"{rows[i][4]}\n{rows[i][5]}" for i in pool]
    scores = list(_reranker(rerank_model).rerank(query, texts))
    ranked = sorted(zip(pool, scores, strict=True), key=lambda p: p[1], reverse=True)[:k]
    return [Hit(*rows[i], score=float(s)) for i, s in ranked]

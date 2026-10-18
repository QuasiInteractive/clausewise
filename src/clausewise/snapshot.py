"""A text snapshot of the ingested corpus, committed to the repo so evals are reproducible.

Live ingest depends on two government websites that change; CI loads this snapshot instead,
so a score moves only when the code moves. Embeddings are not stored (they're rebuilt locally
in about a minute), which keeps the file small and model-independent.
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np

from clausewise.embed import embed_passages
from clausewise.ingest.chunk import Chunk
from clausewise.store import connect, replace_source

SNAPSHOT = Path("data/snapshot/corpus.jsonl")


def export_snapshot(path: Path = SNAPSHOT) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with connect() as conn, path.open("w", encoding="utf-8", newline="\n") as fh:
        sources = conn.execute(
            "SELECT id, url, title, licence, fetched_at FROM sources ORDER BY url").fetchall()
        for sid, url, title, licence, fetched_at in sources:
            chunks = conn.execute(
                "SELECT heading_path, anchor, body, scope FROM chunks WHERE source_id = %s"
                " ORDER BY id", (sid,)).fetchall()
            fh.write(json.dumps({
                "url": url, "title": title, "licence": licence,
                "fetched_at": fetched_at.isoformat(),
                "chunks": [{"heading_path": h, "anchor": a, "body": b, "scope": s}
                           for h, a, b, s in chunks],
            }, ensure_ascii=False) + "\n")
            n += len(chunks)
    return n


def load_snapshot(path: Path = SNAPSHOT) -> int:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    total = 0
    with connect() as conn:
        for rec in records:
            chunks = [Chunk(c["heading_path"], c["body"], c["anchor"], c["scope"])
                      for c in rec["chunks"]]
            vectors = embed_passages([f"{c.heading_path}\n{c.body}" for c in chunks])
            replace_source(
                conn, url=rec["url"], title=rec["title"], licence=rec["licence"],
                fetched_at=datetime.fromisoformat(rec["fetched_at"]), chunks=chunks,
                embeddings=[np.asarray(v).tolist() for v in vectors],
            )
            total += len(chunks)
    return total

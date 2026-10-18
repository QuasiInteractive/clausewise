"""Fetch the current RTRA Act, parse it, embed it and load it into Postgres."""

from datetime import UTC, datetime
from pathlib import Path

import httpx

from clausewise.config import settings
from clausewise.embed import embed_passages
from clausewise.ingest.qld_act import act_meta, parse_act
from clausewise.store import connect, replace_source

USER_AGENT = "Clausewise/0.1 (portfolio research; https://quasi-interactive.com/nick)"
RAW_DIR = Path("data/raw")

RTRA_ACT = {
    "doc_id": "act-2008-073",
    "title": "Residential Tenancies and Rooming Accommodation Act 2008 (Qld)",
    "licence": "CC BY 4.0, State of Queensland (legislation.qld.gov.au)",
}


def ingest_rtra_act() -> None:
    doc_id = RTRA_ACT["doc_id"]
    base = "https://www.legislation.qld.gov.au/view"
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True) as http:
        view = http.get(f"{base}/html/inforce/current/{doc_id}").raise_for_status().text
        meta = act_meta(view, RTRA_ACT["title"], doc_id)
        # fetch the dated version, not "current", so the text matches the citation date
        whole = http.get(f"{base}/whole/html/inforce/{meta.version_date}/{doc_id}")
        whole.raise_for_status()

    fetched_at = datetime.now(UTC)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{doc_id}_{meta.version_date}.html").write_text(whole.text, encoding="utf-8")

    chunks = parse_act(whole.text, settings.chunk_max_chars)
    print(f"{meta.title} (in force {meta.version_date}): {len(chunks)} chunks; embedding...")
    embeddings = embed_passages([f"{c.heading_path}\n{c.body}" for c in chunks])

    with connect() as conn:
        replace_source(
            conn,
            url=meta.base_url,
            title=f"{meta.title}, in force {meta.version_date}",
            licence=RTRA_ACT["licence"],
            fetched_at=fetched_at,
            chunks=chunks,
            embeddings=embeddings,
        )
    print(f"stored {len(chunks)} chunks from {meta.base_url}")

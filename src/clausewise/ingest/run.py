"""Fetch the official sources, parse them, embed them and load them into Postgres."""

import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import httpx

from clausewise.config import settings
from clausewise.embed import embed_passages
from clausewise.ingest.qld_act import act_meta, parse_act
from clausewise.ingest.rta import page_title, parse_rta_page
from clausewise.ingest.scope import rta_scope
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


RTA_LICENCE = "CC BY 3.0 AU, © The State of Queensland Residential Tenancies Authority"
RTA_SECTIONS = (
    "before-renting", "starting-a-tenancy", "during-a-tenancy", "ending-a-tenancy", "disputes",
    "rental-law-changes", "domestic-violence-in-a-rental-property", "who-is-responsible-for-repairs",
)


def rta_guidance_urls(http: httpx.Client) -> list[str]:
    sitemap = http.get("https://www.rta.qld.gov.au/sitemap.xml").raise_for_status().text
    urls = {
        u.replace("http://", "https://")
        for u in (m.split("</loc>")[0] for m in sitemap.split("<loc>")[1:])
    }
    return sorted(
        u for u in urls if u.removeprefix("https://www.rta.qld.gov.au/").split("/")[0] in RTA_SECTIONS
    )


def ingest_rta_guidance(delay_s: float = 1.0) -> None:
    raw = RAW_DIR / "rta"
    raw.mkdir(parents=True, exist_ok=True)
    stored = skipped = 0
    with (
        httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True) as http,
        connect() as conn,
    ):
        urls = rta_guidance_urls(http)
        print(f"RTA guidance: {len(urls)} pages")
        for url in urls:
            resp = http.get(url)
            time.sleep(delay_s)
            if resp.status_code != 200:
                print(f"  skip {resp.status_code} {url}")
                skipped += 1
                continue
            slug = url.removeprefix("https://www.rta.qld.gov.au/").strip("/").replace("/", "__")
            (raw / f"{slug}.html").write_text(resp.text, encoding="utf-8")

            scope = rta_scope(url)
            chunks = [replace(c, scope=scope) for c in parse_rta_page(resp.text, settings.chunk_max_chars)]
            if not chunks:  # index pages that only list their children
                skipped += 1
                continue
            title = page_title(resp.text)
            embeddings = embed_passages([f"{c.heading_path}\n{c.body}" for c in chunks])
            replace_source(
                conn,
                url=url,
                title=f"RTA: {title}",
                licence=RTA_LICENCE,
                fetched_at=datetime.now(UTC),
                chunks=chunks,
                embeddings=embeddings,
            )
            stored += len(chunks)
    print(f"stored {stored} chunks; skipped {skipped} pages")

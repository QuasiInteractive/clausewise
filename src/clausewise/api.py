"""HTTP API and the single-page site.

    uv run uvicorn clausewise.api:app --reload

Uploaded leases are read in memory and never written to disk or the database.
"""

import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from clausewise.answer import DISCLAIMER, answer
from clausewise.lease.check import check_lease
from clausewise.lease.extract import ScannedPdfError
from clausewise.retrieve import Hit, search
from clausewise.store import connect

STATIC = Path(__file__).parent / "static"
MAX_PDF_BYTES = 10 * 1024 * 1024
# a public demo calls a paid API: a few requests per minute per address is plenty for a person
RATE_LIMIT, RATE_WINDOW_S = 6, 60

app = FastAPI(title="Clausewise", docs_url="/api/docs")
_recent: dict[str, deque[float]] = defaultdict(deque)


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now, q = time.monotonic(), _recent[ip]
    while q and now - q[0] > RATE_WINDOW_S:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "Too many requests. Please wait a minute and try again.")
    q.append(now)


def _source(hit: Hit) -> dict:
    source = hit.source_title.split(",")[0]
    if source.startswith("Residential Tenancies and Rooming Accommodation Act"):
        source = "RTRA Act"
    return {"title": hit.heading_path.split(" > ")[-1], "source": source, "link": hit.link}


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.post("/api/ask")
def ask(q: Question, request: Request) -> dict:
    _rate_limit(request)
    with connect() as conn:
        hits = search(conn, q.question)
    result = answer(q.question, hits)
    return {"answer": result.text, "covered": result.covered,
            "sources": [_source(h) for h in result.sources], "disclaimer": DISCLAIMER}


@app.post("/api/check")
async def check(request: Request, file: Annotated[UploadFile, File()]) -> dict:
    _rate_limit(request)
    pdf = await file.read(MAX_PDF_BYTES + 1)
    if len(pdf) > MAX_PDF_BYTES:
        raise HTTPException(413, "That PDF is over 10 MB.")
    if not pdf.startswith(b"%PDF"):
        raise HTTPException(415, "That file isn't a PDF.")
    try:
        report = check_lease(pdf)
    except ScannedPdfError as e:
        raise HTTPException(422, f"{e}. Try the original PDF from your email, not a scan.") from e
    finally:
        del pdf  # nothing about the lease is kept
    return {
        "is_form_18a": report.is_form_18a,
        "problems": report.problems,
        "rules": [{"title": f.title, "verdict": f.verdict, "reason": f.explanation,
                   "sources": [{"title": t, "source": "RTRA Act", "link": u}
                               for t, u in f.citations]} for f in report.rule_findings],
        "clauses": [{"clause": f.clause, "verdict": f.verdict, "reason": f.reason,
                     "sources": [_source(h) for h in f.sources]}
                    for f in report.clause_findings],
        "disclaimer": DISCLAIMER,
    }

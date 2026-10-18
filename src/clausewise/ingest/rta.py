"""Parse an RTA Queensland guidance page (rta.qld.gov.au) into chunks.

The page body is `<article><div class="content">`. Navigation, share buttons and footers live
outside it. Inline links split sentences across many text nodes, so each block is flattened with
single spaces and the stray space before punctuation removed.
"""

import re

from bs4 import BeautifulSoup, Tag

from clausewise.ingest.chunk import Chunk, chunk_markdown

_BLOCKS = {"h2", "h3", "h4", "p", "li", "tr"}
_HEADING_LEVEL = {"h2": "##", "h3": "###", "h4": "####"}
_WS = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,;:!?)])")


def page_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    # the first h1 is the site name in the header
    return next((h for h in h1s if h != "Residential Tenancies Authority"), h1s[-1] if h1s else "")


def page_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("article .content")
    if content is None:
        return ""
    lines = [f"# {page_title(html)}"]
    for el in content.find_all(_BLOCKS):
        # a <p> inside an <li> (or a nested <li>) is emitted by its outermost block only
        if el.find_parent(_BLOCKS - {"tr"}) is not None and el.name != "tr":
            continue
        text = _flatten(el)
        if not text:
            continue
        if el.name in _HEADING_LEVEL:
            lines.append(f"{_HEADING_LEVEL[el.name]} {text}")
        elif el.name == "li":
            lines.append(f"- {text}")
        elif el.name == "tr":
            lines.append(" | ".join(_flatten(td) for td in el.find_all(["th", "td"])))
        else:
            lines.append(text)
    return "\n".join(lines)


def parse_rta_page(html: str, max_chars: int = 1800) -> list[Chunk]:
    return chunk_markdown(page_to_markdown(html), max_chars)


def _flatten(el: Tag) -> str:
    text = _WS.sub(" ", el.get_text(" ").replace("\xa0", " ")).strip()
    return _SPACE_BEFORE_PUNCT.sub(r"\1", text)

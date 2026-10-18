"""Parse a Queensland Act from legislation.qld.gov.au ("view whole" HTML) into section chunks.

The page is one flat run of elements: chapter / part / division headings, then each section's
heading (`p.HeadingParagraph` holding `<a name="sec.185">`) followed by blockquotes until the
next heading. The markup is not well-formed (a `<p>` wraps the whole body), so we walk every
element in document order instead of trusting the tree shape.

Amendment history notes are dropped; statutory notes and examples are kept, because examples
are often the clearest statement of what a section means in practice.
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from clausewise.ingest.chunk import Chunk, split_body

# heading level by the element's class
_LEVELS = {
    "ChapterHeadingParagraph": 1,
    "PartHeadingParagraph": 2,
    "OtherHeadingParagraph": 3,  # divisions and subdivisions, levelled by their text below
}
_SKIP_BLOCK = {"view-history-note", "history-note"}
_WS = re.compile(r"\s+")


@dataclass(frozen=True)
class ActMeta:
    title: str
    version_date: str  # the in-force version, e.g. "2026-08-17"
    base_url: str      # dated URL that anchors are appended to


def parse_act(html: str, max_chars: int = 1800) -> list[Chunk]:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("#fragview .content") or soup

    path: list[tuple[int, str]] = []
    section: tuple[str, str] | None = None  # (heading text, anchor)
    lines: list[str] = []
    chunks: list[Chunk] = []

    def flush() -> None:
        nonlocal section
        if section and lines:
            heading_path = " > ".join([t for _, t in path] + [section[0]])
            body = "\n".join(lines).strip()
            for piece in split_body(body, max_chars):
                chunks.append(Chunk(heading_path, piece, section[1]))
        lines.clear()

    for el in content.find_all(True):
        classes = set(el.get("class", []))

        if el.name == "p" and classes & _LEVELS.keys():
            flush()
            section = None
            text = _clean(el.get_text(" "))
            level = _heading_level(classes, text)
            while path and path[-1][0] >= level:
                path.pop()
            path.append((level, text))

        elif el.name == "p" and "HeadingParagraph" in classes:
            flush()
            anchor = el.find("a", attrs={"name": True})
            number = _clean(el.find("b").get_text()) if el.find("b") else ""
            name = _clean(el.find("span").get_text()) if el.find("span") else ""
            section = (f"s {number} {name}".strip(), anchor["name"] if anchor else None)

        elif el.name == "blockquote" and section and not (classes & _SKIP_BLOCK):
            if el.find_parent("blockquote") is None:
                lines.extend(_block_lines(el))

    flush()
    return chunks


def act_meta(view_html: str, title: str, doc_id: str) -> ActMeta:
    """Read the in-force version date from the act's 'view' page toolbar link."""
    m = re.search(rf"/view/whole/html/inforce/(\d{{4}}-\d{{2}}-\d{{2}})/{re.escape(doc_id)}", view_html)
    if not m:
        raise ValueError("could not find the in-force version date on the view page")
    date = m.group(1)
    return ActMeta(
        title=title,
        version_date=date,
        base_url=f"https://www.legislation.qld.gov.au/view/html/inforce/{date}/{doc_id}",
    )


def _heading_level(classes: set[str], text: str) -> int:
    if "OtherHeadingParagraph" in classes:
        return 4 if text.lower().startswith("subdivision") else 3
    return next(_LEVELS[c] for c in classes if c in _LEVELS)


def _block_lines(block: Tag) -> list[str]:
    """One line per (sub)paragraph, in document order, keeping list numbers like (1) and (a).

    Walks the text nodes in order and starts a new line whenever the nearest enclosing
    blockquote changes. Rebuilding from the tree instead put text that follows a nested list
    (malformed markup) on the wrong line.
    """
    out: list[str] = []
    buf: list[str] = []
    owner = None
    for s in block.find_all(string=True):
        bq = s.find_parent("blockquote")
        if any(set(p.get("class", [])) & _SKIP_BLOCK for p in s.find_parents("blockquote")):
            continue
        parent_classes = set(s.parent.get("class", [])) if s.parent.name == "span" else set()
        # a new blockquote, list number or note heading starts a new line; the markup doesn't
        # always close one list before the next subsection begins
        if bq is not owner or parent_classes & {"ListNumber", "NoteHeadingName"}:
            if buf:
                out.append(_clean("".join(buf)))
            buf, owner = [], bq
        text = str(s)
        if "ListNumber" in parent_classes:
            text += " "
        buf.append(text)
    if buf:
        out.append(_clean("".join(buf)))
    return [line for line in out if line]


def _clean(text: str) -> str:
    return _WS.sub(" ", text.replace("\xa0", " ")).strip()

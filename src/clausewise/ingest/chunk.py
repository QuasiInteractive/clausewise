"""Heading-aware chunking.

Input is markdown-ish text where headings start with '#'. Each chunk carries the full path of
headings above it ("Part 5 > Division 2 > 185 Landlord's obligations"), so a citation can name
the exact section. Sections longer than `max_chars` are split on paragraph boundaries; a single
paragraph longer than that is split on sentence boundaries as a last resort.
"""

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SENTENCE_END = re.compile(r"(?<=[.;:])\s+")


@dataclass(frozen=True)
class Chunk:
    heading_path: str
    body: str
    anchor: str | None = None
    scope: str = "general"  # see clausewise.ingest.scope


def chunk_markdown(text: str, max_chars: int = 1800) -> list[Chunk]:
    path: list[tuple[int, str]] = []
    sections: list[tuple[str, list[str]]] = []
    current: list[str] = []

    def flush() -> None:
        body = "\n".join(current).strip()
        if body:
            sections.append((" > ".join(title for _, title in path), body))
        current.clear()

    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            while path and path[-1][0] >= level:
                path.pop()
            path.append((level, m.group(2)))
        else:
            current.append(line)
    flush()

    chunks: list[Chunk] = []
    for heading_path, body in sections:
        for piece in split_body(body, max_chars):
            chunks.append(Chunk(heading_path, piece))
    return chunks


def split_body(body: str, max_chars: int) -> list[str]:
    if len(body) <= max_chars:
        return [body]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    units: list[str] = []
    for p in paragraphs:
        if len(p) <= max_chars:
            units.append(p)
        else:
            # lines first (legislation puts each subsection on its own line), sentences last
            lines: list[str] = []
            for line in p.splitlines():
                if len(line) <= max_chars:
                    lines.append(line)
                else:
                    lines.extend(_pack(_SENTENCE_END.split(line), max_chars, " "))
            units.extend(_pack(lines, max_chars, "\n"))
    return _pack(units, max_chars, "\n\n")


def _pack(units: list[str], max_chars: int, sep: str) -> list[str]:
    out: list[str] = []
    buf = ""
    for u in units:
        candidate = f"{buf}{sep}{u}" if buf else u
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                out.append(buf)
            buf = u  # a single unit over the limit is kept whole rather than cut mid-sentence
    if buf:
        out.append(buf)
    return out

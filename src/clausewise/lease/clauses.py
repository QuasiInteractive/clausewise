"""Find the parts of a lease worth checking, and split them into clauses.

For a Form 18a the standard terms are set by law (clause 2: the Act overrides any term, and
standard terms override special terms), so the parts a landlord can get wrong are the special
terms and the filled-in items. A custom lease is checked clause by clause in full.
"""

import re

from clausewise.lease.extract import LeaseDoc

SPECIAL_TERMS_FIELD = "Special terms"
_SPECIAL_TERMS_HEADING = re.compile(r"Part 3\s+Special terms", re.IGNORECASE)
# The printed Part 3 page carries this instruction line before the landlord's own text.
_PART3_BOILERPLATE = re.compile(
    r"Insert any special terms here.*?See clause 2\(3\) to 2\(5\)|"
    r"The tenant/s must receive a copy of the information statement.*?(?:\.|$)",
    re.IGNORECASE | re.DOTALL,
)
_SIGNATURES = re.compile(r"\n\s*Signature of (?:lessor|tenant)|\n\s*Lessor/agent signature",
                         re.IGNORECASE)
# a clause starts at "1.", "1)", "12 ", "Clause 3", "a." etc. at the start of a line
_CLAUSE_START = re.compile(r"(?m)^\s*(?:clause\s+)?(\d{1,2}(?:\.\d{1,2})*)[.)]?\s+(?=\S)",
                           re.IGNORECASE)


def special_terms(doc: LeaseDoc) -> list[str]:
    if doc.fields.get(SPECIAL_TERMS_FIELD):
        return split_clauses(doc.fields[SPECIAL_TERMS_FIELD])
    m = _SPECIAL_TERMS_HEADING.search(doc.text)
    if not m:
        return []
    tail = doc.text[m.end():]
    end = _SIGNATURES.search(tail)
    if end:
        tail = tail[: end.start()]
    tail = _PART3_BOILERPLATE.sub("", tail)
    return split_clauses(tail)


def clauses_to_check(doc: LeaseDoc) -> list[str]:
    return special_terms(doc) if doc.is_form_18a else split_clauses(doc.text)


def split_clauses(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    starts = [m.start() for m in _CLAUSE_START.finditer(text) if "." not in m.group(1)]
    if not starts:
        # unnumbered: one clause per paragraph, or per line if there are no blank lines
        parts = re.split(r"\n\s*\n", text) if re.search(r"\n\s*\n", text) else text.splitlines()
        return [_one_line(p) for p in parts if _one_line(p)]
    pieces = [_CLAUSE_START.sub("", text[a:b], count=1)
              for a, b in zip(starts, [*starts[1:], len(text)], strict=True)]
    preamble = text[: starts[0]].strip()
    out = [_one_line(p) for p in pieces if _one_line(p)]
    return ([_one_line(preamble)] if len(preamble) > 40 else []) + out


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

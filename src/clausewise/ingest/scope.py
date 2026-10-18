"""Which kind of tenancy a chunk applies to.

The Act covers ordinary residential tenancies and rooming accommodation side by side, and plain
search happily returns a rooming-house rule for a question about a house lease. Each chunk gets
one scope so retrieval for a lease check can filter:

- residential: ordinary tenancies (houses, units, Form 18a leases)
- rooming:     rooming accommodation
- general:     applies to both, or not tied to either
- other:       moveable dwelling parks, retirement villages and similar, out of scope for v1
- admin:       how the RTA itself runs, transitional provisions; never useful for a lease check
"""

import re

_RESIDENTIAL = re.compile(r"\bresidential tenanc(?:y|ies)\b(?! authority| employing)", re.IGNORECASE)
_ROOMING = re.compile(r"\brooming\b|\bresidential services\b", re.IGNORECASE)
_ADMIN_CHAPTERS = re.compile(
    r"^Chapter (10|11|14) |^Chapter 13A ", re.IGNORECASE
)  # the RTA, its employing office, transitional provisions, State/community housing leases
_OTHER_CHAPTERS = re.compile(r"^Chapter 8 ", re.IGNORECASE)  # nuisance in moveable dwelling parks

_RTA_ROOMING = ("rooming", "residential-services")
_RTA_OTHER = ("moveable", "caravan", "retirement-village", "manufactured-home")


def act_scope(heading_path: str) -> str:
    headings = heading_path.split(" > ")
    if _ADMIN_CHAPTERS.search(headings[0]):
        return "admin"
    if _OTHER_CHAPTERS.search(headings[0]):
        return "other"
    # the deepest heading that names exactly one kind decides
    for heading in reversed(headings):
        residential, rooming = bool(_RESIDENTIAL.search(heading)), bool(_ROOMING.search(heading))
        if residential != rooming:
            return "residential" if residential else "rooming"
    return "general"


def rta_scope(url: str) -> str:
    path = url.lower()
    if any(k in path for k in _RTA_ROOMING):
        return "rooming"
    if any(k in path for k in _RTA_OTHER):
        return "other"
    return "general"

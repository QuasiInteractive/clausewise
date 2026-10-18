"""Checks that plain code can do exactly, with no model involved.

Each rule quotes the section it implements; if the Act changes, the rule's test fails loudly
rather than the model quietly drifting.
"""

import re
from dataclasses import dataclass

from clausewise.lease.extract import LeaseDoc

ACT_URL = "https://www.legislation.qld.gov.au/view/html/inforce/2026-08-17/act-2008-073"
_MONEY = re.compile(r"\$?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")


@dataclass(frozen=True)
class RuleFinding:
    title: str
    verdict: str  # ok | check | likely_unlawful
    explanation: str
    citations: list[tuple[str, str]]  # (label, link)


def money(text: str | None) -> float | None:
    if not text:
        return None
    m = _MONEY.search(text)
    return float(m.group(1).replace(",", "")) if m else None


def weekly_rent(doc: LeaseDoc) -> float | None:
    amount = money(doc.fields.get("Rent amount"))
    period = (doc.fields.get("week, fortnight or month") or "").lower()
    if amount is None:
        return None
    if "fortnight" in period:
        return amount / 2
    if "month" in period:
        return amount * 12 / 52
    if "week" in period:
        return amount
    return None  # unknown period: don't guess


def bond_rule(doc: LeaseDoc) -> RuleFinding | None:
    """s 112(1)(b) and s 146: for a house or unit, the bond can't be more than 4 weeks' rent.

    Moveable dwellings (2-3 weeks) and employer-subsidised tenancies (s 146(2)) differ, so an
    excess is "likely unlawful" with those exceptions named, never stated as certain.
    """
    bond = money(doc.fields.get("Rental bond amount"))
    rent = weekly_rent(doc)
    if bond is None or rent is None:
        return None
    limit = round(rent * 4, 2)
    cites = [("RTRA Act s 112 Meaning of maximum rental bond", f"{ACT_URL}#sec.112"),
             ("RTRA Act s 146 Payments above maximum amount", f"{ACT_URL}#sec.146")]
    if bond <= limit + 0.01:
        return RuleFinding(
            "Bond amount", "ok",
            f"The bond (${bond:,.2f}) is within the 4 weeks' rent limit (${limit:,.2f}).", cites)
    return RuleFinding(
        "Bond amount", "likely_unlawful",
        f"The bond (${bond:,.2f}) is more than 4 weeks' rent (${limit:,.2f}). For a house or "
        "unit the maximum bond is 4 weeks' rent, and requiring more is an offence. Different "
        "limits apply to moveable dwellings and to some employer-subsidised housing.",
        cites)

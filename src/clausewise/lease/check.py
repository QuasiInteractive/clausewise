"""Check a lease: plain-code rules first, then each clause against the rules it retrieves.

For every clause the model gets the clause plus numbered sources and must return a verdict, a
plain-English reason and the source numbers it relied on. Code then enforces the contract:
unknown verdicts, citations to sources it wasn't given, or a "problem" verdict with no citation
are downgraded to "not covered" rather than shown. A finding without a source is never shown.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import anthropic
import psycopg

from clausewise.answer import format_sources
from clausewise.config import settings
from clausewise.lease.clauses import clauses_to_check
from clausewise.lease.extract import LeaseDoc, read_lease
from clausewise.lease.rules import RuleFinding, bond_rule
from clausewise.retrieve import Hit, search

VERDICTS = ("ok", "check", "likely_unlawful", "not_covered")

SYSTEM = """You check one clause from a Queensland residential tenancy agreement (a house or
unit lease, Form 18a) against the numbered sources provided.

Reply with ONLY a JSON object, no other text:
{"verdict": "...", "reason": "...", "cites": [numbers]}

verdict is one of:
- "ok": the sources show the clause is consistent with the rules, or it is an ordinary
  arrangement the rules allow.
- "check": the clause might be fine but depends on conditions the sources describe (for
  example it is only allowed in some situations), or it is unclear.
- "likely_unlawful": the sources show the clause conflicts with a tenant right or a lessor
  duty under the Act (under the agreement's clause 2, the Act would override it).
- "not_covered": the sources don't address this clause.

reason: one or two plain-English sentences for a renter (Year 9 level) saying what the rule is
and how the clause compares. No legal advice, no predictions about tribunals.
cites: the source numbers the reason relies on. Required for every verdict except
"not_covered". Use ONLY the sources provided, never outside knowledge."""


@dataclass(frozen=True)
class ClauseFinding:
    clause: str
    verdict: str
    reason: str
    sources: list[Hit]


@dataclass(frozen=True)
class LeaseReport:
    is_form_18a: bool
    rule_findings: list[RuleFinding]
    clause_findings: list[ClauseFinding]

    @property
    def problems(self) -> int:
        return sum(f.verdict == "likely_unlawful" for f in [*self.rule_findings,
                                                              *self.clause_findings])


def parse_verdict(raw: str, clause: str, hits: list[Hit]) -> ClauseFinding:
    not_covered = ClauseFinding(clause, "not_covered",
                                "The rules I have don't clearly address this clause.", [])
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return not_covered
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return not_covered
    verdict, reason = data.get("verdict"), str(data.get("reason", "")).strip()
    cites = data.get("cites") or []
    if verdict not in VERDICTS or verdict == "not_covered" or not reason:
        return not_covered
    if not isinstance(cites, list) or not cites or any(
        not isinstance(n, int) or n < 1 or n > len(hits) for n in cites
    ):
        return not_covered  # an uncited or mis-cited judgement is not shown
    used = list(dict.fromkeys(cites))
    return ClauseFinding(clause, verdict, reason, [hits[n - 1] for n in used])


def check_clause(conn: psycopg.Connection, client: anthropic.Anthropic, clause: str) -> ClauseFinding:
    hits = search(conn, clause, k=6)
    if not hits:
        return ClauseFinding(clause, "not_covered", "No matching rules found.", [])
    msg = client.messages.create(
        model=settings.answer_model,
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user",
                   "content": f"Sources:\n\n{format_sources(hits)}\n\nClause:\n{clause}"}],
    )
    if msg.stop_reason == "max_tokens":
        return ClauseFinding(clause, "not_covered", "This clause couldn't be checked.", [])
    raw = "".join(b.text for b in msg.content if b.type == "text")
    return parse_verdict(raw, clause, hits)


def check_doc(doc: LeaseDoc, *, client: anthropic.Anthropic | None = None,
              workers: int = 4) -> LeaseReport:
    if client is None:
        key = settings.anthropic_api_key
        client = anthropic.Anthropic(api_key=key.get_secret_value() if key else None)
    rules = [f for f in [bond_rule(doc)] if f is not None]
    clauses = clauses_to_check(doc)

    from clausewise.store import connect

    def one(clause: str) -> ClauseFinding:
        with connect() as conn:  # a connection per worker; psycopg connections aren't shared
            return check_clause(conn, client, clause)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        findings = list(pool.map(one, clauses))
    return LeaseReport(doc.is_form_18a, rules, findings)


def check_lease(pdf: bytes, **kwargs) -> LeaseReport:
    return check_doc(read_lease(pdf), **kwargs)

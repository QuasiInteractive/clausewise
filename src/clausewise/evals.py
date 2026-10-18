"""Retrieval evals: does the right rule come back for a plain-English question?

A question passes at k if any of its acceptable targets is in the top k. A target is either an
Act anchor ("sec.93") or a fragment of an RTA page URL ("/rent-increases").
"""

import json
from dataclasses import dataclass
from pathlib import Path

from clausewise.retrieve import Hit

GOLDEN = Path("eval/search_golden.jsonl")


@dataclass(frozen=True)
class Case:
    q: str
    targets: list[str]


def load_cases(path: Path = GOLDEN) -> list[Case]:
    return [Case(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]


def first_match_rank(hits: list[Hit], targets: list[str]) -> int | None:
    for rank, hit in enumerate(hits, start=1):
        if any(t == hit.anchor or (t.startswith("/") and t in hit.url) for t in targets):
            return rank
    return None


def score(ranks: list[int | None], k: int) -> dict[str, float]:
    n = len(ranks)
    return {
        f"recall@{k}": sum(1 for r in ranks if r is not None and r <= k) / n,
        "recall@1": sum(1 for r in ranks if r == 1) / n,
        "mrr": sum(1 / r for r in ranks if r is not None and r <= k) / n,
    }

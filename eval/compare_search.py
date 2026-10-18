"""Score retrieval configurations against eval/search_golden.jsonl.

    uv run python eval/compare_search.py
"""

from clausewise.evals import first_match_rank, load_cases, score
from clausewise.retrieve import search
from clausewise.store import connect

K = 5
CONFIGS = {
    "vector only": {"mode": "vector", "rerank_model": None},
    "keyword only": {"mode": "keyword", "rerank_model": None},
    "hybrid (RRF)": {"mode": "hybrid", "rerank_model": None},
    "hybrid + MiniLM rerank": {"mode": "hybrid", "rerank_model": "Xenova/ms-marco-MiniLM-L-6-v2"},
    "hybrid + bge-base rerank": {"mode": "hybrid", "rerank_model": "BAAI/bge-reranker-base"},
}


def main() -> None:
    cases = load_cases()
    with connect() as conn:
        for name, cfg in CONFIGS.items():
            ranks = [first_match_rank(search(conn, c.q, k=K, **cfg), c.targets) for c in cases]
            s = score(ranks, K)
            misses = [c.q[:40] for c, r in zip(cases, ranks, strict=True) if r is None]
            print(f"{name:26} recall@{K} {s[f'recall@{K}']:.2f}  recall@1 {s['recall@1']:.2f}"
                  f"  MRR {s['mrr']:.2f}  misses: {misses}")


if __name__ == "__main__":
    main()

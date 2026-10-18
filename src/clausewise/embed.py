"""Local embeddings (fastembed, ONNX on CPU). The model downloads once on first use.

MODEL_LOCK serialises every local model call (embedding and re-ranking). ONNX Runtime gives
each concurrent call its own working memory, so the lease checker's parallel clauses pushed a
2 GB container past its limit (exit 137). Model calls take about a second; the slow part, the
Claude call, still runs in parallel.
"""

import threading
from functools import lru_cache

from fastembed import TextEmbedding

from clausewise.config import settings

MODEL_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(settings.embedding_model)


def embed_passages(texts: list[str]) -> list[list[float]]:
    with MODEL_LOCK:
        return [v.tolist() for v in _model().passage_embed(texts, batch_size=64)]


def embed_query(text: str) -> list[float]:
    with MODEL_LOCK:
        return next(iter(_model().query_embed(text))).tolist()

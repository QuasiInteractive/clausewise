"""Local embeddings (fastembed, ONNX on CPU). The model downloads once on first use."""

from functools import lru_cache

from fastembed import TextEmbedding

from clausewise.config import settings


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(settings.embedding_model)


def embed_passages(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _model().passage_embed(texts, batch_size=64)]


def embed_query(text: str) -> list[float]:
    return next(iter(_model().query_embed(text))).tolist()

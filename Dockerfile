FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    FASTEMBED_CACHE_PATH=/models

COPY --from=ghcr.io/astral-sh/uv:0.12.16 /uv /bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

# Bake the embedding and re-ranking models into the image so a cold start doesn't download them.
RUN uv run python -c "from clausewise.embed import _model; from clausewise.retrieve import _reranker, RERANK_MODEL; _model(); _reranker(RERANK_MODEL)"

RUN useradd --create-home app && chown -R app /app /models
USER app

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "clausewise.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

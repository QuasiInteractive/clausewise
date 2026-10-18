# Plan

Scope for v1: **Queensland general tenancy agreements only** (houses and units, Form 18a).
Rooming accommodation, moveable dwellings and employment contracts come later.

## Milestones

- [x] **0. Setup**: uv project, Postgres + pgvector in Docker, config, chunker with tests.
- [ ] **1. Corpus**: fetch the RTRA Act 2008 (current reprint) and the RTA renting guidance
      pages. Clean to markdown, chunk by section, store with source URL + section + fetch date.
      Check each source's licence and robots.txt first and record it in `docs/SOURCES.md`.
      - [x] RTRA Act, in force 2026-08-17: 769 chunks, every one with a `sec.N` deep link
            (`uv run clausewise ingest`). robots.txt allows /view/html; /view/pdf is disallowed.
      - [ ] RTA guidance pages (plain-English explanations).
      - [ ] Tag each chunk as residential tenancy / rooming accommodation / both. Plain vector
            search already returns rooming sections (s 256B, s 260) for house questions.
- [ ] **2. Search**: embeddings (fastembed, bge-small), Postgres full-text, reciprocal rank
      fusion, cross-encoder re-rank. A CLI: `clausewise search "can my landlord keep my bond"`.
- [ ] **3. Answers**: Claude answers only from retrieved chunks, cites each claim, refuses when
      the sources don't cover it. `clausewise ask "..."`.
- [ ] **4. Lease check**: PDF → text (pypdf; scanned PDFs flagged for OCR later) → clauses →
      per-clause verdict (normal / check this / probably not OK) with citations.
- [ ] **5. Evals**: ~50 golden questions + ~10 sample leases with planted unlawful clauses.
      Metrics: retrieval recall@5, citation correctness, refusal rate on out-of-scope questions,
      planted-clause catch rate. Runs in GitHub Actions; the score goes in the README.
- [ ] **6. Web**: FastAPI endpoints + a small upload page. Deploy. Demo video. LinkedIn post.

## Rules for this repo

- Never invent a rule. Every finding must point at a retrieved source chunk, or it is not shown.
- Queensland rental law changed in 2024 and 2025. Always use the current reprint, and show the
  fetch date on every citation.
- Uploaded leases contain names and addresses. Process in memory, never store them by default.

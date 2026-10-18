# Decisions

## 001: Postgres + pgvector, not a dedicated vector database
One database for documents, full-text search and vectors. Hybrid search is a single SQL query,
and Postgres is already familiar from Mitsuke and Kensa-ya.

## 002: Local embeddings and re-ranking with fastembed
ONNX models on the CPU, no server and no per-call cost. `BAAI/bge-small-en-v1.5` (384 dims) for
embeddings and a small cross-encoder for re-ranking. Swappable behind one function if quality
needs a bigger model.

## 003: pypdf, not PyMuPDF
PyMuPDF is AGPL. pypdf is BSD and handles text-based PDFs, which most emailed leases are.
Scanned leases are detected (no extractable text) and flagged; OCR is a later milestone.

## 004: Hybrid retrieval with reciprocal rank fusion
Legal questions mix exact terms ("bond", "s 185", "entry notice") with paraphrase ("can they
come in without telling me"). Keyword search catches the first, vectors the second; RRF merges
them without tuning score scales against each other.

## 005: Refuse rather than guess
If no retrieved chunk supports an answer, the answer is "not covered by the rules I have".
This is measured in the eval suite, the same principle as Kensa-ya refunding unreadable sheets.

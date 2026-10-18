# Clausewise

**Live:** https://clausewise.bluewater-bad1ebb8.australiaeast.azurecontainerapps.io (scales to zero, so the first visit can take ~30 seconds to wake)

Upload a Queensland residential lease (PDF). Clausewise reads it clause by clause, checks each
clause against the official tenancy rules, and gives back a plain-English report with a link to
the exact rule behind every finding. You can then ask follow-up questions about your own lease.

```
✅ Normal          Rent is paid fortnightly.
⚠️  Check this      Tenant must pay for professional carpet cleaning at the end.   [RTA: Bond refunds]
❌ Probably not OK  Tenant is responsible for all repairs.                         [RTRA Act s 185]
```

(Illustrative output. Section numbers will come from the retrieved sources, not from this README.)

**General information, not legal advice.** Clausewise shows what the rules say and where they
say it. It never tells you what a tribunal will decide.

## How it works

1. **Ingest** official sources (the RTRA Act 2008 and RTA Queensland guidance) into clean,
   heading-aware chunks. Every chunk keeps its source URL, section and the date it was fetched.
2. **Retrieve** with hybrid search: Postgres full-text (keywords) and pgvector (meaning), merged
   with reciprocal rank fusion, then re-ranked by a cross-encoder.
3. **Answer** with Claude, from the retrieved rules only. Every sentence cites a source. When
   the sources don't cover a question, it says so instead of guessing.
4. **Lease check**: the uploaded PDF is split into clauses, and each clause is classified
   against the rules it retrieves.
5. **Evaluate**: a golden set of questions and sample leases with known answers, scored for
   retrieval recall, citation correctness and refusal behaviour, run in CI on every change.

## Stack

Python 3.13 · FastAPI · Postgres 17 + pgvector (Supabase, Sydney) · fastembed (local embeddings
and re-ranking, no API cost) · Claude · pypdf · pytest · GitHub Actions · Docker on Azure
Container Apps (Bicep, scale to zero).

## Results

| Eval | Result |
|---|---|
| Retrieval: 48 renter questions, a correct rule in the top 5 | **92%** (keyword only 67%, vector only 88%, hybrid without re-rank 90%) |
| Lease check: planted unlawful special terms caught | **6 / 6** |
| Lease check: harmless terms wrongly flagged | **0 / 6** |
| Bond rule (plain code, s 112/146) | **3 / 3** |

The retrieval eval runs in CI on every push against a committed snapshot of the corpus. The
lease eval calls Claude, so it runs on manual dispatch. These are small sets; they grow with
every bug found.

## Running it

```bash
docker compose up -d          # Postgres + pgvector on localhost:5433
cp .env.example .env          # add your ANTHROPIC_API_KEY
uv sync
uv run clausewise snapshot-load   # or `clausewise ingest` to fetch live from the sources
uv run uvicorn clausewise.api:app --port 8077   # the site at http://localhost:8077

uv run clausewise ask "How often can the rent go up?"
uv run clausewise check eval/leases/bad.pdf
uv run clausewise eval-search
uv run pytest
```

## Status

Week-one build. See [docs/PLAN.md](docs/PLAN.md) for the milestones and
[docs/DECISIONS.md](docs/DECISIONS.md) for why things are the way they are.

Built by Nicolas Balkhausen (Elyra Software) · [quasi-interactive.com/nick](https://quasi-interactive.com/nick)

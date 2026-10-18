"""Clausewise: check a Queensland lease against the official tenancy rules, with citations."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="clausewise")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="fetch, parse, embed and store the official sources")
    ingest.add_argument("which", nargs="?", choices=["all", "act", "rta"], default="all")
    search = sub.add_parser("search", help="show the sources a question retrieves")
    search.add_argument("query")
    search.add_argument("-k", type=int, default=6)
    search.add_argument("--all-scopes", action="store_true", help="include rooming etc.")
    ask = sub.add_parser("ask", help="answer a question from the rules, with citations")
    ask.add_argument("question")
    check = sub.add_parser("check", help="check a lease PDF clause by clause")
    check.add_argument("pdf")
    sub.add_parser("snapshot-export", help="write the ingested corpus to data/snapshot")
    sub.add_parser("snapshot-load", help="load data/snapshot into the database (used by CI)")
    ev = sub.add_parser("eval-search", help="score retrieval on eval/search_golden.jsonl")
    ev.add_argument("--min-recall", type=float, default=0.0, help="exit 1 below this recall@5")
    args = parser.parse_args()

    if args.command == "snapshot-export":
        from clausewise.snapshot import export_snapshot

        print(f"exported {export_snapshot()} chunks")

    if args.command == "snapshot-load":
        from clausewise.snapshot import load_snapshot

        print(f"loaded {load_snapshot()} chunks")

    if args.command == "eval-search":
        import sys

        from clausewise.evals import first_match_rank, load_cases, score
        from clausewise.retrieve import search as run_search
        from clausewise.store import connect

        cases = load_cases()
        with connect() as conn:
            ranks = [first_match_rank(run_search(conn, c.q, k=5), c.targets) for c in cases]
        s = score(ranks, 5)
        for c, r in zip(cases, ranks, strict=True):
            if r is None:
                print(f"  miss: {c.q}")
        print(f"{len(cases)} questions · recall@5 {s['recall@5']:.2f} · recall@1 "
              f"{s['recall@1']:.2f} · MRR {s['mrr']:.2f}")
        if s["recall@5"] < args.min_recall:
            print(f"FAIL: recall@5 below {args.min_recall}")
            sys.exit(1)

    if args.command == "check":
        from pathlib import Path

        from clausewise.answer import DISCLAIMER
        from clausewise.lease.check import check_lease

        report = check_lease(Path(args.pdf).read_bytes())
        marks = {"ok": "OK   ", "check": "CHECK", "likely_unlawful": "ISSUE",
                 "not_covered": "  ?  "}
        for f in report.rule_findings:
            print(f"[{marks[f.verdict]}] {f.title}: {f.explanation}")
            for label, link in f.citations:
                print(f"          {label}  {link}")
        for f in report.clause_findings:
            print(f"\n[{marks[f.verdict]}] \"{f.clause}\"\n          {f.reason}")
            for hit in f.sources:
                print(f"          {hit.heading_path.split(' > ')[-1]}  {hit.link}")
        print(f"\n{report.problems} likely problem(s). {DISCLAIMER}")

    if args.command == "ask":
        from clausewise.answer import DISCLAIMER, answer
        from clausewise.retrieve import search as run_search
        from clausewise.store import connect

        with connect() as conn:
            hits = run_search(conn, args.question)
        result = answer(args.question, hits)
        print(result.text, end="\n\n")
        for n, hit in enumerate(result.sources, start=1):
            print(f"[{n}] {hit.source_title.split(',')[0]}: {hit.heading_path.split(' > ')[-1]}")
            print(f"    {hit.link}")
        print(f"\n{DISCLAIMER}")

    if args.command == "search":
        from clausewise.retrieve import search as run_search
        from clausewise.store import connect

        scopes = ("residential", "general", "rooming", "other", "admin") if args.all_scopes else (
            "residential", "general")
        with connect() as conn:
            for hit in run_search(conn, args.query, scopes=scopes, k=args.k):
                where = hit.heading_path.split(" > ")[-1]
                print(f"{hit.score:6.2f}  [{hit.scope}] {hit.source_title.split(',')[0]}: {where}")
                print(f"        {hit.link}")

    if args.command == "ingest":
        from clausewise.ingest.run import ingest_rta_guidance, ingest_rtra_act

        if args.which in ("all", "act"):
            ingest_rtra_act()
        if args.which in ("all", "rta"):
            ingest_rta_guidance()

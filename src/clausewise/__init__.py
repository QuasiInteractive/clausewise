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
    args = parser.parse_args()

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

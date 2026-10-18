"""Clausewise: check a Queensland lease against the official tenancy rules, with citations."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="clausewise")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="fetch, parse, embed and store the official sources")
    args = parser.parse_args()

    if args.command == "ingest":
        from clausewise.ingest.run import ingest_rtra_act

        ingest_rtra_act()

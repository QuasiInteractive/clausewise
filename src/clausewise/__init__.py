"""Clausewise: check a Queensland lease against the official tenancy rules, with citations."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="clausewise")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="fetch, parse, embed and store the official sources")
    ingest.add_argument("which", nargs="?", choices=["all", "act", "rta"], default="all")
    args = parser.parse_args()

    if args.command == "ingest":
        from clausewise.ingest.run import ingest_rta_guidance, ingest_rtra_act

        if args.which in ("all", "act"):
            ingest_rtra_act()
        if args.which in ("all", "rta"):
            ingest_rta_guidance()

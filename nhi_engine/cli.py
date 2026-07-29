"""CLI for the NHI engine.

Usage:
    nhi-engine classify --in raw.json --out inventory.json
"""

from __future__ import annotations

import argparse
import sys

from nhi_engine.inventory import write_inventory
from nhi_engine.schema import RawSchemaError, load_raw_records


def _run_classify(args: argparse.Namespace) -> int:
    try:
        records = load_raw_records(args.input)
    except RawSchemaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_inventory(records, args.output)
    print(f"Classified {len(records)} record(s) -> {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nhi-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify_parser = subparsers.add_parser(
        "classify",
        help="Classify raw identity records as human/nhi and write a "
        "schema-1.0 inventory file.",
    )
    classify_parser.add_argument(
        "--in",
        dest="input",
        required=True,
        help="Path to a JSON array of raw identity records.",
    )
    classify_parser.add_argument(
        "--out",
        dest="output",
        required=True,
        help="Path to write the classified inventory JSON file.",
    )
    classify_parser.set_defaults(func=_run_classify)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

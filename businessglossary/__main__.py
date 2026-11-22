"""``python -m businessglossary validate|export``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from businessglossary.export import to_json, to_jsonld
from businessglossary.model import load_glossary
from businessglossary.validate import validate

EXPORTERS = {"json": to_json, "jsonld": to_jsonld}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="businessglossary")
    parser.add_argument("--dir", type=Path, default=Path("glossary"), help="directory of scheme YAML files")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check the glossary; exit 1 on any problem")
    export = sub.add_parser("export", help="write the glossary as JSON or SKOS JSON-LD")
    export.add_argument("--format", choices=sorted(EXPORTERS), default="json")
    export.add_argument("--out", type=Path, help="output file (default: stdout)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    schemes = load_glossary(args.dir)
    problems = validate(schemes)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    if args.command == "validate":
        n = sum(len(s.concepts) for s in schemes)
        print(f"ok: {n} concepts in {len(schemes)} schemes")
        return 0
    text = json.dumps(EXPORTERS[args.format](schemes), indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

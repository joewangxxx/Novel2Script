from __future__ import annotations

import argparse
from typing import Sequence

from novel2script.exporters.fountain_exporter import export_fountain
from novel2script.io import write_yaml
from novel2script.validation import validate_screenplay


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="novel2script")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("yaml_path")
    validate_parser.add_argument("--schema", required=True)
    validate_parser.add_argument("--out", required=True)

    export_parser = subparsers.add_parser("export-fountain")
    export_parser.add_argument("yaml_path")
    export_parser.add_argument("--out", required=True)
    export_parser.add_argument("--map", dest="map_path")

    args = parser.parse_args(argv)
    if args.command == "validate":
        report = validate_screenplay(args.yaml_path, args.schema)
        write_yaml(report, args.out)
        return 0 if report["overall_passed"] else 1
    if args.command == "export-fountain":
        export_fountain(args.yaml_path, args.out, args.map_path)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

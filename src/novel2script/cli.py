from __future__ import annotations

import argparse
import sys
from typing import Sequence

from novel2script.exporters.fountain_exporter import export_fountain
from novel2script.generators.screenplay_builder import build_screenplay
from novel2script.io import read_text, read_yaml, write_yaml
from novel2script.parsers.novel_parser import parse_novel_text
from novel2script.planners.character_bible_builder import build_character_bible
from novel2script.planners.outline_builder import build_outline
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

    parse_novel_parser = subparsers.add_parser("parse-novel")
    parse_novel_parser.add_argument("input_path")
    parse_novel_parser.add_argument("--out", required=True)

    build_outline_parser = subparsers.add_parser("build-outline")
    build_outline_parser.add_argument("story_map_path")
    build_outline_parser.add_argument("--out", required=True)

    build_character_bible_parser = subparsers.add_parser("build-character-bible")
    build_character_bible_parser.add_argument("story_map_path")
    build_character_bible_parser.add_argument("--out", required=True)

    build_screenplay_parser = subparsers.add_parser("build-screenplay")
    build_screenplay_parser.add_argument("--story-map", required=True)
    build_screenplay_parser.add_argument("--outline", required=True)
    build_screenplay_parser.add_argument("--character-bible", required=True)
    build_screenplay_parser.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    if args.command == "validate":
        report = validate_screenplay(args.yaml_path, args.schema)
        write_yaml(report, args.out)
        return 0 if report["overall_passed"] else 1
    if args.command == "export-fountain":
        export_fountain(args.yaml_path, args.out, args.map_path)
        return 0
    if args.command == "parse-novel":
        try:
            text = read_text(args.input_path)
        except OSError as exc:
            print(f"parse-novel failed: {exc}", file=sys.stderr)
            return 1
        write_yaml(parse_novel_text(text, input_file=args.input_path), args.out)
        return 0
    if args.command == "build-outline":
        try:
            story_map = read_yaml(args.story_map_path)
        except OSError as exc:
            print(f"build-outline failed: {exc}", file=sys.stderr)
            return 1
        write_yaml(build_outline(story_map, story_map_file=args.story_map_path), args.out)
        return 0
    if args.command == "build-character-bible":
        try:
            story_map = read_yaml(args.story_map_path)
        except OSError as exc:
            print(f"build-character-bible failed: {exc}", file=sys.stderr)
            return 1
        write_yaml(
            build_character_bible(story_map, story_map_file=args.story_map_path),
            args.out,
        )
        return 0
    if args.command == "build-screenplay":
        try:
            story_map = read_yaml(args.story_map)
            outline = read_yaml(args.outline)
            character_bible = read_yaml(args.character_bible)
        except OSError as exc:
            print(f"build-screenplay failed: {exc}", file=sys.stderr)
            return 1
        write_yaml(
            build_screenplay(
                story_map,
                outline,
                character_bible,
                story_map_file=args.story_map,
                outline_file=args.outline,
                character_bible_file=args.character_bible,
            ),
            args.out,
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

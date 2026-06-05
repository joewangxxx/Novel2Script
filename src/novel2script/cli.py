from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from novel2script.agents.story_semantic_parser import run_story_semantic_parser
from novel2script.exporters.fountain_exporter import export_fountain
from novel2script.generators.screenplay_builder import build_screenplay
from novel2script.importers.fountain_importer import sync_fountain_to_yaml
from novel2script.io import read_text, read_yaml, write_yaml
from novel2script.parsers.novel_parser import parse_novel_text
from novel2script.planners.character_bible_builder import build_character_bible
from novel2script.planners.outline_builder import build_outline
from novel2script.quality.quality_report import build_quality_report, render_quality_dashboard
from novel2script.reviewers.review_report import build_review_report
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

    import_parser = subparsers.add_parser("import-fountain")
    import_parser.add_argument("--screenplay", required=True)
    import_parser.add_argument("--fountain", required=True)
    import_parser.add_argument("--map", required=True, dest="map_path")
    import_parser.add_argument("--out", required=True)
    import_parser.add_argument("--report", required=True)

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

    review_screenplay_parser = subparsers.add_parser("review-screenplay")
    review_screenplay_parser.add_argument("--screenplay", required=True)
    review_screenplay_parser.add_argument("--character-bible", required=True)
    review_screenplay_parser.add_argument("--story-map")
    review_screenplay_parser.add_argument("--outline")
    review_screenplay_parser.add_argument("--out", required=True)

    quality_parser = subparsers.add_parser("evaluate-quality")
    quality_parser.add_argument("--screenplay", required=True)
    quality_parser.add_argument("--validation-report", required=True)
    quality_parser.add_argument("--review-report", required=True)
    quality_parser.add_argument("--roundtrip-report")
    quality_parser.add_argument("--out", required=True)
    quality_parser.add_argument("--markdown")

    run_agent_parser = subparsers.add_parser("run-agent")
    run_agent_parser.add_argument("agent_name", choices=["story-semantic-parser"])
    run_agent_parser.add_argument("--story-map", required=True)
    run_agent_parser.add_argument("--out", required=True)
    run_agent_parser.add_argument("--run-log", required=True)
    run_agent_parser.add_argument("--quality-report")
    run_agent_parser.add_argument("--dry-run", action="store_true", default=True)

    args = parser.parse_args(argv)
    if args.command == "validate":
        report = validate_screenplay(args.yaml_path, args.schema)
        write_yaml(report, args.out)
        return 0 if report["overall_passed"] else 1
    if args.command == "export-fountain":
        export_fountain(args.yaml_path, args.out, args.map_path)
        return 0
    if args.command == "import-fountain":
        try:
            sync_fountain_to_yaml(
                args.screenplay,
                args.fountain,
                args.map_path,
                args.out,
                args.report,
            )
        except OSError as exc:
            print(f"import-fountain failed: {exc}", file=sys.stderr)
            return 1
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
    if args.command == "review-screenplay":
        try:
            screenplay = read_yaml(args.screenplay)
            character_bible = read_yaml(args.character_bible)
            story_map = read_yaml(args.story_map) if args.story_map else None
            outline = read_yaml(args.outline) if args.outline else None
        except OSError as exc:
            print(f"review-screenplay failed: {exc}", file=sys.stderr)
            return 1
        source_artifacts = {"character_bible": args.character_bible}
        if args.story_map:
            source_artifacts["story_map"] = args.story_map
        if args.outline:
            source_artifacts["outline"] = args.outline
        write_yaml(
            build_review_report(
                screenplay,
                character_bible_doc=character_bible,
                outline_doc=outline,
                story_map_doc=story_map,
                source_screenplay=args.screenplay,
                source_artifacts=source_artifacts,
            ),
            args.out,
        )
        return 0
    if args.command == "evaluate-quality":
        try:
            screenplay = read_yaml(args.screenplay)
            validation_report = read_yaml(args.validation_report)
            review_report = read_yaml(args.review_report)
            roundtrip_report = (
                read_yaml(args.roundtrip_report) if args.roundtrip_report else None
            )
        except OSError as exc:
            print(f"evaluate-quality failed: {exc}", file=sys.stderr)
            return 1
        quality_report = build_quality_report(
            screenplay,
            validation_report,
            review_report,
            roundtrip_report_doc=roundtrip_report,
            source_paths={
                "screenplay": args.screenplay,
                "validation_report": args.validation_report,
                "review_report": args.review_report,
                "fountain_roundtrip_report": args.roundtrip_report or "",
                "quality_report_yaml": args.out,
                "quality_dashboard_markdown": args.markdown or "",
            },
        )
        write_yaml(quality_report, args.out)
        if args.markdown:
            markdown_path = Path(args.markdown)
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(
                render_quality_dashboard(quality_report),
                encoding="utf-8",
                newline="\n",
            )
        return 0
    if args.command == "run-agent" and args.agent_name == "story-semantic-parser":
        try:
            run_story_semantic_parser(
                args.story_map,
                out_path=args.out,
                run_log_path=args.run_log,
                quality_report_path=args.quality_report,
                dry_run=args.dry_run,
            )
        except OSError as exc:
            print(f"run-agent story-semantic-parser failed: {exc}", file=sys.stderr)
            return 1
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

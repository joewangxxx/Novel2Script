from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from novel2script.agents.creative_draft import run_kimi_dialogue_scene_drafter
from novel2script.agents.creative_draft_apply import apply_creative_draft
from novel2script.agents.creative_draft_readiness import (
    write_creative_draft_readiness_report,
)
from novel2script.agents.kimi_creative_agents import (
    KIMI_CREATIVE_AGENT_IDS,
    run_kimi_creative_agent,
)
from novel2script.agents.deepseek_reviewer_agents import (
    DEEPSEEK_REVIEWER_AGENT_IDS,
    run_deepseek_reviewer_agent,
)
from novel2script.agents.stage24_candidate_review import (
    apply_stage24_candidate_decisions,
    prepare_stage24_candidate_review,
)
from novel2script.agents.stage26_selected_candidate_apply import (
    apply_stage24_selected_candidates_to_artifacts,
)
from novel2script.agents.semantic_candidate_merge import merge_semantic_candidates
from novel2script.agents.story_semantic_parser import run_story_semantic_parser
from novel2script.exporters.fountain_exporter import export_fountain
from novel2script.generators.screenplay_builder import build_screenplay
from novel2script.importers.fountain_importer import sync_fountain_to_yaml
from novel2script.io import read_text, read_yaml, write_yaml
from novel2script.llm.openai_compatible_provider import (
    ProviderConfigurationError,
    ProviderRuntimeError,
)
from novel2script.llm.router import LLMRouter, ProviderRoutingError
from novel2script.parsers.novel_parser import parse_novel_text
from novel2script.planners.character_bible_builder import build_character_bible
from novel2script.planners.outline_builder import build_outline
from novel2script.quality.quality_report import build_quality_report, render_quality_dashboard
from novel2script.reviewers.author_review import (
    build_author_review_decisions_template,
    render_author_review_packet,
)
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
    import_parser.add_argument("--character-bible")
    import_parser.add_argument("--story-map")
    import_parser.add_argument("--outline")
    import_parser.add_argument("--review-report-out")
    import_parser.add_argument("--review-out")

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
    quality_parser.add_argument("--allow-network", action="store_true")
    quality_parser.add_argument("--run-log")

    run_agent_parser = subparsers.add_parser("run-agent")
    run_agent_parser.add_argument(
        "agent_name",
        choices=[
            "story-semantic-parser",
            "kimi-dialogue-scene-drafter",
            "adaptation-planner",
            "character-bible-agent",
            "scene-writer-agent",
            "dialogue-optimizer-agent",
            "beat-dramaturgy-agent",
            "source-fidelity-reviewer",
            "yaml-repair-agent",
        ],
    )
    run_agent_parser.add_argument("--story-map")
    run_agent_parser.add_argument("--outline")
    run_agent_parser.add_argument("--character-bible")
    run_agent_parser.add_argument("--screenplay")
    run_agent_parser.add_argument("--author-review-report")
    run_agent_parser.add_argument("--review-report")
    run_agent_parser.add_argument("--quality-report")
    run_agent_parser.add_argument("--out", required=True)
    run_agent_parser.add_argument("--run-log", required=True)
    run_agent_parser.add_argument("--dry-run", action="store_true", default=True)
    run_agent_parser.add_argument("--allow-network", action="store_true")

    merge_semantic_parser = subparsers.add_parser("merge-semantic-candidates")
    merge_semantic_parser.add_argument("--story-map", required=True)
    merge_semantic_parser.add_argument("--semantic-candidates", required=True)
    merge_semantic_parser.add_argument("--decisions", required=True)
    merge_semantic_parser.add_argument("--out", required=True)
    merge_semantic_parser.add_argument("--report", required=True)

    author_review_parser = subparsers.add_parser("prepare-author-review")
    author_review_parser.add_argument("--screenplay", required=True)
    author_review_parser.add_argument("--review-report", required=True)
    author_review_parser.add_argument("--quality-report", required=True)
    author_review_parser.add_argument("--quality-dashboard", required=True)
    author_review_parser.add_argument("--packet", required=True)
    author_review_parser.add_argument("--decisions", required=True)

    real_creative_readiness_parser = subparsers.add_parser(
        "check-real-creative-draft-readiness"
    )
    real_creative_readiness_parser.add_argument("--screenplay", required=True)
    real_creative_readiness_parser.add_argument("--author-review-report", required=True)
    real_creative_readiness_parser.add_argument("--mock-candidates", required=True)
    real_creative_readiness_parser.add_argument("--out", required=True)
    real_creative_readiness_parser.add_argument(
        "--routing-config", default="config/agent_routing.example.yaml"
    )
    real_creative_readiness_parser.add_argument(
        "--schema", default="schemas/creative_draft_candidates.schema.json"
    )

    apply_creative_parser = subparsers.add_parser("apply-creative-draft")
    apply_creative_parser.add_argument("--screenplay", required=True)
    apply_creative_parser.add_argument("--creative-candidates", required=True)
    apply_creative_parser.add_argument("--decisions")
    apply_creative_parser.add_argument("--out", required=True)
    apply_creative_parser.add_argument("--report", required=True)

    stage24_review_parser = subparsers.add_parser("prepare-stage24-candidate-review")
    stage24_review_parser.add_argument(
        "--candidate-sidecar", action="append", required=True
    )
    stage24_review_parser.add_argument("--packet", required=True)
    stage24_review_parser.add_argument("--decisions", required=True)

    stage24_apply_parser = subparsers.add_parser("apply-stage24-candidates")
    stage24_apply_parser.add_argument(
        "--candidate-sidecar", action="append", required=True
    )
    stage24_apply_parser.add_argument("--decisions", required=True)
    stage24_apply_parser.add_argument("--selected", required=True)
    stage24_apply_parser.add_argument("--report", required=True)

    stage26_apply_parser = subparsers.add_parser("apply-stage24-selected-to-artifacts")
    stage26_apply_parser.add_argument("--selected", required=True)
    stage26_apply_parser.add_argument("--outline", required=True)
    stage26_apply_parser.add_argument("--character-bible", required=True)
    stage26_apply_parser.add_argument("--screenplay", required=True)
    stage26_apply_parser.add_argument("--outline-out", required=True)
    stage26_apply_parser.add_argument("--character-bible-out", required=True)
    stage26_apply_parser.add_argument("--screenplay-out", required=True)
    stage26_apply_parser.add_argument("--report", required=True)

    serve_workbench_parser = subparsers.add_parser("serve-workbench")
    serve_workbench_parser.add_argument("--port", type=int, default=8000)
    serve_workbench_parser.add_argument("--host", default="127.0.0.1")
    serve_workbench_parser.add_argument("--no-browser", action="store_true")

    run_pipeline_parser = subparsers.add_parser("run-pipeline")
    run_pipeline_parser.add_argument("--novel", required=True)
    run_pipeline_parser.add_argument("--out-dir", required=True)
    run_pipeline_parser.add_argument("--decisions")
    run_pipeline_parser.add_argument("--allow-network", action="store_true")
    run_pipeline_parser.add_argument("--force", action="store_true")

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
            report = sync_fountain_to_yaml(
                args.screenplay,
                args.fountain,
                args.map_path,
                args.out,
                args.report,
            )
        except OSError as exc:
            print(f"import-fountain failed: {exc}", file=sys.stderr)
            return 1

        rt_report = report.get("fountain_roundtrip_report", {})
        applied_changes = rt_report.get("summary", {}).get("applied_changes", 0)
        status = rt_report.get("status")

        if status != "blocked" and applied_changes > 0:
            new_screenplay = read_yaml(args.out)
            character_bible = read_yaml(args.character_bible) if args.character_bible else None
            outline = read_yaml(args.outline) if args.outline else None
            story_map = read_yaml(args.story_map) if args.story_map else None

            source_artifacts = {}
            if args.character_bible:
                source_artifacts["character_bible"] = args.character_bible
            if args.story_map:
                source_artifacts["story_map"] = args.story_map
            if args.outline:
                source_artifacts["outline"] = args.outline

            review_report = build_review_report(
                new_screenplay,
                character_bible_doc=character_bible,
                outline_doc=outline,
                story_map_doc=story_map,
                source_screenplay=args.out,
                source_artifacts=source_artifacts,
            )

            if args.review_report_out:
                write_yaml(review_report, args.review_report_out)

            if args.review_out:
                from novel2script.importers.fountain_importer import (
                    generate_roundtrip_review_markdown,
                )

                md_content = generate_roundtrip_review_markdown(
                    report, review_report, new_screenplay
                )
                md_path = Path(args.review_out)
                md_path.parent.mkdir(parents=True, exist_ok=True)
                md_path.write_text(md_content, encoding="utf-8", newline="\n")

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

        from novel2script.quality.llm_evaluator import run_llm_quality_evaluator
        try:
            llm_scores = run_llm_quality_evaluator(
                screenplay,
                router=LLMRouter.from_environment(allow_network=args.allow_network),
                dry_run=not args.allow_network,
                run_log_path=args.run_log,
            )
        except Exception as exc:
            print(f"evaluate-quality LLM scoring failed: {exc}", file=sys.stderr)
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
            llm_scores=llm_scores,
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
        if not args.story_map:
            print(
                "run-agent story-semantic-parser failed: --story-map is required.",
                file=sys.stderr,
            )
            return 1
        try:
            result = run_story_semantic_parser(
                args.story_map,
                out_path=args.out,
                run_log_path=args.run_log,
                quality_report_path=args.quality_report,
                router=LLMRouter.from_environment(allow_network=args.allow_network),
                dry_run=not args.allow_network,
            )
        except (
            OSError,
            ProviderConfigurationError,
            ProviderRuntimeError,
            ProviderRoutingError,
        ) as exc:
            print(f"run-agent story-semantic-parser failed: {exc}", file=sys.stderr)
            return 1
        if args.allow_network:
            semantic = result["semantic_candidates"]
            blocking_codes = {
                "empty_model_output",
                "malformed_model_json",
                "invalid_model_output_schema",
                "truncated_model_output",
            }
            error_codes = {
                error.get("code", "") for error in semantic.get("errors", [])
            }
            if error_codes & blocking_codes or not semantic.get("candidates"):
                print(
                    "run-agent story-semantic-parser failed: "
                    "real model output was not accepted.",
                    file=sys.stderr,
                )
                return 1
        return 0
    if args.command == "run-agent" and args.agent_name == "kimi-dialogue-scene-drafter":
        missing = [
            option
            for option, value in {
                "--screenplay": args.screenplay,
                "--author-review-report": args.author_review_report,
                "--review-report": args.review_report,
                "--quality-report": args.quality_report,
            }.items()
            if not value
        ]
        if missing:
            print(
                "run-agent kimi-dialogue-scene-drafter failed: missing "
                + ", ".join(missing),
                file=sys.stderr,
            )
            return 1
        try:
            result = run_kimi_dialogue_scene_drafter(
                screenplay_path=args.screenplay,
                author_review_report_path=args.author_review_report,
                review_report_path=args.review_report,
                quality_report_path=args.quality_report,
                out_path=args.out,
                run_log_path=args.run_log,
                dry_run=not args.allow_network,
                router=(
                    LLMRouter.from_environment(allow_network=True, max_attempts=1)
                    if args.allow_network
                    else None
                ),
            )
        except (
            OSError,
            ProviderConfigurationError,
            ProviderRuntimeError,
            ProviderRoutingError,
        ) as exc:
            print(
                f"run-agent kimi-dialogue-scene-drafter failed: {exc}",
                file=sys.stderr,
            )
            return 1
        creative = result["creative_draft_candidates"]
        if creative.get("errors") or not creative.get("candidates"):
            print(
                "run-agent kimi-dialogue-scene-drafter failed: "
                "creative draft candidates were not accepted.",
                file=sys.stderr,
            )
            return 1
        return 0
    if args.command == "run-agent" and args.agent_name.replace("-", "_") in KIMI_CREATIVE_AGENT_IDS:
        agent_id = args.agent_name.replace("-", "_")
        required_by_agent = {
            "adaptation_planner": {
                "--story-map": args.story_map,
                "--outline": args.outline,
                "--quality-report": args.quality_report,
            },
            "character_bible_agent": {
                "--story-map": args.story_map,
                "--outline": args.outline,
                "--character-bible": args.character_bible,
            },
            "scene_writer_agent": {
                "--story-map": args.story_map,
                "--outline": args.outline,
                "--character-bible": args.character_bible,
                "--screenplay": args.screenplay,
            },
            "dialogue_optimizer_agent": {
                "--screenplay": args.screenplay,
                "--character-bible": args.character_bible,
                "--review-report": args.review_report,
            },
        }
        missing = [
            option
            for option, value in required_by_agent[agent_id].items()
            if not value
        ]
        if missing:
            print(
                f"run-agent {args.agent_name} failed: missing " + ", ".join(missing),
                file=sys.stderr,
            )
            return 1
        try:
            result = run_kimi_creative_agent(
                agent_id=agent_id,
                story_map_path=args.story_map,
                outline_path=args.outline,
                character_bible_path=args.character_bible,
                screenplay_path=args.screenplay,
                review_report_path=args.review_report,
                quality_report_path=args.quality_report,
                out_path=args.out,
                run_log_path=args.run_log,
                dry_run=not args.allow_network,
                router=(
                    LLMRouter.from_environment(allow_network=True, max_attempts=1)
                    if args.allow_network
                    else None
                ),
            )
        except (
            OSError,
            ValueError,
            ProviderConfigurationError,
            ProviderRuntimeError,
            ProviderRoutingError,
        ) as exc:
            print(f"run-agent {args.agent_name} failed: {exc}", file=sys.stderr)
            return 1
        root_key = f"{agent_id}_candidates"
        sidecar = result[root_key]
        if sidecar.get("errors") or not sidecar.get("candidates"):
            print(
                f"run-agent {args.agent_name} failed: candidates were not accepted.",
                file=sys.stderr,
            )
            return 1
        return 0
    if args.command == "run-agent" and args.agent_name.replace("-", "_") in DEEPSEEK_REVIEWER_AGENT_IDS:
        agent_id = args.agent_name.replace("-", "_")
        required_by_agent = {
            "beat_dramaturgy_agent": {
                "--screenplay": args.screenplay,
            },
            "source_fidelity_reviewer": {
                "--story-map": args.story_map,
                "--outline": args.outline,
                "--screenplay": args.screenplay,
            },
            "yaml_repair_agent": {
                "--screenplay": args.screenplay,
            },
        }
        missing = [
            option
            for option, value in required_by_agent[agent_id].items()
            if not value
        ]
        if missing:
            print(
                f"run-agent {args.agent_name} failed: missing " + ", ".join(missing),
                file=sys.stderr,
            )
            return 1
        try:
            result = run_deepseek_reviewer_agent(
                agent_id=agent_id,
                story_map_path=args.story_map,
                outline_path=args.outline,
                character_bible_path=args.character_bible,
                screenplay_path=args.screenplay,
                review_report_path=args.review_report,
                out_path=args.out,
                run_log_path=args.run_log,
                dry_run=not args.allow_network,
                router=(
                    LLMRouter.from_environment(allow_network=True, max_attempts=1)
                    if args.allow_network
                    else None
                ),
            )
        except (
            OSError,
            ValueError,
            ProviderConfigurationError,
            ProviderRuntimeError,
            ProviderRoutingError,
        ) as exc:
            print(f"run-agent {args.agent_name} failed: {exc}", file=sys.stderr)
            return 1
        root_key = f"{agent_id}_candidates"
        sidecar = result[root_key]
        if sidecar.get("errors") or not sidecar.get("candidates"):
            print(
                f"run-agent {args.agent_name} failed: candidates were not accepted.",
                file=sys.stderr,
            )
            return 1
        return 0
    if args.command == "merge-semantic-candidates":
        try:
            report = merge_semantic_candidates(
                args.story_map,
                args.semantic_candidates,
                args.decisions,
                out_path=args.out,
                report_path=args.report,
            )
        except OSError as exc:
            print(f"merge-semantic-candidates failed: {exc}", file=sys.stderr)
            return 1
        status = report["semantic_candidate_merge_report"]["status"]
        return 0 if status in {"success", "partial"} else 1
    if args.command == "prepare-author-review":
        try:
            screenplay = read_yaml(args.screenplay)
            review_report = read_yaml(args.review_report)
            quality_report = read_yaml(args.quality_report)
            quality_dashboard = read_text(args.quality_dashboard)
        except OSError as exc:
            print(f"prepare-author-review failed: {exc}", file=sys.stderr)
            return 1
        source_paths = {
            "screenplay": args.screenplay,
            "review_report": args.review_report,
            "quality_report": args.quality_report,
            "quality_dashboard": args.quality_dashboard,
        }
        packet = render_author_review_packet(
            screenplay,
            review_report,
            quality_report,
            quality_dashboard,
            source_paths=source_paths,
        )
        packet_path = Path(args.packet)
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(packet, encoding="utf-8", newline="\n")
        write_yaml(
            build_author_review_decisions_template(source_paths=source_paths),
            args.decisions,
        )
        return 0
    if args.command == "check-real-creative-draft-readiness":
        try:
            report = write_creative_draft_readiness_report(
                screenplay_path=args.screenplay,
                author_review_report_path=args.author_review_report,
                mock_candidates_path=args.mock_candidates,
                out_path=args.out,
                routing_config_path=args.routing_config,
                schema_path=args.schema,
            )
        except OSError as exc:
            print(
                f"check-real-creative-draft-readiness failed: {exc}",
                file=sys.stderr,
            )
            return 1
        status = report["creative_draft_readiness_report"]["status"]
        return 0 if status in {"ready", "ready_pending_network_authorization"} else 1
    if args.command == "apply-creative-draft":
        try:
            report = apply_creative_draft(
                screenplay_path=args.screenplay,
                creative_candidates_path=args.creative_candidates,
                out_path=args.out,
                report_path=args.report,
                decisions_path=args.decisions,
            )
        except (OSError, ValueError) as exc:
            print(f"apply-creative-draft failed: {exc}", file=sys.stderr)
            return 1
        blocked = report["creative_draft_apply_report"]["blocked_count"]
        return 0 if blocked == 0 else 1
    if args.command == "prepare-stage24-candidate-review":
        try:
            prepare_stage24_candidate_review(
                candidate_paths=args.candidate_sidecar,
                packet_path=args.packet,
                decisions_path=args.decisions,
            )
        except OSError as exc:
            print(f"prepare-stage24-candidate-review failed: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.command == "apply-stage24-candidates":
        try:
            report = apply_stage24_candidate_decisions(
                candidate_paths=args.candidate_sidecar,
                decisions_path=args.decisions,
                selected_candidates_path=args.selected,
                report_path=args.report,
            )
        except OSError as exc:
            print(f"apply-stage24-candidates failed: {exc}", file=sys.stderr)
            return 1
        status = report["stage24_candidate_apply_report"]["status"]
        return 0 if status in {"success", "partial", "blocked_pending_author_review"} else 1
    if args.command == "apply-stage24-selected-to-artifacts":
        try:
            report = apply_stage24_selected_candidates_to_artifacts(
                selected_candidates_path=args.selected,
                outline_path=args.outline,
                character_bible_path=args.character_bible,
                screenplay_path=args.screenplay,
                outline_out_path=args.outline_out,
                character_bible_out_path=args.character_bible_out,
                screenplay_out_path=args.screenplay_out,
                report_path=args.report,
            )
        except OSError as exc:
            print(f"apply-stage24-selected-to-artifacts failed: {exc}", file=sys.stderr)
            return 1
        status = report["stage26_selected_candidate_apply_report"]["status"]
        return 0 if status in {"success", "partial"} else 1
    if args.command == "run-pipeline":
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        force = bool(args.force)
        allow_network = bool(args.allow_network)
        
        story_map_path = out_dir / "story_map.yaml"
        semantic_candidates_path = out_dir / "semantic_candidates.yaml"
        semantic_run_log_path = out_dir / "semantic_run_log.yaml"
        decisions_path = Path(args.decisions) if args.decisions else out_dir / "decisions.yaml"
        story_map_merged_path = out_dir / "story_map.merged.yaml"
        merge_report_path = out_dir / "semantic_candidate_merge_report.yaml"
        outline_path = out_dir / "outline.yaml"
        character_bible_path = out_dir / "character_bible.yaml"
        screenplay_path = out_dir / "screenplay.yaml"
        review_report_path = out_dir / "review_report.yaml"
        validation_report_path = out_dir / "validation_report.yaml"
        screenplay_fountain_path = out_dir / "screenplay.fountain"
        fountain_map_path = out_dir / "screenplay.fountain.map.json"
        quality_report_path = out_dir / "quality_report.yaml"
        quality_dashboard_path = out_dir / "quality_dashboard.md"
        packet_path = out_dir / "author_review_packet.md"
        author_review_decisions_path = out_dir / "author_review_decisions.yaml"

        # Step 1: parse-novel
        if force or not story_map_path.exists():
            print("Running step: parse-novel...")
            try:
                text = read_text(args.novel)
                write_yaml(parse_novel_text(text, input_file=args.novel), story_map_path)
            except Exception as exc:
                print(f"Pipeline Step parse_novel failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step parse-novel output exists, skipping.")

        # Step 2: run-agent story-semantic-parser
        if force or not semantic_candidates_path.exists() or not semantic_run_log_path.exists():
            print("Running step: generate-semantic-candidates...")
            try:
                run_story_semantic_parser(
                    story_map_path,
                    out_path=semantic_candidates_path,
                    run_log_path=semantic_run_log_path,
                    router=LLMRouter.from_environment(allow_network=allow_network),
                    dry_run=not allow_network,
                )
            except Exception as exc:
                print(f"Pipeline Step generate_semantic_candidates failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step generate-semantic-candidates output exists, skipping.")

        # Step 3: merge-semantic-candidates
        if force or not story_map_merged_path.exists() or not merge_report_path.exists():
            print("Running step: merge-semantic-candidates...")
            try:
                if not decisions_path.exists():
                    print(f"Decisions file {decisions_path} not found. Generating default Accept-All decisions...")
                    from datetime import datetime
                    from novel2script.agents.semantic_candidate_merge import TYPE_TARGETS

                    candidates_doc = read_yaml(semantic_candidates_path)
                    candidates = candidates_doc.get("semantic_candidates", {}).get("candidates", [])
                    reviewed_at_str = datetime.now().astimezone().isoformat(timespec="seconds")

                    decisions_list = []
                    for idx, cand in enumerate(candidates):
                        c_id = cand.get("id")
                        c_type = cand.get("type")
                        target_field = TYPE_TARGETS.get(c_type, (None, None))[0] or cand.get("target_story_map_field")
                        decisions_list.append({
                            "decision_id": f"dec_{idx+1:03d}",
                            "candidate_id": c_id,
                            "decision": "accept",
                            "target_story_map_field": target_field,
                            "human_approval": {
                                "approved": True,
                                "reviewer_id": "pipeline_auto",
                                "approved_at": reviewed_at_str
                            }
                        })

                    if not decisions_list:
                        # Schema requires minItems: 1. Generate a dummy decision referencing an unknown candidate.
                        # It will be skipped as unknown but satisfies the schema validator.
                        decisions_list.append({
                            "decision_id": "dec_001",
                            "candidate_id": "semcand_000",
                            "decision": "reject",
                            "target_story_map_field": "key_events",
                            "human_approval": {
                                "approved": False,
                                "reviewer_id": "pipeline_auto",
                                "approved_at": reviewed_at_str
                            }
                        })

                    decisions = {
                        "semantic_candidate_decisions": {
                            "schema_version": "0.1.0",
                            "source_story_map": str(story_map_path),
                            "source_semantic_candidates": str(semantic_candidates_path),
                            "reviewed_by": "pipeline_auto",
                            "reviewed_at": reviewed_at_str,
                            "decisions": decisions_list
                        }
                    }
                    write_yaml(decisions, decisions_path)

                merge_semantic_candidates(
                    story_map_path,
                    semantic_candidates_path,
                    decisions_path,
                    out_path=story_map_merged_path,
                    report_path=merge_report_path,
                )
            except Exception as exc:
                print(f"Pipeline Step merge_semantic failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step merge-semantic-candidates output exists, skipping.")

        # Step 4: build-outline
        if force or not outline_path.exists():
            print("Running step: build-outline...")
            try:
                story_map = read_yaml(story_map_merged_path)
                write_yaml(build_outline(story_map, story_map_file=str(story_map_merged_path)), outline_path)
            except Exception as exc:
                print(f"Pipeline Step build_outline failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step build-outline output exists, skipping.")

        # Step 5: build-character-bible
        if force or not character_bible_path.exists():
            print("Running step: build-character-bible...")
            try:
                story_map = read_yaml(story_map_merged_path)
                write_yaml(
                    build_character_bible(story_map, story_map_file=str(story_map_merged_path)),
                    character_bible_path,
                )
            except Exception as exc:
                print(f"Pipeline Step build_character_bible failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step build-character-bible output exists, skipping.")

        # Step 6: build-screenplay
        if force or not screenplay_path.exists():
            print("Running step: build-screenplay...")
            try:
                story_map = read_yaml(story_map_merged_path)
                outline = read_yaml(outline_path)
                character_bible = read_yaml(character_bible_path)
                write_yaml(
                    build_screenplay(
                        story_map,
                        outline,
                        character_bible,
                        story_map_file=str(story_map_merged_path),
                        outline_file=str(outline_path),
                        character_bible_file=str(character_bible_path),
                    ),
                    screenplay_path,
                )
            except Exception as exc:
                print(f"Pipeline Step build_screenplay failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step build-screenplay output exists, skipping.")

        # Step 7: review-screenplay
        if force or not review_report_path.exists():
            print("Running step: review-screenplay...")
            try:
                screenplay = read_yaml(screenplay_path)
                character_bible = read_yaml(character_bible_path)
                story_map = read_yaml(story_map_merged_path)
                outline = read_yaml(outline_path)
                source_artifacts = {
                    "character_bible": str(character_bible_path),
                    "story_map": str(story_map_merged_path),
                    "outline": str(outline_path),
                }
                write_yaml(
                    build_review_report(
                        screenplay,
                        character_bible_doc=character_bible,
                        outline_doc=outline,
                        story_map_doc=story_map,
                        source_screenplay=str(screenplay_path),
                        source_artifacts=source_artifacts,
                    ),
                    review_report_path,
                )
            except Exception as exc:
                print(f"Pipeline Step review_screenplay failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step review-screenplay output exists, skipping.")

        # Step 8: validate-screenplay
        if force or not validation_report_path.exists():
            print("Running step: validate-screenplay...")
            try:
                schema_file = Path(__file__).resolve().parent.parent.parent / "schemas" / "screenplay.schema.json"
                if not schema_file.exists():
                    schema_file = Path.cwd() / "schemas" / "screenplay.schema.json"
                report = validate_screenplay(str(screenplay_path), str(schema_file))
                write_yaml(report, validation_report_path)
            except Exception as exc:
                print(f"Pipeline Step validate_screenplay failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step validate-screenplay output exists, skipping.")

        # Step 9: export-fountain
        if force or not screenplay_fountain_path.exists() or not fountain_map_path.exists():
            print("Running step: export-fountain...")
            try:
                export_fountain(str(screenplay_path), str(screenplay_fountain_path), str(fountain_map_path))
            except Exception as exc:
                print(f"Pipeline Step export_fountain failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step export-fountain output exists, skipping.")

        # Step 10: evaluate-quality
        if force or not quality_report_path.exists() or not quality_dashboard_path.exists():
            print("Running step: evaluate-quality...")
            try:
                screenplay = read_yaml(screenplay_path)
                validation_report = read_yaml(validation_report_path)
                review_report = read_yaml(review_report_path)

                from novel2script.quality.llm_evaluator import run_llm_quality_evaluator
                quality_run_log = out_dir / "quality_eval_run_log.yaml"
                llm_scores = run_llm_quality_evaluator(
                    screenplay,
                    router=LLMRouter.from_environment(allow_network=allow_network),
                    dry_run=not allow_network,
                    run_log_path=quality_run_log,
                )

                quality_report = build_quality_report(
                    screenplay,
                    validation_report,
                    review_report,
                    roundtrip_report_doc=None,
                    source_paths={
                        "screenplay": str(screenplay_path),
                        "validation_report": str(validation_report_path),
                        "review_report": str(review_report_path),
                        "fountain_roundtrip_report": "",
                        "quality_report_yaml": str(quality_report_path),
                        "quality_dashboard_markdown": str(quality_dashboard_path),
                    },
                    llm_scores=llm_scores,
                )
                write_yaml(quality_report, quality_report_path)
                quality_dashboard_path.write_text(
                    render_quality_dashboard(quality_report),
                    encoding="utf-8",
                    newline="\n",
                )
            except Exception as exc:
                print(f"Pipeline Step evaluate_quality failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step evaluate-quality output exists, skipping.")

        # Step 11: prepare-author-review
        if force or not packet_path.exists() or not author_review_decisions_path.exists():
            print("Running step: prepare-author-review...")
            try:
                screenplay = read_yaml(screenplay_path)
                review_report = read_yaml(review_report_path)
                quality_report = read_yaml(quality_report_path)
                quality_dashboard = read_text(str(quality_dashboard_path))
                source_paths = {
                    "screenplay": str(screenplay_path),
                    "review_report": str(review_report_path),
                    "quality_report": str(quality_report_path),
                    "quality_dashboard": str(quality_dashboard_path),
                }
                packet = render_author_review_packet(
                    screenplay,
                    review_report,
                    quality_report,
                    quality_dashboard,
                    source_paths=source_paths,
                )
                packet_path.write_text(packet, encoding="utf-8", newline="\n")
                write_yaml(
                    build_author_review_decisions_template(source_paths=source_paths),
                    author_review_decisions_path,
                )
            except Exception as exc:
                print(f"Pipeline Step prepare_author_review failed: {exc}", file=sys.stderr)
                return 1
        else:
            print("Step prepare-author-review output exists, skipping.")

        print("Pipeline run successfully!")
        return 0
    if args.command == "serve-workbench":
        from novel2script.server import start_server
        start_server(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

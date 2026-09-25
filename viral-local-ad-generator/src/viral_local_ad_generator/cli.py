from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from .agent_memory import AgentMemory, PipelineHalt, create_memory
from .bfl_client import BFLClient
from .config import Settings, load_settings
from .event_logger import PipelineLogger, suggest_fix_for_error
from .nimble_client import NimbleClient, mock_stories
from .pipeline import (
    discover_outlets,
    discover_stories,
    generate_ads_from_stories,
    generate_videos,
    load_concepts,
    load_outlets,
    load_stories,
    run_pipeline,
    select_stories,
    write_run_artifacts,
)
from .staging import load_campaign_record, stage_campaign_variants


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate local-news-reactive video ad concepts with Nimble and BFL FLUX 3 Video."
    )
    subparsers = parser.add_subparsers(dest="command")
    add_run_parser(subparsers)
    add_discover_outlets_parser(subparsers)
    add_discover_news_parser(subparsers)
    add_generate_ad_parser(subparsers)
    add_generate_video_parser(subparsers)
    add_stage_cdn_parser(subparsers)
    return parser


def add_common_news_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--market", required=True, help='Media market, for example "San Francisco".')
    parser.add_argument("--output", required=True, type=Path, help="Output folder for run artifacts.")
    parser.add_argument("--mock-news", action="store_true", help="Use mock stories instead of calling Nimble.")
    parser.add_argument("--story-title", help="Use a specific real news story title instead of searching.")
    parser.add_argument("--story-url", default="", help="URL for --story-title.")
    parser.add_argument("--story-source", default="", help="Publisher/source for --story-title.")
    parser.add_argument("--story-published-at", default="", help="Published date for --story-title.")
    parser.add_argument("--story-snippet", default="", help="Summary/snippet for --story-title.")
    parser.add_argument("--max-stories", type=int, default=5, help="Maximum number of local stories to use.")
    parser.add_argument("--max-outlets", type=int, default=8, help="Maximum number of local outlets to discover/use.")


def add_discover_outlets_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("discover-outlets", help="Find local news outlets and save outlets.json/outlets.md.")
    parser.add_argument("--market", required=True, help='Media market, for example "San Francisco".')
    parser.add_argument("--output", required=True, type=Path, help="Output folder for outlet artifacts.")
    parser.add_argument("--max-outlets", type=int, default=8, help="Maximum number of local outlets to discover.")


def add_run_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("run", help="One-shot flow: discover news, generate ads, optionally generate video.")
    parser.add_argument("--campaign", required=True, type=Path, help="Path to a campaign script text file.")
    add_common_news_args(parser)
    parser.add_argument("--dry-run", action="store_true", help="Create prompts without submitting BFL jobs.")
    parser.add_argument("--generate", action="store_true", help="Submit generated concepts to BFL FLUX 3 Video.")
    parser.add_argument("--poll", action="store_true", help="Poll BFL generation jobs until ready or failed.")
    parser.add_argument(
        "--download-media",
        action="store_true",
        help="Also download completed BFL videos into OUTPUT/videos. Video URLs are saved to OUTPUT/video_links by default when polling finishes.",
    )
    parser.add_argument("--max-videos", type=int, default=None, help="Maximum number of video concepts/jobs to create.")
    add_memory_args(parser)


def add_memory_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--campaign-id",
        default=None,
        help="Campaign id for Tinybird event memory (default: LH_CAMPAIGN_ID, else the campaign file or output folder name).",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="After a Nimble/BFL error is recorded, keep going with the next variant instead of halting the run.",
    )


def add_discover_news_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("discover-news", help="Find/select news stories and save stories.json/news.md.")
    add_common_news_args(parser)
    parser.add_argument("--outlets", type=Path, help="Optional path to outlets.json from discover-outlets.")


def add_generate_ad_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("generate-ad", help="Create ad scripts/prompts from a saved stories.json file.")
    parser.add_argument("--campaign", required=True, type=Path, help="Path to a campaign script text file.")
    parser.add_argument("--market", required=True, help='Media market, for example "San Francisco".')
    parser.add_argument("--stories", required=True, type=Path, help="Path to stories.json from discover-news.")
    parser.add_argument("--output", required=True, type=Path, help="Output folder for ad artifacts.")
    parser.add_argument("--max-videos", type=int, default=None, help="Maximum number of video concepts/jobs to create.")


def add_generate_video_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("generate-video", help="Submit saved concepts.json to BFL and save video links.")
    parser.add_argument("--concepts", required=True, type=Path, help="Path to concepts.json from generate-ad.")
    parser.add_argument("--output", required=True, type=Path, help="Output folder for video artifacts.")
    parser.add_argument("--poll", action="store_true", help="Poll BFL generation jobs until ready or failed.")
    parser.add_argument("--download-media", action="store_true", help="Also download completed BFL videos into OUTPUT/videos.")
    add_memory_args(parser)


def add_stage_cdn_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "stage-cdn",
        help="Generate scripts for a website campaign record and stage them under STAGING/<campaign_id>/<variant>/.",
    )
    parser.add_argument(
        "--campaign-record",
        required=True,
        type=Path,
        help="Campaign record: a JSON file or an issue body containing a fenced ```json block (id, brief, geo, dims...).",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--stories", type=Path, help="Path to stories.json from discover-news.")
    source.add_argument("--mock-news", action="store_true", help="Use mock stories instead of saved discovery.")
    parser.add_argument("--output", required=True, type=Path, help="Output folder for run artifacts (not staged).")
    parser.add_argument("--staging", required=True, type=Path, help="Staging root, normally cdn/staging.")
    parser.add_argument("--max-stories", type=int, default=1, help="Maximum number of local stories to use.")
    parser.add_argument("--max-videos", type=int, default=3, help="Maximum number of variants to stage.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    settings = load_settings()
    nimble_client = NimbleClient(settings.nimble_api_key, settings.nimble_base_url)
    bfl_client = BFLClient(settings.bfl_api_key, settings.bfl_base_url)

    if args.command == "run":
        if args.dry_run and args.generate:
            parser.error("Use either --dry-run or --generate, not both.")
        if not args.dry_run and not args.generate:
            parser.error("Choose --dry-run to plan or --generate to submit BFL jobs.")
        logger = create_logger(args.output, settings, args)
        attach_logger(logger, nimble_client, bfl_client)
        report_previous_failure(logger)
        logger.emit("cli", "start", {"args": args_to_dict(args)})
        logger.emit_run_started()
        memory = start_memory(args, logger)
        try:
            campaign_script = args.campaign.read_text(encoding="utf-8")
            result = run_pipeline(
                campaign_script=campaign_script,
                market=args.market,
                output_dir=args.output,
                nimble_client=nimble_client,
                bfl_client=bfl_client,
                use_mock_news=args.mock_news,
                dry_run=args.dry_run,
                generate=args.generate,
                poll=args.poll,
                download_media=args.download_media,
                max_stories=args.max_stories,
                max_outlets=args.max_outlets,
                max_videos=args.max_videos,
                story_title=args.story_title,
                story_url=args.story_url,
                story_source=args.story_source,
                story_published_at=args.story_published_at,
                story_snippet=args.story_snippet,
                logger=logger,
                memory=memory,
            )
        except Exception as error:
            handle_failure(logger, error, memory)
            raise
        finish_memory(memory, {"story_count": result["story_count"], "concept_count": result["concept_count"]})
        logger.emit_run_completed(result)
        logger.emit("cli", "finish", {"result": result})
        print(
            f"Created {result['concept_count']} ad concepts from {result['story_count']} stories. "
            f"Artifacts saved to {args.output}"
        )
        return

    if args.command == "discover-outlets":
        logger = create_logger(args.output, settings, args)
        attach_logger(logger, nimble_client, bfl_client)
        report_previous_failure(logger)
        logger.emit("cli", "start", {"args": args_to_dict(args)})
        logger.emit_run_started()
        try:
            outlets = discover_outlets(
                market=args.market,
                output_dir=args.output,
                nimble_client=nimble_client,
                max_outlets=args.max_outlets,
                logger=logger,
            )
        except Exception as error:
            handle_failure(logger, error)
            raise
        logger.emit_run_completed({"outlet_count": len(outlets)})
        logger.emit("cli", "finish", {"outlet_count": len(outlets)})
        print(f"Saved {len(outlets)} outlets to {args.output / 'outlets.json'}")
        return

    if args.command == "discover-news":
        logger = create_logger(args.output, settings, args)
        attach_logger(logger, nimble_client, bfl_client)
        report_previous_failure(logger)
        logger.emit("cli", "start", {"args": args_to_dict(args)})
        logger.emit_run_started()
        try:
            outlets = load_outlets(args.outlets) if args.outlets else None
            stories = discover_stories(
                market=args.market,
                output_dir=args.output,
                nimble_client=nimble_client,
                use_mock_news=args.mock_news,
                max_stories=args.max_stories,
                max_outlets=args.max_outlets,
                outlets=outlets,
                story_title=args.story_title,
                story_url=args.story_url,
                story_source=args.story_source,
                story_published_at=args.story_published_at,
                story_snippet=args.story_snippet,
                logger=logger,
            )
        except Exception as error:
            handle_failure(logger, error)
            raise
        logger.emit_run_completed({"story_count": len(stories)})
        logger.emit("cli", "finish", {"story_count": len(stories)})
        print(f"Saved {len(stories)} stories to {args.output / 'stories.json'}")
        return

    if args.command == "generate-ad":
        logger = create_logger(args.output, settings, args)
        attach_logger(logger, nimble_client, bfl_client)
        report_previous_failure(logger)
        logger.emit("cli", "start", {"args": args_to_dict(args)})
        logger.emit_run_started()
        try:
            stories = load_stories(args.stories)
            campaign_script = args.campaign.read_text(encoding="utf-8")
            concepts = generate_ads_from_stories(
                campaign_script=campaign_script,
                market=args.market,
                stories=stories,
                output_dir=args.output,
                max_videos=args.max_videos,
                logger=logger,
            )
            result = write_run_artifacts(args.output, args.market, stories, concepts, logger=logger)
        except Exception as error:
            handle_failure(logger, error)
            raise
        logger.emit_run_completed(result)
        logger.emit("cli", "finish", {"result": result})
        print(f"Saved {len(concepts)} ad concepts to {args.output / 'concepts.json'}")
        return

    if args.command == "generate-video":
        logger = create_logger(args.output, settings, args)
        attach_logger(logger, nimble_client, bfl_client)
        report_previous_failure(logger)
        logger.emit("cli", "start", {"args": args_to_dict(args)})
        logger.emit_run_started()
        memory = start_memory(args, logger)
        try:
            concepts = load_concepts(args.concepts)
            generate_videos(
                concepts=concepts,
                output_dir=args.output,
                bfl_client=bfl_client,
                poll=args.poll,
                download_media=args.download_media,
                logger=logger,
                memory=memory,
            )
        except Exception as error:
            handle_failure(logger, error, memory)
            raise
        finish_memory(memory, {"concept_count": len(concepts)})
        logger.emit_run_completed({"concept_count": len(concepts)})
        logger.emit("cli", "finish", {"concept_count": len(concepts)})
        print(f"Saved video job artifacts to {args.output}")
        return

    if args.command == "stage-cdn":
        logger = create_logger(args.output, settings, args)
        attach_logger(logger, nimble_client, bfl_client)
        report_previous_failure(logger)
        logger.emit("cli", "start", {"args": args_to_dict(args)})
        logger.emit_run_started()
        memory: AgentMemory | None = None
        try:
            record = load_campaign_record(args.campaign_record)
            memory = start_memory(args, logger, campaign_id=record.id)
            stories = mock_stories(record.geo) if args.mock_news else load_stories(args.stories)
            stories = select_stories(stories, count=args.max_stories)
            if not stories:
                raise ValueError("No brand-safe stories available to stage.")
            concepts = generate_ads_from_stories(
                campaign_script=record.brief,
                market=record.geo,
                stories=stories,
                output_dir=args.output,
                max_videos=args.max_videos,
                logger=logger,
                memory=memory,
            )
            write_run_artifacts(args.output, record.geo, stories, concepts, logger=logger)
            logger.emit("campaign_staging", "input", {"campaign_id": record.id, "staging_root": str(args.staging)})
            variant_dirs = stage_campaign_variants(record, stories, concepts, args.staging)
        except Exception as error:
            handle_failure(logger, error, memory)
            raise
        finish_memory(memory, {"variant_count": len(variant_dirs), "staged_under": str(args.staging / record.id)})
        logger.emit_run_completed({"campaign_id": record.id, "variant_count": len(variant_dirs)})
        logger.emit("cli", "finish", {"campaign_id": record.id, "variant_count": len(variant_dirs)})
        print(f"Staged {len(variant_dirs)} variants under {args.staging / record.id}")

def create_logger(output_dir: Path, settings: Settings, args: argparse.Namespace) -> PipelineLogger:
    return PipelineLogger(
        output_dir=output_dir,
        command=str(args.command),
        tinybird_token=settings.tinybird_token,
        tinybird_base_url=settings.tinybird_base_url,
        tinybird_datasource=settings.tinybird_datasource,
        context={
            "args": args_to_dict(args),
            "tinybird_enabled": bool(settings.tinybird_token),
            "tinybird_base_url": settings.tinybird_base_url,
            "tinybird_datasource": settings.tinybird_datasource,
            "api_key_presence": {
                "nimble": bool(settings.nimble_api_key),
                "bfl": bool(settings.bfl_api_key),
                "tinybird": bool(settings.tinybird_token),
            },
        },
    )


def attach_logger(logger: PipelineLogger, nimble_client: NimbleClient, bfl_client: BFLClient) -> None:
    nimble_client.logger = logger
    bfl_client.logger = logger


def args_to_dict(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in vars(args).items():
        if isinstance(value, Path):
            payload[key] = str(value)
        else:
            payload[key] = value
    return payload


def campaign_id_for(args: argparse.Namespace) -> str:
    explicit = getattr(args, "campaign_id", None) or os.getenv("LH_CAMPAIGN_ID", "")
    if explicit:
        return explicit
    campaign_path = getattr(args, "campaign", None)
    if isinstance(campaign_path, Path):
        return campaign_path.stem
    return Path(args.output).name


def start_memory(args: argparse.Namespace, logger: PipelineLogger, campaign_id: str | None = None) -> AgentMemory:
    memory = create_memory(
        campaign_id or campaign_id_for(args),
        run_id=logger.run_id[:12],
        continue_on_error=bool(getattr(args, "continue_on_error", False)),
    )
    logger.context["agent_memory"] = {"enabled": memory.enabled, "campaign_id": memory.campaign_id}
    skipped = sorted(memory.completed_variants())
    memory.emit(
        "run_started",
        {
            "command": str(args.command),
            "market": getattr(args, "market", None),
            "output_dir": str(args.output),
            "continue_on_error": memory.continue_on_error,
            "previously_ready_variants": skipped,
        },
    )
    if skipped:
        print(f"Agent memory: {len(skipped)} variant(s) already reached bfl_ready for {memory.campaign_id}; they will be skipped.")
    return memory


def finish_memory(memory: AgentMemory | None, summary: dict[str, Any]) -> None:
    if memory is None:
        return
    memory.finish(summary)
    if memory.failed:
        print(f"Run finished with {len(memory.errors)} recorded error(s); see the `error` events for {memory.campaign_id}.", file=sys.stderr)


def handle_failure(logger: PipelineLogger, error: Exception, memory: AgentMemory | None = None) -> None:
    logger.emit_run_failed(error)
    if memory is not None:
        if not isinstance(error, PipelineHalt) and not memory.failed:
            memory.error("pipeline", error)
        memory.finish()
    print(
        f"Run failed: {type(error).__name__}: {error}\nSuggested fix: {suggest_fix_for_error(error)}",
        file=sys.stderr,
    )


def report_previous_failure(logger: PipelineLogger) -> None:
    previous = find_previous_run_status(Path("runs"))
    if not previous or not previous["failed"]:
        return
    logger.emit(
        "preflight.previous_run",
        "failure_detected",
        previous,
        status="warning",
    )
    print(
        "Previous ad-generator run did not complete cleanly.\n"
        f"Previous run: {previous['log_path']}\n"
        f"Reason: {previous['reason']}\n"
        f"Suggested fix: {previous['suggested_fix']}",
        file=sys.stderr,
    )


def find_previous_run_status(runs_dir: Path) -> dict[str, Any] | None:
    if not runs_dir.exists():
        return None
    candidates = [
        path
        for path in runs_dir.glob("*/logs/ad_gen_events.ndjson")
        if path.exists()
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return analyze_run_log(latest)


def analyze_run_log(path: Path) -> dict[str, Any]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not events:
        return {
            "failed": True,
            "log_path": str(path),
            "run_id": "",
            "reason": "Log exists but contains no readable events.",
            "suggested_fix": "Open the log file and verify the run process had permission to write complete NDJSON events.",
        }
    run_id = str(events[-1].get("run_id", ""))
    if run_id:
        events = [event for event in events if str(event.get("run_id", "")) == run_id]
    failed_events = [event for event in events if event.get("status") == "error" or event.get("event_type") == "failed"]
    if failed_events:
        event = failed_events[-1]
        payload = parse_payload(event)
        error_text = payload.get("error") or payload.get("detail") or payload.get("error_type") or "Logged error event."
        return {
            "failed": True,
            "log_path": str(path),
            "run_id": run_id,
            "reason": f"{event.get('stage')}.{event.get('event_type')}: {error_text}",
            "suggested_fix": payload.get("suggested_fix") or suggest_fix_for_error(str(error_text)),
            "failed_stage": event.get("stage"),
        }
    started = any(event.get("stage") == "run_status" and event.get("event_type") == "started" for event in events)
    completed = any(event.get("stage") == "run_status" and event.get("event_type") == "completed" for event in events)
    cli_finished = any(event.get("stage") == "cli" and event.get("event_type") == "finish" for event in events)
    if started and (not completed or not cli_finished):
        last_event = events[-1]
        return {
            "failed": True,
            "log_path": str(path),
            "run_id": run_id,
            "reason": f"Run started but did not emit completion markers. Last event was {last_event.get('stage')}.{last_event.get('event_type')}.",
            "suggested_fix": "Inspect the last event in the log. If it stopped during bfl.poll, poll the saved BFL polling_url or rerun generate-video; otherwise rerun with the same output folder and check stderr.",
            "last_stage": last_event.get("stage"),
            "last_event_type": last_event.get("event_type"),
        }
    if not started and not cli_finished:
        last_event = events[-1]
        return {
            "failed": True,
            "log_path": str(path),
            "run_id": run_id,
            "reason": f"Legacy run did not emit cli.finish. Last event was {last_event.get('stage')}.{last_event.get('event_type')}.",
            "suggested_fix": "Inspect the last event in the log and rerun the same command if the expected artifacts are missing.",
            "last_stage": last_event.get("stage"),
            "last_event_type": last_event.get("event_type"),
        }
    return {
        "failed": False,
        "log_path": str(path),
        "run_id": run_id,
        "reason": "Previous run completed cleanly.",
        "suggested_fix": "",
    }


def parse_payload(event: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(str(event.get("payload_json") or "{}"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    main()

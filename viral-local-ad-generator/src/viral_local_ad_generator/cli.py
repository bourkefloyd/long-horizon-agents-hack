from __future__ import annotations

import argparse
from pathlib import Path

from .bfl_client import BFLClient
from .config import load_settings
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
        )
        print(
            f"Created {result['concept_count']} ad concepts from {result['story_count']} stories. "
            f"Artifacts saved to {args.output}"
        )
        return

    if args.command == "discover-outlets":
        outlets = discover_outlets(
            market=args.market,
            output_dir=args.output,
            nimble_client=nimble_client,
            max_outlets=args.max_outlets,
        )
        print(f"Saved {len(outlets)} outlets to {args.output / 'outlets.json'}")
        return

    if args.command == "discover-news":
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
        )
        print(f"Saved {len(stories)} stories to {args.output / 'stories.json'}")
        return

    if args.command == "generate-ad":
        stories = load_stories(args.stories)
        campaign_script = args.campaign.read_text(encoding="utf-8")
        concepts = generate_ads_from_stories(
            campaign_script=campaign_script,
            market=args.market,
            stories=stories,
            output_dir=args.output,
            max_videos=args.max_videos,
        )
        write_run_artifacts(args.output, args.market, stories, concepts)
        print(f"Saved {len(concepts)} ad concepts to {args.output / 'concepts.json'}")
        return

    if args.command == "generate-video":
        concepts = load_concepts(args.concepts)
        generate_videos(
            concepts=concepts,
            output_dir=args.output,
            bfl_client=bfl_client,
            poll=args.poll,
            download_media=args.download_media,
        )
        print(f"Saved video job artifacts to {args.output}")
        return

    if args.command == "stage-cdn":
        record = load_campaign_record(args.campaign_record)
        stories = mock_stories(record.geo) if args.mock_news else load_stories(args.stories)
        stories = select_stories(stories, count=args.max_stories)
        if not stories:
            parser.error("No brand-safe stories available to stage.")
        concepts = generate_ads_from_stories(
            campaign_script=record.brief,
            market=record.geo,
            stories=stories,
            output_dir=args.output,
            max_videos=args.max_videos,
        )
        write_run_artifacts(args.output, record.geo, stories, concepts)
        variant_dirs = stage_campaign_variants(record, stories, concepts, args.staging)
        print(f"Staged {len(variant_dirs)} variants under {args.staging / record.id}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_memory import AgentMemory, env_cost, guard
from .bfl_client import BFLClient, find_media_url
from .brand_guard import validate_no_famous_brands
from .event_logger import PipelineLogger
from .models import NewsOutlet, NewsStory, SanitizedStory, VideoAdConcept
from .nimble_client import NimbleClient, mock_stories
from .prompts import generate_video_concepts, make_campaign_info
from .sanitizer import sanitize_stories_for_ad
from .staging import variant_id_for


def run_pipeline(
    campaign_script: str,
    market: str,
    output_dir: Path,
    nimble_client: NimbleClient,
    bfl_client: BFLClient,
    use_mock_news: bool,
    dry_run: bool,
    generate: bool,
    poll: bool,
    download_media: bool,
    max_stories: int = 5,
    max_outlets: int = 8,
    max_videos: int | None = None,
    story_title: str | None = None,
    story_url: str = "",
    story_source: str = "",
    story_published_at: str = "",
    story_snippet: str = "",
    logger: PipelineLogger | None = None,
    memory: AgentMemory | None = None,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    emit_log(
        logger,
        "pipeline.run",
        "input",
        {
            "campaign_script": campaign_script,
            "market": market,
            "output_dir": str(output_dir),
            "use_mock_news": use_mock_news,
            "dry_run": dry_run,
            "generate": generate,
            "poll": poll,
            "download_media": download_media,
            "max_stories": max_stories,
            "max_outlets": max_outlets,
            "max_videos": max_videos,
            "story_override": {
                "title": story_title,
                "url": story_url,
                "source": story_source,
                "published_at": story_published_at,
                "snippet": story_snippet,
            },
        },
    )

    stories = discover_stories(
        market=market,
        output_dir=output_dir,
        nimble_client=nimble_client,
        use_mock_news=use_mock_news,
        max_stories=max_stories,
        max_outlets=max_outlets,
        story_title=story_title,
        story_url=story_url,
        story_source=story_source,
        story_published_at=story_published_at,
        story_snippet=story_snippet,
        logger=logger,
        memory=memory,
    )
    concepts = generate_ads_from_stories(
        campaign_script=campaign_script,
        market=market,
        stories=stories,
        output_dir=output_dir,
        max_videos=max_videos,
        logger=logger,
        memory=memory,
    )
    if generate and not dry_run:
        generate_videos(
            concepts=concepts,
            output_dir=output_dir,
            bfl_client=bfl_client,
            poll=poll,
            download_media=download_media,
            logger=logger,
            memory=memory,
        )
    result = write_run_artifacts(output_dir, market, stories, concepts, logger=logger)
    emit_log(logger, "pipeline.run", "output", result)
    return result


def discover_stories(
    market: str,
    output_dir: Path,
    nimble_client: NimbleClient,
    use_mock_news: bool,
    max_stories: int = 5,
    max_outlets: int = 8,
    outlets: list[NewsOutlet] | None = None,
    story_title: str | None = None,
    story_url: str = "",
    story_source: str = "",
    story_published_at: str = "",
    story_snippet: str = "",
    logger: PipelineLogger | None = None,
    memory: AgentMemory | None = None,
) -> list[NewsStory]:
    output_dir.mkdir(parents=True, exist_ok=True)
    emit_log(
        logger,
        "news.discovery",
        "input",
        {
            "market": market,
            "use_mock_news": use_mock_news,
            "max_stories": max_stories,
            "max_outlets": max_outlets,
            "provided_outlets": [outlet.to_dict() for outlet in outlets] if outlets else [],
            "story_override": {
                "title": story_title,
                "url": story_url,
                "source": story_source,
                "published_at": story_published_at,
                "snippet": story_snippet,
            },
        },
    )
    if story_title:
        stories = [
            NewsStory(
                title=story_title,
                url=story_url,
                source=story_source,
                published_at=story_published_at,
                snippet=story_snippet,
                relevance_score=1.0,
                virality_score=1.0,
                brand_safe=True,
            )
        ]
    elif use_mock_news:
        stories = mock_stories(market)
    else:
        if outlets is None:
            outlets = discover_outlets(
                market=market,
                output_dir=output_dir,
                nimble_client=nimble_client,
                max_outlets=max_outlets,
                logger=logger,
                memory=memory,
            )
        try:
            stories = nimble_client.search_recent_local_news(market, limit=12, outlets=outlets)
        except Exception as error:
            guard(memory, "nimble_query", error, allow_continue=False)
        emit_memory(
            memory,
            "nimble_query",
            {"kind": "recent_local_news", "market": market, "results": len(stories)},
            cost_usd=env_cost("NIMBLE_QUERY_COST_USD"),
        )
    emit_log(
        logger,
        "news.discovery",
        "candidate_stories",
        {
            "candidate_count": len(stories),
            "stories": [story.to_dict() for story in stories],
        },
    )
    selected_stories = select_stories(stories, count=max_stories)
    emit_memory(
        memory,
        "story_ranked",
        {
            "candidates": len(stories),
            "selected": [
                {"title": story.title, "url": story.url, "score": round(story.virality_score + story.relevance_score, 3)}
                for story in selected_stories
            ],
        },
    )
    write_json(output_dir / "stories.json", [story.to_dict() for story in selected_stories])
    write_news_summary(output_dir / "news.md", market, selected_stories)
    emit_log(
        logger,
        "news.discovery",
        "selected_stories",
        {
            "selected_count": len(selected_stories),
            "stories": [story.to_dict() for story in selected_stories],
            "artifacts": ["stories.json", "news.md"],
        },
    )
    return selected_stories


def discover_outlets(
    market: str,
    output_dir: Path,
    nimble_client: NimbleClient,
    max_outlets: int = 8,
    logger: PipelineLogger | None = None,
    memory: AgentMemory | None = None,
) -> list[NewsOutlet]:
    output_dir.mkdir(parents=True, exist_ok=True)
    emit_log(
        logger,
        "outlets.discovery",
        "input",
        {"market": market, "max_outlets": max_outlets},
    )
    try:
        outlets = nimble_client.search_local_news_outlets(market, limit=max_outlets)
    except Exception as error:
        guard(memory, "nimble_query", error, allow_continue=False)
    emit_memory(
        memory,
        "nimble_query",
        {"kind": "local_news_outlets", "market": market, "results": len(outlets)},
        cost_usd=env_cost("NIMBLE_QUERY_COST_USD"),
    )
    write_json(output_dir / "outlets.json", [outlet.to_dict() for outlet in outlets])
    write_outlets_summary(output_dir / "outlets.md", market, outlets)
    emit_log(
        logger,
        "outlets.discovery",
        "output",
        {
            "outlet_count": len(outlets),
            "outlets": [outlet.to_dict() for outlet in outlets],
            "artifacts": ["outlets.json", "outlets.md"],
        },
    )
    return outlets


def generate_ads_from_stories(
    campaign_script: str,
    market: str,
    stories: list[NewsStory],
    output_dir: Path,
    max_videos: int | None = None,
    logger: PipelineLogger | None = None,
    memory: AgentMemory | None = None,
) -> list[VideoAdConcept]:
    output_dir.mkdir(parents=True, exist_ok=True)
    campaign = make_campaign_info(campaign_script)
    emit_log(
        logger,
        "ad_generation",
        "input",
        {
            "campaign_script": campaign_script,
            "campaign_info": campaign,
            "market": market,
            "story_count": len(stories),
            "stories": [story.to_dict() for story in stories],
            "max_videos": max_videos,
        },
    )
    sanitized_stories = sanitize_stories_for_ad(market, stories)
    write_sanitized_stories(output_dir, market, sanitized_stories)
    emit_log(
        logger,
        "sanitization",
        "output",
        {
            "sanitized_count": len(sanitized_stories),
            "sanitized_stories": [story.to_dict() for story in sanitized_stories],
            "artifacts": ["sanitized_stories.json", "sanitized_stories.md"],
        },
    )
    concepts = [
        concept
        for story, sanitized_story in zip(stories, sanitized_stories, strict=True)
        for concept in generate_video_concepts(campaign_script, market, story, sanitized_story)
    ]
    emit_log(
        logger,
        "ad_generation",
        "concepts_before_limit",
        {
            "concept_count": len(concepts),
            "concepts": [concept.to_dict() for concept in concepts],
        },
    )
    if max_videos is not None:
        concepts = concepts[:max_videos]
    try:
        validate_no_famous_brands(concepts)
    except Exception as error:
        emit_log(logger, "brand_guard", "validation", {"error": str(error)}, status="error")
        guard(memory, "brand_guard", error, allow_continue=False)
    emit_log(
        logger,
        "brand_guard",
        "validation",
        {"concept_count": len(concepts), "result": "passed"},
    )
    for concept in concepts:
        emit_memory(
            memory,
            "script_generated",
            {"story_title": concept.story_title, "angle": concept.angle, "hook": concept.hook},
            variant_id=variant_id_for(concept),
        )
    write_input_webpages(output_dir, stories)
    write_json(output_dir / "concepts.json", [concept.to_dict() for concept in concepts])
    write_markdown_summary(output_dir / "summary.md", market, stories, concepts)
    emit_log(
        logger,
        "ad_generation",
        "output",
        {
            "concept_count": len(concepts),
            "concepts": [concept.to_dict() for concept in concepts],
            "artifacts": ["input_webpages.json", "input_webpages.md", "concepts.json", "summary.md"],
        },
    )
    return concepts


def generate_videos(
    concepts: list[VideoAdConcept],
    output_dir: Path,
    bfl_client: BFLClient,
    poll: bool,
    download_media: bool,
    logger: PipelineLogger | None = None,
    memory: AgentMemory | None = None,
) -> list[VideoAdConcept]:
    output_dir.mkdir(parents=True, exist_ok=True)
    emit_log(
        logger,
        "video_generation",
        "input",
        {
            "concept_count": len(concepts),
            "poll": poll,
            "download_media": download_media,
            "concepts": [concept.to_dict() for concept in concepts],
        },
    )
    try:
        validate_no_famous_brands(concepts)
    except Exception as error:
        guard(memory, "brand_guard", error, allow_continue=False)
    # Variants that reached bfl_ready in an earlier run of this campaign are not re-spent.
    already_done = memory.completed_variants() if memory else set()
    for index, concept in enumerate(concepts, start=1):
        variant_id = variant_id_for(concept)
        if variant_id in already_done:
            concept.bfl_job = {"skipped": True, "reason": "bfl_ready in a previous run", "variant_id": variant_id}
            emit_log(logger, "video_generation", "skip_concept", {"index": index, "variant_id": variant_id})
            emit_memory(memory, "variant_skipped", {"reason": "bfl_ready in a previous run"}, variant_id=variant_id)
            continue
        emit_log(
            logger,
            "video_generation",
            "submit_concept",
            {"index": index, "concept": concept.to_dict()},
        )
        step = "bfl_submit"
        try:
            job = bfl_client.submit_flux3_video(concept.bfl_payload)
            emit_memory(
                memory,
                "bfl_submit",
                {"index": index, "job_id": job.get("id"), "polling": bool(job.get("polling_url"))},
                variant_id=variant_id,
                cost_usd=env_cost("BFL_VIDEO_COST_USD"),
            )
            if poll and job.get("polling_url"):
                step = "bfl_poll"
                job["poll_result"] = bfl_client.poll(str(job["polling_url"]))
                poll_status = job["poll_result"].get("status")
                if poll_status != "Ready":
                    concept.bfl_job = job
                    write_json(output_dir / "concepts.json", [item.to_dict() for item in concepts])
                    raise RuntimeError(f"BFL job ended with status {poll_status}")
                if download_media:
                    step = "bfl_download"
                    media_path = output_dir / "videos" / f"video_{index:02d}.mp4"
                    job["local_video_path"] = bfl_client.download_video_result(job["poll_result"], media_path)
                video_url = find_media_url(job["poll_result"])
                if video_url:
                    job["video_url"] = video_url
                    link_path = output_dir / "video_links" / f"video_{index:02d}.url"
                    write_text(link_path, video_url + "\n")
                emit_memory(memory, "bfl_ready", {"index": index, "video_url": video_url}, variant_id=variant_id)
        except Exception as error:
            concept.bfl_job = concept.bfl_job or {"error": f"{type(error).__name__}: {error}", "step": step}
            write_json(output_dir / "concepts.json", [item.to_dict() for item in concepts])
            guard(memory, step, error, variant_id=variant_id)
            continue
        concept.bfl_job = job
    write_json(output_dir / "concepts.json", [concept.to_dict() for concept in concepts])
    write_video_link_index(output_dir, concepts)
    emit_log(
        logger,
        "video_generation",
        "output",
        {
            "concept_count": len(concepts),
            "concepts": [concept.to_dict() for concept in concepts],
            "artifacts": ["concepts.json", "video_links/index.json"],
        },
    )
    return concepts


def write_run_artifacts(
    output_dir: Path,
    market: str,
    stories: list[NewsStory],
    concepts: list[VideoAdConcept],
    logger: PipelineLogger | None = None,
) -> dict[str, object]:
    sanitized_stories = sanitize_stories_for_ad(market, stories)
    result = {
        "market": market,
        "story_count": len(stories),
        "sanitized_story_count": len(sanitized_stories),
        "concept_count": len(concepts),
        "stories": [story.to_dict() for story in stories],
        "sanitized_stories": [story.to_dict() for story in sanitized_stories],
        "concepts": [concept.to_dict() for concept in concepts],
    }
    write_json(output_dir / "run.json", result)
    write_json(output_dir / "stories.json", result["stories"])
    write_sanitized_stories(output_dir, market, sanitized_stories)
    write_json(output_dir / "concepts.json", result["concepts"])
    write_video_link_index(output_dir, concepts)
    write_markdown_summary(output_dir / "summary.md", market, stories, concepts)
    emit_log(
        logger,
        "artifacts",
        "output",
        {
            "run": result,
            "artifacts": ["run.json", "stories.json", "sanitized_stories.json", "concepts.json", "summary.md"],
        },
    )
    return result


def load_stories(path: Path) -> list[NewsStory]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [NewsStory.from_dict(item) for item in payload]


def load_outlets(path: Path) -> list[NewsOutlet]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [NewsOutlet.from_dict(item) for item in payload]


def load_concepts(path: Path) -> list[VideoAdConcept]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [VideoAdConcept.from_dict(item) for item in payload]


def load_sanitized_stories(path: Path) -> list[SanitizedStory]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [SanitizedStory.from_dict(item) for item in payload]


def select_stories(stories: list[NewsStory], count: int) -> list[NewsStory]:
    safe_stories = [story for story in stories if story.brand_safe]
    ranked = sorted(
        safe_stories,
        key=lambda story: (story.virality_score + story.relevance_score, story.published_at),
        reverse=True,
    )
    return ranked[:count]


def emit_log(
    logger: PipelineLogger | None,
    stage: str,
    event_type: str,
    payload: dict[str, Any],
    status: str = "ok",
) -> None:
    if logger:
        logger.emit(stage, event_type, payload, status=status)


def emit_memory(
    memory: AgentMemory | None,
    event_type: str,
    payload: dict[str, Any],
    variant_id: str | None = None,
    cost_usd: float | None = None,
) -> None:
    if memory:
        memory.emit(event_type, payload, variant_id=variant_id, cost_usd=cost_usd)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_video_link_index(output_dir: Path, concepts: list[VideoAdConcept]) -> None:
    links = []
    for index, concept in enumerate(concepts, start=1):
        if not concept.bfl_job:
            continue
        video_url = concept.bfl_job.get("video_url")
        if isinstance(video_url, str):
            links.append(
                {
                    "index": index,
                    "story_title": concept.story_title,
                    "angle": concept.angle,
                    "video_url": video_url,
                }
            )
    if links:
        write_json(output_dir / "video_links" / "index.json", links)


def write_input_webpages(output_dir: Path, stories: list[NewsStory]) -> None:
    pages = [
        {
            "index": index,
            "title": story.title,
            "url": story.url,
            "source": story.source,
            "published_at": story.published_at,
            "snippet": story.snippet,
            "relevance_score": story.relevance_score,
            "virality_score": story.virality_score,
            "brand_safe": story.brand_safe,
        }
        for index, story in enumerate(stories, start=1)
    ]
    write_json(output_dir / "input_webpages.json", pages)

    lines = ["# Input Webpages Used For Ad Scripting", ""]
    for page in pages:
        lines.extend(
            [
                f"## {page['index']}. {page['title']}",
                "",
                f"- URL: {page['url']}",
                f"- Source: {page['source'] or 'unknown'}",
                f"- Published: {page['published_at'] or 'unknown'}",
                f"- Brand safe: {page['brand_safe']}",
                f"- Scores: relevance {page['relevance_score']:.2f}, virality {page['virality_score']:.2f}",
                "",
                str(page["snippet"]),
                "",
            ]
        )
    write_text(output_dir / "input_webpages.md", "\n".join(lines))


def write_sanitized_stories(
    output_dir: Path,
    market: str,
    sanitized_stories: list[SanitizedStory],
) -> None:
    write_json(output_dir / "sanitized_stories.json", [story.to_dict() for story in sanitized_stories])

    lines = [f"# Sanitized Story Inputs: {market}", ""]
    for index, story in enumerate(sanitized_stories, start=1):
        notes = ", ".join(story.sanitization_notes) or "none"
        lines.extend(
            [
                f"## {index}. {story.sanitized_reference}",
                "",
                f"- Original title: {story.original_title}",
                f"- Original URL: {story.original_url}",
                f"- Sanitized frame: {story.sanitized_frame}",
                f"- Sanitized reference: {story.sanitized_reference}",
                f"- Sanitization notes: {notes}",
                "",
            ]
        )
    write_text(output_dir / "sanitized_stories.md", "\n".join(lines))
def write_outlets_summary(path: Path, market: str, outlets: list[NewsOutlet]) -> None:
    lines = [f"# Local News Outlets: {market}", ""]
    for index, outlet in enumerate(outlets, start=1):
        lines.extend(
            [
                f"## {index}. {outlet.name}",
                "",
                f"- URL: {outlet.url}",
                f"- Domain: {outlet.domain or 'unknown'}",
                "",
                outlet.snippet,
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_news_summary(path: Path, market: str, stories: list[NewsStory]) -> None:
    lines = [f"# News Discovery: {market}", ""]
    for index, story in enumerate(stories, start=1):
        lines.extend(
            [
                f"## {index}. {story.title}",
                "",
                f"- Source: {story.source or 'unknown'}",
                f"- URL: {story.url}",
                f"- Published: {story.published_at or 'unknown'}",
                f"- Brand safe: {story.brand_safe}",
                f"- Scores: relevance {story.relevance_score:.2f}, virality {story.virality_score:.2f}",
                "",
                story.snippet,
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown_summary(
    path: Path,
    market: str,
    stories: list[NewsStory],
    concepts: list[VideoAdConcept],
) -> None:
    sanitized_by_url = {
        story.original_url: story
        for story in sanitize_stories_for_ad(market, stories)
    }
    lines = [f"# Viral Local Ad Run: {market}", ""]
    for story in stories:
        sanitized_story = sanitized_by_url.get(story.url)
        heading = sanitized_story.sanitized_reference if sanitized_story else story.title
        frame = sanitized_story.sanitized_frame if sanitized_story else story.title
        lines.extend(
            [
                f"## {heading}",
                "",
                f"- Sanitized story frame: {frame}",
                "- Source webpage: see input_webpages.md",
                f"- Published: {story.published_at or 'unknown'}",
                f"- Scores: relevance {story.relevance_score:.2f}, virality {story.virality_score:.2f}",
                "",
            ]
        )
        for concept in [item for item in concepts if item.story_url == story.url]:
            lines.extend(
                [
                    f"### Variant {concept.variant_index}: {concept.angle}",
                    "",
                    f"Hook: {concept.hook}",
                    "",
                    "#### 10-Second Video Script",
                    "",
                    concept.video_script,
                    "",
                    "#### FLUX Video Prompt",
                    "",
                    concept.visual_prompt,
                    "",
                ]
            )
    path.write_text("\n".join(lines), encoding="utf-8")

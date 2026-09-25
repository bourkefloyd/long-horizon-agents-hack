from __future__ import annotations

import json
from pathlib import Path

from .bfl_client import BFLClient, find_media_url
from .brand_guard import validate_no_famous_brands
from .models import NewsStory, VideoAdConcept
from .nimble_client import NimbleClient, mock_stories
from .prompts import generate_video_concepts


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
    max_videos: int | None = None,
    story_title: str | None = None,
    story_url: str = "",
    story_source: str = "",
    story_published_at: str = "",
    story_snippet: str = "",
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    stories = discover_stories(
        market=market,
        output_dir=output_dir,
        nimble_client=nimble_client,
        use_mock_news=use_mock_news,
        max_stories=max_stories,
        story_title=story_title,
        story_url=story_url,
        story_source=story_source,
        story_published_at=story_published_at,
        story_snippet=story_snippet,
    )
    concepts = generate_ads_from_stories(
        campaign_script=campaign_script,
        market=market,
        stories=stories,
        output_dir=output_dir,
        max_videos=max_videos,
    )
    if generate and not dry_run:
        generate_videos(
            concepts=concepts,
            output_dir=output_dir,
            bfl_client=bfl_client,
            poll=poll,
            download_media=download_media,
        )
    return write_run_artifacts(output_dir, market, stories, concepts)


def discover_stories(
    market: str,
    output_dir: Path,
    nimble_client: NimbleClient,
    use_mock_news: bool,
    max_stories: int = 5,
    story_title: str | None = None,
    story_url: str = "",
    story_source: str = "",
    story_published_at: str = "",
    story_snippet: str = "",
) -> list[NewsStory]:
    output_dir.mkdir(parents=True, exist_ok=True)
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
        stories = nimble_client.search_recent_local_news(market, limit=12)
    selected_stories = select_stories(stories, count=max_stories)
    write_json(output_dir / "stories.json", [story.to_dict() for story in selected_stories])
    write_news_summary(output_dir / "news.md", market, selected_stories)
    return selected_stories


def generate_ads_from_stories(
    campaign_script: str,
    market: str,
    stories: list[NewsStory],
    output_dir: Path,
    max_videos: int | None = None,
) -> list[VideoAdConcept]:
    output_dir.mkdir(parents=True, exist_ok=True)
    concepts = [
        concept
        for story in stories
        for concept in generate_video_concepts(campaign_script, market, story)
    ]
    if max_videos is not None:
        concepts = concepts[:max_videos]
    validate_no_famous_brands(concepts)
    write_json(output_dir / "concepts.json", [concept.to_dict() for concept in concepts])
    write_markdown_summary(output_dir / "summary.md", market, stories, concepts)
    return concepts


def generate_videos(
    concepts: list[VideoAdConcept],
    output_dir: Path,
    bfl_client: BFLClient,
    poll: bool,
    download_media: bool,
) -> list[VideoAdConcept]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, concept in enumerate(concepts, start=1):
        job = bfl_client.submit_flux3_video(concept.bfl_payload)
        if poll and job.get("polling_url"):
            job["poll_result"] = bfl_client.poll(str(job["polling_url"]))
            if download_media and job["poll_result"].get("status") == "Ready":
                media_path = output_dir / "videos" / f"video_{index:02d}.mp4"
                job["local_video_path"] = bfl_client.download_video_result(job["poll_result"], media_path)
            if job["poll_result"].get("status") == "Ready":
                video_url = find_media_url(job["poll_result"])
                if video_url:
                    job["video_url"] = video_url
                    link_path = output_dir / "video_links" / f"video_{index:02d}.url"
                    write_text(link_path, video_url + "\n")
        concept.bfl_job = job
    write_json(output_dir / "concepts.json", [concept.to_dict() for concept in concepts])
    write_video_link_index(output_dir, concepts)
    return concepts


def write_run_artifacts(
    output_dir: Path,
    market: str,
    stories: list[NewsStory],
    concepts: list[VideoAdConcept],
) -> dict[str, object]:
    result = {
        "market": market,
        "story_count": len(stories),
        "concept_count": len(concepts),
        "stories": [story.to_dict() for story in stories],
        "concepts": [concept.to_dict() for concept in concepts],
    }
    write_json(output_dir / "run.json", result)
    write_json(output_dir / "stories.json", result["stories"])
    write_json(output_dir / "concepts.json", result["concepts"])
    write_video_link_index(output_dir, concepts)
    write_markdown_summary(output_dir / "summary.md", market, stories, concepts)
    return result


def load_stories(path: Path) -> list[NewsStory]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [NewsStory.from_dict(item) for item in payload]


def load_concepts(path: Path) -> list[VideoAdConcept]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [VideoAdConcept.from_dict(item) for item in payload]


def select_stories(stories: list[NewsStory], count: int) -> list[NewsStory]:
    safe_stories = [story for story in stories if story.brand_safe]
    ranked = sorted(
        safe_stories,
        key=lambda story: (story.virality_score + story.relevance_score, story.published_at),
        reverse=True,
    )
    return ranked[:count]


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
    lines = [f"# Viral Local Ad Run: {market}", ""]
    for story in stories:
        lines.extend(
            [
                f"## {story.title}",
                "",
                f"- Source: {story.source or 'unknown'}",
                f"- URL: {story.url}",
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

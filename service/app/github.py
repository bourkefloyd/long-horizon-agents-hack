"""Kick off the campaign-gen LH agent by opening a labeled GitHub issue."""
import json
import os
import urllib.error
import urllib.request

from .models import Campaign

DEFAULT_REPOSITORY = "bourkefloyd/long-horizon-agents-hack"
CAMPAIGN_GEN_LABEL = "lh:campaign-gen"


class GitHubIssueError(RuntimeError):
    pass


def github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or None


def github_repository() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPOSITORY


def issue_body(campaign: Campaign) -> str:
    campaign_json = json.dumps(campaign.model_dump(mode="json"), indent=2)
    return "\n".join(
        [
            f"Generate creative for campaign `{campaign.id}` ({campaign.geo}, {campaign.dims}).",
            "",
            "## Brief",
            "",
            campaign.brief,
            "",
            "## Campaign",
            "",
            "```json",
            campaign_json,
            "```",
            "",
            f"Write output under `cdn/staging/{campaign.id}/<variant>/` so the feed can filter by campaign.",
        ]
    )


def create_campaign_issue(campaign: Campaign, *, token: str, repository: str) -> str:
    """Open the task issue and return its HTML URL."""
    payload = json.dumps(
        {
            "title": f"Campaign: {campaign.name}",
            "body": issue_body(campaign),
            "labels": [CAMPAIGN_GEN_LABEL],
        }
    ).encode()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/issues",
        data=payload,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "lh-campaign-service",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            created = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise GitHubIssueError(f"GitHub returned {exc.code}: {detail}") from exc
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise GitHubIssueError(f"GitHub request failed: {exc}") from exc

    url = created.get("html_url") if isinstance(created, dict) else None
    if not isinstance(url, str):
        raise GitHubIssueError("GitHub response did not include an issue URL")
    return url

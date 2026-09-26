#!/usr/bin/env python3
"""Turn what a content run produced into GitHub follow-up issues.

    python3 scripts/content-followups.py --dry-run                 # newest staged campaign, print only
    python3 scripts/content-followups.py --campaign local-news-20260925
    python3 scripts/content-followups.py --all --dry-run           # every staged campaign

Reads cdn/staging/<campaign>/run.json (scripts/generate-content.py) or campaign.json
(viral-local-ad-generator stage-cdn) plus the published CDN manifest, and derives follow-ups in
three buckets:

  followup:bfl-api        renders that did not come back Ready, credit exhaustion, timeouts,
                          Liquid QA errors, Nimble failures
  followup:agent-workflow discovery fell back past the live outlet search, stories left
                          unsanitised, variants written from generic persona beats, QA skipped
  followup:website        published media a browser cannot show (bad SVG bytes, missing poster),
                          campaigns with nothing published, video ads without a poster

Every issue body ends with an HTML marker `<!-- followup:<key> -->`; an open issue carrying the
same marker is left alone, so re-running is idempotent. Issues are opened with the `gh` CLI
(GH_TOKEN). Nothing here spends money or touches the CDN.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "cdn" / "staging"
MANIFEST_URL = "https://storage.googleapis.com/lh-ads-assets-205515555985/manifest.json"

LABELS = {
    "bfl-api": ["followup:bfl-api", "bug"],
    "agent-workflow": ["followup:agent-workflow", "enhancement"],
    "website": ["followup:website", "bug"],
}
TITLE_PREFIX = {"bfl-api": "BFL/API", "agent-workflow": "Agent workflow", "website": "Website"}


def log(msg):
    print(msg, flush=True)


class Followup:
    def __init__(self, bucket, key, title, body):
        self.bucket, self.key, self.title, self.body = bucket, key, title, body

    @property
    def marker(self):
        return f"<!-- followup:{self.key} -->"

    def full_title(self):
        return f"[{TITLE_PREFIX[self.bucket]}] {self.title}"

    def full_body(self):
        return f"{self.body.rstrip()}\n\n_Opened by `scripts/content-followups.py`; disable with the `ISSUE_WORKFLOW_DISABLED` repository variable._\n{self.marker}\n"


# ---------------------------------------------------------------- inputs

def staged_campaigns():
    if not STAGING.exists():
        return []
    out = []
    for d in sorted(STAGING.iterdir()):
        if (d / "run.json").exists() or (d / "campaign.json").exists():
            out.append(d)
    return out


def newest_campaign(dirs):
    def stamp(d):
        for name in ("run.json", "campaign.json"):
            p = d / name
            if p.exists():
                try:
                    return json.loads(p.read_text()).get("generated_at", "")
                except ValueError:
                    return ""
        return ""
    return max(dirs, key=stamp) if dirs else None


def load_manifest():
    try:
        with urllib.request.urlopen(MANIFEST_URL, timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, ValueError, OSError) as e:
        log(f"manifest: unavailable ({e}); website checks limited to staging")
        return None


def probe(url):
    """(status, content_type, first_bytes) for a published asset; never raises."""
    try:
        req = urllib.request.Request(url, headers={"Range": "bytes=0-65535"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers.get("content-type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, "", b""
    except (urllib.error.URLError, OSError):
        return None, "", b""


# ---------------------------------------------------------------- derivations

def from_run(campaign, run):
    out = []
    disc = run.get("discovery") or {}
    via = disc.get("via")
    if via and via != "nimble-outlets":
        out.append(Followup(
            "agent-workflow", f"{campaign}:discovery:{via}",
            f"{campaign}: discovery fell back to `{via}`",
            f"`scripts/generate-content.py` for `{campaign}` did not get stories from the outlet-restricted Nimble search; "
            f"it used `{via}` instead.\n\nDiscovery record:\n```json\n{json.dumps(disc, indent=1)[:1500]}\n```\n\n"
            "Check `NIMBLE_API_KEY` on the workflow, the outlet query in `viral_local_ad_generator.nimble_client`, "
            "and whether the outlet domain filter is too strict for this market.",
        ))
    if run.get("error"):
        out.append(Followup(
            "bfl-api", f"{campaign}:run-error",
            f"{campaign}: generator stopped early",
            f"`run.json` for `{campaign}` records an error:\n\n> {run['error']}\n\n"
            "If this is a 402, top up credits at dashboard.bfl.ai or rotate `BFL_API_KEY`; otherwise inspect the run log.",
        ))
    raw_titles = [s for s in run.get("sanitized_stories") or [] if s.get("notes") == ["publisher_suffix_removed"]]
    if raw_titles:
        out.append(Followup(
            "agent-workflow", f"{campaign}:sanitizer-passthrough",
            f"{campaign}: sanitizer passed {len(raw_titles)} raw headline(s) into scripts",
            "`sanitize_story_for_ad` only removed a publisher suffix, so the script's *Local moment* line still carries the "
            "raw headline (which can name real people or companies):\n\n"
            + "\n".join(f"- {s['reference']}" for s in raw_titles)
            + "\n\nImprove `_generic_topic_from_title` in `viral-local-ad-generator/src/viral_local_ad_generator/sanitizer.py` "
            "(see campaign-gen state.md Open items) and add tests before changing behaviour.",
        ))
    qa = run.get("liquid_qa")
    if qa == "skipped" or qa is None:
        out.append(Followup(
            "agent-workflow", f"{campaign}:liquid-qa-skipped",
            f"{campaign}: Liquid QA did not run",
            f"Neither `LIQUID_TEXT_BASE_URL` nor `LIQUID_VISION_BASE_URL` was set for the `{campaign}` run, so hooks and "
            "posters were published without the brand-safety / no-text review. Wire the llama-server endpoints into "
            "`generate-content.yml` (see docs/liquid-local.md) or record the decision to ship without QA.",
        ))
    elif isinstance(qa, dict):
        errors = {vid: kinds for vid, kinds in qa.items()
                  if any(isinstance(k, dict) and k.get("error") for k in kinds.values())}
        if errors:
            out.append(Followup(
                "bfl-api", f"{campaign}:liquid-qa-errors",
                f"{campaign}: Liquid QA calls failed for {len(errors)} variant(s)",
                "```json\n" + json.dumps(errors, indent=1)[:2000] + "\n```",
            ))
    generic = [v for v in run.get("variants") or [] if v.get("authored_by") == "scripts/generate-content.py"]
    if generic:
        out.append(Followup(
            "agent-workflow", f"{campaign}:generic-beats",
            f"{campaign}: {len(generic)} variant(s) used generic persona beats",
            "These variants had no authored story in `content/ads/scripts.json` for their brand x persona pairing and fell "
            "back to `PERSONA_BEATS` in `scripts/generate-content.py`:\n\n"
            + "\n".join(f"- `{v['variant_id']}`: \"{v.get('hook', '')}\"" for v in generic)
            + "\n\nAuthor proper pairings in `scripts.json` so the hook and beats fit the product.",
        ))
    failed = []
    for v in run.get("variants") or []:
        for kind, entry in (v.get("render") or {}).items():
            if entry.get("status") != "Ready" or not entry.get("file"):
                failed.append((v["variant_id"], kind, entry))
    if failed:
        body = "\n".join(
            f"- `{vid}` {kind}: status `{e.get('status')}`, task `{e.get('task_id')}`, quoted {e.get('quoted_credits')} credits"
            for vid, kind, e in failed)
        out.append(Followup(
            "bfl-api", f"{campaign}:renders-not-ready",
            f"{campaign}: {len(failed)} BFL render(s) did not come back Ready",
            f"{body}\n\nEstimate was ${run.get('estimate_usd', {}).get('total')}; settled "
            f"{(run.get('cost') or {}).get('settled_credits')} credits. Check the task ids against BFL, and whether the "
            "poll timeout (`--timeout-minutes`) or `safety_tolerance` needs adjusting.",
        ))
    return out


def from_staged_scripts(campaign, index):
    """viral-local-ad-generator stage-cdn output: scripts only, no media yet."""
    variants = index.get("variants") or []
    return [Followup(
        "agent-workflow", f"{campaign}:scripts-only",
        f"{campaign}: {len(variants)} variant(s) staged as scripts, no media",
        f"`{campaign}` was staged by `{index.get('agent')}` as `media_type: script` "
        f"({', '.join(f'`{v}`' for v in variants)}). To get posters and video, run **Generate ad content** with "
        f"`campaign={campaign}` and `from_service=true` (spends BFL credits, ~$0.95 per 2 posters + 1 video), "
        "or decide these stay script previews.",
    )]


def from_manifest(manifest, campaigns_seen):
    out = []
    if not manifest:
        return out
    ads = manifest.get("ads") or []
    by_campaign = {}
    for ad in ads:
        by_campaign.setdefault(ad.get("campaign_id"), []).append(ad)
    for c in campaigns_seen:
        if c not in by_campaign:
            out.append(Followup(
                "website", f"{c}:not-published",
                f"{c}: staged but not in the CDN manifest",
                f"`cdn/staging/{c}/` exists on main but the published manifest has no ads with `campaign_id: {c}`, so "
                f"`/feed?campaign={c}` shows the empty state. Run **Publish ad assets** or check its last run.",
            ))
    for ad in ads:
        if not ad.get("targeting", {}).get("active"):
            continue
        aid = ad.get("id")
        if ad.get("media_type") == "video" and not ad.get("poster_url"):
            out.append(Followup(
                "website", f"{aid}:video-no-poster",
                f"{aid}: video ad without a poster",
                "The feed shows a black frame until the MP4 loads, and falls back to the poster on error. "
                f"Add `poster_file` for `{aid}` in its `meta.json`.",
            ))
        probed = set()
        for field in ("poster_url", "media_url"):
            url = ad.get(field)
            if not url or url in probed or (field == "media_url" and ad.get("media_type") == "script"):
                continue
            probed.add(url)
            status, ctype, head = probe(url)
            if status is None:
                continue
            if status >= 400:
                out.append(Followup(
                    "website", f"{aid}:{field}:http-{status}",
                    f"{aid}: {field} returns HTTP {status}",
                    f"`{url}` returned {status}; the ad renders blank in the feed.",
                ))
            elif "svg" in ctype:
                try:
                    head.decode("utf-8")
                except UnicodeDecodeError as e:
                    out.append(Followup(
                        "website", f"{aid}:svg-not-utf8",
                        f"{aid}: SVG poster is not valid UTF-8, browsers show a broken image",
                        f"`{url}` contains byte 0x{head[e.start]:02x} at offset {e.start} (likely a Windows-1252 apostrophe). "
                        "Browsers refuse to parse it, so the frame shows a broken-image icon. Re-encode the SVG as UTF-8 "
                        "(or escape the character) in the publisher and republish.",
                    ))
    return out


# ---------------------------------------------------------------- github

def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def existing_markers():
    """Markers already present on open followup issues, so reruns are idempotent."""
    try:
        raw = gh("issue", "list", "--state", "open", "--limit", "200", "--search", "followup: in:body", "--json", "body,number,title")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log(f"gh: could not list issues ({e}); assuming none exist")
        return {}
    found = {}
    for issue in json.loads(raw or "[]"):
        body = issue.get("body") or ""
        start = 0
        while (i := body.find("<!-- followup:", start)) != -1:
            j = body.find("-->", i)
            if j == -1:
                break
            found[body[i:j + 3].strip()] = issue["number"]
            start = j + 3
    return found


def ensure_labels(buckets):
    colors = {"followup:bfl-api": "d73a4a", "followup:agent-workflow": "0e8a16", "followup:website": "1d76db"}
    for b in buckets:
        for label in LABELS[b]:
            if label in colors:
                subprocess.run(["gh", "label", "create", label, "--color", colors[label], "--force",
                                "--description", f"Content follow-up: {TITLE_PREFIX[b]}"], capture_output=True, text=True)


def open_issue(f):
    args = ["issue", "create", "--title", f.full_title(), "--body", f.full_body()]
    for label in LABELS[f.bucket]:
        args += ["--label", label]
    return gh(*args).strip()


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign", default=None, help="staged campaign id (default: newest by generated_at)")
    ap.add_argument("--all", action="store_true", help="derive for every staged campaign")
    ap.add_argument("--dry-run", action="store_true", help="print the follow-ups; open nothing")
    ap.add_argument("--max-issues", type=int, default=8, help="cap per run so a bad input cannot flood the tracker")
    a = ap.parse_args()

    dirs = staged_campaigns()
    if a.campaign:
        dirs = [d for d in dirs if d.name == a.campaign]
        if not dirs:
            sys.exit(f"no staged campaign {a.campaign!r} under {STAGING}")
    elif not a.all:
        newest = newest_campaign(dirs)
        dirs = [newest] if newest else []
    if not dirs:
        log("nothing staged; no follow-ups")
        return

    followups = []
    for d in dirs:
        if (d / "run.json").exists():
            followups += from_run(d.name, json.loads((d / "run.json").read_text()))
        elif (d / "campaign.json").exists():
            followups += from_staged_scripts(d.name, json.loads((d / "campaign.json").read_text()))
    followups += from_manifest(load_manifest(), [d.name for d in dirs])

    seen = set()
    unique = []
    for f in followups:
        if f.key not in seen:
            seen.add(f.key)
            unique.append(f)
    log(f"derived {len(unique)} follow-up(s) from {', '.join(d.name for d in dirs)}")
    for f in unique:
        log(f"  [{f.bucket}] {f.title}  ({f.key})")

    if a.dry_run:
        for f in unique:
            print(f"\n--- {f.full_title()}\n{f.full_body()}")
        return

    have = existing_markers()
    todo = [f for f in unique if f.marker not in have]
    skipped = len(unique) - len(todo)
    if skipped:
        log(f"{skipped} already open; skipping")
    if len(todo) > a.max_issues:
        log(f"capping at {a.max_issues} of {len(todo)} new issues")
        todo = todo[:a.max_issues]
    ensure_labels({f.bucket for f in todo})
    opened = []
    for f in todo:
        url = open_issue(f)
        opened.append(url)
        log(f"opened {url}: {f.full_title()}")
    summary = {"derived": len(unique), "already_open": skipped, "opened": opened}
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

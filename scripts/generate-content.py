#!/usr/bin/env python3
"""Local-news discovery -> N ad variants -> BFL poster images and FLUX 3 videos -> cdn/staging.

    python3 scripts/generate-content.py --dry-run                     # plan and cost estimate only
    python3 scripts/generate-content.py --brief "Tartine morning buns for Dolores Park weekends"
    python3 scripts/generate-content.py --variants 4 --videos 2 --max-usd 5
    python3 scripts/generate-content.py --campaign tartine-weekend-buns --from-service   # website campaign
    python3 scripts/generate-content.py --campaign-file campaign.json                    # record or issue body

Reuses Aayush's modules in content/ads (nimble.py for discovery, scripts.json for brand facts,
personas and authored stories, render.py for the BFL call and result parsing) and Thomas's
viral-local-ad-generator (outlet discovery, brand-safety scoring, story ranking, story
sanitizer, brand guard, built-in stories, campaign record contract).

Campaign records: the website's campaigns (service GET /campaigns/<id>, or the ```json block in a
`Campaign: <name>` task issue) carry id, name, brief, geo, audience and dims. --from-service or
--campaign-file loads one; brief, market and audience then come from the record and the campaign
id is the record id, so the feed can filter by it (/feed?campaign=<id>).

Discovery order: Nimble local outlets -> stories restricted to those outlets -> Nimble open news
search -> live rows in content/ads/facts.json -> Thomas's built-in stories. Every story is passed
through the sanitizer so scripts and run.json carry an ad-safe frame instead of publisher, private
or third-party names. Media: one 9:16 poster per variant via /v1/flux-2-pro, a 5 s 9:16 hd
FLUX 3 video for the top --videos variants via /v1/flux-3-video. Everything is estimated
against BFL's published prices before anything is submitted; over --max-usd aborts.

Output: cdn/staging/<campaign>/<variant>/{meta.json,poster.jpg,creative.mp4,script.txt} in the
layout cdn/publish.py expects, plus cdn/staging/<campaign>/run.json with prompts, task ids,
quoted and settled cost, QA verdicts and the stories used.

Keys: BFL_API_KEY (or BLACK_FOREST), NIMBLE_API_KEY. Liquid QA runs only when
LIQUID_TEXT_BASE_URL / LIQUID_VISION_BASE_URL point at an OpenAI-compatible llama-server.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADS = ROOT / "content" / "ads"
sys.path.insert(0, str(ADS))
sys.path.insert(0, str(ROOT / "viral-local-ad-generator" / "src"))

import nimble  # noqa: E402  (content/ads/nimble.py)
import render  # noqa: E402  (content/ads/render.py)
from viral_local_ad_generator.brand_guard import find_famous_brand_terms  # noqa: E402
from viral_local_ad_generator.models import NewsStory  # noqa: E402
from viral_local_ad_generator.nimble_client import (  # noqa: E402
    NimbleClient,
    is_brand_safe,
    mock_stories,
    normalize_nimble_results,
)
from viral_local_ad_generator.pipeline import select_stories  # noqa: E402
from viral_local_ad_generator.sanitizer import sanitize_story_for_ad  # noqa: E402
from viral_local_ad_generator.staging import CampaignRecord, load_campaign_record  # noqa: E402

API_BASE = os.environ.get("BFL_API_BASE", "https://api.bfl.ai").rstrip("/")
NIMBLE_BASE = os.environ.get("NIMBLE_BASE_URL", "https://sdk.nimbleway.com").rstrip("/")
CAMPAIGN_SERVICE_URL = os.environ.get(
    "CAMPAIGN_SERVICE_URL", "https://lh-campaign-service-row663omlq-uc.a.run.app"
).rstrip("/")
VIDEO_ENDPOINT = f"{API_BASE}/v1/flux-3-video"
IMAGE_ENDPOINT = f"{API_BASE}/v1/flux-2-pro"
CREDITS_ENDPOINT = f"{API_BASE}/v1/credits"

# Published prices (docs.bfl.ai/quick_start/pricing, read 2026-09-25). 1 credit = $0.01.
VIDEO_USD_PER_SEC = {"hd": 0.17, "fhd": 0.29, "qhd": 0.40, "uhd": 0.80}
VIDEO_DRAFT_USD_PER_SEC = 0.06
IMAGE_USD_FIRST_MP = 0.03
IMAGE_USD_PER_EXTRA_MP = 0.015
POSTER_W, POSTER_H = 1088, 1920  # 9:16, multiples of 32 like BFL's own fhd output

VIDEO_SECONDS = 5
RESOLUTION = "hd"
MARKET = "San Francisco"
NO_TEXT = "No on-screen text, captions, subtitles, logos, signs or readable words."
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Which personas suit which product, best first. The first --videos entries get a video.
PERSONAS_FOR = {
    "sightglass": ["n_judah_commuter", "soma_founder", "fog_narrator", "new_transplant"],
    "tartine": ["ocean_beach_surfer", "dolores_park_crew", "new_transplant", "n_judah_commuter"],
    "bi_rite_creamery": ["dolores_park_crew", "mission_family_es", "new_transplant", "ocean_beach_surfer"],
    "dandelion": ["soma_founder", "new_transplant", "dolores_park_crew", "fog_narrator"],
    "boudin": ["new_transplant", "fog_narrator", "ocean_beach_surfer", "n_judah_commuter"],
    "sutro_stack": ["soma_lunch", "dolores_park_crew", "n_judah_commuter", "soma_founder"],
}
BRAND_KEYWORDS = {
    "sightglass": ["sightglass"],
    "tartine": ["tartine"],
    "bi_rite_creamery": ["bi-rite", "bi rite", "birite", "creamery"],
    "dandelion": ["dandelion"],
    "boudin": ["boudin"],
    "sutro_stack": ["sutro", "burger"],
}
CTA_FOR = {
    "sightglass": "Find the roastery at 270 7th St",
    "tartine": "Get in line at 600 Guerrero",
    "bi_rite_creamery": "Grab a scoop by Dolores Park",
    "dandelion": "Taste it at 740 Valencia",
    "boudin": "Tear into a loaf",
    "sutro_stack": "Build your Sutro Stack",
}

# Persona stories for pairings scripts.json has not authored. {name} is the brand name.
# Each entry: tension, turn, payoff (shot beats) and the spoken hook (<= 9 words for a 5 s clip).
PERSONA_BEATS = {
    "n_judah_commuter": ("the streetcar doors close in his face and he exhales into the fog",
                         "he turns, walks half a block and steps inside", "first sip by the window, streetcar bell fading behind him",
                         "Missed the N. Not the good part."),
    "soma_founder": ("she rehearses her pitch under her breath, checks the time, eight missed messages",
                     "she steps up to the counter and the room goes quiet", "she walks out, cup in hand, shoulders back, striding toward the city",
                     "Demo day. Four minutes to make it count."),
    "fog_narrator": ("the fog rolls smugly over the rooftops and swallows the Bay Bridge",
                     "below, a door opens and warm light spills onto the wet sidewalk", "the fog peers through the window at people who clearly do not mind it",
                     "Gray again. You're welcome."),
    "new_transplant": ("she shivers in a thin jacket as sea lions bark and the bridge disappears",
                       "a stranger points her toward a warm doorway a block away", "she wraps both hands around something warm and finally smiles",
                       "Nobody told you about July. We did."),
    "ocean_beach_surfer": ("she peels back the hood of a dripping wetsuit, breath visible in the cold",
                           "the camper van door slides open onto the Great Highway", "she leans on the van, board beside her, and takes the first bite",
                           "Fifty-five degree water. Worth it."),
    "dolores_park_crew": ("four friends claim a patch of sloped lawn as the skyline glows behind them",
                          "one of them jogs back up the hill with a paper bag", "the bag opens and everyone reaches in at once, laughing",
                          "Sunday in the park has a menu."),
    "mission_family_es": ("a mom and her son walk past murals in golden afternoon light",
                          "he tugs her sleeve toward a familiar doorway", "they share it on the sidewalk, papel picado fluttering above",
                          "Después de la escuela, lo de siempre."),
    "soma_lunch": ("office workers pour out of glass lobbies at noon, phones lighting up",
                   "smash cut to the counter, the hero product sliding across", "a table of coworkers raises it in a toast, Bay Bridge behind them",
                   "Lunch break. Make it count."),
}
PERSONA_LABEL = {
    "n_judah_commuter": "N-Judah commuters", "soma_founder": "SoMa founders", "fog_narrator": "SoMa fog watchers",
    "new_transplant": "New to SF", "ocean_beach_surfer": "Ocean Beach surfers", "dolores_park_crew": "Dolores Park crews",
    "mission_family_es": "Mission families", "soma_lunch": "SoMa lunch crowd",
}


_T0 = time.time()


def log(msg):
    print(msg, flush=True)
    trace.event(msg)


class Trace:
    """Intermediate artifacts for debugging a run, written as they happen so a crash still leaves them behind.

    Layout under the trace dir ($TRACE_DIR, default out/trace/<campaign>/):
      events.jsonl                 every log line with a UTC timestamp and seconds since start
      discovery.json               provenance, raw and sanitized stories
      plan.json                    variants with hook, CTA, audience, story, prompts and script (before any paid call)
      qa.json                      Liquid text/vision verdicts
      <variant>/poster.prompt.txt  exact prompt sent to the FLUX image endpoint
      <variant>/video.prompt.txt   exact prompt sent to the FLUX video endpoint
      <variant>/script.txt         the ad script the prompts were derived from
      <variant>/<kind>.request.json  full BFL request body plus the returned task id / polling URL
      <variant>/<kind>.result.json   final BFL poll result (status, cost, result URL)
      run.json                     copy of the final run record
    """

    def __init__(self):
        self.dir = None

    def start(self, path):
        self.dir = Path(path)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "events.jsonl").write_text("")

    def event(self, msg):
        if not self.dir:
            return
        rec = {"t": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
               "elapsed_s": round(time.time() - _T0, 3), "msg": str(msg)}
        with (self.dir / "events.jsonl").open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def write_json(self, name, obj):
        if self.dir:
            path = self.dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n")

    def write_text(self, name, text):
        if self.dir:
            path = self.dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text((text or "").rstrip("\n") + "\n")

    def variant(self, v):
        """Snapshot everything the renderer will be asked to do for one variant."""
        vid = v["variant_id"]
        self.write_text(f"{vid}/poster.prompt.txt", v["prompts"]["poster"])
        self.write_text(f"{vid}/video.prompt.txt", v["prompts"]["video"])
        self.write_text(f"{vid}/script.txt", v["script_text"] if v.get("staged_meta") else script_text(v))


trace = Trace()


# ---------------------------------------------------------------- discovery

def story_from_fact(row):
    fact = row.get("fact", "")
    title, _, snippet = fact.partition(": ")
    return NewsStory(title=title.strip(), url=row.get("source", ""), source="Nimble (facts.json)",
                     published_at=row.get("retrieved_at", ""), snippet=snippet.strip(),
                     relevance_score=0.7, virality_score=0.6,
                     brand_safe=is_brand_safe(title, snippet, row.get("source", "")))


def discover_via_outlets(market, count, max_outlets=8):
    """Thomas's staged flow: find the market's own outlets, then only take stories they published.
    Returns (stories, provenance) or (None, reason)."""
    client = NimbleClient(os.environ["NIMBLE_API_KEY"], NIMBLE_BASE)
    outlets = client.search_local_news_outlets(market, limit=max_outlets)
    if not outlets:
        return None, "no local outlets found"
    stories = client.search_recent_local_news(market, limit=12, outlets=outlets)
    picked = select_stories(stories, count)
    if not picked:
        return None, f"{len(outlets)} outlets, {len(stories)} outlet stories, none brand-safe"
    return picked, {"via": "nimble-outlets", "outlets": [{"name": o.name, "domain": o.domain, "url": o.url} for o in outlets],
                    "returned": len(stories), "brand_safe": sum(s.brand_safe for s in stories)}


def discover(market, count):
    """Returns (stories, provenance). Never raises: every layer falls through to the next."""
    query = f"{market} viral local news this week"
    if os.environ.get("NIMBLE_API_KEY"):
        try:
            picked, prov = discover_via_outlets(market, count)
            if picked:
                return picked, prov
            log(f"discovery: outlet-restricted search gave nothing ({prov}); trying open news search")
        except Exception as e:  # network, auth, shape: the open search below still works
            log(f"discovery: outlet discovery failed ({e}); trying open news search")
        try:
            res = nimble.search(query, "news", 8, "week")
            stories = normalize_nimble_results(res)
            if stories:
                for s in stories:
                    s.source = s.source or "Nimble news search"
                picked = select_stories(stories, count)
                if picked:
                    return picked, {"via": "nimble", "query": query, "request_id": res.get("request_id"),
                                    "returned": len(stories), "brand_safe": sum(s.brand_safe for s in stories)}
            log(f"discovery: Nimble returned {len(stories)} stories, none brand-safe; falling back")
        except Exception as e:  # network, auth, shape: keep going with cached facts
            log(f"discovery: Nimble failed ({e}); falling back")
    else:
        log("discovery: NIMBLE_API_KEY not set; using cached facts")
    facts = ADS / "facts.json"
    if facts.exists():
        now = dt.datetime.now(dt.timezone.utc)
        rows = [r for r in json.loads(facts.read_text()) if r.get("source")
                and dt.datetime.fromisoformat(r["expires_at"]) > now]
        picked = select_stories([story_from_fact(r) for r in rows], count)
        if picked:
            return picked, {"via": "facts.json", "live_rows": len(rows)}
        log("discovery: no live brand-safe rows in facts.json; using built-in stories")
    return select_stories(mock_stories(market), count), {"via": "built-in"}


def short_topic(story, limit=60):
    t = re.sub(r"\s+", " ", story.title).strip().rstrip(".!")
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"


def sanitized(market, story):
    """Ad-safe frame and reference for a story: no publisher, private-person or third-party brand names."""
    s = sanitize_story_for_ad(market, story)
    return {"frame": s.sanitized_frame, "reference": s.sanitized_reference, "notes": s.sanitization_notes}


# ---------------------------------------------------------------- campaign records

def fetch_campaign_record(campaign_id):
    """Read a website campaign from the campaign service and validate it against the generator contract."""
    url = f"{CAMPAIGN_SERVICE_URL}/campaigns/{urllib.parse.quote(campaign_id, safe='')}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"campaign service returned HTTP {e.code} for {campaign_id!r}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"campaign service unreachable at {url}: {e.reason}") from e
    return CampaignRecord.from_dict(payload)


def apply_campaign_record(a, record):
    """A campaign record wins over the flag defaults so the feed can filter by the website's id."""
    a.campaign = record.id
    a.brief = record.brief
    a.market = record.geo
    a.campaign_name = record.name or record.id
    a.campaign_audience = record.audience.strip() or None
    a.brief_ref = record.issue_url
    log(f"campaign record: {record.id} ({a.campaign_name}) market={record.geo!r} audience={record.audience!r}")


# ---------------------------------------------------------------- variants

def pick_product(brief, data):
    low = brief.lower()
    for key, words in BRAND_KEYWORDS.items():
        if any(w in low for w in words):
            return key
    return "sightglass"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def build_variants(brief, data, n, stories, market=MARKET):
    product_key = pick_product(brief, data)
    product = data["products"][product_key]
    authored = {v["persona"]: v for v in data["variants"] if v["product"] == product_key and "lines" in v}
    order = PERSONAS_FOR[product_key] + [p for p in PERSONA_BEATS if p not in PERSONAS_FOR[product_key]]
    out = []
    for i, persona_key in enumerate(order[:n]):
        persona = data["personas"][persona_key]
        story = stories[i % len(stories)] if stories else None
        if persona_key in authored:
            a = authored[persona_key]
            tension, turn, payoff, hook = a["tension"], a["turn"], a["payoff"], a["lines"][0]
            authored_by = "content/ads/scripts.json"
        else:
            tension, turn, payoff, hook = PERSONA_BEATS[persona_key]
            authored_by = "scripts/generate-content.py"
        vid = f"{product_key}__{persona_key}".replace("_creamery", "")
        out.append({
            "variant_id": vid, "product_key": product_key, "product": product, "persona_key": persona_key,
            "persona": persona, "hook": hook, "cta": CTA_FOR.get(product_key, f"Visit {product['name']}"),
            "beats": (tension, turn, payoff), "authored_by": authored_by,
            "story": story.to_dict() if story else None,
            "story_safe": sanitized(market, story) if story else None,
            "audience": PERSONA_LABEL.get(persona_key, persona_key.replace("_", " ")),
        })
    return product_key, out


def video_prompt(v):
    p, per = v["product"], v["persona"]
    tension, turn, payoff = v["beats"]
    look = p["look"][0].upper() + p["look"][1:]
    return "\n".join([
        f"{look}. A {VIDEO_SECONDS}-second vertical mobile video ad for {p['name']} in three shots. {NO_TEXT}",
        f"SHOT ONE (0-2s): {per['who']}, {per['where']}, {per['when']}. {tension}.",
        f"HARD CUT. SHOT TWO (2-4s): {turn}. {p['hero']}.",
        f"HARD CUT. SHOT THREE (4-{VIDEO_SECONDS}s): {payoff}.",
        f"AUDIO: Music: {per['music']}, resolving in shot three and ending with {p['sonic_logo']}. "
        f"Sound effects: {p['sfx']}. Voiceover by {per['voice']}, in {per['language']}. "
        f"At 0 seconds the narrator says: \"{v['hook']}\"",
    ])


def poster_prompt(v):
    p, per = v["product"], v["persona"]
    return (f"{p['look'][0].upper() + p['look'][1:]}. Vertical 9:16 poster photograph for a mobile ad for {p['name']}: "
            f"{p['hero']}. In the background, {per['who']}, {per['where']}, {per['when']}. "
            f"Editorial food photography, shallow depth of field, the subject centered with calm negative space in the "
            f"top third and bottom quarter of the frame. {NO_TEXT}")


def script_text(v):
    p, per = v["product"], v["persona"]
    tension, turn, payoff = v["beats"]
    s, safe = v["story"], v.get("story_safe")
    # The sanitized reference is what sits next to the brand; the URL stays for provenance only.
    if s and safe:
        local = f"Local moment: {safe['reference']} (source: {s['url']})"
    elif s:
        local = f"Local moment: {s['title']} ({s['source'] or 'local news'}; {s['url']})"
    else:
        local = "Local moment: none attached"
    header = [f"{p['name']} x {v['audience']} - {VIDEO_SECONDS}-second vertical ad"]
    if v.get("campaign_name"):
        header.append(f"Campaign: {v['campaign_name']} ({v['campaign_id']})")
    return "\n".join([
        *header,
        f"Brief: {v['brief']}",
        local,
        "",
        f"HOOK (VO, 0s): \"{v['hook']}\"",
        f"SHOT ONE (0-2s): {per['who']}, {per['where']}, {per['when']}. {tension}.",
        f"SHOT TWO (2-4s): {turn}. {p['hero']}.",
        f"SHOT THREE (4-{VIDEO_SECONDS}s): {payoff}.",
        f"AUDIO: {per['music']}; {p['sfx']}; ends on {p['sonic_logo']}.",
        f"CTA (overlay): {v['cta']}",
        "",
        "Brand facts: " + "; ".join([p["category"]] + p.get("sources", [])),
        "Unofficial spec work for a hackathon experiment; not affiliated with or endorsed by the brand.",
    ])


# ---------------------------------------------------------------- staged variants (render-only mode)

SHOT_LINE = re.compile(r"^\s*(?P<t>[\d.]+\s*-\s*[\d.]+s)\s*\|\s*Shot:\s*(?P<shot>.*?)\s*(?:\|\s*On-screen text:.*?)?(?:\|\s*Voiceover:\s*\"?(?P<vo>.*?)\"?\s*)?$")


def prompts_from_script(script, hook, duration):
    """Video and poster prompts from a staged script.txt (viral-local-ad-generator layout: timed shot lines).
    On-screen text is dropped on purpose: the feed overlays hook and CTA itself."""
    shots = []
    for line in script.splitlines():
        m = SHOT_LINE.match(line)
        if m:
            shots.append((m.group("t").replace(" ", ""), m.group("shot").rstrip("."), (m.group("vo") or "").strip()))
    if not shots:  # free-form script: use its body as the visual description
        body = re.sub(r"\s+", " ", script).strip()
        shots = [(f"0-{duration}s", body[:900], "")]
    video = [f"A {duration}-second vertical 9:16 mobile video ad in {len(shots)} shots. Bright, clean, upbeat. {NO_TEXT}"]
    for i, (t, shot, _) in enumerate(shots):
        video.append(f"{'HARD CUT. ' if i else ''}SHOT {i + 1} ({t}): {shot}.")
    vo = " ".join(v for _, _, v in shots if v)
    video.append(f"AUDIO: upbeat modern soundtrack; a warm, friendly narrator in English. At 0 seconds the narrator says: \"{hook}\"."
                 + (f" Then: {vo[:400]}" if vo else ""))
    hero = next((s for _, s, _ in shots if "hero" in s.lower() or "product" in s.lower()), shots[len(shots) // 2][1])
    poster = (f"Vertical 9:16 poster photograph for a mobile ad: {hero}. Editorial photography, shallow depth of field, "
              f"the subject centered with calm negative space in the top third and bottom quarter of the frame. {NO_TEXT}")
    return "\n".join(video), poster


def staged_variants(campaign_dir):
    """Variants already staged under cdn/staging/<campaign>/<variant>/ (meta.json + script.txt), ready to render."""
    index = {}
    if (campaign_dir / "campaign.json").exists():
        index = json.loads((campaign_dir / "campaign.json").read_text())
    record = index.get("campaign") or {}
    out = []
    for vdir in sorted(p for p in campaign_dir.iterdir() if p.is_dir() and (p / "meta.json").exists()):
        if not SAFE_ID.fullmatch(vdir.name):
            continue
        meta = json.loads((vdir / "meta.json").read_text())
        script_file = meta.get("script_file") or "script.txt"
        script = (vdir / script_file).read_text() if (vdir / script_file).exists() else ""
        duration = int(meta.get("duration_s") or 10)
        duration = duration if duration in (5, 10) else 10
        video_p, poster_p = prompts_from_script(script, meta["hook"], duration)
        audience = (meta.get("targeting") or {}).get("audience") or []
        out.append({
            "variant_id": vdir.name, "hook": meta["hook"], "cta": meta["cta"],
            "audience": audience[0] if audience else "Open", "authored_by": (meta.get("source") or {}).get("agent", "staged"),
            "story": None, "story_safe": None, "duration_s": duration,
            "staged_meta": meta, "script_file": script_file, "script_text": script,
            "prompts": {"video": video_p, "poster": poster_p},
        })
    return record, out


# ---------------------------------------------------------------- cost

def estimate_usd(n_images, n_videos, seconds=VIDEO_SECONDS, resolution=RESOLUTION, draft=False):
    mp = POSTER_W * POSTER_H / 1e6
    image = IMAGE_USD_FIRST_MP + max(0.0, mp - 1.0) * IMAGE_USD_PER_EXTRA_MP
    per_sec = VIDEO_DRAFT_USD_PER_SEC if draft else VIDEO_USD_PER_SEC[resolution]
    return round(n_images * image, 4), round(n_videos * seconds * per_sec, 4)


# ---------------------------------------------------------------- BFL

def bfl(url, key, body=None):
    try:
        return render.call(url, key, body)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {detail[:800]}") from e


class OutOfCredits(RuntimeError):
    pass


def credits(key):
    try:
        return bfl(CREDITS_ENDPOINT, key).get("credits")
    except Exception as e:
        log(f"credits: unavailable ({e})")
        return None


def submit(url, key, body, label, retries=6):
    for attempt in range(retries):
        try:
            job = bfl(url, key, body)
            log(f"  submitted {label} -> {job.get('id')} quoted {job.get('cost')} credits")
            return job
        except RuntimeError as e:
            msg = str(e)
            if "HTTP 429" in msg or "HTTP 503" in msg:  # nothing was created; wait and resubmit
                time.sleep(20 * (attempt + 1))
                continue
            if "HTTP 402" in msg:
                raise OutOfCredits(f"{label}: BFL account has insufficient credits. Top up at dashboard.bfl.ai "
                                   "or rotate the BFL_API_KEY secret, then re-run.") from e
            raise
    raise RuntimeError(f"{label}: gave up submitting after repeated 429/503")


def poll_once(job, key, label, state):
    """One poll of a BFL task. Returns the final result dict, or None while still running.

    `state` is a per-task mutable dict used to tolerate a few transient "Task not found" replies."""
    try:
        res = render.call(job["polling_url"], key)
    except urllib.error.HTTPError as e:
        try:
            res = json.load(e)
        except ValueError:
            log(f"  {label} poll HTTP {e.code}, retrying")
            return None
    except OSError as e:
        log(f"  {label} poll error {e}, retrying")
        return None
    status = res.get("status")
    state["not_found"] = state.get("not_found", 0) + 1 if status == "Task not found" else 0
    if status not in render.DONE or 0 < state["not_found"] < 10:
        return None
    return res


def wait(job, key, label, timeout_s):
    deadline, state = time.time() + timeout_s, {}
    while time.time() < deadline:
        time.sleep(6)
        res = poll_once(job, key, label, state)
        if res is not None:
            return res
    return {"status": "Timeout", "id": job.get("id")}


def download(url, dest):
    with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    return dest.stat().st_size


# ---------------------------------------------------------------- Liquid QA

def liquid_chat(base, content, schema, max_tokens=200):
    body = {"messages": [{"role": "user", "content": content}], "temperature": 0.1, "max_tokens": max_tokens,
            "response_format": {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}}
    req = urllib.request.Request(f"{base.rstrip('/')}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.load(r)
    return json.loads(out["choices"][0]["message"]["content"])


def liquid_text_qa(base, v):
    prompt = (f"You review ad copy for brand safety. Brand: {v['product']['name']}. Hook: \"{v['hook']}\". "
              f"CTA: \"{v['cta']}\". Local story it sits next to: {v['story']['title'] if v['story'] else 'none'}. "
              "Answer ok=false if the copy is hateful, sexual, exploits a tragedy, names a private person, invents an "
              "offer or price, or implies the news subject endorses the brand.")
    return liquid_chat(base, prompt, {"type": "object", "properties": {"ok": {"type": "boolean"}, "reason": {"type": "string"}},
                                      "required": ["ok", "reason"]})


def liquid_vision_qa(base, image_path):
    data = base64.b64encode(image_path.read_bytes()).decode()
    content = [{"type": "text", "text": "Does this image contain readable text, letters, logos or brand marks? Describe briefly."},
               {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}]
    return liquid_chat(base, content, {"type": "object", "properties": {"has_text_or_logo": {"type": "boolean"},
                                                                          "description": {"type": "string"}},
                                        "required": ["has_text_or_logo", "description"]})


# ---------------------------------------------------------------- validation

def validate_staging(campaign_dir):
    """Run cdn/publish.py's own staging + schema checks when its deps are installed."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lh_publish", ROOT / "cdn" / "publish.py")
        pub = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pub)
    except Exception as e:  # google-cloud-storage / jsonschema missing locally
        log(f"validate: skipped cdn/publish.py checks ({e.__class__.__name__}: {e})")
        return None
    ads, uploads = pub.staged_ads(campaign_dir.parent, "validation-bucket")
    ads = [a for a in ads if a["campaign_id"] == campaign_dir.name]
    manifest = pub.merge_manifest({"ads": []}, ads)
    pub.validate_manifest(manifest)
    log(f"validate: {len(ads)} staged ads pass cdn/publish.py schema checks")
    return ads


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brief", default="Sightglass Coffee pour-over for the people who make San Francisco run before 8 AM")
    ap.add_argument("--campaign", default=None, help="campaign id (default local-news-YYYYMMDD)")
    ap.add_argument("--from-service", action="store_true",
                    help="load brief, market and audience for --campaign from the campaign service ($CAMPAIGN_SERVICE_URL)")
    ap.add_argument("--campaign-file", type=Path, default=None,
                    help="campaign record JSON, or a task-issue body with a ```json block; overrides --brief/--campaign/--market")
    ap.add_argument("--render-staged", metavar="CAMPAIGN_ID", default=None,
                    help="render posters/videos for the variants already staged under cdn/staging/<CAMPAIGN_ID>/*/meta.json "
                         "instead of discovering news and writing new scripts")
    ap.add_argument("--variants", type=int, default=4)
    ap.add_argument("--videos", default="2", help="how many of the top variants get a FLUX 3 video, or 'all'")
    ap.add_argument("--max-usd", type=float, default=5.0, help="abort if the estimate exceeds this; 0 = unlimited")
    ap.add_argument("--market", default=MARKET)
    ap.add_argument("--staging", type=Path, default=ROOT / "cdn" / "staging")
    ap.add_argument("--dry-run", action="store_true", help="discover, write the plan, estimate cost; call nothing paid")
    ap.add_argument("--timeout-minutes", type=float, default=40)
    ap.add_argument("--trace-dir", type=Path, default=os.environ.get("TRACE_DIR") or None,
                    help="where to write intermediate artifacts (prompts, BFL requests/results, events); "
                         "default $TRACE_DIR or out/trace/<campaign>")
    a = ap.parse_args()
    a.campaign_name, a.campaign_audience, a.brief_ref = None, None, None

    if a.campaign_file and a.from_service:
        sys.exit("use either --campaign-file or --from-service, not both")
    if a.campaign_file:
        try:
            apply_campaign_record(a, load_campaign_record(a.campaign_file))
        except (ValueError, OSError) as e:
            sys.exit(f"--campaign-file: {e}")
    elif a.from_service:
        if not a.campaign:
            sys.exit("--from-service needs --campaign <id>")
        try:
            apply_campaign_record(a, fetch_campaign_record(a.campaign))
        except ValueError as e:
            sys.exit(f"campaign service record is not usable: {e}")

    today = dt.datetime.now(dt.timezone.utc)
    campaign = a.render_staged or a.campaign or f"local-news-{today:%Y%m%d}"
    if not SAFE_ID.fullmatch(campaign):
        sys.exit(f"campaign id {campaign!r} must match {SAFE_ID.pattern}")
    if a.videos != "all" and not a.videos.isdigit():
        sys.exit("--videos must be an integer or 'all'")
    if not 1 <= a.variants <= 8:
        sys.exit("--variants must be 1..8")
    if a.max_usd < 0:
        sys.exit("--max-usd must be >= 0 (0 = unlimited)")
    trace.start(a.trace_dir or ROOT / "out" / "trace" / campaign)
    log(f"trace: {trace.dir}")

    if a.render_staged:
        campaign_dir = a.staging / campaign
        if not campaign_dir.is_dir():
            sys.exit(f"--render-staged: {campaign_dir} does not exist")
        record, variants = staged_variants(campaign_dir)
        if not variants:
            sys.exit(f"--render-staged: no <variant>/meta.json under {campaign_dir}")
        a.brief = record.get("brief") or a.brief
        a.market = record.get("geo") or a.market
        a.campaign_name = record.get("name") or None
        a.campaign_audience = (record.get("audience") or "").strip() or None
        stories, provenance = [], {"via": "staged", "agent": (variants[0]["staged_meta"].get("source") or {}).get("agent")}
        product_name = a.campaign_name or campaign
        log(f"render-staged: {len(variants)} variants under {campaign_dir} ({product_name})")
    else:
        data = json.loads((ADS / "scripts.json").read_text())
        stories, provenance = discover(a.market, a.variants)
        log(f"discovery via {provenance['via']}: " + " | ".join(short_topic(s) for s in stories))
        for s in stories:
            safe = sanitized(a.market, s)
            log(f"  sanitized: {safe['reference']} [{', '.join(safe['notes'])}]")
        product_key, variants = build_variants(a.brief, data, a.variants, stories, a.market)
        product_name = data["products"][product_key]["name"]
        for v in variants:
            v["prompts"] = {"video": video_prompt(v), "poster": poster_prompt(v)}
            v["duration_s"] = VIDEO_SECONDS

    n_videos = len(variants) if a.videos == "all" else min(int(a.videos), len(variants))
    for v in variants:
        v["brief"] = a.brief
        v["campaign_id"] = campaign
        v["campaign_name"] = a.campaign_name
        blocked = set()
        for text in (v["hook"], v["cta"], v["prompts"]["video"], v["prompts"]["poster"]):
            blocked |= find_famous_brand_terms(text)
        # scripts.json brands are the advertiser, not third parties; only foreign marks are a problem
        blocked -= {w for words in BRAND_KEYWORDS.values() for w in words}
        if blocked:
            sys.exit(f"{v['variant_id']}: creative references third-party brands: {sorted(blocked)}")

    video_seconds = sum(v["duration_s"] for v in variants[:n_videos])
    img_usd, _ = estimate_usd(len(variants), 0)
    vid_usd = round(video_seconds * VIDEO_USD_PER_SEC[RESOLUTION], 4)
    est = round(img_usd + vid_usd, 2)
    cap = "no cap" if a.max_usd == 0 else f"cap ${a.max_usd:.2f}"
    log(f"plan: {len(variants)} variants of {product_name}, {len(variants)} posters (~${img_usd:.2f}) "
        f"+ {n_videos} videos totalling {video_seconds}s {RESOLUTION} (~${vid_usd:.2f}) = ~${est:.2f}; {cap}")
    for i, v in enumerate(variants):
        log(f"  [{i + 1}] {v['variant_id']}: \"{v['hook'][:80]}\" / {v['cta']}" + (f" (video {v['duration_s']}s)" if i < n_videos else ""))
    if a.max_usd > 0 and est > a.max_usd:
        sys.exit(f"estimated ${est:.2f} exceeds --max-usd {a.max_usd:.2f}; aborting before any submit")

    campaign_dir = a.staging / campaign
    campaign_dir.mkdir(parents=True, exist_ok=True)
    run = {"campaign_id": campaign, "campaign_name": a.campaign_name, "brief": a.brief, "market": a.market,
           "audience": a.campaign_audience, "generated_at": today.isoformat(timespec="seconds"),
           "mode": "render-staged" if a.render_staged else "generate",
           "discovery": provenance, "stories": [s.to_dict() for s in stories],
           "sanitized_stories": [sanitized(a.market, s) for s in stories],
           "estimate_usd": {"images": img_usd, "videos": vid_usd, "total": est, "cap": a.max_usd or None},
           "variants": [], "liquid_qa": None}

    # Plan snapshot before anything is paid for: the exact prompts, scripts and stories behind each variant.
    trace.write_json("discovery.json", {"provenance": provenance, "stories": run["stories"],
                                        "sanitized_stories": run["sanitized_stories"]})
    plan = []
    for i, v in enumerate(variants):
        trace.variant(v)
        plan.append({k: v.get(k) for k in ("variant_id", "hook", "cta", "audience", "authored_by", "story", "story_safe",
                                           "duration_s", "prompts")}
                    | {"video_planned": i < n_videos, "mode": "render-staged" if v.get("staged_meta") else "generate"})
    trace.write_json("plan.json", {"campaign_id": campaign, "campaign_name": a.campaign_name, "brief": a.brief,
                                   "market": a.market, "audience": a.campaign_audience, "product": product_name,
                                   "estimate_usd": run["estimate_usd"], "variants": plan})

    if a.dry_run:
        for v in variants:
            run["variants"].append({k: v[k] for k in ("variant_id", "hook", "cta", "audience", "authored_by", "story",
                                                      "story_safe", "prompts")})
            if not v.get("staged_meta"):
                run["variants"][-1]["script"] = script_text(v)
        (campaign_dir / "run.json").write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n")
        trace.write_json("run.json", run)
        log(f"dry run: wrote {campaign_dir / 'run.json'}; nothing submitted")
        return

    key = os.environ.get("BFL_API_KEY") or os.environ.get("BLACK_FOREST")
    if not key:
        sys.exit("Set BFL_API_KEY (or BLACK_FOREST), or pass --dry-run")

    text_base, vision_base = os.environ.get("LIQUID_TEXT_BASE_URL"), os.environ.get("LIQUID_VISION_BASE_URL")
    if not (text_base or vision_base):
        log("liquid QA: skipped (LIQUID_TEXT_BASE_URL / LIQUID_VISION_BASE_URL not set)")
    qa = {}
    if text_base:
        for v in variants:
            try:
                qa[v["variant_id"]] = {"text": liquid_text_qa(text_base, v)}
            except Exception as e:
                qa[v["variant_id"]] = {"text": {"error": str(e)}}
            log(f"liquid text QA {v['variant_id']}: {qa[v['variant_id']]['text']}")
        trace.write_json("qa.json", qa)

    before = credits(key)
    log(f"credits before: {before}")
    timeout_s = a.timeout_minutes * 60
    deadline = time.time() + timeout_s

    # Submit everything first so BFL renders in parallel (6 tasks, well under the 24-task limit).
    jobs = []
    out_of_credits = None
    try:
        for i, v in enumerate(variants):
            img_body = {"prompt": v["prompts"]["poster"], "width": POSTER_W, "height": POSTER_H, "output_format": "jpeg",
                        "safety_tolerance": 2}
            job = submit(IMAGE_ENDPOINT, key, img_body, f"{v['variant_id']} poster")
            jobs.append((v, "poster", img_body, job))
            trace.write_json(f"{v['variant_id']}/poster.request.json",
                             {"endpoint": IMAGE_ENDPOINT, "body": img_body, "task": job, "submitted_at": dt.datetime.now(dt.timezone.utc)})
            if i < n_videos:
                vid_body = {"mode": "t2v", "prompt": v["prompts"]["video"], "aspect_ratio": "9:16", "duration": v["duration_s"],
                            "resolution": RESOLUTION, "generate_audio": True, "safety_tolerance": 2}
                job = submit(VIDEO_ENDPOINT, key, vid_body, f"{v['variant_id']} video")
                jobs.append((v, "video", vid_body, job))
                trace.write_json(f"{v['variant_id']}/video.request.json",
                                 {"endpoint": VIDEO_ENDPOINT, "body": vid_body, "task": job, "submitted_at": dt.datetime.now(dt.timezone.utc)})
    except OutOfCredits as e:
        out_of_credits = str(e)
        log(f"::error::{out_of_credits}")
        if not jobs:
            run["error"] = out_of_credits
            (campaign_dir / "run.json").write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n")
            sys.exit(out_of_credits)
        log(f"continuing with the {len(jobs)} tasks already paid for")
    quoted = sum(float(j.get("cost") or 0) for *_, j in jobs)
    log(f"all submitted; quoted total {quoted:.0f} credits (~${quoted / 100:.2f})")

    # Poll every task round-robin and download each result the moment it is Ready. Waiting on tasks one
    # at a time let a 12-minute video render outlive the 10-minute signed URL of an already-finished poster.
    results = {}
    pending = [(v, kind, body, job, {}) for v, kind, body, job in jobs]
    while pending:
        time.sleep(6)
        timed_out = time.time() >= deadline
        still_running = []
        for v, kind, body, job, state in pending:
            label = f"{v['variant_id']} {kind}"
            res = poll_once(job, key, label, state)
            if res is None:
                if not timed_out:
                    still_running.append((v, kind, body, job, state))
                    continue
                res = {"status": "Timeout", "id": job.get("id")}
            vdir = campaign_dir / v["variant_id"]
            vdir.mkdir(exist_ok=True)
            trace.write_json(f"{v['variant_id']}/{kind}.result.json",
                             {"finished_at": dt.datetime.now(dt.timezone.utc), "result": res})
            entry = {"task_id": job.get("id"), "quoted_credits": job.get("cost"), "status": res.get("status"),
                     "settled_credits": res.get("cost"), "request": {k: x for k, x in body.items() if k != "prompt"}}
            if res.get("status") == "Ready":
                url = render.find_url(res.get("result"))
                if url:
                    dest = vdir / ("poster.jpg" if kind == "poster" else "creative.mp4")
                    try:
                        entry["bytes"] = download(url, dest)  # signed URL expires (10 min image, ~2 h video): fetch now
                        entry["file"] = dest.name
                        log(f"  saved {dest} ({entry['bytes']} bytes, settled {res.get('cost')} credits)")
                    except (urllib.error.URLError, OSError) as e:
                        entry["status"] = "Download-failed"
                        entry["error"] = str(e)
                        dest.unlink(missing_ok=True)
                        log(f"::warning::{label} ready but download failed: {e}")
                else:
                    entry["status"] = "Ready-without-url"
                    log(f"  {label} ready but no URL: {json.dumps(res)[:300]}")
            else:
                log(f"  {label} ended {res.get('status')}: {res.get('details')}")
            results.setdefault(v["variant_id"], {})[kind] = entry
        pending = still_running

    if vision_base:
        for v in variants:
            poster = campaign_dir / v["variant_id"] / "poster.jpg"
            if poster.exists():
                try:
                    qa.setdefault(v["variant_id"], {})["vision"] = liquid_vision_qa(vision_base, poster)
                except Exception as e:
                    qa.setdefault(v["variant_id"], {})["vision"] = {"error": str(e)}
                log(f"liquid vision QA {v['variant_id']}: {qa[v['variant_id']]['vision']}")
    run["liquid_qa"] = qa or "skipped"
    if out_of_credits:
        run["error"] = out_of_credits

    published = 0
    for v in variants:
        r = results.get(v["variant_id"], {})
        vdir = campaign_dir / v["variant_id"]
        has_video = r.get("video", {}).get("file") == "creative.mp4"
        has_poster = r.get("poster", {}).get("file") == "poster.jpg"
        if not (has_video or has_poster):
            log(f"{v['variant_id']}: no media rendered; not staged")
            if vdir.exists() and not v.get("staged_meta"):  # never delete a variant Thomas already staged
                for f in vdir.glob("*"):
                    f.unlink()
                vdir.rmdir()
            run["variants"].append({"variant_id": v["variant_id"], "staged": False, "render": r})
            continue
        text_verdict = (qa.get(v["variant_id"], {}).get("text") or {})
        active = text_verdict.get("ok", True) is not False
        stamp = today.isoformat(timespec="seconds").replace("+00:00", "Z")
        if v.get("staged_meta"):
            # Render-only mode: keep Thomas's id, hook, cta, targeting and script; swap the media in.
            meta = dict(v["staged_meta"])
            meta["media_type"] = "video" if has_video else "image"
            meta["media_file"] = "creative.mp4" if has_video else "poster.jpg"
            meta["script_file"] = v["script_file"]
            meta.setdefault("targeting", {})["weight"] = 2 if has_video else 1
            if text_verdict.get("ok") is False:
                meta["targeting"]["active"] = False
            # source allows only agent/generated_at/brief_ref; the render provenance lives in run.json.
            meta["source"] = {**(meta.get("source") or {}), "generated_at": stamp}
        else:
            (vdir / "script.txt").write_text(script_text(v) + "\n")
            # Persona label first, then the campaign's own audience line so the feed shows both.
            audience = [v["audience"]] + ([a.campaign_audience] if a.campaign_audience else [])
            meta = {
                "id": f"{campaign}-{slug(v['variant_id'])}",
                "hook": v["hook"], "cta": v["cta"],
                "media_type": "video" if has_video else "image",
                "media_file": "creative.mp4" if has_video else "poster.jpg",
                "script_file": "script.txt",
                "aspect": "9:16",
                "targeting": {"audience": audience, "geo": ["US"], "weight": 2 if has_video else 1, "active": active},
                "source": {"agent": "scripts/generate-content.py", "generated_at": stamp,
                           "brief_ref": a.brief_ref or (v["story"]["url"] if v["story"] and v["story"].get("url") else a.brief)},
            }
        if has_poster:
            meta["poster_file"] = "poster.jpg"
        if has_video:
            meta["duration_s"] = v["duration_s"]
        elif not v.get("staged_meta"):
            meta.pop("duration_s", None)
        (vdir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        published += 1
        run["variants"].append({"variant_id": v["variant_id"], "staged": True, "id": meta["id"], "media_type": meta["media_type"],
                                "hook": v["hook"], "cta": v["cta"], "audience": v["audience"], "authored_by": v["authored_by"],
                                "active": active, "story": v["story"], "story_safe": v.get("story_safe"),
                                "prompts": v["prompts"], "render": r})

    after = credits(key)
    settled = sum(float(e.get("settled_credits") or e.get("quoted_credits") or 0) for r in results.values() for e in r.values())
    run["cost"] = {"quoted_credits": quoted, "settled_credits": settled, "settled_usd": round(settled / 100, 4),
                   "credits_before": before, "credits_after": after,
                   "spent_by_balance_usd": round((before - after) / 100, 4) if before is not None and after is not None else None}
    (campaign_dir / "run.json").write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n")
    trace.write_json("run.json", run)
    log(f"cost: quoted {quoted:.0f} credits, settled {settled:.0f} credits (~${settled / 100:.2f}); balance {before} -> {after}")

    if published == 0:
        sys.exit("no variant produced media; nothing staged")
    validate_staging(campaign_dir)
    log(f"staged {published}/{len(variants)} variants under {campaign_dir}")


if __name__ == "__main__":
    main()

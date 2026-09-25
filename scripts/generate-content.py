#!/usr/bin/env python3
"""Local-news discovery -> N ad variants -> BFL poster images and FLUX 3 videos -> cdn/staging.

    python3 scripts/generate-content.py --dry-run                     # plan and cost estimate only
    python3 scripts/generate-content.py --brief "Tartine morning buns for Dolores Park weekends"
    python3 scripts/generate-content.py --variants 4 --videos 2 --max-usd 5

Reuses Aayush's modules in content/ads (nimble.py for discovery, scripts.json for brand facts,
personas and authored stories, render.py for the BFL call and result parsing) and Thomas's
viral-local-ad-generator (brand-safety scoring, story ranking, brand guard, built-in stories).

Discovery order: Nimble (NIMBLE_API_KEY) -> live rows in content/ads/facts.json -> Thomas's
built-in stories. Media: one 9:16 poster per variant via /v1/flux-2-pro, a 5 s 9:16 hd
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
    is_brand_safe,
    mock_stories,
    normalize_nimble_results,
)
from viral_local_ad_generator.pipeline import select_stories  # noqa: E402

API_BASE = os.environ.get("BFL_API_BASE", "https://api.bfl.ai").rstrip("/")
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


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- discovery

def story_from_fact(row):
    fact = row.get("fact", "")
    title, _, snippet = fact.partition(": ")
    return NewsStory(title=title.strip(), url=row.get("source", ""), source="Nimble (facts.json)",
                     published_at=row.get("retrieved_at", ""), snippet=snippet.strip(),
                     relevance_score=0.7, virality_score=0.6,
                     brand_safe=is_brand_safe(title, snippet, row.get("source", "")))


def discover(market, count):
    """Returns (stories, provenance). Never raises: every layer falls through to the next."""
    query = f"{market} viral local news this week"
    if os.environ.get("NIMBLE_API_KEY"):
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


# ---------------------------------------------------------------- variants

def pick_product(brief, data):
    low = brief.lower()
    for key, words in BRAND_KEYWORDS.items():
        if any(w in low for w in words):
            return key
    return "sightglass"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def build_variants(brief, data, n, stories):
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
    s = v["story"]
    local = (f"Local moment: {s['title']} ({s['source'] or 'local news'}; {s['url']})" if s
             else "Local moment: none attached")
    return "\n".join([
        f"{p['name']} x {v['audience']} - {VIDEO_SECONDS}-second vertical ad",
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
            raise
    raise RuntimeError(f"{label}: gave up submitting after repeated 429/503")


def wait(job, key, label, timeout_s):
    poll, deadline, not_found = job["polling_url"], time.time() + timeout_s, 0
    while time.time() < deadline:
        time.sleep(6)
        try:
            res = render.call(poll, key)
        except urllib.error.HTTPError as e:
            try:
                res = json.load(e)
            except ValueError:
                log(f"  {label} poll HTTP {e.code}, retrying")
                continue
        except OSError as e:
            log(f"  {label} poll error {e}, retrying")
            continue
        status = res.get("status")
        not_found = not_found + 1 if status == "Task not found" else 0
        if status not in render.DONE or 0 < not_found < 10:
            continue
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
    ap.add_argument("--variants", type=int, default=4)
    ap.add_argument("--videos", type=int, default=2, help="how many of the top variants get a FLUX 3 video")
    ap.add_argument("--max-usd", type=float, default=5.0)
    ap.add_argument("--market", default=MARKET)
    ap.add_argument("--staging", type=Path, default=ROOT / "cdn" / "staging")
    ap.add_argument("--dry-run", action="store_true", help="discover, write the plan, estimate cost; call nothing paid")
    ap.add_argument("--timeout-minutes", type=float, default=40)
    a = ap.parse_args()

    today = dt.datetime.now(dt.timezone.utc)
    campaign = a.campaign or f"local-news-{today:%Y%m%d}"
    if not SAFE_ID.fullmatch(campaign):
        sys.exit(f"campaign id {campaign!r} must match {SAFE_ID.pattern}")
    if not 1 <= a.variants <= 8 or not 0 <= a.videos <= a.variants:
        sys.exit("--variants must be 1..8 and 0 <= --videos <= --variants")

    data = json.loads((ADS / "scripts.json").read_text())
    stories, provenance = discover(a.market, a.variants)
    log(f"discovery via {provenance['via']}: " + " | ".join(short_topic(s) for s in stories))

    product_key, variants = build_variants(a.brief, data, a.variants, stories)
    for v in variants:
        v["brief"] = a.brief
        v["prompts"] = {"video": video_prompt(v), "poster": poster_prompt(v)}
        blocked = set()
        for text in (v["hook"], v["cta"], v["prompts"]["video"], v["prompts"]["poster"]):
            blocked |= find_famous_brand_terms(text)
        # scripts.json brands are the advertiser, not third parties; only foreign marks are a problem
        blocked -= {w for words in BRAND_KEYWORDS.values() for w in words}
        if blocked:
            sys.exit(f"{v['variant_id']}: creative references third-party brands: {sorted(blocked)}")

    img_usd, vid_usd = estimate_usd(len(variants), a.videos)
    est = round(img_usd + vid_usd, 2)
    log(f"plan: {len(variants)} variants of {data['products'][product_key]['name']}, {len(variants)} posters (~${img_usd:.2f}) "
        f"+ {a.videos} x {VIDEO_SECONDS}s {RESOLUTION} videos (~${vid_usd:.2f}) = ~${est:.2f}; cap ${a.max_usd:.2f}")
    for i, v in enumerate(variants):
        log(f"  [{i + 1}] {v['variant_id']}: \"{v['hook']}\" / {v['cta']}" + (" (video)" if i < a.videos else ""))
    if est > a.max_usd:
        sys.exit(f"estimated ${est:.2f} exceeds --max-usd {a.max_usd:.2f}; aborting before any submit")

    campaign_dir = a.staging / campaign
    campaign_dir.mkdir(parents=True, exist_ok=True)
    run = {"campaign_id": campaign, "brief": a.brief, "market": a.market, "generated_at": today.isoformat(timespec="seconds"),
           "discovery": provenance, "stories": [s.to_dict() for s in stories],
           "estimate_usd": {"images": img_usd, "videos": vid_usd, "total": est, "cap": a.max_usd},
           "variants": [], "liquid_qa": None}

    if a.dry_run:
        for v in variants:
            run["variants"].append({k: v[k] for k in ("variant_id", "hook", "cta", "audience", "authored_by", "story", "prompts")})
        (campaign_dir / "run.json").write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n")
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

    before = credits(key)
    log(f"credits before: {before}")
    timeout_s = a.timeout_minutes * 60
    deadline = time.time() + timeout_s

    # Submit everything first so BFL renders in parallel (6 tasks, well under the 24-task limit).
    jobs = []
    for i, v in enumerate(variants):
        img_body = {"prompt": v["prompts"]["poster"], "width": POSTER_W, "height": POSTER_H, "output_format": "jpeg",
                    "safety_tolerance": 2}
        jobs.append((v, "poster", img_body, submit(IMAGE_ENDPOINT, key, img_body, f"{v['variant_id']} poster")))
        if i < a.videos:
            vid_body = {"mode": "t2v", "prompt": v["prompts"]["video"], "aspect_ratio": "9:16", "duration": VIDEO_SECONDS,
                        "resolution": RESOLUTION, "generate_audio": True, "safety_tolerance": 2}
            jobs.append((v, "video", vid_body, submit(VIDEO_ENDPOINT, key, vid_body, f"{v['variant_id']} video")))
    quoted = sum(float(j.get("cost") or 0) for *_, j in jobs)
    log(f"all submitted; quoted total {quoted:.0f} credits (~${quoted / 100:.2f})")

    results = {}
    for v, kind, body, job in jobs:
        label = f"{v['variant_id']} {kind}"
        res = wait(job, key, label, max(60, deadline - time.time()))
        vdir = campaign_dir / v["variant_id"]
        vdir.mkdir(exist_ok=True)
        entry = {"task_id": job.get("id"), "quoted_credits": job.get("cost"), "status": res.get("status"),
                 "settled_credits": res.get("cost"), "request": {k: x for k, x in body.items() if k != "prompt"}}
        if res.get("status") == "Ready":
            url = render.find_url(res.get("result"))
            if url:
                dest = vdir / ("poster.jpg" if kind == "poster" else "creative.mp4")
                entry["bytes"] = download(url, dest)  # signed URL expires (10 min image, ~2 h video): fetch now
                entry["file"] = dest.name
                log(f"  saved {dest} ({entry['bytes']} bytes, settled {res.get('cost')} credits)")
            else:
                entry["status"] = "Ready-without-url"
                log(f"  {label} ready but no URL: {json.dumps(res)[:300]}")
        else:
            log(f"  {label} ended {res.get('status')}: {res.get('details')}")
        results.setdefault(v["variant_id"], {})[kind] = entry

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

    published = 0
    for v in variants:
        r = results.get(v["variant_id"], {})
        vdir = campaign_dir / v["variant_id"]
        has_video = r.get("video", {}).get("file") == "creative.mp4"
        has_poster = r.get("poster", {}).get("file") == "poster.jpg"
        if not (has_video or has_poster):
            log(f"{v['variant_id']}: no media rendered; not staged")
            for f in vdir.glob("*"):
                f.unlink()
            vdir.rmdir()
            run["variants"].append({"variant_id": v["variant_id"], "staged": False, "render": r})
            continue
        (vdir / "script.txt").write_text(script_text(v) + "\n")
        text_verdict = (qa.get(v["variant_id"], {}).get("text") or {})
        active = text_verdict.get("ok", True) is not False
        meta = {
            "id": f"{campaign}-{slug(v['variant_id'])}",
            "hook": v["hook"], "cta": v["cta"],
            "media_type": "video" if has_video else "image",
            "media_file": "creative.mp4" if has_video else "poster.jpg",
            "script_file": "script.txt",
            "aspect": "9:16",
            "targeting": {"audience": [v["audience"]], "geo": ["US"], "weight": 2 if has_video else 1, "active": active},
            "source": {"agent": "scripts/generate-content.py", "generated_at": today.isoformat(timespec="seconds").replace("+00:00", "Z"),
                       "brief_ref": v["story"]["url"] if v["story"] and v["story"].get("url") else a.brief},
        }
        if has_poster:
            meta["poster_file"] = "poster.jpg"
        if has_video:
            meta["duration_s"] = VIDEO_SECONDS
        (vdir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        published += 1
        run["variants"].append({"variant_id": v["variant_id"], "staged": True, "id": meta["id"], "media_type": meta["media_type"],
                                "hook": v["hook"], "cta": v["cta"], "audience": v["audience"], "authored_by": v["authored_by"],
                                "active": active, "story": v["story"], "prompts": v["prompts"], "render": r})

    after = credits(key)
    settled = sum(float(e.get("settled_credits") or e.get("quoted_credits") or 0) for r in results.values() for e in r.values())
    run["cost"] = {"quoted_credits": quoted, "settled_credits": settled, "settled_usd": round(settled / 100, 4),
                   "credits_before": before, "credits_after": after,
                   "spent_by_balance_usd": round((before - after) / 100, 4) if before is not None and after is not None else None}
    (campaign_dir / "run.json").write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n")
    log(f"cost: quoted {quoted:.0f} credits, settled {settled:.0f} credits (~${settled / 100:.2f}); balance {before} -> {after}")

    if published == 0:
        sys.exit("no variant produced media; nothing staged")
    validate_staging(campaign_dir)
    log(f"staged {published}/{len(variants)} variants under {campaign_dir}")


if __name__ == "__main__":
    main()

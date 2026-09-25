#!/usr/bin/env python3
"""Compile product x persona ad scripts into FLUX 3 video prompts and optionally render them.

Dry run (default) prints each compiled request and an estimated cost. --submit sends
them to POST https://api.bfl.ai/v1/flux-3-video, polls until Ready, and downloads the
MP4 to content/ads/out/ (result URLs expire, so download right away).

Key: read from BLACK_FOREST (or BFL_API_KEY). Never commit it.

    python3 content/ads/render.py                         # dry run, all variants
    python3 content/ads/render.py --only hush__indie_dev  # one variant
    python3 content/ads/render.py --submit --draft        # render drafts (cheaper)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://api.bfl.ai/v1/flux-3-video"
# USD per second at hd for t2v, from BFL's published price table; draft is about a third.
USD_PER_SEC_HD = 0.17


def compile_prompt(product, persona, variant, duration, aspect_ratio):
    t1, t2 = round(duration * 0.3), round(duration * 0.7)
    orientation = "vertical" if aspect_ratio == "9:16" else aspect_ratio
    hook, close = variant["lines"]
    return "\n".join([
        f"{product['look'][0].upper() + product['look'][1:]}. A {duration}-second {orientation} mobile video ad in three shots. "
        "No on-screen text, captions, or subtitles.",
        f"SHOT ONE (0-{t1}s): {persona['who']}, {persona['where']}, {persona['when']}. {variant['tension']}.",
        f"HARD CUT. SHOT TWO ({t1}-{t2}s): {variant['turn']}. {product['hero']}.",
        f"HARD CUT. SHOT THREE ({t2}-{duration}s): {variant['payoff']}.",
        f"AUDIO: Music: {persona['music']}, building through shot two and resolving in shot three, "
        f"ending with {product['sonic_logo']}. Sound effects: {product['sfx']}. "
        f"Voiceover by {persona['voice']}, in {persona['language']}. "
        f"Over shot one the narrator says: \"{hook}\" "
        f"Over shot three the narrator says: \"{close}\"",
    ])


def build_requests(data, only, draft):
    d = data["defaults"]
    for v in data["variants"]:
        if only and v["id"] not in only:
            continue
        body = {
            "mode": d["mode"],
            "prompt": compile_prompt(data["products"][v["product"]], data["personas"][v["persona"]],
                                     v, d["duration"], d["aspect_ratio"]),
            "duration": d["duration"],
            "aspect_ratio": d["aspect_ratio"],
            "resolution": d["resolution"],
            "generate_audio": d["generate_audio"],
        }
        if draft:
            body["draft"] = True
        yield v, body


def call(url, key, body=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"x-key": key, "accept": "application/json", "content-type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def find_url(obj):
    """First http(s) URL anywhere in the result payload."""
    if isinstance(obj, str):
        return obj if obj.startswith("http") else None
    items = obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else []
    for x in items:
        if u := find_url(x):
            return u
    return None


def render(variant, body, key, out_dir):
    job = call(API, key, body)
    poll = job["polling_url"]
    print(f"  submitted {variant['id']} -> {job.get('id')}", flush=True)
    while True:
        time.sleep(5)
        res = call(poll, key)
        status = res.get("status")
        if status == "Ready":
            url = find_url(res.get("result"))
            dest = out_dir / f"{variant['id']}.mp4"
            urllib.request.urlretrieve(url, dest)
            (out_dir / f"{variant['id']}.json").write_text(json.dumps({"request": body, "result": res}, indent=2))
            print(f"  saved {dest}")
            return
        if status not in ("Pending", "Processing", "Queued", "Task not found"):
            print(f"  {variant['id']} failed: {status} {res}", file=sys.stderr)
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", default=HERE / "scripts.json", type=Path)
    ap.add_argument("--only", nargs="*", help="variant ids to include")
    ap.add_argument("--submit", action="store_true", help="call the BFL API (costs credits)")
    ap.add_argument("--draft", action="store_true", help="request draft quality (about a third of the cost)")
    args = ap.parse_args()

    data = json.loads(args.scripts.read_text())
    reqs = list(build_requests(data, args.only, args.draft))
    secs = sum(b["duration"] for _, b in reqs)
    est = secs * USD_PER_SEC_HD * (1 / 3 if args.draft else 1)
    print(f"{len(reqs)} variants, {secs}s of video, about ${est:.2f} at {'draft' if args.draft else 'hd'}\n")

    if not args.submit:
        for v, body in reqs:
            print(f"=== {v['id']} ===\n{body['prompt']}\n")
        return

    key = os.environ.get("BLACK_FOREST") or os.environ.get("BFL_API_KEY")
    if not key:
        sys.exit("Set BLACK_FOREST (or BFL_API_KEY) in the environment.")
    out_dir = HERE / "out"
    out_dir.mkdir(exist_ok=True)
    for v, body in reqs:
        render(v, body, key, out_dir)


if __name__ == "__main__":
    main()

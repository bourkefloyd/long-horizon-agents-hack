#!/usr/bin/env python3
"""Compile product x persona ad scripts into FLUX 3 video prompts and optionally render them.

Clips that already exist in out/ are skipped unless --force.

Dry run (default) prints each compiled request and an estimated cost. --submit sends
them to POST https://api.bfl.ai/v1/flux-3-video, polls until Ready, and downloads the
MP4 to content/ads/out/ (result URLs expire, so download right away).

Key: read from BLACK_FOREST (or BFL_API_KEY). Never commit it.

    python3 content/ads/render.py                         # dry run, all variants
    python3 content/ads/render.py --only hush__indie_dev  # one variant
    python3 content/ads/render.py --submit --draft        # render drafts (cheaper)
    python3 content/ads/render.py --submit --continuations --only sightglass__fog_narrator
                                                          # clip + the clip its button branches to
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://api.bfl.ai/v1/flux-3-video"
# USD per second at hd for t2v, from BFL's published price table; draft is about a third.
USD_PER_SEC_HD = 0.17
# Terminal statuses from BFL's video quickstart; anything else (Pending, Reasoning, Generating) is in progress.
DONE = {"Ready", "Request Moderated", "Content Moderated", "Error", "Task not found"}


def compile_shots(product, persona, variant, duration, aspect_ratio):
    """Explicit timed shots. On-screen text is burned in afterwards by caption.py, not drawn by FLUX."""
    orientation = "vertical" if aspect_ratio == "9:16" else aspect_ratio
    lines = [f"{product['look'][0].upper() + product['look'][1:]}. A {duration}-second {orientation} mobile video ad "
             f"in {len(variant['shots'])} shots. No on-screen text, captions, subtitles, logos or readable words."]
    names = ["ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX"]
    for i, s in enumerate(variant["shots"]):
        lead = "" if i == 0 else "HARD CUT. "
        lines.append(f"{lead}SHOT {names[i]} ({s['t'][0]}-{s['t'][1]}s): {s['shot']}.")
    vo = " ".join(f"At {s['t'][0]} seconds the narrator says: \"{s['vo']}\"" for s in variant["shots"] if s.get("vo"))
    lines.append(f"AUDIO: Music: {persona['music']}, ending with {product['sonic_logo']}. "
                 f"Sound effects: {product['sfx']}. Voiceover by {persona['voice']}, in {persona['language']}. {vo}")
    return "\n".join(lines)


def compile_prompt(product, persona, variant, duration, aspect_ratio):
    if "shots" in variant:
        return compile_shots(product, persona, variant, duration, aspect_ratio)
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


def submit(item_id, body, key, out_dir):
    """Submit once. The polling URL is saved to out/<id>.job.json so a rerun resumes instead of paying again."""
    job_file = out_dir / f"{item_id}.job.json"
    if job_file.exists():
        poll = json.loads(job_file.read_text())["polling_url"]
        print(f"  resuming {item_id}", flush=True)
        return poll
    job = call(API, key, body)
    job_file.write_text(json.dumps({"id": job.get("id"), "polling_url": job["polling_url"]}))
    print(f"  submitted {item_id} -> {job.get('id')}", flush=True)
    return job["polling_url"]


def wait(item_id, poll, body, key, out_dir):
    not_found = 0
    while True:
        time.sleep(5)
        try:
            res = call(poll, key)
        except urllib.error.HTTPError as e:  # "Task not found" arrives as a 404 with a JSON status body
            try:
                res = json.load(e)
            except ValueError:
                print(f"  {item_id} poll error, retrying: {e}", file=sys.stderr)
                continue
        except OSError as e:  # transient network error: keep polling, the job is still running
            print(f"  {item_id} poll error, retrying: {e}", file=sys.stderr)
            continue
        status = res.get("status")
        # The polling host sometimes routes to a node that doesn't know the job yet or any more;
        # only trust "Task not found" once it repeats for about a minute.
        not_found = not_found + 1 if status == "Task not found" else 0
        if status not in DONE or 0 < not_found < 12:
            continue
        (out_dir / f"{item_id}.job.json").unlink(missing_ok=True)
        if status == "Ready":
            url = find_url(res.get("result"))
            if not url:
                print(f"  {item_id} ready but no URL in result: {res}", file=sys.stderr)
                return False
            dest = out_dir / f"{item_id}.mp4"
            urllib.request.urlretrieve(url, dest)
            meta = {"request": {k: v for k, v in body.items() if k != "start_video"}, "result": res}
            (out_dir / f"{item_id}.json").write_text(json.dumps(meta, indent=2))
            print(f"  saved {dest}")
            return True
        print(f"  {item_id} ended {status}: {res.get('details')}. Error: resubmit. Moderated: reword.",
              file=sys.stderr)
        return False


def render_batch(jobs, key, out_dir):
    """Submit every job first so BFL runs them in parallel, then poll each."""
    polls = [(item_id, submit(item_id, body, key, out_dir), body) for item_id, body in jobs]
    for item_id, poll, body in polls:
        wait(item_id, poll, body, key, out_dir)


def continuation_body(c, d, out_dir, draft):
    """v2v: extend the parent clip. The parent MP4 must already be rendered."""
    parent = out_dir / f"{c['parent']}.mp4"
    body = {
        "mode": "v2v",
        "prompt": c["prompt"],
        "start_video": base64.b64encode(parent.read_bytes()).decode(),
        "duration": c.get("duration", 5),
        "aspect_ratio": d["aspect_ratio"],
        "resolution": d["resolution"],
        "generate_audio": d["generate_audio"],
    }
    if draft:
        body["draft"] = True
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", default=HERE / "scripts.json", type=Path)
    ap.add_argument("--only", nargs="*", help="variant ids to include")
    ap.add_argument("--submit", action="store_true", help="call the BFL API (costs credits)")
    ap.add_argument("--draft", action="store_true", help="request draft quality (about a third of the cost)")
    ap.add_argument("--continuations", action="store_true",
                    help="also render the v2v clips that play after a button tap (continuation pricing is higher)")
    ap.add_argument("--force", action="store_true", help="re-render clips that already exist in out/")
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

    todo = [(v["id"], b) for v, b in reqs if args.force or not (out_dir / f"{v['id']}.mp4").exists()]
    render_batch(todo, key, out_dir)

    if args.continuations:
        ids = {v["id"] for v, _ in reqs}
        conts = [c for c in data.get("continuations", [])
                 if c["parent"] in ids and (out_dir / f"{c['parent']}.mp4").exists()
                 and (args.force or not (out_dir / f"{c['id']}.mp4").exists())]
        render_batch([(c["id"], continuation_body(c, data["defaults"], out_dir, args.draft)) for c in conts],
                     key, out_dir)

if __name__ == "__main__":
    main()

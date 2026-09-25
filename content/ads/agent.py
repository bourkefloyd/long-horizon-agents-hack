#!/usr/bin/env python3
"""Turn one feed action into one FLUX 3 render. The feed's db holds the requests; this does the work.

    python3 content/ads/agent.py order   REQ_ID '{"bun": "sourdough", "cheese": "pepper jack", "extra": "jalapeños"}'
    python3 content/ads/agent.py episode REQ_ID '{"parent": "sightglass__n_judah_commuter", "episode": 2}'
    python3 content/ads/agent.py selfie  REQ_ID '{"image": "/path/to/selfie.jpg"}'

Writes out/<REQ_ID>.mp4. Key from BLACK_FOREST. The selfie file is deleted after the render is submitted.
"""

import base64
import json
import os
import sys
from pathlib import Path

import render

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

# Idea 6: the saga continues one beat per episode. The feed stores only the last clip and the beat index.
SAGA = {
    2: "Continue the same shot and character. Inside the bright roastery he finally gets a seat by the fogged "
       "window, opens his laptop, and the stranger at the next table lifts the same ceramic cup; they share a nod. "
       "Same lo-fi beat continues. The narrator says: \"Episode two. Same fog, new regular.\"",
    3: "Continue the same character. The next foggy morning he sprints and makes the streetcar just as the doors "
       "close, raises his coffee cup in triumph through the window. Lo-fi beat lifts with a bright chord. "
       "The narrator says: \"Episode three. Made the train.\"",
    4: "Continue the same character. Sunny afternoon, he walks out of the roastery with two cups and hands one to "
       "the stranger from episode two, both laughing. Beat resolves warmly. The narrator says: \"Episode four. Coffee for two.\"",
}


def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def body_for(kind, p, defaults):
    base = {"aspect_ratio": defaults["aspect_ratio"], "resolution": defaults["resolution"], "generate_audio": True}
    if kind == "order":
        build = f"{p['bun']} bun, {p['cheese']}, {p['extra']}"
        return {**base, "mode": "t2v", "duration": 10, "prompt": (
            "Punchy social-feed look, saturated warm colors, crisp commercial food lighting. A 10-second vertical "
            "mobile video ad. No on-screen text, captions, logos or readable words.\n"
            f"SHOT ONE (0-4s): a cook at a sizzling flat-top grill in a sunny San Francisco burger shop builds one "
            f"double smash burger to order: {build}. Each ingredient lands on the stack in a satisfying close-up.\n"
            "HARD CUT. SHOT TWO (4-10s): the finished burger in slow-motion hero close-up on a counter in bright "
            "sunshine, cheese dripping, then a hand slides it forward toward the camera.\n"
            "AUDIO: Music: upbeat hip hop beat with snappy hi-hats. Sound effects: sizzle, a crunchy bite. Voiceover by "
            "an energetic, friendly young narrator, American English. At 1 second the narrator says: "
            f"\"You built it: {build}.\" At 6 seconds the narrator says: \"Your Sutro Stack is ready.\"")}
    if kind == "episode":
        parent = OUT / f"{p['parent']}.mp4"
        return {**base, "mode": "v2v", "duration": 5, "start_video": b64(parent), "prompt": SAGA[int(p["episode"])]}
    if kind == "selfie":
        return {**base, "mode": "t2v", "duration": 10, "reference_images": [b64(p["image"])], "prompt": (
            "Punchy social-feed look, bright sunny San Francisco lunchtime, saturated warm colors. A 10-second "
            "vertical mobile video ad. No on-screen text, captions, logos or readable words.\n"
            "SHOT ONE (0-4s): the person from the reference images, same face and hair, walks up to the counter of "
            "a sunny SoMa burger shop and grins at the camera.\n"
            "HARD CUT. SHOT TWO (4-10s): the same person from the reference images takes a big bite of a double "
            "smash burger on a toasted sourdough bun, eyes closed in delight, then gives a thumbs up.\n"
            "AUDIO: Music: upbeat hip hop beat. Sound effects: sizzle, a crunchy bite. Voiceover by an energetic "
            "narrator, American English. At 6 seconds the narrator says: \"Lunch looks good on you.\"")}
    raise ValueError(kind)


def main(kind, req_id, payload):
    p = json.loads(payload)
    defaults = json.loads((HERE / "scripts.json").read_text())["defaults"]
    key = os.environ.get("BLACK_FOREST") or os.environ.get("BFL_API_KEY")
    if not key:
        sys.exit("Set BLACK_FOREST (or BFL_API_KEY) in the environment.")
    OUT.mkdir(exist_ok=True)
    body = body_for(kind, p, defaults)
    poll = render.submit(req_id, body, key, OUT)
    if kind == "selfie":
        Path(p["image"]).unlink(missing_ok=True)  # used once, then dropped
    ok = render.wait(req_id, poll, body, key, OUT)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(*sys.argv[1:4])

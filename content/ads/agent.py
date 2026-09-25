#!/usr/bin/env python3
"""Turn one feed action into one FLUX 3 render. The feed's db holds the requests; this does the work.

    python3 content/ads/agent.py order   REQ_ID '{"brand": "sutro", "bun": "sourdough", "cheese": "pepper jack", "extra": "jalapeños"}'
    python3 content/ads/agent.py order   REQ_ID '{"brand": "sightglass", "drink": "latte", "milk": "oat", "temp": "iced"}'
    python3 content/ads/agent.py episode REQ_ID '{"brand": "sightglass", "parent": "sightglass__n_judah_commuter", "episode": 2}'
    python3 content/ads/agent.py selfie  REQ_ID '{"brand": "sutro", "image": "/path/to/selfie.jpg"}'

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


SCENE = {
    "sutro": {
        "look": "Punchy social-feed look, saturated warm colors, crisp commercial food lighting",
        "place": "a sunny San Francisco burger shop",
        "hero": "a double smash burger on a toasted sourdough bun",
        "music": "upbeat hip hop beat with snappy hi-hats",
        "sfx": "sizzle on a flat-top grill, a crunchy bite",
        "next": "the story moves forward to a warm payoff: the burger gets its first big bite and everyone at the table laughs",
    },
    "sightglass": {
        "look": "Bright airy look, tall industrial windows, soft morning light on wood and steel",
        "place": "a lofty SoMa coffee roastery with a roaster turning in the background",
        "hero": "a coffee in a white ceramic cup",
        "music": "mellow lo-fi beat with muted keys",
        "sfx": "roaster rumble, a cup set down on a wooden bar",
        "next": "the story moves forward to a warm payoff: the same person takes the first sip by the window and smiles",
    },
}
NO_TEXT = "No on-screen text, captions, logos, signs or readable words."


def body_for(kind, p, defaults):
    base = {"aspect_ratio": defaults["aspect_ratio"], "resolution": defaults["resolution"], "generate_audio": True}
    sc = SCENE[p.get("brand", "sutro")]
    if kind == "order":
        if p.get("brand") == "sightglass":
            build = f"{p['temp']} {p['milk']} {p['drink']}".replace("none ", "")
            make = f"a barista makes one {build} to order: espresso pouring, milk added, the drink finished in a white ceramic cup"
            line = f"Your {build}. Ready when you are."
        else:
            build = f"{p['bun']} bun, {p['cheese']}, {p['extra']}"
            make = f"a cook at a sizzling flat-top grill builds one double smash burger to order: {build}, each ingredient landing on the stack in a satisfying close-up"
            line = "Your Sutro Stack is ready."
        return {**base, "mode": "t2v", "duration": 10, "prompt": (
            f"{sc['look']}. A 10-second vertical mobile video ad. {NO_TEXT}\n"
            f"SHOT ONE (0-5s): in {sc['place']}, {make}.\n"
            "HARD CUT. SHOT TWO (5-10s): the finished order in slow-motion hero close-up in bright light, then a hand "
            "slides it toward the camera.\n"
            f"AUDIO: Music: {sc['music']}. Sound effects: {sc['sfx']}. Voiceover by a friendly narrator, American "
            f"English. At 1 second the narrator says: \"You picked {build}.\" At 6 seconds: \"{line}\"")}
    if kind == "episode":
        parent = OUT / f"{p['parent']}.mp4"
        n = int(p["episode"])
        prompt = SAGA.get(n) if p["parent"].startswith("sightglass__n_judah") or p.get("saga") == "n_judah" else None
        prompt = prompt or (f"Continue the same shot, same characters and same setting for five more seconds; "
                            f"{sc['next']}. Same music continues and resolves. {NO_TEXT}")
        return {**base, "mode": "v2v", "duration": 5, "start_video": b64(parent), "prompt": prompt}
    if kind == "selfie":
        return {**base, "mode": "t2v", "duration": 10, "reference_images": [b64(p["image"])], "prompt": (
            f"{sc['look']}. A 10-second vertical mobile video ad. {NO_TEXT}\n"
            f"SHOT ONE (0-4s): the person from the reference images, same face and hair, walks into {sc['place']} "
            "and grins at the camera.\n"
            f"HARD CUT. SHOT TWO (4-10s): the same person from the reference images enjoys {sc['hero']}, eyes closed "
            "in delight, then gives a thumbs up.\n"
            f"AUDIO: Music: {sc['music']}. Sound effects: {sc['sfx']}. Voiceover by an energetic narrator, American "
            "English. At 6 seconds the narrator says: \"Looks good on you.\"")}
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

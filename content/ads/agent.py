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

# Idea 6: each episode is a complete 10-second ad that continues the same characters from the last clip
# the viewer saw. The feed stores only the last clip and the episode number.
SAGAS = {  # story key (the ad the viewer started from) -> episode -> (shot1, shot2, shot3, hook line, brand line)
    "sightglass__n_judah_commuter": {
        2: ("The next foggy morning, the same commuter sprints for the streetcar and makes it just as the doors close",
            "Inside the roastery, a barista hands him his usual pour-over the moment he walks in",
            "He raises the cup to the fogged window with a grin; the city wakes up outside",
            "Same fog. This time, he made the train.", "Sightglass. Your usual, on 7th Street."),
        3: ("At the roastery counter, the same commuter notices the stranger next to him ordered the same pour-over",
            "Close-up: two identical ceramic cups slide across the wooden bar side by side",
            "They clink cups and laugh by the window as the fog lifts",
            "Same order. New friend.", "Sightglass. Coffee that finds your people."),
        4: ("Sunny afternoon, the same commuter walks out of the roastery with two cups",
            "Macro shot of fresh coffee beans pouring out of the drum roaster, steam in window light",
            "He hands one cup to his friend on the sidewalk; they walk off into the sunshine",
            "Season finale. The fog finally lifted.", "Sightglass. Roasted right here on 7th Street."),
    },
    "sightglass__soma_founder": {
        2: ("The same founder finishes her pitch to applause and steps out into bright SoMa sunshine, phone buzzing",
            "She reads the message, covers her mouth in disbelief, then walks straight into the roastery",
            "The barista slides her a cup; she lifts it in a quiet solo toast by the tall windows",
            "She pitched. They said yes.", "Sightglass. Where SoMa celebrates."),
        3: ("Monday morning, the same founder walks into the roastery with three new teammates",
            "A row of ceramic cups lined up on the wooden bar as the barista pours each one",
            "The team huddles around a laptop at a long table, laughing, cups in hand",
            "Day one of the new team.", "Sightglass. Fuel for what's next."),
        4: ("Evening, the same founder alone at the roastery window, city lights coming on",
            "Close-up of her hands around a warm cup, steam rising",
            "She smiles, closes the laptop and heads out into the night",
            "Season finale. Still her favorite table.", "Sightglass. Roasted right here on 7th Street."),
    },
    "sightglass__fog_narrator": {
        2: ("The fog rolls back over SoMa rooftops, grumbling, as people below unzip their jackets in the sun",
            "Inside the roastery, a barista pours a pour-over as sunlight floods through tall windows",
            "The fog peeks through the window, defeated, as the woman sips her coffee in the sun",
            "The fog is back. Nobody minds.", "Sightglass. Good in any weather."),
    },
    "sutrostack__soma_lunch_headline": {
        2: ("The same lunch crowd in sunny SoMa, now lined up outside a busy burger counter, laughing at their phones",
            "Sizzling flat-top: a cook smashes two patties and lays melted cheddar on top, slow motion",
            "Friends at an outdoor table raise their burgers in a toast, the Bay Bridge behind them",
            "The headline faded. The craving didn't.", "Sutro Stack. Built the way you like it."),
    },
}
BRAND_LINE = {"sutro": "Sutro Stack. Built the way you like it.", "sightglass": "Sightglass. Roasted right here on 7th Street."}


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
        brand = p.get("brand", "sutro")
        beat = SAGAS.get(p.get("story") or p["parent"], {}).get(n)
        if beat is None:
            beat = (f"Picking up right where the input video ended, the same characters in the same setting move the "
                    f"story forward", f"Product hero close-up: {sc['hero']} in beautiful light",
                    f"The payoff: {sc['next'].split(': ', 1)[-1]}", f"Episode {n}. The story continues.", BRAND_LINE[brand])
        one, two, three, hook, close = beat
        return {**base, "mode": "v2v", "duration": 10, "start_video": b64(parent), "prompt": (
            f"{sc['look']}. Continue the input video as a complete 10-second vertical mobile video ad, episode {n} of "
            f"a series. Keep the same characters, faces, wardrobe and setting. {NO_TEXT}\n"
            f"SHOT ONE (0-3s): {one}.\n"
            f"HARD CUT. SHOT TWO (3-7s): {two}.\n"
            f"HARD CUT. SHOT THREE (7-10s): {three}.\n"
            f"AUDIO: Music: {sc['music']}, building to a warm resolve. Sound effects: {sc['sfx']}. Voiceover by a "
            f"friendly narrator, American English. At 0 seconds the narrator says: \"{hook}\" At 7 seconds the "
            f"narrator says: \"{close}\"")}
    if kind == "selfie":
        # The photo is the exact opening frame (i2v keyframe); FLUX 3 animates the person from there.
        # (reference_images is not accepted on /v1/flux-3-video for t2v or i2v.)
        return {**base, "mode": "i2v", "duration": 10, "keyframes": b64(p["image"]),  # one image: a plain string
                "prompt": (
            f"{sc['look']}. {NO_TEXT}\n"
            "The person in the opening frame keeps smiling at the camera, then the camera pulls back as they turn and "
            f"walk into {sc['place']}. They are handed {sc['hero']}, enjoy it with eyes closed in delight, and give "
            "the camera a thumbs up. Same person, same face, same shirt throughout.\n"
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

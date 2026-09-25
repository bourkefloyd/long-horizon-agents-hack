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

# ---- Create mode: a campaign brief from the feed's multiple-choice screens becomes one full ad per variant ----
CATEGORY = {  # look + setting + hero for brands we have no scene for yet
    "coffee": ("Bright airy look, soft morning window light, warm wood tones", "a bright neighborhood coffee shop", "a latte in a ceramic cup with latte art"),
    "burger": ("Punchy social-feed look, saturated warm colors, crisp commercial food lighting", "a lively burger counter with a sizzling flat-top", "a juicy double smash burger with melted cheese"),
    "bakery": ("Warm golden look, natural light, flaky pastry in macro detail", "a busy neighborhood bakery with trays fresh from the oven", "a flaky golden croissant torn open, steam rising"),
    "ice cream": ("Sun-drenched summer look, saturated colors, playful handheld energy", "a small ice cream shop with a line out the door", "a glossy scoop of ice cream pressed into a cone"),
    "other": ("Clean modern commercial look, soft natural light", "a friendly neighborhood shop", "the product in a clean hero close-up"),
}
AUDIENCE = {
    "soma lunch": ("office workers on a weekday lunch break", "SoMa, with brick warehouses and the Bay Bridge in the distance"),
    "mission brunch": ("friends meeting for weekend brunch", "a sunny Mission District street lined with murals"),
    "n-judah commuters": ("a commuter with a backpack and earbuds", "a foggy Inner Sunset streetcar stop"),
    "students": ("college students with laptops and backpacks", "a busy campus-side street in San Francisco"),
    "wharf visitors": ("visitors taking in the city", "the waterfront near the piers with sea lions and fog"),
}
MOMENT = {"morning rush": "early morning, soft fog lifting", "lunch": "midday, bright sun", "after work": "golden hour, warm low light", "weekend": "a lazy sunny weekend afternoon"}
MUSIC = {"lo-fi chill": "mellow lo-fi beat with muted keys", "upbeat hip hop": "upbeat hip hop beat with snappy hi-hats",
         "indie acoustic": "bright indie acoustic guitar with hand claps", "cinematic swell": "cinematic strings building to a warm swell"}
VOICE = {"warm narrator": "a warm, friendly narrator, American English", "energetic creator": "an energetic social-media creator talking to camera, American English",
         "spanish narrator": "a warm narrator speaking Mexican Spanish", "music only": None}
GOAL_LINE = {"foot traffic": "Come by today.", "online orders": "Order ahead in two taps.", "new item launch": "New on the menu.", "brand love": "Made for San Francisco."}
FORMAT = {  # (shot one, shot two, shot three, hook line); {who} {where} {hero} filled in
    "pov": ("first-person POV walking through {where}, a hand reaching toward the door", "POV close-up: {hero} slides across the counter toward the camera", "POV: the first taste, the city blurring happily in the background", "POV: you found your spot."),
    "trend hook": ("fast social-feed montage in {where}: {who} glance at phones that light up and react with surprise", "abstract news-feed cards with icons and emoji sliding past, no readable words", "smash cut to {hero} in a slow-motion reveal", "San Francisco's feed is buzzing."),
    "day in the life": ("{who} starting their day in {where}", "{who} stepping inside and being handed {hero}", "{who} sharing it with a friend, laughing", "A day in the life, made better."),
    "asmr close-up": ("extreme macro of {hero} being made, every texture visible", "slow-motion detail: steam, drips and crumbs in window light", "a satisfying first bite or sip in close-up", ""),
    "street interview": ("a friendly host with a microphone stops {who} in {where}", "the person tastes {hero} on the spot and their eyes light up", "they give the camera a big thumbs up as the host laughs", "Quick question: what's the best thing on this block?"),
}


def campaign_body(p, defaults):
    """One variant of a Create-mode campaign as a full 10-second FLUX 3 ad."""
    brand_key = p.get("brand_key")
    if brand_key in SCENE:
        sc = SCENE[brand_key]
        look, place, hero = sc["look"], sc["place"], sc["hero"]
    else:
        look, place, hero = CATEGORY[p.get("category", "other")]
    name = p.get("brand_name") or "the shop"
    who, where = AUDIENCE[p["audience"]]
    one, two, three, hook = (x.format(who=who, where=where, hero=hero) for x in FORMAT[p["format"]])
    sc_in = p.get("script")  # written by Claude Opus 5.5 when the request is processed
    if sc_in and "shot1" in sc_in:
        one, two, three, hook = sc_in["shot1"], sc_in["shot2"], sc_in["shot3"], sc_in["hook"]
    voice = VOICE[p["voice"]]
    close = f"{name}. {GOAL_LINE[p['goal']]}"
    if sc_in and sc_in.get("close"):
        close = sc_in["close"]
    if p["voice"] == "spanish narrator":
        hook, close = "", f"{name}. Te esperamos."
    lines = ""
    if voice:
        said = [f'At 0 seconds the narrator says: "{hook}"'] if hook else []
        said.append(f'At 7 seconds the narrator says: "{close}"')
        lines = f" Voiceover by {voice}. " + " ".join(said)
    dur = int(p.get("length", 10))
    head = f"{look}. A {dur}-second vertical mobile video ad for {name}, set in {place}, {MOMENT[p['moment']]}. {NO_TEXT}"
    music = f"AUDIO: Music: {MUSIC[p['music']]}, ending on a short upbeat sting."
    if sc_in and sc_in.get("shots"):  # Opus 5.5 timed shot list: [{"t": [a, b], "shot": ..., "vo": ...}]
        names = ["ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX"]
        shots = [f"{'' if i == 0 else 'HARD CUT. '}SHOT {names[i]} ({x['t'][0]}-{x['t'][1]}s): {x['shot']}." for i, x in enumerate(sc_in["shots"])]
        said = " ".join(f'At {x["t"][0]} seconds the narrator says: "{x["vo"]}"' for x in sc_in["shots"] if x.get("vo"))
        lines = f" Voiceover by {voice}. {said}" if voice and said else ""
        prompt = "\n".join([head, *shots, music + lines])
    else:
        t1, t2 = round(dur * .3), round(dur * .7)
        prompt = (f"{head}\nSHOT ONE (0-{t1}s): {one}.\nHARD CUT. SHOT TWO ({t1}-{t2}s): {two}.\n"
                  f"HARD CUT. SHOT THREE ({t2}-{dur}s): {three}.\n{music}{lines}")
    return {"aspect_ratio": defaults["aspect_ratio"], "resolution": defaults["resolution"], "generate_audio": True,
            "mode": "t2v", "duration": dur, **({"draft": True} if p.get("quality") == "draft" else {}), "prompt": prompt}


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
    if kind == "campaign":
        return campaign_body(p, defaults)
    raise ValueError(kind)


def clean(line, limit=60):
    """Keep a spoken line speakable: no emoji or symbols, bounded length."""
    out = "".join(ch for ch in line if ch.isalnum() or ch in " .,!?'-:&").strip()
    return out[:limit].rsplit(" ", 1)[0] if len(out) > limit else out


def research(p):
    """Nimble: this week's local stories for the audience's area. Opus 5.5 picks a brand-safe one and writes the script."""
    import nimble
    area = {"soma lunch": "SoMa", "mission brunch": "Mission District", "n-judah commuters": "Inner Sunset",
            "students": "San Francisco", "wharf visitors": "Fisherman's Wharf"}[p["audience"]]
    q = p.get("query") or f"San Francisco {area} local news this week"
    res = nimble.search(q, "news", 6, "week")
    return q, [{"title": x.get("title"), "description": x.get("description"), "url": x.get("url")} for x in res.get("results", [])]


def prepare_campaign(p, ledger):
    if p.get("research"):
        r = p["research"]
        ledger["nimble"] = f"news search '{r['query']}': {r['count']} stories" + (f", used '{p['headline']}'" if p.get("headline") else ", none used")
    if p.get("script"):
        ledger["claude"] = p.get("script_by", "Claude Opus 5.5") + " picked the story and wrote the script"


def main(kind, req_id, payload):
    p = json.loads(payload)
    defaults = json.loads((HERE / "scripts.json").read_text())["defaults"]
    key = os.environ.get("BLACK_FOREST") or os.environ.get("BFL_API_KEY")
    if not key:
        sys.exit("Set BLACK_FOREST (or BFL_API_KEY) in the environment.")
    OUT.mkdir(exist_ok=True)
    ledger = {}
    if kind == "selfie":  # Liquid vision checks the upload before anything is sent to BFL
        import liquid
        chk = liquid.check_image(p["image"])
        ledger["liquid"] = [f"LFM2-VL-1.6B photo check: {'passed' if chk['ok'] else 'rejected'} ({chk['description']})"]
        if not chk["ok"]:
            Path(p["image"]).unlink(missing_ok=True)
            (OUT / f"{req_id}.sponsors.json").write_text(json.dumps(ledger))
            sys.exit(f"photo rejected: {chk}")
    if kind == "research":
        q, stories = research(p)
        print(json.dumps({"query": q, "stories": stories}, indent=1, ensure_ascii=False))
        return
    if kind == "campaign":
        prepare_campaign(p, ledger)
    body = body_for(kind, p, defaults)
    mode = {"t2v": "text-to-video", "i2v": "image-to-video", "v2v": "continuation"}[body["mode"]]
    ledger["bfl"] = f"FLUX 3 {mode}, {body['duration']} s {'draft' if body.get('draft') else 'HD'}"
    poll = render.submit(req_id, body, key, OUT)
    if kind == "selfie":
        Path(p["image"]).unlink(missing_ok=True)  # used once, then dropped
    ok = render.wait(req_id, poll, body, key, OUT)
    if ok and (kind == "campaign" or os.environ.get("LIQUID_QA")):
        import liquid
        qa = liquid.check_video(OUT / f"{req_id}.mp4")
        ledger.setdefault("liquid", []).append("LFM2-VL-1.6B frame check: " + ("flagged " + "; ".join(qa["found"]) if qa["flagged"] else "no text or logos"))
    (OUT / f"{req_id}.sponsors.json").write_text(json.dumps(ledger, ensure_ascii=False))
    print(json.dumps(ledger, ensure_ascii=False))
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main(*sys.argv[1:4])

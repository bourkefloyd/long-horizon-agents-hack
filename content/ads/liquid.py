#!/usr/bin/env python3
"""Liquid AI LFM2 in the ad loop, on-device via llama.cpp's llama-server.

    text  : LFM2-1.2B       -> brand-safety check of Nimble headlines, campaign scripts, game agent
    vision: LFM2-VL-1.6B    -> upload check (one adult, face visible, safe), frame QA (text / logos)

Servers start on demand on localhost:8081 (text) and :8082 (vision). Model paths from LFM_DIR,
llama.cpp binaries from LLAMA_BIN.

    python3 content/ads/liquid.py safety  facts.json "Sutro Stack" burger
    python3 content/ads/liquid.py check-image photo.jpg
    python3 content/ads/liquid.py check-video out/clip.mp4
    python3 content/ads/liquid.py play stack 3
"""

import base64
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

LFM_DIR = Path(os.environ.get("LFM_DIR", "/tmp/lfm"))
LLAMA_BIN = Path(os.environ.get("LLAMA_BIN", "/home/user/ggml-org/llama.cpp/build/bin"))
TEXT = {"port": 8081, "args": ["-m", str(LFM_DIR / "LFM2-1.2B-Q4_K_M.gguf")]}
VISION = {"port": 8082, "args": ["-m", str(LFM_DIR / "LFM2-VL-1.6B-Q8_0.gguf"), "--mmproj", str(LFM_DIR / "mmproj-LFM2-VL-1.6B-Q8_0.gguf")]}
TEXT_NAME, VISION_NAME = "Liquid LFM2-1.2B", "Liquid LFM2-VL-1.6B"


def _up(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def ensure(srv):
    if _up(srv["port"]):
        return
    log = open(Path(tempfile.gettempdir()) / f"llama-{srv['port']}.log", "a")
    subprocess.Popen([str(LLAMA_BIN / "llama-server"), *srv["args"], "--port", str(srv["port"]), "-t", "4", "-c", "4096", "--no-webui"],
                     stdout=log, stderr=log, start_new_session=True)
    for _ in range(180):
        if _up(srv["port"]):
            return
        time.sleep(1)
    raise RuntimeError(f"llama-server on {srv['port']} did not start")


def chat(srv, content, schema, max_tokens=300, temperature=0.2):
    """One chat turn, output constrained to `schema`. Returns the parsed JSON."""
    ensure(srv)
    body = {"messages": [{"role": "user", "content": content}], "temperature": temperature, "max_tokens": max_tokens,
            "response_format": {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}}
    req = urllib.request.Request(f"http://127.0.0.1:{srv['port']}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(json.load(r)["choices"][0]["message"]["content"])


def image_part(path):
    mime = "image/png" if str(path).endswith(".png") else "image/jpeg"
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"}}


# ---- text: brand safety + scripts ----

RISKY = ("fire", "blaze", "death", "dead", "dies", "killed", "shooting", "crash", "injur", "crime", "arrest", "police",
         "lawsuit", "sued", "fined", "fraud", "haywire", "wildfire", "earthquake", "flood", "outbreak", "recall", "layoff")


def safety(headlines, brand, category):
    """Which headlines are safe to riff on in a light ad for this brand."""
    # Reason first, verdict second: the small model decides better after it has written why.
    schema = {"type": "object", "properties": {"topic": {"type": "string", "maxLength": 80},
              "risky_topic": {"type": "string", "enum": ["none", "death or injury", "fire or disaster", "crime", "politics",
                                                          "lawsuit", "health scare", "someone's misfortune"]},
              "verdict": {"type": "string", "enum": ["safe", "not safe"]}}, "required": ["topic", "risky_topic", "verdict"]}
    out = []
    for h in headlines:
        r = chat(TEXT, f"A playful {category} ad for {brand} may reference a local headline. First say what the story is about, "
                       "then name the risky topic it touches (or none), then give the verdict: safe only if the risky topic is none.\n"
                       f"Headline: {h}", schema, 120, 0.0)
        # LFM2-1.2B alone flips with phrasing, so a fixed risky-word list must also pass.
        hit = next((w for w in RISKY if w in h.lower()), None)
        lfm_ok = r["verdict"] == "safe" and r["risky_topic"] == "none"
        r = {"brand_safe": lfm_ok and not hit, "lfm_verdict": "safe" if lfm_ok else r["risky_topic"], "keyword": hit,
             "reason": f"{r['topic']}" + (f" · blocked by word '{hit}'" if hit else "") + ("" if lfm_ok else f" · LFM2: {r['risky_topic']}")}
        out.append({"headline": h, **r})
    return out


def script(brief, headline=None):
    """Campaign shots and lines, written by LFM2 from the brief."""
    schema = {"type": "object", "properties": {k: {"type": "string", "maxLength": 220} for k in ("shot1", "shot2", "shot3", "hook", "close")},
              "required": ["shot1", "shot2", "shot3", "hook", "close"]}
    trend = f"Shot 1 should nod to this local story without naming anyone: {headline}\n" if headline else ""
    return chat(TEXT, (
        f"Write a 10-second vertical video ad for {brief['brand_name']}, which sells {brief.get('category', 'food')} in San Francisco.\n"
        f"Goal: {brief['goal']}. Audience: {brief['audience']}. Moment: {brief['moment']}. Format: {brief['format']}.\n{trend}"
        "Each shot is a camera direction: who is on screen, where, and what they do, like "
        "'Office workers on a sunny SoMa sidewalk glance at their phones and laugh'. No slogans in the shots, no on-screen text, no logos.\n"
        "Return shot1 (0-3s), shot2 (3-7s, the product up close), shot3 (7-10s, the payoff), a spoken hook under 8 words, "
        "and a closing line under 8 words that names the brand."), schema, 320, 0.5)


# ---- vision: upload check + frame QA ----

def check_image(path):
    schema = {"type": "object", "properties": {"one_person": {"type": "boolean"}, "face_visible": {"type": "boolean"},
              "adult": {"type": "boolean"}, "safe": {"type": "boolean"}, "description": {"type": "string", "maxLength": 200}},
              "required": ["one_person", "face_visible", "adult", "safe", "description"]}
    r = chat(VISION, [image_part(path), {"type": "text", "text":
        "Check this photo before it is used as the opening frame of a personalized ad. Is there exactly one person? "
        "Is their face clearly visible? Do they appear to be an adult? Is it safe (no nudity, violence, weapons or "
        "offensive gestures)? Describe the photo in one sentence."}], schema, 120, 0.0)
    r["ok"] = all(r[k] for k in ("one_person", "face_visible", "adult", "safe"))
    return r


def frames(mp4, n=3):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = Path(tempfile.mkdtemp())
    for i, t in enumerate([1.5, 5, 8.5][:n]):
        subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(mp4), "-frames:v", "1",
                        "-vf", "scale=512:-1", str(tmp / f"f{i}.jpg")], check=True)
    return sorted(tmp.glob("f*.jpg"))


def check_video(mp4):
    """Frame QA: readable text or brand logos FLUX drew despite the prompt."""
    schema = {"type": "object", "properties": {"readable_text": {"type": "boolean"}, "brand_logo": {"type": "boolean"},
              "what": {"type": "string", "maxLength": 120}}, "required": ["readable_text", "brand_logo", "what"]}
    found = []
    for f in frames(mp4):
        r = chat(VISION, [image_part(f), {"type": "text", "text":
            "Does this video frame show any readable text (signs, captions, addresses) or a recognizable brand logo? "
            "Answer in JSON; in 'what', name the text or logo, or say none."}], schema, 160, 0.0)
        if r["readable_text"] or r["brand_logo"]:
            found.append(r["what"])
    return {"flagged": bool(found), "found": found}


# ---- the Liquid agent plays the feed's games (same rules and scoring as feed.html) ----

def play_stack(width=390):
    W, LW = width, width * 0.55
    lo, hi, center = 0.0, W - LW, (W - LW) / 2
    schema = {"type": "object", "properties": {"wait_frames": {"type": "integer", "minimum": 0, "maximum": 120}}, "required": ["wait_frames"]}
    x, d, speed, total, combo, moves = 0.0, 1, 0.010, 0, 0, []
    for layer in range(5):
        step = W * speed
        r = chat(TEXT, f"You play a stacking game. A bar moves {step:.2f} px per frame and bounces between x={lo:.0f} and x={hi:.0f}. "
                       f"It is now at x={x:.1f} moving {'right' if d > 0 else 'left'}. You score best if you drop it when x is "
                       f"{center:.1f}. How many frames should you wait before dropping? Answer JSON with wait_frames.", schema, 20, 0.2)
        for _ in range(r["wait_frames"]):
            x += d * step
            if x < lo or x > hi:
                d *= -1
        off = (x - center) / LW
        p = max(0, round(100 - abs(off) * 400))
        if abs(off) < 0.03:
            combo += 1
            p += 10 * combo
        else:
            combo = 0
        total += p
        moves.append({"wait": r["wait_frames"], "points": p})
        speed += 0.0025
        x, d = 0.0, 1
    return total, moves


def play_pour():
    targets = [t + (random.random() - 0.5) * 0.08 for t in (0.34, 0.68, 0.9)]
    schema = {"type": "object", "properties": {"hold_frames": {"type": "integer", "minimum": 0, "maximum": 400}}, "required": ["hold_frames"]}
    level, total, combo, moves = 0.0, 0, 0, []
    for i, target in enumerate(targets):
        rate = 0.0045 + i * 0.0012
        r = chat(TEXT, f"You play a pouring game. The cup is filled to {level:.3f}. Holding the button raises it by {rate:.4f} "
                       f"per frame. The line is at {target:.3f}. How many frames should you hold to stop exactly at the line? "
                       "Answer JSON with hold_frames.", schema, 20, 0.2)
        level = min(1.02, level + r["hold_frames"] * rate)
        miss = level - target
        p = 0 if miss > 0.05 else max(0, round(100 - abs(miss) * 600))
        if abs(miss) < 0.015:
            combo += 1
            p += 10 * combo
        else:
            combo = 0
        total += p
        moves.append({"hold": r["hold_frames"], "points": p})
        level = min(level, target + 0.05)
    return total, moves


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:]
    if cmd == "safety":
        facts = json.loads(Path(rest[0]).read_text())
        print(json.dumps(safety([f["fact"] for f in facts], rest[1], rest[2]), indent=1, ensure_ascii=False))
    elif cmd == "script":
        print(json.dumps(script(json.loads(rest[0]), rest[1] if len(rest) > 1 else None), indent=1, ensure_ascii=False))
    elif cmd == "check-image":
        print(json.dumps(check_image(rest[0]), indent=1))
    elif cmd == "check-video":
        print(json.dumps(check_video(rest[0]), indent=1))
    elif cmd == "play":
        game, n = rest[0], int(rest[1]) if len(rest) > 1 else 1
        for _ in range(n):
            score, moves = (play_stack() if game == "stack" else play_pour())
            print(json.dumps({"agent": TEXT_NAME, "game": game, "score": score, "moves": moves}))

#!/usr/bin/env python3
"""Burn a variant's on-screen text into its rendered clip with ffmpeg.

FLUX 3 garbles text it draws itself (it printed "770 7th St." for 270), so the ad's words are
drawn with Pillow and overlaid with ffmpeg (the static ffmpeg build has no drawtext): each
shot's "text" over that shot, plus a small chip in shot one showing the personalization data the ad used (location, time, weather).

    pip install imageio-ffmpeg Pillow   # static ffmpeg if none on PATH; Pillow draws the text
    python3 content/ads/caption.py sutrostack__soma_lunch_headline
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def chip(persona):
    """Short context line from the persona's data rows, e.g. 'SoMa · Lunch · 68°F mostly sunny'."""
    rows = {r["kind"]: r["fact"] for r in persona.get("data", [])}
    parts = []
    if "location" in rows:
        parts.append(rows["location"].replace("viewer is in ", ""))
    if "time" in rows:
        parts.append("Lunch" if "lunch" in rows["time"] else rows["time"])
    if "weather" in rows:
        w = rows["weather"].split(",")
        parts.append(f"{w[1].strip().split(' ')[0]} {w[0].strip()}" if len(w) > 1 else w[0])
    return " · ".join(parts)


def size(src):
    """Video width and height, parsed from ffmpeg's stream line."""
    err = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(src)], capture_output=True, text=True).stderr
    w, h = re.search(r"Video:.*?, (\d{3,5})x(\d{3,5})", err).groups()
    return int(w), int(h)


def cuts(src):
    """Scene-cut times ffmpeg's scdet filter finds in the clip."""
    err = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(src), "-vf", "scdet=threshold=10", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return [float(t) for t in re.findall(r"lavfi.scd.time: ([0-9.]+)", err)]


def card(path, w, h, text, fontsize, y, box=False, x=None):
    """Transparent full-frame PNG with one line of text (wrapped if wide)."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, fontsize)
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if d.textlength(trial, font=font) > w * 0.86 and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=font)
        tx = (w - tw) / 2 if x is None else x
        ty = y + i * fontsize * 1.2
        if box:
            pad = fontsize * 0.5
            d.rounded_rectangle([tx - pad, ty - pad, tx + tw + pad, ty + fontsize + pad], radius=pad, fill=(0, 0, 0, 115))
            d.text((tx, ty), line, font=font, fill="white")
        else:
            d.text((tx, ty), line, font=font, fill="white", stroke_width=max(2, fontsize // 12), stroke_fill=(0, 0, 0, 220))
    img.save(path)


def main(variant_id):
    data = json.loads((HERE / "scripts.json").read_text())
    v = next(x for x in data["variants"] if x["id"] == variant_id)
    persona = data["personas"][v["persona"]]
    src = HERE / "out" / f"{variant_id}.mp4"
    dst = HERE / "out" / f"{variant_id}.captioned.mp4"
    tmp = Path(tempfile.mkdtemp())
    w, h = size(src)

    print("detected cuts (s):", ", ".join(f"{t:.2f}" for t in cuts(src)))
    # FLUX 3 does not cut exactly on the requested marks; "caption_at" holds each shot's real start
    # time, read off the detected cuts after watching the clip. Without it, the requested marks are used.
    starts = v.get("caption_at") or [s["t"][0] for s in v["shots"]]
    ends = starts[1:] + [v["shots"][-1]["t"][1]]
    overlays = []  # (png, start, end)
    for i, s in enumerate(v["shots"]):
        if s.get("text"):
            png = tmp / f"{i}.png"
            card(png, w, h, s["text"], h // 22, int(h * 0.14))
            overlays.append((png, starts[i], ends[i]))
    line = chip(persona)
    if line:
        png = tmp / "chip.png"
        card(png, w, h, line, h // 50, int(h * 0.05), box=True, x=int(w * 0.07))
        overlays.append((png, starts[0], ends[0]))

    inputs, chain, last = ["-i", str(src)], [], "0:v"
    for n, (png, a, b) in enumerate(overlays, start=1):
        inputs += ["-i", str(png)]
        out = f"v{n}"
        chain.append(f"[{last}][{n}:v]overlay=0:0:enable='between(t,{a},{b})'[{out}]")
        last = out
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(chain),
           "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264", "-crf", "20", "-preset", "fast",
           "-pix_fmt", "yuv420p", "-c:a", "copy", str(dst)]
    subprocess.run(cmd, check=True)
    print(f"saved {dst}")

if __name__ == "__main__":
    main(sys.argv[1])

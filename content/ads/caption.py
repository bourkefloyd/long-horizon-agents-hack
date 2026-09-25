#!/usr/bin/env python3
"""Burn a variant's on-screen text into its rendered clip with ffmpeg.

FLUX 3 garbles text it draws itself (it printed "770 7th St." for 270), so the ad's words are
added here instead: each shot's "text" at its time range, plus a small chip in shot one showing
the personalization data the ad used (location, time, weather).

    pip install imageio-ffmpeg   # static ffmpeg, if ffmpeg is not on PATH
    python3 content/ads/caption.py bigmac__soma_lunch_headline
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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


def main(variant_id):
    data = json.loads((HERE / "scripts.json").read_text())
    v = next(x for x in data["variants"] if x["id"] == variant_id)
    persona = data["personas"][v["persona"]]
    src = HERE / "out" / f"{variant_id}.mp4"
    dst = HERE / "out" / f"{variant_id}.captioned.mp4"
    tmp = Path(tempfile.mkdtemp())

    def textfile(i, s):  # textfile= avoids ffmpeg escaping of quotes, colons and commas
        f = tmp / f"{i}.txt"
        f.write_text(s)
        return str(f)

    filters = []
    for i, s in enumerate(v["shots"]):
        if not s.get("text"):
            continue
        a, b = s["t"]
        filters.append(
            f"drawtext=fontfile={FONT}:textfile={textfile(i, s['text'])}:fontsize=h/24:fontcolor=white"
            f":borderw=4:bordercolor=black@0.85:x=(w-text_w)/2:y=h*0.16:enable='between(t,{a},{b})'"
        )
    line = chip(persona)
    if line:
        a, b = v["shots"][0]["t"]
        filters.append(
            f"drawtext=fontfile={FONT}:textfile={textfile('chip', line)}:fontsize=h/48:fontcolor=white"
            f":box=1:boxcolor=black@0.45:boxborderw=12:x=w*0.05:y=h*0.05:enable='between(t,{a},{b})'"
        )
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
           "-vf", ",".join(filters), "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-c:a", "copy", str(dst)]
    subprocess.run(cmd, check=True)
    print(f"saved {dst}")


if __name__ == "__main__":
    main(sys.argv[1])

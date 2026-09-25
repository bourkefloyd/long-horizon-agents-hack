"""Fog feed API on Lambda, served under /api/* through CloudFront.

State lives as small JSON files in the feed's S3 bucket (data/state.json, data/requests.json) and
rendered clips land in media/. Renders are FLUX 3 calls built by agent.body_for, the same prompts
the claude.ai feed uses. The page polls GET /api/requests; each poll advances pending renders.

    GET  /api/state           -> kept state (orders, saga, best scores, taps, dropped)
    POST /api/state           -> replace kept state
    GET  /api/requests        -> render requests; polls BFL for pending ones
    POST /api/request         -> {kind, payload, title}; payload.image_b64 for a selfie
"""

import base64
import json
import os
import time
import uuid
from pathlib import Path

import boto3

import agent
import render

S3 = boto3.client("s3")
BUCKET = os.environ["BUCKET"]
KEY = os.environ["BLACK_FOREST"]
CAP = int(os.environ.get("RENDER_CAP", "25"))
TMP = Path("/tmp")
agent.OUT = TMP


def get_json(key, default):
    try:
        return json.loads(S3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
    except S3.exceptions.NoSuchKey:
        return default


def put_json(key, value):
    S3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(value).encode(), ContentType="application/json",
                  CacheControl="no-store")


def reply(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json", "cache-control": "no-store"},
            "body": json.dumps(body)}


def body_json(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw)
    return json.loads(raw)


def create(req_in):
    reqs = get_json("data/requests.json", [])
    if sum(r["status"] not in ("failed", "moderated") for r in reqs) >= CAP:
        return reply(429, {"error": "render_cap", "message": f"This demo is capped at {CAP} renders."})
    kind, p = req_in["kind"], dict(req_in.get("payload") or {})
    if kind not in ("order", "episode", "selfie"):
        return reply(400, {"error": "bad_kind"})
    rid = "r" + uuid.uuid4().hex[:12]
    if kind == "episode":
        S3.download_file(BUCKET, f"media/{p['parent']}.mp4", str(TMP / f"{p['parent']}.mp4"))
    if kind == "selfie":
        img = TMP / f"{rid}.jpg"
        img.write_bytes(base64.b64decode(p.pop("image_b64")))  # never stored; deleted below
        p["image"] = str(img)
    defaults = json.loads((Path(__file__).parent / "scripts.json").read_text())["defaults"]
    body = agent.body_for(kind, p, defaults)
    p.pop("image", None)
    try:
        job = render.call(render.API, KEY, body)
        status, reason = "rendering", None
    except Exception as e:  # BFL rejected the request outright
        job, status, reason = {}, "failed", str(e)[:200]
    finally:
        for f in TMP.glob(f"{rid}.*"):
            f.unlink(missing_ok=True)
    r = {"id": rid, "kind": kind, "payload": p, "title": req_in.get("title") or kind, "status": status,
         "reason": reason, "polling_url": job.get("polling_url"), "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    reqs.append(r)
    put_json("data/requests.json", reqs)
    return reply(200, r)


def advance():
    """Poll BFL once for each rendering request; store finished clips in media/."""
    reqs = get_json("data/requests.json", [])
    changed = False
    for r in reqs:
        if r["status"] != "rendering" or not r.get("polling_url"):
            continue
        try:
            res = render.call(r["polling_url"], KEY)
        except Exception:
            continue
        st = res.get("status")
        if st == "Ready":
            url = render.find_url(res.get("result"))
            dest = TMP / f"{r['id']}.mp4"
            render.urllib.request.urlretrieve(url, dest)
            S3.upload_file(str(dest), BUCKET, f"media/{r['id']}.mp4", ExtraArgs={"ContentType": "video/mp4"})
            dest.unlink(missing_ok=True)
            r.update(status="ready", file=f"{r['id']}.mp4", done_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            if r["kind"] == "episode":
                state = get_json("data/state.json", {})
                prev = state.get("saga")
                state["saga"] = {"clip": r["id"], "n": r["payload"]["episode"]}
                if prev:
                    state["dropped"] = (state.get("dropped", []) + [f"episode {prev['n']} clip {prev['clip']}"])[-8:]
                put_json("data/state.json", state)
            changed = True
        elif st in ("Request Moderated", "Content Moderated", "Error"):
            r.update(status="moderated" if "Moderated" in st else "failed", reason=str(res.get("details"))[:200])
            changed = True
    if changed:
        put_json("data/requests.json", reqs)
    return [{k: v for k, v in r.items() if k != "polling_url"} for r in reqs]


def handler(event, context):
    method = event["requestContext"]["http"]["method"]
    path = event.get("rawPath", "")
    if path.endswith("/state"):
        if method == "POST":
            put_json("data/state.json", body_json(event))
            return reply(200, {"ok": True})
        return reply(200, get_json("data/state.json", {}))
    if path.endswith("/requests"):
        return reply(200, advance())
    if path.endswith("/request") and method == "POST":
        return create(body_json(event))
    return reply(404, {"error": "not_found"})

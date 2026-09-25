#!/usr/bin/env python3
"""Publish staged ad variants to GCS and merge them into manifest.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from google.api_core.exceptions import NotFound, PreconditionFailed
from google.cloud import storage
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
DEFAULT_STAGING = ROOT / "staging"
SCHEMA_PATH = ROOT / "manifest.schema.json"
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
MANIFEST_CACHE = "public, max-age=60, must-revalidate"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload cdn/staging variants and update the public ad manifest."
    )
    parser.add_argument(
        "--bucket",
        default=os.environ.get("ADS_BUCKET"),
        help="GCS bucket name (or set ADS_BUCKET).",
    )
    parser.add_argument(
        "--staging",
        type=Path,
        default=DEFAULT_STAGING,
        help="Folder containing <campaign>/<variant>/meta.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the merged manifest without uploading.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_id(value: str, label: str) -> None:
    if not SAFE_ID.fullmatch(value):
        raise ValueError(
            f"{label} {value!r} must use only letters, numbers, dot, dash, or underscore"
        )


def hashed_name(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return f"{path.stem}.{digest}{path.suffix.lower()}"


def public_url(bucket_name: str, object_name: str) -> str:
    return (
        f"https://storage.googleapis.com/{bucket_name}/"
        f"{quote(object_name, safe='/')}"
    )


def load_remote_manifest(
    bucket: storage.Bucket,
) -> tuple[dict[str, Any], int]:
    blob = bucket.blob("manifest.json")
    try:
        raw = blob.download_as_text()
        blob.reload()
        return json.loads(raw), int(blob.generation or 0)
    except NotFound:
        return {"version": 1, "updated_at": datetime.now(timezone.utc).isoformat(), "ads": []}, 0
    except json.JSONDecodeError as exc:
        raise ValueError("The current bucket manifest.json is not valid JSON") from exc


def staged_ads(
    staging: Path, bucket_name: str
) -> tuple[list[dict[str, Any]], list[tuple[Path, str]]]:
    if not staging.is_dir():
        raise ValueError(f"Staging folder does not exist: {staging}")

    ads: list[dict[str, Any]] = []
    uploads: list[tuple[Path, str]] = []
    meta_paths = sorted(staging.glob("*/*/meta.json"))
    if not meta_paths:
        raise ValueError(f"No <campaign>/<variant>/meta.json files found under {staging}")

    for meta_path in meta_paths:
        variant_dir = meta_path.parent
        campaign_id = variant_dir.parent.name
        variant_id = variant_dir.name
        validate_id(campaign_id, "campaign_id")
        validate_id(variant_id, "variant_id")

        meta = load_json(meta_path)
        for field, inferred in (
            ("campaign_id", campaign_id),
            ("variant_id", variant_id),
        ):
            supplied = meta.pop(field, inferred)
            if supplied != inferred:
                raise ValueError(
                    f"{meta_path}: {field} must match its directory name {inferred!r}"
                )

        media_file = meta.pop("media_file", None)
        poster_file = meta.pop("poster_file", None)
        script_file = meta.pop("script_file", None)
        if not isinstance(media_file, str) or not media_file:
            raise ValueError(f"{meta_path}: media_file is required")

        files = {
            path.name: path
            for path in variant_dir.iterdir()
            if path.is_file() and path.name != "meta.json"
        }
        if media_file not in files:
            raise ValueError(f"{meta_path}: media_file {media_file!r} does not exist")
        if poster_file is not None and poster_file not in files:
            raise ValueError(f"{meta_path}: poster_file {poster_file!r} does not exist")
        if script_file is not None:
            if script_file not in files:
                raise ValueError(f"{meta_path}: script_file {script_file!r} does not exist")
            meta["script"] = files[script_file].read_text(encoding="utf-8").strip()

        object_names: dict[str, str] = {}
        for filename, path in files.items():
            object_name = (
                f"ads/{campaign_id}/{variant_id}/{hashed_name(path)}"
            )
            object_names[filename] = object_name
            uploads.append((path, object_name))

        ad = {
            **meta,
            "campaign_id": campaign_id,
            "variant_id": variant_id,
            "media_url": public_url(bucket_name, object_names[media_file]),
        }
        if poster_file is not None:
            ad["poster_url"] = public_url(bucket_name, object_names[poster_file])
        ads.append(ad)

    ids = [ad.get("id") for ad in ads]
    duplicates = sorted({ad_id for ad_id in ids if ids.count(ad_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate staged ad ids: {', '.join(map(str, duplicates))}")
    return ads, uploads


def validate_manifest(manifest: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda error: list(error.path))
    if errors:
        messages = [
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        ]
        raise ValueError("Manifest schema validation failed:\n- " + "\n- ".join(messages))


def merge_manifest(
    current: dict[str, Any], new_ads: list[dict[str, Any]]
) -> dict[str, Any]:
    existing = current.get("ads", [])
    if not isinstance(existing, list):
        raise ValueError("The current manifest ads field must be an array")
    merged = {
        str(ad.get("id")): ad
        for ad in existing
        if isinstance(ad, dict) and ad.get("id")
    }
    merged.update({str(ad["id"]): ad for ad in new_ads})
    return {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ads": [merged[ad_id] for ad_id in sorted(merged)],
    }


def upload_file(bucket: storage.Bucket, path: Path, object_name: str) -> None:
    blob = bucket.blob(object_name)
    blob.cache_control = IMMUTABLE_CACHE
    content_type, _ = mimetypes.guess_type(path.name)
    blob.upload_from_filename(path, content_type=content_type or "application/octet-stream")
    print(f"uploaded gs://{bucket.name}/{object_name}")


def main() -> int:
    args = parse_args()
    if not args.bucket:
        raise SystemExit("--bucket or ADS_BUCKET is required")

    client = storage.Client()
    bucket = client.bucket(args.bucket)
    current, generation = load_remote_manifest(bucket)
    ads, uploads = staged_ads(args.staging.resolve(), args.bucket)
    manifest = merge_manifest(current, ads)
    validate_manifest(manifest)

    if args.dry_run:
        print(json.dumps(manifest, indent=2))
        return 0

    for path, object_name in uploads:
        upload_file(bucket, path, object_name)

    schema_blob = bucket.blob("manifest.schema.json")
    schema_blob.cache_control = "public, max-age=300"
    schema_blob.upload_from_filename(SCHEMA_PATH, content_type="application/schema+json")

    manifest_blob = bucket.blob("manifest.json")
    manifest_blob.cache_control = MANIFEST_CACHE
    try:
        manifest_blob.upload_from_string(
            json.dumps(manifest, indent=2) + "\n",
            content_type="application/json",
            if_generation_match=generation,
        )
    except PreconditionFailed as exc:
        raise RuntimeError(
            "manifest.json changed during publish; rerun to merge with the latest version"
        ) from exc

    print(f"published {len(ads)} ads to {public_url(args.bucket, 'manifest.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

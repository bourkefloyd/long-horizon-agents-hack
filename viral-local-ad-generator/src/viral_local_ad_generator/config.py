from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    nimble_api_key: str
    bfl_api_key: str
    nimble_base_url: str
    bfl_base_url: str
    tinybird_token: str
    tinybird_base_url: str
    tinybird_datasource: str


def load_settings() -> Settings:
    load_dotenv_file(Path(".env"))
    return Settings(
        nimble_api_key=os.getenv("NIMBLE_API_KEY", ""),
        bfl_api_key=os.getenv("BFL_API_KEY", ""),
        nimble_base_url=os.getenv("NIMBLE_BASE_URL", "https://sdk.nimbleway.com").rstrip("/"),
        bfl_base_url=os.getenv("BFL_BASE_URL", "https://api.bfl.ai").rstrip("/"),
        tinybird_token=os.getenv("TINYBIRD_TOKEN", ""),
        tinybird_base_url=os.getenv("TINYBIRD_BASE_URL", "https://api.europe-west2.gcp.tinybird.co").rstrip("/"),
        tinybird_datasource=os.getenv("TINYBIRD_DATASOURCE", "events"),
    )


def load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)

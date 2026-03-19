"""Internal resolver — fetches secrets from the SmartBe control plane."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Optional

_CONFIG_PATH = os.environ.get(
    "SMARTBE_CONFIG_PATH", "/opt/openclaw/.openclaw/.control-plane-secrets.env"
)

_cache: dict[str, str] = {}
_config: Optional[dict[str, str]] = None


def _load_config() -> dict[str, str]:
    global _config
    if _config is not None:
        return _config

    path = Path(_CONFIG_PATH)
    if not path.is_file():
        _config = {}
        return _config

    cfg: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        eq = line.find("=")
        if eq > 0:
            cfg[line[:eq].strip()] = line[eq + 1 :].strip().strip("'\"")

    _config = cfg
    return _config


def _resolve_from_control_plane(key: str) -> Optional[str]:
    cfg = _load_config()
    base_url = cfg.get("OPENCLAW_CONTROL_PLANE_BASE_URL")
    job_id = cfg.get("OPENCLAW_CONTROL_PLANE_JOB_ID")
    token = cfg.get("OPENCLAW_CONTROL_PLANE_TOKEN")

    if not all([base_url, job_id, token]):
        return None

    url = f"{base_url}/api/claw/{job_id}/runtime-secrets/resolve"
    data = json.dumps({"protocolVersion": 1, "ids": [key]}).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-OpenClaw-Callback-Secret": token,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            value = body.get("values", {}).get(key)
            if isinstance(value, str) and value:
                return value
    except Exception:
        pass

    return None


def secret(key: str) -> str:
    """Resolve a secret by key name.

    Resolution order:
    1. In-memory cache
    2. Control plane API
    3. Environment variable fallback

    Raises KeyError if the secret cannot be found.
    """
    if key in _cache:
        return _cache[key]

    # Try control plane
    value = _resolve_from_control_plane(key)
    if value is not None:
        _cache[key] = value
        return value

    # Fallback to environment variable
    env_value = os.environ.get(key)
    if env_value:
        _cache[key] = env_value
        return env_value

    raise KeyError(f"Secret '{key}' not found in control plane or environment")


def clear_cache() -> None:
    """Clear the in-memory secret cache."""
    _cache.clear()

"""Shared helpers for reading configuration from .env files."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str = ".env") -> None:
    """Simple .env loader to avoid external dependencies."""

    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


__all__ = ["load_env_file", "get_required_env"]

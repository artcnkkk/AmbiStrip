"""App data directory on this machine (`%LOCALAPPDATA%/ledsetup` on Windows)."""

from __future__ import annotations

import os
from pathlib import Path


def default_app_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if root:
        return Path(root) / "ledsetup"
    return Path.home() / ".ledsetup"

"""Root conftest: loads .env.test before any module imports."""
from __future__ import annotations

import os
from pathlib import Path

_env_test = Path(__file__).resolve().parent / ".env.test"
if _env_test.exists():
    for line in _env_test.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

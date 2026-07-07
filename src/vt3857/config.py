from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "settings.py"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    path = Path(path)
    if path.suffix != ".py":
        raise ValueError("Config must be a Python settings file, for example config/settings.py")
    ns = runpy.run_path(str(path))
    data = {
        "mvt": ns.get("MVT"),
        "modes": ns.get("MODES"),
        "layers": ns.get("LAYERS"),
        "schema": ns.get("SCHEMA"),
    }
    if not isinstance(data, dict):
        raise ValueError(f"Config {path} must contain a settings mapping")
    missing = [key for key, value in data.items() if value is None]
    if missing:
        raise ValueError(f"Config {path} is missing: {', '.join(missing)}")
    return data

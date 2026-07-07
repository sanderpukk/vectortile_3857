from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def viewer_config(config: dict[str, Any]) -> dict[str, Any]:
    modes = config["modes"]
    mvt = config["mvt"]
    layers_config = config["layers"]

    # Martin tile endpoints (proxied by nginx under /tiles/): no .pbf suffix.
    sources = {
        name: f"/tiles/{mode['output']}/{{z}}/{{x}}/{{y}}"
        for name, mode in modes.items()
    }
    default_source = "estonia" if "estonia" in sources else next(iter(sources))
    bounds = modes[default_source].get("bounds")
    if bounds:
        center = [round((bounds[0] + bounds[2]) / 2, 4), round((bounds[1] + bounds[3]) / 2, 4)]
    else:
        center = [24.9, 58.65]

    # Unique tile layer names in settings order, for the inspector legend.
    layer_names: list[str] = []
    for spec in layers_config.values():
        if spec["target_name"] not in layer_names:
            layer_names.append(spec["target_name"])

    return {
        "projection": "EPSG:3857",
        "minzoom": mvt["minzoom"],
        "maxzoom": mvt["maxzoom"],
        "bounds": bounds,
        "center": center,
        "defaultSource": default_source,
        "sources": sources,
        "layers": layer_names,
        "attribution": config["schema"]["attribution"],
    }


def viewer_config_js(config: dict[str, Any]) -> str:
    data = json.dumps(viewer_config(config))
    return "window.VT_PIPELINE_CONFIG = " + data + ";\n"


def write_viewer_config_js(config: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(viewer_config_js(config), encoding="utf-8")

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .preprocess import TARGET_SRS


DEFAULT_BASEMAP = "/data/basemap.gpkg"


def build_schema(config: dict[str, Any], basemap_path: str | Path = DEFAULT_BASEMAP) -> dict[str, Any]:
    """Convert the Python settings into a Planetiler custommap schema.

    Users edit config/settings.py; this generated schema is only a
    compatibility bridge, like the GDAL MVT CONF JSON in the 3301 pipeline.
    """
    meta = config["schema"]
    layers_config = config["layers"]

    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for source_layer, spec in layers_config.items():
        grouped.setdefault(spec["target_name"], []).append((source_layer, spec))

    layers = []
    for target_name, entries in grouped.items():
        features = []
        for source_layer, spec in entries:
            feature: dict[str, Any] = {
                "source": "basemap",
                "geometry": spec["geometry"],
                # basemap.gpkg tables surface as source layers in Planetiler.
                "include_when": "${ feature.source_layer == '" + source_layer + "' }",
                "min_zoom": spec["minzoom"],
                "max_zoom": spec["maxzoom"],
            }
            minzoom_column = spec.get("feature_minzoom")
            if minzoom_column:
                # Per-feature minimum zoom from the preprocessed column
                # (e.g. place labels). Planetiler drops the feature from
                # lower-zoom tiles; the column stays as a tile attribute too.
                feature["min_zoom"] = "${ int(feature.tags." + minzoom_column + ") }"
            attributes = [{"key": name, "tag_value": name} for name in spec.get("attributes", [])]
            if attributes:
                feature["attributes"] = attributes
            features.append(feature)
        layers.append({"id": target_name, "features": features})

    return {
        "schema_name": meta["name"],
        "schema_description": meta["description"],
        "attribution": meta["attribution"],
        "sources": {
            "basemap": {
                "type": "geopackage",
                "local_path": str(basemap_path),
                # Planetiler's GeoTools reader cannot auto-detect the CRS of
                # GDAL-written GeoPackages and silently reads zero features
                # without this explicit hint.
                "projection": TARGET_SRS,
            },
        },
        "layers": layers,
    }


def schema_yaml(config: dict[str, Any], basemap_path: str | Path = DEFAULT_BASEMAP) -> str:
    # JSON is valid YAML, so emitting JSON keeps this dependency-free while
    # staying loadable by Planetiler's YAML parser.
    return json.dumps(build_schema(config, basemap_path), indent=2, ensure_ascii=False) + "\n"


def write_schema(config: dict[str, Any], path: str | Path, basemap_path: str | Path = DEFAULT_BASEMAP) -> None:
    Path(path).write_text(schema_yaml(config, basemap_path), encoding="utf-8")

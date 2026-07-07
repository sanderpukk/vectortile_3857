from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .gdal import ogr2ogr, require_file
from .layers import LAYERS


# Planetiler works in Web Mercator, so the classification SQL (which runs
# against the EPSG:3301 sources) is reprojected to EPSG:3857 on write.
TARGET_SRS = "EPSG:3857"


def preprocess(sources_dir: str | Path, output: str | Path) -> None:
    sources = Path(sources_dir)
    output = Path(output)
    etak = require_file(sources / "etak.gpkg", "run `python -m vt3857 prepare` first")
    ehak = require_file(sources / "ehak.gpkg", "run `python -m vt3857 prepare` first")

    if output.exists():
        print(f"{output} already exists, skipping. Delete it to rebuild.")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    # ADS is optional (only feeds the secondary place-detail label layer). If it
    # was skipped or failed to download, build without it rather than aborting.
    source_files = {"etak": etak, "ehak": ehak}
    ads = sources / "ads.gpkg"
    if ads.exists():
        source_files["ads"] = ads
    else:
        print(f"ADS source {ads} not found; skipping ADS-based layers.")

    with tempfile.TemporaryDirectory(prefix="basemap-") as tmp:
        tmp_out = Path(tmp) / "basemap.gpkg"
        for layer in LAYERS:
            if layer.source not in source_files:
                print(f"Skipping layer {layer.name}: source {layer.source!r} unavailable.")
                continue
            print(f"Creating layer {layer.name}: {layer.comment}")
            ogr2ogr(
                tmp_out,
                source_files[layer.source],
                layer.sql,
                layer.name,
                update=tmp_out.exists(),
                nlt=layer.nlt,
                t_srs=TARGET_SRS,
            )
        shutil.move(str(tmp_out), output)
    print(f"basemap.gpkg ready: {output}")

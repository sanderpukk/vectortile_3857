from __future__ import annotations

import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .gdal import run


ETAK_URL = "https://geoportaal.maaamet.ee/index.php?lang_id=2&plugin_act=otsing&andmetyyp=ETAK&dl=1&f=ETAK_EESTI_GPKG.zip&page_id=618"
EHAK_BASE_URL = "https://s3.pilw.io/rp-kemit-kataster/EHAK"
ADS_WFS_URL = "WFS:https://aks.geoportaal.ee/aks-ogc"
# Address System (ADS) layers: unofficial city districts, asum neighbourhoods
# and small places, converted to label points. (Housenumbers come from the
# ETAK building layer E_401_hoone_ka.ads_lahiaadress, not from ADS.)
ADS_LAYERS = ["aks:ads_linnaosa", "aks:ads_asum", "aks:ads_vk"]


def prepare(sources_dir: str | Path) -> None:
    sources = Path(sources_dir)
    sources.mkdir(parents=True, exist_ok=True)
    _prepare_etak(sources)
    _prepare_ehak(sources)

    # ADS is an optional source: it only provides the secondary place-label
    # layer (districts/neighbourhoods/small places). Set SKIP_ADS=1 to skip it
    # entirely, and any ADS fetch failure (e.g. the AKS WFS being down) is
    # downgraded to a warning so the rest of the build can proceed without it.
    if _env_flag("SKIP_ADS"):
        print("SKIP_ADS set; skipping ADS (place-detail labels will be omitted).")
        return
    try:
        _prepare_ads(sources)
    except Exception as exc:  # noqa: BLE001 - ADS is non-essential; keep building
        print(f"WARNING: ADS preparation failed ({exc}); continuing without ADS. "
              "Place-detail labels will be omitted. Set SKIP_ADS=1 to silence this.")


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _prepare_etak(sources: Path) -> None:
    output = sources / "etak.gpkg"
    if output.exists():
        print(f"ETAK already exists, skipping: {output}")
        return

    with tempfile.TemporaryDirectory(prefix="etak-") as tmp:
        work = Path(tmp)
        archive = work / "ETAK_EESTI_GPKG.zip"
        _download(ETAK_URL, archive)
        _extract(archive, work)
        gpkg = _first(work, "*.gpkg")
        shutil.copyfile(gpkg, output)
    print(f"ETAK ready: {output}")


def _prepare_ehak(sources: Path) -> None:
    output = sources / "ehak.gpkg"
    if output.exists():
        print(f"EHAK already exists, skipping: {output}")
        return

    with tempfile.TemporaryDirectory(prefix="ehak-") as tmp:
        work = Path(tmp)
        archives = ["maakond_shp.zip", "omavalitsus_shp.zip", "asustusyksus_shp.zip"]
        for archive_name in archives:
            archive = work / archive_name
            _download(f"{EHAK_BASE_URL}/{archive_name}", archive)
            _extract(archive, work)

        maakond = _first(work, "maakond*.shp")
        omavalitsus = _first(work, "omavalitsus*.shp")
        asustus = _first(work, "asustusyksus*.shp")

        # Sources stay in Estonia's native EPSG:3301 so they remain
        # byte-comparable with the 3301 pipeline. The preprocess step
        # reprojects everything to EPSG:3857 for Planetiler.
        run(["ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:3301", "-nln", "maakond", str(output), str(maakond)])
        run(["ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:3301", "-append", "-nln", "omavalitsus", str(output), str(omavalitsus)])
        run(["ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:3301", "-append", "-nln", "asustusyksus", str(output), str(asustus)])
    print(f"EHAK ready: {output}")


def _prepare_ads(sources: Path) -> None:
    output = sources / "ads.gpkg"
    if output.exists():
        print(f"ADS already exists, skipping: {output}")
        return

    # The WFS serves EPSG:3301 natively; -t_srs just pins it.
    with tempfile.TemporaryDirectory(prefix="ads-") as tmp:
        work = Path(tmp)
        tmp_out = work / "ads.gpkg"
        for typename in ADS_LAYERS:
            layer = typename.split(":")[1]
            print(f"Fetching {typename} from AKS WFS")
            update = ["-update", "-append"] if tmp_out.exists() else []
            wfs_config = [
                "--config", "OGR_WFS_PAGING_ALLOWED", "ON",
                "--config", "OGR_WFS_PAGE_SIZE", "10000",
            ]
            # District/small-place polygons become label points here in Python
            # because preprocessing SQL cannot rely on Spatialite (GDAL builds
            # without it lack ST_Centroid).
            raw = work / f"{layer}.json"
            pts = work / f"{layer}_pts.json"
            run(["ogr2ogr", "-f", "GeoJSON", *wfs_config, str(raw), ADS_WFS_URL, typename])
            _polygons_to_label_points(raw, pts)
            run([
                "ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:3301", *update,
                "-nln", layer, "-nlt", "POINT", str(tmp_out), str(pts),
            ])
        shutil.move(str(tmp_out), output)
    print(f"ADS ready: {output}")


def _polygons_to_label_points(src: Path, dst: Path) -> None:
    import json

    data = json.loads(src.read_text(encoding="utf-8"))
    for feature in data.get("features", []):
        geom = feature.get("geometry")
        if not geom:
            continue
        if geom["type"] == "Polygon":
            rings = [geom["coordinates"]]
        elif geom["type"] == "MultiPolygon":
            rings = geom["coordinates"]
        else:
            continue
        outer = max((poly[0] for poly in rings if poly), key=_ring_area)
        feature["geometry"] = {"type": "Point", "coordinates": list(_ring_centroid(outer))}
    dst.write_text(json.dumps(data), encoding="utf-8")


def _ring_area(ring: list) -> float:
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:])))


def _ring_centroid(ring: list) -> tuple[float, float]:
    area = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(area) < 1e-9:
        return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    return cx / (3 * area), cy / (3 * area)


def _download(url: str, path: Path) -> None:
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, path)
    print(f"Downloaded {path} ({path.stat().st_size} bytes)")


def _extract(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(target)


def _first(root: Path, pattern: str) -> Path:
    matches = sorted(root.rglob(pattern))
    if not matches:
        raise SystemExit(f"Could not find {pattern} under {root}")
    return matches[0]

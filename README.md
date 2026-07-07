# Estonia EPSG:3857 Python + Planetiler pipeline

This folder is the Web Mercator (EPSG:3857) sibling of the EPSG:3301 GDAL
pipeline. Python owns the data download, preprocessing layer mapping,
classifier SQL, and tile settings — the same logic as the 3301 build. GDAL
still does the preprocessing through CLI subprocesses,
[Planetiler](https://github.com/onthegomap/planetiler) builds a single
**PMTiles** archive, and [Martin](https://github.com/maplibre/martin) serves
it over HTTP (the same approach as Lithuania's
[national-basemap](https://github.com/govlt/national-basemap)).

The folder is self-contained (own Docker image, compose project, volumes, and
viewer) so it can be moved to its own repository.

## Layout

| Path | Purpose |
| --- | --- |
| `config/settings.py` | User-editable zoom, mode, and layer mapping settings |
| `src/vt3857/prepare.py` | Downloads ETAK and EHAK sources (identical to the 3301 pipeline) |
| `src/vt3857/layers.py` | OMT-like preprocessing layer definitions and classification SQL |
| `src/vt3857/preprocess.py` | Builds `basemap.gpkg` (reprojected to EPSG:3857) from the raw sources |
| `src/vt3857/schema.py` | Generates the Planetiler custommap schema from the Python settings |
| `src/vt3857/generate.py` | Runs Planetiler PMTiles generation |
| `src/vt3857/viewer.py` | Generates browser viewer config from the same Python settings |
| `viewer/` | OpenLayers inspection viewer served by nginx, reading tiles from Martin |

## Run with Docker Compose

From PowerShell:

```powershell
cd C:\vectortile\python-pipeline\planetiler-3857
docker compose run --rm pipeline
docker compose run --rm package
docker compose up viewer
```

`package` copies the generated PMTiles archive into the final datapackage at
`dist\estonia.pmtiles` (or `dist\tallinn.pmtiles` for the Tallinn prototype)
on the host. This single file is the main product of the pipeline; tiles
inside it are gzip-compressed.

`docker compose up viewer` starts two containers: **Martin** serving the
PMTiles archives on port 3000, and nginx serving the OpenLayers viewer on
port 8081 (proxying `/tiles/…` to Martin). Open:

```text
http://localhost:8081
```

(The viewer uses port 8081 so it can run next to the 3301 viewer on 8080.
Martin is also reachable directly, e.g. `http://localhost:3000/catalog` or
`http://localhost:3000/estonia/{z}/{x}/{y}`.)

By default `pipeline` builds the full Estonia tile set. It runs:

1. `prepare` - download ETAK/EHAK source data (plus optional ADS, see below).
2. `preprocess` - build `/data/basemap.gpkg` in EPSG:3857.
3. `generate` - run Planetiler, creating `/out/estonia.pmtiles`.
4. `viewer-config` - update `viewer/config.js`.

Run `docker compose run --rm package` afterwards to copy the PMTiles
datapackage into `dist\` on the host.

For the faster Tallinn prototype (optional), set `MODE=tallinn`:

```powershell
$env:MODE = "tallinn"
docker compose run --rm pipeline
docker compose up viewer
```

Open the Tallinn prototype tile source explicitly with:

```text
http://localhost:8081/?src=tallinn
```

## Optional ADS source

The ADS layers (unofficial city districts, `asum` neighbourhoods and small
places) come from the AKS WFS at `aks.geoportaal.ee` and feed only the
secondary `place` detail label layer. They are optional, so the build does not
depend on that service being available:

- **Skip explicitly:** set `SKIP_ADS=1` on `prepare` / `data-prep` / `pipeline`
  to skip the ADS download entirely.
- **Automatic fallback:** if ADS is not skipped but the download fails, the
  error is downgraded to a warning and the build continues without it.
- **Effect:** when ADS is absent, `preprocess` skips the ADS-based layer and
  place-detail labels are omitted. Everything else is unaffected.

```powershell
docker compose run --rm -e SKIP_ADS=1 pipeline
```

## Run steps separately

```powershell
cd C:\vectortile\python-pipeline\planetiler-3857
docker compose run --rm data-prep                 # add -e SKIP_ADS=1 to skip ADS
docker compose run --rm preprocess
docker compose run --rm generate
docker compose run --rm package
docker compose run --rm viewer-config
docker compose up viewer
```

The steps above default to full Estonia. Set `$env:MODE = "tallinn"` first for
the Tallinn prototype.

Existing outputs are skipped. To rebuild a step, delete that output from the
volume or use a fresh Compose project/volume, e.g.:

```powershell
docker run --rm -v vt-3857-planetiler_vt_data:/data alpine rm -f /data/basemap.gpkg
docker run --rm -v vt-3857-planetiler_vt_tiles:/out alpine rm -f /out/estonia.pmtiles
```

Note: Martin exits at startup if no `.pmtiles` archive exists yet — run
`generate` (or `pipeline`) before `docker compose up viewer`.

## Outputs

| Output | Location in containers | Description |
| --- | --- | --- |
| Source data | `/data/sources/etak.gpkg`, `/data/sources/ehak.gpkg`, `/data/sources/ads.gpkg` (optional) | Downloaded source GeoPackages, kept in EPSG:3301 like the 3301 pipeline |
| Preprocessed map | `/data/basemap.gpkg` | OMT-like render layers reprojected to EPSG:3857 |
| Full Estonia tiles | `/out/estonia.pmtiles` | Full-country PMTiles archive (default), served by Martin |
| Tallinn tiles | `/out/tallinn.pmtiles` | Optional fast prototype archive |
| Datapackage | `dist\estonia.pmtiles` (default), `dist\tallinn.pmtiles` (host) | The PMTiles archive - the final deliverable |
| Viewer config | `viewer/config.js` | Browser tile source config generated from Python settings |

## Local Python commands inside the image

The compose services call these commands:

```bash
python3 -m vt3857 prepare
python3 -m vt3857 preprocess
python3 -m vt3857 generate --mode estonia
python3 -m vt3857 package --mode estonia
python3 -m vt3857 schema-yaml
python3 -m vt3857 viewer-config --output viewer/config.js
python3 -m vt3857 run-all --mode estonia
python3 -m vt3857 run-all --mode tallinn
```

`schema-yaml` prints the Planetiler custommap schema generated from
`config/settings.py`. You normally edit the Python settings file, not the
generated schema. (The schema is emitted as JSON, which is valid YAML.)

## How this relates to the EPSG:3301 pipeline

- The download step and the classification SQL in `layers.py` are identical;
  only the zoom band names and the per-feature `minzoom` values differ.
- Zoom bands are shifted **+4** zoom levels, because L-EST (EPSG:3301) zoom
  levels are about 4 zooms lower than Web Mercator/OpenMapTiles levels
  (L-EST z9 building detail ≈ OMT z13). Bands are clamped to z0-15; bands that
  started at L-EST z0 keep starting at z0.

  | 3301 layer | 3857 layer |
  | --- | --- |
  | `transportation_z0_4` / `z5_8` / `z9_13` | `transportation_z0_8` / `z9_12` / `z13_15` |
  | `transportation_area_z9_13` | `transportation_area_z13_15` |
  | `transportation_name_z8_13` | `transportation_name_z12_15` |
  | `water_z0_4` / `z5_8` / `z9_13` | `water_z0_8` / `z9_12` / `z13_15` |
  | `waterway_z5_13` | `waterway_z9_15` |
  | `landcover_z0_4` / `z5_8` / `z9_13` | `landcover_z0_8` / `z9_12` / `z13_15` |
  | `landuse_z1_13` / `landuse_detail_z8_13` | `landuse_z5_15` / `landuse_detail_z12_15` |
  | `aeroway_z6_13` | `aeroway_z10_15` |
  | `building_z9_13` | `building_z13_15` |
  | `boundary_z0_13` | `boundary_z0_15` |
  | `place_z0_13` / `place_detail_z8_13` | `place_z0_15` / `place_detail_z12_15` |
  | `housenumber_z10_13` | `housenumber_z14_15` |
  | `park_z5_13` | `park_z9_15` |
  | `poi_z8_13` | `poi_z12_15` |

## Deep zooms (z16-z18+)

Tiles are generated to **z15** (Planetiler's practical maximum; its hard cap
is z16). Deeper views do not need deeper tiles: vector clients such as
OpenLayers and MapLibre *overzoom* — they keep rendering the z15 tiles at
z16-z20 display zooms, and because the tiles are vectors this stays fully
crisp. At the 4096 tile extent a z15 tile carries roughly 0.3 m coordinate
precision, which comfortably covers z18 display (~0.4 m/px at Estonian
latitudes) — the same maximum detail the 3301 pipeline delivers at its z13
(L-EST z13 ≈ WM z17-18). The bundled viewer allows zooming to z20.

Generating physical z16+ tiles would multiply the tile count ~4x per level
while adding no new content, since every layer already shows everything from
z13-z15. If a non-overzooming client ever needs deeper tile URLs, raise
`MVT["maxzoom"]` to 16 in `config/settings.py` (Planetiler refuses anything
higher) and extend the terminal `_z*_15` bands accordingly.

- `preprocess` reprojects `basemap.gpkg` to EPSG:3857 (the classification SQL
  still runs against the EPSG:3301 sources, so centroids and boundaries are
  computed in the native CRS first).
- GDAL's MVT driver is replaced by Planetiler. The Python settings are
  converted to a [custommap schema](https://github.com/onthegomap/planetiler/tree/main/planetiler-custommap)
  at runtime, mirroring how the 3301 pipeline generates the GDAL `CONF` JSON.
- The output is a single **PMTiles** archive instead of a `{z}/{x}/{y}.pbf`
  directory tree, and the datapackage is that file instead of a zip. Martin
  serves the archive over HTTP for the viewer (and any other client).
- Planetiler's defaults match the 3301 tile parameters: 4096 tile extent,
  gzip-compressed tiles, and a tile buffer equivalent to the GDAL `BUFFER=64`
  (Planetiler's default 4/256 == 64/4096). There is no `MAX_SIZE` equivalent;
  Planetiler manages tile size through per-zoom simplification instead.
- Modes select lon/lat `--bounds` instead of an EPSG:3301 `-spat` bbox. The
  Tallinn bounds approximate the 3301 prototype bbox.
- **Intentional difference:** the per-feature `minzoom` column on `place`
  layers is now *enforced* by Planetiler (features are dropped from
  lower-zoom tiles), while the 3301/GDAL build only carried it as an
  attribute for styles to filter on. The column is still present in the tile
  attributes as well.
- The viewer is still OpenLayers, but on the standard Web Mercator grid
  (no custom EPSG:3301 tile grid), reading tiles from Martin through the
  nginx `/tiles/` proxy.

## Planetiler version

The Dockerfile downloads the latest Planetiler release jar at build time. Pin
a specific release with:

```powershell
docker compose build --build-arg PLANETILER_VERSION=v0.9.1 pipeline
```

Java heap can be tuned per run with, e.g.,
`docker compose run --rm -e JAVA_TOOL_OPTIONS="-Xmx4g" generate` — the
defaults are fine for Estonia-sized data.

## Timing and progress

Like the 3301 pipeline, each step logs lightweight UTC timestamps and the
total elapsed time at the end. Planetiler prints its own detailed progress
(read/process/write rates) during `generate`.

## Notes

- Source downloads stay in EPSG:3301, so the raw `etak.gpkg`/`ehak.gpkg` are
  identical to the 3301 pipeline's sources.
- `config/settings.py` is the user-facing config. The Planetiler schema and
  viewer JS are generated from it.
- See `docs/ETAK_TO_OMT_MAPPING.md` for the ETAK → OpenMapTiles classifier
  mapping reference (shared with the 3301 pipeline; zoom levels there are
  L-EST zooms, add +4 for this build).

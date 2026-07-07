# ETAK / EHAK → OpenMapTiles Layer Mapping

How Estonian national datasets (ETAK topography + EHAK administration) are transformed into [OpenMapTiles](https://openmaptiles.org/schema/)-style vector tile layers. Built with the Python GDAL pipeline in this repository (`prepare` → `preprocess` → `generate`); the SQL that implements this document lives in `src/vt_pipeline/layers.py`, and tile zoom ranges in `config/settings.py`.

**Zoom levels:** tiles are cut on an EPSG:3301 (L-EST) grid with zooms 0–13. L-EST zoom levels are about **4 lower** than Web Mercator/OpenMapTiles zooms (L-EST z9 ≈ OMT z13). All zoom bands below are L-EST zooms.

---

## 1. Data Sources

| Source ID | File | Description |
|-----------|------|-------------|
| `etak` | `data/sources/etak.gpkg` | Estonian Topographic Database (ETAK), native EPSG:3301, copied as-is |
| `ehak` | `data/sources/ehak.gpkg` | Estonian Administrative and Settlement Division (EHAK), reprojected to EPSG:3301 |
| `ads` | `data/sources/ads.gpkg` | Estonian Address Data System (ADS/AKS) via WFS: building points, unofficial city districts, asum neighbourhoods, small places |

### ETAK download

<https://geoportaal.maaamet.ee/index.php?lang_id=2&plugin_act=otsing&andmetyyp=ETAK&dl=1&f=ETAK_EESTI_GPKG.zip&page_id=618>

### EHAK downloads

| Layer | URL |
|-------|-----|
| maakond (counties) | <https://s3.pilw.io/rp-kemit-kataster/EHAK/maakond_shp.zip> |
| omavalitsus (municipalities) | <https://s3.pilw.io/rp-kemit-kataster/EHAK/omavalitsus_shp.zip> |
| asustusyksus (settlements) | <https://s3.pilw.io/rp-kemit-kataster/EHAK/asustusyksus_shp.zip> |

### ADS source (AKS WFS)

<https://aks.geoportaal.ee/aks-ogc> (`SERVICE=WFS`), layers `aks:ads_linnaosa`, `aks:ads_asum`, `aks:ads_vk`. ADS attribute data is licensed CC0 1.0. These layers are polygons converted to label points during `prepare`. (Housenumbers no longer use ADS — they come from the ETAK building layer, see §3.14.)

### Data Preparation

`python -m vt_pipeline prepare` downloads all sources. The ETAK GeoPackage is already in EPSG:3301 and is copied unchanged. EHAK shapefiles (maakond, omavalitsus, asustusyksus) are reprojected to EPSG:3301 with `ogr2ogr` and merged into a single GeoPackage. ADS layers come from the AKS WFS; the district/small-place polygons are converted to label points in Python during prepare (so preprocessing SQL does not need Spatialite). See `src/vt_pipeline/prepare.py`.

---

## 2. ETAK Source Layers Used

| ETAK Layer | Description | Geometry |
|------------|-------------|----------|
| `E_201_meri_a` | Sea / ocean | Polygon |
| `E_202_seisuveekogu_a` | Standing water bodies (lakes, ponds) | Polygon |
| `E_203_vooluveekogu_a` | Flowing water bodies (area) | Polygon |
| `E_203_vooluveekogu_j` | Flowing water bodies (line) | Line |
| `E_301_muu_kolvik_a` | Other land cover (parks, green areas) | Polygon |
| `E_301_muu_kolvik_ka` | Other land cover — classified (cemeteries, airfields, harbors, quarries, stadiums) | Polygon |
| `E_302_ou_a` | Yards / land use zones (residential, industrial) | Polygon |
| `E_303_haritav_maa_a` | Cultivated land (fields, orchards) | Polygon |
| `E_304_lage_a` | Open land (meadow, sand) | Polygon |
| `E_305_puittaimestik_a` | Tree vegetation (forest, shrubs) | Polygon |
| `E_306_margala_a` | Wetlands | Polygon |
| `E_401_hoone_ka` | Buildings | Polygon |
| `E_501_tee_j` | Roads (line) | Line |
| `E_501_tee_a` | Road areas (parking lots, bus stations, runways, sports grounds, pedestrian areas) | Polygon |
| `E_502_roobastee_j` | Railways | Line |

### EHAK Source Layers

| EHAK Layer | Description |
|------------|-------------|
| `maakond` | Counties |
| `omavalitsus` | Municipalities |
| `asustusyksus` | Settlements |

#### EHAK Fields

| Field | Description |
|-------|-------------|
| `ANIMI` | Settlement name |
| `AKOOD` | Settlement code |
| `TYYP` | Unit type (see values below) |
| `ONIMI` | Municipality name |
| `OKOOD` | Municipality code |
| `MNIMI` | County name |
| `MKOOD` | County code |

**EHAK TYYP values:** `0` = maakond (county), `1` = vald (rural municipality), `3` = alev (borough), `4` = linn (city), `5` = omavalitsuse sisene linn (city within municipality), `6` = linnaosa (city district), `7` = alevik (small borough), `8` = küla (village)

---

## 3. Layer-by-Layer Mapping

### 3.1 `transportation` — Roads

**Source:** `E_501_tee_j`

The class ladder follows OSM-Estonia conventions: põhimaanteed are `trunk` (only their dual-carriageway 2+2 segments are `motorway`), and city main streets rank as `primary`, matching the tier at which state roads continue through towns.

**Dual-carriageway detection:** ETAK draws each carriageway of a 2+2 road as its own one-way line, so `liiklus IN (20, 30)` (one-way) on a state road identifies motorway/expressway segments without joining carriageway pairs.

| OMT class | OMT subclass | ETAK condition | ETAK meaning | L-EST band |
|-----------|-------------|----------------|--------------|------------|
| `motorway` | — | `tyyp=10` + one-way | Põhimaantee, dual carriageway | 0–13 |
| `trunk` | — | `tyyp=10` | Põhimaantee (main national road) | 0–13 |
| `primary` | — | `tyyp=20` | Tugimaantee (support national road) | 0–13 |
| `secondary` | — | `tyyp=30` | Kõrvalmaantee (local national road) | 5–13 |
| `trunk`/`primary`/`secondary` + `ramp=1` | — | `tyyp=40`, class by `tee` number (1–11 / 12–99 / ≥100 or none) | Ramp või ühendustee | 5–13 |
| `tertiary` | — | `tyyp=45` | Muu riigimaantee (other state road) | 5–13 |
| `primary` | — | `tyyp=50` + `tahtsus=10` | Tänav — põhitänav (main street) | 5–13 |
| `secondary` | — | `tyyp=50` + `tahtsus=20` | Tänav — jaotustänav (distributor street) | 5–13 |
| `minor` | — | `tyyp=50` + `tahtsus=30` | Kõrvaltänav (side street) | 9–13 |
| `service` | — | `tyyp=50` + `tahtsus=40` | Kvartalisisene tänav (intra-quarter street) | 9–13 |
| `path` | `pedestrian` | `tyyp=50` + `tahtsus=50` | Jalgtänav (pedestrian street) | 9–13 |
| `minor` | — | `tyyp=50` + `tahtsus` empty/`997` | Tänav, importance not set | 9–13 |
| `service` | — | `tyyp=60` + paved (`teekate` 10/30) | Muu tee (paved access/other road) | 9–13 |
| `track` | — | `tyyp=60` | Muu tee (field/forest/other road) | 9–13 |
| `path` | `path` | `tyyp=70` | Rada (footpath/trail) | 9–13 |
| `path` | `cycleway` | `tyyp=80` | Kergliiklustee (foot/cycle path) | 9–13 |

**Road attributes:**

| OMT Field | ETAK Field | Mapping |
|-----------|------------|---------|
| `surface=paved` | `teekate` | `10` (püsikate) or `30` (kivikate) |
| `surface=unpaved` | `teekate` | `20` (kruuskate) or `40` (pinnas) |
| `brunnel=bridge` | `a_tasand` / `l_tasand` | Values `1`, `2`, `3` |
| `brunnel=tunnel` | `a_tasand` / `l_tasand` | Value `-1` |
| `oneway=1` / `oneway=-1` | `liiklus` | `20` (pärisuunaline) / `30` (vastassuunaline) |
| `ramp=1` | `tyyp` | Value `40` (ramp või ühendustee) |
| `expressway=1` | `tyyp` + `liiklus` | State road (`tyyp` 10/20) drawn as one-way carriageway |
| `ref` | `tee` | Road number from the national road registry |

### 3.2 `transportation` — Railways

**Source:** `E_502_roobastee_j`

| OMT class | OMT subclass | ETAK `tyyp` | ETAK meaning | L-EST band |
|-----------|-------------|-------------|--------------|------------|
| `rail` | `rail` | 10 | Laiarööpmeline (broad gauge) | `tahtsus=10` → 5–13, else 9–13 |
| `rail` | `narrow_gauge` | 20 | Kitsarööpmeline (narrow gauge) | as above |
| `rail` | `funicular` | 30 | Köistee (cable railway) | as above |
| `rail` | `tram` | 40 | Trammitee (tramway) | as above |
| `rail` | `rail` | 50 | Muu raudtee (other railway) | as above |

### 3.3 `transportation` — Pedestrian Areas (polygons)

**Source:** `E_501_tee_a` where `tyyp=60` (jalakäijate ala — squares, plazas).

Emitted as polygons with `class=path`, `subclass=pedestrian`, following the OMT convention that the transportation layer also carries plaza polygons. L-EST band 9–13.

### 3.4 `transportation_name`

**Source:** `E_501_tee_j`, L-EST band 8–13. The `class`/`subclass` values mirror the road geometry mapping in 3.1 so labels style consistently with their lines.

| OMT Field | ETAK Field |
|-----------|------------|
| `name` | `nimetus` → `ads_nimetus` → `karto_nimi` (first non-empty) |
| `ref` | `tee` (road number) |

**Road network classification** (based on `tee` road number):

| OMT `network` | Road Number Range |
|----------------|-------------------|
| `ee-motorway` | 1–11 |
| `ee-primary` | 12–99 |
| `ee-secondary` | ≥ 100 |

### 3.5 `water` — Polygons

| OMT class | ETAK Layer | Description | L-EST band |
|-----------|------------|-------------|------------|
| `ocean` | `E_201_meri_a` | Sea / ocean | 0–13 |
| `lake` | `E_202_seisuveekogu_a` | Lakes, ponds | 5–13 |
| `river` | `E_203_vooluveekogu_a` | Rivers (polygon) | 5–13 |

### 3.6 `waterway` — Lines

**Source:** `E_203_vooluveekogu_j`, L-EST band 5–13.

**Filter:** `telje_staatus` empty or `10` (main axis / põhitelg)

| OMT class | ETAK `tyyp` | ETAK meaning |
|-----------|-------------|--------------|
| `river` | 10 | Jõgi (river) |
| `canal` | 20 | Kanal (canal) |
| `stream` | 30 (default) | Oja (stream) |
| `ditch` | 40, 50 | Peakraav / kraav (main ditch / ditch) |

| OMT Field | ETAK Field |
|-----------|------------|
| `brunnel=tunnel` | `telje_tyyp=20` (underground axis) |
| `name` | `nimetus` |

### 3.7 `landcover`

| OMT class | OMT subclass | ETAK Layer | ETAK `tyyp` | ETAK meaning | L-EST band |
|-----------|-------------|------------|-------------|--------------|------------|
| `wood` | `forest` | `E_305_puittaimestik_a` | 10 | Mets (forest) | 0–13 |
| `wood` | `forest` | `E_305_puittaimestik_a` | 30 | Põõsastik (shrubs) | 9–13 |
| `grass` | `meadow` | `E_304_lage_a` | 10 | Rohumaa (meadow) | 9–13 |
| `grass` | `park` | `E_301_muu_kolvik_a` | 10 | Haljasala (green area) | 5–13 |
| `farmland` | `farmland` | `E_303_haritav_maa_a` | 10 | Põld (field) | 5–13 |
| `farmland` | `orchard` | `E_303_haritav_maa_a` | 20 | Aianduslik (orchard/garden) | 9–13 |
| `wetland` | `wetland` | `E_306_margala_a` | all | Märgala (wetland) | 5–13 |
| `sand` | `sand` | `E_304_lage_a` | 20 | Liivane (sand) | 5–13 |

### 3.8 `landuse`

| OMT class | ETAK Layer | ETAK `tyyp` | ETAK meaning | L-EST band |
|-----------|------------|-------------|--------------|------------|
| `residential` | `E_302_ou_a` | 10 | Eraõu (private yard / residential) | 1–13 |
| `industrial` | `E_302_ou_a` | 20 | Tootmisõu (industrial yard) | 1–13 |
| `cemetery` | `E_301_muu_kolvik_ka` | 30 | Kalmistu (cemetery) | 1–13 |
| `stadium` | `E_301_muu_kolvik_ka` | 60 | Staadion (stadium) | 1–13 |
| `quarry` | `E_301_muu_kolvik_ka` | 100 | Karjäär (quarry) | 1–13 |
| `parking` *(custom)* | `E_501_tee_a` | 20 | Parkla (parking lot) | 8–13 |
| `bus_station` | `E_501_tee_a` | 30 | Bussijaam (bus station) | 8–13 |
| `stadium` | `E_501_tee_a` | 50 | Sport (sports ground) | 8–13 |

**Note:** the OMT schema has no standard home for parking polygons; `class=parking` is a custom extension (MapTiler's planet-v4 schema uses a dedicated `parking` layer for the same purpose). `E_501_tee_a` `tyyp=10` (liiklusala — carriageway surface polygons) is intentionally skipped.

### 3.9 `building`

**Source:** `E_401_hoone_ka`

All building polygons where `tyyp` is `10` or `20`. L-EST band **9–13**.

### 3.10 `aeroway`

| OMT class | ETAK Layer | ETAK `tyyp` | ETAK meaning | L-EST band |
|-----------|------------|-------------|--------------|------------|
| `aerodrome` | `E_301_muu_kolvik_ka` | 40 | Lennuväli (airfield area) | 6–13 |
| `runway` | `E_501_tee_a` | 40 | Lennurada (runway) | 6–13 |

### 3.11 `boundary`

**Source:** EHAK (polygon boundaries converted to linestrings), L-EST band 0–13.

| OMT `admin_level` | EHAK Layer | Name field |
|--------------------|------------|------------|
| 4 (county) | `maakond` | `MNIMI` |
| 6 (municipality) | `omavalitsus` | `ONIMI` |
| 8 (settlement) | `asustusyksus` | `ANIMI` |

All boundaries have `disputed=0` and `maritime=0`.

### 3.12 `place`

**Source:** EHAK (polygon centroids), L-EST band 0–13. Per-feature `minzoom` attribute controls label appearance.

| OMT class | EHAK `TYYP` | Source layer | rank | minzoom attr |
|-----------|-------------|-------------|------|--------------|
| `province` | 0 (maakond) | `maakond` | 10 | 0 |
| `city` | 4 (linn) | `asustusyksus` | 4 (Tallinn: 2) | 2 (Tallinn: 0) |
| `city` | 5 (omavalitsuse sisene linn) | `asustusyksus` | 6 | 3 |
| `town` | 3 (alev) | `asustusyksus` | 7 | 4 |
| `town` | 7 (alevik) | `asustusyksus` | 8 | 5 |
| `suburb` | 6 (linnaosa) | `asustusyksus` | 9 | 7 |
| `village` | 8 (küla) | `asustusyksus` | 12 | 6 |

**Capital:** Tallinn is marked with `capital=2`, `rank=2`.

### 3.13 `place` — City Parts and Small Places (ADS)

**Source:** ADS/AKS WFS layers (label points computed from polygons at prepare time), L-EST band 8–13. Complements the EHAK-based place labels: official EHAK linnaosa remain `suburb`; the ADS layers add the unofficial/finer levels. Generic type suffixes (" linnaosa", " asum", " väikekoht") are stripped from names.

| OMT class | ADS layer | Description | rank | minzoom attr |
|-----------|-----------|-------------|------|--------------|
| `quarter` | `ads_linnaosa` | Unofficial city districts (e.g. Narva, Pärnu districts) | 11 | 8 |
| `neighbourhood` | `ads_asum` | Asum neighbourhoods (e.g. Kalamaja, Lilleküla) | 13 | 9 |
| `neighbourhood` | `ads_vk` | Väikekohad — garden/summer-house co-ops (`olek='K'`) | 14 | 10 |

### 3.14 `housenumber`

**Source:** `E_401_hoone_ka` (ETAK buildings, `ads_lahiaadress`), L-EST band 10–13 (≈ OMT 14+). The label point is placed with `ST_PointOnSurface(geom)` so it always sits inside the building footprint; filtered to `tyyp IN (10, 20)` (same buildings the `building` layer draws).

`housenumber` is the trailing token of `ads_lahiaadress`, kept only when it starts with a digit ("12", "12a", "3/5"). Buildings addressed by name only (farms — "Tiigi", "Konda") are skipped; those could later come from KNR place-name layers. A leading garden-association prefix ("Koppelmaa AÜ, Ilvese tn 12") does not affect the trailing-token extraction.

### 3.15 `park`

**Source:** `E_301_muu_kolvik_a` where `tyyp=10` (haljasala / green area). L-EST band 5–13.

Emitted as polygons with `class=public_park`. `E_301_muu_kolvik_a` has no name field in ETAK (names exist only on the `_ka`/`_p` variants), so park polygons carry no labels; named parks would need the KNR place-name register as a future source. The same green areas also render through `landcover` (`grass`/`park`); this layer adds the semantic park fill/outline styles key on.

### 3.16 `poi`

**Source:** ETAK polygon layers, centroid geometry. L-EST band 8–13.

| OMT class | ETAK Layer | ETAK `tyyp` | Name source |
|-----------|------------|-------------|-------------|
| `harbor` | `E_301_muu_kolvik_ka` | 50 | `nimetus` (non-empty only) |
| `cemetery` | `E_301_muu_kolvik_ka` | 30 | `nimetus` (non-empty only) |

An earlier park POI entry was removed: `E_301_muu_kolvik_a` has no name field, so every POI would have been labeled with the type text "Haljasala". Parks are now polygons in the `park` layer instead.

---

## 4. GPKG Layer → Tile Layer Zoom Bands

Defined in `config/settings.py`; the basemap GPKG layers are produced by `src/vt_pipeline/layers.py`.

| GPKG layer | Tile layer | L-EST zooms |
|------------|-----------|-------------|
| `transportation_z0_4` / `_z5_8` / `_z9_13` | `transportation` | 0–4 / 5–8 / 9–13 |
| `transportation_area_z9_13` | `transportation` | 9–13 |
| `transportation_name_z8_13` | `transportation_name` | 8–13 |
| `water_z0_4` / `_z5_8` / `_z9_13` | `water` | 0–4 / 5–8 / 9–13 |
| `waterway_z5_13` | `waterway` | 5–13 |
| `landcover_z0_4` / `_z5_8` / `_z9_13` | `landcover` | 0–4 / 5–8 / 9–13 |
| `landuse_z1_13` | `landuse` | 1–13 |
| `landuse_detail_z8_13` | `landuse` | 8–13 |
| `aeroway_z6_13` | `aeroway` | 6–13 |
| `building_z9_13` | `building` | 9–13 |
| `park_z5_13` | `park` | 5–13 |
| `boundary_z0_13` | `boundary` | 0–13 |
| `place_z0_13` | `place` | 0–13 |
| `place_detail_z8_13` | `place` | 8–13 |
| `housenumber_z10_13` | `housenumber` | 10–13 |
| `poi_z8_13` | `poi` | 8–13 |

---

## 5. OpenMapTiles Schema Coverage

Full schema documentation: <https://openmaptiles.org/schema/>

| OMT Layer | Implemented | Primary ETAK/EHAK Source |
|-----------|-------------|--------------------------|
| `aerodrome_label` | No | — |
| `aeroway` | Yes | `E_301_muu_kolvik_ka` (tyyp=40), `E_501_tee_a` (tyyp=40) |
| `boundary` | Yes | EHAK (maakond, omavalitsus, asustusyksus) |
| `building` | Yes | `E_401_hoone_ka` |
| `housenumber` | Yes | ETAK `E_401_hoone_ka` (`ads_lahiaadress`) |
| `landcover` | Yes | `E_305_puittaimestik_a`, `E_304_lage_a`, `E_303_haritav_maa_a`, `E_306_margala_a`, `E_301_muu_kolvik_a` |
| `landuse` | Yes | `E_302_ou_a`, `E_301_muu_kolvik_ka`, `E_501_tee_a` |
| `mountain_peak` | No — Estonia is flat, no significant peaks | — |
| `park` | Yes | `E_301_muu_kolvik_a` (tyyp=10) |
| `place` | Yes | EHAK (maakond, asustusyksus), ADS (linnaosa, asum, väikekoht) |
| `poi` | Yes | `E_301_muu_kolvik_a`, `E_301_muu_kolvik_ka` |
| `transportation` | Yes | `E_501_tee_j`, `E_501_tee_a`, `E_502_roobastee_j` |
| `transportation_name` | Yes | `E_501_tee_j` |
| `water` | Yes | `E_201_meri_a`, `E_202_seisuveekogu_a`, `E_203_vooluveekogu_a` |
| `water_name` | No | — |
| `waterway` | Yes | `E_203_vooluveekogu_j` |

`boundary` admin_level=2 (state border) is skipped by design. An earlier Planetiler-based build also produced `water_name`, `aerodrome_label`, and a custom `forest_compartment` layer (`E_503_siht_j`); these have not been ported to the Python pipeline.

---

## 6. ETAK Classifier Reference (excerpts)

From the ETAK data model (`docs/etak_andmemudel_20170330.pdf`, 2017-03-30).

**`tee_tyyp`** (road type): 10 põhimaantee, 20 tugimaantee, 30 kõrvalmaantee, 40 ramp või ühendustee, 45 muu riigimaantee, 50 tänav, 60 muu tee, 70 rada, 80 kergliiklustee

**`tee_tahtsus`** (street importance): 10 põhitänav, 20 jaotustänav, 30 kõrvaltänav, 40 kvartalisisene tänav, 50 jalgtänav, 997 täitmata

**`tee_liiklus`** (allowed direction): 10 kahesuunaline, 20 pärisuunaline, 30 vastassuunaline, 997 täitmata

**`tee_teekate`** (surface): 10 püsikate, 20 kruuskate, 30 kivikate, 40 pinnas, 997 täitmata, 999 muu

**`teeA_tyyp`** (road area type): 10 liiklusala, 20 parkla, 30 bussijaam, 40 lennurada, 50 sport, 60 jalakäijate ala, 997 täitmata, 999 muu

**Note:** newer ETAK extracts may contain classifier values added after 2017; unknown road `tyyp`/`tahtsus` values fall back to `class=minor` at the 9–13 band. After downloading a fresh extract, a quick `SELECT tyyp, tahtsus, COUNT(*) ... GROUP BY 1, 2` sanity check is recommended.

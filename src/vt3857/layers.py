from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayerDef:
    source: str
    name: str
    sql: str
    nlt: str
    comment: str


# The source ETAK schema uses Estonian numeric classifiers. These layer
# definitions translate those classifiers into a compact OpenMapTiles-like
# schema before Planetiler cuts Web Mercator vector tiles.
#
# The classification SQL is identical to the EPSG:3301 pipeline; only the zoom
# band names and per-feature minzoom values differ. Bands are shifted +4 zoom
# levels because L-EST z9 detail is roughly Web Mercator/OpenMapTiles z13, and
# clamped to the 0-15 range (deeper display zooms overzoom the z15 tiles).
#
# Dual carriageways: ETAK draws each carriageway of a 2+2 road as its own
# one-way line (liiklus 20/30), so "state road AND one-way" identifies
# motorway/expressway segments without joining carriageway pairs.
LAYERS = [
    LayerDef(
        "etak",
        "transportation_z0_8",
        """
SELECT geom,
  CASE
    WHEN tyyp = 10 AND liiklus IN (20,30) THEN 'motorway'
    WHEN tyyp = 10 THEN 'trunk'
    WHEN tyyp = 20 THEN 'primary'
  END AS class,
  CAST(NULL AS TEXT) AS subclass,
  CASE WHEN COALESCE(a_tasand, l_tasand) IN (1,2,3) THEN 'bridge'
       WHEN COALESCE(a_tasand, l_tasand) = -1 THEN 'tunnel'
       ELSE NULL END AS brunnel,
  CASE WHEN teekate IN (10,30) THEN 'paved'
       WHEN teekate IN (20,40) THEN 'unpaved'
       ELSE NULL END AS surface,
  CASE WHEN tyyp IN (10,20) AND liiklus IN (20,30) THEN 1 ELSE 0 END AS expressway,
  CASE WHEN liiklus = 20 THEN 1 WHEN liiklus = 30 THEN -1 ELSE 0 END AS oneway,
  0 AS ramp,
  tee AS ref
FROM E_501_tee_j
WHERE tyyp IN (10, 20)
""",
        "PROMOTE_TO_MULTI",
        "Low zoom roads: main and support national roads only.",
    ),
    LayerDef(
        "etak",
        "transportation_z9_12",
        """
SELECT geom,
  CASE
    WHEN tyyp = 10 AND liiklus IN (20,30) THEN 'motorway'
    WHEN tyyp = 10 THEN 'trunk'
    WHEN tyyp = 20 THEN 'primary'
    WHEN tyyp = 30 THEN 'secondary'
    WHEN tyyp = 40 AND tee BETWEEN 1 AND 11 THEN 'trunk'
    WHEN tyyp = 40 AND tee BETWEEN 12 AND 99 THEN 'primary'
    WHEN tyyp = 40 THEN 'secondary'
    WHEN tyyp = 45 THEN 'tertiary'
    WHEN tyyp = 50 AND tahtsus = 10 THEN 'primary'
    WHEN tyyp = 50 AND tahtsus = 20 THEN 'secondary'
  END AS class,
  CAST(NULL AS TEXT) AS subclass,
  CASE WHEN COALESCE(a_tasand, l_tasand) IN (1,2,3) THEN 'bridge'
       WHEN COALESCE(a_tasand, l_tasand) = -1 THEN 'tunnel'
       ELSE NULL END AS brunnel,
  CASE WHEN teekate IN (10,30) THEN 'paved'
       WHEN teekate IN (20,40) THEN 'unpaved'
       ELSE NULL END AS surface,
  CASE WHEN tyyp IN (10,20) AND liiklus IN (20,30) THEN 1 ELSE 0 END AS expressway,
  CASE WHEN liiklus = 20 THEN 1 WHEN liiklus = 30 THEN -1 ELSE 0 END AS oneway,
  CASE WHEN tyyp = 40 THEN 1 ELSE 0 END AS ramp,
  tee AS ref
FROM E_501_tee_j
WHERE tyyp IN (10, 20, 30, 40, 45) OR (tyyp = 50 AND tahtsus IN (10, 20))

UNION ALL

SELECT geom,
  'rail' AS class,
  CASE
    WHEN tyyp = 10 THEN 'rail'
    WHEN tyyp = 20 THEN 'narrow_gauge'
    WHEN tyyp = 30 THEN 'funicular'
    WHEN tyyp = 40 THEN 'tram'
    WHEN tyyp = 50 THEN 'rail'
    ELSE 'rail'
  END AS subclass,
  CAST(NULL AS TEXT) AS brunnel,
  CAST(NULL AS TEXT) AS surface,
  0 AS expressway,
  0 AS oneway,
  0 AS ramp,
  CAST(NULL AS TEXT) AS ref
FROM E_502_roobastee_j
WHERE tahtsus = 10
""",
        "PROMOTE_TO_MULTI",
        "Mid zoom transportation adds secondary/tertiary roads and main rail.",
    ),
    LayerDef(
        "etak",
        "transportation_z13_15",
        """
SELECT geom,
  CASE
    WHEN tyyp = 10 AND liiklus IN (20,30) THEN 'motorway'
    WHEN tyyp = 10 THEN 'trunk'
    WHEN tyyp = 20 THEN 'primary'
    WHEN tyyp = 30 THEN 'secondary'
    WHEN tyyp = 40 AND tee BETWEEN 1 AND 11 THEN 'trunk'
    WHEN tyyp = 40 AND tee BETWEEN 12 AND 99 THEN 'primary'
    WHEN tyyp = 40 THEN 'secondary'
    WHEN tyyp = 45 THEN 'tertiary'
    WHEN tyyp = 50 AND tahtsus = 10 THEN 'primary'
    WHEN tyyp = 50 AND tahtsus = 20 THEN 'secondary'
    WHEN tyyp = 50 AND tahtsus = 30 THEN 'minor'
    WHEN tyyp = 50 AND tahtsus = 40 THEN 'service'
    WHEN tyyp = 50 AND tahtsus = 50 THEN 'path'
    WHEN tyyp = 60 AND teekate IN (10,30) THEN 'service'
    WHEN tyyp = 60 THEN 'track'
    WHEN tyyp = 70 THEN 'path'
    WHEN tyyp = 80 THEN 'path'
    ELSE 'minor'
  END AS class,
  CASE
    WHEN tyyp = 50 AND tahtsus = 50 THEN 'pedestrian'
    WHEN tyyp = 70 THEN 'path'
    WHEN tyyp = 80 THEN 'cycleway'
    ELSE CAST(NULL AS TEXT)
  END AS subclass,
  CASE WHEN COALESCE(a_tasand, l_tasand) IN (1,2,3) THEN 'bridge'
       WHEN COALESCE(a_tasand, l_tasand) = -1 THEN 'tunnel'
       ELSE NULL END AS brunnel,
  CASE WHEN teekate IN (10,30) THEN 'paved'
       WHEN teekate IN (20,40) THEN 'unpaved'
       ELSE NULL END AS surface,
  CASE WHEN tyyp IN (10,20) AND liiklus IN (20,30) THEN 1 ELSE 0 END AS expressway,
  CASE WHEN liiklus = 20 THEN 1 WHEN liiklus = 30 THEN -1 ELSE 0 END AS oneway,
  CASE WHEN tyyp = 40 THEN 1 ELSE 0 END AS ramp,
  tee AS ref
FROM E_501_tee_j

UNION ALL

SELECT geom,
  'rail' AS class,
  CASE
    WHEN tyyp = 10 THEN 'rail'
    WHEN tyyp = 20 THEN 'narrow_gauge'
    WHEN tyyp = 30 THEN 'funicular'
    WHEN tyyp = 40 THEN 'tram'
    WHEN tyyp = 50 THEN 'rail'
    ELSE 'rail'
  END AS subclass,
  CAST(NULL AS TEXT) AS brunnel,
  CAST(NULL AS TEXT) AS surface,
  0 AS expressway,
  0 AS oneway,
  0 AS ramp,
  CAST(NULL AS TEXT) AS ref
FROM E_502_roobastee_j
""",
        "PROMOTE_TO_MULTI",
        "High zoom transportation includes all road and rail detail.",
    ),
    LayerDef(
        "etak",
        "transportation_name_z12_15",
        """
SELECT geom,
  COALESCE(nimetus, ads_nimetus, karto_nimi) AS name,
  tee AS ref,
  CASE
    WHEN CAST(tee AS INTEGER) BETWEEN 1 AND 11 THEN 'ee-motorway'
    WHEN CAST(tee AS INTEGER) BETWEEN 12 AND 99 THEN 'ee-primary'
    WHEN CAST(tee AS INTEGER) >= 100 THEN 'ee-secondary'
    ELSE NULL
  END AS network,
  CASE
    WHEN tyyp = 10 AND liiklus IN (20,30) THEN 'motorway'
    WHEN tyyp = 10 THEN 'trunk'
    WHEN tyyp = 20 THEN 'primary'
    WHEN tyyp = 30 THEN 'secondary'
    WHEN tyyp = 40 AND tee BETWEEN 1 AND 11 THEN 'trunk'
    WHEN tyyp = 40 AND tee BETWEEN 12 AND 99 THEN 'primary'
    WHEN tyyp = 40 THEN 'secondary'
    WHEN tyyp = 45 THEN 'tertiary'
    WHEN tyyp = 50 AND tahtsus = 10 THEN 'primary'
    WHEN tyyp = 50 AND tahtsus = 20 THEN 'secondary'
    WHEN tyyp = 50 AND tahtsus = 30 THEN 'minor'
    WHEN tyyp = 50 AND tahtsus = 40 THEN 'service'
    WHEN tyyp = 50 AND tahtsus = 50 THEN 'path'
    WHEN tyyp = 60 AND teekate IN (10,30) THEN 'service'
    WHEN tyyp = 60 THEN 'track'
    WHEN tyyp = 70 THEN 'path'
    WHEN tyyp = 80 THEN 'path'
    ELSE 'minor'
  END AS class,
  CASE
    WHEN tyyp = 50 AND tahtsus = 50 THEN 'pedestrian'
    WHEN tyyp = 70 THEN 'path'
    WHEN tyyp = 80 THEN 'cycleway'
    ELSE CAST(NULL AS TEXT)
  END AS subclass
FROM E_501_tee_j
WHERE COALESCE(nimetus, ads_nimetus, karto_nimi, tee) IS NOT NULL
""",
        "PROMOTE_TO_MULTI",
        "Road labels start later so low zooms stay light.",
    ),
    LayerDef(
        "etak",
        "transportation_area_z13_15",
        """
SELECT geom, 'path' AS class, 'pedestrian' AS subclass
FROM E_501_tee_a
WHERE tyyp = 60
""",
        "PROMOTE_TO_MULTI",
        "Pedestrian squares and plazas as transportation polygons.",
    ),
    LayerDef("etak", "water_z0_8", "SELECT geom, 'ocean' AS class FROM E_201_meri_a", "PROMOTE_TO_MULTI", "Low zoom water keeps only the sea polygon."),
    LayerDef(
        "etak",
        "water_z9_12",
        """
SELECT geom, 'ocean' AS class FROM E_201_meri_a
UNION ALL
SELECT geom, 'lake' AS class FROM E_202_seisuveekogu_a
UNION ALL
SELECT geom, 'river' AS class FROM E_203_vooluveekogu_a
""",
        "PROMOTE_TO_MULTI",
        "Mid zoom water adds lakes and river polygons.",
    ),
    LayerDef(
        "etak",
        "water_z13_15",
        """
SELECT geom, 'ocean' AS class FROM E_201_meri_a
UNION ALL
SELECT geom, 'lake' AS class FROM E_202_seisuveekogu_a
UNION ALL
SELECT geom, 'river' AS class FROM E_203_vooluveekogu_a
""",
        "PROMOTE_TO_MULTI",
        "High zoom water keeps all water polygon classes.",
    ),
    LayerDef(
        "etak",
        "waterway_z9_15",
        """
SELECT geom,
  CASE
    WHEN tyyp = 10 THEN 'river'
    WHEN tyyp = 20 THEN 'canal'
    WHEN tyyp = 30 THEN 'stream'
    WHEN tyyp IN (40, 50) THEN 'ditch'
    ELSE 'stream'
  END AS class,
  CASE WHEN telje_tyyp = 20 THEN 'tunnel' ELSE NULL END AS brunnel,
  nimetus AS name
FROM E_203_vooluveekogu_j
WHERE COALESCE(telje_staatus, 0) IN (0, 10)
""",
        "PROMOTE_TO_MULTI",
        "Waterway centerlines are useful from mid zoom onward.",
    ),
    LayerDef("etak", "landcover_z0_8", "SELECT geom, 'wood' AS class, 'forest' AS subclass FROM E_305_puittaimestik_a WHERE tyyp = 10", "PROMOTE_TO_MULTI", "Low zoom landcover keeps only broad forest."),
    LayerDef(
        "etak",
        "landcover_z9_12",
        """
SELECT geom, 'wood' AS class, 'forest' AS subclass FROM E_305_puittaimestik_a WHERE tyyp = 10
UNION ALL
SELECT geom, 'wetland' AS class, 'wetland' AS subclass FROM E_306_margala_a
UNION ALL
SELECT geom, 'farmland' AS class, 'farmland' AS subclass FROM E_303_haritav_maa_a WHERE tyyp = 10
UNION ALL
SELECT geom, 'sand' AS class, 'sand' AS subclass FROM E_304_lage_a WHERE tyyp = 20
UNION ALL
SELECT geom, 'grass' AS class, 'park' AS subclass FROM E_301_muu_kolvik_a WHERE tyyp = 10
""",
        "PROMOTE_TO_MULTI",
        "Mid zoom landcover adds visible natural and agricultural areas.",
    ),
    LayerDef(
        "etak",
        "landcover_z13_15",
        """
SELECT geom, 'wood' AS class, 'forest' AS subclass FROM E_305_puittaimestik_a WHERE tyyp = 10
UNION ALL
SELECT geom, 'wood' AS class, 'forest' AS subclass FROM E_305_puittaimestik_a WHERE tyyp = 30
UNION ALL
SELECT geom, 'grass' AS class, 'meadow' AS subclass FROM E_304_lage_a WHERE tyyp = 10
UNION ALL
SELECT geom, 'grass' AS class, 'park' AS subclass FROM E_301_muu_kolvik_a WHERE tyyp = 10
UNION ALL
SELECT geom, 'farmland' AS class, 'farmland' AS subclass FROM E_303_haritav_maa_a WHERE tyyp = 10
UNION ALL
SELECT geom, 'farmland' AS class, 'orchard' AS subclass FROM E_303_haritav_maa_a WHERE tyyp = 20
UNION ALL
SELECT geom, 'wetland' AS class, 'wetland' AS subclass FROM E_306_margala_a
UNION ALL
SELECT geom, 'sand' AS class, 'sand' AS subclass FROM E_304_lage_a WHERE tyyp = 20
""",
        "PROMOTE_TO_MULTI",
        "High zoom landcover includes the full visual detail set.",
    ),
    LayerDef(
        "etak",
        "landuse_z5_15",
        """
SELECT geom,
  CASE
    WHEN tyyp = 10 THEN 'residential'
    WHEN tyyp = 20 THEN 'industrial'
  END AS class
FROM E_302_ou_a
WHERE tyyp IN (10, 20)

UNION ALL

SELECT geom,
  CASE
    WHEN tyyp = 30 THEN 'cemetery'
    WHEN tyyp = 60 THEN 'stadium'
    WHEN tyyp = 100 THEN 'quarry'
  END AS class
FROM E_301_muu_kolvik_ka
WHERE tyyp IN (30, 60, 100)
""",
        "PROMOTE_TO_MULTI",
        "Landuse starts at z5 so the lowest zooms stay simple.",
    ),
    LayerDef(
        "etak",
        "landuse_detail_z12_15",
        """
SELECT geom,
  CASE
    WHEN tyyp = 20 THEN 'parking'
    WHEN tyyp = 30 THEN 'bus_station'
    WHEN tyyp = 50 THEN 'stadium'
  END AS class
FROM E_501_tee_a
WHERE tyyp IN (20, 30, 50)
""",
        "PROMOTE_TO_MULTI",
        "Parking lots, bus stations and sports grounds at street zooms.",
    ),
    LayerDef(
        "etak",
        "aeroway_z10_15",
        """
SELECT geom, 'aerodrome' AS class FROM E_301_muu_kolvik_ka WHERE tyyp = 40

UNION ALL

SELECT geom, 'runway' AS class FROM E_501_tee_a WHERE tyyp = 40
""",
        "PROMOTE_TO_MULTI",
        "Airfield areas and runways.",
    ),
    LayerDef("etak", "building_z13_15", "SELECT geom FROM E_401_hoone_ka WHERE tyyp IN (10, 20)", "PROMOTE_TO_MULTI", "Buildings appear at the OpenMapTiles-standard z13."),
    LayerDef(
        "ehak",
        "boundary_z0_15",
        """
SELECT ST_Boundary(geom) AS geom, 4 AS admin_level, MNIMI AS name, 0 AS maritime, 0 AS disputed
FROM maakond

UNION ALL

SELECT ST_Boundary(geom) AS geom, 6 AS admin_level, ONIMI AS name, 0 AS maritime, 0 AS disputed
FROM omavalitsus

UNION ALL

SELECT ST_Boundary(geom) AS geom, 8 AS admin_level, ANIMI AS name, 0 AS maritime, 0 AS disputed
FROM asustusyksus
""",
        "MULTILINESTRING",
        "EHAK polygons become boundary lines for map styling.",
    ),
    LayerDef(
        "ehak",
        "place_z0_15",
        """
SELECT ST_Centroid(geom) AS geom,
  MNIMI AS name,
  'province' AS class,
  10 AS rank,
  0 AS capital,
  0 AS minzoom
FROM maakond

UNION ALL

SELECT ST_Centroid(geom) AS geom,
  ANIMI AS name,
  CASE
    WHEN TYYP = 4 THEN 'city'
    WHEN TYYP = 5 THEN 'city'
    WHEN TYYP = 3 THEN 'town'
    WHEN TYYP = 7 THEN 'town'
    WHEN TYYP = 6 THEN 'suburb'
    WHEN TYYP = 8 THEN 'village'
    ELSE 'village'
  END AS class,
  CASE
    WHEN TYYP = 4 AND ANIMI = 'Tallinn' THEN 2
    WHEN TYYP = 4 THEN 4
    WHEN TYYP = 5 THEN 6
    WHEN TYYP = 3 THEN 7
    WHEN TYYP = 7 THEN 8
    WHEN TYYP = 6 THEN 9
    WHEN TYYP = 8 THEN 12
    ELSE 12
  END AS rank,
  CASE WHEN TYYP = 4 AND ANIMI = 'Tallinn' THEN 2 ELSE 0 END AS capital,
  CASE
    WHEN TYYP = 4 AND ANIMI = 'Tallinn' THEN 0
    WHEN TYYP = 4 THEN 6
    WHEN TYYP = 5 THEN 7
    WHEN TYYP = 3 THEN 8
    WHEN TYYP = 7 THEN 9
    WHEN TYYP = 6 THEN 11
    WHEN TYYP = 8 THEN 10
    ELSE 12
  END AS minzoom
FROM asustusyksus
WHERE TYYP IN (3, 4, 5, 6, 7, 8)
""",
        "POINT",
        "Settlement polygons become label points; minzoom values are Web Mercator zooms (EPSG:3301 values shifted +4).",
    ),
    LayerDef(
        "etak",
        "park_z9_15",
        # E_301_muu_kolvik_a has no name field, so park polygons carry no label.
        "SELECT geom, 'public_park' AS class FROM E_301_muu_kolvik_a WHERE tyyp = 10",
        "PROMOTE_TO_MULTI",
        "Green areas (haljasala) as park polygons.",
    ),
    LayerDef(
        "ads",
        "place_detail_z12_15",
        """
SELECT geom,
  CASE WHEN nimi LIKE '% linnaosa' THEN substr(nimi, 1, length(nimi) - 9) ELSE nimi END AS name,
  'quarter' AS class, 11 AS rank, 0 AS capital, 12 AS minzoom
FROM ads_linnaosa

UNION ALL

SELECT geom,
  CASE WHEN nimi LIKE '% asum' THEN substr(nimi, 1, length(nimi) - 5) ELSE nimi END AS name,
  'neighbourhood' AS class, 13 AS rank, 0 AS capital, 13 AS minzoom
FROM ads_asum

UNION ALL

SELECT geom,
  CASE WHEN nimi LIKE '% väikekoht' THEN substr(nimi, 1, length(nimi) - 10) ELSE nimi END AS name,
  'neighbourhood' AS class, 14 AS rank, 0 AS capital, 14 AS minzoom
FROM ads_vk
WHERE olek = 'K'
""",
        "POINT",
        "Unofficial city districts, asum neighbourhoods and small places as labels.",
    ),
    LayerDef(
        "etak",
        "housenumber_z14_15",
        """
SELECT ST_PointOnSurface(geom) AS geom,
  substr(ads_lahiaadress, length(rtrim(ads_lahiaadress, replace(ads_lahiaadress, ' ', ''))) + 1) AS housenumber
FROM E_401_hoone_ka
WHERE tyyp IN (10, 20)
  AND ads_lahiaadress IS NOT NULL AND ads_lahiaadress != ''
  AND substr(substr(ads_lahiaadress, length(rtrim(ads_lahiaadress, replace(ads_lahiaadress, ' ', ''))) + 1), 1, 1) BETWEEN '0' AND '9'
""",
        "POINT",
        "Building numbers: trailing digit-token of ads_lahiaadress, point placed on the footprint.",
    ),
    LayerDef(
        "etak",
        "poi_z12_15",
        """
SELECT ST_Centroid(geom) AS geom, nimetus AS name, 'harbor' AS class, 'harbor' AS subclass
FROM E_301_muu_kolvik_ka WHERE tyyp = 50 AND nimetus IS NOT NULL AND nimetus != ''

UNION ALL

SELECT ST_Centroid(geom) AS geom, nimetus AS name, 'cemetery' AS class, 'cemetery' AS subclass
FROM E_301_muu_kolvik_ka WHERE tyyp = 30 AND nimetus IS NOT NULL AND nimetus != ''
""",
        "POINT",
        "POI labels are point features created from area centroids.",
    ),
]

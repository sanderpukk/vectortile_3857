# User-editable settings for the Python + Planetiler EPSG:3857 pipeline.
#
# This file is regular Python on purpose: it is easy to comment, copy, and edit.
# The pipeline converts LAYERS to Planetiler's custommap schema at runtime.
#
# Zoom bands mirror the EPSG:3301 pipeline shifted by +4 zoom levels (L-EST z9
# is roughly Web Mercator/OpenMapTiles z13) and clamped to the 0-15 range.
# Bands that started at L-EST z0 keep starting at z0 here.
#
# maxzoom 15 is the deepest practical Planetiler tile level (hard cap 16).
# Deeper views (z16-z20) are served by client-side overzooming of the z15
# tiles, which stays crisp because the tiles are vectors: z15 at the 4096
# tile extent carries ~0.3 m coordinate precision, plenty for z18 display.

MVT = {
    "minzoom": 0,
    "maxzoom": 15,
}

MODES = {
    # Default: full-country generation. This is the main product; it takes
    # longer and uses more disk than the Tallinn prototype.
    # Bounds are lon/lat (west, south, east, north) covering all of Estonia.
    "estonia": {
        "output": "estonia",
        "bounds": [21.5, 57.4, 28.3, 59.9],
    },
    # Optional fast prototype around Tallinn. Validates the schema and styling
    # without generating all Estonia tiles. Select with `--mode tallinn`
    # (or MODE=tallinn for Docker Compose). Approximates the EPSG:3301
    # prototype bbox [530000, 6570000, 560000, 6600000].
    "tallinn": {
        "output": "tallinn",
        "bounds": [24.5, 59.25, 25.1, 59.55],
    },
}

# Metadata written into the Planetiler schema and tile metadata.json.
SCHEMA = {
    "name": "Estonia ETAK basemap",
    "description": "OpenMapTiles-like vector tiles built from ETAK/EHAK/ADS sources in EPSG:3857",
    "attribution": '&copy; <a href="https://geoportaal.maaamet.ee/">Maa-amet</a>',
}

# Planetiler layer mapping. Keys are layer names inside basemap.gpkg.
# target_name is the layer name exposed in the final vector tiles.
# geometry selects the Planetiler feature geometry (point/line/polygon).
# attributes lists the basemap.gpkg columns copied into tile features.
# feature_minzoom names a column whose value becomes the per-feature minimum
# zoom (Planetiler enforces it; the column is also kept as a tile attribute).
LAYERS = {
    "transportation_z0_8": {
        "target_name": "transportation", "minzoom": 0, "maxzoom": 8, "geometry": "line",
        "attributes": ["class", "subclass", "brunnel", "surface", "expressway", "oneway", "ramp", "ref"],
    },
    "transportation_z9_12": {
        "target_name": "transportation", "minzoom": 9, "maxzoom": 12, "geometry": "line",
        "attributes": ["class", "subclass", "brunnel", "surface", "expressway", "oneway", "ramp", "ref"],
    },
    "transportation_z13_15": {
        "target_name": "transportation", "minzoom": 13, "maxzoom": 15, "geometry": "line",
        "attributes": ["class", "subclass", "brunnel", "surface", "expressway", "oneway", "ramp", "ref"],
    },
    "transportation_area_z13_15": {
        "target_name": "transportation", "minzoom": 13, "maxzoom": 15, "geometry": "polygon",
        "attributes": ["class", "subclass"],
    },
    "transportation_name_z12_15": {
        "target_name": "transportation_name", "minzoom": 12, "maxzoom": 15, "geometry": "line",
        "attributes": ["name", "ref", "network", "class", "subclass"],
    },
    "water_z0_8": {
        "target_name": "water", "minzoom": 0, "maxzoom": 8, "geometry": "polygon",
        "attributes": ["class"],
    },
    "water_z9_12": {
        "target_name": "water", "minzoom": 9, "maxzoom": 12, "geometry": "polygon",
        "attributes": ["class"],
    },
    "water_z13_15": {
        "target_name": "water", "minzoom": 13, "maxzoom": 15, "geometry": "polygon",
        "attributes": ["class"],
    },
    "waterway_z9_15": {
        "target_name": "waterway", "minzoom": 9, "maxzoom": 15, "geometry": "line",
        "attributes": ["class", "brunnel", "name"],
    },
    "landcover_z0_8": {
        "target_name": "landcover", "minzoom": 0, "maxzoom": 8, "geometry": "polygon",
        "attributes": ["class", "subclass"],
    },
    "landcover_z9_12": {
        "target_name": "landcover", "minzoom": 9, "maxzoom": 12, "geometry": "polygon",
        "attributes": ["class", "subclass"],
    },
    "landcover_z13_15": {
        "target_name": "landcover", "minzoom": 13, "maxzoom": 15, "geometry": "polygon",
        "attributes": ["class", "subclass"],
    },
    "landuse_z5_15": {
        "target_name": "landuse", "minzoom": 5, "maxzoom": 15, "geometry": "polygon",
        "attributes": ["class"],
    },
    "landuse_detail_z12_15": {
        "target_name": "landuse", "minzoom": 12, "maxzoom": 15, "geometry": "polygon",
        "attributes": ["class"],
    },
    "aeroway_z10_15": {
        "target_name": "aeroway", "minzoom": 10, "maxzoom": 15, "geometry": "polygon",
        "attributes": ["class"],
    },
    "building_z13_15": {
        "target_name": "building", "minzoom": 13, "maxzoom": 15, "geometry": "polygon",
        "attributes": [],
    },
    "boundary_z0_15": {
        "target_name": "boundary", "minzoom": 0, "maxzoom": 15, "geometry": "line",
        "attributes": ["admin_level", "name", "maritime", "disputed"],
    },
    "place_z0_15": {
        "target_name": "place", "minzoom": 0, "maxzoom": 15, "geometry": "point",
        "attributes": ["name", "class", "rank", "capital", "minzoom"],
        "feature_minzoom": "minzoom",
    },
    "place_detail_z12_15": {
        "target_name": "place", "minzoom": 12, "maxzoom": 15, "geometry": "point",
        "attributes": ["name", "class", "rank", "capital", "minzoom"],
        "feature_minzoom": "minzoom",
    },
    "housenumber_z14_15": {
        "target_name": "housenumber", "minzoom": 14, "maxzoom": 15, "geometry": "point",
        "attributes": ["housenumber"],
    },
    "park_z9_15": {
        "target_name": "park", "minzoom": 9, "maxzoom": 15, "geometry": "polygon",
        "attributes": ["class"],
    },
    "poi_z12_15": {
        "target_name": "poi", "minzoom": 12, "maxzoom": 15, "geometry": "point",
        "attributes": ["name", "class", "subclass"],
    },
}

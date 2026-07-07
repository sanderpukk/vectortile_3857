import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class SchemaTests(unittest.TestCase):
    def _schema(self):
        from vt3857.config import load_config
        from vt3857.schema import schema_yaml

        config = load_config(ROOT / "config" / "settings.py")
        # The schema is emitted as JSON (valid YAML), so json can parse it back.
        return config, json.loads(schema_yaml(config, "/data/basemap.gpkg"))

    def test_schema_source_is_the_preprocessed_geopackage(self):
        _, schema = self._schema()

        self.assertEqual(schema["sources"]["basemap"]["type"], "geopackage")
        self.assertEqual(schema["sources"]["basemap"]["local_path"], "/data/basemap.gpkg")
        # Without the explicit projection Planetiler silently reads 0 features
        # from GDAL-written GeoPackages.
        self.assertEqual(schema["sources"]["basemap"]["projection"], "EPSG:3857")
        self.assertIn("schema_name", schema)
        self.assertIn("attribution", schema)

    def test_layer_ids_are_unique_target_names(self):
        config, schema = self._schema()

        ids = [layer["id"] for layer in schema["layers"]]
        self.assertEqual(len(ids), len(set(ids)))
        expected = {spec["target_name"] for spec in config["layers"].values()}
        self.assertEqual(set(ids), expected)

    def test_every_feature_selects_an_existing_basemap_layer(self):
        config, schema = self._schema()

        source_layers = set(config["layers"])
        for layer in schema["layers"]:
            for feature in layer["features"]:
                self.assertEqual(feature["source"], "basemap")
                match = re.search(r"feature\.source_layer == '([^']+)'", feature["include_when"])
                self.assertIsNotNone(match, feature["include_when"])
                self.assertIn(match.group(1), source_layers)

    def test_place_features_use_per_feature_minzoom(self):
        _, schema = self._schema()

        place = next(layer for layer in schema["layers"] if layer["id"] == "place")
        for feature in place["features"]:
            self.assertEqual(feature["min_zoom"], "${ int(feature.tags.minzoom) }")

    def test_static_zooms_stay_within_webmercator_range(self):
        _, schema = self._schema()

        for layer in schema["layers"]:
            for feature in layer["features"]:
                self.assertLessEqual(feature["max_zoom"], 15)
                if isinstance(feature["min_zoom"], int):
                    self.assertGreaterEqual(feature["min_zoom"], 0)

    def test_transportation_attributes_pass_through(self):
        _, schema = self._schema()

        transportation = next(layer for layer in schema["layers"] if layer["id"] == "transportation")
        line_band = transportation["features"][0]
        keys = [attribute["key"] for attribute in line_band["attributes"]]
        self.assertEqual(keys, ["class", "subclass", "brunnel", "surface", "expressway", "oneway", "ramp", "ref"])
        for attribute in line_band["attributes"]:
            self.assertEqual(attribute["tag_value"], attribute["key"])


if __name__ == "__main__":
    unittest.main()

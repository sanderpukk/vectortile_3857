import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class ConfigAndLayerTests(unittest.TestCase):
    def _config(self):
        from vt3857.config import load_config

        return load_config(ROOT / "config" / "settings.py")

    def test_settings_layers_match_preprocess_layers(self):
        from vt3857.layers import LAYERS as PREPROCESS_LAYERS

        config = self._config()
        settings_names = set(config["layers"])
        preprocess_names = {layer.name for layer in PREPROCESS_LAYERS}

        self.assertEqual(settings_names, preprocess_names)

    def test_zoom_bands_are_within_webmercator_range(self):
        config = self._config()
        mvt = config["mvt"]

        self.assertEqual(mvt["minzoom"], 0)
        self.assertEqual(mvt["maxzoom"], 15)
        for name, spec in config["layers"].items():
            self.assertGreaterEqual(spec["minzoom"], mvt["minzoom"], name)
            self.assertLessEqual(spec["maxzoom"], mvt["maxzoom"], name)
            self.assertLessEqual(spec["minzoom"], spec["maxzoom"], name)

    def test_key_layers_have_expected_bands(self):
        config = self._config()
        layers = config["layers"]

        self.assertEqual(
            {k: layers["transportation_z0_8"][k] for k in ("target_name", "minzoom", "maxzoom", "geometry")},
            {"target_name": "transportation", "minzoom": 0, "maxzoom": 8, "geometry": "line"},
        )
        self.assertEqual(layers["building_z13_15"]["minzoom"], 13)
        self.assertEqual(layers["housenumber_z14_15"]["minzoom"], 14)
        self.assertEqual(layers["housenumber_z14_15"]["maxzoom"], 15)
        self.assertEqual(layers["place_z0_15"]["feature_minzoom"], "minzoom")
        self.assertEqual(layers["place_detail_z12_15"]["feature_minzoom"], "minzoom")
        # Every terminal band must reach the tile maxzoom, otherwise its
        # content would vanish from the deepest tiles that clients overzoom.
        mvt_max = config["mvt"]["maxzoom"]
        top_band_max = max(spec["maxzoom"] for spec in layers.values())
        self.assertEqual(top_band_max, mvt_max)
        for target in {spec["target_name"] for spec in layers.values()}:
            deepest = max(spec["maxzoom"] for spec in layers.values() if spec["target_name"] == target)
            self.assertEqual(deepest, mvt_max, target)

    def test_modes_have_lonlat_bounds(self):
        config = self._config()
        modes = config["modes"]

        self.assertIn("estonia", modes)
        self.assertIn("tallinn", modes)
        for name, mode in modes.items():
            west, south, east, north = mode["bounds"]
            self.assertLess(west, east, name)
            self.assertLess(south, north, name)
            # Sanity: Estonian lon/lat, not projected metres.
            self.assertTrue(20 < west < 30, name)
            self.assertTrue(57 < south < 60, name)

    def test_viewer_config_js_contains_sources_and_layers(self):
        from vt3857.viewer import viewer_config_js

        js = viewer_config_js(self._config())

        self.assertIn("window.VT_PIPELINE_CONFIG", js)
        self.assertIn('"projection": "EPSG:3857"', js)
        self.assertIn('"/tiles/tallinn/{z}/{x}/{y}"', js)
        self.assertIn('"transportation"', js)
        self.assertIn('"attribution"', js)


if __name__ == "__main__":
    unittest.main()

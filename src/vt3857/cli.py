from __future__ import annotations

import argparse
import os
from pathlib import Path

from .config import DEFAULT_CONFIG, load_config
from .generate import generate
from .package import package
from .pipeline import run_all
from .prepare import prepare
from .preprocess import preprocess
from .schema import DEFAULT_BASEMAP, schema_yaml
from .timing import timed_step
from .viewer import write_viewer_config_js


def main() -> None:
    parser = argparse.ArgumentParser(description="Python + Planetiler pipeline for Estonia EPSG:3857 vector tiles")
    parser.add_argument("--config", default=os.environ.get("VT_CONFIG", str(DEFAULT_CONFIG)))
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="download ETAK/EHAK sources")
    p_prepare.add_argument("--sources-dir", default=os.environ.get("SOURCES_DIR", "/data/sources"))

    p_preprocess = sub.add_parser("preprocess", help="build basemap.gpkg in EPSG:3857")
    p_preprocess.add_argument("--sources-dir", default=os.environ.get("SOURCES_DIR", "/data/sources"))
    p_preprocess.add_argument("--output", default=os.environ.get("OUTPUT", "/data/basemap.gpkg"))

    p_generate = sub.add_parser("generate", help="generate a PMTiles archive with Planetiler")
    p_generate.add_argument("--mode", default=os.environ.get("MODE", "estonia"))
    p_generate.add_argument("--data-dir", default=os.environ.get("DATA_DIR", "/data"))
    p_generate.add_argument("--out-dir", default=os.environ.get("OUT_DIR", "/out"))
    p_generate.add_argument("--tmp-dir", default=os.environ.get("TMP_DIR", "/tiletmp"))

    p_package = sub.add_parser("package", help="copy the PMTiles datapackage into the dist dir")
    p_package.add_argument("--mode", default=os.environ.get("MODE", "estonia"))
    p_package.add_argument("--out-dir", default=os.environ.get("OUT_DIR", "/out"))
    p_package.add_argument("--dist-dir", default=os.environ.get("DIST_DIR", "/dist"))

    p_schema = sub.add_parser("schema-yaml", help="print the Planetiler schema generated from Python config")
    p_schema.add_argument("--basemap", default=os.environ.get("BASEMAP", DEFAULT_BASEMAP))

    p_viewer = sub.add_parser("viewer-config", help="write viewer/config.js generated from Python config")
    p_viewer.add_argument("--output", default=os.environ.get("VIEWER_CONFIG", "/app/viewer/config.js"))

    p_run_all = sub.add_parser("run-all", help="run prepare, preprocess, generate, and viewer-config with one total timer")
    p_run_all.add_argument("--mode", default=os.environ.get("MODE", "estonia"))
    p_run_all.add_argument("--sources-dir", default=os.environ.get("SOURCES_DIR", "/data/sources"))
    p_run_all.add_argument("--data-dir", default=os.environ.get("DATA_DIR", "/data"))
    p_run_all.add_argument("--out-dir", default=os.environ.get("OUT_DIR", "/out"))
    p_run_all.add_argument("--tmp-dir", default=os.environ.get("TMP_DIR", "/tiletmp"))
    p_run_all.add_argument("--viewer-config", default=os.environ.get("VIEWER_CONFIG", "/app/viewer/config.js"))

    args = parser.parse_args()
    config_path = Path(args.config)

    if args.command == "prepare":
        with timed_step("prepare"):
            prepare(args.sources_dir)
    elif args.command == "preprocess":
        with timed_step("preprocess"):
            preprocess(args.sources_dir, args.output)
    elif args.command == "generate":
        with timed_step(f"generate {args.mode}"):
            generate(mode=args.mode, config_path=config_path, data_dir=args.data_dir, out_dir=args.out_dir, tmp_dir=args.tmp_dir)
    elif args.command == "package":
        with timed_step(f"package {args.mode}"):
            package(mode=args.mode, config_path=config_path, out_dir=args.out_dir, dist_dir=args.dist_dir)
    elif args.command == "schema-yaml":
        print(schema_yaml(load_config(config_path), args.basemap), end="")
    elif args.command == "viewer-config":
        with timed_step("viewer-config"):
            write_viewer_config_js(load_config(config_path), args.output)
            print(f"Wrote viewer config: {args.output}")
    elif args.command == "run-all":
        run_all(
            mode=args.mode,
            config_path=config_path,
            sources_dir=args.sources_dir,
            data_dir=args.data_dir,
            out_dir=args.out_dir,
            tmp_dir=args.tmp_dir,
            viewer_config=args.viewer_config,
        )

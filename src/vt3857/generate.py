from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .config import load_config
from .gdal import require_file, run
from .schema import write_schema


def generate(
    *,
    mode: str,
    config_path: str | Path,
    data_dir: str | Path,
    out_dir: str | Path,
    tmp_dir: str | Path,
) -> None:
    config = load_config(config_path)
    data_dir = Path(data_dir)
    out_dir = Path(out_dir)
    tmp_dir = Path(tmp_dir)
    basemap = require_file(data_dir / "basemap.gpkg", "run `python -m vt3857 preprocess` first")

    modes = config["modes"]
    if mode not in modes:
        raise SystemExit(f"Unknown mode {mode!r}. Valid modes: {', '.join(sorted(modes))}")

    mode_config = modes[mode]
    output_name = mode_config["output"]
    output = out_dir / f"{output_name}.pmtiles"
    if output.exists():
        print(f"{output} already exists, skipping. Delete it to rebuild.")
        return

    mvt = config["mvt"]
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    jar = os.environ.get("PLANETILER_JAR", "/opt/planetiler.jar")

    # Planetiler wants its layer mapping as a custommap schema. Users edit the
    # Python config; this temporary schema file is only a compatibility bridge.
    with tempfile.TemporaryDirectory(prefix="planetiler-schema-") as schema_tmp:
        schema_path = Path(schema_tmp) / "schema.yml"
        write_schema(config, schema_path, basemap)

        args = [
            "java",
            "-jar",
            jar,
            "generate-custom",
            f"--schema={schema_path}",
            # The .pmtiles extension selects Planetiler's PMTiles archive
            # (single file, tiles gzip-compressed inside), the same output as
            # Lithuania's national-basemap. Martin serves it over HTTP.
            f"--output={output}",
            f"--minzoom={mvt['minzoom']}",
            f"--maxzoom={mvt['maxzoom']}",
            f"--tmpdir={tmp_dir / 'planetiler'}",
            # Only silences disk/RAM headroom warnings: the exists() check
            # above already implements skip-if-present semantics.
            "--force",
        ]
        bounds = mode_config.get("bounds")
        if bounds:
            args.append("--bounds=" + ",".join(str(value) for value in bounds))
        run(args)

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Tiles ready: {output} ({size_mb:.1f} MB)")
    with open(output, "rb") as archive:
        magic = archive.read(7)
    if magic == b"PMTiles":
        print("PMTiles header OK")
    else:
        print(f"WARNING: {output} does not start with the PMTiles magic bytes.")

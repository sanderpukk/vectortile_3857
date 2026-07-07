from __future__ import annotations

import shutil
from pathlib import Path

from .config import load_config
from .gdal import require_file


def package(
    *,
    mode: str,
    config_path: str | Path,
    out_dir: str | Path,
    dist_dir: str | Path,
) -> None:
    config = load_config(config_path)
    modes = config["modes"]
    if mode not in modes:
        raise SystemExit(f"Unknown mode {mode!r}. Valid modes: {', '.join(sorted(modes))}")

    output_name = modes[mode]["output"]
    tiles = require_file(
        Path(out_dir) / f"{output_name}.pmtiles",
        f"run `python -m vt3857 generate --mode {mode}` first",
    )

    dist_dir = Path(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)
    archive = dist_dir / f"{output_name}.pmtiles"
    if archive.exists():
        print(f"{archive} already exists, skipping. Delete it to rebuild.")
        return

    # The PMTiles archive is already a single compressed file, so the
    # datapackage is a plain copy. Copy to a partial name first so a crash
    # mid-copy never leaves a half-written archive in dist.
    dist_partial = archive.with_name(archive.name + ".partial")
    dist_partial.unlink(missing_ok=True)
    shutil.copyfile(tiles, dist_partial)
    dist_partial.replace(archive)

    size_mb = archive.stat().st_size / (1024 * 1024)
    print(f"Datapackage ready: {archive} ({size_mb:.1f} MB)")

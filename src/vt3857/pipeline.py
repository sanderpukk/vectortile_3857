from __future__ import annotations

from pathlib import Path

from .config import load_config
from .generate import generate
from .prepare import prepare
from .preprocess import preprocess
from .timing import timed_step
from .viewer import write_viewer_config_js


def run_all(
    *,
    mode: str,
    config_path: str | Path,
    sources_dir: str | Path,
    data_dir: str | Path,
    out_dir: str | Path,
    tmp_dir: str | Path,
    viewer_config: str | Path,
) -> None:
    config_path = Path(config_path)
    data_dir = Path(data_dir)

    with timed_step("total pipeline"):
        prepare(sources_dir)
        preprocess(sources_dir, data_dir / "basemap.gpkg")
        generate(mode=mode, config_path=config_path, data_dir=data_dir, out_dir=out_dir, tmp_dir=tmp_dir)
        write_viewer_config_js(load_config(config_path), viewer_config)

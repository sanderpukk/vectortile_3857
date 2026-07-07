from __future__ import annotations

import subprocess
from pathlib import Path

from .timing import timed_step


def run(args: list[str], *, cwd: str | Path | None = None) -> None:
    command = " ".join(args)
    with timed_step(command):
        print("+ " + command, flush=True)
        subprocess.run(args, cwd=cwd, check=True)


def ogr2ogr(
    output: str | Path,
    source: str | Path,
    sql: str,
    layer: str,
    *,
    update: bool,
    nlt: str | None = None,
    t_srs: str | None = None,
) -> None:
    args = ["ogr2ogr", "-f", "GPKG"]
    if update:
        args.extend(["-update", "-append"])
    if t_srs:
        args.extend(["-t_srs", t_srs])
    args.extend([str(output), str(source), "-sql", sql, "-nln", layer])
    if nlt:
        args.extend(["-nlt", nlt])
    run(args)


def require_file(path: str | Path, hint: str) -> Path:
    resolved = Path(path)
    if not resolved.exists():
        raise SystemExit(f"Missing {resolved}: {hint}")
    return resolved

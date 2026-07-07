from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_duration(seconds: float) -> str:
    seconds = max(0.0, seconds)
    if seconds < 60:
        return f"{seconds:.1f}s"

    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    return f"{minutes}m {secs}s"


def log(message: str) -> None:
    print(f"[{timestamp()}] {message}", flush=True)


@contextmanager
def timed_step(name: str) -> Iterator[None]:
    start = time.monotonic()
    log(f"START {name}")
    try:
        yield
    finally:
        log(f"END {name} ({format_duration(time.monotonic() - start)})")

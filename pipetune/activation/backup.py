"""Backup and atomic write helpers for activation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import shutil

from pipetune.activation.paths import backup_dir


def create_backup_if_needed(destination: Path) -> Path | None:
    if not destination.exists():
        return None
    directory = backup_dir()
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = directory / f"{timestamp}-{destination.name}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{timestamp}-{counter}-{destination.name}"
        counter += 1
    shutil.copy2(destination, candidate)
    return candidate


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_name(f".{destination.name}.tmp")
    with source.open("rb") as src, temp_path.open("wb") as dst:
        shutil.copyfileobj(src, dst)
        dst.flush()
        os.fsync(dst.fileno())
    temp_path.replace(destination)

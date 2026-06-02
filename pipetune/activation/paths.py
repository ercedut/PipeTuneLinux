"""Runtime paths for user-level PipeTune activation state."""

from __future__ import annotations

import os
from pathlib import Path


def pipetune_home() -> Path | None:
    value = os.environ.get("PIPETUNE_HOME")
    return Path(value).expanduser() if value else None


def user_pipewire_config_dir() -> Path:
    override = pipetune_home()
    if override:
        return override / "config" / "pipewire" / "pipewire.conf.d"
    return Path.home() / ".config" / "pipewire" / "pipewire.conf.d"


def install_state_dir() -> Path:
    override = pipetune_home()
    if override:
        return override / "share" / "pipetune" / "installed-profiles"
    return Path.home() / ".local" / "share" / "pipetune" / "installed-profiles"


def backup_dir() -> Path:
    override = pipetune_home()
    if override:
        return override / "share" / "pipetune" / "backups"
    return Path.home() / ".local" / "share" / "pipetune" / "backups"


def rollback_log_dir() -> Path:
    override = pipetune_home()
    if override:
        return override / "share" / "pipetune" / "rollback-log"
    return Path.home() / ".local" / "share" / "pipetune" / "rollback-log"


def ensure_runtime_dirs() -> None:
    user_pipewire_config_dir().mkdir(parents=True, exist_ok=True)
    install_state_dir().mkdir(parents=True, exist_ok=True)
    backup_dir().mkdir(parents=True, exist_ok=True)
    rollback_log_dir().mkdir(parents=True, exist_ok=True)


def is_within_directory(path: Path, directory: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(directory.resolve(strict=False))
        return True
    except ValueError:
        return False

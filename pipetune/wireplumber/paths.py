"""WirePlumber install path resolution.

All paths respect XDG_CONFIG_HOME and PIPETUNE_HOME environment variables so
that tests and isolated environments can redirect to temporary directories
without touching real user configuration.
"""
from __future__ import annotations

import os
from pathlib import Path

PIPETUNE_RULE_FILENAME_PREFIX = "90-pipetune-"
PIPETUNE_WIREPLUMBER_CONF_SUBDIR = "wireplumber.conf.d"
PIPETUNE_MANIFEST_DIRNAME = "wireplumber-rules"
PIPETUNE_RULE_EXTENSION = ".lua"


def get_xdg_config_home() -> Path:
    """Return XDG_CONFIG_HOME, or ~/.config if unset."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".config"


def get_pipetune_home() -> Path:
    """Return PIPETUNE_HOME for PipeTune state data, or ~/.local/share/pipetune if unset."""
    pipetune_home = os.environ.get("PIPETUNE_HOME")
    if pipetune_home:
        return Path(pipetune_home)
    return Path.home() / ".local" / "share" / "pipetune"


def get_wireplumber_rule_dir() -> Path:
    """Return user-level WirePlumber rule drop-in directory."""
    return get_xdg_config_home() / "wireplumber" / PIPETUNE_WIREPLUMBER_CONF_SUBDIR


def get_manifest_dir() -> Path:
    """Return PipeTune WirePlumber rule manifest directory."""
    return get_pipetune_home() / PIPETUNE_MANIFEST_DIRNAME


def get_manifest_path() -> Path:
    """Return path to the WirePlumber rule manifest JSON file."""
    return get_manifest_dir() / "manifests.json"


def make_rule_filename(install_id: str) -> str:
    """Return the filename for a PipeTune-installed WirePlumber rule."""
    return f"{PIPETUNE_RULE_FILENAME_PREFIX}{install_id}{PIPETUNE_RULE_EXTENSION}"


def is_pipetune_rule_filename(filename: str) -> bool:
    """Return True if the filename looks like a PipeTune-owned rule file."""
    return filename.startswith(PIPETUNE_RULE_FILENAME_PREFIX) and filename.endswith(PIPETUNE_RULE_EXTENSION)


def is_safe_install_path(path: Path) -> bool:
    """Return True iff path is under the allowed user-level WirePlumber rule dir."""
    try:
        path.resolve().relative_to(get_wireplumber_rule_dir().resolve())
        return True
    except ValueError:
        return False

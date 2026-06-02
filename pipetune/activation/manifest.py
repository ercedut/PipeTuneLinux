"""Install manifest persistence."""

from __future__ import annotations

from dataclasses import fields
import hashlib
import json
from pathlib import Path

from pipetune.activation.models import InstallManifest
from pipetune.activation.paths import install_state_dir


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install_manifest_path(install_id: str) -> Path:
    return install_state_dir() / f"{install_id}.json"


def write_install_manifest(manifest: InstallManifest) -> Path:
    path = install_manifest_path(manifest.install_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_install_manifest(path: Path) -> InstallManifest | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    field_names = {field.name for field in fields(InstallManifest)}
    filtered = {key: value for key, value in payload.items() if key in field_names}
    try:
        return InstallManifest(**filtered)
    except TypeError:
        return None


def list_install_manifests() -> list[tuple[Path, InstallManifest]]:
    directory = install_state_dir()
    if not directory.exists():
        return []
    manifests: list[tuple[Path, InstallManifest]] = []
    for path in sorted(directory.glob("*.json")):
        manifest = load_install_manifest(path)
        if manifest is not None:
            manifests.append((path, manifest))
    return manifests


def list_manifest_files() -> list[Path]:
    directory = install_state_dir()
    if not directory.exists():
        return []
    return sorted(directory.glob("*.json"))


def delete_install_manifest(install_id: str) -> bool:
    path = install_manifest_path(install_id)
    if not path.exists():
        return False
    path.unlink()
    return True

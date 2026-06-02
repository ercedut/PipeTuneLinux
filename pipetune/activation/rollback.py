"""Safe rollback for PipeTune-installed profiles."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from pipetune.activation.backup import atomic_copy
from pipetune.activation.installer import MANUAL_RESTART_COMMAND
from pipetune.activation.manifest import list_install_manifests, sha256_file, write_install_manifest
from pipetune.activation.models import InstallManifest, RollbackResult
from pipetune.activation.paths import is_within_directory, rollback_log_dir, user_pipewire_config_dir
from pipetune.activation.state import find_install_manifest


def rollback_profile(*, install_id: str | None = None, latest: bool = False, confirm_rollback: bool = False) -> RollbackResult:
    if not confirm_rollback:
        return _failed(["Rollback requires --confirm-rollback."])

    manifest_path: Path | None = None
    manifest: InstallManifest | None = None
    if latest:
        selected = _latest_active_manifest()
        if selected is not None:
            manifest_path, manifest = selected
    elif install_id:
        selected = find_install_manifest(install_id)
        if selected is not None:
            manifest_path, manifest = selected
    else:
        return _failed(["Rollback requires an install ID or --latest."])

    if manifest_path is None or manifest is None:
        if install_id:
            return _failed([f"Unknown install ID: {install_id}"])
        return _failed(["Install manifest not found."])
    if manifest.rollback_status != "active":
        return _failed([f"Install {manifest.install_id} is already rolled back."])

    installed_path = Path(manifest.installed_config_path)
    if not _is_pipetune_owned_install_path(installed_path):
        return _failed(["Installed config path is not a PipeTune-owned user-level config path."])
    if not installed_path.exists():
        return _failed([f"Installed config file is missing: {installed_path}"])

    current_hash = sha256_file(installed_path)
    if current_hash != manifest.installed_sha256:
        return _failed(["Installed config checksum mismatch; rollback refused to avoid deleting user-modified files."])

    backup_path = Path(manifest.backup_path) if manifest.backup_path else None
    restored_backup = False
    if backup_path and backup_path.exists():
        atomic_copy(backup_path, installed_path)
        restored_backup = True
    else:
        installed_path.unlink()

    manifest.rollback_status = "rolled_back"
    write_install_manifest(manifest)
    log_path = _write_rollback_log(manifest, restored_backup)

    return RollbackResult(
        success=True,
        exit_code=0,
        install_id=manifest.install_id,
        removed_config_path=str(installed_path),
        restored_backup=restored_backup,
        rollback_log_path=str(log_path),
    )


def render_rollback_result(result: RollbackResult) -> str:
    if not result.success:
        lines = ["PipeTune Profile Rollback", "", "Rollback refused:"]
        lines.extend(f"* {error}" for error in result.errors)
        lines.extend(["", "No system configuration was modified."])
        return "\n".join(lines)

    lines = [
        "PipeTune Profile Rollback",
        "",
        f"Rolled back install ID: {result.install_id}",
        f"Removed installed config: {result.removed_config_path}",
        f"Restored backup: {'yes' if result.restored_backup else 'no'}",
        f"Rollback log: {result.rollback_log_path}",
        "",
        "Manual restart recommended:",
        MANUAL_RESTART_COMMAND,
        "",
        "User-level configuration was modified.",
        "No system-level configuration was modified.",
        "No services were restarted automatically.",
    ]
    return "\n".join(lines)


def _latest_active_manifest() -> tuple[Path, InstallManifest] | None:
    active = [(path, manifest) for path, manifest in list_install_manifests() if manifest.rollback_status == "active"]
    if not active:
        return None
    return sorted(active, key=lambda item: item[1].installed_at)[-1]


def _is_pipetune_owned_install_path(path: Path) -> bool:
    return (
        is_within_directory(path, user_pipewire_config_dir())
        and path.name.startswith("90-pipetune-")
        and path.suffix == ".conf"
    )


def _write_rollback_log(manifest: InstallManifest, restored_backup: bool) -> Path:
    directory = rollback_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{manifest.install_id}.json"
    payload = {
        "install_id": manifest.install_id,
        "rolled_back_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "installed_config_path": manifest.installed_config_path,
        "restored_backup": restored_backup,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _failed(errors: list[str]) -> RollbackResult:
    return RollbackResult(
        success=False,
        exit_code=1,
        install_id=None,
        removed_config_path=None,
        restored_backup=False,
        rollback_log_path=None,
        errors=errors,
    )

"""Safe user-level profile installer."""

from __future__ import annotations

from datetime import datetime, timezone
import getpass
import re
from pathlib import Path

from pipetune import __version__
from pipetune.activation.backup import atomic_copy, create_backup_if_needed
from pipetune.activation.manifest import sha256_file, write_install_manifest
from pipetune.activation.models import InstallDryRun, InstallManifest, InstallResult
from pipetune.activation.paths import ensure_runtime_dirs, install_state_dir, is_within_directory, user_pipewire_config_dir
from pipetune.activation.state import active_duplicate_for
from pipetune.safety.manifest import load_manifest_for_config
from pipetune.safety.preflight import run_profile_preflight

MANUAL_RESTART_COMMAND = "systemctl --user restart pipewire pipewire-pulse wireplumber"


def safe_profile_id(raw: str) -> str:
    if raw.endswith(".filter-chain"):
        raw = raw[: -len(".filter-chain")]
    slug = raw.strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9_-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-_")
    return slug or "profile"


def destination_for_profile(profile_id: str) -> Path:
    safe_id = safe_profile_id(profile_id)
    return user_pipewire_config_dir() / f"90-pipetune-{safe_id}.conf"


def run_install_dry_run(config_file: Path, *, user_level: bool) -> InstallDryRun:
    manifest = load_manifest_for_config(config_file)
    profile = manifest.get("profile", {}) if isinstance(manifest, dict) else {}
    profile_id = safe_profile_id(str(profile.get("profile_id") or config_file.stem))
    destination = destination_for_profile(profile_id)
    preflight = run_profile_preflight(config_file)
    hardware_confirmation_required = preflight.readiness.status == "requires_confirmation"

    errors: list[str] = []
    if not user_level:
        errors.append("Install requires --user.")
    if manifest is None:
        errors.append("Manifest missing. Run `pipetune profile manifest ...` before installation.")
    if preflight.readiness.status in {"blocked", "unknown"}:
        errors.append(f"Preflight status is {preflight.readiness.status}; install is not allowed.")

    return InstallDryRun(
        source_config_path=str(config_file),
        destination_path=str(destination),
        manifest_path=str(install_state_dir() / "<install_id>.json"),
        backup_would_be_created=destination.exists(),
        preflight_status=preflight.readiness.status,
        hardware_quirk_confirmation_required=hardware_confirmation_required,
        install_allowed_with_current_flags=not errors and preflight.readiness.status == "ready",
        errors=errors,
        warnings=list(preflight.readiness.warnings),
    )


def install_profile(
    config_file: Path,
    *,
    user_level: bool,
    confirm_install: bool,
    confirm_hardware_quirk: bool,
) -> InstallResult:
    if not user_level:
        return _failed(["Install requires --user."])
    if not confirm_install:
        return _failed(["Install requires --confirm-install."])
    if not config_file.exists() or not config_file.is_file():
        return _failed([f"Config file not found: {config_file}"])

    manifest_payload = load_manifest_for_config(config_file)
    if manifest_payload is None:
        return _failed(["Manifest missing. Run `pipetune profile manifest ...` before installation."])

    preflight = run_profile_preflight(config_file)
    preflight_status = preflight.readiness.status
    if preflight_status == "blocked":
        return _failed(["Preflight status is blocked; install refused."], preflight_status=preflight_status)
    if preflight_status == "unknown":
        return _failed(["Preflight status is unknown; install refused."], preflight_status=preflight_status)
    if preflight_status == "requires_confirmation" and not confirm_hardware_quirk:
        return _failed(
            ["Hardware quirk detected. Re-run with --confirm-hardware-quirk after verifying physical output target."],
            preflight_status=preflight_status,
            warnings=["Hardware quirk detected. Verify physical output target manually before restarting PipeWire."],
        )

    profile = manifest_payload.get("profile", {}) if isinstance(manifest_payload, dict) else {}
    profile_name = str(profile.get("profile_name") or config_file.stem)
    profile_id = safe_profile_id(str(profile.get("profile_id") or profile_name))
    destination = destination_for_profile(profile_id)
    source_hash = sha256_file(config_file)

    duplicate = active_duplicate_for(profile_id, source_hash)
    if duplicate is not None:
        return _failed(
            [
                f"Profile is already installed and active: {duplicate.install_id}",
                "Duplicate install refused; existing active manifest remains unchanged.",
            ],
            preflight_status=preflight_status,
        )

    if not is_within_directory(destination, user_pipewire_config_dir()):
        return _failed(["Destination path is outside the user-level PipeWire config directory."])

    ensure_runtime_dirs()
    backup_path = create_backup_if_needed(destination)
    atomic_copy(config_file, destination)

    installed_hash = sha256_file(destination)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    install_id = f"{timestamp}-{profile_id}"
    install_manifest = InstallManifest(
        install_id=install_id,
        profile_name=profile_name,
        profile_id=profile_id,
        source_config_path=str(config_file),
        installed_config_path=str(destination),
        backup_path=str(backup_path) if backup_path else None,
        installed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        installed_by=getpass.getuser(),
        pipetune_version=__version__,
        preflight_status=preflight_status,
        hardware_quirk_confirmed=confirm_hardware_quirk,
        user_level=True,
        source_sha256=source_hash,
        installed_sha256=installed_hash,
        manifest_schema_version="1",
        rollback_status="active",
        notes=["User-level PipeWire config installed by PipeTune."],
        warnings=list(preflight.readiness.warnings),
    )
    manifest_path = write_install_manifest(install_manifest)

    warnings = list(preflight.readiness.warnings)
    if preflight_status == "requires_confirmation":
        warnings.append("Hardware quirk detected. Verify physical output target manually before restarting PipeWire.")

    return InstallResult(
        success=True,
        exit_code=0,
        profile_name=profile_name,
        install_id=install_id,
        destination_path=str(destination),
        manifest_path=str(manifest_path),
        backup_path=str(backup_path) if backup_path else None,
        backup_created=backup_path is not None,
        preflight_status=preflight_status,
        hardware_quirk_confirmed=confirm_hardware_quirk,
        warnings=warnings,
    )


def render_install_dry_run(result: InstallDryRun) -> str:
    lines = [
        "PipeTune Profile Install Dry Run",
        "",
        f"Source config: {result.source_config_path}",
        f"Destination: {result.destination_path}",
        f"Install manifest would be created: {result.manifest_path}",
        f"Backup would be created: {'yes' if result.backup_would_be_created else 'no'}",
        f"Preflight status: {result.preflight_status}",
        f"Hardware quirk confirmation required: {'yes' if result.hardware_quirk_confirmation_required else 'no'}",
        f"Install allowed with current flags: {'yes' if result.install_allowed_with_current_flags else 'no'}",
        "",
        "Manual restart command after real install:",
        MANUAL_RESTART_COMMAND,
        "",
        "Rollback command after real install:",
        "pipetune profile rollback <install_id> --confirm-rollback",
    ]
    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"* {warning}" for warning in result.warnings)
    if result.errors:
        lines.extend(["", "Blocking issues:"])
        lines.extend(f"* {error}" for error in result.errors)
    lines.extend(["", "No system configuration was modified."])
    return "\n".join(lines)


def render_install_result(result: InstallResult) -> str:
    if not result.success:
        lines = ["PipeTune Profile Install", "", "Install refused:"]
        lines.extend(f"* {error}" for error in result.errors)
        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"* {warning}" for warning in result.warnings)
        lines.extend(["", "No system configuration was modified."])
        return "\n".join(lines)

    lines = [
        "PipeTune Profile Install",
        "",
        f"Installed profile: {result.profile_name}",
        f"Install ID: {result.install_id}",
        f"Destination: {result.destination_path}",
        f"Manifest: {result.manifest_path}",
        f"Backup: {'created' if result.backup_created else 'not needed'}",
        f"Preflight status: {result.preflight_status}",
        f"Hardware quirk confirmed: {'yes' if result.hardware_quirk_confirmed else 'no'}",
    ]
    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"* {warning}" for warning in result.warnings)
    lines.extend(
        [
            "",
            "Manual restart required:",
            MANUAL_RESTART_COMMAND,
            "",
            "Rollback command:",
            f"pipetune profile rollback {result.install_id} --confirm-rollback",
            "",
            "User-level configuration was modified.",
            "No system-level configuration was modified.",
            "No services were restarted automatically.",
        ]
    )
    return "\n".join(lines)


def _failed(
    errors: list[str],
    *,
    preflight_status: str | None = None,
    warnings: list[str] | None = None,
) -> InstallResult:
    return InstallResult(
        success=False,
        exit_code=1,
        profile_name=None,
        install_id=None,
        destination_path=None,
        manifest_path=None,
        backup_path=None,
        backup_created=False,
        preflight_status=preflight_status,
        hardware_quirk_confirmed=False,
        errors=errors,
        warnings=warnings or [],
    )

"""List and status helpers for installed PipeTune profiles."""

from __future__ import annotations

from pathlib import Path

from pipetune.activation.manifest import list_install_manifests, sha256_file
from pipetune.activation.paths import user_pipewire_config_dir
from pipetune.safety.quirk_status import collect_hardware_quirk_metadata


def render_installed_profiles() -> str:
    manifests = list_install_manifests()
    lines = ["PipeTune Installed Profiles", ""]
    if not manifests:
        lines.extend(["No PipeTune-installed profiles found.", "", "No system configuration was modified."])
        return "\n".join(lines)

    for _path, manifest in manifests:
        lines.extend(
            [
                f"* Install ID: {manifest.install_id}",
                f"  Profile: {manifest.profile_name}",
                f"  Status: {manifest.rollback_status}",
                f"  Config: {manifest.installed_config_path}",
                f"  Installed at: {manifest.installed_at}",
            ]
        )
    lines.extend(["", "No system configuration was modified."])
    return "\n".join(lines)


def render_activation_status() -> str:
    manifests = list_install_manifests()
    active = [manifest for _path, manifest in manifests if manifest.rollback_status == "active"]
    rolled_back = [manifest for _path, manifest in manifests if manifest.rollback_status == "rolled_back"]
    consistency, warnings = _manifest_consistency(manifests)
    quirk = collect_hardware_quirk_metadata()

    lines = [
        "PipeTune Profile Activation Status",
        "",
        f"User-level PipeWire config directory: {user_pipewire_config_dir()}",
        f"Installed profiles: {len(manifests)}",
        f"Active profiles: {len(active)}",
        f"Rolled back profiles: {len(rolled_back)}",
        f"Manifest consistency: {consistency}",
        f"Hardware quirk warning: {'yes' if quirk.quirk_detected else 'no'}",
    ]
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"* {warning}" for warning in warnings)
    lines.extend(["", "No system configuration was modified."])
    return "\n".join(lines)


def _manifest_consistency(manifests) -> tuple[str, list[str]]:
    warnings: list[str] = []
    for _path, manifest in manifests:
        installed_path = Path(manifest.installed_config_path)
        if manifest.rollback_status == "active" and not installed_path.exists():
            warnings.append(f"Installed config missing for {manifest.install_id}: {installed_path}")
            continue
        if manifest.rollback_status == "active" and installed_path.exists():
            try:
                if sha256_file(installed_path) != manifest.installed_sha256:
                    warnings.append(f"Installed config checksum mismatch for {manifest.install_id}.")
            except OSError:
                warnings.append(f"Installed config could not be read for {manifest.install_id}.")

    if any("checksum mismatch" in warning for warning in warnings):
        return "fail", warnings
    if warnings:
        return "warn", warnings
    return "pass", warnings

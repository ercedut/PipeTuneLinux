"""Activation state integrity checks."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pipetune.activation.manifest import list_install_manifests, list_manifest_files, load_install_manifest, sha256_file
from pipetune.activation.models import InstallIntegrity, InstallManifest, StateDoctorReport
from pipetune.activation.paths import install_state_dir, is_within_directory, user_pipewire_config_dir


def inspect_install(manifest: InstallManifest) -> InstallIntegrity:
    config_path = Path(manifest.installed_config_path)
    problems: list[str] = []
    config_exists = config_path.exists()
    checksum_state = "missing"

    if config_exists:
        try:
            checksum_state = "valid" if sha256_file(config_path) == manifest.installed_sha256 else "checksum_mismatch"
        except OSError:
            checksum_state = "unreadable"
    elif manifest.rollback_status == "rolled_back":
        checksum_state = "not_applicable"

    if manifest.rollback_status == "active" and not config_exists:
        problems.append("missing_config")
    if manifest.rollback_status == "active" and checksum_state == "checksum_mismatch":
        problems.append("checksum_mismatch")
    if manifest.rollback_status == "rolled_back" and config_exists:
        problems.append("rolled_back_config_present")
    if not _is_manifest_path_user_level(config_path):
        problems.append("invalid_config_path")

    return InstallIntegrity(
        install_id=manifest.install_id,
        profile_id=manifest.profile_id,
        profile_name=manifest.profile_name,
        rollback_status=manifest.rollback_status,
        installed_at=manifest.installed_at,
        installed_config_path=manifest.installed_config_path,
        config_exists=config_exists,
        checksum_state=checksum_state,
        problems=problems,
    )


def build_state_doctor_report() -> StateDoctorReport:
    manifests = list_install_manifests()
    manifest_paths = {path for path, _manifest in manifests}
    corrupted = [str(path) for path in list_manifest_files() if path not in manifest_paths and load_install_manifest(path) is None]
    entries = [inspect_install(manifest) for _path, manifest in manifests]
    active = [manifest for _path, manifest in manifests if manifest.rollback_status == "active"]
    rolled_back = [manifest for _path, manifest in manifests if manifest.rollback_status == "rolled_back"]

    active_config_paths = {str(Path(manifest.installed_config_path).resolve(strict=False)) for manifest in active}
    orphan_configs: list[str] = []
    config_dir = user_pipewire_config_dir()
    if config_dir.exists():
        for path in sorted(config_dir.glob("90-pipetune-*.conf")):
            if str(path.resolve(strict=False)) not in active_config_paths:
                owned_by_rolled_back = any(
                    str(path.resolve(strict=False)) == str(Path(manifest.installed_config_path).resolve(strict=False))
                    for manifest in rolled_back
                )
                if not owned_by_rolled_back:
                    orphan_configs.append(str(path))

    profile_counts = Counter(manifest.profile_id for manifest in active)
    duplicate_profiles = sorted(profile_id for profile_id, count in profile_counts.items() if count > 1)

    missing_config_count = sum(1 for entry in entries if "missing_config" in entry.problems)
    checksum_mismatch_count = sum(1 for entry in entries if "checksum_mismatch" in entry.problems)
    rolled_back_config_present_count = sum(1 for entry in entries if "rolled_back_config_present" in entry.problems)
    duplicate_profile_count = len(duplicate_profiles)

    recommendations: list[str] = []
    if missing_config_count:
        recommendations.append("Mark missing active installs as broken or remove stale manifest entries in a future confirmed repair.")
    if orphan_configs:
        recommendations.append("Remove orphan PipeTune config files only after explicit cleanup confirmation in a future repair flow.")
    if checksum_mismatch_count:
        recommendations.append("Review checksum mismatches manually; do not overwrite automatically.")
    if duplicate_profile_count:
        recommendations.append("Review duplicate active profile manifests before installing again.")
    if rolled_back_config_present_count:
        recommendations.append("Remove rolled-back config files only after verifying they are PipeTune-owned.")

    if checksum_mismatch_count or duplicate_profile_count or corrupted:
        verdict = "fail"
    elif missing_config_count or orphan_configs or rolled_back_config_present_count:
        verdict = "warn"
    else:
        verdict = "pass"

    return StateDoctorReport(
        manifest_path=str(install_state_dir()),
        config_directory=str(config_dir),
        installed_count=len(manifests),
        active_count=len(active),
        rolled_back_count=len(rolled_back),
        missing_config_count=missing_config_count,
        orphan_config_count=len(orphan_configs),
        checksum_mismatch_count=checksum_mismatch_count,
        duplicate_profile_count=duplicate_profile_count,
        corrupted_manifest_count=len(corrupted),
        rolled_back_config_present_count=rolled_back_config_present_count,
        verdict=verdict,
        entries=entries,
        orphan_configs=orphan_configs,
        corrupted_manifests=corrupted,
        duplicate_profiles=duplicate_profiles,
        recommendations=recommendations,
    )


def find_install_manifest(install_id: str) -> tuple[Path, InstallManifest] | None:
    for path, manifest in list_install_manifests():
        if manifest.install_id == install_id:
            return path, manifest
    return None


def active_duplicate_for(profile_id: str, source_sha256: str) -> InstallManifest | None:
    for _path, manifest in list_install_manifests():
        if manifest.rollback_status != "active":
            continue
        if manifest.profile_id == profile_id or manifest.source_sha256 == source_sha256 or manifest.installed_sha256 == source_sha256:
            return manifest
    return None


def render_state_doctor_report(report: StateDoctorReport) -> str:
    lines = [
        "PipeTune Profile State Doctor",
        "",
        f"Manifest path: {report.manifest_path}",
        f"Config directory: {report.config_directory}",
        f"Installed count: {report.installed_count}",
        f"Active count: {report.active_count}",
        f"Rolled back count: {report.rolled_back_count}",
        f"Missing config count: {report.missing_config_count}",
        f"Orphan config count: {report.orphan_config_count}",
        f"Checksum mismatch count: {report.checksum_mismatch_count}",
        f"Duplicate profile count: {report.duplicate_profile_count}",
        f"Corrupted manifest count: {report.corrupted_manifest_count}",
        f"Rolled-back config present count: {report.rolled_back_config_present_count}",
        f"Final verdict: {report.verdict}",
    ]
    if report.orphan_configs:
        lines.extend(["", "Orphan configs:"])
        lines.extend(f"* {path}" for path in report.orphan_configs)
    if report.corrupted_manifests:
        lines.extend(["", "Corrupted manifests:"])
        lines.extend(f"* {path}" for path in report.corrupted_manifests)
    if report.duplicate_profiles:
        lines.extend(["", "Duplicate active profiles:"])
        lines.extend(f"* {profile_id}" for profile_id in report.duplicate_profiles)
    if report.recommendations:
        lines.extend(["", "Recommended actions:"])
        lines.extend(f"* {item}" for item in report.recommendations)
    lines.extend(["", "No system configuration was modified."])
    return "\n".join(lines)


def _is_manifest_path_user_level(path: Path) -> bool:
    return is_within_directory(path, user_pipewire_config_dir()) and path.name.startswith("90-pipetune-")

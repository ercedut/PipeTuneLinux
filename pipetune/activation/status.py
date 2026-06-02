"""List and status helpers for installed PipeTune profiles."""

from __future__ import annotations

from pipetune.activation.manifest import delete_install_manifest, list_install_manifests
from pipetune.activation.paths import user_pipewire_config_dir
from pipetune.activation.state import build_state_doctor_report, find_install_manifest, inspect_install
from pipetune.safety.quirk_status import collect_hardware_quirk_metadata


def render_installed_profiles() -> str:
    manifests = list_install_manifests()
    lines = ["PipeTune Installed Profiles", ""]
    if not manifests:
        lines.extend(["No PipeTune-installed profiles found.", "", "No system configuration was modified."])
        return "\n".join(lines)

    for _path, manifest in manifests:
        integrity = inspect_install(manifest)
        lines.extend(
            [
                f"* Install ID: {manifest.install_id}",
                f"  Profile ID: {manifest.profile_id}",
                f"  Profile: {manifest.profile_name}",
                f"  Status: {manifest.rollback_status}",
                f"  Config exists: {'yes' if integrity.config_exists else 'no'}",
                f"  Checksum state: {integrity.checksum_state}",
                f"  Config: {manifest.installed_config_path}",
                f"  Installed at: {manifest.installed_at}",
            ]
        )
    lines.extend(["", "No system configuration was modified."])
    return "\n".join(lines)


def render_activation_status() -> str:
    report = build_state_doctor_report()
    quirk = collect_hardware_quirk_metadata()

    lines = [
        "PipeTune Profile Activation Status",
        "",
        f"User-level PipeWire config directory: {user_pipewire_config_dir()}",
        f"Installed profiles: {report.installed_count}",
        f"Active profiles: {report.active_count}",
        f"Rolled back profiles: {report.rolled_back_count}",
        f"Missing config profiles: {report.missing_config_count}",
        f"Orphan configs: {report.orphan_config_count}",
        f"Checksum mismatches: {report.checksum_mismatch_count}",
        f"Duplicate profiles: {report.duplicate_profile_count}",
        f"Manifest consistency: {report.verdict}",
        f"Hardware quirk warning: {'yes' if quirk.quirk_detected else 'no'}",
    ]
    if report.recommendations:
        lines.extend(["", "Warnings:"])
        for entry in report.entries:
            if "missing_config" in entry.problems:
                lines.append(f"* Installed config missing for {entry.install_id}: {entry.installed_config_path}")
            if "checksum_mismatch" in entry.problems:
                lines.append(f"* Installed config checksum mismatch for {entry.install_id}.")
        lines.extend(f"* {warning}" for warning in report.recommendations)
    lines.extend(["", "No system configuration was modified."])
    return "\n".join(lines)


def render_verify_install(install_id: str) -> tuple[str, int]:
    selected = find_install_manifest(install_id)
    if selected is None:
        lines = [
            "PipeTune Verify Install",
            "",
            f"Install ID: {install_id}",
            "Status: invalid_id",
            "Errors:",
            f"* Unknown install ID: {install_id}",
            "",
            "No system configuration was modified.",
        ]
        return "\n".join(lines), 1

    _path, manifest = selected
    integrity = inspect_install(manifest)
    failed = bool(integrity.problems)
    lines = [
        "PipeTune Verify Install",
        "",
        f"Install ID: {manifest.install_id}",
        f"Profile ID: {manifest.profile_id}",
        f"Profile: {manifest.profile_name}",
        f"Status: {manifest.rollback_status}",
        f"Config: {manifest.installed_config_path}",
        f"Config exists: {'yes' if integrity.config_exists else 'no'}",
        f"Checksum state: {integrity.checksum_state}",
        f"Integrity: {'fail' if failed else 'pass'}",
    ]
    if integrity.problems:
        lines.extend(["", "Problems:"])
        lines.extend(f"* {problem}" for problem in integrity.problems)
    lines.extend(["", "No system configuration was modified."])
    return "\n".join(lines), 1 if failed else 0


def render_repair_state_dry_run() -> str:
    report = build_state_doctor_report()
    lines = [
        "PipeTune Profile State Repair Dry Run",
        "",
        "Planned actions:",
    ]
    actions: list[str] = []
    for entry in report.entries:
        if "missing_config" in entry.problems:
            actions.append(f"mark missing active install as broken: {entry.install_id}")
        if "rolled_back_config_present" in entry.problems:
            actions.append(f"remove rolled-back config after confirmation: {entry.installed_config_path}")
        if "checksum_mismatch" in entry.problems:
            actions.append(f"review checksum mismatch manually: {entry.install_id}")
    actions.extend(f"remove orphan config after confirmation: {path}" for path in report.orphan_configs)
    actions.extend(f"remove stale/corrupted manifest after confirmation: {path}" for path in report.corrupted_manifests)
    if not actions:
        actions.append("No repair actions proposed.")
    lines.extend(f"* {action}" for action in actions)
    lines.extend(["", "Dry run only. No files were modified.", "No system configuration was modified."])
    return "\n".join(lines)


def cleanup_rolled_back_manifests(*, confirm_cleanup: bool) -> tuple[str, int]:
    if not confirm_cleanup:
        return (
            "\n".join(
                [
                    "PipeTune Cleanup Rolled-Back Profiles",
                    "",
                    "Cleanup refused:",
                    "* Cleanup requires --confirm-cleanup.",
                    "",
                    "No system configuration was modified.",
                ]
            ),
            1,
        )

    removed: list[str] = []
    skipped: list[str] = []
    for _path, manifest in list_install_manifests():
        integrity = inspect_install(manifest)
        if manifest.rollback_status == "rolled_back" and not integrity.config_exists:
            if delete_install_manifest(manifest.install_id):
                removed.append(manifest.install_id)
        else:
            skipped.append(manifest.install_id)

    lines = [
        "PipeTune Cleanup Rolled-Back Profiles",
        "",
        f"Removed manifests: {len(removed)}",
        f"Skipped manifests: {len(skipped)}",
    ]
    if removed:
        lines.extend(["", "Removed:"])
        lines.extend(f"* {install_id}" for install_id in removed)
    lines.extend(["", "User-level PipeTune state was modified." if removed else "No files were modified.", "No system-level configuration was modified."])
    return "\n".join(lines), 0

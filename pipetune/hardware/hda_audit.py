"""Read-only HDA hardware quirk audit."""

from __future__ import annotations

import os
from pathlib import Path

from pipetune.collectors.alsa import collect_alsa_data
from pipetune.hardware.models import HdaAuditResult, PinConfigSnapshot

PROC_ASOUND_DIR = Path("/proc/asound")
SYS_CLASS_SOUND_DIR = Path("/sys/class/sound")
MODPROBE_DIR = Path("/etc/modprobe.d")
FIRMWARE_DIR = Path("/lib/firmware")

DEFAULT_HISTORICAL_ROUTING_ISSUE_NOTED = True

_RETASK_TERMS = ("hda", "snd_hda", "hda-jack-retask", "jack", "retask", "model=")


def _read_snapshot(path: Path) -> PinConfigSnapshot:
    if not path.exists():
        return PinConfigSnapshot(path=str(path), exists=False, readable=False, non_empty=False, error="not found")
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        return PinConfigSnapshot(
            path=str(path),
            exists=True,
            readable=True,
            non_empty=bool(content.strip()),
            error=None,
        )
    except OSError as exc:
        return PinConfigSnapshot(
            path=str(path),
            exists=True,
            readable=False,
            non_empty=False,
            error=str(exc),
        )


def _collect_pin_config_snapshots(sys_class_sound_dir: Path, pin_file_name: str) -> list[PinConfigSnapshot]:
    snapshots: list[PinConfigSnapshot] = []
    for pin_file in sorted(sys_class_sound_dir.glob(f"*/device/{pin_file_name}")):
        snapshots.append(_read_snapshot(pin_file))
    return snapshots


def _search_retask_references(search_dir: Path) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    if not search_dir.exists():
        warnings.append(f"search path skipped (missing): {search_dir}")
        return [], warnings

    hits: list[str] = []
    try:
        for root, dirs, files in os.walk(search_dir, topdown=True, followlinks=False):
            # Skip directory symlinks explicitly to avoid cycles and non-local traversals.
            kept_dirs: list[str] = []
            for directory in dirs:
                full_dir = Path(root) / directory
                if full_dir.is_symlink():
                    continue
                kept_dirs.append(directory)
            dirs[:] = kept_dirs

            for filename in files:
                file_path = Path(root) / filename
                if file_path.is_symlink():
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except OSError as exc:
                    warnings.append(f"search file skipped (unreadable): {file_path} ({exc})")
                    continue

                for line_number, line in enumerate(content.splitlines(), start=1):
                    lowered = line.lower()
                    if any(term in lowered for term in _RETASK_TERMS):
                        hits.append(f"{file_path}:{line_number}:{line.strip()}")
    except OSError as exc:
        warnings.append(f"search path skipped (error): {search_dir} ({exc})")

    return hits, warnings


def _has_non_empty_user_pin_override(snapshots: list[PinConfigSnapshot]) -> bool:
    return any(item.exists and item.readable and item.non_empty for item in snapshots)


def _cannot_read_user_pin_configs(snapshots: list[PinConfigSnapshot]) -> bool:
    if not snapshots:
        return True
    return any(item.exists and not item.readable for item in snapshots)


def _count_card_lines(cards_file: Path) -> int:
    if not cards_file.exists():
        return 0
    try:
        text = cards_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0

    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and stripped[0].isdigit() and "[" in stripped:
            count += 1
    return count


def collect_hda_audit(
    *,
    proc_asound_dir: Path = PROC_ASOUND_DIR,
    sys_class_sound_dir: Path = SYS_CLASS_SOUND_DIR,
    modprobe_dir: Path = MODPROBE_DIR,
    firmware_dir: Path = FIRMWARE_DIR,
    historical_routing_issue_noted: bool = DEFAULT_HISTORICAL_ROUTING_ISSUE_NOTED,
) -> HdaAuditResult:
    codec_files = [str(path) for path in sorted(proc_asound_dir.glob("card*/codec#*"))]

    init_pin_configs = _collect_pin_config_snapshots(sys_class_sound_dir, "init_pin_configs")
    driver_pin_configs = _collect_pin_config_snapshots(sys_class_sound_dir, "driver_pin_configs")
    user_pin_configs = _collect_pin_config_snapshots(sys_class_sound_dir, "user_pin_configs")

    user_pin_overrides_present = None
    if user_pin_configs:
        user_pin_overrides_present = _has_non_empty_user_pin_override(user_pin_configs)

    modprobe_hits, modprobe_warnings = _search_retask_references(modprobe_dir)
    firmware_hits, firmware_warnings = _search_retask_references(firmware_dir)

    retask_reference_hits = modprobe_hits + firmware_hits
    retask_search_errors = modprobe_warnings + firmware_warnings

    manual_hda_retask_detected = bool(
        _has_non_empty_user_pin_override(user_pin_configs)
        or retask_reference_hits
    )

    manual_hda_retask_suspected = bool(
        not manual_hda_retask_detected
        and codec_files
        and historical_routing_issue_noted
        and _cannot_read_user_pin_configs(user_pin_configs)
    )

    if manual_hda_retask_detected or manual_hda_retask_suspected:
        safety = (
            "Manual HDA pin retask detected/suspected. Do not auto-apply speaker/headphone profiles "
            "without manual output confirmation."
        )
    else:
        safety = "No manual HDA retask signal detected from current read-only audit inputs."

    alsa_data = collect_alsa_data()
    alsa_capture_devices_count = len(alsa_data.get("capture_devices", []))
    alsa_cards_count = _count_card_lines(proc_asound_dir / "cards") or len(alsa_data.get("cards", []))

    warnings: list[str] = []
    if retask_search_errors:
        warnings.extend(retask_search_errors)
    if any("unreadable" in warning for warning in retask_search_errors):
        retask_search_status = "completed with skipped unreadable files"
    else:
        retask_search_status = "completed"

    return HdaAuditResult(
        codec_files=codec_files,
        init_pin_configs=init_pin_configs,
        driver_pin_configs=driver_pin_configs,
        user_pin_configs=user_pin_configs,
        user_pin_overrides_present=user_pin_overrides_present,
        retask_reference_hits=retask_reference_hits,
        retask_reference_search_errors=retask_search_errors,
        retask_reference_search_status=retask_search_status,
        alsa_cards_count=alsa_cards_count,
        alsa_capture_devices_count=alsa_capture_devices_count,
        ucm2_directory_exists=bool(alsa_data.get("ucm2_directory", {}).get("exists", False)),
        manual_hda_retask_detected=manual_hda_retask_detected,
        manual_hda_retask_suspected=manual_hda_retask_suspected,
        safety_recommendation=safety,
        warnings=warnings,
    )


def render_hda_audit_summary(result: HdaAuditResult) -> str:
    if result.manual_hda_retask_detected:
        quirk_status = "detected"
    elif result.manual_hda_retask_suspected:
        quirk_status = "suspected"
    else:
        quirk_status = "not detected"

    if result.user_pin_overrides_present is True:
        user_pin_state = "detected"
    elif result.user_pin_overrides_present is False:
        user_pin_state = "not detected"
    else:
        user_pin_state = "unknown"

    lines = [
        "PipeTune HDA Hardware Audit",
        f"- HDA codec files: {'found' if result.codec_files else 'not found'}",
        f"- init_pin_configs files: {'found' if result.init_pin_configs else 'not found'}",
        f"- driver_pin_configs files: {'found' if result.driver_pin_configs else 'not found'}",
        f"- user_pin_configs files: {'found' if result.user_pin_configs else 'not found'}",
        f"- User pin overrides: {user_pin_state}",
        f"- hda-jack-retask references: {'detected' if result.retask_reference_hits else 'not detected'}",
        f"- Retask reference search: {result.retask_reference_search_status}",
        f"- ALSA cards: {result.alsa_cards_count}",
        f"- UCM2 directory: {'found' if result.ucm2_directory_exists else 'not found'}",
        f"- Hardware quirk status: {quirk_status}",
        f"- Safety recommendation: {result.safety_recommendation}",
    ]

    if result.warnings:
        lines.append(f"- Search warnings: {len(result.warnings)} non-fatal warning(s)")

    return "\n".join(lines)

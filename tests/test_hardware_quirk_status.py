from __future__ import annotations

from pipetune import cli
from pipetune.hardware.models import HdaAuditResult
from pipetune.safety.quirk_status import collect_hardware_quirk_metadata


def _hda_result(*, detected: bool = False, suspected: bool = False) -> HdaAuditResult:
    return HdaAuditResult(
        codec_files=["/proc/asound/card0/codec#0"],
        init_pin_configs=[],
        driver_pin_configs=[],
        user_pin_configs=[],
        user_pin_overrides_present=None,
        retask_reference_hits=["/etc/modprobe.d/hda.conf:1:hda-jack-retask"] if detected else [],
        retask_reference_search_errors=[],
        retask_reference_search_status="completed",
        retask_files_scanned=1,
        retask_files_skipped=0,
        alsa_cards_count=1,
        alsa_capture_devices_count=1,
        ucm2_directory_exists=True,
        manual_hda_retask_detected=detected,
        manual_hda_retask_suspected=suspected,
        safety_recommendation="safe",
        warnings=[],
    )


def test_quirk_status_command_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["hardware", "quirk-status"])

    assert args.command == "hardware"
    assert args.hardware_command == "quirk-status"


def test_quirk_status_requires_manual_confirmation_when_hda_retask_detected(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("pipetune.safety.quirk_status.collect_hda_audit", lambda: _hda_result(detected=True))

    metadata = collect_hardware_quirk_metadata(tmp_path / "missing-status.json")

    assert metadata.quirk_detected is True
    assert metadata.quirk_type == "manual_hda_pin_retask"
    assert metadata.auto_switch_safe is False
    assert metadata.requires_manual_output_confirmation is True

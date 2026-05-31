from __future__ import annotations

from pathlib import Path

from pipetune import cli
from pipetune.hardware.models import HdaAuditResult, MicAuditResult
from pipetune.hardware.quirk_report import QuirkReportResult


def test_hardware_command_group_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["hardware", "hda-audit"])
    assert args.command == "hardware"
    assert args.hardware_command == "hda-audit"


def test_hardware_hda_audit_command_returns_success(monkeypatch) -> None:
    fake_result = HdaAuditResult(
        codec_files=[],
        init_pin_configs=[],
        driver_pin_configs=[],
        user_pin_configs=[],
        user_pin_overrides_present=None,
        retask_reference_hits=[],
        retask_reference_search_errors=[],
        retask_reference_search_status="completed",
        retask_files_scanned=0,
        retask_files_skipped=0,
        alsa_cards_count=1,
        alsa_capture_devices_count=1,
        ucm2_directory_exists=True,
        manual_hda_retask_detected=False,
        manual_hda_retask_suspected=False,
        safety_recommendation="safe",
        warnings=[],
    )

    monkeypatch.setattr("pipetune.cli.collect_hda_audit", lambda: fake_result)
    monkeypatch.setattr("pipetune.cli.render_hda_audit_summary", lambda _result: "summary")

    assert cli.main(["hardware", "hda-audit"]) == 0


def test_hardware_mic_audit_command_returns_success(monkeypatch) -> None:
    fake_result = MicAuditResult(
        alsa_capture_devices_count=1,
        source_count=1,
        default_source="alsa_input.test",
        default_source_muted=False,
        default_source_state="RUNNING",
        internal_mic_route_visible="yes",
        capture_test_performed=False,
        microphone_status="visible",
        safety_recommendation="safe",
        warnings=[],
    )

    monkeypatch.setattr("pipetune.cli.collect_mic_audit", lambda: fake_result)
    monkeypatch.setattr("pipetune.cli.render_mic_audit_summary", lambda _result: "summary")

    assert cli.main(["hardware", "mic-audit"]) == 0


def test_hardware_quirk_report_creates_expected_paths(monkeypatch, tmp_path: Path) -> None:
    output_dir = tmp_path / "report"

    def fake_create_quirk_report(output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_dir = output_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        readme = output_dir / "README.md"
        summary = output_dir / "PUBLIC_SUMMARY.md"
        fix_plan = output_dir / "FIX_PLAN.md"
        readme.write_text("# test\n", encoding="utf-8")
        summary.write_text("# test\n", encoding="utf-8")
        fix_plan.write_text("# test\n", encoding="utf-8")
        return QuirkReportResult(
            output_dir=output_dir,
            raw_dir=raw_dir,
            readme_path=readme,
            fix_plan_path=fix_plan,
            public_summary_path=summary,
        )

    monkeypatch.setattr("pipetune.cli.create_quirk_report", fake_create_quirk_report)

    assert cli.main(["hardware", "quirk-report", "--output", str(output_dir)]) == 0
    assert (output_dir / "README.md").exists()
    assert (output_dir / "FIX_PLAN.md").exists()
    assert (output_dir / "PUBLIC_SUMMARY.md").exists()

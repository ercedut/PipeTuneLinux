from __future__ import annotations

from pathlib import Path

from pipetune.models import CommandResult
from pipetune.hardware.quirk_report import create_quirk_report


def _cmd(stdout: str = "", stderr: str = "", available: bool = True, exit_code: int | None = 0) -> CommandResult:
    return CommandResult(
        command="mock",
        available=available,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=False,
        error=None if available else "command not found",
    )


def test_raw_audit_files_are_placed_under_raw(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pipetune.hardware.quirk_report.run_command", lambda *args, **kwargs: _cmd(stdout="ok\n"))
    monkeypatch.setattr(
        "pipetune.hardware.quirk_report.collect_hda_audit",
        lambda **kwargs: type("HDA", (), {
            "manual_hda_retask_detected": True,
            "manual_hda_retask_suspected": False,
            "retask_reference_hits": ["/etc/modprobe.d/x.conf:1:hda-jack-retask"],
            "retask_reference_search_errors": [],
        })(),
    )
    monkeypatch.setattr(
        "pipetune.hardware.quirk_report.collect_mic_audit",
        lambda: type("MIC", (), {"internal_mic_route_visible": "yes"})(),
    )

    out = tmp_path / "audit"
    result = create_quirk_report(out)

    assert result.raw_dir == out / "raw"
    assert (out / "raw" / "wpctl-status.txt").exists()
    assert (out / "raw" / "hda-retask-search.txt").exists()


def test_public_reports_created_and_no_raw_dump_embedded(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pipetune.hardware.quirk_report.run_command", lambda *args, **kwargs: _cmd(stdout="sensitive raw output\n"))
    monkeypatch.setattr(
        "pipetune.hardware.quirk_report.collect_hda_audit",
        lambda **kwargs: type("HDA", (), {
            "manual_hda_retask_detected": True,
            "manual_hda_retask_suspected": False,
            "retask_reference_hits": ["/etc/modprobe.d/x.conf:1:hda-jack-retask"],
            "retask_reference_search_errors": [],
        })(),
    )
    monkeypatch.setattr(
        "pipetune.hardware.quirk_report.collect_mic_audit",
        lambda: type("MIC", (), {"internal_mic_route_visible": "yes"})(),
    )

    out = tmp_path / "audit"
    create_quirk_report(out)

    readme = (out / "README.md").read_text(encoding="utf-8")
    fix_plan = (out / "FIX_PLAN.md").read_text(encoding="utf-8")
    summary = (out / "PUBLIC_SUMMARY.md").read_text(encoding="utf-8")

    assert (out / "README.md").exists()
    assert (out / "FIX_PLAN.md").exists()
    assert (out / "PUBLIC_SUMMARY.md").exists()
    assert "stdout:" not in readme
    assert "sensitive raw output" not in readme
    assert "raw/" in readme
    assert "No system audio configuration was modified" in summary
    assert "MANUAL / DO NOT RUN WITHOUT CONFIRMATION" in fix_plan


def test_existing_top_level_raw_files_moved_into_raw(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pipetune.hardware.quirk_report.run_command", lambda *args, **kwargs: _cmd(stdout="ok\n"))
    monkeypatch.setattr(
        "pipetune.hardware.quirk_report.collect_hda_audit",
        lambda **kwargs: type("HDA", (), {
            "manual_hda_retask_detected": False,
            "manual_hda_retask_suspected": True,
            "retask_reference_hits": [],
            "retask_reference_search_errors": [],
        })(),
    )
    monkeypatch.setattr(
        "pipetune.hardware.quirk_report.collect_mic_audit",
        lambda: type("MIC", (), {"internal_mic_route_visible": "unknown"})(),
    )

    out = tmp_path / "audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "wpctl-status.txt").write_text("old\n", encoding="utf-8")
    (out / "hda-codec-files").mkdir(parents=True, exist_ok=True)
    (out / "hda-codec-files" / "old.txt").write_text("legacy\n", encoding="utf-8")

    create_quirk_report(out)

    assert not (out / "wpctl-status.txt").exists()
    assert (out / "raw" / "wpctl-status.txt").exists()
    assert (out / "raw" / "hda-codec-files").exists()


def test_gitignore_contains_raw_audit_ignore_rules() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "docs/system-audits/**/raw/" in gitignore
    assert "docs/system-audits/**/*.txt" in gitignore
    assert "docs/system-audits/**/hda-codec-files/" in gitignore
    assert "!docs/system-audits/**/README.md" in gitignore
    assert "!docs/system-audits/**/FIX_PLAN.md" in gitignore
    assert "!docs/system-audits/**/PUBLIC_SUMMARY.md" in gitignore

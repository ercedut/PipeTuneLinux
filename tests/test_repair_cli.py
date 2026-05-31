from __future__ import annotations

from pipetune import cli


def test_repair_command_group_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["repair", "hda-plan"])

    assert args.command == "repair"
    assert args.repair_command == "hda-plan"


def test_repair_hda_plan_command_returns_success(monkeypatch) -> None:
    monkeypatch.setattr("pipetune.cli.build_repair_context", lambda: object())
    monkeypatch.setattr("pipetune.cli.render_hda_plan", lambda _ctx: "plan")

    assert cli.main(["repair", "hda-plan"]) == 0


def test_repair_backup_plan_command_returns_success(monkeypatch) -> None:
    monkeypatch.setattr("pipetune.cli.render_backup_plan", lambda: "backup")

    assert cli.main(["repair", "backup-plan"]) == 0


def test_repair_mic_test_plan_command_returns_success(monkeypatch) -> None:
    monkeypatch.setattr("pipetune.cli.render_mic_test_plan", lambda: "mic")

    assert cli.main(["repair", "mic-test-plan"]) == 0


def test_repair_checklist_includes_stop_conditions() -> None:
    output = cli.render_repair_checklist()

    assert "Stop conditions:" in output
    assert "speaker output regresses" in output

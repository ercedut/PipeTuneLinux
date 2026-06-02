from __future__ import annotations

from pipetune import cli


def test_repair_gain_plan_command_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["repair", "gain-plan"])

    assert args.command == "repair"
    assert args.repair_command == "gain-plan"


def test_repair_gain_matrix_command_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["repair", "gain-matrix"])

    assert args.command == "repair"
    assert args.repair_command == "gain-matrix"


def test_repair_gain_plan_command_returns_success(monkeypatch) -> None:
    monkeypatch.setattr("pipetune.cli.collect_gain_audit", lambda: None)
    monkeypatch.setattr("pipetune.cli.render_gain_plan", lambda _audit: "plan")

    assert cli.main(["repair", "gain-plan"]) == 0


def test_repair_gain_matrix_command_returns_success(monkeypatch) -> None:
    monkeypatch.setattr("pipetune.cli.render_gain_matrix", lambda: "matrix")

    assert cli.main(["repair", "gain-matrix"]) == 0

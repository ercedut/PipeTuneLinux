from __future__ import annotations

from pathlib import Path

from pipetune import cli


def test_measure_command_group_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["measure", "generate-sweep", "--output", "out.wav"])

    assert args.command == "measure"
    assert args.measure_command == "generate-sweep"


def test_measure_compare_cli_writes_report(tmp_path, capsys) -> None:
    output = tmp_path / "comparison.json"

    exit_code = cli.main(
        [
            "measure",
            "compare-response",
            "--before",
            "tests/fixtures/measurement/before.csv",
            "--after",
            "tests/fixtures/measurement/after.csv",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output.exists()
    assert "Flatter by variance: true" in captured.out


def test_measure_generate_correction_cli_requires_safe(tmp_path, capsys) -> None:
    output = tmp_path / "draft.toml"

    exit_code = cli.main(
        [
            "measure",
            "generate-correction",
            "--input",
            str(Path("tests/fixtures/measurement/before.csv")),
            "--output",
            str(output),
            "--target",
            "flat",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "requires --safe" in captured.out
    assert not output.exists()


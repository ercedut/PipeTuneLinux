from __future__ import annotations

import json
from pathlib import Path

from pipetune import cli
from pipetune.measurement.response import validate_response_csv


def test_response_validation_pass_warn_and_fail() -> None:
    flat = validate_response_csv(Path("tests/fixtures/measurement/flat.csv"))
    noisy = validate_response_csv(Path("tests/fixtures/measurement/noisy.csv"))
    malformed = validate_response_csv(Path("tests/fixtures/measurement/malformed.csv"))

    assert flat.measurement_quality == "pass"
    assert noisy.measurement_quality == "warn"
    assert "large_magnitude_jump" in noisy.quality_flags
    assert malformed.measurement_quality == "fail"
    assert malformed.errors


def test_response_validation_detects_too_few_narrow_unsorted_and_duplicates(tmp_path) -> None:
    unsorted = tmp_path / "unsorted.csv"
    duplicate = tmp_path / "duplicate.csv"
    unsorted.write_text(
        "freq_hz,magnitude_db\n1000,0\n20,0\n100,0\n500,0\n2000,0\n20000,0\n",
        encoding="utf-8",
    )
    duplicate.write_text(
        "freq_hz,magnitude_db\n20,0\n20,1\n100,0\n1000,0\n10000,0\n20000,0\n",
        encoding="utf-8",
    )

    too_few = validate_response_csv(Path("tests/fixtures/measurement/too_few.csv"))
    narrow = validate_response_csv(Path("tests/fixtures/measurement/narrow.csv"))
    unsorted_report = validate_response_csv(unsorted)
    duplicate_report = validate_response_csv(duplicate)

    assert too_few.measurement_quality == "fail"
    assert "too_few_points" in too_few.quality_flags
    assert narrow.measurement_quality == "fail"
    assert "narrow_coverage" in narrow.quality_flags
    assert unsorted_report.measurement_quality == "warn"
    assert "unsorted" in unsorted_report.quality_flags
    assert duplicate_report.measurement_quality == "fail"
    assert "duplicate_frequencies" in duplicate_report.quality_flags


def test_validate_response_cli_human_and_json(capsys) -> None:
    exit_code = cli.main(["measure", "validate-response", "--input", "tests/fixtures/measurement/flat.csv"])
    human = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune Response Validation" in human
    assert "Verdict: pass" in human

    exit_code = cli.main(["measure", "validate-response", "--input", "tests/fixtures/measurement/flat.csv", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert data["measurement_quality"] == "pass"


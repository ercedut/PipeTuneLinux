from __future__ import annotations

import json

import pytest

from pipetune.measurement import MeasurementError
from pipetune.measurement.rew import import_rew_csv


def test_rew_import_accepts_common_column_names(tmp_path) -> None:
    source = tmp_path / "rew.csv"
    output = tmp_path / "normalized.csv"
    source.write_text("Freq,SPL\n20,-3\n100,1.5\n1000,0\n", encoding="utf-8")

    metadata = import_rew_csv(source, output)

    assert output.read_text(encoding="utf-8").splitlines()[0] == "freq_hz,magnitude_db"
    assert metadata["row_count"] == 3
    sidecar = json.loads(output.with_suffix(output.suffix + ".json").read_text(encoding="utf-8"))
    assert sidecar["source_format"] == "REW"
    assert sidecar["detected_frequency_column"] == "Freq"
    assert sidecar["detected_magnitude_column"] == "SPL"
    assert sidecar["skipped_row_count"] == 0
    assert sidecar["min_freq_hz"] == 20
    assert sidecar["max_freq_hz"] == 1000


def test_malformed_rew_csv_fails_cleanly(tmp_path) -> None:
    source = tmp_path / "bad.csv"
    output = tmp_path / "normalized.csv"
    source.write_text("name,value\nbad,data\n", encoding="utf-8")

    with pytest.raises(MeasurementError, match="frequency and magnitude"):
        import_rew_csv(source, output)


def test_rew_import_accepts_column_variants_and_decimal_comma(tmp_path) -> None:
    variants = [
        ("Frequency,dB\n20,-3\n100,1\n", "Frequency", "dB"),
        ("Hz,Magnitude\n20,\"-3,5\"\n100,\"1,25\"\n", "Hz", "Magnitude"),
    ]
    for index, (text, frequency_column, magnitude_column) in enumerate(variants):
        source = tmp_path / f"rew-{index}.csv"
        output = tmp_path / f"normalized-{index}.csv"
        source.write_text(text, encoding="utf-8")

        metadata = import_rew_csv(source, output)

        assert metadata["detected_frequency_column"] == frequency_column
        assert metadata["detected_magnitude_column"] == magnitude_column
        assert metadata["row_count"] == 2


def test_rew_import_reports_skipped_rows_and_rejects_bad_numeric_data(tmp_path) -> None:
    source = tmp_path / "skipped.csv"
    output = tmp_path / "normalized.csv"
    source.write_text("Frequency,dB\n20,-3\n,\n100,1\n", encoding="utf-8")

    metadata = import_rew_csv(source, output)
    assert metadata["skipped_row_count"] == 1
    assert metadata["warnings"]

    bad_freq = tmp_path / "bad-freq.csv"
    bad_freq.write_text("Frequency,dB\n0,-3\n100,1\n", encoding="utf-8")
    with pytest.raises(MeasurementError, match="frequency must be positive"):
        import_rew_csv(bad_freq, output)

    bad_mag = tmp_path / "bad-mag.csv"
    bad_mag.write_text("Frequency,dB\n20,nope\n100,1\n", encoding="utf-8")
    with pytest.raises(MeasurementError, match="invalid magnitude"):
        import_rew_csv(bad_mag, output)

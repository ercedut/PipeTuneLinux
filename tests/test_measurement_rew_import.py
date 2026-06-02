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
    assert sidecar["min_freq_hz"] == 20
    assert sidecar["max_freq_hz"] == 1000


def test_malformed_rew_csv_fails_cleanly(tmp_path) -> None:
    source = tmp_path / "bad.csv"
    output = tmp_path / "normalized.csv"
    source.write_text("name,value\nbad,data\n", encoding="utf-8")

    with pytest.raises(MeasurementError, match="frequency and magnitude"):
        import_rew_csv(source, output)


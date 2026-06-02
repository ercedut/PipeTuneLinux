from __future__ import annotations

from pathlib import Path

import pytest

from pipetune.measurement import MeasurementError
from pipetune.measurement.correction import generate_correction_draft


def test_generate_correction_creates_conservative_draft_toml(tmp_path) -> None:
    output = tmp_path / "correction-draft.toml"

    generate_correction_draft(Path("tests/fixtures/measurement/before.csv"), output, target="flat", safe=True)

    text = output.read_text(encoding="utf-8")
    assert 'status = "draft"' in text
    assert 'profile_type = "laptop-speaker"' in text
    assert "WARNING: draft correction only" in text
    assert "max_boost_db = 3" in text
    assert 'type = "high_pass"' in text
    assert "preamp_headroom_db = -" in text


def test_generate_correction_refuses_unsafe_boost(tmp_path) -> None:
    source = tmp_path / "unsafe.csv"
    output = tmp_path / "correction-draft.toml"
    source.write_text(
        "freq_hz,magnitude_db\n100,-20\n160,-20\n250,0\n500,0\n1000,0\n2000,0\n",
        encoding="utf-8",
    )

    with pytest.raises(MeasurementError, match="Unsafe correction"):
        generate_correction_draft(source, output, target="flat", safe=True)


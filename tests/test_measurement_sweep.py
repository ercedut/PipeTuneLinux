from __future__ import annotations

import json
import wave

import pytest

from pipetune.measurement import MeasurementError
from pipetune.measurement.sweep import generate_log_sweep, metadata_path_for_wav


def test_generate_sweep_creates_valid_wav_and_metadata(tmp_path) -> None:
    output = tmp_path / "log-sweep.wav"

    generate_log_sweep(output, duration_seconds=1, sample_rate=8000, start_hz=100, end_hz=3000, amplitude=0.3)

    with wave.open(str(output), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 8000
        assert wav_file.getnframes() == 8000

    metadata = json.loads(metadata_path_for_wav(output).read_text(encoding="utf-8"))
    assert metadata["sample_rate"] == 8000
    assert metadata["duration_seconds"] == 1
    assert metadata["start_hz"] == 100
    assert metadata["end_hz"] == 3000
    assert metadata["amplitude"] == 0.3
    assert "playback volume" in metadata["warning"]


def test_unsafe_amplitude_is_rejected(tmp_path) -> None:
    with pytest.raises(MeasurementError, match="Unsafe amplitude"):
        generate_log_sweep(tmp_path / "bad.wav", amplitude=0.91)


def test_invalid_frequency_range_is_rejected(tmp_path) -> None:
    with pytest.raises(MeasurementError, match="start-hz"):
        generate_log_sweep(tmp_path / "bad.wav", start_hz=1000, end_hz=100)


from __future__ import annotations

import json
import math

import pytest

from pipetune import cli
from pipetune.measurement import MeasurementError
from pipetune.measurement.wav import inspect_wav, write_mono_float32, write_mono_pcm16, write_pcm16


def _sine(frequency_hz: float, *, sample_rate: int = 8000, duration_seconds: float = 1.0, amplitude: float = 0.5) -> list[float]:
    return [
        amplitude * math.sin(2.0 * math.pi * frequency_hz * index / sample_rate)
        for index in range(int(sample_rate * duration_seconds))
    ]


def test_inspect_wav_reports_1khz_sine_levels_and_dominant_frequency(tmp_path) -> None:
    path = tmp_path / "sine-1khz.wav"
    write_mono_pcm16(path, _sine(1000), 8000)

    result = inspect_wav(path)

    assert result.channel_count == 1
    assert result.sample_width_or_format == "pcm_s16"
    assert result.measurement_quality == "pass"
    assert result.clipping_detected is False
    assert result.silence_detected is False
    assert result.peak_dbfs == -6.021
    assert -9.05 <= result.rms_dbfs <= -9.0
    assert result.dominant_frequency_hz is not None
    assert 990 <= result.dominant_frequency_hz <= 1010


def test_inspect_wav_reports_100hz_sine_dominant_frequency(tmp_path) -> None:
    path = tmp_path / "sine-100hz.wav"
    write_mono_pcm16(path, _sine(100), 8000)

    result = inspect_wav(path)

    assert result.dominant_frequency_hz is not None
    assert 95 <= result.dominant_frequency_hz <= 105


def test_inspect_wav_handles_stereo_pcm(tmp_path) -> None:
    path = tmp_path / "stereo.wav"
    left = _sine(1000, amplitude=0.4)
    right = _sine(1000, amplitude=0.4)
    write_pcm16(path, [left, right], 8000)

    result = inspect_wav(path)

    assert result.channel_count == 2
    assert result.sample_width_or_format == "pcm_s16"
    assert result.measurement_quality == "pass"


def test_inspect_wav_handles_float32_wav(tmp_path) -> None:
    path = tmp_path / "float.wav"
    write_mono_float32(path, _sine(1000, amplitude=0.25), 8000)

    result = inspect_wav(path)

    assert result.sample_width_or_format == "float32"
    assert result.measurement_quality == "pass"


def test_inspect_wav_detects_quiet_clipped_silent_and_dc_offset(tmp_path) -> None:
    quiet = tmp_path / "quiet.wav"
    clipped = tmp_path / "clipped.wav"
    silent = tmp_path / "silent.wav"
    dc_offset = tmp_path / "dc.wav"

    write_mono_pcm16(quiet, [0.000001] * 8000, 8000)
    write_mono_pcm16(clipped, [1.0] * 8000, 8000)
    write_mono_pcm16(silent, [0.0] * 8000, 8000)
    write_mono_pcm16(dc_offset, [sample + 0.05 for sample in _sine(1000, amplitude=0.2)], 8000)

    assert inspect_wav(quiet).measurement_quality == "fail"
    assert inspect_wav(clipped).clipping_detected is True
    assert inspect_wav(silent).silence_detected is True
    dc_result = inspect_wav(dc_offset)
    assert "dc_offset" in dc_result.quality_flags
    assert dc_result.measurement_quality == "warn"


def test_inspect_wav_cli_human_and_json_output(tmp_path, capsys) -> None:
    path = tmp_path / "sine.wav"
    write_mono_pcm16(path, _sine(1000), 8000)

    exit_code = cli.main(["measure", "inspect-wav", "--input", str(path)])
    human = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune WAV Inspection" in human
    assert "Verdict: pass" in human
    assert "No system configuration was modified." in human

    exit_code = cli.main(["measure", "inspect-wav", "--input", str(path), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert data["sample_rate"] == 8000
    assert data["measurement_quality"] == "pass"


def test_inspect_wav_rejects_empty_file(tmp_path) -> None:
    path = tmp_path / "empty.wav"
    path.write_bytes(b"")

    with pytest.raises(MeasurementError, match="Invalid WAV"):
        inspect_wav(path)

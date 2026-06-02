from __future__ import annotations

from pipetune.measurement.analysis import analyze_sweep
from pipetune.measurement.sweep import generate_log_sweep
from pipetune.measurement.wav import write_mono_pcm16


def test_analyze_sweep_detects_clipping(tmp_path) -> None:
    sweep = tmp_path / "sweep.wav"
    recorded = tmp_path / "clipped.wav"
    report = tmp_path / "report.json"

    generate_log_sweep(sweep, duration_seconds=1, sample_rate=8000, start_hz=100, end_hz=3000, amplitude=0.3)
    write_mono_pcm16(recorded, [1.0] * 8000, 8000)

    result = analyze_sweep(sweep, recorded, report)

    assert result.clipping_detected is True
    assert result.measurement_quality == "fail"
    assert report.exists()


def test_analyze_sweep_reports_quiet_recording_warning_or_fail(tmp_path) -> None:
    sweep = tmp_path / "sweep.wav"
    recorded = tmp_path / "quiet.wav"
    report = tmp_path / "report.json"
    csv_output = tmp_path / "response.csv"

    generate_log_sweep(sweep, duration_seconds=1, sample_rate=8000, start_hz=100, end_hz=3000, amplitude=0.3)
    write_mono_pcm16(recorded, [0.00001] * 8000, 8000)

    result = analyze_sweep(sweep, recorded, report, csv_output=csv_output)

    assert result.measurement_quality in {"warn", "fail"}
    assert "quiet" in result.analysis_warning.lower()
    assert csv_output.read_text(encoding="utf-8").startswith("freq_hz,magnitude_db")

